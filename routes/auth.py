"""
مسارات المصادقة (auth)
التحكم في تسجيل الدخول والخروج وتسجيل المستخدمين الجدد
"""

import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from firebase_utils import verify_firebase_token
from models import Role, Subscription, SubscriptionPlan, SystemSettings, User , db
import re
from firebase_config import firebase_config

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
    decorated_function._csrf_exempt = True
    return decorated_function

auth_bp = Blueprint('auth', __name__)

class LoginForm(FlaskForm):
    phone = StringField('رقم الهاتف', validators=[DataRequired()])
    password = PasswordField('كلمة المرور', validators=[DataRequired()])
    submit = SubmitField('تسجيل الدخول')

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

"""
مسار تسجيل الدخول (Login)
معالجة نموذج تسجيل الدخول والتحقق من صحة البيانات
"""
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # السماح بعرض صفحة تسجيل الدخول حتى لو كان المستخدم مسجل دخوله
    # فقط نعيد توجيهه بعد تسجيل الدخول بنجاح
    
    # لا نطبق Rate Limiting على طلبات GET لتجنب منع الوصول للصفحة

    form = LoginForm()
    if request.method == 'POST' and form.validate_on_submit():
        from models import User
        user = User.query.filter_by(phone=form.phone.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        else:
            flash('فشل تسجيل الدخول. الرجاء التحقق من رقم الهاتف وكلمة المرور', 'danger')

    # GET request أو فشل التحقق من صحة النموذج أو المستخدم مسجل دخوله بالفعل
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    firebase_api_key = os.environ.get("FIREBASE_API_KEY", "")
    firebase_project_id = os.environ.get("FIREBASE_PROJECT_ID", "")
    firebase_app_id = os.environ.get("FIREBASE_APP_ID", "")

    template = 'auth/auth-mobile/login.html' if is_mobile() else 'auth/login.html'

    # الحصول على قيم الألوان من إعدادات النظام
    from models import SystemSettings
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي

    
    return render_template(template,
                          form=form,
                          primary_color=primary_color,
                          secondary_color=secondary_color,
                          firebase_api_key=firebase_api_key,
                          firebase_project_id=firebase_project_id,
                          firebase_app_id=firebase_app_id)

"""
مسار التسجيل (Register)
إنشاء حساب جديد للمستخدم
"""
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # السماح بعرض صفحة التسجيل حتى لو كان المستخدم مسجل دخوله
    
    # لا نطبق Rate Limiting على طلبات GET لتجنب منع الوصول للصفحة

    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        password = request.form.get('password')
        role = request.form.get('role')

        # Validate role
        if role not in [Role.STUDENT, Role.TEACHER, Role.ASSISTANT]:
            flash('دور المستخدم غير صالح', 'danger')
            return redirect(url_for('auth.register'))

        # Check if user already exists
        existing_user = User.query.filter_by(phone=phone).first()
        if existing_user:
            flash('رقم الهاتف مسجل بالفعل', 'danger')
            return redirect(url_for('auth.register'))

        # Create new user
        new_user = User(
            name=name,
            phone=phone,
            role=role
        )
        new_user.set_password(password)

        # Save user first to get ID
        db.session.add(new_user)
        db.session.flush()  # Get ID without committing

        # If the user is a teacher, create a free trial subscription
        if role == Role.TEACHER:
            # Get the premium plan (highest level)
            premium_plan = SubscriptionPlan.query.order_by(SubscriptionPlan.price.desc()).first()

            # If no plan exists yet, create one
            if not premium_plan:
                premium_plan = SubscriptionPlan(
                    name="الباقة الكاملة",
                    description="جميع المميزات متاحة",
                    price=299,
                    duration_days=30,
                    max_classrooms=99,
                    has_chat=True,
                    allow_assistant=True,
                    advanced_analytics=True
                )
                db.session.add(premium_plan)
                db.session.flush()  # Get ID without committing

            # Create trial subscription with explicit user_id
            trial_days = 14  # 2 weeks trial
            trial_subscription = Subscription(
                user_id=new_user.id,  # Now user_id is available
                plan_id=premium_plan.id,
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() + timedelta(days=trial_days),
                is_active=True,
                is_trial=True
            )
            db.session.add(trial_subscription)

        # Finally commit all changes
        db.session.commit()

        flash('تم إنشاء الحساب بنجاح. يمكنك الآن تسجيل الدخول', 'success')
        return redirect(url_for('auth.login'))

    # GET request أو فشل في إنشاء الحساب أو المستخدم مسجل دخوله بالفعل
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    firebase_api_key = os.environ.get("FIREBASE_API_KEY", "")
    firebase_project_id = os.environ.get("FIREBASE_PROJECT_ID", "")
    firebase_app_id = os.environ.get("FIREBASE_APP_ID", "")

    template = 'auth/auth-mobile/register.html' if is_mobile() else 'auth/register.html'

    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي

    
    return render_template(template,
                           primary_color=primary_color,
                           secondary_color=secondary_color,
                          firebase_api_key=firebase_api_key,
                          firebase_project_id=firebase_project_id,
                          firebase_app_id=firebase_app_id)

@auth_bp.route('/verify-token', methods=['POST'])
def verify_token():
    data = request.json
    id_token = data.get('idToken')

    if not id_token:
        return jsonify({'error': 'No token provided'}), 400

    try:
        # Verify the Firebase ID token
        decoded_token = verify_firebase_token(id_token)

        if not decoded_token:
            return jsonify({'error': 'Invalid token'}), 401

        # Get user information from the token
        firebase_uid = decoded_token['uid']
        phone_number = decoded_token.get('phone_number')

        if not phone_number:
            return jsonify({'error': 'Phone number missing in token'}), 400

        # Check if user exists
        user = User.query.filter_by(firebase_uid=firebase_uid).first()

        if not user:
            # Check if phone number is already registered
            existing_user = User.query.filter_by(phone=phone_number).first()

            if existing_user:
                # Link Firebase UID to existing user
                existing_user.firebase_uid = firebase_uid
                db.session.commit()
                login_user(existing_user)
                return jsonify({
                    'success': True,
                    'isNewUser': False,
                    'redirect': url_for('main.index')
                })

            # If name is provided in the token, we can create a new user
            name = decoded_token.get('name', 'User')

            # Store token info in session for registration completion
            session['firebase_uid'] = firebase_uid
            session['phone_number'] = phone_number
            session['name'] = name

            # Redirect to complete registration
            return jsonify({
                'success': True,
                'isNewUser': True,
                'redirect': url_for('auth.complete_registration')
            })
        else:
            # User exists, log them in
            login_user(user)
            return jsonify({
                'success': True,
                'isNewUser': False,
                'redirect': url_for('main.index')
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/complete-registration', methods=['GET', 'POST'])
def complete_registration():
    # Check if we have the firebase data in session
    if not session.get('firebase_uid') or not session.get('phone_number'):
        flash('معلومات غير كافية', 'danger')
        return redirect(url_for('auth.register'))

    if request.method == 'POST':
        name = request.form.get('name', session.get('name', 'User'))
        role = request.form.get('role')

        # Validate role
        if role not in [Role.STUDENT, Role.TEACHER, Role.ASSISTANT]:
            flash('دور المستخدم غير صالح', 'danger')
            return redirect(url_for('auth.complete_registration'))

        # Create new user with Firebase data
        new_user = User(
            name=name,
            phone=session.get('phone_number'),
            role=role,
            firebase_uid=session.get('firebase_uid')
        )

        # Save user first to get ID
        db.session.add(new_user)
        db.session.flush()  # Get ID without committing

        # If the user is a teacher, create a free trial subscription
        if role == Role.TEACHER:
            # Get the premium plan (highest level)
            premium_plan = SubscriptionPlan.query.order_by(SubscriptionPlan.price.desc()).first()

            # If no plan exists yet, create one
            if not premium_plan:
                premium_plan = SubscriptionPlan(
                    name="الباقة التجريبية",
                    description="جميع المميزات متاحة",
                    price=0,
                    duration_days=trial_days,
                    max_classrooms=1,
                    has_chat=True,
                    allow_assistant=True,
                    advanced_analytics=True
                )
                db.session.add(premium_plan)
                db.session.flush()  # Get ID without committing

            # Create trial subscription with explicit user_id
            trial_days = SystemSettings.get_setting('trial_days', 7)  # 1 weeks trial
            trial_subscription = Subscription(
                user_id=new_user.id,  # Set user_id explicitly
                plan_id=premium_plan.id,
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() + timedelta(days=trial_days),
                is_active=True,
                is_trial=True
            )
            db.session.add(trial_subscription)

        # Finally commit all changes
        db.session.commit()

        # Clear session data
        session.pop('firebase_uid', None)
        session.pop('phone_number', None)
        session.pop('name', None)

        # Log in the new user
        login_user(new_user)

        flash('تم إنشاء الحساب بنجاح', 'success')
        return redirect(url_for('main.index'))
    
    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي


    return render_template('auth/complete_registration.html',
                          primary_color=primary_color,
                          secondary_color=secondary_color, 
                          name=session.get('name', ''),
                          phone=session.get('phone_number', ''))

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

# ============================================
# Firebase Phone Authentication Routes
# ============================================

def validate_phone_number(phone):
    """التحقق من صحة رقم الهاتف"""
    # إزالة المسافات والرموز
    phone = re.sub(r'[^\d+]', '', phone)
    
    # التحقق من التنسيق السعودي
    if phone.startswith('+20'):
        return phone
    elif phone.startswith('20'):
        return '+' + phone
    elif phone.startswith('01'):
        return '+20' + phone[1:]
    elif phone.startswith('1') and len(phone) == 9:
        return '+20' + phone
    
    return None

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
                'redirect': f'/{user.role}/dashboard'
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
                'redirect': f'/{new_user.role}/dashboard'
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
        
        # تنسيق رقم الهاتف
        formatted_phone = validate_phone_number(phone)
        
        if not formatted_phone:
            return jsonify({'success': False, 'message': 'رقم الهاتف غير صحيح'})
        
        # البحث عن المستخدم
        user = User.query.filter_by(phone=formatted_phone).first()
        
        return jsonify({
            'success': True,
            'exists': user is not None,
            'phone': formatted_phone
        })
        
    except Exception as e:
        print(f"Check phone error: {e}")
        return jsonify({'success': False, 'message': 'حدث خطأ في التحقق'})