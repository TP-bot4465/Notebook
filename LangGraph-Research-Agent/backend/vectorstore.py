# vectorstore.py
import os
from typing import List, Optional
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http import models # Import models để tạo Filter
from langchain_experimental.text_splitter import SemanticChunker

from config import (
    QDRANT_URL, 
    QDRANT_API_KEY, 
    QDRANT_COLLECTION_NAME, 
    EMBED_MODEL
)

# 1. Initialize Embedding Model
embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)

# 2. Initialize Qdrant Client
client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY
)

# --- HÀM LẤY RETRIEVER (HỖ TRỢ LỌC FILE) ---
def get_retriever(file_filters: Optional[List[str]] = None):
    """
    Trả về retriever. Nếu có danh sách file_filters, sẽ tạo bộ lọc metadata.
    """
    search_kwargs = {"k": 20}
    
    # Nếu người dùng chọn file cụ thể để chat
    if file_filters and len(file_filters) > 0:
        print(f"DEBUG: Đang tạo bộ lọc cho các file: {file_filters}")
        
        # Tạo bộ lọc Qdrant: metadata.source PHẢI nằm trong danh sách file_filters
        qdrant_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="metadata.source", 
                    match=models.MatchAny(any=file_filters)
                )
            ]
        )
        search_kwargs["filter"] = qdrant_filter

    vectorstore = QdrantVectorStore(
        client=client,
        collection_name=QDRANT_COLLECTION_NAME,
        embedding=embeddings,
    )
    
    return vectorstore.as_retriever(search_kwargs=search_kwargs)

# --- HÀM THÊM TÀI LIỆU (SEMANTIC CHUNKING + METADATA) ---
def add_document_to_vectorstore(text_content: str, source_filename: str):
    """
    Sử dụng Semantic Chunking để cắt văn bản và đẩy vào Qdrant kèm Metadata tên file.
    """
    if not text_content:
        raise ValueError("Document content cannot be empty.")

    print(f"Initializing Semantic Chunking for file: {source_filename}...")
    
    # Semantic Chunking: Cắt dựa trên ý nghĩa
    text_splitter = SemanticChunker(
        embeddings=embeddings, 
        breakpoint_threshold_type="percentile" 
    )
    
    # Tạo metadata source cho file
    metadatas = [{"source": source_filename}]
    
    # Tạo documents (LangChain sẽ tự nhân bản metadata cho các chunk)
    documents = text_splitter.create_documents([text_content], metadatas=metadatas)
    
    print(f"Semantic Chunking created {len(documents)} chunks based on meaning.")
    
    if not documents:
        print("No documents created from chunking.")
        return 0

    # Kiểm tra và tạo Collection nếu chưa có
    try:
        if not client.collection_exists(QDRANT_COLLECTION_NAME):
             print(f"Creating new Qdrant collection: {QDRANT_COLLECTION_NAME}")
             client.create_collection(
                 collection_name=QDRANT_COLLECTION_NAME,
                 vectors_config=models.VectorParams(
                     size=384, 
                     distance=models.Distance.COSINE
                 )
             )
    except Exception as e:
        print(f"Check collection error: {e}")

    print(f"Adding {len(documents)} chunks to Qdrant collection '{QDRANT_COLLECTION_NAME}'...")
    
    # Upsert vào Qdrant
    QdrantVectorStore.from_documents(
        documents=documents,
        embedding=embeddings,
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        collection_name=QDRANT_COLLECTION_NAME,
        force_recreate=False
    )
    
    print(f"Successfully added chunks from '{source_filename}' to Qdrant.")
    return len(documents)

# --- HÀM LẤY DANH SÁCH FILE ĐÃ UPLOAD ---
def list_indexed_documents():
    """
    Quét Qdrant để lấy danh sách các tên file (source) duy nhất.
    """
    try:
        if not client.collection_exists(QDRANT_COLLECTION_NAME):
            return []
        
        # Scroll lấy mẫu dữ liệu (limit 1000 để quét sâu)
        response = client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
            limit=1000, 
            with_payload=True,
            with_vectors=False
        )
        points, _ = response
        unique_files = set()
        
        for point in points:
            payload = point.payload or {}
            # Cấu trúc: payload -> metadata -> source (như trong ảnh bạn gửi)
            metadata = payload.get("metadata", {})
            if isinstance(metadata, dict):
                source = metadata.get("source")
                if source:
                    unique_files.add(source)
        
        return sorted(list(unique_files))

    except Exception as e:
        print(f"Error listing documents: {e}")
        return []