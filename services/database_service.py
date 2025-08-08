"""
Database Service สำหรับ PIPELINE_SQLSERVER

จัดการการเชื่อมต่อและอัปโหลดข้อมูลไปยัง SQL Server
"""

import logging
import os
from tkinter import messagebox
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy import create_engine, text

from config.database import DatabaseConfig
from constants import DatabaseConstants, ErrorMessages, SuccessMessages
from .permission_checker_service import PermissionCheckerService

class DatabaseService:
    """
    บริการจัดการฐานข้อมูล SQL Server
    
    ให้บริการการเชื่อมต่อ อัปโหลดข้อมูล และจัดการ schema
    """
    
    def __init__(self) -> None:
        """
        เริ่มต้น DatabaseService
        
        สร้าง database config, engine และ logger
        """
        self.db_config = DatabaseConfig()
        self.engine = self.db_config.get_engine()
        self.logger = logging.getLogger(__name__)
        self.permission_checker = None  # จะสร้างตอนต้องใช้งาน

    def _get_permission_checker(self, log_callback=None):
        """สร้างหรือคืนค่า PermissionCheckerService"""
        if self.permission_checker is None:
            self.permission_checker = PermissionCheckerService(
                engine=self.engine, 
                log_callback=log_callback or print
            )
        return self.permission_checker

    def check_permissions(self, schema_name: str = 'bronze', log_callback=None) -> Dict:
        """
        ตรวจสอบสิทธิ์ SQL Server ที่จำเป็นสำหรับการทำงาน
        
        Args:
            schema_name: ชื่อ schema ที่ต้องการตรวจสอบ
            log_callback: ฟังก์ชันสำหรับแสดง log
            
        Returns:
            Dict: ผลการตรวจสอบสิทธิ์
        """
        checker = self._get_permission_checker(log_callback)
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

    def check_connection(self) -> Tuple[bool, str]:
        """
        ตรวจสอบการเชื่อมต่อกับ SQL Server
        
        Returns:
            Tuple[bool, str]: (สถานะการเชื่อมต่อ, ข้อความผลลัพธ์)
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True, SuccessMessages.DB_CONNECTION_SUCCESS
        except Exception as e:
            error_msg = f"{ErrorMessages.DB_CONNECTION_FAILED}: {e}"
            self.logger.error(error_msg)
            messagebox.showwarning("การเชื่อมต่อฐานข้อมูล", error_msg)
            return False, error_msg

    def test_connection(self, config: Dict[str, Any]) -> bool:
        """
        ทดสอบการเชื่อมต่อกับ SQL Server ด้วย config ที่รับมา
        
        Args:
            config (Dict[str, Any]): การตั้งค่าการเชื่อมต่อ
            
        Returns:
            bool: True หากเชื่อมต่อสำเร็จ, False หากล้มเหลว
        """
        try:
            driver = DatabaseConstants.DEFAULT_DRIVER
            if config["auth_type"] == DatabaseConstants.AUTH_WINDOWS:
                conn_str = (
                    f"mssql+pyodbc://@{config['server']}/{config['database']}?"
                    f"driver={driver}&Trusted_Connection=yes"
                )
            else:
                conn_str = (
                    f"mssql+pyodbc://{config['username']}:{config['password']}@{config['server']}/{config['database']}?"
                    f"driver={driver}"
                )
            engine = create_engine(conn_str)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            return False

    def update_config(self, server=None, database=None, auth_type=None, username=None, password=None):
        """อัปเดตการตั้งค่าการเชื่อมต่อ"""
        # อัปเดตการตั้งค่าใน DatabaseConfig
        self.db_config.update_config(
            server=server,
            database=database,
            auth_type=auth_type,
            username=username,
            password=password
        )
        # อัปเดต engine
        self.engine = self.db_config.get_engine()

    def ensure_schemas_exist(self, schema_names):
        """ตรวจสอบและสร้าง schema ตามที่ระบุ ถ้ายังไม่มี"""
        try:
            with self.engine.begin() as conn:
                for schema_name in schema_names:
                    conn.execute(text(f"""
                        IF NOT EXISTS (
                            SELECT 1 FROM sys.schemas WHERE name = '{schema_name}'
                        )
                        BEGIN
                            EXEC('CREATE SCHEMA {schema_name}')
                        END
                    """))
            return True, f"ตรวจสอบ/สร้าง schema ทั้งหมดเรียบร้อย: {', '.join(schema_names)}"
        except Exception as e:
            error_msg = f"สร้าง schema ไม่สำเร็จ: {e}"
            self.logger.error(error_msg)
            messagebox.showwarning("การสร้าง Schema", error_msg)
            return False, error_msg

    def _fix_text_columns_to_nvarchar_max(self, table_name, required_cols, schema_name='bronze', log_func=None):
        """แก้ไขคอลัมน์ที่เป็น Text() ให้เป็น NVARCHAR(MAX) ใน SQL Server"""
        from sqlalchemy.types import Text
        
        try:
            with self.engine.begin() as conn:
                for col_name, dtype in required_cols.items():
                    if isinstance(dtype, Text):
                        alter_sql = f"ALTER TABLE {schema_name}.{table_name} ALTER COLUMN [{col_name}] NVARCHAR(MAX)"
                        if log_func:
                            log_func(f"🔧 แก้ไขคอลัมน์ '{col_name}' เป็น NVARCHAR(MAX)")
                        conn.execute(text(alter_sql))
        except Exception as e:
            if log_func:
                log_func(f"⚠️ ไม่สามารถแก้ไขคอลัมน์ Text() ได้: {e}")

    def upload_data(self, df, logic_type, required_cols, schema_name='bronze', log_func=None, force_recreate=False):
        """
        อัปโหลดข้อมูลไปยังฐานข้อมูล: สร้างตารางใหม่ตาม config, insert เฉพาะคอลัมน์ที่ตั้งค่าไว้, ถ้า schema DB ไม่ตรงให้ drop และสร้างตารางใหม่
        
        Args:
            df: DataFrame ที่จะอัปโหลด
            logic_type: ประเภทไฟล์
            required_cols: คอลัมน์และชนิดข้อมูลที่ต้องการ
            schema_name: ชื่อ schema ในฐานข้อมูล
            log_func: ฟังก์ชันสำหรับ log
            force_recreate: บังคับสร้างตารางใหม่ (ใช้เมื่อมีการปรับปรุงชนิดข้อมูลอัตโนมัติ)
        """
        
        # สิทธิ์ผ่าน ดำเนินการอัปโหลดปกติ
        if log_func:
            log_func("✅ สิทธิ์การเข้าถึงฐานข้อมูลถูกต้อง")
        
        try:
            import json
            from datetime import datetime
            from sqlalchemy.types import DateTime
            
            # ตรวจสอบข้อมูลเบื้องต้น
            if df is None or df.empty:
                return False, "ข้อมูลว่างเปล่า"
            
            if not required_cols:
                return False, "ไม่พบการตั้งค่าประเภทข้อมูล"
            
            # เพิ่มคอลัมน์ timestamp
            current_time = datetime.now()
            df['updated_at'] = current_time
            
            # เพิ่ม dtype สำหรับคอลัมน์ timestamp
            required_cols['updated_at'] = DateTime()
            
            table_name = None
            try:
                with open('config/column_settings.json', 'r', encoding='utf-8') as f:
                    col_config = json.load(f)
                table_name = col_config.get("__table_names__", {}).get(logic_type)
            except Exception:
                table_name = None
            if not table_name:
                table_name = logic_type

            # ตรวจสอบและสร้าง schema หากยังไม่มี
            schema_result = self.ensure_schemas_exist([schema_name])
            if not schema_result[0]:
                return False, f"ไม่สามารถสร้าง schema ได้: {schema_result[1]}"

            # ตรวจสอบ schema DB ว่าตรงกับ required_cols หรือไม่
            from sqlalchemy import inspect
            from sqlalchemy.types import Text
            insp = inspect(self.engine)
            needs_recreate = force_recreate  # บังคับสร้างใหม่ถ้า auto-fix ทำงาน
            
            if insp.has_table(table_name, schema=schema_name) and not force_recreate:
                db_cols = [col['name'] for col in insp.get_columns(table_name, schema=schema_name)]
                db_col_types = {col['name']: str(col['type']).upper() for col in insp.get_columns(table_name, schema=schema_name)}
                config_cols = list(required_cols.keys())
                
                # ตรวจสอบคอลัมน์
                if set(db_cols) != set(config_cols):
                    msg = f"❌ คอลัมน์ของตาราง {schema_name}.{table_name} ไม่ตรงกับ config"
                    needs_recreate = True
                else:
                    # ตรวจสอบ data types โดยเฉพาะ Text() (NVARCHAR(MAX))
                    for col_name, expected_dtype in required_cols.items():
                        db_type = db_col_types.get(col_name, '')
                        
                        if isinstance(expected_dtype, Text):
                            # สำหรับ Text() ต้องเป็น NVARCHAR(MAX) หรือ TEXT
                            if 'NVARCHAR(MAX)' not in db_type and 'TEXT' not in db_type:
                                msg = f"❌ คอลัมน์ '{col_name}' ควรเป็น NVARCHAR(MAX) แต่เป็น {db_type}"
                                if log_func:
                                    log_func(msg)
                                needs_recreate = True
                                break
            
            if needs_recreate or not insp.has_table(table_name, schema=schema_name):
                if force_recreate and log_func:
                    log_func(f"🔄 มีการปรับปรุงชนิดข้อมูลอัตโนมัติ - สร้างตาราง {schema_name}.{table_name} ใหม่")
                elif needs_recreate and log_func:
                    log_func(f"❌ Schema ไม่ตรงกัน - สร้างตาราง {schema_name}.{table_name} ใหม่")
                elif log_func:
                    log_func(f"📋 สร้างตารางใหม่ {schema_name}.{table_name}")
                    
                # Drop และสร้างตารางใหม่
                df.head(0)[list(required_cols.keys())].to_sql(
                    name=table_name,
                    con=self.engine,
                    schema=schema_name,
                    if_exists='replace',
                    index=False,
                    dtype=required_cols
                )
                # แก้ไขคอลัมน์ที่เป็น Text() ให้เป็น NVARCHAR(MAX)
                self._fix_text_columns_to_nvarchar_max(table_name, required_cols, schema_name, log_func)
            else:
                # ล้างข้อมูลเดิม
                if log_func:
                    log_func(f"🗑️ ล้างข้อมูลเดิมในตาราง {schema_name}.{table_name}")
                with self.engine.begin() as conn:
                    conn.execute(text(f"TRUNCATE TABLE {schema_name}.{table_name}"))
            
            # แปลงคอลัมน์วันที่ให้เป็นรูปแบบที่ SQL Server รองรับ
            for col, dtype in required_cols.items():
                dtype_str = str(dtype).lower()
                if col in df.columns and ("date" in dtype_str or "datetime" in dtype_str):
                    df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=False)
                    if "date" in dtype_str and "datetime" not in dtype_str:
                        df[col] = df[col].dt.strftime("%Y-%m-%d")
                    elif "datetime" in dtype_str:
                        df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M:%S")
            
            # ตรวจสอบว่าข้อมูลไม่ว่างเปล่าหลังการแปลง
            if df.empty:
                return False, "ข้อมูลว่างเปล่าหลังการแปลง"
            
            # อัปโหลดข้อมูลแบบ chunked สำหรับไฟล์ใหญ่
            if len(df) > 10000:  # ถ้าไฟล์ใหญ่กว่า 10,000 แถว
                if log_func:
                    log_func(f"📊 ไฟล์ขนาดใหญ่ ({len(df):,} แถว) - อัปโหลดแบบ chunked")
                
                chunk_size = 5000
                total_chunks = (len(df) + chunk_size - 1) // chunk_size
                uploaded_rows = 0
                
                for i in range(0, len(df), chunk_size):
                    chunk = df.iloc[i:i+chunk_size]
                    chunk[list(required_cols.keys())].to_sql(
                        name=table_name,
                        con=self.engine,
                        schema=schema_name,
                        if_exists='append',
                        index=False,
                        dtype=required_cols
                    )
                    uploaded_rows += len(chunk)
                    
                    chunk_num = (i // chunk_size) + 1
                    if log_func:
                        log_func(f"📤 อัปโหลด chunk {chunk_num}/{total_chunks}: {len(chunk):,} แถว")
                
                return True, f" {schema_name}.{table_name} อัปโหลดข้อมูล {uploaded_rows:,} แถวสำเร็จ (แบบ chunked)"
            else:
                # อัปโหลดแบบปกติสำหรับไฟล์เล็ก
                df[list(required_cols.keys())].to_sql(
                    name=table_name,
                    con=self.engine,
                    schema=schema_name,
                    if_exists='append',
                    index=False,
                    dtype=required_cols
                )
                return True, f" {schema_name}.{table_name} อัปโหลดข้อมูล {df.shape[0]} แถวสำเร็จ"
        except Exception as e:
            error_msg = f"เกิดข้อผิดพลาด: {e}"
            if log_func:
                log_func(f"❌ {error_msg}")
            return False, error_msg
