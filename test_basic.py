#!/usr/bin/env python3
"""
Simple test runner script to verify our testing setup
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    from gmail_automation.config import unix_to_readable, validate_and_normalize_config

    print("✓ Successfully imported config module")

    # Test unix_to_readable
    result = unix_to_readable(1672531200)
    print(f"✓ unix_to_readable(1672531200) = {result}")

    # Test with invalid input
    result = unix_to_readable("invalid")
    print(f"✓ unix_to_readable('invalid') = {result}")

    # Test config validation
    test_config = {
        "SENDER_TO_LABELS": {
            "test": [{"read_status": "true", "delete_after_days": "30"}]
        }
    }
    normalized = validate_and_normalize_config(test_config)
    print(
        f"✓ Config validation works: {normalized['SENDER_TO_LABELS']['test'][0]['read_status']}"
    )

    print("\n✅ All basic tests passed!")

except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
