from qdrant_client import QdrantClient, models
import os
from dotenv import load_dotenv

# Load biến môi trường (URL, API KEY)
load_dotenv()

# 1. Cấu hình Client (Sửa lại cho đúng với setup của bạn)
qdrant_url = os.getenv("QDRANT_URL")
qdrant_api_key = os.getenv("QDRANT_API_KEY")


client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)

COLLECTION_NAME = "langgraph-rag-collection"  
print(f"Đang tạo Index cho collection: {COLLECTION_NAME}...")

try:
    # 3. Tạo Payload Index cho trường 'metadata.source'
    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="metadata.source",  # Trường bị báo lỗi
        field_schema=models.PayloadSchemaType.KEYWORD # Loại index là KEYWORD
    )
    print("Đã tạo Index thành công! Hãy chạy lại chương trình chính.")
except Exception as e:
    print(f" Lỗi: {e}")
    print("Gợi ý: Kiểm tra lại xem COLLECTION_NAME có đúng không?")