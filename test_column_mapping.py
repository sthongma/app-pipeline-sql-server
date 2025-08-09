#!/usr/bin/env python3
"""
Test script สำหรับทดสอบการแก้ไข column mapping
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.file_reader_service import FileReaderService
import json

def test_column_mapping():
    """ทดสอบฟังก์ชัน column mapping ที่แก้ไขแล้ว"""
    
    # สร้าง FileReaderService
    file_reader = FileReaderService()
    
    print("=== ทดสอบ Column Mapping ===")
    print(f"Column Settings ที่โหลด: {len(file_reader.column_settings)} ประเภท")
    
    for logic_type, mapping in file_reader.column_settings.items():
        print(f"\nประเภทไฟล์: {logic_type}")
        print(f"   จำนวนคอลัมน์: {len(mapping)}")
        
        # ตรวจสอบ identity mapping
        normalized_keys = set(file_reader.normalize_col(k) for k in mapping.keys())
        normalized_vals = set(file_reader.normalize_col(v) for v in mapping.values())
        is_identity = normalized_keys == normalized_vals
        
        print(f"   Identity Mapping: {is_identity}")
        
        # แสดงตัวอย่างคอลัมน์
        sample_cols = list(mapping.items())[:3]
        print(f"   ตัวอย่างคอลัมน์:")
        for key, val in sample_cols:
            norm_key = file_reader.normalize_col(key)
            norm_val = file_reader.normalize_col(val)
            print(f"     '{key}' -> '{val}'")
            print(f"     normalized: '{norm_key}' -> '{norm_val}'")
    
    return file_reader

def test_debug_function(file_reader, test_file_path=None):
    """ทดสอบ debug function"""
    
    if not test_file_path:
        print("\n[WARNING] ไม่มีไฟล์ทดสอบ - ข้าม debug test")
        return
    
    if not os.path.exists(test_file_path):
        print(f"\n[WARNING] ไม่พบไฟล์: {test_file_path}")
        return
    
    print(f"\n=== ทดสอบ Debug Function กับไฟล์: {test_file_path} ===")
    
    debug_info = file_reader.debug_column_mapping(test_file_path)
    
    if "error" in debug_info:
        print(f"[ERROR] Error: {debug_info['error']}")
        return
    
    print(f"ตรวจจับประเภทไฟล์: {debug_info.get('detected_logic_type', 'ไม่พบ')}")
    print(f"จำนวนคอลัมน์ในไฟล์: {debug_info.get('actual_columns_count', 0)}")
    
    if debug_info.get('actual_columns'):
        print(f"คอลัมน์จริงในไฟล์:")
        for i, col in enumerate(debug_info['actual_columns'][:5], 1):
            normalized = file_reader.normalize_col(col)
            print(f"   {i}. '{col}' -> normalized: '{normalized}'")
        
        if len(debug_info['actual_columns']) > 5:
            print(f"   ... และอีก {len(debug_info['actual_columns']) - 5} คอลัมน์")
    
    if debug_info.get('rename_mapping'):
        print(f"\nRename Mapping ({debug_info.get('rename_mapping_count', 0)} คอลัมน์):")
        for old_name, new_name in list(debug_info['rename_mapping'].items())[:3]:
            print(f"   '{old_name}' -> '{new_name}'")
    else:
        print(f"\nRename Mapping: ไม่มี (identity mapping หรือไม่ตรงกัน)")
    
    # แสดงสถิติการจับคู่
    if 'keys_match_count' in debug_info:
        print(f"\nสถิติการจับคู่:")
        print(f"   Keys match: {debug_info['keys_match_count']}")
        print(f"   Values match: {debug_info['values_match_count']}")
        print(f"   Identity mapping: {debug_info.get('is_identity_mapping', False)}")
        
        if debug_info.get('missing_from_actual'):
            print(f"   คอลัมน์ที่หายไป: {debug_info['missing_from_actual'][:3]}")
        
        if debug_info.get('extra_in_actual'):
            print(f"   คอลัมน์เพิ่มเติม: {debug_info['extra_in_actual'][:3]}")

def main():
    """ฟังก์ชันหลัก"""
    print("=== เริ่มทดสอบ Column Mapping ===")  
    
    # ทดสอบระบบ mapping
    file_reader = test_column_mapping()
    
    # ลองหาไฟล์ทดสอบใน Downloads
    downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
    test_files = []
    
    if os.path.exists(downloads_path):
        for file in os.listdir(downloads_path):
            if file.lower().endswith(('.xlsx', '.xls', '.csv')):
                test_files.append(os.path.join(downloads_path, file))
    
    if test_files:
        print(f"\nพบไฟล์ทดสอบ: {len(test_files)} ไฟล์")
        
        # ทดสอบไฟล์แรก
        first_file = test_files[0]
        print(f"ทดสอบกับไฟล์: {os.path.basename(first_file)}")
        test_debug_function(file_reader, first_file)
        
        # ทดสอบการตรวจจับประเภทไฟล์
        detected_type = file_reader.detect_file_type(first_file)
        print(f"\nผลการตรวจจับประเภทไฟล์: {detected_type}")
        
        # ทดสอบกับ logic_type แบบบังคับ
        print("\n=== ทดสอบกับ jst แบบบังคับ ===")
        debug_info_forced = file_reader.debug_column_mapping(first_file, "jst")
        
        if "error" not in debug_info_forced:
            keys_match = debug_info_forced.get('keys_match_count', 0)
            values_match = debug_info_forced.get('values_match_count', 0)
            total_config = len(file_reader.column_settings.get('jst', {}))
            
            print(f"Keys match count: {keys_match}")
            print(f"Values match count: {values_match}")
            print(f"Total config columns: {total_config}")
            print(f"Score: {keys_match}/{total_config} = {keys_match/total_config:.3f}")
            
            # คำนวณ threshold ที่ใช้ (เหมือนกับใน detect_file_type)
            if total_config >= 50:
                min_threshold = max(0.1, 5/total_config)
            elif total_config >= 20:
                min_threshold = max(0.2, 5/total_config)
            else:
                min_threshold = 0.3
            print(f"Minimum threshold: {min_threshold:.3f}")
            print(f"Pass threshold: {(keys_match/total_config) >= min_threshold}")
            print(f"Rename mapping count: {debug_info_forced.get('rename_mapping_count', 0)}")
            
            if debug_info_forced.get('keys_intersection'):
                print(f"Keys intersection (first 5): {debug_info_forced['keys_intersection'][:5]}")
            if debug_info_forced.get('missing_from_actual'):
                print(f"Missing from actual (first 5): {debug_info_forced['missing_from_actual'][:5]}")
            if debug_info_forced.get('extra_in_actual'):
                print(f"Extra in actual (first 5): {debug_info_forced['extra_in_actual'][:5]}")
        
    else:
        print(f"\n[WARNING] ไม่พบไฟล์ทดสอบใน {downloads_path}")
        print("   กรุณาใส่ไฟล์ Excel หรือ CSV ลงในโฟลเดอร์ Downloads เพื่อทดสอบ")
    
    print("\n[SUCCESS] ทดสอบเสร็จสิ้น")

if __name__ == "__main__":
    main()