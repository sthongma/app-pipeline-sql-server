# PIPELINE_SQLSERVER Architecture

## ภาพรวมของระบบ

PIPELINE_SQLSERVER เป็นระบบ ETL (Extract, Transform, Load) ที่ออกแบบมาเพื่อ:
- ประมวลผลไฟล์ Excel/CSV 
- แปลงข้อมูลตามการตั้งค่าที่ยืดหยุ่น
- อัปโหลดข้อมูลไปยัง SQL Server
- จัดการไฟล์ที่ประมวลผลแล้ว

## โครงสร้างโปรเจกต์

```
PIPELINE_SQLSERVER/
├── __init__.py                 # Main package initialization
├── constants.py                # ค่าคงที่ทั้งหมดของระบบ
├── requirements.txt            # Dependencies
├── pyproject.toml              # Project configuration
├── ARCHITECTURE.md             # เอกสารสถาปัตยกรรม
│
├── config/                     # การตั้งค่าและ configuration
│   ├── __init__.py
│   ├── database.py             # การจัดการการเชื่อมต่อฐานข้อมูล
│   └── settings.py             # Settings manager แบบรวมศูนย์
│
├── services/                   # Business logic และ services
│   ├── __init__.py
│   ├── database_service.py     # บริการฐานข้อมูล
│   ├── file_service.py         # บริการจัดการไฟล์หลัก (orchestrator)
│   ├── file_reader_service.py  # บริการอ่านและตรวจจับไฟล์
│   ├── data_processor_service.py # บริการประมวลผลและตรวจสอบข้อมูล
│   ├── file_management_service.py # บริการจัดการไฟล์
│   └── README.md               # เอกสาร services โดยละเอียด
│
├── ui/                         # User interface
│   ├── __init__.py
│   ├── main_window.py          # หน้าต่างหลัก GUI
│   ├── login_window.py         # หน้าต่างการตั้งค่า
│   └── components/             # UI components
│       ├── __init__.py
│       ├── file_list.py
│       ├── progress_bar.py
│       └── status_bar.py
│
├── utils/                      # Utility functions
│   ├── __init__.py
│   ├── helpers.py              # Helper functions
│   └── validators.py           # Validation functions
│
├── pipeline_cli_app.py         # CLI application entry point
├── pipeline_gui_app.py         # GUI application entry point
└── move_old_files_cli_app.py   # File management utility
```

## ส่วนประกอบหลัก

### 1. Constants (constants.py)
เก็บค่าคงที่ทั้งหมดของระบบ เพื่อให้ AI เข้าใจและปรับปรุงได้ง่าย:
- `DatabaseConstants`: ค่าคงที่สำหรับฐานข้อมูล
- `FileConstants`: ค่าคงที่สำหรับการประมวลผลไฟล์
- `AppConstants`: ค่าคงที่สำหรับแอปพลิเคชัน
- `PathConstants`: ค่าคงที่สำหรับ path และไฟล์
- `ErrorMessages`, `SuccessMessages`: ข้อความมาตรฐาน

### 2. Configuration Management (config/)
จัดการการตั้งค่าทั้งหมดของระบบ:

#### DatabaseConfig (config/database.py)
- จัดการการเชื่อมต่อ SQL Server
- สนับสนุน Windows Authentication และ SQL Authentication
- สร้างและจัดการ SQLAlchemy engine

#### SettingsManager (config/settings.py)
- Settings manager แบบรวมศูนย์
- จัดการการตั้งค่าฐานข้อมูล, แอปพลิเคชัน, คอลัมน์, และชนิดข้อมูล
- ใช้ dataclass สำหรับ type safety

### 3. Services (services/)
Business logic หลักของระบบ:

#### DatabaseService (services/database_service.py)
- จัดการการเชื่อมต่อฐานข้อมูล
- อัปโหลดข้อมูลไปยัง SQL Server
- จัดการ schema และตาราง

#### FileService (services/file_service.py)
- Orchestrator หลักที่ประสานงานระหว่าง services ต่างๆ
- ให้ interface เดียวกันกับระบบเดิม (backward compatible)
- การอ่านและประมวลผลไฟล์แบบครบวงจร

#### FileReaderService (services/file_reader_service.py)
- ค้นหาและอ่านไฟล์ Excel/CSV
- ตรวจจับประเภทไฟล์อัตโนมัติ
- จัดการ column mapping และตรวจสอบโครงสร้างไฟล์

#### DataProcessorService (services/data_processor_service.py)
- ตรวจสอบความถูกต้องของข้อมูล (validation)
- แปลงประเภทข้อมูล (data type conversion)
- ทำความสะอาดข้อมูล และตัดข้อมูลที่ยาวเกิน
- สร้างรายงานการตรวจสอบ

#### FileManagementService (services/file_management_service.py)
- ย้ายไฟล์ที่ประมวลผลแล้ว
- จัดระเบียบโฟลเดอร์และจัดการการตั้งค่า

### 4. User Interface (ui/)
ส่วนติดต่อผู้ใช้:

#### MainWindow (ui/main_window.py)
- หน้าต่างหลักของ GUI
- แสดงรายการไฟล์และสถานะการประมวลผล
- จัดการการอัปโหลดและการตั้งค่า

#### Components (ui/components/)
- `FileList`: แสดงรายการไฟล์
- `ProgressBar`: แสดงความคืบหน้า
- `StatusBar`: แสดงสถานะปัจจุบัน

### 5. Utilities (utils/)
ฟังก์ชันยูทิลิตี้และ validation:

#### Helpers (utils/helpers.py)
- ฟังก์ชัน helper ต่างๆ เช่น file validation, date parsing
- การจัดการ JSON files อย่างปลอดภัย
- การจัดรูปแบบข้อความแสดงข้อผิดพลาด

#### Validators (utils/validators.py)
- ตรวจสอบความถูกต้องของข้อมูล
- ตรวจสอบการตั้งค่าต่างๆ
- Validation สำหรับ SQL identifiers และ data types

## Design Principles

### 1. Separation of Concerns
แต่ละโมดูลมีหน้าที่ที่ชัดเจน:
- Config: การตั้งค่า
- Services: Business logic
- UI: User interface
- Utils: Utility functions

### 2. Type Safety
- ใช้ Type hints ทุกฟังก์ชัน
- ใช้ dataclass สำหรับ structured data
- ระบุ return types อย่างชัดเจน

### 3. Error Handling
- Centralized error messages
- Proper exception handling
- Graceful degradation

### 4. Configurability
- แยกการตั้งค่าออกจาก code
- สนับสนุนการตั้งค่าแบบ dynamic
- Easy to extend สำหรับ logic types ใหม่

### 5. AI-Friendly Structure
- โครงสร้างที่ชัดเจนและสม่ำเสมอ
- Documentation ที่ครบถ้วน
- Constants และ configuration ที่แยกออกมา
- ฟังก์ชันขนาดเล็กที่ทำงานเฉพาะเจาะจง

## การขยายระบบ

### เพิ่มประเภทไฟล์ใหม่ (Logic Type)
1. เพิ่มการตั้งค่าใน `column_settings.json`
2. เพิ่มการตั้งค่าใน `dtype_settings.json`  
3. ใช้ `SettingsManager.add_logic_type()`

### เพิ่ม Data Source ใหม่
1. สร้าง service class ใหม่ใน `services/`
2. implement interface เดียวกันกับ `DatabaseService`
3. อัปเดต constants ถ้าจำเป็น

### เพิ่ม UI Component ใหม่
1. สร้างไฟล์ใหม่ใน `ui/components/`
2. เพิ่มใน `__init__.py`
3. integrate กับ `MainWindow`

### เพิ่ม Validation Rules
1. เพิ่มฟังก์ชันใน `utils/validators.py`
2. อัปเดต error messages ใน `constants.py`
3. integrate กับ services ที่เกี่ยวข้อง

## Performance Considerations

### File Processing
- ใช้ chunking สำหรับไฟล์ขนาดใหญ่
- Threading สำหรับการย้ายไฟล์หลายไฟล์
- Caching สำหรับ settings และ dtype conversions

### Database Operations
- Batch inserts
- Connection pooling
- Schema validation caching

### Memory Management
- Lazy loading ของ settings
- Proper cleanup ของ DataFrame objects
- Limited cache sizes

## Security Considerations

### Database Connections
- Support สำหรับ Windows Authentication
- Secure storage ของ credentials
- Connection string validation

### File Operations
- Path validation
- Safe file operations
- Backup mechanisms

### Configuration
- Validation ของ configuration files
- Safe JSON operations
- Error handling ที่ไม่ expose sensitive data