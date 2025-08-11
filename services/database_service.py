"""
Database Service สำหรับ PIPELINE_SQLSERVER

จัดการการเชื่อมต่อและอัปโหลดข้อมูลไปยัง SQL Server
"""

import logging
import os
from tkinter import messagebox
from typing import Any, Dict, Tuple

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
                messagebox.showwarning("Database connection", error_msg)
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
            return True, f"Verified/created schemas: {', '.join(schema_names)}"
        except Exception as e:
            error_msg = f"Failed to create schema: {e}"
            self.logger.error(error_msg)
            messagebox.showwarning("Schema creation", error_msg)
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
                            log_func(f"🔧 Alter column '{col_name}' to NVARCHAR(MAX)")
                        conn.execute(text(alter_sql))
        except Exception as e:
            if log_func:
                log_func(f"⚠️ Unable to alter Text() column: {e}")

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
            log_func("✅ Database access permissions are correct")
        
        try:
            import json
            from datetime import datetime
            from sqlalchemy.types import DateTime
            
            # ตรวจสอบข้อมูลเบื้องต้น
            if df is None or df.empty:
                return False, "Empty data"
            
            if not required_cols:
                return False, "Data type settings not found"
            
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
                return False, f"Could not create schema: {schema_result[1]}"

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
                    msg = f"❌ Table {schema_name}.{table_name} columns do not match config"
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

                        # กรณี Text() ต้องเป็น NVARCHAR(MAX) - ตรวจสอบเฉพาะกรณีที่ร้ายแรง
                        if isinstance(expected_dtype, SA_Text):
                            if 'NVARCHAR(MAX)' not in db_type and 'TEXT' not in db_type and 'NVARCHAR' not in db_type:
                                # เฉพาะกรณีที่ชนิดข้อมูลไม่ใช่ NVARCHAR เลย (เช่น INT, DATE)
                                if log_func:
                                    log_func(f"❌ Schema Mismatch: Column '{col_name}' should be NVARCHAR(MAX) but database has {db_type}")
                                    log_func(f"   💡 Suggestion: Allow system to create new table to fix this issue")
                                needs_recreate = True
                                break

                        # ตรวจจับ mismatch ของหมวดชนิดข้อมูล (เช่น STRING ↔ NUMERIC)
                        if cat_db != cat_expected:
                            if log_func:
                                log_func(f"❌ Data type mismatch for column '{col_name}' (DB: {db_type} | Expected: {expected_str})")
                            needs_recreate = True
                            break

                        # ถ้าเป็น STRING ให้ตรวจสอบความยาว NVARCHAR
                        if cat_expected == 'STRING' and 'NVARCHAR' in expected_str:
                            exp_len = _parse_varchar_len(expected_str)
                            act_len = _parse_varchar_len(db_type)
                            if act_len != -1 and exp_len != -1 and act_len < exp_len:
                                if log_func:
                                    log_func(f"❌ NVARCHAR length for '{col_name}' is insufficient (DB: {db_type} | Expected: {expected_str})")
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
                    log_func(f"📦 Created staging table: {schema_name}.{staging_table} (NVARCHAR(MAX) for all columns)")

            # 2) อัปโหลดข้อมูลเข้า staging ด้วย pandas.to_sql
            if len(df) > 10000:
                if log_func:
                    log_func(f"📊 Large file ({len(df):,} rows) - uploading in chunks to staging")
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
                        log_func(f"📤 Uploaded staging chunk {chunk_num}/{total_chunks}: {len(chunk):,} rows")
            else:
                if log_func:
                    log_func(f"📤 Uploaded data: {len(df):,} rows → {schema_name}.{staging_table}")
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
                    log_func(f"🛠️ Creating table {schema_name}.{table_name} to match data type settings")
                elif log_func:
                    log_func(f"📋 Creating table {schema_name}.{table_name} from data type settings")
                
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
                    log_func(f"🧹 Truncating existing data in table {schema_name}.{table_name}")
                with self.engine.begin() as conn:
                    conn.execute(text(f"TRUNCATE TABLE {schema_name}.{table_name}"))

            # 4) ตรวจสอบข้อมูลใน staging table ด้วย SQL validation
            if log_func:
                log_func(f"🔍 Validating data in staging table...")
            
            validation_results = self.validate_data_in_staging(staging_table, logic_type, required_cols, schema_name, log_func)
            
            if not validation_results['is_valid']:
                # ลบ staging table และหยุดการประมวลผล
                with self.engine.begin() as conn:
                    conn.execute(text(f"DROP TABLE {schema_name}.{staging_table}"))
                return False, validation_results['summary']
            
            # 5) แปลงข้อมูลจาก staging → ตารางจริง ด้วย TRY_CONVERT/REPLACE ตาม dtype เดิม
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
                    log_func(f"🗑️ Dropped staging table {schema_name}.{staging_table}")

            return True, f"Upload successful → {schema_name}.{table_name} (ingested NVARCHAR(MAX) then converted by dtype for {len(df):,} rows)"
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
                    f"Database error: {short_msg}",
                    "Likely problematic columns (partial):",
                ]
                for p in problem_hints:
                    ex = ", ".join(p.get("examples", []))
                    lines.append(f"- {p['column']} (expected {p['expected']}) invalid {p['bad_count']:,} rows. Examples: [{ex}]")
                error_msg = "\n".join(lines)
            else:
                error_msg = f"Database error: {short_msg}"

            if log_func:
                log_func(f"❌ {error_msg}")
            return False, error_msg

    def validate_data_in_staging(self, staging_table, logic_type, required_cols, schema_name='bronze', log_func=None):
        """
        ตรวจสอบความถูกต้องของข้อมูลใน staging table ด้วย SQL
        
        Args:
            staging_table: ชื่อ staging table
            logic_type: ประเภทไฟล์
            required_cols: คอลัมน์และชนิดข้อมูลที่ต้องการ
            schema_name: ชื่อ schema
            log_func: ฟังก์ชันสำหรับ log
            
        Returns:
            Dict: ผลการตรวจสอบ {'is_valid': bool, 'issues': [...], 'summary': str}
        """
        try:
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
            
            validation_results = {
                'is_valid': True,
                'issues': [],
                'warnings': [],
                'summary': ''
            }
            
            total_rows = 0
            with self.engine.connect() as conn:
                # นับจำนวนแถวทั้งหมด
                result = conn.execute(text(f"SELECT COUNT(*) FROM {schema_name}.{staging_table}"))
                total_rows = result.scalar()
            
            if total_rows == 0:
                validation_results['is_valid'] = False
                validation_results['summary'] = "No data in staging table"
                return validation_results
            
            if log_func:
                log_func(f"📊 Validating {total_rows:,} rows in staging table")
            
            validation_queries = self._build_validation_queries(staging_table, required_cols, schema_name)
            
            # เพิ่มการตรวจสอบ schema mismatch
            schema_issues = self._check_schema_mismatch_in_staging(staging_table, required_cols, schema_name, log_func)
            if schema_issues:
                validation_results['warnings'].extend(schema_issues)
            
            with self.engine.connect() as conn:
                for validation_type, query in validation_queries.items():
                    try:
                        result = conn.execute(text(query))
                        rows = result.fetchall()
                        
                        if rows:
                            for row in rows:
                                issue = {
                                    'validation_type': validation_type,
                                    'column': row.column_name if hasattr(row, 'column_name') else 'unknown',
                                    'error_count': row.error_count if hasattr(row, 'error_count') else 0,
                                    'percentage': round((row.error_count / total_rows) * 100, 2) if hasattr(row, 'error_count') else 0,
                                    'examples': row.examples if hasattr(row, 'examples') else ''
                                }
                                
                                # กำหนดความรุนแรง
                                if issue['percentage'] > 10:  # มากกว่า 10% ถือว่าเป็นปัญหาร้ายแรง
                                    validation_results['is_valid'] = False
                                    validation_results['issues'].append(issue)
                                elif issue['percentage'] > 1:  # 1-10% ถือว่าเป็นคำเตือน
                                    validation_results['warnings'].append(issue)
                                
                                if log_func and issue['error_count'] > 0:
                                    status = "❌" if issue['percentage'] > 10 else "⚠️"
                                    column_name = issue['column'] if isinstance(issue['column'], str) else str(issue['column'])
                                    examples = issue['examples'][:100] if isinstance(issue['examples'], str) else str(issue['examples'])[:100]
                                    log_func(f"   {status} {column_name}: {issue['error_count']:,} invalid rows ({issue['percentage']}%) Examples: {examples}")
                    
                    except Exception as query_error:
                        if log_func:
                            log_func(f"⚠️ Could not run validation query for {validation_type}: {query_error}")
            
            # สร้างสรุปผล
            if not validation_results['is_valid']:
                serious_issues = len(validation_results['issues'])
                warnings_count = len(validation_results['warnings'])
                validation_results['summary'] = f"Found {serious_issues} serious issues and {warnings_count} warnings - cannot import data"
            elif validation_results['warnings']:
                warnings_count = len(validation_results['warnings'])
                validation_results['summary'] = f"Found {warnings_count} warnings; data can be imported"
                if log_func:
                    log_func(f"✅ Data validation passed (with {warnings_count} warnings)")
            else:
                validation_results['summary'] = "All data valid"
                if log_func:
                    log_func(f"✅ All data passed validation")
                    
            return validation_results
            
        except Exception as e:
            validation_results = {
                'is_valid': False,
                'issues': [],
                'warnings': [],
                'summary': f"Error validating data: {str(e)}"
            }
            if log_func:
                log_func(f"❌ {validation_results['summary']}")
            return validation_results
    
    def _build_validation_queries(self, staging_table, required_cols, schema_name):
        """
        สร้าง SQL queries สำหรับ validation ตามชนิดข้อมูลที่กำหนด
        """
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
        
        queries = {}
        
        # ตรวจสอบข้อมูลตัวเลข
        numeric_columns = []
        for col, dtype in required_cols.items():
            if isinstance(dtype, (SA_Integer, SA_SmallInteger, SA_Float, SA_DECIMAL)):
                numeric_columns.append(col)
        
        if numeric_columns:
            numeric_cases = []
            for col in numeric_columns:
                # ใช้ NVARCHAR literal สำหรับชื่อคอลัมน์ภาษาไทย
                col_literal = f"N'{col}'" if any(ord(c) > 127 for c in col) else f"'{col}'"
                numeric_cases.append(f"""
                    SELECT {col_literal} as column_name, [{col}] as invalid_value, ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) as row_num
                    FROM {schema_name}.{staging_table}
                    WHERE TRY_CAST(REPLACE(REPLACE(NULLIF(LTRIM(RTRIM([{col}])), ''), ',', ''), ' ', '') AS FLOAT) IS NULL 
                      AND NULLIF(LTRIM(RTRIM([{col}])), '') IS NOT NULL
                """)
            
            queries['numeric_validation'] = f"""
                WITH numeric_errors AS (
                    {' UNION ALL '.join(numeric_cases)}
                ),
                error_counts AS (
                    SELECT column_name, COUNT(*) as error_count
                    FROM numeric_errors
                    GROUP BY column_name
                ),
                limited_examples AS (
                    SELECT column_name, invalid_value, row_num,
                           ROW_NUMBER() OVER (PARTITION BY column_name ORDER BY row_num) as rn
                    FROM numeric_errors
                )
                SELECT 
                    ec.column_name,
                    ec.error_count,
                    CAST(STRING_AGG(CAST(le.invalid_value AS NVARCHAR(50)), ', ') WITHIN GROUP (ORDER BY le.row_num) AS NVARCHAR(MAX)) as examples
                FROM error_counts ec
                LEFT JOIN limited_examples le ON ec.column_name = le.column_name AND le.rn <= 5
                GROUP BY ec.column_name, ec.error_count
            """
        
        # ตรวจสอบข้อมูลวันที่
        date_columns = []
        for col, dtype in required_cols.items():
            if isinstance(dtype, (SA_DATE, SA_DateTime)):
                date_columns.append(col)
        
        if date_columns:
            date_cases = []
            for col in date_columns:
                # ใช้ NVARCHAR literal สำหรับชื่อคอลัมน์ภาษาไทย
                col_literal = f"N'{col}'" if any(ord(c) > 127 for c in col) else f"'{col}'"
                date_cases.append(f"""
                    SELECT {col_literal} as column_name, [{col}] as invalid_value, ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) as row_num
                    FROM {schema_name}.{staging_table}
                    WHERE COALESCE(
                        TRY_CONVERT(DATETIME, NULLIF(LTRIM(RTRIM([{col}])), ''), 121),
                        TRY_CONVERT(DATETIME, NULLIF(LTRIM(RTRIM([{col}])), ''), 103),
                        TRY_CONVERT(DATETIME, NULLIF(LTRIM(RTRIM([{col}])), ''), 101)
                    ) IS NULL
                    AND NULLIF(LTRIM(RTRIM([{col}])), '') IS NOT NULL
                """)
            
            queries['date_validation'] = f"""
                WITH date_errors AS (
                    {' UNION ALL '.join(date_cases)}
                ),
                error_counts AS (
                    SELECT column_name, COUNT(*) as error_count
                    FROM date_errors
                    GROUP BY column_name
                ),
                limited_examples AS (
                    SELECT column_name, invalid_value, row_num,
                           ROW_NUMBER() OVER (PARTITION BY column_name ORDER BY row_num) as rn
                    FROM date_errors
                )
                SELECT 
                    ec.column_name,
                    ec.error_count,
                    CAST(STRING_AGG(CAST(le.invalid_value AS NVARCHAR(50)), ', ') WITHIN GROUP (ORDER BY le.row_num) AS NVARCHAR(MAX)) as examples
                FROM error_counts ec
                LEFT JOIN limited_examples le ON ec.column_name = le.column_name AND le.rn <= 5
                GROUP BY ec.column_name, ec.error_count
            """
        
        # ตรวจสอบความยาวของ string (เฉพาะ NVARCHAR ที่มีกำหนดความยาว)
        string_columns = []
        for col, dtype in required_cols.items():
            if isinstance(dtype, SA_NVARCHAR) and hasattr(dtype, 'length') and dtype.length:
                string_columns.append((col, dtype.length))
        
        if string_columns:
            string_cases = []
            for col, max_length in string_columns:
                # ใช้ NVARCHAR literal สำหรับชื่อคอลัมน์ภาษาไทย
                col_literal = f"N'{col}'" if any(ord(c) > 127 for c in col) else f"'{col}'"
                string_cases.append(f"""
                    SELECT {col_literal} as column_name, LEFT([{col}], 50) + '...' as invalid_value, ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) as row_num
                    FROM {schema_name}.{staging_table}
                    WHERE LEN(ISNULL([{col}], '')) > {max_length}
                """)
            
            queries['string_length_validation'] = f"""
                WITH string_errors AS (
                    {' UNION ALL '.join(string_cases)}
                ),
                error_counts AS (
                    SELECT column_name, COUNT(*) as error_count
                    FROM string_errors
                    GROUP BY column_name
                ),
                limited_examples AS (
                    SELECT column_name, invalid_value, row_num,
                           ROW_NUMBER() OVER (PARTITION BY column_name ORDER BY row_num) as rn
                    FROM string_errors
                )
                SELECT 
                    ec.column_name,
                    ec.error_count,
                    CAST(STRING_AGG(CAST(le.invalid_value AS NVARCHAR(100)), ', ') WITHIN GROUP (ORDER BY le.row_num) AS NVARCHAR(MAX)) as examples
                FROM error_counts ec
                LEFT JOIN limited_examples le ON ec.column_name = le.column_name AND le.rn <= 3
                GROUP BY ec.column_name, ec.error_count
            """
        
        # ตรวจสอบข้อมูล boolean
        boolean_columns = []
        for col, dtype in required_cols.items():
            if isinstance(dtype, SA_Boolean):
                boolean_columns.append(col)
        
        if boolean_columns:
            boolean_cases = []
            for col in boolean_columns:
                # ใช้ NVARCHAR literal สำหรับชื่อคอลัมน์ภาษาไทย
                col_literal = f"N'{col}'" if any(ord(c) > 127 for c in col) else f"'{col}'"
                boolean_cases.append(f"""
                    SELECT {col_literal} as column_name, [{col}] as invalid_value, ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) as row_num
                    FROM {schema_name}.{staging_table}
                    WHERE UPPER(LTRIM(RTRIM(ISNULL([{col}], '')))) NOT IN ('1','TRUE','Y','YES','0','FALSE','N','NO','')
                """)
            
            queries['boolean_validation'] = f"""
                WITH boolean_errors AS (
                    {' UNION ALL '.join(boolean_cases)}
                ),
                error_counts AS (
                    SELECT column_name, COUNT(*) as error_count
                    FROM boolean_errors
                    GROUP BY column_name
                ),
                limited_examples AS (
                    SELECT column_name, invalid_value, row_num,
                           ROW_NUMBER() OVER (PARTITION BY column_name ORDER BY row_num) as rn
                    FROM boolean_errors
                )
                SELECT 
                    ec.column_name,
                    ec.error_count,
                    CAST(STRING_AGG(CAST(le.invalid_value AS NVARCHAR(50)), ', ') WITHIN GROUP (ORDER BY le.row_num) AS NVARCHAR(MAX)) as examples
                FROM error_counts ec
                LEFT JOIN limited_examples le ON ec.column_name = le.column_name AND le.rn <= 5
                GROUP BY ec.column_name, ec.error_count
            """
        
        return queries
    
    def _check_schema_mismatch_in_staging(self, staging_table, required_cols, schema_name, log_func=None):
        """
        ตรวจสอบ schema mismatch หลังจากนำเข้า staging table แล้ว
        เหมือนกับการ validation อื่นๆ
        """
        from sqlalchemy.types import Text as SA_Text
        
        schema_issues = []
        
        try:
            with self.engine.connect() as conn:
                # ดึงข้อมูล schema ของตารางปลายทาง (ถ้ามี)
                final_table = staging_table.replace('_staging', '')
                table_info_query = f"""
                    SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, COLLATION_NAME
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = '{schema_name}' 
                    AND TABLE_NAME = '{final_table}'
                """
                
                result = conn.execute(text(table_info_query))
                db_columns = {row.COLUMN_NAME: {
                    'data_type': row.DATA_TYPE,
                    'max_length': row.CHARACTER_MAXIMUM_LENGTH,
                    'collation': row.COLLATION_NAME
                } for row in result.fetchall()}
                
                # ตรวจสอบ schema mismatch สำหรับแต่ละคอลัมน์
                for col_name, expected_dtype in required_cols.items():
                    if col_name in db_columns:
                        db_info = db_columns[col_name]
                        
                        # ตรวจสอบ Text (NVARCHAR(MAX)) vs NVARCHAR ธรรมดา
                        if isinstance(expected_dtype, SA_Text):
                            if db_info['data_type'] == 'nvarchar' and db_info['max_length'] != -1:
                                # NVARCHAR(MAX) in SQL Server has max_length = -1
                                issue = {
                                    'validation_type': 'schema_mismatch',
                                    'column': col_name,
                                    'error_count': 0,  # not an error, informational warning
                                    'percentage': 0,
                                    'message': f"Configured as NVARCHAR(MAX) but database column is NVARCHAR({db_info['max_length'] or 'Unknown'})",
                                    'recommendation': "Data will be saved, but may be truncated if it exceeds column length",
                                    'severity': 'info'
                                }
                                
                                schema_issues.append(issue)
                                
                                if log_func:
                                    log_func(f"   ⚠️  {col_name}: {issue['message']}")
                                    log_func(f"      ℹ️  {issue['recommendation']}")
        
        except Exception as e:
            if log_func:
                log_func(f"⚠️ Unable to check schema mismatch: {e}")
        
        return schema_issues
