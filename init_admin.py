#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
إنشاء حساب الإداري التلقائي
Auto Admin Account Creation
"""

from app import app, db
from models import User, Role
from werkzeug.security import generate_password_hash
import logging

def create_default_admin():
    """إنشاء حساب إداري افتراضي عند بدء التشغيل"""
    with app.app_context():
        try:
            # التحقق من وجود حساب إداري مسبقاً
            admin_phone = "01033607749"
            existing_admin = User.query.filter_by(phone=admin_phone).first()
            
            if existing_admin:
                print(f"✅ حساب الإداري موجود بالفعل: {existing_admin.name}")
                return existing_admin
            
            # إنشاء حساب إداري جديد
            admin_user = User(
                name="محمد هاني عبدالعزيز",
                phone=admin_phone,
                email="admin@al-7esa.com",
                role=Role.ADMIN,
                password_hash=generate_password_hash("zxc65432"),
                is_active=True,
                is_verified=True
            )
            
            db.session.add(admin_user)
            db.session.commit()
            
            print("🎉 تم إنشاء حساب الإداري بنجاح!")
            print(f"   الاسم: {admin_user.name}")
            print(f"   الهاتف: {admin_user.phone}")
            print(f"   كلمة المرور: zxc65432")
            
            return admin_user
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ خطأ في إنشاء حساب الإداري: {str(e)}")
            return None

if __name__ == "__main__":
    create_default_admin()
