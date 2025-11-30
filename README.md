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
