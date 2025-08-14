"""
Constants สำหรับ PIPELINE_SQLSERVER

ไฟล์นี้เก็บค่าคงที่ต่างๆ ที่ใช้ในโปรเจกต์ เพื่อให้ AI สามารถเข้าใจและปรับปรุงได้ง่าย
"""

from typing import List, Dict
import os

# === DATABASE CONSTANTS ===
class DatabaseConstants:
    """Database constants"""
    
    # SQL Server connection settings
    DEFAULT_DRIVER = "ODBC+Driver+17+for+SQL+Server"
    FALLBACK_DRIVER = "SQL Server"
    
    # Authentication types
    AUTH_WINDOWS = "Windows"
    AUTH_SQL = "SQL Server"
    
    # Default schema names
    DEFAULT_BRONZE_SCHEMA = "bronze"
    DEFAULT_SILVER_SCHEMA = "silver"
    DEFAULT_GOLD_SCHEMA = "gold"
    
    # Supported SQL Server data types
    SUPPORTED_DTYPES: List[str] = [
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
    """File processing constants"""
    
    # Supported file extensions
    SUPPORTED_EXCEL_EXTENSIONS = ['.xlsx', '.xls']
    SUPPORTED_CSV_EXTENSIONS = ['.csv']
    SUPPORTED_EXTENSIONS = SUPPORTED_EXCEL_EXTENSIONS + SUPPORTED_CSV_EXTENSIONS
    
    # File size thresholds (in bytes)
    LARGE_FILE_THRESHOLD = 50 * 1024 * 1024  # 50MB
    CHUNK_SIZE_LARGE = 50000  # rows - เพิ่มขึ้นจาก 10000 เพื่อลดจำนวนการเข้าถึง DB
    CHUNK_SIZE_MEDIUM = 20000  # rows - เพิ่มขึ้นจาก 2000 
    CHUNK_SIZE_SMALL = 10000   # rows - เพิ่มขึ้นจาก 1000
    
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
    """Application constants"""
    
    # Application info
    APP_NAME = "PIPELINE_SQLSERVER"
    APP_VERSION = "1.0.0"
    
    # Window settings
    MAIN_WINDOW_SIZE = (900, 780)
    LOGIN_WINDOW_SIZE = (440, 420)
    
    # Threading settings
    MAX_WORKER_THREADS = 3
    UI_UPDATE_INTERVAL = 100  # milliseconds
    
    
    # Logging settings
    LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    
    # Performance settings
    CACHE_SIZE_LIMIT = 100  # number of cached items
    SETTINGS_CACHE_ENABLED = True


# === PATH CONSTANTS ===
class PathConstants:
    """Path and file constants"""
    
    # Configuration files
    CONFIG_DIR = "config"
    COLUMN_SETTINGS_FILE = os.path.join(CONFIG_DIR, "column_settings.json")
    DTYPE_SETTINGS_FILE = os.path.join(CONFIG_DIR, "dtype_settings.json")
    SQL_CONFIG_FILE = os.path.join(CONFIG_DIR, "sql_config.json")
    LAST_PATH_FILE = os.path.join(CONFIG_DIR, "last_path.json")
    
    # Default search path
    DEFAULT_SEARCH_PATH = os.path.join(os.path.expanduser("~"), "Downloads")
    

# === ERROR MESSAGES ===
class ErrorMessages:
    """Standard error messages"""
    
    # Database errors
    DB_CONNECTION_FAILED = "Failed to connect to SQL Server"
    DB_UPLOAD_FAILED = "Data upload failed"
    DB_SCHEMA_MISMATCH = "Table schema does not match configuration"
    
    # File errors
    FILE_NOT_FOUND = "File not found"
    FILE_READ_ERROR = "Error reading file"
    FILE_MOVE_ERROR = "Unable to move file"
    
    # Data validation errors
    MISSING_COLUMNS = "Required columns are missing"
    INVALID_DATA_TYPE = "Invalid data type"
    EMPTY_DATA = "No data found in file"
    
    # Configuration errors
    CONFIG_LOAD_ERROR = "Unable to load configuration"
    CONFIG_SAVE_ERROR = "Unable to save configuration"


# === SUCCESS MESSAGES ===
class SuccessMessages:
    """Standard success messages"""
    
    DB_CONNECTION_SUCCESS = "Database connection successful"
    FILE_UPLOAD_SUCCESS = "File upload successful"
    FILE_MOVE_SUCCESS = "File move successful"
    CONFIG_SAVE_SUCCESS = "Settings saved successfully"


# === REGEX PATTERNS ===
class RegexPatterns:
    """Commonly used regular expression patterns"""
    
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
    """Data type mappings between different systems"""
    
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