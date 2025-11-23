#!/usr/bin/env python
"""
Configuration Migration Script

Migrates JSON config files from old structure to new structure:
- Old: Multiple separate config files in config/
- New: Single app_settings.json + file_types/ directory

This script:
1. Creates backup of all existing config files
2. Migrates app_settings (merges folder and file_management configs)
3. Migrates column_settings and dtype_settings to file_types/*.json
4. Validates migration
5. Optionally cleans up old files
"""

import json
import os
import shutil
import sys
from datetime import datetime
from typing import Dict, Any, List, Tuple

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from constants import PathConstants


class ConfigMigrator:
    """Handles migration from old to new config structure"""

    def __init__(self, dry_run: bool = False):
        """
        Initialize migrator

        Args:
            dry_run: If True, only simulate migration without making changes
        """
        self.dry_run = dry_run
        self.backup_dir = None
        self.migration_log: List[str] = []

    def log(self, message: str) -> None:
        """Log a message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        self.migration_log.append(log_msg)

    def create_backup(self) -> bool:
        """Create backup of all existing config files"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.backup_dir = os.path.join(PathConstants.CONFIG_DIR, f"backup_migration_{timestamp}")

            if self.dry_run:
                self.log(f"[DRY RUN] Would create backup at: {self.backup_dir}")
                return True

            os.makedirs(self.backup_dir, exist_ok=True)

            # Backup all JSON files in config directory
            config_files = [f for f in os.listdir(PathConstants.CONFIG_DIR)
                          if f.endswith('.json') and os.path.isfile(os.path.join(PathConstants.CONFIG_DIR, f))]

            for filename in config_files:
                src = os.path.join(PathConstants.CONFIG_DIR, filename)
                dst = os.path.join(self.backup_dir, filename)
                shutil.copy2(src, dst)
                self.log(f"✓ Backed up: {filename}")

            self.log(f"✓ Backup created at: {self.backup_dir}")
            return True

        except Exception as e:
            self.log(f"✗ Backup failed: {e}")
            return False

    def load_json(self, filepath: str) -> Dict[str, Any]:
        """Load JSON file safely"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.log(f"Warning: Could not load {filepath}: {e}")
        return {}

    def save_json(self, filepath: str, data: Dict[str, Any]) -> bool:
        """Save JSON file safely"""
        try:
            if self.dry_run:
                self.log(f"[DRY RUN] Would save to: {filepath}")
                return True

            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            self.log(f"✗ Failed to save {filepath}: {e}")
            return False

    def migrate_app_settings(self) -> bool:
        """Migrate app_settings.json (merge with folder and file_management configs)"""
        self.log("\n=== Migrating app_settings.json ===")

        # Load existing configs
        app_settings = self.load_json(os.path.join(PathConstants.CONFIG_DIR, 'app_settings.json'))
        input_folder = self.load_json(os.path.join(PathConstants.CONFIG_DIR, 'input_folder_config.json'))
        output_folder = self.load_json(os.path.join(PathConstants.CONFIG_DIR, 'output_folder_config.json'))
        log_folder = self.load_json(os.path.join(PathConstants.CONFIG_DIR, 'log_folder_config.json'))
        file_mgmt = self.load_json(os.path.join(PathConstants.CONFIG_DIR, 'file_management_settings.json'))

        # Create new app_settings structure
        new_app_settings = {
            "window_size": app_settings.get("window_size", [900, 780]),
            "theme": app_settings.get("theme", "system"),
            "backup_enabled": app_settings.get("backup_enabled", True),
            "log_level": app_settings.get("log_level", "INFO"),
            "folders": {
                "input_folder": input_folder.get("folder_path", ""),
                "output_folder": output_folder.get("folder_path", ""),
                "log_folder": log_folder.get("log_folder_path", "")
            },
            "file_management": {
                "auto_move_enabled": file_mgmt.get("auto_move_enabled", True),
                "organize_by_date": file_mgmt.get("organize_by_date", False)
            }
        }

        # Save new app_settings
        app_settings_path = os.path.join(PathConstants.CONFIG_DIR, 'app_settings.json')
        if self.save_json(app_settings_path, new_app_settings):
            self.log("✓ Migrated app_settings.json")
            self.log(f"  - Merged input_folder: {new_app_settings['folders']['input_folder']}")
            self.log(f"  - Merged output_folder: {new_app_settings['folders']['output_folder']}")
            self.log(f"  - Merged log_folder: {new_app_settings['folders']['log_folder']}")
            self.log(f"  - Merged file_management settings")
            return True

        return False

    def migrate_file_types(self) -> Tuple[bool, int]:
        """
        Migrate column_settings and dtype_settings to file_types/*.json

        Returns:
            Tuple of (success, count of file types migrated)
        """
        self.log("\n=== Migrating File Types ===")

        # Load legacy settings
        column_settings = self.load_json(PathConstants.COLUMN_SETTINGS_FILE)
        dtype_settings = self.load_json(PathConstants.DTYPE_SETTINGS_FILE)

        if not column_settings and not dtype_settings:
            self.log("No file types to migrate (column_settings and dtype_settings are empty)")
            return True, 0

        # Get all file types from both settings
        file_types = set(list(column_settings.keys()) + list(dtype_settings.keys()))

        if not file_types:
            self.log("No file types found")
            return True, 0

        # Create file_types directory
        if not self.dry_run:
            os.makedirs(PathConstants.FILE_TYPES_DIR, exist_ok=True)

        # Migrate each file type
        migrated_count = 0
        for file_type in sorted(file_types):
            columns = column_settings.get(file_type, {})
            dtypes = dtype_settings.get(file_type, {})

            file_type_config = {
                "columns": columns,
                "dtypes": dtypes
            }

            file_path = os.path.join(PathConstants.FILE_TYPES_DIR, f"{file_type}.json")
            if self.save_json(file_path, file_type_config):
                self.log(f"✓ Migrated file type: {file_type}")
                self.log(f"  - {len(columns)} column mappings")
                self.log(f"  - {len(dtypes)} dtype mappings")
                migrated_count += 1

        self.log(f"\n✓ Total file types migrated: {migrated_count}")
        return True, migrated_count

    def validate_migration(self) -> bool:
        """Validate that migration was successful"""
        self.log("\n=== Validating Migration ===")

        if self.dry_run:
            self.log("[DRY RUN] Skipping validation")
            return True

        all_valid = True

        # Check app_settings.json exists and has correct structure
        app_settings_path = os.path.join(PathConstants.CONFIG_DIR, 'app_settings.json')
        if os.path.exists(app_settings_path):
            app_settings = self.load_json(app_settings_path)
            if 'folders' in app_settings and 'file_management' in app_settings:
                self.log("✓ app_settings.json has correct structure")
            else:
                self.log("✗ app_settings.json is missing required keys")
                all_valid = False
        else:
            self.log("✗ app_settings.json not found")
            all_valid = False

        # Check file_types directory
        if os.path.exists(PathConstants.FILE_TYPES_DIR):
            file_types = [f.replace('.json', '') for f in os.listdir(PathConstants.FILE_TYPES_DIR)
                         if f.endswith('.json')]
            self.log(f"✓ file_types/ directory exists with {len(file_types)} file types")
        else:
            self.log("Warning: file_types/ directory not found")

        return all_valid

    def cleanup_old_files(self) -> bool:
        """Remove old config files after successful migration"""
        self.log("\n=== Cleaning Up Old Files ===")

        if self.dry_run:
            self.log("[DRY RUN] Would remove old config files")
            return True

        old_files = [
            'input_folder_config.json',
            'output_folder_config.json',
            'log_folder_config.json',
            'file_management_settings.json',
            'column_settings.json',
            'dtype_settings.json'
        ]

        for filename in old_files:
            filepath = os.path.join(PathConstants.CONFIG_DIR, filename)
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    self.log(f"✓ Removed: {filename}")
                except Exception as e:
                    self.log(f"✗ Could not remove {filename}: {e}")
                    return False

        return True

    def run(self, cleanup: bool = False) -> bool:
        """
        Run the full migration

        Args:
            cleanup: If True, remove old config files after migration

        Returns:
            bool: Success status
        """
        self.log("=" * 60)
        self.log("CONFIG MIGRATION SCRIPT")
        self.log("=" * 60)

        if self.dry_run:
            self.log("\n*** DRY RUN MODE - No changes will be made ***\n")

        # Step 1: Create backup
        if not self.create_backup():
            self.log("\n✗ Migration failed: Could not create backup")
            return False

        # Step 2: Migrate app_settings
        if not self.migrate_app_settings():
            self.log("\n✗ Migration failed: app_settings migration failed")
            return False

        # Step 3: Migrate file types
        success, count = self.migrate_file_types()
        if not success:
            self.log("\n✗ Migration failed: file types migration failed")
            return False

        # Step 4: Validate
        if not self.validate_migration():
            self.log("\n✗ Migration failed: validation failed")
            return False

        # Step 5: Cleanup (optional)
        if cleanup and not self.dry_run:
            if not self.cleanup_old_files():
                self.log("\nWarning: Cleanup had some errors (migration still successful)")

        # Summary
        self.log("\n" + "=" * 60)
        if self.dry_run:
            self.log("DRY RUN COMPLETE")
        else:
            self.log("✓ MIGRATION SUCCESSFUL!")
            if self.backup_dir:
                self.log(f"\nBackup location: {self.backup_dir}")
            self.log(f"Migrated {count} file types")

        self.log("=" * 60)

        return True


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Migrate config files to new structure')
    parser.add_argument('--dry-run', action='store_true',
                       help='Simulate migration without making changes')
    parser.add_argument('--cleanup', action='store_true',
                       help='Remove old config files after migration')

    args = parser.parse_args()

    migrator = ConfigMigrator(dry_run=args.dry_run)
    success = migrator.run(cleanup=args.cleanup)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
