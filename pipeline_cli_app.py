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
    ขั้นตอนที่ 1: รวมไฟล์ ZIP อัตโนมัติ (เหมือน _auto_process_zip_merger ใน GUI)
    
    Args:
        source_path (str): โฟลเดอร์ต้นทางที่จะค้นหาไฟล์ ZIP
    """
    logging.info("=== ขั้นตอนที่ 1: รวมไฟล์ ZIP ===")
    try:
        file_mgmt_service = FileManagementService()
        
        # ค้นหาไฟล์ ZIP ในโฟลเดอร์ (รวม subfolder) เหมือน GUI
        zip_files = []
        for root, dirs, files in os.walk(source_path):
            for file in files:
                if file.lower().endswith('.zip'):
                    zip_files.append(os.path.join(root, file))
        
        if not zip_files:
            logging.info("ไม่พบไฟล์ ZIP ในโฟลเดอร์ต้นทาง ข้ามขั้นตอนนี้")
            return
        
        logging.info(f"พบไฟล์ ZIP {len(zip_files)} ไฟล์ กำลังรวมไฟล์ Excel...")
        
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
            logging.info("⚠️ การรวมไฟล์ ZIP ไม่สำเร็จ แต่จะดำเนินการต่อ")
            
        if result["errors"]:
            for error in result["errors"]:
                logging.info(f"⚠️ ข้อผิดพลาดใน ZIP merger: {error}")
                
    except Exception as e:
        logging.error(f"❌ เกิดข้อผิดพลาดในการรวมไฟล์ ZIP: {e}")
        logging.info("จะดำเนินการต่อด้วยการประมวลผลไฟล์หลัก")


def process_main_files_step(source_path: str) -> None:
    """
    ขั้นตอนที่ 2: ประมวลผลไฟล์หลักอัตโนมัติ (เหมือน _auto_process_main_files ใน GUI)
    
    Args:
        source_path (str): โฟลเดอร์ต้นทางที่จะค้นหาไฟล์
    """
    logging.info("=== ขั้นตอนที่ 2: ประมวลผลไฟล์หลัก ===")
    
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
                
                # อ่านไฟล์ (เหมือน GUI)
                success, result = file_service.read_excel_file(file_path, logic_type)
                if not success:
                    logging.info(f"❌ ไม่สามารถอ่านไฟล์: {result}")
                    continue
                
                df = result
                
                # ตรวจสอบคอลัมน์ (เหมือน GUI)
                success, result = file_service.validate_columns(df, logic_type)
                if not success:
                    logging.info(f"❌ คอลัมน์ไม่ถูกต้อง: {result}")
                    continue
                
                # อัปโหลดข้อมูล (เหมือน GUI)
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
                success, message = db_service.upload_data(df, logic_type, required_cols, log_func=logging.info)
                
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
                    except Exception as move_error:
                        logging.info(f"❌ เกิดข้อผิดพลาดในการย้ายไฟล์: {move_error}")
                else:
                    logging.info(f"❌ อัปโหลดไม่สำเร็จ: {message}")
                    # ลองตรวจสอบ error เพิ่มเติม (เหมือน GUI)
                    logging.info(f"🔍 ตรวจสอบข้อมูล: แถว {len(df)}, คอลัมน์ {list(df.columns)}")
                    
            except Exception as e:
                logging.info(f"❌ เกิดข้อผิดพลาดขณะประมวลผล {os.path.basename(file_path)}: {e}")
        
        logging.info(f"✅ ประมวลผลไฟล์เสร็จสิ้น: {successful_uploads}/{total_files} ไฟล์สำเร็จ")
        
    except Exception as e:
        logging.error(f"❌ เกิดข้อผิดพลาดในการประมวลผลไฟล์: {e}", exc_info=True)





def main_cli() -> None:
    """
    ฟังก์ชันหลักสำหรับ CLI application - ประมวลผลอัตโนมัติเหมือน GUI
    
    รันตามลำดับขั้นตอน:
    1. รวมไฟล์ Excel จากไฟล์ ZIP
    2. ประมวลผลและอัปโหลดไฟล์ทั้งหมด
    """
    logging.info("🤖 เริ่มการประมวลผลอัตโนมัติ")

    # ตรวจสอบและโหลด path ต้นทาง
    source_path = validate_source_path()
    if not source_path:
        return
    
    logging.info(f"📂 โฟลเดอร์ต้นทาง: {source_path}")
    
    # ตรวจสอบการเชื่อมต่อฐานข้อมูลก่อน (เหมือน GUI)
    db_service = DatabaseService()
    is_connected, message = db_service.check_connection()
    if not is_connected:
        logging.error(f"ไม่สามารถเชื่อมต่อกับฐานข้อมูลได้: {message}")
        logging.error("กรุณาตรวจสอบการตั้งค่าฐานข้อมูลก่อน")
        return

    try:
        # ดำเนินการตามลำดับขั้นตอน
        process_zip_files_step(source_path)
        process_main_files_step(source_path)
        
        logging.info("=== 🏁 การประมวลผลอัตโนมัติเสร็จสิ้น ===")
        
    except Exception as e:
        logging.error(f"❌ เกิดข้อผิดพลาดในการประมวลผลอัตโนมัติ: {e}", exc_info=True)


def main():
    """ฟังก์ชันหลักที่จัดการ command line arguments"""
    parser = argparse.ArgumentParser(
        description='PIPELINE_SQLSERVER CLI - แอปพลิเคชัน command line สำหรับประมวลผลไฟล์',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
ตัวอย่างการใช้งาน:

  # ประมวลผลไฟล์ปกติ (default)
  python pipeline_cli_app.py

  # รวมไฟล์ Excel จาก ZIP files
  python pipeline_cli_app.py merge-zip --folder ./path/to/zip/folder
        """
    )
    
    # สร้าง subcommands
    subparsers = parser.add_subparsers(dest='command', help='คำสั่งที่ต้องการใช้')
    

    
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
    if args.command == 'merge-zip':
        merge_zip_excel_cli(args)
    else:
        # ถ้าไม่มี command หรือ command ไม่ถูกต้อง ให้รันแบบปกติ
        main_cli()


if __name__ == '__main__':
    main()
