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
        "NVARCHAR(MAX)",
        "INT",
        "FLOAT",
        "DATE",
        "DATETIME"
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


# === PROCESSING CONSTANTS ===
class ProcessingConstants:
    """Data processing and validation constants"""

    # Null value thresholds (percentage)
    NULL_WARNING_THRESHOLD = 50  # Warn if more than 50% nulls

    # Chunk sizes for batch processing
    CHUNK_SIZE_LARGE = 10000      # Large file processing
    CHUNK_SIZE_PROCESSING = 5000  # General processing

    # File type detection match thresholds (percentage of matching columns)
    MATCH_THRESHOLD_PERFECT = 1.0    # 100% match
    MATCH_THRESHOLD_HIGH = 0.8       # 80% match
    MATCH_THRESHOLD_MEDIUM = 0.6     # 60% match
    MATCH_THRESHOLD_LOW = 0.3        # 30% match


# === UI CONSTANTS ===
class UIConstants:
    """UI color and styling constants"""

    # Primary colors
    COLOR_PRIMARY_BLUE = "#2B86F5"
    COLOR_SUCCESS_GREEN = "#41AA41"
    COLOR_ERROR_RED = "#FF4444"
    COLOR_WARNING_ORANGE = "#FFA500"

    # Secondary colors
    COLOR_SECONDARY_GRAY = "#7a7a7a"
    COLOR_TEXT_LIGHT = "#888888"
    COLOR_BACKGROUND_DARK = "#2B2B2B"

    # Emoji colors
    COLOR_EMOJI_SUCCESS = "#41AA41"
    COLOR_EMOJI_ERROR = "#FF4444"
    COLOR_EMOJI_WARNING = "#FFA500"
    COLOR_EMOJI_INFO = "#00BFFF"
    COLOR_EMOJI_HIGHLIGHT = "#FFD700"


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

    # File types configuration directory
    FILE_TYPES_DIR = os.path.join(CONFIG_DIR, "file_types")

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