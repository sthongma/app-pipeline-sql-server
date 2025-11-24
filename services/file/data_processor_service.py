"""
Data Processor Service for PIPELINE_SQLSERVER

Handles data processing, validation, and transformation
Separated from FileService to provide clear responsibilities for each service
"""

import json
import os
import threading
from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd
from dateutil import parser
from sqlalchemy.types import (
    DATE, DateTime, Float, Integer,
    NVARCHAR, Text
)

from constants import PathConstants, ProcessingConstants
from services.settings_manager import settings_manager


class DataProcessorService:
    """
    Data processing service
    
    Responsibilities:
    - Data validation
    - Data type conversion
    - Data cleaning
    - String truncation for oversized data
    """
    
    def __init__(self, log_callback: Optional[callable] = None) -> None:
        """
        Initialize DataProcessorService
        
        Args:
            log_callback (Optional[callable]): Function for displaying logs
        """
        self.log_callback = log_callback if log_callback else print

        # ใช้ SettingsManager singleton แทน local cache
        self._settings_manager = settings_manager

        # Cache สำหรับ dtype conversion (เก็บเฉพาะ conversion results)
        self._settings_cache: Dict[str, Any] = {}
        self._cache_lock = threading.Lock()

        # Instance variables for settings (loaded from settings_manager by FileOrchestrator)
        self._column_settings: Dict[str, Any] = {}
        self._dtype_settings: Dict[str, Any] = {}

    def log_with_time(self, message: str, show_time: bool = True) -> None:
        """
        แสดง log พร้อมเวลา

        Args:
            message (str): ข้อความที่ต้องการแสดง
            show_time (bool): แสดงเวลาหรือไม่ (default: True)
        """
        if show_time:
            timestamp = datetime.now().strftime('%H:%M:%S')
            formatted_message = f"[{timestamp}] {message}"
        else:
            formatted_message = message

        self.log_callback(formatted_message)

    @property
    def column_settings(self) -> Dict[str, Any]:
        """Get column settings"""
        return self._column_settings

    @column_settings.setter
    def column_settings(self, value: Dict[str, Any]) -> None:
        """Set column settings"""
        self._column_settings = value

    @property
    def dtype_settings(self) -> Dict[str, Any]:
        """Get dtype settings"""
        return self._dtype_settings

    @dtype_settings.setter
    def dtype_settings(self, value: Dict[str, Any]) -> None:
        """Set dtype settings"""
        self._dtype_settings = value

    def load_settings(self, force_reload: bool = False) -> None:
        """
        Load column and data type settings (ใช้ SettingsManager)

        Args:
            force_reload: บังคับโหลดใหม่แม้ว่าไฟล์ไม่เปลี่ยน (default: False)
        """
        if force_reload:
            self._settings_manager.reload_all(force=True)
            # Clear dtype conversion cache เมื่อ force reload
            with self._cache_lock:
                self._settings_cache = {k: v for k, v in self._settings_cache.items() if not k.startswith('dtypes_')}

    def _convert_dtype_to_sqlalchemy(self, dtype_str):
        """Convert string dtype to SQLAlchemy type object (cached)"""
        if not isinstance(dtype_str, str):
            return Text()
            
        # Use cache for converted dtypes
        cache_key = str(dtype_str).upper()
        if cache_key in self._settings_cache:
            return self._settings_cache[cache_key]
            
        dtype_str = cache_key
        
        try:
            result = None
            if dtype_str.startswith('NVARCHAR'):
                # Always use Text() for NVARCHAR (maps to NVARCHAR(MAX) in SQL Server)
                result = Text()
            elif dtype_str == 'INT':
                result = Integer()
            elif dtype_str == 'FLOAT':
                result = Float()
            elif dtype_str == 'DATE':
                result = DATE()
            elif dtype_str == 'DATETIME':
                result = DateTime()
            else:
                result = Text()
                
            # Store in cache
            with self._cache_lock:
                self._settings_cache[cache_key] = result
            return result
            
        except Exception:
            result = Text()
            with self._cache_lock:
                self._settings_cache[cache_key] = result
            return result

    def get_required_dtypes(self, file_type):
        """Get column dtypes {new_col: dtype} by file type (cached)"""
        # โหลด settings ล่าสุดก่อนใช้งาน
        self.load_settings()

        if not file_type or file_type not in self.column_settings:
            return {}

        cache_key = f"dtypes_{file_type}"
        if cache_key in self._settings_cache:
            return self._settings_cache[cache_key]
            
        dtypes = {}
        for orig_col, new_col in self.column_settings[file_type].items():
            dtype_str = self.dtype_settings.get(file_type, {}).get(new_col, 'NVARCHAR(255)')
            dtype = self._convert_dtype_to_sqlalchemy(dtype_str)
            dtypes[new_col] = dtype
        # เก็บใน cache
        with self._cache_lock:
            self._settings_cache[cache_key] = dtypes
        return dtypes

    def apply_dtypes(self, df, file_type):
        """
        แปลงประเภทข้อมูลตามการตั้งค่า (เปลี่ยนเป็น SQL-based conversion)
        
        หมายเหตุ: ฟังก์ชันนี้จะถูกย้ายไปในอนาคต เนื่องจากการแปลงข้อมูลจะทำใน staging table แล้วแปลงด้วย SQL
        ตอนนี้เพียงคืนค่า DataFrame เดิม (no-op function)
        """
        if not file_type or file_type not in self.dtype_settings:
            return df
        
        # Return original DataFrame as conversion will be done in SQL
        self.log_with_time(f"🔄 Conversion will be performed in the staging table using SQL")
        return df

    def clean_and_validate_datetime_columns(self, df, file_type):
        """Clean and validate date columns (SQL-based validation)"""
        if not file_type or file_type not in self.dtype_settings:
            return df

        # คืนค่า DataFrame เดิม เนื่องจากการ validation จะทำใน SQL แล้ว
        self.log_with_time(f"🔍 Date validation will be performed in the staging table using SQL")
        return df

    def clean_numeric_columns(self, df, file_type):
        """Clean numeric column data (SQL-based cleaning)"""
        if not file_type or file_type not in self.dtype_settings:
            return df

        # คืนค่า DataFrame เดิม เนื่องจากการ cleaning จะทำใน SQL แล้ว
        self.log_with_time(f"🧹 Numeric cleaning will be performed in the staging table using SQL")
        return df

    def truncate_long_strings(self, df, logic_type):
        """Truncate oversized strings and show report (SQL-based truncation)"""
        if not logic_type or logic_type not in self.dtype_settings:
            return df

        # คืนค่า DataFrame เดิม เนื่องจากการตัดข้อมูลจะทำใน SQL แล้ว
        self.log_with_time(f"✂️ String truncation will be performed in the staging table using SQL")
        return df

    def comprehensive_data_validation(self, df, logic_type):
        """Validate data thoroughly before processing"""
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
                        f"❌ Missing columns: {', '.join(validation_report['missing_columns'])}"
                    )
                
                if validation_report['extra_columns']:
                    validation_report['summary'].append(
                        f"⚠️  Extra columns not defined: {', '.join(validation_report['extra_columns'])}"
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
                        issue_summary = f"❌ Column '{col}': {issues['summary']}"
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
            validation_report['summary'].append(f"❌ An error occurred during validation: {str(e)}")
        
        return validation_report

    def _get_series_row_counts(self, series) -> tuple:
        """Get row counts for validation"""
        total_rows = len(series)
        non_null_rows = series.notna().sum()
        null_rows = total_rows - non_null_rows
        return total_rows, non_null_rows, null_rows

    def _validate_numeric_column(self, series, expected_dtype, total_rows) -> dict:
        """Validate numeric column data"""
        numeric_series = pd.to_numeric(series, errors='coerce')
        invalid_mask = numeric_series.isna() & series.notna()
        invalid_count = invalid_mask.sum()

        if invalid_count == 0:
            return {}

        invalid_examples = series.loc[invalid_mask].unique()[:3]
        problem_rows = series.index[invalid_mask].tolist()[:5]

        return {
            'type': 'numeric_validation_error',
            'expected_type': str(expected_dtype),
            'current_type': str(series.dtype),
            'invalid_count': invalid_count,
            'total_rows': total_rows,
            'percentage': round((invalid_count / total_rows) * 100, 2),
            'examples': [str(x) for x in invalid_examples],
            'problem_rows': [r + 2 for r in problem_rows],  # +2 สำหรับ header
            'summary': f"Found non-numeric data {invalid_count:,} rows ({round((invalid_count / total_rows) * 100, 2)}%)"
        }

    def _get_date_format_setting(self) -> str:
        """Get date format setting from dtype_settings"""
        date_format = 'UK'  # default
        try:
            if logic_type in self.dtype_settings:
                date_format = self.dtype_settings[logic_type].get('_date_format', 'UK')
        except:
            pass
        return date_format

    def _validate_date_column(self, series, expected_dtype, total_rows) -> dict:
        """Validate date/datetime column data"""
        date_format = self._get_date_format_setting()

        def parse_date_safe(val):
            try:
                if pd.isna(val) or val == '':
                    return pd.NaT
                # ใช้การตั้งค่า date format
                dayfirst = (date_format == 'UK')
                return parser.parse(str(val), dayfirst=dayfirst)
            except:
                return pd.NaT

        date_series = series.apply(parse_date_safe)
        invalid_mask = date_series.isna() & series.notna()
        invalid_count = invalid_mask.sum()

        if invalid_count == 0:
            return {}

        invalid_examples = series.loc[invalid_mask].unique()[:3]
        problem_rows = series.index[invalid_mask].tolist()[:5]

        return {
            'type': 'date_validation_error',
            'expected_type': str(expected_dtype),
            'current_type': str(series.dtype),
            'date_format_used': date_format,
            'invalid_count': invalid_count,
            'total_rows': total_rows,
            'percentage': round((invalid_count / total_rows) * 100, 2),
            'examples': [str(x) for x in invalid_examples],
            'problem_rows': [r + 2 for r in problem_rows],  # +2 สำหรับ header
            'summary': f"Found invalid dates {invalid_count:,} rows ({round((invalid_count / total_rows) * 100, 2)}%) using {date_format} format"
        }

    def _validate_string_column(self, series, expected_dtype, total_rows) -> dict:
        """Validate string column length"""
        max_length = expected_dtype.length if hasattr(expected_dtype, 'length') else 255

        # หาข้อมูลที่ยาวเกินกำหนด
        string_series = series.astype(str)
        too_long_mask = string_series.str.len() > max_length
        too_long_count = too_long_mask.sum()

        if too_long_count == 0:
            return {}

        too_long_examples = string_series.loc[too_long_mask].str[:50].unique()[:3]  # แสดงแค่ 50 ตัวอักษรแรก
        actual_lengths = string_series.loc[too_long_mask].str.len().unique()[:5]
        max_actual_length = string_series.str.len().max()
        problem_rows = series.index[too_long_mask].tolist()[:5]

        return {
            'type': 'string_length_error',
            'expected_type': f"NVARCHAR({max_length})",
            'max_allowed_length': max_length,
            'max_actual_length': max_actual_length,
            'too_long_count': too_long_count,
            'total_rows': total_rows,
            'percentage': round((too_long_count / total_rows) * 100, 2),
            'examples': [f"{ex}... (length: {len(string_series.loc[string_series.str.startswith(ex[:10])].iloc[0])})" for ex in too_long_examples],
            'actual_lengths': sorted(actual_lengths, reverse=True),
            'problem_rows': [r + 2 for r in problem_rows],
            'summary': f"Found strings exceeding {max_length} chars: {too_long_count:,} rows ({round((too_long_count / total_rows) * 100, 2)}%) Max length: {max_actual_length}"
        }

    def _check_high_null_percentage(self, null_rows, total_rows, threshold=ProcessingConstants.NULL_WARNING_THRESHOLD) -> dict:
        """Check if null percentage exceeds threshold"""
        if null_rows == 0:
            return {}

        null_percentage = round((null_rows / total_rows) * 100, 2)
        if null_percentage <= threshold:
            return {}

        return {
            'type': 'high_null_percentage',
            'null_count': null_rows,
            'total_rows': total_rows,
            'percentage': null_percentage,
            'summary': f"High number of nulls {null_rows:,} rows ({null_percentage}%)"
        }

    def _validate_column_data_type(self, series, col_name, expected_dtype):
        """Validate specific column data types"""
        issues = {}

        try:
            total_rows, non_null_rows, null_rows = self._get_series_row_counts(series)

            if isinstance(expected_dtype, (Integer, Float)):
                issues = self._validate_numeric_column(series, expected_dtype, total_rows)

            elif isinstance(expected_dtype, (DATE, DateTime)):
                issues = self._validate_date_column(series, expected_dtype, total_rows)

            elif isinstance(expected_dtype, NVARCHAR):
                issues = self._validate_string_column(series, expected_dtype, total_rows)

            elif isinstance(expected_dtype, Text):
                # ข้ามการตรวจสอบความยาวสำหรับ Text() (NVARCHAR(MAX))
                pass

            # เพิ่มข้อมูลเกี่ยวกับ null values ถ้ามี
            if not issues:
                issues = self._check_high_null_percentage(null_rows, total_rows)

        except Exception as e:
            issues = {
                'type': 'validation_error',
                'error': str(e),
                'summary': f"An error occurred during validation: {str(e)}"
            }

        return issues

    def generate_pre_processing_report(self, df, logic_type):
        """Create summary report before data processing"""
        # ตรวจสอบคอลัมน์เบื้องต้นเท่านั้น
        validation_result = self.validate_columns(df, logic_type)
        
        if not validation_result[0]:
            self.log_callback(f"❌ Column issues: {validation_result[1]}")
            return False
        else:
            self.log_callback("✅ Basic column check passed - detailed checks will be performed in staging table using SQL")
            return True

    def check_invalid_numeric(self, df, logic_type):
        """Check non-numeric values in numeric columns with detailed report"""
        validation_report = {
            'has_issues': False,
            'invalid_data': {},
            'summary': []
        }
        
        dtypes = self.get_required_dtypes(logic_type)
        
        for col, dtype in dtypes.items():
            if col not in df.columns:
                continue
                
            if isinstance(dtype, (Integer, Float)):
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
                    
                    summary_msg = (f"❌ Column '{col}' requires numeric data ({str(dtype)}) "
                                 f"but found non-numeric data in {invalid_count:,} rows "
                                 f"({validation_report['invalid_data'][col]['percentage']}%)")
                    validation_report['summary'].append(summary_msg)
                        
        return validation_report

    def validate_columns_by_list(self, column_list, logic_type):
        """
        ตรวจสอบคอลัมน์จาก list แทน DataFrame (สำหรับ preview)
        
        Args:
            column_list: รายการชื่อคอลัมน์
            logic_type: ประเภทไฟล์
            
        Returns:
            tuple: (success, message)
        """
        if not self.column_settings or logic_type not in self.column_settings:
            return False, "No column settings for this file type"
            
        required_cols = set(self.column_settings[logic_type].values())
        file_cols = set(column_list)
        missing_cols = required_cols - file_cols
        
        if missing_cols:
            return False, f"Missing columns: {', '.join(sorted(missing_cols))}"
        
        return True, f"All columns are present for {logic_type}"

    def validate_columns(self, df, logic_type):
        """Validate required columns (dynamic)"""
        if not self.column_settings or logic_type not in self.column_settings:
            return False, "No column settings for this file type"
            
        required_cols = set(self.column_settings[logic_type].values())
        df_cols = set(df.columns)
        missing_cols = required_cols - df_cols
        
        if missing_cols:
            return False, f"Missing columns: {missing_cols}"
        return True, {}

    def _print_conversion_report(self, log):
        """Show data transformation report"""
        if log['successful_conversions']:
            # แสดงเฉพาะจำนวนคอลัมน์ที่แปลงสำเร็จ ไม่แสดงรายชื่อทั้งหมด
            success_count = len(log['successful_conversions'])
            self.log_with_time(f"✅ Successfully converted: {success_count} columns")
        
        if log['failed_conversions']:
            self.log_with_time(f"\n❌ Found issues with data conversion:")
            for col, details in log['failed_conversions'].items():
                self.log_callback(f"   🔸 Column '{col}':")
                self.log_callback(f"      - Expected data type: {details['expected_type']}")
                if 'failed_count' in details:
                    self.log_callback(f"      - Number of rows that failed conversion: {details['failed_count']:,}")
                if 'examples' in details:
                    self.log_callback(f"      - Example data that failed: {details['examples']}")
                if 'error' in details:
                    self.log_callback(f"      - Error: {details['error']}")
        
        if log['warnings']:
            self.log_with_time(f"\n⚠️ Warning: {', '.join(log['warnings'])}")

    def _reset_log_flags(self):
        """Reset log flags to show new logs for next file"""
        # ลบ attributes ที่เกี่ยวข้องกับ log flags
        for attr in dir(self):
            if attr.startswith(('_truncation_log_shown', '_text_skip_log_', '_truncate_log_', 
                               '_no_truncation_log_shown', '_truncation_summary_shown',
                               '_dtype_conversion_log_', '_conversion_report_shown', '_chunk_log_shown',
                               '_datetime_clean_log_')):
                if hasattr(self, attr):
                    delattr(self, attr)


    def _extract_varchar_length(self, dtype_str):
        """Extract length from NVARCHAR(n)"""
        try:
            if 'MAX' in dtype_str:
                return 999999
            length = int(dtype_str.split('(')[1].split(')')[0])
            return length
        except:
            return 255


    # ฟังก์ชัน auto-fix ถูกยกเลิก

    def process_dataframe_in_chunks(self, df, process_func, logic_type, chunk_size=25000):
        """Process DataFrame in chunks to save memory"""
        try:
            if len(df) <= chunk_size:
                return process_func(df, logic_type)
            
            # แสดง log เฉพาะครั้งแรก
            if not hasattr(self, '_chunk_log_shown'):
                self.log_with_time(f"📊 Processing in chunks ({chunk_size:,} rows per chunk)")
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
                    self.log_with_time(f"📊 Processed chunk {chunk_num}/{total_chunks}")
                
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
            self.log_with_time(f"❌ Error processing in chunks: {e}")
            return df
