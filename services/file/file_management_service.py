"""
File Management Service for PIPELINE_SQLSERVER

Responsible for file management:
- Moving processed files
- Organizing folders
- Managing settings
"""

import os
import json
import shutil
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import logging

from config.json_manager import load_file_management_settings, save_file_management_settings


class FileManagementService:
    """
    File management service
    
    Responsibilities:
    - Moving processed files
    - Organizing folders
    - Managing settings
    """
    
    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize File Management Service

        Args:
            base_path: Base path for operations (default: current directory)
        """
        self.base_path = base_path or os.getcwd()
        self.settings_file = os.path.join(self.base_path, 'config', 'file_management_settings.json')
        self.output_folder = None  # Custom output folder for uploaded files
        self._ensure_config_dir()

    def set_output_folder(self, folder_path: str):
        """Set custom output folder for uploaded files"""
        if folder_path and os.path.exists(folder_path):
            self.output_folder = folder_path
            # Log message is handled by main_window._on_output_folder_changed()
    
    def _ensure_config_dir(self):
        """Create config folder if it doesn't exist"""
        config_dir = os.path.dirname(self.settings_file)
        os.makedirs(config_dir, exist_ok=True)
    
    # ========================
    # File Movement Functions
    # ========================
    
    def move_uploaded_files(self, file_paths, logic_types=None, search_path=None):
        """Move uploaded files to date-organized folders with original filenames"""
        try:
            # Use custom output folder if set, otherwise use search_path
            base_folder = self.output_folder if self.output_folder else (search_path or self.base_path)

            # สร้างโฟลเดอร์ย่อยตามวันที่ (YYYY-MM-DD)
            current_date = datetime.now().strftime("%Y-%m-%d")
            date_folder = os.path.join(base_folder, current_date)
            os.makedirs(date_folder, exist_ok=True)

            moved_files = []

            # ใช้ ThreadPoolExecutor สำหรับการย้ายไฟล์หลายไฟล์
            def move_single_file(args):
                idx, file_path = args
                try:
                    # ใช้ชื่อไฟล์เดิม (ไม่เปลี่ยนชื่อ)
                    file_name = os.path.basename(file_path)
                    destination = os.path.join(date_folder, file_name)

                    # ถ้าไฟล์มีชื่อซ้ำ ให้เพิ่ม timestamp ท้ายชื่อไฟล์
                    if os.path.exists(destination):
                        name, ext = os.path.splitext(file_name)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        new_name = f"{name}_{timestamp}{ext}"
                        destination = os.path.join(date_folder, new_name)

                    shutil.move(file_path, destination)
                    return (file_path, destination)
                except Exception as e:
                    logging.error(f"ไม่สามารถย้ายไฟล์ {file_path}: {str(e)}")
                    return None

            # ถ้ามีไฟล์น้อยกว่า 5 ไฟล์ ทำทีละไฟล์
            if len(file_paths) < 5:
                for idx, file_path in enumerate(file_paths):
                    result = move_single_file((idx, file_path))
                    if result:
                        moved_files.append(result)
            else:
                # ใช้ ThreadPoolExecutor สำหรับไฟล์เยอะ
                with ThreadPoolExecutor(max_workers=3) as executor:
                    results = executor.map(move_single_file, enumerate(file_paths))
                    moved_files = [r for r in results if r is not None]

            return True, moved_files

        except Exception as e:
            return False, str(e)
    
    def create_organized_folder_structure(self, base_folder: str, file_type: str) -> str:
        """Create folder structure in format file_type/year-month-day"""
        current_date = datetime.now()
        date_folder = current_date.strftime('%Y-%m-%d')
        organized_path = os.path.join(base_folder, "Processed_Files", file_type, date_folder)
        os.makedirs(organized_path, exist_ok=True)
        return organized_path
    
    # ========================
    # Helper Functions
    # ========================
    
    def get_supported_file_extensions(self) -> List[str]:
        """List of supported file extensions"""
        return ['.xlsx', '.xls', '.csv']
    
    def is_supported_file(self, file_path: str) -> bool:
        """Check if file is supported"""
        file_ext = os.path.splitext(file_path)[1].lower()
        return file_ext in self.get_supported_file_extensions()
    
    def get_file_type_info(self, file_path: str) -> Dict[str, str]:
        """Get file type information"""
        file_ext = os.path.splitext(file_path)[1].lower()
        file_types = {
            '.xlsx': {'type': 'Excel (New)', 'engine': 'openpyxl'},
            '.xls': {'type': 'Excel (Legacy)', 'engine': 'xlrd'},
            '.csv': {'type': 'CSV', 'engine': 'pandas'}
        }
        return file_types.get(file_ext, {'type': 'Unknown', 'engine': 'none'})
    
    def get_file_type_from_filename(self, filename: str) -> str:
        """Extract file type name from filename"""
        name_without_ext = os.path.splitext(filename)[0]
        file_type = ''.join([c for c in name_without_ext if c.isalpha() or c == '_'])
        return file_type if file_type else "Unknown"
    
    def group_files_by_type(self, file_paths: List[str]) -> Dict[str, List[str]]:
        """Group files by type"""
        grouped = {ext: [] for ext in self.get_supported_file_extensions()}
        grouped['unsupported'] = []
        
        for file_path in file_paths:
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext in grouped:
                grouped[file_ext].append(file_path)
            else:
                grouped['unsupported'].append(file_path)
        
        # ลบกลุ่มที่ว่าง
        return {k: v for k, v in grouped.items() if v}
    
    # ========================
    # Settings Management
    # ========================
    
    def load_settings(self) -> Dict[str, Any]:
        """Load settings from JSON file using JSON Manager"""
        try:
            return load_file_management_settings()
        except Exception as e:
            logging.error(f"เกิดข้อผิดพลาดในการโหลดการตั้งค่า: {e}")
            return {}
    
    def save_settings(self, settings: Dict[str, Any]) -> bool:
        """Save settings to JSON file using JSON Manager"""
        try:
            return save_file_management_settings(settings)
        except Exception as e:
            logging.error(f"เกิดข้อผิดพลาดในการบันทึกการตั้งค่า: {e}")
            return False
    
    def cleanup_temp_files(self, temp_directories: List[str]) -> None:
        """Delete unused temporary folders"""
        for temp_dir in temp_directories:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                logging.error(f"ไม่สามารถลบโฟลเดอร์ temp {temp_dir}: {e}")
    
    def get_disk_usage(self, path: str) -> Dict[str, int]:
        """Check disk space usage"""
        try:
            usage = shutil.disk_usage(path)
            return {
                'total': usage.total,
                'used': usage.used,
                'free': usage.free,
                'percent_used': (usage.used / usage.total) * 100
            }
        except Exception as e:
            logging.error(f"ไม่สามารถตรวจสอบการใช้งานดิสก์: {e}")
            return {'total': 0, 'used': 0, 'free': 0, 'percent_used': 0}