"""
Main validation orchestrator that coordinates all validation modules
"""

import logging
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy import text

from .base_validator import BaseValidator
from .numeric_validator import NumericValidator
from .date_validator import DateValidator
from .string_validator import StringValidator
from .boolean_validator import BooleanValidator
from .schema_validator import SchemaValidator
from .index_manager import IndexManager


class MainValidator(BaseValidator):
    """
    Main orchestrator for data validation.
    
    Coordinates between different validators and manages validation workflow.
    """
    
    def __init__(self, engine):
        """
        Initialize MainValidator
        
        Args:
            engine: SQLAlchemy engine instance
        """
        super().__init__(engine)
        
        # สร้าง validator instances
        self.numeric_validator = NumericValidator(engine)
        self.date_validator = DateValidator(engine)
        self.string_validator = StringValidator(engine)
        self.boolean_validator = BooleanValidator(engine)
        self.schema_validator = SchemaValidator(engine)
        self.index_manager = IndexManager(engine)
    
    def validate(self, conn, staging_table: str, schema_name: str, columns: List, 
                total_rows: int, chunk_size: int, log_func=None, **kwargs) -> List[Dict]:
        """
        Implementation of abstract method from BaseValidator
        
        For MainValidator, this method is not used directly 
        but validate_data_in_staging is used instead
        
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
            List[Dict]: Empty list (not used directly)
        """
        # MainValidator ไม่ใช้ method นี้โดยตรง
        # ใช้ validate_data_in_staging แทน
        return []
    
    def validate_data_in_staging(self, staging_table: str, logic_type: str, required_cols: Dict, 
                                schema_name: str = 'bronze', log_func=None, progress_callback=None, 
                                date_format: str = 'UK') -> Dict:
        """
        Main method for validating data in staging table
        
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
            
            total_rows = self._get_total_rows(staging_table, schema_name)
            
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
            
            index_count = self.index_manager.create_temp_indexes(staging_table, required_cols, schema_name, log_func)
            
            # Phase 3: Schema compatibility check
            if progress_callback:
                progress_callback(0.2, "Schema Check", "Verifying column compatibility...")
            
            if log_func:
                log_func(f"   🔍 Checking schema compatibility...")
            
            schema_issues = self.schema_validator.validate_schema_compatibility(
                staging_table, required_cols, schema_name, log_func
            )
            if schema_issues:
                validation_results['warnings'].extend(schema_issues)
            
            # Phase 4: Build and run validation phases
            validation_phases = self._build_validation_phases(required_cols, date_format)
            
            if log_func and validation_phases:
                log_func(f"   📋 Running {len(validation_phases)} validation phases...")
            
            # Phase 5-8: Run validation phases
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
                    if issue['percentage'] > 50:
                        validation_results['is_valid'] = False
                        validation_results['issues'].append(issue)
                    elif issue['percentage'] > 10:
                        validation_results['warnings'].append(issue)
            
            # Phase 9: Final summary
            if progress_callback:
                progress_callback(0.9, "Summary", "Preparing validation results...")
            
            validation_results['summary'] = self._generate_summary(validation_results, log_func)
            
            # Cleanup: ลบ temporary indexes
            if log_func:
                log_func(f"   🧹 Cleaning up temporary indexes...")
            
            self.index_manager.drop_temp_indexes(staging_table, required_cols, schema_name, log_func)
            
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
    
    def _get_total_rows(self, staging_table: str, schema_name: str) -> int:
        """
        Get total number of rows in staging table
        
        Args:
            staging_table: Staging table name
            schema_name: Schema name
            
        Returns:
            int: Total number of rows
        """
        with self.engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {schema_name}.{staging_table}"))
            return result.scalar()
    
    def _build_validation_phases(self, required_cols: Dict, date_format: str) -> Dict:
        """
        Build validation phases for chunked processing
        
        Args:
            required_cols: Required columns and data types
            date_format: Date format preference
            
        Returns:
            Dict: Validation phases configuration
        """
        phases = {}
        
        # กรองเฉพาะคอลัมน์ที่มีใน staging table (ไม่รวม updated_at)
        staging_cols = {col: dtype for col, dtype in required_cols.items() if col != 'updated_at'}
        
        # Phase 1: Numeric validation
        numeric_columns = self.numeric_validator.get_numeric_columns(staging_cols)
        if numeric_columns:
            phases['Numeric Data Types'] = {
                'type': 'numeric_validation',
                'validator': self.numeric_validator,
                'columns': numeric_columns,
                'chunk_size': 10000
            }
        
        # Phase 2: Date validation
        date_columns = self.date_validator.get_date_columns(staging_cols)
        if date_columns:
            phases['Date/DateTime Formats'] = {
                'type': 'date_validation',
                'validator': self.date_validator,
                'columns': date_columns,
                'chunk_size': 10000
            }
        
        # Phase 3: String length validation
        string_columns = self.string_validator.get_string_columns_with_length(staging_cols)
        if string_columns:
            phases['String Length Limits'] = {
                'type': 'string_length_validation',
                'validator': self.string_validator,
                'columns': string_columns,
                'chunk_size': 15000
            }
        
        # Phase 4: Boolean validation
        boolean_columns = self.boolean_validator.get_boolean_columns(staging_cols)
        if boolean_columns:
            phases['Boolean Values'] = {
                'type': 'boolean_validation',
                'validator': self.boolean_validator,
                'columns': boolean_columns,
                'chunk_size': 20000
            }
        
        return phases
    
    def _run_validation_phase(self, phase_name: str, phase_data: Dict, schema_name: str, 
                             staging_table: str, total_rows: int, log_func, progress_callback, 
                             base_progress: float, date_format: str) -> List[Dict]:
        """
        Run a single validation phase
        
        Args:
            phase_name: Name of the validation phase
            phase_data: Phase configuration data
            schema_name: Schema name
            staging_table: Staging table name
            total_rows: Total number of rows
            log_func: Logging function
            progress_callback: Progress callback function
            base_progress: Base progress value
            date_format: Date format preference
            
        Returns:
            List[Dict]: List of validation issues
        """
        issues = []
        validator = phase_data['validator']
        columns = phase_data['columns']
        chunk_size = phase_data.get('chunk_size', 10000)
        
        try:
            # สำหรับคอลัมน์หลายตัว ใช้ parallel processing
            if len(columns) > 1 and phase_data['type'] in ['numeric_validation', 'date_validation']:
                issues = self._validate_columns_parallel(
                    validator, staging_table, schema_name, columns, 
                    total_rows, chunk_size, log_func, date_format=date_format
                )
            else:
                # สำหรับคอลัมน์เดียวหรือ validation ประเภทอื่น ใช้แบบปกติ
                with self.engine.connect() as conn:
                    issues = validator.validate(
                        conn, staging_table, schema_name, columns, 
                        total_rows, chunk_size, log_func, date_format=date_format
                    )
            
            # Log results
            if issues:
                if log_func:
                    log_func(f"      ❌ Found {len(issues)} issue type(s) in {phase_name}")
                
                for issue in issues:
                    if log_func and issue['error_count'] > 0:
                        status = "❌" if issue['percentage'] > 50 else "⚠️"
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
    
    def _validate_columns_parallel(self, validator, staging_table: str, schema_name: str, 
                                 columns: List, total_rows: int, chunk_size: int, 
                                 log_func, **kwargs) -> List[Dict]:
        """
        Validate multiple columns in parallel for improved performance
        
        Args:
            validator: Validator instance
            staging_table: Staging table name
            schema_name: Schema name
            columns: List of columns
            total_rows: Total number of rows
            chunk_size: Chunk size
            log_func: Logging function
            **kwargs: Additional parameters
            
        Returns:
            List[Dict]: All validation issues
        """
        all_issues = []
        
        def validate_single_column(col):
            """ตรวจสอบคอลัมน์เดียวในแต่ละ thread"""
            try:
                with self.engine.connect() as conn:
                    return validator.validate(
                        conn, staging_table, schema_name, [col], 
                        total_rows, chunk_size, None, **kwargs  # ไม่ส่ง log_func เพื่อป้องกัน race condition
                    )
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
                all_issues = validator.validate(
                    conn, staging_table, schema_name, columns, 
                    total_rows, chunk_size, log_func, **kwargs
                )
        
        return all_issues
    
    def _generate_summary(self, validation_results: Dict, log_func) -> str:
        """
        Generate summary of validation results
        
        Args:
            validation_results: Validation results dictionary
            log_func: Logging function
            
        Returns:
            str: Summary message
        """
        if not validation_results['is_valid']:
            serious_issues = len(validation_results['issues'])
            warnings_count = len(validation_results['warnings'])
            summary = f"Found {serious_issues} serious issues and {warnings_count} warnings - cannot import data"
        elif validation_results['warnings']:
            warnings_count = len(validation_results['warnings'])
            summary = f"Found {warnings_count} warnings; data can be imported"
            if log_func:
                log_func(f"✅ Data validation passed (with {warnings_count} warnings)")
        else:
            summary = "All data valid"
            if log_func:
                log_func(f"✅ All data passed validation")
        
        return summary
    
    def get_validation_statistics(self, staging_table: str, schema_name: str) -> Dict:
        """
        Get statistics of data in staging table
        
        Args:
            staging_table: Staging table name
            schema_name: Schema name
            
        Returns:
            Dict: Validation statistics
        """
        stats = {
            'table_name': staging_table,
            'schema_name': schema_name,
            'total_rows': self._get_total_rows(staging_table, schema_name),
            'index_usage': self.index_manager.get_index_usage_stats(schema_name, staging_table)
        }
        
        return stats
