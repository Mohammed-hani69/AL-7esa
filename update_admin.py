
import os
import sys
from app import app, db
from models import User, Role
from werkzeug.security import generate_password_hash

def update_admin(phone, password, name="مسؤول النظام"):
    with app.app_context():
        # البحث عن المستخدم برقم الهاتف
        user = User.query.filter_by(phone=phone).first()

        if not user:
            print(f"المستخدم برقم الهاتف {phone} غير موجود!")
            return False

        # تحديث المعلومات
        user.role = Role.ADMIN
        user.name = name
        user.password_hash = generate_password_hash(password)
        user.is_active = True

        db.session.commit()
        print(f"تم تحديث بيانات المستخدم {name} (رقم الهاتف: {phone}) وتعيينه كمسؤول بنجاح")
        return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("الاستخدام: python update_admin.py <phone> <password> [name]")
        sys.exit(1)

    phone = sys.argv[1]
    password = sys.argv[2]
    name = sys.argv[3] if len(sys.argv) > 3 else "مسؤول النظام"

    update_admin(phone, password, name)
