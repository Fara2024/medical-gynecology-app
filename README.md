# Medical Gynecology Consultation Application

AI-powered gynecology consultation system using Ollama and custom Gemma 3 model.

## Setup

1. **Install Ollama**
```bash
   # Visit https://ollama.ai to install
```

2. **Pull base model**
```bash
   ollama pull gemma3:latest and deepseek-r1:1.5b
```

3. **Create custom model**
```bash
   chmod +x scripts/setup_model.sh
   ./scripts/setup_model.sh
```

4. **Install Python dependencies**

```bash
   pip install -r requirements.txt
   python -3.13 -m venv gyn
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
├── main.py                                    ← main file
├── transfer_to_pregnancy.py                   ← ⭐ new file
├── requirements.txt
├── .env
│
├── app\
│   ├── __init__.py
│   │
│   ├── core\
│   │   ├── __init__.py
│   │   ├── gynecology_session.py             ← first file
│   │   └── pregnancy_session.py              ← second file(new)
│   │
│   ├── models\
│   │   ├── gynecology\
│   │   │   └── Modelfile                     ← gynecology model
│   │   │
│   │   └── pregnancy\
│   │       └── Modelfile                     ← pregnancy model(new)
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
── gui.py 
└── venv\
    └── ...
