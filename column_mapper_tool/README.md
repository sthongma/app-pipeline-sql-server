# Column Mapper CLI Tool

Independent CLI tool for ML-enhanced column mapping and missing column detection with comprehensive logging and dual-mode operation.

## 🚀 Features

- **🔍 Missing Column Detection**: Automatically detect columns that are expected but missing from files
- **🤖 ML-Enhanced Suggestions**: Use machine learning (sentence-transformers + scikit-learn) to suggest the best column mappings
- **⚡ Dual Mode Operation**: Interactive mode for manual selection, Auto mode for automated processing
- **📊 Comprehensive Analysis**: Detailed column analysis with confidence scores and reasoning
- **🔄 Automatic Updates**: Update `column_settings.json` with high-confidence mappings (>70%)
- **📁 Batch Processing**: Process multiple files in a folder
- **📝 Advanced Logging**: File + console logging with detailed session tracking
- **🎯 Smart Thresholds**: Configurable confidence thresholds for auto-application

## 💻 Usage

### 🖥️ Batch Files (Recommended)

```bash
# Interactive Mode - User selection required
run_column_mapper.bat

# Auto Mode - Show analysis + auto-apply high confidence mappings
run_column_mapper_auto.bat

# With specific folder
run_column_mapper.bat "C:\path\to\files"
```

### 📟 Command Line

```bash
# Interactive mode (default)
python column_mapper_tool\column_mapper_cli.py

# Auto mode (no user prompts)
python column_mapper_tool\column_mapper_cli.py --auto

# With specific folder
python column_mapper_tool\column_mapper_cli.py "C:\path\to\files"

# Auto mode with folder
python column_mapper_tool\column_mapper_cli.py "C:\path\to\files" --auto
```

### 🎮 Mode Comparison

| Feature | Interactive Mode | Auto Mode |
|---------|------------------|-----------|
| **User Input** | ✅ Required | ❌ None |
| **Show Analysis** | ✅ Detailed | ✅ Detailed |
| **ML Suggestions** | ✅ With selection | ✅ Display only |
| **Auto-Apply** | 🤔 User choice | ✅ Confidence >70% |
| **Settings Update** | 🤔 User confirmation | ✅ Automatic |
| **Best For** | Manual review | Quick analysis |

## 🔧 How It Works

### 📋 Processing Steps

1. **🔎 Scan Files**: Finds all Excel (.xlsx, .xls) and CSV files in the specified folder
2. **🏷️ Detect File Type**: Uses the main program's logic to identify file types
3. **📊 Analyze Columns**: Compares actual columns with expected columns from settings
4. **🤖 ML Analysis**: Generates intelligent mapping suggestions using:
   - **Semantic Similarity**: sentence-transformers for meaning matching
   - **String Similarity**: fuzzy matching for text similarity
   - **Context Similarity**: domain-specific keyword matching
5. **⚖️ Confidence Scoring**: Combines multiple similarity scores into confidence percentage
6. **🎯 Smart Application**: 
   - **Interactive**: User selects mappings
   - **Auto**: Auto-apply mappings with >70% confidence
7. **💾 Update Settings**: Automatically updates `column_settings.json` with new mappings
8. **📝 Logging**: Comprehensive logging to file and console

### 🧠 ML Algorithm

```python
# Combined similarity scoring
combined_score = (
    semantic_score * 0.5 +    # sentence-transformers
    string_score * 0.3 +      # fuzzy matching  
    context_score * 0.2       # domain keywords
)

# Confidence levels
🔥 HIGH: >70% (auto-applied in auto mode)
⚡ MED:  50-70% (user review recommended)  
💡 LOW:  <50% (manual review required)
```

## 📊 Example Output

### Auto Mode Analysis
```
============================================================
FILE: OrderActionReport-20250912124021.xlsx
TYPE: order_action_jst
MISSING COLUMNS: 2
EXTRA COLUMNS: 2
============================================================

🤖 Auto Mode - Showing ML suggestions:

📊 COLUMN ANALYSIS SUMMARY:
   • Missing columns (expected but not found): 2
   • Extra columns (found but not expected): 2
   • Total columns in file: 7
   • Expected columns for this file type: 7

❌ MISSING COLUMNS:
   • รหัสขั้นตอนการสั่ง
   • วันที่สร้างเอกสาร

➕ EXTRA COLUMNS:
   • รหัสขั้นตอน
   • วันที่ที่มีการสร้าง

🔍 ML MAPPING SUGGESTIONS:

📌 Missing column: 'รหัสขั้นตอนการสั่ง'
   1. รหัสขั้นตอน (75.4% - 🔥 HIGH)
      📝 Reason: ความหมายคล้ายกันมาก | ชื่อคล้ายกัน | ทั้งคู่เป็นรหัสขั้นตอน

✅ Auto-applied: 'รหัสขั้นตอนการสั่ง' → 'รหัสขั้นตอน' (75.4%)

🔄 Updating column_settings.json for order_action_jst:
   'รหัสขั้นตอนการสั่ง' → 'รหัสขั้นตอน'

✅ Settings updated automatically!
```

### Interactive Mode Selection
```
Missing column: 'รหัสสินค้า'
Suggestions:
  1. SKU (85.0% - 🔥 HIGH)
     Reason: ความหมายคล้ายกันมาก | ทั้งคู่เป็นหมายเลขอ้างอิง
  2. ProductCode (72.3% - 🔥 HIGH)  
     Reason: ความหมายคล้ายกัน | ชื่อคล้ายกัน

Select mapping for 'รหัสสินค้า' (1-2, s=skip, c=custom): 1
Selected: 'รหัสสินค้า' -> 'SKU'
```

## 📁 Files Structure

```
column_mapper_tool/
├── column_mapper_cli.py              # 🎯 Main CLI program
├── services/
│   ├── __init__.py                   # 📦 Services package
│   ├── ml_column_mapper.py           # 🤖 ML mapping service
│   └── auto_column_rename_service.py # ⚡ Auto rename service
├── constants.py                      # 🔧 Standalone constants
├── column_mapper.log                 # 📝 Session logs
├── __init__.py                       # 📦 Package init
└── README.md                         # 📖 This file
```

## 🎯 Batch Files

```
PIPELINE_SQLSERVER/
├── run_column_mapper.bat             # 🎮 Interactive mode
├── run_column_mapper_auto.bat        # ⚡ Auto mode
```

## 📋 Dependencies

### Core Dependencies (Required)
- `pandas` - Data processing
- `openpyxl` - Excel file support
- `logging` - File logging
- Main program services (file reading, type detection)

### ML Dependencies (Optional)
```bash
pip install sentence-transformers scikit-learn
```

- `sentence-transformers` - Semantic similarity matching
- `scikit-learn` - String similarity and ML utilities
- **Fallback**: Basic string matching if ML dependencies unavailable

## 📝 Logging

### Log Locations
- **File**: `column_mapper_tool/column_mapper.log`
- **Console**: Real-time output during execution

### Log Levels
- `INFO` - Normal operations, analysis results
- `WARNING` - Missing suggestions, low confidence
- `ERROR` - File errors, update failures

### Log Format
```
2024-09-12 11:26:53 - ColumnMapperCLI - INFO - ML models loaded successfully
2024-09-12 11:26:53 - MLColumnMapper - INFO - Auto-mapped 'รหัสสินค้า' -> 'SKU' (85.4%)
```

## ⚙️ Configuration

### Confidence Thresholds
- **Auto-apply threshold**: 70% (configurable in code)
- **Display threshold**: 30% (minimum to show suggestions)

### File Type Support
- **Excel**: `.xlsx`, `.xls`
- **CSV**: `.csv`
- **Auto-detection**: Based on main program logic

## 🔗 Integration

Uses the following from the main program:
- `services/file/file_reader_service.py` - File reading and type detection  
- `config/column_settings.json` - Column mapping configuration
- `config/dtype_settings.json` - Data type settings
- `config/app_settings.json` - Last search path

## 🛠️ Troubleshooting

### Common Issues

**ML Dependencies Not Found**
```
WARNING: ML dependencies not found
For enhanced ML features, install:
  pip install sentence-transformers scikit-learn
```
**Solution**: Install ML dependencies or use basic string matching mode

**No Suggestions Available**  
**Solution**: Check if file type exists in column_settings.json, verify column names

**Permission Errors**
**Solution**: Ensure write permissions to config directory

**EOFError in Batch Mode**
**Solution**: Use auto mode (`--auto` flag) for non-interactive execution