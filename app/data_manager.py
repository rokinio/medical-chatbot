"""
مدیریت داده‌ها، فایل‌ها و ایندکس‌گذاری
"""

import json
import os
import numpy as np
import faiss
import streamlit as st
from sentence_transformers import SentenceTransformer

from config import *

def check_and_create_files():
    """بررسی وجود فایل‌های ضروری و ایجاد آنها در صورت نیاز"""
    # ایجاد فایل بازخورد اگر وجود ندارد
    if not os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False)
        print(f"فایل بازخورد ایجاد شد: {FEEDBACK_FILE}")
    
    # ایجاد فایل سوالات پردازش شده اگر وجود ندارد
    if not os.path.exists(PROCESSED_QUESTIONS_PATH):
        sample_data = [
            {
                "question": "زگیل تناسلی درمان دارد؟",
                "conversation": [
                    {"sender": "user", "message": "زگیل تناسلی درمان دارد؟"}
                ],
                "source": "sample"  # افزودن فیلد source
            },
            {
                "question": "سنگ کلیه را چگونه درمان کنیم؟",
                "conversation": [
                    {"sender": "user", "message": "سنگ کلیه را چگونه درمان کنیم؟"}
                ],
                "source": "sample"
            },
            {
                "question": "علائم سکته قلبی چیست؟",
                "conversation": [
                    {"sender": "user", "message": "علائم سکته قلبی چیست؟"}
                ],
                "source": "sample"
            },
            {
                "question": "چگونه از ابتلا به آنفولانزا جلوگیری کنیم؟",
                "conversation": [
                    {"sender": "user", "message": "چگونه از ابتلا به آنفولانزا جلوگیری کنیم؟"}
                ],
                "source": "sample"
            },
            {
                "question": "راه‌های درمان سردرد میگرنی چیست؟",
                "conversation": [
                    {"sender": "user", "message": "راه‌های درمان سردرد میگرنی چیست؟"}
                ],
                "source": "sample"
            }
        ]
        with open(PROCESSED_QUESTIONS_PATH, "w", encoding="utf-8") as f:
            json.dump(sample_data, f, ensure_ascii=False, indent=4)
        print("فایل سوالات نمونه ایجاد شد")
    
    # ایجاد فایل‌های FAISS اگر وجود ندارند
    if not os.path.exists(FAISS_INDEX_PATH) or not os.path.exists(FAISS_METADATA_PATH):
        try:
            # سعی می‌کنیم با استفاده از سوالات موجود، فایل‌های FAISS را بسازیم
            with open(PROCESSED_QUESTIONS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            questions = [entry["question"] for entry in data]
            sources = [entry.get("source", "unknown") for entry in data]  # دریافت منبع هر سوال
            
            # استفاده از مدل کش شده برای ایجاد embeddings
            model = SentenceTransformer(MODEL_NAME, cache_folder=MODEL_PATH)
            
            # ایجاد embedding‌ها
            embeddings = model.encode(questions)
            
            # ایجاد FAISS index
            dimension = embeddings.shape[1]
            index = faiss.IndexFlatL2(dimension)
            index.add(np.array(embeddings, dtype=np.float32))
            
            # ذخیره FAISS index
            faiss.write_index(index, FAISS_INDEX_PATH)
            
            # ذخیره متادیتا
            with open(FAISS_METADATA_PATH, "w", encoding="utf-8") as f:
                json.dump({"questions": questions, "sources": sources}, f, ensure_ascii=False, indent=4)
                
            print("فایل‌های FAISS با موفقیت ایجاد شدند")
            
        except Exception as e:
            print(f"خطا در ایجاد فایل‌های FAISS: {e}")
            
            # ایجاد فایل‌های ساده در صورت خطا برای جلوگیری از خطای بعدی
            if not os.path.exists(FAISS_METADATA_PATH):
                with open(PROCESSED_QUESTIONS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                questions = [entry["question"] for entry in data]
                sources = [entry.get("source", "unknown") for entry in data]
                with open(FAISS_METADATA_PATH, "w", encoding="utf-8") as f:
                    json.dump({"questions": questions, "sources": sources}, f, ensure_ascii=False, indent=4)
                
            if not os.path.exists(FAISS_INDEX_PATH):
                # ایجاد یک فایل خالی برای جلوگیری از خطا
                with open(FAISS_INDEX_PATH, "wb") as f:
                    f.write(b"FAISS_INDEX_PLACEHOLDER")

# بارگذاری منابع داده
@st.cache_data
def load_data_sources():
    """بارگذاری و گروه‌بندی منابع داده از فایل متادیتا"""
    try:
        if os.path.exists(FAISS_METADATA_PATH):
            with open(FAISS_METADATA_PATH, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            
            # استخراج منابع منحصر به فرد
            if "sources" in metadata:
                return sorted(list(set(metadata["sources"])))
            else:
                return ["همه"]
        else:
            return ["همه"]
    except Exception as e:
        st.error(f"خطا در بارگذاری منابع داده: {e}")
        return ["همه"]

# بارگذاری دسته‌بندی‌ها
@st.cache_data
def load_categories():
    try:
        return MEDICAL_CATEGORIES
    except Exception as e:
        st.error(f"خطا در بارگذاری دسته‌بندی‌ها: {e}")
        return {}

# کش کردن مدل برای استفاده مجدد
@st.cache_resource(show_spinner="بارگذاری مدل زبانی...")
def load_model():
    """بارگذاری مدل زبانی و کش کردن آن"""
    try:
        # استفاده از کش محلی و تنظیم زمان انقضا بالا
        return SentenceTransformer(MODEL_NAME, cache_folder=MODEL_PATH)
    except Exception as e:
        st.error(f"خطا در بارگذاری مدل: {e}")
        return None

# بارگذاری FAISS index
@st.cache_resource
def load_faiss():
    """بارگذاری ایندکس FAISS و متادیتا"""
    try:
        if os.path.exists(FAISS_INDEX_PATH) and os.path.exists(FAISS_METADATA_PATH):
            index = faiss.read_index(FAISS_INDEX_PATH)
            with open(FAISS_METADATA_PATH, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            return index, metadata
        else:
            st.warning("فایل‌های FAISS یافت نشدند. از جستجوی متنی ساده استفاده می‌شود.")
            return None, None
    except Exception as e:
        st.error(f"خطا در بارگذاری FAISS: {e}")
        return None, None

def save_feedback(query, response, rating, comment=""):
    """ذخیره بازخورد کاربر"""
    feedback = {
        "query": query,
        "response": response,
        "rating": rating,
        "comment": comment,
        "timestamp": import_time().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    st.session_state.feedback_data.append(feedback)
    
    # ذخیره بازخورد با آدرس نسبی فایل
    try:
        with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
            json.dump(st.session_state.feedback_data, f, ensure_ascii=False, indent=4)
        st.success("بازخورد با موفقیت ذخیره شد!")
    except Exception as e:
        st.error(f"خطا در ذخیره بازخورد: {e}")

def import_time():
    """وارد کردن ماژول time (برای جلوگیری از مشکل وارد کردن در بالای فایل)"""
    import time
    return time