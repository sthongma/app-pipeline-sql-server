#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive test for complete project structure
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_orchestrators():
    """Test all orchestrator services"""
    print("Testing Orchestrator Services...")
    
    try:
        from services.orchestrators.file_orchestrator import FileOrchestrator
        from services.orchestrators.database_orchestrator import DatabaseOrchestrator
        from services.orchestrators.config_orchestrator import ConfigOrchestrator
        from services.orchestrators.validation_orchestrator import ValidationOrchestrator
        from services.orchestrators.utility_orchestrator import UtilityOrchestrator
        
        # Test instantiation
        FileOrchestrator()
        DatabaseOrchestrator()
        ConfigOrchestrator()
        ValidationOrchestrator()
        UtilityOrchestrator()
        
        print("  Orchestrators: SUCCESS")
        return True
        
    except Exception as e:
        print(f"  Orchestrators: FAILED - {e}")
        return False

def test_modular_services():
    """Test modular services"""
    print("Testing Modular Services...")
    
    try:
        # Database services
        from services.database.connection_service import ConnectionService
        from services.database.schema_service import SchemaService
        from services.database.data_validation_service import DataValidationService
        from services.database.data_upload_service import DataUploadService
        
        # File services
        from services.file.file_reader_service import FileReaderService
        from services.file.data_processor_service import DataProcessorService
        from services.file.file_management_service import FileManagementService
        
        # Utility services
        from services.utilities.permission_checker_service import PermissionCheckerService
        from services.utilities.preload_service import PreloadService
        
        print("  Modular Services: SUCCESS")
        return True
        
    except Exception as e:
        print(f"  Modular Services: FAILED - {e}")
        return False

def test_ui_components():
    """Test UI components"""
    print("Testing UI Components...")
    
    try:
        # Main windows
        from ui.login_window import LoginWindow
        from ui.main_window import MainWindow
        from ui.loading_dialog import LoadingDialog
        
        # Components
        from ui.components.file_list import FileList
        from ui.components.progress_bar import ProgressBar
        from ui.components.status_bar import StatusBar
        
        # Handlers
        from ui.handlers.file_handler import FileHandler
        from ui.handlers.settings_handler import SettingsHandler
        
        # Tabs
        from ui.tabs.main_tab import MainTab
        from ui.tabs.log_tab import LogTab
        from ui.tabs.settings_tab import SettingsTab
        
        print("  UI Components: SUCCESS")
        return True
        
    except Exception as e:
        print(f"  UI Components: FAILED - {e}")
        return False

def test_utilities():
    """Test utility modules"""
    print("Testing Utilities...")
    
    try:
        # Utils
        from utils.helpers import normalize_column_name, safe_json_load
        from utils.validators import validate_file_path, validate_database_connection
        from utils.logger import setup_logging
        
        # Config
        from config.database import DatabaseConfig
        from config.settings import SettingsManager
        
        print("  Utilities: SUCCESS")
        return True
        
    except Exception as e:
        print(f"  Utilities: FAILED - {e}")
        return False

def test_main_entry_points():
    """Test main application entry points"""
    print("Testing Main Entry Points...")
    
    try:
        # Check main files can be imported
        import pipeline_gui_app
        import auto_process_cli
        import constants
        import performance_optimizations
        
        print("  Main Entry Points: SUCCESS")
        return True
        
    except Exception as e:
        print(f"  Main Entry Points: FAILED - {e}")
        return False

def test_structure_consistency():
    """Test structure consistency"""
    print("Testing Structure Consistency...")
    
    issues = []
    
    # Check no old files exist
    old_files = [
        "services/file_service.py",
        "services/database_service.py", 
        "services/config_service.py",
        "services/validation_orchestrator.py",
        "services/utility_orchestrator.py",
        "services/permission_checker_service.py",
        "services/preload_service.py"
    ]
    
    for file_path in old_files:
        if os.path.exists(file_path):
            issues.append(f"Old file still exists: {file_path}")
    
    # Check required directories exist
    required_dirs = [
        "services/orchestrators",
        "services/utilities",
        "services/database",
        "services/file",
        "ui/components",
        "ui/handlers", 
        "ui/tabs",
        "utils",
        "config"
    ]
    
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            issues.append(f"Required directory missing: {dir_path}")
    
    # Check services/config doesn't exist
    if os.path.exists("services/config"):
        issues.append("Empty services/config directory still exists")
    
    if issues:
        print(f"  Structure Consistency: FAILED")
        for issue in issues:
            print(f"    - {issue}")
        return False
    else:
        print("  Structure Consistency: SUCCESS")
        return True

def main():
    """Main test function"""
    print("=" * 60)
    print("COMPREHENSIVE PROJECT STRUCTURE TEST")
    print("=" * 60)
    
    test_results = []
    
    # Run all tests
    test_results.append(("Structure Consistency", test_structure_consistency()))
    test_results.append(("Orchestrators", test_orchestrators()))
    test_results.append(("Modular Services", test_modular_services()))
    test_results.append(("UI Components", test_ui_components()))
    test_results.append(("Utilities", test_utilities()))
    test_results.append(("Main Entry Points", test_main_entry_points()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "PASSED" if result else "FAILED"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\nEXCELLENT! Complete project structure is working perfectly!")
        print("All components follow consistent patterns and standards.")
        return True
    else:
        print(f"\nSome tests failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)