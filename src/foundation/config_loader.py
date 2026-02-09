import os
import yaml
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class PathsConfig(BaseModel):
    artifacts_root: str = "artifacts"
    logs_root: str = "logs"

class ParamsConfig(BaseModel):
    max_rerenders: int = 3
    veo_duration_seconds: float = 8.0
    usable_cut_seconds: float = 4.0
    min_beat_duration_s: float = 2.0
    max_beat_duration_s: float = 12.0
    default_image_aspect_ratio: str = "16:9"
    img2img_strength_default: float = 0.75

class TogglesConfig(BaseModel):
    dry_run: bool = False
    stubs_only: bool = False

class AppConfig(BaseModel):
    paths: PathsConfig
    params: ParamsConfig
    toggles: TogglesConfig

    @classmethod
    def load(cls, config_path: str = "configs/config.yaml") -> "AppConfig":
        """
        Load config from yaml file and override with environment variables.
        Env var format: APP_PATHS_ARTIFACTS_ROOT, APP_PARAMS_MAX_RERENDERS, etc.
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, "r") as f:
            yaml_data = yaml.safe_load(f)

        # Basic env var override mechanism (recursive)
        # Flattened override: e.g. APP_PARAMS__MAX_RERENDERS
        _override_from_env(yaml_data)

        return cls(**yaml_data)

def _override_from_env(data: Dict[str, Any], prefix: str = "APP", sep: str = "__"):
    """
    Recursively checks for env vars to override config.
    Key structure matches yaml: params -> max_rerenders becomes APP__PARAMS__MAX_RERENDERS
    """
    for key, value in data.items():
        env_key = f"{prefix}{sep}{key.upper()}"
        if isinstance(value, dict):
            _override_from_env(value, prefix=env_key, sep=sep)
        else:
            env_val = os.getenv(env_key)
            if env_val is not None:
                # Type casting based on current value type
                if isinstance(value, bool):
                     data[key] = env_val.lower() in ('true', '1', 'yes')
                elif isinstance(value, int):
                     data[key] = int(env_val)
                elif isinstance(value, float):
                     data[key] = float(env_val)
                else:
                     data[key] = env_val
