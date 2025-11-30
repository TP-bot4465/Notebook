import os
from typing import List, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver  # hiện không dùng, nhưng cứ để đó nếu sau này muốn bật
from langchain_core.runnables import RunnableConfig

from config import GOOGLE_API_KEY, TAVILY_API_KEY
from vectorstore import get_retriever

# =====================================================================
# TOOLS
# =====================================================================

# Config Tavily
os.environ["TAVILY_API_KEY"] = TAVILY_API_KEY
tavily = TavilySearch(max_results=3, topic="general")


@tool
def web_search_tool(query: str) -> str:
    """Use Tavily to perform an up-to-date web search and return text summary."""
    try:
        result = tavily.invoke({"query": query})
        if isinstance(result, dict) and "results" in result:
            formatted_results = []
            for item in result["results"]:
                title = item.get("title", "No title")
                content = item.get("content", "No content")
                url = item.get("url", "")
                formatted_results.append(
                    f"Title: {title}\nContent: {content}\nURL: {url}"
                )
            return "\n\n".join(formatted_results) if formatted_results else "No results found"
        else:
            return str(result)
    except Exception as e:
        # Để cho web_node xử lý chuỗi WEB_ERROR::... và không đưa vào context
        return f"WEB_ERROR::{e}"


# =====================================================================
# SCHEMAS (STRUCTURED OUTPUT)
# =====================================================================

class RouteDecision(BaseModel):
    """Router quyết định bước tiếp theo cho agent."""
    route: Literal["rag", "web", "answer", "end"]
    reply: str | None = Field(
        None,
        description="Short friendly reply when route == 'end'.",
    )


class RagJudge(BaseModel):
    """Judge đánh giá chất lượng thông tin từ RAG."""
    sufficient: bool = Field(
        ...,
        description="True nếu thông tin RAG đủ & liên quan để trả lời.",
    )


# =====================================================================
# LLM INSTANCES (GEMINI)
# =====================================================================

os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

router_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
).with_structured_output(RouteDecision)

judge_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
).with_structured_output(RagJudge)

answer_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.7,
)

# =====================================================================
# STATE TYPE
# =====================================================================

class AgentState(TypedDict, total=False):
    """Trạng thái chia sẻ giữa các node LangGraph."""
    messages: List[BaseMessage]
    route: Literal["rag", "web", "answer", "end"]
    rag: str
    web: str
    web_search_enabled: bool


# =====================================================================
# NODE 1: ROUTER
# =====================================================================

def router_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """Quyết định route: rag / web / answer / end."""
    print("\n--- Entering router_node ---")
    query = next(
        (m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
        "",
    )

    configurable = config.get("configurable", {}) or {}
    web_search_enabled = configurable.get("web_search_enabled", True)
    selected_files = configurable.get("selected_files", [])

    # Prompt mô tả nhiệm vụ router
    system_prompt = """
    You are a routing controller in a QA system. Your job is to decide which information source the agent should use next for the user's query.

    Available routes:
    - "rag": Query the internal knowledge base / vector store.
    - "web": Use real-time web search (only when web search is enabled).
    - "answer": Answer directly from your own general knowledge, without using any external tool.
    - "end": For pure greetings or small-talk where no factual answer is needed. When you choose "end", you MUST also provide a short friendly reply in the "reply" field.

    General routing strategy:
    - For most factual, explanatory, or procedural questions, you should prefer "rag" and let the system try the internal knowledge base first.
    - Web search is mainly a fallback: if information from RAG is insufficient, irrelevant, or clearly not useful, the system may then use the "web" route (when web search is enabled) to look for better information.
    - You MAY route directly to "web" only when the question clearly depends on very time-sensitive, live, or very recent information that a static knowledge base is unlikely to contain (e.g. today’s news, current weather, live sports scores, stock prices).
    - Use "answer" only for very simple questions that do not need any lookup (e.g. 'What is your name?', 'What can you do?').
    - Use "end" only for greetings or small-talk where the user is not asking for information.

    If you are unsure between "rag" and "web", choose "rag" by default.
    """

    # Thông tin trạng thái web search
    if web_search_enabled:
        system_prompt += "\n\nWeb search status: ENABLED."
    else:
        system_prompt += "\n\nWeb search status: DISABLED. You MUST NOT route to 'web'."

    # Thông tin trạng thái knowledge base
    if not selected_files:
        system_prompt += """
        Knowledge base status: NO documents are selected.
        You do NOT have access to any user-provided PDFs or documents.
        If the user asks about 'the document I gave you', 'the PDF I uploaded', or similar:
        - Do NOT route to 'web' just to guess the content of their document.
        - Prefer the 'answer' route and explain that no documents are selected, so you cannot see their file.
        """
    else:
        system_prompt += """
        Knowledge base status: Some documents ARE selected.
        If the user asks about the content of their documents/PDFs, you should choose the 'rag' route (not 'web').
        """

    messages = [("system", system_prompt), ("user", query)]
    result: RouteDecision = router_llm.invoke(messages)

    # Chặn case web_search_disabled nhưng LLM vẫn chọn "web"
    if not web_search_enabled and result.route == "web":
        # Nếu có KB thì dùng rag; nếu không thì answer thẳng
        result.route = "rag" if selected_files else "answer"

    print(f"Router decision: {result.route}")

    out: AgentState = {
        "messages": state["messages"],
        "route": result.route,
        "web_search_enabled": web_search_enabled,
    }

    # Nếu là small-talk thì trả lời ngay tại đây
    if result.route == "end":
        out["messages"] = state["messages"] + [
            AIMessage(content=result.reply or "Hello!")
        ]

    return out


# =====================================================================
# NODE 2: RAG LOOKUP
# =====================================================================

def rag_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """Tìm kiếm trên vectorstore + dùng judge để đánh giá đủ / chưa."""
    print("\n--- Entering rag_node ---")
    query = next(
        (m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
        "",
    )

    configurable = config.get("configurable", {}) or {}
    web_search_enabled = configurable.get("web_search_enabled", True)
    selected_files = configurable.get("selected_files", [])

    print(f"RAG query: {query}")
    print(f"Web search enabled: {web_search_enabled}")
    print(f"Selected files: {selected_files}")

    chunks = ""
    next_route: Literal["answer", "web"] = "answer"

    # Nếu user không chọn file nào -> bỏ qua RAG, chuyển sang web hoặc answer
    if not selected_files:
        print("User selected NO files. Skipping RAG retrieval.")
        chunks = ""
        next_route = "web" if web_search_enabled else "answer"
    else:
        print(f"Searching in specific files: {selected_files}")
        try:
            retriever_instance = get_retriever(file_filters=selected_files)
            docs = retriever_instance.invoke(query)
            chunks = "\n\n".join(d.page_content for d in docs) if docs else ""
            print(f"Retrieved {len(docs) if docs else 0} chunks.")
        except Exception as e:
            print(f"RAG Error: {e}")
            chunks = ""

        # Không có chunk hữu ích -> fallback web / answer
        if not chunks:
            print("No useful RAG chunks. Routing to web/answer.")
            next_route = "web" if web_search_enabled else "answer"
        else:
            # Judge: đánh giá xem chunks có đủ để trả lời không
            judge_messages = [
                (
                    "system",
                    """
                    You are a judge evaluating whether the retrieved text is sufficient and relevant to fully answer the user's question.

                    Criteria for sufficiency:
                    - The retrieved text directly addresses the main question.
                    - It contains enough detail for a clear and accurate answer.
                    - It is specific and relevant, not just vague background.

                    NOT sufficient if:
                    - It is vague, generic, or only partially related.
                    - It does not clearly answer the user's main question.
                    - It is obviously incomplete or missing key details.
                    - There was effectively no useful retrieval (e.g. 'No results found').

                    Respond ONLY with a JSON object of the form:
                    {"sufficient": true}  or  {"sufficient": false}

                    Examples:
                    - Question: 'What is the capital of France?'
                    Retrieved: 'Paris is the capital of France.'
                    -> {"sufficient": true}

                    - Question: 'What are the symptoms of diabetes?'
                    Retrieved: 'Diabetes is a chronic condition.'
                    -> {"sufficient": false}  (does not list symptoms)

                    - Question: 'How to fix error X in software Y?'
                    Retrieved: 'No relevant information found.'
                    -> {"sufficient": false}
                    """,
                ),
                (
                    "user",
                    f"Question: {query}\n\nRetrieved info:\n{chunks}\n\nIs this sufficient to answer the question? Respond ONLY with JSON.",
                ),
            ]

            verdict: RagJudge = judge_llm.invoke(judge_messages)
            print(f"RAG Judge verdict: {verdict.sufficient}")

            if verdict.sufficient:
                next_route = "answer"
            else:
                next_route = "web" if web_search_enabled else "answer"
                print(f"RAG not sufficient. Next route: {next_route}")

    print(f"RAG node decided next_route = {next_route}")
    print("--- Exiting rag_node ---")

    return {
        **state,
        "rag": chunks,
        "route": next_route,
        "web_search_enabled": web_search_enabled,
    }


# =====================================================================
# NODE 3: WEB SEARCH
# =====================================================================

def web_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """Gọi Tavily để lấy kết quả web."""
    print("\n--- Entering web_node ---")
    query = next(
        (m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
        "",
    )

    web_search_enabled = config.get("configurable", {}).get("web_search_enabled", True)

    # Nếu web bị tắt -> ghi chú + route sang answer
    if not web_search_enabled:
        return {**state, "web": "Web search disabled.", "route": "answer"}

    snippets = web_search_tool.invoke(query)
    if snippets.startswith("WEB_ERROR::"):
        # Lỗi Tavily -> không đưa lỗi vào context
        print(snippets)
        snippets = ""

    return {**state, "web": snippets, "route": "answer"}


# =====================================================================
# NODE 4: ANSWER
# =====================================================================

def answer_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """
    Node cuối cùng sinh câu trả lời:
    - Ghép context từ RAG + Web.
    - Tôn trọng trạng thái: có/không có KB, có/không có web.
    """
    print("\n--- Entering answer_node ---")
    user_q = next(
        (m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
        "",
    )

    configurable = config.get("configurable", {}) or {}
    selected_files = configurable.get("selected_files", [])
    web_search_enabled = configurable.get("web_search_enabled", True)

    # Ghép context từ state
    ctx_parts: List[str] = []
    if state.get("rag"):
        ctx_parts.append("Knowledge Base Info:\n" + state["rag"])
    if state.get("web") and not state["web"].startswith("Web search disabled"):
        ctx_parts.append("Web Search Results:\n" + state["web"])

    context = "\n\n".join(ctx_parts).strip()

    # CASE ĐẶC BIỆT:
    # Không có KB, không cho web, không có context từ RAG & web -> trả về "không đủ thông tin", tránh gọi LLM
    no_kb = not selected_files
    no_web_allowed = not web_search_enabled
    no_web_context = (not state.get("web")) or state.get("web", "").startswith(
        "Web search disabled"
    )
    no_rag_context = not state.get("rag")

    if no_kb and no_web_allowed and no_web_context and no_rag_context:
        print("No KB, no web, no external context -> returning explicit 'I don't know'.")
        ans = (
            "Hiện tại tôi không có tài liệu nào để tham chiếu và chức năng tìm kiếm web đang bị tắt, "
            "nên tôi không đủ thông tin để trả lời chính xác câu hỏi này."
        )
        return {
            **state,
            "messages": state["messages"] + [AIMessage(content=ans)],
        }

    # NOTE cho LLM: có / không có tài liệu
    if not selected_files:
        kb_status = (
            "System note: There are currently NO knowledge base documents selected. "
            "You do NOT have access to any user-provided PDFs or documents. "
            "If the question asks about 'the document I gave you', 'the PDF I uploaded', or similar, "
            "you MUST clearly say that you cannot see any document and ask the user to upload/select one. "
            "Do NOT invent or guess the content of any document."
        )
    else:
        kb_status = (
            "System note: Knowledge base documents are available. "
            "Any information from those documents will appear in the 'Knowledge Base Info' section inside the context below. "
            "Do not claim to know things from the documents if they are not present in that section."
        )

    if not context:
        context = "(no external context – rely on general knowledge, but obey the system note above)"

    prompt = f"""
    You are the final answer generator in a QA system that can use a document knowledge base and web search.

    {kb_status}

    Question:
    {user_q}

    Context:
    {context}

    Instructions:
    - Prefer to base your answer on the context when it is relevant.
    - If the context is empty or clearly unrelated, you may answer from your general knowledge.
    - However, if the question requires reading a specific user-provided document and there are no documents selected,
    clearly explain that you cannot access any document instead of guessing.
    - Never pretend to have read a document that does not appear in the context.
    """.strip()

    ans = answer_llm.invoke([HumanMessage(content=prompt)]).content

    return {
        **state,
        "messages": state["messages"] + [AIMessage(content=ans)],
    }


# =====================================================================
# GRAPH BUILD
# =====================================================================

def from_router(st: AgentState) -> Literal["rag", "web", "answer", "end"]:
    """Mapping route sau router -> node tiếp theo."""
    return st["route"]


def after_rag(st: AgentState) -> Literal["answer", "web"]:
    """Mapping route sau RAG -> answer hoặc web."""
    return st["route"]


def build_agent():
    """Khởi tạo và compile LangGraph agent."""
    g = StateGraph(AgentState)

    # Đăng ký node
    g.add_node("router", router_node)
    g.add_node("rag_lookup", rag_node)
    g.add_node("web_search", web_node)
    g.add_node("answer", answer_node)

    # Entry point
    g.set_entry_point("router")

    # Router -> next node
    g.add_conditional_edges(
        "router",
        from_router,
        {
            "rag": "rag_lookup",
            "web": "web_search",
            "answer": "answer",
            "end": END,
        },
    )

    # RAG -> answer / web
    g.add_conditional_edges(
        "rag_lookup",
        after_rag,
        {
            "answer": "answer",
            "web": "web_search",
        },
    )

    # Web luôn chuyển sang answer
    g.add_edge("web_search", "answer")

    # Answer là node cuối
    g.add_edge("answer", END)

    # Nếu sau này muốn checkpoint thì dùng:
    # return g.compile(checkpointer=MemorySaver())
    return g.compile()


rag_agent = build_agent()
