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
                                schema_name: str = 'bronze', log_func=None, progress_callback=None) -> Dict:
        """
        Validate data correctness in staging table using SQL with chunked processing
        
        Args:
            staging_table: Staging table name
            logic_type: File type
            required_cols: Required columns and data types
            schema_name: Schema name
            log_func: Function for logging
            progress_callback: Function to call with progress updates (progress, phase, details)
            
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
            
            # Phase 1: Basic checks
            if progress_callback:
                progress_callback(0.1, "Initialization", "Checking table structure...")
            
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
            
            # Phase 2: Schema compatibility check
            if progress_callback:
                progress_callback(0.2, "Schema Check", "Verifying column compatibility...")
            
            if log_func:
                log_func(f"   🔍 Checking schema compatibility...")
            schema_issues = self._check_schema_mismatch_in_staging(staging_table, required_cols, schema_name, log_func)
            if schema_issues:
                validation_results['warnings'].extend(schema_issues)
            
            # Phase 3: Build validation phases
            validation_phases = self._build_validation_phases(staging_table, required_cols, schema_name)
            
            if log_func and validation_phases:
                log_func(f"   📋 Running {len(validation_phases)} validation phases...")
            
            # Phase 4-7: Run validation phases
            phase_progress_step = 0.6 / len(validation_phases) if validation_phases else 0
            base_progress = 0.3
            
            for i, (phase_name, phase_data) in enumerate(validation_phases.items(), 1):
                current_progress = base_progress + (i * phase_progress_step)
                
                if progress_callback:
                    progress_callback(current_progress, f"Validation Phase {i}", f"Running {phase_name}...")
                
                if log_func:
                    log_func(f"   ⏳ Phase {i}/{len(validation_phases)}: {phase_name}...")
                
                phase_issues = self._run_validation_phase(
                    phase_name, phase_data, schema_name, staging_table, 
                    total_rows, log_func, progress_callback, current_progress
                )
                
                # Process phase results
                for issue in phase_issues:
                    if issue['percentage'] > 10:
                        validation_results['is_valid'] = False
                        validation_results['issues'].append(issue)
                    elif issue['percentage'] > 1:
                        validation_results['warnings'].append(issue)
            
            # Phase 8: Final summary
            if progress_callback:
                progress_callback(0.9, "Summary", "Preparing validation results...")
            
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
            
            if progress_callback:
                progress_callback(1.0, "Completed", validation_results['summary'])
                    
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
    
    def _build_validation_phases(self, staging_table: str, required_cols: Dict, schema_name: str) -> Dict:
        """
        Build validation phases for chunked processing
        """
        phases = {}
        
        # Phase 1: Numeric validation
        numeric_columns = []
        for col, dtype in required_cols.items():
            if isinstance(dtype, (SA_Integer, SA_SmallInteger, SA_Float, SA_DECIMAL)):
                numeric_columns.append(col)
        
        if numeric_columns:
            phases['Numeric Data Types'] = {
                'type': 'numeric_validation',
                'columns': numeric_columns,
                'chunk_size': 10000
            }
        
        # Phase 2: Date validation
        date_columns = []
        for col, dtype in required_cols.items():
            if isinstance(dtype, (SA_DATE, SA_DateTime)):
                date_columns.append(col)
        
        if date_columns:
            phases['Date/DateTime Formats'] = {
                'type': 'date_validation',
                'columns': date_columns,
                'chunk_size': 10000
            }
        
        # Phase 3: String length validation
        string_columns = []
        for col, dtype in required_cols.items():
            if isinstance(dtype, SA_NVARCHAR) and hasattr(dtype, 'length') and dtype.length:
                string_columns.append((col, dtype.length))
        
        if string_columns:
            phases['String Length Limits'] = {
                'type': 'string_length_validation',
                'columns': string_columns,
                'chunk_size': 15000
            }
        
        # Phase 4: Boolean validation
        boolean_columns = []
        for col, dtype in required_cols.items():
            if isinstance(dtype, SA_Boolean):
                boolean_columns.append(col)
        
        if boolean_columns:
            phases['Boolean Values'] = {
                'type': 'boolean_validation',
                'columns': boolean_columns,
                'chunk_size': 20000
            }
        
        return phases
    
    def _run_validation_phase(self, phase_name, phase_data, schema_name, staging_table, 
                             total_rows, log_func, progress_callback, base_progress):
        """
        Run a single validation phase with chunked processing
        """
        issues = []
        validation_type = phase_data['type']
        columns = phase_data['columns']
        chunk_size = phase_data.get('chunk_size', 10000)
        
        try:
            with self.engine.connect() as conn:
                if validation_type == 'numeric_validation':
                    issues = self._validate_numeric_chunked(
                        conn, staging_table, schema_name, columns, 
                        total_rows, chunk_size, log_func
                    )
                elif validation_type == 'date_validation':
                    issues = self._validate_date_chunked(
                        conn, staging_table, schema_name, columns, 
                        total_rows, chunk_size, log_func
                    )
                elif validation_type == 'string_length_validation':
                    issues = self._validate_string_length_chunked(
                        conn, staging_table, schema_name, columns, 
                        total_rows, chunk_size, log_func
                    )
                elif validation_type == 'boolean_validation':
                    issues = self._validate_boolean_chunked(
                        conn, staging_table, schema_name, columns, 
                        total_rows, chunk_size, log_func
                    )
                
                if issues:
                    if log_func:
                        log_func(f"      ❌ Found {len(issues)} issue type(s) in {phase_name}")
                    
                    for issue in issues:
                        if log_func and issue['error_count'] > 0:
                            status = "❌" if issue['percentage'] > 10 else "⚠️"
                            column_name = issue['column'] if isinstance(issue['column'], str) else str(issue['column'])
                            examples = issue['examples'][:100] if isinstance(issue['examples'], str) else str(issue['examples'])[:100]
                            log_func(f"      {status} {column_name}: {issue['error_count']:,} invalid rows ({issue['percentage']}%) Examples: {examples}")
                else:
                    if log_func:
                        log_func(f"      ✅ {phase_name} - No issues found")
                        
        except Exception as phase_error:
            if log_func:
                log_func(f"      ⚠️ Could not run {phase_name}: {phase_error}")
        
        return issues
    
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
    
    def _validate_numeric_chunked(self, conn, staging_table, schema_name, columns, 
                                  total_rows, chunk_size, log_func):
        """
        Validate numeric columns in chunks
        """
        issues = []
        
        for col in columns:
            col_literal = f"N'{col}'" if any(ord(c) > 127 for c in col) else f"'{col}'"
            
            # Simplified cleaning for better performance
            cleaned_col_expression = f"""
                LTRIM(RTRIM(REPLACE(REPLACE([{col}], ',', ''), ' ', '')))
            """
            
            # Count errors with simpler query
            error_query = f"""
                SELECT COUNT(*) as error_count
                FROM {schema_name}.{staging_table}
                WHERE TRY_CAST({cleaned_col_expression} AS FLOAT) IS NULL 
                  AND NULLIF({cleaned_col_expression}, '') IS NOT NULL
            """
            
            try:
                result = conn.execute(text(error_query))
                error_count = result.scalar()
                
                if error_count > 0:
                    # Get sample examples (limited)
                    examples_query = f"""
                        SELECT TOP 3 [{col}] as example_value
                        FROM {schema_name}.{staging_table}
                        WHERE TRY_CAST({cleaned_col_expression} AS FLOAT) IS NULL 
                          AND NULLIF({cleaned_col_expression}, '') IS NOT NULL
                    """
                    
                    examples_result = conn.execute(text(examples_query))
                    examples = [str(row.example_value) for row in examples_result.fetchall()]
                    
                    issue = {
                        'validation_type': 'numeric_validation',
                        'column': col,
                        'error_count': error_count,
                        'percentage': round((error_count / total_rows) * 100, 2),
                        'examples': ', '.join(examples)
                    }
                    issues.append(issue)
            
            except Exception as e:
                if log_func:
                    log_func(f"        ⚠️ Error checking column {col}: {e}")
        
        return issues
    
    def _validate_date_chunked(self, conn, staging_table, schema_name, columns, 
                               total_rows, chunk_size, log_func):
        """
        Validate date columns in chunks
        """
        issues = []
        
        for col in columns:
            col_literal = f"N'{col}'" if any(ord(c) > 127 for c in col) else f"'{col}'"
            
            # Simplified cleaning
            cleaned_col_expression = f"""
                LTRIM(RTRIM(REPLACE([{col}], ',', '')))
            """
            
            # Count errors with multiple date format attempts
            error_query = f"""
                SELECT COUNT(*) as error_count
                FROM {schema_name}.{staging_table}
                WHERE COALESCE(
                    TRY_CONVERT(DATETIME, {cleaned_col_expression}, 121),
                    TRY_CONVERT(DATETIME, {cleaned_col_expression}, 103),
                    TRY_CONVERT(DATETIME, {cleaned_col_expression}, 101)
                ) IS NULL
                AND NULLIF({cleaned_col_expression}, '') IS NOT NULL
            """
            
            try:
                result = conn.execute(text(error_query))
                error_count = result.scalar()
                
                if error_count > 0:
                    # Get sample examples
                    examples_query = f"""
                        SELECT TOP 3 [{col}] as example_value
                        FROM {schema_name}.{staging_table}
                        WHERE COALESCE(
                            TRY_CONVERT(DATETIME, {cleaned_col_expression}, 121),
                            TRY_CONVERT(DATETIME, {cleaned_col_expression}, 103),
                            TRY_CONVERT(DATETIME, {cleaned_col_expression}, 101)
                        ) IS NULL
                        AND NULLIF({cleaned_col_expression}, '') IS NOT NULL
                    """
                    
                    examples_result = conn.execute(text(examples_query))
                    examples = [str(row.example_value) for row in examples_result.fetchall()]
                    
                    issue = {
                        'validation_type': 'date_validation',
                        'column': col,
                        'error_count': error_count,
                        'percentage': round((error_count / total_rows) * 100, 2),
                        'examples': ', '.join(examples)
                    }
                    issues.append(issue)
            
            except Exception as e:
                if log_func:
                    log_func(f"        ⚠️ Error checking column {col}: {e}")
        
        return issues
    
    def _validate_string_length_chunked(self, conn, staging_table, schema_name, columns, 
                                        total_rows, chunk_size, log_func):
        """
        Validate string length in chunks
        """
        issues = []
        
        for col, max_length in columns:
            col_literal = f"N'{col}'" if any(ord(c) > 127 for c in col) else f"'{col}'"
            
            # Count errors
            error_query = f"""
                SELECT COUNT(*) as error_count
                FROM {schema_name}.{staging_table}
                WHERE LEN(ISNULL([{col}], '')) > {max_length}
            """
            
            try:
                result = conn.execute(text(error_query))
                error_count = result.scalar()
                
                if error_count > 0:
                    # Get sample examples
                    examples_query = f"""
                        SELECT TOP 3 LEFT([{col}], 30) + '...' as example_value
                        FROM {schema_name}.{staging_table}
                        WHERE LEN(ISNULL([{col}], '')) > {max_length}
                    """
                    
                    examples_result = conn.execute(text(examples_query))
                    examples = [str(row.example_value) for row in examples_result.fetchall()]
                    
                    issue = {
                        'validation_type': 'string_length_validation',
                        'column': col,
                        'error_count': error_count,
                        'percentage': round((error_count / total_rows) * 100, 2),
                        'examples': ', '.join(examples)
                    }
                    issues.append(issue)
            
            except Exception as e:
                if log_func:
                    log_func(f"        ⚠️ Error checking column {col}: {e}")
        
        return issues
    
    def _validate_boolean_chunked(self, conn, staging_table, schema_name, columns, 
                                  total_rows, chunk_size, log_func):
        """
        Validate boolean columns in chunks
        """
        issues = []
        
        for col in columns:
            col_literal = f"N'{col}'" if any(ord(c) > 127 for c in col) else f"'{col}'"
            
            # Simplified cleaning
            cleaned_col_expression = f"""
                UPPER(LTRIM(RTRIM(ISNULL([{col}], ''))))
            """
            
            # Count errors
            error_query = f"""
                SELECT COUNT(*) as error_count
                FROM {schema_name}.{staging_table}
                WHERE {cleaned_col_expression} NOT IN ('1','TRUE','Y','YES','0','FALSE','N','NO','')
            """
            
            try:
                result = conn.execute(text(error_query))
                error_count = result.scalar()
                
                if error_count > 0:
                    # Get sample examples
                    examples_query = f"""
                        SELECT TOP 3 [{col}] as example_value
                        FROM {schema_name}.{staging_table}
                        WHERE {cleaned_col_expression} NOT IN ('1','TRUE','Y','YES','0','FALSE','N','NO','')
                    """
                    
                    examples_result = conn.execute(text(examples_query))
                    examples = [str(row.example_value) for row in examples_result.fetchall()]
                    
                    issue = {
                        'validation_type': 'boolean_validation',
                        'column': col,
                        'error_count': error_count,
                        'percentage': round((error_count / total_rows) * 100, 2),
                        'examples': ', '.join(examples)
                    }
                    issues.append(issue)
            
            except Exception as e:
                if log_func:
                    log_func(f"        ⚠️ Error checking column {col}: {e}")
        
        return issues