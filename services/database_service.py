from sqlalchemy import text, create_engine
from config.database import DatabaseConfig
import pandas as pd
from tkinter import messagebox
import logging
import os

class DatabaseService:
    def __init__(self):
        self.db_config = DatabaseConfig()
        self.engine = self.db_config.get_engine()
        self.logger = logging.getLogger(__name__)

    def check_connection(self):
        """ตรวจสอบการเชื่อมต่อกับ SQL Server"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True, "เชื่อมต่อกับ SQL Server สำเร็จ"
        except Exception as e:
            error_msg = f"ไม่สามารถเชื่อมต่อกับ SQL Server ได้: {e}"
            self.logger.error(error_msg)
            messagebox.showwarning("การเชื่อมต่อฐานข้อมูล", error_msg)
            return False, error_msg

    def test_connection(self, config):
        """ทดสอบการเชื่อมต่อกับ SQL Server ด้วย config ที่รับมา"""
        try:
            driver = "ODBC+Driver+17+for+SQL+Server"
            if config["auth_type"] == "Windows":
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
            print(f"Connection error: {e}")
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

    def upload_data(self, df, logic_type, required_cols, schema_name='bronze', log_func=None):
        """อัปโหลดข้อมูลไปยังฐานข้อมูล: สร้างตารางใหม่ตาม config, insert เฉพาะคอลัมน์ที่ตั้งค่าไว้, ถ้า schema DB ไม่ตรงให้ drop และสร้างตารางใหม่"""
        try:
            import json
            from datetime import datetime
            from sqlalchemy.types import DateTime
            
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
            self.ensure_schemas_exist([schema_name])

            # ตรวจสอบ schema DB ว่าตรงกับ required_cols หรือไม่
            from sqlalchemy import inspect
            insp = inspect(self.engine)
            if insp.has_table(table_name, schema=schema_name):
                db_cols = [col['name'] for col in insp.get_columns(table_name, schema=schema_name)]
                config_cols = list(required_cols.keys())
                if set(db_cols) != set(config_cols):
                    msg = f"❌ Schema ของตาราง {schema_name}.{table_name} ใน DB ไม่ตรงกับ config: {config_cols} กำลังลบและสร้างตารางใหม่"
                    if log_func:
                        log_func(msg)
                    # Drop และสร้างตารางใหม่
                    df.head(0)[list(required_cols.keys())].to_sql(
                        name=table_name,
                        con=self.engine,
                        schema=schema_name,
                        if_exists='replace',
                        index=False,
                        dtype=required_cols
                    )
                else:
                    # ล้างข้อมูลเดิม
                    with self.engine.begin() as conn:
                        conn.execute(text(f"TRUNCATE TABLE {schema_name}.{table_name}"))
            else:
                # สร้างตารางใหม่ตาม config
                df.head(0)[list(required_cols.keys())].to_sql(
                    name=table_name,
                    con=self.engine,
                    schema=schema_name,
                    if_exists='replace',
                    index=False,
                    dtype=required_cols
                )
            # แปลงคอลัมน์วันที่ให้เป็นรูปแบบที่ SQL Server รองรับ
            for col, dtype in required_cols.items():
                dtype_str = str(dtype).lower()
                if col in df.columns and ("date" in dtype_str or "datetime" in dtype_str):
                    df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=False)
                    if "date" in dtype_str and "datetime" not in dtype_str:
                        df[col] = df[col].dt.strftime("%Y-%m-%d")
                    elif "datetime" in dtype_str:
                        df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M:%S")
            # เพิ่มข้อมูลทั้งหมด เฉพาะคอลัมน์ที่ตั้งค่าไว้ (รวม timestamp)
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
            return False, f"เกิดข้อผิดพลาด: {e}"
