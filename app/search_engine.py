"""
موتور جستجو برای یافتن سوالات مشابه
"""

import streamlit as st
import numpy as np
import json
import os

from config import *
from data_manager import load_model, load_faiss

def search_with_faiss_cached(query, top_k=5, selected_source=None):
    """جستجو با استفاده از FAISS با قابلیت کش"""
    # ایجاد کلید کش
    cache_key = f"{query}_{top_k}_{selected_source}"
    
    # بررسی وجود نتیجه در کش
    if 'search_cache' not in st.session_state:
        st.session_state.search_cache = {}
        
    if cache_key in st.session_state.search_cache:
        st.write("💡 نتیجه از کش بازیابی شد!")
        return st.session_state.search_cache[cache_key]
    
    try:
        # بارگذاری مدل و ایندکس
        model = load_model()
        index, metadata = load_faiss()
        
        if model is None or index is None or metadata is None:
            return search_text(query, top_k, selected_source)
        
        # تبدیل سؤال به embedding
        query_embedding = model.encode([query])
        
        # جستجو در FAISS
        distances, indices = index.search(np.array(query_embedding, dtype=np.float32), top_k * 3)  # جستجوی بیشتر برای فیلتر کردن
        
        # استخراج سؤالات مشابه
        results = []
        sources = metadata.get("sources", ["unknown"] * len(metadata["questions"]))
        
        for i, idx in enumerate(indices[0]):
            if idx < len(metadata["questions"]):
                question = metadata["questions"][idx]
                source = sources[idx] if idx < len(sources) else "unknown"
                
                # فیلتر کردن بر اساس منبع اگر مقدار انتخاب شده باشد
                if selected_source == "همه" or selected_source is None or source == selected_source:
                    results.append({"question": question, "source": source})
                
                # جمع آوری به اندازه کافی
                if len(results) >= top_k:
                    break
        
        # اگر به اندازه کافی نتیجه پیدا نشد، از جستجوی متنی استفاده می‌کنیم
        if not results:
            results = search_text(query, top_k, selected_source)
        
        # ذخیره در کش
        st.session_state.search_cache[cache_key] = results
        return results
    
    except Exception as e:
        st.error(f"خطا در جستجوی FAISS: {e}")
        # برگشت به جستجوی متنی ساده در صورت خطا
        return search_text(query, top_k, selected_source)

def search_text(query, top_k=5, selected_source=None):
    """جستجوی ساده متنی (به عنوان پشتیبان)"""
    try:
        if not os.path.exists(PROCESSED_QUESTIONS_PATH):
            st.error(f"فایل سوالات ({PROCESSED_QUESTIONS_PATH}) یافت نشد!")
            return []
            
        with open(PROCESSED_QUESTIONS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # جستجوی ساده متنی
        matching_questions = []
        
        if isinstance(data, list):
            for entry in data:
                if "question" in entry:
                    question = entry["question"].lower()
                    source = entry.get("source", "unknown")
                    
                    # فیلتر کردن بر اساس منبع اگر مقدار انتخاب شده باشد
                    if selected_source == "همه" or selected_source is None or source == selected_source:
                        if any(word.lower() in question for word in query.lower().split()):
                            matching_questions.append({"question": entry["question"], "source": source})
                            if len(matching_questions) >= top_k:
                                break
        
        return matching_questions
    
    except Exception as e:
        st.error(f"خطا در جستجوی متنی: {e}")
        return []

def get_question_category(question):
    """تشخیص دسته‌بندی یک سوال"""
    question_lower = question.lower()
    categories = MEDICAL_CATEGORIES
    matching_categories = []
    
    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword in question_lower:
                matching_categories.append(category)
                break
    
    return matching_categories if matching_categories else ["متفرقه"]

def filter_by_category(results, category):
    """فیلتر کردن نتایج بر اساس دسته‌بندی"""
    if category == "همه":
        return results
        
    filtered_results = []
    for result in results:
        q_categories = get_question_category(result["question"])
        if category in q_categories:
            filtered_results.append(result)
    
    return filtered_results