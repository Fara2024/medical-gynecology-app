import uuid
from app.core.gynecology_session import GynecologySession
from app.config.settings import SESSION_DIR

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

def run_cli():
    session_id = f"patient_{uuid.uuid4().hex[:8]}"
    session = GynecologySession(session_id)

    print(f"\n🩺 شروع ویزیت: {session_id}")
    print("="*60)

    print(f"\nپزشک: {session.get_current_question()}\n")

    q_index = 0
    while session.status.value == "active":
        answer = input("بیمار: ").strip()

        if answer in ["خروج", "پایان"]:
            session.complete_session()
            break

        if not answer:
            continue

        key = QUESTION_KEYS[q_index] if q_index < len(QUESTION_KEYS) else f"extra_{q_index}"
        next_q = session.submit_answer(key, answer)

        if session.pregnancy_suspicion:
            print("\n⚠️ احتمال بارداری وجود دارد.")
            break

        if next_q:
            print(f"\nپزشک: {next_q}\n")
            q_index += 1
        else:
            break

    SESSION_DIR.mkdir(exist_ok=True)
    path = SESSION_DIR / f"{session_id}.json"
    session.save_to_file(str(path))

    print(f"\n💾 ذخیره شد: {path}")

if __name__ == "__main__":
    run_cli()
