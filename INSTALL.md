# SQL Server Data Pipeline - Installation Guide

คู่มือการติดตั้งและใช้งาน SQL Server Data Pipeline

---

## สารบัญ

1. [System Requirements](#system-requirements)
2. [Pre-Installation Checklist](#pre-installation-checklist)
3. [Installation Steps](#installation-steps)
4. [First-Time Configuration](#first-time-configuration)
5. [Testing the Installation](#testing-the-installation)
6. [Troubleshooting](#troubleshooting)
7. [Uninstallation](#uninstallation)

---

## System Requirements

### ข้อกำหนดขั้นต่ำ (Minimum Requirements)

- **Operating System**: Windows 10 (64-bit) or Windows 11
- **RAM**: 4 GB
- **Disk Space**: 100 MB free space
- **Database**: SQL Server 2016+ or SQL Server Express 2016+
- **ODBC Driver**: ODBC Driver 17 or 18 for SQL Server

### ข้อกำหนดที่แนะนำ (Recommended Requirements)

- **Operating System**: Windows 11 (64-bit)
- **RAM**: 8 GB or more
- **Disk Space**: 500 MB free space
- **Database**: SQL Server 2019+ or SQL Server Express 2019+
- **ODBC Driver**: ODBC Driver 18 for SQL Server

---

## Pre-Installation Checklist

ก่อนติดตั้ง กรุณาตรวจสอบรายการต่อไปนี้:

### 1. SQL Server หรือ SQL Server Express ติดตั้งและทำงานอยู่

```powershell
# ตรวจสอบ SQL Server services
Get-Service -Name MSSQL*
```

หรือเปิด **SQL Server Configuration Manager** และตรวจสอบว่า SQL Server service กำลังทำงาน

### 2. ODBC Driver for SQL Server ติดตั้งแล้ว

**ดาวน์โหลดได้จาก:**
- [ODBC Driver 18 for SQL Server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)

**ตรวจสอบ ODBC Driver:**
1. กด `Windows + R`
2. พิมพ์ `odbcad32` และกด Enter
3. ไปที่แท็บ "Drivers"
4. ตรวจสอบว่ามี "ODBC Driver 17 for SQL Server" หรือ "ODBC Driver 18 for SQL Server"

### 3. มีสิทธิ์ Administrator สำหรับติดตั้งโปรแกรม

โปรแกรมต้องการสิทธิ์ Administrator เพื่อ:
- ติดตั้งไฟล์ลงใน `Program Files`
- สร้าง shortcuts
- ติดตั้ง dependencies

---

## Installation Steps

### ขั้นตอนที่ 1: ดาวน์โหลด Installer

ดาวน์โหลดไฟล์ `SQLServerPipeline_v1.0.0_Setup.exe` จาก:
- GitHub Releases: [releases page](https://github.com/sthongma/app-pipeline-sql-server/releases)
- หรือแหล่งที่ได้รับ installer file

### ขั้นตอนที่ 2: รัน Installer

1. **คลิกขวา** ที่ไฟล์ `SQLServerPipeline_v1.0.0_Setup.exe`
2. เลือก **"Run as administrator"**
3. หาก Windows SmartScreen แสดงคำเตือน:
   - คลิก **"More info"**
   - คลิก **"Run anyway"**

### ขั้นตอนที่ 3: ทำตาม Installation Wizard

1. **Welcome Screen**
   - คลิก "Next"

2. **License Agreement**
   - อ่าน MIT License
   - เลือก "I accept the agreement"
   - คลิก "Next"

3. **Select Destination Location**
   - Location เริ่มต้น: `C:\Program Files\SQL Server Pipeline`
   - สามารถเปลี่ยนได้ถ้าต้องการ
   - คลิก "Next"

4. **Select Additional Tasks**
   - ☑ Create a desktop icon (แนะนำ)
   - ☐ Create a Quick Launch icon (ตัวเลือก)
   - คลิก "Next"

5. **Ready to Install**
   - ตรวจสอบข้อมูลและคลิก "Install"

6. **Installing**
   - รอจนการติดตั้งเสร็จสิ้น (ประมาณ 1-2 นาที)

7. **Completing Setup**
   - ☐ View README file (ตัวเลือก)
   - ☑ Launch SQL Server Pipeline (ถ้าต้องการเปิดใช้งานทันที)
   - คลิก "Finish"

### ขั้นตอนที่ 4: ข้อความสำคัญหลังติดตั้ง

หลังจากติดตั้งเสร็จ จะมีข้อความแจ้งเตือน:
```
Important: Please configure your database connection in the .env file
before running the application.

You will also need ODBC Driver 17 or 18 for SQL Server installed.
```

คลิก "OK" และทำตามขั้นตอนในส่วน **First-Time Configuration** ด้านล่าง

---

## First-Time Configuration

### ตั้งค่าการเชื่อมต่อฐานข้อมูล

1. **เปิดโฟลเดอร์ที่ติดตั้ง**
   - Default: `C:\Program Files\SQL Server Pipeline`
   - หรือคลิกขวาที่ shortcut → "Open file location"

2. **แก้ไขไฟล์ `.env`**
   - คลิกขวาที่ไฟล์ `.env`
   - เลือก "Open with" → "Notepad" หรือ text editor อื่น

3. **กรอกข้อมูลการเชื่อมต่อ**

   **สำหรับ Windows Authentication (แนะนำ):**
   ```env
   DB_SERVER=localhost\SQLEXPRESS
   DB_NAME=YourDatabaseName
   DB_USERNAME=
   DB_PASSWORD=
   ```

   **สำหรับ SQL Server Authentication:**
   ```env
   DB_SERVER=localhost\SQLEXPRESS
   DB_NAME=YourDatabaseName
   DB_USERNAME=your_username
   DB_PASSWORD=your_password
   ```

4. **บันทึกไฟล์**
   - กด `Ctrl + S` หรือ File → Save

---

## Testing the Installation

### ทดสอบการเปิดโปรแกรม

1. **เปิดโปรแกรม**
   - ดับเบิลคลิกที่ desktop icon "SQL Server Pipeline"
   - หรือเปิดจาก Start Menu

2. **ทดสอบการเชื่อมต่อฐานข้อมูล**
   - ในหน้าต่าง Login
   - โปรแกรมจะพยายามเชื่อมต่อฐานข้อมูล
   - หากสำเร็จ จะเข้าสู่หน้าจอหลัก

3. **ทดสอบฟีเจอร์พื้นฐาน**
   - เลือกโฟลเดอร์ที่มีไฟล์ Excel/CSV ทดสอบ
   - กดปุ่ม "ตรวจสอบไฟล์"
   - ควรเห็นรายการไฟล์ที่ตรวจพบ

---

## Troubleshooting

### ปัญหา 1: ไม่สามารถเชื่อมต่อฐานข้อมูล

**อาการ:** แสดงข้อความ "Cannot connect to database"

**วิธีแก้:**

1. ตรวจสอบว่า SQL Server กำลังทำงานอยู่:
   ```powershell
   Get-Service -Name MSSQL*
   ```

2. ตรวจสอบชื่อ Server ใน `.env`:
   - ใช้ SQL Server Management Studio (SSMS) เชื่อมต่อ
   - ชื่อ server ที่ใช้ใน SSMS คือชื่อที่ต้องใส่ใน `DB_SERVER`

3. ตรวจสอบว่าฐานข้อมูลมีอยู่จริง:
   ```sql
   SELECT name FROM sys.databases
   ```

4. ตรวจสอบสิทธิ์การเข้าถึง:
   - สำหรับ Windows Authentication: User ปัจจุบันต้องมีสิทธิ์ใน SQL Server
   - สำหรับ SQL Server Authentication: Username/Password ต้องถูกต้อง

### ปัญหา 2: ไม่พบ ODBC Driver

**อาการ:** แสดงข้อความเกี่ยวกับ ODBC Driver

**วิธีแก้:**

1. ดาวน์โหลดและติดตั้ง ODBC Driver:
   - [Download ODBC Driver 18](https://go.microsoft.com/fwlink/?linkid=2249004)

2. รันไฟล์ติดตั้งที่ดาวน์โหลด
3. Restart คอมพิวเตอร์
4. เปิดโปรแกรมอีกครั้ง

### ปัญหา 3: โปรแกรมไม่เปิด / Crash ทันที

**อาการ:** โปรแกรมปิดทันทีเมื่อเปิด หรือมีข้อความ error

**วิธีแก้:**

1. ตรวจสอบ `.env` file:
   - ต้องอยู่ในโฟลเดอร์เดียวกับ `.exe`
   - Format ต้องถูกต้อง

2. ตรวจสอบ `config` folder:
   - ต้องมีโฟลเดอร์ `config` ในโฟลเดอร์ติดตั้ง

3. รันด้วย Administrator:
   - คลิกขวาที่โปรแกรม → "Run as administrator"

4. ตรวจสอบ log files:
   - ตรวจสอบไฟล์ log ในโฟลเดอร์ที่ระบุ

### ปัญหา 4: Windows SmartScreen Block

**อาการ:** Windows Defender SmartScreen ป้องกันไม่ให้รันโปรแกรม

**วิธีแก้:**

1. คลิก "More info"
2. คลิก "Run anyway"
3. โปรแกรมจะทำงานปกติ

**หมายเหตุ:** นี่เป็นพฤติกรรมปกติสำหรับโปรแกรมที่ไม่มี code signature

---

## Uninstallation

### วิธีการถอนการติดตั้ง

**วิธีที่ 1: ผ่าน Control Panel**

1. เปิด **Control Panel**
2. ไปที่ **Programs and Features**
3. ค้นหา "SQL Server Data Pipeline"
4. คลิก **Uninstall**
5. ทำตาม Uninstall Wizard

**วิธีที่ 2: ผ่าน Start Menu**

1. เปิด **Start Menu**
2. ค้นหา "SQL Server Pipeline"
3. คลิกขวา → **Uninstall**

**วิธีที่ 3: ผ่าน Settings (Windows 10/11)**

1. เปิด **Settings** (กด `Windows + I`)
2. ไปที่ **Apps**
3. ค้นหา "SQL Server Data Pipeline"
4. คลิก **Uninstall**

### ไฟล์ที่เหลือหลังถอนการติดตั้ง

หลังถอนการติดตั้ง ไฟล์ `.env` (การตั้งค่าฐานข้อมูล) จะไม่ถูกลบ เพื่อความปลอดภัยของข้อมูล

หากต้องการลบทั้งหมด:
1. ลบโฟลเดอร์ `C:\Program Files\SQL Server Pipeline` ด้วยตนเอง (ถ้ายังมี)
2. ลบ shortcuts ที่เหลือ (ถ้ามี)

---

## Additional Information

### การอัปเดตโปรแกรม

เมื่อมีเวอร์ชันใหม่:
1. ดาวน์โหลด installer เวอร์ชันใหม่
2. รัน installer (จะติดตั้งทับเวอร์ชันเก่า)
3. การตั้งค่าเดิมจะถูกเก็บไว้

### ค้นหาความช่วยเหลือเพิ่มเติม

- **GitHub Issues**: [Report issues](https://github.com/sthongma/app-pipeline-sql-server/issues)
- **README**: ดูรายละเอียดฟีเจอร์ใน `README.md`

---

## สรุป

หลังจากติดตั้งและตั้งค่าเสร็จสิ้น คุณสามารถเริ่มใช้งาน SQL Server Data Pipeline เพื่อนำเข้าข้อมูล Excel/CSV เข้าสู่ SQL Server ได้ทันที!

หากพบปัญหาหรือต้องการความช่วยเหลือ กรุณาดูที่ส่วน [Troubleshooting](#troubleshooting) หรือติดต่อผ่าน GitHub Issues

**ขอให้ใช้งานอย่างมีความสุข!**
