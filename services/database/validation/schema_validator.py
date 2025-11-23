"""
Schema compatibility validation module
"""

from typing import List, Dict
from sqlalchemy import text
from sqlalchemy.types import Text as SA_Text

from .base_validator import BaseValidator


class SchemaValidator(BaseValidator):
    """
    Validator สำหรับตรวจสอบความเข้ากันได้ของ schema
    
    ตรวจสอบว่า schema ของ staging table เข้ากันได้กับ final table หรือไม่
    """
    
    def validate(self, conn, staging_table: str, schema_name: str, columns: List, 
                total_rows: int, chunk_size: int, log_func=None, **kwargs) -> List[Dict]:
        """
        Implementation ของ abstract method จาก BaseValidator
        
        สำหรับ SchemaValidator จะ redirect ไปใช้ validate_schema_compatibility
        
        Args:
            conn: Database connection (ไม่ใช้สำหรับ schema validation)
            staging_table: Staging table name
            schema_name: Schema name
            columns: ไม่ใช้ - จะใช้ required_cols จาก kwargs แทน
            total_rows: Total number of rows (ไม่ใช้)
            chunk_size: Chunk size (ไม่ใช้)
            log_func: Logging function
            **kwargs: Additional parameters including 'required_cols'
            
        Returns:
            List[Dict]: List of schema compatibility issues
        """
        required_cols = kwargs.get('required_cols', {})
        return self.validate_schema_compatibility(staging_table, required_cols, schema_name, log_func)
    
    def validate_schema_compatibility(self, staging_table: str, required_cols: Dict, 
                                   schema_name: str = 'bronze', log_func=None) -> List[Dict]:
        """
        ตรวจสอบความเข้ากันได้ของ schema หลังจาก import ข้อมูลเข้า staging table
        
        Args:
            staging_table: Staging table name
            required_cols: Required columns and data types
            schema_name: Schema name
            log_func: Logging function
            
        Returns:
            List[Dict]: List of schema compatibility issues
        """
        schema_issues = []
        
        try:
            with self.engine.connect() as conn:
                final_table = staging_table.replace('_staging', '')
                
                # ดึงข้อมูล schema ของ final table
                db_columns = self._get_table_schema_info(conn, final_table, schema_name)
                
                if not db_columns:
                    if log_func:
                        log_func(f"   ℹ️  Final table {final_table} not found - skipping schema validation")
                    return schema_issues
                
                # ตรวจสอบแต่ละคอลัมน์ (ข้ามคอลัมน์ระบบ และ metadata columns)
                # Metadata columns ถูกสร้างอัตโนมัติโดยระบบ ไม่ต้อง validate
                system_columns = {
                    '_loaded_at', '_created_at', '_source_file', '_batch_id', '_upsert_hash'  # Metadata columns 
                }

                for col_name, expected_dtype in required_cols.items():
                    # ข้ามคอลัมน์ระบบและ metadata columns
                    if col_name in system_columns:
                        continue

                    if col_name in db_columns:
                        db_info = db_columns[col_name]

                        # ตรวจสอบ Text fields ที่อาจมีปัญหา
                        issue = self._check_text_field_compatibility(
                            col_name, expected_dtype, db_info, log_func
                        )
                        if issue:
                            schema_issues.append(issue)

                        # ตรวจสอบ data type compatibility อื่นๆ
                        other_issues = self._check_data_type_compatibility(
                            col_name, expected_dtype, db_info, log_func
                        )
                        schema_issues.extend(other_issues)
                    else:
                        # คอลัมน์ไม่มีใน final table
                        issue = {
                            'validation_type': 'schema_missing_column',
                            'column': col_name,
                            'error_count': 0,
                            'percentage': 0,
                            'message': f"Column not found in final table {final_table}",
                            'recommendation': "Column will be ignored during final import",
                            'severity': 'warning'
                        }
                        schema_issues.append(issue)

                        if log_func:
                            log_func(f"   ⚠️  {col_name}: Column not found in final table")
        
        except Exception as e:
            if log_func:
                log_func(f"⚠️ Unable to check schema compatibility: {e}")
        
        return schema_issues
    
    def _get_table_schema_info(self, conn, table_name: str, schema_name: str) -> Dict:
        """
        ดึงข้อมูล schema ของ table
        
        Args:
            conn: Database connection
            table_name: Table name
            schema_name: Schema name
            
        Returns:
            Dict: Table schema information
        """
        table_info_query = f"""
            SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, 
                   COLLATION_NAME, IS_NULLABLE, COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = '{schema_name}' 
            AND TABLE_NAME = '{table_name}'
        """
        
        result = self.execute_query_safely(
            conn, table_info_query, f"Error getting schema info for {table_name}"
        )
        
        if result is None:
            return {}
        
        db_columns = {}
        for row in result.fetchall():
            db_columns[row.COLUMN_NAME] = {
                'data_type': row.DATA_TYPE,
                'max_length': row.CHARACTER_MAXIMUM_LENGTH,
                'collation': row.COLLATION_NAME,
                'is_nullable': row.IS_NULLABLE,
                'default_value': row.COLUMN_DEFAULT
            }
        
        return db_columns
    
    def _check_text_field_compatibility(self, col_name: str, expected_dtype, 
                                      db_info: Dict, log_func) -> Dict:
        """
        ตรวจสอบความเข้ากันได้ของ Text fields
        
        Args:
            col_name: Column name
            expected_dtype: Expected data type
            db_info: Database column information
            log_func: Logging function
            
        Returns:
            Dict: Schema issue หรือ None ถ้าไม่มีปัญหา
        """
        if isinstance(expected_dtype, SA_Text):
            if db_info['data_type'] == 'nvarchar' and db_info['max_length'] != -1:
                issue = {
                    'validation_type': 'schema_mismatch',
                    'column': col_name,
                    'error_count': 0,
                    'percentage': 0,
                    'message': f"Configured as NVARCHAR(MAX) but database column is NVARCHAR({db_info['max_length'] or 'Unknown'})",
                    'recommendation': "Data will be saved, but may be truncated if it exceeds column length",
                    'severity': 'info',
                    'expected_type': 'NVARCHAR(MAX)',
                    'actual_type': f"NVARCHAR({db_info['max_length']})"
                }
                
                if log_func:
                    log_func(f"   ⚠️  {col_name}: {issue['message']}")
                    log_func(f"      ℹ️  {issue['recommendation']}")
                
                return issue
        
        return None
    
    def _check_data_type_compatibility(self, col_name: str, expected_dtype, 
                                     db_info: Dict, log_func) -> List[Dict]:
        """
        ตรวจสอบความเข้ากันได้ของ data types อื่นๆ
        
        Args:
            col_name: Column name
            expected_dtype: Expected data type
            db_info: Database column information
            log_func: Logging function
            
        Returns:
            List[Dict]: List of schema issues
        """
        issues = []
        
        # ตรวจสอบ nullable compatibility
        if hasattr(expected_dtype, 'nullable'):
            if expected_dtype.nullable is False and db_info['is_nullable'] == 'YES':
                issue = {
                    'validation_type': 'schema_nullable_mismatch',
                    'column': col_name,
                    'error_count': 0,
                    'percentage': 0,
                    'message': f"Expected NOT NULL but database allows NULL",
                    'recommendation': "Ensure no NULL values in data or update database schema",
                    'severity': 'warning'
                }
                issues.append(issue)
                
                if log_func:
                    log_func(f"   ⚠️  {col_name}: Nullable mismatch")
        
        return issues
    
    def validate_column_exists(self, conn, table_name: str, schema_name: str, 
                              column_name: str) -> bool:
        """
        ตรวจสอบว่าคอลัมน์มีอยู่ใน table หรือไม่
        
        Args:
            conn: Database connection
            table_name: Table name
            schema_name: Schema name
            column_name: Column name
            
        Returns:
            bool: True if column exists, False otherwise
        """
        check_query = f"""
            SELECT COUNT(*) as count
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = '{schema_name}' 
            AND TABLE_NAME = '{table_name}'
            AND COLUMN_NAME = '{column_name}'
        """
        
        result = self.execute_query_safely(
            conn, check_query, f"Error checking if column {column_name} exists"
        )
        
        if result is None:
            return False
        
        return result.scalar() > 0
    
    def get_table_constraints(self, conn, table_name: str, schema_name: str) -> Dict:
        """
        ดึงข้อมูล constraints ของ table
        
        Args:
            conn: Database connection
            table_name: Table name
            schema_name: Schema name
            
        Returns:
            Dict: Table constraints information
        """
        constraints_query = f"""
            SELECT 
                tc.CONSTRAINT_NAME,
                tc.CONSTRAINT_TYPE,
                kcu.COLUMN_NAME,
                cc.CHECK_CLAUSE
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
            LEFT JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu 
                ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME 
                AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
                AND tc.TABLE_NAME = kcu.TABLE_NAME
            LEFT JOIN INFORMATION_SCHEMA.CHECK_CONSTRAINTS cc
                ON tc.CONSTRAINT_NAME = cc.CONSTRAINT_NAME
            WHERE tc.TABLE_SCHEMA = '{schema_name}' 
            AND tc.TABLE_NAME = '{table_name}'
        """
        
        result = self.execute_query_safely(
            conn, constraints_query, f"Error getting constraints for {table_name}"
        )
        
        if result is None:
            return {}
        
        constraints = {
            'primary_keys': [],
            'foreign_keys': [],
            'unique_constraints': [],
            'check_constraints': []
        }
        
        for row in result.fetchall():
            constraint_type = row.CONSTRAINT_TYPE
            column_name = row.COLUMN_NAME
            constraint_name = row.CONSTRAINT_NAME
            
            if constraint_type == 'PRIMARY KEY':
                constraints['primary_keys'].append({
                    'name': constraint_name,
                    'column': column_name
                })
            elif constraint_type == 'FOREIGN KEY':
                constraints['foreign_keys'].append({
                    'name': constraint_name,
                    'column': column_name
                })
            elif constraint_type == 'UNIQUE':
                constraints['unique_constraints'].append({
                    'name': constraint_name,
                    'column': column_name
                })
            elif constraint_type == 'CHECK':
                constraints['check_constraints'].append({
                    'name': constraint_name,
                    'column': column_name,
                    'check_clause': row.CHECK_CLAUSE
                })
        
        return constraints
    
    def validate_against_constraints(self, conn, staging_table: str, schema_name: str, 
                                   constraints: Dict, total_rows: int = 0, 
                                   log_func=None) -> List[Dict]:
        """
        ตรวจสอบข้อมูลใน staging table กับ constraints
        
        Args:
            conn: Database connection
            staging_table: Staging table name
            schema_name: Schema name
            constraints: Table constraints
            total_rows: Total number of rows
            log_func: Logging function
            
        Returns:
            List[Dict]: List of constraint violation issues
        """
        issues = []
        
        # ตรวจสอบ unique constraints
        for unique_constraint in constraints.get('unique_constraints', []):
            column_name = unique_constraint['column']
            safe_col = self.safe_column_name(column_name)
            
            # หา duplicate values
            duplicate_query = f"""
                SELECT COUNT(*) as duplicate_count
                FROM (
                    SELECT {safe_col}, COUNT(*) as count
                    FROM {schema_name}.{staging_table}
                    WHERE {safe_col} IS NOT NULL
                    GROUP BY {safe_col}
                    HAVING COUNT(*) > 1
                ) duplicates
            """
            
            result = self.execute_query_safely(
                conn, duplicate_query, f"Error checking unique constraint for {column_name}", log_func
            )
            
            if result and result.scalar() > 0:
                duplicate_count = result.scalar()
                
                # ดึงตัวอย่าง duplicate values
                examples_query = f"""
                    SELECT TOP 3 {safe_col} as example_value
                    FROM (
                        SELECT {safe_col}, COUNT(*) as count
                        FROM {schema_name}.{staging_table}
                        WHERE {safe_col} IS NOT NULL
                        GROUP BY {safe_col}
                        HAVING COUNT(*) > 1
                    ) duplicates
                """
                
                examples_result = self.execute_query_safely(
                    conn, examples_query, f"Error getting duplicate examples for {column_name}", log_func
                )
                
                examples = []
                if examples_result:
                    examples = [str(row.example_value) for row in examples_result.fetchall()]
                
                issue = self.create_issue_dict(
                    validation_type='unique_constraint_violation',
                    column=column_name,
                    error_count=duplicate_count,
                    total_rows=total_rows,
                    examples=examples,
                    constraint_name=unique_constraint['name']
                )
                issues.append(issue)
        
        return issues
