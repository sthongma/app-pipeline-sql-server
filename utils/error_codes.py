"""
Standardized error codes and messages for SQL Server Pipeline

Error Code Format: PPE-CCCC
- PP: Category (DB=Database, FL=File, VL=Validation, CF=Configuration, SC=Security)
- CCCC: Unique error number

Usage:
    from utils.error_codes import ErrorCode, get_error_message

    # Raise standardized error
    raise Exception(get_error_message(ErrorCode.DB_CONNECTION_FAILED, server="localhost"))
"""

from enum import Enum
from typing import Optional


class ErrorCode(Enum):
    """Standardized error codes"""

    # Database Errors (DB-XXXX)
    DB_CONNECTION_FAILED = "DB-1001"
    DB_CONNECTION_TIMEOUT = "DB-1002"
    DB_AUTHENTICATION_FAILED = "DB-1003"
    DB_PERMISSION_DENIED = "DB-1004"
    DB_SCHEMA_NOT_FOUND = "DB-1005"
    DB_TABLE_NOT_FOUND = "DB-1006"
    DB_QUERY_FAILED = "DB-1007"
    DB_TRANSACTION_FAILED = "DB-1008"
    DB_POOL_EXHAUSTED = "DB-1009"

    # File Errors (FL-XXXX)
    FL_FILE_NOT_FOUND = "FL-2001"
    FL_FILE_READ_ERROR = "FL-2002"
    FL_FILE_WRITE_ERROR = "FL-2003"
    FL_FILE_FORMAT_INVALID = "FL-2004"
    FL_FILE_SIZE_EXCEEDED = "FL-2005"
    FL_FILE_ENCODING_ERROR = "FL-2006"
    FL_FILE_PERMISSION_DENIED = "FL-2007"

    # Validation Errors (VL-XXXX)
    VL_DATA_TYPE_MISMATCH = "VL-3001"
    VL_NULL_VALUE_NOT_ALLOWED = "VL-3002"
    VL_VALUE_OUT_OF_RANGE = "VL-3003"
    VL_INVALID_DATE_FORMAT = "VL-3004"
    VL_INVALID_NUMBER_FORMAT = "VL-3005"
    VL_STRING_TOO_LONG = "VL-3006"
    VL_DUPLICATE_KEY = "VL-3007"
    VL_CONSTRAINT_VIOLATION = "VL-3008"

    # Configuration Errors (CF-XXXX)
    CF_CONFIG_NOT_FOUND = "CF-4001"
    CF_CONFIG_INVALID = "CF-4002"
    CF_CONFIG_MISSING_FIELD = "CF-4003"
    CF_ENV_VARIABLE_NOT_SET = "CF-4004"
    CF_SETTINGS_LOAD_FAILED = "CF-4005"

    # Security Errors (SC-XXXX)
    SC_SQL_INJECTION_DETECTED = "SC-5001"
    SC_INVALID_IDENTIFIER = "SC-5002"
    SC_CREDENTIAL_INVALID = "SC-5003"
    SC_ACCESS_DENIED = "SC-5004"
    SC_SECURITY_SCAN_FAILED = "SC-5005"


# Error message templates (English)
ERROR_MESSAGES = {
    # Database
    ErrorCode.DB_CONNECTION_FAILED: "Failed to connect to database server '{server}'. Please check connection settings and ensure SQL Server is running.",
    ErrorCode.DB_CONNECTION_TIMEOUT: "Connection to database timed out after {timeout} seconds. Server may be overloaded or unreachable.",
    ErrorCode.DB_AUTHENTICATION_FAILED: "Database authentication failed for user '{username}'. Please check credentials.",
    ErrorCode.DB_PERMISSION_DENIED: "Permission denied for operation '{operation}' on database '{database}'. Contact database administrator.",
    ErrorCode.DB_SCHEMA_NOT_FOUND: "Schema '{schema}' not found in database '{database}'.",
    ErrorCode.DB_TABLE_NOT_FOUND: "Table '{table}' not found in schema '{schema}'.",
    ErrorCode.DB_QUERY_FAILED: "Database query failed: {error}",
    ErrorCode.DB_TRANSACTION_FAILED: "Database transaction failed: {error}",
    ErrorCode.DB_POOL_EXHAUSTED: "Connection pool exhausted. Maximum {max_connections} connections reached.",

    # File
    ErrorCode.FL_FILE_NOT_FOUND: "File not found: '{filepath}'. Please check the file path.",
    ErrorCode.FL_FILE_READ_ERROR: "Error reading file '{filename}': {error}",
    ErrorCode.FL_FILE_WRITE_ERROR: "Error writing file '{filename}': {error}",
    ErrorCode.FL_FILE_FORMAT_INVALID: "Invalid file format for '{filename}'. Expected {expected_format}.",
    ErrorCode.FL_FILE_SIZE_EXCEEDED: "File size ({size_mb}MB) exceeds maximum allowed ({max_mb}MB).",
    ErrorCode.FL_FILE_ENCODING_ERROR: "File encoding error in '{filename}'. Try UTF-8, CP874, or Latin1.",
    ErrorCode.FL_FILE_PERMISSION_DENIED: "Permission denied accessing file '{filepath}'.",

    # Validation
    ErrorCode.VL_DATA_TYPE_MISMATCH: "Data type mismatch in column '{column}': expected {expected}, got {actual}.",
    ErrorCode.VL_NULL_VALUE_NOT_ALLOWED: "NULL value not allowed in column '{column}' (row {row_number}).",
    ErrorCode.VL_VALUE_OUT_OF_RANGE: "Value out of range in column '{column}': {value} (row {row_number}).",
    ErrorCode.VL_INVALID_DATE_FORMAT: "Invalid date format in column '{column}': '{value}' (row {row_number}).",
    ErrorCode.VL_INVALID_NUMBER_FORMAT: "Invalid number format in column '{column}': '{value}' (row {row_number}).",
    ErrorCode.VL_STRING_TOO_LONG: "String too long in column '{column}': {length} characters (max {max_length}).",
    ErrorCode.VL_DUPLICATE_KEY: "Duplicate key value in column(s) '{columns}': {value}.",
    ErrorCode.VL_CONSTRAINT_VIOLATION: "Constraint violation: {constraint_name} - {details}",

    # Configuration
    ErrorCode.CF_CONFIG_NOT_FOUND: "Configuration file not found: '{config_file}'.",
    ErrorCode.CF_CONFIG_INVALID: "Invalid configuration in '{config_file}': {error}",
    ErrorCode.CF_CONFIG_MISSING_FIELD: "Required configuration field missing: '{field}'.",
    ErrorCode.CF_ENV_VARIABLE_NOT_SET: "Environment variable not set: '{variable}'. Please check .env file.",
    ErrorCode.CF_SETTINGS_LOAD_FAILED: "Failed to load settings from '{file}': {error}",

    # Security
    ErrorCode.SC_SQL_INJECTION_DETECTED: "Potential SQL injection detected in input: '{input}'. Request blocked for security.",
    ErrorCode.SC_INVALID_IDENTIFIER: "Invalid SQL identifier '{identifier}': {reason}",
    ErrorCode.SC_CREDENTIAL_INVALID: "Invalid credentials provided. Please check username and password.",
    ErrorCode.SC_ACCESS_DENIED: "Access denied to resource '{resource}'. Insufficient permissions.",
    ErrorCode.SC_SECURITY_SCAN_FAILED: "Security scan failed: {error}",
}


def get_error_message(error_code: ErrorCode, **kwargs) -> str:
    """
    Get formatted error message for error code

    Args:
        error_code: ErrorCode enum value
        **kwargs: Variables to format into message template

    Returns:
        str: Formatted error message with code

    Example:
        >>> get_error_message(ErrorCode.DB_CONNECTION_FAILED, server="localhost")
        '[DB-1001] Failed to connect to database server localhost. ...'
    """
    template = ERROR_MESSAGES.get(error_code, "Unknown error: {error_code}")

    try:
        message = template.format(**kwargs)
    except KeyError:
        # If formatting fails, return template with available args
        message = template + f" (Missing parameters: {kwargs})"

    return f"[{error_code.value}] {message}"


def get_user_friendly_message(error_code: ErrorCode) -> str:
    """
    Get user-friendly error message (less technical)

    Args:
        error_code: ErrorCode enum value

    Returns:
        str: Simplified error message for end users
    """
    user_messages = {
        # Database - simplified
        ErrorCode.DB_CONNECTION_FAILED: "Unable to connect to database. Please check your settings.",
        ErrorCode.DB_CONNECTION_TIMEOUT: "Database connection timed out. Please try again.",
        ErrorCode.DB_AUTHENTICATION_FAILED: "Database login failed. Please check your credentials.",
        ErrorCode.DB_PERMISSION_DENIED: "You don't have permission for this operation. Contact administrator.",

        # File - simplified
        ErrorCode.FL_FILE_NOT_FOUND: "File not found. Please check the file path.",
        ErrorCode.FL_FILE_READ_ERROR: "Unable to read file. File may be corrupted or in use.",
        ErrorCode.FL_FILE_FORMAT_INVALID: "Invalid file format. Please use Excel (.xlsx, .xls) or CSV (.csv) files.",

        # Validation - simplified
        ErrorCode.VL_DATA_TYPE_MISMATCH: "Data format error. Please check your data.",
        ErrorCode.VL_NULL_VALUE_NOT_ALLOWED: "Missing required value. Please fill in all required fields.",
        ErrorCode.VL_INVALID_DATE_FORMAT: "Invalid date format. Please use proper date format.",

        # Configuration - simplified
        ErrorCode.CF_CONFIG_NOT_FOUND: "Configuration not found. Please set up application settings.",
        ErrorCode.CF_ENV_VARIABLE_NOT_SET: "Application not configured. Please check .env file.",

        # Security - simplified
        ErrorCode.SC_SQL_INJECTION_DETECTED: "Invalid input detected. Please check your data.",
        ErrorCode.SC_INVALID_IDENTIFIER: "Invalid name. Please use only letters, numbers, and underscores.",
    }

    return user_messages.get(error_code, "An error occurred. Please check the logs for details.")


class PipelineException(Exception):
    """
    Base exception class for SQL Server Pipeline

    All custom exceptions should inherit from this class
    """

    def __init__(self, error_code: ErrorCode, user_facing: bool = False, **kwargs):
        """
        Initialize PipelineException

        Args:
            error_code: ErrorCode enum value
            user_facing: If True, use simplified user-friendly message
            **kwargs: Variables for error message formatting
        """
        self.error_code = error_code

        if user_facing:
            message = get_user_friendly_message(error_code)
        else:
            message = get_error_message(error_code, **kwargs)

        super().__init__(message)


# Specific exception classes
class DatabaseException(PipelineException):
    """Database-related exceptions"""
    pass


class FileException(PipelineException):
    """File operation exceptions"""
    pass


class ValidationException(PipelineException):
    """Data validation exceptions"""
    pass


class ConfigurationException(PipelineException):
    """Configuration-related exceptions"""
    pass


class SecurityException(PipelineException):
    """Security-related exceptions"""
    pass
