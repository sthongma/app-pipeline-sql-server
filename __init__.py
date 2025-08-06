"""
PIPELINE_SQLSERVER: ระบบ pipeline สำหรับการจัดการไฟล์และอัปโหลดข้อมูลไปยัง SQL Server

โปรเจกต์นี้ช่วยในการ:
- ตรวจสอบและตรวจสอบไฟล์ Excel/CSV
- อัปโหลดข้อมูลไปยัง SQL Server ด้วยการตั้งค่าคอลัมน์ที่ยืดหยุ่น
- ย้ายไฟล์ที่ประมวลผลแล้วไปยังโฟลเดอร์ที่จัดระเบียบ
- รองรับทั้ง GUI และ CLI interface
"""

__version__ = "1.0.0"
__author__ = "PIPELINE_SQLSERVER Development Team"

# การนำเข้าหลักสำหรับ package
from .config.database import DatabaseConfig
from .services.database_service import DatabaseService
from .services.file_service import FileService

__all__ = [
    'DatabaseConfig',
    'DatabaseService', 
    'FileService',
]