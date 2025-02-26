import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# مدل برای تولید embeddings
model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# بارگذاری سوالات پردازش‌شده
processed_file = "processed_all_questions.json"

with open(processed_file, "r", encoding="utf-8") as f:
    data = json.load(f)

questions = [entry["question"] for entry in data]

# تولید embeddings برای سوالات
embeddings = model.encode(questions)

# ایجاد FAISS index
index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(np.array(embeddings, dtype=np.float32))

# ذخیره FAISS index
faiss.write_index(index, "faq_index.faiss")

# ذخیره متادیتا
with open("faq_metadata.json", "w", encoding="utf-8") as f:
    json.dump({"questions": questions}, f, ensure_ascii=False, indent=4)

print("✅ Embeddings created and saved in faq_index.faiss!")
