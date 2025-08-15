"""
Date and DateTime validation module
"""

from typing import List, Dict
from sqlalchemy import text
from sqlalchemy.types import DATE, DateTime

from .base_validator import BaseValidator


class DateValidator(BaseValidator):
    """
    Validator สำหรับตรวจสอบข้อมูลวันที่และเวลา
    
    ตรวจสอบว่าข้อมูลในคอลัมน์สามารถแปลงเป็นวันที่ได้หรือไม่
    รองรับรูปแบบวันที่ต่างๆ ตาม date_format ที่กำหนด
    """
    
    def validate(self, conn, staging_table: str, schema_name: str, columns: List, 
                total_rows: int, chunk_size: int, log_func=None, **kwargs) -> List[Dict]:
        """
        ตรวจสอบข้อมูลวันที่ในคอลัมน์ต่างๆ
        
        Args:
            conn: Database connection
            staging_table: Staging table name
            schema_name: Schema name
            columns: List of column names to validate
            total_rows: Total number of rows
            chunk_size: Chunk size for processing (unused in this implementation)
            log_func: Logging function
            **kwargs: Additional parameters including 'date_format'
            
        Returns:
            List[Dict]: List of validation issues
        """
        issues = []
        date_format = kwargs.get('date_format', 'UK')
        
        for col in columns:
            try:
                issue = self._validate_single_date_column(
                    conn, staging_table, schema_name, col, total_rows, date_format, log_func
                )
                if issue:
                    issues.append(issue)
            except Exception as e:
                if log_func:
                    log_func(f"        ⚠️ Error checking column {col}: {e}")
        
        return issues
    
    def _validate_single_date_column(self, conn, staging_table: str, schema_name: str, 
                                    col: str, total_rows: int, date_format: str, log_func) -> Dict:
        """
        ตรวจสอบคอลัมน์วันที่เดียว
        
        Args:
            conn: Database connection
            staging_table: Staging table name
            schema_name: Schema name
            col: Column name
            total_rows: Total number of rows
            date_format: Date format preference ('UK' or 'US')
            log_func: Logging function
            
        Returns:
            Dict: Validation issue หรือ None ถ้าไม่มีปัญหา
        """
        # สร้าง expression สำหรับทำความสะอาดข้อมูล
        cleaned_col_expression = self.get_cleaned_column_expression(col, 'date')
        
        # สร้าง query สำหรับตรวจสอบรูปแบบวันที่
        error_query = self._build_date_validation_query(
            staging_table, schema_name, cleaned_col_expression, date_format
        )
        
        result = self.execute_query_safely(
            conn, error_query, f"Error checking date column {col}", log_func
        )
        
        if result is None:
            return None
            
        error_count = result.scalar()
        
        if error_count > 0:
            # ดึงข้อมูล debug เพิ่มเติม
            debug_info = self._get_date_debug_info(
                conn, staging_table, schema_name, cleaned_col_expression, col
            )
            
            # ดึงตัวอย่างข้อมูลที่มีปัญหา
            where_condition = self._build_date_error_condition(cleaned_col_expression, date_format)
            examples = self.get_sample_examples(
                conn, staging_table, schema_name, where_condition, col
            )
            
            return self.create_issue_dict(
                validation_type='date_validation',
                column=col,
                error_count=error_count,
                total_rows=total_rows,
                examples=examples,
                date_format_used=date_format,
                debug_info=debug_info[:3]
            )
        
        return None
    
    def _build_date_validation_query(self, staging_table: str, schema_name: str, 
                                   cleaned_col_expression: str, date_format: str) -> str:
        """
        สร้าง SQL query สำหรับตรวจสอบรูปแบบวันที่
        
        Args:
            staging_table: Staging table name
            schema_name: Schema name
            cleaned_col_expression: Cleaned column expression
            date_format: Date format preference ('UK' or 'US')
            
        Returns:
            str: SQL query
        """
        if date_format == 'UK':  # DD-MM format
            query = f"""
                SELECT COUNT(*) as error_count
                FROM {schema_name}.{staging_table}
                WHERE {cleaned_col_expression} IS NOT NULL
                AND CASE 
                    WHEN TRY_CONVERT(DATETIME, {cleaned_col_expression}, 103) IS NOT NULL THEN 1  -- DD/MM/YYYY
                    WHEN TRY_CONVERT(DATETIME, {cleaned_col_expression}, 104) IS NOT NULL THEN 1  -- DD.MM.YYYY
                    WHEN TRY_CONVERT(DATETIME, {cleaned_col_expression}, 105) IS NOT NULL THEN 1  -- DD-MM-YYYY
                    WHEN TRY_CONVERT(DATETIME, {cleaned_col_expression}, 121) IS NOT NULL THEN 1  -- YYYY-MM-DD HH:MI:SS
                    WHEN TRY_CONVERT(DATETIME, {cleaned_col_expression}, 101) IS NOT NULL THEN 1  -- MM/DD/YYYY (fallback)
                    ELSE 0
                END = 0
            """
        else:  # US format - MM-DD
            query = f"""
                SELECT COUNT(*) as error_count
                FROM {schema_name}.{staging_table}
                WHERE {cleaned_col_expression} IS NOT NULL
                AND CASE 
                    WHEN TRY_CONVERT(DATETIME, {cleaned_col_expression}, 101) IS NOT NULL THEN 1  -- MM/DD/YYYY
                    WHEN TRY_CONVERT(DATETIME, {cleaned_col_expression}, 102) IS NOT NULL THEN 1  -- MM.DD.YYYY
                    WHEN TRY_CONVERT(DATETIME, {cleaned_col_expression}, 110) IS NOT NULL THEN 1  -- MM-DD-YYYY
                    WHEN TRY_CONVERT(DATETIME, {cleaned_col_expression}, 121) IS NOT NULL THEN 1  -- YYYY-MM-DD HH:MI:SS
                    WHEN TRY_CONVERT(DATETIME, {cleaned_col_expression}, 103) IS NOT NULL THEN 1  -- DD/MM/YYYY (fallback)
                    ELSE 0
                END = 0
            """
        
        return query
    
    def _build_date_error_condition(self, cleaned_col_expression: str, date_format: str) -> str:
        """
        สร้าง WHERE condition สำหรับหาข้อมูลที่มีปัญหา
        
        Args:
            cleaned_col_expression: Cleaned column expression
            date_format: Date format preference ('UK' or 'US')
            
        Returns:
            str: WHERE condition
        """
        if date_format == 'UK':
            return f"""
                {cleaned_col_expression} IS NOT NULL
                AND CASE 
                    WHEN TRY_CONVERT(DATETIME, {cleaned_col_expression}, 103) IS NOT NULL THEN 1
                    WHEN TRY_CONVERT(DATETIME, {cleaned_col_expression}, 104) IS NOT NULL THEN 1
                    WHEN TRY_CONVERT(DATETIME, {cleaned_col_expression}, 105) IS NOT NULL THEN 1
                    WHEN TRY_CONVERT(DATETIME, {cleaned_col_expression}, 121) IS NOT NULL THEN 1
                    WHEN TRY_CONVERT(DATETIME, {cleaned_col_expression}, 101) IS NOT NULL THEN 1
                    ELSE 0
                END = 0
            """
        else:
            return f"""
                {cleaned_col_expression} IS NOT NULL
                AND CASE 
                    WHEN TRY_CONVERT(DATETIME, {cleaned_col_expression}, 101) IS NOT NULL THEN 1
                    WHEN TRY_CONVERT(DATETIME, {cleaned_col_expression}, 102) IS NOT NULL THEN 1
                    WHEN TRY_CONVERT(DATETIME, {cleaned_col_expression}, 110) IS NOT NULL THEN 1
                    WHEN TRY_CONVERT(DATETIME, {cleaned_col_expression}, 121) IS NOT NULL THEN 1
                    WHEN TRY_CONVERT(DATETIME, {cleaned_col_expression}, 103) IS NOT NULL THEN 1
                    ELSE 0
                END = 0
            """
    
    def _get_date_debug_info(self, conn, staging_table: str, schema_name: str, 
                           cleaned_col_expression: str, col: str) -> List[str]:
        """
        ดึงข้อมูล debug สำหรับการแสดงรายละเอียดปัญหา
        
        Args:
            conn: Database connection
            staging_table: Staging table name
            schema_name: Schema name
            cleaned_col_expression: Cleaned column expression
            col: Column name
            
        Returns:
            List[str]: Debug information
        """
        safe_col = self.safe_column_name(col)
        debug_query = f"""
            SELECT TOP 5 {safe_col} as raw_value, 
                           {cleaned_col_expression} as cleaned_value,
                           TRY_CONVERT(DATETIME, {cleaned_col_expression}, 103) as uk_103,
                           TRY_CONVERT(DATETIME, {cleaned_col_expression}, 104) as uk_104,
                           TRY_CONVERT(DATETIME, {cleaned_col_expression}, 105) as uk_105,
                           TRY_CONVERT(DATETIME, {cleaned_col_expression}, 121) as iso_121,
                           TRY_CONVERT(DATETIME, {cleaned_col_expression}, 101) as us_101
            FROM {schema_name}.{staging_table}
            WHERE {cleaned_col_expression} IS NOT NULL
            AND CASE 
                WHEN TRY_CONVERT(DATETIME, {cleaned_col_expression}, 103) IS NOT NULL THEN 1
                WHEN TRY_CONVERT(DATETIME, {cleaned_col_expression}, 104) IS NOT NULL THEN 1
                WHEN TRY_CONVERT(DATETIME, {cleaned_col_expression}, 105) IS NOT NULL THEN 1
                WHEN TRY_CONVERT(DATETIME, {cleaned_col_expression}, 121) IS NOT NULL THEN 1
                WHEN TRY_CONVERT(DATETIME, {cleaned_col_expression}, 101) IS NOT NULL THEN 1
                ELSE 0
            END = 0
            ORDER BY {safe_col}
        """
        
        try:
            result = conn.execute(text(debug_query))
            debug_rows = result.fetchall()
            
            debug_info = []
            for row in debug_rows:
                debug_info.append(f"Raw: '{row.raw_value}' -> Cleaned: '{row.cleaned_value}'")
            
            return debug_info
        except Exception:
            return []
    
    def get_date_columns(self, required_cols: Dict) -> List[str]:
        """
        ดึงรายชื่อคอลัมน์ที่เป็นประเภทวันที่
        
        Args:
            required_cols: Dictionary ของคอลัมน์และ data types
            
        Returns:
            List[str]: List of date column names
        """
        date_columns = []
        for col, dtype in required_cols.items():
            if isinstance(dtype, (DATE, DateTime)):
                date_columns.append(col)
        
        return date_columns
    
    def validate_date_range(self, conn, staging_table: str, schema_name: str, 
                           col: str, min_date=None, max_date=None, 
                           total_rows: int = 0, date_format: str = 'UK', log_func=None) -> Dict:
        """
        ตรวจสอบว่าข้อมูลวันที่อยู่ในช่วงที่กำหนดหรือไม่
        
        Args:
            conn: Database connection
            staging_table: Staging table name
            schema_name: Schema name
            col: Column name
            min_date: Minimum allowed date (string)
            max_date: Maximum allowed date (string)
            total_rows: Total number of rows
            date_format: Date format preference
            log_func: Logging function
            
        Returns:
            Dict: Validation issue หรือ None ถ้าไม่มีปัญหา
        """
        if min_date is None and max_date is None:
            return None
            
        cleaned_col_expression = self.get_cleaned_column_expression(col, 'date')
        conditions = []
        
        # สร้าง conversion ตาม date format
        if date_format == 'UK':
            date_conversion = f"TRY_CONVERT(DATETIME, {cleaned_col_expression}, 103)"
        else:
            date_conversion = f"TRY_CONVERT(DATETIME, {cleaned_col_expression}, 101)"
        
        if min_date is not None:
            conditions.append(f"{date_conversion} < '{min_date}'")
        
        if max_date is not None:
            conditions.append(f"{date_conversion} > '{max_date}'")
        
        where_condition = " OR ".join(conditions)
        where_condition += f" AND {date_conversion} IS NOT NULL"
        
        error_query = f"""
            SELECT COUNT(*) as error_count
            FROM {schema_name}.{staging_table}
            WHERE {where_condition}
        """
        
        result = self.execute_query_safely(
            conn, error_query, f"Error checking date range for column {col}", log_func
        )
        
        if result is None:
            return None
            
        error_count = result.scalar()
        
        if error_count > 0:
            examples = self.get_sample_examples(
                conn, staging_table, schema_name, where_condition, col
            )
            
            range_info = []
            if min_date is not None:
                range_info.append(f"min: {min_date}")
            if max_date is not None:
                range_info.append(f"max: {max_date}")
            
            return self.create_issue_dict(
                validation_type='date_range_validation',
                column=col,
                error_count=error_count,
                total_rows=total_rows,
                examples=examples,
                allowed_range=", ".join(range_info),
                date_format_used=date_format
            )
        
        return None
