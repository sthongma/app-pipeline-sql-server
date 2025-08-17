"""Service สำหรับโหลดข้อมูลล่วงหน้า"""
import os
import json
from typing import Dict, Any, Tuple


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
            column_settings = self._load_column_settings()
            
            if progress_callback:
                progress_callback("Loading data type settings...")
            
            # โหลดการตั้งค่าประเภทข้อมูล
            dtype_settings = self._load_dtype_settings()
            
            if progress_callback:
                progress_callback("Loading latest path...")
            
            # โหลด path ล่าสุด
            last_path = self._load_last_path()
            
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
    
    def _load_column_settings(self) -> Dict[str, Any]:
        """โหลดการตั้งค่าคอลัมน์"""
        try:
            settings_file = "config/column_settings.json"
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
    
    def _load_dtype_settings(self) -> Dict[str, Any]:
        """โหลดการตั้งค่าประเภทข้อมูล"""
        try:
            dtype_file = "config/dtype_settings.json"
            if os.path.exists(dtype_file):
                with open(dtype_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
    
    def _load_last_path(self) -> str:
        """โหลด path ล่าสุด"""
        try:
            with open('config/last_path.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('last_path', None)
        except Exception:
            pass
        return None
    
    def get_cached_data(self) -> Dict[str, Any]:
        """คืนค่าข้อมูลที่แคชไว้"""
        return self._cached_data.copy()
    
    def clear_cache(self):
        """ล้างแคช"""
        self._cached_data.clear()