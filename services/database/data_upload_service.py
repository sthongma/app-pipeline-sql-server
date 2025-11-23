"""
Data Upload Service for PIPELINE_SQLSERVER

Handles data upload operations to database
"""

import json
import logging
from datetime import datetime
from typing import Dict
import uuid

import pandas as pd
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError

from services.settings_manager import settings_manager
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
    LargeBinary,
)

from .data_validation_service import DataValidationService
from utils.sql_utils import get_numeric_cleaning_expression, get_basic_cleaning_expression


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

        # โหลดการตั้งค่าประเภทข้อมูล
        self.dtype_settings = {}
        self._load_dtype_settings()

    def _load_dtype_settings(self):
        """Load data type settings from settings_manager"""
        try:
            # Load all file types from settings_manager
            self.dtype_settings = {}
            file_types = settings_manager.list_file_types()
            for file_type in file_types:
                self.dtype_settings[file_type] = settings_manager.get_dtype_settings(file_type)
        except Exception as e:
            self.logger.warning(f"ไม่สามารถโหลด dtype_settings ได้: {e}")
            self.dtype_settings = {}

    def upload_data(self, df, logic_type: str, required_cols: Dict, schema_name: str = 'bronze',
                   log_func=None, force_recreate: bool = False, clear_existing: bool = True, source_file: str = None):
        """
        Upload data to database with support for Replace or Upsert strategies

        Args:
            df: DataFrame to upload
            logic_type: File type
            required_cols: Required columns and data types
            schema_name: Database schema name
            log_func: Function for logging
            force_recreate: Force table recreation (used when auto-updating data types)
            clear_existing: Whether to clear existing data (ignored if update_strategy='upsert')
            source_file: Source filename for metadata tracking
        """

        # โหลด dtype_settings ใหม่ทุกครั้งเพื่อให้ได้ค่าล่าสุดหลัง Save
        self._load_dtype_settings()

        # สร้าง batch_id สำหรับการ upload ครั้งนี้
        batch_id = str(uuid.uuid4())

        # อ่าน update strategy และ upsert keys
        update_strategy = "replace"  # default
        upsert_keys = []

        if logic_type in self.dtype_settings:
            update_strategy = self.dtype_settings[logic_type].get(
                '_update_strategy', 'replace'
            )
            upsert_keys = self.dtype_settings[logic_type].get(
                '_upsert_keys', []
            )

        if log_func:
            log_func("✅ Database access permissions are correct")
            strategy_name = "Upsert (Incremental)" if update_strategy == "upsert" else "Replace (Full)"
            log_func(f"📋 Update Strategy: {strategy_name}")
            if update_strategy == "upsert" and upsert_keys:
                log_func(f"🔑 Upsert Keys: {', '.join(upsert_keys)}")
        
        try:
            if df is None or df.empty:
                return False, "Empty data"
            
            if not required_cols:
                return False, "Data type settings not found"

            # เพิ่ม metadata columns ที่จะถูกเพิ่มโดย SQL ในขั้นตอนสุดท้าย
            required_cols['_loaded_at'] = DateTime()
            required_cols['_created_at'] = DateTime()
            required_cols['_source_file'] = SA_NVARCHAR(500)
            required_cols['_batch_id'] = SA_NVARCHAR(50)
            required_cols['_upsert_hash'] = LargeBinary(16)
            
            table_name = None
            try:
                # Load column settings from settings_manager for this specific file type
                col_config = settings_manager.get_column_settings(logic_type)
                # Check if there's a custom table name mapping in the settings
                # Note: Using logic_type as table name if not specified
                if isinstance(col_config, dict):
                    table_name = col_config.get("__table_name__")
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
            # staging table ไม่รวม metadata columns เพราะจะเพิ่มใน SQL ตอน transfer
            metadata_cols = {'_loaded_at', '_created_at', '_source_file', '_batch_id', '_upsert_hash'}
            staging_cols = [col for col in required_cols.keys() if col not in metadata_cols]
            
            if log_func:
                log_func(f"📋 Creating staging table {schema_name}.{staging_table}")
            self._create_staging_table(staging_table, staging_cols, schema_name, log_func)

            # เพิ่ม metadata columns ลง DataFrame ก่อน upload เข้า staging
            df_with_metadata = df.copy()
            df_with_metadata['_loaded_at'] = datetime.now()
            df_with_metadata['_created_at'] = datetime.now()
            df_with_metadata['_source_file'] = source_file or 'unknown'
            df_with_metadata['_batch_id'] = batch_id
            df_with_metadata['_upsert_hash'] = None  # จะคำนวณทีหลังถ้าเป็น upsert mode

            if log_func:
                log_func(f"📤 Uploading {len(df):,} rows to staging table (with metadata)")
            self._upload_to_staging(df_with_metadata, staging_table, staging_cols, schema_name, log_func)
            
            # โหลดการตั้งค่า date format
            date_format = 'UK'  # default
            try:
                if logic_type in self.dtype_settings:
                    date_format = self.dtype_settings[logic_type].get('_date_format', 'UK')
                    if log_func:
                        log_func(f"📅 Using Date Format: {date_format}")
            except Exception as e:
                if log_func:
                    log_func(f"⚠️ Could not load date format: {e}")
            
            if log_func:
                log_func(f"🔍 Validating data in staging table")
            validation_results = self.validation_service.validate_data_in_staging(
                staging_table, logic_type, required_cols, schema_name, log_func, 
                progress_callback=None, date_format=date_format
            )
            
            if not validation_results['is_valid']:
                with self.engine.begin() as conn:
                    conn.execute(text(f"DROP TABLE {schema_name}.{staging_table}"))
                # ส่ง validation details กลับมาด้วยในรูปแบบ dict
                return False, {
                    'summary': validation_results['summary'],
                    'issues': validation_results.get('issues', []),
                    'warnings': validation_results.get('warnings', [])
                }
            
            self._create_or_recreate_final_table(
                table_name, required_cols, schema_name, needs_recreate, log_func, df,
                clear_existing, update_strategy, upsert_keys
            )
            
            if log_func:
                log_func(f"🔄 Transferring data from staging to main table {schema_name}.{table_name}")
            self._transfer_data_from_staging(
                staging_table, table_name, required_cols, schema_name, log_func, date_format,
                batch_id=batch_id, source_file=source_file, upsert_keys=upsert_keys,
                update_strategy=update_strategy
            )

            # Keep staging table for debugging - it will be cleaned up when new data comes
            if log_func:
                log_func(f"✅ Keeping staging table {schema_name}.{staging_table} for debugging")

            # Create indexes after successful upload
            if log_func:
                log_func(f"🔍 Creating indexes on final table")
            self._create_indexes_after_upload(
                table_name, schema_name, upsert_keys, log_func
            )

            # Build summary message
            summary_message = f"Upload successful → {schema_name}.{table_name} (ingested NVARCHAR(MAX) then converted by dtype for {len(df):,} rows)"

            return True, summary_message
        
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

    def _fix_column_types(self, table_name: str, required_cols: Dict, 
                         schema_name: str = 'bronze', log_func=None):
        """Fix column types to match required types for all data types"""
        try:
            with self.engine.begin() as conn:
                # ตรวจสอบชนิดข้อมูลปัจจุบันในฐานข้อมูล
                check_query = f"""
                    SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, NUMERIC_SCALE
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = '{schema_name}' 
                    AND TABLE_NAME = '{table_name}'
                """
                result = conn.execute(text(check_query))
                current_columns = {row.COLUMN_NAME: {
                    'data_type': row.DATA_TYPE,
                    'max_length': row.CHARACTER_MAXIMUM_LENGTH,
                    'precision': row.NUMERIC_PRECISION,
                    'scale': row.NUMERIC_SCALE
                } for row in result.fetchall()}
                
                for col_name, dtype in required_cols.items():
                    if col_name not in current_columns:
                        continue
                        
                    current_col = current_columns[col_name]
                    target_sql_type = self._get_sql_server_type(dtype)
                    current_type_str = self._format_current_type(current_col)
                    
                    # เปรียบเทียบชนิดข้อมูล ถ้าเหมือนกันก็ข้าม
                    if self._types_are_equivalent(current_type_str, target_sql_type, dtype):
                        continue
                    
                    # มีการเปลี่ยนแปลง ต้อง ALTER
                    alter_sql = f"ALTER TABLE {schema_name}.{table_name} ALTER COLUMN [{col_name}] {target_sql_type}"
                    if log_func:
                        log_func(f"🔧 ALTER column '{col_name}': {current_type_str} → {target_sql_type}")
                    conn.execute(text(alter_sql))
                    
        except Exception as e:
            if log_func:
                log_func(f"⚠️ Unable to alter column types: {e}")
    
    def _get_sql_server_type(self, sa_type) -> str:
        """Convert SQLAlchemy type to SQL Server type string"""
        if isinstance(sa_type, (SA_Text, SA_NVARCHAR)):
            # Always use NVARCHAR(MAX) for all string types
            return "NVARCHAR(MAX)"
        elif isinstance(sa_type, SA_Integer):
            return "INT"
        elif isinstance(sa_type, SA_SmallInteger):
            return "SMALLINT"
        elif isinstance(sa_type, SA_Float):
            return "FLOAT"
        elif isinstance(sa_type, SA_DECIMAL):
            if hasattr(sa_type, 'precision') and hasattr(sa_type, 'scale'):
                precision = sa_type.precision or 18
                scale = sa_type.scale or 0
                return f"DECIMAL({precision},{scale})"
            else:
                return "DECIMAL(18,0)"
        elif isinstance(sa_type, SA_DATE):
            return "DATE"
        elif isinstance(sa_type, SA_DateTime):
            return "DATETIME2"
        elif isinstance(sa_type, SA_Boolean):
            return "BIT"
        elif isinstance(sa_type, LargeBinary):
            return "VARBINARY(16)"  # For _upsert_hash
        else:
            return "NVARCHAR(MAX)"  # Default fallback
    
    def _format_current_type(self, col_info: Dict) -> str:
        """Format current column info to readable type string"""
        data_type = col_info['data_type'].upper()

        if data_type in ['NVARCHAR', 'VARCHAR']:
            if col_info['max_length'] == -1:
                return f"{data_type}(MAX)"
            elif col_info['max_length']:
                return f"{data_type}({col_info['max_length']})"
            else:
                return data_type
        elif data_type in ['VARBINARY', 'BINARY']:
            if col_info['max_length'] == -1:
                return f"{data_type}(MAX)"
            elif col_info['max_length']:
                return f"{data_type}({col_info['max_length']})"
            else:
                return data_type
        elif data_type in ['DECIMAL', 'NUMERIC']:
            precision = col_info['precision'] or 18
            scale = col_info['scale'] or 0
            return f"{data_type}({precision},{scale})"
        else:
            return data_type
    
    def _types_are_equivalent(self, current_type: str, target_type: str, sa_type) -> bool:
        """Check if current and target types are equivalent"""
        current_upper = current_type.upper()
        target_upper = target_type.upper()

        # ตรวจสอบความเท่าเทียมแบบเข้มงวด
        if current_upper == target_upper:
            return True

        # ตรวจสอบความเท่าเทียมสำหรับ NVARCHAR(MAX)
        if isinstance(sa_type, SA_Text):
            return current_upper in ['NVARCHAR(MAX)', 'TEXT', 'NTEXT']

        # ตรวจสอบความเท่าเทียมสำหรับ DATETIME
        if isinstance(sa_type, SA_DateTime):
            return current_upper in ['DATETIME', 'DATETIME2', 'SMALLDATETIME']

        # ตรวจสอบความเท่าเทียมสำหรับ VARBINARY (สำหรับ _upsert_hash)
        if isinstance(sa_type, LargeBinary):
            # VARBINARY(16) = VARBINARY(16) or just VARBINARY
            return current_upper.startswith('VARBINARY') or current_upper.startswith('BINARY')

        return False

    def _check_type_compatibility(self, db_col_types: Dict, required_cols: Dict, log_func=None) -> bool:
        """Check if database column types are compatible with required types - Now more permissive for ALTER operations"""
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

        def _can_alter_type(from_cat: str, to_cat: str) -> bool:
            """Check if type can be ALTERed instead of requiring table recreation"""
            # อนุญาต ALTER สำหรับการเปลี่ยนแปลงเหล่านี้
            alterable_changes = [
                ('STRING', 'STRING'),    # VARCHAR → NVARCHAR, size changes, etc.
                ('NUMERIC', 'NUMERIC'),  # INT → BIGINT, DECIMAL changes, etc.
                ('DATETIME', 'DATETIME'), # DATETIME → DATETIME2, etc.
                ('BOOLEAN', 'BOOLEAN'),  # BIT changes
            ]
            return (from_cat, to_cat) in alterable_changes

        for col_name, expected_dtype in required_cols.items():
            db_type = db_col_types.get(col_name, '')
            expected_str = _expected_type_str(expected_dtype)
            cat_db = _type_category(db_type)
            cat_expected = _type_category(expected_str)

            # ตรวจสอบว่าสามารถ ALTER ได้หรือต้อง recreate table
            if cat_db != cat_expected and not _can_alter_type(cat_db, cat_expected):
                if log_func:
                    log_func(f"❌ Data type mismatch for column '{col_name}' (DB: {db_type} | Expected: {expected_str})")
                needs_recreate = True
                break

            # เอาเงื่อนไข NVARCHAR length ออก เพราะ _fix_column_types() จะจัดการให้
                    
        return needs_recreate

    def _create_staging_table(self, staging_table: str, staging_cols: list, schema_name: str, log_func=None):
        """Create staging table with NVARCHAR(MAX) for business columns and metadata columns"""
        with self.engine.begin() as conn:
            conn.execute(text(f"""
                IF OBJECT_ID('{schema_name}.{staging_table}', 'U') IS NOT NULL
                    DROP TABLE {schema_name}.{staging_table};
            """))
            # Business columns: NVARCHAR(MAX)
            cols_sql = ", ".join([f"[{c}] NVARCHAR(MAX) NULL" for c in staging_cols])

            # Add metadata columns with proper data types
            metadata_cols_sql = """
                [_loaded_at] DATETIME2 NULL,
                [_created_at] DATETIME2 NULL,
                [_source_file] NVARCHAR(500) NULL,
                [_batch_id] NVARCHAR(50) NULL,
                [_upsert_hash] VARBINARY(16) NULL
            """

            # Combine all columns
            all_cols_sql = cols_sql + ", " + metadata_cols_sql

            conn.execute(text(f"CREATE TABLE {schema_name}.{staging_table} ({all_cols_sql})"))
            if log_func:
                log_func(f"📦 Created staging table: {schema_name}.{staging_table} (business cols + metadata cols)")

    def _upload_to_staging(self, df, staging_table: str, staging_cols: list, schema_name: str, log_func=None):
        """Upload data to staging table (including metadata columns)"""
        # รวมคอลัมน์ธุรกิจและ metadata columns
        metadata_cols = ['_loaded_at', '_created_at', '_source_file', '_batch_id', '_upsert_hash']
        all_cols = list(staging_cols) + metadata_cols

        if len(df) > 10000:
            if log_func:
                log_func(f"📊 Large file ({len(df):,} rows) - uploading in chunks to staging")
            chunk_size = 5000
            total_chunks = (len(df) + chunk_size - 1) // chunk_size
            for i in range(0, len(df), chunk_size):
                chunk = df.iloc[i:i+chunk_size]
                chunk[all_cols].to_sql(
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
            df[all_cols].to_sql(
                name=staging_table,
                con=self.engine,
                schema=schema_name,
                if_exists='append',
                index=False
            )

    def _delete_by_keys(self, staging_table: str, final_table: str,
                       upsert_keys: list, schema_name: str, log_func=None):
        """
        Delete rows in final table where upsert hash matches staging table

        Uses MD5 hash of cleaned upsert keys for fast and accurate matching.
        This is more reliable than matching on raw values as it uses cleaned data.

        Args:
            staging_table: Staging table name
            final_table: Final table name
            upsert_keys: List of column names to match on
            schema_name: Database schema
            log_func: Logging function

        Example SQL:
            DELETE T FROM bronze.orders T
            INNER JOIN bronze.orders__stg S
            ON T._upsert_hash = S._upsert_hash
            WHERE S._upsert_hash IS NOT NULL
        """
        if not upsert_keys:
            if log_func:
                log_func("⚠️ No upsert keys specified, skipping delete")
            return

        # Validate upsert keys exist in staging table
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"""
                    SELECT COLUMN_NAME
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = '{schema_name}'
                    AND TABLE_NAME = '{staging_table}'
                """))
                available_cols = {row[0] for row in result}

                missing_keys = set(upsert_keys) - available_cols
                if missing_keys:
                    raise ValueError(f"Upsert keys not found in table: {missing_keys}")

                # Check for NULL values in upsert keys
                for key in upsert_keys:
                    result = conn.execute(text(f"""
                        SELECT COUNT(*)
                        FROM {schema_name}.{staging_table}
                        WHERE [{key}] IS NULL
                    """))
                    null_count = result.scalar()
                    if null_count > 0:
                        raise ValueError(
                            f"Upsert key '{key}' contains {null_count} NULL values. "
                            f"All upsert keys must be non-NULL."
                        )
        except Exception as e:
            if log_func:
                log_func(f"❌ Validation failed: {e}")
            raise

        # Staging table มี _upsert_hash column อยู่แล้ว (สร้างตอน create table)
        # เพียงแค่คำนวณ hash และ DELETE
        with self.engine.begin() as conn:
            try:
                # Calculate and populate _upsert_hash in staging table
                cleaned_keys = []
                for key in upsert_keys:
                    cleaned = get_basic_cleaning_expression(key)
                    cleaned_keys.append(f"COALESCE({cleaned}, '')")

                concat_expr = " + '|' + ".join(cleaned_keys)
                hash_expr = f"HASHBYTES('MD5', {concat_expr})"

                update_sql = f"""
                    UPDATE {schema_name}.{staging_table}
                    SET [_upsert_hash] = {hash_expr}
                """
                conn.execute(text(update_sql))

                # Now perform DELETE using _upsert_hash
                delete_sql = f"""
                    DELETE T
                    FROM {schema_name}.{final_table} T
                    INNER JOIN {schema_name}.{staging_table} S
                    ON T.[_upsert_hash] = S.[_upsert_hash]
                    WHERE S.[_upsert_hash] IS NOT NULL
                """

                if log_func:
                    keys_str = ", ".join(upsert_keys)
                    log_func(f"🗑️ Deleting existing rows using MD5 hash of keys: {keys_str}")

                result = conn.execute(text(delete_sql))
                deleted_count = result.rowcount

                if log_func:
                    log_func(f"✅ Deleted {deleted_count:,} existing rows")

            except Exception as e:
                if log_func:
                    log_func(f"❌ Delete failed: {e}")
                raise

    def _create_or_recreate_final_table(self, table_name: str, required_cols: Dict, schema_name: str,
                                      needs_recreate: bool, log_func, df, clear_existing: bool = True,
                                      update_strategy: str = "replace", upsert_keys: list = None):
        """
        Create or recreate final table based on dtype config

        Now supports two strategies:
        - replace: TRUNCATE table before INSERT (default)
        - upsert: DELETE matching keys, then INSERT

        Args:
            table_name: Name of the final table
            required_cols: Required columns and their data types
            schema_name: Database schema name
            needs_recreate: Whether to recreate the table
            log_func: Logging function
            df: DataFrame being uploaded
            clear_existing: Whether to clear existing data (ignored if update_strategy='upsert')
            update_strategy: 'replace' or 'upsert'
            upsert_keys: List of columns to use as keys for upsert (required if update_strategy='upsert')
        """
        upsert_keys = upsert_keys or []
        insp = inspect(self.engine)

        if needs_recreate or not insp.has_table(table_name, schema=schema_name):
            if needs_recreate and log_func:
                log_func(f"🛠️ Creating table {schema_name}.{table_name} to match data type settings")
            elif log_func:
                log_func(f"📋 Creating table {schema_name}.{table_name} from data type settings")

            # สร้าง empty DataFrame ที่มีเฉพาะคอลัมน์ที่มีอยู่ใน df (ไม่รวม metadata columns)
            metadata_cols = {'_loaded_at', '_created_at', '_source_file', '_batch_id', '_upsert_hash'}
            df_cols = [col for col in required_cols.keys() if col not in metadata_cols]
            df.head(0)[df_cols].to_sql(
                name=table_name,
                con=self.engine,
                schema=schema_name,
                if_exists='replace',
                index=False,
                dtype={col: required_cols[col] for col in df_cols}
            )
            # เพิ่ม metadata columns ด้วย SQL
            with self.engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {schema_name}.{table_name} ADD [_loaded_at] DATETIME2 NULL"))
                conn.execute(text(f"ALTER TABLE {schema_name}.{table_name} ADD [_created_at] DATETIME2 NULL"))
                conn.execute(text(f"ALTER TABLE {schema_name}.{table_name} ADD [_source_file] NVARCHAR(500) NULL"))
                conn.execute(text(f"ALTER TABLE {schema_name}.{table_name} ADD [_batch_id] NVARCHAR(50) NULL"))
                conn.execute(text(f"ALTER TABLE {schema_name}.{table_name} ADD [_upsert_hash] VARBINARY(16) NULL"))
        else:
            # แก้ไขชนิดข้อมูลสำหรับตารางที่มีอยู่แล้ว
            self._fix_column_types(table_name, required_cols, schema_name, log_func)

            # เลือก strategy
            if update_strategy == "upsert":
                # Incremental: DELETE by keys
                staging_table = f"{table_name}__stg"
                self._delete_by_keys(
                    staging_table, table_name, upsert_keys, schema_name, log_func
                )
            elif clear_existing:
                # Replace: TRUNCATE table
                if log_func:
                    log_func(f"🧹 Truncating existing data in table {schema_name}.{table_name}")
                with self.engine.begin() as conn:
                    conn.execute(text(f"TRUNCATE TABLE {schema_name}.{table_name}"))
            else:
                # Append mode
                if log_func:
                    log_func(f"📋 Appending to existing table {schema_name}.{table_name}")

    def _transfer_data_from_staging(self, staging_table: str, table_name: str, required_cols: Dict,
                                  schema_name: str, log_func=None, date_format: str = 'UK',
                                  batch_id: str = None, source_file: str = None, upsert_keys: list = None,
                                  update_strategy: str = 'replace'):
        """Transfer data from staging to final table with type conversion and metadata

        Args:
            staging_table: Staging table name
            table_name: Final table name
            required_cols: Required columns and data types
            schema_name: Database schema
            log_func: Logging function
            date_format: Date format for conversion
            batch_id: Batch ID for this upload
            source_file: Source filename
            upsert_keys: List of upsert key columns
            update_strategy: 'replace' or 'upsert'

        Returns:
            None
        """

        # Get row count for progress monitoring
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {schema_name}.{staging_table}"))
                total_rows = result.scalar()
                if log_func:
                    log_func(f"📊 Preparing to transfer {total_rows:,} rows with type conversion")
        except Exception as e:
            if log_func:
                log_func(f"⚠️ Could not get row count: {e}")
            total_rows = "unknown"
        def _sql_type_and_expr(col_name: str, sa_type_obj) -> str:
            col_ref = f"[{col_name}]"
            # Basic cleaning for most data types
            base = f"NULLIF(LTRIM(RTRIM({col_ref})), '')"
            
            if isinstance(sa_type_obj, (SA_Integer, SA_SmallInteger)):
                # Use shared numeric cleaning function for consistency
                cleaned = get_numeric_cleaning_expression(col_name)
                return f"TRY_CONVERT(INT, {cleaned})"
            if isinstance(sa_type_obj, SA_Float):
                # Use shared numeric cleaning function for consistency
                cleaned = get_numeric_cleaning_expression(col_name)
                return f"TRY_CONVERT(FLOAT, {cleaned})"
            if isinstance(sa_type_obj, SA_DECIMAL):
                precision = getattr(sa_type_obj, 'precision', 18) or 18
                scale = getattr(sa_type_obj, 'scale', 2) or 2
                # Use shared numeric cleaning function for consistency
                cleaned = get_numeric_cleaning_expression(col_name)
                return f"TRY_CONVERT(DECIMAL({precision},{scale}), {cleaned})"
            if isinstance(sa_type_obj, (SA_DATE, SA_DateTime)):
                # Enhanced date cleaning to handle tab characters and special characters
                date_cleaned = f"NULLIF(LTRIM(RTRIM(REPLACE(REPLACE(REPLACE({col_ref}, CHAR(9), ''), CHAR(10), ''), CHAR(13), ''))), '')"
                
                if date_format == 'UK':  # DD-MM format priority
                    return f"COALESCE(TRY_CONVERT(DATETIME, {date_cleaned}, 103), TRY_CONVERT(DATETIME, {date_cleaned}, 121), TRY_CONVERT(DATETIME, {date_cleaned}, 101))"
                else:  # US format - MM-DD priority
                    return f"COALESCE(TRY_CONVERT(DATETIME, {date_cleaned}, 101), TRY_CONVERT(DATETIME, {date_cleaned}, 121), TRY_CONVERT(DATETIME, {date_cleaned}, 103))"
            if isinstance(sa_type_obj, SA_Boolean):
                return (
                    "CASE "
                    f"WHEN UPPER(LTRIM(RTRIM({col_ref}))) IN ('1','TRUE','Y','YES') THEN 1 "
                    f"WHEN UPPER(LTRIM(RTRIM({col_ref}))) IN ('0','FALSE','N','NO') THEN 0 "
                    "ELSE NULL END"
                )
            target = 'NVARCHAR(MAX)' if isinstance(sa_type_obj, SA_Text) else str(sa_type_obj).upper()
            return f"TRY_CONVERT({target}, {col_ref})"

        # Build SELECT expressions
        # Metadata columns: เอาจาก staging table โดยตรง (สร้างไว้แล้วตอน upload)
        # Business columns: แปลง data type ด้วย TRY_CONVERT
        metadata_cols = {'_loaded_at', '_created_at', '_source_file', '_batch_id', '_upsert_hash'}
        select_exprs = []
        for col_name, sa_type in required_cols.items():
            if col_name in metadata_cols:
                # Metadata columns: เอาจาก staging table โดยตรง (ไม่ต้องคำนวณใหม่)
                select_exprs.append(f"[{col_name}]")
            else:
                # Business columns: แปลง data type
                select_exprs.append(f"{_sql_type_and_expr(col_name, sa_type)} AS [{col_name}]")
        select_sql = ", ".join(select_exprs)

        with self.engine.begin() as conn:
            insert_sql = (
                f"INSERT INTO {schema_name}.{table_name} (" + ", ".join([f"[{c}]" for c in required_cols.keys()]) + ") "
                f"SELECT {select_sql} FROM {schema_name}.{staging_table}"
            )
            if log_func:
                log_func(f"📝 Executing data transfer with type conversion...")
                log_func(f"⏳ This may take a while for large datasets, please wait...")

            # Execute with timeout monitoring
            import time
            start_time = time.time()
            try:
                result = conn.execute(text(insert_sql))
                execution_time = time.time() - start_time

                # Count inserted rows
                count_result = conn.execute(text(f"SELECT COUNT(*) FROM {schema_name}.{table_name}"))
                inserted_rows = count_result.scalar()

                if log_func:
                    log_func(f"✅ Data transfer completed successfully in {execution_time:.1f} seconds")
                    log_func(f"📊 Inserted {inserted_rows:,} rows")

                return None

            except Exception as e:
                execution_time = time.time() - start_time
                if log_func:
                    log_func(f"❌ Data transfer failed after {execution_time:.1f} seconds: {str(e)[:100]}...")
                raise

    def _create_indexes_after_upload(self, table_name: str, schema_name: str,
                                    upsert_keys: list = None, log_func=None):
        """Create indexes on final table after upload

        Creates indexes on:
        - _upsert_hash (for fast upsert operations)
        - _loaded_at (for querying by load date)
        - Individual upsert key columns (if specified)

        Args:
            table_name: Final table name
            schema_name: Database schema
            upsert_keys: List of upsert key columns
            log_func: Logging function
        """
        upsert_keys = upsert_keys or []

        try:
            with self.engine.begin() as conn:
                # Index 1: _upsert_hash (for fast upsert matching)
                idx_upsert_hash = f"IX_{table_name}_upsert_hash"
                create_idx_upsert = f"""
                IF NOT EXISTS (SELECT * FROM sys.indexes
                              WHERE name = '{idx_upsert_hash}'
                              AND object_id = OBJECT_ID('{schema_name}.{table_name}'))
                BEGIN
                    CREATE NONCLUSTERED INDEX [{idx_upsert_hash}]
                    ON {schema_name}.{table_name} ([_upsert_hash])
                END
                """
                conn.execute(text(create_idx_upsert))
                if log_func:
                    log_func(f"✅ Created index on _upsert_hash")

                # Index 2: _loaded_at (for querying by load date)
                idx_loaded_at = f"IX_{table_name}_loaded_at"
                create_idx_loaded = f"""
                IF NOT EXISTS (SELECT * FROM sys.indexes
                              WHERE name = '{idx_loaded_at}'
                              AND object_id = OBJECT_ID('{schema_name}.{table_name}'))
                BEGIN
                    CREATE NONCLUSTERED INDEX [{idx_loaded_at}]
                    ON {schema_name}.{table_name} ([_loaded_at])
                END
                """
                conn.execute(text(create_idx_loaded))
                if log_func:
                    log_func(f"✅ Created index on _loaded_at")

                # Note: We don't create indexes on individual upsert key columns because:
                # - We use _upsert_hash for matching (which already has an index)
                # - Most upsert keys are NVARCHAR(MAX) which cannot be indexed
                # - Query performance relies on _upsert_hash, not individual columns

        except Exception as e:
            if log_func:
                log_func(f"⚠️ Warning: Could not create some indexes: {e}")
            # Don't fail the upload if index creation fails
            pass

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