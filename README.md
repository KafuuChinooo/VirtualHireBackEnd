# VirtuHire AI Backend

Đây là máy chủ back-end (FastAPI) phục vụ cho hệ thống Interview Simulator (Phỏng vấn ảo). Khối AI này có nhiệm vụ nhận và xử lý giọng nói, tạo ra các phản hồi thông minh thông qua LLM, sau đó tổng hợp lại thành giọng nói để trả về cho Client (Unity/Web).

## 🚀 Các Tính Năng Cốt Lõi

1. **Speech-to-Text (STT)**: Chuyển đổi tệp thu âm (WAV) từ người dùng thành văn bản, sử dụng mô hình [faster-whisper](https://github.com/SYSTRAN/faster-whisper) chạy hoàn toàn offline cho tốc độ cao.
2. **Ngôn ngữ Lớn (LLM Chat)**: Quản lý hội thoại và xử lý logic phỏng vấn bằng **Google Gemini** (thông qua SDK `google-genai`), tự động sinh ra câu hỏi hoặc phản hồi phù hợp với ngữ cảnh job và thái độ ứng viên.
3. **Text-to-Speech (TTS)**: Tổng hợp câu trả lời văn bản thành giọng nói bằng **Piper TTS** chạy offline với tốc độ cực nhanh, hỗ trợ cả Tiếng Anh và Tiếng Việt.
4. **Quản lý Phiên & Logging**: Ghi chép lịch sử trò chuyện cục bộ (`chat_logs.json`) và có một Web UI nhỏ để các admin có thể can thiệp luồng phỏng vấn trực tiếp.

## 📂 Kiến Trúc Thư Mục

- `main.py`: Điểm vào (entry point) của API, định nghĩa các endpoint và kết nối các pipeline (STT -> LLM -> TTS).
- `llm_service.py`: Xử lý giao tiếp với Gemini API, khởi tạo lịch sử trò chuyện và cấu hình Prompt.
- `voice.py`: Quản lý việc nạp mô hình Piper, sinh ra file âm thanh `.wav` tạm thời từ văn bản.
- `prompt.py`: Lưu trữ các System Prompt định hình "tính cách" và "nhiệm vụ" của bot phỏng vấn viên.
- `models/`: Thư mục lưu trữ tĩnh các mô hình (ONNX) của Piper (ví dụ: `en_GB-semaine-medium.onnx`, `vi_VN-vais1000-medium.onnx`) và Whisper.
- `templates/`: Giao diện Web (HTML) có sẵn để xem / quản lý quá trình trò chuyện (Jinja2).

## ⚙️ Cài Đặt Khởi Chạy

1. **Môi trường**: Khuyến nghị sử dụng Python 3.10+ và tạo virtual environment.
   ```shell
   python -m venv venv
   source venv/bin/activate  # Hoặc venv\Scripts\activate trên Windows
   ```

2. **Cài đặt thư viện**:
   ```shell
   pip install -r requirements.txt
   ```

3. **Cấu hình API Key**:
   Tạo tệp `.env` ở thư mục gốc chứa biến môi trường cho Gemini API.
   ```env
   GEMINI_API_KEY=AIzaSy... (Khóa của bạn)
   ```

4. **Tải Audio Models**:
   Hãy chắc chắn rằng các model Piper (`.onnx` và `.onnx.json`) đã được tải xuống và thả đúng vào thư mục `models/` hoặc ngang hàng thư mục gốc.

5. **Chạy Server**:
   Sử dụng Uvicorn để khởi chạy FastAPI:
   ```shell
   uvicorn main:app --host 127.0.0.1 --port 8000 --reload --reload-exclude "chat_logs.json"
   ```
   *Dashboard kiểm thử có thể được truy cập tại: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)*

## 📡 API Endpoints Chính

- `POST /api/stt`: Gửi file `audio` dạng form-data để nhận lại chuỗi văn bản nhận diện được.
- `POST /api/chat`: Gửi Request chứa lịch sử và câu nói lấy về Text Answer.
- `POST /api/tts`: Gửi một nội dung văn bản để nhận về tệp âm thanh phản hồi.
- `POST /api/chat_voice`: (Endpoint tất-cả-trong-một) Nhận lịch sử tin nhắn dạng mô hình JSON -> Sinh câu trả lời mượt mà -> Lập tức tổng hợp giọng nói -> Trả về Client tệp `audio/wav` cùng Header `X-Transcript` chứa nội dung chữ.
