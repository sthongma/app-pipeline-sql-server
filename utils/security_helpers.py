"""
Security helper functions for password masking and sensitive data handling
"""

import re
from typing import Optional


def mask_password(value: str, mask_char: str = "*", visible_chars: int = 0) -> str:
    """
    Mask a password or sensitive string for logging purposes.

    Args:
        value: The sensitive value to mask
        mask_char: Character to use for masking (default: *)
        visible_chars: Number of characters to show at the end (default: 0)

    Returns:
        str: Masked string

    Examples:
        >>> mask_password("MyPassword123")
        '*************'
        >>> mask_password("MyPassword123", visible_chars=3)
        '**********123'
    """
    if not value or not isinstance(value, str):
        return "****"

    if len(value) <= visible_chars:
        return mask_char * 8  # Always show at least 8 mask characters

    if visible_chars > 0:
        visible_part = value[-visible_chars:]
        masked_part = mask_char * (len(value) - visible_chars)
        return masked_part + visible_part
    else:
        return mask_char * len(value)


def mask_connection_string(conn_str: str) -> str:
    """
    Mask passwords in database connection strings for safe logging.

    Handles multiple formats:
    - SQLAlchemy: mssql+pyodbc://user:password@server/db
    - ODBC: PWD=password;
    - URLs with passwords

    Args:
        conn_str: Connection string possibly containing passwords

    Returns:
        str: Connection string with passwords masked

    Examples:
        >>> mask_connection_string("mssql+pyodbc://user:pass123@server/db")
        'mssql+pyodbc://user:****@server/db'
        >>> mask_connection_string("PWD=mypassword;SERVER=localhost")
        'PWD=****;SERVER=localhost'
    """
    if not conn_str or not isinstance(conn_str, str):
        return str(conn_str)

    masked = conn_str

    # Pattern 1: SQLAlchemy format - protocol://user:password@host
    masked = re.sub(
        r'(://[^:]+:)([^@]+)(@)',
        r'\1****\3',
        masked
    )

    # Pattern 2: ODBC PWD parameter
    masked = re.sub(
        r'(PWD=)([^;]+)(;?)',
        r'\1****\3',
        masked,
        flags=re.IGNORECASE
    )

    # Pattern 3: PASSWORD parameter
    masked = re.sub(
        r'(PASSWORD=)([^;]+)(;?)',
        r'\1****\3',
        masked,
        flags=re.IGNORECASE
    )

    # Pattern 4: Generic password in URL query params
    masked = re.sub(
        r'([?&]password=)([^&]+)',
        r'\1****',
        masked,
        flags=re.IGNORECASE
    )

    return masked


def mask_credentials_in_dict(data: dict, sensitive_keys: Optional[list] = None) -> dict:
    """
    Mask sensitive values in a dictionary (useful for logging config).

    Args:
        data: Dictionary that may contain sensitive data
        sensitive_keys: List of keys to mask (default: common password keys)

    Returns:
        dict: New dictionary with sensitive values masked

    Examples:
        >>> config = {"username": "admin", "password": "secret123", "server": "localhost"}
        >>> mask_credentials_in_dict(config)
        {'username': 'admin', 'password': '****', 'server': 'localhost'}
    """
    if not isinstance(data, dict):
        return data

    # Default sensitive keys
    if sensitive_keys is None:
        sensitive_keys = [
            'password', 'passwd', 'pwd', 'secret', 'token',
            'api_key', 'apikey', 'access_token', 'refresh_token',
            'private_key', 'client_secret', 'auth_token'
        ]

    # Convert to lowercase for case-insensitive matching
    sensitive_keys_lower = [key.lower() for key in sensitive_keys]

    # Create masked copy
    masked_data = {}
    for key, value in data.items():
        if key.lower() in sensitive_keys_lower:
            masked_data[key] = mask_password(str(value)) if value else "****"
        elif isinstance(value, dict):
            masked_data[key] = mask_credentials_in_dict(value, sensitive_keys)
        elif isinstance(value, str) and any(sens in key.lower() for sens in ['password', 'secret', 'token']):
            # Catch variations like 'db_password', 'api_secret', etc.
            masked_data[key] = mask_password(value) if value else "****"
        else:
            masked_data[key] = value

    return masked_data


def safe_error_message(error: Exception, include_details: bool = False) -> str:
    """
    Generate a safe error message for display to users, hiding sensitive information.

    Args:
        error: The exception to format
        include_details: Whether to include technical details (only for logs)

    Returns:
        str: Safe error message
    """
    error_str = str(error)

    # Mask any passwords in error messages
    safe_message = mask_connection_string(error_str)

    # Remove SQL Server connection details if present
    safe_message = re.sub(
        r'\[SQL Server Native Client[^\]]*\]',
        '[SQL Server]',
        safe_message
    )

    # Mask IP addresses (optional - uncomment if needed)
    # safe_message = re.sub(
    #     r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
    #     'xxx.xxx.xxx.xxx',
    #     safe_message
    # )

    if not include_details:
        # For user-facing messages, provide generic error
        if 'connection' in safe_message.lower():
            return "Failed to connect to database. Please check your connection settings."
        elif 'login' in safe_message.lower() or 'authentication' in safe_message.lower():
            return "Authentication failed. Please check your credentials."
        elif 'permission' in safe_message.lower():
            return "Permission denied. Please contact your database administrator."
        else:
            return "An error occurred. Please check the logs for more information."

    return safe_message
