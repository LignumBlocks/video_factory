import os
import requests
import time
import json
import base64
import subprocess
import tempfile
from typing import Dict, Optional, Union
from ..models import VeoRequest

class VeoClient:
    """
    Client for Kie.ai Veo API (Async).
    """
    def __init__(self, api_key: Optional[str] = None):
        # Prefer KIE_API_KEY
        self.api_key = api_key or os.environ.get("KIE_API_KEY") or os.environ.get("VEO_API_KEY")
        self.base_url = os.environ.get("KIE_API_BASE", "https://api.kie.ai")
        self.model_id = os.environ.get("KIE_VEO_MODEL", "veo3_fast")
        
        # Mock mode environment check
        self.mock_mode = (os.environ.get("KIE_MOCK_MODE") == "1") or (os.environ.get("VEO_MOCK_MODE") == "1")
        
        if not self.api_key and not self.mock_mode:
             print("WARNING: KIE_API_KEY not set. Real generation will fail.")

    def generate_clip(self, req: VeoRequest) -> tuple[bytes, str]:
        """
        Generates a video clip via Kie.ai async job.
        Returns: (bytes, public_url)
        """
        if self.mock_mode:
            print(f"VEO (MOCK): Generating dummy clip for {req.shot_id} (Duration: {req.duration_s}s)")
            return self._generate_mock_mp4(), "http://mock.url/dummy.mp4"

        if not self.api_key:
            raise ValueError("VEO_API_KEY or KIE_API_KEY is not set.")

        task_id = self._create_task(req)
        video_url = self._poll_result(task_id)
        video_bytes = self._download_video(video_url)
        return video_bytes, video_url

    def _create_task(self, req: VeoRequest) -> str:
        url = f"{self.base_url}/api/v1/veo/generate"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Determine format for image inputs
        image_urls = []
        if req.image_ref_start:
             # Constraint from docs: "image DEBE ser una URL pública accesible"
             # If local path, we might fail here unless we have a hosting solution.
             # For now, we assume req.image_ref_start might be a URL or we warn.
             if req.image_ref_start.startswith("http") or req.image_ref_start.startswith("data:"):
                  image_urls.append(req.image_ref_start)
             else:
                  # If we are strictly following the guide, we can't send local files.
                  # However, if this is a pipeline run where we uploaded to GCS previously
                  # and stored that URL, we are good.
                  print(f"WARNING: Local file path detected for Veo input: {req.image_ref_start}. "
                        "Veo API requires public URLs.")
        
        if req.image_ref_end and req.image_ref_end.startswith("http"):
             image_urls.append(req.image_ref_end)

        # Determinar generationType basado en imageUrls
        if not image_urls:
            generation_type = "TEXT_2_VIDEO"
        elif len(image_urls) == 1:
            generation_type = "FIRST_AND_LAST_FRAMES_2_VIDEO"
        elif len(image_urls) == 2:
            generation_type = "FIRST_AND_LAST_FRAMES_2_VIDEO"
        else:  # >= 3 imágenes
            generation_type = "REFERENCE_2_VIDEO"  # Solo veo3_fast + 16:9
        
        payload = {
            "prompt": req.prompt,
            "model": self.model_id,
            "aspect_ratio": req.aspect_ratio,  # snake_case según docs
            "imageUrls": image_urls,  # Optional
            "generationType": generation_type,
            "enableTranslation": True  # Traducir prompts a inglés
        }
        
        # Agregar seeds si está en rango válido (10000-99999)
        if req.seeds and 10000 <= req.seeds <= 99999:
            payload["seeds"] = req.seeds
        
        print(f"VEO CREATE: {req.shot_id} -> {url}")
        # UPDATE: Increase timeout to 120s to avoid creation failures
        resp = requests.post(url, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("code") != 200:
             raise RuntimeError(f"Kie.ai Veo Error: {data.get('msg')}")
             
        task_id = data.get("data", {}).get("taskId")
        if not task_id:
            raise ValueError("No taskId received from Kie.ai Veo API")
        return task_id

    def _poll_result(self, task_id: str) -> str:
        url = f"{self.base_url}/api/v1/veo/record-info"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        max_total_seconds = 20 * 60  # 20 min real (wall clock)
        poll_interval = 10
        start = time.time()

        print(f"VEO POLLING: {task_id}...")

        attempt = 0
        while True:
            attempt += 1
            elapsed = int(time.time() - start)
            if elapsed > max_total_seconds:
                raise TimeoutError(f"Veo task {task_id} timed out after {elapsed}s.")
            
            try:
                # UPDATE: Increase timeout to 60s and add retry logic
                resp = requests.get(url, params={"taskId": task_id}, headers=headers, timeout=60)
                resp.raise_for_status()
                res_data = resp.json()
            except requests.exceptions.ReadTimeout:
                print(f"VEO POLL TIMEOUT (Attempt {attempt}): Request timed out. Retrying...")
                time.sleep(poll_interval)
                continue
            except requests.exceptions.RequestException as e:
                print(f"VEO POLL NETWORK ERROR (Attempt {attempt}): {e}. Retrying...")
                time.sleep(poll_interval)
                continue

            # Validate code/msg
            if res_data.get("code") != 200:
                print(f"VEO POLL non-200 code payload: {res_data}")
                time.sleep(poll_interval)
                continue

            data = res_data.get("data") or {}
            if attempt == 1:
                print(f"VEO RESPONSE STRUCTURE (first poll): {json.dumps(res_data, indent=2)[:800]}")

            # Official fields: data.successFlag, data.response.resultUrls
            success_flag = data.get("successFlag")
            error_code = data.get("errorCode")
            error_msg = data.get("errorMessage", "")

            # Normalize flag (handle "1" vs 1)
            try:
                success_flag_norm = int(success_flag) if success_flag is not None else None
            except (ValueError, TypeError):
                success_flag_norm = None

            response_obj = data.get("response") or {}
            result_urls = response_obj.get("resultUrls") or []

            print(
                f"Poll {attempt}: elapsed={elapsed}s successFlag={success_flag} "
                f"errorCode={error_code} errorMessage={str(error_msg)[:120]} "
                f"resultUrls={len(result_urls)}"
            )

            # Success conditions
            if result_urls:
                return result_urls[0]

            if success_flag_norm == 1:
                raise ValueError("Veo job successFlag=1 but found no resultUrls in data.response.resultUrls")

            # Fail conditions
            if success_flag_norm in (2, 3):
                raise RuntimeError(f"Veo Generation Failed (Flag {success_flag_norm}) - {error_code}: {error_msg}")

            # Still running/queued
            time.sleep(poll_interval)

    def _download_video(self, url: str) -> bytes:
        print(f"Downloading Video Asset: {url}")
        r = requests.get(url, timeout=600) # Videos can be large
        r.raise_for_status()
        return r.content

    def _generate_mock_mp4(self) -> bytes:
        # Generate valid MP4 using ffmpeg locally
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # 1s green video 
            cmd = [
                "ffmpeg", "-y", "-f", "lavfi", 
                "-i", f"color=c=green:s=1280x720:r=30", 
                "-t", "1.0", # Minimal duration
                "-c:v", "libx264", "-preset", "ultrafast",
                "-f", "mp4",
                tmp_path
            ]
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            
            with open(tmp_path, "rb") as f:
                data = f.read()
            return data
        except Exception as e:
            print(f"MOCK GEN FAILED: {e}")
            return b"FAKE_MP4_CONTENT"
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
