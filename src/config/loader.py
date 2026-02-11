import yaml
import os
from .models import ShotMenuConfig, SystemRulesConfig

class ConfigLoaderError(Exception):
    pass

def load_shot_menu(path: str) -> ShotMenuConfig:
    if not os.path.exists(path):
        raise ConfigLoaderError(f"Shot Menu not found at: {path}")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return ShotMenuConfig(**data)
    except Exception as e:
        raise ConfigLoaderError(f"Failed to load Shot Menu from {path}: {e}")

def load_system_rules(path: str) -> SystemRulesConfig:
    if not os.path.exists(path):
        raise ConfigLoaderError(f"System Rules not found at: {path}")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return SystemRulesConfig(**data)
    except Exception as e:
        raise ConfigLoaderError(f"Failed to load System Rules from {path}: {e}")
