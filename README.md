# PipelineBronze_App - ระบบ ETL Pipeline สำหรับ Bronze Layer

## ภาพรวมโครงการ

PipelineBronze_App เป็นแอปพลิเคชันสำหรับอัปโหลดไฟล์ Excel ไปยัง Bronze Layer ในฐานข้อมูล โดยใช้สถาปัตยกรรม Medallion Architecture (Bronze → Silver → Gold Layer) เพื่อแปลงข้อมูลดิบให้เป็นข้อมูลที่พร้อมใช้งานสำหรับการวิเคราะห์

## โครงสร้างโครงการ

```
PipelineBronze_App/
├── config/                    # ไฟล์การกำหนดค่า
│   ├── column_settings.json   # การแมปคอลัมน์สำหรับแต่ละประเภทไฟล์
│   ├── database.py           # การเชื่อมต่อฐานข้อมูล
│   └── last_path.json        # เก็บ path ล่าสุดที่ใช้งาน
├── services/                  # บริการหลัก
│   ├── database_service.py   # บริการจัดการฐานข้อมูล
│   └── file_service.py       # บริการจัดการไฟล์
├── ui/                       # ส่วนติดต่อผู้ใช้
│   ├── components/           # องค์ประกอบ UI
│   │   ├── file_list.py     # รายการไฟล์
│   │   ├── progress_bar.py  # แถบความคืบหน้า
│   │   └── status_bar.py    # แถบสถานะ
│   ├── login_window.py      # หน้าต่างล็อกอิน
│   └── main_window.py       # หน้าต่างหลัก
├── pipeline_gui_app.py       # แอปพลิเคชัน GUI
├── pipeline_cli_app.py       # แอปพลิเคชัน Command Line Interface
├── move_old_files_cli_app.py # ย้ายไฟล์เก่าไปโฟลเดอร์ backup
├── requirements.txt          # Dependencies
└── *.bat                    # ไฟล์ batch สำหรับรันแอปพลิเคชัน
```

## การติดตั้ง

### 1. ติดตั้ง Dependencies
```bash
install_requirements.bat
```

### 2. กำหนดค่าฐานข้อมูล
แก้ไขไฟล์ `config/database.py`:
```python
# การตั้งค่าการเชื่อมต่อฐานข้อมูล
SERVER = 'your_server_name'
DATABASE = 'DWH_EP'
USERNAME = 'your_username'
PASSWORD = 'your_password'
```

## วิธีใช้งาน

### GUI Application
```bash
run_pipeline_gui.bat
```

### CLI Application
```bash
run_pipeline_cli.bat
```

### ย้ายไฟล์เก่า
```bash
run_move_old_files.bat
```

## ประเภทข้อมูลที่รองรับ

### แพลตฟอร์มการขาย
- **JST (Just Sell It):** order, inprocess, loading, release, return, sku_set, sku_single
- **Lazada:** order, status
- **Shopee:** order, status  
- **TikTok:** order, status

### รายงานอื่นๆ
- **DHL Report:** รายงานการจัดส่ง DHL
- **Ship Plan Report:** แผนการจัดส่ง

## การกำหนดค่า

### Column Settings
แก้ไขไฟล์ `config/column_settings.json` เพื่อกำหนดการแมปคอลัมน์สำหรับแต่ละประเภทไฟล์

### Database Settings
แก้ไขไฟล์ `config/database.py` เพื่อกำหนดการเชื่อมต่อฐานข้อมูล

## ข้อกำหนดระบบ

- **Database:** SQL Server 2016+
- **Python:** 3.8+
- **OS:** Windows (สำหรับ batch files)
- **Libraries:** pandas, openpyxl, customtkinter, pyodbc

## การแก้ไขปัญหาเบื้องต้น

1. **ไม่สามารถเชื่อมต่อฐานข้อมูล:** ตรวจสอบการตั้งค่าใน `config/database.py`
2. **ไฟล์ Excel อ่านไม่ได้:** ตรวจสอบรูปแบบและ encoding
3. **Dependencies ขาดหาย:** รัน `install_requirements.bat` ใหม่

## ผู้พัฒนา

โครงการนี้พัฒนาสำหรับ ST-415 Data Warehouse EP 