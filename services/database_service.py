"""
Database Service สำหรับ PIPELINE_SQLSERVER

Orchestrator service that coordinates database operations using modular services
"""

import logging
from typing import Any, Dict, Tuple

from config.database import DatabaseConfig
from .permission_checker_service import PermissionCheckerService
from .database import (
    ConnectionService,
    SchemaService,
    DataValidationService,
    DataUploadService
)

class DatabaseService:
    """
    บริการจัดการฐานข้อมูล SQL Server
    
    Orchestrator service that coordinates all database operations using modular services
    """
    
    def __init__(self) -> None:
        """
        เริ่มต้น DatabaseService
        
        สร้าง database config และ service instances
        """
        self.db_config = DatabaseConfig()
        self.logger = logging.getLogger(__name__)
        self.permission_checker = None  # จะสร้างตอนต้องใช้งาน
        
        # Initialize service components
        self.connection_service = ConnectionService(self.db_config)
        self.schema_service = SchemaService(self.connection_service.get_engine())
        self.validation_service = DataValidationService(self.connection_service.get_engine())
        self.upload_service = DataUploadService(
            self.connection_service.get_engine(),
            self.schema_service,
            self.validation_service
        )
        
        # Keep engine reference for backward compatibility
        self.engine = self.connection_service.get_engine()

    def _get_permission_checker(self, log_callback=None):
        """สร้างหรือคืนค่า PermissionCheckerService"""
        if self.permission_checker is None:
            # ใช้ silent callback เป็นค่าเริ่มต้นสำหรับ GUI
            default_callback = log_callback or (lambda msg: None)
            self.permission_checker = PermissionCheckerService(
                engine=self.connection_service.get_engine(), 
                log_callback=default_callback
            )
        return self.permission_checker

    def check_permissions(self, schema_name: str = 'bronze', log_callback=None) -> Dict:
        """
        ตรวจสอบสิทธิ์ SQL Server ที่จำเป็นสำหรับการทำงาน
        
        Args:
            schema_name: ชื่อ schema ที่ต้องการตรวจสอบ
            log_callback: ฟังก์ชันสำหรับแสดง log (None = ไม่แสดง log)
            
        Returns:
            Dict: ผลการตรวจสอบสิทธิ์
        """
        # สำหรับ GUI ไม่ต้องแสดง log ใน CLI
        silent_callback = lambda msg: None  # ฟังก์ชันเงียบ
        checker = self._get_permission_checker(silent_callback if log_callback is None else log_callback)
        return checker.check_all_permissions(schema_name)

    def generate_permission_report(self, schema_name: str = 'bronze') -> str:
        """
        สร้างรายงานสิทธิ์แบบละเอียด
        
        Args:
            schema_name: ชื่อ schema ที่ต้องการตรวจสอบ
            
        Returns:
            str: รายงานสิทธิ์
        """
        checker = self._get_permission_checker()
        return checker.generate_permission_report(schema_name)

    def check_connection(self, show_warning: bool = True) -> Tuple[bool, str]:
        """
        ตรวจสอบการเชื่อมต่อกับ SQL Server
        
        Returns:
            Tuple[bool, str]: (สถานะการเชื่อมต่อ, ข้อความผลลัพธ์)
        """
        return self.connection_service.check_connection(show_warning)

    def test_connection(self, config: Dict[str, Any]) -> bool:
        """
        ทดสอบการเชื่อมต่อกับ SQL Server ด้วย config ที่รับมา
        
        Args:
            config (Dict[str, Any]): การตั้งค่าการเชื่อมต่อ
            
        Returns:
            bool: True หากเชื่อมต่อสำเร็จ, False หากล้มเหลว
        """
        return self.connection_service.test_connection(config)

    def update_config(self, server=None, database=None, auth_type=None, username=None, password=None):
        """อัปเดตการตั้งค่าการเชื่อมต่อ"""
        self.connection_service.update_config(
            server=server,
            database=database,
            auth_type=auth_type,
            username=username,
            password=password
        )
        # Update engine reference for backward compatibility
        self.engine = self.connection_service.get_engine()
        
        # Update engine references in other services
        new_engine = self.connection_service.get_engine()
        self.schema_service.engine = new_engine
        self.validation_service.engine = new_engine
        self.upload_service.engine = new_engine

    def ensure_schemas_exist(self, schema_names):
        """ตรวจสอบและสร้าง schema ตามที่ระบุ ถ้ายังไม่มี"""
        return self.schema_service.ensure_schemas_exist(schema_names)

    def upload_data(self, df, logic_type, required_cols, schema_name='bronze', log_func=None, force_recreate=False, clear_existing=True):
        """
        อัปโหลดข้อมูลไปยังฐานข้อมูล: สร้างตารางใหม่ตาม config, insert เฉพาะคอลัมน์ที่ตั้งค่าไว้, ถ้า schema DB ไม่ตรงให้ drop และสร้างตารางใหม่
        
        Args:
            df: DataFrame ที่จะอัปโหลด
            logic_type: ประเภทไฟล์
            required_cols: คอลัมน์และชนิดข้อมูลที่ต้องการ
            schema_name: ชื่อ schema ในฐานข้อมูล
            log_func: ฟังก์ชันสำหรับ log
            force_recreate: บังคับสร้างตารางใหม่ (ใช้เมื่อมีการปรับปรุงชนิดข้อมูลอัตโนมัติ)
            clear_existing: ล้างข้อมูลเดิมหรือไม่ (default True เพื่อความเข้ากันได้แบบเดิม)
        """
        return self.upload_service.upload_data(
            df, logic_type, required_cols, schema_name, log_func, force_recreate, clear_existing
        )

    def validate_data_in_staging(self, staging_table, logic_type, required_cols, schema_name='bronze', log_func=None, progress_callback=None):
        """
        ตรวจสอบความถูกต้องของข้อมูลใน staging table ด้วย SQL
        
        Args:
            staging_table: ชื่อ staging table
            logic_type: ประเภทไฟล์
            required_cols: คอลัมน์และชนิดข้อมูลที่ต้องการ
            schema_name: ชื่อ schema
            log_func: ฟังก์ชันสำหรับ log
            progress_callback: ฟังก์ชันสำหรับรับ progress updates
            
        Returns:
            Dict: ผลการตรวจสอบ {'is_valid': bool, 'issues': [...], 'summary': str}
        """
        return self.validation_service.validate_data_in_staging(
            staging_table, logic_type, required_cols, schema_name, log_func, progress_callback
        )