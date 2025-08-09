"""
File Reader Service สำหรับ PIPELINE_SQLSERVER

จัดการการอ่านไฟล์ Excel/CSV และการค้นหาไฟล์
แยกออกมาจาก FileService เพื่อให้แต่ละ service มีหน้าที่ชัดเจน
"""

import glob
import json
import os
import re
import threading
from typing import Optional, Dict, Any

import pandas as pd

from constants import FileConstants, PathConstants, RegexPatterns


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
            # Fallback ใช้ glob แบบเดิม
            xlsx_files = glob.glob(os.path.join(self.search_path, '*.xlsx'))
            xls_files = glob.glob(os.path.join(self.search_path, '*.xls'))
            csv_files = glob.glob(os.path.join(self.search_path, '*.csv'))
            return xlsx_files + xls_files + csv_files

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
        """ปรับปรุงการ normalize column (เร็วขึ้น)"""
        if pd.isna(col):
            return ""
        return str(col).strip().lower().replace(' ', '').replace('\u200b', '')

    def detect_file_type(self, file_path):
        """ตรวจสอบประเภทของไฟล์ (แบบ dynamic, normalize header) รองรับทั้ง xlsx/xls/csv และ mapping กลับด้าน"""
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

            for logic_type, mapping in self.column_settings.items():
                # พิจารณาทั้ง keys (old->new) และ values (new->old) เพื่อรองรับกรณีผู้ใช้ใส่กลับด้าน
                required_keys = set(self.normalize_col(c) for c in mapping.keys())
                required_vals = set(self.normalize_col(c) for c in mapping.values())
                for row in range(min(2, df_peek.shape[0])):
                    header_row = set(self.normalize_col(col) for col in df_peek.iloc[row].values)
                    if required_keys.issubset(header_row) or required_vals.issubset(header_row):
                        return logic_type
            return None
        except Exception:
            return None

    def build_rename_mapping_for_dataframe(self, df_columns, logic_type):
        """
        สร้าง mapping สำหรับ df.rename(columns=...) โดยอัตโนมัติให้ทิศทางถูกต้อง
        - รองรับทั้ง config ที่เป็น old->new (คาดหวัง) และ new->old (ผู้ใช้ใส่กลับด้าน)
        """
        mapping = self.get_column_name_mapping(logic_type)
        if not mapping:
            return {}

        # Normalize รายชื่อคอลัมน์จาก DataFrame เพื่อเปรียบเทียบ
        normalized_df_cols = set(self.normalize_col(c) for c in list(df_columns))

        # เตรียมชุด normalized ของ keys และ values
        normalized_keys = set(self.normalize_col(k) for k in mapping.keys())
        normalized_vals = set(self.normalize_col(v) for v in mapping.values())

        # วัดว่าชุดไหนตรงกับ header มากกว่า
        overlap_keys = len(normalized_df_cols & normalized_keys)
        overlap_vals = len(normalized_df_cols & normalized_vals)

        # ถ้า header ตรงกับ keys มากกว่า แสดงว่า mapping เป็น old->new อยู่แล้ว
        if overlap_keys >= overlap_vals:
            return mapping

        # ถ้า header ตรงกับ values มากกว่า แสดงว่า mapping ใส่กลับด้าน ต้องกลับทิศทาง
        inverted = {v: k for k, v in mapping.items()}
        return inverted

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
                df = pd.read_csv(file_path, encoding='utf-8')
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
