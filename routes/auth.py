"""
مسارات المصادقة (auth)
التحكم في تسجيل الدخول والخروج وتسجيل المستخدمين الجدد
"""

import re
import os
import json
import requests
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFError
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from firebase_utils import verify_firebase_token
from models import Role, Subscription, SubscriptionPlan, SystemSettings, User, Notification, db
import re
from firebase_config import firebase_config
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from urllib.parse import urlencode

# Load Google OAuth configuration
def get_google_client_id():
    """الحصول على Google Client ID حسب البيئة"""
    return firebase_config.get_google_client_id()

def get_google_oauth_settings():
    """الحصول على إعدادات Google OAuth"""
    return firebase_config.get_google_oauth_settings()

# تحديث متغيرات Google OAuth
google_settings = get_google_oauth_settings()
GOOGLE_CLIENT_ID = google_settings.get('client_id') if google_settings else None
GOOGLE_CLIENT_SECRET = google_settings.get('client_secret') if google_settings else None

# تحديد redirect URI بناءً على البيئة
def get_google_redirect_uri():
    """الحصول على redirect URI المناسب للبيئة"""
    oauth_settings = get_google_oauth_settings()
    if not oauth_settings or 'redirect_uris' not in oauth_settings:
        return None
    
    redirect_uris = oauth_settings['redirect_uris']
    
    # التحقق من البيئة بناءً على الطلب
    if request:
        host = request.headers.get('Host', '')
        if firebase_config.is_production_domain(host):
            # استخدام URI الإنتاج
            return next((uri for uri in redirect_uris if 'al-7esa.com' in uri), redirect_uris[0])
        else:
            # استخدام URI التطوير
            return next((uri for uri in redirect_uris if 'localhost' in uri or '127.0.0.1' in uri), redirect_uris[-1])
    
    return redirect_uris[0]

# دالة للتحقق من نوع الجهاز (موبايل أو جهاز مكتبي)
def is_mobile():
    user_agent = request.headers.get('User-Agent', '').lower()
    mobile_patterns = [
        'android', 'iphone', 'ipod', 'windows phone', 'mobile', 'tablet',
        'blackberry', 'opera mini', 'opera mobi', 'webos', 'fennec'
    ]
    return any(pattern in user_agent for pattern in mobile_patterns)

# Custom decorator to skip CSRF for specific routes
def csrf_exempt(f):
    """Decorator to exempt a route from CSRF protection"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    
    # Mark the function as CSRF exempt for Flask-WTF
    decorated_function._csrf_exempt = True
    # Also add the Flask-WTF specific attribute
    decorated_function.csrf_exempt = True
    
    return decorated_function

auth_bp = Blueprint('auth', __name__)

# CSRF error handler
@auth_bp.errorhandler(CSRFError)
def handle_csrf_error(e):
    from flask import request, jsonify
    from flask_wtf.csrf import generate_csrf
    
    # Check if this is an AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('Content-Type') == 'application/json':
        return jsonify({
            'error': 'csrf_token_expired',
            'message': 'انتهت صلاحية النموذج. يرجى إعادة تحميل الصفحة والمحاولة مرة أخرى.',
            'csrf_token': generate_csrf()
        }), 400
    else:
        flash('انتهت صلاحية النموذج. يرجى إعادة تحميل الصفحة والمحاولة مرة أخرى.', 'danger')
        return redirect(url_for('auth.login'))

# Route to get fresh CSRF token
@auth_bp.route('/csrf-token')
def get_csrf_token():
    from flask_wtf.csrf import generate_csrf
    return jsonify({'csrf_token': generate_csrf()})

class LoginForm(FlaskForm):
    phone = StringField('رقم الهاتف', validators=[DataRequired()])
    password = PasswordField('كلمة المرور', validators=[DataRequired()])
    submit = SubmitField('تسجيل الدخول')

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """صفحة التسجيل الرئيسية بالنظام المتدرج"""
    # الحصول على Google Client ID المناسب للبيئة
    current_google_client_id = get_google_client_id()
    
    template = 'auth/auth-mobile/register.html' if is_mobile() else 'auth/register.html'
    return render_template(template, google_client_id=current_google_client_id)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """صفحة تسجيل الدخول"""
    if current_user.is_authenticated:
        # توجيه المستخدم حسب دوره
        redirect_urls = {
            'admin': url_for('admin.dashboard'),
            'teacher': url_for('teacher.dashboard'),
            'student': url_for('student.dashboard'),
            'assistant': url_for('assistant.dashboard')
        }
        return redirect(redirect_urls.get(current_user.role, url_for('main.index')))
    
    # الحصول على Google Client ID المناسب للبيئة
    current_google_client_id = get_google_client_id()
    
    template = 'auth/auth-mobile/login.html' if is_mobile() else 'auth/login.html'
    return render_template(template, google_client_id=current_google_client_id)

@auth_bp.route('/login-step', methods=['POST'])
@csrf_exempt
def login_step():
    """معالجة تسجيل الدخول بنظام الخطوات - مع دعم CSRF"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'بيانات غير صالحة'})

        phone = data.get('phone')
        password = data.get('password')

        # التحقق من وجود البيانات المطلوبة
        if not phone or not password:
            return jsonify({'success': False, 'message': 'رقم الهاتف وكلمة المرور مطلوبان'})

        # تنظيف رقم الهاتف
        phone = re.sub(r'\D', '', phone)
        if not phone.startswith('01') or len(phone) != 11:
            return jsonify({'success': False, 'message': 'رقم الهاتف غير صحيح. يجب أن يبدأ بـ 01 ويتكون من 11 رقم'})

        # البحث عن المستخدم
        user = User.query.filter_by(phone=phone).first()
        if not user:
            return jsonify({'success': False, 'message': 'رقم الهاتف غير مسجل في النظام'})

        # التحقق من كلمة المرور
        if not user.check_password(password):
            return jsonify({'success': False, 'message': '❌ كلمة المرور غير صحيحة. يرجى التأكد من كلمة المرور وإعادة المحاولة.'})

        # تسجيل دخول المستخدم مع ضمان استمرار الجلسة
        login_user(user, remember=True, duration=timedelta(days=7))
        
        # التأكد من تحديث الجلسة
        session.permanent = True
        session['user_id'] = user.id
        session['user_role'] = user.role
        session['user_name'] = user.name
        session.modified = True
        
        # فرض حفظ الجلسة
        db.session.commit()
        
        # تحديث آخر نشاط للمستخدم
        user.updated_at = datetime.utcnow()
        db.session.commit()

        # تحديد وجهة التوجيه حسب الدور
        redirect_urls = {
            'admin': url_for('admin.dashboard'),
            'teacher': url_for('teacher.dashboard'),
            'student': url_for('student.dashboard'),
            'assistant': url_for('assistant.dashboard')
        }

        redirect_url = redirect_urls.get(user.role, url_for('main.index'))

        # إضافة flash message للترحيب
        flash(f'مرحباً بعودتك {user.name}! 👋', 'success')

        # التوجه المباشر من الباك إند - بدون الحاجة للجافا سكريبت
        return jsonify({
            'success': True,
            'message': f'تم تسجيل الدخول بنجاح',
            'redirect_url': redirect_url,
            'user': {
                'name': user.name,
                'role': user.role,
                'id': user.id
            },
            'direct_redirect': True,  # إشارة للفرونت إند للتوجه فوراً
            'force_redirect': True   # إجبار التوجه الفوري
        })

    except Exception as e:
        current_app.logger.error(f"Login error: {str(e)}")
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء تسجيل الدخول'})

    except Exception as e:
        current_app.logger.error(f"Login error: {str(e)}")
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء تسجيل الدخول'})

@auth_bp.route('/verify-token', methods=['POST'])
def verify_token():
    """توجيه للنظام الحديث"""
    return jsonify({'error': 'هذا النظام لم يعد مستخدماً، يرجى استخدام النظام الحديث'}), 410

@auth_bp.route('/complete-registration', methods=['GET', 'POST'])
def complete_registration():
    """توجيه للنظام الحديث"""
    flash('يرجى استخدام نظام التسجيل الحديث', 'warning')
    return redirect(url_for('auth.register'))

"""
مسارات Google Sign-In
"""
@auth_bp.route('/google-signin', methods=['POST'])
@csrf_exempt
def google_signin():
    """معالجة تسجيل الدخول بـ Google"""
    try:
        data = request.get_json()
        if not data or 'credential' not in data:
            return jsonify({'success': False, 'message': 'بيانات غير صالحة'})
        
        # التحقق من الرمز المميز
        current_google_client_id = get_google_client_id()
        if not current_google_client_id:
            return jsonify({'success': False, 'message': 'تسجيل الدخول بـ جوجل غير متاح حالياً'})
        
        idinfo = id_token.verify_oauth2_token(
            data['credential'], 
            google_requests.Request(), 
            current_google_client_id
        )
        
        # استخراج معلومات المستخدم
        google_id = idinfo['sub']
        email = idinfo.get('email')
        name = idinfo.get('name')
        picture = idinfo.get('picture')
        
        if not email:
            return jsonify({'success': False, 'message': 'لم يتم العثور على البريد الإلكتروني'})
        
        # البحث عن مستخدم موجود بنفس البريد الإلكتروني
        user = User.query.filter_by(email=email).first()
        
        if user:
            # تحديث معلومات Google إذا لم تكن موجودة
            if not user.google_id:
                user.google_id = google_id
            if not user.profile_picture and picture:
                user.profile_picture = picture
            
            db.session.commit()
            
            # تسجيل دخول المستخدم
            login_user(user, remember=True, duration=timedelta(days=7))
            
            # التأكد من تحديث الجلسة
            session.permanent = True
            session['user_id'] = user.id
            session['user_role'] = user.role
            session['user_name'] = user.name
            session.modified = True
            
            # فرض حفظ الجلسة
            db.session.commit()
            
            # تحديد وجهة التوجيه حسب الدور
            redirect_urls = {
                'admin': url_for('admin.dashboard'),
                'teacher': url_for('teacher.dashboard'),
                'student': url_for('student.dashboard'),
                'assistant': url_for('assistant.dashboard')
            }
            
            redirect_url = redirect_urls.get(user.role, url_for('main.index'))
            
            # إضافة flash message للترحيب
            flash(f'مرحباً بعودتك {user.name}! 👋', 'success')
            
            return jsonify({
                'success': True,
                'message': f'تم تسجيل الدخول بنجاح',
                'redirect_url': redirect_url,
                'user': {
                    'name': user.name,
                    'role': user.role,
                    'id': user.id
                },
                'direct_redirect': True  # إشارة للفرونت إند للتوجه فوراً
            })
        else:
            # إذا لم يكن المستخدم موجود، توجيهه للتسجيل
            return jsonify({
                'success': False, 
                'message': 'لم يتم العثور على حساب مرتبط بهذا البريد الإلكتروني. يرجى إنشاء حساب جديد أولاً.',
                'require_registration': True
            })
            
    except ValueError as e:
        current_app.logger.error(f"Google Sign-In token verification error: {str(e)}")
        return jsonify({'success': False, 'message': 'رمز Google غير صالح'})
    except Exception as e:
        current_app.logger.error(f"Google Sign-In error: {str(e)}")
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء تسجيل الدخول بـ جوجل'})

"""
مسار تسجيل الخروج (Logout)
تسجيل خروج المستخدم وإنهاء الجلسة
"""
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    template = 'auth/auth-mobile/profile.html' if is_mobile() else 'auth/profile.html'
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email') or None  # Convert empty string to None
        alt_phone = request.form.get('alt_phone') or None
        address = request.form.get('address') or None
        interests = request.form.get('interests') or None
        
        # التحقق من رقم هاتف ولي الأمر للطلاب
        if current_user.role == 'student':
            if not alt_phone:
                flash('رقم هاتف ولي الأمر مطلوب للطلاب', 'danger')
                return redirect(url_for('auth.profile'))
            
            # التحقق من صحة رقم هاتف ولي الأمر
            import re
            alt_phone_clean = re.sub(r'\D', '', alt_phone)
            if not alt_phone_clean.startswith('01') or len(alt_phone_clean) != 11:
                flash('رقم هاتف ولي الأمر غير صحيح. يجب أن يبدأ بـ 01 ويتكون من 11 رقم', 'danger')
                return redirect(url_for('auth.profile'))
            
            # حفظ رقم ولي الأمر في حقل parent_phone أيضاً للطلاب
            current_user.parent_phone = alt_phone
        
        # معالجة أرقام المحافظ للمعلمين
        if current_user.role == 'teacher':
            ewallet_number_1 = request.form.get('ewallet_number_1') or None
            ewallet_number_2 = request.form.get('ewallet_number_2') or None
            
            # تحديث أرقام المحافظ
            current_user.ewallet_number_1 = ewallet_number_1
            current_user.ewallet_number_2 = ewallet_number_2

        # Update user info
        current_user.name = name
        current_user.email = email
        current_user.alt_phone = alt_phone
        current_user.address = address
        current_user.interests = interests

        # Handle profile picture upload
        profile_pic = request.files.get('profile_picture')
        if profile_pic and profile_pic.filename:
            if allowed_file(profile_pic.filename):
                # Ensure filename is secure
                filename = secure_filename(profile_pic.filename)
                # Create unique filename with user ID
                unique_filename = f"{current_user.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{filename}"
                # Set the path for saving
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'profile_pictures')
                # Create directory if it doesn't exist
                os.makedirs(upload_folder, exist_ok=True)
                # Full path for the file
                filepath = os.path.join(upload_folder, unique_filename)

                try:
                    # Save the file
                    profile_pic.save(filepath)
                    # Update database with relative path
                    current_user.profile_picture = f"/static/uploads/profile_pictures/{unique_filename}"
                    flash('تم تحديث الصورة الشخصية بنجاح', 'success')
                except Exception as e:
                    flash('حدث خطأ أثناء حفظ الصورة', 'danger')
            else:
                flash('نوع الملف غير مسموح به. يرجى استخدام صور بامتداد: png, jpg, jpeg, gif', 'danger')

        current_user.updated_at = datetime.utcnow()
        db.session.commit()
        flash('تم تحديث الملف الشخصي بنجاح', 'success')
        return redirect(url_for('auth.profile'))
    
    # للMELLMين فقط: جلب الاشتراك النشط
    active_subscription = None
    if current_user.role == 'teacher':
        active_subscription = Subscription.query.filter(
            Subscription.user_id == current_user.id,
            Subscription.end_date > datetime.utcnow(),
            Subscription.is_active == True
        ).first()
    
    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي

    return render_template(template, now=datetime.utcnow(),
                           primary_color=primary_color,
                           secondary_color=secondary_color,
                           active_subscription=active_subscription)

@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """تغيير كلمة المرور للمستخدم الحالي"""
    try:
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # التحقق من أن جميع الحقول مملوءة
        if not all([current_password, new_password, confirm_password]):
            flash('يرجى ملء جميع الحقول', 'danger')
            return redirect(url_for('auth.profile'))
        
        # التحقق من كلمة المرور الحالية
        if not current_user.check_password(current_password):
            flash('كلمة المرور الحالية غير صحيحة', 'danger')
            return redirect(url_for('auth.profile'))
        
        # التحقق من تطابق كلمة المرور الجديدة
        if new_password != confirm_password:
            flash('كلمة المرور الجديدة وتأكيدها غير متطابقين', 'danger')
            return redirect(url_for('auth.profile'))
        
        # التحقق من طول كلمة المرور الجديدة
        if len(new_password) < 8:
            flash('يجب أن تكون كلمة المرور الجديدة 8 أحرف على الأقل', 'danger')
            return redirect(url_for('auth.profile'))
        
        # تحديث كلمة المرور
        current_user.set_password(new_password)
        current_user.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash('تم تغيير كلمة المرور بنجاح', 'success')
        return redirect(url_for('auth.profile'))
        
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ أثناء تغيير كلمة المرور', 'danger')
        return redirect(url_for('auth.profile'))

# ============================================
# تنظيف النظام - إزالة المسارات القديمة
# ============================================

@auth_bp.route('/verify-phone', methods=['POST'])
@csrf_exempt
def verify_phone():
    """التحقق من رقم الهاتف باستخدام Firebase"""
    try:
        data = request.get_json()
        id_token = data.get('idToken')
        name = data.get('name', '')
        user_type = data.get('userType', 'student')
        
        if not id_token:
            return jsonify({'success': False, 'message': 'رمز التحقق مطلوب'})
        
        # التحقق من الرمز مع Firebase
        decoded_token = firebase_config.verify_phone_token(id_token)
        
        if not decoded_token:
            return jsonify({'success': False, 'message': 'رمز التحقق غير صحيح'})
        
        firebase_uid = decoded_token['uid']
        phone_number = decoded_token.get('phone_number')
        
        if not phone_number:
            return jsonify({'success': False, 'message': 'رقم الهاتف غير متوفر'})
        
        # البحث عن المستخدم الحالي
        user = User.query.filter_by(firebase_uid=firebase_uid).first()
        
        if user:
            # تسجيل دخول المستخدم الموجود
            if not user.is_verified:
                user.is_verified = True
                db.session.commit()
            
            login_user(user)
            
            return jsonify({
                'success': True, 
                'message': 'تم تسجيل الدخول بنجاح',
                'redirect_url': url_for(f'{user.role}.dashboard'),
                'user': {
                    'name': user.name,
                    'role': user.role,
                    'id': user.id
                },
                'direct_redirect': True,
                'force_redirect': True
            })
        else:
            # إنشاء مستخدم جديد
            if not name:
                return jsonify({'success': False, 'message': 'الاسم مطلوب للتسجيل'})
            
            new_user = User(
                name=name,
                phone=phone_number,
                role=user_type,
                firebase_uid=firebase_uid,
                is_verified=True
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            login_user(new_user)
            
            return jsonify({
                'success': True,
                'message': 'تم إنشاء الحساب بنجاح',
                'redirect_url': url_for(f'{new_user.role}.dashboard'),
                'user': {
                    'name': new_user.name,
                    'role': new_user.role,
                    'id': new_user.id
                },
                'direct_redirect': True,
                'force_redirect': True
            })
            
    except Exception as e:
        print(f"Verification error: {e}")
        return jsonify({'success': False, 'message': 'حدث خطأ في التحقق'})

@auth_bp.route('/check-phone', methods=['POST'])
@csrf_exempt
def check_phone():
    """التحقق من وجود رقم الهاتف"""
    try:
        data = request.get_json()
        phone = data.get('phone')
        
        if not phone:
            return jsonify({'success': False, 'message': 'رقم الهاتف مطلوب'})
        
        # التحقق من تنسيق رقم الهاتف المصري
        if not re.match(r'^01[0-9]{9}$', phone):
            return jsonify({'success': False, 'message': 'رقم الهاتف غير صحيح'})
        
        # البحث عن المستخدم
        user = User.query.filter_by(phone=phone).first()
        
        return jsonify({
            'success': True,
            'exists': user is not None,
            'phone': phone
        })
    
    except Exception as e:
        current_app.logger.error(f"خطأ في التحقق من رقم الهاتف: {str(e)}")
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء التحقق'})


"""
Google OAuth Routes
"""

@auth_bp.route('/google/login')
def google_login():
    """توجيه المستخدم إلى Google للمصادقة"""
    # بناء URL للمصادقة مع Google
    current_google_client_id = get_google_client_id()
    current_redirect_uri = get_google_redirect_uri()
    
    if not current_google_client_id or not current_redirect_uri:
        flash('تسجيل الدخول بـ جوجل غير متاح حالياً', 'error')
        return redirect(url_for('auth.login'))
    
    params = {
        'client_id': current_google_client_id,
        'redirect_uri': current_redirect_uri,
        'scope': 'openid email profile',
        'response_type': 'code',
        'state': 'login'  # للتمييز بين تسجيل الدخول والتسجيل
    }
    
    google_auth_url = f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"
    return redirect(google_auth_url)

@auth_bp.route('/google/register')
def google_register():
    """توجيه للنظام الحديث"""
    return redirect(url_for('auth.register'))

@auth_bp.route('/google/callback')
def google_callback():
    """توجيه للنظام الحديث"""
    flash('يرجى استخدام نظام التسجيل الحديث', 'info')
    return redirect(url_for('auth.register'))

@auth_bp.route('/complete-google-registration', methods=['POST'])
@csrf_exempt
def complete_google_registration():
    """توجيه للنظام الحديث"""
    flash('يرجى استخدام نظام التسجيل الحديث', 'info')
    return redirect(url_for('auth.register'))


# Registration routes for the step-by-step system

@auth_bp.route('/register-step', methods=['POST'])
@csrf_exempt
def register_step():
    """معالجة التسجيل بالخطوات (رقم الهاتف) - مع دعم CSRF"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'لا توجد بيانات في الطلب'})
        
        phone = data.get('phone', '').strip()
        name = data.get('name', '').strip()
        role = data.get('role', 'student')
        password = data.get('password', '')
        
        # التحقق من صحة البيانات
        if not phone or not name or not password:
            return jsonify({'success': False, 'message': 'جميع الحقول مطلوبة'})
        
        # التحقق من تنسيق رقم الهاتف
        if not re.match(r'^01[0-9]{9}$', phone):
            return jsonify({'success': False, 'message': 'رقم الهاتف غير صحيح'})
        
        # التحقق من عدم وجود المستخدم مسبقاً
        existing_user = User.query.filter_by(phone=phone).first()
        if existing_user:
            return jsonify({'success': False, 'message': 'رقم الهاتف مستخدم بالفعل'})
        
        # إنشاء المستخدم الجديد
        new_user = User(
            name=name,
            phone=phone,
            role=role,
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow()
        )
        
        # تعيين كلمة المرور
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.flush()  # للحصول على ID للمستخدم الجديد
        
        # إنشاء اشتراك تجريبي للمعلمين (يوم واحد)
        if role == 'teacher':
            # البحث عن باقة تجريبية أو إنشاؤها
            trial_plan = SubscriptionPlan.query.filter_by(
                name='الباقة التجريبية',
                price=0
            ).first()
            
            if not trial_plan:
                # إنشاء باقة تجريبية جديدة
                trial_plan = SubscriptionPlan(
                    name='الباقة التجريبية',
                    description='باقة تجريبية مجانية لمدة يوم واحد',
                    price=0,
                    duration_days=1,
                    max_classrooms=2,
                    has_chat=True,
                    allow_assistant=False,
                    advanced_analytics=False
                )
                db.session.add(trial_plan)
                db.session.flush()  # للحصول على ID
            
            # إنشاء الاشتراك التجريبي
            trial_subscription = Subscription(
                user_id=new_user.id,
                plan_id=trial_plan.id,
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() + timedelta(days=1),
                is_active=True,
                is_trial=True
            )
            db.session.add(trial_subscription)
        
        # إنشاء إشعار ترحيب للمستخدم الجديد
        welcome_title = "مرحباً بك في منصة الحصة! 🎉"
        
        if role == 'teacher':
            welcome_message = f"أهلاً وسهلاً بك {name}! نحن سعداء لانضمامك كمعلم في منصة الحصة. يمكنك الآن إنشاء فصولك الدراسية وبدء رحلة التعليم الرقمي. تم منحك باقة تجريبية مجانية لمدة يوم واحد للاستمتاع بجميع المميزات."
        elif role == 'student':
            welcome_message = f"أهلاً وسهلاً بك {name}! نحن سعداء لانضمامك كطالب في منصة الحصة. يمكنك الآن الانضمام للفصول الدراسية والاستفادة من المحتوى التعليمي المتميز."
        else:
            welcome_message = f"أهلاً وسهلاً بك {name}! نحن سعداء لانضمامك في منصة الحصة. استمتع بتجربة تعليمية متميزة."
        
        welcome_notification = Notification(
            user_id=new_user.id,
            title=welcome_title,
            message=welcome_message
        )
        db.session.add(welcome_notification)
        
        db.session.commit()
        
        # تسجيل دخول المستخدم مع ضمان استمرار الجلسة
        login_user(new_user, remember=True, duration=timedelta(days=7))
        
        # التأكد من تحديث الجلسة
        session.permanent = True
        session['user_id'] = new_user.id
        session['user_role'] = role
        session['user_name'] = name
        session.modified = True
        
        # تحديد وجهة التوجيه حسب الدور
        redirect_urls = {
            'admin': url_for('admin.dashboard'),
            'teacher': url_for('teacher.dashboard'),
            'student': url_for('student.dashboard'),
            'assistant': url_for('assistant.dashboard')
        }
        
        redirect_url = redirect_urls.get(role, url_for('main.index'))
        
        return jsonify({
            'success': True,
            'message': '🎉 تم إنشاء حسابك بنجاح!',
            'redirect_url': redirect_url,
            'is_teacher': role == 'teacher',
            'needs_wallet_setup': role == 'teacher'  # المعلمون الجدد يحتاجون إعداد المحفظة
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"خطأ في التسجيل: {str(e)}")
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء إنشاء الحساب'})


@auth_bp.route('/google-auth', methods=['POST'])
@csrf_exempt
def google_auth():
    """معالجة تسجيل الدخول/التسجيل بـ Google"""
    try:
        data = request.get_json()
        credential = data.get('credential')
        
        if not credential:
            return jsonify({'success': False, 'message': 'بيانات Google غير صحيحة'})
        
        # التحقق من صحة Google ID Token
        try:
            current_google_client_id = get_google_client_id()
            if not current_google_client_id:
                return jsonify({'success': False, 'message': 'خدمة Google غير متاحة حالياً'})
                
            idinfo = id_token.verify_oauth2_token(
                credential, google_requests.Request(), current_google_client_id
            )
            
            google_id = idinfo['sub']
            email = idinfo['email']
            name = idinfo.get('name', '')
            picture = idinfo.get('picture', '')
            
            current_app.logger.info(f"Google auth successful for user: {email}")
            
        except ValueError as e:
            current_app.logger.error(f"خطأ في التحقق من Google Token: {str(e)}")
            return jsonify({'success': False, 'message': 'بيانات Google غير صالحة'})
        
        # التحقق من وجود المستخدم بـ Google ID أولاً
        existing_user = User.query.filter_by(google_id=google_id).first()
        if existing_user:
            # تسجيل دخول المستخدم الموجود
            login_user(existing_user, remember=True, duration=timedelta(days=7))
            
            # تحديث الجلسة
            session.permanent = True
            session['user_id'] = existing_user.id
            session['user_role'] = existing_user.role
            session['user_name'] = existing_user.name
            session.modified = True
            
            redirect_urls = {
                'admin': url_for('admin.dashboard'),
                'teacher': url_for('teacher.dashboard'),
                'student': url_for('student.dashboard'),
                'assistant': url_for('assistant.dashboard')
            }
            
            redirect_url = redirect_urls.get(existing_user.role, url_for('main.index'))
            
            return jsonify({
                'success': True,
                'existing_user': True,
                'message': f'مرحباً بعودتك {existing_user.name}! 👋',
                'redirect_url': redirect_url,
                'user': {
                    'name': existing_user.name,
                    'role': existing_user.role,
                    'id': existing_user.id
                },
                'direct_redirect': True,
                'force_redirect': True
            })
        
        # التحقق من وجود مستخدم بنفس البريد الإلكتروني (بدون Google ID)
        email_user = User.query.filter_by(email=email).first()
        if email_user:
            # ربط الحساب الموجود بـ Google
            email_user.google_id = google_id
            if not email_user.profile_picture and picture:
                email_user.profile_picture = picture
            
            db.session.commit()
            
            # تسجيل دخول المستخدم
            login_user(email_user, remember=True, duration=timedelta(days=7))
            
            # تحديث الجلسة
            session.permanent = True
            session['user_id'] = email_user.id
            session['user_role'] = email_user.role
            session['user_name'] = email_user.name
            session.modified = True
            
            redirect_urls = {
                'admin': url_for('admin.dashboard'),
                'teacher': url_for('teacher.dashboard'),
                'student': url_for('student.dashboard'),
                'assistant': url_for('assistant.dashboard')
            }
            
            redirect_url = redirect_urls.get(email_user.role, url_for('main.index'))
            
            return jsonify({
                'success': True,
                'existing_user': True,
                'message': f'تم ربط حسابك بـ Google بنجاح. مرحباً بعودتك {email_user.name}! 👋',
                'redirect_url': redirect_url,
                'user': {
                    'name': email_user.name,
                    'role': email_user.role,
                    'id': email_user.id
                },
                'direct_redirect': True,
                'force_redirect': True
            })
        
        # مستخدم جديد - إرجاع البيانات لإكمال التسجيل
        current_app.logger.info(f"New Google user detected, sending registration data for: {email}")
        
        return jsonify({
            'success': True,
            'existing_user': False,
            'user': {
                'google_id': google_id,
                'email': email,
                'name': name,
                'picture': picture
            },
            'message': 'تم التحقق من بيانات Google بنجاح. يرجى إكمال بياناتك.'
        })
        
    except Exception as e:
        current_app.logger.error(f"خطأ في Google Auth: {str(e)}")
        return jsonify({'success': False, 'message': 'حدث خطأ في التسجيل بـ Google'})


@auth_bp.route('/complete-google-registration-api', methods=['POST'])
@csrf_exempt
def complete_google_registration_api():
    """إكمال التسجيل بـ Google بعد إدخال البيانات"""
    try:
        data = request.get_json()
        current_app.logger.info(f"Google registration data received: {data}")
        
        if not data:
            return jsonify({'success': False, 'message': 'لا توجد بيانات في الطلب'})
        
        # استخراج البيانات
        google_id = data.get('google_id')
        email = data.get('email')
        name = data.get('name', '').strip()
        picture = data.get('picture', '')
        phone = data.get('phone', '').strip()
        role = data.get('role', 'student')
        
        current_app.logger.info(f"Extracted data - google_id: {google_id}, email: {email}, name: {name}, phone: {phone}, role: {role}")
        
        # التحقق من البيانات المطلوبة
        if not all([google_id, email, name, phone]):
            missing_fields = []
            if not google_id: missing_fields.append('google_id')
            if not email: missing_fields.append('email')
            if not name: missing_fields.append('name')
            if not phone: missing_fields.append('phone')
            
            return jsonify({
                'success': False, 
                'message': f'البيانات التالية مطلوبة: {", ".join(missing_fields)}'
            })
        
        # التحقق من تنسيق رقم الهاتف
        if not re.match(r'^01[0-9]{9}$', phone):
            return jsonify({'success': False, 'message': 'رقم الهاتف غير صحيح. يجب أن يبدأ بـ 01 ويتكون من 11 رقم'})
        
        # التحقق من عدم وجود المستخدم بنفس رقم الهاتف أو Google ID
        existing_user_phone = User.query.filter_by(phone=phone).first()
        if existing_user_phone:
            return jsonify({'success': False, 'message': 'رقم الهاتف مستخدم بالفعل'})
        
        existing_user_google = User.query.filter_by(google_id=google_id).first()
        if existing_user_google:
            return jsonify({'success': False, 'message': 'هذا الحساب موجود بالفعل'})
        
        # إنشاء المستخدم الجديد
        new_user = User(
            name=name,
            phone=phone,
            email=email,
            role=role,
            google_id=google_id,
            profile_picture=picture if picture else None,
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow()
        )
        
        db.session.add(new_user)
        db.session.flush()  # للحصول على ID للمستخدم الجديد
        
        current_app.logger.info(f"Created new user with ID: {new_user.id}")
        
        # إنشاء اشتراك تجريبي للمعلمين (يوم واحد)
        if role == 'teacher':
            # البحث عن باقة تجريبية أو إنشاؤها
            trial_plan = SubscriptionPlan.query.filter_by(
                name='الباقة التجريبية',
                price=0
            ).first()
            
            if not trial_plan:
                # إنشاء باقة تجريبية جديدة
                trial_plan = SubscriptionPlan(
                    name='الباقة التجريبية',
                    description='باقة تجريبية مجانية لمدة يوم واحد',
                    price=0,
                    duration_days=1,
                    max_classrooms=2,
                    has_chat=True,
                    allow_assistant=False,
                    advanced_analytics=False
                )
                db.session.add(trial_plan)
                db.session.flush()
            
            # إنشاء الاشتراك التجريبي
            trial_subscription = Subscription(
                user_id=new_user.id,
                plan_id=trial_plan.id,
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() + timedelta(days=1),
                is_active=True,
                is_trial=True
            )
            db.session.add(trial_subscription)
        
        # إنشاء إشعار ترحيب
        welcome_title = "مرحباً بك في منصة الحصة! 🎉"
        
        if role == 'teacher':
            welcome_message = f"أهلاً وسهلاً بك {name}! نحن سعداء لانضمامك كمعلم في منصة الحصة. يمكنك الآن إنشاء فصولك الدراسية وبدء رحلة التعليم الرقمي. تم منحك باقة تجريبية مجانية لمدة يوم واحد للاستمتاع بجميع المميزات."
        else:
            welcome_message = f"أهلاً وسهلاً بك {name}! نحن سعداء لانضمامك كطالب في منصة الحصة. يمكنك الآن الانضمام للفصول الدراسية والاستفادة من المحتوى التعليمي المتميز."
        
        welcome_notification = Notification(
            user_id=new_user.id,
            title=welcome_title,
            message=welcome_message
        )
        db.session.add(welcome_notification)
        
        db.session.commit()
        current_app.logger.info(f"Successfully created user {new_user.id} with Google registration")
        
        # تسجيل دخول المستخدم
        login_user(new_user, remember=True, duration=timedelta(days=7))
        
        # تحديث الجلسة
        session.permanent = True
        session['user_id'] = new_user.id
        session['user_role'] = role
        session['user_name'] = name
        session.modified = True
        
        # تحديد وجهة التوجيه
        redirect_urls = {
            'admin': url_for('admin.dashboard'),
            'teacher': url_for('teacher.dashboard'),
            'student': url_for('student.dashboard'),
            'assistant': url_for('assistant.dashboard')
        }
        
        redirect_url = redirect_urls.get(role, url_for('main.index'))
        
        return jsonify({
            'success': True,
            'message': '🎉 تم إنشاء حسابك بنجاح!',
            'redirect_url': redirect_url,
            'user': {
                'name': new_user.name,
                'role': new_user.role,
                'id': new_user.id
            },
            'is_teacher': role == 'teacher',
            'needs_wallet_setup': role == 'teacher',
            'direct_redirect': True,
            'force_redirect': True
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"خطأ في إكمال التسجيل بـ Google: {str(e)}")
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء إنشاء الحساب'})


@auth_bp.route('/update-wallet-numbers', methods=['POST'])
@login_required
@csrf_exempt
def update_wallet_numbers():
    """تحديث أرقام المحافظ الإلكترونية للمعلم"""
    try:
        # التحقق من أن المستخدم معلم
        if current_user.role != 'teacher':
            return jsonify({'success': False, 'message': 'هذه الميزة متاحة للمعلمين فقط'})
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'لا توجد بيانات في الطلب'})
        
        ewallet_number_1 = data.get('ewallet_number_1', '').strip()
        ewallet_number_2 = data.get('ewallet_number_2', '').strip()
        
        # التحقق من وجود رقم واحد على الأقل
        if not ewallet_number_1:
            return jsonify({'success': False, 'message': 'يجب إدخال رقم المحفظة الأول'})
        
        # التحقق من تنسيق الأرقام
        phone_regex = r'^01[0-9]{9}$'
        if not re.match(phone_regex, ewallet_number_1):
            return jsonify({'success': False, 'message': 'رقم المحفظة الأول غير صحيح. يجب أن يبدأ بـ 01 ويتكون من 11 رقم'})
        
        if ewallet_number_2 and not re.match(phone_regex, ewallet_number_2):
            return jsonify({'success': False, 'message': 'رقم المحفظة الثاني غير صحيح. يجب أن يبدأ بـ 01 ويتكون من 11 رقم'})
        
        # تحديث أرقام المحافظ
        current_user.ewallet_number_1 = ewallet_number_1
        current_user.ewallet_number_2 = ewallet_number_2 if ewallet_number_2 else None
        current_user.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم حفظ أرقام المحافظ بنجاح! يمكن للطلاب الآن دفع رسوم الاشتراك في فصولك.'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"خطأ في تحديث أرقام المحافظ: {str(e)}")
        return jsonify({'success': False, 'message': 'حدث خطأ أثناء حفظ أرقام المحافظ'})


@auth_bp.route('/check-wallet-status')
@login_required
def check_wallet_status():
    """فحص حالة المحفظة للمستخدم الحالي"""
    try:
        is_teacher = current_user.role == 'teacher'
        has_wallet = current_user.has_ewallet_numbers() if is_teacher else True
        
        return jsonify({
            'success': True,
            'is_teacher': is_teacher,
            'has_wallet': has_wallet
        })
        
    except Exception as e:
        current_app.logger.error(f"خطأ في فحص حالة المحفظة: {str(e)}")
        return jsonify({'success': False, 'message': 'حدث خطأ'})


@auth_bp.route('/components/wallet-modal')
def wallet_modal_component():
    """إرجاع HTML الخاص بنافذة المحفظة"""
    try:
        return render_template('components/wallet_modal.html')
    except Exception as e:
        current_app.logger.error(f"خطأ في تحميل نافذة المحفظة: {str(e)}")
        return "حدث خطأ في تحميل النافذة", 500