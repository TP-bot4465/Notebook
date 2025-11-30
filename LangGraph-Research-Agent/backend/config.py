# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# --- Qdrant Configuration ---
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333") 
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None) 
QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "user_documents")
# SYSTEM_COLLECTION_NAME = os.getenv("SYSTEM_COLLECTION_NAME", "system_intelligence")  

# --- Google Gemini Configuration ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- Tavily Configuration ---
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# --- Embedding Model ---
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# --- Paths ---
DOC_SOURCE_DIR = os.getenv("DOC_SOURCE_DIR", "data")