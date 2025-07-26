#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
إصلاح حساب المسؤول المُنشأ بشكل خاطئ
Fix incorrectly created admin account
"""

import os
import sys
from app import app, db
from models import User, Role
from datetime import datetime

def fix_admin_account():
    """إصلاح حساب المسؤول"""
    with app.app_context():
        print("🔍 البحث عن الحساب المُنشأ بشكل خاطئ...")
        
        # البحث عن المستخدم برقم الهاتف "zezo"
        wrong_user = User.query.filter_by(phone="zezo").first()
        
        if wrong_user:
            print(f"✅ تم العثور على الحساب الخاطئ:")
            print(f"   الاسم: {wrong_user.name}")
            print(f"   الهاتف: {wrong_user.phone}")
            print(f"   الدور: {wrong_user.role}")
            
            # حذف الحساب الخاطئ
            db.session.delete(wrong_user)
            print("🗑️ تم حذف الحساب الخاطئ")
        else:
            print("❌ لم يتم العثور على حساب برقم الهاتف 'zezo'")
        
        # إنشاء حساب المسؤول الصحيح
        print("\n📝 إنشاء حساب المسؤول الصحيح...")
        
        # التحقق من وجود مستخدم برقم الهاتف الصحيح
        correct_phone = "01145425207"
        existing_admin = User.query.filter_by(phone=correct_phone).first()
        
        if existing_admin:
            print(f"⚠️ يوجد مستخدم بالفعل برقم الهاتف {correct_phone}")
            print(f"   الاسم: {existing_admin.name}")
            print(f"   الدور: {existing_admin.role}")
            
            # تحديث الدور إلى مسؤول إذا لم يكن كذلك
            if existing_admin.role != Role.ADMIN:
                existing_admin.role = Role.ADMIN
                existing_admin.is_active = True
                existing_admin.is_verified = True
                db.session.commit()
                print("✅ تم تحديث الدور إلى مسؤول")
            else:
                print("✅ المستخدم مسؤول بالفعل")
        else:
            # إنشاء مستخدم جديد
            admin = User(
                name="zxc65432",  # الاسم الذي تم إدخاله
                phone=correct_phone,
                role=Role.ADMIN,
                is_active=True,
                is_verified=True,
                created_at=datetime.utcnow()
            )
            
            # تعيين كلمة المرور (نفس كلمة المرور التي أدخلتها)
            admin.set_password("zxc65432")
            
            db.session.add(admin)
            print("✅ تم إنشاء حساب المسؤول الجديد")
        
        # حفظ التغييرات
        db.session.commit()
        
        print("\n🎉 تم إصلاح المشكلة بنجاح!")
        print("\nمعلومات تسجيل الدخول:")
        print(f"رقم الهاتف: {correct_phone}")
        print(f"كلمة المرور: zxc65432")
        print(f"الدور: مسؤول النظام")

def list_all_users():
    """عرض جميع المستخدمين"""
    with app.app_context():
        print("\n📋 قائمة جميع المستخدمين:")
        print("-" * 50)
        
        users = User.query.all()
        if not users:
            print("❌ لا يوجد مستخدمين في النظام")
            return
        
        for user in users:
            print(f"🆔 ID: {user.id}")
            print(f"👤 الاسم: {user.name}")
            print(f"📱 الهاتف: {user.phone}")
            print(f"🎭 الدور: {user.role}")
            print(f"✅ نشط: {'نعم' if user.is_active else 'لا'}")
            print(f"🔐 مُفعل: {'نعم' if user.is_verified else 'لا'}")
            print("-" * 30)

if __name__ == "__main__":
    print("🔧 بدء إصلاح حساب المسؤول...")
    print("=" * 50)
    
    fix_admin_account()
    list_all_users()
    
    print("\n" + "=" * 50)
    print("✨ تم الانتهاء من الإصلاح")
    print("\nيمكنك الآن تسجيل الدخول باستخدام:")
    print("رقم الهاتف: 01145425207")
    print("كلمة المرور: zxc65432")
