"""
Permission Checker Service for PIPELINE_SQLSERVER

Checks SQL Server permissions required for application operation
"""

import logging
from typing import Dict, List
from sqlalchemy import text


class PermissionCheckerService:
    """
    SQL Server permission checking service
    
    Checks required permissions:
    - CREATE SCHEMA
    - CREATE TABLE 
    - DROP TABLE
    - INSERT, UPDATE, DELETE
    - SELECT
    - ALTER TABLE
    """
    
    def __init__(self, engine=None, log_callback=None):
        """
        Initialize Permission Checker Service
        
        Args:
            engine: SQLAlchemy engine (if not provided, will create new one)
            log_callback: Function for logging (None = silent mode)
        """
        self.engine = engine
        # ใช้ silent callback เป็นค่าเริ่มต้น (ไม่แสดง log ใน CLI)
        self.log_callback = log_callback if log_callback else (lambda msg: None)
        self.logger = logging.getLogger(__name__)
        
        # กำหนดสิทธิ์ที่จำเป็น
        self.required_permissions = [
            {
                'name': 'CREATE SCHEMA',
                'description': 'Permission to create new schema',
                'test_query': self._test_create_schema_permission,
                'critical': True
            },
            {
                'name': 'CREATE TABLE',
                'description': 'Permission to create tables',
                'test_query': self._test_create_table_permission,
                'critical': True
            },
            {
                'name': 'DROP TABLE',
                'description': 'Permission to drop tables',
                'test_query': self._test_drop_table_permission,
                'critical': True
            },
            {
                'name': 'INSERT',
                'description': 'Permission to insert data',
                'test_query': self._test_insert_permission,
                'critical': True
            },
            {
                'name': 'UPDATE',
                'description': 'Permission to update data',
                'test_query': self._test_update_permission,
                'critical': False
            },
            {
                'name': 'DELETE',
                'description': 'Permission to delete data',
                'test_query': self._test_delete_permission,
                'critical': False
            },
            {
                'name': 'ALTER TABLE',
                'description': 'Permission to alter table structure',
                'test_query': self._test_alter_table_permission,
                'critical': True
            },
            {
                'name': 'TRUNCATE TABLE',
                'description': 'Permission to truncate tables',
                'test_query': self._test_truncate_permission,
                'critical': True
            }
        ]
    
    def check_all_permissions(self, schema_name: str = 'bronze') -> Dict:
        """
        ตรวจสอบสิทธิ์ทั้งหมดที่จำเป็น
        
        Args:
            schema_name: ชื่อ schema ที่ต้องการตรวจสอบ
            
        Returns:
            Dict: ผลการตรวจสอบสิทธิ์
        """
        if not self.engine:
            return {
                'success': False,
                'error': 'Database connection not found',
                'permissions': [],
                'missing_critical': [],
                'missing_optional': []
            }
        
        # ไม่แสดงข้อความ "Starting SQL Server permission check" ใน GUI
        # self.log_callback("Starting SQL Server permission check...")

        results = {
            'success': True,
            'user_info': {},
            'permissions': [],
            'missing_critical': [],
            'missing_optional': [],
            'recommendations': []
        }

        try:
            # ตรวจสอบข้อมูลผู้ใช้
            results['user_info'] = self._get_user_info()

            # ตรวจสอบแต่ละสิทธิ์ (ไม่แสดงข้อความแต่ละสิทธิ์ใน GUI)
            for permission in self.required_permissions:
                try:
                    has_permission = permission['test_query'](schema_name)

                    permission_result = {
                        'name': permission['name'],
                        'description': permission['description'],
                        'granted': has_permission,
                        'critical': permission['critical']
                    }

                    results['permissions'].append(permission_result)

                    if not has_permission:
                        if permission['critical']:
                            results['missing_critical'].append(permission['name'])
                        else:
                            results['missing_optional'].append(permission['name'])

                    # ไม่แสดงข้อความแต่ละสิทธิ์ใน GUI
                    # status = "" if has_permission else ("Error: " if permission['critical'] else "Warning: ")
                    # self.log_callback(f"  {status} {permission['name']}: {permission['description']}")

                except Exception as e:
                    self.logger.error(f"Error testing {permission['name']}: {e}")
                    results['missing_critical'].append(permission['name'])
                    # ไม่แสดง error ใน GUI
                    # self.log_callback(f"  {permission['name']}: Cannot test - {e}")

            # ไม่แสดงสรุปผลใน GUI
            # if results['missing_critical']:
            #     results['success'] = False
            #     results['recommendations'] = self._generate_recommendations(results)
            # else:
            #     if results['missing_optional']:
            #         pass

            if results['missing_critical']:
                results['success'] = False
                results['recommendations'] = self._generate_recommendations(results)
            
        except Exception as e:
            results['success'] = False
            results['error'] = f"An error occurred while checking permissions: {e}"
            self.logger.error(f"Permission check failed: {e}")
        
        return results
    
    def _get_user_info(self) -> Dict:
        """ดึงข้อมูลผู้ใช้ปัจจุบัน"""
        try:
            with self.engine.connect() as conn:
                # ข้อมูลผู้ใช้พื้นฐาน
                user_query = text("""
                    SELECT 
                        SYSTEM_USER as login_name,
                        USER_NAME() as user_name,
                        IS_SRVROLEMEMBER('sysadmin') as is_sysadmin,
                        IS_SRVROLEMEMBER('dbcreator') as is_dbcreator,
                        IS_MEMBER('db_owner') as is_db_owner,
                        IS_MEMBER('db_ddladmin') as is_db_ddladmin,
                        IS_MEMBER('db_datawriter') as is_db_datawriter,
                        IS_MEMBER('db_datareader') as is_db_datareader
                """)
                
                result = conn.execute(user_query).fetchone()
                
                return {
                    'login_name': result[0],
                    'user_name': result[1],
                    'is_sysadmin': bool(result[2]),
                    'is_dbcreator': bool(result[3]),
                    'is_db_owner': bool(result[4]),
                    'is_db_ddladmin': bool(result[5]),
                    'is_db_datawriter': bool(result[6]),
                    'is_db_datareader': bool(result[7])
                }
        except Exception as e:
            self.logger.error(f"Failed to get user info: {e}")
            return {'error': str(e)}
    
    def _test_create_schema_permission(self, schema_name: str) -> bool:
        """ทดสอบสิทธิ์ CREATE SCHEMA"""
        try:
            test_schema = f"test_schema_{schema_name}"
            with self.engine.connect() as conn:
                # ลองสร้าง schema ทดสอบ
                conn.execute(text(f"CREATE SCHEMA [{test_schema}]"))
                # ลบทิ้งทันที
                conn.execute(text(f"DROP SCHEMA [{test_schema}]"))
                conn.commit()
                return True
        except Exception:
            return False
    
    def _test_create_table_permission(self, schema_name: str) -> bool:
        """ทดสอบสิทธิ์ CREATE TABLE"""
        try:
            # ตรวจสอบว่ามี schema หรือไม่ ถ้าไม่มีให้สร้าง
            self._ensure_test_schema_exists(schema_name)
            
            test_table = f"{schema_name}.test_permissions_table"
            with self.engine.connect() as conn:
                # ลองสร้างตารางทดสอบ
                conn.execute(text(f"""
                    CREATE TABLE [{test_table}] (
                        id INT PRIMARY KEY,
                        test_column NVARCHAR(50)
                    )
                """))
                # ลบทิ้งทันที
                conn.execute(text(f"DROP TABLE [{test_table}]"))
                conn.commit()
                return True
        except Exception:
            return False
    
    def _test_drop_table_permission(self, schema_name: str) -> bool:
        """ทดสอบสิทธิ์ DROP TABLE"""
        try:
            # ตรวจสอบว่ามี schema หรือไม่ ถ้าไม่มีให้สร้าง
            self._ensure_test_schema_exists(schema_name)
            
            test_table = f"{schema_name}.test_drop_table"
            with self.engine.connect() as conn:
                # สร้างตารางทดสอบ
                conn.execute(text(f"""
                    CREATE TABLE [{test_table}] (
                        id INT PRIMARY KEY
                    )
                """))
                # ลองลบตาราง
                conn.execute(text(f"DROP TABLE [{test_table}]"))
                conn.commit()
                return True
        except Exception:
            return False
    
    def _test_insert_permission(self, schema_name: str) -> bool:
        """ทดสอบสิทธิ์ INSERT"""
        try:
            # ตรวจสอบว่ามี schema หรือไม่ ถ้าไม่มีให้สร้าง
            self._ensure_test_schema_exists(schema_name)
            
            test_table = f"{schema_name}.test_insert_table"
            with self.engine.connect() as conn:
                # สร้างตารางทดสอบ
                conn.execute(text(f"""
                    CREATE TABLE [{test_table}] (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        test_data NVARCHAR(50)
                    )
                """))
                # ลอง INSERT
                conn.execute(text(f"INSERT INTO [{test_table}] (test_data) VALUES ('test')"))
                # ลบตารางทดสอบ
                conn.execute(text(f"DROP TABLE [{test_table}]"))
                conn.commit()
                return True
        except Exception:
            return False
    
    def _test_update_permission(self, schema_name: str) -> bool:
        """ทดสอบสิทธิ์ UPDATE"""
        try:
            # ตรวจสอบว่ามี schema หรือไม่ ถ้าไม่มีให้สร้าง
            self._ensure_test_schema_exists(schema_name)
            
            test_table = f"{schema_name}.test_update_table"
            with self.engine.connect() as conn:
                # สร้างตารางทดสอบ
                conn.execute(text(f"""
                    CREATE TABLE [{test_table}] (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        test_data NVARCHAR(50)
                    )
                """))
                # INSERT ข้อมูลทดสอบ
                conn.execute(text(f"INSERT INTO [{test_table}] (test_data) VALUES ('test')"))
                # ลอง UPDATE
                conn.execute(text(f"UPDATE [{test_table}] SET test_data = 'updated' WHERE id = 1"))
                # ลบตารางทดสอบ
                conn.execute(text(f"DROP TABLE [{test_table}]"))
                conn.commit()
                return True
        except Exception:
            return False
    
    def _test_delete_permission(self, schema_name: str) -> bool:
        """ทดสอบสิทธิ์ DELETE"""
        try:
            # ตรวจสอบว่ามี schema หรือไม่ ถ้าไม่มีให้สร้าง
            self._ensure_test_schema_exists(schema_name)
            
            test_table = f"{schema_name}.test_delete_table"
            with self.engine.connect() as conn:
                # สร้างตารางทดสอบ
                conn.execute(text(f"""
                    CREATE TABLE [{test_table}] (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        test_data NVARCHAR(50)
                    )
                """))
                # INSERT ข้อมูลทดสอบ
                conn.execute(text(f"INSERT INTO [{test_table}] (test_data) VALUES ('test')"))
                # ลอง DELETE
                conn.execute(text(f"DELETE FROM [{test_table}] WHERE id = 1"))
                # ลบตารางทดสอบ
                conn.execute(text(f"DROP TABLE [{test_table}]"))
                conn.commit()
                return True
        except Exception:
            return False
    
    def _test_alter_table_permission(self, schema_name: str) -> bool:
        """ทดสอบสิทธิ์ ALTER TABLE"""
        try:
            # ตรวจสอบว่ามี schema หรือไม่ ถ้าไม่มีให้สร้าง
            self._ensure_test_schema_exists(schema_name)
            
            test_table = f"{schema_name}.test_alter_table"
            with self.engine.connect() as conn:
                # สร้างตารางทดสอบ
                conn.execute(text(f"""
                    CREATE TABLE [{test_table}] (
                        id INT PRIMARY KEY
                    )
                """))
                # ลอง ALTER TABLE
                conn.execute(text(f"ALTER TABLE [{test_table}] ADD test_column NVARCHAR(50)"))
                # ลบตารางทดสอบ
                conn.execute(text(f"DROP TABLE [{test_table}]"))
                conn.commit()
                return True
        except Exception:
            return False
    
    def _test_truncate_permission(self, schema_name: str) -> bool:
        """ทดสอบสิทธิ์ TRUNCATE TABLE"""
        try:
            # ตรวจสอบว่ามี schema หรือไม่ ถ้าไม่มีให้สร้าง
            self._ensure_test_schema_exists(schema_name)
            
            test_table = f"{schema_name}.test_truncate_table"
            with self.engine.connect() as conn:
                # สร้างตารางทดสอบ
                conn.execute(text(f"""
                    CREATE TABLE [{test_table}] (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        test_data NVARCHAR(50)
                    )
                """))
                # INSERT ข้อมูลทดสอบ
                conn.execute(text(f"INSERT INTO [{test_table}] (test_data) VALUES ('test')"))
                # ลอง TRUNCATE
                conn.execute(text(f"TRUNCATE TABLE [{test_table}]"))
                # ลบตารางทดสอบ
                conn.execute(text(f"DROP TABLE [{test_table}]"))
                conn.commit()
                return True
        except Exception:
            return False
    
    def _ensure_test_schema_exists(self, schema_name: str):
        """ตรวจสอบและสร้าง schema สำหรับทดสอบ"""
        try:
            with self.engine.connect() as conn:
                # ตรวจสอบว่ามี schema หรือไม่
                result = conn.execute(text(f"""
                    SELECT COUNT(*) FROM sys.schemas WHERE name = '{schema_name}'
                """)).scalar()
                
                if result == 0:
                    # สร้าง schema ถ้ายังไม่มี
                    conn.execute(text(f"CREATE SCHEMA [{schema_name}]"))
                    conn.commit()
        except Exception:
            # ถ้าสร้าง schema ไม่ได้ ให้ใช้ dbo แทน
            pass
    
    def _generate_recommendations(self, results: Dict) -> List[str]:
        """สร้างคำแนะนำสำหรับการแก้ไขสิทธิ์"""
        recommendations = []
        user_info = results.get('user_info', {})
        missing = results.get('missing_critical', [])
        
        if not missing:
            return recommendations
        
        # คำแนะนำทั่วไป
        recommendations.append("คำแนะนำการแก้ไขสิทธิ์:")
        recommendations.append("")

        # ตรวจสอบ role ปัจจุบัน
        if user_info.get('is_sysadmin'):
            recommendations.append("Warning: ผู้ใช้เป็น sysadmin แล้ว แต่ยังมีปัญหาสิทธิ์ - อาจเป็นปัญหาการเชื่อมต่อ")
        elif user_info.get('is_db_owner'):
            recommendations.append("Warning: ผู้ใช้เป็น db_owner แล้ว แต่ยังมีปัญหาสิทธิ์ - ตรวจสอบ schema permission")
        else:
            recommendations.append("1. เพิ่ม User ใน Database Role:")
            recommendations.append("   • db_owner (แนะนำ - ให้สิทธิ์เต็ม)")
            recommendations.append("   • หรือ db_ddladmin + db_datawriter + db_datareader")

        recommendations.append("")
        recommendations.append("2. คำสั่ง SQL สำหรับ DBA:")
        recommendations.append(f"   USE [{user_info.get('database_name', 'YourDatabase')}]")
        recommendations.append(f"   ALTER ROLE db_owner ADD MEMBER [{user_info.get('login_name', 'YourUser')}]")

        recommendations.append("")
        recommendations.append("3. หรือให้สิทธิ์เฉพาะที่จำเป็น:")
        if 'CREATE SCHEMA' in missing:
            recommendations.append("   GRANT CREATE SCHEMA TO [YourUser]")
        if 'CREATE TABLE' in missing:
            recommendations.append("   GRANT CREATE TABLE TO [YourUser]")
        if 'ALTER TABLE' in missing:
            recommendations.append("   -- สิทธิ์ ALTER รวมอยู่ใน db_ddladmin")

        recommendations.append("")
        recommendations.append("4. วิธีที่เร็วที่สุด (สำหรับ Development):")
        recommendations.append(f"   ALTER SERVER ROLE sysadmin ADD MEMBER [{user_info.get('login_name', 'YourUser')}]")
        recommendations.append("   Warning: ใช้เฉพาะ Development เท่านั้น!")
        
        return recommendations
    
    def generate_permission_report(self, schema_name: str = 'bronze') -> str:
        """สร้างรายงานสิทธิ์แบบละเอียด"""
        results = self.check_all_permissions(schema_name)
        
        report = []
        report.append("=" * 70)
        report.append("รายงานการตรวจสอบสิทธิ์ SQL Server")
        report.append("=" * 70)

        # ข้อมูลผู้ใช้
        user_info = results.get('user_info', {})
        if user_info and 'error' not in user_info:
            report.append(f"ผู้ใช้: {user_info.get('login_name', 'ไม่ระบุ')}")
            report.append(f"Database User: {user_info.get('user_name', 'ไม่ระบุ')}")
            report.append(f"System Admin: {'Yes' if user_info.get('is_sysadmin') else 'No'}")
            report.append(f"DB Creator: {'Yes' if user_info.get('is_dbcreator') else 'No'}")
            report.append(f"DB Owner: {'Yes' if user_info.get('is_db_owner') else 'No'}")
            report.append(f"DDL Admin: {'Yes' if user_info.get('is_db_ddladmin') else 'No'}")
            report.append(f"Data Writer: {'Yes' if user_info.get('is_db_datawriter') else 'No'}")
            report.append(f"Data Reader: {'Yes' if user_info.get('is_db_datareader') else 'No'}")

        report.append("")
        report.append("สิทธิ์ที่ตรวจสอบ:")
        report.append("-" * 50)

        # รายละเอียดสิทธิ์
        for perm in results.get('permissions', []):
            status = "[OK]" if perm['granted'] else ("[ERROR]" if perm['critical'] else "[WARNING]")
            critical = "จำเป็น" if perm['critical'] else "เสริม"
            report.append(f"{status} {perm['name']} ({critical})")
            report.append(f"    {perm['description']}")

        report.append("")

        # สรุปผล
        if results.get('success'):
            report.append("ผลการตรวจสอบ: ผ่าน")
            report.append("ผู้ใช้มีสิทธิ์ครบถ้วนสำหรับการใช้งานแอปพลิเคชัน")
        else:
            report.append("Error: ผลการตรวจสอบ: ไม่ผ่าน")
            report.append(f"สิทธิ์ที่จำเป็นขาดหายไป: {', '.join(results.get('missing_critical', []))}")

        if results.get('missing_optional'):
            report.append(f"Warning: สิทธิ์เสริมที่ขาดหายไป: {', '.join(results.get('missing_optional', []))}")
        
        # คำแนะนำ
        recommendations = results.get('recommendations', [])
        if recommendations:
            report.append("")
            report.extend(recommendations)
        
        report.append("")
        report.append("=" * 70)
        
        return "\n".join(report)