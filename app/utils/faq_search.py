import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# بارگذاری مدل
model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# بارگذاری FAISS index و متادیتا
index = faiss.read_index("faq_index.faiss")
with open("faq_metadata.json", "r", encoding="utf-8") as f:
    metadata = json.load(f)

def search_faq(query, top_k=3):
    # تبدیل سوال ورودی به embedding
    query_embedding = model.encode([query])

    # جستجو در FAISS
    distances, indices = index.search(np.array(query_embedding, dtype=np.float32), top_k)

    # نمایش نتایج
    results = [metadata["questions"][idx] for idx in indices[0] if idx < len(metadata["questions"])]
    return results

# تست بازیابی سوالات
query = "چگونه سنگ کلیه را درمان کنم؟"
related_questions = search_faq(query)

print("🚀 مرتبط‌ترین سوالات:")
for q in related_questions:
    print(f"- {q}")
