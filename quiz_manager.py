import json
import random
from pathlib import Path
from datetime import datetime
from typing import Optional


QUIZ_DIR = Path(__file__).parent / "data" / "quiz"


def load_all_questions() -> list:
    """Load all questions from all JSON files in the quiz directory."""
    questions = []
    for file_path in QUIZ_DIR.glob("*.json"):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            questions.extend(data)
    return questions


def get_questions_by_topic(topic: str) -> list:
    """Get questions filtered by topic."""
    all_questions = load_all_questions()
    if topic == "mixed":
        return all_questions
    return [q for q in all_questions if q.get("topic") == topic]


def get_questions_by_difficulty(difficulty: str) -> list:
    """Get questions filtered by difficulty."""
    all_questions = load_all_questions()
    if difficulty == "mixed":
        return all_questions
    return [q for q in all_questions if q.get("difficulty") == difficulty]


class QuizSession:
    def __init__(self, thread_id: str, exam_type: str = "bpsc", topic: str = "mixed", count: int = 10):
        self.thread_id = thread_id
        self.exam_type = exam_type
        self.topic = topic
        self.count = min(count, 50)
        self.current_index = 0
        self.score = 0
        self.user_answers = []
        self.status = "active"
        self.created_at = datetime.utcnow()

        all_questions = get_questions_by_topic(topic)
        random.shuffle(all_questions)
        self.questions = all_questions[:self.count]

    def get_current_question(self) -> Optional[dict]:
        """Return current question with options."""
        if self.current_index >= len(self.questions) or self.status == "completed":
            return None

        q = self.questions[self.current_index]
        return {
            "question_id": q["id"],
            "question_number": self.current_index + 1,
            "total_questions": len(self.questions),
            "question": q["question"],
            "options": q["options"],
            "topic": q.get("topic", "general"),
            "difficulty": q.get("difficulty", "medium"),
            "source": q.get("source", ""),
            "score": self.score,
            "answered_so_far": len(self.user_answers)
        }

    def submit_answer(self, question_id: str, selected_option: int) -> dict:
        """Submit answer and return result."""
        if self.status == "completed":
            return {"error": "Quiz is already completed"}

        if self.current_index >= len(self.questions):
            return {"error": "No more questions"}

        q = self.questions[self.current_index]
        is_correct = selected_option == q["answer"]

        if is_correct:
            self.score += 1

        self.user_answers.append({
            "question_id": q["id"],
            "question": q["question"],
            "selected_option": selected_option,
            "correct_option": q["answer"],
            "is_correct": is_correct,
            "options": q["options"],
            "explanation": q.get("explanation", "")
        })

        self.current_index += 1

        if self.current_index >= len(self.questions):
            self.status = "completed"
            return {
                "is_correct": is_correct,
                "correct_answer": q["options"][q["answer"]],
                "explanation": q.get("explanation", ""),
                "quiz_completed": True,
                "score": self.score,
                "total": len(self.questions)
            }

        next_q = self.get_current_question()
        return {
            "is_correct": is_correct,
            "correct_answer": q["options"][q["answer"]],
            "explanation": q.get("explanation", ""),
            "quiz_completed": False,
            "next_question": next_q,
            "score": self.score,
            "current_question": self.current_index + 1,
            "total_questions": len(self.questions)
        }

    def get_results(self) -> dict:
        """Return final quiz results."""
        return {
            "score": self.score,
            "total": len(self.questions),
            "percentage": round((self.score / len(self.questions)) * 100, 1) if self.questions else 0,
            "answers": self.user_answers,
            "exam_type": self.exam_type,
            "topic": self.topic,
            "status": self.status
        }


class QuizManager:
    def __init__(self):
        self.sessions: dict[str, QuizSession] = {}

    def start_quiz(self, thread_id: str, exam_type: str = "bpsc", topic: str = "mixed", count: int = 10) -> dict:
        """Start a new quiz session."""
        session = QuizSession(thread_id, exam_type, topic, count)
        self.sessions[thread_id] = session

        first_question = session.get_current_question()
        return {
            "status": "started",
            "message": f"Quiz started! {len(session.questions)} questions on '{topic}' topic.",
            "question": first_question
        }

    def submit_answer(self, thread_id: str, selected_option: int) -> dict:
        """Submit answer for current question."""
        session = self.sessions.get(thread_id)
        if not session:
            return {"error": "No active quiz. Start a new quiz first."}

        if session.status == "completed":
            return {"error": "Quiz already completed. Start a new quiz."}

        if session.current_index >= len(session.questions):
            return {"error": "No more questions available."}

        current_q = session.questions[session.current_index]
        return session.submit_answer(current_q["id"], selected_option)

    def get_status(self, thread_id: str) -> dict:
        """Check if quiz is active."""
        session = self.sessions.get(thread_id)
        if not session:
            return {"active": False}

        return {
            "active": session.status == "active",
            "current_question": session.current_index + 1,
            "total_questions": len(session.questions),
            "score": session.score,
            "status": session.status
        }

    def get_results(self, thread_id: str) -> dict:
        """Get quiz results."""
        session = self.sessions.get(thread_id)
        if not session:
            return {"error": "No quiz session found"}

        return session.get_results()

    def end_quiz(self, thread_id: str) -> dict:
        """End current quiz."""
        session = self.sessions.get(thread_id)
        if not session:
            return {"error": "No active quiz"}

        session.status = "completed"
        return session.get_results()


quiz_manager = QuizManager()
