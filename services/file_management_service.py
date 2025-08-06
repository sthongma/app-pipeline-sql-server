"""
File Management Service สำหรับ PIPELINE_SQLSERVER

รวมฟังชั่นการจัดการไฟล์:
1. การย้ายไฟล์เก่าและโฟลเดอร์ว่าง (จาก move_old_files_cli_app.py)
2. การรวมไฟล์ Excel จาก ZIP files (จาก ZipExcelMerger)
"""

import os
import json
import shutil
import zipfile
import pandas as pd
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from openpyxl.utils import get_column_letter

try:
    from send2trash import send2trash
except ImportError:
    send2trash = None

# ปิดการแจ้งเตือนของ openpyxl
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')


class FileManagementService:
    """บริการจัดการไฟล์รวม"""
    
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
    # File Moving Functions (จาก move_old_files_cli_app.py)
    # ========================
    
    def find_files_older_than(self, root_path: str, days: int) -> List[str]:
        """
        ค้นหาไฟล์ที่มีอายุมากกว่าจำนวนวันที่กำหนด
        
        Args:
            root_path: โฟลเดอร์ที่ต้องการค้นหา
            days: จำนวนวันที่กำหนด
            
        Returns:
            List[str]: รายการไฟล์ที่เก่ากว่าจำนวนวันที่กำหนด
        """
        cutoff = datetime.now() - timedelta(days=days)
        old_files = []
        
        for dirpath, _, filenames in os.walk(root_path):
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                try:
                    mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                    if mtime < cutoff:
                        old_files.append(fpath)
                except Exception:
                    continue
                    
        return old_files
    
    def find_empty_directories(self, root_path: str) -> List[str]:
        """
        ค้นหาโฟลเดอร์ที่ว่างเปล่า
        
        Args:
            root_path: โฟลเดอร์ที่ต้องการค้นหา
            
        Returns:
            List[str]: รายการโฟลเดอร์ที่ว่างเปล่า
        """
        empty_dirs = []
        
        for dirpath, dirnames, filenames in os.walk(root_path, topdown=False):
            if not dirnames and not filenames:
                empty_dirs.append(dirpath)
                
        return empty_dirs
    
    def move_files(self, files: List[str], src_root: str, dest_root: str) -> List[Tuple[str, str]]:
        """
        ย้ายไฟล์ไปยังปลายทางโดยรักษาโครงสร้างโฟลเดอร์
        
        Args:
            files: รายการไฟล์ที่ต้องการย้าย
            src_root: โฟลเดอร์ต้นทาง
            dest_root: โฟลเดอร์ปลายทาง
            
        Returns:
            List[Tuple[str, str]]: รายการ (ต้นทาง, ปลายทาง) ที่ย้ายสำเร็จ
        """
        moved = []
        
        for f in files:
            try:
                rel = os.path.relpath(f, src_root)
                dest_dir = os.path.join(dest_root, os.path.dirname(rel))
                os.makedirs(dest_dir, exist_ok=True)
                dest_path = os.path.join(dest_dir, os.path.basename(f))
                
                shutil.move(f, dest_path)
                moved.append((f, dest_path))
            except Exception as e:
                print(f"❌ ย้าย {f} ไม่สำเร็จ: {e}")
                
        return moved
    
    def move_empty_directories(self, empty_dirs: List[str], src_root: str, dest_root: str) -> List[Tuple[str, str]]:
        """
        ย้ายโฟลเดอร์ที่ว่างเปล่าไปยังปลายทาง
        
        Args:
            empty_dirs: รายการโฟลเดอร์ที่ว่างเปล่า
            src_root: โฟลเดอร์ต้นทาง
            dest_root: โฟลเดอร์ปลายทาง
            
        Returns:
            List[Tuple[str, str]]: รายการ (ต้นทาง, ปลายทาง) ที่ย้ายสำเร็จ
        """
        moved_dirs = []
        
        for dir_path in empty_dirs:
            try:
                rel = os.path.relpath(dir_path, src_root)
                dest_dir = os.path.join(dest_root, rel)
                os.makedirs(os.path.dirname(dest_dir), exist_ok=True)
                shutil.move(dir_path, dest_dir)
                moved_dirs.append((dir_path, dest_dir))
            except Exception as e:
                print(f"❌ ย้ายโฟลเดอร์ {dir_path} ไม่สำเร็จ: {e}")
                
        return moved_dirs
    
    def delete_files_older_than(self, root_path: str, days: int) -> List[str]:
        """
        ลบไฟล์ที่เก่ากว่าจำนวนวันที่กำหนดโดยย้ายไปถังขยะ
        
        Args:
            root_path: โฟลเดอร์ที่ต้องการลบไฟล์
            days: จำนวนวันที่กำหนด
            
        Returns:
            List[str]: รายการไฟล์ที่ลบสำเร็จ
        """
        if send2trash is None:
            print("[!] ไม่พบไลบรารี send2trash กรุณาติดตั้งด้วย pip install send2trash")
            return []
            
        cutoff = datetime.now() - timedelta(days=days)
        deleted = []
        
        for dirpath, _, filenames in os.walk(root_path):
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                try:
                    mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                    if mtime < cutoff:
                        send2trash(fpath)
                        deleted.append(fpath)
                except Exception:
                    continue
                    
        return deleted
    
    def archive_old_files(self, source_path: str, archive_path: str, days: int = 30, 
                         delete_archive_days: int = 90) -> Dict[str, Any]:
        """
        ฟังชั่นหลักสำหรับการจัดเก็บไฟล์เก่า
        
        Args:
            source_path: โฟลเดอร์ต้นทาง
            archive_path: โฟลเดอร์เก็บ archive
            days: จำนวนวันสำหรับไฟล์ที่จะย้าย (default: 30)
            delete_archive_days: จำนวนวันสำหรับการลบใน archive (default: 90)
            
        Returns:
            Dict[str, Any]: ผลลัพธ์การดำเนินการ
        """
        result = {
            "moved_files": [],
            "moved_dirs": [],
            "deleted_files": [],
            "errors": []
        }
        
        try:
            # ค้นหาไฟล์เก่า
            old_files = self.find_files_older_than(source_path, days)
            
            if old_files:
                moved_files = self.move_files(old_files, source_path, archive_path)
                result["moved_files"] = moved_files
            
            # ค้นหาและย้ายโฟลเดอร์ว่าง
            empty_dirs = self.find_empty_directories(source_path)
            if empty_dirs:
                moved_dirs = self.move_empty_directories(empty_dirs, source_path, archive_path)
                result["moved_dirs"] = moved_dirs
            
            # ลบไฟล์ใน archive ที่เก่ากว่า delete_archive_days วัน
            if os.path.exists(archive_path):
                deleted_files = self.delete_files_older_than(archive_path, delete_archive_days)
                result["deleted_files"] = deleted_files
                
        except Exception as e:
            result["errors"].append(str(e))
            
        return result
    
    # ========================
    # ZIP Excel Merger Functions (จาก ZipExcelMerger)
    # ========================
    
    def is_large_number(self, value: Any) -> bool:
        """ตรวจสอบว่าตัวเลขใหญ่เกินไปหรือไม่"""
        try:
            if isinstance(value, str):
                if value.replace('.', '').replace('-', '').replace('+', '').replace('e', '').replace('E', '').isdigit():
                    clean_number = value.replace('.', '').replace('-', '').replace('+', '')
                    if 'e' in clean_number.lower():
                        return True
                    return len(clean_number) > 15
            elif isinstance(value, (int, float)):
                return abs(value) >= 1e15
            return False
        except:
            return False
    
    def safe_convert_column(self, series: pd.Series) -> pd.Series:
        """แปลงคอลัมน์อย่างปลอดภัย โดยเก็บตัวเลขใหญ่เป็นข้อความ"""
        try:
            non_null_series = series.dropna()
            
            if len(non_null_series) == 0:
                return series
            
            numeric_series = pd.to_numeric(non_null_series, errors='coerce')
            
            # ตรวจสอบว่ามีตัวเลขใหญ่หรือไม่
            has_large_numbers = False
            for val in numeric_series.dropna():
                if self.is_large_number(val):
                    has_large_numbers = True
                    break
            
            if has_large_numbers:
                result_series = series.copy()
                result_series = result_series.astype('object')
                mask = pd.notna(result_series)
                result_series.loc[mask] = result_series.loc[mask].astype(str)
                return result_series
            
            if not numeric_series.isna().all():
                result_series = series.copy()
                non_null_mask = pd.notna(series)
                numeric_converted = pd.to_numeric(series[non_null_mask], errors='coerce')
                
                if not numeric_converted.isna().any():
                    result_series[non_null_mask] = numeric_converted
                    return result_series
            
            result_series = series.copy()
            result_series = result_series.astype('object')
            mask = pd.notna(result_series)
            result_series.loc[mask] = result_series.loc[mask].astype(str)
            return result_series
            
        except Exception as e:
            print(f"เกิดข้อผิดพลาดในการแปลงคอลัมน์: {e}")
            return series
    
    def read_excel_safely(self, file_path: str) -> Optional[pd.DataFrame]:
        """อ่านไฟล์ Excel อย่างปลอดภัย"""
        try:
            df = pd.read_excel(file_path, sheet_name=0)
            
            for col in df.columns:
                df[col] = self.safe_convert_column(df[col])
            
            return df
        except Exception as e:
            print(f"ไม่สามารถอ่านไฟล์ {file_path}: {e}")
            return None
    
    def create_organized_folder_structure(self, base_folder: str, file_type: str) -> str:
        """สร้างโครงสร้างโฟลเดอร์ตามรูปแบบ ZipExcelMerger/ปี-เดือน-วัน"""
        current_date = datetime.now()
        date_folder = current_date.strftime('%Y-%m-%d')
        organized_path = os.path.join(base_folder, "ZipExcelMerger", date_folder)
        os.makedirs(organized_path, exist_ok=True)
        return organized_path
    
    def move_zip_files(self, source_folder: str, zip_files: List[str], file_type: str) -> Tuple[Optional[str], List[str]]:
        """ย้ายไฟล์ ZIP ไปยังโฟลเดอร์ที่จัดระเบียบแล้ว"""
        try:
            organized_folder = self.create_organized_folder_structure(source_folder, file_type)
            moved_files = []
            
            for zip_file in zip_files:
                source_path = os.path.join(source_folder, zip_file)
                destination_path = os.path.join(organized_folder, zip_file)
                
                if os.path.exists(destination_path):
                    name, ext = os.path.splitext(zip_file)
                    timestamp = datetime.now().strftime('%H%M%S')
                    destination_path = os.path.join(organized_folder, f"{name}_{timestamp}{ext}")
                
                shutil.move(source_path, destination_path)
                moved_files.append(zip_file)
            
            return organized_folder, moved_files
        except Exception as e:
            print(f"ไม่สามารถย้ายไฟล์ ZIP: {e}")
            return None, []
    
    def get_file_type_from_filename(self, filename: str) -> str:
        """ดึงชื่อประเภทไฟล์จากชื่อไฟล์"""
        name_without_ext = os.path.splitext(filename)[0]
        file_type = ''.join([c for c in name_without_ext if c.isalpha() or c == '_'])
        return file_type if file_type else "Unknown"
    
    def process_zip_excel_merger(self, folder_path: str, progress_callback=None) -> Dict[str, Any]:
        """
        ประมวลผลการรวมไฟล์ Excel จาก ZIP files
        
        Args:
            folder_path: โฟลเดอร์ที่มีไฟล์ ZIP
            progress_callback: callback function สำหรับการแสดงความคืบหน้า
            
        Returns:
            Dict[str, Any]: ผลลัพธ์การดำเนินการ
        """
        result = {
            "success": False,
            "saved_files": [],
            "organized_folder": None,
            "moved_files": [],
            "errors": []
        }
        
        try:
            zip_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.zip')]
            if not zip_files:
                result["errors"].append("ไม่พบไฟล์ ZIP ในโฟลเดอร์ที่เลือก")
                return result
            
            all_excel_files = []
            temp_dirs = []
            
            if progress_callback:
                progress_callback(0.05, f"พบ ZIP {len(zip_files)} ไฟล์ กำลังแตกไฟล์...")
            
            # แตกไฟล์ ZIP
            for i, zip_name in enumerate(zip_files):
                zip_path = os.path.join(folder_path, zip_name)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    file_list = zip_ref.namelist()
                    xlsx_files = [f for f in file_list if f.endswith('.xlsx') and not f.startswith('__MACOSX')]
                    
                    if not xlsx_files:
                        continue
                    
                    temp_dir = os.path.join(folder_path, f"temp_extract_{zip_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                    os.makedirs(temp_dir, exist_ok=True)
                    temp_dirs.append(temp_dir)
                    
                    for j, file in enumerate(xlsx_files):
                        if progress_callback:
                            progress = 0.05 + 0.3 * (i + (j + 1) / len(xlsx_files)) / len(zip_files)
                            progress_callback(progress, f"แตก {zip_name}: {j+1}/{len(xlsx_files)}")
                        
                        zip_ref.extract(file, temp_dir)
                        all_excel_files.append(os.path.join(temp_dir, file))
            
            if not all_excel_files:
                result["errors"].append("ไม่พบไฟล์ Excel (.xlsx) ใน ZIP ใดๆ")
                return result
            
            if progress_callback:
                progress_callback(0.4, "กำลังจัดกลุ่มไฟล์...")
            
            # จัดกลุ่มไฟล์
            group_dict = {}
            header_map = {}
            
            for file_path in all_excel_files:
                try:
                    df_header = pd.read_excel(file_path, sheet_name=0, nrows=1)
                    header_tuple = tuple(df_header.columns)
                    
                    base = os.path.basename(file_path)
                    prefix = ''.join([c for c in base if c.isalpha()])
                    
                    if header_tuple in header_map:
                        group_name = header_map[header_tuple]
                    else:
                        group_name = prefix if prefix else 'Group'
                        count = 1
                        while f"{group_name}_{count}" in group_dict:
                            count += 1
                        if count > 1 or group_name in group_dict:
                            group_name = f"{group_name}_{count}"
                        header_map[header_tuple] = group_name
                    
                    group_dict.setdefault(group_name, []).append(file_path)
                except Exception as e:
                    result["errors"].append(f"ไม่สามารถอ่าน header ของ {file_path}: {e}")
                    continue
            
            if not group_dict:
                result["errors"].append("ไม่พบกลุ่มไฟล์ที่มีโครงสร้างเหมือนกัน")
                return result
            
            file_type = self.get_file_type_from_filename(zip_files[0])
            saved_files = []
            
            # รวมไฟล์แต่ละกลุ่ม
            for idx, (group_name, files) in enumerate(group_dict.items()):
                if progress_callback:
                    progress = 0.4 + 0.5 * (idx + 1) / len(group_dict)
                    progress_callback(progress, f"กำลังรวมกลุ่ม {group_name} ({len(files)} ไฟล์)")
                
                merged_data = []
                for file_path in files:
                    try:
                        df = self.read_excel_safely(file_path)
                        if df is not None:
                            merged_data.append(df)
                    except Exception as e:
                        result["errors"].append(f"ไม่สามารถอ่านไฟล์ {file_path}: {e}")
                        continue
                
                if not merged_data:
                    continue
                
                # รวมข้อมูล
                final_df = pd.concat(merged_data, ignore_index=True)
                
                # บันทึกไฟล์
                output_filename = f"{group_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                output_path = os.path.join(folder_path, output_filename)
                
                with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                    final_df.to_excel(writer, index=False, sheet_name='Merged_Data')
                    worksheet = writer.sheets['Merged_Data']
                    
                    # จัดรูปแบบคอลัมน์
                    for col_idx, col in enumerate(final_df.columns, 1):
                        if final_df[col].dtype == 'object':
                            col_letter = get_column_letter(col_idx)
                            for row in range(2, len(final_df) + 2):
                                cell = worksheet[f'{col_letter}{row}']
                                if cell.value and isinstance(cell.value, str) and self.is_large_number(cell.value):
                                    cell.number_format = '@'
                
                saved_files.append((output_filename, len(final_df)))
            
            # ลบไฟล์ temp
            for temp_dir in temp_dirs:
                shutil.rmtree(temp_dir, ignore_errors=True)
            
            # ย้ายไฟล์ ZIP
            if progress_callback:
                progress_callback(0.95, "กำลังย้ายไฟล์ ZIP...")
            
            organized_folder, moved_files = self.move_zip_files(folder_path, zip_files, file_type)
            
            if progress_callback:
                progress_callback(1.0, f"สำเร็จ! บันทึกไฟล์ {len(saved_files)} กลุ่ม")
            
            result.update({
                "success": True,
                "saved_files": saved_files,
                "organized_folder": organized_folder,
                "moved_files": moved_files
            })
            
        except Exception as e:
            result["errors"].append(f"เกิดข้อผิดพลาด: {str(e)}")
        
        return result
    
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