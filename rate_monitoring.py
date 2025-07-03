#!/usr/bin/env python3
"""
مراقب Rate Limiting - تسجيل أحداث Rate Limiting أثناء التشغيل
"""

import logging
from datetime import datetime
from flask import request, session
from flask_login import current_user
import os

# إعداد ملف تسجيل منفصل لـ Rate Limiting
RATE_LIMIT_LOG_FILE = os.path.join(os.path.dirname(__file__), 'logs', 'rate_limiting.log')

# إنشاء مجلد logs إذا لم يكن موجوداً
os.makedirs(os.path.dirname(RATE_LIMIT_LOG_FILE), exist_ok=True)

# إعداد logger منفصل
rate_logger = logging.getLogger('rate_limiting')
rate_logger.setLevel(logging.INFO)

# إعداد file handler
file_handler = logging.FileHandler(RATE_LIMIT_LOG_FILE, encoding='utf-8')
file_handler.setLevel(logging.INFO)

# إعداد format
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)

# إضافة handler إلى logger
if not rate_logger.handlers:
    rate_logger.addHandler(file_handler)

def log_rate_limit_hit(limit_type, user_info=None, ip_address=None):
    """تسجيل حدث تجاوز Rate Limit"""
    
    user_id = "anonymous"
    user_role = "guest"
    
    if current_user and current_user.is_authenticated:
        user_id = current_user.id
        user_role = getattr(current_user, 'role', 'user')
    
    if not ip_address:
        ip_address = request.remote_addr if request else "unknown"
    
    message = f"RATE_LIMIT_HIT - Type: {limit_type} - User: {user_id} ({user_role}) - IP: {ip_address}"
    
    if user_info:
        message += f" - Info: {user_info}"
    
    rate_logger.warning(message)

def log_rate_limit_success(limit_type, user_info=None):
    """تسجيل عملية ناجحة (ضمن الحد المسموح)"""
    
    user_id = "anonymous"
    user_role = "guest"
    
    if current_user and current_user.is_authenticated:
        user_id = current_user.id
        user_role = getattr(current_user, 'role', 'user')
    
    ip_address = request.remote_addr if request else "unknown"
    
    message = f"RATE_LIMIT_OK - Type: {limit_type} - User: {user_id} ({user_role}) - IP: {ip_address}"
    
    if user_info:
        message += f" - Info: {user_info}"
    
    rate_logger.info(message)

def get_rate_limit_stats():
    """الحصول على إحصائيات Rate Limiting من ملف التسجيل"""
    
    stats = {
        'total_hits': 0,
        'total_success': 0,
        'by_type': {},
        'by_user': {},
        'recent_events': []
    }
    
    try:
        if os.path.exists(RATE_LIMIT_LOG_FILE):
            with open(RATE_LIMIT_LOG_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
                for line in lines[-100:]:  # آخر 100 سطر
                    if 'RATE_LIMIT_HIT' in line:
                        stats['total_hits'] += 1
                        stats['recent_events'].append(line.strip())
                    elif 'RATE_LIMIT_OK' in line:
                        stats['total_success'] += 1
                        
    except Exception as e:
        rate_logger.error(f"Error reading rate limit stats: {e}")
    
    return stats

# دالة لمراقبة الحالة الحالية
def print_current_status():
    """طباعة حالة Rate Limiting الحالية"""
    
    stats = get_rate_limit_stats()
    
    print("\n" + "="*50)
    print("📊 Rate Limiting Status Report")
    print("="*50)
    print(f"✅ Successful operations: {stats['total_success']}")
    print(f"⚠️  Rate limit hits: {stats['total_hits']}")
    
    if stats['recent_events']:
        print("\n🔴 Recent Rate Limit Events:")
        for event in stats['recent_events'][-5:]:  # آخر 5 أحداث
            print(f"  {event}")
    
    print("="*50)

if __name__ == "__main__":
    print_current_status()
