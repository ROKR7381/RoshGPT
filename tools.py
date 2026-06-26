import math
import os
import io
import sys
import warnings
import subprocess
import tempfile
import requests
import certifi
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from database import save_memory, search_memory
from rag import retrieve_from_rag
from quiz_manager import quiz_manager

warnings.filterwarnings("ignore", message="Unverified HTTPS request")


load_dotenv()


CURRENT_THREAD_ID = "default"


def set_current_thread_id(thread_id: str):
    global CURRENT_THREAD_ID
    CURRENT_THREAD_ID = thread_id


web_search = TavilySearch(
    max_results=5,
    topic="general",
    search_depth="advanced"
)


@tool
def calculator(expression: str) -> str:
    """
    Useful for simple math calculations.
    Input should be a valid math expression.
    Example: 2 + 2, math.sqrt(16), 10 * 5
    """

    try:
        allowed = {
            "math": math,
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum
        }

        result = eval(expression, {"__builtins__": {}}, allowed)
        return str(result)

    except Exception as e:
        return f"Calculation error: {str(e)}"


@tool
def search_uploaded_documents(query: str) -> str:
    """
    Search uploaded documents for relevant information.
    Use this when the user asks about uploaded PDFs, DOCX, TXT, notes, files, or documents.
    """

    return retrieve_from_rag(
        query=query,
        thread_id=CURRENT_THREAD_ID
    )


@tool
def remember_this(memory: str) -> str:
    """
    Save an important user preference or fact into long-term memory.
    Use this when the user asks you to remember something.
    """

    return save_memory(
        thread_id=CURRENT_THREAD_ID,
        memory=memory
    )


@tool
def recall_memory(query: str) -> str:
    """
    Recall saved long-term memories about the user or this conversation.
    """

    return search_memory(
        thread_id=CURRENT_THREAD_ID,
        query=query
    )


NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")


@tool
def search_news(query: str) -> str:
    """
    Search latest news articles by topic or keyword.
    Use this when the user asks about current events, breaking news, or recent headlines.
    """

    if not NEWSAPI_KEY:
        return "NewsAPI key not configured. Please set NEWSAPI_KEY in .env."

    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "apiKey": NEWSAPI_KEY,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 5
        }

        try:
            response = requests.get(url, params=params, timeout=10, verify=certifi.where())
        except requests.exceptions.SSLError:
            response = requests.get(url, params=params, timeout=10, verify=False)
        data = response.json()

        if data.get("status") != "ok":
            return f"NewsAPI error: {data.get('message', 'Unknown error')}"

        articles = data.get("articles", [])

        if not articles:
            return f"No news found for: {query}"

        results = []
        for i, article in enumerate(articles, start=1):
            title = article.get("title", "No title")
            source = article.get("source", {}).get("name", "Unknown")
            description = article.get("description", "No description")
            url_link = article.get("url", "")
            published = article.get("publishedAt", "")[:10]

            results.append(
                f"[{i}] {title}\n"
                f"    Source: {source} | Date: {published}\n"
                f"    {description}\n"
                f"    Link: {url_link}"
            )

        return "\n\n".join(results)

    except Exception as e:
        return f"News search error: {str(e)}"


@tool
def search_wikipedia(query: str) -> str:
    """
    Search Wikipedia for articles matching a query.
    Returns summaries of up to 3 relevant articles.
    Use this when the user asks about facts, definitions, history, science, people, or any encyclopedic topic.
    """

    headers = {"User-Agent": "RoshGPT/1.0 (https://github.com/RoshGPT; roshgpt@example.com) requests"}

    try:
        search_url = "https://en.wikipedia.org/w/api.php"
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": 3,
            "format": "json"
        }

        try:
            search_resp = requests.get(search_url, params=search_params, headers=headers, timeout=10, verify=certifi.where())
        except requests.exceptions.SSLError:
            search_resp = requests.get(search_url, params=search_params, headers=headers, timeout=10, verify=False)

        search_data = search_resp.json()
        results_list = search_data.get("query", {}).get("search", [])

        if not results_list:
            return f"No Wikipedia articles found for: {query}"

        summaries = []
        for item in results_list:
            title = item.get("title", "")
            snippet = item.get("snippet", "").replace('<span class="searchmatch">', "").replace("</span>", "")

            try:
                summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
                try:
                    summary_resp = requests.get(summary_url, headers=headers, timeout=10, verify=certifi.where())
                except requests.exceptions.SSLError:
                    summary_resp = requests.get(summary_url, headers=headers, timeout=10, verify=False)

                summary_data = summary_resp.json()
                extract = summary_data.get("extract", snippet)
                page_url = summary_data.get("content_urls", {}).get("desktop", {}).get("page", f"https://en.wikipedia.org/wiki/{title}")
            except Exception:
                extract = snippet
                page_url = f"https://en.wikipedia.org/wiki/{title}"

            summaries.append(
                f"[{title}]\n"
                f"{extract[:500]}...\n"
                f"Link: {page_url}"
            )

        return "\n\n".join(summaries)

    except Exception as e:
        return f"Wikipedia search error: {str(e)}"


@tool
def execute_python(code: str) -> str:
    """
    Execute Python code and return the output.
    Use this for running code, testing algorithms, data analysis, file processing,
    debugging, or any programming task. The code runs in a safe sandbox with a 15-second timeout.
    You can use print() to see output, or the last expression value is returned.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=tempfile.gettempdir()
        )

        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            if output:
                output += "\n"
            output += result.stderr

        if not output.strip():
            output = "(No output)"

        if len(output) > 3000:
            output = output[:3000] + "\n... (output truncated)"

        return output

    except subprocess.TimeoutExpired:
        return "Code execution timed out (15s limit). Try simplifying the code."
    except Exception as e:
        return f"Execution error: {str(e)}"


@tool
def start_quiz(exam_type: str, question_count: int, topic: str = "mixed") -> str:
    """
    Start a quiz with MCQ questions from BPSC previous year papers.
    Use this when user wants to practice questions, take a quiz, or wants MCQs.

    Args:
        exam_type: Type of exam (bpsc, uppcs, general)
        question_count: Number of questions (1-50)
        topic: Topic for questions (mixed, indian_history, bihar_history, geography, bihar_geography, polity, economy, science, current_affairs, bihar_specific)
    """
    result = quiz_manager.start_quiz(
        thread_id=CURRENT_THREAD_ID,
        exam_type=exam_type,
        topic=topic,
        count=question_count
    )

    if "error" in result:
        return result["error"]

    q = result["question"]
    if not q:
        return "Failed to start quiz. No questions available."

    options_text = "\n".join([f"  {i+1}. {opt}" for i, opt in enumerate(q["options"])])

    return (
        f"Quiz started! {result['message']}\n\n"
        f"Q{q['question_number']}/{q['total_questions']} [{q['topic'].upper()}]\n\n"
        f"{q['question']}\n\n"
        f"{options_text}\n\n"
        f"Score: {q['score']}/{q['answered_so_far']} | Reply with option number (1-4)"
    )


@tool
def submit_quiz_answer(selected_option: int) -> str:
    """
    Submit answer for current quiz question.
    Use this when a quiz is active and user sends a number (1-4) as answer.

    Args:
        selected_option: Option number (1-4)
    """
    if selected_option < 1 or selected_option > 4:
        return "Please select a valid option (1-4)."

    result = quiz_manager.submit_answer(CURRENT_THREAD_ID, selected_option)

    if "error" in result:
        return result["error"]

    feedback = "Correct!" if result["is_correct"] else "Wrong!"
    explanation = result.get("explanation", "")

    if result["quiz_completed"]:
        score = result["score"]
        total = result["total"]
        percentage = round((score / total) * 100, 1) if total > 0 else 0

        return (
            f"{feedback} Correct answer: {result['correct_answer']}\n"
            f"Explanation: {explanation}\n\n"
            f"Quiz Complete!\n"
            f"Score: {score}/{total} ({percentage}%)\n\n"
            f"Start a new quiz by saying 'Start a new quiz' or ask for more questions."
        )

    q = result["next_question"]
    options_text = "\n".join([f"  {i+1}. {opt}" for i, opt in enumerate(q["options"])])

    return (
        f"{feedback} Correct answer: {result['correct_answer']}\n"
        f"Explanation: {explanation}\n\n"
        f"Q{q['question_number']}/{q['total_questions']} [{q['topic'].upper()}]\n\n"
        f"{q['question']}\n\n"
        f"{options_text}\n\n"
        f"Score: {result['score']}/{result['current_question']} | Reply with option number (1-4)"
    )


@tool
def get_quiz_results() -> str:
    """
    Get current quiz results or status.
    Use this when user asks about quiz score, results, or wants to end the quiz.
    """
    status = quiz_manager.get_status(CURRENT_THREAD_ID)

    if not status.get("active"):
        results = quiz_manager.get_results(CURRENT_THREAD_ID)
        if "error" in results:
            return "No quiz session found. Start a new quiz first."

        score = results["score"]
        total = results["total"]
        percentage = results["percentage"]

        review_lines = []
        for i, ans in enumerate(results["answers"], 1):
            mark = "Correct" if ans["is_correct"] else "Wrong"
            review_lines.append(
                f"Q{i}: {mark} | Your: {ans['options'][ans['selected_option']]} | "
                f"Correct: {ans['options'][ans['correct_option']]}"
            )

        review = "\n".join(review_lines)

        return (
            f"Quiz Results ({results['exam_type'].upper()} - {results['topic']})\n\n"
            f"Score: {score}/{total} ({percentage}%)\n\n"
            f"Review:\n{review}\n\n"
            f"Start a new quiz by saying 'Start a new quiz'."
        )

    return (
        f"Quiz is active!\n"
        f"Progress: Q{status['current_question']}/{status['total_questions']}\n"
        f"Score: {status['score']}/{status['current_question']-1}\n\n"
        f"Continue answering or say 'End quiz' to see results."
    )


tools = [
    calculator,
    search_uploaded_documents,
    remember_this,
    recall_memory,
    web_search,
    search_news,
    search_wikipedia,
    execute_python,
    start_quiz,
    submit_quiz_answer,
    get_quiz_results
]
