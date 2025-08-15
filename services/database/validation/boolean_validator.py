"""
Boolean data validation module
"""

from typing import List, Dict
from sqlalchemy import text
from sqlalchemy.types import Boolean as SA_Boolean

from .base_validator import BaseValidator


class BooleanValidator(BaseValidator):
    """
    Validator สำหรับตรวจสอบข้อมูล boolean
    
    ตรวจสอบว่าข้อมูลในคอลัมน์สามารถแปลงเป็น boolean ได้หรือไม่
    รองรับค่าต่างๆ เช่น 1, 0, TRUE, FALSE, Y, N, YES, NO
    """
    
    # ค่าที่ยอมรับได้สำหรับ boolean
    VALID_BOOLEAN_VALUES = {
        '1', 'TRUE', 'Y', 'YES', 
        '0', 'FALSE', 'N', 'NO', 
        ''  # empty string ถือเป็น NULL/False
    }
    
    def validate(self, conn, staging_table: str, schema_name: str, columns: List, 
                total_rows: int, chunk_size: int, log_func=None, **kwargs) -> List[Dict]:
        """
        ตรวจสอบข้อมูล boolean ในคอลัมน์ต่างๆ
        
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
                issue = self._validate_single_boolean_column(
                    conn, staging_table, schema_name, col, total_rows, log_func
                )
                if issue:
                    issues.append(issue)
            except Exception as e:
                if log_func:
                    log_func(f"        ⚠️ Error checking column {col}: {e}")
        
        return issues
    
    def _validate_single_boolean_column(self, conn, staging_table: str, schema_name: str, 
                                       col: str, total_rows: int, log_func) -> Dict:
        """
        ตรวจสอบคอลัมน์ boolean เดียว
        
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
        safe_col = self.safe_column_name(col)
        
        # สร้าง expression สำหรับทำความสะอาดข้อมูล
        cleaned_col_expression = f"UPPER(LTRIM(RTRIM(ISNULL({safe_col}, ''))))"
        
        # สร้าง list ของค่าที่ยอมรับได้
        valid_values_str = "','".join(self.VALID_BOOLEAN_VALUES)
        
        # นับจำนวน error
        error_query = f"""
            SELECT COUNT(*) as error_count
            FROM {schema_name}.{staging_table}
            WHERE {cleaned_col_expression} NOT IN ('{valid_values_str}')
        """
        
        result = self.execute_query_safely(
            conn, error_query, f"Error checking boolean column {col}", log_func
        )
        
        if result is None:
            return None
            
        error_count = result.scalar()
        
        if error_count > 0:
            # ดึงตัวอย่างข้อมูลที่มีปัญหา
            where_condition = f"{cleaned_col_expression} NOT IN ('{valid_values_str}')"
            examples = self.get_sample_examples(
                conn, staging_table, schema_name, where_condition, col
            )
            
            return self.create_issue_dict(
                validation_type='boolean_validation',
                column=col,
                error_count=error_count,
                total_rows=total_rows,
                examples=examples,
                valid_values=list(self.VALID_BOOLEAN_VALUES)
            )
        
        return None
    
    def get_boolean_columns(self, required_cols: Dict) -> List[str]:
        """
        ดึงรายชื่อคอลัมน์ที่เป็นประเภท boolean
        
        Args:
            required_cols: Dictionary ของคอลัมน์และ data types
            
        Returns:
            List[str]: List of boolean column names
        """
        boolean_columns = []
        for col, dtype in required_cols.items():
            if isinstance(dtype, SA_Boolean):
                boolean_columns.append(col)
        
        return boolean_columns
    
    def validate_custom_boolean_values(self, conn, staging_table: str, schema_name: str, 
                                     col: str, true_values: List[str], false_values: List[str],
                                     total_rows: int = 0, log_func=None) -> Dict:
        """
        ตรวจสอบข้อมูล boolean ด้วยค่าที่กำหนดเอง
        
        Args:
            conn: Database connection
            staging_table: Staging table name
            schema_name: Schema name
            col: Column name
            true_values: List of values that represent TRUE
            false_values: List of values that represent FALSE
            total_rows: Total number of rows
            log_func: Logging function
            
        Returns:
            Dict: Validation issue หรือ None ถ้าไม่มีปัญหา
        """
        safe_col = self.safe_column_name(col)
        cleaned_col_expression = f"UPPER(LTRIM(RTRIM(ISNULL({safe_col}, ''))))"
        
        # รวมค่าที่ยอมรับได้
        all_valid_values = set()
        all_valid_values.update([v.upper() for v in true_values])
        all_valid_values.update([v.upper() for v in false_values])
        all_valid_values.add('')  # empty string
        
        valid_values_str = "','".join(all_valid_values)
        
        error_query = f"""
            SELECT COUNT(*) as error_count
            FROM {schema_name}.{staging_table}
            WHERE {cleaned_col_expression} NOT IN ('{valid_values_str}')
        """
        
        result = self.execute_query_safely(
            conn, error_query, f"Error checking custom boolean values for column {col}", log_func
        )
        
        if result is None:
            return None
            
        error_count = result.scalar()
        
        if error_count > 0:
            where_condition = f"{cleaned_col_expression} NOT IN ('{valid_values_str}')"
            examples = self.get_sample_examples(
                conn, staging_table, schema_name, where_condition, col
            )
            
            return self.create_issue_dict(
                validation_type='custom_boolean_validation',
                column=col,
                error_count=error_count,
                total_rows=total_rows,
                examples=examples,
                true_values=true_values,
                false_values=false_values
            )
        
        return None
    
    def get_boolean_value_distribution(self, conn, staging_table: str, schema_name: str, 
                                     col: str, log_func=None) -> Dict:
        """
        ดึงการกระจายตัวของค่า boolean ในคอลัมน์
        
        Args:
            conn: Database connection
            staging_table: Staging table name
            schema_name: Schema name
            col: Column name
            log_func: Logging function
            
        Returns:
            Dict: Boolean value distribution
        """
        safe_col = self.safe_column_name(col)
        cleaned_col_expression = f"UPPER(LTRIM(RTRIM(ISNULL({safe_col}, ''))))"
        
        distribution_query = f"""
            SELECT 
                {cleaned_col_expression} as value,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
            FROM {schema_name}.{staging_table}
            GROUP BY {cleaned_col_expression}
            ORDER BY count DESC
        """
        
        result = self.execute_query_safely(
            conn, distribution_query, f"Error getting boolean distribution for column {col}", log_func
        )
        
        if result is None:
            return {}
        
        distribution = {}
        total_count = 0
        
        for row in result.fetchall():
            value = row.value or 'NULL/EMPTY'
            count = row.count
            percentage = row.percentage
            
            distribution[value] = {
                'count': count,
                'percentage': percentage
            }
            total_count += count
        
        # จำแนกค่าเป็นหมวดหมู่
        true_like = 0
        false_like = 0
        invalid = 0
        
        for value, data in distribution.items():
            if value.upper() in ['1', 'TRUE', 'Y', 'YES']:
                true_like += data['count']
            elif value.upper() in ['0', 'FALSE', 'N', 'NO', 'NULL/EMPTY']:
                false_like += data['count']
            else:
                invalid += data['count']
        
        return {
            'column': col,
            'total_count': total_count,
            'distribution': distribution,
            'summary': {
                'true_like_count': true_like,
                'false_like_count': false_like,
                'invalid_count': invalid,
                'true_like_percentage': round((true_like / total_count) * 100, 2) if total_count > 0 else 0,
                'false_like_percentage': round((false_like / total_count) * 100, 2) if total_count > 0 else 0,
                'invalid_percentage': round((invalid / total_count) * 100, 2) if total_count > 0 else 0
            }
        }
    
    def convert_to_standard_boolean(self, conn, staging_table: str, schema_name: str, 
                                  col: str, true_values: List[str] = None, 
                                  false_values: List[str] = None, log_func=None) -> bool:
        """
        แปลงค่า boolean ในคอลัมน์ให้เป็นรูปแบบมาตรฐาน (1/0)
        
        Args:
            conn: Database connection
            staging_table: Staging table name
            schema_name: Schema name
            col: Column name
            true_values: List of values that should be converted to 1
            false_values: List of values that should be converted to 0
            log_func: Logging function
            
        Returns:
            bool: True if conversion successful, False otherwise
        """
        if true_values is None:
            true_values = ['TRUE', 'Y', 'YES', '1']
        if false_values is None:
            false_values = ['FALSE', 'N', 'NO', '0', '']
        
        safe_col = self.safe_column_name(col)
        
        # สร้าง CASE statement สำหรับการแปลง
        true_conditions = " OR ".join([f"UPPER(LTRIM(RTRIM(ISNULL({safe_col}, '')))) = '{v.upper()}'" for v in true_values])
        false_conditions = " OR ".join([f"UPPER(LTRIM(RTRIM(ISNULL({safe_col}, '')))) = '{v.upper()}'" for v in false_values])
        
        update_query = f"""
            UPDATE {schema_name}.{staging_table}
            SET {safe_col} = CASE 
                WHEN {true_conditions} THEN '1'
                WHEN {false_conditions} THEN '0'
                ELSE {safe_col}
            END
        """
        
        try:
            result = conn.execute(text(update_query))
            rows_affected = result.rowcount
            
            if log_func:
                log_func(f"    ✅ Converted {rows_affected:,} boolean values in column {col}")
            
            return True
            
        except Exception as e:
            if log_func:
                log_func(f"    ❌ Error converting boolean values in column {col}: {e}")
            return False
