#!/usr/bin/env python3
# scripts/export_data.py
"""
استخراج داده‌های سوال و جواب از دیتابیس
- پشتیبانی از چندین جدول به صورت خودکار
- شناسایی جفت‌های جداول مرتبط
"""

import mysql.connector
import json
import os
import argparse
from datetime import datetime
import re

def connect_to_database(host, user, password, database):
    """اتصال به دیتابیس"""
    try:
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        return conn
    except mysql.connector.Error as e:
        print(f"❌ خطا در اتصال به دیتابیس: {e}")
        return None

def get_table_pairs(connection):
    """یافتن جفت‌های جداول مرتبط با الگوی _faq و _faqr"""
    if not connection:
        return []
    
    try:
        cursor = connection.cursor()
        
        # استخراج همه جداول دیتابیس
        cursor.execute("SHOW TABLES")
        all_tables = [table[0] for table in cursor.fetchall()]
        
        # یافتن جداول با پسوند _faq
        faq_tables = [table for table in all_tables if table.endswith('_faq')]
        
        # بررسی وجود جدول متناظر با پسوند _faqr
        table_pairs = []
        for faq_table in faq_tables:
            faqr_table = faq_table + 'r'  # افزودن حرف r به انتهای نام جدول
            if faqr_table in all_tables:
                prefix = faq_table[:-4]  # حذف _faq از انتهای نام
                table_pairs.append((prefix, faq_table, faqr_table))
        
        return table_pairs
    
    except Exception as e:
        print(f"❌ خطا در استخراج لیست جداول: {e}")
        return []

def export_data_from_table_pair(connection, output_dir, prefix, questions_table, answers_table, min_answers=1):
    """استخراج سوالات و پاسخ‌ها از یک جفت جدول"""
    if not connection:
        return False
    
    output_file = os.path.join(output_dir, f"{prefix}_questions.json")
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # استخراج سوالات
        print(f"📊 استخراج سوالات از جدول {questions_table}...")
        cursor.execute(f"SELECT id, name, subject, message FROM {questions_table}")
        questions = cursor.fetchall()
        print(f"✅ {len(questions)} سوال استخراج شد.")
        
        # استخراج پاسخ‌ها
        print(f"📊 استخراج پاسخ‌ها از جدول {answers_table}...")
        cursor.execute(f"SELECT tid, message, uid FROM {answers_table}")
        answers = cursor.fetchall()
        print(f"✅ {len(answers)} پاسخ استخراج شد.")
        
        # سازماندهی پاسخ‌ها بر اساس ID سوال
        answers_dict = {}
        for ans in answers:
            tid = ans['tid']
            sender = "user" if ans['uid'] == -1 else "doctor"
            if tid not in answers_dict:
                answers_dict[tid] = []
            answers_dict[tid].append({"sender": sender, "message": ans['message']})
        
        # تبدیل داده‌ها به فرمت JSON
        faq_data = []
        skipped_count = 0
        
        for q in questions:
            # بررسی تعداد پاسخ‌های سوال
            if q['id'] not in answers_dict or len(answers_dict[q['id']]) < min_answers:
                skipped_count += 1
                continue
                
            conversation = [{"sender": "user", "message": q['message']}]
            conversation.extend(answers_dict[q['id']])
            
            faq_data.append({
                "question": q['subject'],
                "conversation": conversation,
                "source": prefix  # افزودن منبع برای بازیابی بهتر
            })
        
        # ذخیره سوالات در فایل JSON
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(faq_data, f, ensure_ascii=False, indent=4)
        
        print(f"🔍 {skipped_count} سوال به دلیل نداشتن حداقل {min_answers} پاسخ، حذف شد.")
        print(f"✅ {len(faq_data)} سوال و پاسخ با موفقیت استخراج و در فایل {output_file} ذخیره شد.")
        
        # ذخیره اطلاعات آماری
        stats = {
            "export_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": prefix,
            "questions_table": questions_table,
            "answers_table": answers_table,
            "total_questions": len(questions),
            "total_answers": len(answers),
            "exported_items": len(faq_data),
            "skipped_items": skipped_count
        }
        
        stats_file = f"{os.path.splitext(output_file)[0]}_stats.json"
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=4)
        
        return True
    
    except Exception as e:
        print(f"❌ خطا در استخراج داده‌ها از جداول {questions_table} و {answers_table}: {e}")
        return False

def merge_all_data(output_dir):
    """ترکیب داده‌های استخراج شده از همه جداول"""
    try:
        all_questions = []
        stats_summary = {}
        
        # یافتن همه فایل‌های JSON با الگوی *_questions.json
        question_files = [f for f in os.listdir(output_dir) if f.endswith('_questions.json') and not f.startswith('all_')]
        
        if not question_files:
            print("❌ هیچ فایل داده‌ای برای ترکیب یافت نشد.")
            return False
        
        # ترکیب همه فایل‌ها
        for file in question_files:
            file_path = os.path.join(output_dir, file)
            prefix = re.sub(r'_questions\.json$', '', file)
            
            # خواندن فایل داده
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_questions.extend(data)
            
            # خواندن فایل آمار
            stats_file = os.path.join(output_dir, f"{prefix}_questions_stats.json")
            if os.path.exists(stats_file):
                with open(stats_file, "r", encoding="utf-8") as f:
                    stats = json.load(f)
                    stats_summary[prefix] = stats
        
        # ذخیره فایل ترکیبی
        all_questions_file = os.path.join(output_dir, "all_questions.json")
        with open(all_questions_file, "w", encoding="utf-8") as f:
            json.dump(all_questions, f, ensure_ascii=False, indent=4)
        
        # ذخیره آمار کلی
        summary_stats = {
            "merge_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_sources": len(question_files),
            "total_questions": len(all_questions),
            "sources": list(stats_summary.keys()),
            "detailed_stats": stats_summary
        }
        
        summary_stats_file = os.path.join(output_dir, "all_questions_stats.json")
        with open(summary_stats_file, "w", encoding="utf-8") as f:
            json.dump(summary_stats, f, ensure_ascii=False, indent=4)
        
        print(f"✅ {len(all_questions)} سوال و پاسخ از {len(question_files)} منبع با موفقیت ترکیب و در فایل {all_questions_file} ذخیره شد.")
        return True
    
    except Exception as e:
        print(f"❌ خطا در ترکیب داده‌ها: {e}")
        return False

def export_data_all_tables(connection, output_dir, min_answers=1, single_table_pair=None):
    """استخراج داده‌ها از تمامی جداول مرتبط یا یک جفت خاص"""
    if not connection:
        return False
    
    try:
        # ساخت پوشه خروجی
        os.makedirs(output_dir, exist_ok=True)
        
        if single_table_pair:
            # استخراج داده‌ها از یک جفت جدول خاص
            prefix, questions_table, answers_table = single_table_pair
            success = export_data_from_table_pair(
                connection, output_dir, prefix, questions_table, answers_table, min_answers
            )
            return success
        else:
            # استخراج داده‌ها از همه جداول مرتبط
            table_pairs = get_table_pairs(connection)
            
            if not table_pairs:
                print("❌ هیچ جفت جدول مرتبطی یافت نشد.")
                return False
            
            results = []
            for prefix, questions_table, answers_table in table_pairs:
                print(f"\n{'='*50}")
                print(f"🚀 استخراج داده‌ها از {prefix} ({questions_table} و {answers_table})")
                print(f"{'='*50}")
                
                success = export_data_from_table_pair(
                    connection, output_dir, prefix, questions_table, answers_table, min_answers
                )
                results.append((prefix, success))
            
            # نمایش خلاصه نتیجه
            print("\n" + "="*50)
            print("📊 خلاصه استخراج داده‌ها:")
            print("-"*50)
            
            for prefix, success in results:
                status = "✅ موفق" if success else "❌ ناموفق"
                print(f"{prefix}: {status}")
            
            print("="*50)
            
            # ترکیب همه داده‌ها
            if any(success for _, success in results):
                merge_all_data(output_dir)
            
            return True
    
    except Exception as e:
        print(f"❌ خطا در استخراج داده‌ها: {e}")
        return False
    finally:
        if connection:
            connection.close()

def main():
    parser = argparse.ArgumentParser(description="استخراج سوالات و پاسخ‌ها از دیتابیس")
    
    # پارامترهای اتصال به دیتابیس
    parser.add_argument("--host", type=str, default="localhost", help="آدرس سرور دیتابیس")
    parser.add_argument("--user", type=str, default="root", help="نام کاربری دیتابیس")
    parser.add_argument("--password", type=str, required=True, help="رمز عبور دیتابیس")
    parser.add_argument("--database", type=str, default="question_system", help="نام دیتابیس")
    
    # پارامترهای استخراج داده‌ها
    parser.add_argument("--prefix", type=str, help="پیشوند جداول برای استخراج (اختیاری، برای استخراج از یک جفت جدول خاص)")
    parser.add_argument("--questions-table", type=str, help="نام جدول سوالات (برای استفاده با --prefix)")
    parser.add_argument("--answers-table", type=str, help="نام جدول پاسخ‌ها (برای استفاده با --prefix)")
    parser.add_argument("--min-answers", type=int, default=1, help="حداقل تعداد پاسخ برای هر سوال")
    
    # پارامترهای خروجی
    parser.add_argument("--output-dir", type=str, default="../app/data", help="مسیر پوشه خروجی")
    
    # پارامتر لیست جداول
    parser.add_argument("--list-tables", action="store_true", help="فقط نمایش لیست جفت‌های جداول و خروج")
    
    args = parser.parse_args()
    
    # اتصال به دیتابیس
    connection = connect_to_database(args.host, args.user, args.password, args.database)
    
    if not connection:
        print("❌ به دلیل خطا در اتصال به دیتابیس، عملیات متوقف شد.")
        return
    
    # نمایش لیست جداول
    if args.list_tables:
        table_pairs = get_table_pairs(connection)
        print("\n📋 لیست جفت‌های جداول یافت شده:")
        print("-"*50)
        
        if not table_pairs:
            print("❌ هیچ جفت جدول مرتبطی یافت نشد.")
        else:
            for i, (prefix, questions_table, answers_table) in enumerate(table_pairs, 1):
                print(f"{i}. پیشوند: {prefix}")
                print(f"   جدول سوالات: {questions_table}")
                print(f"   جدول پاسخ‌ها: {answers_table}")
                print()
        
        connection.close()
        return
    
    # استخراج داده‌ها
    if args.prefix and args.questions_table and args.answers_table:
        # استخراج از یک جفت جدول خاص
        single_table_pair = (args.prefix, args.questions_table, args.answers_table)
        success = export_data_all_tables(
            connection, 
            args.output_dir, 
            args.min_answers,
            single_table_pair
        )
    else:
        # استخراج از همه جداول
        success = export_data_all_tables(
            connection, 
            args.output_dir, 
            args.min_answers
        )
    
    if success:
        print("✅ عملیات استخراج با موفقیت انجام شد.")
    else:
        print("❌ خطا در عملیات استخراج.")

if __name__ == "__main__":
    main()