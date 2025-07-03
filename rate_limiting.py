"""
نظام Rate Limiting للمنصة التعليمية AL-7esa
يحمي من الهجمات ويضمن توزيع عادل للموارد
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import current_app, request, jsonify, flash, redirect, url_for
from flask_login import current_user
import time
from functools import wraps

def get_user_identifier():
    """الحصول على معرف فريد للمستخدم أو IP"""
    if current_user and current_user.is_authenticated:
        return f"user_{current_user.id}"
    return f"ip_{get_remote_address()}"

def get_user_type():
    """تحديد نوع المستخدم لتطبيق حدود مختلفة"""
    if current_user and current_user.is_authenticated:
        return getattr(current_user, 'role', 'user')
    return 'anonymous'

# إعداد Flask-Limiter
def init_limiter(app):
    """تهيئة نظام Rate Limiting"""
    import os
    import logging
    
    # التحقق من تعطيل Rate Limiting عن طريق متغير بيئة
    if os.environ.get('DISABLE_RATE_LIMITING') == 'True':
        app.config['TESTING_RATE_LIMIT'] = False
        logging.info("Rate Limiting is disabled via environment variable")
        return None
    
    # إعداد التخزين (Redis إذا كان متاحاً، وإلا memory)
    storage_uri = app.config.get('RATE_LIMIT_STORAGE_URI', 'memory://')
    
    # حدود افتراضية مريحة
    default_limits = [
        "5000 per day",   # حد يومي عام مريح
        "1000 per hour",  # حد ساعي عام مريح للتصفح
        "200 per minute"  # حد دقيقي مريح للتصفح العادي
    ]
    
    try:
        limiter = Limiter(
            app=app,
            key_func=get_user_identifier,
            default_limits=default_limits,
            storage_uri=storage_uri,
            strategy="fixed-window",
            headers_enabled=True,
            swallow_errors=True,  # تجاهل الأخطاء في بيئة التطوير
            enabled=not (app.config.get('ENV') == 'development' and not app.config.get('TESTING_RATE_LIMIT', False))
        )
        
        # معالج أخطاء Rate Limiting
        @limiter.request_filter
        def ip_whitelist():
            """قائمة بيضاء للـ IPs (للصيانة) وتجاهل في بيئة التطوير"""
            # تجاهل Rate Limiting في بيئة التطوير
            if app.config.get('ENV') == 'development' or app.debug:
                return True
                
            whitelist = app.config.get('RATE_LIMIT_WHITELIST', [])
            return get_remote_address() in whitelist
        
        @app.errorhandler(429)
        def ratelimit_handler(e):
            """معالج خطأ تجاوز الحد المسموح"""
            if request.is_json:
                return jsonify({
                    'error': 'تم تجاوز الحد المسموح من الطلبات',
                    'message': 'يرجى المحاولة لاحقاً',
                    'retry_after': getattr(e, 'retry_after', None)
                }), 429
            else:
                flash('تم تجاوز الحد المسموح من الطلبات. يرجى المحاولة لاحقاً.', 'warning')
                return redirect(request.referrer or url_for('main.index'))
        
        # حفظ المرجع لسهولة الوصول
        app._limiter = limiter
        
        logging.info("Rate Limiting initialized successfully")
        return limiter
        
    except Exception as e:
        logging.error(f"Error initializing rate limiter: {e}")
        return None

# حدود مخصصة للعمليات المختلفة
RATE_LIMITS = {
    # عمليات المصادقة - حماية من Brute Force
    'auth_login': "5 per minute",
    'auth_register': "3 per minute", 
    'auth_reset_password': "3 per hour",
    'auth_verify_token': "10 per hour",
    'auth_page_access': "50 per minute",  # حماية خفيفة للصفحات العامة
    
    # عمليات المعلمين
    'teacher': {
        'create_classroom': "2 per hour",
        'start_stream': "3 per hour",
        'upload_content': "20 per hour",
        'grade_assignment': "50 per hour",
        'create_assignment': "5 per hour",
        'create_quiz': "3 per hour",
    },
    
    # عمليات الطلاب  
    'student': {
        'join_classroom': "5 per hour",
        'submit_assignment': "3 per hour",
        'send_message': "30 per hour",
        'take_quiz': "5 per hour",
    },
    
    # عمليات الملفات - حماية من رفع ملفات كثيرة
    'file_upload': "10 per hour",
    'file_download': "50 per hour",
    
    # عمليات المدفوعات - حماية من الاحتيال
    'payment_submit': "3 per hour",
    'payment_verify': "10 per hour",
    
    # عمليات المشرفين
    'admin_user_management': "50 per hour",
    'admin_system_settings': "20 per hour",
    
    # عمليات API
    'api_general': "100 per hour",
    'api_heavy': "20 per hour",
    
    # عمليات المشرفين
    'admin_user_management': "50 per hour",
    'admin_system_settings': "20 per hour",
}

def rate_limit_by_role(operation):
    """تطبيق Rate Limiting حسب نوع العملية ودور المستخدم"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            import os
            
            # التحقق من تعطيل Rate Limiting
            if os.environ.get('DISABLE_RATE_LIMITING') == 'True':
                return f(*args, **kwargs)
                
            user_type = get_user_type()
            base_limit = RATE_LIMITS.get(operation, "50 per hour")
            
            # حدود مختلفة حسب نوع المستخدم
            if user_type == 'ADMIN':
                # المشرفون لديهم حدود أعلى
                multiplier = 3
            elif user_type == 'TEACHER':
                # المعلمون لديهم حدود معقولة
                multiplier = 2
            elif user_type == 'STUDENT':
                # الطلاب لديهم حدود محدودة
                multiplier = 1
            elif user_type == 'ASSISTANT':
                # المساعدون لديهم حدود متوسطة
                multiplier = 1.5
            else:
                # المستخدمون غير المسجلين لديهم حدود صارمة
                multiplier = 0.5
            
            # حساب الحد النهائي
            base_count = int(base_limit.split()[0])
            period = ' '.join(base_limit.split()[1:])
            final_limit = f"{int(base_count * multiplier)} {period}"
            
            # تطبيق الحد
            try:
                limiter = current_app.extensions.get('limiter')
                if limiter and not (current_app.debug or current_app.config.get('ENV') == 'development'):
                    return limiter.limit(final_limit)(f)(*args, **kwargs)
            except Exception as e:
                import logging
                logging.warning(f"Rate limiting error: {e}")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Decorators جاهزة للاستخدام
def auth_rate_limit(f):
    """حد للعمليات المصادقة"""
    return rate_limit_by_role('auth_login')(f)

def teacher_rate_limit(f):
    """حد لعمليات المعلمين"""
    return rate_limit_by_role('teacher_create_classroom')(f)

def student_rate_limit(f):
    """حد لعمليات الطلاب"""
    return rate_limit_by_role('student_join_classroom')(f)

def upload_rate_limit(f):
    """حد لرفع الملفات"""
    return rate_limit_by_role('file_upload')(f)

def payment_rate_limit(f):
    """حد لعمليات المدفوعات"""
    return rate_limit_by_role('payment_submit')(f)

def admin_rate_limit(f):
    """حد لعمليات المشرفين"""
    return rate_limit_by_role('admin_user_management')(f)

# إعدادات خاصة بكل route
ROUTE_LIMITS = {
    # مسارات المصادقة
    'auth.login': RATE_LIMITS['auth_login'],
    'auth.register': RATE_LIMITS['auth_register'],
    'auth.verify_token': RATE_LIMITS['auth_verify_token'],
    
    # مسارات المعلمين
    'teacher.create_classroom': RATE_LIMITS['teacher']['create_classroom'],
    'teacher.start_stream': RATE_LIMITS['teacher']['start_stream'],
    'teacher.upload_content': RATE_LIMITS['teacher']['upload_content'],
    'teacher.create_assignment': RATE_LIMITS['teacher']['create_assignment'],
    'teacher.create_quiz': RATE_LIMITS['teacher']['create_quiz'],
    
    # مسارات الطلاب
    'student.join_classroom': RATE_LIMITS['student']['join_classroom'],
    'student.submit_assignment': RATE_LIMITS['student']['submit_assignment'],
    'student.process_payment': RATE_LIMITS['payment_submit'],
    
    # مسارات الملفات
    'upload_file': RATE_LIMITS['file_upload'],
    'download_file': RATE_LIMITS['file_download'],
}

def get_rate_limit_for_endpoint(endpoint):
    """الحصول على حد معين لـ endpoint محدد"""
    return ROUTE_LIMITS.get(endpoint, "50 per hour")

# دالة لمراقبة الاستخدام
def log_rate_limit_violation(user_id, endpoint, limit):
    """تسجيل انتهاكات Rate Limiting"""
    try:
        from datetime import datetime
        import logging
        
        logging.warning(f"Rate limit violation: User {user_id} exceeded {limit} for {endpoint} at {datetime.utcnow()}")
        
        # يمكن إضافة تخزين في قاعدة البيانات هنا
        # RateLimitViolation.create(user_id=user_id, endpoint=endpoint, limit=limit)
        
    except Exception as e:
        logging.error(f"Error logging rate limit violation: {e}")

# حماية خاصة للعمليات الحرجة
def critical_operation_limit(f):
    """حد صارم للعمليات الحرجة"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        limiter = current_app.extensions.get('limiter')
        if limiter:
            # حد صارم للعمليات الحرجة
            return limiter.limit("1 per minute")(f)(*args, **kwargs)
        return f(*args, **kwargs)
    return decorated_function

# دالة للعمليات المكلفة
def expensive_operation_limit(f):
    """حد للعمليات المكلفة"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        limiter = current_app.extensions.get('limiter')
        if limiter:
            return limiter.limit("5 per hour")(f)(*args, **kwargs)
        return f(*args, **kwargs)
    return decorated_function

# دالة للحصول على limiter من التطبيق - للاستيراد المباشر في الملفات الأخرى
def get_limiter():
    """الحصول على limiter من التطبيق الحالي"""
    try:
        from flask import current_app
        return getattr(current_app, '_limiter', None) or current_app.extensions.get('limiter')
    except Exception:
        return None

# دالة آمنة لتطبيق Rate Limiting
def apply_rate_limit(limit_key, default_limit="50 per hour"):
    """تطبيق Rate Limiting بطريقة آمنة"""
    try:
        import os
        import logging
        
        # تحقق من متغير البيئة لتعطيل Rate Limiting
        if os.environ.get('DISABLE_RATE_LIMITING') == 'True':
            return True
        
        from flask import current_app
        
        # تجاهل في بيئة التطوير إلا إذا تم تفعيل الاختبار
        if (current_app.debug or current_app.config.get('ENV') == 'development') and not current_app.config.get('TESTING_RATE_LIMIT'):
            return True
        
        # الحصول على limiter بطريقة آمنة
        limiter = getattr(current_app, '_limiter', None)
        if not limiter:
            limiter = current_app.extensions.get('limiter')
        
        if not limiter:
            logging.warning("Rate limiter not found, allowing request")
            return True  # لا يوجد limiter مُعرف، نسمح بالمتابعة
            
        # تحديد الحد المناسب
        limit = None
        if isinstance(limit_key, str):
            # البحث في الحدود العادية
            limit = RATE_LIMITS.get(limit_key)
            
            # إذا لم يتم العثور، نتحقق من وجود قسم فرعي
            if not limit and '.' in limit_key:
                main_key, sub_key = limit_key.split('.', 1)
                if main_key in RATE_LIMITS and isinstance(RATE_LIMITS[main_key], dict):
                    limit = RATE_LIMITS[main_key].get(sub_key)
        
        # استخدام الحد الافتراضي إذا لم يتم العثور على حد
        if not limit:
            limit = default_limit
        
        # تطبيق الحد بطريقة آمنة
        def dummy_function():
            return True
            
        try:
            limited_func = limiter.limit(limit)(dummy_function)
            return limited_func()
        except Exception as e:
            logging.warning(f"Error applying rate limit '{limit}' for key '{limit_key}': {e}")
            return True  # نسمح بالطلب في حالة الخطأ
        
    except Exception as e:
        # في حالة حدوث خطأ، نسمح بالمتابعة (fail-safe)
        import logging
        logging.warning(f"Rate limiting system error for {limit_key}: {e}")
        return True
