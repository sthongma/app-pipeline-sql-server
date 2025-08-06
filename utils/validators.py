"""
Validator functions สำหรับ PIPELINE_SQLSERVER

ฟังก์ชันสำหรับตรวจสอบความถูกต้องของข้อมูลต่างๆ
"""

import os
import re
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


def validate_column_mapping(mapping: Dict[str, str]) -> Tuple[bool, str]:
    """
    ตรวจสอบการแมปคอลัมน์
    
    Args:
        mapping: การแมปคอลัมน์ {original: new}
        
    Returns:
        Tuple[bool, str]: (ถูกต้องหรือไม่, ข้อความ)
    """
    try:
        if not mapping:
            return False, "ไม่มีการแมปคอลัมน์"
            
        # ตรวจสอบว่าชื่อคอลัมน์ใหม่เป็น SQL identifier ที่ถูกต้อง
        for original, new in mapping.items():
            if not new:
                return False, f"ชื่อคอลัมน์ใหม่สำหรับ '{original}' ไม่ถูกต้อง"
                
            if not is_valid_sql_identifier(new):
                return False, f"ชื่อคอลัมน์ '{new}' ไม่เป็น SQL identifier ที่ถูกต้อง"
                
        # ตรวจสอบว่าไม่มีชื่อคอลัมน์ใหม่ซ้ำ
        new_columns = list(mapping.values())
        if len(new_columns) != len(set(new_columns)):
            duplicates = [col for col in new_columns if new_columns.count(col) > 1]
            return False, f"ชื่อคอลัมน์ใหม่ซ้ำกัน: {set(duplicates)}"
            
        return True, "การแมปคอลัมน์ถูกต้อง"
        
    except Exception as e:
        return False, f"เกิดข้อผิดพลาดในการตรวจสอบการแมปคอลัมน์: {str(e)}"


def validate_dtype_settings(dtype_settings: Dict[str, str]) -> Tuple[bool, str]:
    """
    ตรวจสอบการตั้งค่าชนิดข้อมูล
    
    Args:
        dtype_settings: การตั้งค่าชนิดข้อมูล {column: dtype}
        
    Returns:
        Tuple[bool, str]: (ถูกต้องหรือไม่, ข้อความ)
    """
    try:
        if not dtype_settings:
            return False, "ไม่มีการตั้งค่าชนิดข้อมูล"
            
        # ตรวจสอบว่าชนิดข้อมูลที่ระบุรองรับหรือไม่
        for column, dtype in dtype_settings.items():
            if column.startswith('_'):  # ข้าม special keys
                continue
                
            # ตรวจสอบว่า dtype รองรับหรือไม่
            if not _is_supported_dtype(dtype):
                return False, f"ชนิดข้อมูล '{dtype}' สำหรับคอลัมน์ '{column}' ไม่รองรับ"
                
        return True, "การตั้งค่าชนิดข้อมูลถูกต้อง"
        
    except Exception as e:
        return False, f"เกิดข้อผิดพลาดในการตรวจสอบชนิดข้อมูล: {str(e)}"


def validate_file_for_upload(file_path: str, 
                           expected_logic_type: Optional[str] = None) -> Tuple[bool, str]:
    """
    ตรวจสอบไฟล์ก่อนการอัปโหลด
    
    Args:
        file_path: ที่อยู่ไฟล์
        expected_logic_type: ประเภทไฟล์ที่คาดหวัง
        
    Returns:
        Tuple[bool, str]: (ถูกต้องหรือไม่, ข้อความ)
    """
    try:
        # ตรวจสอบไฟล์มีอยู่หรือไม่
        is_valid, message = validate_file_path(file_path)
        if not is_valid:
            return False, message
            
        # ตรวจสอบประเภทไฟล์
        if not is_supported_file_type(file_path):
            return False, f"ประเภทไฟล์ไม่รองรับ: {os.path.splitext(file_path)[1]}"
            
        # ตรวจสอบขนาดไฟล์
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return False, "ไฟล์ว่างเปล่า"
            
        # ตรวจสอบว่าไฟล์ไม่ถูกล็อค
        try:
            with open(file_path, 'r') as f:
                pass
        except PermissionError:
            return False, "ไฟล์ถูกล็อคหรือใช้งานอยู่"
            
        return True, "ไฟล์พร้อมสำหรับการอัปโหลด"
        
    except Exception as e:
        return False, f"เกิดข้อผิดพลาดในการตรวจสอบไฟล์: {str(e)}"


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


# Import function จาก helpers.py
from .helpers import validate_file_path