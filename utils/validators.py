"""
Validator functions for PIPELINE_SQLSERVER

Functions for validating various types of data and configurations
"""

import os
import re
import json
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional

from constants import (
    FileConstants, 
    RegexPatterns, 
    DatabaseConstants,
    ErrorMessages
)


def is_valid_sql_identifier(name: str) -> bool:
    """
    ตรวจสอบว่าชื่อเป็น SQL identifier ที่ถูกต้องหรือไม่
    
    Args:
        name: ชื่อที่ต้องการตรวจสอบ
        
    Returns:
        bool: ถูกต้องหรือไม่
    """
    if not name or not isinstance(name, str):
        return False
        
    return bool(re.match(RegexPatterns.SQL_IDENTIFIER, name))


def is_supported_file_type(file_path: str) -> bool:
    """
    ตรวจสอบว่าเป็นไฟล์ที่รองรับหรือไม่
    
    Args:
        file_path: ที่อยู่ไฟล์
        
    Returns:
        bool: รองรับหรือไม่
    """
    if not file_path:
        return False
        
    extension = os.path.splitext(file_path.lower())[1]
    return extension in FileConstants.SUPPORTED_EXTENSIONS


def validate_dataframe(df: pd.DataFrame, 
                      required_columns: Optional[List[str]] = None) -> Tuple[bool, str]:
    """
    ตรวจสอบความถูกต้องของ DataFrame
    
    Args:
        df: DataFrame ที่ต้องการตรวจสอบ
        required_columns: รายการคอลัมน์ที่จำเป็น
        
    Returns:
        Tuple[bool, str]: (ถูกต้องหรือไม่, ข้อความ)
    """
    try:
        # ตรวจสอบว่า DataFrame ไม่เป็น None
        if df is None:
            return False, "DataFrame เป็น None"
            
        # ตรวจสอบว่ามีข้อมูล
        if df.empty:
            return False, ErrorMessages.EMPTY_DATA
            
        # ตรวจสอบคอลัมน์ที่จำเป็น
        if required_columns:
            missing_columns = set(required_columns) - set(df.columns)
            if missing_columns:
                return False, f"{ErrorMessages.MISSING_COLUMNS}: {list(missing_columns)}"
                
        # ตรวจสอบว่ามีแถวข้อมูล
        if len(df) == 0:
            return False, "ไม่มีข้อมูลในแถว"
            
        return True, "DataFrame ถูกต้อง"
        
    except Exception as e:
        return False, f"เกิดข้อผิดพลาดในการตรวจสอบ DataFrame: {str(e)}"


def validate_database_config(config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    ตรวจสอบการตั้งค่าฐานข้อมูล
    
    Args:
        config: การตั้งค่าฐานข้อมูล
        
    Returns:
        Tuple[bool, str]: (ถูกต้องหรือไม่, ข้อความ)
    """
    try:
        required_keys = ['server', 'database', 'auth_type']
        
        # ตรวจสอบ key ที่จำเป็น
        for key in required_keys:
            if key not in config:
                return False, f"ไม่พบการตั้งค่า: {key}"
                
        # ตรวจสอบ server
        if not config.get('server'):
            return False, "ไม่ได้ระบุ server"
            
        # ตรวจสอบ database
        if not config.get('database'):
            return False, "ไม่ได้ระบุ database"
            
        # ตรวจสอบ auth_type
        auth_type = config.get('auth_type')
        if auth_type not in [DatabaseConstants.AUTH_WINDOWS, DatabaseConstants.AUTH_SQL]:
            return False, f"ประเภทการยืนยันตัวตนไม่ถูกต้อง: {auth_type}"
            
        # ถ้าใช้ SQL Authentication ต้องมี username และ password
        if auth_type == DatabaseConstants.AUTH_SQL:
            if not config.get('username'):
                return False, "ไม่ได้ระบุ username สำหรับ SQL Authentication"
            if not config.get('password'):
                return False, "ไม่ได้ระบุ password สำหรับ SQL Authentication"
                
        return True, "การตั้งค่าฐานข้อมูลถูกต้อง"
        
    except Exception as e:
        return False, f"เกิดข้อผิดพลาดในการตรวจสอบการตั้งค่า: {str(e)}"


def validate_file_path(file_path: str) -> bool:
    """
    ตรวจสอบว่า file path ถูกต้องและมีไฟล์จริง
    
    Args:
        file_path: เส้นทางไฟล์
        
    Returns:
        bool: ถูกต้องหรือไม่
    """
    if not file_path:
        return False
    
    try:
        return os.path.exists(file_path) and os.path.isfile(file_path)
    except Exception:
        return False


def validate_database_connection(engine) -> bool:
    """
    ตรวจสอบการเชื่อมต่อฐานข้อมูล
    
    Args:
        engine: SQLAlchemy engine
        
    Returns:
        bool: เชื่อมต่อได้หรือไม่
    """
    if not engine:
        return False
    
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False


def _is_supported_dtype(dtype_str: str) -> bool:
    """
    ตรวจสอบว่าชนิดข้อมูลรองรับหรือไม่ (internal function)
    
    Args:
        dtype_str: ชนิดข้อมูลในรูปแบบ string
        
    Returns:
        bool: รองรับหรือไม่
    """
    if not dtype_str:
        return False
        
    dtype_upper = dtype_str.upper()
    
    # ตรวจสอบ exact match
    if dtype_upper in [dt.upper() for dt in DatabaseConstants.SUPPORTED_DTYPES]:
        return True
        
    # ตรวจสอบ pattern match สำหรับ NVARCHAR, DECIMAL etc.
    supported_patterns = [
        r'^NVARCHAR\(\d+\)$',
        r'^VARCHAR\(\d+\)$', 
        r'^DECIMAL\(\d+,\d+\)$',
        r'^CHAR\(\d+\)$'
    ]
    
    for pattern in supported_patterns:
        if re.match(pattern, dtype_upper):
            return True
            
    return False


def validate_json_config(config_data: Dict[str, Any], schema: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate JSON configuration against a schema
    
    Args:
        config_data: Configuration data to validate
        schema: Schema definition with required fields and types
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    try:
        # Check required fields
        required_fields = schema.get('required', [])
        for field in required_fields:
            if field not in config_data:
                return False, f"Missing required field: {field}"
        
        # Check field types
        field_types = schema.get('types', {})
        for field, expected_type in field_types.items():
            if field in config_data:
                value = config_data[field]
                if expected_type == 'string' and not isinstance(value, str):
                    return False, f"Field '{field}' must be a string"
                elif expected_type == 'integer' and not isinstance(value, int):
                    return False, f"Field '{field}' must be an integer"
                elif expected_type == 'boolean' and not isinstance(value, bool):
                    return False, f"Field '{field}' must be a boolean"
                elif expected_type == 'dict' and not isinstance(value, dict):
                    return False, f"Field '{field}' must be a dictionary"
                elif expected_type == 'list' and not isinstance(value, list):
                    return False, f"Field '{field}' must be a list"
        
        # Check field values
        field_values = schema.get('values', {})
        for field, allowed_values in field_values.items():
            if field in config_data:
                value = config_data[field]
                if value not in allowed_values:
                    return False, f"Field '{field}' must be one of: {allowed_values}"
        
        return True, ""
        
    except (TypeError, ValueError) as e:
        return False, f"Validation error: {str(e)}"


def validate_config_file(file_path: str, schema: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate a JSON configuration file against a schema
    
    Args:
        file_path: Path to the configuration file
        schema: Schema definition
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            return False, f"Configuration file not found: {file_path}"
        
        # Load and parse JSON
        with open(file_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        # Validate against schema
        return validate_json_config(config_data, schema)
        
    except (FileNotFoundError, PermissionError) as e:
        return False, f"File access error: {str(e)}"
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON format: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


