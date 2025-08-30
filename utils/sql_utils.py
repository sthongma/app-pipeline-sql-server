"""
SQL utility functions for consistent data cleaning across the application
"""


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