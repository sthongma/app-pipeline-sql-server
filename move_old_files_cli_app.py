# move_old_files_cli.py
# Script to move old files from Uploaded_Files to Archived_Files

import os
import argparse
from datetime import datetime, timedelta
from shutil import move, rmtree
import json
try:
    from send2trash import send2trash
except ImportError:
    send2trash = None

# อ่าน last_path จาก config/last_path.json
def get_last_path():
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'last_path.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('last_path', os.path.join(os.path.dirname(__file__), 'Uploaded_Files'))
    except Exception:
        return os.path.join(os.path.dirname(__file__), 'Uploaded_Files')

DEFAULT_SOURCE = os.path.join(get_last_path(), 'Uploaded_Files')
DEFAULT_DEST = os.path.join('D:\\', 'Archived_Files')

def find_files_older_than(root, days):
    """ค้นหาไฟล์ใน root ที่มีอายุมากกว่า days วัน (recursively)"""
    cutoff = datetime.now() - timedelta(days=days)
    old_files = []
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                if mtime < cutoff:
                    old_files.append(fpath)
            except Exception:
                continue
    return old_files

def find_empty_directories(root):
    """ค้นหาโฟลเดอร์ที่ว่างเปล่าใน root (recursively)"""
    empty_dirs = []
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        # ตรวจสอบว่าโฟลเดอร์นี้ว่างเปล่าหรือไม่
        if not dirnames and not filenames:
            empty_dirs.append(dirpath)
    return empty_dirs

def move_files(files, src_root, dest_root):
    """ย้ายไฟล์ไปยังปลายทางที่โครงสร้างโฟลเดอร์เหมือนเดิม"""
    moved = []
    for f in files:
        rel = os.path.relpath(f, src_root)
        dest_dir = os.path.join(dest_root, os.path.dirname(rel))
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, os.path.basename(f))
        try:
            move(f, dest_path)
            moved.append((f, dest_path))
        except Exception as e:
            print(f"❌ ย้าย {f} ไม่สำเร็จ: {e}")
    return moved

def move_empty_directories(empty_dirs, src_root, dest_root):
    """ย้ายโฟลเดอร์ที่ว่างเปล่าไปยังปลายทาง"""
    moved_dirs = []
    for dir_path in empty_dirs:
        try:
            rel = os.path.relpath(dir_path, src_root)
            dest_dir = os.path.join(dest_root, rel)
            os.makedirs(os.path.dirname(dest_dir), exist_ok=True)
            move(dir_path, dest_dir)
            moved_dirs.append((dir_path, dest_dir))
        except Exception as e:
            print(f"❌ ย้ายโฟลเดอร์ {dir_path} ไม่สำเร็จ: {e}")
    return moved_dirs

def delete_files_older_than(root, days):
    """ย้ายไฟล์ใน root ที่มีอายุมากกว่า days วันไปถังขยะ (recursively)"""
    if send2trash is None:
        print("[!] ไม่พบไลบรารี send2trash กรุณาติดตั้งด้วย pip install send2trash")
        return []
    cutoff = datetime.now() - timedelta(days=days)
    deleted = []
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                if mtime < cutoff:
                    send2trash(fpath)
                    deleted.append(fpath)
            except Exception:
                continue
    return deleted

def main():
    parser = argparse.ArgumentParser(description='Move old files from Uploaded_Files to Archived_Files.')
    parser.add_argument('--days', type=int, default=30, help='จำนวนวัน (default: 30)')
    parser.add_argument('--src', type=str, default=DEFAULT_SOURCE, help='โฟลเดอร์ต้นทาง (default: Uploaded_Files)')
    parser.add_argument('--dest', type=str, default=DEFAULT_DEST, help='โฟลเดอร์ปลายทาง (default: Archived_Files)')
    args = parser.parse_args()

    print(f"ค้นหาไฟล์ที่เก่ากว่า {args.days} วัน ใน {args.src}")
    old_files = find_files_older_than(args.src, args.days)
    print(f"พบ {len(old_files)} ไฟล์")
    
    if old_files:
        print(f"กำลังย้ายไฟล์ไป {args.dest} ...")
        moved = move_files(old_files, args.src, args.dest)
        print(f"ย้ายสำเร็จ {len(moved)} ไฟล์")
        for src, dst in moved:
            print(f"{src} -> {dst}")
    
    # ค้นหาและย้ายโฟลเดอร์ที่ว่างเปล่า
    print("ค้นหาโฟลเดอร์ที่ว่างเปล่า...")
    empty_dirs = find_empty_directories(args.src)
    if empty_dirs:
        print(f"พบ {len(empty_dirs)} โฟลเดอร์ที่ว่างเปล่า")
        print(f"กำลังย้ายโฟลเดอร์ไป {args.dest} ...")
        moved_dirs = move_empty_directories(empty_dirs, args.src, args.dest)
        print(f"ย้ายโฟลเดอร์สำเร็จ {len(moved_dirs)} โฟลเดอร์")
        for src, dst in moved_dirs:
            print(f"{src} -> {dst}")
    else:
        print("ไม่พบโฟลเดอร์ที่ว่างเปล่า")

    # ลบไฟล์ในโฟลเดอร์ปลายทางที่เกิน 90 วัน
    deleted = delete_files_older_than(args.dest, 90)
    print(f"ลบไฟล์ใน {args.dest} ที่เก่ากว่า 90 วันแล้ว {len(deleted)} ไฟล์")
    for f in deleted:
        print(f"ลบ {f}")

if __name__ == '__main__':
    main()
