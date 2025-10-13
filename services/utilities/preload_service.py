"""Service for preloading data - Modernized with JSON Manager"""
from typing import Dict, Any, Tuple
from config.json_manager import (
    json_manager,
    load_column_settings,
    load_dtype_settings,
    get_input_folder
)


class PreloadService:
    """Service for preloading file types and various settings"""
    
    def __init__(self):
        self._cached_data = {}
    
    def preload_file_settings(self, progress_callback=None) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Preload all file settings in advance
        
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
                progress_callback("Loading input folder path...")

            # โหลด input folder path
            input_folder_path = get_input_folder()

            if progress_callback:
                progress_callback("Preparing data for UI creation...")

            # รวมข้อมูลทั้งหมด
            data = {
                'column_settings': column_settings,
                'dtype_settings': dtype_settings,
                'input_folder_path': input_folder_path
            }
            
            # เก็บในแคช
            self._cached_data = data
            
            if progress_callback:
                progress_callback("Data loading completed, preparing UI...")
            
            return True, "Data loaded successfully", data
            
        except Exception as e:
            return False, f"An error occurred while loading data: {str(e)}", {}
    
    def get_cached_data(self) -> Dict[str, Any]:
        """Return cached data"""
        return self._cached_data.copy()
    
    def clear_cache(self):
        """Clear cache"""
        self._cached_data.clear()
        # Also clear JSON manager cache
        json_manager.clear_cache()