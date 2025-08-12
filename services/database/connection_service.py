"""
Connection Service for PIPELINE_SQLSERVER

Manages database connections and configuration updates
"""

import logging
from tkinter import messagebox
from typing import Any, Dict, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError, ProgrammingError

from config.database import DatabaseConfig
from constants import DatabaseConstants, ErrorMessages, SuccessMessages


class ConnectionService:
    """
    Database connection management service
    
    Handles connection testing, configuration updates, and connection validation
    """
    
    def __init__(self, db_config: DatabaseConfig = None) -> None:
        """
        Initialize ConnectionService
        
        Args:
            db_config: Database configuration instance (optional)
        """
        self.db_config = db_config or DatabaseConfig()
        self.engine = self.db_config.get_engine()
        self.logger = logging.getLogger(__name__)

    def check_connection(self, show_warning: bool = True) -> Tuple[bool, str]:
        """
        Check connection to SQL Server
        
        Args:
            show_warning: Whether to show warning dialog on failure
            
        Returns:
            Tuple[bool, str]: (connection status, result message)
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
        Test connection to SQL Server with provided config
        
        Args:
            config (Dict[str, Any]): Connection configuration
            
        Returns:
            bool: True if connection successful, False if failed
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
        """
        Update connection configuration
        
        Args:
            server: Database server
            database: Database name
            auth_type: Authentication type
            username: Username for SQL auth
            password: Password for SQL auth
        """
        self.db_config.update_config(
            server=server,
            database=database,
            auth_type=auth_type,
            username=username,
            password=password
        )
        self.engine = self.db_config.get_engine()

    def get_engine(self):
        """Get current database engine"""
        return self.engine