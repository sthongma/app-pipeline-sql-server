"""
Constants for Column Mapper Tool
Standalone paths and configuration
"""

import os
from pathlib import Path

class PathConstants:
    """Path constants for the column mapper tool"""
    
    # Base paths
    BASE_DIR = Path(__file__).parent.parent
    TOOL_DIR = Path(__file__).parent
    CONFIG_DIR = BASE_DIR / "config"
    
    # Configuration files (ใช้จากโปรแกรมหลัก)
    COLUMN_SETTINGS_FILE = str(CONFIG_DIR / "column_settings.json")
    DTYPE_SETTINGS_FILE = str(CONFIG_DIR / "dtype_settings.json")
    
    # Default search path
    DEFAULT_SEARCH_PATH = str(Path.home() / "Downloads")
    
    # Tool-specific files
    TOOL_LOG_FILE = str(TOOL_DIR / "column_mapper.log")
    MAPPING_HISTORY_FILE = str(TOOL_DIR / "mapping_history.json")