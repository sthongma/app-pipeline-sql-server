# SQL Server Data Pipeline

**Simple Excel/CSV to SQL Server ETL tool - No coding required**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A user-friendly desktop application that simplifies importing Excel and CSV files into SQL Server databases with automatic data cleaning, validation, and file management.

## Features

✅ **Multi-format Support**: Excel (.xlsx, .xls) and CSV files  
✅ **Flexible Column Mapping**: Customize column names and data types  
✅ **Automatic Data Validation**: Built-in data cleaning and type conversion  
✅ **Schema Management**: Automatic database schema creation and validation  
✅ **File Organization**: Automatic file management after processing  
✅ **GUI Interface**: Easy-to-use desktop application  
✅ **CLI Support**: Command-line interface for automation  
✅ **Security**: Secure database connections with Windows/SQL authentication  
✅ **Performance**: Optimized for large files with chunked processing  

## Quick Start

### 1. Installation

```bash
git clone https://github.com/ST-415/PIPELINE_SQLSERVER.git
cd PIPELINE_SQLSERVER

# Install dependencies
pip install -r requirements.txt

# Run setup script
python install_requirements.py
```

### 2. Database Configuration

Edit the generated `.env` file:

```env
# Database connection settings
DB_SERVER=localhost\SQLEXPRESS
DB_NAME=YourDatabase

# For Windows Authentication (recommended)
DB_USERNAME=
DB_PASSWORD=

# For SQL Server Authentication
# DB_USERNAME=your_username
# DB_PASSWORD=your_password
```

### 3. Run the Application

```bash
# GUI Application
python pipeline_gui_app.py

# Or use the Windows batch file
run_pipeline_gui.bat
```

### 4. CLI for Automation

```bash
# Process all files in a folder automatically
python auto_process_cli.py "C:\path\to\your\data"

# Or use the Windows batch file
run_auto_process.bat
```

## How It Works

1. **Select Data Folder**: Choose the folder containing your Excel/CSV files
2. **Configure File Types**: Set up column mappings and data types for each file type
3. **Process Files**: The application will:
   - Automatically detect file types
   - Clean and validate data
   - Upload to SQL Server with proper data types
   - Move processed files to organized folders
   - Add upload timestamps for incremental updates

## System Requirements

- **Python**: 3.8 or higher
- **Database**: SQL Server or SQL Server Express
- **ODBC Driver**: ODBC Driver 17 or 18 for SQL Server
- **Operating System**: Windows (recommended for GUI)

## Configuration

The application uses JSON configuration files for flexible data mapping:

### Column Mapping (`config/column_settings.json`)
```json
{
    "sales_data": {
        "Date": "sale_date",
        "Product": "product_name",
        "Amount": "amount",
        "Customer": "customer_name"
    }
}
```

### Data Types (`config/dtype_settings.json`)
```json
{
    "sales_data": {
        "Date": "DATE",
        "Product": "NVARCHAR(255)",
        "Amount": "DECIMAL(18,2)",
        "Customer": "NVARCHAR(500)"
    }
}
```

## Architecture

The application follows a clean service-oriented architecture:

- **UI Layer**: Desktop interface using CustomTkinter
- **Orchestrator Services**: High-level coordination services
- **Modular Services**: Specialized services for database, file operations, and utilities
- **Configuration Layer**: Centralized settings management

## Use Cases

### Daily Data Processing
Set up automated daily processing using Windows Task Scheduler:

```batch
@echo off
python auto_process_cli.py "C:\daily\reports"
```

### Large File Processing
The application automatically handles large files using chunked processing and memory optimization.

### Multiple File Types
Configure different column mappings and data types for various file formats in your data pipeline.

## Troubleshooting

### Database Connection Issues
1. Verify SQL Server is running
2. Check ODBC Driver installation
3. Validate `.env` file configuration
4. Test connection using SQL Server Management Studio

### File Reading Issues
1. Close Excel files before processing
2. Check file permissions
3. Verify file formats (.xlsx, .xls, .csv)

### Performance Issues
1. Use CLI for large file processing
2. Close unnecessary applications
3. Check available disk space
4. Consider breaking large files into smaller chunks

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: Report bugs and request features through GitHub Issues
- **Documentation**: Complete documentation available in the repository
- **Updates**: Check CHANGELOG.md for version history

---

**Ready to streamline your data pipeline!** 🚀