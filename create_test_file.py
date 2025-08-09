#!/usr/bin/env python3
"""
สร้างไฟล์ทดสอบสำหรับ column mapping
"""

import pandas as pd
import os

def create_test_file():
    """สร้างไฟล์ Excel ทดสอบที่ใช้คอลัมน์จาก jst mapping"""
    
    # ใช้คอลัมน์จาก column_settings.json
    test_data = {
        'หมายเลขคำสั่งซื้อภายใน': [1001, 1002, 1003, 1004, 1005],
        'หมายเลขการสั่งซื้อออนไลน์': ['ON001', 'ON002', 'ON003', 'ON004', 'ON005'],
        'สินค้า ': ['สินค้า A', 'สินค้า B', 'สินค้า C', 'สินค้า D', 'สินค้า E'],
        'จำนวนชิ้น': [1, 2, 1, 3, 1],
        'สถานะคำสั่งซื้อ': ['จัดส่งแล้ว', 'รอจัดส่ง', 'จัดส่งแล้ว', 'ยกเลิก', 'จัดส่งแล้ว'],
        'บริษัทขนส่ง': ['Kerry', 'J&T', 'Flash', 'ไปรษณีย์', 'Kerry'],
        'เลขพัสดุ': ['K001', 'J001', 'F001', 'P001', 'K002'],
        'ราคาสินค้าทั้งหมด': [100.0, 250.0, 75.0, 450.0, 125.0],
        'เวลาสั่งซื้อ': ['2024-01-01 10:00', '2024-01-01 11:00', '2024-01-01 12:00', '2024-01-01 13:00', '2024-01-01 14:00'],
        'ร้านค้า​': ['Shop A', 'Shop B', 'Shop A', 'Shop C', 'Shop B']
    }
    
    df = pd.DataFrame(test_data)
    
    # สร้างโฟลเดอร์ Downloads ถ้าไม่มี
    downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(downloads_path, exist_ok=True)
    
    # บันทึกไฟล์
    test_file_path = os.path.join(downloads_path, "test_jst_data.xlsx")
    df.to_excel(test_file_path, index=False)
    
    print(f"สร้างไฟล์ทดสอบสำเร็จ: {test_file_path}")
    print(f"จำนวนแถว: {len(df)}")
    print(f"จำนวนคอลัมน์: {len(df.columns)}")
    print("คอลัมน์ในไฟล์:")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i}. '{col}'")
    
    return test_file_path

if __name__ == "__main__":
    create_test_file()