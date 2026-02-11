"""
T-101 Tests: Shot Menu and System Rules configuration
"""
import os
import pytest
from src.config.loader import load_shot_menu, load_system_rules, ConfigLoaderError
from src.config.models import ShotMenuConfig, SystemRulesConfig

def test_load_shot_menu_valid():
    """Test loading a valid shot menu"""
    menu = load_shot_menu("config/shot_menu.yaml")
    
    assert menu.schema_version == "1.0"
    assert menu.menu_id == "clean_score_jump_v1"
    assert len(menu.shot_types) == 3
    
    # Check specific shot type
    score_jump = next(s for s in menu.shot_types if s.id == "SCORE_JUMP")
    assert score_jump.description is not None
    assert score_jump.constraints.allow_amber == False
    assert "high" in score_jump.allowed.energy

def test_load_system_rules_valid():
    """Test loading valid system rules"""
    rules = load_system_rules("config/system_rules.yaml")
    
    assert rules.schema_version == "1.0"
    assert rules.run_mode_defaults.duration_s_default == 8
    assert rules.durations.enforce_exact == True
    assert "humans" in rules.guardrails.required_negative_terms
    assert rules.models.video.target == "veo"

def test_shot_id_validation():
    """Test that invalid shot IDs are rejected"""
    from src.config.models import ShotType, ShotAllowed, ShotConstraints
    
    with pytest.raises(ValueError, match="must match UPPER_SNAKE_CASE"):
        ShotType(
            id="invalid-id",  # Invalid format
            description="Test",
            allowed=ShotAllowed(),
            constraints=ShotConstraints()
        )

def test_duplicate_shot_ids():
    """Test that duplicate shot IDs are rejected"""
    from src.config.models import ShotMenuConfig, ShotType, ShotAllowed, ShotConstraints
    
    shot1 = ShotType(
        id="TEST_SHOT",
        description="Test 1",
        allowed=ShotAllowed(),
        constraints=ShotConstraints()
    )
    
    shot2 = ShotType(
        id="TEST_SHOT",  # Duplicate
        description="Test 2",
        allowed=ShotAllowed(),
        constraints=ShotConstraints()
    )
    
    with pytest.raises(ValueError, match="Duplicate Shot IDs"):
        ShotMenuConfig(
            menu_id="test_menu",
            shot_types=[shot1, shot2]
        )

def test_config_loader_error():
    """Test that missing config files raise ConfigLoaderError"""
    with pytest.raises(ConfigLoaderError, match="not found"):
        load_shot_menu("nonexistent.yaml")
