"""
Main application entry point
"""
import uuid
from app.core.gynecology_session import GynecologySession
from app.config.settings import OLLAMA_BASE_URL, MODEL_NAME, SESSION_DIR



QUESTION_KEYS = [
    "age",
    "chief_complaint",
    "lmp",
    "cycle_regular",
    "pregnancy_history",
    "contraception",
    "current_symptoms",
    "medical_history",
    "medications",
    "surgery_history",
    "drug_allergy"
]



def main():
    """Run a sample gynecology consultation"""
    
    # Generate unique session ID
    session_id = f"patient_{uuid.uuid4().hex[:8]}"
    
    print(f"Starting new session: {session_id}")
    print("="*60)
    
    # Create session
    session = GynecologySession(
        session_id=session_id,
        ollama_base_url="http://localhost:11434",
        model_name="gyn-assistant:latest"
    )

    # Start session with Persian system instruction
    

    # Get initial question
    initial_question = session.get_current_question()
    print(f"\nپزشک: {initial_question}\n")
    
    # Interactive loop
    question_counter = 1
    while session.status.value == "active":
        answer = input("بیمار: ").strip()

        if answer in ['خروج', 'پایان']:
            session.complete_session()
            break

        if not answer:
            continue

        question_key = QUESTION_KEYS[question_counter - 1] \
            if question_counter <= len(QUESTION_KEYS) \
            else f"extra_{question_counter}"

        next_question = session.submit_answer(question_key, answer)

        if session.pregnancy_suspicion:
            print("\n⚠️ احتمال بارداری وجود دارد. ارجاع به ماژول بارداری.")
            break

        if next_question:
            print(f"\nپزشک: {next_question}\n")
            question_counter += 1
        else:
            print("❌ خطا در دریافت پاسخ از مدل")
            break





    # Save session
    session_file = SESSION_DIR / f"{session_id}.json"
    session.save_to_file(str(session_file))
    
    print("\n" + "="*60)
    print(f"Session saved to: {session_file}")
    print(f"Pregnancy suspicion detected: {session.pregnancy_suspicion}")
    print(f"Total questions answered: {len(session.patient_answers)}")


if __name__ == "__main__":
    QUESTION_KEYS = [
    "age",
    "chief_complaint",
    "lmp",
    "cycle_regular",
    "pregnancy_history",
    "contraception",
    "current_symptoms",
    "medical_history",
    "medications",
    "surgery_history",
    "drug_allergy"
]

    main()