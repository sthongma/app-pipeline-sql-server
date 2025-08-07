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
                setattr(self, f'_conversion_report_shown_{file_type}', True)
                
            return df
            
        except Exception as e:
            self.log_callback(f"❌ เกิดข้อผิดพลาดในการแปลงประเภทข้อมูล: {e}")
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
                               '_dtype_conversion_log_', '_conversion_report_shown', '_chunk_log_shown')):
                if hasattr(self, attr):
                    delattr(self, attr)

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
