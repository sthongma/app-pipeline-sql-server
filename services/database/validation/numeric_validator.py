"""
Numeric data validation module
"""

from typing import List, Dict
from sqlalchemy import text
from sqlalchemy.types import Integer as SA_Integer, Float as SA_Float

from .base_validator import BaseValidator


class NumericValidator(BaseValidator):
    """
    Validator สำหรับตรวจสอบข้อมูลตัวเลข
    
    ตรวจสอบว่าข้อมูลในคอลัมน์สามารถแปลงเป็นตัวเลขได้หรือไม่
    """
    
    def validate(self, conn, staging_table: str, schema_name: str, columns: List, 
                total_rows: int, chunk_size: int, log_func=None, **kwargs) -> List[Dict]:
        """
        ตรวจสอบข้อมูลตัวเลขในคอลัมน์ต่างๆ
        
        Args:
            conn: Database connection
            staging_table: Staging table name
            schema_name: Schema name
            columns: List of column names to validate
            total_rows: Total number of rows
            chunk_size: Chunk size for processing (unused in this implementation)
            log_func: Logging function
            **kwargs: Additional parameters
            
        Returns:
            List[Dict]: List of validation issues
        """
        issues = []
        
        for col in columns:
            try:
                issue = self._validate_single_numeric_column(
                    conn, staging_table, schema_name, col, total_rows, log_func
                )
                if issue:
                    issues.append(issue)
            except Exception as e:
                if log_func:
                    log_func(f"        Warning: Error checking column {col}: {e}")
        
        return issues
    
    def _validate_single_numeric_column(self, conn, staging_table: str, schema_name: str, 
                                       col: str, total_rows: int, log_func) -> Dict:
        """
        ตรวจสอบคอลัมน์ตัวเลขเดียว
        
        Args:
            conn: Database connection
            staging_table: Staging table name
            schema_name: Schema name
            col: Column name
            total_rows: Total number of rows
            log_func: Logging function
            
        Returns:
            Dict: Validation issue หรือ None ถ้าไม่มีปัญหา
        """
        # สร้าง expression สำหรับทำความสะอาดข้อมูล
        cleaned_col_expression = self.get_cleaned_column_expression(col, 'numeric')
        
        # นับจำนวน error
        error_query = f"""
            SELECT COUNT(*) as error_count
            FROM {schema_name}.{staging_table}
            WHERE TRY_CAST({cleaned_col_expression} AS FLOAT) IS NULL 
              AND NULLIF({cleaned_col_expression}, '') IS NOT NULL
        """
        
        result = self.execute_query_safely(
            conn, error_query, f"Error checking numeric column {col}", log_func
        )
        
        if result is None:
            return None
            
        error_count = result.scalar()
        
        if error_count > 0:
            # ดึงตัวอย่างข้อมูลที่มีปัญหา
            where_condition = f"""
                TRY_CAST({cleaned_col_expression} AS FLOAT) IS NULL 
                AND NULLIF({cleaned_col_expression}, '') IS NOT NULL
            """
            
            examples = self.get_sample_examples(
                conn, staging_table, schema_name, where_condition, col
            )
            
            return self.create_issue_dict(
                validation_type='numeric_validation',
                column=col,
                error_count=error_count,
                total_rows=total_rows,
                examples=examples
            )
        
        return None
    
    def get_numeric_columns(self, required_cols: Dict) -> List[str]:
        """
        ดึงรายชื่อคอลัมน์ที่เป็นประเภทตัวเลข
        
        Args:
            required_cols: Dictionary ของคอลัมน์และ data types
            
        Returns:
            List[str]: List of numeric column names
        """
        numeric_columns = []
        for col, dtype in required_cols.items():
            if isinstance(dtype, (SA_Integer, SA_Float)):
                numeric_columns.append(col)

        return numeric_columns
    
    def validate_numeric_range(self, conn, staging_table: str, schema_name: str, 
                              col: str, min_value=None, max_value=None, 
                              total_rows: int = 0, log_func=None) -> Dict:
        """
        ตรวจสอบว่าข้อมูลตัวเลขอยู่ในช่วงที่กำหนดหรือไม่
        
        Args:
            conn: Database connection
            staging_table: Staging table name
            schema_name: Schema name
            col: Column name
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            total_rows: Total number of rows
            log_func: Logging function
            
        Returns:
            Dict: Validation issue หรือ None ถ้าไม่มีปัญหา
        """
        if min_value is None and max_value is None:
            return None
            
        cleaned_col_expression = self.get_cleaned_column_expression(col, 'numeric')
        conditions = []
        
        if min_value is not None:
            conditions.append(f"TRY_CAST({cleaned_col_expression} AS FLOAT) < {min_value}")
        
        if max_value is not None:
            conditions.append(f"TRY_CAST({cleaned_col_expression} AS FLOAT) > {max_value}")
        
        where_condition = " OR ".join(conditions)
        where_condition += f" AND TRY_CAST({cleaned_col_expression} AS FLOAT) IS NOT NULL"
        
        error_query = f"""
            SELECT COUNT(*) as error_count
            FROM {schema_name}.{staging_table}
            WHERE {where_condition}
        """
        
        result = self.execute_query_safely(
            conn, error_query, f"Error checking numeric range for column {col}", log_func
        )
        
        if result is None:
            return None
            
        error_count = result.scalar()
        
        if error_count > 0:
            examples = self.get_sample_examples(
                conn, staging_table, schema_name, where_condition, col
            )
            
            range_info = []
            if min_value is not None:
                range_info.append(f"min: {min_value}")
            if max_value is not None:
                range_info.append(f"max: {max_value}")
            
            return self.create_issue_dict(
                validation_type='numeric_range_validation',
                column=col,
                error_count=error_count,
                total_rows=total_rows,
                examples=examples,
                allowed_range=", ".join(range_info)
            )
        
        return None
