import os
import json
from sqlalchemy import create_engine

class DatabaseConfig:
    CONFIG_FILE = "sql_config.json"
    
    def __init__(self):
        self.config = None
        self.load_config()
        self.engine = None
        self.update_engine()

    def load_config(self):
        """โหลดการตั้งค่าจากไฟล์"""
        default_config = {
            "server": os.environ.get('COMPUTERNAME', 'localhost') + '\\SQLEXPRESS',
            "database": '',
            "auth_type": "Windows",  # Windows หรือ SQL
            "username": "",
            "password": ""
        }
        if os.path.exists(self.CONFIG_FILE):
            with open(self.CONFIG_FILE, 'r') as f:
                saved_config = json.load(f)
                self.config = default_config.copy()
                self.config.update(saved_config)
        else:
            self.config = default_config.copy()
            self.save_config()
    
    def save_config(self):
        """บันทึกการตั้งค่าลงไฟล์"""
        with open(self.CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=4)
    
    def update_engine(self):
        """อัปเดต SQLAlchemy engine ตามการตั้งค่าปัจจุบัน"""
        if self.config["auth_type"] == "Windows":
            # Windows Authentication
            connection_string = f'mssql+pyodbc://{self.config["server"]}/{self.config["database"]}?driver=ODBC+Driver+17+for+SQL+Server&Trusted_Connection=yes'
        else:
            # SQL Server Authentication
            connection_string = f'mssql+pyodbc://{self.config["username"]}:{self.config["password"]}@{self.config["server"]}/{self.config["database"]}?driver=ODBC+Driver+17+for+SQL+Server'
        
        self.engine = create_engine(connection_string)
    
    def get_engine(self):
        """คืนค่า SQLAlchemy engine"""
        return self.engine
    
    def get_connection_string(self):
        """คืนค่าสตริงการเชื่อมต่อสำหรับ pyodbc"""
        if self.config["auth_type"] == "Windows":
            return f"DRIVER={{SQL Server}};SERVER={self.config['server']};DATABASE={self.config['database']};Trusted_Connection=yes"
        else:
            return f"DRIVER={{SQL Server}};SERVER={self.config['server']};DATABASE={self.config['database']};UID={self.config['username']};PWD={self.config['password']}"
    
    def update_config(self, server=None, database=None, auth_type=None, username=None, password=None):
        """อัปเดตการตั้งค่า"""
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
        
        self.save_config()
        self.update_engine()