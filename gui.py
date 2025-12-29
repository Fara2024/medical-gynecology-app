import streamlit as st
from pathlib import Path
from app.core.gynecology_session import GynecologySession
from app.core.pregnancy_session import PregnancySession
from app.config.settings import OLLAMA_BASE_URL, SESSION_DIR

SESSION_DIR.mkdir(parents=True, exist_ok=True)

# مقداردهی اولیه session_state
for key in ["current_session", "pregnancy_session", "in_pregnancy", "last_question"]:
    if key not in st.session_state:
        st.session_state[key] = None
st.session_state.in_pregnancy = st.session_state.in_pregnancy or False

for key in ["gyne_answer", "preg_answer"]:
    if key not in st.session_state:
        st.session_state[key] = ""

st.title("سیستم مشاوره زنان و بارداری 🤰")

# شروع جلسه زنان
def start_gynecology_session():
    import uuid
    session_id = f"patient_{uuid.uuid4().hex[:8]}"
    session = GynecologySession(session_id=session_id, ollama_base_url=OLLAMA_BASE_URL)
    st.session_state.current_session = session
    st.session_state.last_question = session.get_current_question()
    st.rerun()  # ریفرش صفحه بعد از ایجاد جلسه

# ارسال پاسخ
def submit_answer(answer: str):
    session = st.session_state.current_session
    next_question = session.submit_answer(f"q{len(session.patient_answers)+1}", answer)

    if session.pregnancy_suspicion and not st.session_state.in_pregnancy:
        st.session_state.in_pregnancy = True
        # ذخیره جلسه زنان
        gyn_file = SESSION_DIR / f"{session.session_id}.json"
        session.save_to_file(str(gyn_file))
        # ایجاد خودکار جلسه بارداری
        st.session_state.pregnancy_session = PregnancySession.from_gynecology_session(
            gyn_session_file=str(gyn_file),
            ollama_base_url=OLLAMA_BASE_URL
        )
        st.session_state.current_session = None
        st.session_state.last_question = st.session_state.pregnancy_session.start()
    else:
        st.session_state.last_question = next_question

    # ریفرش صفحه برای پاک کردن ورودی
    st.rerun()

# نمایش سوال و پاسخ‌دهی
if st.session_state.current_session:
    st.write(f"پزشک: {st.session_state.last_question}")
    st.text_input(
        "پاسخ بیمار:",
        key="gyne_answer",
        value=st.session_state.gyne_answer
    )
    if st.button("ارسال پاسخ"):
        if st.session_state.gyne_answer.strip():
            submit_answer(st.session_state.gyne_answer.strip())

elif st.session_state.in_pregnancy:
    session = st.session_state.pregnancy_session
    st.write(f"پزشک: {st.session_state.last_question}")
    st.text_input(
        "پاسخ بیمار:",
        key="preg_answer",
        value=st.session_state.preg_answer
    )
    if st.button("ارسال پاسخ به مشاوره بارداری"):
        if st.session_state.preg_answer.strip():
            session.submit_answer(st.session_state.preg_answer.strip())
            st.session_state.last_question = session.get_current_question()
            st.rerun()

else:
    st.write("برای شروع، جلسه زنان جدید ایجاد کنید.")
    if st.button("شروع جلسه زنان"):
        start_gynecology_session()
