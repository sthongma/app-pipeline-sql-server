"""
Helper functions for PIPELINE_SQLSERVER

Utility functions used across multiple parts of the application
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
    Normalize column name to standard format
    
    Args:
        column_name: Original column name
        
    Returns:
        str: Normalized column name
    """
    if pd.isna(column_name):
        return ""
        
    # Convert to string and remove leading/trailing whitespace
    name = str(column_name).strip().lower()
    
    # Replace special characters with underscore
    name = re.sub(RegexPatterns.COLUMN_CLEANUP, FileConstants.REPLACEMENT_CHAR, name)
    
    # Remove leading and trailing underscores
    return name.strip(FileConstants.REPLACEMENT_CHAR)


def parse_date_safe(value: Any, dayfirst: bool = True, date_format: str = 'UK') -> Optional[pd.Timestamp]:
    """
    Safely parse value to date
    
    Args:
        value: Value to parse
        dayfirst: Whether day comes before month (True for UK format)
        date_format: Date format ('UK' or 'US')
        
    Returns:
        Optional[pd.Timestamp]: Parsed date or None if parsing fails
    """
    try:
        if pd.isna(value) or value == "":
            return None
            
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
        
        # Use date_format if dayfirst is not specified
        if date_format and date_format != 'UK':
            dayfirst = False
                
        return parser.parse(str(value), dayfirst=dayfirst)
        
    except (ValueError, TypeError, parser.ParserError):
        return None


def parse_date_with_format(value: Any, date_format: str = 'UK') -> Optional[pd.Timestamp]:
    """
    Parse value to date according to specified format
    
    Args:
        value: Value to parse
        date_format: Date format ('UK' for DD-MM or 'US' for MM-DD)
        
    Returns:
        Optional[pd.Timestamp]: Parsed date or None if parsing fails
    """
    try:
        if pd.isna(value) or value == "":
            return None
            
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
        
        # Set dayfirst based on date_format
        dayfirst = (date_format == 'UK')
        
        # Try parsing with dateutil.parser first
        try:
            return parser.parse(str(value), dayfirst=dayfirst)
        except:
            pass
        
        # If parsing fails, try with pandas
        try:
            if dayfirst:
                return pd.to_datetime(value, format='%d/%m/%Y', errors='coerce')
            else:
                return pd.to_datetime(value, format='%m/%d/%Y', errors='coerce')
        except:
            pass
        
        # Try parsing with other formats
        try:
            return pd.to_datetime(value, errors='coerce')
        except:
            pass
            
        return None
        
    except (ValueError, TypeError, parser.ParserError):
        return None


def clean_numeric_value(value: Any) -> Optional[float]:
    """
    Clean numeric value
    
    Args:
        value: Value to clean
        
    Returns:
        Optional[float]: Cleaned numeric value or None if not numeric
    """
    try:
        if pd.isna(value) or value == "":
            return None
            
        # Convert to string and remove non-numeric characters
        cleaned = re.sub(RegexPatterns.NUMERIC_ONLY, "", str(value))
        
        if not cleaned or cleaned == "-":
            return None
            
        return float(cleaned)
        
    except (ValueError, TypeError):
        return None


def format_error_message(error: Exception, context: str = "") -> str:
    """
    Format error message
    
    Args:
        error: Exception that occurred
        context: Context of the error
        
    Returns:
        str: Formatted error message
    """
    error_msg = str(error)
    
    if context:
        return f"Error: {context}: {error_msg}"
    else:
        return f"Error: {error_msg}"


def safe_json_load(file_path: str, default: dict = None) -> dict:
    """
    Safely load JSON file
    
    Args:
        file_path: Path to JSON file
        default: Default value if loading fails
        
    Returns:
        dict: Data from JSON file or default value
    """
    import json
    
    if default is None:
        default = {}
        
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, PermissionError):
        pass
        
    return default


def safe_json_save(data: dict, file_path: str) -> bool:
    """
    Safely save JSON file
    
    Args:
        data: Data to save
        file_path: Path to save file
        
    Returns:
        bool: Whether operation was successful
    """
    import json
    
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
        
    except (FileNotFoundError, PermissionError, TypeError):
        return False




