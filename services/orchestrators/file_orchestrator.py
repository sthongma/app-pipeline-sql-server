"""
File Service for PIPELINE_SQLSERVER (Reorganized New Version)

Orchestrator that combines various services:
- FileReaderService: Read and detect files
- DataProcessorService: Process and validate data
- FileManagementService: Manage files

Usage examples:
    # For GUI
    file_service = FileService(log_callback=gui_log_function)
    
    # For CLI
    file_service = FileService(log_callback=logging.info)
    
    # Normal usage (original interface)
    success, df = file_service.read_excel_file("data.xlsx", "sales_data")
    
    # Separate usage
    file_info = file_service.get_file_info("data.xlsx")
    validation = file_service.validate_file_before_processing("data.xlsx", "sales_data")
"""

from typing import Optional, Tuple
import logging

from services.file import (
    FileReaderService,
    DataProcessorService,
    FileManagementService
)
from performance_optimizations import PerformanceOptimizer
from services.settings_manager import settings_manager


class FileOrchestrator:
    """
    Main file service (orchestrator)

    Responsibilities:
    - Coordinate between different services
    - Complete file reading and processing
    - Provide same interface as legacy system
    """

    def __init__(self, search_path: Optional[str] = None, log_callback: Optional[callable] = None) -> None:
        """
        Initialize FileService

        Args:
            search_path (Optional[str]): Folder path for file search
            log_callback (Optional[callable]): Function for logging
        """
        self.log_callback = log_callback if log_callback else logging.info

        # สร้าง services
        self.file_reader = FileReaderService(search_path, self.log_callback)
        self.data_processor = DataProcessorService(self.log_callback)
        self.file_manager = FileManagementService(search_path)

        # Load all file types from settings_manager
        # Build legacy-style dictionaries for services that expect them
        column_settings = {}
        dtype_settings = {}

        file_types = settings_manager.list_file_types()
        for file_type in file_types:
            column_settings[file_type] = settings_manager.get_column_settings(file_type)
            dtype_settings[file_type] = settings_manager.get_dtype_settings(file_type)

        self.file_reader.column_settings = column_settings
        self.file_reader.dtype_settings = dtype_settings

        self.data_processor.column_settings = column_settings
        self.data_processor.dtype_settings = dtype_settings

        # สร้าง performance optimizer
        self.performance_optimizer = PerformanceOptimizer(self.log_callback)

        # เก็บ reference สำหรับ backward compatibility
        self.search_path = self.file_reader.search_path
        self.column_settings = column_settings

    # ========================
    # Main Interface Methods
    # ========================
    
    def preview_file_columns(self, file_path, logic_type, max_rows=5):
        """
        Check file columns by reading only the first few rows to save time
        
        Args:
            file_path: File path
            logic_type: File type
            max_rows: Number of rows to read for preview (default: 5)
            
        Returns:
            tuple: (success, result/error_message, columns_info)
        """
        try:
            import pandas as pd
            
            # อ่านเฉพาะแถวแรกๆ เพื่อดูโครงสร้างคอลัมน์
            if file_path.lower().endswith('.csv'):
                try:
                    preview_df = pd.read_csv(file_path, nrows=max_rows, encoding='utf-8')
                except UnicodeDecodeError:
                    preview_df = pd.read_csv(file_path, nrows=max_rows, encoding='tis-620')
            else:
                # สำหรับ Excel
                preview_df = pd.read_excel(file_path, nrows=max_rows)
            
            if preview_df.empty:
                return False, "File is empty", None
            
            # ดึงชื่อคอลัมน์จาก preview
            file_columns = list(preview_df.columns)
            
            # Apply column mapping เพื่อดูว่าคอลัมน์จะถูก rename อย่างไร
            col_map = self.file_reader.build_rename_mapping_for_dataframe(file_columns, logic_type)
            
            mapped_columns = file_columns.copy()
            if col_map:
                for old_name, new_name in col_map.items():
                    if old_name in mapped_columns:
                        idx = mapped_columns.index(old_name)
                        mapped_columns[idx] = new_name
            
            # ตรวจสอบคอลัมน์ที่จำเป็น
            success, validation_message = self.data_processor.validate_columns_by_list(mapped_columns, logic_type)
            
            columns_info = {
                'original_columns': file_columns,
                'mapped_columns': mapped_columns,
                'column_mapping': col_map,
                'total_columns': len(file_columns),
                'preview_rows': len(preview_df)
            }
            
            if success:
                return True, f"Columns validation passed for {logic_type}", columns_info
            else:
                return False, validation_message, columns_info
                
        except Exception as e:
            return False, f"Error previewing file: {str(e)}", None

    def read_excel_file(self, file_path, logic_type):
        """
        Read Excel or CSV file according to specified type without using automatic correction system
        
        Args:
            file_path: File path
            logic_type: File type
            No automatic correction system is used
        """
        try:
            # รีเซ็ต log flags สำหรับไฟล์ใหม่
            self.data_processor._reset_log_flags()
            
            # อ่านไฟล์ด้วย Performance Optimizer
            if file_path.lower().endswith('.csv'):
                file_type = 'csv'
            elif file_path.lower().endswith('.xls'):
                file_type = 'excel_xls'
            else:
                file_type = 'excel'
            
            success, df = self.performance_optimizer.read_large_file_chunked(file_path, file_type)
            if not success:
                return False, "Unable to read file"
            
            # Apply column mapping (พิจารณาทิศทาง mapping ให้ตรงกับ header ของไฟล์)
            col_map = self.file_reader.build_rename_mapping_for_dataframe(df.columns, logic_type)
            if col_map:
                self.log_callback(f"🔄 Renamed columns by mapping ({len(col_map)} columns)")
                df.rename(columns=col_map, inplace=True)
            
            # ปรับปรุง memory usage
            df = self.performance_optimizer.optimize_memory_usage(df)
            
            # หมายเหตุ: การตรวจสอบข้อมูลจะทำใน staging table ด้วย SQL แทน pandas
            self.log_callback(f"🔄 Ingest as NVARCHAR(MAX) first, then validate/convert using SQL")
            
            # ทำความสะอาด memory
            self.performance_optimizer.cleanup_memory()
            
            self.log_callback(f"🎉 File processing completed")
            return True, df
            
        except Exception as e:
            error_msg = f"❌ Error while reading file: {e}"
            self.log_callback(error_msg)
            return False, error_msg
    
    # ========================
    # Delegation Methods
    # ========================
    
    def set_search_path(self, path):
        """Set path for Excel file search"""
        self.search_path = path
        self.file_reader.set_search_path(path)

    def find_data_files(self):
        """Find Excel and CSV files in specified path"""
        return self.file_reader.find_data_files()

    def detect_file_type(self, file_path):
        """Detect file type"""
        return self.file_reader.detect_file_type(file_path)

    def get_column_name_mapping(self, file_type):
        """Get column name mapping by file type"""
        return self.file_reader.get_column_name_mapping(file_type)

    def get_required_dtypes(self, file_type):
        """Get column dtypes by file type"""
        return self.data_processor.get_required_dtypes(file_type)

    def validate_columns(self, df, logic_type):
        """Validate required columns"""
        return self.data_processor.validate_columns(df, logic_type)

    def comprehensive_data_validation(self, df, logic_type):
        """Comprehensive data validation before processing"""
        return self.data_processor.comprehensive_data_validation(df, logic_type)

    def check_invalid_numeric(self, df, logic_type):
        """Check non-numeric values in numeric columns"""
        return self.data_processor.check_invalid_numeric(df, logic_type)

    def generate_pre_processing_report(self, df, logic_type):
        """Generate pre-processing summary report (deprecated - use SQL validation instead)"""
        return self.data_processor.generate_pre_processing_report(df, logic_type)

    def apply_dtypes(self, df, file_type):
        """Convert data types according to settings"""
        return self.data_processor.apply_dtypes(df, file_type)

    def move_uploaded_files(self, file_paths, logic_types=None):
        """Move uploaded files to Uploaded_Files folder"""
        return self.file_manager.move_uploaded_files(file_paths, logic_types, self.search_path)

    # ========================
    # Legacy Methods (เก็บไว้เพื่อ backward compatibility)
    # ========================
    
    def get_required_columns(self, file_type):
        """(Deprecated) Use get_required_dtypes instead"""
        return self.data_processor.get_required_dtypes(file_type)

    def standardize_column_name(self, col_name):
        """Convert column names to standard format"""
        return self.file_reader.standardize_column_name(col_name)

    def normalize_col(self, col):
        """Improve column normalization"""
        return self.file_reader.normalize_col(col)

    def load_settings(self):
        """Load new settings from settings_manager"""
        # โหลดการตั้งค่าใหม่จาก settings_manager
        # Build legacy-style dictionaries for services that expect them
        column_settings = {}
        dtype_settings = {}

        file_types = settings_manager.list_file_types()
        for file_type in file_types:
            column_settings[file_type] = settings_manager.get_column_settings(file_type)
            dtype_settings[file_type] = settings_manager.get_dtype_settings(file_type)

        # อัปเดตข้อมูลใน file_reader และ data_processor
        self.file_reader.column_settings = column_settings
        self.file_reader.dtype_settings = dtype_settings
        self.file_reader._settings_loaded = True

        self.data_processor.column_settings = column_settings
        self.data_processor.dtype_settings = dtype_settings
        self.data_processor._settings_loaded = True

        # อัปเดต reference ใน FileService
        self.column_settings = column_settings

    def _process_dataframe_in_chunks(self, df, process_func, logic_type, chunk_size=5000):
        """Process DataFrame in chunks (legacy wrapper)"""
        return self.data_processor.process_dataframe_in_chunks(df, process_func, logic_type, chunk_size)

    def _reset_log_flags(self):
        """Reset log flags (legacy wrapper)"""
        self.data_processor._reset_log_flags()

    def clean_numeric_columns(self, df, file_type):
        """Clean numeric column data"""
        return self.data_processor.clean_numeric_columns(df, file_type)

    def truncate_long_strings(self, df, logic_type):
        """Truncate strings that exceed specified length"""
        return self.data_processor.truncate_long_strings(df, logic_type)


    def upload_data_with_auto_schema_update(self, df, logic_type, processing_report=None, schema_name='bronze'):
        """
        Upload data with automatic schema update
        
        Args:
            df: DataFrame to upload
            logic_type: File type
            processing_report: (Not used)
            schema_name: Schema name in database
            
        Returns:
            Tuple[bool, str]: (Success status, Result message)
        """
        try:
            from services.orchestrators.database_orchestrator import DatabaseOrchestrator
            
            # สร้าง database service
            db_service = DatabaseOrchestrator()
            
            # ตรวจสอบการเชื่อมต่อ
            connection_ok, conn_msg = db_service.check_connection()
            if not connection_ok:
                return False, f"Unable to connect to database: {conn_msg}"
            
            # ได้ required columns ตามการตั้งค่าล่าสุด
            required_cols = self.get_required_dtypes(logic_type)
            if not required_cols:
                return False, "Data type settings not found"
            
            # ไม่รองรับ auto-fix อีกต่อไป จึงไม่ใช้ force_recreate จาก processing_report
            force_recreate = False
            
            # อัปโหลดข้อมูล
            success, upload_msg = db_service.upload_data(
                df=df,
                logic_type=logic_type,
                required_cols=required_cols,
                schema_name=schema_name,
                log_func=self.log_callback,
                force_recreate=force_recreate
            )
            
            return success, upload_msg
            
        except Exception as e:
            error_msg = f"❌ Error during upload: {e}"
            self.log_callback(error_msg)
            return False, error_msg


    def print_detailed_validation_report(self, df, logic_type):
        """Display detailed data validation report (legacy method)"""
        # สร้างรายงานแบบละเอียด
        self.log_callback("\n" + "="*80)
        self.log_callback("🔍 Detailed data validation report")
        self.log_callback("="*80)
        
        # ข้อมูลพื้นฐาน
        self.log_callback(f"📊 Basic info:")
        self.log_callback(f"   • Total rows: {len(df):,}")
        self.log_callback(f"   • Total columns: {len(df.columns)}")
        self.log_callback(f"   • File type: {logic_type}")
        
        # ใช้ comprehensive validation
        validation_result = self.comprehensive_data_validation(df, logic_type)
        
        if validation_result['summary']:
            self.log_callback("\n📋 Validation summary:")
            for msg in validation_result['summary']:
                self.log_callback(f"   • {msg}")
        
        self.log_callback("="*80)
