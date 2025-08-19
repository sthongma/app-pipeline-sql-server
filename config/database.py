"""
Database configuration management for PIPELINE_SQLSERVER

This module handles SQL Server connection configuration including:
- Loading and saving configuration settings
- Creating SQLAlchemy engines
- Managing connection strings
"""

import os
import re
from typing import Dict, Any, Optional
from sqlalchemy import create_engine, Engine

from constants import DatabaseConstants
from utils.validators import validate_database_config


def load_env_file(env_file_path: str = ".env") -> None:
    """Load environment variables from .env file."""
    if not os.path.exists(env_file_path):
        return
    
    try:
        with open(env_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # Only set if not already in environment
                    if key not in os.environ:
                        os.environ[key] = value
    except Exception:
        pass  # Silently ignore errors


class DatabaseConfig:
    
    def __init__(self) -> None:
        """
        Initialize DatabaseConfig.
        
        Loads configuration from environment variables.
        """
        self.config: Optional[Dict[str, Any]] = None
        self.engine: Optional[Engine] = None
        self.load_config()
        # Don't create engine automatically - wait for valid config

    def load_config(self) -> None:
        """
        Load configuration from environment variables and .env file.
        """
        # Load .env file first
        load_env_file()
        
        # Load configuration from environment variables
        self.config = {
            "server": os.getenv('DB_SERVER', ''),
            "database": os.getenv('DB_NAME', ''),
            "auth_type": "SQL Server" if os.getenv('DB_USERNAME') else DatabaseConstants.AUTH_WINDOWS,
            "username": os.getenv('DB_USERNAME', ''),
            "password": os.getenv('DB_PASSWORD', '')
        }
    
    def save_config(self) -> bool:
        """
        Configuration is managed via environment variables only.
        
        Returns:
            bool: Always True (no file operations needed)
        """
        # Environment variables are the only source of configuration
        return True
    
    def update_engine(self) -> None:
        """
        Update SQLAlchemy engine according to current configuration.
        
        Creates new connection string and engine based on current settings.
        """
        if self.config is None:
            return
            
        # Validate configuration before creating engine
        is_valid, error_msg = validate_database_config(self.config)
        if not is_valid:
            # Don't raise error - just log it and return
            return
            
        if self.config["auth_type"] == DatabaseConstants.AUTH_WINDOWS:
            # Windows Authentication
            server = self.config["server"]
            database = self.config["database"]
            
            connection_string = (
                f'mssql+pyodbc://{server}/{database}'
                f'?driver={DatabaseConstants.DEFAULT_DRIVER}&Trusted_Connection=yes&'
                f'charset=utf8&autocommit=true'
            )
        else:
            # SQL Server Authentication
            server = self.config["server"]
            database = self.config["database"]
            username = self.config["username"]
            password = self.config["password"]
            
            connection_string = (
                f'mssql+pyodbc://{username}:{password}'
                f'@{server}/{database}'
                f'?driver={DatabaseConstants.DEFAULT_DRIVER}&'
                f'charset=utf8&autocommit=true'
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
    
    def save_to_env_file(self, server: str, database: str, auth_type: str, 
                         username: str = "", password: str = "") -> bool:
        """
        Save database configuration to .env file.
        
        Args:
            server: Database server
            database: Database name
            auth_type: Authentication type
            username: Username (for SQL Server auth)
            password: Password (for SQL Server auth)
            
        Returns:
            bool: Success status
        """
        try:
            env_file_path = ".env"
            
            # Prepare new values
            new_values = {
                'DB_SERVER': server,
                'DB_NAME': database,
                'DB_USERNAME': username if auth_type == "SQL Server" else '',
                'DB_PASSWORD': password if auth_type == "SQL Server" else ''
            }
            
            if os.path.exists(env_file_path):
                # Read existing .env file
                with open(env_file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Update existing values
                updated_lines = []
                updated_keys = set()
                
                for line in lines:
                    line = line.rstrip()
                    if '=' in line and not line.strip().startswith('#'):
                        key = line.split('=')[0].strip()
                        if key in new_values:
                            updated_lines.append(f"{key}={new_values[key]}\n")
                            updated_keys.add(key)
                        else:
                            updated_lines.append(line + '\n')
                    else:
                        updated_lines.append(line + '\n')
                
                # Add missing keys
                for key, value in new_values.items():
                    if key not in updated_keys:
                        updated_lines.append(f"{key}={value}\n")
            else:
                # Create new .env file
                updated_lines = [
                    "# Database Configuration for PIPELINE_SQLSERVER\n",
                    f"DB_SERVER={new_values['DB_SERVER']}\n",
                    f"DB_NAME={new_values['DB_NAME']}\n",
                    f"DB_USERNAME={new_values['DB_USERNAME']}\n",
                    f"DB_PASSWORD={new_values['DB_PASSWORD']}\n",
                    "\n",
                    "# Logging Configuration\n",
                    "STRUCTURED_LOGGING=false\n"
                ]
            
            # Write back to file
            with open(env_file_path, 'w', encoding='utf-8') as f:
                f.writelines(updated_lines)
            
            # Update environment variables in current process
            for key, value in new_values.items():
                os.environ[key] = value
            
            # Reload config
            self.load_config()
            
            return True
            
        except Exception as e:
            return False