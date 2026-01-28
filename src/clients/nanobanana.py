import os
import requests
import time
import json
import base64
from typing import Optional, Tuple
from ..models import NanobananaRequest

class NanobananaClient:
    """
    Client for Kie.ai Nano Banana API (Async).
    """
    def __init__(self, api_key: Optional[str] = None):
        # Prefer KIE_API_KEY, fallback to specific key
        self.api_key = api_key or os.environ.get("KIE_API_KEY") or os.environ.get("NANOBANANA_API_KEY")
        self.base_url = os.environ.get("KIE_API_BASE", "https://api.kie.ai")
        self.model_id = os.environ.get("KIE_NANO_BANANA_MODEL", "nano-banana-pro")
        
        if not self.api_key:
            print("WARNING: KIE_API_KEY (or NANOBANANA_API_KEY) not set. Real generation will fail.")


    def generate_image(self, request: NanobananaRequest) -> Tuple[bytes, str]:
        """
        Generates a single image via Kie.ai async job.
        Returns (image_bytes, remote_url).
        """
        # [MOCK MODE] Cost-free validation
        if os.environ.get("KIE_MOCK_MODE") == "1" or os.environ.get("NANOBANANA_MOCK_MODE") == "1":
            print(f"NANOBANANA (MOCK): Generating dummy bytes for {request.shot_id}")
            # Return 1x1 transparent PNG bytes + dummy URL
            dummy_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
            return (dummy_bytes, "https://mock.kie.ai/image.png")

        if not self.api_key:
            raise ValueError("Missing KIE_API_KEY")

        task_id = self._create_task(request)
        image_url = self._poll_result(task_id)
        img_bytes = self._download_image(image_url)
        return (img_bytes, image_url)

    def _create_task(self, req: NanobananaRequest) -> str:
        url = f"{self.base_url}/api/v1/jobs/createTask"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Base Input según documentación oficial de Kie.ai
        input_payload = {
            "prompt": req.prompt,
            "aspect_ratio": getattr(req, 'aspect_ratio', "16:9"),  # Default 16:9
            "resolution": "1K",  # Default 1K
            "output_format": "png"
        }
        
        # Agregar negative_prompt solo si el modelo lo soporta (opcional)
        if req.negative_prompt:
            input_payload["negative_prompt"] = req.negative_prompt
        
        # Img2Img Injection
        if req.image_input_path:
            if req.image_input_path.startswith("http"):
                 print(f"NANOBANANA: Using Init Image URL: {req.image_input_path}")
                 input_payload["image_input"] = [req.image_input_path]  # Array de URLs
                 input_payload["strength"] = req.image_strength
            elif os.path.exists(req.image_input_path):
                print(f"NANOBANANA: Using Init Image File: {req.image_input_path}")
                try:
                    with open(req.image_input_path, "rb") as img_file:
                        encoded_string = base64.b64encode(img_file.read()).decode('utf-8')
                        input_payload["image_input"] = [f"data:image/png;base64,{encoded_string}"]  # Array
                        input_payload["strength"] = req.image_strength
                except Exception as e:
                    print(f"WARNING: Failed to read init image {req.image_input_path}: {e}")
            else:
                print(f"WARNING: Init Image not found: {req.image_input_path}")

        payload = {
            "model": self.model_id,
            "input": input_payload
        }
        # If we had image input support in our Request model, we would add it here
        
        print(f"NANOBANANA CREATE: {req.shot_id} -> {url}")
        resp = requests.post(url, json=payload, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("code") != 200:
             raise RuntimeError(f"Kie.ai Error: {data.get('msg')}")
             
        task_id = data.get("data", {}).get("taskId")
        if not task_id:
            raise ValueError("No taskId received from Kie.ai")
        return task_id

    def _poll_result(self, task_id: str) -> str:
        url = f"{self.base_url}/api/v1/jobs/recordInfo"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        max_retries = 90 # 90 * 2s = 180s (3 min) max wait
        
        print(f"NANOBANANA POLLING: {task_id}...")
        
        for attempt in range(max_retries):
            try:
                resp = requests.get(url, params={"taskId": task_id}, headers=headers, timeout=10)
                resp.raise_for_status()
                res_data = resp.json()
            except Exception as e:
                print(f"Polling warning (attempt {attempt}): {e}")
                time.sleep(2)
                continue
            
            # According to docs: data.state
            inner_data = res_data.get("data", {})
            state = inner_data.get("state")
            
            if attempt % 10 == 0:  # Log every 20 seconds
                print(f"  Polling status (attempt {attempt}/90): state={state}")
            
            if state == "success":
                result_str = inner_data.get("resultJson", "{}")
                try:
                    result_json = json.loads(result_str)
                    urls = result_json.get("resultUrls", [])
                    if urls:
                        print(f"✓ Generation complete: {urls[0]}")
                        return urls[0] # Return first image
                except:
                    print(f"Error parsing resultJson: {result_str}")
                    pass
                raise ValueError("Job succeeded but found no image URL")
            
            elif state == "fail":
                fail_msg = inner_data.get("failMsg", "Unknown error")
                raise RuntimeError(f"Nanobanana Generation Failed: {fail_msg}")
            
            else:
                # waiting, queuing, generating
                time.sleep(2)
        
        raise TimeoutError(f"Nanobanana task {task_id} timed out after {max_retries * 2}s. Last state: {state if 'state' in locals() else 'unknown'}")

    def _download_image(self, url: str) -> bytes:
        print(f"Downloading Asset: {url}")
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return r.content
