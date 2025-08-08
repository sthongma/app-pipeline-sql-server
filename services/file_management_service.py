"""
File Management Service สำหรับ PIPELINE_SQLSERVER

รับผิดชอบการจัดการไฟล์:
- การย้ายไฟล์ที่ประมวลผลแล้ว
- การจัดระเบียบโฟลเดอร์
- การจัดการ settings
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor

import pandas as pd


class FileManagementService:
    """
    บริการจัดการไฟล์
    
    รับผิดชอบ:
    - การย้ายไฟล์ที่ประมวลผลแล้ว
    - การจัดระเบียบโฟลเดอร์
    - การจัดการ settings
    """
    
    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize File Management Service
        
        Args:
            base_path: ที่อยู่ฐานสำหรับการทำงาน (default: current directory)
        """
        self.base_path = base_path or os.getcwd()
        self.settings_file = os.path.join(self.base_path, 'config', 'file_management_settings.json')
        self._ensure_config_dir()
    
    def _ensure_config_dir(self):
        """สร้างโฟลเดอร์ config หากไม่มี"""
        config_dir = os.path.dirname(self.settings_file)
        os.makedirs(config_dir, exist_ok=True)
    
    # ========================
    # File Movement Functions
    # ========================
    
    def move_uploaded_files(self, file_paths, logic_types=None, search_path=None):
        """ย้ายไฟล์ที่อัปโหลดแล้วไปยังโฟลเดอร์ Uploaded_Files"""
        try:
            if not search_path:
                search_path = self.base_path
                
            moved_files = []
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            # ใช้ ThreadPoolExecutor สำหรับการย้ายไฟล์หลายไฟล์
            def move_single_file(args):
                idx, file_path = args
                try:
                    logic_type = logic_types[idx] if logic_types else "Unknown"
                    
                    # สร้างโฟลเดอร์
                    uploaded_folder = os.path.join(search_path, "Uploaded_Files", logic_type, current_date)
                    os.makedirs(uploaded_folder, exist_ok=True)
                    
                    # สร้างชื่อไฟล์ใหม่
                    file_name = os.path.basename(file_path)
                    name, ext = os.path.splitext(file_name)
                    timestamp = datetime.now().strftime("%H%M%S")
                    new_name = f"{name}_{timestamp}{ext}"
                    destination = os.path.join(uploaded_folder, new_name)
                    
                    shutil.move(file_path, destination)
                    return (file_path, destination)
                    
                except Exception as e:
                    print(f"ไม่สามารถย้ายไฟล์ {file_path}: {str(e)}")
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
        """สร้างโครงสร้างโฟลเดอร์ตามรูปแบบ file_type/ปี-เดือน-วัน"""
        current_date = datetime.now()
        date_folder = current_date.strftime('%Y-%m-%d')
        organized_path = os.path.join(base_folder, "Processed_Files", file_type, date_folder)
        os.makedirs(organized_path, exist_ok=True)
        return organized_path
    
    # ========================
    # Helper Functions
    # ========================
    
    def get_supported_file_extensions(self) -> List[str]:
        """รายการนามสกุลไฟล์ที่รองรับ"""
        return ['.xlsx', '.xls', '.csv']
    
    def is_supported_file(self, file_path: str) -> bool:
        """ตรวจสอบว่าไฟล์ได้รับการรองรับหรือไม่"""
        file_ext = os.path.splitext(file_path)[1].lower()
        return file_ext in self.get_supported_file_extensions()
    
    def get_file_type_info(self, file_path: str) -> Dict[str, str]:
        """ดึงข้อมูลประเภทไฟล์"""
        file_ext = os.path.splitext(file_path)[1].lower()
        file_types = {
            '.xlsx': {'type': 'Excel (New)', 'engine': 'openpyxl'},
            '.xls': {'type': 'Excel (Legacy)', 'engine': 'xlrd'},
            '.csv': {'type': 'CSV', 'engine': 'pandas'}
        }
        return file_types.get(file_ext, {'type': 'Unknown', 'engine': 'none'})
    
    def get_file_type_from_filename(self, filename: str) -> str:
        """ดึงชื่อประเภทไฟล์จากชื่อไฟล์"""
        name_without_ext = os.path.splitext(filename)[0]
        file_type = ''.join([c for c in name_without_ext if c.isalpha() or c == '_'])
        return file_type if file_type else "Unknown"
    
    def group_files_by_type(self, file_paths: List[str]) -> Dict[str, List[str]]:
        """จัดกลุ่มไฟล์ตามประเภท"""
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
        """โหลดการตั้งค่าจากไฟล์ JSON"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"เกิดข้อผิดพลาดในการโหลดการตั้งค่า: {e}")
            return {}
    
    def save_settings(self, settings: Dict[str, Any]) -> bool:
        """บันทึกการตั้งค่าลงไฟล์ JSON"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"เกิดข้อผิดพลาดในการบันทึกการตั้งค่า: {e}")
            return False
    
    def cleanup_temp_files(self, temp_directories: List[str]) -> None:
        """ลบโฟลเดอร์ temporary ที่ไม่ได้ใช้แล้ว"""
        for temp_dir in temp_directories:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                print(f"ไม่สามารถลบโฟลเดอร์ temp {temp_dir}: {e}")
    
    def get_disk_usage(self, path: str) -> Dict[str, int]:
        """ตรวจสอบการใช้งานพื้นที่ดิสก์"""
        try:
            usage = shutil.disk_usage(path)
            return {
                'total': usage.total,
                'used': usage.used,
                'free': usage.free,
                'percent_used': (usage.used / usage.total) * 100
            }
        except Exception as e:
            print(f"ไม่สามารถตรวจสอบการใช้งานดิสก์: {e}")
            return {'total': 0, 'used': 0, 'free': 0, 'percent_used': 0}