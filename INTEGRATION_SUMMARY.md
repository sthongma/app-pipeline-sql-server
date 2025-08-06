# การรวมแอพ File Management เข้าสู่แอพหลัก

## สรุปการดำเนินการ

ได้ทำการรวมแอพทั้งสองจาก `File management/` เข้าสู่แอพหลัก PIPELINE_SQLSERVER เรียบร้อยแล้ว:

### แอพที่ถูกรวม
1. **move_old_files_cli_app.py** - แอพสำหรับย้ายไฟล์เก่าไป archive
2. **ZipExcelMerger** - แอพสำหรับรวมไฟล์ Excel จาก ZIP files

## การเปลี่ยนแปลงที่ทำ

### 1. สร้าง FileManagementService ใหม่
- ไฟล์: `services/file_management_service.py`
- รวมฟังชั่นทั้งสองแอพเข้าไว้ในคลาสเดียว
- รองรับการย้ายไฟล์เก่า, ลบไฟล์, และรวมไฟล์ Excel จาก ZIP

### 2. อัปเดต CLI Application
- ไฟล์: `pipeline_cli_app.py`
- เพิ่ม command line arguments สำหรับฟังชั่นใหม่:
  - `python pipeline_cli_app.py archive --days 30 --src ./Uploaded_Files --dest D:/Archived_Files`
  - `python pipeline_cli_app.py merge-zip --folder ./path/to/zip/folder`
- ยังคงรองรับการใช้งานแบบเดิม (โดยไม่ระบุ command)

### 3. อัปเดต GUI Application
- ไฟล์: `ui/main_window.py`
- เพิ่ม Tab ใหม่ "File Management" ใน GUI
- มีฟังชั่น:
  - **จัดเก็บไฟล์เก่า**: เลือกโฟลเดอร์ต้นทาง/ปลายทาง, ตั้งจำนวนวัน
  - **รวมไฟล์ Excel จาก ZIP**: เลือกโฟลเดอร์ที่มี ZIP files
  - Progress bar และ status monitoring
  - Results log แสดงผลลัพธ์การดำเนินการ

### 4. อัปเดต Dependencies
- ไฟล์: `requirements.txt`
- เพิ่ม `openpyxl>=3.0.0` สำหรับการประมวลผล Excel files

### 5. ทำความสะอาดไฟล์เก่า
- ลบไฟล์ที่ไม่ต้องการใน `File management/`
- เก็บเฉพาะ `README.md` ของ ZipExcelMerger ไว้สำหรับการอ้างอิง

## วิธีการใช้งาน

### CLI Mode
```bash
# ประมวลผลไฟล์ปกติ (แบบเดิม)
python pipeline_cli_app.py

# จัดเก็บไฟล์เก่า
python pipeline_cli_app.py archive --days 30 --src ./Uploaded_Files --dest D:/Archived_Files

# รวมไฟล์ Excel จาก ZIP
python pipeline_cli_app.py merge-zip --folder ./path/to/zip/folder
```

### GUI Mode
```bash
python pipeline_gui_app.py
```
จากนั้นใช้ Tab "File Management" สำหรับฟังชั่นการจัดการไฟล์

## ข้อดีของการรวม

1. **ความสะดวกในการใช้งาน**: ผู้ใช้ไม่ต้องเปิดแอพหลายตัว
2. **การจัดการที่ดีขึ้น**: ใช้ระบบ logging และ settings เดียวกัน
3. **UI ที่สอดคล้องกัน**: ใช้ CustomTkinter theme เดียวกัน
4. **การบำรุงรักษา**: ลดจำนวนไฟล์ที่ต้องดูแล

## หมายเหตุ

- ฟังชั่นทั้งหมดจากแอพเดิมยังคงทำงานได้เหมือนเดิม
- การตั้งค่าจะถูกเก็บใน `config/file_management_settings.json`
- รองรับการแสดงความคืบหน้าและ error handling ที่ดีขึ้น