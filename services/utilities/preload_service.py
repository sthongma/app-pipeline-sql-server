"""Service สำหรับโหลดข้อมูลล่วงหน้า - Modernized with JSON Manager"""
from typing import Dict, Any, Tuple
from config.json_manager import (
    json_manager,
    load_column_settings,
    load_dtype_settings,
    get_last_path
)


class PreloadService:
    """Service สำหรับโหลดประเภทไฟล์และการตั้งค่าต่างๆ ล่วงหน้า"""
    
    def __init__(self):
        self._cached_data = {}
    
    def preload_file_settings(self, progress_callback=None) -> Tuple[bool, str, Dict[str, Any]]:
        """
        โหลดการตั้งค่าไฟล์ทั้งหมดล่วงหน้า
        
        Args:
            progress_callback: Function to call for progress updates (message)
            
        Returns:
            Tuple[bool, str, Dict]: (success, message, data)
        """
        try:
            if progress_callback:
                progress_callback("Loading column settings...")
            
            # โหลดการตั้งค่าคอลัมน์
            column_settings = load_column_settings()
            
            if progress_callback:
                progress_callback("Loading data type settings...")
            
            # โหลดการตั้งค่าประเภทข้อมูล
            dtype_settings = load_dtype_settings()
            
            if progress_callback:
                progress_callback("Loading latest path...")
            
            # โหลด path ล่าสุด
            last_path = get_last_path()
            
            if progress_callback:
                progress_callback("Preparing data for UI creation...")
            
            # รวมข้อมูลทั้งหมด
            data = {
                'column_settings': column_settings,
                'dtype_settings': dtype_settings,
                'last_path': last_path
            }
            
            # เก็บในแคช
            self._cached_data = data
            
            if progress_callback:
                progress_callback("Data loading completed, preparing UI...")
            
            return True, "Data loaded successfully", data
            
        except Exception as e:
            return False, f"An error occurred while loading data: {str(e)}", {}
    
    def get_cached_data(self) -> Dict[str, Any]:
        """คืนค่าข้อมูลที่แคชไว้"""
        return self._cached_data.copy()
    
    def clear_cache(self):
        """ล้างแคช"""
        self._cached_data.clear()
        # Also clear JSON manager cache
        json_manager.clear_cache()