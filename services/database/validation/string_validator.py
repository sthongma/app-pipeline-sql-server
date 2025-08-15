"""
String length validation module
"""

from typing import List, Dict, Tuple
from sqlalchemy import text
from sqlalchemy.types import NVARCHAR as SA_NVARCHAR

from .base_validator import BaseValidator


class StringValidator(BaseValidator):
    """
    Validator สำหรับตรวจสอบความยาวของ string
    
    ตรวจสอบว่าข้อมูลในคอลัมน์ไม่เกินความยาวที่กำหนด
    """
    
    def validate(self, conn, staging_table: str, schema_name: str, columns: List, 
                total_rows: int, chunk_size: int, log_func=None, **kwargs) -> List[Dict]:
        """
        ตรวจสอบความยาวของ string ในคอลัมน์ต่างๆ
        
        Args:
            conn: Database connection
            staging_table: Staging table name
            schema_name: Schema name
            columns: List of tuples (column_name, max_length) to validate
            total_rows: Total number of rows
            chunk_size: Chunk size for processing (unused in this implementation)
            log_func: Logging function
            **kwargs: Additional parameters
            
        Returns:
            List[Dict]: List of validation issues
        """
        issues = []
        
        for col, max_length in columns:
            try:
                issue = self._validate_single_string_column(
                    conn, staging_table, schema_name, col, max_length, total_rows, log_func
                )
                if issue:
                    issues.append(issue)
            except Exception as e:
                if log_func:
                    log_func(f"        ⚠️ Error checking column {col}: {e}")
        
        return issues
    
    def _validate_single_string_column(self, conn, staging_table: str, schema_name: str, 
                                      col: str, max_length: int, total_rows: int, log_func) -> Dict:
        """
        ตรวจสอบความยาวของ string คอลัมน์เดียว
        
        Args:
            conn: Database connection
            staging_table: Staging table name
            schema_name: Schema name
            col: Column name
            max_length: Maximum allowed length
            total_rows: Total number of rows
            log_func: Logging function
            
        Returns:
            Dict: Validation issue หรือ None ถ้าไม่มีปัญหา
        """
        safe_col = self.safe_column_name(col)
        
        # นับจำนวน error
        error_query = f"""
            SELECT COUNT(*) as error_count
            FROM {schema_name}.{staging_table}
            WHERE LEN(ISNULL({safe_col}, '')) > {max_length}
        """
        
        result = self.execute_query_safely(
            conn, error_query, f"Error checking string length for column {col}", log_func
        )
        
        if result is None:
            return None
            
        error_count = result.scalar()
        
        if error_count > 0:
            # ดึงตัวอย่างข้อมูลที่มีปัญหา (แสดงเฉพาะ 30 ตัวอักษรแรก)
            examples_query = f"""
                SELECT TOP 3 LEFT({safe_col}, 30) + '...' as example_value
                FROM {schema_name}.{staging_table}
                WHERE LEN(ISNULL({safe_col}, '')) > {max_length}
            """
            
            examples_result = self.execute_query_safely(
                conn, examples_query, f"Error getting examples for column {col}", log_func
            )
            
            examples = []
            if examples_result:
                examples = [str(row.example_value) for row in examples_result.fetchall()]
            
            return self.create_issue_dict(
                validation_type='string_length_validation',
                column=col,
                error_count=error_count,
                total_rows=total_rows,
                examples=examples,
                max_length=max_length
            )
        
        return None
    
    def get_string_columns_with_length(self, required_cols: Dict) -> List[Tuple[str, int]]:
        """
        ดึงรายชื่อคอลัมน์ที่เป็นประเภท string พร้อมความยาวสูงสุด
        
        Args:
            required_cols: Dictionary ของคอลัมน์และ data types
            
        Returns:
            List[Tuple[str, int]]: List of tuples (column_name, max_length)
        """
        string_columns = []
        for col, dtype in required_cols.items():
            if isinstance(dtype, SA_NVARCHAR) and hasattr(dtype, 'length') and dtype.length:
                string_columns.append((col, dtype.length))
        
        return string_columns
    
    def validate_string_pattern(self, conn, staging_table: str, schema_name: str, 
                              col: str, pattern: str, pattern_name: str = "pattern",
                              total_rows: int = 0, log_func=None) -> Dict:
        """
        ตรวจสอบว่าข้อมูล string ตรงตาม pattern ที่กำหนดหรือไม่
        
        Args:
            conn: Database connection
            staging_table: Staging table name
            schema_name: Schema name
            col: Column name
            pattern: SQL LIKE pattern หรือ regex pattern
            pattern_name: ชื่อของ pattern สำหรับแสดงใน error message
            total_rows: Total number of rows
            log_func: Logging function
            
        Returns:
            Dict: Validation issue หรือ None ถ้าไม่มีปัญหา
        """
        safe_col = self.safe_column_name(col)
        
        # ใช้ LIKE pattern หรือ PATINDEX สำหรับ regex
        if '%' in pattern or '_' in pattern:
            # LIKE pattern
            where_condition = f"{safe_col} NOT LIKE '{pattern}' AND {safe_col} IS NOT NULL AND {safe_col} != ''"
        else:
            # Regex pattern (ใช้ PATINDEX)
            where_condition = f"PATINDEX('{pattern}', {safe_col}) = 0 AND {safe_col} IS NOT NULL AND {safe_col} != ''"
        
        error_query = f"""
            SELECT COUNT(*) as error_count
            FROM {schema_name}.{staging_table}
            WHERE {where_condition}
        """
        
        result = self.execute_query_safely(
            conn, error_query, f"Error checking string pattern for column {col}", log_func
        )
        
        if result is None:
            return None
            
        error_count = result.scalar()
        
        if error_count > 0:
            examples = self.get_sample_examples(
                conn, staging_table, schema_name, where_condition, col
            )
            
            return self.create_issue_dict(
                validation_type='string_pattern_validation',
                column=col,
                error_count=error_count,
                total_rows=total_rows,
                examples=examples,
                expected_pattern=pattern,
                pattern_name=pattern_name
            )
        
        return None
    
    def validate_string_not_empty(self, conn, staging_table: str, schema_name: str, 
                                 columns: List[str], total_rows: int = 0, log_func=None) -> List[Dict]:
        """
        ตรวจสอบว่าคอลัมน์ที่จำเป็นไม่เป็นค่าว่าง
        
        Args:
            conn: Database connection
            staging_table: Staging table name
            schema_name: Schema name
            columns: List of column names that should not be empty
            total_rows: Total number of rows
            log_func: Logging function
            
        Returns:
            List[Dict]: List of validation issues
        """
        issues = []
        
        for col in columns:
            safe_col = self.safe_column_name(col)
            
            where_condition = f"({safe_col} IS NULL OR LTRIM(RTRIM({safe_col})) = '')"
            
            error_query = f"""
                SELECT COUNT(*) as error_count
                FROM {schema_name}.{staging_table}
                WHERE {where_condition}
            """
            
            result = self.execute_query_safely(
                conn, error_query, f"Error checking empty values for column {col}", log_func
            )
            
            if result is None:
                continue
                
            error_count = result.scalar()
            
            if error_count > 0:
                # สำหรับ empty values ไม่ต้องดึง examples
                issue = self.create_issue_dict(
                    validation_type='string_not_empty_validation',
                    column=col,
                    error_count=error_count,
                    total_rows=total_rows,
                    examples=["NULL or empty values"]
                )
                issues.append(issue)
        
        return issues
    
    def get_string_statistics(self, conn, staging_table: str, schema_name: str, 
                            col: str, log_func=None) -> Dict:
        """
        ดึงสถิติของข้อมูล string ในคอลัมน์
        
        Args:
            conn: Database connection
            staging_table: Staging table name
            schema_name: Schema name
            col: Column name
            log_func: Logging function
            
        Returns:
            Dict: String statistics
        """
        safe_col = self.safe_column_name(col)
        
        stats_query = f"""
            SELECT 
                COUNT(*) as total_count,
                COUNT({safe_col}) as non_null_count,
                COUNT(CASE WHEN LTRIM(RTRIM({safe_col})) = '' THEN 1 END) as empty_count,
                MIN(LEN({safe_col})) as min_length,
                MAX(LEN({safe_col})) as max_length,
                AVG(CAST(LEN({safe_col}) AS FLOAT)) as avg_length
            FROM {schema_name}.{staging_table}
        """
        
        result = self.execute_query_safely(
            conn, stats_query, f"Error getting string statistics for column {col}", log_func
        )
        
        if result is None:
            return {}
            
        row = result.fetchone()
        
        return {
            'column': col,
            'total_count': row.total_count,
            'non_null_count': row.non_null_count,
            'empty_count': row.empty_count,
            'null_count': row.total_count - row.non_null_count,
            'min_length': row.min_length or 0,
            'max_length': row.max_length or 0,
            'avg_length': round(row.avg_length or 0, 2)
        }
