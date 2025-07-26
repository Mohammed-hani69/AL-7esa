#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
اختبار سريع لإنشاء المسؤولين وحل مشكلة البريد الإلكتروني
Quick test for admin creation and email duplicate fix
"""

import os
import sys

# إضافة المسار الحالي
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_admin_creation():
    """اختبار إنشاء المسؤولين"""
    print("🧪 اختبار إنشاء حسابات المسؤولين...")
    print("🎯 الهدف: التأكد من حل مشكلة البريد الإلكتروني المكرر")
    print("=" * 60)
    
    try:
        from app import app, db
        from models import User, Role
        from init_admin import create_default_admin
        
        with app.app_context():
            print("📊 عدد المستخدمين قبل الاختبار:")
            admins_before = User.query.filter_by(role=Role.ADMIN).all()
            print(f"   المسؤولين: {len(admins_before)}")
            
            for admin in admins_before:
                print(f"   - {admin.name} ({admin.phone}) - {admin.email}")
            
            print("\n🔧 تشغيل دالة إنشاء المسؤولين...")
            result = create_default_admin()
            
            print("\n📊 عدد المستخدمين بعد الاختبار:")
            admins_after = User.query.filter_by(role=Role.ADMIN).all()
            print(f"   المسؤولين: {len(admins_after)}")
            
            for admin in admins_after:
                print(f"   - {admin.name} ({admin.phone}) - {admin.email}")
            
            print("\n✅ الاختبار مكتمل!")
            
            # التحقق من المستخدم الجديد تحديداً
            new_admin = User.query.filter_by(phone="01033607749").first()
            if new_admin:
                print(f"\n🎉 تم العثور على المستخدم الجديد:")
                print(f"   الاسم: {new_admin.name}")
                print(f"   الهاتف: {new_admin.phone}")
                print(f"   البريد الإلكتروني: {new_admin.email}")
                print(f"   الدور: {new_admin.role}")
                print(f"   نشط: {'نعم' if new_admin.is_active else 'لا'}")
                print(f"   مُفعل: {'نعم' if new_admin.is_verified else 'لا'}")
            else:
                print("❌ لم يتم العثور على المستخدم الجديد")
            
            return True
            
    except Exception as e:
        print(f"❌ خطأ في الاختبار: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_login():
    """اختبار تسجيل الدخول"""
    print("\n🔐 اختبار تسجيل الدخول...")
    print("=" * 40)
    
    try:
        from app import app
        from models import User
        
        with app.app_context():
            # اختبار تسجيل الدخول للمستخدم الجديد
            admin = User.query.filter_by(phone="01033607749").first()
            if admin:
                password_test = admin.check_password("zxc65432")
                print(f"✅ اختبار كلمة المرور: {'نجح' if password_test else 'فشل'}")
                
                if password_test:
                    print("🎯 بيانات تسجيل الدخول:")
                    print(f"   رقم الهاتف: 01033607749")
                    print(f"   كلمة المرور: zxc65432")
                    print(f"   الرابط: http://localhost:5000/auth/login")
            else:
                print("❌ لم يتم العثور على المستخدم")
                
    except Exception as e:
        print(f"❌ خطأ في اختبار تسجيل الدخول: {str(e)}")

def main():
    """الدالة الرئيسية"""
    print("🚀 بدء اختبار النظام بعد الإصلاح")
    print("📅 التاريخ: 26 يوليو 2025")
    print("🎯 الهدف: التأكد من إنشاء المستخدم 'عبدالعزيز هاني' بنجاح")
    print("\n" + "=" * 70)
    
    success = test_admin_creation()
    
    if success:
        test_login()
    
    print("\n" + "=" * 70)
    print("✨ انتهى الاختبار")
    
    if success:
        print("🎉 النتيجة: نجح الاختبار!")
        print("\n💡 الخطوة التالية:")
        print("   1. شغل الخادم: python app.py")
        print("   2. افتح المتصفح: http://localhost:5000/auth/login")
        print("   3. سجل الدخول بالبيانات المعروضة أعلاه")
    else:
        print("❌ النتيجة: فشل الاختبار!")

if __name__ == "__main__":
    main()
