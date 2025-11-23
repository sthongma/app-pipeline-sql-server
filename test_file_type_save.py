#!/usr/bin/env python
"""
Test script to verify file type save functionality
"""

import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def mock_log(msg):
    """Mock log function"""
    print(f"[LOG] {msg}")

def test_save_file_type():
    """Test saving file type through settings handler"""
    print("=" * 60)
    print("TEST: Save File Type")
    print("=" * 60)

    # Import after adding to path
    from ui.handlers.settings_handler import SettingsHandler

    # Create handler
    handler = SettingsHandler("dummy.json", mock_log)

    # Test data
    test_column_settings = {
        "test_invoice": {
            "invoice_no": "InvoiceNumber",
            "date": "InvoiceDate",
            "amount": "Amount"
        },
        "test_payment": {
            "payment_id": "PaymentID",
            "date": "PaymentDate"
        }
    }

    test_dtype_settings = {
        "test_invoice": {
            "InvoiceNumber": "NVARCHAR(100)",
            "InvoiceDate": "DATE",
            "Amount": "DECIMAL(18,2)"
        },
        "test_payment": {
            "PaymentID": "NVARCHAR(50)",
            "PaymentDate": "DATE"
        }
    }

    print("\n1. Saving column settings...")
    handler.save_column_settings(test_column_settings)

    print("\n2. Saving dtype settings...")
    handler.save_dtype_settings(test_dtype_settings)

    # Verify files were created
    print("\n3. Verifying file_types directory...")
    file_types_dir = "config/file_types"

    if not os.path.exists(file_types_dir):
        print("✗ file_types directory not found!")
        return False

    print(f"✓ file_types directory exists")

    # Check for created files
    expected_files = ["test_invoice.json", "test_payment.json"]

    for filename in expected_files:
        filepath = os.path.join(file_types_dir, filename)

        if not os.path.exists(filepath):
            print(f"✗ {filename} not found!")
            return False

        # Load and verify content
        with open(filepath, 'r') as f:
            content = json.load(f)

        file_type = filename.replace('.json', '')

        # Verify structure
        if 'columns' not in content or 'dtypes' not in content:
            print(f"✗ {filename} has invalid structure!")
            return False

        # Verify content
        expected_columns = test_column_settings[file_type]
        expected_dtypes = test_dtype_settings[file_type]

        if content['columns'] != expected_columns:
            print(f"✗ {filename} columns mismatch!")
            print(f"  Expected: {expected_columns}")
            print(f"  Got: {content['columns']}")
            return False

        if content['dtypes'] != expected_dtypes:
            print(f"✗ {filename} dtypes mismatch!")
            print(f"  Expected: {expected_dtypes}")
            print(f"  Got: {content['dtypes']}")
            return False

        print(f"✓ {filename} created and verified")
        print(f"  - {len(content['columns'])} columns")
        print(f"  - {len(content['dtypes'])} dtypes")

    # Clean up test files
    print("\n4. Cleaning up test files...")
    for filename in expected_files:
        filepath = os.path.join(file_types_dir, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"✓ Removed {filename}")

    # Also clean up legacy files if they exist
    legacy_files = ["config/column_settings.json", "config/dtype_settings.json"]
    for filepath in legacy_files:
        if os.path.exists(filepath):
            # Load current content
            with open(filepath, 'r') as f:
                content = json.load(f)

            # Remove test entries
            for test_type in ["test_invoice", "test_payment"]:
                content.pop(test_type, None)

            # Save back
            with open(filepath, 'w') as f:
                json.dump(content, f, indent=2)

    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED!")
    print("=" * 60)
    return True

if __name__ == '__main__':
    try:
        success = test_save_file_type()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
