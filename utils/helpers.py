"""
Helper functions สำหรับ PIPELINE_SQLSERVER

ฟังก์ชันยูทิลิตี้ที่ใช้ในหลายส่วนของแอปพลิเคชัน
"""

import os
import re
import pandas as pd
from datetime import datetime
from typing import Optional, Union, Any
from dateutil import parser

from constants import FileConstants, RegexPatterns, ErrorMessages



def normalize_column_name(column_name: Union[str, Any]) -> str:
    """
    ปรับปรุงชื่อคอลัมน์ให้เป็นรูปแบบมาตรฐาน
    
    Args:
        column_name: ชื่อคอลัมน์ต้นฉบับ
        
    Returns:
        str: ชื่อคอลัมน์ที่ปรับปรุงแล้ว
    """
    if pd.isna(column_name):
        return ""
        
    # แปลงเป็น string และลบช่องว่างข้างหน้า-หลัง
    name = str(column_name).strip().lower()
    
    # แทนที่อักขระพิเศษด้วย underscore
    name = re.sub(RegexPatterns.COLUMN_CLEANUP, FileConstants.REPLACEMENT_CHAR, name)
    
    # ลบ underscore ที่ขึ้นต้นและลงท้าย
    return name.strip(FileConstants.REPLACEMENT_CHAR)


def parse_date_safe(value: Any, dayfirst: bool = True, date_format: str = 'UK') -> Optional[pd.Timestamp]:
    """
    แปลงค่าเป็นวันที่อย่างปลอดภัย
    
    Args:
        value: ค่าที่ต้องการแปลง
        dayfirst: ให้วันมาก่อนเดือนหรือไม่ (True สำหรับรูปแบบ UK)
        date_format: รูปแบบวันที่ ('UK' หรือ 'US')
        
    Returns:
        Optional[pd.Timestamp]: วันที่ที่แปลงแล้ว หรือ None ถ้าแปลงไม่ได้
    """
    try:
        if pd.isna(value) or value == "":
            return None
            
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
        
        # ใช้ date_format ถ้าไม่ระบุ dayfirst
        if date_format and date_format != 'UK':
            dayfirst = False
                
        return parser.parse(str(value), dayfirst=dayfirst)
        
    except Exception:
        return None


def parse_date_with_format(value: Any, date_format: str = 'UK') -> Optional[pd.Timestamp]:
    """
    แปลงค่าเป็นวันที่ตามรูปแบบที่กำหนด
    
    Args:
        value: ค่าที่ต้องการแปลง
        date_format: รูปแบบวันที่ ('UK' สำหรับ DD-MM หรือ 'US' สำหรับ MM-DD)
        
    Returns:
        Optional[pd.Timestamp]: วันที่ที่แปลงแล้ว หรือ None ถ้าแปลงไม่ได้
    """
    try:
        if pd.isna(value) or value == "":
            return None
            
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
        
        # กำหนด dayfirst ตาม date_format
        dayfirst = (date_format == 'UK')
        
        # ลองแปลงด้วย dateutil.parser ก่อน
        try:
            return parser.parse(str(value), dayfirst=dayfirst)
        except:
            pass
        
        # ถ้าแปลงไม่ได้ ลองแปลงด้วย pandas
        try:
            if dayfirst:
                return pd.to_datetime(value, format='%d/%m/%Y', errors='coerce')
            else:
                return pd.to_datetime(value, format='%m/%d/%Y', errors='coerce')
        except:
            pass
        
        # ลองแปลงด้วยรูปแบบอื่นๆ
        try:
            return pd.to_datetime(value, errors='coerce')
        except:
            pass
            
        return None
        
    except Exception:
        return None


def clean_numeric_value(value: Any) -> Optional[float]:
    """
    ทำความสะอาดค่าตัวเลข
    
    Args:
        value: ค่าที่ต้องการทำความสะอาด
        
    Returns:
        Optional[float]: ค่าตัวเลขที่ทำความสะอาดแล้ว หรือ None ถ้าไม่ใช่ตัวเลข
    """
    try:
        if pd.isna(value) or value == "":
            return None
            
        # แปลงเป็น string และลบอักขระที่ไม่ใช่ตัวเลข
        cleaned = re.sub(RegexPatterns.NUMERIC_ONLY, "", str(value))
        
        if not cleaned or cleaned == "-":
            return None
            
        return float(cleaned)
        
    except Exception:
        return None


def format_error_message(error: Exception, context: str = "") -> str:
    """
    จัดรูปแบบข้อความแสดงข้อผิดพลาด
    
    Args:
        error: ข้อผิดพลาดที่เกิดขึ้น
        context: บริบทของข้อผิดพลาด
        
    Returns:
        str: ข้อความแสดงข้อผิดพลาดที่จัดรูปแบบแล้ว
    """
    error_msg = str(error)
    
    if context:
        return f"❌ {context}: {error_msg}"
    else:
        return f"❌ Error: {error_msg}"


def safe_json_load(file_path: str, default: dict = None) -> dict:
    """
    โหลดไฟล์ JSON อย่างปลอดภัย
    
    Args:
        file_path: ที่อยู่ไฟล์ JSON
        default: ค่าเริ่มต้นถ้าโหลดไม่ได้
        
    Returns:
        dict: ข้อมูลจากไฟล์ JSON หรือค่าเริ่มต้น
    """
    import json
    
    if default is None:
        default = {}
        
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
        
    return default


def safe_json_save(data: dict, file_path: str) -> bool:
    """
    บันทึกไฟล์ JSON อย่างปลอดภัย
    
    Args:
        data: ข้อมูลที่ต้องการบันทึก
        file_path: ที่อยู่ไฟล์ที่ต้องการบันทึก
        
    Returns:
        bool: สำเร็จหรือไม่
    """
    import json
    
    try:
        # สร้างโฟลเดอร์ถ้ายังไม่มี
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
        
    except Exception:
        return False




