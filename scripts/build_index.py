#!/usr/bin/env python3
# scripts/build_index.py
"""
ساخت ایندکس FAISS برای جستجوی سریع متن
- پشتیبانی از حجم بالای داده (تا 50,000+ سوال)
- بهینه‌سازی با استفاده از بچ‌ها برای کاهش مصرف حافظه
- استفاده از IndexIVFFlat برای کارایی بهتر با تعداد زیاد سوال
"""

import json
import os
import argparse
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from datetime import datetime
from tqdm import tqdm

def load_questions(input_file):
    """بارگذاری سوالات از فایل JSON"""
    try:
        print(f"📚 بارگذاری سوالات از {input_file}...")
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        questions = [entry["question"] for entry in data]
        print(f"✅ {len(questions)} سوال بارگذاری شد.")
        return questions
    except Exception as e:
        print(f"❌ خطا در بارگذاری فایل سوالات: {e}")
        return []

def build_index(questions, model_name, output_dir, batch_size=32, use_ivf=True):
    """ساخت ایندکس FAISS برای سوالات"""
    if not questions:
        print("❌ هیچ سوالی برای ایندکس‌سازی یافت نشد.")
        return False
    
    try:
        # تنظیم مسیر خروجی
        os.makedirs(output_dir, exist_ok=True)
        index_path = os.path.join(output_dir, "faq_index.faiss")
        metadata_path = os.path.join(output_dir, "faq_metadata.json")
        
        # تنظیم مسیر کش مدل
        model_cache_dir = os.path.join(os.path.dirname(output_dir), "models")
        os.makedirs(model_cache_dir, exist_ok=True)
        
        # بارگذاری مدل
        print(f"📚 بارگذاری مدل {model_name}...")
        model = SentenceTransformer(model_name, cache_folder=model_cache_dir)
        
        # ایجاد embeddings به صورت بچ برای کاهش مصرف حافظه
        print(f"🔄 ساخت embeddings با اندازه بچ {batch_size}...")
        embeddings = []
        
        for i in tqdm(range(0, len(questions), batch_size)):
            batch = questions[i:i+batch_size]
            batch_embeddings = model.encode(batch)
            embeddings.append(batch_embeddings)
        
        # ترکیب همه embeddings
        all_embeddings = np.vstack(embeddings)
        dimension = all_embeddings.shape[1]
        print(f"✅ embeddings با ابعاد {all_embeddings.shape} ساخته شد.")
        
        # ساخت ایندکس مناسب بر اساس تعداد سوالات
        if use_ivf and len(questions) > 1000:
            # محاسبه تعداد کلاسترها
            nlist = min(int(len(questions) / 39), 1024)  # حداکثر 1024 کلاستر
            nlist = max(nlist, 4)  # حداقل 4 کلاستر
            
            print(f"🔄 ساخت ایندکس IndexIVFFlat با {nlist} کلاستر...")
            quantizer = faiss.IndexFlatL2(dimension)
            index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
            
            # آموزش ایندکس قبل از اضافه کردن داده‌ها
            if not index.is_trained:
                index.train(all_embeddings)
            
            # تنظیم پارامتر nprobe برای جستجوی بهتر
            nprobe = min(nlist // 4, 16)  # حداکثر 16
            nprobe = max(nprobe, 1)  # حداقل 1
            index.nprobe = nprobe
            
            print(f"✅ ایندکس با nprobe={nprobe} تنظیم شد.")
        else:
            print(f"🔄 ساخت ایندکس IndexFlatL2...")
            index = faiss.IndexFlatL2(dimension)
        
        # اضافه کردن داده‌ها به ایندکس
        index.add(all_embeddings)
        print(f"✅ {len(questions)} سوال به ایندکس اضافه شد.")
        
        # ذخیره ایندکس
        print(f"💾 ذخیره ایندکس در {index_path}...")
        faiss.write_index(index, index_path)
        
        # ذخیره متادیتا
        print(f"💾 ذخیره متادیتا در {metadata_path}...")
        metadata = {
            "questions": questions,
            "model_name": model_name,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "dimension": dimension,
            "count": len(questions)
        }
        
        if use_ivf and len(questions) > 1000:
            metadata["index_type"] = "IndexIVFFlat"
            metadata["nlist"] = nlist
            metadata["nprobe"] = index.nprobe
        else:
            metadata["index_type"] = "IndexFlatL2"
        
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=4)
        
        print("✅ ساخت ایندکس با موفقیت انجام شد.")
        return True
    
    except Exception as e:
        print(f"❌ خطا در ساخت ایندکس: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="ساخت ایندکس FAISS برای جستجوی سریع متن")
    
    # پارامترهای ورودی و خروجی
    parser.add_argument("--input", type=str, default="../app/data/processed_all_questions.json", help="مسیر فایل سوالات پردازش شده")
    parser.add_argument("--output-dir", type=str, default="../app/data", help="مسیر پوشه خروجی")
    
    # پارامترهای مدل
    parser.add_argument("--model", type=str, default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", help="نام مدل Sentence Transformer")
    parser.add_argument("--batch-size", type=int, default=32, help="اندازه بچ برای ساخت embeddings")
    
    # پارامترهای ایندکس
    parser.add_argument("--no-ivf", action="store_true", help="عدم استفاده از IndexIVFFlat حتی برای تعداد زیاد سوال")
    
    args = parser.parse_args()
    
    # بارگذاری سوالات
    questions = load_questions(args.input)
    
    # ساخت ایندکس
    if questions:
        use_ivf = not args.no_ivf
        success = build_index(questions, args.model, args.output_dir, args.batch_size, use_ivf)
        
        if success:
            print("✅ عملیات ساخت ایندکس با موفقیت انجام شد.")
        else:
            print("❌ خطا در عملیات ساخت ایندکس.")
    else:
        print("❌ به دلیل عدم وجود سوال، عملیات متوقف شد.")

if __name__ == "__main__":
    main()