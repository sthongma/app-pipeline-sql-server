# PIPELINE_SQLSERVER

ระบบ ETL (Extract, Transform, Load) ที่ออกแบบเพื่อให้ AI ทำงานได้ง่าย สำหรับประมวลผลและอัปโหลดไฟล์ Excel/CSV ไปยัง SQL Server ผ่าน GUI

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## จุดเด่นสำหรับ AI Development

🤖 **AI-Friendly Architecture**: โครงสร้างที่ชัดเจน มี type hints ครบถ้วน และ documentation ที่ดี  
📁 **Modular Design**: แยกส่วนต่างๆ ออกจากกันอย่างชัดเจน (config, services, ui, utils)  
🔧 **Centralized Configuration**: จัดการการตั้งค่าทั้งหมดจากที่เดียว  
📊 **Type Safety**: ใช้ Type hints และ dataclass เพื่อความปลอดภัยของข้อมูล  
🛠️ **Extensible**: ง่ายต่อการขยายและปรับปรุงโดย AI  
🏗️ **Service-Oriented Architecture**: แยก business logic เป็น modular services ที่สามารถใช้งานแยกหรือรวมกันได้  

## คุณสมบัติหลัก

✅ รองรับไฟล์ Excel (.xlsx) และ CSV  
✅ การตั้งค่าคอลัมน์และประเภทข้อมูลแบบยืดหยุ่น  
✅ ตรวจจับประเภทไฟล์อัตโนมัติ  
✅ การตรวจสอบและทำความสะอาดข้อมูลอัตโนมัติ  
✅ การตรวจสอบและแก้ไขชนิดข้อมูลอัตโนมัติ  
✅ อัปโหลดข้อมูลไปยัง SQL Server พร้อม schema validation  
✅ ย้ายไฟล์ที่ประมวลผลแล้วไปยังโฟลเดอร์ที่จัดระเบียบ  
✅ GUI ที่ใช้งานง่ายด้วย CustomTkinter  
✅ เตรียมรองรับ CLI (จะเพิ่มภายหลัง)  
✅ การตรวจสอบสิทธิ์และความปลอดภัย  
✅ Error handling และ logging ที่ครบถ้วน  
✅ Performance optimization สำหรับไฟล์ขนาดใหญ่

## โครงสร้างโปรเจกต์

```
PIPELINE_SQLSERVER/
├── __init__.py                      # Main package initialization
├── constants.py                     # ค่าคงที่ทั้งหมดของระบบ
├── requirements.txt                 # Dependencies
├── pyproject.toml                   # Project configuration
├── install_requirements.bat         # สคริปต์ติดตั้งสำหรับ Windows
├── run_pipeline_gui.bat             # สคริปรัน GUI สำหรับ Windows
│
├── config/                          # การตั้งค่าและ configuration
│   ├── __init__.py
│   ├── database.py                  # การจัดการการเชื่อมต่อฐานข้อมูล
│   └── settings.py                  # Settings manager แบบรวมศูนย์
│
├── services/                        # Business logic และ services
│   ├── __init__.py
│   ├── database_service.py          # Orchestrator บริการฐานข้อมูล (รวม modular services)
│   ├── file_service.py              # Orchestrator บริการไฟล์ (รวม modular services)
│   ├── permission_checker_service.py# ตรวจสอบสิทธิ์ฐานข้อมูล
│   ├── preload_service.py           # โหลดการตั้งค่า/ประเภทไฟล์ล่วงหน้า
│   │
│   ├── database/                    # Modular Database Services
│   │   ├── __init__.py
│   │   ├── connection_service.py    # จัดการการเชื่อมต่อฐานข้อมูล
│   │   ├── schema_service.py        # จัดการ schema และ table
│   │   ├── data_validation_service.py # ตรวจสอบข้อมูลใน staging
│   │   └── data_upload_service.py   # อัปโหลดข้อมูลไปฐานข้อมูล
│   │
│   ├── file/                        # Modular File Services
│   │   ├── __init__.py
│   │   ├── file_reader_service.py   # อ่านและตรวจจับไฟล์
│   │   ├── data_processor_service.py# ประมวลผลและตรวจสอบข้อมูล
│   │   └── file_management_service.py # จัดการไฟล์
│   │
│   └── README.md                    # เอกสาร services โดยละเอียด
│
├── ui/                              # User interface
│   ├── __init__.py
│   ├── login_window.py              # หน้าต่างล็อกอิน/ตั้งค่าฐานข้อมูล
│   ├── main_window.py               # หน้าต่างหลัก GUI
│   ├── loading_dialog.py            # หน้าต่างโหลด/แสดงความคืบหน้าเบื้องหลัง
│   ├── components/                  # UI components
│   │   ├── __init__.py
│   │   ├── file_list.py
│   │   ├── progress_bar.py
│   │   └── status_bar.py
│   ├── handlers/                    # จัดการ events/logic ของ UI
│   │   ├── __init__.py
│   │   ├── file_handler.py
│   │   └── settings_handler.py
│   └── tabs/                        # แท็บต่างๆ ของ UI
│       ├── __init__.py
│       ├── main_tab.py
│       ├── log_tab.py
│       └── settings_tab.py
│
├── utils/                           # Utility functions
│   ├── __init__.py
│   ├── helpers.py                   # Helper functions
│   ├── logger.py                    # Logging helpers/handlers
│   └── validators.py                # Validation functions
│
├── test_column_mapping.py           # ตัวอย่างไฟล์ทดสอบ
└── pipeline_gui_app.py              # GUI application entry point
```

## การติดตั้ง

### ความต้องการของระบบ
- Python 3.8+ (แนะนำ 3.9+)
- SQL Server หรือ SQL Server Express
- ODBC Driver 17 หรือ 18 for SQL Server
- Windows OS (สำหรับ GUI)

### ขั้นตอนการติดตั้ง

1. **Clone repository**:
```bash
git clone <repository-url>
cd PIPELINE_SQLSERVER
```

2. **ติดตั้ง dependencies (Windows แนะนำใช้สคริปต์อัตโนมัติ)**:
```bash
# วิธีแนะนำ (Windows)
install_requirements.bat

# หรือแบบปกติ
pip install -r requirements.txt

# ติดตั้งเป็น package (ถ้าต้องการ)
pip install -e .
```

3. **ติดตั้ง development dependencies** (optional):
```bash
pip install -e ".[dev]"
```

## การใช้งาน

### GUI Application

```bash
# วิธีแนะนำ (Windows)
run_pipeline_gui.bat

# หรือรันด้วย Python โดยตรง
python pipeline_gui_app.py
```

หมายเหตุ: เวอร์ชันนี้รองรับเฉพาะ GUI. ส่วน CLI จะเพิ่มภายหลัง (ยังไม่มีไฟล์ `pipeline_cli_app.py`).

### การตั้งค่าการเชื่อมต่อฐานข้อมูล

1. **Windows Authentication** (แนะนำ):
```json
{
    "server": "localhost\\SQLEXPRESS",
    "database": "your_database",
    "auth_type": "Windows",
    "username": "",
    "password": ""
}
```

2. **SQL Server Authentication**:
```json
{
    "server": "localhost\\SQLEXPRESS", 
    "database": "your_database",
    "auth_type": "SQL",
    "username": "your_username",
    "password": "your_password"
}
```

## การกำหนดค่าและไฟล์ข้อมูล

หลังจากล็อกอิน ระบบจะบันทึกไฟล์ตั้งค่าที่โฟลเดอร์ `config/` อัตโนมัติ เช่น `sql_config.json`, `app_settings.json`, `column_settings.json`, `dtype_settings.json`.

### Column Settings (`config/column_settings.json`)
```json
{
    "sales_data": {
        "Date": "date",
        "Product": "product_name",
        "Amount": "amount",
        "Customer": "customer_name"
    },
    "inventory_data": {
        "ItemCode": "item_code",
        "Quantity": "quantity",
        "Location": "location"
    }
}
```

### Data Type Settings (`config/dtype_settings.json`)
```json
{
    "sales_data": {
        "Date": "DATE",
        "Product": "NVARCHAR(255)",
        "Amount": "DECIMAL(18,2)",
        "Customer": "NVARCHAR(500)"
    },
    "inventory_data": {
        "ItemCode": "NVARCHAR(100)",
        "Quantity": "INT",
        "Location": "NVARCHAR(255)"
    }
}
```

## สำหรับนักพัฒนา AI

### โครงสร้างที่เป็นมิตรกับ AI

1. **Type Hints ครบถ้วน**: ทุกฟังก์ชันมี type annotations
2. **Docstrings มาตรฐาน**: อธิบายพารามิเตอร์และ return values
3. **Constants แยกออกมา**: ค่าคงที่ทั้งหมดอยู่ใน `constants.py`
4. **Error Messages มาตรฐาน**: ข้อความแสดงข้อผิดพลาดแบบ centralized
5. **Configuration Management**: จัดการการตั้งค่าแบบรวมศูนย์

### การเพิ่มฟีเจอร์ใหม่

1. **เพิ่มประเภทไฟล์ใหม่**:
```python
from config.settings import settings_manager

# เพิ่ม logic type ใหม่
settings_manager.add_logic_type(
    "new_data_type",
    column_mapping={"OldCol": "new_col"},
    dtype_mapping={"OldCol": "NVARCHAR(255)"}
)
```

2. **เพิ่ม Validation Rule**:
```python
from utils.validators import validate_dataframe

def custom_validation(df, logic_type):
    # Custom validation logic
    return True, "Valid"
```

3. **เพิ่ม UI Component**:
```python
# ui/components/new_component.py
import customtkinter as ctk

class NewComponent(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        # Component implementation
```

### Testing

```bash
# รัน tests ทั้งโปรเจกต์
pytest -q

# รันเฉพาะไฟล์ตัวอย่าง
pytest -q test_column_mapping.py

# ตัวตรวจสไตล์โค้ด (ถ้าติดตั้ง optional deps)
black .
flake8 .
mypy .
```

## Performance Features

- **Chunking**: สำหรับไฟล์ขนาดใหญ่ (>50MB)
- **Threading**: การย้ายไฟล์หลายไฟล์พร้อมกัน
- **Caching**: Settings และ dtype conversions
- **Batch Operations**: Database inserts แบบ batch
- **Memory Management**: การจัดการหน่วยความจำที่มีประสิทธิภาพ

## Troubleshooting

### ปัญหาการเชื่อมต่อฐานข้อมูล
1. ตรวจสอบว่า SQL Server กำลังทำงาน
2. ตรวจสอบ ODBC Driver 17 for SQL Server
3. ตรวจสอบ firewall settings
4. ทดสอบการเชื่อมต่อด้วย SQL Server Management Studio

### ปัญหาการอ่านไฟล์
1. ตรวจสอบว่าไฟล์ไม่ถูกเปิดในโปรแกรมอื่น
2. ตรวจสอบสิทธิ์การเข้าถึงไฟล์
3. ตรวจสอบรูปแบบของไฟล์ (Excel/CSV)

### ปัญหา Performance
1. ใช้ chunking สำหรับไฟล์ขนาดใหญ่
2. ปิดโปรแกรมอื่นที่ไม่จำเป็น
3. ตรวจสอบ disk space

## Contributing

1. Fork the repository
2. สร้าง feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit การเปลี่ยนแปลง (`git commit -m 'Add some AmazingFeature'`)
4. Push ไปยัง branch (`git push origin feature/AmazingFeature`)
5. เปิด Pull Request

## License

โครงการนี้ใช้ MIT License (อ้างอิงที่ `https://opensource.org/licenses/MIT`).

---

**หมายเหตุ**: โครงการนี้ออกแบบมาเพื่อให้ AI สามารถเข้าใจ ปรับปรุง และขยายได้ง่าย ด้วยโครงสร้างที่ชัดเจนและเอกสารที่ครบถ้วน