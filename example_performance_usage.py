"""
ตัวอย่างการใช้งาน Performance Optimizer สำหรับ PIPELINE_SQLSERVER

ไฟล์นี้แสดงวิธีการใช้งาน Performance Optimizer เพื่อปรับปรุงการประมวลผลไฟล์ใหญ่
"""

import os
import threading
import time
from performance_optimizations import PerformanceOptimizer, LargeFileProcessor, estimate_processing_time, format_file_size

def example_basic_usage():
    """ตัวอย่างการใช้งานพื้นฐาน"""
    print("=== ตัวอย่างการใช้งานพื้นฐาน ===")
    
    # สร้าง Performance Optimizer
    def log_callback(message):
        print(f"[LOG] {message}")
    
    optimizer = PerformanceOptimizer(log_callback)
    
    # ตัวอย่างการอ่านไฟล์ใหญ่
    file_path = "example_large_file.xlsx"
    if os.path.exists(file_path):
        success, df = optimizer.read_large_file_chunked(file_path, 'excel')
        if success:
            print(f"✅ อ่านไฟล์สำเร็จ: {len(df):,} แถว")
            
            # ปรับปรุง memory usage
            df = optimizer.optimize_memory_usage(df)
            
            # ประมวลผลแบบ chunk
            chunks = optimizer.process_dataframe_in_chunks(df, chunk_size=5000)
            print(f"📊 แบ่งเป็น {len(chunks)} chunks")
        else:
            print("❌ ไม่สามารถอ่านไฟล์ได้")
    else:
        print(f"⚠️ ไม่พบไฟล์: {file_path}")

def example_cancellation():
    """ตัวอย่างการยกเลิกการทำงาน"""
    print("\n=== ตัวอย่างการยกเลิกการทำงาน ===")
    
    def log_callback(message):
        print(f"[LOG] {message}")
    
    optimizer = PerformanceOptimizer(log_callback)
    
    # สร้าง cancellation token
    cancellation_token = threading.Event()
    optimizer.set_cancellation_token(cancellation_token)
    
    # จำลองการทำงานที่ใช้เวลานาน
    def long_running_task():
        for i in range(10):
            if cancellation_token.is_set():
                print("❌ การทำงานถูกยกเลิก")
                return
            print(f"🔄 กำลังทำงาน... ขั้นตอน {i+1}/10")
            time.sleep(1)
        print("✅ การทำงานเสร็จสิ้น")
    
    # เริ่มการทำงานใน thread แยก
    import threading
    thread = threading.Thread(target=long_running_task)
    thread.start()
    
    # รอ 3 วินาทีแล้วยกเลิก
    time.sleep(3)
    print("🛑 ยกเลิกการทำงาน...")
    cancellation_token.set()
    
    thread.join()

def example_progress_tracking():
    """ตัวอย่างการติดตามความคืบหน้า"""
    print("\n=== ตัวอย่างการติดตามความคืบหน้า ===")
    
    def log_callback(message):
        print(f"[LOG] {message}")
    
    optimizer = PerformanceOptimizer(log_callback)
    
    # สร้าง progress tracker
    total_items = 100
    progress_tracker = optimizer.create_progress_tracker(total_items, "ประมวลผลข้อมูล")
    
    # จำลองการประมวลผล
    for i in range(total_items):
        time.sleep(0.1)  # จำลองการทำงาน
        progress, message = progress_tracker()
        print(f"📊 {message}")

def example_large_file_processor():
    """ตัวอย่างการใช้ LargeFileProcessor"""
    print("\n=== ตัวอย่างการใช้ LargeFileProcessor ===")
    
    def log_callback(message):
        print(f"[LOG] {message}")
    
    processor = LargeFileProcessor(log_callback)
    
    # กำหนดขั้นตอนการประมวลผล
    def step1_clean_data(df):
        print("🧹 ขั้นตอนที่ 1: ทำความสะอาดข้อมูล")
        return df.dropna()
    
    def step2_transform_data(df):
        print("🔄 ขั้นตอนที่ 2: แปลงข้อมูล")
        return df.fillna(0)
    
    def step3_validate_data(df):
        print("✅ ขั้นตอนที่ 3: ตรวจสอบข้อมูล")
        return df
    
    processing_steps = [step1_clean_data, step2_transform_data, step3_validate_data]
    
    # ประมวลผลไฟล์
    file_path = "example_large_file.xlsx"
    if os.path.exists(file_path):
        success, df = processor.process_large_file(file_path, 'excel', processing_steps)
        if success:
            print(f"✅ ประมวลผลสำเร็จ: {len(df):,} แถว")
        else:
            print("❌ ประมวลผลไม่สำเร็จ")
    else:
        print(f"⚠️ ไม่พบไฟล์: {file_path}")

def example_parallel_processing():
    """ตัวอย่างการประมวลผลแบบ parallel"""
    print("\n=== ตัวอย่างการประมวลผลแบบ parallel ===")
    
    def log_callback(message):
        print(f"[LOG] {message}")
    
    optimizer = PerformanceOptimizer(log_callback)
    
    # จำลองไฟล์หลายไฟล์
    file_paths = [
        "file1.xlsx",
        "file2.xlsx", 
        "file3.xlsx",
        "file4.xlsx"
    ]
    
    def process_file(file_path):
        """ฟังก์ชันสำหรับประมวลผลไฟล์"""
        print(f"📁 กำลังประมวลผล: {file_path}")
        time.sleep(2)  # จำลองการประมวลผล
        return f"เสร็จสิ้น: {file_path}"
    
    # ประมวลผลแบบ parallel
    results = optimizer.parallel_process_files(
        file_paths, 
        process_file,
        progress_callback=lambda p, msg: print(f"📊 {msg}: {p*100:.1f}%")
    )
    
    print("📋 ผลลัพธ์:")
    for success, result in results:
        status = "✅" if success else "❌"
        print(f"{status} {result}")

def example_memory_optimization():
    """ตัวอย่างการปรับปรุง memory"""
    print("\n=== ตัวอย่างการปรับปรุง memory ===")
    
    import pandas as pd
    import numpy as np
    
    def log_callback(message):
        print(f"[LOG] {message}")
    
    optimizer = PerformanceOptimizer(log_callback)
    
    # สร้าง DataFrame ตัวอย่าง
    data = {
        'id': range(100000),
        'name': [f'Name_{i}' for i in range(100000)],
        'value': np.random.randn(100000),
        'category': np.random.choice(['A', 'B', 'C'], 100000)
    }
    
    df = pd.DataFrame(data)
    print(f"📊 DataFrame เริ่มต้น: {len(df):,} แถว")
    print(f"💾 Memory เริ่มต้น: {df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")
    
    # ปรับปรุง memory
    df_optimized = optimizer.optimize_memory_usage(df)
    
    print(f"💾 Memory หลังปรับปรุง: {df_optimized.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")

def example_time_estimation():
    """ตัวอย่างการประมาณเวลา"""
    print("\n=== ตัวอย่างการประมาณเวลา ===")
    
    # ตัวอย่างไฟล์ขนาดต่างๆ
    file_sizes = [10, 50, 100, 500, 1000]  # MB
    
    for size in file_sizes:
        estimated_time = estimate_processing_time(size, 'standard')
        print(f"📁 ไฟล์ {size} MB: ประมาณ {estimated_time:.1f} วินาที ({estimated_time/60:.1f} นาที)")

def example_file_size_formatting():
    """ตัวอย่างการจัดรูปแบบขนาดไฟล์"""
    print("\n=== ตัวอย่างการจัดรูปแบบขนาดไฟล์ ===")
    
    sizes = [1024, 1024*1024, 1024*1024*1024, 1024*1024*1024*1024]
    
    for size in sizes:
        formatted = format_file_size(size)
        print(f"📏 {size} bytes = {formatted}")

def main():
    """ฟังก์ชันหลักสำหรับรันตัวอย่างทั้งหมด"""
    print("🚀 เริ่มต้นตัวอย่างการใช้งาน Performance Optimizer")
    print("=" * 60)
    
    try:
        example_basic_usage()
        example_cancellation()
        example_progress_tracking()
        example_large_file_processor()
        example_parallel_processing()
        example_memory_optimization()
        example_time_estimation()
        example_file_size_formatting()
        
        print("\n" + "=" * 60)
        print("✅ ตัวอย่างการใช้งานเสร็จสิ้น")
        
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")

if __name__ == "__main__":
    main() 