"""
Transfer to Pregnancy - اسکریپت انتقال بیمار به بخش بارداری
"""
import sys
import os
from pathlib import Path

# اضافه کردن مسیر پروژه
sys.path.insert(0, str(Path(__file__).parent))

from app.core.gynecology_session import GynecologySession
from app.core.pregnancy_session import PregnancySession
from app.config.settings import OLLAMA_BASE_URL, SESSION_DIR


def check_pregnancy_suspicion(gyn_session: GynecologySession) -> bool:
    """
    بررسی مشکوک به بارداری بودن
    
    Args:
        gyn_session: جلسه زنان
        
    Returns:
        True اگر مشکوک به بارداری باشد
    """
    # روش ۱: چک کردن پرچم خود جلسه
    if gyn_session.pregnancy_suspicion:
        return True
    
    # روش ۲: تحلیل پاسخ‌های بیمار
    pregnancy_keywords = [
        "تاخیر قاعدگی",
        "تاخیر پریود", 
        "تست بارداری",
        "حالت تهوع",
        "استفراغ صبح",
        "پستان حساس",
        "باردار"
    ]
    
    for answer_data in gyn_session.patient_answers.values():
        answer = answer_data.get("answer", "") if isinstance(answer_data, dict) else str(answer_data)
        
        if any(keyword in answer for keyword in pregnancy_keywords):
            return True
    
    return False


def transfer_patient(gyn_session_file: str) -> None:
    """
    انتقال بیمار از بخش زنان به بخش بارداری
    
    Args:
        gyn_session_file: مسیر فایل جلسه زنان
    """
    print("\n" + "="*60)
    print("🔄 سیستم انتقال به بخش بارداری")
    print("="*60 + "\n")
    
    # بارگذاری جلسه زنان
    print("📂 در حال بارگذاری جلسه زنان...")
    gyn_session = GynecologySession.load_from_file(gyn_session_file, OLLAMA_BASE_URL)
    
    print(f"✅ جلسه بارگذاری شد: {gyn_session.session_id}")
    print(f"   - تعداد پاسخ‌ها: {len(gyn_session.patient_answers)}")
    print(f"   - وضعیت: {gyn_session.status.value}")
    
    # بررسی مشکوک به بارداری بودن
    print("\n🔍 در حال بررسی علائم بارداری...")
    
    if check_pregnancy_suspicion(gyn_session):
        print("⚠️  علائم مشکوک به بارداری شناسایی شد!")
        
        # تایید از کاربر
        confirm = input("\nآیا می‌خواهید بیمار را به بخش بارداری منتقل کنید؟ (y/n): ")
        
        if confirm.lower() not in ['y', 'yes', 'بله']:
            print("❌ انتقال لغو شد.")
            return
        
        print("\n🚀 در حال ایجاد جلسه بارداری...")
        
        # ایجاد جلسه بارداری
        pregnancy_session = PregnancySession(
            session_id=f"pregnancy_{gyn_session.session_id}",
            gynecology_session_data=gyn_session.to_dict(),
            ollama_base_url=OLLAMA_BASE_URL,
            pregnancy_model="deepseek-r1:1.5b"
        )
        
        print("✅ جلسه بارداری ایجاد شد")
        
        # شروع مشاوره بارداری
        print("\n" + "="*60)
        print("🤰 شروع مشاوره تخصصی بارداری")
        print("="*60 + "\n")
        
        first_question = pregnancy_session.start_pregnancy_consultation()
        print(f"پزشک: {first_question}\n")
        
        # حلقه تعاملی
        question_count = 0
        while pregnancy_session.status.value != "confirmed" and question_count < 20:
            answer = input("بیمار: ").strip()
            
            if answer.lower() in ['quit', 'exit', 'خروج', 'done']:
                break
            
            if not answer:
                continue
            
            next_question = pregnancy_session.submit_answer(answer)
            
            if next_question:
                print(f"\nپزشک: {next_question}\n")
                question_count += 1
            else:
                print("❌ خطا در دریافت سوال بعدی")
                break
        
        # ذخیره گزارش نهایی
        pregnancy_file = SESSION_DIR / f"{pregnancy_session.session_id}.json"
        pregnancy_session.save_to_file(str(pregnancy_file))
        
        print("\n" + "="*60)
        print("📊 خلاصه جلسه بارداری")
        print("="*60)
        print(f"Session ID: {pregnancy_session.session_id}")
        print(f"وضعیت: {pregnancy_session.status.value}")
        print(f"تعداد سوالات: {question_count}")
        print(f"LMP: {pregnancy_session.pregnancy_data.lmp or 'وارد نشده'}")
        print(f"β-hCG: {pregnancy_session.pregnancy_data.beta_hcg or 'انجام نشده'}")
        print(f"\n💾 گزارش ذخیره شد: {pregnancy_file}")
        
        # تولید گزارش نهایی
        print("\n📋 آیا می‌خواهید گزارش نهایی تولید شود؟ (y/n): ", end="")
        if input().lower() in ['y', 'yes', 'بله']:
            report = pregnancy_session.generate_pregnancy_report()
            print("\n" + "="*60)
            print("📄 گزارش نهایی بارداری")
            print("="*60)
            print(report.get('final_summary', 'خطا در تولید گزارش'))
    
    else:
        print("✅ علائم مشکوک به بارداری یافت نشد")
        print("ℹ️  ادامه مشاوره در بخش زنان توصیه می‌شود")


def main():
    """تابع اصلی"""
    if len(sys.argv) < 2:
        print("❌ خطا: فایل جلسه زنان مشخص نشده است")
        print("\nاستفاده:")
        print(f"  python {sys.argv[0]} <gyn_session_file.json>")
        print("\nمثال:")
        print(f"  python {sys.argv[0]} data/sessions/patient_001.json")
        sys.exit(1)
    
    gyn_file = sys.argv[1]
    
    # بررسی وجود فایل
    if not os.path.exists(gyn_file):
        print(f"❌ خطا: فایل {gyn_file} یافت نشد")
        sys.exit(1)
    
    try:
        transfer_patient(gyn_file)
    except KeyboardInterrupt:
        print("\n\n⚠️  عملیات توسط کاربر لغو شد")
    except Exception as e:
        print(f"\n❌ خطای غیرمنتظره: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()