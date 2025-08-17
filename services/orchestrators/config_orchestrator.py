"""
Configuration Service สำหรับ PIPELINE_SQLSERVER

Orchestrator service สำหรับจัดการการตั้งค่าต่างๆ ของแอปพลิเคชัน
ประสานงานระหว่าง SettingsManager และ configuration-related services
"""

import logging
from typing import Dict, Any, Optional, Tuple, List
from config.settings import SettingsManager, DatabaseSettings, AppSettings
from services.utilities.preload_service import PreloadService


class ConfigOrchestrator:
    """
    Configuration Orchestrator Service
    
    ทำหน้าที่เป็น orchestrator สำหรับการจัดการ:
    - Settings management
    - Configuration loading/saving
    - Preload services
    - Configuration validation
    """
    
    def __init__(self, log_callback=None):
        """
        เริ่มต้น Configuration Service
        
        Args:
            log_callback: ฟังก์ชันสำหรับแสดง log
        """
        self.log_callback = log_callback if log_callback else (lambda msg: None)
        self.logger = logging.getLogger(__name__)
        
        # Initialize modular services
        self.settings_manager = SettingsManager()
        self.preload_service = PreloadService()
        
        self.logger.info("ConfigService initialized")
    
    def initialize_application_config(self, progress_callback=None) -> Tuple[bool, str, Dict[str, Any]]:
        """
        เริ่มต้นการตั้งค่าแอปพลิเคชันทั้งหมด
        
        Args:
            progress_callback: ฟังก์ชันสำหรับแสดงความคืบหน้า
            
        Returns:
            Tuple[bool, str, Dict]: (success, message, config_data)
        """
        try:
            self.log_callback("🔧 Initializing application configuration...")
            
            # โหลดการตั้งค่าพื้นฐาน
            if progress_callback:
                progress_callback("Loading basic settings...")
            
            app_settings = self.settings_manager.get_app_settings()
            db_settings = self.settings_manager.get_database_settings()
            
            # โหลดข้อมูลล่วงหน้า
            if progress_callback:
                progress_callback("Preloading application data...")
            
            preload_success, preload_message, preload_data = self.preload_service.preload_file_settings(
                progress_callback=progress_callback
            )
            
            # รวมข้อมูลการตั้งค่าทั้งหมด
            config_data = {
                'app_settings': app_settings,
                'database_settings': db_settings,
                'preload_data': preload_data if preload_success else {},
                'preload_success': preload_success,
                'preload_message': preload_message
            }
            
            if progress_callback:
                progress_callback("Configuration initialization completed")
            
            self.log_callback("✅ Application configuration initialized successfully")
            return True, "Configuration initialized successfully", config_data
            
        except Exception as e:
            error_msg = f"Failed to initialize configuration: {str(e)}"
            self.logger.error(error_msg)
            self.log_callback(f"❌ {error_msg}")
            return False, error_msg, {}
    
    def update_database_config(self, **config_params) -> Tuple[bool, str]:
        """
        อัปเดตการตั้งค่าฐานข้อมูล
        
        Args:
            **config_params: พารามิเตอร์การตั้งค่าฐานข้อมูล
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            self.log_callback("🔧 Updating database configuration...")
            
            # อัปเดตผ่าน settings manager
            success, message = self.settings_manager.update_database_settings(**config_params)
            
            if success:
                self.log_callback("✅ Database configuration updated successfully")
            else:
                self.log_callback(f"❌ Failed to update database configuration: {message}")
            
            return success, message
            
        except Exception as e:
            error_msg = f"Error updating database configuration: {str(e)}"
            self.logger.error(error_msg)
            self.log_callback(f"❌ {error_msg}")
            return False, error_msg
    
    def update_app_settings(self, **settings_params) -> Tuple[bool, str]:
        """
        อัปเดตการตั้งค่าแอปพลิเคชัน
        
        Args:
            **settings_params: พารามิเตอร์การตั้งค่าแอปพลิเคชัน
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            self.log_callback("🔧 Updating application settings...")
            
            # อัปเดตผ่าน settings manager
            success, message = self.settings_manager.update_app_settings(**settings_params)
            
            if success:
                self.log_callback("✅ Application settings updated successfully")
            else:
                self.log_callback(f"❌ Failed to update application settings: {message}")
            
            return success, message
            
        except Exception as e:
            error_msg = f"Error updating application settings: {str(e)}"
            self.logger.error(error_msg)
            self.log_callback(f"❌ {error_msg}")
            return False, error_msg
    
    def get_complete_config(self) -> Dict[str, Any]:
        """
        ดึงการตั้งค่าทั้งหมดของแอปพลิเคชัน
        
        Returns:
            Dict: การตั้งค่าทั้งหมด
        """
        try:
            return {
                'app_settings': self.settings_manager.get_app_settings(),
                'database_settings': self.settings_manager.get_database_settings(),
                'cached_preload_data': self.preload_service.get_cached_data()
            }
        except Exception as e:
            self.logger.error(f"Error getting complete config: {e}")
            return {}
    
    def validate_config(self) -> Tuple[bool, str, List[str]]:
        """
        ตรวจสอบความถูกต้องของการตั้งค่า
        
        Returns:
            Tuple[bool, str, List[str]]: (is_valid, message, issues)
        """
        try:
            self.log_callback("🔍 Validating configuration...")
            
            issues = []
            
            # ตรวจสอบการตั้งค่าฐานข้อมูล
            db_settings = self.settings_manager.get_database_settings()
            if not db_settings.server:
                issues.append("Database server not configured")
            if not db_settings.database:
                issues.append("Database name not configured")
            
            # ตรวจสอบการตั้งค่าแอปพลิเคชัน
            app_settings = self.settings_manager.get_app_settings()
            if not app_settings.last_search_path:
                issues.append("Search path not configured")
            
            # ตรวจสอบ preload data
            preload_data = self.preload_service.get_cached_data()
            if not preload_data:
                issues.append("Preload data not available")
            
            is_valid = len(issues) == 0
            
            if is_valid:
                self.log_callback("✅ Configuration validation passed")
                return True, "Configuration is valid", []
            else:
                message = f"Configuration has {len(issues)} issues"
                self.log_callback(f"⚠️ {message}: {', '.join(issues)}")
                return False, message, issues
            
        except Exception as e:
            error_msg = f"Error validating configuration: {str(e)}"
            self.logger.error(error_msg)
            self.log_callback(f"❌ {error_msg}")
            return False, error_msg, [error_msg]
    
    def reset_config(self) -> Tuple[bool, str]:
        """
        รีเซ็ตการตั้งค่าเป็นค่าเริ่มต้น
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            self.log_callback("🔄 Resetting configuration to defaults...")
            
            # รีเซ็ต settings manager
            success, message = self.settings_manager.reset_to_defaults()
            
            if success:
                # ล้าง preload cache
                self.preload_service.clear_cache()
                self.log_callback("✅ Configuration reset to defaults")
            else:
                self.log_callback(f"❌ Failed to reset configuration: {message}")
            
            return success, message
            
        except Exception as e:
            error_msg = f"Error resetting configuration: {str(e)}"
            self.logger.error(error_msg)
            self.log_callback(f"❌ {error_msg}")
            return False, error_msg
    
    def export_config(self, file_path: str) -> Tuple[bool, str]:
        """
        ส่งออกการตั้งค่าเป็นไฟล์
        
        Args:
            file_path: เส้นทางไฟล์ที่จะส่งออก
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            self.log_callback(f"📤 Exporting configuration to {file_path}...")
            
            # ดึงการตั้งค่าทั้งหมด
            config_data = self.get_complete_config()
            
            # ส่งออกผ่าน settings manager
            success, message = self.settings_manager.export_settings(file_path, config_data)
            
            if success:
                self.log_callback("✅ Configuration exported successfully")
            else:
                self.log_callback(f"❌ Failed to export configuration: {message}")
            
            return success, message
            
        except Exception as e:
            error_msg = f"Error exporting configuration: {str(e)}"
            self.logger.error(error_msg)
            self.log_callback(f"❌ {error_msg}")
            return False, error_msg
    
    def import_config(self, file_path: str) -> Tuple[bool, str]:
        """
        นำเข้าการตั้งค่าจากไฟล์
        
        Args:
            file_path: เส้นทางไฟล์ที่จะนำเข้า
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            self.log_callback(f"📥 Importing configuration from {file_path}...")
            
            # นำเข้าผ่าน settings manager
            success, message = self.settings_manager.import_settings(file_path)
            
            if success:
                # ล้าง preload cache เพื่อโหลดใหม่
                self.preload_service.clear_cache()
                self.log_callback("✅ Configuration imported successfully")
            else:
                self.log_callback(f"❌ Failed to import configuration: {message}")
            
            return success, message
            
        except Exception as e:
            error_msg = f"Error importing configuration: {str(e)}"
            self.logger.error(error_msg)
            self.log_callback(f"❌ {error_msg}")
            return False, error_msg
    
    # Convenience methods for backward compatibility
    def get_database_settings(self) -> DatabaseSettings:
        """ดึงการตั้งค่าฐานข้อมูล"""
        return self.settings_manager.get_database_settings()
    
    def get_app_settings(self) -> AppSettings:
        """ดึงการตั้งค่าแอปพลิเคชัน"""
        return self.settings_manager.get_app_settings()
    
    def save_last_path(self, path: str) -> Tuple[bool, str]:
        """บันทึก path ล่าสุด"""
        return self.settings_manager.save_last_path(path)