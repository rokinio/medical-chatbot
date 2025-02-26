#!/usr/bin/env python3
# scripts/process_data.py
"""
پردازش و تمیزسازی داده‌های سوال و جواب
- حذف اطلاعات شخصی (نام‌ها، شماره تلفن‌ها، ایمیل‌ها)
- حذف پیام‌های تکراری
- استانداردسازی داده‌ها
"""

import json
import re
import os
import argparse
import pandas as pd
from collections import Counter
from datetime import datetime
from tqdm import tqdm

def load_names(names_file):
    """بارگذاری لیست نام‌های فارسی از فایل CSV"""
    try:
        print(f"📚 بارگذاری نام‌های فارسی از {names_file}...")
        df = pd.read_csv(names_file)
        names = set(df.iloc[:, 0].dropna().str.strip())  # فرض بر این است که نام‌ها در ستون اول هستند
        print(f"✅ {len(names)} نام فارسی بارگذاری شد.")
        return names
    except Exception as e:
        print(f"❌ خطا در بارگذاری فایل نام‌ها: {e}")
        return set()

def get_excluded_names():
    """لیست نام‌هایی که باید نادیده گرفته شوند"""
    return {
        "مني", "دعا", "نور", "عوض", "صفر", "عزت", "ماه", "بگم", "سبا", "شكر", "كرم", 
        "آذر", "همت", "صفا", "شفق", "هوا", "عسل", "بهار", "محرم", "جمعه", "صورت", 
        "هلال", "دفتر", "حافظ", "روزي", "تراب", "اصلي", "فرصت", "محبت", "قسمت", 
        "ماهه", "لازم", "ترحم", "كشور", "بانو", "نظام", "بهمن", "جهان", "خانم", 
        "دانش", "پرتو", "يسري", "ملكي", "كامل", "مطلب", "دختر", "زمان", "راضي", 
        "بالا", "شاهد", "صاحب", "سالم", "گلاب", "شنبه", "كوچك", "بزرگ", "نبات", 
        "آزاد", "رمضان", "تماشا", "گيلان", "بهبود", "فرمان", "منتهي", "ارشاد", 
        "نوروز", "سعادت", "ايران", "معروف", "شرافت", "تابان", "سلامت", "البرز", 
        "حافظه", "منتظر", "احترام", "انتظار", "ماندگار"
    }

def clean_text(text, iranian_names, excluded_names, phone_counter, removed_names):
    """حذف اطلاعات حساس و نام‌ها از متن"""
    if not text or text.strip() == "":
        return ""

    original_text = text  # ذخیره متن اصلی برای بررسی لاگ

    # حذف شماره تلفن (فرمت 09xx xxx xxxx یا 09xx-xxx-xxxx)
    phone_matches = re.findall(r'09\d{2}[- ]?\d{3}[- ]?\d{4}', text)
    for phone in phone_matches:
        phone_counter[phone] += 1
    text = re.sub(r'09\d{2}[- ]?\d{3}[- ]?\d{4}', '[REDACTED]', text)

    # حذف آدرس ایمیل
    text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[REDACTED]', text)

    # حذف نام‌های ایرانی از متن مگر اینکه در لیست excluded_names باشند
    words = re.findall(r'\w+', original_text)
    for word in words:
        cleaned_word = word.lower().strip()
        if cleaned_word in iranian_names and cleaned_word not in excluded_names:
            removed_names.add(cleaned_word)
            text = re.sub(rf'\b{re.escape(cleaned_word)}\b', '[REDACTED]', text)
    
    return text

def process_data(input_file, output_file, names_file, log_dir=None):
    """پردازش فایل داده‌ها و تمیزسازی آن"""
    # تنظیم مسیر فایل‌های لاگ
    if not log_dir:
        log_dir = os.path.join(os.path.dirname(output_file), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # بارگذاری نام‌های فارسی
    iranian_names = load_names(names_file)
    excluded_names = get_excluded_names()
    
    # آماده‌سازی متغیرهای آمارگیری
    phone_counter = Counter()
    removed_names = set()
    removed_duplicates = 0
    
    try:
        # خواندن داده خام
        print(f"📂 خواندن فایل {input_file}...")
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        print(f"🔍 پردازش {len(data)} سوال و پاسخ...")
        
        unique_messages = set()  # ذخیره سوالات و پاسخ‌های تکراری
        
        # پردازش داده‌ها
        for entry in tqdm(data):
            new_conversation = []
            for message in entry["conversation"]:
                cleaned_content = clean_text(
                    message["message"], 
                    iranian_names, 
                    excluded_names, 
                    phone_counter, 
                    removed_names
                )
                
                if cleaned_content and cleaned_content not in unique_messages:
                    unique_messages.add(cleaned_content)
                    new_conversation.append({"sender": message["sender"], "message": cleaned_content})
                else:
                    removed_duplicates += 1
            
            entry["conversation"] = new_conversation
        
        # حذف سوالاتی که مکالمه خالی دارند
        original_count = len(data)
        data = [entry for entry in data if entry["conversation"]]
        empty_conversations = original_count - len(data)
        
        # ذخیره خروجی پردازش‌شده
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        
        # ذخیره لاگ نام‌های حذف‌شده
        names_log_file = os.path.join(log_dir, "removed_names.txt")
        with open(names_log_file, "w", encoding="utf-8") as f:
            f.write("نام‌های حذف شده (مرتب شده بر اساس طول):\n")
            sorted_removed_names = sorted(removed_names, key=len)
            for name in sorted_removed_names:
                f.write(f"{name} ({len(name)} کاراکتر)\n")
        
        # ذخیره لاگ شماره‌های تلفن حذف‌شده
        phone_log_file = os.path.join(log_dir, "phone_numbers.txt")
        with open(phone_log_file, "w", encoding="utf-8") as f:
            f.write("شماره‌های تلفن شناسایی شده:\n")
            for phone, count in phone_counter.most_common():
                f.write(f"{phone}: {count} مورد\n")
        
        # ذخیره لاگ آماری
        stats_file = os.path.join(log_dir, "processing_stats.json")
        stats = {
            "processing_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "original_records": original_count,
            "processed_records": len(data),
            "empty_conversations_removed": empty_conversations,
            "duplicate_messages_removed": removed_duplicates,
            "unique_names_removed": len(removed_names),
            "phone_numbers_found": len(phone_counter)
        }
        
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=4)
        
        print(f"✅ پردازش با موفقیت انجام شد.")
        print(f"✅ {len(data)} سوال و پاسخ در فایل {output_file} ذخیره شد.")
        print(f"✅ {removed_duplicates} پیام تکراری حذف شد.")
        print(f"✅ {len(removed_names)} نام فارسی شناسایی و حذف شد.")
        print(f"✅ {len(phone_counter)} شماره تلفن شناسایی و حذف شد.")
        print(f"✅ فایل‌های لاگ در پوشه {log_dir} ذخیره شدند.")
        
        return True
    
    except Exception as e:
        print(f"❌ خطا در پردازش فایل: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="پردازش و تمیزسازی داده‌های سوال و جواب")
    
    # پارامترهای ورودی و خروجی
    parser.add_argument("--input", type=str, default="../app/data/all_questions.json", help="مسیر فایل ورودی")
    parser.add_argument("--output", type=str, default="../app/data/processed_all_questions.json", help="مسیر فایل خروجی")
    parser.add_argument("--names-file", type=str, default="name.csv", help="مسیر فایل نام‌های فارسی")
    parser.add_argument("--log-dir", type=str, help="مسیر ذخیره فایل‌های لاگ")
    
    args = parser.parse_args()
    
    # اجرای پردازش داده‌ها
    success = process_data(args.input, args.output, args.names_file, args.log_dir)
    
    if success:
        print("✅ عملیات پردازش با موفقیت انجام شد.")
    else:
        print("❌ خطا در عملیات پردازش.")

if __name__ == "__main__":
    main()