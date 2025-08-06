import os
import sys
import time
import logging
import json
from services.file_service import FileService
from services.database_service import DatabaseService
import pandas as pd

# ทำให้ working directory เป็น root ของโปรเจกต์เสมอ
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_last_path():
    try:
        with open('config/last_path.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('last_path', None)
    except Exception:
        return None

def process_file(file_path, file_service, db_service):
    """
    Processes a single file: reads, transforms, uploads, and moves it (เหมือน GUI)
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


def main_cli():
    """
    Main function for the CLI application. Runs once and processes all found files.
    """
    logging.info("Starting CLI application for file processing.")

    last_path = load_last_path()
    if last_path and os.path.isdir(last_path):
        file_service = FileService(search_path=last_path)
    else:
        file_service = FileService()
    db_service = DatabaseService()

    # Check DB connection first
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
        
        logging.info("CLI application has finished processing all files.")

    except Exception as e:
        logging.error(f"An error occurred during file processing: {e}", exc_info=True)


if __name__ == '__main__':
    main_cli()
