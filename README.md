# Medical Gynecology Consultation Application

AI-powered gynecology consultation system using Ollama and custom Gemma 3 model.

## Setup

1. **Install Ollama**
```bash
   # Visit https://ollama.ai to install
```

2. **Pull base model**
```bash
   ollama pull gemma2:2b
```

3. **Create custom model**
```bash
   chmod +x scripts/setup_model.sh
   ./scripts/setup_model.sh
```

4. **Install Python dependencies**
```bash
   pip install -r requirements.txt
```

5. **Run the application**
```bash
   python main.py
```

## Project Structure

- `app/core/gynecology_session.py` - Main session management class
- `app/models/Modelfile` - Ollama model configuration
- `data/sessions/` - Stored patient sessions
- `main.py` - Application entry point

## Usage
```python
from app.core.gynecology_session import GynecologySession

session = GynecologySession("patient_001")
next_q = session.submit_answer("q1", "I have irregular periods")
session.save_to_file("data/sessions/patient_001.json")
```


C:\Users\FARA\OneDrive\Desktop\medical-gynecology-app\
│
├── main.py                                    ← فایل اصلی
├── transfer_to_pregnancy.py                   ← ⭐ فایل جدید (اینجا)
├── requirements.txt
├── .env
│
├── app\
│   ├── __init__.py
│   │
│   ├── core\
│   │   ├── __init__.py
│   │   ├── gynecology_session.py             ← فایل اول شما
│   │   └── pregnancy_session.py              ← فایل دوم (جدید)
│   │
│   ├── models\
│   │   ├── gynecology\
│   │   │   └── Modelfile                     ← مدل زنان
│   │   │
│   │   └── pregnancy\
│   │       └── Modelfile                     ← مدل بارداری (جدید)
│   │
│   ├── api\
│   │   ├── __init__.py
│   │   └── routes.py
│   │
│   └── config\
│       ├── __init__.py
│       └── settings.py
│
├── data\
│   └── sessions\
│       ├── patient_001.json
│       ├── patient_002.json
│       └── ...
│
├── scripts\
│   └── setup_model.sh
│
└── venv\
    └── ...