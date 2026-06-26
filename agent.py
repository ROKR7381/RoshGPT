import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
import certifi
from tools import tools

load_dotenv()

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()


from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.sqlite import SqliteSaver

Path("data").mkdir(exist_ok=True)

AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o")
AZURE_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")

OPENAI_FALLBACK_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

AZURE_AVAILABLE = bool(AZURE_ENDPOINT and AZURE_API_KEY)

ALLOWED_MODELS = {
    'gpt-4o-mini',
    'gpt-4o',
    'gpt-4-turbo',
    'gpt-4',
    'gpt-3.5-turbo',
    'o1-mini',
    'o1-preview',
}


SYSTEM_PROMPT = """
You are a helpful Agentic AI assistant named BappyGPT similar to ChatGPT.

You can:
1. Answer normal questions.
2. Use tools when needed.
3. Search uploaded documents using the RAG tool.
4. Search the web for latest/current information using Tavily Search.
5. Remember important user information using the memory tool.
6. Recall memory when useful.
7. Use calculator for math.
8. Execute Python code for programming tasks.
9. Search Wikipedia for encyclopedic information.
10. Search latest news using NewsAPI.
11. Conduct BPSC/UPPCS quiz practice with MCQ questions.

Rules:
- If the user asks about latest news, current events, recent updates, today's information, current prices, current people, current versions, new releases, or anything time-sensitive, use Tavily Search or search_news.
- If the user asks about an uploaded document, use search_uploaded_documents.
- If the user asks you to remember something, use remember_this.
- If the user asks about previous preferences or saved facts, use recall_memory.
- Use calculator for math questions.
- Use execute_python for any coding, programming, or data analysis tasks.
- Use search_wikipedia for facts, definitions, history, science, or encyclopedic topics.
- When using web search, summarize clearly and mention that the answer is based on web search results.

QUIZ MODE RULES:
- If user says "practice questions", "take quiz", "start MCQ", "I need N questions", "quiz", "BPSC practice", "UPPCS practice" → use start_quiz tool.
- If quiz is active and user sends a number (1-4) → use submit_quiz_answer tool.
- If quiz is active, do NOT answer general questions — continue the quiz.
- After each answer, show if correct/wrong with explanation, then show next question.
- After quiz ends, show final score and detailed review.
- If user says "end quiz" or "show results" → use get_quiz_results tool.
- Available topics: mixed, indian_history, bihar_history, geography, bihar_geography, polity, economy, science, current_affairs, bihar_specific.

Be clear, helpful, and concise.
"""

def normalize_model_name(model_name: str | None) -> str:
    """
    Validate selected model from frontend.
    If model is missing or not allowed, fallback to OPENAI_FALLBACK_MODEL.
    """

    if not model_name:
        return OPENAI_FALLBACK_MODEL

    model_name = model_name.strip()

    if model_name not in ALLOWED_MODELS:
        return OPENAI_FALLBACK_MODEL

    return model_name


def build_llm(model_name: str):
    """
    Try Azure OpenAI first (using configured deployment).
    If Azure is not available or fails, fallback to direct OpenAI API.
    """

    selected_model = normalize_model_name(model_name)

    if AZURE_AVAILABLE:
        try:
            llm = AzureChatOpenAI(
                azure_deployment=AZURE_DEPLOYMENT,
                api_version=AZURE_API_VERSION,
                azure_endpoint=AZURE_ENDPOINT,
                api_key=AZURE_API_KEY,
                temperature=0.3,
                streaming=True,
            )
            llm.invoke("ping")
            print(f"[RoshGPT] Using Azure OpenAI deployment: {AZURE_DEPLOYMENT}")
            return llm
        except Exception as e:
            print(f"[RoshGPT] Azure OpenAI failed ({e}), falling back to OpenAI...")

    print(f"[RoshGPT] Using OpenAI model: {selected_model}")
    return ChatOpenAI(
        model=selected_model,
        temperature=0.3,
        streaming=True,
    )


def build_agent(model_name: str):
    """
    Build one LangGraph agent with Azure OpenAI (primary) or OpenAI (fallback).
    """

    llm = build_llm(model_name)
    llm_with_tools = llm.bind_tools(tools)

    def chatbot_node(state: MessagesState):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]

        response = llm_with_tools.invoke(messages)

        return {
            "messages": [response]
        }

    tool_node = ToolNode(tools)

    workflow = StateGraph(MessagesState)

    workflow.add_node("chatbot", chatbot_node)
    workflow.add_node("tools", tool_node)

    workflow.add_edge(START, "chatbot")
    workflow.add_conditional_edges("chatbot", tools_condition)
    workflow.add_edge("tools", "chatbot")

    conn = sqlite3.connect(
        "data/langgraph_checkpoints.sqlite",
        check_same_thread=False
    )

    checkpointer = SqliteSaver(conn)

    return workflow.compile(checkpointer=checkpointer)


_AGENT_CACHE = {}


def get_agent(model_name: str | None = None):
    """
    Return cached LangGraph agent for selected model.
    If not created yet, create it once and reuse it.
    """

    selected_model = normalize_model_name(model_name)

    if selected_model not in _AGENT_CACHE:
        _AGENT_CACHE[selected_model] = build_agent(selected_model)

    return _AGENT_CACHE[selected_model]



