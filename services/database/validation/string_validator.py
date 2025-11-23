"""
String validation module
"""

from typing import List, Dict
from sqlalchemy import text

from .base_validator import BaseValidator


class StringValidator(BaseValidator):
    """
    Validator สำหรับตรวจสอบ string data

    เนื่องจากระบบใช้ NVARCHAR(MAX) เท่านั้น จึงไม่ต้องตรวจสอบความยาว
    Class นี้เก็บ utility methods สำหรับ string validation อื่นๆ
    """

    def validate(self, conn, staging_table: str, schema_name: str, columns: List,
                total_rows: int, chunk_size: int, log_func=None, **kwargs) -> List[Dict]:
        """
        Implementation ของ abstract method จาก BaseValidator

        ไม่ได้ใช้งานสำหรับ StringValidator เนื่องจากระบบใช้ NVARCHAR(MAX)
        ซึ่งไม่มีข้อจำกัดความยาว

        Args:
            conn: Database connection
            staging_table: Staging table name
            schema_name: Schema name
            columns: List of columns (ไม่ใช้)
            total_rows: Total number of rows (ไม่ใช้)
            chunk_size: Chunk size for processing (ไม่ใช้)
            log_func: Logging function (ไม่ใช้)
            **kwargs: Additional parameters (ไม่ใช้)

        Returns:
            List[Dict]: Empty list
        """
        return []
    
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
