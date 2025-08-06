"""
Settings management สำหรับ PIPELINE_SQLSERVER

จัดการการตั้งค่าต่างๆ ของแอปพลิเคชันแบบรวมศูนย์
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from constants import PathConstants, DatabaseConstants, AppConstants
from utils.helpers import safe_json_load, safe_json_save


@dataclass
class DatabaseSettings:
    """การตั้งค่าฐานข้อมูล"""
    server: str = ""
    database: str = ""
    auth_type: str = DatabaseConstants.AUTH_WINDOWS
    username: str = ""
    password: str = ""
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DatabaseSettings':
        """สร้าง instance จาก dictionary"""
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})
        
    def to_dict(self) -> Dict[str, Any]:
        """แปลงเป็น dictionary"""
        return {
            'server': self.server,
            'database': self.database,
            'auth_type': self.auth_type,
            'username': self.username,
            'password': self.password
        }


@dataclass
class AppSettings:
    """การตั้งค่าแอปพลิเคชัน"""
    last_search_path: str = PathConstants.DEFAULT_SEARCH_PATH
    window_size: tuple = AppConstants.MAIN_WINDOW_SIZE
    auto_move_files: bool = True
    backup_enabled: bool = True
    log_level: str = "INFO"
    theme: str = "system"  # system, dark, light
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppSettings':
        """สร้าง instance จาก dictionary"""
        # แปลง tuple จาก list ถ้าจำเป็น
        if 'window_size' in data and isinstance(data['window_size'], list):
            data['window_size'] = tuple(data['window_size'])
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})
        
    def to_dict(self) -> Dict[str, Any]:
        """แปลงเป็น dictionary"""
        return {
            'last_search_path': self.last_search_path,
            'window_size': list(self.window_size),  # แปลง tuple เป็น list สำหรับ JSON
            'auto_move_files': self.auto_move_files,
            'backup_enabled': self.backup_enabled,
            'log_level': self.log_level,
            'theme': self.theme
        }


class SettingsManager:
    """
    จัดการการตั้งค่าของแอปพลิเคชัน
    
    ทำหน้าที่เป็น centralized settings manager ที่รวบรวมการตั้งค่าทั้งหมด
    """
    
    def __init__(self):
        """Initialize SettingsManager"""
        self.database_settings: Optional[DatabaseSettings] = None
        self.app_settings: Optional[AppSettings] = None
        self.column_settings: Dict[str, Dict[str, str]] = {}
        self.dtype_settings: Dict[str, Dict[str, str]] = {}
        
        # สร้างโฟลเดอร์ config ถ้าไม่มี
        os.makedirs(PathConstants.CONFIG_DIR, exist_ok=True)
        
        # โหลดการตั้งค่าทั้งหมด
        self.load_all_settings()
    
    def load_all_settings(self) -> None:
        """โหลดการตั้งค่าทั้งหมด"""
        self.load_database_settings()
        self.load_app_settings()
        self.load_column_settings()
        self.load_dtype_settings()
    
    def load_database_settings(self) -> None:
        """โหลดการตั้งค่าฐานข้อมูล"""
        data = safe_json_load(PathConstants.SQL_CONFIG_FILE, {})
        
        # ใช้ค่าเริ่มต้น
        default_data = {
            "server": os.environ.get('COMPUTERNAME', 'localhost') + '\\SQLEXPRESS',
            "database": '',
            "auth_type": DatabaseConstants.AUTH_WINDOWS,
            "username": "",
            "password": ""
        }
        default_data.update(data)
        
        self.database_settings = DatabaseSettings.from_dict(default_data)
    
    def load_app_settings(self) -> None:
        """โหลดการตั้งค่าแอปพลิเคชัน"""
        app_config_file = os.path.join(PathConstants.CONFIG_DIR, "app_settings.json")
        data = safe_json_load(app_config_file, {})
        self.app_settings = AppSettings.from_dict(data)
    
    def load_column_settings(self) -> None:
        """โหลดการตั้งค่าคอลัมน์"""
        self.column_settings = safe_json_load(PathConstants.COLUMN_SETTINGS_FILE, {})
    
    def load_dtype_settings(self) -> None:
        """โหลดการตั้งค่าชนิดข้อมูล"""
        self.dtype_settings = safe_json_load(PathConstants.DTYPE_SETTINGS_FILE, {})
    
    def save_database_settings(self) -> bool:
        """บันทึกการตั้งค่าฐานข้อมูล"""
        if self.database_settings is None:
            return False
        return safe_json_save(self.database_settings.to_dict(), PathConstants.SQL_CONFIG_FILE)
    
    def save_app_settings(self) -> bool:
        """บันทึกการตั้งค่าแอปพลิเคชัน"""
        if self.app_settings is None:
            return False
        app_config_file = os.path.join(PathConstants.CONFIG_DIR, "app_settings.json")
        return safe_json_save(self.app_settings.to_dict(), app_config_file)
    
    def save_column_settings(self) -> bool:
        """บันทึกการตั้งค่าคอลัมน์"""
        return safe_json_save(self.column_settings, PathConstants.COLUMN_SETTINGS_FILE)
    
    def save_dtype_settings(self) -> bool:
        """บันทึกการตั้งค่าชนิดข้อมูล"""
        return safe_json_save(self.dtype_settings, PathConstants.DTYPE_SETTINGS_FILE)
    
    def save_all_settings(self) -> bool:
        """บันทึกการตั้งค่าทั้งหมด"""
        results = [
            self.save_database_settings(),
            self.save_app_settings(),
            self.save_column_settings(),
            self.save_dtype_settings()
        ]
        return all(results)
    
    def get_database_config(self) -> Dict[str, Any]:
        """
        ดึงการตั้งค่าฐานข้อมูลในรูปแบบ dict
        
        Returns:
            Dict[str, Any]: การตั้งค่าฐานข้อมูล
        """
        if self.database_settings is None:
            return {}
        return self.database_settings.to_dict()
    
    def update_database_config(self, **kwargs) -> bool:
        """
        อัปเดตการตั้งค่าฐานข้อมูล
        
        Args:
            **kwargs: การตั้งค่าที่ต้องการอัปเดต
            
        Returns:
            bool: สำเร็จหรือไม่
        """
        if self.database_settings is None:
            return False
            
        # อัปเดตเฉพาะค่าที่ระบุ
        for key, value in kwargs.items():
            if hasattr(self.database_settings, key):
                setattr(self.database_settings, key, value)
        
        return self.save_database_settings()
    
    def get_column_mapping(self, logic_type: str) -> Dict[str, str]:
        """
        ดึงการแมปคอลัมน์สำหรับประเภทไฟล์
        
        Args:
            logic_type: ประเภทไฟล์
            
        Returns:
            Dict[str, str]: การแมปคอลัมน์
        """
        return self.column_settings.get(logic_type, {})
    
    def get_dtype_mapping(self, logic_type: str) -> Dict[str, str]:
        """
        ดึงการแมปชนิดข้อมูลสำหรับประเภทไฟล์
        
        Args:
            logic_type: ประเภทไฟล์
            
        Returns:
            Dict[str, str]: การแมปชนิดข้อมูล
        """
        return self.dtype_settings.get(logic_type, {})
    
    def add_logic_type(self, logic_type: str, column_mapping: Dict[str, str], 
                      dtype_mapping: Dict[str, str]) -> bool:
        """
        เพิ่มประเภทไฟล์ใหม่
        
        Args:
            logic_type: ชื่อประเภทไฟล์
            column_mapping: การแมปคอลัมน์
            dtype_mapping: การแมปชนิดข้อมูล
            
        Returns:
            bool: สำเร็จหรือไม่
        """
        self.column_settings[logic_type] = column_mapping
        self.dtype_settings[logic_type] = dtype_mapping
        
        return (self.save_column_settings() and self.save_dtype_settings())
    
    def remove_logic_type(self, logic_type: str) -> bool:
        """
        ลบประเภทไฟล์
        
        Args:
            logic_type: ชื่อประเภทไฟล์
            
        Returns:
            bool: สำเร็จหรือไม่
        """
        if logic_type in self.column_settings:
            del self.column_settings[logic_type]
        if logic_type in self.dtype_settings:
            del self.dtype_settings[logic_type]
            
        return (self.save_column_settings() and self.save_dtype_settings())
    
    def get_last_search_path(self) -> str:
        """
        ดึง search path ล่าสุด
        
        Returns:
            str: search path
        """
        if self.app_settings is None:
            return PathConstants.DEFAULT_SEARCH_PATH
        return self.app_settings.last_search_path
    
    def update_last_search_path(self, path: str) -> bool:
        """
        อัปเดต search path ล่าสุด
        
        Args:
            path: search path ใหม่
            
        Returns:
            bool: สำเร็จหรือไม่
        """
        if self.app_settings is None:
            return False
            
        self.app_settings.last_search_path = path
        return self.save_app_settings()


# Global settings instance
settings_manager = SettingsManager()