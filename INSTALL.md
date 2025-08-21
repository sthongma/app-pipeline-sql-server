# Installation Guide

This guide will help you install and set up the SQL Server Data Pipeline application.

## Prerequisites

Before installing, ensure you have:

- **Python 3.8+** installed on your system
- **SQL Server or SQL Server Express** running
- **ODBC Driver 17 or 18 for SQL Server**
- **Windows OS** (recommended for GUI features)

## Quick Installation

### Method 1: Automated Installation (Windows)

```batch
# Clone the repository
git clone https://github.com/ST-415/PIPELINE_SQLSERVER.git
cd PIPELINE_SQLSERVER

# Run automated installation
install_requirements.bat
```

### Method 2: Manual Installation

```bash
# Clone the repository
git clone https://github.com/ST-415/PIPELINE_SQLSERVER.git
cd PIPELINE_SQLSERVER

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run setup script
python install_requirements.py
```

## Configuration

1. **Database Configuration**: Edit the generated `.env` file:

```env
DB_SERVER=localhost\SQLEXPRESS
DB_NAME=YourDatabase
DB_USERNAME=
DB_PASSWORD=
```

2. **Test the Installation**:

```bash
# Test GUI application
python pipeline_gui_app.py

# Test CLI application
python auto_process_cli.py --help
```

## Verification

If installation is successful, you should see:
- ✅ All dependencies installed
- ✅ `.env` file created
- ✅ GUI application launches without errors
- ✅ Database connection test passes

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'customtkinter'`  
**Solution**: Ensure all dependencies are installed: `pip install -r requirements.txt`

**Issue**: Database connection fails  
**Solution**: 
1. Verify SQL Server is running
2. Check ODBC driver installation
3. Validate `.env` file settings

**Issue**: Permission denied errors  
**Solution**: Run command prompt as Administrator (Windows)

### Getting Help

- Check the main [README.md](README.md) for detailed documentation
- Review [CHANGELOG.md](CHANGELOG.md) for version-specific information
- Create an issue on GitHub for support

## Next Steps

After successful installation:

1. **Configure File Types**: Set up column mappings for your data files
2. **Test with Sample Data**: Process a small test file first
3. **Set Up Automation**: Use CLI for batch processing if needed

Ready to start processing your data! 🚀