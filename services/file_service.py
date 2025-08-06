"""
File Service สำหรับ PIPELINE_SQLSERVER

จัดการการอ่าน ประมวลผล และตรวจสอบไฟล์ Excel/CSV
พร้อมการแจ้งเตือน error และ log ที่ละเอียดเพื่อระบุปัญหาคอลัมน์และชนิดข้อมูล

ฟีเจอร์ใหม่:
- comprehensive_data_validation(): ตรวจสอบข้อมูลอย่างละเอียดก่อนประมวลผล
- generate_pre_processing_report(): แสดงรายงานสรุปก่อนประมวลผล  
- print_detailed_validation_report(): รายงานการตรวจสอบแบบละเอียด
- check_invalid_numeric(): ตรวจสอบข้อมูลตัวเลขพร้อมรายงานละเอียด
- apply_dtypes(): แปลงข้อมูลพร้อมรายงานการแปลง

ตัวอย่างการใช้งาน:
    # สำหรับ GUI
    file_service = FileService(log_callback=gui_log_function)
    
    # สำหรับ CLI
    file_service = FileService(log_callback=logging.info)
    
    # การใช้งานปกติ
    success, df = file_service.read_excel_file("data.xlsx", "sales_data")
    # จะแสดงรายงานการตรวจสอบข้อมูลอัตโนมัติใน log ที่กำหนด
    
    # หรือตรวจสอบแยก
    validation_report = file_service.comprehensive_data_validation(df, "sales_data")
    file_service.generate_pre_processing_report(df, "sales_data")
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
    NVARCHAR, SmallInteger, Text
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
    
    def __init__(self, search_path: Optional[str] = None, log_callback: Optional[callable] = None) -> None:
        """
        เริ่มต้น FileService
        
        Args:
            search_path (Optional[str]): ที่อยู่โฟลเดอร์สำหรับค้นหาไฟล์
                            ถ้าไม่ระบุ จะใช้ Downloads folder
            log_callback (Optional[callable]): ฟังก์ชันสำหรับแสดง log
                            ถ้าไม่ระบุ จะใช้ print
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
                if dtype_str == 'NVARCHAR(MAX)':
                    # ใช้ Text สำหรับ NVARCHAR(MAX) เพื่อรองรับข้อมูลยาว
                    result = Text()
                else:
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
        """แปลงประเภทข้อมูลตามการตั้งค่า พร้อมรายงานข้อผิดพลาดละเอียด"""
        if not file_type or file_type not in self.dtype_settings:
            return df
            
        # อ่านค่า format จาก config (default UK)
        date_format = self.dtype_settings[file_type].get('_date_format', 'UK').upper()
        dayfirst = True if date_format == 'UK' else False

        conversion_log = {
            'successful_conversions': [],
            'failed_conversions': {},
            'warnings': []
        }

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
            
            # แสดง log เฉพาะครั้งแรก (ไม่ซ้ำในแต่ละ chunk)
            if not hasattr(self, f'_dtype_conversion_log_{file_type}'):
                self.log_callback(f"\n🔄 กำลังแปลงประเภทข้อมูลสำหรับไฟล์ประเภท: {file_type}")
                self.log_callback("-" * 50)
                self._dtype_conversion_log_shown = True
            
            # ประมวลผลแต่ละคอลัมน์
            for col, dtype_str in self.dtype_settings[file_type].items():
                if col.startswith('_') or col not in df.columns:
                    continue
                    
                dtype_str = dtype_str.upper()
                original_null_count = df[col].isnull().sum()
                
                try:
                    if 'DATE' in dtype_str:
                        # ใช้ vectorized operation สำหรับ datetime
                        df[col] = df[col].astype(str).apply(parse_datetime_safe)
                        new_null_count = df[col].isnull().sum()
                        failed_count = new_null_count - original_null_count
                        
                        if failed_count > 0:
                            # ตัวอย่างข้อมูลที่แปลงไม่ได้
                            original_series = df[col].astype(str)
                            failed_mask = df[col].isnull() & original_series.notna() & (original_series != 'nan')
                            failed_examples = original_series.loc[failed_mask].unique()[:3]
                            
                            conversion_log['failed_conversions'][col] = {
                                'expected_type': dtype_str,
                                'failed_count': failed_count,
                                'examples': failed_examples.tolist(),
                                'error_type': 'Invalid date format'
                            }
                            
                            if failed_count > len(df) * 0.1:  # มากกว่า 10%
                                conversion_log['warnings'].append(f"คอลัมน์ '{col}' มีข้อมูลวันที่ผิดมากกว่า 10%")
                        else:
                            conversion_log['successful_conversions'].append(f"{col} ({dtype_str})")
                            
                    elif dtype_str in ['INT', 'BIGINT', 'SMALLINT', 'FLOAT', 'DECIMAL']:
                        # ใช้ pd.to_numeric ที่เร็วกว่า
                        numeric_result = pd.to_numeric(df[col], errors='coerce')
                        new_null_count = numeric_result.isnull().sum()
                        failed_count = new_null_count - original_null_count
                        
                        if failed_count > 0:
                            # ตัวอย่างข้อมูลที่แปลงไม่ได้
                            failed_mask = numeric_result.isnull() & df[col].notna()
                            failed_examples = df.loc[failed_mask, col].unique()[:3]
                            
                            conversion_log['failed_conversions'][col] = {
                                'expected_type': dtype_str,
                                'failed_count': failed_count,
                                'examples': [str(x) for x in failed_examples],
                                'error_type': 'Invalid numeric format'
                            }
                            
                            if failed_count > len(df) * 0.05:  # มากกว่า 5%
                                conversion_log['warnings'].append(f"คอลัมน์ '{col}' มีข้อมูลตัวเลขผิดมากกว่า 5%")
                        else:
                            conversion_log['successful_conversions'].append(f"{col} ({dtype_str})")
                        
                        df[col] = numeric_result
                        
                    elif dtype_str == 'BIT':
                        # แปลง boolean อย่างปลอดภัย
                        original_series = df[col].copy()
                        df[col] = df[col].map({'True': True, 'False': False, '1': True, '0': False, 1: True, 0: False})
                        df[col] = df[col].fillna(False).astype(bool)
                        
                        # ตรวจสอบว่ามีข้อมูลที่แปลงไม่ได้หรือไม่
                        unmapped_mask = df[col].isnull() & original_series.notna()
                        if unmapped_mask.any():
                            unmapped_examples = original_series.loc[unmapped_mask].unique()[:3]
                            conversion_log['warnings'].append(
                                f"คอลัมน์ '{col}' มีข้อมูลที่ไม่ใช่ boolean: {[str(x) for x in unmapped_examples]}"
                            )
                        
                        conversion_log['successful_conversions'].append(f"{col} (BOOLEAN)")
                        
                    else:
                        # String columns
                        df[col] = df[col].replace(pd.NA, None)
                        conversion_log['successful_conversions'].append(f"{col} (STRING)")
                        
                except Exception as e:
                    conversion_log['failed_conversions'][col] = {
                        'expected_type': dtype_str,
                        'error': str(e),
                        'error_type': 'Conversion error'
                    }
                    continue
            
            # แสดงรายงานการแปลงเฉพาะครั้งสุดท้าย
            if not hasattr(self, f'_conversion_report_shown_{file_type}'):
                self._print_conversion_report(conversion_log)
                self._conversion_report_shown = True
                
            return df
            
        except Exception as e:
            self.log_callback(f"❌ เกิดข้อผิดพลาดในการแปลงประเภทข้อมูล: {e}")
            return df

    def check_invalid_numeric(self, df, logic_type):
        """ตรวจสอบค่าที่ไม่ใช่ตัวเลขในคอลัมน์ที่เป็นตัวเลข พร้อมรายงานละเอียด"""
        validation_report = {
            'has_issues': False,
            'invalid_data': {},
            'summary': []
        }
        
        dtypes = self.get_required_dtypes(logic_type)
        
        for col, dtype in dtypes.items():
            if col not in df.columns:
                continue
                
            if isinstance(dtype, (Integer, Float, DECIMAL, SmallInteger)):
                numeric_series = pd.to_numeric(df[col], errors='coerce')
                mask = numeric_series.isna() & df[col].notna()
                
                if mask.any():
                    validation_report['has_issues'] = True
                    invalid_count = mask.sum()
                    bad_values = df.loc[mask, col].unique()[:5]  # เพิ่มตัวอย่างเป็น 5
                    
                    # หาแถวที่มีปัญหา
                    problem_rows = df.index[mask].tolist()[:10]  # แสดงแค่ 10 แถวแรก
                    
                    validation_report['invalid_data'][col] = {
                        'expected_type': str(dtype),
                        'invalid_count': invalid_count,
                        'total_rows': len(df),
                        'percentage': round((invalid_count / len(df)) * 100, 2),
                        'examples': bad_values.tolist(),
                        'problem_rows': [r + 2 for r in problem_rows]  # +2 เพราะ header + 0-indexed
                    }
                    
                    summary_msg = (f"❌ คอลัมน์ '{col}' ต้องการข้อมูลตัวเลข ({str(dtype)}) "
                                 f"แต่พบข้อมูลที่ไม่ใช่ตัวเลข {invalid_count:,} แถว "
                                 f"({validation_report['invalid_data'][col]['percentage']}%)")
                    validation_report['summary'].append(summary_msg)
                        
        return validation_report

    def comprehensive_data_validation(self, df, logic_type):
        """ตรวจสอบข้อมูลอย่างละเอียดก่อนประมวลผล"""
        validation_report = {
            'status': True,
            'column_issues': {},
            'data_type_issues': {},
            'missing_columns': [],
            'extra_columns': [],
            'summary': [],
            'details': {}
        }
        
        try:
            # ตรวจสอบคอลัมน์
            if logic_type in self.column_settings:
                required_cols = set(self.column_settings[logic_type].values())
                df_cols = set(df.columns)
                
                validation_report['missing_columns'] = list(required_cols - df_cols)
                validation_report['extra_columns'] = list(df_cols - required_cols)
                
                if validation_report['missing_columns']:
                    validation_report['status'] = False
                    validation_report['summary'].append(
                        f"❌ คอลัมน์ที่ขาดหายไป: {', '.join(validation_report['missing_columns'])}"
                    )
                
                if validation_report['extra_columns']:
                    validation_report['summary'].append(
                        f"⚠️  คอลัมน์เพิ่มเติมที่ไม่ได้กำหนดไว้: {', '.join(validation_report['extra_columns'])}"
                    )
            
            # ตรวจสอบชนิดข้อมูลแต่ละคอลัมน์
            dtypes = self.get_required_dtypes(logic_type)
            
            for col, expected_dtype in dtypes.items():
                if col in df.columns:
                    issues = self._validate_column_data_type(df[col], col, expected_dtype)
                    if issues:
                        validation_report['data_type_issues'][col] = issues
                        validation_report['status'] = False
                        
                        # เพิ่มข้อความสรุป
                        issue_summary = f"❌ คอลัมน์ '{col}': {issues['summary']}"
                        validation_report['summary'].append(issue_summary)
            
            # สรุปภาพรวม
            validation_report['details'] = {
                'total_rows': len(df),
                'total_columns': len(df.columns),
                'required_columns': len(dtypes),
                'validation_timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            validation_report['status'] = False
            validation_report['summary'].append(f"❌ เกิดข้อผิดพลาดในการตรวจสอบ: {str(e)}")
        
        return validation_report

    def _validate_column_data_type(self, series, col_name, expected_dtype):
        """ตรวจสอบชนิดข้อมูลของคอลัมน์เฉพาะ"""
        issues = {}
        
        try:
            total_rows = len(series)
            non_null_rows = series.notna().sum()
            null_rows = total_rows - non_null_rows
            
            if isinstance(expected_dtype, (Integer, Float, DECIMAL, SmallInteger)):
                # ตรวจสอบข้อมูลตัวเลข
                numeric_series = pd.to_numeric(series, errors='coerce')
                invalid_mask = numeric_series.isna() & series.notna()
                invalid_count = invalid_mask.sum()
                
                if invalid_count > 0:
                    invalid_examples = series.loc[invalid_mask].unique()[:3]
                    problem_rows = series.index[invalid_mask].tolist()[:5]
                    
                    issues = {
                        'type': 'numeric_validation_error',
                        'expected_type': str(expected_dtype),
                        'current_type': str(series.dtype),
                        'invalid_count': invalid_count,
                        'total_rows': total_rows,
                        'percentage': round((invalid_count / total_rows) * 100, 2),
                        'examples': [str(x) for x in invalid_examples],
                        'problem_rows': [r + 2 for r in problem_rows],  # +2 สำหรับ header
                        'summary': f"พบข้อมูลที่ไม่ใช่ตัวเลข {invalid_count:,} แถว ({round((invalid_count / total_rows) * 100, 2)}%)"
                    }
                    
            elif isinstance(expected_dtype, (DATE, DateTime)):
                # ตรวจสอบข้อมูลวันที่
                def parse_date_safe(val):
                    try:
                        if pd.isna(val) or val == '':
                            return pd.NaT
                        return parser.parse(str(val))
                    except:
                        return pd.NaT
                
                date_series = series.apply(parse_date_safe)
                invalid_mask = date_series.isna() & series.notna()
                invalid_count = invalid_mask.sum()
                
                if invalid_count > 0:
                    invalid_examples = series.loc[invalid_mask].unique()[:3]
                    problem_rows = series.index[invalid_mask].tolist()[:5]
                    
                    issues = {
                        'type': 'date_validation_error',
                        'expected_type': str(expected_dtype),
                        'current_type': str(series.dtype),
                        'invalid_count': invalid_count,
                        'total_rows': total_rows,
                        'percentage': round((invalid_count / total_rows) * 100, 2),
                        'examples': [str(x) for x in invalid_examples],
                        'problem_rows': [r + 2 for r in problem_rows],
                        'summary': f"พบข้อมูลวันที่ที่ไม่ถูกต้อง {invalid_count:,} แถว ({round((invalid_count / total_rows) * 100, 2)}%)"
                    }
                    
            elif isinstance(expected_dtype, NVARCHAR):
                # ตรวจสอบความยาวของ string
                max_length = expected_dtype.length if hasattr(expected_dtype, 'length') else 255
                
                # หาข้อมูลที่ยาวเกินกำหนด
                string_series = series.astype(str)
                too_long_mask = string_series.str.len() > max_length
                too_long_count = too_long_mask.sum()
                
                if too_long_count > 0:
                    too_long_examples = string_series.loc[too_long_mask].str[:50].unique()[:3]  # แสดงแค่ 50 ตัวอักษรแรก
                    actual_lengths = string_series.loc[too_long_mask].str.len().unique()[:5]
                    max_actual_length = string_series.str.len().max()
                    problem_rows = series.index[too_long_mask].tolist()[:5]
                    
                    issues = {
                        'type': 'string_length_error',
                        'expected_type': f"NVARCHAR({max_length})",
                        'max_allowed_length': max_length,
                        'max_actual_length': max_actual_length,
                        'too_long_count': too_long_count,
                        'total_rows': total_rows,
                        'percentage': round((too_long_count / total_rows) * 100, 2),
                        'examples': [f"{ex}... (ความยาว: {len(string_series.loc[string_series.str.startswith(ex[:10])].iloc[0])})" for ex in too_long_examples],
                        'actual_lengths': sorted(actual_lengths, reverse=True),
                        'problem_rows': [r + 2 for r in problem_rows],
                        'summary': f"พบข้อมูลที่ยาวเกิน {max_length} ตัวอักษร จำนวน {too_long_count:,} แถว ({round((too_long_count / total_rows) * 100, 2)}%) ความยาวสูงสุด: {max_actual_length}"
                    }
            elif isinstance(expected_dtype, Text):
                # ข้ามการตรวจสอบความยาวสำหรับ Text() (NVARCHAR(MAX))
                pass
            
            # เพิ่มข้อมูลเกี่ยวกับ null values ถ้ามี
            if null_rows > 0 and not issues:
                null_percentage = round((null_rows / total_rows) * 100, 2)
                if null_percentage > 50:  # เตือนถ้า null มากกว่า 50%
                    issues = {
                        'type': 'high_null_percentage',
                        'null_count': null_rows,
                        'total_rows': total_rows,
                        'percentage': null_percentage,
                        'summary': f"มีข้อมูลว่าง {null_rows:,} แถว ({null_percentage}%)"
                    }
        
        except Exception as e:
            issues = {
                'type': 'validation_error',
                'error': str(e),
                'summary': f"เกิดข้อผิดพลาดในการตรวจสอบ: {str(e)}"
            }
        
        return issues

    def generate_pre_processing_report(self, df, logic_type):
        """สร้างรายงานสรุปก่อนประมวลผลข้อมูล"""
        self.log_callback("=" * 70)
        self.log_callback("📋 รายงานการตรวจสอบข้อมูลก่อนประมวลผล")
        self.log_callback("=" * 70)
        
        # ข้อมูลทั่วไป
        self.log_callback(f"📄 ไฟล์ประเภท: {logic_type}")
        self.log_callback(f"📊 จำนวนแถว: {len(df):,}")
        self.log_callback(f"📊 จำนวนคอลัมน์: {len(df.columns)}")
        self.log_callback(f"⏰ เวลาตรวจสอบ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log_callback("-" * 70)
        
        # ตรวจสอบคอลัมน์
        validation_result = self.validate_columns(df, logic_type)
        if not validation_result[0]:
            self.log_callback(f"❌ {validation_result[1]}")
        else:
            self.log_callback("✅ คอลัมน์ครบถ้วนตามที่กำหนด")
        
        # ตรวจสอบข้อมูลตัวเลข
        numeric_validation = self.check_invalid_numeric(df, logic_type)
        if numeric_validation['has_issues']:
            self.log_callback("\n⚠️  พบปัญหาข้อมูลตัวเลข:")
            for msg in numeric_validation['summary']:
                self.log_callback(f"   • {msg}")
                
            # แสดงรายละเอียดเพิ่มเติม
            self.log_callback("\n📝 รายละเอียดปัญหา:")
            for col, details in numeric_validation['invalid_data'].items():
                self.log_callback(f"   🔸 คอลัมน์ '{col}':")
                self.log_callback(f"      - ชนิดข้อมูลที่ต้องการ: {details['expected_type']}")
                self.log_callback(f"      - ตัวอย่างข้อมูลที่ผิด: {details['examples']}")
                self.log_callback(f"      - แถวที่มีปัญหา (ตัวอย่าง): {details['problem_rows']}")
        else:
            self.log_callback("\n✅ ข้อมูลตัวเลขถูกต้องทั้งหมด")
        
        # ตรวจสอบข้อมูลอย่างละเอียด
        comprehensive_result = self.comprehensive_data_validation(df, logic_type)
        if not comprehensive_result['status']:
            self.log_callback("\n🔍 การตรวจสอบเพิ่มเติม:")
            for msg in comprehensive_result['summary']:
                self.log_callback(f"   • {msg}")
        
        self.log_callback("=" * 70)
        overall_status = validation_result[0] and not numeric_validation['has_issues'] and comprehensive_result['status']
        
        if overall_status:
            self.log_callback("🎉 ผ่านการตรวจสอบทั้งหมด พร้อมประมวลผล")
        else:
            self.log_callback("⚠️  พบปัญหาที่ต้องแก้ไขก่อนประมวลผล")
        
        self.log_callback("=" * 70)
        return overall_status

    def _print_conversion_report(self, log):
        """แสดงรายงานการแปลงข้อมูล"""
        if log['successful_conversions']:
            # แสดงเฉพาะจำนวนคอลัมน์ที่แปลงสำเร็จ ไม่แสดงรายชื่อทั้งหมด
            success_count = len(log['successful_conversions'])
            self.log_callback(f"✅ แปลงข้อมูลสำเร็จ: {success_count} คอลัมน์")
        
        if log['failed_conversions']:
            self.log_callback("\n❌ พบปัญหาการแปลงข้อมูล:")
            for col, details in log['failed_conversions'].items():
                self.log_callback(f"   🔸 คอลัมน์ '{col}':")
                self.log_callback(f"      - ชนิดข้อมูลที่ต้องการ: {details['expected_type']}")
                if 'failed_count' in details:
                    self.log_callback(f"      - จำนวนแถวที่แปลงไม่ได้: {details['failed_count']:,}")
                if 'examples' in details:
                    self.log_callback(f"      - ตัวอย่างข้อมูลที่ผิด: {details['examples']}")
                if 'error' in details:
                    self.log_callback(f"      - ข้อผิดพลาด: {details['error']}")
        
        if log['warnings']:
            self.log_callback(f"\n⚠️  คำเตือน: {', '.join(log['warnings'])}")

    def print_detailed_validation_report(self, df, logic_type):
        """แสดงรายงานการตรวจสอบข้อมูลแบบละเอียด (สำหรับ debug)"""
        self.log_callback("\n" + "="*80)
        self.log_callback("🔍 รายงานการตรวจสอบข้อมูลแบบละเอียด")
        self.log_callback("="*80)
        
        # ข้อมูลพื้นฐาน
        self.log_callback(f"📊 ข้อมูลพื้นฐาน:")
        self.log_callback(f"   • จำนวนแถวทั้งหมด: {len(df):,}")
        self.log_callback(f"   • จำนวนคอลัมน์ทั้งหมด: {len(df.columns)}")
        self.log_callback(f"   • ประเภทไฟล์: {logic_type}")
        
        # ตรวจสอบคอลัมน์แต่ละชนิด
        dtypes = self.get_required_dtypes(logic_type)
        numeric_cols = []
        date_cols = []
        string_cols = []
        
        for col, dtype in dtypes.items():
            if col in df.columns:
                if isinstance(dtype, (Integer, Float, DECIMAL, SmallInteger)):
                    numeric_cols.append(col)
                elif isinstance(dtype, (DATE, DateTime)):
                    date_cols.append(col)
                else:
                    string_cols.append(col)
        
        # รายงานคอลัมน์ตัวเลข
        if numeric_cols:
            self.log_callback(f"\n🔢 คอลัมน์ตัวเลข ({len(numeric_cols)} คอลัมน์):")
            for col in numeric_cols:
                null_count = df[col].isnull().sum()
                null_pct = round((null_count / len(df)) * 100, 1)
                
                # ตรวจสอบข้อมูลที่ไม่ใช่ตัวเลข
                numeric_series = pd.to_numeric(df[col], errors='coerce')
                invalid_count = (numeric_series.isnull() & df[col].notna()).sum()
                
                status = "✅" if invalid_count == 0 else "❌"
                self.log_callback(f"   {status} {col}: ข้อมูลว่าง {null_count:,} ({null_pct}%)" + 
                      (f", ข้อมูลผิด {invalid_count:,}" if invalid_count > 0 else ""))
        
        # รายงานคอลัมน์วันที่
        if date_cols:
            self.log_callback(f"\n📅 คอลัมน์วันที่ ({len(date_cols)} คอลัมน์):")
            for col in date_cols:
                null_count = df[col].isnull().sum()
                null_pct = round((null_count / len(df)) * 100, 1)
                
                # ตรวจสอบรูปแบบวันที่
                def parse_date_safe(val):
                    try:
                        if pd.isna(val) or val == '':
                            return pd.NaT
                        return parser.parse(str(val))
                    except:
                        return pd.NaT
                
                date_series = df[col].apply(parse_date_safe)
                invalid_count = (date_series.isna() & df[col].notna()).sum()
                
                status = "✅" if invalid_count == 0 else "❌"
                self.log_callback(f"   {status} {col}: ข้อมูลว่าง {null_count:,} ({null_pct}%)" + 
                      (f", รูปแบบผิด {invalid_count:,}" if invalid_count > 0 else ""))
        
        # รายงานคอลัมน์ข้อความ
        if string_cols:
            self.log_callback(f"\n📝 คอลัมน์ข้อความ ({len(string_cols)} คอลัมน์):")
            for col in string_cols:
                null_count = df[col].isnull().sum()
                null_pct = round((null_count / len(df)) * 100, 1)
                unique_count = df[col].nunique()
                
                self.log_callback(f"   ✅ {col}: ข้อมูลว่าง {null_count:,} ({null_pct}%), ค่าไม่ซ้ำ {unique_count:,}")
        
        self.log_callback("="*80)

    def truncate_long_strings(self, df, logic_type):
        """ตัดข้อมูล string ที่ยาวเกินกำหนดและแสดงรายงาน"""
        if not logic_type or logic_type not in self.dtype_settings:
            return df
            
        dtypes = self.get_required_dtypes(logic_type)
        truncation_report = {
            'truncated_columns': {},
            'total_truncated': 0
        }
        
        # แสดง log เฉพาะครั้งแรก (ไม่ซ้ำในแต่ละ chunk)
        if not hasattr(self, '_truncation_log_shown'):
            self.log_callback(f"\n✂️ ตรวจสอบและตัดข้อมูล string ที่ยาวเกิน...")
            self._truncation_log_shown = True
        
        for col, dtype in dtypes.items():
            if col not in df.columns:
                continue
                
            # ข้ามคอลัมน์ที่เป็น Text() (NVARCHAR(MAX)) เพราะไม่ต้องตัด
            if isinstance(dtype, Text):
                # แสดง log เฉพาะครั้งแรก
                if not hasattr(self, f'_text_skip_log_{col}'):
                    self.log_callback(f"   ✅ ข้าม '{col}': เป็น Text() (NVARCHAR(MAX)) ไม่จำกัดความยาว")
                    setattr(self, f'_text_skip_log_{col}', True)
                continue
                
            if isinstance(dtype, NVARCHAR):
                max_length = dtype.length if hasattr(dtype, 'length') else 255
                
                # หาข้อมูลที่ยาวเกินกำหนด
                string_series = df[col].astype(str)
                too_long_mask = string_series.str.len() > max_length
                too_long_count = too_long_mask.sum()
                
                if too_long_count > 0:
                    # เก็บตัวอย่างก่อนตัด
                    original_examples = string_series.loc[too_long_mask].str[:100].head(3).tolist()
                    max_original_length = string_series.str.len().max()
                    
                    # แก้ไขปัญหา Categorical: สร้าง series ใหม่แทนการใช้ loc assignment
                    new_series = df[col].copy()
                    if new_series.dtype.name == 'category':
                        # แปลง Categorical เป็น object ก่อน
                        new_series = new_series.astype('object')
                    
                    # ตัดข้อมูลที่ยาวเกิน
                    new_series.loc[too_long_mask] = string_series.loc[too_long_mask].str[:max_length]
                    df[col] = new_series
                    
                    truncation_report['truncated_columns'][col] = {
                        'max_allowed': max_length,
                        'max_original': max_original_length,
                        'truncated_count': too_long_count,
                        'examples': original_examples
                    }
                    truncation_report['total_truncated'] += too_long_count
                    
                    # แสดง log เฉพาะครั้งแรกสำหรับคอลัมน์นี้
                    if not hasattr(self, f'_truncate_log_{col}'):
                        self.log_callback(f"   ✂️ ตัดข้อมูลคอลัมน์ '{col}': {too_long_count:,} แถว (เหลือ {max_length} ตัวอักษร)")
                        setattr(self, f'_truncate_log_{col}', True)
        
        # แสดงสรุปเฉพาะครั้งสุดท้าย (เมื่อไม่มีข้อมูลที่ต้องตัด)
        if truncation_report['total_truncated'] == 0 and not hasattr(self, '_no_truncation_log_shown'):
            self.log_callback("   ✅ ไม่พบข้อมูล string ที่ยาวเกินกำหนด")
            self._no_truncation_log_shown = True
        elif truncation_report['total_truncated'] > 0 and not hasattr(self, '_truncation_summary_shown'):
            self.log_callback(f"\n⚠️ สรุป: ตัดข้อมูลทั้งหมด {truncation_report['total_truncated']:,} แถว ใน {len(truncation_report['truncated_columns'])} คอลัมน์")
            self.log_callback("   📝 ข้อมูลที่ตัดจะยังคงอยู่ใน DataFrame แต่จะถูกย่อให้เข้ากับฐานข้อมูล")
            self._truncation_summary_shown = True
            
        return df

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
                    
                    # แก้ไขปัญหา Categorical: สร้าง series ใหม่
                    col_series = df[col].copy()
                    if col_series.dtype.name == 'category':
                        # แปลง Categorical เป็น object ก่อน
                        col_series = col_series.astype('object')
                    
                    # ใช้ vectorized operations แทน regex ทีละแถว
                    # แปลงเป็น string ก่อน
                    col_str = col_series.astype(str)
                    
                    # เอาเฉพาะตัวเลข จุด และเครื่องหมายลบ
                    cleaned = col_str.str.replace(r"[^\d.-]", "", regex=True)
                    
                    # แปลงเป็นตัวเลข
                    df[col] = pd.to_numeric(cleaned, errors='coerce')
                    
            return df
        except Exception as e:
            self.log_callback(f"เกิดข้อผิดพลาดในการ clean ข้อมูลตัวเลข: {e}")
            return df

    def _reset_log_flags(self):
        """รีเซ็ต log flags เพื่อให้แสดง log ใหม่ในไฟล์ถัดไป"""
        # ลบ attributes ที่เกี่ยวข้องกับ log flags
        for attr in dir(self):
            if attr.startswith(('_truncation_log_shown', '_text_skip_log_', '_truncate_log_', 
                               '_no_truncation_log_shown', '_truncation_summary_shown',
                               '_dtype_conversion_log_', '_conversion_report_shown', '_chunk_log_shown')):
                if hasattr(self, attr):
                    delattr(self, attr)

    def read_excel_file(self, file_path, logic_type):
        """อ่านไฟล์ Excel หรือ CSV ตามประเภทที่กำหนด พร้อมรายงานการตรวจสอบละเอียด"""
        try:
            # รีเซ็ต log flags สำหรับไฟล์ใหม่
            self._reset_log_flags()
            
            # ใช้ Performance Optimizer สำหรับการอ่านไฟล์
            from performance_optimizations import PerformanceOptimizer
            
            optimizer = PerformanceOptimizer(self.log_callback)
            
            # ตรวจสอบประเภทไฟล์
            file_type = 'csv' if file_path.lower().endswith('.csv') else 'excel'
            
            # อ่านไฟล์ด้วย Performance Optimizer
            success, df = optimizer.read_large_file_chunked(file_path, file_type)
            if not success:
                return False, "ไม่สามารถอ่านไฟล์ได้"
            
            # Apply column mapping
            col_map = self.get_column_name_mapping(logic_type)
            if col_map:
                self.log_callback(f"�� ปรับชื่อคอลัมน์ตาม mapping ({len(col_map)} คอลัมน์)")
                df.rename(columns=col_map, inplace=True)
            
            # ปรับปรุง memory usage
            df = optimizer.optimize_memory_usage(df)
            
            # สร้างรายงานก่อนประมวลผล
            validation_passed = self.generate_pre_processing_report(df, logic_type)
            
            if not validation_passed:
                self.log_callback("\n⚠️  พบปัญหาในการตรวจสอบข้อมูล - ดำเนินการประมวลผลต่อไป แต่อาจมีข้อผิดพลาด")
            
            # Clean และ apply dtypes แบบ chunked
            self.log_callback(f"\n🧹 ทำความสะอาดข้อมูลตัวเลข...")
            df = self._process_dataframe_in_chunks(df, self.clean_numeric_columns, logic_type)
            
            # ตัดข้อมูล string ที่ยาวเกิน
            df = self._process_dataframe_in_chunks(df, self.truncate_long_strings, logic_type)
            
            self.log_callback(f"\n🔄 แปลงประเภทข้อมูล...")
            df = self._process_dataframe_in_chunks(df, self.apply_dtypes, logic_type)
            
            # ทำความสะอาด memory
            optimizer.cleanup_memory()
            
            self.log_callback(f"\n🎉 ประมวลผลไฟล์เสร็จสิ้น")
            return True, df
            
        except Exception as e:
            error_msg = f"❌ เกิดข้อผิดพลาดขณะอ่านไฟล์: {e}"
            self.log_callback(error_msg)
            return False, error_msg
    
    def _process_dataframe_in_chunks(self, df, process_func, logic_type, chunk_size=5000):
        """ประมวลผล DataFrame แบบ chunk เพื่อประหยัด memory"""
        try:
            if len(df) <= chunk_size:
                return process_func(df, logic_type)
            
            # แสดง log เฉพาะครั้งแรก
            if not hasattr(self, '_chunk_log_shown'):
                self.log_callback(f"📊 ประมวลผลแบบ chunk ({chunk_size:,} แถวต่อ chunk)")
                self._chunk_log_shown = True
                
            chunks = []
            total_chunks = (len(df) + chunk_size - 1) // chunk_size
            
            for i in range(0, len(df), chunk_size):
                chunk = df.iloc[i:i+chunk_size].copy()
                processed_chunk = process_func(chunk, logic_type)
                chunks.append(processed_chunk)
                
                chunk_num = (i // chunk_size) + 1
                
                # แสดง progress เฉพาะบางครั้ง (ทุก 5 chunks หรือ chunk สุดท้าย)
                if chunk_num % 5 == 0 or chunk_num == total_chunks:
                    self.log_callback(f"📊 ประมวลผล chunk {chunk_num}/{total_chunks}")
                
                # ปล่อย memory ทุก 5 chunks
                if chunk_num % 5 == 0:
                    import gc
                    gc.collect()
            
            # รวม chunks
            result = pd.concat(chunks, ignore_index=True)
            del chunks  # ปล่อย memory
            import gc
            gc.collect()
            
            return result
            
        except Exception as e:
            self.log_callback(f"❌ เกิดข้อผิดพลาดในการประมวลผลแบบ chunk: {e}")
            return df

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
        
        # ตรวจสอบ string truncation error
        if 'String or binary data would be truncated' in msg or 'would be truncated' in msg:
            # ดึงชื่อตารางและคอลัมน์จาก error message
            import re
            table_match = re.search(r"table '([^']+)'", msg)
            column_match = re.search(r"column '([^']+)'", msg)
            
            table_name = table_match.group(1) if table_match else "ไม่ทราบ"
            column_name = column_match.group(1) if column_match else "ไม่ทราบ"
            
            result.append(f"❌ ข้อมูลในคอลัมน์ '{column_name}' ยาวเกินกว่าที่ฐานข้อมูลรองรับ")
            result.append(f"📋 ตาราง: {table_name}")
            
            # หาข้อมูลที่ยาวเกินใน DataFrame
            if column_name in df.columns and column_name in dtypes:
                expected_dtype = dtypes[column_name]
                if isinstance(expected_dtype, NVARCHAR):
                    max_length = expected_dtype.length if hasattr(expected_dtype, 'length') else 255
                    string_series = df[column_name].astype(str)
                    actual_max = string_series.str.len().max()
                    too_long_count = (string_series.str.len() > max_length).sum()
                    
                    result.append(f"📏 ความยาวที่อนุญาต: {max_length} ตัวอักษร")
                    result.append(f"📏 ความยาวสูงสุดในข้อมูล: {actual_max} ตัวอักษร")
                    result.append(f"📊 จำนวนแถวที่ยาวเกิน: {too_long_count:,} แถว")
                    
                    # แสดงตัวอย่างข้อมูลที่ยาวเกิน
                    too_long_mask = string_series.str.len() > max_length
                    if too_long_mask.any():
                        example = string_series.loc[too_long_mask].iloc[0]
                        result.append(f"📝 ตัวอย่างข้อมูลที่ยาวเกิน: '{example[:100]}...'")
                elif isinstance(expected_dtype, Text):
                    # คอลัมน์ที่เป็น Text() (NVARCHAR(MAX)) ไม่ควรมีปัญหาความยาว
                    string_series = df[column_name].astype(str)
                    actual_max = string_series.str.len().max()
                    result.append(f"⚠️ คอลัมน์นี้ถูกตั้งค่าเป็น NVARCHAR(MAX) แล้ว แต่ยังมี error")
                    result.append(f"📏 ความยาวสูงสุดในข้อมูล: {actual_max} ตัวอักษร")
                    result.append(f"🔧 แนะนำ: ตรวจสอบการตั้งค่าฐานข้อมูลหรือ data type mapping")
                        
            result.append("💡 แนะนำ: เพิ่มขนาดคอลัมน์ในฐานข้อมูล หรือตัดข้อมูลให้สั้นลง")
            
        elif 'Error converting data type nvarchar to numeric' in msg:
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
            result.append("❌ เกิดข้อผิดพลาดขณะอัปโหลดข้อมูล")
            # แสดง error message บางส่วน
            if len(msg) > 200:
                result.append(f"📋 รายละเอียด: {msg[:200]}...")
            else:
                result.append(f"📋 รายละเอียด: {msg}")
            
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
        
        # แก้ไขคอลัมน์ที่เป็น Text() ให้เป็น NVARCHAR(MAX) ใน SQL Server
        with engine.begin() as conn:
            for col_name, dtype in dtypes.items():
                if isinstance(dtype, Text):
                    # เปลี่ยนคอลัมน์จาก TEXT เป็น NVARCHAR(MAX)
                    alter_sql = f"ALTER TABLE {table_name} ALTER COLUMN [{col_name}] NVARCHAR(MAX)"
                    try:
                        conn.execute(alter_sql)
                        print(f"✅ แก้ไขคอลัมน์ {col_name} เป็น NVARCHAR(MAX)")
                    except Exception as e:
                        print(f"⚠️ ไม่สามารถแก้ไขคอลัมน์ {col_name}: {e}")

    def _schema_mismatch(self, sql_schema, dtypes):
        """ตรวจสอบว่า schema ตรงกันหรือไม่"""
        for col, dtype in dtypes.items():
            if col not in sql_schema:
                return True
            
            # ตรวจสอบ special case สำหรับ Text() และ NVARCHAR(MAX)
            if isinstance(dtype, Text):
                # Text() ควรตรงกับ NVARCHAR(MAX) หรือ TEXT
                sql_type = sql_schema[col]
                if not ('NVARCHAR(MAX)' in sql_type or 'TEXT' in sql_type):
                    return True
            else:
                # ตรวจสอบแบบปกติ
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
                    self.log_callback(f"ไม่สามารถย้ายไฟล์ {file_path}: {str(e)}")
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