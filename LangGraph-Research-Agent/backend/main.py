# main.py
import os
import tempfile
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.document_loaders import PyPDFLoader

# Import agent và các hàm từ vectorstore
from agent import rag_agent
from vectorstore import add_document_to_vectorstore, list_indexed_documents

# Initialize FastAPI app
app = FastAPI(
    title="LangGraph RAG Agent API",
    description="API for the LangGraph-powered RAG agent with Qdrant & Gemini.",
    version="1.0.0",
)

# --- CORS Config (QUAN TRỌNG) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models ---
class TraceEvent(BaseModel):
    step: int
    node_name: str
    description: str
    details: Dict[str, Any] = Field(default_factory=dict)
    event_type: str

class QueryRequest(BaseModel):
    session_id: str
    query: str
    enable_web_search: bool = True
    selected_files: List[str] = [] # Danh sách file người dùng chọn

class AgentResponse(BaseModel):
    response: str
    trace_events: List[TraceEvent] = Field(default_factory=list)

class DocumentUploadResponse(BaseModel):
    message: str
    filename: str
    processed_chunks: int

# --- API 1: LẤY DANH SÁCH FILE ---
@app.get("/documents/", response_model=List[str])
async def get_documents():
    """Trả về danh sách các file đang có trong DB"""
    docs = list_indexed_documents()
    return docs

# --- API 2: UPLOAD DOCUMENT ---
@app.post("/upload-document/", response_model=DocumentUploadResponse, status_code=status.HTTP_200_OK)
async def upload_document(file: UploadFile = File(...)):
    """Uploads a PDF document."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        file_content = await file.read()
        tmp_file.write(file_content)
        temp_file_path = tmp_file.name
    
    print(f"Received PDF: {file.filename}")

    try:
        loader = PyPDFLoader(temp_file_path)
        documents = loader.load()

        total_chunks_added = 0
        if documents:
            full_text_content = "\n\n".join([doc.page_content for doc in documents])
            
            # Gọi hàm add với filename để lưu metadata
            total_chunks_added = add_document_to_vectorstore(full_text_content, file.filename)
        
        return DocumentUploadResponse(
            message=f"PDF '{file.filename}' uploaded and indexed.",
            filename=file.filename,
            processed_chunks=total_chunks_added
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {e}")
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

# --- API 3: CHAT ---
@app.post("/chat/", response_model=AgentResponse)
async def chat_with_agent(request: QueryRequest):
    trace_events_for_frontend: List[TraceEvent] = []
    
    try:
        # Cấu hình truyền xuống Agent
        config = {
            "configurable": {
                "thread_id": request.session_id,
                "web_search_enabled": request.enable_web_search,
                "selected_files": request.selected_files # Truyền danh sách file
            }
        }
        inputs = {"messages": [HumanMessage(content=request.query)]}
        final_message = ""
        
        print(f"--- Chat Session: {request.session_id} | Files: {request.selected_files} ---")

        for i, s in enumerate(rag_agent.stream(inputs, config=config)):
            # Trace logic
            if '__end__' in s:
                current_node_name = '__end__'
                node_output_state = s['__end__']
            else:
                current_node_name = list(s.keys())[0] 
                node_output_state = s[current_node_name]

            event_desc = f"Node: {current_node_name}"
            event_details = {}
            
            if current_node_name == "router":
                route = node_output_state.get('route')
                event_desc = f"Router -> {route}"
                event_details = {"decision": route}
            elif current_node_name == "rag_lookup":
                rag_txt = node_output_state.get("rag", "")
                event_desc = "RAG Check"
                event_details = {"summary": rag_txt[:100]}
            elif current_node_name == "web_search":
                web_txt = node_output_state.get("web", "")
                event_desc = "Web Search"
                event_details = {"summary": web_txt[:100]}

            trace_events_for_frontend.append(TraceEvent(
                step=i+1, node_name=current_node_name, 
                description=event_desc, details=event_details, event_type="node"
            ))

            state_dict = s.get('__end__') or s.get(list(s.keys())[0])
            if state_dict and "messages" in state_dict:
                for msg in reversed(state_dict["messages"]):
                    if isinstance(msg, AIMessage):
                        final_message = msg.content
                        break
        
        if not final_message: final_message = "No response generated."

        return AgentResponse(response=final_message, trace_events=trace_events_for_frontend)

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error: {e}")

@app.get("/health")
async def health_check():
    return {"status": "ok"}