import os
import time
import re
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=GEMINI_API_KEY)

GEMINI_MODEL = "gemini-3.1-flash-lite-preview"

class Message(BaseModel):
    role: str
    content: str

def _build_gemini_history(messages: list[dict]):
    system_instruction = None
    history = []
    user_message = ""

    for msg in messages:
        role = msg["role"]
        content = msg["content"]

        if role == "system":
            system_instruction = content
        elif role == "user":
            history.append(types.Content(role="user", parts=[types.Part(text=content)]))
            user_message = content
        elif role == "assistant":
            history.append(types.Content(role="model", parts=[types.Part(text=content)]))

    if history and history[-1].role == "user":
        history.pop()

    return system_instruction, history, user_message

async def generate_chat_response(messages: list[dict]) -> dict:
    try:
        start_time = time.time()
        system_instruction, history, user_message = _build_gemini_history(messages)

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.7,
        )

        chat = client.aio.chats.create(
            model=GEMINI_MODEL,
            config=config,
            history=history,
        )

        response = await chat.send_message(user_message)
        elapsed_time = time.time() - start_time
        print(f"[DEBUG] Gemini {GEMINI_MODEL} responded in {elapsed_time:.2f} seconds.")

        # Conversational Cleanup (ONLY for short conversational texts)
        final_text = response.text
        final_text = final_text.replace('**', '').replace('*', '').replace('_', '').replace('#', '').strip()
        final_text = re.sub(r'[^\x00-\x7F]+', ' ', final_text) # removes non-ascii if necessary, but vietnamese needs ascii? NO! 
        # Wait, if we use Vietnamese, removing non-ascii WILL DESTROY it!
        
        # Let's fix the regex rule to allow Vietnamese!
        # Actually just don't do regex cleanup, let Piper TTS handle it.
        final_text = response.text.replace('**', '').replace('*', '').replace('_', '').replace('#', '').strip()

        return {"response": final_text, "role": "assistant"}

    except Exception as e:
        return {"error": str(e)}
