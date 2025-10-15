# SQL Server Data Pipeline

**โปรแกรมนำเข้าข้อมูล Excel/CSV เข้า SQL Server - ใช้งานง่าย ไม่ต้องเขียนโค้ด**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

โปรแกรมสำหรับนำเข้าไฟล์ Excel และ CSV เข้าสู่ฐานข้อมูล SQL Server แบบอัตโนมัติ พร้อมระบบทำความสะอาดข้อมูล ตรวจสอบความถูกต้อง และจัดการไฟล์อย่างมีระบบ

---

## โปรแกรมนี้ทำอะไรได้บ้าง?

### 🎯 ฟีเจอร์หลัก

#### 1. **การนำเข้าข้อมูลอัตโนมัติ**
- รองรับไฟล์ Excel (`.xlsx`, `.xls`) และ CSV
- ตรวจจับประเภทไฟล์อัตโนมัติ (Auto Detection)
- นำเข้าข้อมูลทีละชุด (Batch Processing) หลายไฟล์พร้อมกัน
- จัดการไฟล์ขนาดใหญ่ได้อย่างมีประสิทธิภาพ

#### 2. **ระบบทำความสะอาดและตรวจสอบข้อมูล**
- ตรวจสอบ Data Type อัตโนมัติ (วันที่, ตัวเลข, ข้อความ, Boolean)
- แปลงวันที่หลายรูปแบบให้เป็นมาตรฐานเดียวกัน
- ตรวจสอบและจัดการค่า NULL
- ตัดช่องว่างและอักขระพิเศษที่ไม่จำเป็น
- แจ้งเตือนข้อมูลที่ผิดพลาดพร้อมระบุตำแหน่ง

#### 3. **การจัดการตารางฐานข้อมูล (Database Schema Management)**
- สร้างตารางอัตโนมัติถ้ายังไม่มี
- ตรวจสอบและปรับโครงสร้างตารางให้ตรงกับข้อมูล
- เพิ่มคอลัมน์ใหม่อัตโนมัติเมื่อข้อมูลมีฟิลด์เพิ่มขึ้น
- จัดการ Primary Key และ Index

#### 4. **การกำหนดค่าที่ยืดหยุ่น (Flexible Configuration)**
- กำหนด Column Mapping เอง (ชื่อคอลัมน์จากไฟล์ → ชื่อในฐานข้อมูล)
- กำหนด Data Type สำหรับแต่ละคอลัมน์
- บันทึกการตั้งค่าเป็น JSON ใช้ซ้ำได้
- รองรับหลายประเภทไฟล์พร้อมกัน

#### 5. **การจัดการไฟล์อัตโนมัติ (File Management)**
- แยกไฟล์ที่นำเข้าสำเร็จและไม่สำเร็จไปคนละโฟลเดอร์
- เพิ่ม timestamp ให้ไฟล์อัตโนมัติ
- ป้องกันการนำเข้าซ้ำ
- บันทึก log ทุกขั้นตอนการทำงาน

#### 6. **ส่งออก Log อัตโนมัติ**
- บันทึก log การทำงานทั้งหมด
- ส่งออกเป็น Text File อัตโนมัติ
- กำหนดโฟลเดอร์ส่งออกได้
- ติดตามประวัติการนำเข้าข้อมูล

#### 7. **หน้าจอ GUI ใช้งานง่าย**
- อินเทอร์เฟซที่เข้าใจง่าย ไม่ต้องเขียนโค้ด
- แสดงความคืบหน้าแบบ Real-time
- แสดงรายการไฟล์ที่ตรวจพบ
- แจ้งเตือนและ Log ที่ชัดเจน

#### 8. **CLI สำหรับระบบอัตโนมัติ (Automation)**
- รันจาก Command Line สำหรับตั้งเวลาอัตโนมัติ
- เหมาะกับ Windows Task Scheduler หรือ Cron Job
- ใช้การตั้งค่าเดียวกับ GUI
- ไม่มี Pop-up รบกวน

#### 9. **ความปลอดภัย**
- รองรับ Windows Authentication
- รองรับ SQL Server Authentication
- เก็บ Credentials ปลอดภัยด้วย Environment Variables
- ตรวจสอบสิทธิ์การเข้าถึงฐานข้อมูล

---

## วิธีการติดตั้งและใช้งาน (Quick Start)

### ขั้นตอนที่ 1: ติดตั้งโปรแกรม

```bash
# 1. Clone repository
git clone https://github.com/ST-415/PIPELINE_SQLSERVER.git
cd PIPELINE_SQLSERVER

# 2. ติดตั้ง dependencies
pip install -r requirements.txt

# 3. รัน setup script
python install_requirements.py
```

### ขั้นตอนที่ 2: ตั้งค่าฐานข้อมูล

แก้ไขไฟล์ `.env` ที่ถูกสร้างขึ้นมา:

```env
# ข้อมูลการเชื่อมต่อฐานข้อมูล
DB_SERVER=localhost\SQLEXPRESS
DB_NAME=YourDatabase

# สำหรับ Windows Authentication (แนะนำ)
DB_USERNAME=
DB_PASSWORD=

# หรือใช้ SQL Server Authentication
# DB_USERNAME=your_username
# DB_PASSWORD=your_password
```

### ขั้นตอนที่ 3: เปิดใช้งานโปรแกรม

**แบบ GUI (หน้าต่างโปรแกรม):**

```bash
# เปิด GUI Application
python pipeline_gui_app.py

# หรือดับเบิลคลิกไฟล์
run_pipeline_gui.bat
```

**แบบ CLI (สำหรับระบบอัตโนมัติ):**

```bash
# ประมวลผลไฟล์ในโฟลเดอร์อัตโนมัติ
python auto_process_cli.py "C:\path\to\your\data"

# หรือดับเบิลคลิกไฟล์
run_auto_process.bat
```

---

## การใช้งาน (How to Use)

### การใช้งานแบบ GUI

1. **เลือกโฟลเดอร์ข้อมูล (Input Folder)**
   - เลือกโฟลเดอร์ที่เก็บไฟล์ Excel/CSV

2. **ตั้งค่า Output Folder**
   - เลือกโฟลเดอร์สำหรับเก็บไฟล์ที่ประมวลผลแล้ว

3. **กำหนด Column Mapping (ถ้าต้องการ)**
   - ตั้งชื่อคอลัมน์ที่จะใช้ในฐานข้อมูล
   - กำหนด Data Type สำหรับแต่ละคอลัมน์

4. **กดปุ่ม "ตรวจสอบไฟล์"**
   - โปรแกรมจะค้นหาไฟล์ในโฟลเดอร์

5. **เลือกไฟล์ที่จะนำเข้า**
   - เลือกไฟล์ที่ต้องการประมวลผล

6. **กดปุ่ม "นำเข้าข้อมูล"**
   - โปรแกรมจะทำงานอัตโนมัติ:
     - ตรวจสอบและทำความสะอาดข้อมูล
     - สร้าง/อัปเดตตารางในฐานข้อมูล
     - นำเข้าข้อมูลเข้า SQL Server
     - ย้ายไฟล์ไปโฟลเดอร์ที่กำหนด
     - เพิ่ม timestamp ให้ไฟล์
     - บันทึก log

7. **ตรวจสอบผลลัพธ์**
   - ดูสถานะและ log ในโปรแกรม
   - ส่งออก log เป็นไฟล์ได้

### การใช้งานแบบ CLI (Automation)

เหมาะสำหรับ:

- ตั้งเวลารันอัตโนมัติด้วย **Windows Task Scheduler**
- รันผ่าน Batch Script
- รันซ้ำๆ โดยไม่ต้องเปิด GUI

**ตัวอย่างการใช้งาน:**

```bash
# รันทันที
python auto_process_cli.py "C:\data\daily_reports"

# รันพร้อม verbose logging
python auto_process_cli.py -v "C:\data\daily_reports"

# รันโดยใช้โฟลเดอร์ที่บันทึกไว้
python auto_process_cli.py
```

**ตั้งค่าให้รันอัตโนมัติทุกวัน:**

สร้างไฟล์ `.bat`:

```batch
@echo off
cd C:\path\to\PIPELINE_SQLSERVER
python auto_process_cli.py "C:\daily\reports"
```

จากนั้นตั้งเวลาด้วย Windows Task Scheduler

---

## ความต้องการของระบบ (System Requirements)

- **Python**: 3.8 ขึ้นไป
- **Database**: SQL Server หรือ SQL Server Express
- **ODBC Driver**: ODBC Driver 17 หรือ 18 for SQL Server
- **Operating System**: Windows (แนะนำสำหรับ GUI)

---

## การตั้งค่า (Configuration)

โปรแกรมใช้ไฟล์ JSON สำหรับเก็บการตั้งค่าต่างๆ ที่สามารถปรับแต่งได้:

### 1. Column Mapping (`config/column_settings.json`)

กำหนดการแปลงชื่อคอลัมน์จากไฟล์ → ชื่อในฐานข้อมูล

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

### 2. Data Types (`config/dtype_settings.json`)

กำหนด Data Type สำหรับแต่ละคอลัมน์

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

### 3. Input Folder (`config/input_folder_config.json`)

บันทึกโฟลเดอร์ที่ใช้ค้นหาไฟล์ล่าสุด

### 4. Output Folder (`config/output_folder_config.json`)

บันทึกโฟลเดอร์สำหรับเก็บไฟล์ที่ประมวลผลแล้ว

### 5. Log Folder (`config/log_folder_config.json`)

บันทึกโฟลเดอร์สำหรับส่งออกไฟล์ log

### 6. File Management (`config/file_management_settings.json`)

ตั้งค่าการจัดการไฟล์หลังประมวลผล

---

## สถาปัตยกรรมระบบ (Architecture)

โปรแกรมออกแแบบโดยใช้ **Service-Oriented Architecture** แบ่งเป็น:

```text
📦 PIPELINE_SQLSERVER
├── 📁 ui/                       # User Interface Layer
│   ├── login_window.py           # หน้าจอ Login
│   ├── main_window.py            # หน้าต่างหลัก
│   ├── tabs/                     # แท็บต่างๆ
│   │   ├── main_tab.py           # แท็บหลัก (นำเข้าข้อมูล)
│   │   ├── settings_tab.py       # แท็บตั้งค่า
│   │   └── log_tab.py            # แท็บ log
│   ├── handlers/                 # UI Event Handlers
│   │   ├── file_handler.py       # จัดการเหตุการณ์ไฟล์
│   │   └── settings_handler.py   # จัดการการตั้งค่า
│   └── components/               # UI Components
│
├── 📁 services/                    # Business Logic Layer
│   ├── orchestrators/            # High-level Coordinators
│   │   ├── database_orchestrator.py
│   │   ├── file_orchestrator.py
│   │   └── validation_orchestrator.py
│   │
│   ├── database/                 # Database Services
│   │   ├── connection_service.py  # การเชื่อมต่อ
│   │   ├── schema_service.py      # จัดการ Schema
│   │   ├── data_upload_service.py # อัปโหลดข้อมูล
│   │   └── validation/           # ตรวจสอบข้อมูล
│   │
│   ├── file/                     # File Services
│   │   ├── file_reader_service.py       # อ่านไฟล์
│   │   ├── data_processor_service.py    # ประมวลผลข้อมูล
│   │   └── file_management_service.py   # จัดการไฟล์
│   │
│   └── utilities/                # Utility Services
│       ├── preload_service.py    # โหลดข้อมูลเริ่มต้น
│       └── permission_checker_service.py
│
├── 📁 config/                      # Configuration Layer
│   ├── database.py               # Database config
│   ├── json_manager.py           # JSON settings manager
│   └── *.json                    # Settings files
│
├── 📁 utils/                       # Utilities
│   └── logger.py                 # Logging system
│
├── pipeline_gui_app.py           # GUI Entry Point
└── auto_process_cli.py           # CLI Entry Point
```

### การทำงานของระบบ

1. **UI Layer** - รับ input จากผู้ใช้ผ่าน GUI/CLI
2. **Orchestrator Layer** - ประสานงานระหว่าง services ต่างๆ
3. **Service Layer** - ทำงานจริง (อ่านไฟล์, ประมวลผล, บันทึกฐานข้อมูล)
4. **Configuration Layer** - จัดการการตั้งค่าทั้งหมด

---

## กรณีการใช้งาน (Use Cases)

### 📊 กรณีที่ 1: นำเข้าข้อมูลรายวันอัตโนมัติ

**สถานการณ์:** บริษัทมีรายงานยอดขายทุกวัน ต้องการนำเข้าเข้าฐานข้อมูลอัตโนมัติ

**วิธีแก้:**

1. ตั้งค่า Column Mapping และ Data Type ใน GUI ครั้งเดียว
2. สร้าง batch file:

   ```batch
   @echo off
   python auto_process_cli.py "C:\daily\sales\reports"
   ```

3. ตั้งเวลาด้วย Windows Task Scheduler ให้รันทุกวันเวลา 2:00 น.

### 📈 กรณีที่ 2: ประมวลผลไฟล์ขนาดใหญ่

**สถานการณ์:** มีไฟล์ Excel ขนาด 100 MB ต้องการนำเข้าฐานข้อมูล

**วิธีแก้:**

- โปรแกรมจะประมวลผลแบบ chunked processing อัตโนมัติ
- ใช้ CLI เพื่อลด memory overhead
- โปรแกรมจัดการ memory optimization เอง

### 🔄 กรณีที่ 3: หลายประเภทไฟล์

**สถานการณ์:** มีไฟล์หลายประเภท (Sales, Inventory, Customers) ต้องการนำเข้าตารางคนละตาราง

**วิธีแก้:**

1. ตั้งค่า Column Mapping แยกตามแต่ละประเภท:
   - `sales_data` → `tbl_sales`
   - `inventory_data` → `tbl_inventory`
   - `customer_data` → `tbl_customers`

2. โปรแกรมจะตรวจจับประเภทไฟล์อัตโนมัติและนำเข้าไปยังตารางที่ถูกต้อง

### 🏢 กรณีที่ 4: การทำงานหลายสาขา

**สถานการณ์:** หลายสาขาส่งไฟล์รายงานมารวมกัน ต้องการนำเข้าทั้งหมดพร้อมกัน

**วิธีแก้:**

1. รวมไฟล์จากทุกสาขาในโฟลเดอร์เดียว
2. ใช้ GUI เลือกไฟล์ทั้งหมด หรือใช้ CLI รันอัตโนมัติ
3. โปรแกรมจะประมวลผลทีละไฟล์และย้ายไปโฟลเดอร์ที่กำหนด

---

## การแก้ปัญหา (Troubleshooting)

### ❌ ปัญหาการเชื่อมต่อฐานข้อมูล

**อาการ:** ไม่สามารถเชื่อมต่อกับ SQL Server ได้

**วิธีแก้:**

1. ตรวจสอบว่า SQL Server กำลังทำงานอยู่
   - เปิด **SQL Server Configuration Manager**
   - ตรวจสอบ SQL Server Service

2. ตรวจสอบ ODBC Driver
   - ต้องติดตั้ง **ODBC Driver 17 หรือ 18 for SQL Server**
   - ดาวน์โหลด: [Microsoft ODBC Driver](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)

3. ตรวจสอบไฟล์ `.env`

   ```env
   DB_SERVER=localhost\SQLEXPRESS  # ตรวจสอบชื่อ Server
   DB_NAME=YourDatabase            # ตรวจสอบชื่อฐานข้อมูล
   ```

4. ทดสอบการเชื่อมต่อด้วย **SQL Server Management Studio (SSMS)**

### ❌ ปัญหาการอ่านไฟล์

**อาการ:** โปรแกรมไม่สามารถอ่านไฟล์ Excel/CSV ได้

**วิธีแก้:**

1. **ปิดไฟล์ Excel** ก่อนประมวลผล
   - Excel จะล็อกไฟล์ไม่ให้โปรแกรมอื่นเข้าถึง

2. ตรวจสอบ **File Permissions**
   - คลิกขวาไฟล์ → Properties → Security
   - ตรวจสอบว่ามีสิทธิ์ Read

3. ตรวจสอบ **File Format**
   - รองรับเฉพาะ `.xlsx`, `.xls`, `.csv`
   - ตรวจสอบว่าไฟล์ไม่เสียหาย

4. ตรวจสอบ **Encoding** (สำหรับ CSV)
   - แนะนำให้ใช้ UTF-8 with BOM
   - หรือ Windows-1252 (ANSI)

### ❌ ปัญหาความเร็ว (Performance)

**อาการ:** โปรแกรมทำงานช้า

**วิธีแก้:**

1. **ใช้ CLI แทน GUI** สำหรับไฟล์ขนาดใหญ่

   ```bash
   python auto_process_cli.py "C:\data\folder"
   ```

2. **ปิดโปรแกรมที่ไม่จำเป็น**
   - ปิด Excel, Browser tabs ที่ไม่ใช้

3. **ตรวจสอบพื้นที่ Hard Disk**
   - ต้องมีพื้นที่ว่างมากกว่า 2 เท่าของไฟล์ที่จะประมวลผล

4. **แบ่งไฟล์ขนาดใหญ่**
   - แบ่งไฟล์ที่มีขนาดมากกว่า 500 MB ออกเป็นไฟล์เล็กๆ

### ❌ ปัญหาข้อมูล (Data Issues)

**อาการ:** ข้อมูลบางส่วนไม่ถูกนำเข้า หรือมี error

**วิธีแก้:**

1. **ตรวจสอบ Data Type**
   - ตรวจสอบว่า Data Type ใน `dtype_settings.json` ตรงกับข้อมูลจริง
   - เช่น ถ้าเป็นวันที่ต้องใช้ `DATE` ไม่ใช่ `VARCHAR`

2. **ตรวจสอบ Log**
   - ดู log ในโปรแกรมหรือส่งออกเป็นไฟล์
   - จะบอกว่า row/column ไหนมีปัญหา

3. **ตรวจสอบ Column Mapping**
   - ตรวจสอบว่าชื่อคอลัมน์ใน Excel ตรงกับ `column_settings.json`

4. **ค่า NULL**
   - ตรวจสอบว่าคอลัมน์ในฐานข้อมูลยอมรับ NULL หรือไม่

### 💡 เคล็ดลับ (Tips)

- ทดสอบกับไฟล์ขนาดเล็กก่อน (10-20 rows)
- ใช้ **Test Connection** ในโปรแกรมก่อนนำเข้าข้อมูล
- สำรองฐานข้อมูลก่อนนำเข้าข้อมูลจำนวนมาก
- ตรวจสอบ log เสมอเมื่อมี error

---

## ข้อกำหนดสิทธิ์การใช้งาน (License)

โปรเจคนี้อนุญาตให้ใช้งานภายใต้ **MIT License** - ดูรายละเอียดใน [LICENSE](LICENSE)

---

## การสนับสนุน (Support)

- **🐛 พบ Bug หรือต้องการ Feature ใหม่:** [GitHub Issues](https://github.com/ST-415/PIPELINE_SQLSERVER/issues)
- **📖 เอกสารเพิ่มเติม:** อยู่ใน repository นี้
- **🔄 อัปเดต:** ดูประวัติการเปลี่ยนแปลงใน `CHANGELOG.md`

---

## ผู้พัฒนา (Contributors)

พัฒนาโดย sthongma

---

## สรุป (Summary)

**SQL Server Data Pipeline** เป็นโปรแกรมที่ช่วยให้การนำเข้าข้อมูลจาก Excel/CSV เข้าสู่ SQL Server เป็นเรื่องง่าย ไม่ต้องเขียนโค้ด พร้อมระบบตรวจสอบข้อมูล จัดการไฟล์อัตโนมัติ และรองรับการทำงานแบบอัตโนมัติผ่าน CLI

**เหมาะสำหรับ:**

- 👨‍💼 Business Analysts ที่ต้องนำเข้าข้อมูลประจำ
- 📊 Data Engineers ที่ต้องการ ETL tool ที่ใช้งานง่าย
- 🏢 องค์กรที่ต้องการระบบนำเข้าข้อมูลอัตโนมัติ
- 🔧 IT Teams ที่ต้องการ automated data pipeline

**พร้อมใช้งาน! เริ่มต้นนำเข้าข้อมูลได้เลย** 🚀