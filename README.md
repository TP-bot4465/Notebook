Đây là phiên bản `README.md` chuẩn chỉnh bằng Tiếng Việt, sử dụng phong cách chuyên nghiệp (Engineering Standard), hạn chế tối đa các biểu tượng (icon) trang trí thừa thãi để tập trung vào tính kỹ thuật.

-----

````markdown
# LangGraph Research Agent

Một trợ lý nghiên cứu thông minh được xây dựng trên nền tảng **LangGraph**, **FastAPI** và **Qdrant**. Hệ thống tích hợp RAG (Retrieval-Augmented Generation) với khả năng tìm kiếm web thời gian thực để cung cấp câu trả lời chính xác và có ngữ cảnh. Dự án sử dụng quy trình tác vụ tự chủ (agentic workflow) với khả năng tự đánh giá và quyết định luồng xử lý thông tin.

## Mục lục

- [Tổng quan](#tổng-quan)
- [Tính năng chính](#tính-năng-chính)
- [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
- [Công nghệ sử dụng](#công-nghệ-sử-dụng)
- [Yêu cầu tiên quyết](#yêu-cầu-tiên-quyết)
- [Cài đặt](#cài-đặt)
- [Cấu hình](#cấu-hình)
- [Hướng dẫn sử dụng](#hướng-dẫn-sử-dụng)
- [Cấu trúc dự án](#cấu-trúc-dự-án)

## Tổng quan

Dự án này triển khai một AI Agent tự chủ sử dụng kiến trúc biểu đồ trạng thái (state graph). Khác với các chuỗi RAG tuyến tính truyền thống, Agent này sử dụng logic điều kiện để định tuyến truy vấn, tự đánh giá chất lượng tài liệu tìm được (Self-Correction) và tự động chuyển sang tìm kiếm web khi dữ liệu nội bộ không đủ đáp ứng. Hệ thống đi kèm với giao diện người dùng hiển thị minh bạch "quá trình suy luận" (thinking process) theo thời gian thực.

## Tính năng chính

- **Quy trình Agent (Agentic Workflow):** Xây dựng trên LangGraph để quản lý trạng thái và các luồng logic phức tạp (Định tuyến, Fallback, Vòng lặp).
- **Truy xuất thông tin lai (Hybrid Retrieval):**
  - **RAG:** Tìm kiếm trong tài liệu PDF do người dùng tải lên thông qua vector database Qdrant.
  - **Web Search:** Cơ chế dự phòng sử dụng Tavily API để cập nhật thông tin mới nhất.
- **Định tuyến thông minh (Intelligent Routing):** Phân loại ý định người dùng để chọn công cụ phù hợp (RAG vs. Web vs. Trả lời trực tiếp).
- **Cơ chế tự đánh giá (Judge Node):** Một module LLM đánh giá xem tài liệu truy xuất được có đủ để trả lời câu hỏi hay không. Nếu không, hệ thống sẽ kích hoạt tìm kiếm web.
- **Phân mảnh ngữ nghĩa (Semantic Chunking):** Sử dụng kỹ thuật cắt văn bản dựa trên độ tương đồng ngữ nghĩa thay vì độ dài ký tự cố định.
- **Giao diện minh bạch:** Frontend hiển thị chi tiết vết thực thi (các node đã đi qua, quyết định được đưa ra) song song với câu trả lời cuối cùng.

## Kiến trúc hệ thống

Agent hoạt động dựa trên biểu đồ định hướng sau:

```mermaid
graph TD
    Start([Truy vấn người dùng]) --> Router{Router Node}
    Router -- "Dựa trên tài liệu" --> RAG[Tra cứu RAG]
    Router -- "Sự kiện thời sự" --> Web[Tìm kiếm Web]
    Router -- "Hội thoại chung" --> Answer[Sinh câu trả lời]
    
    RAG --> Judge{Judge Node}
    Judge -- "Đủ thông tin" --> Answer
    Judge -- "Thiếu thông tin" --> Web
    
    Web --> Answer
    Answer --> End([Phản hồi cuối cùng])
````

## Công nghệ sử dụng

**Backend**

  - **Ngôn ngữ:** Python 3.10+
  - **Framework:** FastAPI
  - **Điều phối:** LangGraph, LangChain
  - **LLM:** Google Gemini 1.5 Flash
  - **Vector Database:** Qdrant (Cloud hoặc Local)
  - **Công cụ tìm kiếm:** Tavily API
  - **Embeddings:** HuggingFace (`sentence-transformers/all-MiniLM-L6-v2`)

**Frontend**

  - **Core:** HTML5, CSS3, Vanilla JavaScript
  - **Hiển thị:** Custom CSS hỗ trợ Markdown (Marked.js, Highlight.js)

## Yêu cầu tiên quyết

Đảm bảo hệ thống đã cài đặt:

  - Python 3.10 trở lên
  - Git
  - API Key cho các dịch vụ:
      - Google AI Studio (Gemini)
      - Tavily Search
      - Qdrant (URL và API Key)

## Cài đặt

1.  **Clone dự án**

    ```bash
    git clone [https://github.com/username-cua-ban/LangGraph-Research-Agent.git](https://github.com/username-cua-ban/LangGraph-Research-Agent.git)
    cd LangGraph-Research-Agent
    ```

2.  **Thiết lập môi trường ảo**

    ```bash
    python -m venv .venv

    # Windows
    .venv\Scripts\activate

    # macOS/Linux
    source .venv/bin/activate
    ```

3.  **Cài đặt thư viện phụ thuộc**

    ```bash
    pip install -r requirements.txt
    ```

## Cấu hình

1.  Tạo file `.env` tại thư mục gốc của dự án.

2.  Thêm các biến môi trường sau (thay thế bằng key thực tế của bạn):

    ```ini
    # Google Gemini
    GOOGLE_API_KEY=your_google_api_key_here

    # Qdrant Vector DB
    QDRANT_URL=your_qdrant_url
    QDRANT_API_KEY=your_qdrant_api_key
    QDRANT_COLLECTION_NAME=langgraph-rag-collection

    # Tavily Search
    TAVILY_API_KEY=your_tavily_api_key_here

    # Embedding Model (Tùy chọn)
    EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2
    ```

3.  **Khởi tạo Index cơ sở dữ liệu**
    Chạy script khởi tạo để thiết lập Qdrant collection và payload index cho tính năng lọc file:

    ```bash
    python backend/fix_qdrant_index.py
    ```

## Hướng dẫn sử dụng

### 1\. Khởi chạy Backend Server

```bash
uvicorn backend.main:app --reload
```

API sẽ hoạt động tại địa chỉ `http://localhost:8000`.

### 2\. Khởi chạy Frontend

Mở file `frontend_web/index.html` trong trình duyệt web.
*Lưu ý: Để có trải nghiệm tốt nhất và tránh lỗi CORS, nên sử dụng Live Server (VS Code Extension).*

### 3\. Quy trình sử dụng

1.  **Tải lên:** Sử dụng thanh bên (sidebar) để tải lên các tài liệu PDF.
2.  **Chọn nguồn:** Tích vào các ô bên cạnh tên file để yêu cầu Agent tập trung tìm kiếm trong các tài liệu đó.
3.  **Hội thoại:** Nhập câu hỏi vào khung chat.
      - Bật/Tắt "Enable Web Search" để cho phép Agent truy cập internet.
      - Nhấn vào "Thinking Process" trong câu trả lời để xem các bước suy luận nội bộ.

## Cấu trúc dự án

```text
LangGraph-Research-Agent/
├── backend/
│   ├── agent.py             # Logic các node và cạnh trong LangGraph
│   ├── config.py            # Quản lý biến môi trường
│   ├── main.py              # Các endpoint FastAPI và điểm vào ứng dụng
│   ├── vectorstore.py       # Tương tác với Qdrant và logic phân mảnh (chunking)
│   └── fix_qdrant_index.py  # Script khởi tạo cơ sở dữ liệu
├── frontend_web/
│   ├── index.html           # Giao diện người dùng chính
│   ├── style.css            # Định dạng giao diện
│   └── script.js            # Logic frontend và tích hợp API
├── requirements.txt         # Các thư viện Python phụ thuộc
└── README.md                # Tài liệu dự án
```

```
```
