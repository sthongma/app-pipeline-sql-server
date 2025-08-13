"""
Data Validation Service for PIPELINE_SQLSERVER

Handles data validation in staging tables
"""

import logging
from typing import Dict

from sqlalchemy import text
from sqlalchemy.types import (
    Integer as SA_Integer,
    SmallInteger as SA_SmallInteger,
    Float as SA_Float,
    DECIMAL as SA_DECIMAL,
    DATE as SA_DATE,
    DateTime as SA_DateTime,
    NVARCHAR as SA_NVARCHAR,
    Text as SA_Text,
    Boolean as SA_Boolean,
)


class DataValidationService:
    """
    Data validation service for staging tables
    
    Validates data types and format before final insertion
    """
    
    def __init__(self, engine) -> None:
        """
        Initialize DataValidationService
        
        Args:
            engine: SQLAlchemy engine instance
        """
        self.engine = engine
        self.logger = logging.getLogger(__name__)

    def validate_data_in_staging(self, staging_table: str, logic_type: str, required_cols: Dict, 
                                schema_name: str = 'bronze', log_func=None) -> Dict:
        """
        Validate data correctness in staging table using SQL
        
        Args:
            staging_table: Staging table name
            logic_type: File type
            required_cols: Required columns and data types
            schema_name: Schema name
            log_func: Function for logging
            
        Returns:
            Dict: Validation results {'is_valid': bool, 'issues': [...], 'summary': str}
        """
        try:
            validation_results = {
                'is_valid': True,
                'issues': [],
                'warnings': [],
                'summary': ''
            }
            
            total_rows = 0
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {schema_name}.{staging_table}"))
                total_rows = result.scalar()
            
            if total_rows == 0:
                validation_results['is_valid'] = False
                validation_results['summary'] = "No data in staging table"
                return validation_results
            
            if log_func:
                log_func(f"📊 Validating {total_rows:,} rows in staging table")
            
            if log_func:
                log_func(f"   🔨 Building validation queries...")
            validation_queries = self._build_validation_queries(staging_table, required_cols, schema_name)
            
            if log_func:
                log_func(f"   🔍 Checking schema compatibility...")
            schema_issues = self._check_schema_mismatch_in_staging(staging_table, required_cols, schema_name, log_func)
            if schema_issues:
                validation_results['warnings'].extend(schema_issues)
            
            # แสดงรายการ validation types ที่จะตรวจสอบ
            if log_func and validation_queries:
                validation_names = {
                    'numeric_validation': 'Numeric data types',
                    'date_validation': 'Date/DateTime formats', 
                    'string_length_validation': 'String length limits',
                    'boolean_validation': 'Boolean values'
                }
                log_func(f"   📋 Running {len(validation_queries)} validation checks...")
            
            with self.engine.connect() as conn:
                for i, (validation_type, query) in enumerate(validation_queries.items(), 1):
                    if log_func:
                        validation_name = validation_names.get(validation_type, validation_type)
                        log_func(f"   ⏳ [{i}/{len(validation_queries)}] Checking {validation_name}...")
                    
                    try:
                        result = conn.execute(text(query))
                        rows = result.fetchall()
                        
                        if rows:
                            issues_found = len(rows)
                            if log_func:
                                log_func(f"      ❌ Found {issues_found} issue(s) in {validation_name}")
                            
                            for row in rows:
                                issue = {
                                    'validation_type': validation_type,
                                    'column': row.column_name if hasattr(row, 'column_name') else 'unknown',
                                    'error_count': row.error_count if hasattr(row, 'error_count') else 0,
                                    'percentage': round((row.error_count / total_rows) * 100, 2) if hasattr(row, 'error_count') else 0,
                                    'examples': row.examples if hasattr(row, 'examples') else ''
                                }
                                
                                if issue['percentage'] > 10:
                                    validation_results['is_valid'] = False
                                    validation_results['issues'].append(issue)
                                elif issue['percentage'] > 1:
                                    validation_results['warnings'].append(issue)
                                
                                if log_func and issue['error_count'] > 0:
                                    status = "❌" if issue['percentage'] > 10 else "⚠️"
                                    column_name = issue['column'] if isinstance(issue['column'], str) else str(issue['column'])
                                    examples = issue['examples'][:100] if isinstance(issue['examples'], str) else str(issue['examples'])[:100]
                                    log_func(f"      {status} {column_name}: {issue['error_count']:,} invalid rows ({issue['percentage']}%) Examples: {examples}")
                        else:
                            if log_func:
                                log_func(f"      ✅ {validation_name} - No issues found")
                    
                    except Exception as query_error:
                        if log_func:
                            log_func(f"      ⚠️ Could not run {validation_name}: {query_error}")
            
            if not validation_results['is_valid']:
                serious_issues = len(validation_results['issues'])
                warnings_count = len(validation_results['warnings'])
                validation_results['summary'] = f"Found {serious_issues} serious issues and {warnings_count} warnings - cannot import data"
            elif validation_results['warnings']:
                warnings_count = len(validation_results['warnings'])
                validation_results['summary'] = f"Found {warnings_count} warnings; data can be imported"
                if log_func:
                    log_func(f"✅ Data validation passed (with {warnings_count} warnings)")
            else:
                validation_results['summary'] = "All data valid"
                if log_func:
                    log_func(f"✅ All data passed validation")
                    
            return validation_results
            
        except Exception as e:
            validation_results = {
                'is_valid': False,
                'issues': [],
                'warnings': [],
                'summary': f"Error validating data: {str(e)}"
            }
            if log_func:
                log_func(f"❌ {validation_results['summary']}")
            return validation_results
    
    def _build_validation_queries(self, staging_table: str, required_cols: Dict, schema_name: str) -> Dict:
        """
        Build SQL queries for validation based on specified data types
        """
        queries = {}
        
        numeric_columns = []
        for col, dtype in required_cols.items():
            if isinstance(dtype, (SA_Integer, SA_SmallInteger, SA_Float, SA_DECIMAL)):
                numeric_columns.append(col)
        
        if numeric_columns:
            numeric_cases = []
            for col in numeric_columns:
                col_literal = f"N'{col}'" if any(ord(c) > 127 for c in col) else f"'{col}'"
                # Enhanced cleaning for numeric data: remove commas, spaces, tabs, newlines, invisible chars
                cleaned_col_expression = f"""
                    NULLIF(LTRIM(RTRIM(
                        REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE([{col}], 
                            ',', ''), 
                            ' ', ''), 
                            CHAR(9), ''), 
                            CHAR(10), ''), 
                            CHAR(13), ''), 
                            CHAR(160), ''), 
                            NCHAR(65279), ''), 
                            NCHAR(8203), ''), 
                            NCHAR(8288), '')
                    )), '')
                """
                numeric_cases.append(f"""
                    SELECT {col_literal} as column_name, [{col}] as invalid_value, ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) as row_num
                    FROM {schema_name}.{staging_table}
                    WHERE TRY_CAST({cleaned_col_expression} AS FLOAT) IS NULL 
                      AND {cleaned_col_expression} IS NOT NULL
                """)
            
            queries['numeric_validation'] = f"""
                WITH numeric_errors AS (
                    {' UNION ALL '.join(numeric_cases)}
                ),
                error_counts AS (
                    SELECT column_name, COUNT(*) as error_count
                    FROM numeric_errors
                    GROUP BY column_name
                ),
                limited_examples AS (
                    SELECT column_name, invalid_value, row_num,
                           ROW_NUMBER() OVER (PARTITION BY column_name ORDER BY row_num) as rn
                    FROM numeric_errors
                )
                SELECT 
                    ec.column_name,
                    ec.error_count,
                    CAST(STRING_AGG(CAST(le.invalid_value AS NVARCHAR(50)), ', ') WITHIN GROUP (ORDER BY le.row_num) AS NVARCHAR(MAX)) as examples
                FROM error_counts ec
                LEFT JOIN limited_examples le ON ec.column_name = le.column_name AND le.rn <= 5
                GROUP BY ec.column_name, ec.error_count
            """
        
        date_columns = []
        for col, dtype in required_cols.items():
            if isinstance(dtype, (SA_DATE, SA_DateTime)):
                date_columns.append(col)
        
        if date_columns:
            date_cases = []
            for col in date_columns:
                col_literal = f"N'{col}'" if any(ord(c) > 127 for c in col) else f"'{col}'"
                # Enhanced cleaning: remove commas, tabs, newlines, carriage returns, BOM, zero-width spaces
                cleaned_col_expression = f"""
                    NULLIF(LTRIM(RTRIM(
                        REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE([{col}], 
                            ',', ''), 
                            CHAR(9), ''), 
                            CHAR(10), ''), 
                            CHAR(13), ''), 
                            CHAR(160), ' '), 
                            NCHAR(65279), ''), 
                            NCHAR(8203), ''), 
                            NCHAR(8288), '')
                    )), '')
                """
                date_cases.append(f"""
                    SELECT {col_literal} as column_name, [{col}] as invalid_value, ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) as row_num
                    FROM {schema_name}.{staging_table}
                    WHERE COALESCE(
                        TRY_CONVERT(DATETIME, {cleaned_col_expression}, 121),
                        TRY_CONVERT(DATETIME, {cleaned_col_expression}, 103),
                        TRY_CONVERT(DATETIME, {cleaned_col_expression}, 101),
                        TRY_CONVERT(DATETIME, {cleaned_col_expression}, 104),
                        TRY_CONVERT(DATETIME, {cleaned_col_expression}, 105)
                    ) IS NULL
                    AND {cleaned_col_expression} IS NOT NULL
                """)
            
            queries['date_validation'] = f"""
                WITH date_errors AS (
                    {' UNION ALL '.join(date_cases)}
                ),
                error_counts AS (
                    SELECT column_name, COUNT(*) as error_count
                    FROM date_errors
                    GROUP BY column_name
                ),
                limited_examples AS (
                    SELECT column_name, invalid_value, row_num,
                           ROW_NUMBER() OVER (PARTITION BY column_name ORDER BY row_num) as rn
                    FROM date_errors
                )
                SELECT 
                    ec.column_name,
                    ec.error_count,
                    CAST(STRING_AGG(CAST(le.invalid_value AS NVARCHAR(50)), ', ') WITHIN GROUP (ORDER BY le.row_num) AS NVARCHAR(MAX)) as examples
                FROM error_counts ec
                LEFT JOIN limited_examples le ON ec.column_name = le.column_name AND le.rn <= 5
                GROUP BY ec.column_name, ec.error_count
            """
        
        string_columns = []
        for col, dtype in required_cols.items():
            if isinstance(dtype, SA_NVARCHAR) and hasattr(dtype, 'length') and dtype.length:
                string_columns.append((col, dtype.length))
        
        if string_columns:
            string_cases = []
            for col, max_length in string_columns:
                col_literal = f"N'{col}'" if any(ord(c) > 127 for c in col) else f"'{col}'"
                string_cases.append(f"""
                    SELECT {col_literal} as column_name, LEFT([{col}], 50) + '...' as invalid_value, ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) as row_num
                    FROM {schema_name}.{staging_table}
                    WHERE LEN(ISNULL([{col}], '')) > {max_length}
                """)
            
            queries['string_length_validation'] = f"""
                WITH string_errors AS (
                    {' UNION ALL '.join(string_cases)}
                ),
                error_counts AS (
                    SELECT column_name, COUNT(*) as error_count
                    FROM string_errors
                    GROUP BY column_name
                ),
                limited_examples AS (
                    SELECT column_name, invalid_value, row_num,
                           ROW_NUMBER() OVER (PARTITION BY column_name ORDER BY row_num) as rn
                    FROM string_errors
                )
                SELECT 
                    ec.column_name,
                    ec.error_count,
                    CAST(STRING_AGG(CAST(le.invalid_value AS NVARCHAR(100)), ', ') WITHIN GROUP (ORDER BY le.row_num) AS NVARCHAR(MAX)) as examples
                FROM error_counts ec
                LEFT JOIN limited_examples le ON ec.column_name = le.column_name AND le.rn <= 3
                GROUP BY ec.column_name, ec.error_count
            """
        
        boolean_columns = []
        for col, dtype in required_cols.items():
            if isinstance(dtype, SA_Boolean):
                boolean_columns.append(col)
        
        if boolean_columns:
            boolean_cases = []
            for col in boolean_columns:
                col_literal = f"N'{col}'" if any(ord(c) > 127 for c in col) else f"'{col}'"
                # Enhanced cleaning for boolean data
                cleaned_col_expression = f"""
                    UPPER(LTRIM(RTRIM(
                        REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(ISNULL([{col}], ''), 
                            ',', ''), 
                            CHAR(9), ''), 
                            CHAR(10), ''), 
                            CHAR(13), ''), 
                            CHAR(160), ' '), 
                            NCHAR(65279), ''), 
                            NCHAR(8203), ''), 
                            NCHAR(8288), '')
                    )))
                """
                boolean_cases.append(f"""
                    SELECT {col_literal} as column_name, [{col}] as invalid_value, ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) as row_num
                    FROM {schema_name}.{staging_table}
                    WHERE {cleaned_col_expression} NOT IN ('1','TRUE','Y','YES','0','FALSE','N','NO','')
                """)
            
            queries['boolean_validation'] = f"""
                WITH boolean_errors AS (
                    {' UNION ALL '.join(boolean_cases)}
                ),
                error_counts AS (
                    SELECT column_name, COUNT(*) as error_count
                    FROM boolean_errors
                    GROUP BY column_name
                ),
                limited_examples AS (
                    SELECT column_name, invalid_value, row_num,
                           ROW_NUMBER() OVER (PARTITION BY column_name ORDER BY row_num) as rn
                    FROM boolean_errors
                )
                SELECT 
                    ec.column_name,
                    ec.error_count,
                    CAST(STRING_AGG(CAST(le.invalid_value AS NVARCHAR(50)), ', ') WITHIN GROUP (ORDER BY le.row_num) AS NVARCHAR(MAX)) as examples
                FROM error_counts ec
                LEFT JOIN limited_examples le ON ec.column_name = le.column_name AND le.rn <= 5
                GROUP BY ec.column_name, ec.error_count
            """
        
        return queries
    
    def _check_schema_mismatch_in_staging(self, staging_table: str, required_cols: Dict, 
                                        schema_name: str, log_func=None) -> list:
        """
        Check schema mismatch after importing to staging table
        """
        schema_issues = []
        
        try:
            with self.engine.connect() as conn:
                final_table = staging_table.replace('_staging', '')
                table_info_query = f"""
                    SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, COLLATION_NAME
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = '{schema_name}' 
                    AND TABLE_NAME = '{final_table}'
                """
                
                result = conn.execute(text(table_info_query))
                db_columns = {row.COLUMN_NAME: {
                    'data_type': row.DATA_TYPE,
                    'max_length': row.CHARACTER_MAXIMUM_LENGTH,
                    'collation': row.COLLATION_NAME
                } for row in result.fetchall()}
                
                for col_name, expected_dtype in required_cols.items():
                    if col_name in db_columns:
                        db_info = db_columns[col_name]
                        
                        if isinstance(expected_dtype, SA_Text):
                            if db_info['data_type'] == 'nvarchar' and db_info['max_length'] != -1:
                                issue = {
                                    'validation_type': 'schema_mismatch',
                                    'column': col_name,
                                    'error_count': 0,
                                    'percentage': 0,
                                    'message': f"Configured as NVARCHAR(MAX) but database column is NVARCHAR({db_info['max_length'] or 'Unknown'})",
                                    'recommendation': "Data will be saved, but may be truncated if it exceeds column length",
                                    'severity': 'info'
                                }
                                
                                schema_issues.append(issue)
                                
                                if log_func:
                                    log_func(f"   ⚠️  {col_name}: {issue['message']}")
                                    log_func(f"      ℹ️  {issue['recommendation']}")
        
        except Exception as e:
            if log_func:
                log_func(f"⚠️ Unable to check schema mismatch: {e}")
        
        return schema_issues