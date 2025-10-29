"""
Load testing script for SQL Server Pipeline

Tests system performance under various load conditions:
- Small files (1K rows)
- Medium files (10K rows)
- Large files (100K rows)
- Concurrent uploads
- Connection pool stress test

Usage:
    python tests/load_tests/load_test.py --scenario small
    python tests/load_tests/load_test.py --scenario all
"""

import argparse
import time
import pandas as pd
import numpy as np
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple

from config.database import DatabaseConfig
from services.database.schema_service import SchemaService
from utils.health_check import check_database_health


class LoadTestResults:
    """Store and display load test results"""

    def __init__(self):
        self.results = []

    def add_result(self, scenario: str, rows: int, duration: float, success: bool, error: str = None):
        """Add a test result"""
        throughput = rows / duration if duration > 0 else 0
        self.results.append({
            'scenario': scenario,
            'rows': rows,
            'duration_seconds': round(duration, 2),
            'throughput_rows_per_sec': round(throughput, 2),
            'success': success,
            'error': error
        })

    def print_summary(self):
        """Print formatted test summary"""
        print("\n" + "="*80)
        print("LOAD TEST RESULTS SUMMARY")
        print("="*80)

        if not self.results:
            print("No results to display")
            return

        # Print detailed results
        print(f"\n{'Scenario':<25} {'Rows':>10} {'Duration':>12} {'Throughput':>15} {'Status':>10}")
        print("-"*80)

        for result in self.results:
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"{result['scenario']:<25} {result['rows']:>10,} "
                  f"{result['duration_seconds']:>10.2f}s "
                  f"{result['throughput_rows_per_sec']:>12,.0f} r/s "
                  f"{status:>10}")

            if result['error']:
                print(f"  Error: {result['error']}")

        # Calculate statistics
        successful_tests = [r for r in self.results if r['success']]

        if successful_tests:
            avg_throughput = sum(r['throughput_rows_per_sec'] for r in successful_tests) / len(successful_tests)
            max_throughput = max(r['throughput_rows_per_sec'] for r in successful_tests)
            min_throughput = min(r['throughput_rows_per_sec'] for r in successful_tests)

            print("\n" + "="*80)
            print("STATISTICS")
            print("="*80)
            print(f"Total Tests: {len(self.results)}")
            print(f"Successful: {len(successful_tests)}")
            print(f"Failed: {len(self.results) - len(successful_tests)}")
            print(f"\nAverage Throughput: {avg_throughput:,.0f} rows/second")
            print(f"Max Throughput: {max_throughput:,.0f} rows/second")
            print(f"Min Throughput: {min_throughput:,.0f} rows/second")


def generate_test_data(num_rows: int) -> pd.DataFrame:
    """Generate test dataset"""
    return pd.DataFrame({
        'id': range(1, num_rows + 1),
        'name': [f'User_{i}' for i in range(1, num_rows + 1)],
        'email': [f'user{i}@example.com' for i in range(1, num_rows + 1)],
        'value': np.random.randint(1, 1000, num_rows),
        'score': np.random.uniform(0, 100, num_rows),
        'created_at': [datetime.now() for _ in range(num_rows)],
        'status': np.random.choice(['active', 'inactive', 'pending'], num_rows),
        'category': np.random.choice(['A', 'B', 'C', 'D'], num_rows)
    })


def upload_test_data(engine, schema_name: str, table_name: str, df: pd.DataFrame) -> Tuple[bool, float, str]:
    """
    Upload test data and measure time

    Returns:
        Tuple[bool, float, str]: (success, duration, error_message)
    """
    try:
        start_time = time.time()

        df.to_sql(
            name=table_name,
            con=engine,
            schema=schema_name,
            if_exists='replace',
            index=False
        )

        duration = time.time() - start_time
        return True, duration, None

    except Exception as e:
        duration = time.time() - start_time
        return False, duration, str(e)


def test_small_file(engine, schema_name: str, results: LoadTestResults):
    """Test with small file (1K rows)"""
    print("\n📊 Testing small file (1,000 rows)...")
    df = generate_test_data(1000)
    success, duration, error = upload_test_data(engine, schema_name, 'load_test_small', df)
    results.add_result('Small File (1K rows)', len(df), duration, success, error)


def test_medium_file(engine, schema_name: str, results: LoadTestResults):
    """Test with medium file (10K rows)"""
    print("\n📊 Testing medium file (10,000 rows)...")
    df = generate_test_data(10000)
    success, duration, error = upload_test_data(engine, schema_name, 'load_test_medium', df)
    results.add_result('Medium File (10K rows)', len(df), duration, success, error)


def test_large_file(engine, schema_name: str, results: LoadTestResults):
    """Test with large file (100K rows)"""
    print("\n📊 Testing large file (100,000 rows)...")
    df = generate_test_data(100000)
    success, duration, error = upload_test_data(engine, schema_name, 'load_test_large', df)
    results.add_result('Large File (100K rows)', len(df), duration, success, error)


def test_concurrent_uploads(engine, schema_name: str, results: LoadTestResults, num_threads: int = 5):
    """Test concurrent uploads"""
    print(f"\n📊 Testing concurrent uploads ({num_threads} threads, 5K rows each)...")

    def upload_worker(thread_id):
        df = generate_test_data(5000)
        table_name = f'load_test_concurrent_{thread_id}'
        return upload_test_data(engine, schema_name, table_name, df)

    start_time = time.time()
    total_rows = 5000 * num_threads

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(upload_worker, i) for i in range(num_threads)]

        successes = 0
        for future in as_completed(futures):
            success, _, error = future.result()
            if success:
                successes += 1

    duration = time.time() - start_time
    success = (successes == num_threads)

    results.add_result(
        f'Concurrent Uploads ({num_threads} threads)',
        total_rows,
        duration,
        success,
        f"{successes}/{num_threads} succeeded" if not success else None
    )


def test_connection_pool_stress(engine, results: LoadTestResults):
    """Stress test connection pool"""
    print("\n📊 Testing connection pool under stress...")

    from sqlalchemy import text

    def query_worker(query_id):
        try:
            start = time.time()
            with engine.connect() as conn:
                conn.execute(text(f"SELECT {query_id} AS id, GETDATE() AS timestamp"))
            return True, time.time() - start
        except Exception as e:
            return False, str(e)

    num_queries = 50
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(query_worker, i) for i in range(num_queries)]

        successes = 0
        for future in as_completed(futures):
            success, _ = future.result()
            if success:
                successes += 1

    duration = time.time() - start_time
    success = (successes == num_queries)

    results.add_result(
        'Connection Pool Stress',
        num_queries,
        duration,
        success,
        f"{successes}/{num_queries} succeeded" if not success else None
    )


def test_health_under_load(engine, results: LoadTestResults):
    """Test health check during load"""
    print("\n📊 Testing health check responsiveness...")

    status, details = check_database_health(engine, timeout=10)

    success = status in ['healthy', 'degraded']
    results.add_result(
        'Health Check Under Load',
        1,
        details['response_time_ms'] / 1000,
        success,
        None if success else f"Status: {status}"
    )


def setup_test_environment(db_config: DatabaseConfig, schema_name: str):
    """Setup test environment"""
    print(f"\n🔧 Setting up test environment...")
    print(f"   Schema: {schema_name}")

    db_config.update_engine()
    engine = db_config.get_engine()

    if not engine:
        raise Exception("Failed to create database engine")

    # Create test schema
    schema_service = SchemaService(engine)
    success, message = schema_service.ensure_schemas_exist([schema_name])

    if not success:
        raise Exception(f"Failed to create test schema: {message}")

    print(f"   ✅ Test environment ready")

    return engine


def cleanup_test_environment(engine, schema_name: str):
    """Cleanup test environment"""
    print(f"\n🧹 Cleaning up test environment...")

    try:
        from sqlalchemy import text

        with engine.begin() as conn:
            # Drop all tables in test schema
            conn.execute(text(f"""
                DECLARE @sql NVARCHAR(MAX) = '';
                SELECT @sql += 'DROP TABLE [{schema_name}].[' + name + ']; '
                FROM sys.tables
                WHERE schema_id = SCHEMA_ID('{schema_name}');
                EXEC sp_executesql @sql;
            """))

        print(f"   ✅ Cleanup complete")

    except Exception as e:
        print(f"   ⚠️  Cleanup warning: {e}")


def main():
    parser = argparse.ArgumentParser(description='SQL Server Pipeline Load Testing')
    parser.add_argument(
        '--scenario',
        choices=['small', 'medium', 'large', 'concurrent', 'pool', 'health', 'all'],
        default='all',
        help='Test scenario to run'
    )
    parser.add_argument(
        '--schema',
        default='load_test',
        help='Test schema name (default: load_test)'
    )
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Cleanup test data after completion'
    )

    args = parser.parse_args()

    print("="*80)
    print("SQL SERVER PIPELINE - LOAD TESTING")
    print("="*80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Scenario: {args.scenario}")
    print(f"Test Schema: {args.schema}")

    # Initialize
    results = LoadTestResults()
    db_config = DatabaseConfig()

    try:
        engine = setup_test_environment(db_config, args.schema)

        # Run tests based on scenario
        if args.scenario in ['small', 'all']:
            test_small_file(engine, args.schema, results)

        if args.scenario in ['medium', 'all']:
            test_medium_file(engine, args.schema, results)

        if args.scenario in ['large', 'all']:
            test_large_file(engine, args.schema, results)

        if args.scenario in ['concurrent', 'all']:
            test_concurrent_uploads(engine, args.schema, results)

        if args.scenario in ['pool', 'all']:
            test_connection_pool_stress(engine, results)

        if args.scenario in ['health', 'all']:
            test_health_under_load(engine, results)

        # Print results
        results.print_summary()

        # Cleanup if requested
        if args.cleanup:
            cleanup_test_environment(engine, args.schema)

    except Exception as e:
        print(f"\n❌ Load test failed: {e}")
        return 1

    finally:
        if 'engine' in locals():
            engine.dispose()

    print(f"\nEnd Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    return 0


if __name__ == '__main__':
    exit(main())
