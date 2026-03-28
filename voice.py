import os
import asyncio
import wave
import tempfile
from piper import PiperVoice, SynthesisConfig

voices = {}
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

def load_piper_model(filename):
    # Try models folder first, then BASE_DIR
    for d in [MODELS_DIR, BASE_DIR]:
        path = os.path.join(d, filename)
        if os.path.exists(path):
            print(f"Loading Piper Voice model: {path}")
            return PiperVoice.load(path)
    return None

try:
    en_voice = load_piper_model("en_GB-semaine-medium.onnx")
    if en_voice: voices["English"] = en_voice
except Exception as e:
    print(f"Failed to load English Voice: {e}")

try:
    vi_voice = load_piper_model("vi_VN-vais1000-medium.onnx")
    if vi_voice: voices["Vietnamese"] = vi_voice
except Exception as e:
    print(f"Failed to load Vietnamese Voice: {e}")

if not voices:
    print("WARNING: No Piper models found! TTS will fail.")

async def generate_audio_file(text: str, language: str = "Vietnamese") -> str:
    text = text.strip() if text else ""
    if not text:
        raise Exception("Bỏ qua TTS: Chuỗi văn bản rỗng.")
        
    voice = voices.get(language, voices.get("Vietnamese") or voices.get("English"))
    if not voice:
        raise Exception(f"Piper TTS model not loaded for {language}. Please download the .onnx models.")

    def sync_generate():
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            path = tmp_file.name

        with wave.open(path, 'wb') as wav_file:
            syn_config = SynthesisConfig(length_scale=1.2)
            voice.synthesize_wav(text, wav_file, syn_config=syn_config)

        return path
    return await asyncio.to_thread(sync_generate)
