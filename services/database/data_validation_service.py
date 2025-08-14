"""
Data Validation Service for PIPELINE_SQLSERVER

Handles data validation in staging tables
"""

import logging
from typing import Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

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
                                schema_name: str = 'bronze', log_func=None, progress_callback=None, 
                                date_format: str = 'UK') -> Dict:
        """
        Validate data correctness in staging table using SQL with chunked processing
        
        Args:
            staging_table: Staging table name
            logic_type: File type
            required_cols: Required columns and data types
            schema_name: Schema name
            log_func: Function for logging
            progress_callback: Function to call with progress updates (progress, phase, details)
            date_format: Date format preference ('UK' for DD-MM or 'US' for MM-DD)
            
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
            
            # Phase 2: Create temporary indexes for performance
            if progress_callback:
                progress_callback(0.15, "Index Creation", "Creating temporary indexes for faster validation...")
            
            if log_func:
                log_func(f"   🚀 Creating temporary indexes for better performance...")
            self._create_temp_indexes(staging_table, required_cols, schema_name, log_func)
            
            # Phase 3: Schema compatibility check
            if progress_callback:
                progress_callback(0.2, "Schema Check", "Verifying column compatibility...")
            
            if log_func:
                log_func(f"   🔍 Checking schema compatibility...")
            schema_issues = self._check_schema_mismatch_in_staging(staging_table, required_cols, schema_name, log_func)
            if schema_issues:
                validation_results['warnings'].extend(schema_issues)
            
            # Phase 3: Build validation phases
            validation_phases = self._build_validation_phases(staging_table, required_cols, schema_name, date_format)
            
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
                    total_rows, log_func, progress_callback, current_progress, date_format
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
            
            # Cleanup: ลบ temporary indexes
            if log_func:
                log_func(f"   🧹 Cleaning up temporary indexes...")
            self._drop_temp_indexes(staging_table, required_cols, schema_name, log_func)
            
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
    
    def _build_validation_phases(self, staging_table: str, required_cols: Dict, schema_name: str, date_format: str) -> Dict:
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
                             total_rows, log_func, progress_callback, base_progress, date_format):
        """
        Run a single validation phase with chunked processing
        """
        issues = []
        validation_type = phase_data['type']
        columns = phase_data['columns']
        chunk_size = phase_data.get('chunk_size', 10000)
        
        try:
            # สำหรับคอลัมน์หลายตัว ใช้ parallel processing
            if len(columns) > 1 and validation_type in ['numeric_validation', 'date_validation']:
                issues = self._validate_columns_parallel(
                    validation_type, staging_table, schema_name, columns, 
                    total_rows, chunk_size, log_func, date_format
                )
            else:
                # สำหรับคอลัมน์เดียวหรือ validation ประเภทอื่น ใช้แบบปกติ
                with self.engine.connect() as conn:
                    if validation_type == 'numeric_validation':
                        issues = self._validate_numeric_chunked(
                            conn, staging_table, schema_name, columns, 
                            total_rows, chunk_size, log_func
                        )
                    elif validation_type == 'date_validation':
                        issues = self._validate_date_chunked(
                            conn, staging_table, schema_name, columns, 
                            total_rows, chunk_size, log_func, date_format
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
    
    def _create_temp_indexes(self, staging_table: str, required_cols: Dict, schema_name: str, log_func=None):
        """สร้าง temporary indexes เพื่อเร่งการ validation"""
        try:
            with self.engine.connect() as conn:
                index_count = 0
                for col_name in required_cols.keys():
                    # สร้าง index ชั่วคราวสำหรับ column ที่มีข้อมูลเยอะ
                    index_name = f"temp_idx_{staging_table}_{col_name}".replace(' ', '_').replace('-', '_')[:128]
                    try:
                        # ตรวจสอบว่า index มีอยู่แล้วหรือไม่
                        check_sql = f"""
                            SELECT COUNT(*) FROM sys.indexes 
                            WHERE object_id = OBJECT_ID('{schema_name}.{staging_table}') 
                            AND name = '{index_name}'
                        """
                        result = conn.execute(text(check_sql))
                        if result.scalar() == 0:
                            # สร้าง index ใหม่
                            create_index_sql = f"""
                                CREATE NONCLUSTERED INDEX [{index_name}] 
                                ON {schema_name}.{staging_table} ([{col_name}])
                                WHERE [{col_name}] IS NOT NULL
                            """
                            conn.execute(text(create_index_sql))
                            index_count += 1
                    except Exception as e:
                        # ถ้าสร้าง index ไม่ได้ก็ข้าม (อาจเป็น column ที่มีข้อมูลยาวเกินไป)
                        pass
                        
                conn.commit()
                if log_func and index_count > 0:
                    log_func(f"   ✅ Created {index_count} temporary indexes for validation")
                    
        except Exception as e:
            if log_func:
                log_func(f"   ⚠️ Unable to create temporary indexes: {e}")
    
    def _drop_temp_indexes(self, staging_table: str, required_cols: Dict, schema_name: str, log_func=None):
        """ลบ temporary indexes หลังจาก validation เสร็จ"""
        try:
            with self.engine.connect() as conn:
                dropped_count = 0
                for col_name in required_cols.keys():
                    index_name = f"temp_idx_{staging_table}_{col_name}".replace(' ', '_').replace('-', '_')[:128]
                    try:
                        # ตรวจสอบและลบ index
                        check_sql = f"""
                            SELECT COUNT(*) FROM sys.indexes 
                            WHERE object_id = OBJECT_ID('{schema_name}.{staging_table}') 
                            AND name = '{index_name}'
                        """
                        result = conn.execute(text(check_sql))
                        if result.scalar() > 0:
                            drop_sql = f"DROP INDEX [{index_name}] ON {schema_name}.{staging_table}"
                            conn.execute(text(drop_sql))
                            dropped_count += 1
                    except Exception as e:
                        # ถ้าลบไม่ได้ก็ข้าม
                        pass
                        
                conn.commit()
                if log_func and dropped_count > 0:
                    log_func(f"   🗑️ Cleaned up {dropped_count} temporary indexes")
                    
        except Exception as e:
            if log_func:
                log_func(f"   ⚠️ Unable to drop temporary indexes: {e}")
                
    def _validate_columns_parallel(self, validation_type: str, staging_table: str, schema_name: str, 
                                 columns: list, total_rows: int, chunk_size: int, log_func, date_format: str):
        """ตรวจสอบหลายคอลัมน์แบบ parallel เพื่อเพิ่มประสิทธิภาพ"""
        all_issues = []
        
        def validate_single_column(col):
            """ตรวจสอบคอลัมน์เดียวในแต่ละ thread"""
            try:
                with self.engine.connect() as conn:
                    if validation_type == 'numeric_validation':
                        return self._validate_numeric_chunked(
                            conn, staging_table, schema_name, [col], 
                            total_rows, chunk_size, None  # ไม่ส่ง log_func เพื่อป้องกัน race condition
                        )
                    elif validation_type == 'date_validation':
                        return self._validate_date_chunked(
                            conn, staging_table, schema_name, [col], 
                            total_rows, chunk_size, None, date_format
                        )
                    else:
                        return []
            except Exception as e:
                return []
        
        try:
            # ใช้ ThreadPoolExecutor สำหรับ parallel processing
            max_workers = min(len(columns), 3)  # จำกัดจำนวน threads ไม่เกิน 3
            
            if log_func:
                log_func(f"      🔄 Processing {len(columns)} columns in parallel ({max_workers} threads)...")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # ส่งงานแต่ละคอลัมน์ไปยัง thread แยกกัน
                future_to_column = {executor.submit(validate_single_column, col): col for col in columns}
                
                # รวบรวมผลลัพธ์
                for future in as_completed(future_to_column):
                    col = future_to_column[future]
                    try:
                        issues = future.result()
                        all_issues.extend(issues)
                        if log_func and issues:
                            log_func(f"        ✓ Column '{col}': {len(issues)} issue(s)")
                    except Exception as e:
                        if log_func:
                            log_func(f"        ❌ Error validating column '{col}': {e}")
            
            if log_func:
                log_func(f"      ✅ Parallel validation completed: {len(all_issues)} total issue(s)")
                
        except Exception as e:
            if log_func:
                log_func(f"      ⚠️ Parallel validation failed, falling back to sequential: {e}")
            # Fallback เป็นแบบปกติ
            with self.engine.connect() as conn:
                if validation_type == 'numeric_validation':
                    all_issues = self._validate_numeric_chunked(
                        conn, staging_table, schema_name, columns, 
                        total_rows, chunk_size, log_func
                    )
                elif validation_type == 'date_validation':
                    all_issues = self._validate_date_chunked(
                        conn, staging_table, schema_name, columns, 
                        total_rows, chunk_size, log_func, date_format
                    )
        
        return all_issues
    
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
    
    def _create_temp_indexes(self, staging_table: str, required_cols: Dict, schema_name: str, log_func=None):
        """สร้าง temporary indexes เพื่อเร่งการ validation"""
        try:
            with self.engine.connect() as conn:
                index_count = 0
                for col_name in required_cols.keys():
                    # สร้าง index ชั่วคราวสำหรับ column ที่มีข้อมูลเยอะ
                    index_name = f"temp_idx_{staging_table}_{col_name}".replace(' ', '_').replace('-', '_')[:128]
                    try:
                        # ตรวจสอบว่า index มีอยู่แล้วหรือไม่
                        check_sql = f"""
                            SELECT COUNT(*) FROM sys.indexes 
                            WHERE object_id = OBJECT_ID('{schema_name}.{staging_table}') 
                            AND name = '{index_name}'
                        """
                        result = conn.execute(text(check_sql))
                        if result.scalar() == 0:
                            # สร้าง index ใหม่
                            create_index_sql = f"""
                                CREATE NONCLUSTERED INDEX [{index_name}] 
                                ON {schema_name}.{staging_table} ([{col_name}])
                                WHERE [{col_name}] IS NOT NULL
                            """
                            conn.execute(text(create_index_sql))
                            index_count += 1
                    except Exception as e:
                        # ถ้าสร้าง index ไม่ได้ก็ข้าม (อาจเป็น column ที่มีข้อมูลยาวเกินไป)
                        pass
                        
                conn.commit()
                if log_func and index_count > 0:
                    log_func(f"   ✅ Created {index_count} temporary indexes for validation")
                    
        except Exception as e:
            if log_func:
                log_func(f"   ⚠️ Unable to create temporary indexes: {e}")
    
    def _drop_temp_indexes(self, staging_table: str, required_cols: Dict, schema_name: str, log_func=None):
        """ลบ temporary indexes หลังจาก validation เสร็จ"""
        try:
            with self.engine.connect() as conn:
                dropped_count = 0
                for col_name in required_cols.keys():
                    index_name = f"temp_idx_{staging_table}_{col_name}".replace(' ', '_').replace('-', '_')[:128]
                    try:
                        # ตรวจสอบและลบ index
                        check_sql = f"""
                            SELECT COUNT(*) FROM sys.indexes 
                            WHERE object_id = OBJECT_ID('{schema_name}.{staging_table}') 
                            AND name = '{index_name}'
                        """
                        result = conn.execute(text(check_sql))
                        if result.scalar() > 0:
                            drop_sql = f"DROP INDEX [{index_name}] ON {schema_name}.{staging_table}"
                            conn.execute(text(drop_sql))
                            dropped_count += 1
                    except Exception as e:
                        # ถ้าลบไม่ได้ก็ข้าม
                        pass
                        
                conn.commit()
                if log_func and dropped_count > 0:
                    log_func(f"   🗑️ Cleaned up {dropped_count} temporary indexes")
                    
        except Exception as e:
            if log_func:
                log_func(f"   ⚠️ Unable to drop temporary indexes: {e}")
                
    def _validate_columns_parallel(self, validation_type: str, staging_table: str, schema_name: str, 
                                 columns: list, total_rows: int, chunk_size: int, log_func, date_format: str):
        """ตรวจสอบหลายคอลัมน์แบบ parallel เพื่อเพิ่มประสิทธิภาพ"""
        all_issues = []
        
        def validate_single_column(col):
            """ตรวจสอบคอลัมน์เดียวในแต่ละ thread"""
            try:
                with self.engine.connect() as conn:
                    if validation_type == 'numeric_validation':
                        return self._validate_numeric_chunked(
                            conn, staging_table, schema_name, [col], 
                            total_rows, chunk_size, None  # ไม่ส่ง log_func เพื่อป้องกัน race condition
                        )
                    elif validation_type == 'date_validation':
                        return self._validate_date_chunked(
                            conn, staging_table, schema_name, [col], 
                            total_rows, chunk_size, None, date_format
                        )
                    else:
                        return []
            except Exception as e:
                return []
        
        try:
            # ใช้ ThreadPoolExecutor สำหรับ parallel processing
            max_workers = min(len(columns), 3)  # จำกัดจำนวน threads ไม่เกิน 3
            
            if log_func:
                log_func(f"      🔄 Processing {len(columns)} columns in parallel ({max_workers} threads)...")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # ส่งงานแต่ละคอลัมน์ไปยัง thread แยกกัน
                future_to_column = {executor.submit(validate_single_column, col): col for col in columns}
                
                # รวบรวมผลลัพธ์
                for future in as_completed(future_to_column):
                    col = future_to_column[future]
                    try:
                        issues = future.result()
                        all_issues.extend(issues)
                        if log_func and issues:
                            log_func(f"        ✓ Column '{col}': {len(issues)} issue(s)")
                    except Exception as e:
                        if log_func:
                            log_func(f"        ❌ Error validating column '{col}': {e}")
            
            if log_func:
                log_func(f"      ✅ Parallel validation completed: {len(all_issues)} total issue(s)")
                
        except Exception as e:
            if log_func:
                log_func(f"      ⚠️ Parallel validation failed, falling back to sequential: {e}")
            # Fallback เป็นแบบปกติ
            with self.engine.connect() as conn:
                if validation_type == 'numeric_validation':
                    all_issues = self._validate_numeric_chunked(
                        conn, staging_table, schema_name, columns, 
                        total_rows, chunk_size, log_func
                    )
                elif validation_type == 'date_validation':
                    all_issues = self._validate_date_chunked(
                        conn, staging_table, schema_name, columns, 
                        total_rows, chunk_size, log_func, date_format
                    )
        
        return all_issues
    
    def _validate_date_chunked(self, conn, staging_table, schema_name, columns, 
                               total_rows, chunk_size, log_func, date_format):
        """
        Validate date columns in chunks
        """
        issues = []
        
        for col in columns:
            col_literal = f"N'{col}'" if any(ord(c) > 127 for c in col) else f"'{col}'"
            
            # ปรับปรุงการทำความสะอาดข้อมูล - ใช้ TRANSLATE และ REPLACE น้อยลงเพื่อประสิทธิภาพที่ดีขึ้น
            cleaned_col_expression = f"""
                NULLIF(LTRIM(RTRIM(
                    REPLACE(REPLACE(
                        TRANSLATE([{col}], 
                            CHAR(9) + CHAR(10) + CHAR(13) + CHAR(160) + ',', 
                            '     '
                        ),
                        NCHAR(65279) + NCHAR(8203) + NCHAR(8288), ''
                    ), '  ', ' ')
                )), '')
            """
            
            # ปรับปรุงการแปลงรูปแบบวันที่ - ใช้ CASE WHEN แทน COALESCE เพื่อประสิทธิภาพที่ดีขึ้น
            if date_format == 'UK':  # DD-MM format
                error_query = f"""
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
                error_query = f"""
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
            
            try:
                result = conn.execute(text(error_query))
                error_count = result.scalar()
                
                if error_count > 0:
                    # ตรวจสอบข้อมูลที่ไม่สามารถแปลงได้เพื่อหาสาเหตุ
                    debug_query = f"""
                        SELECT TOP 5 [{col}] as raw_value, 
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
                        ORDER BY [{col}]
                    """
                    
                    debug_result = conn.execute(text(debug_query))
                    debug_rows = debug_result.fetchall()
                    
                    # สร้างรายงาน debug
                    debug_info = []
                    for row in debug_rows:
                        debug_info.append(f"Raw: '{row.raw_value}' -> Cleaned: '{row.cleaned_value}'")
                    
                    # Get sample examples
                    if date_format == 'UK':
                        examples_query = f"""
                            SELECT TOP 3 [{col}] as example_value
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
                        """
                    else:
                        examples_query = f"""
                            SELECT TOP 3 [{col}] as example_value
                            FROM {schema_name}.{staging_table}
                            WHERE {cleaned_col_expression} IS NOT NULL
                            AND CASE 
                                WHEN TRY_CONVERT(DATETIME, {cleaned_col_expression}, 101) IS NOT NULL THEN 1
                                WHEN TRY_CONVERT(DATETIME, {cleaned_col_expression}, 102) IS NOT NULL THEN 1
                                WHEN TRY_CONVERT(DATETIME, {cleaned_col_expression}, 110) IS NOT NULL THEN 1
                                WHEN TRY_CONVERT(DATETIME, {cleaned_col_expression}, 121) IS NOT NULL THEN 1
                                WHEN TRY_CONVERT(DATETIME, {cleaned_col_expression}, 103) IS NOT NULL THEN 1
                                ELSE 0
                            END = 0
                        """
                    
                    examples_result = conn.execute(text(examples_query))
                    examples = [str(row.example_value) for row in examples_result.fetchall()]
                    
                    issue = {
                        'validation_type': 'date_validation',
                        'column': col,
                        'error_count': error_count,
                        'percentage': round((error_count / total_rows) * 100, 2),
                        'examples': ', '.join(examples),
                        'date_format_used': date_format,
                        'debug_info': debug_info[:3]  # เพิ่มข้อมูล debug
                    }
                    issues.append(issue)
                    
                    # แสดงข้อมูล debug ใน log
                    if log_func:
                        log_func(f"        🔍 Debug info for {col}:")
                        for debug_line in debug_info[:2]:  # แสดงแค่ 2 แรก
                            log_func(f"          {debug_line}")
            
            except Exception as e:
                if log_func:
                    log_func(f"        ⚠️ Error checking column {col}: {e}")
        
        return issues
    
    def _create_temp_indexes(self, staging_table: str, required_cols: Dict, schema_name: str, log_func=None):
        """สร้าง temporary indexes เพื่อเร่งการ validation"""
        try:
            with self.engine.connect() as conn:
                index_count = 0
                for col_name in required_cols.keys():
                    # สร้าง index ชั่วคราวสำหรับ column ที่มีข้อมูลเยอะ
                    index_name = f"temp_idx_{staging_table}_{col_name}".replace(' ', '_').replace('-', '_')[:128]
                    try:
                        # ตรวจสอบว่า index มีอยู่แล้วหรือไม่
                        check_sql = f"""
                            SELECT COUNT(*) FROM sys.indexes 
                            WHERE object_id = OBJECT_ID('{schema_name}.{staging_table}') 
                            AND name = '{index_name}'
                        """
                        result = conn.execute(text(check_sql))
                        if result.scalar() == 0:
                            # สร้าง index ใหม่
                            create_index_sql = f"""
                                CREATE NONCLUSTERED INDEX [{index_name}] 
                                ON {schema_name}.{staging_table} ([{col_name}])
                                WHERE [{col_name}] IS NOT NULL
                            """
                            conn.execute(text(create_index_sql))
                            index_count += 1
                    except Exception as e:
                        # ถ้าสร้าง index ไม่ได้ก็ข้าม (อาจเป็น column ที่มีข้อมูลยาวเกินไป)
                        pass
                        
                conn.commit()
                if log_func and index_count > 0:
                    log_func(f"   ✅ Created {index_count} temporary indexes for validation")
                    
        except Exception as e:
            if log_func:
                log_func(f"   ⚠️ Unable to create temporary indexes: {e}")
    
    def _drop_temp_indexes(self, staging_table: str, required_cols: Dict, schema_name: str, log_func=None):
        """ลบ temporary indexes หลังจาก validation เสร็จ"""
        try:
            with self.engine.connect() as conn:
                dropped_count = 0
                for col_name in required_cols.keys():
                    index_name = f"temp_idx_{staging_table}_{col_name}".replace(' ', '_').replace('-', '_')[:128]
                    try:
                        # ตรวจสอบและลบ index
                        check_sql = f"""
                            SELECT COUNT(*) FROM sys.indexes 
                            WHERE object_id = OBJECT_ID('{schema_name}.{staging_table}') 
                            AND name = '{index_name}'
                        """
                        result = conn.execute(text(check_sql))
                        if result.scalar() > 0:
                            drop_sql = f"DROP INDEX [{index_name}] ON {schema_name}.{staging_table}"
                            conn.execute(text(drop_sql))
                            dropped_count += 1
                    except Exception as e:
                        # ถ้าลบไม่ได้ก็ข้าม
                        pass
                        
                conn.commit()
                if log_func and dropped_count > 0:
                    log_func(f"   🗑️ Cleaned up {dropped_count} temporary indexes")
                    
        except Exception as e:
            if log_func:
                log_func(f"   ⚠️ Unable to drop temporary indexes: {e}")
                
    def _validate_columns_parallel(self, validation_type: str, staging_table: str, schema_name: str, 
                                 columns: list, total_rows: int, chunk_size: int, log_func, date_format: str):
        """ตรวจสอบหลายคอลัมน์แบบ parallel เพื่อเพิ่มประสิทธิภาพ"""
        all_issues = []
        
        def validate_single_column(col):
            """ตรวจสอบคอลัมน์เดียวในแต่ละ thread"""
            try:
                with self.engine.connect() as conn:
                    if validation_type == 'numeric_validation':
                        return self._validate_numeric_chunked(
                            conn, staging_table, schema_name, [col], 
                            total_rows, chunk_size, None  # ไม่ส่ง log_func เพื่อป้องกัน race condition
                        )
                    elif validation_type == 'date_validation':
                        return self._validate_date_chunked(
                            conn, staging_table, schema_name, [col], 
                            total_rows, chunk_size, None, date_format
                        )
                    else:
                        return []
            except Exception as e:
                return []
        
        try:
            # ใช้ ThreadPoolExecutor สำหรับ parallel processing
            max_workers = min(len(columns), 3)  # จำกัดจำนวน threads ไม่เกิน 3
            
            if log_func:
                log_func(f"      🔄 Processing {len(columns)} columns in parallel ({max_workers} threads)...")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # ส่งงานแต่ละคอลัมน์ไปยัง thread แยกกัน
                future_to_column = {executor.submit(validate_single_column, col): col for col in columns}
                
                # รวบรวมผลลัพธ์
                for future in as_completed(future_to_column):
                    col = future_to_column[future]
                    try:
                        issues = future.result()
                        all_issues.extend(issues)
                        if log_func and issues:
                            log_func(f"        ✓ Column '{col}': {len(issues)} issue(s)")
                    except Exception as e:
                        if log_func:
                            log_func(f"        ❌ Error validating column '{col}': {e}")
            
            if log_func:
                log_func(f"      ✅ Parallel validation completed: {len(all_issues)} total issue(s)")
                
        except Exception as e:
            if log_func:
                log_func(f"      ⚠️ Parallel validation failed, falling back to sequential: {e}")
            # Fallback เป็นแบบปกติ
            with self.engine.connect() as conn:
                if validation_type == 'numeric_validation':
                    all_issues = self._validate_numeric_chunked(
                        conn, staging_table, schema_name, columns, 
                        total_rows, chunk_size, log_func
                    )
                elif validation_type == 'date_validation':
                    all_issues = self._validate_date_chunked(
                        conn, staging_table, schema_name, columns, 
                        total_rows, chunk_size, log_func, date_format
                    )
        
        return all_issues
    
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
    
    def _create_temp_indexes(self, staging_table: str, required_cols: Dict, schema_name: str, log_func=None):
        """สร้าง temporary indexes เพื่อเร่งการ validation"""
        try:
            with self.engine.connect() as conn:
                index_count = 0
                for col_name in required_cols.keys():
                    # สร้าง index ชั่วคราวสำหรับ column ที่มีข้อมูลเยอะ
                    index_name = f"temp_idx_{staging_table}_{col_name}".replace(' ', '_').replace('-', '_')[:128]
                    try:
                        # ตรวจสอบว่า index มีอยู่แล้วหรือไม่
                        check_sql = f"""
                            SELECT COUNT(*) FROM sys.indexes 
                            WHERE object_id = OBJECT_ID('{schema_name}.{staging_table}') 
                            AND name = '{index_name}'
                        """
                        result = conn.execute(text(check_sql))
                        if result.scalar() == 0:
                            # สร้าง index ใหม่
                            create_index_sql = f"""
                                CREATE NONCLUSTERED INDEX [{index_name}] 
                                ON {schema_name}.{staging_table} ([{col_name}])
                                WHERE [{col_name}] IS NOT NULL
                            """
                            conn.execute(text(create_index_sql))
                            index_count += 1
                    except Exception as e:
                        # ถ้าสร้าง index ไม่ได้ก็ข้าม (อาจเป็น column ที่มีข้อมูลยาวเกินไป)
                        pass
                        
                conn.commit()
                if log_func and index_count > 0:
                    log_func(f"   ✅ Created {index_count} temporary indexes for validation")
                    
        except Exception as e:
            if log_func:
                log_func(f"   ⚠️ Unable to create temporary indexes: {e}")
    
    def _drop_temp_indexes(self, staging_table: str, required_cols: Dict, schema_name: str, log_func=None):
        """ลบ temporary indexes หลังจาก validation เสร็จ"""
        try:
            with self.engine.connect() as conn:
                dropped_count = 0
                for col_name in required_cols.keys():
                    index_name = f"temp_idx_{staging_table}_{col_name}".replace(' ', '_').replace('-', '_')[:128]
                    try:
                        # ตรวจสอบและลบ index
                        check_sql = f"""
                            SELECT COUNT(*) FROM sys.indexes 
                            WHERE object_id = OBJECT_ID('{schema_name}.{staging_table}') 
                            AND name = '{index_name}'
                        """
                        result = conn.execute(text(check_sql))
                        if result.scalar() > 0:
                            drop_sql = f"DROP INDEX [{index_name}] ON {schema_name}.{staging_table}"
                            conn.execute(text(drop_sql))
                            dropped_count += 1
                    except Exception as e:
                        # ถ้าลบไม่ได้ก็ข้าม
                        pass
                        
                conn.commit()
                if log_func and dropped_count > 0:
                    log_func(f"   🗑️ Cleaned up {dropped_count} temporary indexes")
                    
        except Exception as e:
            if log_func:
                log_func(f"   ⚠️ Unable to drop temporary indexes: {e}")
                
    def _validate_columns_parallel(self, validation_type: str, staging_table: str, schema_name: str, 
                                 columns: list, total_rows: int, chunk_size: int, log_func, date_format: str):
        """ตรวจสอบหลายคอลัมน์แบบ parallel เพื่อเพิ่มประสิทธิภาพ"""
        all_issues = []
        
        def validate_single_column(col):
            """ตรวจสอบคอลัมน์เดียวในแต่ละ thread"""
            try:
                with self.engine.connect() as conn:
                    if validation_type == 'numeric_validation':
                        return self._validate_numeric_chunked(
                            conn, staging_table, schema_name, [col], 
                            total_rows, chunk_size, None  # ไม่ส่ง log_func เพื่อป้องกัน race condition
                        )
                    elif validation_type == 'date_validation':
                        return self._validate_date_chunked(
                            conn, staging_table, schema_name, [col], 
                            total_rows, chunk_size, None, date_format
                        )
                    else:
                        return []
            except Exception as e:
                return []
        
        try:
            # ใช้ ThreadPoolExecutor สำหรับ parallel processing
            max_workers = min(len(columns), 3)  # จำกัดจำนวน threads ไม่เกิน 3
            
            if log_func:
                log_func(f"      🔄 Processing {len(columns)} columns in parallel ({max_workers} threads)...")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # ส่งงานแต่ละคอลัมน์ไปยัง thread แยกกัน
                future_to_column = {executor.submit(validate_single_column, col): col for col in columns}
                
                # รวบรวมผลลัพธ์
                for future in as_completed(future_to_column):
                    col = future_to_column[future]
                    try:
                        issues = future.result()
                        all_issues.extend(issues)
                        if log_func and issues:
                            log_func(f"        ✓ Column '{col}': {len(issues)} issue(s)")
                    except Exception as e:
                        if log_func:
                            log_func(f"        ❌ Error validating column '{col}': {e}")
            
            if log_func:
                log_func(f"      ✅ Parallel validation completed: {len(all_issues)} total issue(s)")
                
        except Exception as e:
            if log_func:
                log_func(f"      ⚠️ Parallel validation failed, falling back to sequential: {e}")
            # Fallback เป็นแบบปกติ
            with self.engine.connect() as conn:
                if validation_type == 'numeric_validation':
                    all_issues = self._validate_numeric_chunked(
                        conn, staging_table, schema_name, columns, 
                        total_rows, chunk_size, log_func
                    )
                elif validation_type == 'date_validation':
                    all_issues = self._validate_date_chunked(
                        conn, staging_table, schema_name, columns, 
                        total_rows, chunk_size, log_func, date_format
                    )
        
        return all_issues
    
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
    
    def _create_temp_indexes(self, staging_table: str, required_cols: Dict, schema_name: str, log_func=None):
        """สร้าง temporary indexes เพื่อเร่งการ validation"""
        try:
            with self.engine.connect() as conn:
                index_count = 0
                for col_name in required_cols.keys():
                    # สร้าง index ชั่วคราวสำหรับ column ที่มีข้อมูลเยอะ
                    index_name = f"temp_idx_{staging_table}_{col_name}".replace(' ', '_').replace('-', '_')[:128]
                    try:
                        # ตรวจสอบว่า index มีอยู่แล้วหรือไม่
                        check_sql = f"""
                            SELECT COUNT(*) FROM sys.indexes 
                            WHERE object_id = OBJECT_ID('{schema_name}.{staging_table}') 
                            AND name = '{index_name}'
                        """
                        result = conn.execute(text(check_sql))
                        if result.scalar() == 0:
                            # สร้าง index ใหม่
                            create_index_sql = f"""
                                CREATE NONCLUSTERED INDEX [{index_name}] 
                                ON {schema_name}.{staging_table} ([{col_name}])
                                WHERE [{col_name}] IS NOT NULL
                            """
                            conn.execute(text(create_index_sql))
                            index_count += 1
                    except Exception as e:
                        # ถ้าสร้าง index ไม่ได้ก็ข้าม (อาจเป็น column ที่มีข้อมูลยาวเกินไป)
                        pass
                        
                conn.commit()
                if log_func and index_count > 0:
                    log_func(f"   ✅ Created {index_count} temporary indexes for validation")
                    
        except Exception as e:
            if log_func:
                log_func(f"   ⚠️ Unable to create temporary indexes: {e}")
    
    def _drop_temp_indexes(self, staging_table: str, required_cols: Dict, schema_name: str, log_func=None):
        """ลบ temporary indexes หลังจาก validation เสร็จ"""
        try:
            with self.engine.connect() as conn:
                dropped_count = 0
                for col_name in required_cols.keys():
                    index_name = f"temp_idx_{staging_table}_{col_name}".replace(' ', '_').replace('-', '_')[:128]
                    try:
                        # ตรวจสอบและลบ index
                        check_sql = f"""
                            SELECT COUNT(*) FROM sys.indexes 
                            WHERE object_id = OBJECT_ID('{schema_name}.{staging_table}') 
                            AND name = '{index_name}'
                        """
                        result = conn.execute(text(check_sql))
                        if result.scalar() > 0:
                            drop_sql = f"DROP INDEX [{index_name}] ON {schema_name}.{staging_table}"
                            conn.execute(text(drop_sql))
                            dropped_count += 1
                    except Exception as e:
                        # ถ้าลบไม่ได้ก็ข้าม
                        pass
                        
                conn.commit()
                if log_func and dropped_count > 0:
                    log_func(f"   🗑️ Cleaned up {dropped_count} temporary indexes")
                    
        except Exception as e:
            if log_func:
                log_func(f"   ⚠️ Unable to drop temporary indexes: {e}")
                
    def _validate_columns_parallel(self, validation_type: str, staging_table: str, schema_name: str, 
                                 columns: list, total_rows: int, chunk_size: int, log_func, date_format: str):
        """ตรวจสอบหลายคอลัมน์แบบ parallel เพื่อเพิ่มประสิทธิภาพ"""
        all_issues = []
        
        def validate_single_column(col):
            """ตรวจสอบคอลัมน์เดียวในแต่ละ thread"""
            try:
                with self.engine.connect() as conn:
                    if validation_type == 'numeric_validation':
                        return self._validate_numeric_chunked(
                            conn, staging_table, schema_name, [col], 
                            total_rows, chunk_size, None  # ไม่ส่ง log_func เพื่อป้องกัน race condition
                        )
                    elif validation_type == 'date_validation':
                        return self._validate_date_chunked(
                            conn, staging_table, schema_name, [col], 
                            total_rows, chunk_size, None, date_format
                        )
                    else:
                        return []
            except Exception as e:
                return []
        
        try:
            # ใช้ ThreadPoolExecutor สำหรับ parallel processing
            max_workers = min(len(columns), 3)  # จำกัดจำนวน threads ไม่เกิน 3
            
            if log_func:
                log_func(f"      🔄 Processing {len(columns)} columns in parallel ({max_workers} threads)...")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # ส่งงานแต่ละคอลัมน์ไปยัง thread แยกกัน
                future_to_column = {executor.submit(validate_single_column, col): col for col in columns}
                
                # รวบรวมผลลัพธ์
                for future in as_completed(future_to_column):
                    col = future_to_column[future]
                    try:
                        issues = future.result()
                        all_issues.extend(issues)
                        if log_func and issues:
                            log_func(f"        ✓ Column '{col}': {len(issues)} issue(s)")
                    except Exception as e:
                        if log_func:
                            log_func(f"        ❌ Error validating column '{col}': {e}")
            
            if log_func:
                log_func(f"      ✅ Parallel validation completed: {len(all_issues)} total issue(s)")
                
        except Exception as e:
            if log_func:
                log_func(f"      ⚠️ Parallel validation failed, falling back to sequential: {e}")
            # Fallback เป็นแบบปกติ
            with self.engine.connect() as conn:
                if validation_type == 'numeric_validation':
                    all_issues = self._validate_numeric_chunked(
                        conn, staging_table, schema_name, columns, 
                        total_rows, chunk_size, log_func
                    )
                elif validation_type == 'date_validation':
                    all_issues = self._validate_date_chunked(
                        conn, staging_table, schema_name, columns, 
                        total_rows, chunk_size, log_func, date_format
                    )
        
        return all_issues