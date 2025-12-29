"""
Medical Gynecology Session Manager with Ollama Integration
"""
import json
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict, field
from enum import Enum


class SessionStatus(Enum):
    """Session status enumeration"""
    ACTIVE = "active"
    COMPLETED = "completed"
    SUSPENDED = "suspended"


@dataclass
class Message:
    """Message structure for conversation history"""
    role: str  # 'user' or 'assistant' or 'system'
    content: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class SessionState:
    """Complete session state for persistence"""
    session_id: str
    status: str
    patient_answers: Dict[str, Any]
    conversation_history: List[Dict[str, Any]]
    pregnancy_suspicion: bool
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str


class GynecologySession:
    """
    Manages gynecology consultation sessions with Ollama LLM integration.
    """

    def __init__(
        self,
        session_id: str,
        ollama_base_url: str = "http://localhost:11434",
        model_name: str = "gyn-assistant:latest",
        system_prompt: Optional[str] = None
    ):
        self.session_id = session_id
        self.ollama_base_url = ollama_base_url.rstrip("/")
        self.model_name = model_name

        # Session state
        self.status = SessionStatus.ACTIVE
        self.patient_answers: Dict[str, Any] = {}
        self.conversation_history: List[Message] = []
        self.pregnancy_suspicion = False

        # Metadata
        self.metadata = {"model": model_name, "ollama_url": self.ollama_base_url}
        self.created_at = datetime.utcnow().isoformat()
        self.updated_at = self.created_at

        # System prompt
        self.system_prompt = system_prompt or self._default_system_prompt()

        # Initialize conversation
        self._initialize_conversation()


    def _default_system_prompt(self) -> str:
        return """
            شما یک دستیار پزشکی زنان حرفه‌ای هستید که به زبان فارسی با بیمار گفتگو می‌کنید.

            وظایف شما:
            1. تنها یک سوال در هر مرحله مطرح کنید.
            2. ترتیب جمع‌آوری شرح حال را رعایت کنید: 
            - سن و مشخصات پایه
            - مشکل اصلی و علائم
            - سابقه قاعدگی و بارداری
            - روش‌های پیشگیری، داروها و بیماری‌های زمینه‌ای
            - جراحی‌ها و حساسیت‌ها
            3. سوالات باید واضح، محترمانه و به زبان فارسی باشند.
            4. هیچ تشخیص یا درمان قطعی ارائه ندهید.
            5. اگر پاسخ‌ها احتمال بارداری بدهند، ادامه دهید اما نتیجه‌گیری نکنید.
            6. همیشه هر پیام یک سوال مشخص و کوتاه داشته باشد.

            قوانین اضافی:
            - از زبان رسمی و محترمانه استفاده کنید.
            - پیام‌ها کوتاه و قابل فهم باشند.
            - در پایان هر پاسخ، یک سوال بعدی برای ادامه شرح حال بپرسید.
            - از ارائه توضیحات اضافی پزشکی خارج از سوال پرهیز کنید.
            """




    def _call_ollama(self, user_message: str) -> Optional[str]:
        """
        Make a REST API call to Ollama /api/chat.
        """
        url = f"{self.ollama_base_url}/api/chat"

        messages = []

        # ✅ system prompt first
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})

        # conversation history
        for msg in self.conversation_history:
            # system پیام‌های تکراری نفرستیم (ما فقط یکی اول می‌فرستیم)
            if msg.role == "system":
                continue
            messages.append({"role": msg.role, "content": msg.content})

        if user_message:
            messages.append({"role": "user", "content": user_message})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.4, "top_p": 0.9}
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            result = response.json()

            assistant_message = result.get("message", {}).get("content", "")
            assistant_message = (assistant_message or "").strip()

            return assistant_message if assistant_message else None

        except requests.exceptions.RequestException as e:
            print(f"Error calling Ollama API: {e}")
            return None

    def _initialize_conversation(self) -> None:
        opening = self._call_ollama(
            "Start the consultation with a polite greeting and ask the chief complaint."
        )
        if opening:
            self._add_message("assistant", opening)

    def _add_message(self, role: str, content: str) -> None:
        msg = Message(role=role, content=content)
        self.conversation_history.append(msg)
        self.updated_at = datetime.utcnow().isoformat()

    def _validate_age(self, answer: str) -> Optional[str]:
        try:
            year = int(answer.strip())
            current_year = datetime.utcnow().year
            age = current_year - year

            from app.config.settings import MIN_GYNECOLOGY_AGE
            if age < MIN_GYNECOLOGY_AGE:
                self.status = SessionStatus.SUSPENDED
                return "با توجه به سن بیمار، این نوع ویزیت نیازمند بررسی و ارجاع حضوری توسط پزشک متخصص است."
        except ValueError:
            pass
        return None

    def submit_answer(self, question_key: str, answer: str) -> Optional[str]:
        if self.status != SessionStatus.ACTIVE:
            raise ValueError(f"Session is not active. Status: {self.status.value}")

        # Store the answer
        self.patient_answers[question_key] = {
            "answer": answer,
            "timestamp": datetime.utcnow().isoformat()
        }

        # ✅ pregnancy detection AFTER storing answer
        self._detect_pregnancy()

        # Age validation (only once)
        if question_key.lower().startswith("q") and not self.patient_answers.get("_age_checked"):
            age_warning = self._validate_age(answer)
            self.patient_answers["_age_checked"] = True
            if age_warning:
                self._add_message("assistant", age_warning)
                return age_warning

        # Add user message to history
        self._add_message("user", answer)

        # Ask next question
        next_question = self._call_ollama(
            "پاسخ بیمار ثبت شد. لطفاً سوال بعدی را طبق ترتیب شرح حال بپرس."
        )
        if next_question:
            self._add_message("assistant", next_question)

        self.updated_at = datetime.utcnow().isoformat()
        return next_question

    def get_current_question(self) -> Optional[str]:
        for msg in reversed(self.conversation_history):
            if msg.role == "assistant":
                return msg.content
        return None

    def complete_session(self) -> None:
        self.status = SessionStatus.COMPLETED
        self.updated_at = datetime.utcnow().isoformat()

    def suspend_session(self) -> None:
        self.status = SessionStatus.SUSPENDED
        self.updated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "patient_answers": self.patient_answers,
            "conversation_history": [asdict(msg) for msg in self.conversation_history],
            "pregnancy_suspicion": self.pregnancy_suspicion,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    def to_json(self) -> str:
        state = SessionState(
            session_id=self.session_id,
            status=self.status.value,
            patient_answers=self.patient_answers,
            conversation_history=[asdict(msg) for msg in self.conversation_history],
            pregnancy_suspicion=self.pregnancy_suspicion,
            metadata=self.metadata,
            created_at=self.created_at,
            updated_at=self.updated_at
        )
        return json.dumps(asdict(state), indent=2, ensure_ascii=False)

    def save_to_file(self, filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_json())

    @classmethod
    def load_from_file(cls, filepath: str, ollama_base_url: str = "http://localhost:11434") -> "GynecologySession":
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data, ollama_base_url)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], ollama_base_url: str = "http://localhost:11434") -> "GynecologySession":
        session = cls(
            session_id=data["session_id"],
            ollama_base_url=ollama_base_url,
            model_name=data.get("metadata", {}).get("model", "gemma3-medical"),
            system_prompt=None
        )

        session.status = SessionStatus(data.get("status", SessionStatus.ACTIVE.value))
        session.patient_answers = data.get("patient_answers", {})

        # ✅ restore conversation history correctly
        raw_hist = data.get("conversation_history", [])
        session.conversation_history = []
        for item in raw_hist:
            if isinstance(item, dict) and "role" in item and "content" in item:
                session.conversation_history.append(
                    Message(
                        role=item["role"],
                        content=item["content"],
                        timestamp=item.get("timestamp", datetime.utcnow().isoformat())
                    )
                )

        session.pregnancy_suspicion = bool(data.get("pregnancy_suspicion", False))
        session.metadata = data.get("metadata", session.metadata)
        session.created_at = data.get("created_at", session.created_at)
        session.updated_at = data.get("updated_at", session.updated_at)

        return session

    def _detect_pregnancy(self) -> None:
        answers_text = " ".join(
            v.get("answer", "") for v in self.patient_answers.values() if isinstance(v, dict)
        )

        from app.config.settings import PREGNANCY_RULES

        symptoms_found = any(
            symptom in answers_text for symptom in PREGNANCY_RULES.get("required_symptoms", [])
        )
        months_found = any(word in answers_text for word in ["2 ماه", "3 ماه", "سه ماه", "دو ماه"])

        if symptoms_found and months_found:
            self.pregnancy_suspicion = True

    def switch_model(self, new_model_name: str) -> None:
        self.model_name = new_model_name
        self.metadata["model"] = new_model_name
        self.metadata["model_switched_at"] = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow().isoformat()
