"""
Schema Service for PIPELINE_SQLSERVER

Manages database schema operations
"""

import logging
from tkinter import messagebox
from typing import List, Tuple

from sqlalchemy import text


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