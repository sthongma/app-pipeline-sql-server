# Load Testing

Performance and load testing utilities for SQL Server Pipeline.

## Overview

Load tests validate system performance under various conditions:
- Different file sizes (1K, 10K, 100K rows)
- Concurrent upload scenarios
- Connection pool stress testing
- Health check responsiveness

## Requirements

```bash
pip install -r requirements-lock.txt
pip install numpy  # Additional dependency for load testing
```

## Running Load Tests

### All Tests
```bash
python tests/load_tests/load_test.py --scenario all --cleanup
```

### Specific Scenarios

**Small File (1K rows)**
```bash
python tests/load_tests/load_test.py --scenario small
```

**Medium File (10K rows)**
```bash
python tests/load_tests/load_test.py --scenario medium
```

**Large File (100K rows)**
```bash
python tests/load_tests/load_test.py --scenario large
```

**Concurrent Uploads**
```bash
python tests/load_tests/load_test.py --scenario concurrent
```

**Connection Pool Stress**
```bash
python tests/load_tests/load_test.py --scenario pool
```

**Health Check**
```bash
python tests/load_tests/load_test.py --scenario health
```

## Options

- `--scenario`: Test scenario to run (small, medium, large, concurrent, pool, health, all)
- `--schema`: Test schema name (default: load_test)
- `--cleanup`: Cleanup test data after completion

## Example Output

```
================================================================================
SQL SERVER PIPELINE - LOAD TESTING
================================================================================
Start Time: 2025-10-29 10:30:00
Scenario: all
Test Schema: load_test

🔧 Setting up test environment...
   Schema: load_test
   ✅ Test environment ready

📊 Testing small file (1,000 rows)...
📊 Testing medium file (10,000 rows)...
📊 Testing large file (100,000 rows)...
📊 Testing concurrent uploads (5 threads, 5K rows each)...
📊 Testing connection pool under stress...
📊 Testing health check responsiveness...

================================================================================
LOAD TEST RESULTS SUMMARY
================================================================================

Scenario                      Rows     Duration     Throughput     Status
--------------------------------------------------------------------------------
Small File (1K rows)          1,000       0.45s       2,222 r/s   ✅ PASS
Medium File (10K rows)       10,000       2.10s       4,762 r/s   ✅ PASS
Large File (100K rows)      100,000      18.50s       5,405 r/s   ✅ PASS
Concurrent Uploads (5)       25,000       5.20s       4,808 r/s   ✅ PASS
Connection Pool Stress           50       1.30s          38 r/s   ✅ PASS
Health Check Under Load           1       0.08s          12 r/s   ✅ PASS

================================================================================
STATISTICS
================================================================================
Total Tests: 6
Successful: 6
Failed: 0

Average Throughput: 3,875 rows/second
Max Throughput: 5,405 rows/second
Min Throughput: 12 rows/second

End Time: 2025-10-29 10:31:30
================================================================================
```

## Performance Benchmarks

### Expected Results (Baseline)

| Test | Rows | Expected Duration | Expected Throughput |
|------|------|-------------------|---------------------|
| Small | 1K | < 1s | > 1,000 r/s |
| Medium | 10K | < 5s | > 2,000 r/s |
| Large | 100K | < 30s | > 3,000 r/s |
| Concurrent | 25K | < 10s | > 2,500 r/s |

### Status Criteria

- ✅ **PASS**: Meets or exceeds performance targets
- ⚠️ **DEGRADED**: 50-80% of target performance
- ❌ **FAIL**: Below 50% of target or errors occurred

## Interpreting Results

### Throughput
- **> 5,000 r/s**: Excellent performance
- **2,000-5,000 r/s**: Good performance
- **1,000-2,000 r/s**: Acceptable performance
- **< 1,000 r/s**: Poor performance - investigate

### Common Issues

**Low Throughput:**
1. Check network latency
2. Verify connection pool settings
3. Check SQL Server resource usage
4. Review indexing strategy

**Concurrent Upload Failures:**
1. Increase connection pool size
2. Check max_overflow setting
3. Verify SQL Server connection limits
4. Check for locking/blocking issues

**Health Check Slow:**
1. Database may be under heavy load
2. Check for long-running queries
3. Verify network connectivity
4. Review SQL Server performance counters

## Test Data Cleanup

Test data is stored in the specified schema (default: `load_test`).

**Manual Cleanup:**
```sql
-- Drop all tables in load_test schema
DECLARE @sql NVARCHAR(MAX) = '';
SELECT @sql += 'DROP TABLE [load_test].[' + name + ']; '
FROM sys.tables
WHERE schema_id = SCHEMA_ID('load_test');
EXEC sp_executesql @sql;

-- Drop schema
DROP SCHEMA [load_test];
```

**Automatic Cleanup:**
```bash
# Use --cleanup flag
python tests/load_tests/load_test.py --scenario all --cleanup
```

## Advanced Usage

### Custom Test Scenarios

Modify `load_test.py` to add custom scenarios:

```python
def test_custom_scenario(engine, schema_name: str, results: LoadTestResults):
    """Your custom test"""
    df = generate_test_data(50000)  # Custom size
    success, duration, error = upload_test_data(engine, schema_name, 'custom_test', df)
    results.add_result('Custom Scenario', len(df), duration, success, error)
```

### Integration with CI/CD

Add to GitHub Actions:

```yaml
- name: Run Load Tests
  run: |
    python tests/load_tests/load_test.py --scenario small --cleanup
  timeout-minutes: 10
```

## Troubleshooting

**"No database configuration found"**
- Ensure `.env` file exists with DB_SERVER and DB_NAME
- Or set environment variables directly

**"Connection timeout"**
- Increase DB_POOL_TIMEOUT in .env
- Check SQL Server is accepting connections
- Verify firewall settings

**"Memory error with large files"**
- Reduce test data size
- Increase available system memory
- Close other applications

## Notes

- Load tests require a real SQL Server instance
- Tests create temporary tables in test schema
- Use `--cleanup` to remove test data automatically
- Run during off-peak hours for accurate results
- Results may vary based on hardware and network
