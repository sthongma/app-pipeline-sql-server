"""Settings Operation Handlers"""
import os
import json


class SettingsHandler:
    def __init__(self, settings_file, log_callback):
        """
        Initialize Settings Handler
        
        Args:
            settings_file: Path to settings file
            log_callback: Function to call for logging
        """
        self.settings_file = settings_file
        self.log = log_callback
    
    def load_column_settings(self):
        """โหลดการตั้งค่าคอลัมน์จากไฟล์"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.log(f"ไม่สามารถโหลดการตั้งค่าคอลัมน์ได้: {e}")
        return {}
    
    def save_column_settings(self, column_settings):
        """บันทึกการตั้งค่าคอลัมน์ลงไฟล์"""
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(column_settings, f, ensure_ascii=False, indent=2)
            self.log("บันทึกการตั้งค่าคอลัมน์เรียบร้อย")
        except Exception as e:
            self.log(f"ไม่สามารถบันทึกการตั้งค่าคอลัมน์ได้: {e}")
    
    def load_dtype_settings(self):
        """โหลดการตั้งค่าประเภทข้อมูลจากไฟล์ รวมทั้ง _date_format"""
        try:
            dtype_file = "config/dtype_settings.json"
            if os.path.exists(dtype_file):
                with open(dtype_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.log(f"ไม่สามารถโหลดการตั้งค่าประเภทข้อมูลได้: {e}")
        return {}
    
    def save_dtype_settings(self, dtype_settings):
        """บันทึกการตั้งค่าประเภทข้อมูลลงไฟล์ รวมทั้ง _date_format ของแต่ละประเภทไฟล์"""
        try:
            dtype_file = "config/dtype_settings.json"
            os.makedirs(os.path.dirname(dtype_file), exist_ok=True)
            
            with open(dtype_file, 'w', encoding='utf-8') as f:
                json.dump(dtype_settings, f, ensure_ascii=False, indent=2)
            self.log("บันทึกการตั้งค่าประเภทข้อมูลเรียบร้อย")
        except Exception as e:
            self.log(f"ไม่สามารถบันทึกการตั้งค่าประเภทข้อมูลได้: {e}")
    
    def load_last_path(self):
        """โหลด path ล่าสุดจากไฟล์"""
        try:
            with open('config/last_path.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('last_path', None)
        except Exception:
            return None
    
    def save_last_path(self, path):
        """บันทึก path ล่าสุดลงไฟล์"""
        try:
            os.makedirs('config', exist_ok=True)
            with open('config/last_path.json', 'w', encoding='utf-8') as f:
                json.dump({'last_path': path}, f)
        except Exception as e:
            self.log(f"Save last path error: {e}")
