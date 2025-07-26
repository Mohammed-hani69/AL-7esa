#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
اختبار وتشغيل النظام المحدث
Test and Run Updated System
"""

import os
import subprocess
import sys

def check_and_install_requirements():
    """التحقق من المتطلبات وتثبيتها"""
    print("🔍 التحقق من المتطلبات...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ تم تثبيت المتطلبات بنجاح")
        return True
    except subprocess.CalledProcessError:
        print("❌ فشل في تثبيت المتطلبات")
        return False

def verify_database():
    """التحقق من قاعدة البيانات"""
    print("🗄️ التحقق من قاعدة البيانات...")
    try:
        import sqlite3
        conn = sqlite3.connect('instance/al-7esa.db')
        cursor = conn.cursor()
        
        # التحقق من وجود عمود google_id
        cursor.execute("PRAGMA table_info(user)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'google_id' in columns:
            print("✅ عمود google_id موجود")
        else:
            print("⚠️ عمود google_id غير موجود - سيتم إضافته")
            cursor.execute("ALTER TABLE user ADD COLUMN google_id VARCHAR(100)")
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_user_google_id ON user (google_id)")
            conn.commit()
            print("✅ تم إضافة عمود google_id")
        
        # التحقق من جدول الحضور
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='attendance'")
        if cursor.fetchone():
            print("✅ جدول الحضور موجود")
        else:
            print("⚠️ جدول الحضور غير موجود - قد تحتاج لتشغيل migrations")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ خطأ في قاعدة البيانات: {e}")
        return False

def check_file_structure():
    """التحقق من هيكل الملفات"""
    print("📁 التحقق من هيكل الملفات...")
    
    required_files = [
        'routes/attendance.py',
        'templates/attendance/mark_attendance.html',
        'templates/attendance/attendance_report.html',
        'static/js/attendance-system.js',
        'ATTENDANCE_SYSTEM_GUIDE.md'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
        else:
            print(f"✅ {file_path}")
    
    if missing_files:
        print(f"❌ ملفات مفقودة: {missing_files}")
        return False
    
    print("✅ جميع الملفات المطلوبة موجودة")
    return True

def test_imports():
    """اختبار استيراد الوحدات"""
    print("🐍 اختبار استيراد الوحدات...")
    
    try:
        from routes.attendance import attendance_bp
        print("✅ وحدة الحضور")
        
        from models import User, Attendance, Classroom
        print("✅ نماذج قاعدة البيانات")
        
        import flask_login
        print("✅ Flask-Login")
        
        from google.oauth2 import id_token
        print("✅ Google OAuth")
        
        return True
        
    except ImportError as e:
        print(f"❌ خطأ في الاستيراد: {e}")
        return False

def check_google_oauth_config():
    """التحقق من إعدادات Google OAuth"""
    print("🔑 التحقق من إعدادات Google OAuth...")
    
    config_files = [
        'google_oauth_config.json',
        'google_config.py',
        'firebase_config.py'
    ]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"✅ {config_file}")
        else:
            print(f"⚠️ {config_file} غير موجود")
    
    try:
        from firebase_config import firebase_config
        client_id = firebase_config.get_google_client_id()
        if client_id:
            print("✅ Google Client ID متاح")
        else:
            print("⚠️ Google Client ID غير متاح")
        return True
    except Exception as e:
        print(f"❌ خطأ في إعدادات Google: {e}")
        return False

def run_system_check():
    """تشغيل فحص شامل للنظام"""
    print("=" * 60)
    print("🚀 بدء فحص النظام المحدث")
    print("=" * 60)
    
    checks = [
        ("المتطلبات", check_and_install_requirements),
        ("قاعدة البيانات", verify_database),
        ("هيكل الملفات", check_file_structure),
        ("استيراد الوحدات", test_imports),
        ("إعدادات Google OAuth", check_google_oauth_config)
    ]
    
    passed = 0
    total = len(checks)
    
    for check_name, check_func in checks:
        print(f"\n📋 فحص {check_name}...")
        if check_func():
            passed += 1
        else:
            print(f"❌ فشل فحص {check_name}")
    
    print("\n" + "=" * 60)
    print(f"📊 نتائج الفحص: {passed}/{total} اختبار نجح")
    
    if passed == total:
        print("🎉 النظام جاهز للتشغيل!")
        print("\n📋 خطوات التشغيل:")
        print("1. python app.py")
        print("2. افتح المتصفح على http://localhost:5000")
        print("3. سجل دخول كمعلم أو مساعد لاختبار نظام الحضور")
        print("4. سجل دخول كطالب لاختبار التحقق من رقم ولي الأمر")
        
        print("\n🔗 مسارات مهمة:")
        print("- تسجيل الحضور: /attendance/mark/{classroom_id}")
        print("- تقرير الحضور: /attendance/report/{classroom_id}")
        print("- معلومات الطالب: /attendance/student-info/{student_id}")
        
    else:
        print("⚠️ يحتاج النظام لإصلاحات قبل التشغيل")
        print("راجع الأخطاء أعلاه وقم بإصلاحها")
    
    print("=" * 60)

def create_test_data():
    """إنشاء بيانات تجريبية للاختبار"""
    print("📊 إنشاء بيانات تجريبية...")
    
    try:
        from app import app
        from models import db, User, Classroom, ClassroomEnrollment
        from datetime import datetime
        
        with app.app_context():
            # التحقق من وجود مستخدمين
            if User.query.count() == 0:
                print("⚠️ لا توجد مستخدمين في النظام")
                print("يرجى إنشاء مستخدمين من خلال واجهة التسجيل")
            else:
                print(f"✅ يوجد {User.query.count()} مستخدم في النظام")
            
            # التحقق من وجود فصول
            if Classroom.query.count() == 0:
                print("⚠️ لا توجد فصول في النظام")
                print("يرجى إنشاء فصول من خلال لوحة تحكم المعلم")
            else:
                print(f"✅ يوجد {Classroom.query.count()} فصل في النظام")
                
        return True
        
    except Exception as e:
        print(f"❌ خطأ في التحقق من البيانات: {e}")
        return False

if __name__ == "__main__":
    run_system_check()
    print("\n" + "=" * 60)
    create_test_data()
