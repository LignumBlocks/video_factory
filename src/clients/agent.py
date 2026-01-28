import os
import requests
import json
from typing import Dict, Optional, Any

class AgentClient:
    """
    Client for interacting with an LLM-based Agent API (e.g., OpenAI compatible).
    Used for intelligent decisions like Visual Direction.
    """
    def __init__(self):
        self.api_key = os.environ.get("AGENT_API_KEY")
        gemini_key = os.environ.get("GEMINI_API_KEY")
        
        self.mock_mode = os.environ.get("AGENT_MOCK_MODE", "0") == "1"

        if gemini_key and not self.api_key:
            self.api_key = gemini_key
            # Default to Google OpenAI-compat endpoint
            self.base_url = os.environ.get("AGENT_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai")
            self.model = os.environ.get("AGENT_MODEL", "gemini-1.5-flash")
            print(f"DEBUG: Using Gemini API Key with model {self.model}")
        else:
            self.base_url = os.environ.get("AGENT_BASE_URL", "https://api.openai.com/v1")
            self.model = os.environ.get("AGENT_MODEL", "gpt-3.5-turbo")
        
        if not self.api_key and not self.mock_mode:
            print("WARNING: AGENT_API_KEY (or GEMINI_API_KEY) not set. Agent calls will fail or fallback if handled.")

    def suggest_visuals(self, script_text: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Asks the agent to suggest visual metaphors and camera movements for a given script segment.
        Expected return format:
        {
            "metaphor": "description...",
            "camera": "TILT_UP",
            "intent": "visualize growth..."
        }
        """
        if self.mock_mode or not self.api_key:
            # Return None to signal caller to use fallback heuristics
            return None

        prompt = f"""
        You are a Visual Director for a finance video.
        Analyze the following script segment and suggest a visual metaphor (image description) and a camera movement.
        
        Script Segment: "{script_text}"
        Context: {context or "N/A"}
        
        Available Camera Movements: STATIC, PAN_LEFT, PAN_RIGHT, TILT_UP, TILT_DOWN, ZOOM_IN, ZOOM_OUT
        
        Respond ONLY with a valid JSON object in this format:
        {{
            "metaphor": "Detailed visual description of the scene...",
            "camera": "CAMERA_MOVEMENT_ENUM",
            "intent": "Brief explanation of the director's intent..."
        }}
        """

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful creative assistant outputting JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }

        try:
            # Assuming OpenAI Chat Completion format, widely supported
            url = f"{self.base_url}/chat/completions"
            # Adjust if base_url includes /v1 etc
            if "chat/completions" not in url and not url.endswith("/"):
                 url += "/chat/completions"

            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            # Simple JSON cleanup if md blocks are used
            content = content.replace("```json", "").replace("```", "").strip()
            
            return json.loads(content)

        except Exception as e:
            print(f"Agent API Error: {e}")
            # On failure, return None -> Fallback
            return None

    def render_nanobanana_prompt(self, input_data: Dict) -> str:
        """
        GPT-04 Prompt Renderer for NanoBananaPro.
        Embeds Style Bible constraints into final prompt.
        """
        if self.mock_mode:
            # Fallback: simple concatenation (NO "frame" tokens)
            base = input_data['raw_prompt']
            role = input_data['pair_role']
            static = " | end_static=True" if input_data['end_static'] else ""
            return f"{base} | role={role}{static}"
        
        # Real GPT-04 call
        system_prompt = f"""You are GPT-04, the Prompt Renderer for NanoBananaPro.

LOCKED Style Bible (single source of truth):
{input_data['style_bible']}

YOUR TASK:
1. Read the raw prompt provided by the user
2. Identify any violations of the Style Bible rules
3. GENERATE A CORRECTED PROMPT that complies with ALL Style Bible rules
4. Return ONLY the corrected prompt text - NO explanations, NO analysis, NO error messages

CRITICAL RULES:
- NO humans, faces, hands, or body parts
- NO text, numbers, symbols, or UI elements
- NO motion for stills (start_ref/end_ref with end_static=True)
- Use ONLY whitelisted props and colors from the Style Bible
- Keep prompts abstract, minimal, and geometric
- If pair_role=end_ref and end_static=True: enforce "fully static, no motion cues"

OUTPUT FORMAT:
Return ONLY the final corrected prompt as plain text. Do NOT include:
- Error analysis
- Violation lists
- Explanations
- Meta-commentary
"""
        
        user_prompt = f"""Raw Prompt: {input_data['raw_prompt']}
Role: {input_data['pair_role']}
End Static: {input_data['end_static']}
Props Count: {input_data['props_count']}
Accent Color: {input_data['accent_color']}
A→B Plan: {input_data['ab_plan']}
A→B Changes Count: {input_data['ab_changes_count']}

Render final NanoBananaPro prompt:"""
        
        response = self._call_llm(system_prompt, user_prompt)
        return response.strip()

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Helper for LLM calls."""
        if not self.api_key:
            return f"{user_prompt} [MOCK_RESPONSE]"
            
        # Check for Gemini Key (AIza...) to use native REST API
        if self.api_key.startswith("AIza"):
            return self._call_gemini_native(system_prompt, user_prompt)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7
        }
        
        try:
            url = f"{self.base_url}/chat/completions"
            if "chat/completions" not in url and not url.endswith("/"):
                url += "/chat/completions"
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return content.strip()
        except Exception as e:
            print(f"LLM Call Error: {e}")
            return f"{user_prompt} [ERROR_FALLBACK]"

    def _call_gemini_native(self, system_prompt: str, user_prompt: str) -> str:
        """Native REST call to Gemini API."""
        # Use gemini-2.5-flash by default as 1.5 is deprecated/gone
        model = "gemini-2.5-flash" if "gpt" in self.model or "1.5" in self.model else self.model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
        
        # Merge system and user into a single prompt for simple models, or use system_instruction if supported
        # For Flash 2.5, simple concatenation is safest for REST.
        full_text = f"System: {system_prompt}\n\nUser: {user_prompt}"
        
        payload = {
            "contents": [{
                "parts": [{"text": full_text}]
            }],
            "generationConfig": {
                "temperature": 0.7
            }
        }
        
        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            # Extract text
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            print(f"Gemini Native Error: {e}")
            return f"{user_prompt} [GEMINI_ERROR]"

