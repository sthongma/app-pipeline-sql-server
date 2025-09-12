# Column Mapper CLI Tool

Independent CLI tool for ML-enhanced column mapping and missing column detection.

## Features

- **Missing Column Detection**: Automatically detect columns that are expected but missing from files
- **ML-Enhanced Suggestions**: Use machine learning to suggest the best column mappings
- **Interactive Selection**: User-friendly interface for selecting and confirming mappings
- **Automatic Updates**: Update `column_settings.json` with new mappings
- **Batch Processing**: Process multiple files in a folder

## Usage

### Command Line
```bash
python column_mapper_cli.py [folder_path]
```

### Interactive Mode
```bash
python column_mapper_cli.py
# Enter folder path when prompted
```

## How It Works

1. **Scan Files**: Finds all Excel (.xlsx, .xls) and CSV files in the specified folder
2. **Detect File Type**: Uses the main program's logic to identify file types
3. **Analyze Columns**: Compares actual columns with expected columns from settings
4. **ML Suggestions**: Generates intelligent mapping suggestions using ML algorithms
5. **User Selection**: Presents options for user to choose the best mappings
6. **Update Settings**: Automatically updates `column_settings.json` with new mappings

## Example

When a file has column "SKU" but settings expect "รหัสสินค้า":

```
Missing column: 'รหัสสินค้า'
Suggestions:
  1. SKU (85.0% - HIGH)
     Reason: ความหมายคล้ายกันมาก | ทั้งคู่เป็นหมายเลขอ้างอิง

Select mapping for 'รหัสสินค้า' (1-1, s=skip, c=custom): 1
Selected: 'รหัสสินค้า' -> 'SKU'
```

Result: `"SKU": "รหัสสินค้า"` added to column_settings.json

## Dependencies

Uses the following from the main program:
- `services/file/file_reader_service.py` - File reading and type detection
- `services/file/ml_column_mapper.py` - ML-enhanced column mapping
- `config/column_settings.json` - Column mapping configuration
- `constants.py` - Path constants

## Files Structure

```
column_mapper_tool/
├── column_mapper_cli.py      # Main CLI program
├── services/
│   ├── __init__.py
│   ├── ml_column_mapper.py   # ML mapping service (copied)
│   └── auto_column_rename_service.py  # Auto rename service (copied)
├── constants.py              # Standalone constants
├── __init__.py
└── README.md                # This file
```