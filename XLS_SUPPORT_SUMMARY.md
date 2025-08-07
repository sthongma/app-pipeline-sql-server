# การเพิ่มการรองรับไฟล์ .xls ใน PIPELINE_SQLSERVER

## สรุปการเปลี่ยนแปลง

ระบบ PIPELINE_SQLSERVER ได้รับการปรับปรุงให้รองรับไฟล์ Excel รุ่นเก่า (.xls) นอกเหนือจากไฟล์ .xlsx และ .csv ที่รองรับอยู่แล้ว

## ไฟล์ที่มีการปรับปรุง

### 1. requirements.txt
- ✅ เพิ่ม `xlrd>=2.0.0` สำหรับการอ่านไฟล์ .xls

### 2. services/file_reader_service.py
- ✅ อัปเดต `find_data_files()` ให้ค้นหาไฟล์ .xls
- ✅ ปรับปรุง `detect_file_type()` ให้รองรับไฟล์ .xls
- ✅ อัปเดต `read_file_basic()` ให้ใช้ xlrd engine สำหรับไฟล์ .xls
- ✅ ปรับปรุง `peek_file_structure()` และ `get_file_info()` 

### 3. services/file_service.py
- ✅ อัปเดต `read_excel_file()` ให้ตรวจจับไฟล์ .xls และใช้ file_type ที่เหมาะสม

### 4. performance_optimizations.py
- ✅ ปรับปรุง `read_large_file_chunked()` ให้รองรับ 'excel_xls' type
- ✅ อัปเดต `_read_small_file()` ให้ใช้ xlrd engine สำหรับไฟล์ .xls
- ✅ เพิ่มการจัดการไฟล์ .xls ในการอ่านแบบ chunked สำหรับไฟล์ใหญ่

## การติดตั้งและใช้งาน

### ขั้นตอนการติดตั้ง
```bash
# ติดตั้ง dependencies ใหม่
pip install xlrd>=2.0.0

# หรือติดตั้งจาก requirements.txt
pip install -r requirements.txt
```

### การใช้งาน
ระบบจะตรวจจับและประมวลผลไฟล์ .xls โดยอัตโนมัติ:

```python
from services import FileService

# สร้าง FileService
file_service = FileService(search_path="path/to/files")

# อ่านไฟล์ .xls (เหมือนกับไฟล์ .xlsx)
success, df = file_service.read_excel_file("old_data.xls", "sales_data")

# ค้นหาไฟล์ทั้งหมด (รวม .xls)
files = file_service.find_data_files()
```

## ประเภทไฟล์ที่รองรับ

| นามสกุล | Engine | สถานะ |
|---------|--------|-------|
| .xlsx   | openpyxl | ✅ รองรับเดิม |
| .xls    | xlrd     | ✅ รองรับใหม่ |
| .csv    | pandas   | ✅ รองรับเดิม |

## การทำงานของระบบ

### การตรวจจับไฟล์อัตโนมัติ
- ระบบจะตรวจจับไฟล์ .xls ในการค้นหาไฟล์ข้อมูล
- การ auto-detect file type จะจำแนก .xls เป็น 'excel_xls' type

### การอ่านไฟล์
- ไฟล์ .xls จะใช้ xlrd engine
- รองรับการอ่านแบบ chunked สำหรับไฟล์ใหญ่
- Memory optimization ทำงานเหมือนกับไฟล์ .xlsx

### Performance
- ไฟล์ .xls อาจอ่านช้ากว่า .xlsx เล็กน้อยเนื่องจาก xlrd engine
- ยังคงรองรับการอ่านแบบ chunked สำหรับไฟล์ใหญ่

## หมายเหตุสำคัญ

⚠️ **ข้อกำหนดสำคัญ:**
- ต้องติดตั้ง `xlrd>=2.0.0` ก่อนใช้งาน
- xlrd 2.0+ รองรับเฉพาะไฟล์ .xls (ไม่รองรับ .xlsx)
- สำหรับไฟล์ .xlsx ยังคงใช้ openpyxl เหมือนเดิม

⚡ **การปรับปรุงประสิทธิภาพ:**
- ระบบจะเลือก engine ที่เหมาะสมตามนามสกุลไฟล์อัตโนมัติ
- การจัดการ memory และ chunking ทำงานได้กับทุกประเภทไฟล์

## การทดสอบ

ระบบได้ผ่านการทดสอบการทำงานพื้นฐาน:
- ✅ การตรวจจับไฟล์ .xls
- ✅ การ auto-detect ประเภทไฟล์
- ✅ การทำงานของ PerformanceOptimizer
- ✅ การทำงานร่วมกันของ services

## สำหรับการพัฒนาเพิ่มเติม

หากต้องการเพิ่มฟีเจอร์พิเศษสำหรับไฟล์ .xls:
1. แก้ไขใน `services/file_reader_service.py` สำหรับการอ่านไฟล์
2. อัปเดต `performance_optimizations.py` สำหรับ performance tuning
3. ปรับ `services/file_service.py` สำหรับ business logic

---
*อัปเดตเมื่อ: วันนี้*
*โดย: AI Assistant*
