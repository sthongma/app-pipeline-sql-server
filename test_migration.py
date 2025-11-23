#!/usr/bin/env python
"""
Quick test script to verify config migration
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.json_manager import json_manager, get_input_folder, set_input_folder
from services.settings_manager import settings_manager

def test_app_settings():
    """Test app_settings loading"""
    print("\n=== Testing app_settings ===")
    settings = json_manager.load('app_settings')

    print(f"✓ Window size: {settings.get('window_size')}")
    print(f"✓ Theme: {settings.get('theme')}")
    print(f"✓ Folders: {settings.get('folders')}")
    print(f"✓ File management: {settings.get('file_management')}")

    assert 'folders' in settings, "Missing 'folders' key"
    assert 'file_management' in settings, "Missing 'file_management' key"
    print("✓ app_settings structure is correct")

def test_folder_helpers():
    """Test folder helper functions"""
    print("\n=== Testing Folder Helpers ===")

    # Test getting folders (should be empty initially)
    input_folder = get_input_folder()
    print(f"✓ get_input_folder(): '{input_folder}'")

    # Test setting folder
    test_path = "/test/path"
    success = set_input_folder(test_path)
    assert success, "Failed to set input folder"

    # Verify it was saved
    new_path = get_input_folder()
    assert new_path == test_path, f"Expected '{test_path}', got '{new_path}'"
    print(f"✓ set_input_folder() works: '{new_path}'")

    # Reset to empty
    set_input_folder("")

def test_file_type():
    """Test file type operations"""
    print("\n=== Testing File Type Operations ===")

    # Create a test file type
    test_columns = {
        "invoice_no": "InvoiceNumber",
        "date": "InvoiceDate",
        "amount": "Amount"
    }

    test_dtypes = {
        "InvoiceNumber": "NVARCHAR(100)",
        "InvoiceDate": "DATE",
        "Amount": "DECIMAL(18,2)"
    }

    # Save file type
    success = json_manager.save_file_type("test_invoice", test_columns, test_dtypes)
    assert success, "Failed to save file type"
    print("✓ Saved file type: test_invoice")

    # Load file type
    loaded = json_manager.load_file_type("test_invoice")
    assert loaded['columns'] == test_columns, "Columns mismatch"
    assert loaded['dtypes'] == test_dtypes, "Dtypes mismatch"
    print(f"✓ Loaded file type: {len(loaded['columns'])} columns, {len(loaded['dtypes'])} dtypes")

    # List file types
    file_types = json_manager.list_file_types()
    assert "test_invoice" in file_types, "test_invoice not in list"
    print(f"✓ Listed file types: {file_types}")

    # Test settings_manager integration
    columns = settings_manager.get_column_settings("test_invoice")
    assert columns == test_columns, "Settings manager returned wrong columns"
    print("✓ settings_manager.get_column_settings() works")

    dtypes = settings_manager.get_dtype_settings("test_invoice")
    assert dtypes == test_dtypes, "Settings manager returned wrong dtypes"
    print("✓ settings_manager.get_dtype_settings() works")

    # Clean up
    json_manager.delete_file_type("test_invoice")
    print("✓ Deleted test file type")

def test_backward_compatibility():
    """Test that legacy code still works"""
    print("\n=== Testing Backward Compatibility ===")

    # Import legacy functions
    from config.json_manager import load_file_management_settings

    # Should work even though structure changed
    file_mgmt = load_file_management_settings()
    assert isinstance(file_mgmt, dict), "load_file_management_settings() failed"
    print(f"✓ load_file_management_settings() works: {file_mgmt}")

def main():
    """Run all tests"""
    print("=" * 60)
    print("CONFIG MIGRATION TESTS")
    print("=" * 60)

    try:
        test_app_settings()
        test_folder_helpers()
        test_file_type()
        test_backward_compatibility()

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
