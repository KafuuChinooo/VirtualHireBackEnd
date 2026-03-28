import os
import tempfile
import json
import time
import collections
import asyncio
import traceback
import urllib.parse
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.background import BackgroundTask
from pydantic import BaseModel

from faster_whisper import WhisperModel

# --- WORKAROUND: Thêm đường dẫn DLL của mini CUDA (cuBLAS/cuDNN) vào PATH ---
try:
    import nvidia
    nv_path = nvidia.__path__[0]
    cublas_dir = os.path.join(nv_path, "cublas", "bin")
    cudnn_dir = os.path.join(nv_path, "cudnn", "bin")
    os.environ["PATH"] = cublas_dir + os.pathsep + cudnn_dir + os.pathsep + os.environ.get("PATH", "")
    print(f"CUDA workaround loaded from: {cublas_dir}")
except Exception as e:
    print(f"Warning: Failed to load CUDA path: {e}")
# -----------------------------------------------------------------------------

from prompt import get_system_prompt
from voice import generate_audio_file
from llm_service import generate_chat_response, Message

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "chat_logs.json")

def append_to_log(job_title: str, session_id: str, role: str, message: str):
    log_entry = {
        "timestamp": time.time(),
        "job_title": job_title,
        "session_id": session_id,
        "role": role,
        "message": message
    }
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except:
        pass

# Load Whisper STT model 
models_dir = os.path.join(BASE_DIR, "models")
print(f"Loading Whisper STT model (small) into {models_dir}...")
stt_model = WhisperModel("small", device="auto", compute_type="float16", download_root=models_dir)
print("Whisper STT loaded!")

app = FastAPI(title="VirtuHire Assistant (Web)")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

class ChatRequest(BaseModel):
    message: str
    job_title: str | None = None
    interview_type: str = "Attitude Interview"
    language: str = "Vietnamese"
    history: list[Message] = []

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the web frontend UI."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/logs", response_class=HTMLResponse)
async def view_logs(request: Request):
    """Serve the logs viewer UI."""
    return templates.TemplateResponse("logs.html", {"request": request})

@app.get("/api/logs")
async def get_logs_endpoint():
    """Return all conversation logs."""
    if not os.path.exists(LOG_FILE):
        return {"logs": []}
    logs = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try: logs.append(json.loads(line))
                except: pass
    return {"logs": logs}

admin_messages_queue = collections.deque()

@app.post("/api/admin_message")
async def post_admin_message(request: Request):
    """Admin injects a message to rescue the STT session."""
    data = await request.json()
    msg = data.get("message", "").strip()
    if msg:
        admin_messages_queue.append(msg)
        print(f"[Admin Rescue] Đã đưa vào hàng chờ: {msg}")
    return {"status": "success", "queued": msg}

@app.get("/api/poll_admin_message")
async def poll_admin_message():
    """Unity polls this to get any injected admin messages."""
    if admin_messages_queue:
        return {"has_message": True, "message": admin_messages_queue.popleft()}
    return {"has_message": False, "message": ""}

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """Handle chat requests using Gemini API"""
    messages = []
    if req.job_title:
        sys_prompt = get_system_prompt(req.job_title, req.interview_type, req.language)
        messages.append({"role": "system", "content": sys_prompt})
        
    for msg in req.history:
        messages.append({"role": msg.role, "content": msg.content})
        
    messages.append({"role": "user", "content": req.message})
    return await generate_chat_response(messages)

class TTSRequest(BaseModel):
    text: str
    language: str = "Vietnamese"

@app.post("/api/tts")
async def tts_endpoint(req: TTSRequest):
    try:
        temp_path = await generate_audio_file(req.text, req.language)
        return FileResponse(temp_path, media_type="audio/wav", background=BackgroundTask(os.remove, temp_path))
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/stt")
async def stt_endpoint(audio: UploadFile = File(...)):
    """Nhận file WAV từ Unity, dùng Whisper chuyển text."""
    try:
        contents = await audio.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        def transcribe():
            try:
                start_stt = time.time()
                segments, _ = stt_model.transcribe(tmp_path, beam_size=5)
                result = " ".join(seg.text.strip() for seg in segments)
                print(f"[STT] Processing Time: {time.time() - start_stt:.3f} s")
                return result
            except Exception as inner_e:
                print(f"[STT] Transcribe error: {inner_e}")
                raise inner_e

        text = await asyncio.to_thread(transcribe)
        os.unlink(tmp_path)

        print(f"[STT] Transcribed: {text}")
        return JSONResponse({"text": text.strip()})
    except Exception as e:
        print(f"[STT] Endpoint Error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/chat_voice")
async def chat_voice_endpoint(req: ChatRequest):
    """Handle chat requests and directly return TTS audio!"""
    print(f"\n[API] Bắt đầu nhận request /api/chat_voice!")
    print(f"[API] Tin nhắn từ người dùng: {req.message}")
    
    messages = []
    if req.job_title:
        sys_prompt = get_system_prompt(req.job_title, req.interview_type, req.language)
        messages.append({"role": "system", "content": sys_prompt})
        
    for msg in req.history:
        messages.append({"role": msg.role, "content": msg.content})
        
    messages.append({"role": "user", "content": req.message})
    
    print("[API] Đang chờ AI Gemini xử lý...")
    chat_response = await generate_chat_response(messages)
    
    if "error" in chat_response:
        print(f"[API] Lỗi từ Gemini: {chat_response['error']}")
        return {"error": chat_response["error"]}
        
    ai_text = chat_response.get("response", "")
    
    # Text is guaranteed to be conversational string!
    print(f"[API] AI đã trả lời xong:\n------------------\n{ai_text}\n------------------")
    print(f"[API] Đang bắt đầu gửi cho Piper tạo giọng nói...")
    
    # Ghi lại log
    session_id = f"{req.job_title}_{req.language}" if req.job_title else "general"
    append_to_log(req.job_title or "No Title", session_id, "user", req.message)
    append_to_log(req.job_title or "No Title", session_id, "assistant", ai_text)

    try:
        temp_path = await generate_audio_file(ai_text, language=req.language)
        print(f"[API] Đã tạo xong file âm thanh! Đang trả về Unity...")
        
        # Add background task to automatically delete .wav after sending to prevent disk full!
        response = FileResponse(temp_path, media_type="audio/wav", background=BackgroundTask(os.remove, temp_path))
        response.headers["X-Transcript"] = urllib.parse.quote(ai_text)
        response.headers["Access-Control-Expose-Headers"] = "X-Transcript"
        return response
    except Exception as e:
        print(f"[API] Lỗi quá trình tạo âm thanh TTS: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    # Use reload_excludes to prevent server looping from log updates
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True, reload_excludes=["chat_logs.json"])