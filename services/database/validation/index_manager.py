"""
Temporary index management module for validation performance optimization
"""

import logging
from typing import Dict, List
from sqlalchemy import text

from .base_validator import BaseValidator


class IndexManager(BaseValidator):
    """
    Manager สำหรับจัดการ temporary indexes เพื่อเพิ่มประสิทธิภาพการ validation
    
    สร้างและลบ indexes ชั่วคราวเพื่อเร่งการ query ในระหว่างการ validation
    """
    
    def __init__(self, engine):
        """
        Initialize IndexManager
        
        Args:
            engine: SQLAlchemy engine instance
        """
        super().__init__(engine)
        self.created_indexes = []  # เก็บรายการ indexes ที่สร้างขึ้น
    
    def validate(self, conn, staging_table: str, schema_name: str, columns: List, 
                total_rows: int, chunk_size: int, log_func=None, **kwargs) -> List[Dict]:
        """
        Implementation ของ abstract method จาก BaseValidator
        
        สำหรับ IndexManager ไม่ได้ทำ validation โดยตรง แต่จัดการ indexes
        Method นี้จึงไม่ใช้งาน
        
        Args:
            conn: Database connection (ไม่ใช้)
            staging_table: Staging table name (ไม่ใช้)
            schema_name: Schema name (ไม่ใช้)
            columns: List of columns (ไม่ใช้)
            total_rows: Total number of rows (ไม่ใช้)
            chunk_size: Chunk size (ไม่ใช้)
            log_func: Logging function (ไม่ใช้)
            **kwargs: Additional parameters (ไม่ใช้)
            
        Returns:
            List[Dict]: Empty list (IndexManager ไม่ทำ validation)
        """
        # IndexManager ไม่ทำ validation โดยตรง
        return []
    
    def create_temp_indexes(self, staging_table: str, required_cols: Dict, 
                          schema_name: str, log_func=None) -> int:
        """
        สร้าง temporary indexes เพื่อเร่งการ validation
        
        Args:
            staging_table: Staging table name
            required_cols: Required columns dictionary
            schema_name: Schema name
            log_func: Logging function
            
        Returns:
            int: Number of indexes created
        """
        index_count = 0
        
        try:
            with self.engine.connect() as conn:
                for col_name in required_cols.keys():
                    if self._should_create_index(col_name, required_cols[col_name]):
                        if self._create_single_index(conn, staging_table, schema_name, col_name, log_func):
                            index_count += 1
                
                conn.commit()
                
                if log_func and index_count > 0:
                    log_func(f"   Created {index_count} temporary indexes for validation")
                    
        except Exception as e:
            if log_func:
                log_func(f"   Warning: Unable to create temporary indexes: {e}")
        
        return index_count
    
    def _should_create_index(self, col_name: str, dtype) -> bool:
        """
        ตัดสินใจว่าควรสร้าง index สำหรับคอลัมน์นี้หรือไม่
        
        Args:
            col_name: Column name
            dtype: Data type
            
        Returns:
            bool: True if should create index
        """
        # ไม่สร้าง index สำหรับคอลัมน์ที่มีชื่อยาวเกินไป
        if len(col_name) > 100:
            return False
        
        # ไม่สร้าง index สำหรับ Text columns ที่อาจมีข้อมูลยาว
        from sqlalchemy.types import Text as SA_Text
        if isinstance(dtype, SA_Text):
            return False
        
        return True
    
    def _create_single_index(self, conn, staging_table: str, schema_name: str, 
                           col_name: str, log_func=None) -> bool:
        """
        สร้าง index เดียวสำหรับคอลัมน์
        
        Args:
            conn: Database connection
            staging_table: Staging table name
            schema_name: Schema name
            col_name: Column name
            log_func: Logging function
            
        Returns:
            bool: True if index created successfully
        """
        index_name = self._generate_index_name(staging_table, col_name)
        safe_col = self.safe_column_name(col_name)
        
        try:
            # ตรวจสอบว่า index มีอยู่แล้วหรือไม่
            if self._index_exists(conn, schema_name, staging_table, index_name):
                return False
            
            # สร้าง index ใหม่
            create_index_sql = f"""
                CREATE NONCLUSTERED INDEX [{index_name}] 
                ON {schema_name}.{staging_table} ({safe_col})
                WHERE {safe_col} IS NOT NULL
            """
            
            conn.execute(text(create_index_sql))
            
            # เก็บข้อมูล index ที่สร้าง
            index_info = {
                'name': index_name,
                'table': staging_table,
                'schema': schema_name,
                'column': col_name
            }
            self.created_indexes.append(index_info)
            
            return True
            
        except Exception as e:
            # ถ้าสร้าง index ไม่ได้ก็ข้าม (อาจเป็น column ที่มีข้อมูลยาวเกินไป)
            if log_func:
                self.logger.debug(f"Could not create index for {col_name}: {e}")
            return False
    
    def _generate_index_name(self, staging_table: str, col_name: str) -> str:
        """
        สร้างชื่อ index ที่ไม่ซ้ำและไม่ยาวเกินไป
        
        Args:
            staging_table: Staging table name
            col_name: Column name
            
        Returns:
            str: Generated index name
        """
        # สร้างชื่อ index ที่ปลอดภัย
        safe_table = staging_table.replace(' ', '_').replace('-', '_')
        safe_column = col_name.replace(' ', '_').replace('-', '_')
        
        index_name = f"temp_idx_{safe_table}_{safe_column}"
        
        # ตัดให้ไม่เกิน 128 ตัวอักษร (SQL Server limit)
        if len(index_name) > 128:
            index_name = index_name[:128]
        
        return index_name
    
    def _index_exists(self, conn, schema_name: str, table_name: str, index_name: str) -> bool:
        """
        ตรวจสอบว่า index มีอยู่แล้วหรือไม่
        
        Args:
            conn: Database connection
            schema_name: Schema name
            table_name: Table name
            index_name: Index name
            
        Returns:
            bool: True if index exists
        """
        check_sql = f"""
            SELECT COUNT(*) FROM sys.indexes 
            WHERE object_id = OBJECT_ID('{schema_name}.{table_name}') 
            AND name = '{index_name}'
        """
        
        result = self.execute_query_safely(
            conn, check_sql, f"Error checking if index {index_name} exists"
        )
        
        if result is None:
            return False
        
        return result.scalar() > 0
    
    def drop_temp_indexes(self, staging_table: str, required_cols: Dict, 
                         schema_name: str, log_func=None) -> int:
        """
        ลบ temporary indexes หลังจาก validation เสร็จ
        
        Args:
            staging_table: Staging table name
            required_cols: Required columns dictionary
            schema_name: Schema name
            log_func: Logging function
            
        Returns:
            int: Number of indexes dropped
        """
        dropped_count = 0
        
        try:
            with self.engine.connect() as conn:
                # ลบจาก created_indexes list
                for index_info in self.created_indexes.copy():
                    if (index_info['table'] == staging_table and 
                        index_info['schema'] == schema_name):
                        
                        if self._drop_single_index(conn, index_info, log_func):
                            dropped_count += 1
                            self.created_indexes.remove(index_info)
                
                # ลบ indexes ที่อาจสร้างไว้ก่อนหน้า (fallback)
                for col_name in required_cols.keys():
                    index_name = self._generate_index_name(staging_table, col_name)
                    if self._index_exists(conn, schema_name, staging_table, index_name):
                        if self._drop_index_by_name(conn, schema_name, staging_table, index_name, log_func):
                            dropped_count += 1
                
                conn.commit()
                
                if log_func and dropped_count > 0:
                    log_func(f"   Cleaned up {dropped_count} temporary indexes")
                    
        except Exception as e:
            if log_func:
                log_func(f"   Warning: Unable to drop temporary indexes: {e}")
        
        return dropped_count
    
    def _drop_single_index(self, conn, index_info: Dict, log_func=None) -> bool:
        """
        ลบ index เดียว
        
        Args:
            conn: Database connection
            index_info: Index information dictionary
            log_func: Logging function
            
        Returns:
            bool: True if index dropped successfully
        """
        try:
            drop_sql = f"DROP INDEX [{index_info['name']}] ON {index_info['schema']}.{index_info['table']}"
            conn.execute(text(drop_sql))
            return True
        except Exception as e:
            if log_func:
                self.logger.debug(f"Could not drop index {index_info['name']}: {e}")
            return False
    
    def _drop_index_by_name(self, conn, schema_name: str, table_name: str, 
                           index_name: str, log_func=None) -> bool:
        """
        ลบ index โดยใช้ชื่อ
        
        Args:
            conn: Database connection
            schema_name: Schema name
            table_name: Table name
            index_name: Index name
            log_func: Logging function
            
        Returns:
            bool: True if index dropped successfully
        """
        try:
            drop_sql = f"DROP INDEX [{index_name}] ON {schema_name}.{table_name}"
            conn.execute(text(drop_sql))
            return True
        except Exception as e:
            if log_func:
                self.logger.debug(f"Could not drop index {index_name}: {e}")
            return False
    
    def cleanup_all_temp_indexes(self, log_func=None) -> int:
        """
        ลบ temporary indexes ทั้งหมดที่ถูกสร้างโดย manager นี้
        
        Args:
            log_func: Logging function
            
        Returns:
            int: Number of indexes cleaned up
        """
        cleaned_count = 0
        
        try:
            with self.engine.connect() as conn:
                for index_info in self.created_indexes.copy():
                    if self._drop_single_index(conn, index_info, log_func):
                        cleaned_count += 1
                        self.created_indexes.remove(index_info)
                
                conn.commit()
                
                if log_func and cleaned_count > 0:
                    log_func(f"   Cleaned up {cleaned_count} temporary indexes")
                    
        except Exception as e:
            if log_func:
                log_func(f"   Warning: Error during cleanup: {e}")
        
        return cleaned_count
    
    def get_index_usage_stats(self, schema_name: str, table_name: str) -> List[Dict]:
        """
        ดึงสถิติการใช้งาน indexes ของ table
        
        Args:
            schema_name: Schema name
            table_name: Table name
            
        Returns:
            List[Dict]: Index usage statistics
        """
        stats_query = f"""
            SELECT 
                i.name as index_name,
                i.type_desc as index_type,
                us.user_seeks,
                us.user_scans,
                us.user_lookups,
                us.user_updates,
                us.last_user_seek,
                us.last_user_scan,
                us.last_user_lookup
            FROM sys.indexes i
            LEFT JOIN sys.dm_db_index_usage_stats us 
                ON i.object_id = us.object_id AND i.index_id = us.index_id
            WHERE i.object_id = OBJECT_ID('{schema_name}.{table_name}')
            AND i.name IS NOT NULL
            ORDER BY i.name
        """
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(stats_query))
                
                stats = []
                for row in result.fetchall():
                    stats.append({
                        'index_name': row.index_name,
                        'index_type': row.index_type,
                        'user_seeks': row.user_seeks or 0,
                        'user_scans': row.user_scans or 0,
                        'user_lookups': row.user_lookups or 0,
                        'user_updates': row.user_updates or 0,
                        'last_user_seek': row.last_user_seek,
                        'last_user_scan': row.last_user_scan,
                        'last_user_lookup': row.last_user_lookup,
                        'total_usage': (row.user_seeks or 0) + (row.user_scans or 0) + (row.user_lookups or 0)
                    })
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Error getting index usage stats: {e}")
            return []
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup all indexes"""
        self.cleanup_all_temp_indexes()
