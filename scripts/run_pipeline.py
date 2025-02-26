#!/usr/bin/env python3
# scripts/run_pipeline.py
"""
اجرای کامل فرایند استخراج، پردازش و ایندکس‌سازی
- یک اسکریپت برای اجرای کامل فرایند
- پشتیبانی از چندین جدول به صورت خودکار
- امکان اجرای مرحله‌ای فرایند
- نمایش گزارش کامل از هر مرحله
"""

import argparse
import os
import subprocess
import sys
import json
from datetime import datetime

def run_command(command, description):
    """اجرای یک دستور در خط فرمان"""
    print(f"\n{'='*50}")
    print(f"🚀 {description}")
    print(f"{'='*50}")
    print(f"📋 اجرای دستور: {' '.join(command)}")
    print(f"{'-'*50}")
    
    # اجرای دستور
    result = subprocess.run(command)
    
    if result.returncode == 0:
        print(f"\n✅ {description} با موفقیت انجام شد.")
        return True
    else:
        print(f"\n❌ خطا در {description}.")
        return False

def list_tables(args):
    """نمایش لیست جداول مرتبط"""
    command = [
        sys.executable, 
        os.path.join(os.path.dirname(__file__), "export_data.py"),
        "--host", args.host,
        "--user", args.user,
        "--password", args.password,
        "--database", args.database,
        "--list-tables"
    ]
    
    run_command(command, "نمایش لیست جفت‌های جداول")
    return True

def export_data(args):
    """اجرای مرحله استخراج داده‌ها"""
    command = [
        sys.executable, 
        os.path.join(os.path.dirname(__file__), "export_data.py"),
        "--host", args.host,
        "--user", args.user,
        "--password", args.password,
        "--database", args.database,
        "--min-answers", str(args.min_answers),
        "--output-dir", args.output_dir
    ]
    
    # اگر پیشوند جدول مشخص شده باشد
    if args.prefix:
        command.extend([
            "--prefix", args.prefix,
            "--questions-table", f"{args.prefix}_faq",
            "--answers-table", f"{args.prefix}_faqr"
        ])
    
    return run_command(command, "استخراج داده‌ها از دیتابیس")

def process_data(args):
    """اجرای مرحله پردازش داده‌ها"""
    log_dir = os.path.join(args.output_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    command = [
        sys.executable, 
        os.path.join(os.path.dirname(__file__), "process_data.py"),
        "--input", os.path.join(args.output_dir, "all_questions.json"),
        "--output", os.path.join(args.output_dir, "processed_all_questions.json"),
        "--names-file", args.names_file,
        "--log-dir", log_dir
    ]
    
    return run_command(command, "پردازش و تمیزسازی داده‌ها")

def build_index(args):
    """اجرای مرحله ساخت ایندکس FAISS"""
    command = [
        sys.executable, 
        os.path.join(os.path.dirname(__file__), "build_index.py"),
        "--input", os.path.join(args.output_dir, "processed_all_questions.json"),
        "--output-dir", args.output_dir,
        "--model", args.model,
        "--batch-size", str(args.batch_size)
    ]
    
    if args.no_ivf:
        command.append("--no-ivf")
    
    return run_command(command, "ساخت ایندکس FAISS")

def save_pipeline_log(args, steps_result):
    """ذخیره گزارش اجرای پایپلاین"""
    log_file = os.path.join(args.output_dir, "pipeline_log.json")
    
    log_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "steps": steps_result,
        "arguments": vars(args)
    }
    
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=4)
    
    print(f"\n📝 گزارش اجرای پایپلاین در فایل {log_file} ذخیره شد.")

def main():
    parser = argparse.ArgumentParser(description="اجرای کامل فرایند استخراج، پردازش و ایندکس‌سازی")
    
    # پارامترهای عمومی
    parser.add_argument("--output-dir", type=str, default="../app/data", help="مسیر پوشه خروجی")
    parser.add_argument("--only", type=str, choices=["export", "process", "index", "list"], help="فقط اجرای یک مرحله خاص")
    
    # پارامترهای استخراج داده‌ها
    parser.add_argument("--host", type=str, default="localhost", help="آدرس سرور دیتابیس")
    parser.add_argument("--user", type=str, default="root", help="نام کاربری دیتابیس")
    parser.add_argument("--password", type=str, help="رمز عبور دیتابیس")
    parser.add_argument("--database", type=str, default="question_system", help="نام دیتابیس")
    parser.add_argument("--prefix", type=str, help="پیشوند جداول برای استخراج (اختیاری، برای استخراج از یک جفت جدول خاص)")
    parser.add_argument("--min-answers", type=int, default=1, help="حداقل تعداد پاسخ برای هر سوال")
    
    # پارامترهای پردازش داده‌ها
    parser.add_argument("--names-file", type=str, default="name.csv", help="مسیر فایل نام‌های فارسی")
    
    # پارامترهای ساخت ایندکس
    parser.add_argument("--model", type=str, default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", help="نام مدل Sentence Transformer")
    parser.add_argument("--batch-size", type=int, default=32, help="اندازه بچ برای ساخت embeddings")
    parser.add_argument("--no-ivf", action="store_true", help="عدم استفاده از IndexIVFFlat حتی برای تعداد زیاد سوال")
    
    args = parser.parse_args()
    
    # ایجاد پوشه خروجی
    os.makedirs(args.output_dir, exist_ok=True)
    
    # تنظیم مراحل اجرای پایپلاین
    steps_result = {}
    
    if args.only == "list":
        # فقط نمایش لیست جداول
        if not args.password:
            print("❌ لطفاً رمز عبور دیتابیس را با پارامتر --password مشخص کنید.")
            return
        
        steps_result["list"] = list_tables(args)
    
    elif args.only == "export":
        # فقط اجرای مرحله استخراج داده‌ها
        if not args.password:
            print("❌ لطفاً رمز عبور دیتابیس را با پارامتر --password مشخص کنید.")
            return
        
        steps_result["export"] = export_data(args)
    
    elif args.only == "process":
        # فقط اجرای مرحله پردازش داده‌ها
        steps_result["process"] = process_data(args)
    
    elif args.only == "index":
        # فقط اجرای مرحله ساخت ایندکس
        steps_result["index"] = build_index(args)
    
    else:
        # اجرای کامل پایپلاین
        if not args.password:
            print("❌ لطفاً رمز عبور دیتابیس را با پارامتر --password مشخص کنید.")
            return
        
        # استخراج داده‌ها
        steps_result["export"] = export_data(args)
        
        # اگر استخراج موفق بود، ادامه می‌دهیم
        if steps_result["export"]:
            # پردازش داده‌ها
            steps_result["process"] = process_data(args)
            
            # اگر پردازش موفق بود، ادامه می‌دهیم
            if steps_result["process"]:
                # ساخت ایندکس
                steps_result["index"] = build_index(args)
    
    # ذخیره گزارش اجرای پایپلاین
    save_pipeline_log(args, steps_result)
    
    # نمایش خلاصه نتیجه
    print("\n" + "="*50)
    print("📊 خلاصه اجرای پایپلاین:")
    print("-"*50)
    
    for step, result in steps_result.items():
        status = "✅ موفق" if result else "❌ ناموفق"
        print(f"{step.capitalize()}: {status}")
    
    print("="*50)

if __name__ == "__main__":
    main()