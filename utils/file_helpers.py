"""
File Helper Utilities

Common file operations and type detection functions
"""

from typing import Optional, List, Tuple
import os
import pandas as pd


def detect_file_extension_type(file_path: str) -> str:
    """
    Detect file type from extension for processing strategy

    Args:
        file_path: Path to the file

    Returns:
        File type string: 'csv', 'excel_xls', or 'excel'
    """
    ext = file_path.lower()
    if ext.endswith('.csv'):
        return 'csv'
    elif ext.endswith('.xls'):
        return 'excel_xls'
    else:
        return 'excel'


def get_file_size_mb(file_path: str) -> float:
    """
    Get file size in megabytes

    Args:
        file_path: Path to the file

    Returns:
        File size in MB, or 0 if file doesn't exist
    """
    if not os.path.exists(file_path):
        return 0.0
    return os.path.getsize(file_path) / (1024 * 1024)


def is_excel_file(file_path: str) -> bool:
    """Check if file is Excel format (.xlsx, .xls)"""
    ext = file_path.lower()
    return ext.endswith(('.xlsx', '.xls'))


def is_csv_file(file_path: str) -> bool:
    """Check if file is CSV format"""
    return file_path.lower().endswith('.csv')


def is_data_file(file_path: str) -> bool:
    """Check if file is a supported data file (Excel or CSV)"""
    return is_excel_file(file_path) or is_csv_file(file_path)


def normalize_file_path(file_path: str) -> str:
    """
    Normalize file path for cross-platform compatibility

    Args:
        file_path: Path to normalize

    Returns:
        Normalized path
    """
    return os.path.normpath(file_path)


def ensure_directory_exists(directory_path: str) -> bool:
    """
    Ensure directory exists, create if needed

    Args:
        directory_path: Path to directory

    Returns:
        True if directory exists or was created successfully
    """
    try:
        os.makedirs(directory_path, exist_ok=True)
        return True
    except Exception:
        return False


def read_csv_with_encoding_fallback(
    file_path: str,
    encodings: Optional[List[str]] = None,
    **kwargs
) -> Tuple[bool, pd.DataFrame]:
    """
    Try reading CSV file with multiple encodings (fallback pattern)

    Common in Thai datasets where encoding might be UTF-8, CP874, or Latin1

    Args:
        file_path: Path to CSV file
        encodings: List of encodings to try (default: ['utf-8', 'cp874', 'latin1'])
        **kwargs: Additional arguments to pass to pd.read_csv

    Returns:
        Tuple of (success: bool, dataframe or error_message)

    Example:
        success, result = read_csv_with_encoding_fallback('data.csv')
        if success:
            df = result
        else:
            error_msg = result
    """
    if encodings is None:
        encodings = ['utf-8', 'cp874', 'latin1']

    last_error = None

    for encoding in encodings:
        try:
            df = pd.read_csv(file_path, encoding=encoding, **kwargs)
            return True, df
        except UnicodeDecodeError as e:
            last_error = e
            continue
        except Exception as e:
            # Other errors (file not found, etc.) should fail immediately
            return False, str(e)

    # If all encodings failed
    error_msg = f"Could not read file with any encoding: {encodings}. Last error: {last_error}"
    return False, error_msg
