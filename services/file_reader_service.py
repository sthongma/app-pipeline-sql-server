"""
File Reader Service สำหรับ PIPELINE_SQLSERVER

จัดการการอ่านไฟล์ Excel/CSV และการค้นหาไฟล์
แยกออกมาจาก FileService เพื่อให้แต่ละ service มีหน้าที่ชัดเจน
"""

import json
import os
import re
import threading
from typing import Optional, Dict, Any

import pandas as pd

from constants import PathConstants


class FileReaderService:
    """
    บริการอ่านไฟล์
    
    รับผิดชอบ:
    - การค้นหาไฟล์ Excel/CSV
    - การอ่านไฟล์ Excel/CSV
    - การตรวจจับประเภทไฟล์ (file type detection)
    - การจัดการ column mapping
    """
    
    def __init__(self, search_path: Optional[str] = None, log_callback: Optional[callable] = None) -> None:
        """
        เริ่มต้น FileReaderService
        
        Args:
            search_path (Optional[str]): ที่อยู่โฟลเดอร์สำหรับค้นหาไฟล์
            log_callback (Optional[callable]): ฟังก์ชันสำหรับแสดง log
        """
        # หากไม่ได้ระบุ path ให้ใช้ Downloads เป็นค่า default
        if search_path:
            self.search_path = search_path
        else:
            self.search_path = PathConstants.DEFAULT_SEARCH_PATH
        
        # ตั้งค่า log callback
        self.log_callback = log_callback if log_callback else print
        
        # Cache สำหรับการตั้งค่า
        self._settings_cache: Dict[str, Any] = {}
        self._cache_lock = threading.Lock()
        self._settings_loaded = False
        
        self.load_settings()
    
    def load_settings(self) -> None:
        """โหลดการตั้งค่าคอลัมน์และประเภทข้อมูล"""
        if self._settings_loaded:
            return
            
        try:
            # โหลดการตั้งค่าคอลัมน์
            settings_file = PathConstants.COLUMN_SETTINGS_FILE
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    self.column_settings = json.load(f)
            else:
                self.column_settings = {}
            
            # โหลดการตั้งค่าประเภทข้อมูล
            dtype_file = PathConstants.DTYPE_SETTINGS_FILE
            if os.path.exists(dtype_file):
                with open(dtype_file, 'r', encoding='utf-8') as f:
                    self.dtype_settings = json.load(f)
            else:
                self.dtype_settings = {}
                
            self._settings_loaded = True
            
        except Exception:
            self.column_settings = {}
            self.dtype_settings = {}
            self._settings_loaded = True

    def set_search_path(self, path):
        """ตั้งค่า path สำหรับค้นหาไฟล์ Excel"""
        self.search_path = path

    def find_data_files(self):
        """ค้นหาไฟล์ Excel (.xlsx, .xls) และ CSV ใน path ที่กำหนด (ปรับปรุงประสิทธิภาพ)"""
        try:
            # ใช้ os.scandir แทน glob เพื่อความเร็ว
            xlsx_files = []
            xls_files = []
            csv_files = []
            
            with os.scandir(self.search_path) as entries:
                for entry in entries:
                    if entry.is_file():
                        name_lower = entry.name.lower()
                        if name_lower.endswith('.xlsx'):
                            xlsx_files.append(entry.path)
                        elif name_lower.endswith('.xls'):
                            xls_files.append(entry.path)
                        elif name_lower.endswith('.csv'):
                            csv_files.append(entry.path)
            
            return xlsx_files + xls_files + csv_files
        except Exception:
            return []

    def standardize_column_name(self, col_name):
        """แปลงชื่อคอลัมน์ให้เป็นรูปแบบมาตรฐาน"""
        if pd.isna(col_name):
            return ""
        name = str(col_name).strip().lower()
        name = re.sub(r'[\s\W]+', '_', name)
        return name.strip('_')

    def get_column_name_mapping(self, file_type):
        """รับ mapping ชื่อคอลัมน์ {original: new} ตามประเภทไฟล์"""
        if not file_type or file_type not in self.column_settings:
            return {}
        return self.column_settings[file_type]

    def normalize_col(self, col):
        """ปรับปรุงการ normalize column (แม่นยำกับข้อมูลจริง)"""
        if pd.isna(col):
            return ""
        
        # แปลงเป็น string และทำความสะอาดขั้นพื้นฐาน
        normalized = str(col).strip()
        
        # ลบ zero-width characters และ invisible characters
        normalized = normalized.replace('\u200b', '')  # Zero Width Space
        normalized = normalized.replace('\u200c', '')  # Zero Width Non-Joiner
        normalized = normalized.replace('\u200d', '')  # Zero Width Joiner
        normalized = normalized.replace('\ufeff', '')  # Byte Order Mark
        
        # แปลงเป็น lowercase สำหรับการเปรียบเทียบ
        normalized = normalized.lower()
        
        # ปรับปรุงการจัดการช่องว่าง - ลบช่องว่างซ้ำซ้อนแต่เก็บช่องว่างเดี่ยว
        normalized = ' '.join(normalized.split())
        
        return normalized

    def detect_file_type(self, file_path):
        """ตรวจสอบประเภทของไฟล์ (แบบ dynamic, normalize header) รองรับทั้ง xlsx/xls/csv และ identity mapping"""
        try:
            if not self.column_settings:
                return None

            # อ่านหัวตารางบางส่วนเพื่อเดาประเภทไฟล์
            if file_path.lower().endswith('.csv'):
                df_peek = pd.read_csv(file_path, header=None, nrows=2, encoding='utf-8')
            elif file_path.lower().endswith('.xls'):
                # สำหรับไฟล์ .xls ใช้ xlrd engine
                df_peek = pd.read_excel(file_path, header=None, nrows=2, engine='xlrd')
            else:
                # สำหรับไฟล์ .xlsx
                df_peek = pd.read_excel(file_path, header=None, nrows=2)

            # ตรวจสอบทุก header row ที่เป็นไปได้
            for row in range(min(2, df_peek.shape[0])):
                header_row = set(self.normalize_col(col) for col in df_peek.iloc[row].values if not pd.isna(col))
                
                # ถ้าไม่มี header ใน row นี้ ข้าม
                if not header_row:
                    continue
                
                # หา logic_type ที่ตรงกันมากที่สุด
                best_match = None
                best_score = 0
                
                for logic_type, mapping in self.column_settings.items():
                    if not mapping:  # ข้าม mapping ที่ว่าง
                        continue
                    
                    required_keys = set(self.normalize_col(c) for c in mapping.keys() if c)
                    required_vals = set(self.normalize_col(c) for c in mapping.values() if c)
                    
                    # ตรวจสอบว่าเป็น identity mapping หรือไม่
                    is_identity_mapping = (required_keys == required_vals)
                    
                    if is_identity_mapping:
                        # สำหรับ identity mapping ใช้การจับคู่แบบตรง
                        match_count = len(header_row & required_keys)
                        total_required = len(required_keys)
                        
                        # ใช้เกณฑ์แบบปรับตัว: อย่างน้อย 5 คอลัมน์ตรง หรือ 10% สำหรับ config ขนาดใหญ่
                        if total_required > 0:
                            score = match_count / total_required
                            if total_required >= 50:
                                # สำหรับ config ขนาดใหญ่ (50+ คอลัมน์) ใช้เกณฑ์ 10% หรืออย่างน้อย 5 คอลัมน์
                                min_threshold = max(0.1, 5/total_required)
                            elif total_required >= 20:
                                # สำหรับ config ขนาดกลาง (20-49 คอลัมน์) ใช้เกณฑ์ 20% หรืออย่างน้อย 5 คอลัมน์  
                                min_threshold = max(0.2, 5/total_required)
                            else:
                                # สำหรับ config ขนาดเล็ก (< 20 คอลัมน์) ใช้เกณฑ์ 30%
                                min_threshold = 0.3
                            
                            if score >= min_threshold and score > best_score:
                                best_match = logic_type
                                best_score = score
                    else:
                        # สำหรับ mapping ปกติ ตรวจสอบทั้ง keys และ values
                        keys_match = len(header_row & required_keys)
                        vals_match = len(header_row & required_vals)
                        
                        # เลือกทิศทางที่มี match มากกว่า
                        if keys_match > vals_match:
                            score = keys_match / len(required_keys) if required_keys else 0
                        else:
                            score = vals_match / len(required_vals) if required_vals else 0
                        
                        # ใช้เกณฑ์แบบปรับตัวเดียวกัน
                        total_keys = len(required_keys) if keys_match > vals_match else len(required_vals)
                        if total_keys >= 50:
                            min_threshold = max(0.1, 5/total_keys)
                        elif total_keys >= 20:
                            min_threshold = max(0.2, 5/total_keys)
                        else:
                            min_threshold = 0.3
                            
                        if score >= min_threshold and score > best_score:
                            best_match = logic_type
                            best_score = score
                
                if best_match:
                    return best_match
            
            return None
        except Exception:
            return None

    def build_rename_mapping_for_dataframe(self, df_columns, logic_type):
        """
        สร้าง mapping สำหรับ df.rename(columns=...) โดยอัตโนมัติให้ทิศทางถูกต้อง
        - รองรับ identity mapping และ mapping ปกติ
        - จับคู่คอลัมน์แบบ fuzzy matching สำหรับความแม่นยำ
        """
        mapping = self.get_column_name_mapping(logic_type)
        if not mapping:
            return {}

        # สร้าง normalized mapping สำหรับเปรียบเทียบ
        df_cols_normalized = {self.normalize_col(c): c for c in df_columns}
        
        # สร้าง mapping dictionaries
        keys_to_original = {self.normalize_col(k): k for k in mapping.keys() if k}
        vals_to_original = {self.normalize_col(v): v for v in mapping.values() if v}
        
        # ตรวจสอบว่าเป็น identity mapping หรือไม่
        normalized_keys = set(keys_to_original.keys())
        normalized_vals = set(vals_to_original.keys())
        is_identity_mapping = (normalized_keys == normalized_vals)
        
        if is_identity_mapping:
            # สำหรับ identity mapping ไม่ต้อง rename
            # แต่ให้จับคู่กับชื่อคอลัมน์ที่ตรงกันเพื่อ standardize
            result_mapping = {}
            
            for norm_col, original_df_col in df_cols_normalized.items():
                if norm_col in normalized_keys:
                    # หาคอลัมน์ที่ตรงกันใน mapping
                    for orig_key, orig_val in mapping.items():
                        if self.normalize_col(orig_key) == norm_col:
                            # ใช้ชื่อจาก mapping เป็นชื่อใหม่
                            if original_df_col != orig_key:
                                result_mapping[original_df_col] = orig_key
                            break
            
            return result_mapping
        else:
            # สำหรับ mapping ปกติ ตรวจสอบทิศทาง
            keys_matches = set(df_cols_normalized.keys()) & normalized_keys
            vals_matches = set(df_cols_normalized.keys()) & normalized_vals
            
            result_mapping = {}
            
            if len(keys_matches) >= len(vals_matches):
                # DataFrame columns ตรงกับ keys มากกว่า -> mapping คือ old->new
                for norm_col, original_df_col in df_cols_normalized.items():
                    if norm_col in keys_to_original:
                        original_key = keys_to_original[norm_col]
                        new_value = mapping.get(original_key)
                        if new_value and original_df_col != new_value:
                            result_mapping[original_df_col] = new_value
            else:
                # DataFrame columns ตรงกับ values มากกว่า -> mapping ถูกใส่กลับด้าน
                inverted_mapping = {v: k for k, v in mapping.items() if k and v}
                for norm_col, original_df_col in df_cols_normalized.items():
                    if norm_col in vals_to_original:
                        original_val = vals_to_original[norm_col]
                        new_value = inverted_mapping.get(original_val)
                        if new_value and original_df_col != new_value:
                            result_mapping[original_df_col] = new_value
            
            return result_mapping

    def debug_column_mapping(self, file_path, logic_type=None):
        """
        Debug ฟังก์ชันสำหรับตรวจสอบการ mapping คอลัมน์
        
        Args:
            file_path: ที่อยู่ไฟล์
            logic_type: ประเภทไฟล์ (ถ้าไม่ระบุจะ auto detect)
            
        Returns:
            Dict: ข้อมูล debug
        """
        try:
            # อ่านไฟล์พื้นฐาน (ปิดการใช้ log_callback ระหว่างอ่าน)
            original_log_callback = self.log_callback
            self.log_callback = lambda x: None  # Disable logging
            
            success, result = self.read_file_basic(file_path)
            
            # คืน log_callback เดิม
            self.log_callback = original_log_callback
            
            if not success:
                return {"error": result}
            
            df = result
            actual_columns = list(df.columns)
            
            # ตรวจจับประเภทไฟล์ถ้าไม่ระบุ
            if not logic_type:
                logic_type = self.detect_file_type(file_path)
            
            # ข้อมูล debug
            debug_info = {
                "file_path": file_path,
                "detected_logic_type": logic_type,
                "actual_columns": actual_columns,
                "actual_columns_count": len(actual_columns),
                "normalized_actual_columns": [self.normalize_col(c) for c in actual_columns],
            }
            
            if logic_type and logic_type in self.column_settings:
                mapping = self.column_settings[logic_type]
                debug_info.update({
                    "config_mapping": mapping,
                    "config_keys": list(mapping.keys()),
                    "config_values": list(mapping.values()),
                    "normalized_config_keys": [self.normalize_col(k) for k in mapping.keys()],
                    "normalized_config_values": [self.normalize_col(v) for v in mapping.values()],
                    "is_identity_mapping": set(self.normalize_col(k) for k in mapping.keys()) == set(self.normalize_col(v) for v in mapping.values()),
                })
                
                # ทดสอบ rename mapping
                rename_mapping = self.build_rename_mapping_for_dataframe(df.columns, logic_type)
                debug_info["rename_mapping"] = rename_mapping
                debug_info["rename_mapping_count"] = len(rename_mapping)
                
                # วิเคราะห์การจับคู่
                actual_normalized = set(self.normalize_col(c) for c in actual_columns)
                config_keys_normalized = set(self.normalize_col(k) for k in mapping.keys())
                config_vals_normalized = set(self.normalize_col(v) for v in mapping.values())
                
                debug_info.update({
                    "keys_intersection": list(actual_normalized & config_keys_normalized),
                    "values_intersection": list(actual_normalized & config_vals_normalized),
                    "keys_match_count": len(actual_normalized & config_keys_normalized),
                    "values_match_count": len(actual_normalized & config_vals_normalized),
                    "missing_from_actual": list(config_keys_normalized - actual_normalized),
                    "extra_in_actual": list(actual_normalized - config_keys_normalized),
                })
            
            return debug_info
            
        except Exception as e:
            return {"error": f"Exception occurred: {type(e).__name__}: {str(e)}"}

    def read_file_basic(self, file_path, file_type='auto'):
        """
        อ่านไฟล์ Excel (.xlsx, .xls) หรือ CSV แบบพื้นฐาน (ไม่ทำการประมวลผล)
        
        Args:
            file_path: ที่อยู่ไฟล์
            file_type: ประเภทไฟล์ ('excel', 'excel_xls', 'csv', 'auto')
            
        Returns:
            Tuple[bool, Union[pd.DataFrame, str]]: (สำเร็จ, DataFrame หรือข้อความข้อผิดพลาด)
        """
        try:
            # ตรวจสอบไฟล์มีอยู่หรือไม่
            if not os.path.exists(file_path):
                return False, f"ไม่พบไฟล์: {file_path}"
            
            # Auto-detect file type
            if file_type == 'auto':
                if file_path.lower().endswith('.csv'):
                    file_type = 'csv'
                elif file_path.lower().endswith('.xls'):
                    file_type = 'excel_xls'
                else:
                    file_type = 'excel'
            
            # อ่านไฟล์
            if file_type == 'csv':
                # รองรับไฟล์ภาษาไทย: UTF-8 → cp874 → latin1
                try:
                    df = pd.read_csv(file_path, encoding='utf-8')
                except UnicodeDecodeError:
                    try:
                        df = pd.read_csv(file_path, encoding='cp874')
                    except UnicodeDecodeError:
                        df = pd.read_csv(file_path, encoding='latin1')
            elif file_type == 'excel_xls':
                # สำหรับไฟล์ .xls ใช้ xlrd engine
                df = pd.read_excel(file_path, sheet_name=0, engine='xlrd')
            else:
                # สำหรับไฟล์ .xlsx
                df = pd.read_excel(file_path, sheet_name=0)
            
            if df.empty:
                return False, "ไฟล์ว่างเปล่า"
            
            self.log_callback(f"✅ อ่านไฟล์สำเร็จ: {os.path.basename(file_path)} ({len(df):,} แถว, {len(df.columns)} คอลัมน์)")
            
            return True, df
            
        except Exception as e:
            error_msg = f"ไม่สามารถอ่านไฟล์ {os.path.basename(file_path)}: {str(e)}"
            self.log_callback(f"❌ {error_msg}")
            return False, error_msg

    def read_file_with_mapping(self, file_path, logic_type):
        """
        อ่านไฟล์และ apply column mapping
        
        Args:
            file_path: ที่อยู่ไฟล์
            logic_type: ประเภทไฟล์ตาม logic
            
        Returns:
            Tuple[bool, Union[pd.DataFrame, str]]: (สำเร็จ, DataFrame หรือข้อความข้อผิดพลาด)
        """
        try:
            # อ่านไฟล์พื้นฐาน
            success, result = self.read_file_basic(file_path)
            if not success:
                return success, result
            
            df = result
            
            # Apply column mapping (เลือกทิศทางอัตโนมัติให้ตรงกับ header)
            col_map = self.build_rename_mapping_for_dataframe(df.columns, logic_type)
            if col_map:
                self.log_callback(f"🔄 ปรับชื่อคอลัมน์ตาม mapping ({len(col_map)} คอลัมน์)")
                df.rename(columns=col_map, inplace=True)
            
            return True, df
            
        except Exception as e:
            error_msg = f"ไม่สามารถประมวลผล mapping สำหรับ {os.path.basename(file_path)}: {str(e)}"
            self.log_callback(f"❌ {error_msg}")
            return False, error_msg

    def peek_file_structure(self, file_path, num_rows=5):
        """
        ดูโครงสร้างไฟล์โดยไม่อ่านทั้งหมด
        
        Args:
            file_path: ที่อยู่ไฟล์
            num_rows: จำนวนแถวที่ต้องการดู
            
        Returns:
            Dict: ข้อมูลโครงสร้างไฟล์
        """
        try:
            # ตรวจสอบไฟล์มีอยู่หรือไม่
            if not os.path.exists(file_path):
                return {"error": f"ไม่พบไฟล์: {file_path}"}
            
            if file_path.lower().endswith('.csv'):
                file_type = 'csv'
            elif file_path.lower().endswith('.xls'):
                file_type = 'excel_xls'
            else:
                file_type = 'excel'
            
            # อ่านแค่ส่วนบน
            if file_type == 'csv':
                df = pd.read_csv(file_path, nrows=num_rows, encoding='utf-8')
            elif file_type == 'excel_xls':
                df = pd.read_excel(file_path, sheet_name=0, nrows=num_rows, engine='xlrd')
            else:
                df = pd.read_excel(file_path, sheet_name=0, nrows=num_rows)
            
            # ตรวจจับประเภทไฟล์
            detected_type = self.detect_file_type(file_path)
            
            # สร้างรายงาน
            structure_info = {
                "file_name": os.path.basename(file_path),
                "file_type": file_type,
                "detected_logic_type": detected_type,
                "total_columns": len(df.columns),
                "columns": list(df.columns),
                "sample_data": df.to_dict('records'),
                "column_types": {col: str(df[col].dtype) for col in df.columns}
            }
            
            # เพิ่มข้อมูล mapping ถ้ามี
            if detected_type:
                col_mapping = self.get_column_name_mapping(detected_type)
                if col_mapping:
                    structure_info["column_mapping"] = col_mapping
            
            return structure_info
            
        except Exception as e:
            return {"error": f"ไม่สามารถอ่านโครงสร้างไฟล์: {str(e)}"}

    def get_file_info(self, file_path):
        """
        ดูข้อมูลพื้นฐานของไฟล์
        
        Args:
            file_path: ที่อยู่ไฟล์
            
        Returns:
            Dict: ข้อมูลไฟล์
        """
        try:
            if not os.path.exists(file_path):
                return {"error": f"ไม่พบไฟล์: {file_path}"}
            
            file_stats = os.stat(file_path)
            if file_path.lower().endswith('.csv'):
                file_type = 'csv'
            elif file_path.lower().endswith('.xls'):
                file_type = 'excel_xls'
            else:
                file_type = 'excel'
            
            # นับจำนวนแถวโดยประมาณ (สำหรับไฟล์ใหญ่)
            try:
                if file_type == 'csv':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        row_count = sum(1 for line in f) - 1  # ลบ header
                elif file_type == 'excel_xls':
                    # สำหรับ Excel .xls ใช้ xlrd engine
                    df_shape = pd.read_excel(file_path, sheet_name=0, engine='xlrd').shape
                    row_count = df_shape[0]
                else:
                    # สำหรับ Excel .xlsx
                    df_shape = pd.read_excel(file_path, sheet_name=0).shape
                    row_count = df_shape[0]
            except:
                row_count = "ไม่สามารถนับได้"
            
            # ตรวจจับประเภทไฟล์
            detected_type = self.detect_file_type(file_path)
            
            return {
                "file_name": os.path.basename(file_path),
                "file_path": file_path,
                "file_size": f"{file_stats.st_size / (1024*1024):.2f} MB",
                "file_type": file_type,
                "detected_logic_type": detected_type or "ไม่รู้จัก",
                "estimated_rows": row_count,
                "last_modified": pd.Timestamp.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            return {"error": f"ไม่สามารถดูข้อมูลไฟล์: {str(e)}"}

    def validate_file_before_processing(self, file_path, logic_type):
        """
        ตรวจสอบไฟล์ก่อนประมวลผล
        
        Args:
            file_path: ที่อยู่ไฟล์
            logic_type: ประเภทไฟล์ตาม logic
            
        Returns:
            Dict: ผลการตรวจสอบ
        """
        validation_result = {
            "valid": False,
            "issues": [],
            "warnings": [],
            "file_info": {}
        }
        
        try:
            # ตรวจสอบไฟล์มีอยู่หรือไม่
            if not os.path.exists(file_path):
                validation_result["issues"].append(f"ไม่พบไฟล์: {file_path}")
                return validation_result
            
            # ตรวจสอบขนาดไฟล์
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                validation_result["issues"].append("ไฟล์ว่างเปล่า")
                return validation_result
            
            if file_size > 100 * 1024 * 1024:  # 100 MB
                validation_result["warnings"].append("ไฟล์ขนาดใหญ่ (>100MB) อาจใช้เวลานาน")
            
            # ตรวจสอบประเภทไฟล์
            detected_type = self.detect_file_type(file_path)
            if not detected_type:
                validation_result["warnings"].append("ไม่สามารถตรวจจับประเภทไฟล์อัตโนมัติได้")
            elif detected_type != logic_type:
                validation_result["warnings"].append(f"ประเภทไฟล์ที่ตรวจจับได้ ({detected_type}) ไม่ตรงกับที่ระบุ ({logic_type})")
            
            # ตรวจสอบโครงสร้างพื้นฐาน
            structure = self.peek_file_structure(file_path, 1)
            if "error" in structure:
                validation_result["issues"].append(structure["error"])
                return validation_result
            
            validation_result["file_info"] = structure
            
            # ตรวจสอบคอลัมน์ที่จำเป็น
            if logic_type in self.column_settings:
                required_original_cols = set(self.column_settings[logic_type].keys())
                file_cols = set(structure["columns"])
                
                # Normalize เพื่อเปรียบเทียบ
                required_normalized = set(self.normalize_col(col) for col in required_original_cols)
                file_normalized = set(self.normalize_col(col) for col in file_cols)
                
                missing_cols = required_normalized - file_normalized
                if missing_cols:
                    validation_result["issues"].append(f"คอลัมน์ที่ขาดหายไป: {missing_cols}")
                else:
                    validation_result["valid"] = True
            else:
                validation_result["warnings"].append(f"ไม่มีการตั้งค่าสำหรับประเภทไฟล์ '{logic_type}'")
                validation_result["valid"] = True  # ยอมรับไฟล์ที่ไม่มี config
            
        except Exception as e:
            validation_result["issues"].append(f"เกิดข้อผิดพลาดในการตรวจสอบ: {str(e)}")
        
        return validation_result

    def list_available_file_types(self):
        """แสดงรายการประเภทไฟล์ที่สามารถประมวลผลได้"""
        if not self.column_settings:
            return []
        
        file_types = []
        for logic_type, mapping in self.column_settings.items():
            if isinstance(mapping, dict) and mapping:
                file_types.append({
                    "logic_type": logic_type,
                    "required_columns": len(mapping),
                    "column_mapping": mapping
                })
        
        return file_types
