#!/usr/bin/env python3
# medical_chat_app_improved.py - فایل اصلی برنامه
"""
چت‌بات پزشکی هوشمند با قابلیت جستجوی پیشرفته
- پشتیبانی از چندین منبع داده
- جستجوی معنایی با FAISS
- امکان فیلتر بر اساس دسته‌بندی و منبع
"""

import streamlit as st
import time
import os

# وارد کردن ماژول‌های پروژه
from config import APP_STYLE
from data_manager import check_and_create_files, load_categories, load_data_sources, save_feedback
from search_engine import search_with_faiss_cached, get_question_category, filter_by_category
from api_client import ask_openai

def init_session_state():
    """مقداردهی اولیه متغیرهای جلسه"""
    if 'search_cache' not in st.session_state:
        st.session_state.search_cache = {}
        
    if 'feedback_data' not in st.session_state:
        st.session_state.feedback_data = []
        
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
        
    if 'last_query' not in st.session_state:
        st.session_state.last_query = ""
        
    if 'last_response' not in st.session_state:
        st.session_state.last_response = ""
        
    if 'has_response' not in st.session_state:
        st.session_state.has_response = False
        
    if 'user_query' not in st.session_state:
        st.session_state.user_query = ""

def create_chat_tab():
    """ایجاد تب گفتگو"""
    # بارگذاری منابع داده
    data_sources = load_data_sources()
    
    # انتخاب منبع داده
    selected_source = st.selectbox(
        "منبع داده:",
        ["همه"] + data_sources if "همه" not in data_sources else data_sources
    )
    
    # انتخاب دسته‌بندی
    categories = load_categories()
    selected_category = st.selectbox(
        "دسته‌بندی موضوعی:",
        ["همه"] + list(categories.keys())
    )
    
    # انتخاب روش جستجو
    search_method = st.radio(
        "روش جستجو:",
        ["جستجوی پیشرفته (FAISS)", "جستجوی ساده متنی"]
    )
    
    # ورودی کاربر
    query = st.text_area("سوال خود را بنویسید:", st.session_state.user_query, height=100)
    st.session_state.user_query = ""  # پاک کردن مقدار قبلی پس از استفاده
    
    # دکمه جستجو
    if st.button("دریافت پاسخ", key="submit_button", type="primary"):
        if query:
            with st.spinner("در حال پردازش..."):
                # زمان‌سنجی
                start_time = time.time()
                
                # یافتن سوالات مشابه
                if search_method == "جستجوی پیشرفته (FAISS)":
                    similar_results = search_with_faiss_cached(query, top_k=5, selected_source=selected_source)
                else:
                    similar_results = search_with_faiss_cached(query, top_k=5, selected_source=selected_source)
                
                # فیلتر کردن بر اساس دسته‌بندی
                if selected_category != "همه":
                    similar_results = filter_by_category(similar_results, selected_category)
                
                # استخراج سوالات از نتایج
                similar_questions = [result["question"] for result in similar_results]
                
                search_time = time.time() - start_time
                
                # ساخت پرامپت برای API
                context = "\n".join(similar_questions) if similar_questions else "سوال مشابهی یافت نشد."
                
                # دریافت پاسخ
                prompt = f"سوال کاربر: {query}\n\nسوالات مشابه در پایگاه داده:\n{context}\n\nلطفاً یک پاسخ جامع پزشکی ارائه دهید."
                response = ask_openai(prompt)
                total_time = time.time() - start_time
                
                # ذخیره سوال و جواب در حافظه جلسه
                st.session_state.last_query = query
                st.session_state.last_response = response
                st.session_state.has_response = True
                
                # افزودن به تاریخچه
                chat_entry = {
                    "query": query,
                    "response": response,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "categories": get_question_category(query),
                    "similar_questions": similar_results  # ذخیره سوالات مشابه با اطلاعات منبع
                }
                st.session_state.chat_history.append(chat_entry)
                
                # نمایش پاسخ
                st.markdown(f'<div class="answer-box"><h3>📌 پاسخ:</h3>{response}</div>', unsafe_allow_html=True)
                
                # بخش بازخورد
                st.write("### آیا این پاسخ مفید بود؟")
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("👍 بله، مفید بود", key="feedback_positive"):
                        save_feedback(query, response, "مثبت")
                        st.success("از بازخورد شما متشکریم!")
                
                with col2:
                    if st.button("👎 خیر، مفید نبود", key="feedback_negative"):
                        comment_container = st.container()
                        with comment_container:
                            comment = st.text_area("لطفاً دلیل آن را توضیح دهید:", key="feedback_comment")
                            if st.button("ارسال بازخورد", key="submit_feedback"):
                                save_feedback(query, response, "منفی", comment)
                                st.success("از بازخورد شما متشکریم!")
                
                # نمایش سوالات مشابه
                if similar_results:
                    with st.expander("🔍 سوالات مشابه"):
                        for i, result in enumerate(similar_results):
                            # نمایش متن با markdown برای حفظ قالب و جهت متن
                            st.markdown(f"**🔍 {result['question']}** (منبع: {result['source']})", unsafe_allow_html=True)
                            # دکمه جداگانه برای انتخاب سوال
                            if st.button(f"انتخاب این سوال", key=f"similar_q_{i}"):
                                st.session_state.user_query = result["question"]
                                st.experimental_rerun()
                
                # نمایش زمان و روش جستجو
                st.info(f"⏱️ زمان جستجو: {search_time:.2f} ثانیه | زمان کل: {total_time:.2f} ثانیه | روش: {search_method}")
                
                # امکان اشتراک‌گذاری
                with st.expander("💾 ذخیره یا اشتراک‌گذاری پاسخ"):
                    st.code(response)  # نمایش پاسخ در قالب قابل کپی
        else:
            st.warning("لطفاً سوال خود را وارد کنید.")

def create_history_tab():
    """ایجاد تب تاریخچه گفتگوها"""
    st.subheader("📜 تاریخچه گفتگوها")
    
    if not st.session_state.chat_history:
        st.info("هنوز هیچ گفتگویی ثبت نشده است.")
    else:
        # نمایش تاریخچه از جدیدترین به قدیمی‌ترین
        for i, entry in enumerate(reversed(st.session_state.chat_history)):
            with st.expander(f"**{entry['timestamp']}** - {entry['query']}"):
                st.write(f"**سوال:** {entry['query']}")
                st.write(f"**دسته‌بندی:** {', '.join(entry['categories'])}")
                st.write(f"**پاسخ:**")
                st.write(entry['response'])
                
                # دکمه برای استفاده مجدد از این سوال
                if st.button(f"استفاده مجدد از این سوال", key=f"reuse_{i}"):
                    st.session_state.user_query = entry['query']
                    st.experimental_rerun()
        
        # دکمه پاک کردن تاریخچه
        if st.button("🗑️ پاک کردن تاریخچه", key="clear_history"):
            st.session_state.chat_history = []
            st.success("تاریخچه با موفقیت پاک شد!")
            st.experimental_rerun()

def create_settings_tab():
    """ایجاد تب تنظیمات"""
    from config import FAISS_INDEX_PATH, FAISS_METADATA_PATH, PROCESSED_QUESTIONS_PATH, FEEDBACK_FILE
    
    st.subheader("⚙️ تنظیمات چت‌بات")
    
    # بررسی وضعیت فایل‌ها
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**وضعیت فایل‌ها:**")
        st.write(f"- FAISS Index: {'✅ موجود' if os.path.exists(FAISS_INDEX_PATH) else '❌ ناموجود'}")
        st.write(f"- FAISS Metadata: {'✅ موجود' if os.path.exists(FAISS_METADATA_PATH) else '❌ ناموجود'}")
        st.write(f"- سوالات پردازش شده: {'✅ موجود' if os.path.exists(PROCESSED_QUESTIONS_PATH) else '❌ ناموجود'}")
        st.write(f"- فایل بازخورد: {'✅ موجود' if os.path.exists(FEEDBACK_FILE) else '❌ ناموجود'}")
    
    with col2:
        st.write("**آمار:**")
        st.write(f"- تعداد گفتگوها: {len(st.session_state.chat_history)}")
        st.write(f"- تعداد بازخوردها: {len(st.session_state.feedback_data)}")
        st.write(f"- تعداد موارد کش شده: {len(st.session_state.search_cache)}")
    
    # پاک کردن کش
    if st.button("🗑️ پاک کردن کش جستجو", key="clear_cache"):
        st.session_state.search_cache = {}
        st.success("کش جستجو با موفقیت پاک شد!")
        st.experimental_rerun()
    
    # ایجاد مجدد فایل‌های FAISS
    st.subheader("بازسازی فایل‌های FAISS")
    if st.button("🔄 بازسازی فایل‌های FAISS", key="rebuild_faiss"):
        try:
            # حذف فایل‌های قبلی
            if os.path.exists(FAISS_INDEX_PATH):
                os.remove(FAISS_INDEX_PATH)
            if os.path.exists(FAISS_METADATA_PATH):
                os.remove(FAISS_METADATA_PATH)
            
            # فراخوانی تابع بررسی و ایجاد فایل‌ها
            check_and_create_files()
            
            st.success("فایل‌های FAISS با موفقیت بازسازی شدند!")
            st.experimental_rerun()
        except Exception as e:
            st.error(f"خطا در بازسازی فایل‌های FAISS: {e}")

def main():
    # تنظیمات صفحه
    st.set_page_config(page_title="چت‌بات پزشکی هوشمند", page_icon="🏥", layout="wide")
    
    # مقداردهی اولیه متغیرهای جلسه
    init_session_state()
    
    # تنظیم استایل صفحه - اطمینان از اعمال CSS قبل از هر چیز دیگر
    st.markdown(APP_STYLE, unsafe_allow_html=True)
    
    # بررسی و ایجاد فایل‌های ضروری
    check_and_create_files()

    # عنوان
    st.title("🏥 چت‌بات پزشکی هوشمند")
    st.markdown('<p style="direction:rtl; text-align:right;">سوال پزشکی خود را بپرسید و پاسخی مبتنی بر اطلاعات علمی دریافت کنید.</p>', unsafe_allow_html=True)
    st.markdown('<p style="direction:rtl; text-align:right; color:red;">⚠️ توجه: این چت‌بات جایگزین مشاوره پزشکی نیست.</p>', unsafe_allow_html=True)

    # ایجاد تب‌ها
    tab1, tab2, tab3 = st.tabs(["💬 گفتگو", "📜 تاریخچه", "⚙️ تنظیمات"])

    with tab1:
        create_chat_tab()

    with tab2:
        create_history_tab()

    with tab3:
        create_settings_tab()

    # پاورقی
    st.markdown('<div style="margin-top: 50px; text-align: center; color: #666; font-size: 0.8rem; direction:rtl;">این پروژه صرفاً برای اهداف آموزشی توسعه یافته است. © 1403</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()