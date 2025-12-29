"""
Pregnancy Session Manager - Specialized Module for Pregnancy Cases
"""
import json
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict, field
from enum import Enum


class PregnancyStatus(Enum):
    SUSPECTED = "suspected"
    CONFIRMED = "confirmed"
    RULED_OUT = "ruled_out"
    NEEDS_TESTING = "needs_testing"


@dataclass
class PregnancyData:
    lmp: Optional[str] = None
    gestational_age: Optional[int] = None
    beta_hcg: Optional[float] = None
    ultrasound_findings: Optional[str] = None
    risk_factors: List[str] = field(default_factory=list)
    symptoms: List[str] = field(default_factory=list)


class PregnancySession:
    """
    Pregnancy consultation session (Ollama-based)
    """

    def __init__(
        self,
        session_id: str,
        gynecology_session_data: Optional[Dict] = None,
        ollama_base_url: str = "http://localhost:11434",
        pregnancy_model: str = "pregnancy-assistant:latest"
    ):
        self.session_id = session_id
        self.ollama_base_url = ollama_base_url.rstrip("/")
        self.pregnancy_model = pregnancy_model

        self.status = PregnancyStatus.SUSPECTED
        self.pregnancy_data = PregnancyData()
        self.conversation_history: List[Dict[str, Any]] = []

        self.metadata = {
            "model": pregnancy_model,
            "transferred_from": None,
            "source_session_id": None
        }

        self.created_at = datetime.utcnow().isoformat()
        self.updated_at = self.created_at

        self.system_prompt = self._pregnancy_system_prompt()

        if gynecology_session_data:
            self._import_from_gynecology(gynecology_session_data)

    # --------------------------------------------------
    def _pregnancy_system_prompt(self) -> str:
        return (
            "شما یک متخصص بارداری و زایمان هستید.\n\n"
            "قوانین:\n"
            "- همیشه فارسی پاسخ دهید\n"
            "- یک سوال در هر پیام\n"
            "- تشخیص قطعی ندهید\n"
            "- لحن دلسوزانه و حرفه‌ای\n\n"
            "در پایان اضافه کنید:\n"
            "✍️ نظر متخصص بارداری و زایمان:\n"
            "(پزشک تشخیص نهایی را وارد می‌کند)"
        )

    # --------------------------------------------------
    def _import_from_gynecology(self, gyn_data: dict) -> None:
        """
        دریافت و پردازش داده از gynecology_session
        """
        print(f"📥 دریافت داده از جلسه زنان...")

        self.metadata["transferred_from"] = "gynecology_session"
        self.metadata["source_session_id"] = gyn_data.get("session_id")

        patient_answers = gyn_data.get("patient_answers", {})
        for key, value in patient_answers.items():
            answer_text = value.get("answer", "") if isinstance(value, dict) else str(value)
            answer_lower = answer_text.lower()

            # شناسایی LMP
            if "lmp" in key.lower() or "قاعدگی" in answer_text:
                self.pregnancy_data.lmp = answer_text

            # شناسایی علائم بارداری
            pregnancy_symptoms = ["تهوع", "حالت", "پستان", "خستگی", "تاخیر"]
            if any(symptom in answer_text for symptom in pregnancy_symptoms):
                self.pregnancy_data.symptoms.append(answer_text)

        # خلاصه‌سازی تاریخچه جلسه زنان
        conv_history = gyn_data.get("conversation_history", [])
        summary_lines = []
        for msg in conv_history[:10]:  # فقط ۱۰ پیام اول
            if msg.get("role") == "user" and msg.get("content"):
                summary_lines.append(f"- بیمار: {msg['content'][:100]}")
        summary = "\n".join(summary_lines)

        self.conversation_history.append({
            "role": "system",
            "content": f"خلاصه جلسه زنان:\n{summary}",
            "timestamp": datetime.utcnow().isoformat()
        })

        print(f"✅ داده دریافت شد - علائم بارداری: {len(self.pregnancy_data.symptoms)}")

    # --------------------------------------------------
    def _call_pregnancy_model(self, user_message: str) -> Optional[str]:
        url = f"{self.ollama_base_url}/api/chat"

        messages = [{"role": "system", "content": self.system_prompt}]

        for msg in self.conversation_history:
            if msg["role"] != "system":
                messages.append({"role": msg["role"], "content": msg["content"]})

        if user_message:
            messages.append({"role": "user", "content": user_message})

        payload = {
            "model": self.pregnancy_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.6, "top_p": 0.85}
        }

        try:
            response = requests.post(url, json=payload, timeout=45)
            response.raise_for_status()

            result = response.json()
            answer = result.get("message", {}).get("content", "")
            answer = (answer or "").strip()

            if answer:
                self._detect_pregnancy_status(answer)
                self.updated_at = datetime.utcnow().isoformat()

            return answer or None

        except requests.exceptions.RequestException as e:
            print(f"Pregnancy model error: {e}")
            return None

    # --------------------------------------------------
    def _detect_pregnancy_status(self, text: str) -> None:
        t = text.lower()
        if any(w in t for w in ["تایید", "confirmed", "مثبت"]):
            self.status = PregnancyStatus.CONFIRMED
        elif any(w in t for w in ["آزمایش", "test", "بتا"]):
            self.status = PregnancyStatus.NEEDS_TESTING
        elif any(w in t for w in ["منفی", "negative", "رد"]):
            self.status = PregnancyStatus.RULED_OUT

    # --------------------------------------------------
    def start(self) -> Optional[str]:
        if self.conversation_history:
            return self.get_last_assistant_message()

        intro = (
            "بر اساس اطلاعات قبلی، احتمال بارداری بررسی می‌شود. "
            "اولین سوال را مطرح کنید."
        )
        q = self._call_pregnancy_model(intro)

        if q:
            self.conversation_history.append({
                "role": "assistant",
                "content": q,
                "timestamp": datetime.utcnow().isoformat()
            })

        return q

    # --------------------------------------------------
    def submit_answer(self, answer: str) -> Optional[str]:
        self.conversation_history.append({
            "role": "user",
            "content": answer,
            "timestamp": datetime.utcnow().isoformat()
        })

        q = self._call_pregnancy_model(answer)

        if q:
            self.conversation_history.append({
                "role": "assistant",
                "content": q,
                "timestamp": datetime.utcnow().isoformat()
            })

        return q

    # --------------------------------------------------
    def get_last_assistant_message(self) -> Optional[str]:
        for msg in reversed(self.conversation_history):
            if msg["role"] == "assistant":
                return msg["content"]
        return None

    # --------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "pregnancy_data": asdict(self.pregnancy_data),
            "conversation_history": self.conversation_history,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def save_to_file(self, filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_json())

    # --------------------------------------------------
    @classmethod
    def load_from_file(cls, filepath: str, ollama_base_url: str = "http://localhost:11434"):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        session = cls(
            session_id=data["session_id"],
            ollama_base_url=ollama_base_url,
            pregnancy_model=data.get("metadata", {}).get("model", "deepseek-r1:1.5b")
        )

        session.status = PregnancyStatus(data["status"])
        session.pregnancy_data = PregnancyData(**data.get("pregnancy_data", {}))
        session.conversation_history = data.get("conversation_history", [])
        session.metadata = data.get("metadata", {})
        session.created_at = data.get("created_at")
        session.updated_at = data.get("updated_at")

        return session

    # --------------------------------------------------
    @classmethod
    def from_gynecology_session(cls, gyn_session_file: str, ollama_base_url: str):
        with open(gyn_session_file, "r", encoding="utf-8") as f:
            gyn_data = json.load(f)

        new_id = f"pregnancy_{gyn_data['session_id']}"
        return cls(new_id, gynecology_session_data=gyn_data, ollama_base_url=ollama_base_url)
