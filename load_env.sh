#!/bin/bash
# load_env.sh - Helper script to safely load .env variables

set -a  # automatically export all variables
source .env
set +a

echo "✅ Environment variables loaded:"
echo "   GEMINI_API_KEY: ${GEMINI_API_KEY:0:20}..."
echo "   AGENT_MODEL: $AGENT_MODEL"
echo "   AGENT_MOCK_MODE: $AGENT_MOCK_MODE"
echo "   KIE_API_KEY: ${KIE_API_KEY:0:20}..."
echo "   ALIGNMENT_MODE: $ALIGNMENT_MODE"
