#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نشر Firebase بشكل سريع
"""

import subprocess
import sys
import os

def quick_firebase_deploy():
    """نشر Firebase بشكل سريع"""
    print("🚀 نشر Firebase Rules...")
    
    try:
        # التحقق من Firebase CLI
        result = subprocess.run(['firebase', '--version'], 
                              capture_output=True, text=True, check=True)
        print(f"✅ Firebase CLI: {result.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Firebase CLI غير متوفر")
        print("تثبيت: npm install -g firebase-tools")
        return False
    
    try:
        # نشر القواعد
        print("📤 نشر Firestore Rules...")
        result = subprocess.run(['firebase', 'deploy', '--only', 'firestore:rules'], 
                              capture_output=True, text=True, check=True)
        
        print("✅ تم نشر Firebase Rules بنجاح!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ فشل النشر: {e}")
        
        # محاولة تسجيل الدخول
        print("🔑 محاولة تسجيل الدخول...")
        try:
            subprocess.run(['firebase', 'login'], check=True)
            print("✅ تم تسجيل الدخول")
            
            # إعادة المحاولة
            result = subprocess.run(['firebase', 'deploy', '--only', 'firestore:rules'], 
                                  capture_output=True, text=True, check=True)
            print("✅ تم النشر بعد تسجيل الدخول!")
            return True
            
        except subprocess.CalledProcessError:
            print("❌ فشل في تسجيل الدخول أو النشر")
            return False

if __name__ == "__main__":
    if quick_firebase_deploy():
        print("\n🎉 Firebase جاهز!")
        print("يمكنك الآن اختبار المحادثة")
    else:
        print("\n⚠️ يرجى نشر Firebase يدوياً:")
        print("1. firebase login")
        print("2. firebase deploy --only firestore:rules")
    
    sys.exit(0)
