#!/usr/bin/env python3
"""
Auto Process CLI - Automated File Processing Command Line Program
A standalone CLI program that processes files automatically without GUI
Uses the same settings and configuration as the GUI application

Usage: python auto_process_cli.py [source_folder]
"""

# Standard library imports
import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime

# Local imports
from config.database import DatabaseConfig
from config.json_manager import json_manager, get_output_folder
from constants import PathConstants
from services.file import FileManagementService
from services.orchestrators.database_orchestrator import DatabaseOrchestrator
from services.orchestrators.file_orchestrator import FileOrchestrator
from services.utilities.preload_service import PreloadService
from ui.handlers.file_handler import FileHandler
from ui.handlers.settings_handler import SettingsHandler
from utils.logger import setup_logging

# Override messagebox for CLI to prevent GUI popups
class CLIMessageBox:
    @staticmethod
    def showinfo(title, message):
        print(f"INFO: {message}")
    
    @staticmethod
    def showerror(title, message):
        print(f"ERROR: {message}")
    
    @staticmethod
    def showwarning(title, message):
        print(f"WARNING: {message}")
    
    @staticmethod
    def askyesno(title, message):
        # For CLI, always return True for auto processing
        return True

# Replace tkinter messagebox with CLI version
import tkinter.messagebox
tkinter.messagebox.showinfo = CLIMessageBox.showinfo
tkinter.messagebox.showerror = CLIMessageBox.showerror
tkinter.messagebox.showwarning = CLIMessageBox.showwarning
tkinter.messagebox.askyesno = CLIMessageBox.askyesno


class CLIProgressCallback:
    """CLI Progress callbacks for file processing operations"""
    def __init__(self, cli_instance):
        self.cli = cli_instance
        
    def reset_progress(self):
        pass
        
    def set_progress_status(self, status, detail):
        self.cli.log(f"Status: {status} - {detail}")
        
    def update_progress(self, progress, status, detail):
        percentage = int(progress * 100)
        self.cli.log(f"[{percentage}%] {status}: {detail}")
        
    def clear_file_list(self):
        pass
        
    def add_file_to_list(self, file_path, logic_type):
        self.cli.log(f"Found file: {os.path.basename(file_path)} [{logic_type}]")
        
    def reset_select_all(self):
        pass
        
    def enable_select_all(self):
        pass
        
    def update_status(self, status, is_error):
        if is_error:
            self.cli.log(f"ERROR: {status}")
        else:
            self.cli.log(f"SUCCESS: {status}")
            
    def disable_controls(self):
        pass
        
    def enable_controls(self):
        pass
        
    def disable_checkbox(self, checkbox):
        # CLI doesn't have checkboxes, safe to ignore
        pass
        
    def set_file_uploaded(self, file_path):
        pass


class AutoProcessCLI:
    def __init__(self):
        """
        Initialize Auto Process CLI - Standalone program using GUI settings
        """
        # Setup console logging with English format
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        self.settings_file = "config/column_settings.json"
        self.settings_handler = SettingsHandler(self.settings_file, self.log)
        
        # Create CLI callbacks
        self.ui_callbacks = CLIProgressCallback(self)
        
        # Load settings (same as GUI)
        self.column_settings = self.settings_handler.load_column_settings()
        self.dtype_settings = self.settings_handler.load_dtype_settings()
        
        # Create services (same as GUI)
        self.file_service = FileOrchestrator(log_callback=self.log)
        self.db_service = DatabaseOrchestrator()
        self.file_mgmt_service = FileManagementService()
        self.preload_service = PreloadService()

        # Load output folder from config if exists
        self._load_output_folder_from_config()

        # Create file handler (same as GUI)
        self.file_handler = FileHandler(
            self.file_service,
            self.db_service,
            self.file_mgmt_service,
            self.log
        )
    
    def _load_output_folder_from_config(self):
        """Load output folder setting using JSONManager"""
        try:
            output_folder_path = get_output_folder()
            if output_folder_path and os.path.exists(output_folder_path):
                # Set output folder in both file management services
                self.file_mgmt_service.set_output_folder(output_folder_path)
                if hasattr(self.file_service, 'file_manager'):
                    self.file_service.file_manager.set_output_folder(output_folder_path)
                self.log(f"Output folder loaded: {output_folder_path}")
        except Exception as e:
            self.log(f"WARNING: Could not load output folder setting: {e}")

    def log(self, message):
        """Log message to console in English"""
        try:
            logging.info(str(message))
        except Exception:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")
    
    def validate_database_connection(self):
        """Validate database connection and permissions"""
        self.log("Checking database connection...")
        
        # Load database configuration from environment variables
        try:
            db_config = DatabaseConfig()
            config = db_config.config
            if not config:
                self.log("ERROR: Database configuration not found. Please set environment variables (DB_SERVER, DB_NAME).")
                return False
            
            # Check if essential configuration is present
            if not config.get('server') or not config.get('database'):
                self.log("ERROR: DB_SERVER or DB_NAME environment variables not set.")
                return False
                
            self.log(f"Loaded database configuration: {config.get('server', 'Unknown')}")
        except Exception as e:
            self.log(f"ERROR: Failed to load database configuration: {e}")
            return False
        
        # Test database connection
        self.log("Testing database connection...")
        connection_ok = self.db_service.test_connection(config)
        if not connection_ok:
            self.log("ERROR: Failed to connect to database")
            return False
        
        self.log("Database connection successful")
        
        # Check database permissions
        self.log("Checking database permissions...")
        permission_results = self.db_service.check_permissions('bronze', log_callback=self.log)
        if not permission_results.get('success', False):
            missing_permissions = permission_results.get('missing_critical', [])
            self.log(f"ERROR: Insufficient permissions: {', '.join(missing_permissions)}")
            return False
        
        self.log("Database permissions validated")
        
        # Load file type settings
        self.log("Loading file type settings...")
        preload_success, _msg, data = self.preload_service.preload_file_settings()
        if preload_success and data:
            self.column_settings = data.get('column_settings', {})
            self.dtype_settings = data.get('dtype_settings', {})
            self.log(f"Loaded {len(self.column_settings)} file type configurations")
        else:
            self.log("WARNING: No file type settings found. Please configure in GUI first.")
            if not self.column_settings:
                return False
        
        return True
    
    def scan_files(self, folder_path):
        """Scan for data files in the specified folder"""
        self.log("Scanning for data files...")
        
        # Set search path
        self.file_service.set_search_path(folder_path)
        self.settings_handler.save_input_folder(folder_path)
        
        # Create UI callbacks
        ui_callbacks = {
            'reset_progress': self.ui_callbacks.reset_progress,
            'set_progress_status': self.ui_callbacks.set_progress_status,
            'update_progress': self.ui_callbacks.update_progress,
            'clear_file_list': self.ui_callbacks.clear_file_list,
            'add_file_to_list': self.ui_callbacks.add_file_to_list,
            'reset_select_all': self.ui_callbacks.reset_select_all,
            'enable_select_all': self.ui_callbacks.enable_select_all,
            'update_status': self.ui_callbacks.update_status,
            'disable_controls': self.ui_callbacks.disable_controls,
            'enable_controls': self.ui_callbacks.enable_controls
        }
        
        # Run file scan (no threading for CLI)
        try:
            self.file_handler._check_files(ui_callbacks)
            return True
        except Exception as e:
            self.log(f"ERROR: Failed to scan files: {e}")
            return False
    
    def process_files_automatically(self):
        """Process all files automatically using batch processing (same as GUI)"""
        self.log("Starting automatic file processing...")

        # Get all scanned files from file service
        data_files = self.file_service.find_data_files()

        if not data_files:
            self.log("No data files found")
            return False

        # Prepare selected files in the format expected by _upload_selected_files
        # Format: [(file_path, logic_type), checkbox_widget]
        selected_files = []
        for file_path in data_files:
            logic_type = self.file_service.detect_file_type(file_path)
            if logic_type:
                # Use None for checkbox since we don't have GUI widgets in CLI
                selected_files.append(((file_path, logic_type), None))

        if not selected_files:
            self.log("No matching files found")
            return False

        self.log(f"Found {len(selected_files)} files to process")

        # Create UI callbacks
        ui_callbacks = {
            'disable_controls': self.ui_callbacks.disable_controls,
            'enable_controls': self.ui_callbacks.enable_controls,
            'reset_progress': self.ui_callbacks.reset_progress,
            'set_progress_status': self.ui_callbacks.set_progress_status,
            'update_progress': self.ui_callbacks.update_progress,
            'clear_file_list': self.ui_callbacks.clear_file_list,
            'reset_select_all': self.ui_callbacks.reset_select_all,
            'disable_checkbox': self.ui_callbacks.disable_checkbox,
            'set_file_uploaded': self.ui_callbacks.set_file_uploaded
        }

        # Use the same batch processing method as GUI
        try:
            self.file_handler._upload_selected_files(selected_files, ui_callbacks)
            return True
        except Exception as e:
            self.log(f"ERROR: Failed to process files: {e}")
            return False
    
    def run_auto_process(self, folder_path):
        """Run automatic file processing - standalone CLI program"""
        self.log(f"Starting auto processing for folder: {folder_path}")
        
        # Step 1: Validate database connection and settings
        if not self.validate_database_connection():
            self.log("ERROR: Database validation failed")
            return False
        
        # Step 2: Scan for files
        if not self.scan_files(folder_path):
            self.log("ERROR: File scanning failed")
            return False

        # Step 3: Process files automatically (using batch processing like GUI)
        if not self.process_files_automatically():
            self.log("ERROR: Automatic file processing failed")
            return False
        
        self.log("SUCCESS: Auto processing completed successfully")
        return True
    

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Automated File Processing CLI - Standalone program using GUI settings',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python auto_process_cli.py C:\\path\\to\\data\\folder
  python auto_process_cli.py "C:\\Documents\\Excel Files"
  
Notes:
  - Database connection and file type settings must be configured in GUI first
  - CLI uses the same settings and services as the GUI application
  - Processes all files automatically without user interaction
        """
    )
    
    parser.add_argument(
        'folder_path',
        nargs='?',
        help='Source folder to process files from (if not specified, uses last folder from settings)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='Auto Process CLI v3.0 (Standalone)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging with environment variable support
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(level=log_level)
    
    # Log environment variables status
    env_vars = ['DB_SERVER', 'DB_NAME', 'DB_USERNAME', 'DB_PASSWORD']
    logging.info("Environment Variables Status:")
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if 'PASSWORD' in var or 'USERNAME' in var:
                logging.info(f"  {var}: *** (set)")
            else:
                logging.info(f"  {var}: {value}")
        else:
            logging.info(f"  {var}: (not set)")
    
    # Create CLI instance
    cli = AutoProcessCLI()
    
    # Determine source folder
    folder_path = args.folder_path
    
    # If no folder specified, use input folder from settings
    if not folder_path:
        folder_path = cli.settings_handler.load_input_folder()
        if folder_path:
            cli.log(f"Using input folder from settings: {folder_path}")
        else:
            cli.log("ERROR: No source folder specified and no input folder found in settings")
            cli.log("Please specify a folder path or select an input folder in GUI first")
            parser.print_help()
            sys.exit(1)
    
    # Validate folder exists
    if not os.path.isdir(folder_path):
        cli.log(f"ERROR: Invalid folder path: {folder_path}")
        sys.exit(1)
    
    # Start processing
    success = cli.run_auto_process(folder_path)
    
    # Exit with appropriate status
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
