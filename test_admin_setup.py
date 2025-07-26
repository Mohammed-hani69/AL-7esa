#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
اختبار إنشاء المستخدم الإداري الجديد
Test new admin user creation
"""

import os
import sys
from app import app, db
from models import User, Role
from init_admin import create_default_admin

def test_admin_creation():
    """اختبار إنشاء المسؤولين"""
    print("🧪 اختبار إنشاء حسابات المسؤولين...")
    print("=" * 60)
    
    with app.app_context():
        # استدعاء دالة إنشاء المسؤولين
        result = create_default_admin()
        
        print("\n" + "=" * 60)
        print("📊 التحقق من النتائج...")
        
        # عرض جميع المستخدمين الإداريين
        admins = User.query.filter_by(role=Role.ADMIN).all()
        
        if not admins:
            print("❌ لا يوجد مستخدمين إداريين في النظام")
            return False
        
        print(f"✅ تم العثور على {len(admins)} مسؤول(ين):")
        print("-" * 40)
        
        for admin in admins:
            print(f"👤 الاسم: {admin.name}")
            print(f"📱 الهاتف: {admin.phone}")
            print(f"📧 البريد: {admin.email}")
            print(f"🎭 الدور: {admin.role}")
            print(f"✅ نشط: {'نعم' if admin.is_active else 'لا'}")
            print(f"🔐 مُفعل: {'نعم' if admin.is_verified else 'لا'}")
            
            # اختبار كلمة المرور
            if admin.check_password("zxc65432"):
                print("🔑 كلمة المرور: صحيحة ✅")
            else:
                print("🔑 كلمة المرور: خطأ ❌")
            print("-" * 40)
        
        return True

def test_login_simulation():
    """محاكاة تسجيل الدخول"""
    print("\n🔐 محاكاة تسجيل الدخول للمسؤولين...")
    print("=" * 60)
    
    test_credentials = [
        ("01033607749", "zxc65432", "عبدالعزيز هاني"),
        ("01145425207", "zxc65432", "محمد هاني عبدالعزيز")
    ]
    
    with app.app_context():
        for phone, password, expected_name in test_credentials:
            print(f"\n🧪 اختبار: {phone}")
            
            user = User.query.filter_by(phone=phone).first()
            if not user:
                print(f"❌ المستخدم غير موجود")
                continue
            
            if user.check_password(password):
                print(f"✅ تسجيل الدخول نجح")
                print(f"   الاسم: {user.name}")
                print(f"   الدور: {user.role}")
                print(f"   نشط: {'نعم' if user.is_active else 'لا'}")
                
                if user.name == expected_name:
                    print(f"✅ الاسم صحيح: {expected_name}")
                else:
                    print(f"⚠️ الاسم مختلف: متوقع '{expected_name}', موجود '{user.name}'")
            else:
                print(f"❌ تسجيل الدخول فشل - كلمة مرور خاطئة")

def main():
    """الدالة الرئيسية للاختبار"""
    print("🚀 بدء اختبار النظام")
    print("🎯 الهدف: التحقق من إنشاء المستخدم الإداري الجديد")
    print("👤 البيانات المطلوبة:")
    print("   الاسم: عبدالعزيز هاني")
    print("   الهاتف: 01033607749")
    print("   كلمة المرور: zxc65432")
    print("\n" + "=" * 60)
    
    # اختبار إنشاء المسؤولين
    test_admin_creation()
    
    # اختبار تسجيل الدخول
    test_login_simulation()
    
    print("\n" + "=" * 60)
    print("✨ انتهى الاختبار")
    print("\n📋 معلومات تسجيل الدخول:")
    print("🔗 الرابط: http://localhost:5000/auth/login")
    print("\n👥 حسابات المسؤولين:")
    print("1️⃣ عبدالعزيز هاني - 01033607749 - zxc65432")
    print("2️⃣ محمد هاني عبدالعزيز - 01145425207 - zxc65432")

if __name__ == "__main__":
    main()
