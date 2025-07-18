#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نشر قواعد Firebase Firestore
"""

import subprocess
import sys
import os
import json
from firebase_config import get_firebase_config

def deploy_firestore_rules():
    """نشر قواعد Firestore"""
    try:
        print("🔥 بدء نشر قواعد Firebase Firestore...")
        
        # التحقق من وجود Firebase CLI
        try:
            result = subprocess.run(['firebase', '--version'], 
                                  capture_output=True, text=True, check=True)
            print(f"✅ Firebase CLI متوفر: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Firebase CLI غير مثبت. يرجى تثبيته أولاً:")
            print("npm install -g firebase-tools")
            return False
        
        # التحقق من تسجيل الدخول
        try:
            result = subprocess.run(['firebase', 'projects:list'], 
                                  capture_output=True, text=True, check=True)
            print("✅ تم تسجيل الدخول إلى Firebase")
        except subprocess.CalledProcessError:
            print("❌ يجب تسجيل الدخول إلى Firebase:")
            print("firebase login")
            return False
        
        # نشر القواعد
        try:
            result = subprocess.run(['firebase', 'deploy', '--only', 'firestore:rules'], 
                                  cwd=os.getcwd(), 
                                  capture_output=True, 
                                  text=True, 
                                  check=True)
            
            print("✅ تم نشر قواعد Firestore بنجاح!")
            print(result.stdout)
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ فشل في نشر القواعد: {e}")
            print(f"خطأ: {e.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ خطأ عام: {e}")
        return False

def create_firebase_json():
    """إنشاء ملف firebase.json إذا لم يكن موجوداً"""
    firebase_json_path = "firebase.json"
    
    if not os.path.exists(firebase_json_path):
        config = get_firebase_config()
        project_id = config.get('projectId', 'al-7esa-default')
        
        firebase_config = {
            "firestore": {
                "rules": "firestore.rules",
                "indexes": "firestore.indexes.json"
            },
            "hosting": {
                "public": "static",
                "ignore": [
                    "firebase.json",
                    "**/.*",
                    "**/node_modules/**"
                ]
            }
        }
        
        with open(firebase_json_path, 'w', encoding='utf-8') as f:
            json.dump(firebase_config, f, indent=2, ensure_ascii=False)
        
        print(f"✅ تم إنشاء {firebase_json_path}")
    else:
        print(f"✅ {firebase_json_path} موجود بالفعل")

def main():
    """الدالة الرئيسية"""
    print("🚀 بدء عملية نشر Firebase...")
    
    # إنشاء firebase.json
    create_firebase_json()
    
    # نشر القواعد
    if deploy_firestore_rules():
        print("🎉 تم نشر جميع مكونات Firebase بنجاح!")
    else:
        print("❌ فشل في نشر Firebase")
        sys.exit(1)

if __name__ == "__main__":
    main()
