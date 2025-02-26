"""
ارتباط با OpenAI API برای دریافت پاسخ
"""

import requests
import json
from config import API_KEY

def ask_openai(question):
    """ارسال درخواست مستقیم به OpenAI API"""
    url = "https://api.openai.com/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    data = {
        "model": "gpt-4",
        "messages": [
            {"role": "system", "content": "شما یک پزشک متخصص هستید و پاسخ‌های دقیق و علمی ارائه می‌دهید."},
            {"role": "user", "content": question}
        ],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()  # بررسی خطای HTTP
        response_json = response.json()
        
        if "choices" in response_json and len(response_json["choices"]) > 0:
            return response_json["choices"][0]["message"]["content"]
        else:
            error_message = response_json.get("error", {}).get("message", "خطای نامشخص")
            return f"خطا در دریافت پاسخ: {error_message}"
            
    except requests.exceptions.RequestException as e:
        return f"خطای ارتباط با API: {str(e)}"
    except Exception as e:
        return f"خطای غیرمنتظره: {str(e)}"