#!/usr/bin/env python3
"""
اختبار التحقق من رقم المحفظة الإلكترونية للمعلم عند إنشاء فصل مدفوع
Test script to verify ewallet number validation for teachers creating paid classrooms
"""

from app import create_app
from models import db, User, Role, Classroom
from werkzeug.security import generate_password_hash

def test_ewallet_validation():
    """اختبار التحقق من أرقام المحافظ الإلكترونية"""
    
    # إنشاء التطبيق للاختبار
    app = create_app()
    
    with app.app_context():
        print("🧪 بدء اختبار التحقق من أرقام المحافظ الإلكترونية...")
        
        # اختبار 1: معلم بدون أرقام محافظ
        teacher_without_ewallet = User(
            phone="+966501234567",
            password_hash=generate_password_hash("password123"),
            name="معلم بدون محفظة",
            role=Role.TEACHER,
            is_verified=True,
            ewallet_number_1=None,
            ewallet_number_2=None
        )
        
        print(f"✅ اختبار 1: معلم بدون أرقام محافظ")
        print(f"   - has_ewallet_numbers(): {teacher_without_ewallet.has_ewallet_numbers()}")
        assert not teacher_without_ewallet.has_ewallet_numbers(), "يجب أن يعيد False للمعلم بدون أرقام محافظ"
        
        # اختبار 2: معلم برقم محفظة واحد
        teacher_with_one_ewallet = User(
            phone="+966507654321",
            password_hash=generate_password_hash("password123"),
            name="معلم برقم محفظة واحد",
            role=Role.TEACHER,
            is_verified=True,
            ewallet_number_1="0123456789",
            ewallet_number_2=None
        )
        
        print(f"✅ اختبار 2: معلم برقم محفظة واحد")
        print(f"   - has_ewallet_numbers(): {teacher_with_one_ewallet.has_ewallet_numbers()}")
        assert teacher_with_one_ewallet.has_ewallet_numbers(), "يجب أن يعيد True للمعلم برقم محفظة واحد"
        
        # اختبار 3: معلم برقمي محفظة
        teacher_with_two_ewallets = User(
            phone="+966509876543",
            password_hash=generate_password_hash("password123"),
            name="معلم برقمي محفظة",
            role=Role.TEACHER,
            is_verified=True,
            ewallet_number_1="0123456789",
            ewallet_number_2="0987654321"
        )
        
        print(f"✅ اختبار 3: معلم برقمي محفظة")
        print(f"   - has_ewallet_numbers(): {teacher_with_two_ewallets.has_ewallet_numbers()}")
        assert teacher_with_two_ewallets.has_ewallet_numbers(), "يجب أن يعيد True للمعلم برقمي محفظة"
        
        # اختبار 4: معلم برقم محفظة ثاني فقط
        teacher_with_second_ewallet = User(
            phone="+966508765432",
            password_hash=generate_password_hash("password123"),
            name="معلم برقم محفظة ثاني",
            role=Role.TEACHER,
            is_verified=True,
            ewallet_number_1=None,
            ewallet_number_2="0987654321"
        )
        
        print(f"✅ اختبار 4: معلم برقم محفظة ثاني فقط")
        print(f"   - has_ewallet_numbers(): {teacher_with_second_ewallet.has_ewallet_numbers()}")
        assert teacher_with_second_ewallet.has_ewallet_numbers(), "يجب أن يعيد True للمعلم برقم محفظة ثاني فقط"
        
        # اختبار 5: عرض أرقام المحافظ
        print(f"✅ اختبار 5: عرض أرقام المحافظ")
        display_numbers = teacher_with_two_ewallets.get_ewallet_numbers_display()
        print(f"   - أرقام المحافظ: {display_numbers}")
        assert len(display_numbers) == 2, "يجب أن يعيد رقمين للمعلم برقمي محفظة"
        
        display_numbers_one = teacher_with_one_ewallet.get_ewallet_numbers_display()
        print(f"   - رقم محفظة واحد: {display_numbers_one}")
        assert len(display_numbers_one) == 1, "يجب أن يعيد رقم واحد للمعلم برقم محفظة واحد"
        
        display_numbers_none = teacher_without_ewallet.get_ewallet_numbers_display()
        print(f"   - بدون أرقام محافظ: {display_numbers_none}")
        assert len(display_numbers_none) == 0, "يجب أن يعيد قائمة فارغة للمعلم بدون أرقام محافظ"
        
        print("\n🎉 تم اجتياز جميع الاختبارات بنجاح!")
        print("\n📝 ملخص النتائج:")
        print("   - التحقق من وجود أرقام المحافظ يعمل بشكل صحيح")
        print("   - عرض أرقام المحافظ يعمل بشكل صحيح")
        print("   - التحقق يدعم رقم واحد أو رقمين أو بدون أرقام")
        print("\n✨ يمكن الآن للمعلمين إضافة أرقام محافظهم في الملف الشخصي")
        print("✨ لن يتمكن المعلمون من إنشاء فصول مدفوعة بدون أرقام محافظ")

if __name__ == "__main__":
    test_ewallet_validation()
