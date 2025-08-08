"""
Data Processor Service สำหรับ PIPELINE_SQLSERVER

จัดการการประมวลผล ตรวจสอบ และแปลงข้อมูล
แยกออกมาจาก FileService เพื่อให้แต่ละ service มีหน้าที่ชัดเจน
"""

import json
import os
import re
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from dateutil import parser
from sqlalchemy.types import (
    DECIMAL, DATE, Boolean, DateTime, Float, Integer,
    NVARCHAR, SmallInteger, Text
)

from constants import PathConstants


class DataProcessorService:
    """
    บริการประมวลผลข้อมูล
    
    รับผิดชอบ:
    - การตรวจสอบข้อมูล (validation)
    - การแปลงประเภทข้อมูล (data type conversion)
    - การทำความสะอาดข้อมูล (data cleaning)
    - การตัดข้อมูลที่ยาวเกิน (string truncation)
    """
    
    def __init__(self, log_callback: Optional[callable] = None) -> None:
        """
        เริ่มต้น DataProcessorService
        
        Args:
            log_callback (Optional[callable]): ฟังก์ชันสำหรับแสดง log
        """
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

    def get_required_dtypes(self, file_type):
        """รับ dtype ของคอลัมน์ {new_col: dtype} ตามประเภทไฟล์ (ใช้ cache)"""
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
                setattr(self, f'_dtype_conversion_log_{file_type}', True)
            
            # ประมวลผลแต่ละคอลัมน์
            for col, dtype_str in self.dtype_settings[file_type].items():
                if col.startswith('_') or col not in df.columns:
                    continue
                    
                dtype_str = dtype_str.upper()
                original_null_count = df[col].isnull().sum()
                
                try:
                    if 'DATE' in dtype_str:
                        # ใช้การแปลงข้อมูลวันที่ที่เข้มงวดและปลอดภัยขึ้น
                        def parse_datetime_safe_strict(val):
                            try:
                                if pd.isna(val) or val == '' or str(val).lower() in ['nan', 'null', 'none']:
                                    return pd.NaT
                                
                                # ลองแปลงด้วย pandas
                                converted_date = parser.parse(str(val), dayfirst=dayfirst)
                                
                                # ตรวจสอบช่วงปีที่ SQL Server รองรับ
                                if converted_date.year < 1753 or converted_date.year > 9999:
                                    return pd.NaT
                                
                                # ตรวจสอบปีที่สมเหตุสมผล (1900-2100)
                                if converted_date.year < 1900 or converted_date.year > 2100:
                                    return pd.NaT
                                
                                return converted_date
                                
                            except (ValueError, OverflowError, TypeError):
                                return pd.NaT
                        
                        df[col] = df[col].astype(str).apply(parse_datetime_safe_strict)
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
                                'error_type': 'Invalid date format or out of SQL Server range'
                            }
                            
                            # เพิ่มความเข้มงวด: ถ้ามีข้อมูลวันที่ผิดมากกว่า 5% ให้เตือน
                            if failed_count > len(df) * 0.05:
                                conversion_log['warnings'].append(f"คอลัมน์ '{col}' มีข้อมูลวันที่ผิดมากกว่า 5% - ควรเปลี่ยนเป็น STRING")
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
                setattr(self, f'_conversion_report_shown_{file_type}', True)
                
            return df
            
        except Exception as e:
            self.log_callback(f"❌ เกิดข้อผิดพลาดในการแปลงประเภทข้อมูล: {e}")
            return df

    def clean_and_validate_datetime_columns(self, df, file_type):
        """ทำความสะอาดและตรวจสอบข้อมูลคอลัมน์วันที่"""
        if not file_type or file_type not in self.dtype_settings:
            return df
            
        try:
            for col, dtype_str in self.dtype_settings[file_type].items():
                if col not in df.columns:
                    continue
                    
                dtype_str_upper = str(dtype_str).upper()
                if 'DATE' in dtype_str_upper:
                    
                    # ตรวจสอบและทำความสะอาดข้อมูลวันที่
                    original_count = len(df)
                    problematic_values = []
                    
                    def clean_datetime_value(val):
                        try:
                            if pd.isna(val) or val == '' or str(val).lower() in ['nan', 'null', 'none', '0']:
                                return None
                            
                            val_str = str(val).strip()
                            
                            # ตรวจสอบรูปแบบที่ผิดปกติ
                            if len(val_str) < 4:  # วันที่ต้องมีอย่างน้อย 4 ตัวอักษร
                                problematic_values.append(val_str)
                                return None
                                
                            # ตรวจสอบปีที่เป็นไปไม่ได้
                            if val_str.isdigit() and len(val_str) == 4:
                                year = int(val_str)
                                if year < 1753 or year > 9999:
                                    problematic_values.append(val_str)
                                    return None
                            
                            # ลองแปลงเป็นวันที่
                            try:
                                converted_date = pd.to_datetime(val_str, errors='raise')
                                
                                # ตรวจสอบช่วงปีที่ SQL Server รองรับ
                                if converted_date.year < 1753 or converted_date.year > 9999:
                                    problematic_values.append(val_str)
                                    return None
                                    
                                # ตรวจสอบปีที่สมเหตุสมผล
                                if converted_date.year < 1900 or converted_date.year > 2100:
                                    problematic_values.append(val_str)
                                    return None
                                
                                return val_str
                                
                            except (ValueError, OverflowError, TypeError):
                                problematic_values.append(val_str)
                                return None
                                
                        except Exception:
                            return None
                    
                    # ทำความสะอาดข้อมูล
                    df[col] = df[col].apply(clean_datetime_value)
                    
                    # รายงานผล
                    cleaned_count = df[col].isnull().sum()
                    if cleaned_count > 0:
                        problem_percentage = (cleaned_count / original_count) * 100
                        unique_problems = list(set(problematic_values[:5]))  # แสดงตัวอย่าง 5 ค่า
                        
                        if not hasattr(self, f'_datetime_clean_log_{col}'):
                            self.log_callback(f"   🧹 ทำความสะอาด '{col}': ลบข้อมูลวันที่ที่ไม่ถูกต้อง {cleaned_count:,} แถว ({problem_percentage:.1f}%)")
                            if unique_problems:
                                self.log_callback(f"      ตัวอย่างข้อมูลที่ลบ: {unique_problems}")
                            setattr(self, f'_datetime_clean_log_{col}', True)
                        
                        # ถ้าข้อมูลผิดมากกว่า 30% ให้แนะนำเปลี่ยนเป็น string
                        if problem_percentage > 30:
                            self.log_callback(f"   ⚠️ คำแนะนำ: คอลัมน์ '{col}' มีข้อมูลวันที่ผิดมาก ({problem_percentage:.1f}%) - ควรเปลี่ยนเป็น NVARCHAR")
                    
            return df
        except Exception as e:
            self.log_callback(f"เกิดข้อผิดพลาดในการ clean ข้อมูลวันที่: {e}")
            return df

    def clean_numeric_columns(self, df, file_type):
        """ทำความสะอาดข้อมูลคอลัมน์ตัวเลข"""
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

    def _reset_log_flags(self):
        """รีเซ็ต log flags เพื่อให้แสดง log ใหม่ในไฟล์ถัดไป"""
        # ลบ attributes ที่เกี่ยวข้องกับ log flags
        for attr in dir(self):
            if attr.startswith(('_truncation_log_shown', '_text_skip_log_', '_truncate_log_', 
                               '_no_truncation_log_shown', '_truncation_summary_shown',
                               '_dtype_conversion_log_', '_conversion_report_shown', '_chunk_log_shown',
                               '_datetime_clean_log_')):
                if hasattr(self, attr):
                    delattr(self, attr)

    def auto_detect_and_fix_data_types(self, df, logic_type):
        """
        ตรวจสอบชนิดข้อมูลอัตโนมัติ แปลงให้เข้ากับ SQL และอัพเดท JSON config
        
        Args:
            df: DataFrame ที่ต้องการประมวลผล
            logic_type: ประเภทไฟล์
            
        Returns:
            Tuple[DataFrame, bool, Dict]: (DataFrame ที่แก้ไขแล้ว, มีการเปลี่ยนแปลง, รายละเอียดการเปลี่ยนแปลง)
        """
        changes_made = False
        change_details = {
            'modified_columns': {},
            'auto_conversions': {},
            'warnings': []
        }
        
        if not logic_type or logic_type not in self.dtype_settings:
            return df, changes_made, change_details
            
        self.log_callback(f"\n🤖 เริ่มการตรวจสอบและแก้ไขชนิดข้อมูลอัตโนมัติ...")
        
        for col, expected_dtype_str in self.dtype_settings[logic_type].items():
            if col.startswith('_') or col not in df.columns:
                continue
                
            expected_dtype_str = expected_dtype_str.upper()
            original_dtype = expected_dtype_str
            
            try:
                # ตรวจสอบข้อมูลในคอลัมน์
                sample_data = df[col].dropna().head(100)  # ใช้ sample แทนการตรวจทั้งหมด
                
                if len(sample_data) == 0:
                    continue
                
                # วิเคราะห์ข้อมูลและแนะนำชนิดที่เหมาะสม
                suggested_dtype = self._analyze_and_suggest_data_type(sample_data, expected_dtype_str, col)
                
                if suggested_dtype != expected_dtype_str:
                    # อัพเดท dtype settings
                    self.dtype_settings[logic_type][col] = suggested_dtype
                    changes_made = True
                    
                    change_details['modified_columns'][col] = {
                        'original': original_dtype,
                        'new': suggested_dtype,
                        'reason': self._get_change_reason(sample_data, original_dtype, suggested_dtype)
                    }
                    
                    self.log_callback(f"   🔄 แก้ไข '{col}': {original_dtype} → {suggested_dtype}")
                    
            except Exception as e:
                change_details['warnings'].append(f"ไม่สามารถวิเคราะห์คอลัมน์ '{col}': {e}")
                
        if changes_made:
            # บันทึกการตั้งค่าใหม่
            self._save_updated_dtype_settings(logic_type)
            self.log_callback(f"\n💾 บันทึกการตั้งค่าใหม่สำเร็จ")
            
        return df, changes_made, change_details

    def _analyze_and_suggest_data_type(self, sample_data, expected_dtype, col_name):
        """วิเคราะห์ข้อมูลและแนะนำชนิดข้อมูลที่เหมาะสม"""
        try:
            # ตรวจสอบข้อมูลตัวเลข
            if expected_dtype in ['INT', 'BIGINT', 'SMALLINT', 'FLOAT'] or expected_dtype.startswith('DECIMAL'):
                numeric_data = pd.to_numeric(sample_data, errors='coerce')
                invalid_count = numeric_data.isna().sum()
                
                # ถ้าข้อมูลไม่ใช่ตัวเลขมากกว่า 20% ให้เปลี่ยนเป็น string
                if invalid_count > len(sample_data) * 0.2:
                    max_length = sample_data.astype(str).str.len().max()
                    return self._suggest_string_type(max_length)
                    
                # ถ้าเป็นตัวเลขและมีทศนิยม แต่กำหนดเป็น INT ให้เปลี่ยนเป็น DECIMAL
                if expected_dtype in ['INT', 'BIGINT', 'SMALLINT']:
                    valid_numeric = numeric_data.dropna()
                    if len(valid_numeric) > 0 and (valid_numeric % 1 != 0).any():
                        return 'DECIMAL(18,4)'
                        
            # ตรวจสอบข้อมูลวันที่ - เพิ่มการตรวจสอบที่เข้มงวดขึ้น
            elif 'DATE' in expected_dtype:
                valid_dates = 0
                total_non_null = len(sample_data)
                
                for value in sample_data:
                    if pd.isna(value) or value == '':
                        continue
                        
                    try:
                        # ลองแปลงด้วย pandas
                        converted_date = pd.to_datetime(str(value), errors='raise')
                        
                        # ตรวจสอบว่าวันที่อยู่ในช่วงที่ SQL Server รองรับ (1753-01-01 ถึง 9999-12-31)
                        if converted_date.year < 1753 or converted_date.year > 9999:
                            continue
                            
                        # ตรวจสอบรูปแบบวันที่ที่แปลกประหลาด
                        if converted_date.year < 1900 or converted_date.year > 2100:
                            continue
                            
                        valid_dates += 1
                        
                    except (ValueError, pd._libs.tslibs.parsing.DateParseError, OverflowError):
                        continue
                
                # ถ้าข้อมูลวันที่ที่ถูกต้องน้อยกว่า 70% ให้เปลี่ยนเป็น string
                valid_percentage = valid_dates / total_non_null if total_non_null > 0 else 0
                if valid_percentage < 0.7:
                    max_length = sample_data.astype(str).str.len().max()
                    suggested_type = self._suggest_string_type(max_length)
                    self.log_callback(f"   ⚠️ คอลัมน์ '{col_name}': วันที่ถูกต้องเพียง {valid_percentage:.1%} → เปลี่ยนเป็น {suggested_type}")
                    return suggested_type
                    
            # ตรวจสอบข้อมูล string
            elif expected_dtype.startswith('NVARCHAR'):
                max_length = sample_data.astype(str).str.len().max()
                current_limit = self._extract_varchar_length(expected_dtype)
                
                # ถ้าข้อมูลยาวเกิน 120% ของขนาดที่กำหนด ให้ขยายขนาด
                if max_length > current_limit * 1.2:
                    return self._suggest_string_type(max_length)
                    
            return expected_dtype
            
        except Exception as e:
            self.log_callback(f"   ⚠️ ไม่สามารถวิเคราะห์คอลัมน์ '{col_name}': {e}")
            return expected_dtype

    def _suggest_string_type(self, max_length):
        """แนะนำชนิด string ที่เหมาะสมตามความยาว"""
        if max_length <= 100:
            return 'NVARCHAR(255)'
        elif max_length <= 500:
            return 'NVARCHAR(1000)'
        elif max_length <= 2000:
            return 'NVARCHAR(4000)'
        else:
            return 'NVARCHAR(MAX)'

    def _extract_varchar_length(self, dtype_str):
        """ดึงความยาวจาก NVARCHAR(n)"""
        try:
            if 'MAX' in dtype_str:
                return 999999
            length = int(dtype_str.split('(')[1].split(')')[0])
            return length
        except:
            return 255

    def _get_change_reason(self, sample_data, original_dtype, new_dtype):
        """สร้างข้อความอธิบายเหตุผลของการเปลี่ยนแปลง"""
        if original_dtype in ['INT', 'BIGINT', 'SMALLINT'] and 'DECIMAL' in new_dtype:
            return "พบข้อมูลทศนิยม"
        elif 'DATE' in original_dtype and 'NVARCHAR' in new_dtype:
            return "พบข้อมูลที่ไม่ใช่วันที่"
        elif original_dtype in ['INT', 'FLOAT'] and 'NVARCHAR' in new_dtype:
            return "พบข้อมูลที่ไม่ใช่ตัวเลข"
        elif 'NVARCHAR' in original_dtype and 'NVARCHAR' in new_dtype:
            return "ข้อมูลยาวเกินขนาดที่กำหนด"
        else:
            return "ปรับปรุงความเข้ากันได้"

    def _save_updated_dtype_settings(self, logic_type):
        """บันทึกการตั้งค่า dtype ที่อัพเดทแล้ว"""
        try:
            dtype_file = PathConstants.DTYPE_SETTINGS_FILE
            with open(dtype_file, 'w', encoding='utf-8') as f:
                json.dump(self.dtype_settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_callback(f"❌ ไม่สามารถบันทึกการตั้งค่าได้: {e}")

    def process_with_auto_fix(self, df, logic_type):
        """
        ประมวลผลข้อมูลพร้อมระบบแก้ไขอัตโนมัติ
        
        Args:
            df: DataFrame ที่ต้องการประมวลผล  
            logic_type: ประเภทไฟล์
            
        Returns:
            Tuple[DataFrame, Dict]: (DataFrame ที่ประมวลผลแล้ว, รายงานการแก้ไข)
        """
        processing_report = {
            'auto_fixes_applied': False,
            'changes_made': {},
            'processing_steps': []
        }
        
        try:
            # ขั้นตอนที่ 1: ตรวจสอบและแก้ไขชนิดข้อมูลอัตโนมัติ
            self.log_callback(f"🔍 ขั้นตอนที่ 1: ตรวจสอบความเข้ากันได้ของชนิดข้อมูล")
            df, changes_made, change_details = self.auto_detect_and_fix_data_types(df, logic_type)
            
            if changes_made:
                processing_report['auto_fixes_applied'] = True
                processing_report['changes_made'] = change_details
                processing_report['processing_steps'].append("อัพเดทชนิดข้อมูลอัตโนมัติ")
                
                # แจ้งเตือนผู้ใช้
                self._notify_user_about_changes(change_details)
            
            # ขั้นตอนที่ 2: ประมวลผลข้อมูลแบบปกติ
            self.log_callback(f"🔄 ขั้นตอนที่ 2: ประมวลผลข้อมูล")
            
            # โหลดการตั้งค่าใหม่ (หลังจากอัพเดท)
            self.load_settings()
            
            # ทำความสะอาดและแปลงข้อมูล
            df = self.process_dataframe_in_chunks(df, self.clean_numeric_columns, logic_type)
            df = self.process_dataframe_in_chunks(df, self.clean_and_validate_datetime_columns, logic_type)
            df = self.process_dataframe_in_chunks(df, self.truncate_long_strings, logic_type)
            df = self.process_dataframe_in_chunks(df, self.apply_dtypes, logic_type)
            
            processing_report['processing_steps'].extend([
                "ทำความสะอาดข้อมูลตัวเลข",
                "ทำความสะอาดข้อมูลวันที่",
                "ตัดข้อมูล string ที่ยาวเกิน", 
                "แปลงชนิดข้อมูล"
            ])
            
            return df, processing_report
            
        except Exception as e:
            self.log_callback(f"❌ เกิดข้อผิดพลาดในการประมวลผลอัตโนมัติ: {e}")
            return df, processing_report

    def _notify_user_about_changes(self, change_details):
        """แจ้งเตือนผู้ใช้เกี่ยวกับการเปลี่ยนแปลงที่เกิดขึ้น"""
        if not change_details['modified_columns']:
            return
            
        self.log_callback(f"\n🚨 แจ้งเตือน: ระบบได้ปรับปรุงการตั้งค่าชนิดข้อมูลอัตโนมัติ")
        self.log_callback(f"═" * 60)
        
        for col, details in change_details['modified_columns'].items():
            self.log_callback(f"📊 คอลัมน์: {col}")
            self.log_callback(f"   • เดิม: {details['original']}")
            self.log_callback(f"   • ใหม่: {details['new']}")
            self.log_callback(f"   • เหตุผล: {details['reason']}")
            self.log_callback(f"─" * 40)
            
        self.log_callback(f"💡 การตั้งค่าใหม่จะถูกใช้ในการสร้างตารางฐานข้อมูล")
        self.log_callback(f"📁 ไฟล์การตั้งค่า: {PathConstants.DTYPE_SETTINGS_FILE}")
        self.log_callback(f"═" * 60)

    def process_dataframe_in_chunks(self, df, process_func, logic_type, chunk_size=5000):
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
