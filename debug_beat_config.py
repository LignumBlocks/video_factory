#!/usr/bin/env python3
"""Quick debug of beat segmenter integration"""
import os
import sys
from dotenv import load_dotenv
load_dotenv()

from src.config.loader import load_system_rules
from src.llm.factory import build_llm_client_from_config

# Load config
system_rules = load_system_rules("config/system_rules.yaml")
agent_config = system_rules.agent_settings.beat_segmenter

print("Agent config:", agent_config)
print("Type:", type(agent_config))

# Try to build client
try:
    llm = build_llm_client_from_config(agent_config)
    print("✅ Client created successfully:", llm)
except Exception as e:
    print(f"❌ Error creating client: {e}")
    import traceback
    traceback.print_exc()
