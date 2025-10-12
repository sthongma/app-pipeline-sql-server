#!/usr/bin/env python3
"""
Installation and requirements checker for PIPELINE_SQLSERVER.

This script checks for required JSON configuration files and creates them if missing.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

def create_directory_if_not_exists(directory: str) -> bool:
    """Create directory if it doesn't exist."""
    try:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"[OK] Directory ensured: {directory}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to create directory {directory}: {e}")
        return False

def check_and_create_json_file(file_path: str, default_content: Dict[str, Any]) -> bool:
    """Check if JSON file exists and create with default content if missing."""
    try:
        if os.path.exists(file_path):
            # Validate existing file
            with open(file_path, 'r', encoding='utf-8') as f:
                json.load(f)
            print(f"[OK] JSON file exists and is valid: {file_path}")
            return True
        else:
            # Create missing file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(default_content, f, indent=4, ensure_ascii=False)
            print(f"[CREATED] Created JSON file: {file_path}")
            return True
    except json.JSONDecodeError as e:
        print(f"[WARNING] Invalid JSON in {file_path}: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Failed to process {file_path}: {e}")
        return False

def get_json_file_templates() -> Dict[str, Dict[str, Any]]:
    """Return templates for all required JSON files (sql_config.json no longer needed - using env vars)."""
    return {
        "config/app_settings.json": {
            "window_size": [900, 780],
            "theme": "system",
            "auto_move_files": True,
            "backup_enabled": True,
            "log_level": "INFO"
        },
        "config/input_folder_config.json": {
            "folder_path": ""
        },
        "config/column_settings.json": {},
        "config/dtype_settings.json": {}
    }

def check_python_dependencies() -> bool:
    """Check if required Python packages are installed."""
    required_packages = [
        'pandas',
        'openpyxl',
        'xlrd',
        'pyodbc',
        'tkinter'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'tkinter':
                import tkinter
            else:
                __import__(package)
            print(f"[OK] Package available: {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"[MISSING] Missing package: {package}")
    
    if missing_packages:
        print(f"\n[WARNING] Missing packages: {', '.join(missing_packages)}")
        print("Install missing packages with: pip install -r requirements.txt")
        return False
    
    return True

def check_and_create_env_file() -> bool:
    """Check and create .env file if it doesn't exist."""
    env_file_path = ".env"
    
    if os.path.exists(env_file_path):
        print(f"[OK] Environment file exists: {env_file_path}")
        return True
    
    try:
        # Read from .env.example
        example_file = ".env.example"
        if not os.path.exists(example_file):
            print(f"[WARNING] {example_file} not found, creating basic .env file")
            env_content = """# Database Configuration for PIPELINE_SQLSERVER
# Set these values according to your SQL Server setup

# Database Connection
DB_SERVER=
DB_NAME=

# SQL Server Authentication (optional - leave blank for Windows Authentication)
DB_USERNAME=
DB_PASSWORD=

# Logging Configuration
STRUCTURED_LOGGING=false

# Example values:
# DB_SERVER=localhost
# DB_SERVER=MYSERVER\\SQLEXPRESS
# DB_SERVER=192.168.1.100
# DB_NAME=MyDatabase
# DB_USERNAME=myuser
# DB_PASSWORD=mypassword
# STRUCTURED_LOGGING=true
"""
        else:
            # Copy from .env.example
            with open(example_file, 'r', encoding='utf-8') as f:
                env_content = f.read()
        
        # Create .env file
        with open(env_file_path, 'w', encoding='utf-8') as f:
            f.write(env_content)
            
        print(f"[CREATED] Environment file created: {env_file_path}")
        print("[INFO] Please edit .env file with your actual database credentials")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to create {env_file_path}: {e}")
        return False

def main():
    """Main installation and checking function."""
    print("PIPELINE_SQLSERVER Installation & Requirements Check")
    print("=" * 60)
    
    success = True
    
    # 1. Check/Create config directory
    print("\n[1] Checking configuration directory...")
    if not create_directory_if_not_exists("config"):
        success = False
    
    # 2. Check/Create JSON files
    print("\n[2] Checking JSON configuration files...")
    json_templates = get_json_file_templates()
    
    for file_path, template in json_templates.items():
        if not check_and_create_json_file(file_path, template):
            success = False
    
    # 3. Check Python dependencies
    print("\n[3] Checking Python dependencies...")
    if not check_python_dependencies():
        success = False
    
    # 4. Check/Create environment file
    print("\n[4] Checking environment configuration...")
    if not check_and_create_env_file():
        print("[WARNING] Environment file setup had issues, but continuing...")
    
    # 5. Create additional directories if needed
    print("\n[5] Checking additional directories...")
    additional_dirs = [
        "temp"
    ]
    
    for directory in additional_dirs:
        create_directory_if_not_exists(directory)
    
    # 6. Summary
    print("\n" + "=" * 60)
    if success:
        print("[SUCCESS] Installation check completed successfully!")
        print("[INFO] Project is ready to run.")
        print("[INFO] Don't forget to configure your .env file with database credentials!")
    else:
        print("[ERROR] Installation check completed with errors!")
        print("[WARNING] Please resolve the issues above before running the project.")
        print("[INFO] Don't forget to configure your .env file with database credentials!")
        sys.exit(1)

if __name__ == "__main__":
    main()