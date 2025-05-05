import os
import sys
from app import app, db
from models import User, Role
from werkzeug.security import generate_password_hash

def create_admin(phone, password, name="مسؤول النظام"):
    with app.app_context():
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
            password_hash=generate_password_hash(password)
        )

        db.session.add(admin)
        db.session.commit()

        print(f"تم إنشاء المسؤول بنجاح: {name}, الهاتف: {phone}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("الاستخدام: python create_admin.py <phone> <password> [name]")
        sys.exit(1)

    phone = sys.argv[1]
    password = sys.argv[2]
    name = sys.argv[3] if len(sys.argv) > 3 else "مسؤول النظام"

    create_admin(phone, password, name)