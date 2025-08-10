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
from sqlalchemy.exc import DBAPIError, ProgrammingError

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
            # ใช้ silent callback เป็นค่าเริ่มต้นสำหรับ GUI
            default_callback = log_callback or (lambda msg: None)
            self.permission_checker = PermissionCheckerService(
                engine=self.engine, 
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
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True, SuccessMessages.DB_CONNECTION_SUCCESS
        except Exception as e:
            error_msg = f"{ErrorMessages.DB_CONNECTION_FAILED}: {e}"
            self.logger.error(error_msg)
            if show_warning:
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
            needs_recreate = force_recreate
            
            if insp.has_table(table_name, schema=schema_name) and not force_recreate:
                db_cols = [col['name'] for col in insp.get_columns(table_name, schema=schema_name)]
                db_col_types = {col['name']: str(col['type']).upper() for col in insp.get_columns(table_name, schema=schema_name)}
                config_cols = list(required_cols.keys())
                
                # ตรวจสอบคอลัมน์
                if set(db_cols) != set(config_cols):
                    msg = f"❌ คอลัมน์ของตาราง {schema_name}.{table_name} ไม่ตรงกับ config"
                    needs_recreate = True
                else:
                    # ตรวจสอบ data types ให้ครอบคลุมทุกรูปแบบ
                    from sqlalchemy.types import NVARCHAR as SA_NVARCHAR, DateTime as SA_DateTime, DATE as SA_DATE
                    from sqlalchemy.types import Integer as SA_Integer, SmallInteger as SA_SmallInteger, Float as SA_Float, DECIMAL as SA_DECIMAL, Text as SA_Text, Boolean as SA_Boolean

                    def _type_category(type_str: str) -> str:
                        t = (type_str or '').upper()
                        if any(x in t for x in ['INT', 'BIGINT', 'SMALLINT', 'FLOAT', 'DECIMAL', 'NUMERIC', 'REAL', 'MONEY']):
                            return 'NUMERIC'
                        if any(x in t for x in ['DATE', 'DATETIME', 'SMALLDATETIME', 'DATETIME2', 'TIME']):
                            return 'DATETIME'
                        if any(x in t for x in ['BIT', 'BOOLEAN']):
                            return 'BOOLEAN'
                        if any(x in t for x in ['CHAR', 'NCHAR', 'VARCHAR', 'NVARCHAR', 'TEXT']):
                            return 'STRING'
                        return 'OTHER'

                    def _expected_type_str(sa_type_obj) -> str:
                        # แปลง SQLAlchemy type object เป็น string ที่ใช้เทียบกับ DB
                        s = str(sa_type_obj).upper()
                        # Map Text() ให้เทียบเป็น NVARCHAR(MAX)
                        if isinstance(sa_type_obj, SA_Text):
                            return 'NVARCHAR(MAX)'
                        return s

                    def _parse_varchar_len(type_str: str) -> int:
                        try:
                            if 'MAX' in type_str.upper():
                                return 2_147_483_647  # ใหญ่พอแทน MAX
                            if '(' in type_str and ')' in type_str:
                                return int(type_str.split('(')[1].split(')')[0])
                        except Exception:
                            pass
                        return -1

                    for col_name, expected_dtype in required_cols.items():
                        db_type = db_col_types.get(col_name, '')
                        expected_str = _expected_type_str(expected_dtype)
                        cat_db = _type_category(db_type)
                        cat_expected = _type_category(expected_str)

                        # กรณี Text() ต้องเป็น NVARCHAR(MAX)
                        if isinstance(expected_dtype, SA_Text):
                            if 'NVARCHAR(MAX)' not in db_type and 'TEXT' not in db_type:
                                if log_func:
                                    log_func(f"❌ คอลัมน์ '{col_name}' ควรเป็น NVARCHAR(MAX) แต่เป็น {db_type}")
                                needs_recreate = True
                                break

                        # ตรวจจับ mismatch ของหมวดชนิดข้อมูล (เช่น STRING ↔ NUMERIC)
                        if cat_db != cat_expected:
                            if log_func:
                                log_func(f"❌ ชนิดข้อมูลของคอลัมน์ '{col_name}' ไม่ตรงกัน (DB: {db_type} | Expected: {expected_str})")
                            needs_recreate = True
                            break

                        # ถ้าเป็น STRING ให้ตรวจสอบความยาว NVARCHAR
                        if cat_expected == 'STRING' and 'NVARCHAR' in expected_str:
                            exp_len = _parse_varchar_len(expected_str)
                            act_len = _parse_varchar_len(db_type)
                            if act_len != -1 and exp_len != -1 and act_len < exp_len:
                                if log_func:
                                    log_func(f"❌ ความยาว NVARCHAR ของ '{col_name}' ไม่พอ (DB: {db_type} | Expected: {expected_str})")
                                needs_recreate = True
                                break
            
            # ------------------------------
            # ขั้นตอนใหม่: Ingest → NVARCHAR(MAX) staging → SQL แปลงหลังนำเข้า
            # ------------------------------
            # 1) สร้างตาราง staging ด้วย NVARCHAR(MAX) ทั้งหมด
            staging_table = f"{table_name}__stg"
            staging_cols = list(required_cols.keys())
            with self.engine.begin() as conn:
                # ลบ staging table ถ้ามีอยู่แล้ว
                conn.execute(text(f"""
                    IF OBJECT_ID('{schema_name}.{staging_table}', 'U') IS NOT NULL
                        DROP TABLE {schema_name}.{staging_table};
                """))
                # สร้าง staging table ที่เป็น NVARCHAR(MAX) ทุกคอลัมน์
                cols_sql = ", ".join([f"[{c}] NVARCHAR(MAX) NULL" for c in staging_cols])
                conn.execute(text(f"CREATE TABLE {schema_name}.{staging_table} ({cols_sql})"))
                if log_func:
                    log_func(f"📦 สร้างตารางชั่วคราวสำหรับนำเข้า: {schema_name}.{staging_table} (NVARCHAR(MAX) ทุกคอลัมน์)")

            # 2) อัปโหลดข้อมูลเข้า staging ด้วย pandas.to_sql
            if len(df) > 10000:
                if log_func:
                    log_func(f"📊 ไฟล์ขนาดใหญ่ ({len(df):,} แถว) - อัปโหลดแบบ chunked ไปยัง staging")
                chunk_size = 5000
                total_chunks = (len(df) + chunk_size - 1) // chunk_size
                for i in range(0, len(df), chunk_size):
                    chunk = df.iloc[i:i+chunk_size]
                    chunk[staging_cols].to_sql(
                        name=staging_table,
                        con=self.engine,
                        schema=schema_name,
                        if_exists='append',
                        index=False
                    )
                    chunk_num = (i // chunk_size) + 1
                    if log_func:
                        log_func(f"📤 อัปโหลด staging chunk {chunk_num}/{total_chunks}: {len(chunk):,} แถว")
            else:
                if log_func:
                    log_func(f"📤 อัปโหลดข้อมูล: {len(df):,} แถว → {schema_name}.{staging_table}")
                df[staging_cols].to_sql(
                    name=staging_table,
                    con=self.engine,
                    schema=schema_name,
                    if_exists='append',
                    index=False
                )

            # 3) สร้าง/รีสร้างตารางจริงตาม dtype config (ไม่ auto-fix)
            if needs_recreate or not insp.has_table(table_name, schema=schema_name):
                if needs_recreate and log_func:
                    log_func(f"🛠️ สร้างตาราง {schema_name}.{table_name} ใหม่ให้ตรงกับการตั้งค่าประเภทข้อมูล")
                elif log_func:
                    log_func(f"📋 สร้างตาราง {schema_name}.{table_name} ตามการตั้งค่าประเภทข้อมูล")
                
                df.head(0)[list(required_cols.keys())].to_sql(
                    name=table_name,
                    con=self.engine,
                    schema=schema_name,
                    if_exists='replace',
                    index=False,
                    dtype=required_cols
                )
                # ปรับ Text() → NVARCHAR(MAX)
                self._fix_text_columns_to_nvarchar_max(table_name, required_cols, schema_name, log_func)
            else:
                # ล้างข้อมูลเดิมของตารางจริง
                if log_func:
                    log_func(f"🧹 ล้างข้อมูลเดิมในตาราง {schema_name}.{table_name}")
                with self.engine.begin() as conn:
                    conn.execute(text(f"TRUNCATE TABLE {schema_name}.{table_name}"))

            # 4) แปลงข้อมูลจาก staging → ตารางจริง ด้วย TRY_CONVERT/REPLACE ตาม dtype เดิม
            from sqlalchemy.types import (
                Integer as SA_Integer,
                SmallInteger as SA_SmallInteger,
                Float as SA_Float,
                DECIMAL as SA_DECIMAL,
                DATE as SA_DATE,
                DateTime as SA_DateTime,
                NVARCHAR as SA_NVARCHAR,
                Text as SA_Text,
                Boolean as SA_Boolean,
            )

            def _sql_type_and_expr(col_name: str, sa_type_obj) -> str:
                col_ref = f"[{col_name}]"
                base = "NULLIF(LTRIM(RTRIM(" + col_ref + ")), '')"
                if isinstance(sa_type_obj, (SA_Integer, SA_SmallInteger)):
                    return f"TRY_CONVERT(INT, REPLACE(REPLACE({base}, ',', ''), ' ', ''))"
                if isinstance(sa_type_obj, SA_Float):
                    return f"TRY_CONVERT(FLOAT, REPLACE(REPLACE({base}, ',', ''), ' ', ''))"
                if isinstance(sa_type_obj, SA_DECIMAL):
                    precision = getattr(sa_type_obj, 'precision', 18) or 18
                    scale = getattr(sa_type_obj, 'scale', 2) or 2
                    return f"TRY_CONVERT(DECIMAL({precision},{scale}), REPLACE(REPLACE({base}, ',', ''), ' ', ''))"
                if isinstance(sa_type_obj, (SA_DATE, SA_DateTime)):
                    # ลองหลายรูปแบบ: ISO(121), UK(103), US(101)
                    return (
                        f"COALESCE("
                        f"TRY_CONVERT(DATETIME, {base}, 121),"
                        f"TRY_CONVERT(DATETIME, {base}, 103),"
                        f"TRY_CONVERT(DATETIME, {base}, 101)"
                        f")"
                    )
                if isinstance(sa_type_obj, SA_Boolean):
                    return (
                        "CASE "
                        f"WHEN UPPER(LTRIM(RTRIM({col_ref}))) IN ('1','TRUE','Y','YES') THEN 1 "
                        f"WHEN UPPER(LTRIM(RTRIM({col_ref}))) IN ('0','FALSE','N','NO') THEN 0 "
                        "ELSE NULL END"
                    )
                # NVARCHAR(n) / NVARCHAR(MAX)
                target = 'NVARCHAR(MAX)' if isinstance(sa_type_obj, SA_Text) else str(sa_type_obj).upper()
                return f"TRY_CONVERT({target}, {col_ref})"

            select_exprs = []
            for col_name, sa_type in required_cols.items():
                select_exprs.append(f"{_sql_type_and_expr(col_name, sa_type)} AS [{col_name}]")
            select_sql = ", ".join(select_exprs)

            with self.engine.begin() as conn:
                insert_sql = (
                    f"INSERT INTO {schema_name}.{table_name} (" + ", ".join([f"[{c}]" for c in required_cols.keys()]) + ") "
                    f"SELECT {select_sql} FROM {schema_name}.{staging_table}"
                )
                conn.execute(text(insert_sql))

                # ลบ staging table เมื่อเสร็จสิ้น
                conn.execute(text(f"DROP TABLE {schema_name}.{staging_table}"))
                if log_func:
                    log_func(f"🗑️ ลบตารางชั่วคราว {schema_name}.{staging_table}")

            return True, f"อัปโหลดสำเร็จ → {schema_name}.{table_name} (นำเข้า NVARCHAR(MAX) แล้วแปลงตาม dtype {len(df):,} แถว)"
        except Exception as e:
            # สรุปข้อความผิดพลาดให้สั้นและชี้เป้าคอลัมน์ที่น่าจะมีปัญหา
            def _short_exception_message(exc: Exception) -> str:
                try:
                    if isinstance(exc, DBAPIError) and getattr(exc, "orig", None):
                        # ดึงเฉพาะข้อความหลักจาก DBAPI/pyodbc โดยตัด SQL และ parameters ทิ้ง
                        orig = exc.orig
                        # pyodbc จะมี args เป็น tuple ที่มีข้อความยาว เราเลือกอันที่สื่อความสุด
                        parts = [str(p) for p in getattr(orig, "args", []) if p]
                        core = parts[-1] if parts else str(exc)
                    else:
                        core = str(exc)
                    # ตัดส่วน [SQL: ...] และ [parameters: ...] ถ้ามี
                    for token in ["[SQL:", "[parameters:"]:
                        if token in core:
                            core = core.split(token)[0].strip()
                    # ย่อบรรทัดให้สั้น (เอาเฉพาะบรรทัดแรก)
                    core = core.splitlines()[0]
                    return core
                except Exception:
                    return str(exc)

            def _detect_problem_columns(df_local, required_map, max_cols: int = 5, max_examples: int = 3):
                import pandas as pd  # ภายในเพื่อหลีกเลี่ยง import วน
                from sqlalchemy.types import (
                    Integer as SA_Integer,
                    SmallInteger as SA_SmallInteger,
                    Float as SA_Float,
                    DECIMAL as SA_DECIMAL,
                    DATE as SA_DATE,
                    DateTime as SA_DateTime,
                    NVARCHAR as SA_NVARCHAR,
                )
                problems = []
                try:
                    for col, dtype in required_map.items():
                        if col not in df_local.columns:
                            continue
                        # ตัวเลข
                        if isinstance(dtype, (SA_Integer, SA_SmallInteger, SA_Float, SA_DECIMAL)):
                            numeric_series = pd.to_numeric(df_local[col], errors="coerce")
                            mask = numeric_series.isna() & df_local[col].notna()
                            bad_count = int(mask.sum())
                            if bad_count > 0:
                                examples = [str(x) for x in df_local.loc[mask, col].head(max_examples).tolist()]
                                problems.append({
                                    "column": col,
                                    "expected": str(dtype),
                                    "bad_count": bad_count,
                                    "examples": examples,
                                })
                        # วันที่
                        elif isinstance(dtype, (SA_DATE, SA_DateTime)):
                            parsed = pd.to_datetime(df_local[col], errors="coerce")
                            mask = parsed.isna() & df_local[col].notna()
                            bad_count = int(mask.sum())
                            if bad_count > 0:
                                examples = [str(x) for x in df_local.loc[mask, col].head(max_examples).tolist()]
                                problems.append({
                                    "column": col,
                                    "expected": str(dtype),
                                    "bad_count": bad_count,
                                    "examples": examples,
                                })
                        # ความยาวของ string (ถ้ากำหนด NVARCHAR(n))
                        elif isinstance(dtype, SA_NVARCHAR) and getattr(dtype, "length", None):
                            max_len = int(dtype.length)
                            str_series = df_local[col].astype(str)
                            mask = str_series.str.len() > max_len
                            bad_count = int(mask.sum())
                            if bad_count > 0:
                                examples = str_series.loc[mask].str[:50].head(max_examples).tolist()
                                problems.append({
                                    "column": col,
                                    "expected": f"NVARCHAR({max_len})",
                                    "bad_count": bad_count,
                                    "examples": examples,
                                })
                        # อื่น ๆ ข้ามไป
                        if len(problems) >= max_cols:
                            break
                except Exception:
                    pass
                return problems

            short_msg = _short_exception_message(e)
            problem_hints = _detect_problem_columns(df, required_cols)

            if problem_hints:
                lines = [
                    f"เกิดข้อผิดพลาดจากฐานข้อมูล: {short_msg}",
                    "คอลัมน์ที่น่าจะมีปัญหา (แสดงบางส่วน):",
                ]
                for p in problem_hints:
                    ex = ", ".join(p.get("examples", []))
                    lines.append(f"- {p['column']} (คาดว่า {p['expected']}) ผิด {p['bad_count']:,} แถว ตัวอย่าง: [{ex}]")
                error_msg = "\n".join(lines)
            else:
                error_msg = f"เกิดข้อผิดพลาดจากฐานข้อมูล: {short_msg}"

            if log_func:
                log_func(f"❌ {error_msg}")
            return False, error_msg
