import json
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent import get_agent
from database import (
    init_db,
    create_or_update_conversation,
    list_conversations,
    save_chat_message,
    get_chat_history,
)
from rag import add_document_to_rag
from tools import set_current_thread_id

BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR / "frontend" / "dist"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


class ChatRequest(BaseModel):
    message: str
    thread_id: str
    model: str = "gpt-4o-mini"


@app.get("/api/conversations")
def get_conversations():
    conversations = list_conversations()
    return {
        "conversations": [
            {"thread_id": c.thread_id, "title": c.title}
            for c in conversations
        ]
    }


@app.get("/api/history/{thread_id}")
def get_history(thread_id: str):
    messages = get_chat_history(thread_id)
    return {
        "messages": [
            {"role": m.role, "content": m.content}
            for m in messages
        ]
    }


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    set_current_thread_id(req.thread_id)
    create_or_update_conversation(req.thread_id, req.message)
    save_chat_message(req.thread_id, "user", req.message)

    agent = get_agent(req.model)
    config = {"configurable": {"thread_id": req.thread_id}}

    async def event_generator():
        full_response = ""
        try:
            for chunk, metadata in agent.stream(
                {"messages": [{"role": "user", "content": req.message}]},
                config=config,
                stream_mode="messages",
            ):
                if chunk.content:
                    token = chunk.content
                    full_response += token
                    yield f"data: {json.dumps({'token': token})}\n\n"

            save_chat_message(req.thread_id, "assistant", full_response)
            yield f"data: {json.dumps({'done': True})}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), thread_id: str = Form(...)):
    allowed = {".pdf", ".docx", ".txt", ".md", ".py", ".csv"}
    suffix = Path(file.filename).suffix.lower()

    if suffix not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed)}",
        )

    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    try:
        result = add_document_to_rag(str(file_path), thread_id)
        create_or_update_conversation(thread_id, f"Uploaded {file.filename}")
        return {
            "success": True,
            "message": f"Uploaded '{result['filename']}' and created {result['chunks']} chunks.",
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


# Mount static assets BEFORE the catch-all
if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="static-assets")


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Catch-all: serve index.html for SPA routing."""
    file_path = DIST_DIR / full_path
    if file_path.is_file():
        return FileResponse(str(file_path))
    return FileResponse(str(DIST_DIR / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
