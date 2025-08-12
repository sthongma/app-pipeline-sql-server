"""
Data Upload Service for PIPELINE_SQLSERVER

Handles data upload operations to database
"""

import json
import logging
from datetime import datetime
from typing import Dict

import pandas as pd
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.types import (
    DateTime,
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

from .data_validation_service import DataValidationService


class DataUploadService:
    """
    Data upload service for database operations
    
    Handles staging, validation, and final data upload
    """
    
    def __init__(self, engine, schema_service, validation_service: DataValidationService = None) -> None:
        """
        Initialize DataUploadService
        
        Args:
            engine: SQLAlchemy engine instance
            schema_service: Schema service instance
            validation_service: Data validation service instance
        """
        self.engine = engine
        self.schema_service = schema_service
        self.validation_service = validation_service or DataValidationService(engine)
        self.logger = logging.getLogger(__name__)

    def upload_data(self, df, logic_type: str, required_cols: Dict, schema_name: str = 'bronze', 
                   log_func=None, force_recreate: bool = False, clear_existing: bool = True):
        """
        Upload data to database: create table from config, insert only configured columns,
        if database schema doesn't match, drop and recreate table
        
        Args:
            df: DataFrame to upload
            logic_type: File type
            required_cols: Required columns and data types
            schema_name: Database schema name
            log_func: Function for logging
            force_recreate: Force table recreation (used when auto-updating data types)
            clear_existing: Whether to clear existing data (default True for backwards compatibility)
        """
        
        if log_func:
            log_func("✅ Database access permissions are correct")
        
        try:
            if df is None or df.empty:
                return False, "Empty data"
            
            if not required_cols:
                return False, "Data type settings not found"
            
            current_time = datetime.now()
            df['updated_at'] = current_time
            
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

            schema_result = self.schema_service.ensure_schemas_exist([schema_name])
            if not schema_result[0]:
                return False, f"Could not create schema: {schema_result[1]}"

            insp = inspect(self.engine)
            needs_recreate = force_recreate
            
            if insp.has_table(table_name, schema=schema_name) and not force_recreate:
                db_cols = [col['name'] for col in insp.get_columns(table_name, schema=schema_name)]
                db_col_types = {col['name']: str(col['type']).upper() for col in insp.get_columns(table_name, schema=schema_name)}
                config_cols = list(required_cols.keys())
                
                if set(db_cols) != set(config_cols):
                    msg = f"❌ Table {schema_name}.{table_name} columns do not match config"
                    needs_recreate = True
                else:
                    needs_recreate = self._check_type_compatibility(db_col_types, required_cols, log_func)
            
            staging_table = f"{table_name}__stg"
            staging_cols = list(required_cols.keys())
            
            self._create_staging_table(staging_table, staging_cols, schema_name, log_func)
            
            self._upload_to_staging(df, staging_table, staging_cols, schema_name, log_func)
            
            validation_results = self.validation_service.validate_data_in_staging(
                staging_table, logic_type, required_cols, schema_name, log_func
            )
            
            if not validation_results['is_valid']:
                with self.engine.begin() as conn:
                    conn.execute(text(f"DROP TABLE {schema_name}.{staging_table}"))
                return False, validation_results['summary']
            
            self._create_or_recreate_final_table(
                table_name, required_cols, schema_name, needs_recreate, log_func, df, clear_existing
            )
            
            self._transfer_data_from_staging(
                staging_table, table_name, required_cols, schema_name, log_func
            )
            
            with self.engine.begin() as conn:
                conn.execute(text(f"DROP TABLE {schema_name}.{staging_table}"))
                if log_func:
                    log_func(f"🗑️ Dropped staging table {schema_name}.{staging_table}")

            return True, f"Upload successful → {schema_name}.{table_name} (ingested NVARCHAR(MAX) then converted by dtype for {len(df):,} rows)"
        
        except Exception as e:
            short_msg = self._short_exception_message(e)
            problem_hints = self._detect_problem_columns(df, required_cols)

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

    def _fix_text_columns_to_nvarchar_max(self, table_name: str, required_cols: Dict, 
                                        schema_name: str = 'bronze', log_func=None):
        """Fix Text() columns to NVARCHAR(MAX) in SQL Server"""
        try:
            with self.engine.begin() as conn:
                for col_name, dtype in required_cols.items():
                    if isinstance(dtype, SA_Text):
                        alter_sql = f"ALTER TABLE {schema_name}.{table_name} ALTER COLUMN [{col_name}] NVARCHAR(MAX)"
                        if log_func:
                            log_func(f"🔧 Alter column '{col_name}' to NVARCHAR(MAX)")
                        conn.execute(text(alter_sql))
        except Exception as e:
            if log_func:
                log_func(f"⚠️ Unable to alter Text() column: {e}")

    def _check_type_compatibility(self, db_col_types: Dict, required_cols: Dict, log_func=None) -> bool:
        """Check if database column types are compatible with required types"""
        needs_recreate = False
        
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
            s = str(sa_type_obj).upper()
            if isinstance(sa_type_obj, SA_Text):
                return 'NVARCHAR(MAX)'
            return s

        def _parse_varchar_len(type_str: str) -> int:
            try:
                if 'MAX' in type_str.upper():
                    return 2_147_483_647
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

            if isinstance(expected_dtype, SA_Text):
                if 'NVARCHAR(MAX)' not in db_type and 'TEXT' not in db_type and 'NVARCHAR' not in db_type:
                    if log_func:
                        log_func(f"❌ Schema Mismatch: Column '{col_name}' should be NVARCHAR(MAX) but database has {db_type}")
                        log_func(f"   💡 Suggestion: Allow system to create new table to fix this issue")
                    needs_recreate = True
                    break

            if cat_db != cat_expected:
                if log_func:
                    log_func(f"❌ Data type mismatch for column '{col_name}' (DB: {db_type} | Expected: {expected_str})")
                needs_recreate = True
                break

            if cat_expected == 'STRING' and 'NVARCHAR' in expected_str:
                exp_len = _parse_varchar_len(expected_str)
                act_len = _parse_varchar_len(db_type)
                if act_len != -1 and exp_len != -1 and act_len < exp_len:
                    if log_func:
                        log_func(f"❌ NVARCHAR length for '{col_name}' is insufficient (DB: {db_type} | Expected: {expected_str})")
                    needs_recreate = True
                    break
                    
        return needs_recreate

    def _create_staging_table(self, staging_table: str, staging_cols: list, schema_name: str, log_func=None):
        """Create staging table with NVARCHAR(MAX) for all columns"""
        with self.engine.begin() as conn:
            conn.execute(text(f"""
                IF OBJECT_ID('{schema_name}.{staging_table}', 'U') IS NOT NULL
                    DROP TABLE {schema_name}.{staging_table};
            """))
            cols_sql = ", ".join([f"[{c}] NVARCHAR(MAX) NULL" for c in staging_cols])
            conn.execute(text(f"CREATE TABLE {schema_name}.{staging_table} ({cols_sql})"))
            if log_func:
                log_func(f"📦 Created staging table: {schema_name}.{staging_table} (NVARCHAR(MAX) for all columns)")

    def _upload_to_staging(self, df, staging_table: str, staging_cols: list, schema_name: str, log_func=None):
        """Upload data to staging table"""
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

    def _create_or_recreate_final_table(self, table_name: str, required_cols: Dict, schema_name: str, 
                                      needs_recreate: bool, log_func, df, clear_existing: bool = True):
        """Create or recreate final table based on dtype config"""
        insp = inspect(self.engine)
        
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
            self._fix_text_columns_to_nvarchar_max(table_name, required_cols, schema_name, log_func)
        else:
            if clear_existing:
                if log_func:
                    log_func(f"🧹 Truncating existing data in table {schema_name}.{table_name}")
                with self.engine.begin() as conn:
                    conn.execute(text(f"TRUNCATE TABLE {schema_name}.{table_name}"))
            else:
                if log_func:
                    log_func(f"📋 Appending to existing table {schema_name}.{table_name}")

    def _transfer_data_from_staging(self, staging_table: str, table_name: str, required_cols: Dict, 
                                  schema_name: str, log_func=None):
        """Transfer data from staging to final table with type conversion"""
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

    def _short_exception_message(self, exc: Exception) -> str:
        """Extract short exception message"""
        try:
            if isinstance(exc, DBAPIError) and getattr(exc, "orig", None):
                orig = exc.orig
                parts = [str(p) for p in getattr(orig, "args", []) if p]
                core = parts[-1] if parts else str(exc)
            else:
                core = str(exc)
            for token in ["[SQL:", "[parameters:"]:
                if token in core:
                    core = core.split(token)[0].strip()
            core = core.splitlines()[0]
            return core
        except Exception:
            return str(exc)

    def _detect_problem_columns(self, df_local, required_map, max_cols: int = 5, max_examples: int = 3):
        """Detect problematic columns in data"""
        problems = []
        try:
            for col, dtype in required_map.items():
                if col not in df_local.columns:
                    continue
                
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
                
                if len(problems) >= max_cols:
                    break
        except Exception:
            pass
        return problems