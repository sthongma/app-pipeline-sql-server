"""
Schema Service for PIPELINE_SQLSERVER

Manages database schema operations
"""

import logging
from tkinter import messagebox
from typing import List, Tuple

from sqlalchemy import text

from utils.sql_utils import sanitize_sql_identifier, quote_identifier


class SchemaService:
    """
    Database schema management service
    
    Handles schema creation and validation
    """
    
    def __init__(self, engine) -> None:
        """
        Initialize SchemaService
        
        Args:
            engine: SQLAlchemy engine instance
        """
        self.engine = engine
        self.logger = logging.getLogger(__name__)

    def ensure_schemas_exist(self, schema_names: List[str]) -> Tuple[bool, str]:
        """
        Check and create schemas if they don't exist

        Args:
            schema_names: List of schema names to create

        Returns:
            Tuple[bool, str]: (success status, result message)
        """
        try:
            with self.engine.begin() as conn:
                for schema_name in schema_names:
                    # Sanitize schema name to prevent SQL injection
                    try:
                        safe_schema_name = sanitize_sql_identifier(schema_name)
                    except ValueError as ve:
                        error_msg = f"Invalid schema name '{schema_name}': {ve}"
                        self.logger.error(error_msg)
                        messagebox.showwarning("Schema validation", error_msg)
                        return False, error_msg

                    # Use parameterized query for schema check
                    check_query = text("""
                        SELECT COUNT(*) FROM sys.schemas WHERE name = :schema_name
                    """)
                    result = conn.execute(check_query, {"schema_name": safe_schema_name})
                    exists = result.scalar() > 0

                    if not exists:
                        # Use quoted identifier for CREATE SCHEMA
                        # Note: CREATE SCHEMA cannot use bind parameters, but identifier is sanitized
                        create_query = text(f"CREATE SCHEMA {quote_identifier(safe_schema_name)}")
                        conn.execute(create_query)
                        self.logger.info(f"Created schema: {safe_schema_name}")
                    else:
                        self.logger.debug(f"Schema already exists: {safe_schema_name}")

            return True, f"Verified/created schemas: {', '.join(schema_names)}"
        except ValueError as ve:
            error_msg = f"Schema validation error: {ve}"
            self.logger.error(error_msg)
            messagebox.showwarning("Schema validation", error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Failed to create schema: {e}"
            self.logger.error(error_msg)
            messagebox.showwarning("Schema creation", error_msg)
            return False, error_msg