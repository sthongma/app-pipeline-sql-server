"""
Data Validation Service for PIPELINE_SQLSERVER

Handles data validation in staging tables using modular validation architecture
"""

import logging
from typing import Dict

from .validation.main_validator import MainValidator


class DataValidationService:
    """
    Data validation service for staging tables
    
    Validates data types and format before final insertion using modular validators
    """
    
    def __init__(self, engine) -> None:
        """
        Initialize DataValidationService
        
        Args:
            engine: SQLAlchemy engine instance
        """
        self.engine = engine
        self.logger = logging.getLogger(__name__)
        
        # สร้าง main validator ที่จะจัดการ validation ทั้งหมด
        self.main_validator = MainValidator(engine)

    def validate_data_in_staging(self, staging_table: str, logic_type: str, required_cols: Dict, 
                                schema_name: str = 'bronze', log_func=None, progress_callback=None, 
                                date_format: str = 'UK') -> Dict:
        """
        Validate data correctness in staging table using modular validation approach
        
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
        return self.main_validator.validate_data_in_staging(
            staging_table=staging_table,
            logic_type=logic_type,
            required_cols=required_cols,
            schema_name=schema_name,
            log_func=log_func,
            progress_callback=progress_callback,
            date_format=date_format
        )
    
    def get_validation_statistics(self, staging_table: str, schema_name: str = 'bronze') -> Dict:
        """
        Get validation statistics for a staging table
        
        Args:
            staging_table: Staging table name
            schema_name: Schema name
            
        Returns:
            Dict: Validation statistics
        """
        return self.main_validator.get_validation_statistics(staging_table, schema_name)
    
    def validate_numeric_data(self, staging_table: str, columns: list, 
                             schema_name: str = 'bronze', log_func=None) -> Dict:
        """
        Validate numeric data specifically
        
        Args:
            staging_table: Staging table name
            columns: List of numeric column names
            schema_name: Schema name
            log_func: Logging function
            
        Returns:
            Dict: Numeric validation results
        """
        total_rows = self.main_validator._get_total_rows(staging_table, schema_name)
        
        with self.engine.connect() as conn:
            issues = self.main_validator.numeric_validator.validate(
                conn, staging_table, schema_name, columns, total_rows, 10000, log_func
            )
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'total_columns_checked': len(columns),
            'columns_with_issues': len(issues)
        }
    
    def validate_date_data(self, staging_table: str, columns: list, 
                          schema_name: str = 'bronze', date_format: str = 'UK', log_func=None) -> Dict:
        """
        Validate date data specifically
        
        Args:
            staging_table: Staging table name
            columns: List of date column names
            schema_name: Schema name
            date_format: Date format preference
            log_func: Logging function
            
        Returns:
            Dict: Date validation results
        """
        total_rows = self.main_validator._get_total_rows(staging_table, schema_name)
        
        with self.engine.connect() as conn:
            issues = self.main_validator.date_validator.validate(
                conn, staging_table, schema_name, columns, total_rows, 10000, log_func, 
                date_format=date_format
            )
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'total_columns_checked': len(columns),
            'columns_with_issues': len(issues),
            'date_format_used': date_format
        }
    
    def validate_string_lengths(self, staging_table: str, columns_with_lengths: list, 
                               schema_name: str = 'bronze', log_func=None) -> Dict:
        """
        Validate string length constraints
        
        Args:
            staging_table: Staging table name
            columns_with_lengths: List of tuples (column_name, max_length)
            schema_name: Schema name
            log_func: Logging function
            
        Returns:
            Dict: String validation results
        """
        total_rows = self.main_validator._get_total_rows(staging_table, schema_name)
        
        with self.engine.connect() as conn:
            issues = self.main_validator.string_validator.validate(
                conn, staging_table, schema_name, columns_with_lengths, total_rows, 15000, log_func
            )
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'total_columns_checked': len(columns_with_lengths),
            'columns_with_issues': len(issues)
        }
    
    def validate_boolean_data(self, staging_table: str, columns: list, 
                             schema_name: str = 'bronze', log_func=None) -> Dict:
        """
        Validate boolean data specifically
        
        Args:
            staging_table: Staging table name
            columns: List of boolean column names
            schema_name: Schema name
            log_func: Logging function
            
        Returns:
            Dict: Boolean validation results
        """
        total_rows = self.main_validator._get_total_rows(staging_table, schema_name)
        
        with self.engine.connect() as conn:
            issues = self.main_validator.boolean_validator.validate(
                conn, staging_table, schema_name, columns, total_rows, 20000, log_func
            )
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'total_columns_checked': len(columns),
            'columns_with_issues': len(issues)
        }
    
    def check_schema_compatibility(self, staging_table: str, required_cols: Dict, 
                                  schema_name: str = 'bronze', log_func=None) -> Dict:
        """
        Check schema compatibility between staging and final tables
        
        Args:
            staging_table: Staging table name
            required_cols: Required columns and data types
            schema_name: Schema name
            log_func: Logging function
            
        Returns:
            Dict: Schema compatibility results
        """
        issues = self.main_validator.schema_validator.validate_schema_compatibility(
            staging_table, required_cols, schema_name, log_func
        )
        
        return {
            'is_compatible': len([i for i in issues if i.get('severity') == 'error']) == 0,
            'issues': issues,
            'warnings': [i for i in issues if i.get('severity') in ['warning', 'info']],
            'errors': [i for i in issues if i.get('severity') == 'error']
        }
    
    def optimize_validation_performance(self, staging_table: str, required_cols: Dict, 
                                      schema_name: str = 'bronze', log_func=None) -> Dict:
        """
        Create temporary indexes to optimize validation performance
        
        Args:
            staging_table: Staging table name
            required_cols: Required columns and data types
            schema_name: Schema name
            log_func: Logging function
            
        Returns:
            Dict: Performance optimization results
        """
        # สร้าง temporary indexes
        indexes_created = self.main_validator.index_manager.create_temp_indexes(
            staging_table, required_cols, schema_name, log_func
        )
        
        # ดึงสถิติการใช้งาน indexes
        index_stats = self.main_validator.index_manager.get_index_usage_stats(schema_name, staging_table)
        
        return {
            'indexes_created': indexes_created,
            'index_statistics': index_stats,
            'optimization_active': indexes_created > 0
        }
    
    def cleanup_validation_resources(self, staging_table: str, required_cols: Dict, 
                                   schema_name: str = 'bronze', log_func=None) -> Dict:
        """
        Clean up temporary validation resources (indexes, etc.)
        
        Args:
            staging_table: Staging table name
            required_cols: Required columns and data types
            schema_name: Schema name
            log_func: Logging function
            
        Returns:
            Dict: Cleanup results
        """
        indexes_dropped = self.main_validator.index_manager.drop_temp_indexes(
            staging_table, required_cols, schema_name, log_func
        )
        
        return {
            'indexes_dropped': indexes_dropped,
            'cleanup_successful': True
        }
    
    def get_comprehensive_report(self, staging_table: str, required_cols: Dict, 
                               schema_name: str = 'bronze', date_format: str = 'UK', 
                               log_func=None) -> Dict:
        """
        Get a comprehensive validation report for a staging table
        
        Args:
            staging_table: Staging table name
            required_cols: Required columns and data types
            schema_name: Schema name
            date_format: Date format preference
            log_func: Logging function
            
        Returns:
            Dict: Comprehensive validation report
        """
        # รัน validation แบบเต็มรูปแบบ
        main_results = self.validate_data_in_staging(
            staging_table, 'comprehensive', required_cols, schema_name, log_func, None, date_format
        )
        
        # ดึงสถิติเพิ่มเติม
        statistics = self.get_validation_statistics(staging_table, schema_name)
        
        # ตรวจสอบ schema compatibility
        schema_results = self.check_schema_compatibility(staging_table, required_cols, schema_name, log_func)
        
        return {
            'table_info': {
                'staging_table': staging_table,
                'schema_name': schema_name,
                'total_rows': statistics.get('total_rows', 0),
                'date_format_used': date_format
            },
            'validation_results': main_results,
            'schema_compatibility': schema_results,
            'statistics': statistics,
            'summary': {
                'overall_valid': main_results['is_valid'] and schema_results['is_compatible'],
                'total_issues': len(main_results.get('issues', [])),
                'total_warnings': len(main_results.get('warnings', [])) + len(schema_results.get('warnings', [])),
                'can_proceed': main_results['is_valid']
            }
        }
