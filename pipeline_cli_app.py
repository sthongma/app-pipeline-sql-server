"""
CLI Application สำหรับ PIPELINE_SQLSERVER

แอปพลิเคชัน command line สำหรับประมวลผลไฟล์แบบ batch
"""

"""CLI Application สำหรับ PIPELINE_SQLSERVER"""

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


def archive_old_files_cli(args) -> None:
    """
    ฟังก์ชันสำหรับการย้ายไฟล์เก่าไปเก็บ archive
    
    Args:
        args: arguments จาก argparse
    """
    logging.info("Starting file archiving process.")
    
    file_mgmt_service = FileManagementService()
    
    # ใช้ path จาก args หรือ default path
    source_path = args.src or os.path.join(os.getcwd(), 'Uploaded_Files')
    archive_path = args.dest or os.path.join('D:\\', 'Archived_Files')
    
    if not os.path.exists(source_path):
        logging.error(f"Source path does not exist: {source_path}")
        return
    
    logging.info(f"Archiving files older than {args.days} days from {source_path} to {archive_path}")
    
    try:
        result = file_mgmt_service.archive_old_files(
            source_path=source_path,
            archive_path=archive_path,
            days=args.days,
            delete_archive_days=args.delete_days
        )
        
        # แสดงผลลัพธ์
        if result["moved_files"]:
            logging.info(f"Moved {len(result['moved_files'])} files to archive")
            for src, dst in result["moved_files"]:
                logging.info(f"  {src} -> {dst}")
        
        if result["moved_dirs"]:
            logging.info(f"Moved {len(result['moved_dirs'])} empty directories to archive")
            for src, dst in result["moved_dirs"]:
                logging.info(f"  {src} -> {dst}")
        
        if result["deleted_files"]:
            logging.info(f"Deleted {len(result['deleted_files'])} old files from archive")
            for file_path in result["deleted_files"]:
                logging.info(f"  Deleted: {file_path}")
        
        if result["errors"]:
            for error in result["errors"]:
                logging.error(f"Error during archiving: {error}")
        
        logging.info("File archiving process completed.")
        
    except Exception as e:
        logging.error(f"An error occurred during file archiving: {e}", exc_info=True)


def merge_zip_excel_cli(args) -> None:
    """
    ฟังก์ชันสำหรับการรวมไฟล์ Excel จาก ZIP files
    
    Args:
        args: arguments จาก argparse
    """
    logging.info("Starting ZIP Excel merger process.")
    
    file_mgmt_service = FileManagementService()
    
    if not os.path.exists(args.folder):
        logging.error(f"Folder does not exist: {args.folder}")
        return
    
    def progress_callback(value, status):
        """Callback สำหรับแสดงความคืบหน้า"""
        logging.info(f"Progress: {value*100:.1f}% - {status}")
    
    try:
        result = file_mgmt_service.process_zip_excel_merger(
            folder_path=args.folder,
            progress_callback=progress_callback
        )
        
        if result["success"]:
            logging.info("ZIP Excel merger completed successfully!")
            
            if result["saved_files"]:
                logging.info(f"Saved {len(result['saved_files'])} merged files:")
                for filename, rows in result["saved_files"]:
                    logging.info(f"  {filename}: {rows} rows")
            
            if result["organized_folder"] and result["moved_files"]:
                logging.info(f"Moved {len(result['moved_files'])} ZIP files to: {result['organized_folder']}")
        else:
            logging.error("ZIP Excel merger failed.")
            
        if result["errors"]:
            for error in result["errors"]:
                logging.error(f"Error during ZIP Excel merger: {error}")
        
    except Exception as e:
        logging.error(f"An error occurred during ZIP Excel merger: {e}", exc_info=True)


def validate_source_path() -> Optional[str]:
    """
    ตรวจสอบและโหลด path ต้นทางจาก last_path.json
    
    Returns:
        Optional[str]: path ต้นทางหากถูกต้อง, None หากไม่ถูกต้อง
    """
    last_path = load_last_path()
    if not last_path or not os.path.isdir(last_path):
        logging.error(f"โฟลเดอร์ต้นทางไม่ถูกต้องใน last_path.json: {last_path}")
        logging.error("กรุณาตั้งค่าโฟลเดอร์ต้นทางใน config/last_path.json")
        return None
    
    logging.info(f"ใช้โฟลเดอร์ต้นทางจาก last_path.json: {last_path}")
    return last_path


def process_zip_files_step(source_path: str) -> None:
    """
    ขั้นตอนที่ 1: รวมไฟล์ Excel จากไฟล์ ZIP
    
    Args:
        source_path (str): โฟลเดอร์ต้นทางที่จะค้นหาไฟล์ ZIP
    """
    logging.info("=== ขั้นตอนที่ 1: รวมไฟล์ ZIP ===")
    try:
        file_mgmt_service = FileManagementService()
        
        # ค้นหาไฟล์ ZIP ในโฟลเดอร์ต้นทาง (รวมถึง subfolder)
        zip_files = []
        for root, dirs, files in os.walk(source_path):
            for file in files:
                if file.lower().endswith('.zip'):
                    zip_files.append(os.path.join(root, file))
        
        if zip_files:
            logging.info(f"พบไฟล์ ZIP {len(zip_files)} ไฟล์ จะทำการรวมไฟล์ Excel")
            
            def progress_callback(value: float, status: str) -> None:
                logging.info(f"ความคืบหน้า: {value*100:.1f}% - {status}")
            
            result = file_mgmt_service.process_zip_excel_merger(
                folder_path=source_path,
                progress_callback=progress_callback
            )
            
            if result["success"]:
                logging.info("✅ รวมไฟล์ Excel จาก ZIP เสร็จสิ้น")
                if result["saved_files"]:
                    for filename, rows in result["saved_files"]:
                        logging.info(f"  บันทึก: {filename} ({rows} แถว)")
            else:
                logging.warning("⚠️ การรวมไฟล์ ZIP ไม่สำเร็จ แต่จะดำเนินการต่อ")
                
            if result["errors"]:
                for error in result["errors"]:
                    logging.warning(f"ข้อผิดพลาดใน ZIP merger: {error}")
        else:
            logging.info("ไม่พบไฟล์ ZIP ในโฟลเดอร์ต้นทาง ข้ามขั้นตอนนี้")
            
    except Exception as e:
        logging.error(f"เกิดข้อผิดพลาดในการรวมไฟล์ ZIP: {e}")
        logging.info("จะดำเนินการต่อด้วยการประมวลผลไฟล์หลัก")


def process_main_files_step(source_path: str) -> None:
    """
    ขั้นตอนที่ 2: ประมวลผลไฟล์หลัก (Excel/CSV)
    
    Args:
        source_path (str): โฟลเดอร์ต้นทางที่จะค้นหาไฟล์
    """
    logging.info("=== ขั้นตอนที่ 2: ประมวลผลไฟล์หลัก ===")
    
    # ใช้ logging.info เป็น log_callback สำหรับ CLI
    file_service = FileService(search_path=source_path, log_callback=logging.info)
    db_service = DatabaseService()

    # ตรวจสอบการเชื่อมต่อฐานข้อมูลก่อน
    is_connected, message = db_service.check_connection()
    if not is_connected:
        logging.error(f"Database connection failed: {message}. Exiting.")
        return

    logging.info(f"Database connection successful. Searching for files in: {file_service.search_path}")

    try:
        data_files = file_service.find_data_files()

        if not data_files:
            logging.info("No data files found in the specified path.")
        else:
            logging.info(f"Found {len(data_files)} files to process.")
            for file_path in data_files:
                process_file(file_path, file_service, db_service)
        
        logging.info("✅ การประมวลผลไฟล์หลักเสร็จสิ้น")

    except Exception as e:
        logging.error(f"An error occurred during file processing: {e}", exc_info=True)


def archive_old_files_step(source_path: str) -> None:
    """
    ขั้นตอนที่ 3: ย้ายไฟล์เก่าไปเก็บ archive
    
    Args:
        source_path (str): โฟลเดอร์ต้นทางที่จะค้นหาไฟล์เก่า
    """
    logging.info("=== ขั้นตอนที่ 3: ย้ายไฟล์เก่าไปถังขยะ ===")
    
    try:
        file_mgmt_service = FileManagementService()
        
        # กำหนดโฟลเดอร์ปลายทางในไดร์ D
        archive_path = PathConstants.DEFAULT_ARCHIVE_PATH
        
        logging.info(f"กำลังย้ายไฟล์เก่ามากว่า {AppConstants.DEFAULT_ARCHIVE_DAYS} วันจาก {source_path} ไปยัง {archive_path}")
        
        result = file_mgmt_service.archive_old_files(
            source_path=source_path,
            archive_path=archive_path,
            days=AppConstants.DEFAULT_ARCHIVE_DAYS,
            delete_archive_days=AppConstants.DEFAULT_DELETE_ARCHIVE_DAYS
        )
        
        # แสดงผลลัพธ์
        if result["moved_files"]:
            logging.info(f"✅ ย้ายไฟล์ {len(result['moved_files'])} ไฟล์ไปยัง archive")
            
        if result["moved_dirs"]:
            logging.info(f"✅ ย้ายโฟลเดอร์ว่าง {len(result['moved_dirs'])} โฟลเดอร์ไปยัง archive")
            
        if result["deleted_files"]:
            logging.info(f"🗑️ ย้ายไฟล์เก่า {len(result['deleted_files'])} ไฟล์ไปถังขยะ")
            
        if result["errors"]:
            for error in result["errors"]:
                logging.warning(f"ข้อผิดพลาดในการจัดการไฟล์: {error}")
        
        logging.info("✅ การย้ายไฟล์เก่าเสร็จสิ้น")
        
    except Exception as e:
        logging.error(f"เกิดข้อผิดพลาดในการย้ายไฟล์เก่า: {e}", exc_info=True)


def main_cli() -> None:
    """
    ฟังก์ชันหลักสำหรับ CLI application
    
    รันตามลำดับ:
    1. รวมไฟล์ ZIP ก่อน
    2. รันส่วนของโปรแกรมหลัก
    3. ย้ายไฟล์เก่ามากว่า {AppConstants.DEFAULT_ARCHIVE_DAYS} วันไปถังขยะ
    """
    logging.info("Starting CLI application for file processing.")

    # ตรวจสอบและโหลด path ต้นทาง
    source_path = validate_source_path()
    if not source_path:
        return

    # ดำเนินการตามลำดับขั้นตอน
    process_zip_files_step(source_path)
    process_main_files_step(source_path)
    archive_old_files_step(source_path)
    
    logging.info("=== 🏁 การดำเนินการทั้งหมดเสร็จสิ้น ===")


def main():
    """ฟังก์ชันหลักที่จัดการ command line arguments"""
    parser = argparse.ArgumentParser(
        description='PIPELINE_SQLSERVER CLI - แอปพลิเคชัน command line สำหรับประมวลผลไฟล์',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
ตัวอย่างการใช้งาน:

  # ประมวลผลไฟล์ปกติ (default)
  python pipeline_cli_app.py

  # ย้ายไฟล์เก่าไปเก็บ archive
  python pipeline_cli_app.py archive --days 30 --src ./Uploaded_Files --dest D:/Archived_Files

  # รวมไฟล์ Excel จาก ZIP files
  python pipeline_cli_app.py merge-zip --folder ./path/to/zip/folder
        """
    )
    
    # สร้าง subcommands
    subparsers = parser.add_subparsers(dest='command', help='คำสั่งที่ต้องการใช้')
    
    # Subcommand สำหรับ archive files
    archive_parser = subparsers.add_parser(
        'archive', 
        help='ย้ายไฟล์เก่าไปเก็บ archive และลบไฟล์เก่าใน archive'
    )
    archive_parser.add_argument(
        '--days', 
        type=int, 
        default=30, 
        help='จำนวนวันสำหรับไฟล์ที่จะย้าย (default: 30)'
    )
    archive_parser.add_argument(
        '--src', 
        type=str, 
        help='โฟลเดอร์ต้นทาง (default: ./Uploaded_Files)'
    )
    archive_parser.add_argument(
        '--dest', 
        type=str, 
        help='โฟลเดอร์ปลายทาง (default: D:/Archived_Files)'
    )
    archive_parser.add_argument(
        '--delete-days', 
        type=int, 
        default=AppConstants.DEFAULT_DELETE_ARCHIVE_DAYS, 
        help=f'จำนวนวันสำหรับการลบไฟล์ใน archive (default: {AppConstants.DEFAULT_DELETE_ARCHIVE_DAYS})'
    )
    
    # Subcommand สำหรับ ZIP Excel merger
    merge_parser = subparsers.add_parser(
        'merge-zip', 
        help='รวมไฟล์ Excel จาก ZIP files'
    )
    merge_parser.add_argument(
        '--folder', 
        type=str, 
        required=True, 
        help='โฟลเดอร์ที่มีไฟล์ ZIP (จำเป็นต้องระบุ)'
    )
    
    args = parser.parse_args()
    
    # เรียกใช้ฟังก์ชันตาม command ที่เลือก
    if args.command == 'archive':
        archive_old_files_cli(args)
    elif args.command == 'merge-zip':
        merge_zip_excel_cli(args)
    else:
        # ถ้าไม่มี command หรือ command ไม่ถูกต้อง ให้รันแบบปกติ
        main_cli()


if __name__ == '__main__':
    main()
