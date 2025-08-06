"""
Constants สำหรับ PIPELINE_SQLSERVER

ไฟล์นี้เก็บค่าคงที่ต่างๆ ที่ใช้ในโปรเจกต์ เพื่อให้ AI สามารถเข้าใจและปรับปรุงได้ง่าย
"""

from typing import List, Dict
import os

# === DATABASE CONSTANTS ===
class DatabaseConstants:
    """ค่าคงที่สำหรับฐานข้อมูล"""
    
    # SQL Server connection settings
    DEFAULT_DRIVER = "ODBC+Driver+17+for+SQL+Server"
    FALLBACK_DRIVER = "SQL Server"
    
    # Authentication types
    AUTH_WINDOWS = "Windows"
    AUTH_SQL = "SQL"
    
    # Default schema names
    DEFAULT_BRONZE_SCHEMA = "bronze"
    DEFAULT_SILVER_SCHEMA = "silver"
    DEFAULT_GOLD_SCHEMA = "gold"
    
    # Supported SQL Server data types
    SUPPORTED_DTYPES: List[str] = [
        "VARCHAR(255)",
        "NVARCHAR(100)",
        "NVARCHAR(255)", 
        "NVARCHAR(500)",
        "NVARCHAR(1000)",
        "NVARCHAR(MAX)",
        "INT",
        "BIGINT",
        "DECIMAL(18,2)",
        "FLOAT",
        "DATE",
        "DATETIME",
        "BIT"
    ]


# === FILE PROCESSING CONSTANTS ===
class FileConstants:
    """ค่าคงที่สำหรับการประมวลผลไฟล์"""
    
    # Supported file extensions
    SUPPORTED_EXCEL_EXTENSIONS = ['.xlsx', '.xls']
    SUPPORTED_CSV_EXTENSIONS = ['.csv']
    SUPPORTED_EXTENSIONS = SUPPORTED_EXCEL_EXTENSIONS + SUPPORTED_CSV_EXTENSIONS
    
    # File size thresholds (in bytes)
    LARGE_FILE_THRESHOLD = 50 * 1024 * 1024  # 50MB
    CHUNK_SIZE_LARGE = 10000  # rows
    CHUNK_SIZE_MEDIUM = 2000  # rows
    CHUNK_SIZE_SMALL = 1000   # rows
    
    # Default upload folder structure
    UPLOADED_FOLDER_NAME = "Uploaded_Files"
    
    # Date format options
    DATE_FORMAT_UK = "UK"  # day first
    DATE_FORMAT_US = "US"  # month first
    
    # Column name cleaning patterns
    INVALID_COLUMN_CHARS = r'[\s\W]+'
    REPLACEMENT_CHAR = '_'


# === APPLICATION CONSTANTS ===
class AppConstants:
    """ค่าคงที่สำหรับแอปพลิเคชัน"""
    
    # Application info
    APP_NAME = "PIPELINE_SQLSERVER"
    APP_VERSION = "1.0.0"
    
    # Window settings
    MAIN_WINDOW_SIZE = (900, 700)
    LOGIN_WINDOW_SIZE = (400, 300)
    
    # Threading settings
    MAX_WORKER_THREADS = 3
    UI_UPDATE_INTERVAL = 100  # milliseconds
    
    # File management settings
    DEFAULT_ARCHIVE_DAYS = 90  # วันสำหรับย้ายไฟล์เก่า
    DEFAULT_DELETE_ARCHIVE_DAYS = 90  # วันสำหรับลบไฟล์ใน archive
    
    # Logging settings
    LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    
    # Performance settings
    CACHE_SIZE_LIMIT = 100  # number of cached items
    SETTINGS_CACHE_ENABLED = True


# === PATH CONSTANTS ===
class PathConstants:
    """ค่าคงที่สำหรับ path และไฟล์"""
    
    # Configuration files
    CONFIG_DIR = "config"
    COLUMN_SETTINGS_FILE = os.path.join(CONFIG_DIR, "column_settings.json")
    DTYPE_SETTINGS_FILE = os.path.join(CONFIG_DIR, "dtype_settings.json")
    SQL_CONFIG_FILE = "sql_config.json"
    LAST_PATH_FILE = os.path.join(CONFIG_DIR, "last_path.json")
    
    # Default search path
    DEFAULT_SEARCH_PATH = os.path.join(os.path.expanduser("~"), "Downloads")
    
    # Archive paths
    DEFAULT_ARCHIVE_PATH = "D:/Archived_Files"
    
    # Backup and logs
    BACKUP_DIR = "backups"
    LOGS_DIR = "logs"


# === ERROR MESSAGES ===
class ErrorMessages:
    """ข้อความแสดงข้อผิดพลาดมาตรฐาน"""
    
    # Database errors
    DB_CONNECTION_FAILED = "ไม่สามารถเชื่อมต่อกับ SQL Server ได้"
    DB_UPLOAD_FAILED = "การอัปโหลดข้อมูลล้มเหลว"
    DB_SCHEMA_MISMATCH = "Schema ของตารางไม่ตรงกับการตั้งค่า"
    
    # File errors
    FILE_NOT_FOUND = "ไม่พบไฟล์ที่ระบุ"
    FILE_READ_ERROR = "เกิดข้อผิดพลาดขณะอ่านไฟล์"
    FILE_MOVE_ERROR = "ไม่สามารถย้ายไฟล์ได้"
    
    # Data validation errors
    MISSING_COLUMNS = "คอลัมน์ที่จำเป็นหายไป"
    INVALID_DATA_TYPE = "ชนิดข้อมูลไม่ถูกต้อง"
    EMPTY_DATA = "ไม่พบข้อมูลในไฟล์"
    
    # Configuration errors
    CONFIG_LOAD_ERROR = "ไม่สามารถโหลดการตั้งค่าได้"
    CONFIG_SAVE_ERROR = "ไม่สามารถบันทึกการตั้งค่าได้"


# === SUCCESS MESSAGES ===
class SuccessMessages:
    """ข้อความแสดงความสำเร็จมาตรฐาน"""
    
    DB_CONNECTION_SUCCESS = "เชื่อมต่อฐานข้อมูลสำเร็จ"
    FILE_UPLOAD_SUCCESS = "อัปโหลดไฟล์สำเร็จ"
    FILE_MOVE_SUCCESS = "ย้ายไฟล์สำเร็จ"
    CONFIG_SAVE_SUCCESS = "บันทึกการตั้งค่าสำเร็จ"


# === REGEX PATTERNS ===
class RegexPatterns:
    """Regular expression patterns ที่ใช้บ่อย"""
    
    # Numeric cleaning
    NUMERIC_ONLY = r"[^\d.-]"
    
    # Column name standardization  
    COLUMN_CLEANUP = r'[\s\W]+'
    
    # File validation
    EXCEL_FILE_PATTERN = r'.*\.(xlsx|xls)$'
    CSV_FILE_PATTERN = r'.*\.csv$'
    
    # SQL Server object naming
    SQL_IDENTIFIER = r'^[a-zA-Z_][a-zA-Z0-9_]*$'


# === TYPE MAPPINGS ===
class TypeMappings:
    """การแมปชนิดข้อมูลระหว่างระบบต่างๆ"""
    
    # Pandas to SQL Server type mapping
    PANDAS_TO_SQL: Dict[str, str] = {
        'object': 'NVARCHAR(255)',
        'int64': 'BIGINT',
        'int32': 'INT',
        'float64': 'FLOAT',
        'datetime64[ns]': 'DATETIME',
        'bool': 'BIT'
    }
    
    # String representations to actual types
    DTYPE_STRING_MAPPING: Dict[str, str] = {
        'string': 'NVARCHAR(255)',
        'integer': 'INT',
        'float': 'FLOAT',
        'date': 'DATE',
        'datetime': 'DATETIME',
        'boolean': 'BIT'
    }