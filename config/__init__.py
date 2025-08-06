"""
Configuration module สำหรับ PIPELINE_SQLSERVER

ประกอบด้วย:
- DatabaseConfig: การจัดการการตั้งค่าฐานข้อมูล
- การโหลดและบันทึกการตั้งค่าต่างๆ
"""

from .database import DatabaseConfig

__all__ = ['DatabaseConfig']