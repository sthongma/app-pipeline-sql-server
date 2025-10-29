# Performance Optimization Guide

## Overview

This document describes performance optimizations and configurations for the SQL Server Pipeline application.

## Connection Pooling

### Configuration

Connection pooling is enabled by default using SQLAlchemy's `QueuePool`. Configure via environment variables:

```env
# .env file
DB_POOL_SIZE=5              # Keep 5 connections in pool (default)
DB_POOL_MAX_OVERFLOW=10     # Allow up to 10 additional connections (default)
DB_POOL_TIMEOUT=30          # Wait up to 30 seconds for connection (default)
DB_POOL_RECYCLE=3600        # Recycle connections after 1 hour (default)
```

### Benefits

- **Reduced Latency**: Reuse existing connections instead of creating new ones
- **Resource Efficiency**: Limit maximum concurrent connections
- **Connection Health**: Automatic recycling prevents stale connections
- **Pre-ping**: Test connections before use to avoid errors

### Monitoring

Check connection pool status:
```python
from utils.health_check import check_database_health

status, details = check_database_health(engine)
print(f"Pool size: {details['pool_size']}")
print(f"Checked out: {details['pool_checked_out']}")
print(f"Checked in: {details['pool_checked_in']}")
```

## Batch Processing

### Large File Handling

Files > 10,000 rows are automatically processed in chunks:

- **Chunk Size**: 5,000 rows per batch (configurable in `ProcessingConstants.CHUNK_SIZE_PROCESSING`)
- **Memory Usage**: Reduced memory footprint for large datasets
- **Progress Tracking**: Per-chunk progress reporting

### Optimization Tips

1. **Adjust Chunk Size**: For very large files (>100K rows), consider increasing chunk size:
   ```python
   # In constants.py
   CHUNK_SIZE_PROCESSING = 10000  # Increase from 5000
   ```

2. **fast_executemany**: Enabled by default for pyodbc, significantly speeds up bulk inserts

## SQL Server Optimizations

### Staging Table Approach

The application uses a two-stage upload process:

1. **Stage 1**: Upload to staging table with NVARCHAR(MAX) columns
2. **Stage 2**: Transfer to final table with type conversion and validation

**Benefits:**
- Faster initial upload (no type validation)
- Better error reporting (validation happens after upload)
- Transactional integrity (rollback on validation failure)

### NVARCHAR(MAX) Considerations

**Default Behavior:**
- Staging tables use NVARCHAR(MAX) for all columns
- Final tables use configured data types

**Performance Impact:**
- NVARCHAR(MAX) is slower for small strings
- Consider using NVARCHAR(4000) if MAX is not needed

**To Optimize:**
Configure specific lengths in `dtype_settings.json`:
```json
{
  "your_file_type": {
    "column_name": "NVARCHAR(500)"  // Instead of NVARCHAR(MAX)
  }
}
```

## Database Indexing

### Recommended Indexes

For better query performance, create indexes on frequently queried columns:

```sql
-- Index on updated_at for temporal queries
CREATE INDEX idx_tablename_updated_at
ON bronze.tablename(updated_at);

-- Composite index for common filters
CREATE INDEX idx_tablename_composite
ON bronze.tablename(column1, column2, updated_at);
```

### Deduplication Performance

The application uses `SELECT DISTINCT` for deduplication. For better performance on large datasets:

1. **Add Unique Constraint**: If natural key exists
   ```sql
   ALTER TABLE bronze.tablename
   ADD CONSTRAINT uk_natural_key UNIQUE (col1, col2);
   ```

2. **Use Hash Index**: For equality searches
   ```sql
   CREATE INDEX idx_hash
   ON bronze.tablename(col1, col2)
   WITH (FILLFACTOR = 90);
   ```

## Memory Management

### Python Memory

- **Pandas DataFrame**: Released after upload to reduce memory
- **Chunk Processing**: Prevents loading entire file into memory
- **Connection Pooling**: Limits memory used for connections

### SQL Server Memory

Configure SQL Server memory limits:
```sql
-- Set max server memory (MB)
EXEC sp_configure 'max server memory (MB)', 4096;
RECONFIGURE;

-- Check current memory usage
SELECT
    (physical_memory_in_use_kb/1024) AS Memory_usedby_Sqlserver_MB,
    (locked_page_allocations_kb/1024) AS Locked_pages_used_Sqlserver_MB
FROM sys.dm_os_process_memory;
```

## Network Optimization

### Compression

Enable SQL Server network compression:
```sql
-- For specific connection
-- Add to connection string: ;Compress=True

-- Or enable server-wide (SQL Server 2019+)
EXEC sp_configure 'network packet size', 8192;
RECONFIGURE;
```

### TCP/IP Optimization

1. **Use Named Pipes for Local Connections**:
   ```env
   DB_SERVER=localhost\SQLEXPRESS
   # Faster than TCP/IP for local connections
   ```

2. **Increase Network Packet Size**:
   ```sql
   EXEC sp_configure 'network packet size', 8192;
   RECONFIGURE;
   ```

## Monitoring & Profiling

### Application Monitoring

```python
from utils.health_check import perform_full_health_check

# Get comprehensive health report
report = perform_full_health_check(engine)
print(f"Database response time: {report['components']['database']['details']['response_time_ms']}ms")
```

### SQL Server Monitoring

```sql
-- Check expensive queries
SELECT TOP 10
    SUBSTRING(qt.TEXT, (qs.statement_start_offset/2)+1,
    ((CASE qs.statement_end_offset
        WHEN -1 THEN DATALENGTH(qt.TEXT)
        ELSE qs.statement_end_offset
    END - qs.statement_start_offset)/2)+1) AS query_text,
    qs.execution_count,
    qs.total_logical_reads,
    qs.last_logical_reads,
    qs.total_worker_time,
    qs.last_worker_time
FROM sys.dm_exec_query_stats qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) qt
ORDER BY qs.total_worker_time DESC;

-- Check connection pool usage
SELECT
    DB_NAME(dbid) as DatabaseName,
    COUNT(dbid) as NumberOfConnections,
    loginame as LoginName
FROM sys.sysprocesses
WHERE dbid > 0
GROUP BY dbid, loginame;
```

## Performance Benchmarks

### Expected Performance (Baseline)

| Operation | File Size | Expected Time |
|-----------|-----------|---------------|
| CSV Upload | 10K rows | < 5 seconds |
| CSV Upload | 100K rows | < 30 seconds |
| Excel Upload | 10K rows | < 10 seconds |
| Validation | 10K rows | < 3 seconds |
| Type Conversion | 10K rows | < 2 seconds |
| Database Response | - | < 100ms |

### Optimization Targets

- **Database Response**: < 100ms (healthy), < 1000ms (degraded)
- **Upload Rate**: > 1000 rows/second
- **Memory Usage**: < 500MB for files up to 100K rows
- **Connection Pool**: < 5 connections for typical workload

## Troubleshooting Slow Performance

### Symptom: Slow Uploads

1. **Check Connection Pool**:
   - Ensure pool not exhausted
   - Increase `DB_POOL_SIZE` if needed

2. **Check Network**:
   - Test connection speed
   - Use local server if possible

3. **Check SQL Server**:
   ```sql
   -- Check for blocking
   EXEC sp_who2 'active';

   -- Check wait stats
   SELECT * FROM sys.dm_os_wait_stats
   ORDER BY wait_time_ms DESC;
   ```

### Symptom: High Memory Usage

1. **Reduce Chunk Size**:
   ```python
   # In constants.py
   CHUNK_SIZE_PROCESSING = 2500  # Reduce from 5000
   ```

2. **Check for Memory Leaks**:
   ```python
   import psutil
   import os

   process = psutil.Process(os.getpid())
   print(f"Memory usage: {process.memory_info().rss / 1024 / 1024} MB")
   ```

### Symptom: Connection Timeouts

1. **Increase Timeout**:
   ```env
   DB_POOL_TIMEOUT=60  # Increase from 30 seconds
   ```

2. **Check SQL Server Connectivity**:
   ```sql
   -- Check max connections
   EXEC sp_configure 'user connections';
   ```

## Best Practices

1. **Use Windows Authentication**: Faster than SQL Server authentication
2. **Index Frequently Queried Columns**: Especially `updated_at`
3. **Regular Maintenance**: Update statistics, rebuild indexes
4. **Monitor Regularly**: Use health checks and SQL Server DMVs
5. **Test with Production Data**: Benchmark with real file sizes
6. **Scale Horizontally**: Consider multiple application instances for high load

## Advanced: Database Partitioning

For very large tables (millions of rows), consider partitioning:

```sql
-- Create partition function (by date)
CREATE PARTITION FUNCTION pf_by_month (datetime2)
AS RANGE RIGHT FOR VALUES
    ('2024-01-01', '2024-02-01', '2024-03-01', ...);

-- Create partition scheme
CREATE PARTITION SCHEME ps_by_month
AS PARTITION pf_by_month
ALL TO ([PRIMARY]);

-- Create partitioned table
CREATE TABLE bronze.large_table (
    id INT IDENTITY(1,1),
    updated_at DATETIME2,
    -- other columns
) ON ps_by_month(updated_at);
```

---

**Last Updated:** 2025-10-29
**Applies to Version:** 2.2.0+
