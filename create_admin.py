import os
import sys
from app import app, db
from models import User, Role
from datetime import datetime

def create_admin(name, phone, password):
    with app.app_context():
        # التحقق من صحة رقم الهاتف
        if not phone.startswith('01') or len(phone) != 11:
            print(f"رقم الهاتف غير صحيح: {phone}. يجب أن يبدأ بـ 01 ويتكون من 11 رقم")
            return

        # التحقق من وجود مستخدم بنفس رقم الهاتف
        existing_user = User.query.filter_by(phone=phone).first()

        if existing_user:
            print(f"المستخدم برقم الهاتف {phone} موجود بالفعل")
            return

        # إنشاء المستخدم الجديد
        admin = User(
            name=name,
            phone=phone,
            role=Role.ADMIN,
            is_active=True,
            is_verified=True
        )
        
        # تعيين كلمة المرور
        admin.set_password(password)

        db.session.add(admin)
        db.session.commit()

        print(f"تم إنشاء المسؤول بنجاح!")
        print(f"الاسم: {name}")
        print(f"رقم الهاتف: {phone}")
        print(f"الدور: مسؤول النظام")
        print(f"حالة الحساب: نشط ومُفعل")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("الاستخدام: python create_admin.py <name> <phone> <password>")
        print("مثال: python create_admin.py 'أحمد محمد' 01123456789 password123")
        print("")
        print("ملاحظات:")
        print("- الاسم: اسم المسؤول")
        print("- رقم الهاتف: يجب أن يبدأ بـ 01 ويتكون من 11 رقم")
        print("- كلمة المرور: يُفضل أن تكون قوية")
        sys.exit(1)

    name = sys.argv[1]
    phone = sys.argv[2]
    password = sys.argv[3]

    create_admin(name, phone, password)