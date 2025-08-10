"""
Database configuration management สำหรับ PIPELINE_SQLSERVER

โมดูลนี้จัดการการตั้งค่าการเชื่อมต่อกับ SQL Server รวมถึง:
- การโหลดและบันทึกการตั้งค่า
- การสร้าง SQLAlchemy engine
- การจัดการ connection strings
"""

import os
import json
from typing import Dict, Any, Optional
from sqlalchemy import create_engine, Engine

from constants import DatabaseConstants, PathConstants
from utils.helpers import safe_json_load, safe_json_save
from utils.validators import validate_database_config


class DatabaseConfig:
    CONFIG_FILE = PathConstants.SQL_CONFIG_FILE
    
    def __init__(self) -> None:
        """
        Initialize DatabaseConfig
        
        โหลดการตั้งค่าจากไฟล์และสร้าง engine
        """
        self.config: Optional[Dict[str, Any]] = None
        self.engine: Optional[Engine] = None
        self.load_config()
        self.update_engine()

    def load_config(self) -> None:
        """
        โหลดการตั้งค่าจากไฟล์
        
        ใช้ค่าเริ่มต้นหากไม่มีไฟล์การตั้งค่า
        """
        default_config = {
            "server": os.environ.get('COMPUTERNAME', 'localhost') + '\\SQLEXPRESS',
            "database": '',
            "auth_type": DatabaseConstants.AUTH_WINDOWS,
            "username": "",
            "password": ""
        }
        
        # ใช้ safe_json_load แทน
        saved_config = safe_json_load(self.CONFIG_FILE, {})
        
        self.config = default_config.copy()
        self.config.update(saved_config)
        
        # บันทึกการตั้งค่าถ้าไม่มีไฟล์
        if not os.path.exists(self.CONFIG_FILE):
            self.save_config()
    
    def save_config(self) -> bool:
        """
        บันทึกการตั้งค่าลงไฟล์
        
        Returns:
            bool: สำเร็จหรือไม่
        """
        if self.config is None:
            return False
            
        return safe_json_save(self.config, self.CONFIG_FILE)
    
    def update_engine(self) -> None:
        """
        อัปเดต SQLAlchemy engine ตามการตั้งค่าปัจจุบัน
        
        สร้าง connection string และ engine ใหม่ตามการตั้งค่า
        """
        if self.config is None:
            return
            
        # ตรวจสอบการตั้งค่าก่อนสร้าง engine
        is_valid, error_msg = validate_database_config(self.config)
        if not is_valid:
            raise ValueError(f"การตั้งค่าฐานข้อมูลไม่ถูกต้อง: {error_msg}")
            
        if self.config["auth_type"] == DatabaseConstants.AUTH_WINDOWS:
            # Windows Authentication
            connection_string = (
                f'mssql+pyodbc://{self.config["server"]}/{self.config["database"]}'
                f'?driver={DatabaseConstants.DEFAULT_DRIVER}&Trusted_Connection=yes'
            )
        else:
            # SQL Server Authentication
            connection_string = (
                f'mssql+pyodbc://{self.config["username"]}:{self.config["password"]}'
                f'@{self.config["server"]}/{self.config["database"]}'
                f'?driver={DatabaseConstants.DEFAULT_DRIVER}'
            )
        
        # เปิด fast_executemany เพื่อเร่งการอัปโหลด Unicode ผ่าน pyodbc
        try:
            self.engine = create_engine(connection_string, fast_executemany=True)
        except TypeError:
            # เผื่อกรณี SQLAlchemy รุ่นเก่า ไม่รองรับ keyword นี้
            self.engine = create_engine(connection_string)
    
    def get_engine(self) -> Optional[Engine]:
        """
        คืนค่า SQLAlchemy engine
        
        Returns:
            Optional[Engine]: SQLAlchemy engine หรือ None ถ้าไม่ได้ initialize
        """
        return self.engine
    
    def get_connection_string(self) -> str:
        """
        คืนค่าสตริงการเชื่อมต่อสำหรับ pyodbc
        
        Returns:
            str: Connection string สำหรับ pyodbc
            
        Raises:
            ValueError: ถ้าการตั้งค่าไม่ถูกต้อง
        """
        if self.config is None:
            raise ValueError("ไม่มีการตั้งค่าฐานข้อมูล")
            
        if self.config["auth_type"] == DatabaseConstants.AUTH_WINDOWS:
            return (
                f"DRIVER={{{DatabaseConstants.FALLBACK_DRIVER}}};"
                f"SERVER={self.config['server']};"
                f"DATABASE={self.config['database']};"
                f"Trusted_Connection=yes"
            )
        else:
            return (
                f"DRIVER={{{DatabaseConstants.FALLBACK_DRIVER}}};"
                f"SERVER={self.config['server']};"
                f"DATABASE={self.config['database']};"
                f"UID={self.config['username']};"
                f"PWD={self.config['password']}"
            )
    
    def update_config(self, 
                     server: Optional[str] = None, 
                     database: Optional[str] = None, 
                     auth_type: Optional[str] = None, 
                     username: Optional[str] = None, 
                     password: Optional[str] = None) -> bool:
        """
        อัปเดตการตั้งค่า
        
        Args:
            server: ชื่อ server
            database: ชื่อ database
            auth_type: ประเภทการยืนยันตัวตน (Windows หรือ SQL)
            username: username สำหรับ SQL Authentication
            password: password สำหรับ SQL Authentication
            
        Returns:
            bool: สำเร็จหรือไม่
        """
        if self.config is None:
            return False
            
        # อัปเดตเฉพาะค่าที่ระบุ
        if server is not None:
            self.config["server"] = server
        if database is not None:
            self.config["database"] = database
        if auth_type is not None:
            self.config["auth_type"] = auth_type
        if username is not None:
            self.config["username"] = username
        if password is not None:
            self.config["password"] = password
        
        # บันทึกและอัปเดต engine
        success = self.save_config()
        if success:
            try:
                self.update_engine()
                return True
            except Exception:
                return False
        return False