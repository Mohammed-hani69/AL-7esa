
"""
منصة الحصة التعليمية - نقطة الدخول الرئيسية للتطبيق
"""

import os
import sys
import logging
from app import app

# إعداد المسار الجذر للتطبيق
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(ROOT_DIR)

if __name__ == '__main__':
    try:
        # تهيئة قاعدة البيانات وإنشاء المسؤولين
        with app.app_context():
            from models import db
            from init_admin import create_default_admin
            
            # إنشاء الجداول إذا لم تكن موجودة
            db.create_all()
            
            # إنشاء حسابات المسؤولين
            create_default_admin()
        
        # تشغيل التطبيق باستخدام Flask العادي
        app.run(host='0.0.0.0', port=5000, debug=True)
    except KeyboardInterrupt:
        logging.info("تم إيقاف الخادم بواسطة المستخدم")
    except Exception as e:
        logging.error(f"خطأ غير متوقع: {e}")
