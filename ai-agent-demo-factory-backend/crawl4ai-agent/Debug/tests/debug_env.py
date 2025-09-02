#!/usr/bin/env python3
"""
Debug script to check if environment variables are loading
"""
import os
from pathlib import Path

# Try to load dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ python-dotenv loaded successfully")
except ImportError:
    print("❌ python-dotenv not available - install with: pip install python-dotenv")

# Check current working directory
print(f"Current working directory: {os.getcwd()}")

# Look for .env files
env_files = [
    Path(".env"),
    Path("../.env"),  
    Path("../../.env"),
    Path("../../../.env")
]

print("\nLooking for .env files:")
for env_file in env_files:
    if env_file.exists():
        print(f"✅ Found: {env_file.absolute()}")
        # Try to read first few lines
        try:
            with open(env_file, 'r') as f:
                lines = f.readlines()[:3]
                for line in lines:
                    if 'OPENAI_API_KEY' in line:
                        # Mask the key for security
                        masked = line.strip().replace(line.split('=')[1] if '=' in line else '', '***MASKED***')
                        print(f"   Content: {masked}")
        except Exception as e:
            print(f"   Could not read: {e}")
    else:
        print(f"❌ Not found: {env_file.absolute()}")

# Check environment variables
print(f"\nEnvironment variable check:")
openai_key = os.getenv('OPENAI_API_KEY')
if openai_key:
    masked_key = openai_key[:8] + '***' + openai_key[-4:] if len(openai_key) > 12 else '***MASKED***'
    print(f"✅ OPENAI_API_KEY found: {masked_key}")
else:
    print("❌ OPENAI_API_KEY not found in environment")

anthropic_key = os.getenv('ANTHROPIC_API_KEY')  
if anthropic_key:
    print(f"✅ ANTHROPIC_API_KEY found: {anthropic_key[:8]}***")
else:
    print("❌ ANTHROPIC_API_KEY not found in environment")

# Test the AI config loading
print(f"\nTesting AI config loading:")
try:
    from ai_config import get_ai_config
    config = get_ai_config()
    if config.openai_api_key:
        masked = config.openai_api_key[:8] + '***' if len(config.openai_api_key) > 8 else '***'
        print(f"✅ AI config loaded OpenAI key: {masked}")
    else:
        print("❌ AI config did not load OpenAI key")
        
    print(f"   Preferred model: {config.preferred_model}")
    print(f"   Fallback model: {config.fallback_model}")
    
except Exception as e:
    print(f"❌ Error loading AI config: {e}")