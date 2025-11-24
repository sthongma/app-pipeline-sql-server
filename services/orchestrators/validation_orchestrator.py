"""
Validation Orchestrator for PIPELINE_SQLSERVER

Orchestrator service for managing various validation services
Coordinates between validators and validation-related services
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd

from services.database.validation.main_validator import MainValidator
from services.database.validation.date_validator import DateValidator
from services.database.validation.numeric_validator import NumericValidator
from services.database.validation.string_validator import StringValidator
from services.database.validation.boolean_validator import BooleanValidator
from services.database.validation.schema_validator import SchemaValidator
from services.database.validation.index_manager import IndexManager


class ValidationOrchestrator:
    """
    Validation Orchestrator Service
    
    Acts as orchestrator for managing:
    - Data validation
    - Schema validation
    - Column validation
    - Type validation
    - Index management
    """
    
    def __init__(self, engine=None, log_callback=None):
        """
        Initialize Validation Orchestrator
        
        Args:
            engine: SQLAlchemy engine
            log_callback: Function for logging
        """
        self.engine = engine
        self.log_callback = log_callback if log_callback else (lambda msg: None)
        self.logger = logging.getLogger(__name__)
        
        # Initialize validators
        self._initialize_validators()
        
        self.logger.info("ValidationOrchestrator initialized")
    
    def _initialize_validators(self):
        """เริ่มต้น validators ทั้งหมด"""
        try:
            self.main_validator = MainValidator(engine=self.engine)
            self.date_validator = DateValidator(engine=self.engine)
            self.numeric_validator = NumericValidator(engine=self.engine)
            self.string_validator = StringValidator(engine=self.engine)
            self.boolean_validator = BooleanValidator(engine=self.engine)
            self.schema_validator = SchemaValidator(engine=self.engine)
            self.index_manager = IndexManager(engine=self.engine)
            
            self.logger.info("All validators initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing validators: {e}")
            raise
    
    def comprehensive_validation(self, df: pd.DataFrame, logic_type: str, 
                                schema_name: str = 'bronze') -> Dict[str, Any]:
        """
        ตรวจสอบข้อมูลแบบครอบคลุม
        
        Args:
            df: DataFrame ที่ต้องการตรวจสอบ
            logic_type: ประเภทของ logic
            schema_name: ชื่อ schema
            
        Returns:
            Dict: ผลการตรวจสอบแบบครอบคลุม
        """
        try:
            self.log_callback("Starting comprehensive data validation...")
            
            validation_results = {
                'overall_success': True,
                'total_issues': 0,
                'column_validation': {},
                'data_validation': {},
                'schema_validation': {},
                'index_validation': {},
                'summary': {},
                'recommendations': []
            }
            
            # 1. Column Structure Validation
            self.log_callback("  Validating column structure...")
            column_valid, column_msg = self.main_validator.validate_columns(df, logic_type)
            validation_results['column_validation'] = {
                'success': column_valid,
                'message': column_msg
            }
            
            if not column_valid:
                validation_results['overall_success'] = False
                validation_results['total_issues'] += 1
            
            # 2. Data Type and Content Validation
            self.log_callback("  🔢 Validating data types and content...")
            data_validation = self._validate_data_content(df, logic_type)
            validation_results['data_validation'] = data_validation
            
            if not data_validation['success']:
                validation_results['overall_success'] = False
                validation_results['total_issues'] += data_validation.get('issue_count', 1)
            
            # 3. Schema Validation (if engine available)
            if self.engine:
                self.log_callback("  Validating database schema...")
                schema_validation = self._validate_schema_compatibility(schema_name, logic_type)
                validation_results['schema_validation'] = schema_validation
                
                if not schema_validation['success']:
                    validation_results['overall_success'] = False
                    validation_results['total_issues'] += 1
                
                # 4. Index Validation
                self.log_callback("  Validating database indexes...")
                index_validation = self._validate_indexes(schema_name, logic_type)
                validation_results['index_validation'] = index_validation
                
                if not index_validation['success']:
                    validation_results['total_issues'] += index_validation.get('issue_count', 1)
            
            # 5. Generate Summary and Recommendations
            validation_results['summary'] = self._generate_validation_summary(validation_results)
            validation_results['recommendations'] = self._generate_recommendations(validation_results)
            
            if validation_results['overall_success']:
                self.log_callback("Comprehensive validation completed successfully")
            else:
                self.log_callback(f"Warning: Validation completed with {validation_results['total_issues']} issues")
            
            return validation_results
            
        except Exception as e:
            error_msg = f"Error in comprehensive validation: {str(e)}"
            self.logger.error(error_msg)
            self.log_callback(f"Error: {error_msg}")
            return {
                'overall_success': False,
                'error': error_msg,
                'total_issues': 1
            }
    
    def _validate_data_content(self, df: pd.DataFrame, logic_type: str) -> Dict[str, Any]:
        """ตรวจสอบเนื้อหาข้อมูล"""
        try:
            results = {
                'success': True,
                'issue_count': 0,
                'column_results': {},
                'type_validation': {},
                'cleaning_suggestions': []
            }
            
            # ตรวจสอบแต่ละคอลัมน์
            for column in df.columns:
                column_results = {}
                
                # ตรวจสอบประเภทข้อมูล
                if 'date' in column.lower() or 'วันที่' in column:
                    # Date validation
                    date_result = self.date_validator.validate_date_column(df[column])
                    column_results['date_validation'] = date_result
                    
                elif df[column].dtype in ['int64', 'float64'] or 'จำนวน' in column:
                    # Numeric validation
                    numeric_result = self.numeric_validator.validate_numeric_column(df[column])
                    column_results['numeric_validation'] = numeric_result
                    
                elif df[column].dtype == 'bool' or column.lower() in ['active', 'enabled']:
                    # Boolean validation
                    boolean_result = self.boolean_validator.validate_boolean_column(df[column])
                    column_results['boolean_validation'] = boolean_result
                    
                else:
                    # String validation
                    string_result = self.string_validator.validate_string_column(df[column])
                    column_results['string_validation'] = string_result
                
                # นับปัญหา
                for validation_type, validation_result in column_results.items():
                    if not validation_result.get('is_valid', True):
                        results['issue_count'] += 1
                        results['success'] = False
                
                results['column_results'][column] = column_results
            
            return results
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'issue_count': 1
            }
    
    def _validate_schema_compatibility(self, schema_name: str, logic_type: str) -> Dict[str, Any]:
        """ตรวจสอบความเข้ากันได้ของ schema"""
        try:
            # ใช้ schema validator
            validation_result = self.schema_validator.validate_schema_exists(schema_name)
            
            return {
                'success': validation_result,
                'schema_name': schema_name,
                'message': f"Schema '{schema_name}' validation: {'passed' if validation_result else 'failed'}"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'schema_name': schema_name
            }
    
    def _validate_indexes(self, schema_name: str, logic_type: str) -> Dict[str, Any]:
        """ตรวจสอบ indexes"""
        try:
            # ใช้ index manager
            index_results = self.index_manager.validate_indexes(schema_name)
            
            return {
                'success': True,
                'indexes': index_results,
                'message': "Index validation completed"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'issue_count': 1
            }
    
    def _generate_validation_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """สร้างสรุปผลการตรวจสอบ"""
        summary = {
            'total_checks': 0,
            'passed_checks': 0,
            'failed_checks': 0,
            'categories': {}
        }
        
        # นับผลการตรวจสอบ
        for category, result in results.items():
            if category in ['column_validation', 'data_validation', 'schema_validation', 'index_validation']:
                summary['total_checks'] += 1
                if result.get('success', False):
                    summary['passed_checks'] += 1
                else:
                    summary['failed_checks'] += 1
                
                summary['categories'][category] = result.get('success', False)
        
        summary['success_rate'] = (summary['passed_checks'] / summary['total_checks'] * 100) if summary['total_checks'] > 0 else 0
        
        return summary
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """สร้างคำแนะนำ"""
        recommendations = []
        
        # คำแนะนำสำหรับปัญหาคอลัมน์
        if not results['column_validation'].get('success', True):
            recommendations.append("ตรวจสอบและแก้ไขโครงสร้างคอลัมน์ให้ตรงตามมาตรฐาน")
        
        # คำแนะนำสำหรับปัญหาข้อมูล
        if not results['data_validation'].get('success', True):
            recommendations.append("ทำความสะอาดข้อมูลก่อนนำเข้าฐานข้อมูล")
        
        # คำแนะนำสำหรับปัญหา schema
        if not results['schema_validation'].get('success', True):
            recommendations.append("ตรวจสอบและสร้าง schema ที่จำเป็น")
        
        # คำแนะนำสำหรับปัญหา index
        if not results['index_validation'].get('success', True):
            recommendations.append("ตรวจสอบและสร้าง indexes ที่จำเป็น")
        
        if not recommendations:
            recommendations.append("ข้อมูลพร้อมสำหรับการนำเข้าฐานข้อมูล")
        
        return recommendations
    
    def quick_validate(self, df: pd.DataFrame, logic_type: str) -> Tuple[bool, str]:
        """
        ตรวจสอบข้อมูลแบบรวดเร็ว
        
        Args:
            df: DataFrame ที่ต้องการตรวจสอบ
            logic_type: ประเภทของ logic
            
        Returns:
            Tuple[bool, str]: (is_valid, message)
        """
        try:
            # ตรวจสอบโครงสร้างคอลัมน์
            column_valid, column_msg = self.main_validator.validate_columns(df, logic_type)
            
            if not column_valid:
                return False, f"Column validation failed: {column_msg}"
            
            # ตรวจสอบข้อมูลพื้นฐาน
            if df.empty:
                return False, "DataFrame is empty"
            
            if df.isnull().all().any():
                return False, "Found columns with all null values"
            
            return True, "Quick validation passed"
            
        except Exception as e:
            return False, f"Quick validation error: {str(e)}"
    
    def validate_before_upload(self, df: pd.DataFrame, logic_type: str, 
                              schema_name: str = 'bronze') -> Tuple[bool, str, Dict[str, Any]]:
        """
        ตรวจสอบก่อนอัปโหลดข้อมูล
        
        Args:
            df: DataFrame ที่ต้องการตรวจสอบ
            logic_type: ประเภทของ logic
            schema_name: ชื่อ schema
            
        Returns:
            Tuple[bool, str, Dict]: (is_ready, message, validation_details)
        """
        try:
            self.log_callback("Pre-upload validation...")
            
            # ตรวจสอบแบบครอบคลุม
            validation_results = self.comprehensive_validation(df, logic_type, schema_name)
            
            is_ready = validation_results['overall_success']
            message = "Ready for upload" if is_ready else f"Validation failed with {validation_results['total_issues']} issues"
            
            return is_ready, message, validation_results
            
        except Exception as e:
            error_msg = f"Pre-upload validation error: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg, {'error': error_msg}
    
    # Convenience methods for individual validators
    def clean_data(self, df: pd.DataFrame, logic_type: str) -> pd.DataFrame:
        """ทำความสะอาดข้อมูล"""
        try:
            cleaned_df = df.copy()
            
            # ทำความสะอาดแต่ละคอลัมน์ตามประเภท
            for column in cleaned_df.columns:
                if 'date' in column.lower() or 'วันที่' in column:
                    cleaned_df[column] = self.date_validator.clean_date_column(cleaned_df[column])
                elif cleaned_df[column].dtype in ['int64', 'float64']:
                    cleaned_df[column] = self.numeric_validator.clean_numeric_column(cleaned_df[column])
                elif cleaned_df[column].dtype == 'object':
                    cleaned_df[column] = self.string_validator.clean_string_column(cleaned_df[column])
            
            return cleaned_df
            
        except Exception as e:
            self.logger.error(f"Error cleaning data: {e}")
            return df
    
    def update_engine(self, new_engine):
        """อัปเดต database engine"""
        self.engine = new_engine
        self.main_validator.engine = new_engine
        self.schema_validator.engine = new_engine
        self.index_manager.engine = new_engine