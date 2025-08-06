"""
File Service สำหรับ PIPELINE_SQLSERVER

จัดการการอ่าน ประมวลผล และตรวจสอบไฟล์ Excel/CSV
"""

import glob
import json
import os
import re
import threading
import warnings
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
from dateutil import parser
from sqlalchemy.types import (
    DECIMAL, DATE, Boolean, DateTime, Float, Integer,
    NVARCHAR, SmallInteger
)

from constants import FileConstants, PathConstants, RegexPatterns


# ปิดการแจ้งเตือนของ openpyxl
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

class FileService:
    """
    บริการจัดการไฟล์ Excel/CSV สำหรับ PIPELINE_SQLSERVER
    
    ให้บริการการค้นหา อ่าน ตรวจสอบ และย้ายไฟล์
    พร้อมทั้ง cache สำหรับ performance optimization
    """
    
    def __init__(self, search_path: Optional[str] = None) -> None:
        """
        เริ่มต้น FileService
        
        Args:
            search_path (Optional[str]): ที่อยู่โฟลเดอร์สำหรับค้นหาไฟล์
                            ถ้าไม่ระบุ จะใช้ Downloads folder
        """
        # หากไม่ได้ระบุ path ให้ใช้ Downloads เป็นค่า default
        if search_path:
            self.search_path = search_path
        else:
            self.search_path = PathConstants.DEFAULT_SEARCH_PATH
        
        # Cache สำหรับการตั้งค่า
        self._settings_cache: Dict[str, Any] = {}
        self._cache_lock = threading.Lock()
        self._settings_loaded = False
        
        self.load_settings()
    
    def load_settings(self) -> None:
        """
        โหลดการตั้งค่าคอลัมน์และประเภทข้อมูล
        
        ใช้ cache เพื่อป้องกันการโหลดซ้ำหากได้โหลดแล้ว
        ใช้ thread-safe locking เพื่อ concurrent access
        """
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
        """ค้นหาไฟล์ Excel และ CSV ใน path ที่กำหนด (ปรับปรุงประสิทธิภาพ)"""
        # ไม่ต้องโหลด settings ซ้ำ เพราะโหลดใน __init__ แล้ว
        try:
            # ใช้ os.scandir แทน glob เพื่อความเร็ว
            xlsx_files = []
            csv_files = []
            
            with os.scandir(self.search_path) as entries:
                for entry in entries:
                    if entry.is_file():
                        name_lower = entry.name.lower()
                        if name_lower.endswith('.xlsx'):
                            xlsx_files.append(entry.path)
                        elif name_lower.endswith('.csv'):
                            csv_files.append(entry.path)
            
            return xlsx_files + csv_files
        except Exception:
            # Fallback ใช้ glob แบบเดิม
            xlsx_files = glob.glob(os.path.join(self.search_path, '*.xlsx'))
            csv_files = glob.glob(os.path.join(self.search_path, '*.csv'))
            return xlsx_files + csv_files

    def standardize_column_name(self, col_name):
        """แปลงชื่อคอลัมน์ให้เป็นรูปแบบมาตรฐาน"""
        if pd.isna(col_name):
            return ""
        name = str(col_name).strip().lower()
        name = re.sub(r'[\s\W]+', '_', name)
        return name.strip('_')

    def _convert_dtype_to_sqlalchemy(self, dtype_str):
        """แปลง string dtype เป็น SQLAlchemy type object (ใช้ cache)"""
        if not isinstance(dtype_str, str):
            return NVARCHAR(255)
            
        # ใช้ cache สำหรับ dtype ที่แปลงแล้ว
        cache_key = str(dtype_str).upper()
        if cache_key in self._settings_cache:
            return self._settings_cache[cache_key]
            
        dtype_str = cache_key
        
        try:
            result = None
            if dtype_str.startswith('NVARCHAR'):
                try:
                    length = int(dtype_str.split('(')[1].split(')')[0])
                except Exception:
                    length = 255
                result = NVARCHAR(length)
            elif dtype_str.startswith('DECIMAL'):
                precision, scale = map(int, dtype_str.split('(')[1].split(')')[0].split(','))
                result = DECIMAL(precision, scale)
            elif dtype_str == 'INT':
                result = Integer()
            elif dtype_str == 'BIGINT':
                result = Integer()
            elif dtype_str == 'SMALLINT':
                result = SmallInteger()
            elif dtype_str == 'FLOAT':
                result = Float()
            elif dtype_str == 'DATE':
                result = DATE()
            elif dtype_str == 'DATETIME':
                result = DateTime()
            elif dtype_str == 'BIT':
                result = Boolean()
            else:
                result = NVARCHAR(500)
                
            # เก็บใน cache
            with self._cache_lock:
                self._settings_cache[cache_key] = result
            return result
            
        except Exception:
            result = NVARCHAR(500)
            with self._cache_lock:
                self._settings_cache[cache_key] = result
            return result

    def get_column_name_mapping(self, file_type):
        """รับ mapping ชื่อคอลัมน์ {original: new} ตามประเภทไฟล์ (ใช้ key ตรงๆ)"""
        if not file_type or file_type not in self.column_settings:
            return {}
        return self.column_settings[file_type]

    def get_required_dtypes(self, file_type):
        """รับ dtype ของคอลัมน์ {new_col: dtype} ตามประเภทไฟล์ (ใช้ key ตรงๆ) - ใช้ cache"""
        if not file_type or file_type not in self.column_settings:
            return {}
            
        cache_key = f"dtypes_{file_type}"
        if cache_key in self._settings_cache:
            return self._settings_cache[cache_key]
            
        dtypes = {}
        for orig_col, new_col in self.column_settings[file_type].items():
            dtype_str = self.dtype_settings.get(file_type, {}).get(orig_col, 'NVARCHAR(255)')
            dtype = self._convert_dtype_to_sqlalchemy(dtype_str)
            dtypes[new_col] = dtype
            
        # เก็บใน cache
        with self._cache_lock:
            self._settings_cache[cache_key] = dtypes
        return dtypes

    def get_required_columns(self, file_type):
        """(Deprecated) ใช้ get_required_dtypes แทน"""
        return self.get_required_dtypes(file_type)

    def normalize_col(self, col):
        """ปรับปรุงการ normalize column (เร็วขึ้น)"""
        if pd.isna(col):
            return ""
        return str(col).strip().lower().replace(' ', '').replace('\u200b', '')

    def detect_file_type(self, file_path):
        """ตรวจสอบประเภทของไฟล์ (แบบ dynamic, normalize header) รองรับทั้ง xlsx/csv"""
        try:
            if not self.column_settings:
                return None
                
            # ใช้วิธีเดิมที่ทำงานได้ดี แต่เพิ่ม cache เล็กน้อย
            if file_path.lower().endswith('.csv'):
                df_peek = pd.read_csv(file_path, header=None, nrows=2, encoding='utf-8')
            else:
                df_peek = pd.read_excel(file_path, header=None, nrows=2)
                
            for logic_type in self.column_settings.keys():
                required_cols = set(self.normalize_col(c) for c in self.column_settings[logic_type].keys())
                for row in range(min(2, df_peek.shape[0])):
                    header_row = set(self.normalize_col(col) for col in df_peek.iloc[row].values)
                    if required_cols.issubset(header_row):
                        return logic_type
            return None
        except Exception:
            return None

    def apply_dtypes(self, df, file_type):
        """แปลงประเภทข้อมูลตามการตั้งค่า (ปรับปรุงประสิทธิภาพ) พร้อมรองรับรูปแบบวันเวลาหลากหลาย"""
        if not file_type or file_type not in self.dtype_settings:
            return df
            
        # อ่านค่า format จาก config (default UK)
        date_format = self.dtype_settings[file_type].get('_date_format', 'UK').upper()
        dayfirst = True if date_format == 'UK' else False

        def parse_datetime_safe(val):
            try:
                if isinstance(val, str):
                    val = val.strip()
                    if not val:
                        return pd.NaT
                    return parser.parse(val, dayfirst=dayfirst)
                return parser.parse(str(val), dayfirst=dayfirst)
            except:
                return pd.NaT

        try:
            # แทนที่ค่าว่างทั้งหมดในครั้งเดียว (เร็วกว่า)
            df = df.replace(['', 'nan', 'NaN', 'NULL', 'null', None], pd.NA)
            
            # ประมวลผลแต่ละคอลัมน์
            for col, dtype_str in self.dtype_settings[file_type].items():
                if col.startswith('_') or col not in df.columns:
                    continue
                    
                dtype_str = dtype_str.upper()
                
                try:
                    if 'DATE' in dtype_str:
                        # ใช้ vectorized operation สำหรับ datetime
                        df[col] = df[col].astype(str).apply(parse_datetime_safe)
                    elif dtype_str in ['INT', 'BIGINT', 'SMALLINT', 'FLOAT', 'DECIMAL']:
                        # ใช้ pd.to_numeric ที่เร็วกว่า
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                    elif dtype_str == 'BIT':
                        # แปลง boolean อย่างปลอดภัย
                        df[col] = df[col].map({'True': True, 'False': False, '1': True, '0': False, 1: True, 0: False})
                        df[col] = df[col].fillna(False).astype(bool)
                    else:
                        # String columns
                        df[col] = df[col].replace(pd.NA, None)
                except Exception as e:
                    print(f"เกิดข้อผิดพลาดในการแปลงคอลัมน์ '{col}': {e}")
                    continue
                    
            return df
        except Exception as e:
            print(f"เกิดข้อผิดพลาดในการแปลงประเภทข้อมูล: {e}")
            return df

    def check_invalid_numeric(self, df, logic_type):
        """ตรวจสอบค่าที่ไม่ใช่ตัวเลขในคอลัมน์ที่เป็นตัวเลข (ปรับปรุงประสิทธิภาพ)"""
        invalid = {}
        dtypes = self.get_required_dtypes(logic_type)
        
        for col, dtype in dtypes.items():
            if col not in df.columns:
                continue
                
            if isinstance(dtype, (Integer, Float, DECIMAL, SmallInteger)):
                # ใช้ pd.to_numeric เพื่อหาค่าที่ไม่ใช่ตัวเลข (เร็วกว่า apply)
                numeric_series = pd.to_numeric(df[col], errors='coerce')
                mask = numeric_series.isna() & df[col].notna()
                
                if mask.any():
                    bad_values = df.loc[mask, col].unique()
                    if len(bad_values) > 0:
                        invalid[col] = bad_values[:10]  # จำกัดแค่ 10 ตัวอย่าง
                        
        return invalid

    def clean_numeric_columns(self, df, file_type):
        """Clean ข้อมูลคอลัมน์ตัวเลข (ปรับปรุงประสิทธิภาพ)"""
        if not file_type or file_type not in self.dtype_settings:
            return df
            
        try:
            for col, dtype_str in self.dtype_settings[file_type].items():
                if col not in df.columns:
                    continue
                    
                dtype_str_upper = str(dtype_str).upper()
                if (dtype_str_upper in ["INT", "BIGINT", "SMALLINT", "FLOAT"] 
                    or dtype_str_upper.startswith("DECIMAL")):
                    
                    # ใช้ vectorized operations แทน regex ทีละแถว
                    # แปลงเป็น string ก่อน
                    col_str = df[col].astype(str)
                    
                    # เอาเฉพาะตัวเลข จุด และเครื่องหมายลบ
                    cleaned = col_str.str.replace(r"[^\d.-]", "", regex=True)
                    
                    # แปลงเป็นตัวเลข
                    df[col] = pd.to_numeric(cleaned, errors='coerce')
                    
            return df
        except Exception as e:
            print(f"เกิดข้อผิดพลาดในการ clean ข้อมูลตัวเลข: {e}")
            return df

    def read_excel_file(self, file_path, logic_type):
        """อ่านไฟล์ Excel หรือ CSV ตามประเภทที่กำหนด (ปรับปรุงประสิทธิภาพ)"""
        try:
            # อ่านไฟล์ด้วย chunk เมื่อไฟล์ใหญ่
            if file_path.lower().endswith('.csv'):
                # ตรวจสอบขนาดไฟล์
                file_size = os.path.getsize(file_path)
                if file_size > 50 * 1024 * 1024:  # 50MB
                    # อ่านแบบ chunk สำหรับไฟล์ใหญ่
                    chunks = []
                    for chunk in pd.read_csv(file_path, header=0, encoding='utf-8', chunksize=10000):
                        chunks.append(chunk)
                    df = pd.concat(chunks, ignore_index=True)
                else:
                    df = pd.read_csv(file_path, header=0, encoding='utf-8')
            else:
                # Excel file
                df = pd.read_excel(file_path, header=0, sheet_name=0, engine='openpyxl')
            
            # Apply column mapping
            col_map = self.get_column_name_mapping(logic_type)
            if col_map:
                df.rename(columns=col_map, inplace=True)
            
            # Clean และ apply dtypes
            df = self.clean_numeric_columns(df, logic_type)
            df = self.apply_dtypes(df, logic_type)
            
            return True, df
            
        except Exception as e:
            return False, f"เกิดข้อผิดพลาดขณะอ่านไฟล์: {e}"

    def validate_columns(self, df, logic_type):
        """ตรวจสอบคอลัมน์ที่จำเป็น (dynamic)"""
        if not self.column_settings or logic_type not in self.column_settings:
            return False, "ยังไม่ได้ตั้งค่าคอลัมน์สำหรับประเภทไฟล์นี้"
            
        required_cols = set(self.column_settings[logic_type].values())
        df_cols = set(df.columns)
        missing_cols = required_cols - df_cols
        
        if missing_cols:
            return False, f"คอลัมน์ไม่ครบ: {missing_cols}"
        return True, {}

    def _force_nvarchar_for_invalid(self, df, dtypes):
        """ถ้า dtype ใน DataFrame ไม่ตรงกับ dtype ที่ config ให้แปลงเป็น NVARCHAR(255)"""
        fixed_dtypes = dtypes.copy()
        for col, dtype in dtypes.items():
            if col in df.columns:
                # ถ้า dtype เป็น numeric แต่ข้อมูลจริงเป็น object/str
                if isinstance(dtype, (Integer, Float, DECIMAL, SmallInteger)):
                    if df[col].dtype == object:
                        fixed_dtypes[col] = NVARCHAR(255)
        return fixed_dtypes

    def _analyze_upload_error(self, df, dtypes, error):
        """วิเคราะห์ error และให้ข้อมูลที่เป็นประโยชน์"""
        msg = str(error)
        result = []
        
        if 'Error converting data type nvarchar to numeric' in msg:
            for col, dtype in dtypes.items():
                if isinstance(dtype, (Integer, Float, DECIMAL, SmallInteger)):
                    if col in df.columns:
                        # ใช้ pd.to_numeric เพื่อหาค่าที่แปลงไม่ได้
                        numeric_series = pd.to_numeric(df[col], errors='coerce')
                        mask = numeric_series.isna() & df[col].notna()
                        
                        if mask.any():
                            bad_values = df.loc[mask, col].unique()[:2]  # แค่ 2 ตัวอย่าง
                            bad_examples = ', '.join([repr(str(b)) for b in bad_values])
                            result.append(f"❌ คอลัมน์ '{col}' มีข้อมูลที่ไม่ใช่ตัวเลข เช่น {bad_examples}")
            
            if not result:
                result.append("❌ พบข้อมูลที่ไม่ตรงชนิดข้อมูล (string -> numeric) ในบางคอลัมน์ กรุณาตรวจสอบข้อมูล")
        else:
            result.append("❌ เกิดข้อผิดพลาดขณะอัปโหลดข้อมูล กรุณาตรวจสอบชนิดข้อมูลและค่าที่นำเข้า")
            
        return '\n'.join(result)

    def _get_sql_table_schema(self, engine, table_name):
        """ดึง schema ของตารางจาก SQL Server"""
        from sqlalchemy import inspect
        insp = inspect(engine)
        columns = {}
        if insp.has_table(table_name):
            for col in insp.get_columns(table_name):
                columns[col['name']] = str(col['type']).upper()
        return columns

    def _dtypes_to_sqlalchemy(self, dtypes):
        """แปลง dtypes dict เป็น SQLAlchemy Column object list"""
        from sqlalchemy import Column
        cols = []
        for col, dtype in dtypes.items():
            cols.append(Column(col, dtype))
        return cols

    def _create_table(self, engine, table_name, dtypes):
        """สร้างตารางใหม่"""
        from sqlalchemy import Table, MetaData
        meta = MetaData()
        cols = self._dtypes_to_sqlalchemy(dtypes)
        Table(table_name, meta, *cols)
        meta.drop_all(engine, [meta.tables[table_name]], checkfirst=True)
        meta.create_all(engine, [meta.tables[table_name]])

    def _schema_mismatch(self, sql_schema, dtypes):
        """ตรวจสอบว่า schema ตรงกันหรือไม่"""
        for col, dtype in dtypes.items():
            if col not in sql_schema:
                return True
            if not str(dtype).split('(')[0].upper() in sql_schema[col]:
                return True
        return False

    def upload_to_sql(self, df, table_name, engine, logic_type):
        """อัปโหลดข้อมูลลง SQL Server (ปรับปรุงประสิทธิภาพ)"""
        try:
            dtypes = self.get_required_dtypes(logic_type)
            sql_schema = self._get_sql_table_schema(engine, table_name)
            
            if sql_schema and self._schema_mismatch(sql_schema, dtypes):
                # drop & create table ใหม่
                self._create_table(engine, table_name, dtypes)
            else:
                # ลบข้อมูลเก่า
                with engine.begin() as conn:
                    conn.execute(f"DELETE FROM {table_name}")
            
            # คำนวณ chunk size ที่เหมาะสม
            row_count = len(df)
            if row_count > 100000:
                chunksize = 5000
            elif row_count > 10000:
                chunksize = 2000
            else:
                chunksize = 1000
            
            # เปิด fast_executemany
            from sqlalchemy import event
            @event.listens_for(engine, 'before_cursor_execute')
            def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
                if executemany:
                    cursor.fast_executemany = True
            
            # อัปโหลดแบบ batch
            df.to_sql(
                name=table_name,
                con=engine,
                if_exists='append',
                index=False,
                dtype=dtypes,
                method=None,
                chunksize=chunksize
            )
            
            return True, "อัปโหลดข้อมูลสำเร็จ (ตรวจ dtype, ถ้าไม่ตรงจะ drop แล้วสร้างใหม่)"
            
        except Exception as e:
            dtypes = self.get_required_dtypes(logic_type)
            user_msg = self._analyze_upload_error(df, dtypes, e)
            return False, user_msg

    def move_uploaded_files(self, file_paths, logic_types=None):
        """ย้ายไฟล์ที่อัปโหลดแล้วไปยังโฟลเดอร์ Uploaded_Files (ปรับปรุงประสิทธิภาพ)"""
        try:
            from shutil import move
            moved_files = []
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            # ใช้ ThreadPoolExecutor สำหรับการย้ายไฟล์หลายไฟล์
            def move_single_file(args):
                idx, file_path = args
                try:
                    logic_type = logic_types[idx] if logic_types else "Unknown"
                    
                    # สร้างโฟลเดอร์
                    uploaded_folder = os.path.join(self.search_path, "Uploaded_Files", logic_type, current_date)
                    os.makedirs(uploaded_folder, exist_ok=True)
                    
                    # สร้างชื่อไฟล์ใหม่
                    file_name = os.path.basename(file_path)
                    name, ext = os.path.splitext(file_name)
                    timestamp = datetime.now().strftime("%H%M%S")
                    new_name = f"{name}_{timestamp}{ext}"
                    destination = os.path.join(uploaded_folder, new_name)
                    
                    move(file_path, destination)
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