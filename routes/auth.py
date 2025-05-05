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
from app import db
from models import User, Role, Subscription, SubscriptionPlan
from firebase_utils import verify_firebase_token

auth_bp = Blueprint('auth', __name__)

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

"""
مسار تسجيل الدخول (Login)
معالجة نموذج تسجيل الدخول والتحقق من صحة البيانات
"""
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        phone = request.form.get('phone')
        password = request.form.get('password')
        
        user = User.query.filter_by(phone=phone).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('فشل تسجيل الدخول. الرجاء التحقق من رقم الهاتف وكلمة المرور', 'danger')
    
    firebase_api_key = os.environ.get("FIREBASE_API_KEY", "")
    firebase_project_id = os.environ.get("FIREBASE_PROJECT_ID", "")
    firebase_app_id = os.environ.get("FIREBASE_APP_ID", "")
    
    return render_template('auth/login.html', 
                          firebase_api_key=firebase_api_key,
                          firebase_project_id=firebase_project_id,
                          firebase_app_id=firebase_app_id)

"""
مسار التسجيل (Register)
إنشاء حساب جديد للمستخدم
"""
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
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
    
    firebase_api_key = os.environ.get("FIREBASE_API_KEY", "")
    firebase_project_id = os.environ.get("FIREBASE_PROJECT_ID", "")
    firebase_app_id = os.environ.get("FIREBASE_APP_ID", "")
    
    return render_template('auth/register.html',
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
                    'redirect': url_for('index')
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
                'redirect': url_for('index')
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
        return redirect(url_for('index'))
    
    return render_template('auth/complete_registration.html', 
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
    return redirect(url_for('index'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        alt_phone = request.form.get('alt_phone')
        address = request.form.get('address')
        interests = request.form.get('interests')
        
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
        
        db.session.commit()
        flash('تم تحديث الملف الشخصي بنجاح', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/profile.html', now=datetime.utcnow())
