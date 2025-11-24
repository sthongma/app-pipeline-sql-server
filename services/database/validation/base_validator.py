"""
Base validator class with common utilities for all validation types
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any
from sqlalchemy import text
from utils.sql_utils import get_cleaning_expression


class BaseValidator(ABC):
    """
    Abstract base class สำหรับ validators ทั้งหมด
    
    มี common utilities ที่ validators อื่นๆ สามารถใช้ร่วมกันได้
    """
    
    def __init__(self, engine):
        """
        Initialize BaseValidator
        
        Args:
            engine: SQLAlchemy engine instance
        """
        self.engine = engine
        self.logger = logging.getLogger(__name__)
    
    @abstractmethod
    def validate(self, conn, staging_table: str, schema_name: str, columns: List, 
                total_rows: int, chunk_size: int, log_func=None, **kwargs) -> List[Dict]:
        """
        Abstract method สำหรับการ validate
        
        Args:
            conn: Database connection
            staging_table: Staging table name
            schema_name: Schema name
            columns: List of columns to validate
            total_rows: Total number of rows
            chunk_size: Chunk size for processing
            log_func: Logging function
            **kwargs: Additional parameters
            
        Returns:
            List[Dict]: List of validation issues
        """
        pass
    
    def safe_column_name(self, col_name: str) -> str:
        """
        สร้าง column name ที่ปลอดภัยสำหรับ SQL query
        
        Args:
            col_name: Column name
            
        Returns:
            str: Safe column name for SQL
        """
        return f"[{col_name}]"
    
    def get_cleaned_column_expression(self, col_name: str, cleaning_type: str = 'basic') -> str:
        """
        สร้าง SQL expression สำหรับทำความสะอาดข้อมูล
        แปลงเครื่องหมาย '-' เดี่ยวๆ ให้เป็นค่าว่างเฉพาะชนิดตัวเลขและวันที่
        
        Args:
            col_name: Column name
            cleaning_type: Type of cleaning ('basic', 'numeric', 'date')
            
        Returns:
            str: SQL expression for cleaning
        """
        # Use shared utility function to ensure consistency
        return get_cleaning_expression(col_name, cleaning_type)
    
    def execute_query_safely(self, conn, query: str, error_message: str = "", log_func=None) -> Any:
        """
        ดำเนินการ query อย่างปลอดภัยพร้อม error handling
        
        Args:
            conn: Database connection
            query: SQL query to execute
            error_message: Custom error message
            log_func: Logging function
            
        Returns:
            Query result หรือ None ถ้าเกิด error
        """
        try:
            result = conn.execute(text(query))
            return result
        except Exception as e:
            if log_func:
                log_func(f"Warning: {error_message}: {e}")
            return None
    
    def get_sample_examples(self, conn, staging_table: str, schema_name: str, 
                           where_condition: str, column_name: str, limit: int = 3) -> List[str]:
        """
        ดึงตัวอย่างข้อมูลที่มีปัญหา
        
        Args:
            conn: Database connection
            staging_table: Staging table name
            schema_name: Schema name
            where_condition: WHERE condition for filtering problematic data
            column_name: Column name to get examples from
            limit: Number of examples to get
            
        Returns:
            List[str]: List of example values
        """
        safe_col = self.safe_column_name(column_name)
        query = f"""
            SELECT TOP {limit} {safe_col} as example_value
            FROM {schema_name}.{staging_table}
            WHERE {where_condition}
        """
        
        try:
            result = conn.execute(text(query))
            examples = [str(row.example_value) for row in result.fetchall()]
            return examples
        except Exception:
            return []
    
    def calculate_error_percentage(self, error_count: int, total_rows: int) -> float:
        """
        คำนวณเปอร์เซ็นต์ของ error
        
        Args:
            error_count: Number of errors
            total_rows: Total number of rows
            
        Returns:
            float: Error percentage
        """
        if total_rows == 0:
            return 0.0
        return round((error_count / total_rows) * 100, 2)
    
    def create_issue_dict(self, validation_type: str, column: str, error_count: int, 
                         total_rows: int, examples: List[str], **kwargs) -> Dict:
        """
        สร้าง dictionary สำหรับ validation issue
        
        Args:
            validation_type: Type of validation
            column: Column name
            error_count: Number of errors
            total_rows: Total number of rows
            examples: List of example values
            **kwargs: Additional issue data
            
        Returns:
            Dict: Issue dictionary
        """
        issue = {
            'validation_type': validation_type,
            'column': column,
            'error_count': error_count,
            'percentage': self.calculate_error_percentage(error_count, total_rows),
            'examples': ', '.join(examples)
        }
        
        # เพิ่มข้อมูลเพิ่มเติมจาก kwargs
        issue.update(kwargs)
        
        return issue
    
    def log_validation_result(self, log_func, column: str, issues: List[Dict]):
        """
        Log ผลลัพธ์การ validation
        
        Args:
            log_func: Logging function
            column: Column name
            issues: List of issues found
        """
        if not log_func:
            return
            
        if issues:
            for issue in issues:
                status = "Error" if issue['percentage'] > 10 else "Warning"
                column_name = issue['column'] if isinstance(issue['column'], str) else str(issue['column'])
                examples = issue['examples'][:100] if isinstance(issue['examples'], str) else str(issue['examples'])[:100]
                log_func(f"      {status}: {column_name}: {issue['error_count']:,} invalid rows ({issue['percentage']}%) Examples: {examples}")
        else:
            log_func(f"      {column} - No issues found")
