"""
Auto Column Rename Service for PIPELINE_SQLSERVER

This service automatically renames DataFrame columns to match the expected schema
using ML-enhanced mapping suggestions. It integrates with the existing pipeline
to provide seamless column transformation.
"""

import pandas as pd
import json
import os
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from .ml_column_mapper import MLColumnMapper
from constants import PathConstants


class AutoColumnRenameService:
    """
    Auto Column Rename Service
    
    Features:
    1. Automatic column renaming based on ML suggestions
    2. Integration with existing column_settings.json
    3. Fallback to user interaction when confidence is low
    4. Batch processing for multiple files
    5. Logging and reporting of rename operations
    """
    
    def __init__(self, log_callback: Optional[callable] = None):
        """Initialize the Auto Column Rename Service"""
        self.log_callback = log_callback if log_callback else print
        
        # Setup file logging
        self.setup_logging()
        
        self.ml_mapper = MLColumnMapper(log_callback)
        
        # Rename statistics
        self.rename_stats = {
            'total_files_processed': 0,
            'total_columns_renamed': 0,
            'auto_renamed': 0,
            'manual_review_required': 0,
            'failed_renames': 0
        }
    
    def setup_logging(self):
        """Setup file logging for Auto Column Rename Service"""
        # Create logger
        self.file_logger = logging.getLogger('AutoColumnRenameService')
        self.file_logger.setLevel(logging.INFO)
        
        # Clear existing handlers to avoid duplication
        self.file_logger.handlers.clear()
        
        # File handler - use direct path calculation
        tool_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_file = os.path.join(tool_dir, "column_mapper.log")
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        self.file_logger.addHandler(file_handler)
    
    def _log(self, message: str, level: str = 'info'):
        """Log to both callback and file"""
        # Log to callback (console)
        if self.log_callback:
            self.log_callback(message)
        
        # Log to file
        if hasattr(self, 'file_logger'):
            if level.lower() == 'error':
                self.file_logger.error(message)
            elif level.lower() == 'warning':
                self.file_logger.warning(message)
            elif level.lower() == 'debug':
                self.file_logger.debug(message)
            else:
                self.file_logger.info(message)
    
    def auto_rename_dataframe_columns(self, 
                                    df: pd.DataFrame, 
                                    file_type: str, 
                                    confidence_threshold: float = 70.0,
                                    create_new_mapping: bool = True) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Automatically rename DataFrame columns to match expected schema
        
        Args:
            df: Input DataFrame
            file_type: File type identifier (e.g., 'order_shopee', 'new_format')
            confidence_threshold: Minimum confidence for auto-rename
            create_new_mapping: Whether to create new mapping for unknown file types
            
        Returns:
            Tuple of (renamed_dataframe, rename_report)
        """
        original_columns = list(df.columns)
        rename_report = {
            'success': False,
            'file_type': file_type,
            'original_columns': original_columns,
            'renamed_columns': {},
            'auto_renamed': [],
            'manual_review_needed': [],
            'unmapped_columns': [],
            'confidence_scores': {},
            'suggestions': {},
            'operation_log': []
        }
        
        try:
            self._log(f"🔄 Starting auto-rename for file type: {file_type}")
            
            # Check if file type already exists in settings
            if file_type in self.ml_mapper.column_settings:
                return self._rename_with_existing_mapping(df, file_type, rename_report)
            
            # File type doesn't exist - use ML to suggest mappings
            self._log(f"🆕 New file type detected: {file_type}")
            
            # Try to identify file type from columns
            file_type_suggestions = self.ml_mapper.suggest_file_type_from_columns(original_columns)
            
            if file_type_suggestions:
                self._log(f"🎯 Suggested similar file types:")
                for suggestion in file_type_suggestions:
                    self._log(f"   • {suggestion['file_type']} ({suggestion['confidence']}%)")
                
                # If there's a high confidence match, ask user if they want to use it
                best_match = file_type_suggestions[0]
                if best_match['confidence'] > 80:
                    self._log(f"🔥 High confidence match found: {best_match['file_type']}")
                    return self._rename_with_existing_mapping(df, best_match['file_type'], rename_report, 
                                                            original_file_type=file_type)
            
            # Get ML suggestions for new mapping
            ml_suggestions = self.ml_mapper.suggest_mappings_for_new_file(original_columns, file_type)
            rename_report['suggestions'] = ml_suggestions
            
            # Generate mapping report
            mapping_report = self.ml_mapper.generate_mapping_report(ml_suggestions)
            self._log(f"\\n{mapping_report}")
            
            # Auto-map columns with high confidence
            auto_mappings = {}
            manual_review = {}
            
            for source_col in original_columns:
                if source_col in ml_suggestions and ml_suggestions[source_col]:
                    best_suggestion = ml_suggestions[source_col][0]
                    confidence = best_suggestion['confidence']
                    target_col = best_suggestion['target_column']
                    
                    rename_report['confidence_scores'][source_col] = confidence
                    
                    if confidence >= confidence_threshold:
                        auto_mappings[source_col] = target_col
                        rename_report['auto_renamed'].append({
                            'source': source_col,
                            'target': target_col,
                            'confidence': confidence
                        })
                    else:
                        manual_review[source_col] = ml_suggestions[source_col]
                        rename_report['manual_review_needed'].append({
                            'source': source_col,
                            'suggestions': ml_suggestions[source_col][:3]  # Top 3 suggestions
                        })
                else:
                    rename_report['unmapped_columns'].append(source_col)
            
            # Apply auto-mappings
            if auto_mappings:
                df_renamed = df.rename(columns=auto_mappings)
                rename_report['renamed_columns'] = auto_mappings
                self._log(f"✅ Auto-renamed {len(auto_mappings)} columns")
                
                # Create new mapping if requested
                if create_new_mapping and len(auto_mappings) > 0:
                    self._create_new_file_type_mapping(file_type, auto_mappings, ml_suggestions)
            else:
                df_renamed = df.copy()
                self._log(f"⚠️ No columns met confidence threshold for auto-rename", 'warning')
            
            rename_report['success'] = True
            self.rename_stats['total_files_processed'] += 1
            self.rename_stats['auto_renamed'] += len(auto_mappings)
            self.rename_stats['manual_review_required'] += len(manual_review)
            
            return df_renamed, rename_report
            
        except Exception as e:
            error_msg = f"❌ Error during auto-rename: {str(e)}"
            self._log(error_msg, 'error')
            rename_report['error'] = error_msg
            self.rename_stats['failed_renames'] += 1
            return df, rename_report
    
    def _rename_with_existing_mapping(self, 
                                    df: pd.DataFrame, 
                                    file_type: str, 
                                    rename_report: Dict[str, Any],
                                    original_file_type: str = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Rename using existing column mapping configuration"""
        existing_mappings = self.ml_mapper.column_settings[file_type]
        original_columns = list(df.columns)
        
        # Direct mappings that exist
        direct_mappings = {}
        missing_columns = []
        
        for source_col in original_columns:
            if source_col in existing_mappings:
                direct_mappings[source_col] = existing_mappings[source_col]
            else:
                # Try to find similar column using ML
                suggestions = self.ml_mapper._find_similar_columns(
                    source_col, 
                    set(existing_mappings.keys()), 
                    file_type
                )
                
                if suggestions and suggestions[0]['confidence'] > 70:
                    # High confidence match found
                    suggested_source = suggestions[0]['target_column']
                    if suggested_source in existing_mappings:
                        direct_mappings[source_col] = existing_mappings[suggested_source]
                        self._log(f"🎯 Mapped '{source_col}' via similarity to '{suggested_source}'")
                else:
                    missing_columns.append(source_col)
        
        # Apply mappings
        if direct_mappings:
            df_renamed = df.rename(columns=direct_mappings)
            rename_report['renamed_columns'] = direct_mappings
            rename_report['auto_renamed'] = [
                {'source': k, 'target': v, 'confidence': 100} 
                for k, v in direct_mappings.items()
            ]
            self._log(f"✅ Applied existing mapping for {file_type}: {len(direct_mappings)} columns")
        else:
            df_renamed = df.copy()
        
        if missing_columns:
            rename_report['unmapped_columns'] = missing_columns
            self._log(f"⚠️ {len(missing_columns)} columns not found in existing mapping", 'warning')
        
        # Update file type if it was suggested
        if original_file_type and original_file_type != file_type:
            rename_report['file_type'] = original_file_type
            rename_report['suggested_file_type'] = file_type
        
        rename_report['success'] = True
        self.rename_stats['total_files_processed'] += 1
        self.rename_stats['auto_renamed'] += len(direct_mappings)
        
        return df_renamed, rename_report
    
    def _create_new_file_type_mapping(self, file_type: str, auto_mappings: Dict[str, str], 
                                    all_suggestions: Dict[str, List[Dict[str, Any]]]):
        """Create a new file type mapping based on auto-mappings and suggestions"""
        try:
            # Include manual review suggestions for future reference
            complete_mapping = auto_mappings.copy()
            
            # Add high-confidence manual review items (>60% confidence)
            for source_col, suggestions in all_suggestions.items():
                if source_col not in complete_mapping and suggestions:
                    best_suggestion = suggestions[0]
                    if best_suggestion['confidence'] > 60:
                        # Store as potential mapping (can be reviewed later)
                        complete_mapping[f"{source_col}_suggested"] = best_suggestion['target_column']
            
            # Save the new mapping
            success = self.ml_mapper.create_new_file_type_mapping(file_type, auto_mappings)
            
            if success:
                # Log the learning for future improvements
                self.ml_mapper.learn_from_user_mapping(file_type, auto_mappings)
                self._log(f"📚 Created new mapping configuration for: {file_type}")
            
        except Exception as e:
            self._log(f"⚠️ Could not create new mapping: {str(e)}", 'error')
    
    def batch_rename_files(self, file_data_list: List[Dict[str, Any]], 
                          confidence_threshold: float = 70.0) -> List[Dict[str, Any]]:
        """
        Batch process multiple files for column renaming
        
        Args:
            file_data_list: List of dicts with keys: 'df', 'file_type', 'file_path'
            confidence_threshold: Confidence threshold for auto-rename
            
        Returns:
            List of processing results
        """
        results = []
        
        self._log(f"🔄 Starting batch rename for {len(file_data_list)} files...")
        
        for i, file_data in enumerate(file_data_list, 1):
            df = file_data['df']
            file_type = file_data['file_type']
            file_path = file_data.get('file_path', f'File_{i}')
            
            self._log(f"\\n📁 Processing file {i}/{len(file_data_list)}: {file_path}")
            
            df_renamed, report = self.auto_rename_dataframe_columns(
                df, file_type, confidence_threshold
            )
            
            results.append({
                'file_path': file_path,
                'original_df': df,
                'renamed_df': df_renamed,
                'report': report
            })
        
        # Print batch summary
        self._print_batch_summary()
        
        return results
    
    def _print_batch_summary(self):
        """Print summary of batch processing statistics"""
        stats = self.rename_stats
        self._log("\\n" + "=" * 60)
        self._log("📊 Batch Processing Summary")
        self._log("=" * 60)
        self._log(f"Files processed: {stats['total_files_processed']}")
        self._log(f"Columns auto-renamed: {stats['auto_renamed']}")
        self._log(f"Manual review needed: {stats['manual_review_required']}")
        self._log(f"Failed operations: {stats['failed_renames']}")
        
        if stats['total_files_processed'] > 0:
            success_rate = ((stats['total_files_processed'] - stats['failed_renames']) / 
                          stats['total_files_processed']) * 100
            self._log(f"Success rate: {success_rate:.1f}%")
        
        self._log("=" * 60)
    
    def validate_renamed_dataframe(self, df: pd.DataFrame, file_type: str) -> Dict[str, Any]:
        """
        Validate that the renamed DataFrame matches the expected schema
        
        Args:
            df: Renamed DataFrame
            file_type: Expected file type
            
        Returns:
            Validation report
        """
        validation_report = {
            'valid': False,
            'file_type': file_type,
            'expected_columns': [],
            'actual_columns': list(df.columns),
            'missing_columns': [],
            'extra_columns': [],
            'column_count_match': False
        }
        
        try:
            if file_type in self.ml_mapper.column_settings:
                expected_columns = set(self.ml_mapper.column_settings[file_type].values())
                actual_columns = set(df.columns)
                
                validation_report['expected_columns'] = list(expected_columns)
                validation_report['missing_columns'] = list(expected_columns - actual_columns)
                validation_report['extra_columns'] = list(actual_columns - expected_columns)
                validation_report['column_count_match'] = len(expected_columns) == len(actual_columns)
                
                # Check if all expected columns are present
                validation_report['valid'] = len(validation_report['missing_columns']) == 0
                
                if validation_report['valid']:
                    self._log(f"✅ DataFrame validation passed for {file_type}")
                else:
                    self._log(f"⚠️ DataFrame validation issues found for {file_type}", 'warning')
                    if validation_report['missing_columns']:
                        self._log(f"   Missing: {validation_report['missing_columns']}", 'warning')
                    if validation_report['extra_columns']:
                        self._log(f"   Extra: {validation_report['extra_columns']}", 'warning')
            else:
                self._log(f"⚠️ No validation schema found for file type: {file_type}", 'warning')
                
        except Exception as e:
            self._log(f"❌ Validation error: {str(e)}", 'error')
            validation_report['error'] = str(e)
        
        return validation_report
    
    def export_rename_report(self, rename_reports: List[Dict[str, Any]], 
                           output_path: str = None) -> str:
        """
        Export detailed rename reports to JSON file
        
        Args:
            rename_reports: List of rename reports
            output_path: Output file path (optional)
            
        Returns:
            Path to exported file
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"rename_report_{timestamp}.json"
        
        try:
            report_data = {
                'export_timestamp': datetime.now().isoformat(),
                'total_reports': len(rename_reports),
                'statistics': self.rename_stats,
                'reports': rename_reports
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            self._log(f"📄 Rename report exported to: {output_path}")
            return output_path
            
        except Exception as e:
            self._log(f"❌ Error exporting report: {str(e)}", 'error')
            return None
    
    def reset_statistics(self):
        """Reset rename statistics"""
        self.rename_stats = {
            'total_files_processed': 0,
            'total_columns_renamed': 0,
            'auto_renamed': 0,
            'manual_review_required': 0,
            'failed_renames': 0
        }
        self._log("📊 Statistics reset")
    
    def get_mapping_suggestions_interactive(self, df: pd.DataFrame, 
                                          file_type: str) -> Dict[str, str]:
        """
        Get mapping suggestions in an interactive format (for GUI integration)
        
        Args:
            df: Input DataFrame
            file_type: File type
            
        Returns:
            Dictionary suitable for GUI display
        """
        columns = list(df.columns)
        suggestions = self.ml_mapper.suggest_mappings_for_new_file(columns, file_type)
        
        interactive_data = {
            'file_type': file_type,
            'total_columns': len(columns),
            'columns_with_suggestions': len(suggestions),
            'column_mappings': {}
        }
        
        for column in columns:
            if column in suggestions and suggestions[column]:
                interactive_data['column_mappings'][column] = {
                    'suggestions': suggestions[column][:5],  # Top 5 suggestions
                    'recommended': suggestions[column][0]['target_column'],
                    'confidence': suggestions[column][0]['confidence']
                }
            else:
                interactive_data['column_mappings'][column] = {
                    'suggestions': [],
                    'recommended': None,
                    'confidence': 0
                }
        
        return interactive_data