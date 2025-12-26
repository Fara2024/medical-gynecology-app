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
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class SessionState:
    """Complete session state for persistence"""
    session_id: str
    status: str
    patient_answers: Dict[str, Any]
    conversation_history: List[Dict[str, str]]
    pregnancy_suspicion: bool
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str


class GynecologySession:
    """
    Manages gynecology consultation sessions with Ollama LLM integration.
    
    Features:
    - REST API communication with Ollama
    - Conversation state management
    - Patient answer persistence
    - Adaptive questioning
    - Pregnancy suspicion detection
    - Model-agnostic design for easy switching
    """
    
    def __init__(
        self,
        session_id: str,
        ollama_base_url: str = "http://localhost:11434",
        model_name: str = "gemma3-medical",
        system_prompt: Optional[str] = None
    ):
        """
        Initialize a new gynecology session.
        
        Args:
            session_id: Unique identifier for the session
            ollama_base_url: Base URL for Ollama API
            model_name: Name of the Ollama model to use
            system_prompt: Custom system prompt for the model
        """
        self.session_id = session_id
        self.ollama_base_url = ollama_base_url.rstrip('/')
        self.model_name = model_name
        
        # Session state
        self.status = SessionStatus.ACTIVE
        self.patient_answers: Dict[str, Any] = {}
        self.conversation_history: List[Message] = []
        self.pregnancy_suspicion = False
        
        # Metadata
        self.metadata = {
            "model": model_name,
            "ollama_url": ollama_base_url
        }
        self.created_at = datetime.utcnow().isoformat()
        self.updated_at = self.created_at
        
        # System prompt
        self.system_prompt = system_prompt or self._default_system_prompt()

        
        # Initialize conversation
        self._initialize_conversation()
    
    

    def _default_system_prompt(self) -> str:
    return """
    You are a professional gynecology medical assistant.

    Rules:
    - Ask ONLY ONE question at a time
    - Follow standard gynecology history taking order
    - Be concise and clear
    - Do NOT give diagnosis or treatment yet
    - If answers suggest pregnancy, continue history but do not conclude

    Always end with ONE clear question.
    """

    def _call_ollama(self, user_message: str) -> Optional[str]:
        """
        Make a REST API call to Ollama.
        
        Args:
            user_message: The user's message to send
            
        Returns:
            Model's response or None if error
        """
        url = f"{self.ollama_base_url}/api/chat"
        
        # Build messages for API call
        messages = []
        
        # Add conversation history
        for msg in self.conversation_history:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Add current user message if provided
        if user_message:
            messages.append({"role": "user", "content": user_message})
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.4,
                "top_p": 0.9
            }
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
            
            # Check for pregnancy suspicion flag
            
            
        except requests.exceptions.RequestException as e:
            print(f"Error calling Ollama API: {e}")
            return None
    
    def _initialize_conversation(self) -> None:
        opening = self._call_ollama(
            "Start the consultation with a polite greeting and ask the chief complaint.")
    
        if opening:
            self._add_message("assistant", opening)







    def _add_message(self, role: str, content: str) -> None:
        """Add a message to conversation history"""
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
                return (
                    "با توجه به سن بیمار، این نوع ویزیت نیازمند بررسی و ارجاع حضوری توسط پزشک متخصص است.")
            
        except ValueError:
            pass

        return None

    def submit_answer(self, question_key: str, answer: str) -> Optional[str]:
        """
        Submit a patient answer and get the next question.
        
        Args:
            question_key: Identifier for the question being answered
            answer: Patient's answer
            
        Returns:
            Next question from the model or None if error
        """
        if self.status != SessionStatus.ACTIVE:
            raise ValueError(f"Session is not active. Status: {self.status.value}")
        self._detect_pregnancy()

        # Store the answer
        self.patient_answers[question_key] = {
            "answer": answer,
            "timestamp": datetime.utcnow().isoformat()
        }
        


        # Age validation (only once)
        if question_key.lower().startswith("q") and not self.patient_answers.get("_age_checked"):
            age_warning = self._validate_age(answer)
            self.patient_answers["_age_checked"] = True

            if age_warning:
                self._add_message("assistant", age_warning)
                return age_warning

        # Add user message to history
        self._add_message("user", answer)
        
        # Get next question from model
        next_question = self._call_ollama("پاسخ بیمار ثبت شد. لطفاً سوال بعدی را طبق ترتیب شرح حال بپرس.")

        if next_question:
            self._add_message("assistant", next_question)
        
        self.updated_at = datetime.utcnow().isoformat()
        
        return next_question
    
    def get_current_question(self) -> Optional[str]:
        """Get the most recent question from the assistant"""
        for msg in reversed(self.conversation_history):
            if msg.role == "assistant":
                return msg.content
        return None
    
    def complete_session(self) -> None:
        """Mark the session as completed"""
        self.status = SessionStatus.COMPLETED
        self.updated_at = datetime.utcnow().isoformat()
    
    def suspend_session(self) -> None:
        """Suspend the session for later continuation"""
        self.status = SessionStatus.SUSPENDED
        self.updated_at = datetime.utcnow().isoformat()
    
    def to_json(self) -> str:
        """
        Export session state as JSON string.
        
        Returns:
            JSON string representation of the session
        """
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
        
        return json.dumps(asdict(state), indent=2)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Export session state as dictionary.
        
        Returns:
            Dictionary representation of the session
        """
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
    
    def save_to_file(self, filepath: str) -> None:
        """
        Save session state to a JSON file.
        
        Args:
            filepath: Path to save the JSON file
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_json())
    
    @classmethod
    def load_from_file(cls, filepath: str, ollama_base_url: str = "http://localhost:11434") -> 'GynecologySession':
        """
        Load a session from a JSON file.
        
        Args:
            filepath: Path to the JSON file
            ollama_base_url: Base URL for Ollama API
            
        Returns:
            Restored GynecologySession instance
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return cls.from_dict(data, ollama_base_url)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], ollama_base_url: str = "http://localhost:11434") -> 'GynecologySession':
        """
        Restore a session from a dictionary.
        
        Args:
            data: Dictionary containing session state
            ollama_base_url: Base URL for Ollama API
            
        Returns:
            Restored GynecologySession instance
        """
        session = cls(
            session_id=data["session_id"],
            ollama_base_url=ollama_base_url,
            model_name=data["metadata"]["model"]
        )
        
        # Restore state
        session.status = SessionStatus(data["status"])
        session.patient_answers = data["patient_answers"]
      #  session.conversation_history = [
            Message(**msg) for msg in data["conversation_history"]
        
        session.pregnancy_suspicion = data["pregnancy_suspicion"]
        session.metadata = data["metadata"]
        session.created_at = data["created_at"]
        session.updated_at = data["updated_at"]
        
        return session
    
    def _detect_pregnancy(self) -> None:
        answers_text = " ".join(
            v["answer"] for v in self.patient_answers.values() if isinstance(v, dict)
        )

        from app.config.settings import PREGNANCY_RULES

        symptoms_found = any(
            symptom in answers_text for symptom in PREGNANCY_RULES["required_symptoms"]
        )

        months_found = any(
            word in answers_text for word in ["2 ماه", "3 ماه", "سه ماه", "دو ماه"]
        )

        if symptoms_found and months_found:
            self.pregnancy_suspicion = True






    def switch_model(self, new_model_name: str) -> None:
        """
        Switch to a different Ollama model.
        
        Args:
            new_model_name: Name of the new model to use
        """
        self.model_name = new_model_name
        self.metadata["model"] = new_model_name
        self.metadata["model_switched_at"] = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow().isoformat()


