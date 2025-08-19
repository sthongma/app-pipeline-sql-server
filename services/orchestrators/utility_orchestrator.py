"""
Utility Orchestrator for PIPELINE_SQLSERVER

Orchestrator service for managing various utility services
Coordinates between permission checker, performance optimizer and utility functions
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd

from services.utilities.permission_checker_service import PermissionCheckerService
from performance_optimizations import PerformanceOptimizer
from utils.helpers import safe_json_load, safe_json_save
from utils.validators import validate_file_path, validate_database_connection
from utils.logger import setup_logging


class UtilityOrchestrator:
    """
    Utility Orchestrator Service
    
    Acts as orchestrator for managing:
    - Permission checking
    - Performance optimization
    - File utilities
    - Logging utilities
    - General helper functions
    """
    
    def __init__(self, engine=None, log_callback=None):
        """
        Initialize Utility Orchestrator
        
        Args:
            engine: SQLAlchemy engine
            log_callback: Function for logging
        """
        self.engine = engine
        self.log_callback = log_callback if log_callback else (lambda msg: None)
        self.logger = logging.getLogger(__name__)
        
        # Initialize utility services
        self._initialize_services()
        
        self.logger.info("UtilityOrchestrator initialized")
    
    def _initialize_services(self):
        """Initialize all utility services"""
        try:
            # Permission checker
            self.permission_checker = PermissionCheckerService(
                engine=self.engine,
                log_callback=self.log_callback
            )
            
            # Performance optimizer
            self.performance_optimizer = PerformanceOptimizer()
            
            self.logger.info("All utility services initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing utility services: {e}")
            raise
    
    def comprehensive_system_check(self, schema_name: str = 'bronze') -> Dict[str, Any]:
        """
        ตรวจสอบระบบแบบครอบคลุม
        
        Args:
            schema_name: ชื่อ schema ที่ต้องการตรวจสอบ
            
        Returns:
            Dict: ผลการตรวจสอบระบบ
        """
        try:
            self.log_callback("🔍 Starting comprehensive system check...")
            
            system_check_results = {
                'overall_success': True,
                'total_checks': 0,
                'passed_checks': 0,
                'failed_checks': 0,
                'permission_check': {},
                'performance_check': {},
                'database_check': {},
                'file_system_check': {},
                'recommendations': []
            }
            
            # 1. Permission Check
            self.log_callback("  🔐 Checking database permissions...")
            permission_results = self.check_database_permissions(schema_name)
            system_check_results['permission_check'] = permission_results
            system_check_results['total_checks'] += 1
            
            if permission_results['success']:
                system_check_results['passed_checks'] += 1
            else:
                system_check_results['failed_checks'] += 1
                system_check_results['overall_success'] = False
            
            # 2. Performance Check
            self.log_callback("  ⚡ Checking system performance...")
            performance_results = self.check_system_performance()
            system_check_results['performance_check'] = performance_results
            system_check_results['total_checks'] += 1
            
            if performance_results['success']:
                system_check_results['passed_checks'] += 1
            else:
                system_check_results['failed_checks'] += 1
            
            # 3. Database Connection Check
            if self.engine:
                self.log_callback("  🗄️ Checking database connection...")
                db_results = self.check_database_connection()
                system_check_results['database_check'] = db_results
                system_check_results['total_checks'] += 1
                
                if db_results['success']:
                    system_check_results['passed_checks'] += 1
                else:
                    system_check_results['failed_checks'] += 1
                    system_check_results['overall_success'] = False
            
            # 4. File System Check
            self.log_callback("  📁 Checking file system...")
            file_results = self.check_file_system()
            system_check_results['file_system_check'] = file_results
            system_check_results['total_checks'] += 1
            
            if file_results['success']:
                system_check_results['passed_checks'] += 1
            else:
                system_check_results['failed_checks'] += 1
            
            # Generate recommendations
            system_check_results['recommendations'] = self._generate_system_recommendations(system_check_results)
            
            if system_check_results['overall_success']:
                self.log_callback("✅ Comprehensive system check completed successfully")
            else:
                self.log_callback(f"⚠️ System check completed with {system_check_results['failed_checks']} failed checks")
            
            return system_check_results
            
        except Exception as e:
            error_msg = f"Error in comprehensive system check: {str(e)}"
            self.logger.error(error_msg)
            self.log_callback(f"❌ {error_msg}")
            return {
                'overall_success': False,
                'error': error_msg
            }
    
    def check_database_permissions(self, schema_name: str = 'bronze') -> Dict[str, Any]:
        """
        ตรวจสอบสิทธิ์ฐานข้อมูล
        
        Args:
            schema_name: ชื่อ schema ที่ต้องการตรวจสอบ
            
        Returns:
            Dict: ผลการตรวจสอบสิทธิ์
        """
        try:
            if not self.engine:
                return {
                    'success': False,
                    'error': 'Database connection not available',
                    'permissions': [],
                    'missing_critical': [],
                    'missing_optional': []
                }
            
            # ใช้ permission checker service
            return self.permission_checker.check_all_permissions(schema_name)
            
        except Exception as e:
            error_msg = f"Error checking database permissions: {str(e)}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def check_system_performance(self) -> Dict[str, Any]:
        """ตรวจสอบประสิทธิภาพระบบ"""
        try:
            performance_results = {
                'success': True,
                'memory_usage': {},
                'optimization_status': {},
                'recommendations': []
            }
            
            # ตรวจสอบ memory usage
            try:
                import psutil
                memory = psutil.virtual_memory()
                performance_results['memory_usage'] = {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'free': memory.free
                }
                
                # เตือนถ้า memory ใช้งานมากเกินไป
                if memory.percent > 80:
                    performance_results['recommendations'].append("High memory usage detected - consider closing other applications")
                    
            except ImportError:
                performance_results['memory_usage'] = {'error': 'psutil not available'}
            
            # ตรวจสอบ optimization settings
            optimization_settings = self.performance_optimizer.get_current_settings()
            performance_results['optimization_status'] = optimization_settings
            
            # ตรวจสอบ chunk size settings
            chunk_info = self.performance_optimizer.get_optimal_chunk_size()
            performance_results['chunk_settings'] = chunk_info
            
            return performance_results
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_database_connection(self) -> Dict[str, Any]:
        """ตรวจสอบการเชื่อมต่อฐานข้อมูล"""
        try:
            if not self.engine:
                return {
                    'success': False,
                    'error': 'Database engine not available'
                }
            
            # ทดสอบการเชื่อมต่อ
            connection_valid = validate_database_connection(self.engine)
            
            if connection_valid:
                # ตรวจสอบข้อมูลเพิ่มเติม
                with self.engine.connect() as conn:
                    result = conn.execute("SELECT @@VERSION").scalar()
                    server_version = result if result else "Unknown"
                
                return {
                    'success': True,
                    'server_version': server_version,
                    'connection_status': 'Connected'
                }
            else:
                return {
                    'success': False,
                    'error': 'Database connection validation failed'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_file_system(self) -> Dict[str, Any]:
        """ตรวจสอบระบบไฟล์"""
        try:
            file_results = {
                'success': True,
                'config_files': {},
                'directories': {},
                'disk_space': {}
            }
            
            # ตรวจสอบไฟล์ config (sql_config.json no longer needed - using env vars)
            config_files = [
                'config/column_settings.json',
                'config/dtype_settings.json'
            ]
            
            for config_file in config_files:
                file_exists = validate_file_path(config_file)
                file_results['config_files'][config_file] = {
                    'exists': file_exists,
                    'readable': file_exists  # simplified check
                }
            
            # ตรวจสอบ directories
            required_dirs = ['config', 'logs', 'services']
            for directory in required_dirs:
                import os
                dir_exists = os.path.exists(directory) and os.path.isdir(directory)
                file_results['directories'][directory] = {
                    'exists': dir_exists,
                    'writable': os.access(directory, os.W_OK) if dir_exists else False
                }
            
            # ตรวจสอบ disk space
            try:
                import shutil
                total, used, free = shutil.disk_usage(".")
                file_results['disk_space'] = {
                    'total': total,
                    'used': used,
                    'free': free,
                    'free_percent': (free / total) * 100
                }
                
                # เตือนถ้า disk space น้อย
                if (free / total) * 100 < 10:
                    file_results['success'] = False
                    file_results['error'] = 'Low disk space warning'
                    
            except Exception:
                file_results['disk_space'] = {'error': 'Cannot check disk space'}
            
            return file_results
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def optimize_dataframe_memory(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        ปรับปรุงการใช้งาน memory ของ DataFrame
        
        Args:
            df: DataFrame ที่ต้องการปรับปรุง
            
        Returns:
            Tuple[DataFrame, Dict]: (optimized_df, optimization_info)
        """
        try:
            self.log_callback("⚡ Optimizing DataFrame memory usage...")
            
            original_memory = df.memory_usage(deep=True).sum()
            
            # ใช้ performance optimizer
            optimized_df = self.performance_optimizer.optimize_dataframe_memory(df)
            
            optimized_memory = optimized_df.memory_usage(deep=True).sum()
            memory_saved = original_memory - optimized_memory
            
            optimization_info = {
                'original_memory': original_memory,
                'optimized_memory': optimized_memory,
                'memory_saved': memory_saved,
                'reduction_percent': (memory_saved / original_memory) * 100 if original_memory > 0 else 0
            }
            
            self.log_callback(f"✅ Memory optimization completed - {optimization_info['reduction_percent']:.1f}% reduction")
            
            return optimized_df, optimization_info
            
        except Exception as e:
            error_msg = f"Error optimizing DataFrame memory: {str(e)}"
            self.logger.error(error_msg)
            return df, {'error': error_msg}
    
    def setup_application_logging(self, log_level: str = "INFO") -> Tuple[bool, str]:
        """
        ตั้งค่า logging สำหรับแอปพลิเคชัน
        
        Args:
            log_level: ระดับของ log
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # ใช้ utility logger
            logger = setup_logging(log_level)
            
            if logger:
                self.log_callback(f"✅ Application logging setup completed - Level: {log_level}")
                return True, f"Logging setup successful with level {log_level}"
            else:
                return False, "Failed to setup logging"
                
        except Exception as e:
            error_msg = f"Error setting up logging: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def generate_permission_report(self, schema_name: str = 'bronze') -> str:
        """สร้างรายงานสิทธิ์แบบละเอียด"""
        try:
            return self.permission_checker.generate_permission_report(schema_name)
        except Exception as e:
            return f"Error generating permission report: {str(e)}"
    
    def _generate_system_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """สร้างคำแนะนำสำหรับระบบ"""
        recommendations = []
        
        # คำแนะนำด้านสิทธิ์
        permission_check = results.get('permission_check', {})
        if not permission_check.get('success', True):
            recommendations.append("🔐 ตรวจสอบและแก้ไขสิทธิ์ฐานข้อมูล")
        
        # คำแนะนำด้านประสิทธิภาพ
        performance_check = results.get('performance_check', {})
        if performance_check.get('memory_usage', {}).get('percent', 0) > 80:
            recommendations.append("💾 ลด memory usage โดยปิดโปรแกรมอื่นๆ")
        
        # คำแนะนำด้านฐานข้อมูล
        database_check = results.get('database_check', {})
        if not database_check.get('success', True):
            recommendations.append("🗄️ ตรวจสอบการเชื่อมต่อฐานข้อมูล")
        
        # คำแนะนำด้านไฟล์
        file_check = results.get('file_system_check', {})
        if not file_check.get('success', True):
            recommendations.append("📁 ตรวจสอบพื้นที่ดิสก์และไฟล์ config")
        
        if not recommendations:
            recommendations.append("✅ ระบบพร้อมใช้งาน")
        
        return recommendations
    
    def update_engine(self, new_engine):
        """อัปเดต database engine"""
        self.engine = new_engine
        self.permission_checker.engine = new_engine
    
    # Convenience methods
    def get_file_helper(self):
        """ดึง file helper functions"""
        return {
            'safe_json_load': safe_json_load,
            'safe_json_save': safe_json_save,
            'validate_file_path': validate_file_path
        }
    
    def get_performance_settings(self) -> Dict[str, Any]:
        """ดึงการตั้งค่าประสิทธิภาพ"""
        return self.performance_optimizer.get_current_settings()