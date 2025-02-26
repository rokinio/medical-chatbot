"""
فایل تنظیمات و مسیرهای پروژه چت‌بات پزشکی
"""

import os

# کلید API
API_KEY = "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"

# مسیرهای فایل‌ها
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)  # ایجاد پوشه اگر وجود ندارد

FAISS_INDEX_PATH = os.path.join(DATA_DIR, "faq_index.faiss")
FAISS_METADATA_PATH = os.path.join(DATA_DIR, "faq_metadata.json")
PROCESSED_QUESTIONS_PATH = os.path.join(DATA_DIR, "processed_all_questions.json")
FEEDBACK_FILE = os.path.join(DATA_DIR, "feedback_data.json")

# مسیر مدل‌ها
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
os.makedirs(MODEL_PATH, exist_ok=True)

# تنظیمات مدل
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# دسته‌بندی‌های پزشکی
MEDICAL_CATEGORIES = {
    "قلب و عروق": ["قلب", "عروق", "فشار خون", "کلسترول", "سکته قلبی", "آنژین", "تپش قلب"],
    "تنفسی": ["ریه", "آسم", "تنفس", "برونشیت", "سرفه", "تنگی نفس"],
    "گوارش": ["معده", "روده", "هضم", "اسهال", "یبوست", "نفخ", "سوءهاضمه"],
    "مغز و اعصاب": ["سردرد", "میگرن", "تشنج", "مغز", "عصب", "سرگیجه"],
    "کلیه و مجاری ادراری": ["کلیه", "سنگ کلیه", "مثانه", "ادرار", "پروستات"],
    "پوست و مو": ["پوست", "مو", "آکنه", "خارش", "جوش", "اگزما", "ریزش مو"],
    "دیابت و غدد": ["دیابت", "قند خون", "تیروئید", "هورمون", "انسولین"],
    "استخوان و مفاصل": ["استخوان", "مفصل", "آرتروز", "کمردرد", "شکستگی", "دررفتگی"]
}

# CSS استایل برای رابط کاربری - فایل این استایل به درستی اصلاح شده است
APP_STYLE = """
<style>
    @import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazir-font@v30.1.0/dist/font-face.css');
    
    * {
        font-family: 'Vazir', 'Tahoma', sans-serif !important;
        direction: rtl;
        text-align: right;
    }
    
    .stTextInput>div>div>input, .stTextArea>div>textarea {
        text-align: right !important;
    }
    
    .stButton>button {
        background-color: #4CAF50 !important;
        color: white !important;
    }
    
    .answer-box {
        background-color: #f0f8ff;
        padding: 15px;
        border-radius: 5px;
        margin-top: 20px;
    }
    
    .feedback-buttons {
        display: flex;
        justify-content: center;
        gap: 20px;
        margin-top: 10px;
    }
    
    .similar-question-btn {
        text-align: right;
        width: 100%;
        margin: 2px 0;
    }
    
    .history-item {
        background-color: #f5f5f5;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
    
    .tabs {
        margin-top: 20px;
    }
    
    .source-tag {
        display: inline-block;
        background-color: #e1e1e1;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.8em;
        margin-left: 6px;
    }
</style>
"""