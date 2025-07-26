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
            # قائمة المسؤولين المطلوب إنشاؤهم
            admins_to_create = [
                {
                    "name": "عبدالعزيز هاني", 
                    "phone": "01033607749",
                    "email": "admin1@al-7esa.com"
                },
                {
                    "name": "محمد هاني عبدالعزيز", 
                    "phone": "01508755174",
                    "email": "admin2@al-7esa.com"
                }
            ]
            
            created_count = 0
            
            for admin_data in admins_to_create:
                existing_admin = User.query.filter_by(phone=admin_data["phone"]).first()
                
                if existing_admin:
                    print(f"✅ حساب الإداري موجود بالفعل: {existing_admin.name} ({existing_admin.phone})")
                    # التأكد من أن الدور صحيح
                    if existing_admin.role != Role.ADMIN:
                        existing_admin.role = Role.ADMIN
                        existing_admin.is_active = True
                        existing_admin.is_verified = True
                        print(f"   تم تحديث الدور إلى مسؤول")
                        created_count += 1
                else:
                    # التحقق من البريد الإلكتروني لتجنب التكرار
                    existing_email = User.query.filter_by(email=admin_data["email"]).first()
                    if existing_email:
                        # استخدم بريد إلكتروني فريد بناء على رقم الهاتف
                        unique_email = f"admin_{admin_data['phone']}@al-7esa.com"
                        print(f"⚠️ البريد الإلكتروني {admin_data['email']} موجود، سيتم استخدام: {unique_email}")
                        admin_data["email"] = unique_email
                    
                    # إنشاء حساب إداري جديد
                    admin_user = User(
                        name=admin_data["name"],
                        phone=admin_data["phone"],
                        email=admin_data["email"],
                        role=Role.ADMIN,
                        password_hash=generate_password_hash("zxc65432"),
                        is_active=True,
                        is_verified=True
                    )
                    
                    db.session.add(admin_user)
                    created_count += 1
                    
                    print(f"🎉 تم إنشاء حساب إداري جديد!")
                    print(f"   الاسم: {admin_user.name}")
                    print(f"   الهاتف: {admin_user.phone}")
                    print(f"   البريد الإلكتروني: {admin_user.email}")
                    print(f"   كلمة المرور: zxc65432")
                    print(f"   الدور: مسؤول النظام")
            
            if created_count > 0:
                db.session.commit()
                print(f"\n✨ تم إنشاء/تحديث {created_count} من حسابات المسؤولين")
            
            print("\n📋 معلومات تسجيل الدخول للمسؤولين:")
            print("=" * 50)
            for admin_data in admins_to_create:
                print(f"👤 {admin_data['name']}")
                print(f"   📱 الهاتف: {admin_data['phone']}")
                print(f"   🔑 كلمة المرور: zxc65432")
                print("-" * 30)
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ خطأ في إنشاء حساب الإداري: {str(e)}")
            return None

if __name__ == "__main__":
    create_default_admin()
