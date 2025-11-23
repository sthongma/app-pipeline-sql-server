#!/usr/bin/env python
"""
Simple test for config structure (no UI dependencies)
"""

import json
import os

def test_config_structure():
    """Test that config files have correct structure"""
    print("=" * 60)
    print("SIMPLE CONFIG STRUCTURE TEST")
    print("=" * 60)

    # Test 1: app_settings.json structure
    print("\n=== Testing app_settings.json ===")
    app_settings_path = "config/app_settings.json"

    if not os.path.exists(app_settings_path):
        print("✗ app_settings.json not found")
        return False

    with open(app_settings_path, 'r') as f:
        app_settings = json.load(f)

    # Check required keys
    required_keys = ['window_size', 'theme', 'backup_enabled', 'log_level', 'folders', 'file_management']
    for key in required_keys:
        if key not in app_settings:
            print(f"✗ Missing key: {key}")
            return False
        print(f"✓ Found key: {key}")

    # Check folders structure
    folder_keys = ['input_folder', 'output_folder', 'log_folder']
    for key in folder_keys:
        if key not in app_settings['folders']:
            print(f"✗ Missing folder key: {key}")
            return False
        print(f"✓ Found folder: {key} = '{app_settings['folders'][key]}'")

    # Check file_management structure
    fm_keys = ['auto_move_enabled', 'organize_by_date']
    for key in fm_keys:
        if key not in app_settings['file_management']:
            print(f"✗ Missing file_management key: {key}")
            return False
        print(f"✓ Found file_management: {key} = {app_settings['file_management'][key]}")

    # Test 2: file_types directory
    print("\n=== Testing file_types directory ===")
    file_types_dir = "config/file_types"

    if not os.path.exists(file_types_dir):
        print("✗ file_types directory not found")
        return False

    print(f"✓ file_types directory exists")

    # Test 3: Create and load a test file type
    print("\n=== Testing file type creation ===")
    test_file = os.path.join(file_types_dir, "test.json")

    test_data = {
        "columns": {
            "col1": "Column1",
            "col2": "Column2"
        },
        "dtypes": {
            "Column1": "NVARCHAR(100)",
            "Column2": "INT"
        }
    }

    with open(test_file, 'w') as f:
        json.dump(test_data, f, indent=2)
    print("✓ Created test file type")

    # Load and verify
    with open(test_file, 'r') as f:
        loaded = json.load(f)

    if loaded != test_data:
        print("✗ Loaded data doesn't match")
        return False
    print("✓ Loaded test file type correctly")

    # Clean up
    os.remove(test_file)
    print("✓ Cleaned up test file")

    # Test 4: Check backup
    print("\n=== Checking migration backup ===")
    config_dir = "config"
    backups = [d for d in os.listdir(config_dir) if d.startswith("backup_migration_")]

    if backups:
        print(f"✓ Found {len(backups)} backup(s): {backups}")
    else:
        print("Warning: No migration backup found")

    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED!")
    print("=" * 60)
    return True

if __name__ == '__main__':
    import sys
    success = test_config_structure()
    sys.exit(0 if success else 1)
