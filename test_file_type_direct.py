#!/usr/bin/env python
"""
Direct test of file type save functionality (no UI dependencies)
"""

import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.json_manager import json_manager

def test_file_type_save():
    """Test file type save directly"""
    print("=" * 60)
    print("DIRECT FILE TYPE SAVE TEST")
    print("=" * 60)

    # Test data
    test_data = {
        "test_invoice": {
            "columns": {
                "invoice_no": "InvoiceNumber",
                "date": "InvoiceDate",
                "amount": "Amount"
            },
            "dtypes": {
                "InvoiceNumber": "NVARCHAR(100)",
                "InvoiceDate": "DATE",
                "Amount": "DECIMAL(18,2)"
            }
        },
        "test_payment": {
            "columns": {
                "payment_id": "PaymentID",
                "date": "PaymentDate"
            },
            "dtypes": {
                "PaymentID": "NVARCHAR(50)",
                "PaymentDate": "DATE"
            }
        }
    }

    print("\n1. Saving file types...")
    for file_type, data in test_data.items():
        success = json_manager.save_file_type(
            file_type,
            data['columns'],
            data['dtypes']
        )

        if not success:
            print(f"✗ Failed to save {file_type}")
            return False

        print(f"✓ Saved {file_type}")

    print("\n2. Verifying saved files...")
    file_types_dir = "config/file_types"

    for file_type, expected_data in test_data.items():
        filepath = os.path.join(file_types_dir, f"{file_type}.json")

        if not os.path.exists(filepath):
            print(f"✗ {file_type}.json not found!")
            return False

        # Load and verify
        with open(filepath, 'r') as f:
            loaded = json.load(f)

        if loaded['columns'] != expected_data['columns']:
            print(f"✗ {file_type} columns mismatch!")
            return False

        if loaded['dtypes'] != expected_data['dtypes']:
            print(f"✗ {file_type} dtypes mismatch!")
            return False

        print(f"✓ {file_type}.json verified")
        print(f"  - {len(loaded['columns'])} columns")
        print(f"  - {len(loaded['dtypes'])} dtypes")

    print("\n3. Testing json_manager.list_file_types()...")
    file_types = json_manager.list_file_types()

    if "test_invoice" not in file_types:
        print("✗ test_invoice not in list!")
        return False

    if "test_payment" not in file_types:
        print("✗ test_payment not in list!")
        return False

    print(f"✓ Found {len(file_types)} file types: {file_types}")

    print("\n4. Testing json_manager.load_file_type()...")
    for file_type, expected_data in test_data.items():
        loaded = json_manager.load_file_type(file_type)

        if loaded['columns'] != expected_data['columns']:
            print(f"✗ load_file_type({file_type}) columns mismatch!")
            return False

        if loaded['dtypes'] != expected_data['dtypes']:
            print(f"✗ load_file_type({file_type}) dtypes mismatch!")
            return False

        print(f"✓ load_file_type({file_type}) works correctly")

    print("\n5. Cleaning up test files...")
    for file_type in test_data.keys():
        success = json_manager.delete_file_type(file_type)
        if success:
            print(f"✓ Deleted {file_type}")
        else:
            print(f"Warning: Could not delete {file_type}")

    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nนี่แสดงว่า:")
    print("- json_manager.save_file_type() ทำงานได้")
    print("- ไฟล์ถูกสร้างที่ config/file_types/")
    print("- โครงสร้างถูกต้อง (columns + dtypes)")
    print("- json_manager.load_file_type() ทำงานได้")
    print("- json_manager.list_file_types() ทำงานได้")
    print("\nตอนนี้เมื่อคุณเพิ่ม file type ผ่าน UI")
    print("จะบันทึกไปที่ config/file_types/*.json แล้ว!")
    return True

if __name__ == '__main__':
    try:
        success = test_file_type_save()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
