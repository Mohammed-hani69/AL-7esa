
"""
منصة الحصة التعليمية - نقطة الدخول الرئيسية للتطبيق
"""

import os
import sys
import logging
from app import app, socketio

# إعداد المسار الجذر للتطبيق
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(ROOT_DIR)

if __name__ == '__main__':
    try:
        # تشغيل التطبيق باستخدام SocketIO
        socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        logging.info("تم إيقاف الخادم بواسطة المستخدم")
    except Exception as e:
        logging.error(f"خطأ غير متوقع: {e}")
