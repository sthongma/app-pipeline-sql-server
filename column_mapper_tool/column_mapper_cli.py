#!/usr/bin/env python3
"""
Column Mapper CLI Tool
Independent CLI for ML-enhanced column mapping and missing column detection

Usage: python column_mapper_cli.py [folder_path]
"""

import argparse
import json
import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pandas as pd

# Setup paths for imports
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

# Import main program services first (before local services to avoid namespace conflict)
sys.path.insert(0, parent_dir)
from services.file.file_reader_service import FileReaderService  
from constants import PathConstants
from config.json_manager import json_manager

# Import local services with explicit path manipulation
import importlib.util
spec = importlib.util.spec_from_file_location("ml_column_mapper", os.path.join(current_dir, "services", "ml_column_mapper.py"))
ml_mapper_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ml_mapper_module)
MLColumnMapper = ml_mapper_module.MLColumnMapper


class ColumnMapperCLI:
    """
    CLI tool for ML-enhanced column mapping
    
    Features:
    - Detect missing columns in files
    - Suggest new mappings using ML
    - Interactive user selection
    - Update column_settings.json
    """
    
    def __init__(self):
        # Setup logging
        self.setup_logging()
        
        self.ml_mapper = MLColumnMapper(log_callback=self.log)
        self.file_reader = FileReaderService(log_callback=self.log)
        
    def setup_logging(self):
        """Setup logging to both console and file"""
        # Import constants for log file path
        from .constants import PathConstants
        
        # Create logger
        self.logger = logging.getLogger('ColumnMapperCLI')
        self.logger.setLevel(logging.INFO)
        
        # Clear existing handlers to avoid duplication
        self.logger.handlers.clear()
        
        # Create log directory if it doesn't exist
        log_file = PathConstants.TOOL_LOG_FILE
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # File handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # Simple formatter for console
        console_formatter = logging.Formatter(
            '[%(asctime)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Log startup message
        self.logger.info("="*50)
        self.logger.info("Column Mapper CLI Started")
        self.logger.info("="*50)
        
    def log(self, message: str, level: str = 'info'):
        """Enhanced logging function with file and console output"""
        if hasattr(self, 'logger'):
            if level.lower() == 'error':
                self.logger.error(message)
            elif level.lower() == 'warning':
                self.logger.warning(message)
            elif level.lower() == 'debug':
                self.logger.debug(message)
            else:
                self.logger.info(message)
        else:
            # Fallback to simple print if logger not initialized
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    def find_missing_columns(self, file_path: str, file_type: str) -> Dict[str, List[str]]:
        """
        Find missing columns by comparing file columns with expected mapping
        
        Args:
            file_path: Path to the file to analyze
            file_type: Detected or specified file type
            
        Returns:
            Dict with missing and extra columns
        """
        try:
            # Read file columns
            if file_path.lower().endswith('.csv'):
                df_peek = pd.read_csv(file_path, nrows=0)
            else:
                df_peek = pd.read_excel(file_path, nrows=0)
            
            actual_columns = list(df_peek.columns)
            
            # Get expected columns from settings
            expected_mapping = self.ml_mapper.column_settings.get(file_type, {})
            expected_columns = list(expected_mapping.keys())
            
            # Find differences
            missing_columns = [col for col in expected_columns if col not in actual_columns]
            extra_columns = [col for col in actual_columns if col not in expected_columns]
            
            return {
                'missing': missing_columns,
                'extra': extra_columns,
                'actual': actual_columns,
                'expected': expected_columns
            }
            
        except Exception as e:
            self.log(f"Error analyzing file {file_path}: {str(e)}", 'error')
            return {'missing': [], 'extra': [], 'actual': [], 'expected': []}
    
    def suggest_mappings_for_missing_columns(self, missing_columns: List[str], 
                                           extra_columns: List[str], 
                                           file_type: str) -> Dict[str, List[Dict]]:
        """
        Use ML to suggest mappings for missing columns
        
        Args:
            missing_columns: Columns that are expected but not found
            extra_columns: Columns that exist but not in mapping
            file_type: File type for context
            
        Returns:
            Dictionary of suggestions
        """
        suggestions = {}
        
        for missing_col in missing_columns:
            # Find suggestions from extra columns
            col_suggestions = self.ml_mapper._find_similar_columns(
                missing_col, set(extra_columns), file_type
            )
            
            if col_suggestions:
                suggestions[missing_col] = col_suggestions
        
        return suggestions
    
    def interactive_mapping_selection(self, suggestions: Dict[str, List[Dict]]) -> Dict[str, str]:
        """
        Interactive selection of column mappings
        
        Args:
            suggestions: ML suggestions for each missing column
            
        Returns:
            Selected mappings {missing_column: selected_extra_column}
        """
        selected_mappings = {}
        
        print("\n" + "="*60)
        print("MISSING COLUMN MAPPING SUGGESTIONS")
        print("="*60)
        
        for missing_col, sug_list in suggestions.items():
            print(f"\nMissing column: '{missing_col}'")
            print("Suggestions:")
            
            # Show suggestions with numbers
            for i, sug in enumerate(sug_list, 1):
                confidence_level = "HIGH" if sug['confidence'] > 70 else "MED" if sug['confidence'] > 50 else "LOW"
                print(f"  {i}. {sug['target_column']} ({sug['confidence']}% - {confidence_level})")
                print(f"     Reason: {sug['reasoning']}")
            
            # User selection
            while True:
                try:
                    choice = input(f"\nSelect mapping for '{missing_col}' (1-{len(sug_list)}, s=skip, c=custom): ").strip().lower()
                    
                    if choice == 's':
                        print(f"Skipped mapping for '{missing_col}'")
                        break
                    elif choice == 'c':
                        custom_col = input("Enter custom column name: ").strip()
                        if custom_col:
                            selected_mappings[missing_col] = custom_col
                            print(f"Custom mapping: '{missing_col}' -> '{custom_col}'")
                        break
                    else:
                        choice_num = int(choice)
                        if 1 <= choice_num <= len(sug_list):
                            selected_col = sug_list[choice_num - 1]['target_column']
                            selected_mappings[missing_col] = selected_col
                            print(f"Selected: '{missing_col}' -> '{selected_col}'")
                            break
                        else:
                            print("Invalid choice. Please try again.")
                except ValueError:
                    print("Invalid input. Please enter a number, 's', or 'c'.")
        
        return selected_mappings
    
    def update_column_settings(self, file_type: str, new_mappings: Dict[str, str]) -> bool:
        """
        Update column_settings.json with new mappings
        
        Args:
            file_type: File type to update
            new_mappings: New column mappings {old_key: new_key}
            
        Returns:
            Success status
        """
        try:
            # Load current settings
            settings_file = PathConstants.COLUMN_SETTINGS_FILE
            with open(settings_file, 'r', encoding='utf-8') as f:
                current_settings = json.load(f)
            
            # Update the mappings (change keys, keep values)
            if file_type in current_settings:
                current_mapping = current_settings[file_type]
                updated_mapping = {}
                
                # Copy existing mappings
                for old_key, value in current_mapping.items():
                    # If this key should be renamed
                    if old_key in new_mappings:
                        new_key = new_mappings[old_key]
                        updated_mapping[new_key] = value
                        self.log(f"Updated mapping: '{old_key}' -> '{new_key}': '{value}'")
                    else:
                        updated_mapping[old_key] = value
                
                current_settings[file_type] = updated_mapping
                
                # Save updated settings
                with open(settings_file, 'w', encoding='utf-8') as f:
                    json.dump(current_settings, f, ensure_ascii=False, indent=2)
                
                self.log(f"Successfully updated {len(new_mappings)} mappings in column_settings.json")
                return True
            else:
                self.log(f"File type '{file_type}' not found in settings", 'warning')
                return False
                
        except Exception as e:
            self.log(f"Error updating column settings: {str(e)}", 'error')
            return False
    
    def process_folder(self, folder_path: str):
        """
        Process all files in the specified folder
        
        Args:
            folder_path: Path to folder containing files to process
        """
        self.log(f"Processing folder: {folder_path}")
        
        # Set search path and find files
        self.file_reader.set_search_path(folder_path)
        files = self.file_reader.find_data_files()
        
        total_files = len(files)
        self.log(f"Found {total_files} files to process")
        
        if total_files == 0:
            print("No Excel or CSV files found in the specified folder.")
            return
        
        # Process each file
        all_files = files
        
        for file_path in all_files:
            self.log(f"Analyzing file: {os.path.basename(file_path)}")
            
            # Detect file type
            file_type = self.file_reader.detect_file_type(file_path)
            
            if not file_type:
                self.log(f"Could not detect file type for {os.path.basename(file_path)}", 'warning')
                continue
            
            self.log(f"Detected file type: {file_type}")
            
            # Find missing columns
            column_analysis = self.find_missing_columns(file_path, file_type)
            
            if not column_analysis['missing']:
                self.log("No missing columns found")
                continue
            
            print(f"\n{'='*60}")
            print(f"FILE: {os.path.basename(file_path)}")
            print(f"TYPE: {file_type}")
            print(f"MISSING COLUMNS: {len(column_analysis['missing'])}")
            print(f"EXTRA COLUMNS: {len(column_analysis['extra'])}")
            print(f"{'='*60}")
            
            # Get ML suggestions
            suggestions = self.suggest_mappings_for_missing_columns(
                column_analysis['missing'],
                column_analysis['extra'],
                file_type
            )
            
            if not suggestions:
                self.log("No mapping suggestions available", 'warning')
                continue
            
            # Interactive selection
            selected_mappings = self.interactive_mapping_selection(suggestions)
            
            if selected_mappings:
                # Confirm before updating
                print(f"\nSelected mappings for {file_type}:")
                for old_key, new_key in selected_mappings.items():
                    print(f"  '{old_key}' -> '{new_key}'")
                
                confirm = input("\nUpdate column_settings.json with these mappings? (y/n): ").strip().lower()
                
                if confirm == 'y':
                    success = self.update_column_settings(file_type, selected_mappings)
                    if success:
                        print("Settings updated successfully!")
                    else:
                        print("Failed to update settings.")
                else:
                    print("Settings not updated.")
    
    def get_last_search_path(self):
        """Get last search path from main program settings"""
        try:
            # Load app_settings.json directly
            app_settings_file = os.path.join(os.path.dirname(current_dir), 'config', 'app_settings.json')
            if os.path.exists(app_settings_file):
                with open(app_settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    return settings.get('last_search_path', '')
            return ''
        except Exception as e:
            self.log(f"Error loading last search path: {e}", 'error')
            return ''

    def save_last_search_path(self, path):
        """Save last search path to main program settings"""
        try:
            # Save to app_settings.json directly
            app_settings_file = os.path.join(os.path.dirname(current_dir), 'config', 'app_settings.json')
            settings = {}
            
            # Load existing settings if file exists
            if os.path.exists(app_settings_file):
                with open(app_settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            
            # Update last_search_path
            settings['last_search_path'] = path
            
            # Save back to file
            os.makedirs(os.path.dirname(app_settings_file), exist_ok=True)
            with open(app_settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
                
            return True
        except Exception as e:
            self.log(f"Error saving last search path: {e}", 'error')
            return False
    
    def run(self, args):
        """Main entry point"""
        folder_path = args.folder
        
        # If no folder specified, try to use last folder from main program
        if not folder_path:
            folder_path = self.get_last_search_path()
            if folder_path and os.path.exists(folder_path):
                self.log(f"Using last folder from main program: {folder_path}")
            else:
                try:
                    folder_path = input("Enter folder path to process: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nOperation cancelled.")
                    return
        
        if not folder_path:
            print("Error: No folder path provided.")
            return
            
        if not os.path.exists(folder_path):
            print(f"Error: Folder '{folder_path}' does not exist.")
            return
        
        if not os.path.isdir(folder_path):
            print(f"Error: '{folder_path}' is not a directory.")
            return
        
        # Save the path for next time
        self.save_last_search_path(folder_path)
        
        self.process_folder(folder_path)
        self.log("Processing complete!")
        self.log("="*50)
        self.log("Column Mapper CLI Session Ended")
        self.log("="*50)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="ML-enhanced column mapping tool for missing column detection"
    )
    parser.add_argument(
        'folder', 
        nargs='?', 
        help='Folder path containing Excel/CSV files to process (if not specified, uses last folder from main program)'
    )
    
    args = parser.parse_args()
    
    # Import datetime here to avoid issues
    from datetime import datetime
    
    cli = ColumnMapperCLI()
    cli.run(args)


if __name__ == '__main__':
    main()