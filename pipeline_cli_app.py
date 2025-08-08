"""
CLI Application สำหรับ PIPELINE_SQLSERVER

แอปพลิเคชัน command line สำหรับประมวลผลไฟล์แบบ batch
"""

import argparse
import logging
import os
from typing import Optional

from config.settings import settings_manager
from constants import AppConstants, PathConstants
from services.database_service import DatabaseService
from services.file_management_service import FileManagementService
from services.file_service import FileService

# ทำให้ working directory เป็น root ของโปรเจกต์เสมอ
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Setup logging
logging.basicConfig(
    level=logging.INFO, 
    format=AppConstants.LOG_FORMAT
)

def load_last_path() -> Optional[str]:
    """
    โหลด search path ล่าสุดจากไฟล์ last_path.json (เหมือนกับ GUI)
    
    Returns:
        Optional[str]: search path หรือ None ถ้าไม่มี
    """
    try:
        import json
        with open('config/last_path.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('last_path', None)
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return None

def process_file(file_path: str, file_service: FileService, db_service: DatabaseService) -> None:
    """
    ประมวลผลไฟล์เดียว: อ่าน แปลง อัปโหลด และย้าย (เหมือน GUI)
    
    Args:
        file_path: ที่อยู่ไฟล์ที่ต้องการประมวลผล
        file_service: บริการจัดการไฟล์
        db_service: บริการฐานข้อมูล
    """
    try:
        logging.info(f"Processing file: {file_path}")
        # 1. พยายามตรวจ logic_type จาก header ก่อน (เหมือน GUI)
        logic_type = file_service.detect_file_type(file_path)
        # 2. ถ้าไม่ได้ ให้ fallback เดาจากชื่อไฟล์
        if not logic_type:
            filename = os.path.basename(file_path)
            if hasattr(file_service, 'column_settings'):
                for key in file_service.column_settings.keys():
                    if key.lower() in filename.lower():
                        logic_type = key
                        break
        if not logic_type:
            logging.warning(f"ไม่สามารถระบุประเภทไฟล์ (logic_type) สำหรับ {os.path.basename(file_path)} ได้ ข้ามไฟล์นี้")
            return
        logging.info(f"Determined file type as: {logic_type}")
        # 3. อ่านไฟล์ (เหมือน GUI)
        success, df_or_msg = file_service.read_excel_file(file_path, logic_type)
        if not success:
            logging.error(f"{df_or_msg}")
            return
        df = df_or_msg
        # 4. ตรวจสอบคอลัมน์ (เหมือน GUI)
        success, result = file_service.validate_columns(df, logic_type)
        if not success:
            logging.error(f"{result}")
            return
        required_cols = file_service.get_required_dtypes(logic_type)
        # 5. อัปโหลดข้อมูล
        success, message = db_service.upload_data(df, logic_type, required_cols)
        if success:
            logging.info(f"Successfully uploaded data from {file_path} to table for logic type {logic_type}.")
            # Move file after upload (เหมือน GUI)
            move_success, move_result = file_service.move_uploaded_files([file_path], [logic_type])
            if move_success:
                for original_path, new_path in move_result:
                    logging.info(f"Moved file: {original_path} -> {new_path}")
            else:
                logging.error(f"❌ ไม่สามารถย้ายไฟล์: {move_result}")
        else:
            logging.error(f"Failed to upload data for {file_path}. Reason: {message}")
    except Exception as e:
        logging.error(f"An unexpected error occurred while processing {file_path}: {e}", exc_info=True)


def validate_source_path() -> Optional[str]:
    """
    ตรวจสอบและโหลด path ต้นทางจาก last_path.json
    
    Returns:
        Optional[str]: path ที่ถูกต้อง หรือ None
    """
    path = load_last_path()
    if not path:
        logging.error("❌ ไม่พบ source path ใน config/last_path.json")
        logging.info("💡 กรุณาเปิด GUI ก่อนเพื่อตั้งค่า source path หรือใช้ --source ระบุ path")
        return None
    
    if not os.path.isdir(path):
        logging.error(f"❌ Source path ไม่ถูกต้อง: {path}")
        return None
    
    logging.info(f"✅ ใช้ source path: {path}")
    return path


def upload_files_auto_cli(args):
    """
    ฟังก์ชันสำหรับการอัปโหลดไฟล์อัตโนมัติผ่าน CLI
    
    Args:
        args (argparse.Namespace): arguments จาก command line  
    """
    logging.info("Starting CLI auto upload process.")
    
    source_path = args.source
    if not source_path or not os.path.isdir(source_path):
        logging.error(f"Invalid source path: {source_path}")
        return
    
    logging.info(f"Source path: {source_path}")


def process_main_files_step(source_path: str) -> None:
    """
    ประมวลผลไฟล์หลักอัตโนมัติ
    
    Args:
        source_path (str): โฟลเดอร์ต้นทางที่จะค้นหาไฟล์
    """
    logging.info("=== กำลังประมวลผลไฟล์ ===")
    
    try:
        # ใช้ logging.info เป็น log_callback สำหรับ CLI (เหมือน GUI)
        file_service = FileService(search_path=source_path, log_callback=logging.info)
        db_service = DatabaseService()

        # ค้นหาไฟล์ข้อมูล
        data_files = file_service.find_data_files()
        
        if not data_files:
            logging.info("ไม่พบไฟล์ข้อมูลในโฟลเดอร์ต้นทาง")
            return
        
        logging.info(f"พบไฟล์ข้อมูล {len(data_files)} ไฟล์ กำลังประมวลผล...")
        
        total_files = len(data_files)
        processed_files = 0
        successful_uploads = 0
        
        for file_path in data_files:
            try:
                processed_files += 1
                
                logging.info(f"📁 กำลังประมวลผล: {os.path.basename(file_path)} ({processed_files}/{total_files})")
                
                # ตรวจหา logic_type (เหมือน GUI)
                logic_type = file_service.detect_file_type(file_path)
                if not logic_type:
                    # ลองเดาจากชื่อไฟล์ (เหมือน GUI)
                    filename = os.path.basename(file_path).lower()
                    for key in file_service.column_settings.keys():
                        if key.lower() in filename:
                            logic_type = key
                            break
                
                if not logic_type:
                    logging.info(f"❌ ไม่สามารถระบุประเภทไฟล์: {os.path.basename(file_path)}")
                    continue
                
                logging.info(f"📋 ระบุประเภทไฟล์: {logic_type}")
                
                # อ่านไฟล์พร้อมระบบแก้ไขอัตโนมัติ
                success, result = file_service.read_excel_file(file_path, logic_type, use_auto_fix=True)
                if not success:
                    logging.info(f"❌ ไม่สามารถอ่านไฟล์: {result}")
                    continue
                
                df = result
                
                # ตรวจสอบคอลัมน์ (เหมือน GUI)
                success, result = file_service.validate_columns(df, logic_type)
                if not success:
                    logging.info(f"❌ คอลัมน์ไม่ถูกต้อง: {result}")
                    continue
                
                # อัปโหลดข้อมูลพร้อม auto schema update
                required_cols = file_service.get_required_dtypes(logic_type)
                
                # ตรวจสอบว่า required_cols ไม่ว่างเปล่า
                if not required_cols:
                    logging.info(f"❌ ไม่พบการตั้งค่าประเภทข้อมูลสำหรับ {logic_type}")
                    continue
                
                # ตรวจสอบว่าข้อมูลไม่ว่างเปล่า
                if df.empty:
                    logging.info(f"❌ ไฟล์ {os.path.basename(file_path)} ไม่มีข้อมูล")
                    continue
                
                logging.info(f"📊 กำลังอัปโหลดข้อมูล {len(df)} แถว สำหรับประเภท {logic_type}")
                
                # ใช้ระบบ auto schema update
                processing_report = {'auto_fixes_applied': True}  # สมมติว่าใช้ auto-fix
                success, message = file_service.upload_data_with_auto_schema_update(
                    df, logic_type, processing_report
                )
                
                if success:
                    logging.info(f"✅ อัปโหลดสำเร็จ: {message}")
                    successful_uploads += 1
                    
                    # ย้ายไฟล์หลังอัปโหลดสำเร็จ (เหมือน GUI)
                    try:
                        move_success, move_result = file_service.move_uploaded_files([file_path], [logic_type])
                        if move_success:
                            for original_path, new_path in move_result:
                                logging.info(f"📦 ย้ายไฟล์ไปยัง: {os.path.basename(new_path)}")
                        else:
                            logging.info(f"❌ ไม่สามารถย้ายไฟล์: {move_result}")
                    except Exception as e:
                        logging.info(f"❌ ข้อผิดพลาดในการย้ายไฟล์: {e}")
                else:
                    logging.info(f"❌ อัปโหลดล้มเหลว: {message}")
                    
            except Exception as e:
                logging.error(f"❌ ข้อผิดพลาดในการประมวลผล {os.path.basename(file_path)}: {e}")
                continue
        
        # สรุปผล
        logging.info(f"🏁 สรุป: ประมวลผล {total_files} ไฟล์ สำเร็จ {successful_uploads} ไฟล์")
        
    except Exception as e:
        logging.error(f"❌ เกิดข้อผิดพลาดในการประมวลผลไฟล์หลัก: {e}")


def auto_upload_cli(args) -> None:
    """
    ฟังก์ชันหลักสำหรับการประมวลผลอัตโนมัติผ่าน CLI (เหมือน GUI auto process)
    
    Args:
        args: arguments จาก argparse
    """
    logging.info("🤖 เริ่มการประมวลผลอัตโนมัติผ่าน CLI")
    
    # กำหนด source path
    source_path = args.source if args.source else validate_source_path()
    
    if not source_path:
        return
    
    # ตรวจสอบการเชื่อมต่อฐานข้อมูล
    db_service = DatabaseService()
    success, message = db_service.check_connection()
    if not success:
        logging.error(f"❌ ไม่สามารถเชื่อมต่อฐานข้อมูล: {message}")
        return
    
    logging.info("✅ เชื่อมต่อฐานข้อมูลสำเร็จ")
    
    # ตรวจสอบสิทธิ์ฐานข้อมูล
    logging.info("🔐 ตรวจสอบสิทธิ์ฐานข้อมูล...")
    permission_results = db_service.check_permissions('bronze', logging.info)
    
    if not permission_results.get('success', False):
        logging.error("❌ ไม่สามารถดำเนินการได้เนื่องจากสิทธิ์ไม่เพียงพอ")
        logging.info("📋 รายงานสิทธิ์:")
        report = db_service.generate_permission_report('bronze')
        for line in report.split('\n'):
            if line.strip():
                logging.info(line)
        return
    
    logging.info("✅ สิทธิ์ฐานข้อมูลถูกต้อง")
    
    try:
        # ขั้นตอนหลัก: ประมวลผลไฟล์
        process_main_files_step(source_path)
        
        logging.info("🎉 การประมวลผลอัตโนมัติเสร็จสิ้นแล้ว")
        
    except Exception as e:
        logging.error(f"❌ เกิดข้อผิดพลาดในการประมวลผลอัตโนมัติ: {e}")


def main():
    """
    Main function สำหรับ CLI
    """
    parser = argparse.ArgumentParser(description='PIPELINE_SQLSERVER CLI - ระบบประมวลผลไฟล์ Excel/CSV สู่ SQL Server')
    
    # Main command
    subparsers = parser.add_subparsers(dest='command', help='คำสั่งที่ใช้ได้')
    
    # Auto upload command
    auto_parser = subparsers.add_parser(
        'auto', 
        help='ประมวลผลไฟล์อัตโนมัติ (เหมือน GUI auto process)'
    )
    auto_parser.add_argument(
        '--source', '-s',
        type=str, 
        help='โฟลเดอร์ต้นทาง (ถ้าไม่ระบุจะใช้จาก last_path.json)'
    )
    
    args = parser.parse_args()
    
    if args.command == 'auto':
        auto_upload_cli(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()