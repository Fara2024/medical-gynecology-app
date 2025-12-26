"""
Pregnancy Session Manager - Specialized Module for Pregnancy Cases
ماژول تخصصی مدیریت بارداری
"""
import json
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict, field
from enum import Enum


class PregnancyStatus(Enum):
    """وضعیت جلسه بارداری"""
    SUSPECTED = "suspected"  # مشکوک
    CONFIRMED = "confirmed"  # تایید شده
    RULED_OUT = "ruled_out"  # رد شده
    NEEDS_TESTING = "needs_testing"  # نیاز به آزمایش


@dataclass
class PregnancyData:
    """داده‌های بارداری"""
    lmp: Optional[str] = None  # Last Menstrual Period
    gestational_age: Optional[int] = None  # سن بارداری (هفته)
    beta_hcg: Optional[float] = None  # نتیجه آزمایش
    ultrasound_findings: Optional[str] = None
    risk_factors: List[str] = field(default_factory=list)
    symptoms: List[str] = field(default_factory=list)


class PregnancySession:
    """
    مدیریت جلسات تخصصی بارداری
    
    ویژگی‌ها:
    - دریافت داده از gynecology_session
    - اتصال به مدل pregnancy-assistant
    - تحلیل تخصصی بارداری
    - پیگیری و مشاوره
    """
    
    def __init__(
        self,
        session_id: str,
        gynecology_session_data: Optional[Dict] = None,
        ollama_base_url: str = "http://localhost:11434",
        pregnancy_model: str = "deepseek-r1:1.5b"
    ):
        """
        ایجاد جلسه بارداری
        
        Args:
            session_id: شناسه یکتا
            gynecology_session_data: داده‌های جلسه زنان (اختیاری)
            ollama_base_url: آدرس Ollama
            pregnancy_model: نام مدل بارداری
        """
        self.session_id = session_id
        self.ollama_base_url = ollama_base_url.rstrip('/')
        self.pregnancy_model = pregnancy_model
        
        # وضعیت جلسه
        self.status = PregnancyStatus.SUSPECTED
        self.pregnancy_data = PregnancyData()
        self.conversation_history: List[Dict] = []
        
        # متادیتا
        self.metadata = {
            "model": pregnancy_model,
            "transferred_from": None,
            "source_session_id": None
        }
        self.created_at = datetime.utcnow().isoformat()
        self.updated_at = self.created_at
        
        # System prompt تخصصی بارداری
        self.system_prompt = self._pregnancy_system_prompt()
        
        # اگر داده از gynecology_session دریافت شده
        if gynecology_session_data:
            self._import_from_gynecology(gynecology_session_data)
    
    def _pregnancy_system_prompt(self) -> str:
        """System prompt برای مدل بارداری"""
        return """شما یک متخصص بارداری و زایمان هستید.

وظایف شما:
1. بررسی دقیق علائم و نشانه‌های بارداری
2. محاسبه سن بارداری بر اساس LMP
3. تفسیر نتایج آزمایش β-hCG
4. ارائه مشاوره تخصصی بارداری
5. شناسایی عوامل خطر
6. پیشنهاد اقدامات لازم

قوانین:
- همیشه به فارسی پاسخ دهید
- یک سوال در هر پیام
- لحن دلسوزانه و حرفه‌ای
- هرگز تشخیص قطعی ندهید
- همیشه نظر پزشک را درخواست کنید

سوالات کلیدی بارداری:
1. تاریخ دقیق آخرین قاعدگی (LMP)
2. آیا قاعدگی منظم بود؟
3. آیا تست بارداری انجام شده؟
4. علائم: حالت تهوع، حساسیت پستان، خستگی
5. سابقه بارداری قبلی و عوارض آن
6. بیماری‌های زمینه‌ای (دیابت، فشار خون)
7. مصرف دارو یا مکمل

در پایان همیشه این بخش را اضافه کنید:
✍️ نظر متخصص بارداری و زایمان:
(پزشک تشخیص نهایی و برنامه مراقبت را وارد می‌کند)
"""
    
    def _import_from_gynecology(self, gyn_data: Dict) -> None:
        """
        دریافت و پردازش داده از gynecology_session
        
        Args:
            gyn_data: دیکشنری داده‌های جلسه زنان
        """
        print(f"📥 در حال دریافت داده از جلسه زنان...")
        
        # ذخیره منبع
        self.metadata["transferred_from"] = "gynecology_session"
        self.metadata["source_session_id"] = gyn_data.get("session_id")
        
        # استخراج پاسخ‌های بیمار
        patient_answers = gyn_data.get("patient_answers", {})
        
        # استخراج اطلاعات مهم
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
        
        # کپی تاریخچه مکالمه
        conv_history = gyn_data.get("conversation_history", [])
        summary = self._summarize_gynecology_history(conv_history)
        
        # افزودن خلاصه به تاریخچه
        self.conversation_history.append({
            "role": "system",
            "content": f"خلاصه جلسه زنان:\n{summary}",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        print(f"✅ داده دریافت شد - علائم بارداری: {len(self.pregnancy_data.symptoms)}")
    
    def _summarize_gynecology_history(self, history: List[Dict]) -> str:
        """خلاصه‌سازی تاریخچه جلسه زنان"""
        summary_parts = []
        
        for msg in history:
            role = msg.get("role")
            content = msg.get("content", "")
            
            if role == "user" and content:
                summary_parts.append(f"- بیمار: {content[:100]}")
        
        return "\n".join(summary_parts[:10])  # فقط ۱۰ پاسخ اول
    
    def _call_pregnancy_model(self, user_message: str) -> Optional[str]:
        """
        فراخوانی مدل بارداری
        
        Args:
            user_message: پیام کاربر
            
        Returns:
            پاسخ مدل
        """
        url = f"{self.ollama_base_url}/api/chat"
        
        # ساخت پیام‌ها
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # افزودن تاریخچه
        messages.extend(self.conversation_history)
        
        # افزودن پیام فعلی
        if user_message:
            messages.append({"role": "user", "content": user_message})
        
        payload = {
            "model": self.pregnancy_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.6,  # کمتر برای دقت بیشتر
                "top_p": 0.85
            }
        }
        
        try:
            print(f"🤖 فراخوانی مدل: {self.pregnancy_model}")
            
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=45
            )
            response.raise_for_status()
            
            result = response.json()
            assistant_message = result.get("message", {}).get("content", "")
            
            # شناسایی وضعیت بارداری از پاسخ
            self._detect_pregnancy_status(assistant_message)
            
            return assistant_message
            
        except requests.exceptions.RequestException as e:
            print(f"❌ خطا در فراخوانی مدل بارداری: {e}")
            return None
    
    def _detect_pregnancy_status(self, message: str) -> None:
        """شناسایی وضعیت بارداری از پاسخ مدل"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["تایید", "confirmed", "مثبت"]):
            self.status = PregnancyStatus.CONFIRMED
        elif any(word in message_lower for word in ["آزمایش", "test", "بتا"]):
            self.status = PregnancyStatus.NEEDS_TESTING
        elif any(word in message_lower for word in ["منفی", "negative", "رد"]):
            self.status = PregnancyStatus.RULED_OUT
    
    def start_pregnancy_consultation(self) -> str:
        """شروع مشاوره بارداری"""
        initial_message = """بر اساس اطلاعات دریافت شده از جلسه قبل، علائمی مشکوک به بارداری مشاهده شده است.
        
لطفاً برای ادامه بررسی، اولین سوال را پاسخ دهید."""
        
        first_question = self._call_pregnancy_model(initial_message)
        
        if first_question:
            self.conversation_history.append({
                "role": "assistant",
                "content": first_question,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        return first_question or "خطا در دریافت سوال اول"
    
    def submit_answer(self, answer: str) -> Optional[str]:
        """
        ثبت پاسخ بیمار
        
        Args:
            answer: پاسخ بیمار
            
        Returns:
            سوال بعدی
        """
        # ثبت پاسخ کاربر
        self.conversation_history.append({
            "role": "user",
            "content": answer,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # دریافت سوال بعدی
        next_question = self._call_pregnancy_model(answer)
        
        if next_question:
            self.conversation_history.append({
                "role": "assistant",
                "content": next_question,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        self.updated_at = datetime.utcnow().isoformat()
        
        return next_question
    
    def add_lab_result(self, test_name: str, value: float, unit: str) -> str:
        """
        افزودن نتیجه آزمایش
        
        Args:
            test_name: نام آزمایش
            value: مقدار
            unit: واحد
            
        Returns:
            تفسیر مدل
        """
        if "hcg" in test_name.lower() or "بتا" in test_name:
            self.pregnancy_data.beta_hcg = value
        
        lab_message = f"نتیجه آزمایش {test_name}: {value} {unit}"
        interpretation = self._call_pregnancy_model(
            f"لطفاً این نتیجه آزمایش را تفسیر کنید:\n{lab_message}"
        )
        
        return interpretation or "خطا در تفسیر آزمایش"
    
    def generate_pregnancy_report(self) -> Dict[str, Any]:
        """
        تولید گزارش نهایی بارداری
        
        Returns:
            گزارش کامل JSON
        """
        report_request = """لطفاً یک گزارش جامع از وضعیت بارداری این بیمار تهیه کنید شامل:
1. خلاصه علائم و یافته‌ها
2. تفسیر نتایج آزمایش (در صورت وجود)
3. احتمال بارداری
4. توصیه‌های تخصصی
5. اقدامات بعدی پیشنهادی"""
        
        final_summary = self._call_pregnancy_model(report_request)
        
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "pregnancy_data": asdict(self.pregnancy_data),
            "final_summary": final_summary,
            "conversation_history": self.conversation_history,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    def to_json(self) -> str:
        """تبدیل به JSON"""
        return json.dumps(self.generate_pregnancy_report(), ensure_ascii=False, indent=2)
    
    def save_to_file(self, filepath: str) -> None:
        """ذخیره در فایل"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_json())
        print(f"💾 گزارش بارداری ذخیره شد: {filepath}")
    
    @classmethod
    def from_gynecology_session(
        cls,
        gyn_session_file: str,
        ollama_base_url: str = "http://localhost:11434"
    ) -> 'PregnancySession':
        """
        ایجاد جلسه بارداری از فایل جلسه زنان
        
        Args:
            gyn_session_file: مسیر فایل JSON جلسه زنان
            ollama_base_url: آدرس Ollama
            
        Returns:
            نمونه PregnancySession
        """
        with open(gyn_session_file, 'r', encoding='utf-8') as f:
            gyn_data = json.load(f)
        
        # تولید session_id جدید
        new_session_id = f"pregnancy_{gyn_data['session_id']}"
        
        return cls(
            session_id=new_session_id,
            gynecology_session_data=gyn_data,
            ollama_base_url=ollama_base_url
        )


# مثال استفاده
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("استفاده: python pregnancy_session.py <gyn_session_file.json>")
        sys.exit(1)
    
    gyn_file = sys.argv[1]
    
    print("="*60)
    print("🤰 سیستم مشاوره تخصصی بارداری")
    print("="*60)
    
    # ایجاد جلسه بارداری از فایل زنان
    pregnancy_session = PregnancySession.from_gynecology_session(gyn_file)
    
    # شروع مشاوره
    first_q = pregnancy_session.start_pregnancy_consultation()
    print(f"\nپزشک: {first_q}\n")
    
    # حلقه تعاملی
    while True:
        answer = input("بیمار: ").strip()
        
        if answer.lower() in ['quit', 'exit', 'خروج']:
            break
        
        if not answer:
            continue
        
        next_q = pregnancy_session.submit_answer(answer)
        if next_q:
            print(f"\nپزشک: {next_q}\n")
    
    # تولید گزارش
    report_file = f"data/sessions/{pregnancy_session.session_id}.json"
    pregnancy_session.save_to_file(report_file)
    
    print(f"\n✅ وضعیت نهایی: {pregnancy_session.status.value}")