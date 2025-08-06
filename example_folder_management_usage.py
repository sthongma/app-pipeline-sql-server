#!/usr/bin/env python3
"""
ตัวอย่างการใช้งาน File Management Service กับฟีเจอร์ใหม่
- การตรวจสอบโฟลเดอร์ที่มีไฟล์
- การจัดกลุ่มตาม logic type เหมือน move_uploaded_files
"""

import os
import sys
from pathlib import Path

# เพิ่ม path ของ project
sys.path.insert(0, str(Path(__file__).parent))

from services.file_management_service import FileManagementService


def example_folder_analysis():
    """ตัวอย่างการวิเคราะห์โครงสร้างโฟลเดอร์"""
    print("🔍 ตัวอย่างการวิเคราะห์โครงสร้างโฟลเดอร์")
    print("=" * 60)
    
    # สร้าง service
    file_mgmt = FileManagementService()
    
    # เลือกโฟลเดอร์ที่ต้องการวิเคราะห์
    target_folder = input("📁 ระบุโฟลเดอร์ที่ต้องการวิเคราะห์ (หรือกด Enter เพื่อใช้โฟลเดอร์ปัจจุบัน): ").strip()
    
    if not target_folder:
        target_folder = os.getcwd()
    
    if not os.path.exists(target_folder):
        print(f"❌ ไม่พบโฟลเดอร์: {target_folder}")
        return
    
    print(f"\n🔎 กำลังวิเคราะห์โฟลเดอร์: {target_folder}")
    print("-" * 60)
    
    # วิเคราะห์โครงสร้าง
    analysis = file_mgmt.analyze_folder_structure(target_folder)
    
    # แสดงผล
    file_mgmt.print_folder_analysis(analysis)
    
    return analysis


def example_organize_folders():
    """ตัวอย่างการจัดระเบียบโฟลเดอร์ตาม logic type"""
    print("\n📦 ตัวอย่างการจัดระเบียบโฟลเดอร์ตาม Logic Type")
    print("=" * 60)
    
    # สร้าง service
    file_mgmt = FileManagementService()
    
    # เลือกโฟลเดอร์
    source_folder = input("📂 ระบุโฟลเดอร์ต้นทาง (หรือกด Enter เพื่อใช้โฟลเดอร์ปัจจุบัน): ").strip()
    if not source_folder:
        source_folder = os.getcwd()
    
    if not os.path.exists(source_folder):
        print(f"❌ ไม่พบโฟลเดอร์: {source_folder}")
        return
    
    # เลือกโฟลเดอร์ปลายทาง
    dest_folder = input("📥 ระบุโฟลเดอร์ปลายทาง (หรือกด Enter เพื่อใช้ 'Organized_Output'): ").strip()
    if not dest_folder:
        dest_folder = os.path.join(source_folder, "Organized_Output")
    
    print(f"\n🔄 กำลังจัดระเบียบจาก: {source_folder}")
    print(f"📥 ไปยัง: {dest_folder}")
    print("-" * 60)
    
    # ค้นหาโฟลเดอร์ที่มีไฟล์
    folder_info = file_mgmt.find_folders_with_files(source_folder)
    
    if not folder_info:
        print("ℹ️  ไม่พบโฟลเดอร์ที่มีไฟล์")
        return
    
    print("📋 พบโฟลเดอร์ที่มีไฟล์:")
    for logic_type, info in folder_info.items():
        print(f"  🏷️  {logic_type}: {len(info['folders'])} โฟลเดอร์, {info['count']} ไฟล์")
    
    # ยืนยันการย้าย
    confirm = input("\n❓ ต้องการย้ายโฟลเดอร์เหล่านี้หรือไม่? (y/N): ").strip().lower()
    
    if confirm in ['y', 'yes', 'ใช่']:
        print("\n🚀 กำลังย้ายโฟลเดอร์...")
        
        # ย้ายโฟลเดอร์
        moved_results = file_mgmt.move_folders_by_logic_type(folder_info, source_folder, dest_folder)
        
        print("\n✅ การย้ายเสร็จสิ้น!")
        for logic_type, moves in moved_results.items():
            print(f"  🏷️  {logic_type}: ย้าย {len(moves)} โฟลเดอร์")
            for src, dst in moves[:3]:  # แสดง 3 รายการแรก
                print(f"    📁 {os.path.basename(src)} → {os.path.basename(dst)}")
            if len(moves) > 3:
                print(f"    ... และอีก {len(moves) - 3} โฟลเดอร์")
    else:
        print("❌ ยกเลิกการย้าย")


def example_archive_with_logic_type():
    """ตัวอย่างการจัดเก็บไฟล์เก่าพร้อมจัดกลุ่มตาม logic type (ใช้เสมอเพื่อความปลอดภัย)"""
    print("\n🗂️  ตัวอย่างการจัดเก็บไฟล์เก่าแบบจัดกลุ่ม (ใช้ Logic Type เสมอ)")
    print("=" * 60)
    
    # สร้าง service
    file_mgmt = FileManagementService()
    
    # เลือกโฟลเดอร์
    source_folder = input("📂 ระบุโฟลเดอร์ต้นทาง (หรือกด Enter เพื่อใช้โฟลเดอร์ปัจจุบัน): ").strip()
    if not source_folder:
        source_folder = os.getcwd()
    
    if not os.path.exists(source_folder):
        print(f"❌ ไม่พบโฟลเดอร์: {source_folder}")
        return
    
    # เลือกโฟลเดอร์ archive
    archive_folder = input("📚 ระบุโฟลเดอร์ archive (หรือกด Enter เพื่อใช้ 'Archive'): ").strip()
    if not archive_folder:
        archive_folder = os.path.join(source_folder, "Archive")
    
    # เลือกจำนวนวัน
    try:
        days = int(input("📅 ระบุจำนวนวันสำหรับไฟล์เก่า (default: 30): ").strip() or "30")
    except ValueError:
        days = 30
    
    print(f"\n🗃️  กำลังจัดเก็บไฟล์เก่ากว่า {days} วัน")
    print(f"📂 จาก: {source_folder}")
    print(f"📚 ไปยัง: {archive_folder}")
    print("-" * 60)
    
    # ดำเนินการจัดเก็บ (ใช้ logic type เสมอเพื่อความปลอดภัย)
    result = file_mgmt.archive_old_files(
        source_path=source_folder,
        archive_path=archive_folder,
        days=days
    )
    
    # แสดงผลลัพธ์
    print("\n📊 ผลลัพธ์การจัดเก็บ:")
    print(f"  📄 ย้ายไฟล์: {len(result.get('moved_files', []))}")
    print(f"  📁 ย้ายโฟลเดอร์ว่าง: {len(result.get('moved_dirs', []))}")
    
    moved_by_type = result.get('moved_folders_by_type', {})
    if moved_by_type:
        print(f"  🏷️  ย้ายโฟลเดอร์ตาม logic type:")
        for logic_type, moves in moved_by_type.items():
            print(f"    {logic_type}: {len(moves)} โฟลเดอร์")
    
    deleted_files = result.get('deleted_files', [])
    if deleted_files:
        print(f"  🗑️  ลบไฟล์เก่าใน archive: {len(deleted_files)}")
    
    errors = result.get('errors', [])
    if errors:
        print(f"  ❌ ข้อผิดพลาด: {len(errors)}")
        for error in errors:
            print(f"    {error}")


def main():
    """ฟังก์ชันหลักสำหรับรันตัวอย่าง"""
    print("🚀 File Management Service - ตัวอย่างการใช้งานฟีเจอร์ใหม่")
    print("=" * 60)
    print("ฟีเจอร์ใหม่:")
    print("✅ ตรวจสอบโฟลเดอร์ที่มีไฟล์")
    print("✅ จัดกลุ่มตาม logic type เหมือน move_uploaded_files")
    print("✅ จัดระเบียบโฟลเดอร์อัตโนมัติ")
    print("=" * 60)
    
    while True:
        print("\n📋 เลือกตัวอย่างที่ต้องการทดสอบ:")
        print("1. 🔍 วิเคราะห์โครงสร้างโฟลเดอร์")
        print("2. 📦 จัดระเบียบโฟลเดอร์ตาม Logic Type")
        print("3. 🗂️  จัดเก็บไฟล์เก่าแบบจัดกลุ่ม")
        print("0. 🚪 ออกจากโปรแกรม")
        
        choice = input("\n🎯 เลือก (0-3): ").strip()
        
        try:
            if choice == "1":
                example_folder_analysis()
            elif choice == "2":
                example_organize_folders()
            elif choice == "3":
                example_archive_with_logic_type()
            elif choice == "0":
                print("👋 ขอบคุณที่ใช้งาน!")
                break
            else:
                print("❌ กรุณาเลือกตัวเลข 0-3")
                
        except KeyboardInterrupt:
            print("\n\n👋 ขอบคุณที่ใช้งาน!")
            break
        except Exception as e:
            print(f"\n❌ เกิดข้อผิดพลาด: {e}")


if __name__ == "__main__":
    main()