"""
SQL utility functions for consistent data cleaning across the application
"""

import re
from typing import Optional


def sanitize_sql_identifier(identifier: str, max_length: int = 128) -> str:
    """
    Sanitize SQL identifier (schema, table, column names) to prevent SQL injection.

    SQL Server identifiers rules:
    - Must start with letter, underscore, @, or #
    - Can contain letters, digits, @, $, #, _
    - Maximum 128 characters

    Args:
        identifier: The identifier to sanitize
        max_length: Maximum allowed length (default 128 for SQL Server)

    Returns:
        str: Sanitized identifier

    Raises:
        ValueError: If identifier is invalid or contains suspicious characters
    """
    if not identifier or not isinstance(identifier, str):
        raise ValueError("Identifier must be a non-empty string")

    # Trim whitespace
    identifier = identifier.strip()

    # Check length
    if len(identifier) > max_length:
        raise ValueError(f"Identifier too long (max {max_length} characters): {identifier[:50]}...")

    # SQL Server identifier pattern - alphanumeric and underscore only for safety
    # This is more restrictive than SQL Server allows, but safer
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier):
        raise ValueError(
            f"Invalid SQL identifier: '{identifier}'. "
            "Must start with letter or underscore, contain only alphanumeric and underscore characters."
        )

    # Blacklist dangerous keywords (case-insensitive)
    dangerous_keywords = {
        'drop', 'delete', 'truncate', 'exec', 'execute', 'sp_executesql',
        'xp_cmdshell', 'alter', 'create', 'insert', 'update', 'grant', 'revoke'
    }

    if identifier.lower() in dangerous_keywords:
        raise ValueError(f"Identifier cannot be a SQL keyword: {identifier}")

    return identifier


def quote_identifier(identifier: str) -> str:
    """
    Safely quote a SQL Server identifier with square brackets after sanitization.

    Args:
        identifier: The identifier to quote

    Returns:
        str: Quoted identifier like [table_name]

    Raises:
        ValueError: If identifier is invalid
    """
    # First sanitize the identifier
    safe_identifier = sanitize_sql_identifier(identifier)

    # Return with square brackets
    return f"[{safe_identifier}]"


def build_qualified_table_name(schema_name: str, table_name: str) -> str:
    """
    Build a safely quoted qualified table name (schema.table).

    Args:
        schema_name: Schema name
        table_name: Table name

    Returns:
        str: Qualified table name like [schema].[table]

    Raises:
        ValueError: If identifiers are invalid
    """
    safe_schema = quote_identifier(schema_name)
    safe_table = quote_identifier(table_name)
    return f"{safe_schema}.{safe_table}"


def validate_identifier_list(identifiers: list) -> bool:
    """
    Validate a list of SQL identifiers.

    Args:
        identifiers: List of identifier strings

    Returns:
        bool: True if all identifiers are valid

    Raises:
        ValueError: If any identifier is invalid
    """
    if not isinstance(identifiers, list):
        raise ValueError("identifiers must be a list")

    for identifier in identifiers:
        sanitize_sql_identifier(identifier)

    return True


def get_numeric_cleaning_expression(col_name: str) -> str:
    """
    Generate SQL expression for cleaning numeric data consistently
    
    This function ensures that both validation and data transfer use the same
    cleaning logic to avoid inconsistencies.
    
    Args:
        col_name: Column name to clean
        
    Returns:
        str: SQL expression that cleans the column data
    """
    safe_col = f"[{col_name}]"
    return f"NULLIF(LTRIM(RTRIM(REPLACE(REPLACE(REPLACE({safe_col}, '\"', ''), ',', ''), ' ', ''))), '-')"


def get_date_cleaning_expression(col_name: str) -> str:
    """
    Generate SQL expression for cleaning date data consistently
    
    Args:
        col_name: Column name to clean
        
    Returns:
        str: SQL expression that cleans the column data for dates
    """
    safe_col = f"[{col_name}]"
    return f"""NULLIF(LTRIM(RTRIM(REPLACE(REPLACE(REPLACE(TRANSLATE({safe_col}, CHAR(9) + CHAR(10) + CHAR(13) + CHAR(160) + ',', '     '), NCHAR(65279), ''), NCHAR(8203), ''), NCHAR(8288), ''))), '-')"""


def get_basic_cleaning_expression(col_name: str) -> str:
    """
    Generate SQL expression for basic string cleaning
    
    Args:
        col_name: Column name to clean
        
    Returns:
        str: SQL expression that trims the column
    """
    safe_col = f"[{col_name}]"
    return f"LTRIM(RTRIM({safe_col}))"


def get_cleaning_expression(col_name: str, cleaning_type: str = 'basic') -> str:
    """
    Generate SQL expression for data cleaning based on type
    
    Args:
        col_name: Column name to clean
        cleaning_type: Type of cleaning ('basic', 'numeric', 'date')
        
    Returns:
        str: SQL expression for cleaning
    """
    if cleaning_type == 'basic':
        return get_basic_cleaning_expression(col_name)
    elif cleaning_type == 'numeric':
        return get_numeric_cleaning_expression(col_name)
    elif cleaning_type == 'date':
        return get_date_cleaning_expression(col_name)
    else:
        raise ValueError(f"Unknown cleaning_type: {cleaning_type}")