#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test clean structure without backward compatibility
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_orchestrator_imports():
    """Test orchestrator imports"""
    print("Testing orchestrator imports...")
    
    try:
        from services.orchestrators.file_orchestrator import FileOrchestrator
        from services.orchestrators.database_orchestrator import DatabaseOrchestrator
        from services.orchestrators.config_orchestrator import ConfigOrchestrator
        from services.orchestrators.validation_orchestrator import ValidationOrchestrator
        from services.orchestrators.utility_orchestrator import UtilityOrchestrator
        
        print("Orchestrator imports: SUCCESS")
        
        # Test instantiation
        file_orchestrator = FileOrchestrator()
        database_orchestrator = DatabaseOrchestrator()
        config_orchestrator = ConfigOrchestrator()
        validation_orchestrator = ValidationOrchestrator()
        utility_orchestrator = UtilityOrchestrator()
        
        print("Orchestrator instantiation: SUCCESS")
        return True
        
    except Exception as e:
        print(f"Orchestrator test FAILED: {e}")
        return False

def test_utility_imports():
    """Test utility imports"""
    print("\nTesting utility imports...")
    
    try:
        from services.utilities.permission_checker_service import PermissionCheckerService
        from services.utilities.preload_service import PreloadService
        
        print("Utility imports: SUCCESS")
        
        # Test instantiation
        permission_checker = PermissionCheckerService()
        preload_service = PreloadService()
        
        print("Utility instantiation: SUCCESS")
        return True
        
    except Exception as e:
        print(f"Utility test FAILED: {e}")
        return False

def test_modular_services():
    """Test modular service imports"""
    print("\nTesting modular services...")
    
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
        
        print("Modular service imports: SUCCESS")
        return True
        
    except Exception as e:
        print(f"Modular service test FAILED: {e}")
        return False

def test_clean_structure():
    """Test that old files are removed"""
    print("\nTesting clean structure...")
    
    old_files = [
        "services/file_service.py",
        "services/database_service.py", 
        "services/config_service.py",
        "services/validation_orchestrator.py",
        "services/utility_orchestrator.py",
        "services/permission_checker_service.py",
        "services/preload_service.py"
    ]
    
    found_old_files = []
    for file_path in old_files:
        if os.path.exists(file_path):
            found_old_files.append(file_path)
    
    if found_old_files:
        print(f"Found old files (should be removed): {found_old_files}")
        return False
    else:
        print("Clean structure: SUCCESS - no old files found")
        return True

def main():
    """Main test function"""
    print("Testing Clean Structure (No Backward Compatibility)")
    print("=" * 55)
    
    test_results = []
    
    # Run all tests
    test_results.append(("Clean Structure", test_clean_structure()))
    test_results.append(("Orchestrator Services", test_orchestrator_imports()))
    test_results.append(("Utility Services", test_utility_imports()))
    test_results.append(("Modular Services", test_modular_services()))
    
    # Summary
    print("\n" + "=" * 55)
    print("Test Results Summary")
    print("=" * 55)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "PASSED" if result else "FAILED"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("Clean structure is working perfectly!")
        return True
    else:
        print("Some tests failed.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)