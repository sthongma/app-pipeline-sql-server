"""
Constants for PIPELINE_SQLSERVER

This file contains various constants used throughout the project for better maintainability and AI comprehension.
"""

from typing import List
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
    
    # Date format options
    DATE_FORMAT_UK = "UK"  # day first
    DATE_FORMAT_US = "US"  # month first
    
    # Column name cleaning patterns
    INVALID_COLUMN_CHARS = r'[\s\W]+'
    REPLACEMENT_CHAR = '_'


# === APPLICATION CONSTANTS ===
class AppConstants:
    """Application constants"""

    # Window settings
    MAIN_WINDOW_SIZE = (900, 780)
    LOGIN_WINDOW_SIZE = (440, 420)

    # Logging settings
    LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'


# === PATH CONSTANTS ===
class PathConstants:
    """Path and file constants"""

    # Base directory (where this constants.py file is located)
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # Configuration files (sql_config.json no longer used - using environment variables)
    CONFIG_DIR = os.path.join(_BASE_DIR, "config")
    COLUMN_SETTINGS_FILE = os.path.join(CONFIG_DIR, "column_settings.json")
    DTYPE_SETTINGS_FILE = os.path.join(CONFIG_DIR, "dtype_settings.json")

    # Default search path
    DEFAULT_SEARCH_PATH = os.path.join(os.path.expanduser("~"), "Downloads")
    

# === ERROR MESSAGES ===
class ErrorMessages:
    """Standard error messages"""

    # Database errors
    DB_CONNECTION_FAILED = "Failed to connect to SQL Server"

    # Data validation errors
    MISSING_COLUMNS = "Required columns are missing"
    EMPTY_DATA = "No data found in file"


# === SUCCESS MESSAGES ===
class SuccessMessages:
    """Standard success messages"""

    DB_CONNECTION_SUCCESS = "Database connection successful"


# === REGEX PATTERNS ===
class RegexPatterns:
    """Commonly used regular expression patterns"""

    # Numeric cleaning
    NUMERIC_ONLY = r"[^\d.-]"

    # Column name standardization
    COLUMN_CLEANUP = r'[\s\W]+'

    # SQL Server object naming
    SQL_IDENTIFIER = r'^[a-zA-Z_][a-zA-Z0-9_]*$'