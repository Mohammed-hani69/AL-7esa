"""
مسارات المعلم (Teacher Routes)
التحكم في إدارة الفصول الدراسية والمحتوى التعليمي
"""

import random
import string
import os
import re
import mimetypes
from werkzeug.utils import secure_filename
from flask import Blueprint, abort, make_response, render_template, redirect, send_file, url_for, request, flash, jsonify, current_app, send_from_directory
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, timedelta
from models import ChatMessage, Payment, QuizAnswer, QuizAttempt, User, Role, Classroom, ClassroomEnrollment, ClassroomContent, ContentType
from models import Assignment, AssignmentSubmission, Quiz, QuizQuestion, QuizQuestionOption
from models import Subscription, SubscriptionPlan, ChatSettings, ChatParticipant, SubscriptionPayment, SubscriptionPayment
from models import SystemSettings, LiveStream, Notification, Banner

from models import db


teacher_bp = Blueprint('teacher', __name__)

# Allowed file extensions for uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'mp4', 'mp3', 'wav', 'webm', 'mov', 'ogg', 'ppt', 'pptx'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_size_limit(content_type):
    """Get file size limit based on content type - بدون حدود للحجم"""
    # إزالة قيود الحجم لمنع خطأ 413
    return float('inf')  # بدون حد أقصى


def is_mobile():
    """Check if current request is from a mobile device"""
    user_agent = request.headers.get('User-Agent', '').lower()
    return any(device in user_agent for device in ['android', 'iphone', 'ipad', 'mobile'])

# Teacher required decorator
def teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != Role.TEACHER:
            flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Generate unique classroom code
def generate_classroom_code(length=6):
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        # Check if code already exists
        existing = Classroom.query.filter_by(code=code).first()
        if not existing:
            return code

# Check if teacher has active subscription
def has_active_subscription():
    active_sub = Subscription.query.filter(
        Subscription.user_id == current_user.id,
        Subscription.end_date > datetime.utcnow(),
        Subscription.is_active == True
    ).first()

    return active_sub is not None

# Get teacher's current subscription plan
def get_current_plan():
    active_sub = Subscription.query.filter(
        Subscription.user_id == current_user.id,
        Subscription.end_date > datetime.utcnow(),
        Subscription.is_active == True
    ).first()

    if active_sub:
        return active_sub.plan
    return None

# Check if current plan allows creating more classrooms
def can_create_classroom():
    plan = get_current_plan()

    if not plan:
        return False

    # Count teacher's current classrooms
    current_classrooms = Classroom.query.filter_by(teacher_id=current_user.id).count()

    return current_classrooms < plan.max_classrooms

"""
الصفحة الرئيسية للمعلم
عرض لوحة التحكم والإحصائيات
"""
@teacher_bp.route('/dashboard')
@login_required
@teacher_required
def dashboard():
    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي

    # الحصول على الفصول 
    classrooms = Classroom.query.filter_by(teacher_id=current_user.id).all()
    
    # حساب عدد الطلاب الإجمالي
    total_students = db.session.query(db.func.count(ClassroomEnrollment.id))\
        .join(Classroom)\
        .filter(Classroom.teacher_id == current_user.id)\
        .scalar()
    
    # حساب عدد الواجبات النشطة
    active_assignments = Assignment.query.join(Classroom)\
        .filter(Classroom.teacher_id == current_user.id)\
        .filter(Assignment.due_date > datetime.utcnow())\
        .count()
    
    # حساب عدد الاختبارات النشطة
    active_quizzes = Quiz.query.join(Classroom)\
        .filter(Classroom.teacher_id == current_user.id)\
        .count()

    # Get all students across all classrooms and calculate their performance
    top_students = []
    all_enrollments = ClassroomEnrollment.query\
        .join(Classroom)\
        .filter(Classroom.teacher_id == current_user.id)\
        .all()

    for enrollment in all_enrollments:
        # Calculate assignment completion and average grade
        assignment_submissions = AssignmentSubmission.query\
            .join(Assignment)\
            .filter(
                AssignmentSubmission.enrollment_id == enrollment.id,
                Assignment.classroom_id == enrollment.classroom_id
            ).all()
        
        total_assignments = Assignment.query\
            .filter(Assignment.classroom_id == enrollment.classroom_id)\
            .count()

        completed_assignments = len(assignment_submissions)
        total_grade = sum(sub.grade for sub in assignment_submissions if sub.grade is not None)
        
        average_grade = (total_grade / completed_assignments) if completed_assignments > 0 else 0
        
        # Calculate quiz performance
        quiz_attempts = QuizAttempt.query\
            .join(Quiz)\
            .filter(
                QuizAttempt.enrollment_id == enrollment.id,
                Quiz.classroom_id == enrollment.classroom_id
            ).all()
        
        total_quiz_score = 0
        completed_quizzes = 0
        for attempt in quiz_attempts:
            if attempt.score is not None:  # Changed from grade to score
                total_quiz_score += attempt.score
                completed_quizzes += 1
        
        quiz_average = (total_quiz_score / completed_quizzes) if completed_quizzes > 0 else 0
        
        # Calculate overall performance score (50% assignments, 50% quizzes)
        overall_score = (average_grade + quiz_average) / 2

        student_data = {
            'name': enrollment.user.name,
            'classroom_name': enrollment.classroom.name,
            'average_grade': overall_score,
            'assignments_completed': completed_assignments,
            'quizzes_score': quiz_average
        }
        top_students.append(student_data)
    
    # Sort students by overall score and get top 3
    top_students.sort(key=lambda x: x['average_grade'], reverse=True)
    top_students = top_students[:3]

    # الحصول على الاشتراك النشط
    active_subscription = Subscription.query.filter(
        Subscription.user_id == current_user.id,
        Subscription.end_date > datetime.utcnow(),
        Subscription.is_active == True
    ).first()

    has_active_sub = active_subscription is not None
    subscription_days_left = 0
    
    if active_subscription and active_subscription.end_date:
        days_left = (active_subscription.end_date - datetime.utcnow()).days
        subscription_days_left = max(0, days_left)

    # إضافة التحليلات لكل فصل
    for classroom in classrooms:
        try:
            classroom = get_classroom_analytics(classroom)
        except Exception as e:
            current_app.logger.error(f"Error calculating analytics for classroom {classroom.id}: {str(e)}")
            # تعيين قيم افتراضية في حالة حدوث خطأ
            classroom.top_students = []
            classroom.submission_rate = 0
            classroom.average_attendance = 0
            classroom.quiz_completion = 0
            classroom.recent_activities = []

    template = 'dashboard/mobile-theme/teacher.html' if is_mobile() else 'dashboard/teacher.html'
    
    # جلب الإشعارات غير المقروءة
    unread_notifications_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    unread_notifications = Notification.query.filter_by(
        user_id=current_user.id, 
        is_read=False
    ).order_by(Notification.created_at.desc()).limit(5).all()
    
    # فحص حالة المحفظة الإلكترونية
    has_wallet_numbers = current_user.has_ewallet_numbers()
    
    # جلب البانرات النشطة للمعلمين
    active_banners = Banner.query.filter(
        Banner.is_active == True,
        (Banner.start_date.is_(None)) | (Banner.start_date <= datetime.utcnow()),
        (Banner.end_date.is_(None)) | (Banner.end_date >= datetime.utcnow())
    ).filter(
        (Banner.target_roles == 'all') |
        (Banner.target_roles.like('%teacher%'))
    ).order_by(Banner.priority.desc()).all()
    
    # فلترة البانرات للمعلمين
    teacher_banners = [banner for banner in active_banners if banner.is_valid_for_user('teacher')]
    
    # حساب إجمالي عدد الطلاب المنضمين في جميع الفصول
    total_enrolled_students = db.session.query(db.func.count(ClassroomEnrollment.id))\
        .join(Classroom)\
        .filter(Classroom.teacher_id == current_user.id)\
        .scalar() or 0
    
    return render_template(template,
                         classrooms=classrooms,
                         total_students=total_students,
                         total_enrolled_students=total_enrolled_students,
                         active_assignments=active_assignments,
                         active_quizzes=active_quizzes,
                         has_active_subscription=has_active_sub,
                         subscription_days_left=subscription_days_left,
                         can_create_classroom=can_create_classroom(),
                         unread_notifications_count=unread_notifications_count,
                         unread_notifications=unread_notifications,
                         has_wallet_numbers=has_wallet_numbers,
                         banners=teacher_banners,
                         primary_color=primary_color,
                         secondary_color=secondary_color)

def get_classroom_analytics(classroom):
    """استخراج البيانات التحليلية للفصل"""
    try:
        # الحصول على أفضل الطلاب أداءً
        top_students = []
        enrollments = ClassroomEnrollment.query.filter_by(classroom_id=classroom.id).all()
        
        for enrollment in enrollments:
            try:
                # حساب متوسط الدرجات
                submissions = AssignmentSubmission.query.join(Assignment).filter(
                    Assignment.classroom_id == classroom.id,
                    AssignmentSubmission.enrollment_id == enrollment.id
                ).all()
                
                total_grade = sum(sub.grade for sub in submissions if sub.grade is not None)
                total_submissions = len([sub for sub in submissions if sub.grade is not None])
                average_grade = total_grade / total_submissions if total_submissions > 0 else 0
                
                # حساب نسبة إكمال الواجبات
                total_assignments = Assignment.query.filter_by(classroom_id=classroom.id).count()
                completed_assignments = AssignmentSubmission.query.join(Assignment).filter(
                    Assignment.classroom_id == classroom.id,
                    AssignmentSubmission.enrollment_id == enrollment.id
                ).count()
                
                # حساب معدل المشاركة
                participation_rate = (completed_assignments / total_assignments * 100) if total_assignments > 0 else 0
                
                top_students.append({
                    'name': enrollment.user.name,
                    'average_grade': average_grade,
                    'completed_assignments': completed_assignments,
                    'total_assignments': total_assignments,
                    'participation_rate': participation_rate
                })
            except Exception as e:
                current_app.logger.error(f"Error calculating student analytics: {str(e)}")
                continue
        
        # ترتيب الطلاب حسب متوسط الدرجات
        top_students.sort(key=lambda x: x['average_grade'], reverse=True)
        
        # حساب إحصائيات الفصل
        total_assignments = Assignment.query.filter_by(classroom_id=classroom.id).count()
        total_submissions = AssignmentSubmission.query.join(Assignment).filter(
            Assignment.classroom_id == classroom.id
        ).count()
        
        submission_rate = (total_submissions / (total_assignments * len(enrollments) or 1)) * 100
        
        # حساب متوسط الحضور (يمكن تعديله حسب نظام تتبع الحضور لديك)
        average_attendance = 85  # قيمة افتراضية
        
        # حساب نسبة إكمال الاختبارات
        total_quizzes = Quiz.query.filter_by(classroom_id=classroom.id).count()
        completed_attempts = QuizAttempt.query.join(Quiz).filter(
            Quiz.classroom_id == classroom.id,
            QuizAttempt.is_completed == True
        ).count()
        
        quiz_completion = (completed_attempts / (total_quizzes * len(enrollments) or 1)) * 100
        
        # إضافة البيانات التحليلية للفصل
        classroom.top_students = top_students[:3]  # أفضل 3 طلاب
        classroom.submission_rate = submission_rate
        classroom.average_attendance = average_attendance
        classroom.quiz_completion = quiz_completion
        
        # إضافة النشاطات الأخيرة
        recent_activities = []
        
        # إضافة آخر الواجبات المسلمة
        latest_submissions = AssignmentSubmission.query.join(Assignment).join(ClassroomEnrollment).join(User).filter(
            Assignment.classroom_id == classroom.id
        ).order_by(AssignmentSubmission.submission_date.desc()).limit(3).all()
        
        for submission in latest_submissions:
            recent_activities.append({
                'icon': 'file-upload',
                'description': f'قام {submission.enrollment.user.name} بتسليم {submission.assignment.title}',
                'time': submission.submission_date
            })
        
        # إضافة آخر الاختبارات المكتملة
        latest_quiz_attempts = QuizAttempt.query.join(Quiz).join(ClassroomEnrollment).join(User).filter(
            Quiz.classroom_id == classroom.id,
            QuizAttempt.is_completed == True
        ).order_by(QuizAttempt.end_time.desc()).limit(3).all()
        
        for attempt in latest_quiz_attempts:
            recent_activities.append({
                'icon': 'check-circle',
                'description': f'أكمل {attempt.enrollment.user.name} اختبار {attempt.quiz.title}',
                'time': attempt.end_time
            })
        
        # ترتيب النشاطات حسب الوقت
        recent_activities.sort(key=lambda x: x['time'], reverse=True)
        classroom.recent_activities = recent_activities[:3]  # آخر 3 نشاطات
        
        return classroom
    except Exception as e:
        current_app.logger.error(f"Error in get_classroom_analytics: {str(e)}")
        raise

"""
مسار لاشتراك المعلم في باقة محددة
"""
@teacher_bp.route('/subscribe/<int:plan_id>', methods=['POST'])
@login_required
@teacher_required
def subscribe_to_plan(plan_id):
    # التحقق من وجود الباقة
    plan = SubscriptionPlan.query.get_or_404(plan_id)
    
    # في التطبيق الفعلي، هنا سيتم معالجة عملية الدفع الإلكتروني
    # ولكن لأغراض العرض، سنقوم بإنشاء اشتراك مباشرةً

    # التحقق من وجود اشتراك نشط وتحديثه
    active_sub = Subscription.query.filter(
        Subscription.user_id == current_user.id,
        Subscription.end_date > datetime.utcnow(),
        Subscription.is_active == True
    ).first()
    
    if active_sub:
        # إلغاء تفعيل الاشتراك الحالي
        active_sub.is_active = False
        db.session.commit()
    
    # إنشاء اشتراك جديد
    new_subscription = Subscription(
        user_id=current_user.id,
        plan_id=plan.id,
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=plan.duration_days),
        is_active=True,
        is_trial=False
    )
    
    # إنشاء سجل دفع
    payment = Payment(
        user_id=current_user.id,
        subscription_id=new_subscription.id,
        amount=plan.price,
        currency='SAR',  # عملة الريال السعودي
        payment_method='credit_card',  # طريقة الدفع الافتراضية
        status='success'  # حالة الدفع
    )
    
    # حفظ البيانات في قاعدة البيانات
    db.session.add(new_subscription)
    db.session.add(payment)
    db.session.commit()
    
    flash(f'تم الاشتراك في باقة {plan.name} بنجاح!', 'success')
    return redirect(url_for('teacher.dashboard'))

@teacher_bp.route('/renew_subscription', methods=['POST'])
@login_required
@teacher_required
def renew_subscription():
    """
    مسار لتجديد الاشتراك الحالي
    """
    # الحصول على الاشتراك الحالي
    active_sub = Subscription.query.filter(
        Subscription.user_id == current_user.id,
        Subscription.is_active == True
    ).first()
    
    if not active_sub:
        flash('لا يوجد اشتراك نشط لتجديده', 'warning')
        return redirect(url_for('teacher.dashboard'))
    
    # تجديد الاشتراك لنفس المدة
    plan = active_sub.plan
    
    # تحديث تاريخ الانتهاء
    new_end_date = datetime.utcnow() + timedelta(days=plan.duration_days)
    active_sub.end_date = new_end_date
    
    # إنشاء سجل دفع
    payment = Payment(
        user_id=current_user.id,
        subscription_id=active_sub.id,
        amount=plan.price,
        currency='SAR',  # عملة الريال السعودي
        payment_method='credit_card',  # طريقة الدفع الافتراضية
        status='success'  # حالة الدفع
    )
    
    db.session.add(payment)
    db.session.commit()
    
    flash(f'تم تجديد اشتراكك في باقة {plan.name} بنجاح!', 'success')
    return redirect(url_for('teacher.dashboard'))

"""
مسار عرض الاشتراكات وإدارتها
"""
@teacher_bp.route('/subscriptions')
@login_required
@teacher_required
def subscriptions():
    # Get all subscription plans
    plans = SubscriptionPlan.query.all()

    # Get current active subscription
    active_subscription = Subscription.query.filter(
        Subscription.user_id == current_user.id,
        Subscription.end_date > datetime.utcnow(),
        Subscription.is_active == True
    ).first()

    # Calculate remaining days if there's an active subscription 
    subscription_days_left = 0
    if active_subscription and active_subscription.end_date:
        subscription_days_left = (active_subscription.end_date - datetime.utcnow()).days

    template = 'teacher/mobile-theme/teacher_plans.html' if is_mobile() else 'teacher/teacher_plans.html'

    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي



    return render_template(template,
                         plans=plans,
                         primary_color=primary_color,
                         secondary_color=secondary_color,
                         active_subscription=active_subscription,
                         subscription_days_left=subscription_days_left)

"""
إدارة الفصول الدراسية
إنشاء وتعديل وحذف الفصول
"""
@teacher_bp.route('/classroom/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_classroom():
    # التحقق من وجود اشتراك نشط للمعلم
    if not has_active_subscription():
        flash('لا يمكنك إنشاء فصول دراسية جديدة. يرجى الاشتراك في باقة نشطة أولاً.', 'warning')
        return redirect(url_for('teacher.dashboard'))
        
    # Check if teacher can create a new classroom
    if not can_create_classroom():
        flash('لا يمكنك إنشاء فصول دراسية أخرى. الرجاء ترقية اشتراكك', 'warning')
        return redirect(url_for('teacher.dashboard'))

    if request.method == 'POST':


   
        name = request.form.get('name')
        subject = request.form.get('subject')
        grade = request.form.get('grade')
        academic_year = request.form.get('academic_year')
        description = request.form.get('description', '')
        color = request.form.get('color', '#3498db')
        is_free = 'is_free' in request.form

        # Handle paid classroom details
        price = None
        duration_days = None
        if not is_free:
            # التحقق من وجود أرقام المحافظ الإلكترونية للمعلم قبل إنشاء فصل مدفوع
            if not current_user.has_ewallet_numbers():
                flash('يجب إضافة رقم محفظة إلكترونية في ملفك الشخصي قبل إنشاء فصل مدفوع', 'warning')
                return redirect(url_for('auth.profile'))
                
            price = float(request.form.get('price', 0))
            duration_days = int(request.form.get('duration_days', 30))

        # Generate unique classroom code
        code = generate_classroom_code()

        # Create new classroom
        new_classroom = Classroom(
            code=code,
            name=name,
            description=description,
            subject=subject,
            grade=grade,
            academic_year=academic_year,
            color=color,
            is_free=is_free,
            price=price,
            duration_days=duration_days,
            teacher_id=current_user.id
        )

        db.session.add(new_classroom)
        db.session.commit()

        flash(f'تم إنشاء الفصل الدراسي بنجاح. كود الفصل: {code}', 'success')
        return redirect(url_for('teacher.classroom', classroom_id=new_classroom.id))
    
    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي

    template = 'teacher/mobile-theme/create.html' if is_mobile() else 'teacher/create.html'


    return render_template(template,
                           primary_color=primary_color,
                           secondary_color=secondary_color)

@teacher_bp.route('/classroom/<int:classroom_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_classroom(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)

    # Ensure the teacher owns this classroom
    if classroom.teacher_id != current_user.id:
        flash('غير مصرح لك بتعديل هذا الفصل', 'danger')
        return redirect(url_for('teacher.dashboard'))

    if request.method == 'POST':
        name = request.form.get('name')
        subject = request.form.get('subject')
        grade = request.form.get('grade')
        academic_year = request.form.get('academic_year')
        description = request.form.get('description', '')
        color = request.form.get('color', '#3498db')
        is_free = 'is_free' in request.form

        # Validation
        if not name or not subject or not grade or not academic_year:
            flash('جميع الحقول الأساسية مطلوبة', 'danger')
            return redirect(url_for('teacher.edit_classroom', classroom_id=classroom.id))

        # Handle paid classroom details
        price = None
        duration_days = None
        if not is_free:
            # التحقق من وجود أرقام المحافظ الإلكترونية للمعلم قبل تحويل فصل إلى مدفوع
            if not current_user.has_ewallet_numbers():
                flash('يجب إضافة رقم محفظة إلكترونية في ملفك الشخصي قبل تحويل الفصل إلى مدفوع', 'warning')
                return redirect(url_for('teacher.edit_classroom', classroom_id=classroom.id))
            
            try:
                price = float(request.form.get('price', 0))
                duration_days = int(request.form.get('duration_days', 30))
                
                if price <= 0:
                    flash('يجب أن يكون سعر الفصل أكبر من صفر', 'danger')
                    return redirect(url_for('teacher.edit_classroom', classroom_id=classroom.id))
                    
                if duration_days <= 0:
                    flash('يجب أن تكون مدة الفصل أكبر من صفر', 'danger')
                    return redirect(url_for('teacher.edit_classroom', classroom_id=classroom.id))
            except (ValueError, TypeError):
                flash('قيم السعر والمدة يجب أن تكون أرقام صحيحة', 'danger')
                return redirect(url_for('teacher.edit_classroom', classroom_id=classroom.id))

        # Update classroom
        classroom.name = name
        classroom.subject = subject
        classroom.grade = grade
        classroom.academic_year = academic_year
        classroom.description = description
        classroom.color = color
        classroom.is_free = is_free
        classroom.price = price
        classroom.duration_days = duration_days

        db.session.commit()
        flash('تم تحديث بيانات الفصل بنجاح', 'success')
        return redirect(url_for('teacher.classroom', classroom_id=classroom.id))

    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')

    template = 'teacher/mobile-theme/edit_classroom.html' if is_mobile() else 'teacher/edit_classroom.html'

    return render_template(template,
                         classroom=classroom,
                         primary_color=primary_color,
                         secondary_color=secondary_color)

@teacher_bp.route('/classroom/<int:classroom_id>')
@login_required
@teacher_required
def classroom(classroom_id):
    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')
    
    # التحقق من وجود اشتراك نشط للمعلم
    has_subscription = has_active_subscription()
    if not has_subscription:
        flash('لا يمكنك الوصول إلى الفصول الدراسية. يرجى الاشتراك في باقة نشطة أولاً.', 'warning')
        return redirect(url_for('teacher.dashboard'))
        
    classroom = Classroom.query.get_or_404(classroom_id)

    # Ensure the teacher owns this classroom
    if classroom.teacher_id != current_user.id:
        flash('غير مصرح لك بالوصول إلى هذا الفصل', 'danger')
        return redirect(url_for('teacher.dashboard'))

    # Get classroom content
    contents = ClassroomContent.query.filter_by(classroom_id=classroom.id).order_by(ClassroomContent.created_at.desc()).all()

    # Get enrolled students
    enrollments = ClassroomEnrollment.query.filter_by(classroom_id=classroom.id).all()

    # Get assignments
    assignments = Assignment.query.filter_by(classroom_id=classroom.id).all()

    # Get quizzes
    quizzes = Quiz.query.filter_by(classroom_id=classroom.id).all()

    # Check if the classroom has an assistant
    assistant = None
    if classroom.assistant_id:
        assistant = User.query.get(classroom.assistant_id)

    # Check if plan allows chat
    can_use_chat = False
    can_use_assistant = False
    plan = get_current_plan()
    if plan:
        if plan.has_chat:
            can_use_chat = True
        if plan.allow_assistant:
            can_use_assistant = True

    # Check if assistant is active
    assistant_active = classroom.assistant_id is not None

    template = 'teacher/mobile-theme/classroom.html' if is_mobile() else 'teacher/classroom.html'


    return render_template(template,
                       classroom=classroom,
                       contents=contents,
                       enrollments=enrollments,
                       assignments=assignments,
                       quizzes=quizzes,
                       assistant=assistant,
                       can_use_chat=can_use_chat,
                       can_use_assistant=can_use_assistant,
                       assistant_active=assistant_active,
                       plan=plan,
                       primary_color=primary_color,
                       secondary_color=secondary_color)

@teacher_bp.route('/classrooms')
@login_required
@teacher_required
def list_classrooms():
    # التحقق من وجود اشتراك نشط للمعلم
    has_subscription = has_active_subscription()
    if not has_subscription:
        flash('لا يمكنك الوصول إلى الفصول الدراسية. يرجى الاشتراك في باقة نشطة أولاً.', 'warning')
        return redirect(url_for('teacher.dashboard'))
        
    # Get teacher's classrooms
    classrooms = Classroom.query.filter_by(teacher_id=current_user.id).order_by(Classroom.created_at.desc()).all()

    # Get total number of students for each classroom
    classroom_stats = {}
    for classroom in classrooms:
        enrollments = ClassroomEnrollment.query.filter_by(classroom_id=classroom.id).all()
        classroom_stats[classroom.id] = {
            'total_students': len(enrollments),
            'active_assignments': Assignment.query.filter(
                Assignment.classroom_id == classroom.id,
                Assignment.due_date > datetime.utcnow()
            ).count(),
            'active_quizzes': Quiz.query.filter(
                Quiz.classroom_id == classroom.id,
                Quiz.end_time > datetime.utcnow()
            ).count()
        }

    template = 'teacher/mobile-theme/classrooms.html' if is_mobile() else 'teacher/classrooms.html'

    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي

    # جلب الإشعارات غير المقروءة
    unread_notifications_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()

    return render_template(template,
                         classrooms=classrooms,
                         primary_color=primary_color,
                         secondary_color=secondary_color,
                         classroom_stats=classroom_stats,
                         unread_notifications_count=unread_notifications_count,
                         can_create_classroom=can_create_classroom())

"""
البث المباشر للفصل
إدارة الحصص المباشرة والتفاعل مع الطلاب
"""
@teacher_bp.route('/classroom/<int:classroom_id>/live')
@login_required
@teacher_required
def live_classroom(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)

    # Ensure the teacher owns this classroom
    if classroom.teacher_id != current_user.id:
        flash('غير مصرح لك بالوصول إلى هذا الفصل', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    # Get current active live stream for this classroom
    active_stream = LiveStream.query.filter_by(
        classroom_id=classroom_id,
        is_active=True
    ).first()
    
    # Check if the stream has expired and auto-end it
    if active_stream and active_stream.is_expired:
        active_stream.end_stream()
        active_stream = None
    
    # Get recent streams for this classroom (last 10)
    recent_streams = LiveStream.query.filter_by(
        classroom_id=classroom_id
    ).order_by(LiveStream.created_at.desc()).limit(10).all()
    
    # Get system colors
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')

    template = 'teacher/live_class.html' if not is_mobile() else 'teacher/mobile-theme/live_class.html'
    return render_template(template, 
                         classroom=classroom,
                         active_stream=active_stream,
                         recent_streams=recent_streams,
                         current_time=datetime.utcnow(),
                         user_type='teacher',
                         primary_color=primary_color,
                         secondary_color=secondary_color)

@teacher_bp.route('/classroom/<int:classroom_id>/add_content', methods=['POST'])
@login_required
@teacher_required
def add_content(classroom_id):
    """Add content to classroom with enhanced file handling"""
    classroom = Classroom.query.get_or_404(classroom_id)

    # Ensure the teacher owns this classroom
    if classroom.teacher_id != current_user.id:
        flash('غير مصرح لك بالوصول إلى هذا الفصل', 'danger')
        return redirect(url_for('teacher.classroom', classroom_id=classroom.id))

    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    content_type = request.form.get('content_type')

    # Validate required fields
    if not title:
        flash('يجب إدخال عنوان المحتوى', 'danger')
        return redirect(url_for('teacher.classroom', classroom_id=classroom.id))

    # Validate content type
    valid_types = [ContentType.FILE, ContentType.IMAGE, ContentType.AUDIO, ContentType.VIDEO, ContentType.TEXT]
    if content_type not in valid_types:
        flash('نوع المحتوى غير صالح', 'danger')
        return redirect(url_for('teacher.classroom', classroom_id=classroom.id))

    content_url = None
    content_text = None

    try:
        if content_type == ContentType.TEXT:
            # Handle text content
            content_text = request.form.get('content_text', '').strip()
            if not content_text:
                flash('يجب إدخال محتوى نصي', 'danger')
                return redirect(url_for('teacher.classroom', classroom_id=classroom.id))
        else:
            # Handle file upload
            if 'content_file' not in request.files:
                flash('لم يتم تحديد ملف', 'danger')
                return redirect(url_for('teacher.classroom', classroom_id=classroom.id))

            file = request.files['content_file']

            if not file or file.filename == '':
                flash('لم يتم اختيار ملف صالح', 'danger')
                return redirect(url_for('teacher.classroom', classroom_id=classroom.id))

            # Validate file extension
            if not allowed_file(file.filename):
                flash('نوع الملف غير مدعوم', 'danger')
                return redirect(url_for('teacher.classroom', classroom_id=classroom.id))

            # Get file size for logging (بدون فحص القيود)
            file.seek(0, 2)  # Seek to end to get size
            file_size = file.tell()
            file.seek(0)  # Reset file pointer
            
            current_app.logger.info(f"Processing file upload: {file.filename} ({file_size} bytes)")

            # Create upload directory
            upload_dir = os.path.join('static', 'uploads', 'classroom_content', str(classroom_id))
            abs_upload_dir = os.path.join(current_app.root_path, upload_dir)
            
            try:
                os.makedirs(abs_upload_dir, exist_ok=True)
            except Exception as e:
                current_app.logger.error(f"Error creating upload directory: {e}")
                flash('خطأ في إنشاء مجلد التحميل', 'danger')
                return redirect(url_for('teacher.classroom', classroom_id=classroom.id))

            # Generate secure filename
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')[:-3]  # Include milliseconds
            _, file_extension = os.path.splitext(secure_filename(file.filename))
            saved_filename = f"{timestamp}_{secure_filename(os.path.splitext(file.filename)[0])}{file_extension}"
            
            # Save file
            file_path = os.path.join(abs_upload_dir, saved_filename)
            
            try:
                # Save file in chunks for large files
                with open(file_path, 'wb') as f:
                    while True:
                        chunk = file.read(8192)  # 8KB chunks
                        if not chunk:
                            break
                        f.write(chunk)
                
                # Verify file was saved
                if not os.path.exists(file_path) or os.path.getsize(file_path) != file_size:
                    raise Exception("فشل في حفظ الملف بشكل صحيح")
                
                # Create URL for database
                content_url = f"/static/uploads/classroom_content/{classroom_id}/{saved_filename}"
                
                current_app.logger.info(f"File uploaded successfully: {file_path} ({file_size} bytes)")
                
            except Exception as e:
                current_app.logger.error(f"Error saving file: {e}")
                # Clean up partial file if exists
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except:
                        pass
                flash(f'حدث خطأ أثناء حفظ الملف: {str(e)}', 'danger')
                return redirect(url_for('teacher.classroom', classroom_id=classroom.id))

        # Create content record
        new_content = ClassroomContent(
            classroom_id=classroom.id,
            title=title,
            description=description,
            content_type=content_type,
            content_url=content_url,
            content_text=content_text
        )

        db.session.add(new_content)
        db.session.commit()

        flash('تم إضافة المحتوى بنجاح', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding content: {e}")
        flash(f'حدث خطأ أثناء إضافة المحتوى: {str(e)}', 'danger')

    return redirect(url_for('teacher.classroom', classroom_id=classroom.id))




@teacher_bp.route('/classroom/<int:classroom_id>/delete_content/<int:content_id>', methods=['POST'])
@login_required
@teacher_required
def delete_content(classroom_id, content_id):

  
    classroom = Classroom.query.get_or_404(classroom_id)
    content = ClassroomContent.query.get_or_404(content_id)

    # Ensure the teacher owns this classroom and content
    if classroom.teacher_id != current_user.id or content.classroom_id != classroom.id:
        flash('غير مصرح لك بالوصول إلى هذا المحتوى', 'danger')
        return redirect(url_for('teacher.dashboard'))

    try:
        # Delete physical file if it exists
        if content.content_url and content.content_type != ContentType.TEXT:
            file_path = os.path.join(current_app.root_path, 'static', 'uploads', 'classroom_content', str(classroom_id), os.path.basename(content.content_url))
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Deleted physical file: {file_path}")

        # Delete database record
        db.session.delete(content)
        db.session.commit()

        flash('تم حذف المحتوى بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting content: {e}")
        flash('حدث خطأ أثناء حذف المحتوى', 'danger')

    return redirect(url_for('teacher.classroom', classroom_id=classroom.id))



@teacher_bp.route('/classroom/<int:classroom_id>/assignments')
@login_required
@teacher_required
def assignments(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)

    # Ensure the teacher owns this classroom
    if classroom.teacher_id != current_user.id:
        flash('غير مصرح لك بالوصول إلى هذا الفصل', 'danger')
        return redirect(url_for('teacher.dashboard'))

    # Get assignments
    assignments = Assignment.query.filter_by(classroom_id=classroom.id).order_by(Assignment.created_at.desc()).all()

    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي

    template = 'classroom/mobile-theme/assignments.html' if is_mobile() else 'classroom/assignments.html'


    return render_template(template,
                           classroom=classroom,
                           assignments=assignments,
                           primary_color=primary_color,
                           secondary_color=secondary_color,)


@teacher_bp.route('/classroom/<int:classroom_id>/create_assignment', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_assignment(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)

    # Ensure the teacher owns this classroom
    if classroom.teacher_id != current_user.id:
        flash('غير مصرح لك بالوصول إلى هذا الفصل', 'danger')
        return redirect(url_for('teacher.dashboard'))

    if request.method == 'POST':


      
        title = request.form.get('title')
        description = request.form.get('description')
        due_date_str = request.form.get('due_date')
        points = int(request.form.get('points', 10))

        # Parse due date if provided
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('تنسيق التاريخ غير صالح', 'danger')
                return redirect(url_for('teacher.create_assignment', classroom_id=classroom.id))

        attachment_url = None
        if 'assignment_file' in request.files:
            file = request.files['assignment_file']
            if file and file.filename:
                # الحصول على الامتداد الأصلي للملف
                filename = file.filename
                if allowed_file(filename):
                    try:
                        # Create assignments directory if it doesn't exist
                        assignments_dir = os.path.join('static', 'uploads', 'assignments')
                        if not os.path.exists(assignments_dir):
                            os.makedirs(assignments_dir, exist_ok=True)
                            
                        # Create classroom-specific directory if it doesn't exist
                        upload_dir = os.path.join(assignments_dir, str(classroom_id))
                        if not os.path.exists(upload_dir):
                            os.makedirs(upload_dir)

                        # Generate filename with timestamp while keeping the original extension
                        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
                        original_name, file_extension = os.path.splitext(filename)
                        saved_filename = f"{timestamp}_{file_extension}"  # إضافة underscore قبل الامتداد
                        
                        # Get absolute path for saving
                        file_path = os.path.join(os.getcwd(), upload_dir, saved_filename)
                        
                        # Save file
                        file.save(file_path)
                        
                        # Store relative URL for database
                        attachment_url = f"/uploads/assignments/{classroom_id}/{saved_filename}"
                        
                        print(f"تم حفظ الملف بنجاح في: {file_path}")
                        print(f"الامتداد الأصلي: {file_extension}")
                        
                    except Exception as e:
                        print(f"خطأ في رفع الملف: {e}")
                        flash(f'حدث خطأ أثناء رفع الملف: {str(e)}', 'danger')
                        return redirect(url_for('teacher.assignments', classroom_id=classroom.id))
                else:
                    flash('نوع الملف غير مسموح به', 'danger')
                    return redirect(url_for('teacher.assignments', classroom_id=classroom.id))

        # Create assignment
        new_assignment = Assignment(
            classroom_id=classroom.id,
            title=title,
            description=description,
            due_date=due_date,
            points=points,
            attachment_url=attachment_url
        )

        db.session.add(new_assignment)
        db.session.commit()

        flash('تم إنشاء الواجب بنجاح', 'success')
        return redirect(url_for('teacher.assignments', classroom_id=classroom.id))
    
    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي

    template = 'classroom/mobile-theme/assignments.html' if is_mobile() else 'classroom/assignments.html'


    return render_template(template, classroom=classroom,
                           primary_color=primary_color,
                           secondary_color=secondary_color,)



@teacher_bp.route('/classroom/<int:classroom_id>/assignment/<int:assignment_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_assignment(classroom_id, assignment_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    assignment = Assignment.query.get_or_404(assignment_id)

    # Ensure the teacher owns this classroom and assignment
    if classroom.teacher_id != current_user.id or assignment.classroom_id != classroom.id:
        flash('غير مصرح لك بتعديل هذا الواجب', 'danger')
        return redirect(url_for('teacher.dashboard'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        due_date_str = request.form.get('due_date')
        points = int(request.form.get('points', 10))

        # Parse due date if provided
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('تنسيق التاريخ غير صالح', 'danger')
                return redirect(url_for('teacher.edit_assignment', classroom_id=classroom.id, assignment_id=assignment.id))

        # Handle new file upload if provided
        if 'assignment_file' in request.files:
            file = request.files['assignment_file']
            if file and file.filename:
                if allowed_file(file.filename):
                    try:
                        # Create classroom-specific directory if it doesn't exist
                        upload_dir = os.path.join('static', 'uploads', 'assignments', str(classroom_id))
                        os.makedirs(upload_dir, exist_ok=True)

                        # Generate secure filename with timestamp
                        filename = secure_filename(file.filename)
                        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
                        saved_filename = f"{timestamp}_{filename}"
                        
                        # Save file
                        file_path = os.path.join(upload_dir, saved_filename)
                        file.save(file_path)
                        
                        # Update assignment's attachment URL
                        assignment.attachment_url = f"/uploads/assignments/{classroom_id}/{saved_filename}"
                        
                    except Exception as e:
                        flash(f'حدث خطأ أثناء رفع الملف: {str(e)}', 'danger')
                        return redirect(url_for('teacher.edit_assignment', classroom_id=classroom.id, assignment_id=assignment.id))
                else:
                    flash('نوع الملف غير مسموح به', 'danger')
                    return redirect(url_for('teacher.edit_assignment', classroom_id=classroom.id, assignment_id=assignment.id))

        # Update assignment
        assignment.title = title
        assignment.description = description
        assignment.due_date = due_date
        assignment.points = points

        db.session.commit()
        flash('تم تحديث الواجب بنجاح', 'success')
        return redirect(url_for('teacher.assignments', classroom_id=classroom.id))
    
    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي

    template = 'classroom/mobile-theme/edit_assignment.html' if is_mobile() else 'classroom/edit_assignment.html'



    return render_template(template,
                         classroom=classroom,
                         assignment=assignment,
                         primary_color=primary_color,
                         secondary_color=secondary_color)


@teacher_bp.route('/classroom/<int:classroom_id>/assignment/<int:assignment_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_assignment(classroom_id, assignment_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    assignment = Assignment.query.get_or_404(assignment_id)

    # Ensure the teacher owns this classroom and assignment
    if classroom.teacher_id != current_user.id or assignment.classroom_id != classroom.id:
        flash('غير مصرح لك بحذف هذا الواجب', 'danger')
        return redirect(url_for('teacher.dashboard'))

    # Delete all submissions first
    AssignmentSubmission.query.filter_by(assignment_id=assignment.id).delete()
    
    # Delete the assignment
    db.session.delete(assignment)
    db.session.commit()

    flash('تم حذف الواجب بنجاح', 'success')
    return redirect(url_for('teacher.assignments', classroom_id=classroom.id))


@teacher_bp.route('/classroom/<int:classroom_id>/assignment/<int:assignment_id>/submissions')
@login_required
@teacher_required
def assignment_submissions(classroom_id, assignment_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    assignment = Assignment.query.get_or_404(assignment_id)

    # Ensure the teacher owns this classroom
    if classroom.teacher_id != current_user.id or assignment.classroom_id != classroom.id:
        flash('غير مصرح لك بالوصول إلى هذا الواجب', 'danger')
        return redirect(url_for('teacher.dashboard'))

    # Get submissions
    submissions = AssignmentSubmission.query.join(ClassroomEnrollment).filter(
        AssignmentSubmission.assignment_id == assignment.id,
        ClassroomEnrollment.classroom_id == classroom.id
    ).all()

    # Get students who haven't submitted
    enrolled_students = ClassroomEnrollment.query.filter_by(classroom_id=classroom.id).all()
    submitted_student_ids = [sub.enrollment.user_id for sub in submissions]
    missing_submissions = [
        enrollment for enrollment in enrolled_students 
        if enrollment.user_id not in submitted_student_ids
    ]

    template = 'teacher/mobile-theme/assignment_submissions.html' if is_mobile() else 'teacher/assignment_submissions.html'

    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي


    return render_template(template,
                           classroom=classroom,
                           assignment=assignment,
                           submissions=submissions,
                           missing_submissions=missing_submissions,
                           primary_color=primary_color,
                           secondary_color=secondary_color,)



@teacher_bp.route('/classroom/<int:classroom_id>/assignment/<int:assignment_id>/grade/<int:submission_id>', methods=['POST'])
@login_required
@teacher_required
def grade_submission(classroom_id, assignment_id, submission_id):

    
    classroom = Classroom.query.get_or_404(classroom_id)
    assignment = Assignment.query.get_or_404(assignment_id)
    submission = AssignmentSubmission.query.get_or_404(submission_id)

    # Ensure the teacher owns this classroom
    if classroom.teacher_id != current_user.id or assignment.classroom_id != classroom.id:
        flash('غير مصرح لك بالوصول إلى هذا الواجب', 'danger')
        return redirect(url_for('teacher.dashboard'))

    grade = int(request.form.get('grade', 0))
    feedback = request.form.get('feedback', '')

    # Ensure grade is within assignment points
    if grade > assignment.points:
        grade = assignment.points

    # Update submission
    submission.grade = grade
    submission.feedback = feedback

    # Add points to student's enrollment
    enrollment = submission.enrollment
    enrollment.points += grade

    db.session.commit()

    flash('تم تقييم الواجب بنجاح', 'success')
    return redirect(url_for('teacher.assignment_submissions', classroom_id=classroom.id, assignment_id=assignment.id))

"""
إدارة الاختبارات
إنشاء وتحرير وتصحيح الاختبارات
"""
@teacher_bp.route('/classroom/<int:classroom_id>/quizzes')
@login_required
@teacher_required
def quizzes(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)

    # Ensure the teacher owns this classroom
    if classroom.teacher_id != current_user.id:
        flash('غير مصرح لك بالوصول إلى هذا الفصل', 'danger')
        return redirect(url_for('teacher.dashboard'))

    # Get quizzes
    quizzes = Quiz.query.filter_by(classroom_id=classroom.id).order_by(Quiz.created_at.desc()).all()

    template = 'teacher/mobile-theme/quizzes.html' if is_mobile() else 'teacher/quizzes.html'

    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي



    return render_template(template,
                           classroom=classroom,
                           quizzes=quizzes,
                           primary_color=primary_color,
                           secondary_color=secondary_color,)



@teacher_bp.route('/classroom/<int:classroom_id>/create_quiz', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_quiz(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)

    # Ensure the teacher owns this classroom
    if classroom.teacher_id != current_user.id:
        flash('غير مصرح لك بالوصول إلى هذا الفصل', 'danger')
        return redirect(url_for('teacher.dashboard'))

    if request.method == 'POST':

        
        title = request.form.get('title')
        description = request.form.get('description', '')
        duration_minutes = int(request.form.get('duration_minutes', 0))
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')

        # Parse dates if provided
        start_time = None
        end_time = None

        if start_time_str:
            try:
                start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('تنسيق وقت البدء غير صالح', 'danger')
                return redirect(url_for('teacher.create_quiz', classroom_id=classroom.id))

        if end_time_str:
            try:
                end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('تنسيق وقت النهاية غير صالح', 'danger')
                return redirect(url_for('teacher.create_quiz', classroom_id=classroom.id))

        # Create quiz
        new_quiz = Quiz(
            classroom_id=classroom.id,
            title=title,
            description=description,
            duration_minutes=duration_minutes,
            start_time=start_time,
            end_time=end_time,
            is_active=True
        )

        db.session.add(new_quiz)
        db.session.commit()

        flash('تم إنشاء الاختبار بنجاح. قم بإضافة الأسئلة الآن', 'success')
        return redirect(url_for('teacher.edit_quiz', classroom_id=classroom.id, quiz_id=new_quiz.id))
    
    template = 'teacher/mobile-theme/create_quiz.html' if is_mobile() else 'teacher/create_quiz.html'

    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي



    return render_template(template, classroom=classroom,
                           primary_color=primary_color,
                           secondary_color=secondary_color,)



@teacher_bp.route('/classroom/<int:classroom_id>/quiz/<int:quiz_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_quiz(classroom_id, quiz_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    quiz = Quiz.query.get_or_404(quiz_id)

    # Ensure the teacher owns this classroom
    if classroom.teacher_id != current_user.id or quiz.classroom_id != classroom.id:
        flash('غير مصرح لك بالوصول إلى هذا الاختبار', 'danger')
        return redirect(url_for('teacher.dashboard'))

    if request.method == 'POST':
        # Update basic quiz information
        title = request.form.get('title')
        description = request.form.get('description', '')
        duration_minutes = int(request.form.get('duration_minutes', 0))
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')

        # Parse dates if provided
        start_time = None
        end_time = None

        if start_time_str:
            try:
                start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('تنسيق وقت البدء غير صالح', 'danger')
                return redirect(url_for('teacher.edit_quiz', classroom_id=classroom.id, quiz_id=quiz.id))

        if end_time_str:
            try:
                end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('تنسيق وقت النهاية غير صالح', 'danger')
                return redirect(url_for('teacher.edit_quiz', classroom_id=classroom.id, quiz_id=quiz.id))

        # Update quiz
        quiz.title = title
        quiz.description = description
        quiz.duration_minutes = duration_minutes
        quiz.start_time = start_time
        quiz.end_time = end_time

        db.session.commit()
        flash('تم تحديث معلومات الاختبار بنجاح', 'success')
        return redirect(url_for('teacher.edit_quiz', classroom_id=classroom.id, quiz_id=quiz.id))

    # Get existing questions for display
    questions = QuizQuestion.query.filter_by(quiz_id=quiz.id).order_by(QuizQuestion.position).all()

    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي


    template = 'teacher/mobile-theme/edit_quiz.html' if is_mobile() else 'teacher/edit_quiz.html'


    return render_template(template,
                         classroom=classroom,
                         quiz=quiz,
                         questions=questions,
                         primary_color=primary_color,
                         secondary_color=secondary_color,)



@teacher_bp.route('/classroom/<int:classroom_id>/quiz/<int:quiz_id>/add_question', methods=['POST'])
@login_required
@teacher_required
def add_question(classroom_id, quiz_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    quiz = Quiz.query.get_or_404(quiz_id)

    # Ensure the teacher owns this classroom
    if classroom.teacher_id != current_user.id or quiz.classroom_id != classroom.id:
        flash('غير مصرح لك بالوصول إلى هذا الاختبار', 'danger')
        return redirect(url_for('teacher.dashboard'))

    question_text = request.form.get('question_text')
    question_type = request.form.get('question_type')
    points = int(request.form.get('points', 1))

    # Get current highest position
    last_position = db.session.query(db.func.max(QuizQuestion.position)).filter_by(quiz_id=quiz.id).scalar() or 0

    # Create question
    new_question = QuizQuestion(
        quiz_id=quiz.id,
        question_text=question_text,
        question_type=question_type,
        points=points,
        position=last_position + 1
    )

    db.session.add(new_question)
    db.session.flush()  # Get the question ID without committing

    # For multiple choice or true/false, add options
    if question_type in ['multiple_choice', 'true_false']:
        # Handle options from form
        option_texts = request.form.getlist('option_text[]')
        correct_option = request.form.get('correct_option')

        for i, text in enumerate(option_texts):
            if text.strip():  # Only add non-empty options
                is_correct = (str(i) == correct_option)
                option = QuizQuestionOption(
                    question_id=new_question.id,
                    option_text=text,
                    is_correct=is_correct,
                    position=i
                )
                db.session.add(option)

    # Update quiz total points
    quiz.total_points += points

    db.session.commit()

    flash('تم إضافة السؤال بنجاح', 'success')
    return redirect(url_for('teacher.edit_quiz', classroom_id=classroom.id, quiz_id=quiz.id))



@teacher_bp.route('/classroom/<int:classroom_id>/quiz/<int:quiz_id>/delete_question/<int:question_id>', methods=['POST'])
@login_required
@teacher_required
def delete_question(classroom_id, quiz_id, question_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    quiz = Quiz.query.get_or_404(quiz_id)
    question = QuizQuestion.query.get_or_404(question_id)

    # Ensure the teacher owns this classroom and question
    if classroom.teacher_id != current_user.id or quiz.classroom_id != classroom.id or question.quiz_id != quiz.id:
        flash('غير مصرح لك بالوصول إلى هذا السؤال', 'danger')
        return redirect(url_for('teacher.dashboard'))

    # Update quiz total points
    quiz.total_points -= question.points
    if quiz.total_points < 0:
        quiz.total_points = 0

    # Delete question (and its options through cascade)
    db.session.delete(question)
    db.session.commit()

    flash('تم حذف السؤال بنجاح', 'success')
    return redirect(url_for('teacher.edit_quiz', classroom_id=classroom.id, quiz_id=quiz.id))



@teacher_bp.route('/classroom/<int:classroom_id>/quiz/<int:quiz_id>/grade')
@login_required
@teacher_required
def grade_quiz(classroom_id, quiz_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    quiz = Quiz.query.get_or_404(quiz_id)

    # Ensure the teacher owns this classroom
    if classroom.teacher_id != current_user.id or quiz.classroom_id != classroom.id:
        flash('غير مصرح لك بالوصول إلى هذا الاختبار', 'danger')
        return redirect(url_for('teacher.dashboard'))

    # Get attempts that need grading (have ungraded essay/short answer questions)
    attempts = QuizAttempt.query\
        .join(QuizAnswer)\
        .join(QuizQuestion)\
        .filter(
            QuizAttempt.quiz_id == quiz.id,
            QuizQuestion.question_type.in_(['essay', 'short_answer']),
            QuizAnswer.points_earned.is_(None),
            QuizAttempt.is_completed == True
        )\
        .distinct()\
        .all()
    
    template = 'teacher/mobile-theme/grade_quiz.html' if is_mobile() else 'teacher/grade_quiz.html'

    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي


    return render_template(template,
                           classroom=classroom,
                           quiz=quiz,
                           attempts=attempts,
                           primary_color=primary_color,
                           secondary_color=secondary_color,)



@teacher_bp.route('/classroom/<int:classroom_id>/quiz/<int:quiz_id>/attempt/<int:attempt_id>/grade', methods=['POST'])
@login_required
@teacher_required
def grade_quiz_attempt(classroom_id, quiz_id, attempt_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    quiz = Quiz.query.get_or_404(quiz_id)
    attempt = QuizAttempt.query.get_or_404(attempt_id)

    # Ensure the teacher owns this classroom
    if classroom.teacher_id != current_user.id or quiz.classroom_id != classroom.id or attempt.quiz_id != quiz.id:
        flash('غير مصرح لك بالوصول إلى هذا الاختبار', 'danger')
        return redirect(url_for('teacher.dashboard'))

    # Process grades
    total_points = 0
    all_graded = True

    for answer in attempt.answers:
        if answer.question.question_type in ['essay', 'short_answer']:
            points_str = request.form.get(f'points_{answer.id}')
            feedback = request.form.get(f'feedback_{answer.id}')
            
            if points_str is None:
                # هذا السؤال لم يتم تصحيحه بعد
                all_graded = False
                continue
                
            try:
                points = float(points_str)
                # التأكد من أن النقاط ضمن الحدود المسموحة
                points = max(0, min(points, answer.question.points))
                answer.points_earned = points
                answer.feedback = feedback
                total_points += points
            except ValueError:
                flash('قيمة النقاط غير صالحة', 'danger')
                return redirect(url_for('teacher.grade_quiz', classroom_id=classroom.id, quiz_id=quiz.id))

    if all_graded:
        # Update attempt total score if all questions are graded
        current_score = attempt.score or 0
        attempt.score = current_score + total_points
        # إضافة النقاط إلى نقاط الطالب
        attempt.enrollment.points += total_points
        flash('تم حفظ التصحيح بنجاح', 'success')
    else:
        flash('يرجى تصحيح جميع الأسئلة', 'danger')
        return redirect(url_for('teacher.grade_quiz', classroom_id=classroom.id, quiz_id=quiz.id))

    try:
        db.session.commit()
    except:
        db.session.rollback()
        flash('حدث خطأ أثناء حفظ التصحيح', 'danger')
        return redirect(url_for('teacher.grade_quiz', classroom_id=classroom.id, quiz_id=quiz.id))

    return redirect(url_for('teacher.grade_quiz', classroom_id=classroom.id, quiz_id=quiz.id))



@teacher_bp.route('/classroom/<int:classroom_id>/quiz/<int:quiz_id>/results')
@login_required
@teacher_required
def quiz_results(classroom_id, quiz_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    quiz = Quiz.query.get_or_404(quiz_id)

    # Ensure the teacher owns this classroom
    if classroom.teacher_id != current_user.id or quiz.classroom_id != classroom.id:
        flash('غير مصرح لك بالوصول إلى هذا الاختبار', 'danger')
        return redirect(url_for('teacher.dashboard'))

    # Get all attempts for this quiz, including user information through enrollment
    attempts = QuizAttempt.query.filter_by(quiz_id=quiz.id).order_by(QuizAttempt.start_time.desc()).all()

    template = 'teacher/mobile-theme/quiz_results.html' if is_mobile() else 'teacher/quiz_results.html'

    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي


    return render_template(template,
                         classroom=classroom,
                         quiz=quiz,
                         attempts=attempts,
                         primary_color=primary_color,
                         secondary_color=secondary_color,)



@teacher_bp.route('/classroom/<int:classroom_id>/quiz/<int:quiz_id>/attempt/<int:attempt_id>/view')
@login_required
@teacher_required
def view_student_attempt(classroom_id, quiz_id, attempt_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    quiz = Quiz.query.get_or_404(quiz_id)
    attempt = QuizAttempt.query.get_or_404(attempt_id)

    # Ensure the teacher owns this classroom and the attempt belongs to this quiz
    if classroom.teacher_id != current_user.id or quiz.classroom_id != classroom.id or attempt.quiz_id != quiz.id:
        flash('غير مصرح لك بالوصول إلى هذا الاختبار', 'danger')
        return redirect(url_for('teacher.dashboard'))

    # Get answers with their questions, ordered by question position
    answers = QuizAnswer.query\
        .join(QuizQuestion)\
        .filter(QuizAnswer.attempt_id == attempt.id)\
        .order_by(QuizQuestion.position)\
        .all()
    
    template = 'teacher/mobile-theme/view_student_attempt.html' if is_mobile() else 'teacher/view_student_attempt.html'

    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي


    return render_template(template,
                         classroom=classroom,
                         quiz=quiz,
                         attempt=attempt,
                         answers=answers,
                         primary_color=primary_color,
                         secondary_color=secondary_color,)



@teacher_bp.route('/classroom/<int:classroom_id>/students')
@login_required
@teacher_required
def students(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)

    # Ensure the teacher owns this classroom
    if classroom.teacher_id != current_user.id:
        flash('غير مصرح لك بالوصول إلى هذا الفصل', 'danger')
        return redirect(url_for('teacher.dashboard'))

    # Get enrollments with students
    enrollments = ClassroomEnrollment.query.filter_by(classroom_id=classroom.id).all()

    template = 'teacher/mobile-theme/students.html' if is_mobile() else 'teacher/students.html'

    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي



    return render_template(template,
                           classroom=classroom,
                           enrollments=enrollments,
                           primary_color=primary_color,
                           secondary_color=secondary_color,)



@teacher_bp.route('/classroom/<int:classroom_id>/student/<int:enrollment_id>/toggle_status', methods=['POST'])
@login_required
@teacher_required
def toggle_student_status(classroom_id, enrollment_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    enrollment = ClassroomEnrollment.query.get_or_404(enrollment_id)

    # Ensure the teacher owns this classroom and enrollment
    if classroom.teacher_id != current_user.id or enrollment.classroom_id != classroom.id:
        flash('غير مصرح لك بالوصول إلى هذا الطالب', 'danger')
        return redirect(url_for('teacher.dashboard'))

    enrollment.is_active = not enrollment.is_active
    db.session.commit()

    status = "تفعيل" if enrollment.is_active else "تعطيل"
    flash(f'تم {status} الطالب في الفصل بنجاح', 'success')
    return redirect(url_for('teacher.students', classroom_id=classroom.id))


@teacher_bp.route('/classroom/<int:classroom_id>/set_assistant', methods=['POST'])
@login_required
@teacher_required
def set_assistant(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)

    # Ensure the teacher owns this classroom
    if classroom.teacher_id != current_user.id:
        flash('غير مصرح لك بالوصول إلى هذا الفصل', 'danger')
        return redirect(url_for('teacher.dashboard'))

    # Check if plan allows assistant
    plan = get_current_plan()
    if not plan or not plan.allow_assistant:
        flash('باقة اشتراكك الحالية لا تسمح بتعيين مساعد. الرجاء ترقية اشتراكك', 'warning')
        return redirect(url_for('teacher.classroom', classroom_id=classroom.id))

    assistant_phone = request.form.get('assistant_phone')

    # Find user by phone
    assistant = User.query.filter_by(phone=assistant_phone, role=Role.ASSISTANT).first()

    if not assistant:
        flash('لم يتم العثور على مساعد بهذا الرقم. تأكد من أن المستخدم مسجل كمساعد', 'danger')
        return redirect(url_for('teacher.classroom', classroom_id=classroom.id))

    # Set assistant
    classroom.assistant_id = assistant.id
    db.session.commit()

    flash(f'تم تعيين {assistant.name} كمساعد للفصل بنجاح', 'success')
    return redirect(url_for('teacher.classroom', classroom_id=classroom.id))



@teacher_bp.route('/classroom/<int:classroom_id>/remove_assistant', methods=['POST'])
@login_required
@teacher_required
def remove_assistant(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)

    # Ensure the teacher owns this classroom
    if classroom.teacher_id != current_user.id:
        flash('غير مصرح لك بالوصول إلى هذا الفصل', 'danger')
        return redirect(url_for('teacher.dashboard'))

    classroom.assistant_id = None
    db.session.commit()

    flash('تم إزالة المساعد من الفصل بنجاح', 'success')
    return redirect(url_for('teacher.classroom', classroom_id=classroom.id))


@teacher_bp.route('/classroom/<int:classroom_id>/chat/settings', methods=['GET', 'POST'])
@login_required
@teacher_required
def chat_settings(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)

    # Ensure the teacher owns this classroom
    if classroom.teacher_id != current_user.id:
        flash('غير مصرح لك بالوصول إلى هذا الفصل', 'danger')
        return redirect(url_for('teacher.dashboard'))

    # Check if plan allows chat
    plan = get_current_plan()
    if not plan or not plan.has_chat:
        flash('باقة اشتراكك الحالية لا تتضمن ميزة المحادثات', 'warning')
        return redirect(url_for('teacher.classroom', classroom_id=classroom.id))

    # Get or create chat settings
    settings = ChatSettings.query.filter_by(classroom_id=classroom.id).first()
    if not settings:
        settings = ChatSettings(classroom_id=classroom.id)
        db.session.add(settings)
        db.session.commit()

    if request.method == 'POST':
        settings.background_color = request.form.get('background_color')
        settings.is_enabled = 'is_enabled' in request.form

        # Handle image upload
        if 'chat_image' in request.files:
            image = request.files['chat_image']
            if image and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                filepath = os.path.join('uploads', 'chat_images', filename)
                if not os.path.exists(os.path.dirname(filepath)):
                    os.makedirs(os.path.dirname(filepath))
                image.save(filepath)
                settings.image_url = filepath

        db.session.commit()
        flash('تم حفظ إعدادات المحادثة بنجاح', 'success')
        return redirect(url_for('teacher.chat_settings', classroom_id=classroom.id))

    # Get enrolled students
    enrollments = ClassroomEnrollment.query.filter_by(classroom_id=classroom.id).all()

    # Get chat participants
    chat_participants = ChatParticipant.query.filter_by(classroom_id=classroom.id).all()

    template = 'classroom/mobile-theme/chat_settings.html' if is_mobile() else 'classroom/chat_settings.html'

    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي



    return render_template(template
                           ,
                         classroom=classroom,
                         settings=settings,
                         enrollments=enrollments,
                         chat_participants=chat_participants,
                         user_type='teacher',
                         primary_color=primary_color,
                         secondary_color=secondary_color,)



@teacher_bp.route('/classroom/<int:classroom_id>/chat/manage_participants', methods=['POST'])
@login_required
@teacher_required
def manage_chat_participants(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)

    # Ensure the teacher owns this classroom
    if classroom.teacher_id != current_user.id:
        flash('غير مصرح لك بالوصول إلى هذا الفصل', 'danger')
        return redirect(url_for('teacher.dashboard'))

    action = request.form.get('action')
    enrollment_id = request.form.get('enrollment_id')

    if not action or not enrollment_id:
        flash('بيانات غير كاملة', 'danger')
        return redirect(url_for('teacher.chat_settings', classroom_id=classroom.id))

    enrollment = ClassroomEnrollment.query.get_or_404(enrollment_id)
    if enrollment.classroom_id != classroom.id:
        flash('الطالب غير مسجل في هذا الفصل', 'danger')
        return redirect(url_for('teacher.chat_settings', classroom_id=classroom.id))

    participant = ChatParticipant.query.filter_by(
        classroom_id=classroom.id,
        enrollment_id=enrollment.id
    ).first()

    if action == 'add':
        if not participant:
            participant = ChatParticipant(
                classroom_id=classroom.id,
                enrollment_id=enrollment.id,
                added_by_id=current_user.id
            )
            db.session.add(participant)
            flash('تمت إضافة الطالب إلى المحادثة بنجاح', 'success')
        else:
            participant.is_enabled = True
            flash('تم تفعيل الطالب في المحادثة', 'success')

    elif action == 'remove':
        if participant:
            participant.is_enabled = False
            flash('تم منع الطالب من الوصول إلى المحادثة', 'success')

    db.session.commit()
    return redirect(url_for('teacher.chat_settings', classroom_id=classroom.id))



@teacher_bp.route('/payments')
@login_required
@teacher_required
def payments():
    # الحصول على الفصول الخاصة بالمعلم
    classrooms = Classroom.query.filter_by(teacher_id=current_user.id).all()
    
    # الحصول على جميع عمليات الدفع المعلقة للفصول
    pending_payments = Payment.query.join(Classroom)\
        .filter(
            Classroom.teacher_id == current_user.id,
            Payment.status == 'pending'
        ).order_by(Payment.created_at.desc()).all()
    
    # الحصول على جميع عمليات الدفع المكتملة للفصول
    completed_payments = Payment.query.join(Classroom)\
        .filter(
            Classroom.teacher_id == current_user.id,
            Payment.status.in_(['success', 'failed'])
        ).order_by(Payment.created_at.desc()).all()
    
    template = 'teacher/mobile-theme/payments.html' if is_mobile() else 'teacher/payments.html'

    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي


    return render_template(template,
                         classrooms=classrooms,
                         pending_payments=pending_payments,
                         completed_payments=completed_payments,
                         primary_color=primary_color,
                         secondary_color=secondary_color,)


@teacher_bp.route('/payment/<int:payment_id>/approve', methods=['POST'])
@login_required
@teacher_required
def approve_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    
    # التحقق من أن المعلم يملك هذا الفصل
    if payment.classroom.teacher_id != current_user.id:
        flash('غير مصرح لك بإدارة هذا الدفع', 'danger')
        return redirect(url_for('teacher.payments'))
    
    # تحديث حالة الدفع
    payment.status = 'success'
    
    # تفعيل اشتراك الطالب في الفصل
    enrollment = ClassroomEnrollment.query.filter_by(
        user_id=payment.user_id,
        classroom_id=payment.classroom_id
    ).first()
    
    if enrollment:
        enrollment.payment_status = 'paid'
        enrollment.is_active = True
        enrollment.payment_date = datetime.utcnow()
    
    db.session.commit()
    flash('تم تفعيل اشتراك الطالب بنجاح', 'success')
    return redirect(url_for('teacher.payments'))


@teacher_bp.route('/payment/<int:payment_id>/reject', methods=['POST'])
@login_required
@teacher_required
def reject_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    
    # التحقق من أن المعلم يملك هذا الفصل
    if payment.classroom.teacher_id != current_user.id:
        flash('غير مصرح لك بإدارة هذا الدفع', 'danger')
        return redirect(url_for('teacher.payments'))
    
    # تحديث حالة الدفع
    payment.status = 'failed'
    
    # تعطيل اشتراك الطالب في الفصل
    enrollment = ClassroomEnrollment.query.filter_by(
        user_id=payment.user_id,
        classroom_id=payment.classroom_id
    ).first()
    
    if enrollment:
        enrollment.payment_status = 'failed'
        enrollment.is_active = False
    
    db.session.commit()
    flash('تم رفض عملية الدفع', 'danger')
    return redirect(url_for('teacher.payments'))



@teacher_bp.route('/classroom/<int:classroom_id>/analytics')
@login_required
@teacher_required
def classroom_analytics(classroom_id):
    """جلب تحليلات إضافية للفصل الدراسي"""
    classroom = Classroom.query.get_or_404(classroom_id)
    
    # التحقق من ملكية الفصل
    if classroom.teacher_id != current_user.id:
        return jsonify({'error': 'غير مصرح لك بالوصول إلى هذا الفصل'}), 403

    # تحليلات الواجبات
    assignments = Assignment.query.filter_by(classroom_id=classroom_id).all()
    submissions_by_month = db.session.query(
        db.func.strftime('%Y-%m', AssignmentSubmission.submission_date).label('month'),
        db.func.count(AssignmentSubmission.id).label('count')
    ).join(Assignment).filter(Assignment.classroom_id == classroom_id)\
     .group_by('month').order_by('month').all()

    # تحليلات الاختبارات
    quizzes = Quiz.query.filter_by(classroom_id=classroom_id).all()
    quiz_attempts_by_month = db.session.query(
        db.func.strftime('%Y-%m', QuizAttempt.start_time).label('month'),
        db.func.avg(QuizAttempt.score).label('average_score')
    ).join(Quiz).filter(Quiz.classroom_id == classroom_id)\
     .group_by('month').order_by('month').all()

    # تصنيف الطلاب حسب مستوى الأداء
    student_grades = []
    for enrollment in classroom.enrollments:
        avg_grade = db.session.query(db.func.avg(AssignmentSubmission.grade))\
            .join(Assignment).filter(
                AssignmentSubmission.enrollment_id == enrollment.id,
                Assignment.classroom_id == classroom_id
            ).scalar() or 0
        
        quiz_avg = db.session.query(db.func.avg(QuizAttempt.score))\
            .join(Quiz).filter(
                QuizAttempt.enrollment_id == enrollment.id,
                Quiz.classroom_id == classroom_id
            ).scalar() or 0
        
        final_grade = (avg_grade + quiz_avg) / 2
        student_grades.append(final_grade)

    # تصنيف الدرجات
    grade_distribution = {
        'ممتاز': len([g for g in student_grades if g >= 90]),
        'جيد جداً': len([g for g in student_grades if 80 <= g < 90]),
        'جيد': len([g for g in student_grades if 70 <= g < 80]),
        'مقبول': len([g for g in student_grades if g < 70])
    }

    # تحليلات تفاعل الطلاب
    interaction_data = []
    for month in range(6):
        date = datetime.now() - timedelta(days=30 * month)
        month_str = date.strftime('%Y-%m')
        
        total_activities = db.session.query(db.func.count(AssignmentSubmission.id))\
            .join(Assignment).filter(
                Assignment.classroom_id == classroom_id,
                db.func.strftime('%Y-%m', AssignmentSubmission.submission_date) == month_str
            ).scalar() or 0
            
        total_activities += db.session.query(db.func.count(QuizAttempt.id))\
            .join(Quiz).filter(
                Quiz.classroom_id == classroom_id,
                db.func.strftime('%Y-%m', QuizAttempt.start_time) == month_str
            ).scalar() or 0
        
        interaction_data.insert(0, {
            'month': date.strftime('%B'),  # اسم الشهر
            'activities': total_activities
        })

    return jsonify({
        'classroom': {
            'name': classroom.name,
            'total_students': len(classroom.enrollments),
            'interaction_rate': classroom.interaction_rate,
            'average_grade': classroom.average_grade,
            'assignments_completion_rate': classroom.assignments_completion_rate,
            'attendance_rate': classroom.attendance_rate
        },
        'grade_distribution': grade_distribution,
        'interaction_data': interaction_data,
        'submissions_by_month': [{
            'month': row.month,
            'count': row.count
        } for row in submissions_by_month],
        'quiz_performance': [{
            'month': row.month,
            'average_score': float(row.average_score)
        } for row in quiz_attempts_by_month]
    })


@teacher_bp.route('/classroom/<int:classroom_id>/quiz/<int:quiz_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_quiz(classroom_id, quiz_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    quiz = Quiz.query.get_or_404(quiz_id)

    # Ensure the teacher owns this classroom and quiz
    if classroom.teacher_id != current_user.id or quiz.classroom_id != classroom.id:
        flash('غير مصرح لك بحذف هذا الاختبار', 'danger')
        return redirect(url_for('teacher.dashboard'))
        
    # Delete quiz attempts and answers first (cascade will handle question options)
    QuizAttempt.query.filter_by(quiz_id=quiz.id).delete()
    
    # Delete the quiz (will cascade delete questions)
    db.session.delete(quiz)
    db.session.commit()
    
    flash('تم حذف الاختبار بنجاح', 'success')
    return redirect(url_for('teacher.quizzes', classroom_id=classroom.id))



@teacher_bp.route('/payment/<int:plan_id>', methods=['GET', 'POST'])
@login_required
@teacher_required 
def payment(plan_id):
    """
    عرض صفحة الدفع ومعالجة تأكيد الدفع لخطة اشتراك معينة
    """
    # Get the subscription plan
    plan = SubscriptionPlan.query.get_or_404(plan_id)
    
    # Get e-wallet number from system settings
    ewallet_number = SystemSettings.get_setting('ewallet_number', '01145425207 / 01033607749 او انستا باي zezohani777@instapay')

    if request.method == 'POST':
        # Handle file upload
        if 'screenshot' not in request.files:
            flash('يجب إرفاق صورة إثبات الدفع', 'danger')
            return redirect(url_for('teacher.payment', plan_id=plan.id))

        file = request.files['screenshot']
        if file.filename == '':
            flash('لم يتم اختيار ملف', 'danger')
            return redirect(url_for('teacher.payment', plan_id=plan.id))

        if not allowed_file(file.filename):
            flash('نوع الملف غير مسموح به. يجب أن يكون الملف صورة (PNG, JPG, JPEG)', 'danger')
            return redirect(url_for('teacher.payment', plan_id=plan.id))

        # Save screenshot
        filename = secure_filename(f"payment_{plan_id}_{current_user.id}_{int(datetime.utcnow().timestamp())}.{file.filename.rsplit('.', 1)[1].lower()}")
        screenshots_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'subscription_payments')
        os.makedirs(screenshots_dir, exist_ok=True)
        file_path = os.path.join(screenshots_dir, filename)
        file.save(file_path)

        
        
        # Create payment record using SubscriptionPayment
        payment = SubscriptionPayment(
            user_id=current_user.id,
            plan_id=plan.id,
            amount=plan.price,
            payment_method='ewallet',
            payment_proof=f'uploads/subscription_payments/{filename}',
            status='pending',
            notes=request.form.get('transfer_note')
        )

        db.session.add(payment)
        db.session.commit()

        flash('تم إرسال طلب الدفع بنجاح. سيتم تفعيل اشتراكك بعد مراجعة عملية الدفع', 'success')
        return redirect(url_for('teacher.subscriptions'))
    
    template = 'teacher/mobile-theme/payment.html' if is_mobile() else 'teacher/payment.html'

    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي



    return render_template(template, 
                         plan=plan,
                         ewallet_number=ewallet_number,
                         primary_color=primary_color,
                         secondary_color=secondary_color,)



@teacher_bp.route('/uploads/<path:filename>')
@login_required
@teacher_required
def serve_file(filename):
    """
    Serve files using X-Sendfile/X-Accel-Redirect with streaming support
    """
    if not filename:
        abort(404)

    # Determine appropriate folder based on file type
    folder = None
    for folder_type, path in current_app.config['UPLOAD_FOLDERS'].items():
        if folder_type in filename:
            folder = path
            break
    
    if not folder:
        folder = current_app.config['UPLOAD_FOLDER']
        
    file_path = os.path.join(folder, filename)
    
    if not os.path.exists(file_path):
        abort(404)
        
    # Security check
    if not check_file_access_permission(filename):
        abort(403)

    # Get file type and extension
    file_extension = os.path.splitext(filename)[1].lower()
    mime_type = None

    # Map file extensions to MIME types
    mime_types = {
        '.pdf': 'application/pdf',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.txt': 'text/plain',
        '.mp4': 'video/mp4',
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav'
    }

    mime_type = mime_types.get(file_extension, 'application/octet-stream')
    
    # الحصول على نوع الملف
    file_type = get_file_type(filename)
    
    # إعداد رأس الاستجابة
    headers = {
        'Accept-Ranges': 'bytes',
        'Cache-Control': 'public, max-age=43200'  # 12 ساعة
    }
    
    # استخدام X-Accel-Redirect مع Nginx
    if current_app.config.get('USE_X_ACCEL_REDIRECT', False):
        response = make_response('')
        internal_path = f'/protected/{filename}'  # يجب أن يتطابق مع إعدادات Nginx
        response.headers['X-Accel-Redirect'] = internal_path
        for key, value in headers.items():
            response.headers[key] = value
        return response
        
    # Fallback لخادم التطوير مع دعم التدفق
    file_size = os.path.getsize(file_path)
    
    # التعامل مع طلبات النطاق للتدفق
    range_header = request.headers.get('Range')
    
    if range_header:
        byte1, byte2 = 0, None
        match = re.search('bytes=(\d+)-(\d*)', range_header)
        groups = match.groups()

        if groups[0]:
            byte1 = int(groups[0])
        if groups[1]:
            byte2 = int(groups[1])

        if byte2 is None:
            byte2 = file_size - 1
            
        length = byte2 - byte1 + 1
        
        response = send_file(
            file_path,
            mimetype=file_type,
            as_attachment=False,
            download_name=filename
        )
        
        response.headers.add('Content-Range',
                           f'bytes {byte1}-{byte2}/{file_size}')
        response.headers.add('Accept-Ranges', 'bytes')
        response.headers.add('Content-Length', str(length))
        response.status_code = 206
        
        return response
    
    # إرسال الملف كاملاً
    return send_file(file_path,
                    mimetype=file_type,
                    as_attachment=False,
                    download_name=filename)

def get_file_type(filename):
    """تحديد نوع الملف"""
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or 'application/octet-stream'

def check_file_access_permission(filename):
    """التحقق من صلاحيات الوصول للملف"""
    # التحقق من أن المستخدم له صلاحية الوصول للملف
    if 'classroom_content' in filename:
        content_id = filename.split('/')[-1].split('.')[0]
        content = ClassroomContent.query.filter_by(content_url=filename).first()
        if content and content.classroom.teacher_id == current_user.id:
            return True
    return False



@teacher_bp.route('/classroom/<int:classroom_id>/chat')
@login_required
@teacher_required
def chat(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)

    # Ensure the teacher owns this classroom
    if classroom.teacher_id != current_user.id:
        flash('غير مصرح لك بالوصول إلى هذا الفصل', 'danger')
        return redirect(url_for('teacher.dashboard'))

    # Check if chat is enabled in settings
    settings = ChatSettings.query.filter_by(classroom_id=classroom.id).first()
    if not settings or not settings.is_enabled:
        flash('المحادثة غير مفعلة لهذا الفصل', 'warning')
        return redirect(url_for('teacher.classroom', classroom_id=classroom.id))

    # Get chat participants
    participants = ChatParticipant.query.filter_by(
        classroom_id=classroom.id,
        is_enabled=True
    ).all()

    # Get chat messages
    messages = ChatMessage.query.filter_by(
        classroom_id=classroom.id
    ).order_by(ChatMessage.created_at.desc()).limit(100).all()
    messages.reverse()  # Show oldest messages first

    template = 'teacher/mobile-theme/chat.html' if is_mobile() else 'teacher/chat.html'

    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي


    return render_template(template,
                         classroom=classroom,
                         settings=settings,
                         participants=participants,
                         messages=messages,
                         current_user=current_user,
                         primary_color=primary_color,
                         secondary_color=secondary_color,
                         user_type='teacher')

@teacher_bp.route('/classroom/<int:classroom_id>/participants')
@login_required
@teacher_required
def chat_participants(classroom_id):
    """جلب قائمة المشاركين في المحادثة"""
    try:
        classroom = Classroom.query.get_or_404(classroom_id)
        
        # التأكد من أن المعلم يملك هذا الفصل
        if classroom.teacher_id != current_user.id:
            return jsonify({'success': False, 'error': 'غير مصرح'}), 403
        
        # جلب جميع المشاركين في المحادثة
        participants = []
        
        # إضافة المعلم
        participants.append({
            'id': classroom.teacher.id,
            'name': classroom.teacher.name,
            'role': 'teacher',
            'status': 'online'
        })
        
        # إضافة المساعد إذا وجد
        if classroom.assistant_id:
            assistant = User.query.get(classroom.assistant_id)
            if assistant:
                participants.append({
                    'id': assistant.id,
                    'name': assistant.name,
                    'role': 'assistant',
                    'status': 'online'
                })
        
        # إضافة الطلاب المسموح لهم بالمحادثة
        chat_participants = ChatParticipant.query.filter_by(
            classroom_id=classroom.id,
            is_enabled=True
        ).all()
        
        for chat_participant in chat_participants:
            if chat_participant.enrollment:
                participants.append({
                    'id': chat_participant.enrollment.user.id,
                    'name': chat_participant.enrollment.user.name,
                    'role': 'student',
                    'status': 'online'
                })
        
        return jsonify({
            'success': True,
            'participants': participants
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@teacher_bp.route('/classroom/<int:classroom_id>/assistant/settings', methods=['GET', 'POST'])
@login_required
@teacher_required
def assistant_settings(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)

    # Ensure the teacher owns this classroom
    if classroom.teacher_id != current_user.id:
        flash('غير مصرح لك بالوصول إلى هذا الفصل', 'danger')
        return redirect(url_for('teacher.dashboard'))

    # Check if plan allows assistant
    plan = get_current_plan()
    if not plan or not plan.allow_assistant:
        flash('باقة اشتراكك الحالية لا تسمح بتعيين مساعد. الرجاء ترقية اشتراكك', 'warning')
        return redirect(url_for('teacher.classroom', classroom_id=classroom.id))

    if request.method == 'POST':
        assistant_phone = request.form.get('assistant_phone')
        if not assistant_phone:
            flash('رقم الهاتف مطلوب', 'danger')
            return redirect(url_for('teacher.assistant_settings', classroom_id=classroom.id))

        # Find assistant by phone
        assistant = User.query.filter_by(phone=assistant_phone, role=Role.ASSISTANT).first()
        if not assistant:
            flash('لم يتم العثور على مساعد بهذا الرقم. تأكد من أن المستخدم مسجل كمساعد', 'danger')
            return redirect(url_for('teacher.assistant_settings', classroom_id=classroom.id))

        # Update assistant
        classroom.assistant_id = assistant.id
        db.session.commit()

        flash(f'تم تعيين {assistant.name} كمساعد للفصل بنجاح', 'success')
        return redirect(url_for('teacher.classroom', classroom_id=classroom.id))

    template = 'teacher/mobile-theme/assistant_settings.html' if is_mobile() else 'teacher/assistant_settings.html'

    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي


    return render_template(template,
                         classroom=classroom,
                         current_assistant=User.query.get(classroom.assistant_id) if classroom.assistant_id else None,
                         primary_color=primary_color,
                         secondary_color=secondary_color,)


@teacher_bp.route('/classroom/<int:classroom_id>/start_live_stream', methods=['POST'])
@login_required
@teacher_required
def start_live_stream(classroom_id):
    """Start a new live stream for the classroom"""
    classroom = Classroom.query.get_or_404(classroom_id)

    # Ensure the teacher owns this classroom
    if classroom.teacher_id != current_user.id:
        flash('غير مصرح لك بالوصول إلى هذا الفصل', 'danger')
        return redirect(url_for('teacher.dashboard'))

    # Check if there's already an active stream
    existing_stream = LiveStream.query.filter_by(
        classroom_id=classroom_id,
        is_active=True
    ).first()
    
    if existing_stream and existing_stream.is_currently_active:
        message = 'يوجد بث مباشر نشط بالفعل'
        flash(message, 'warning')
        return redirect(url_for('teacher.live_classroom', classroom_id=classroom_id))

    # Get form data
    stream_url = request.form.get('stream_url', '').strip()
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()

    if not stream_url or not title:
        message = 'رابط البث والعنوان مطلوبان'
        flash(message, 'danger')
        return redirect(url_for('teacher.live_classroom', classroom_id=classroom_id))

    try:
        # Create new live stream
        auto_end_time = datetime.utcnow() + timedelta(hours=24)
        live_stream = LiveStream(
            classroom_id=classroom_id,
            teacher_id=current_user.id,
            stream_url=stream_url,
            title=title,
            description=description,
            started_at=datetime.utcnow(),
            auto_end_at=auto_end_time
        )
        
        db.session.add(live_stream)
        db.session.commit()

        # Send notifications to all students in the classroom
        enrollments = ClassroomEnrollment.query.filter_by(classroom_id=classroom_id).all()
        notifications_created = 0
        
        for enrollment in enrollments:
            if enrollment.user.role == Role.STUDENT:
                notification = Notification(
                    user_id=enrollment.user.id,
                    title=f'بث مباشر جديد في {classroom.name}',
                    message=f'بدأ الأستاذ {current_user.name} بثًا مباشرًا بعنوان: {title}'
                )
                db.session.add(notification)
                notifications_created += 1

        db.session.commit()
        
        success_message = f'تم بدء البث المباشر بنجاح وإرسال {notifications_created} إشعار للطلاب'
        flash(success_message, 'success')
        return redirect(url_for('teacher.live_classroom', classroom_id=classroom_id))

    except Exception as e:
        db.session.rollback()
        error_message = 'حدث خطأ أثناء بدء البث المباشر'
        flash(error_message, 'danger')
        return redirect(url_for('teacher.live_classroom', classroom_id=classroom_id))

@teacher_bp.route('/classroom/<int:classroom_id>/end_live_stream', methods=['POST'])
@login_required
@teacher_required
def end_live_stream(classroom_id):
    """End the current live stream for the classroom"""
    classroom = Classroom.query.get_or_404(classroom_id)

    # Ensure the teacher owns this classroom
    if classroom.teacher_id != current_user.id:
        flash('غير مصرح لك بالوصول إلى هذا الفصل', 'danger')
        return redirect(url_for('teacher.dashboard'))

    # Find the active stream
    current_stream = LiveStream.query.filter_by(
        classroom_id=classroom_id,
        is_active=True
    ).first()

    if not current_stream:
        message = 'لا يوجد بث مباشر نشط'
        flash(message, 'warning')
        return redirect(url_for('teacher.live_classroom', classroom_id=classroom_id))

    try:
        # End the stream
        current_stream.end_stream()
        
        # Send notifications to all students
        enrollments = ClassroomEnrollment.query.filter_by(classroom_id=classroom_id).all()
        notifications_created = 0
        
        for enrollment in enrollments:
            if enrollment.user.role == Role.STUDENT:
                notification = Notification(
                    user_id=enrollment.user.id,
                    title=f'انتهى البث المباشر في {classroom.name}',
                    message=f'انتهى البث المباشر "{current_stream.title}" من الأستاذ {current_user.name}'
                )
                db.session.add(notification)
                notifications_created += 1

        db.session.commit()
        
        success_message = f'تم إنهاء البث المباشر بنجاح وإرسال {notifications_created} إشعار للطلاب'
        flash(success_message, 'success')
        return redirect(url_for('teacher.live_classroom', classroom_id=classroom_id))

    except Exception as e:
        db.session.rollback()
        error_message = 'حدث خطأ أثناء إنهاء البث المباشر'
        flash(error_message, 'danger')
        return redirect(url_for('teacher.live_classroom', classroom_id=classroom_id))


@teacher_bp.route('/notifications')
@login_required
@teacher_required
def notifications():
    """صفحة الإشعارات للمعلم"""
    # جلب الإشعارات الخاصة بالمعلم الحالي مرتبة بالتاريخ
    notifications_query = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc())
    
    # تطبيق التصفية حسب حالة القراءة إذا تم تحديدها
    status_filter = request.args.get('status')
    if status_filter == 'unread':
        notifications_query = notifications_query.filter_by(is_read=False)
    elif status_filter == 'read':
        notifications_query = notifications_query.filter_by(is_read=True)
    
    # تطبيق البحث إذا تم تحديده
    search_query = request.args.get('search', '').strip()
    if search_query:
        notifications_query = notifications_query.filter(
            db.or_(
                Notification.title.ilike(f'%{search_query}%'),
                Notification.message.ilike(f'%{search_query}%')
            )
        )
    
    # التقسيم على صفحات (10 إشعارات لكل صفحة)
    page = request.args.get('page', 1, type=int)
    notifications_pagination = notifications_query.paginate(
        page=page, per_page=10, error_out=False
    )
    
    # إحصائيات الإشعارات
    total_notifications = Notification.query.filter_by(user_id=current_user.id).count()
    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    read_count = total_notifications - unread_count
    
    # تحديد القالب حسب نوع الجهاز
    if is_mobile():
        template = 'teacher/mobile-theme/notifications.html'
    else:
        template = 'teacher/notifications.html'
    
    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي
    
    return render_template(template,
                         notifications=notifications_pagination.items,
                         pagination=notifications_pagination,
                         total_notifications=total_notifications,
                         unread_count=unread_count,
                         read_count=read_count,
                         status_filter=status_filter,
                         search_query=search_query,
                         primary_color=primary_color,
                         secondary_color=secondary_color)


@teacher_bp.route('/notifications/mark_read/<int:notification_id>', methods=['POST'])
@login_required
@teacher_required
def mark_notification_read(notification_id):
    """تعيين إشعار كمقروء"""
    notification = Notification.query.filter_by(
        id=notification_id, 
        user_id=current_user.id
    ).first_or_404()
    
    notification.is_read = True
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'تم تعيين الإشعار كمقروء'})


@teacher_bp.route('/notifications/mark_all_read', methods=['POST'])
@login_required
@teacher_required
def mark_all_notifications_read():
    """تعيين جميع الإشعارات كمقروءة"""
    Notification.query.filter_by(
        user_id=current_user.id, 
        is_read=False
    ).update({'is_read': True})
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'تم تعيين جميع الإشعارات كمقروءة'})


@teacher_bp.route('/notifications/delete/<int:notification_id>', methods=['POST'])
@login_required
@teacher_required
def delete_notification(notification_id):
    """حذف إشعار"""
    notification = Notification.query.filter_by(
        id=notification_id, 
        user_id=current_user.id
    ).first_or_404()
    
    db.session.delete(notification)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'تم حذف الإشعار بنجاح'})


@teacher_bp.route('/notifications/delete_all_read', methods=['POST'])
@login_required
@teacher_required
def delete_all_read_notifications():
    """حذف جميع الإشعارات المقروءة"""
    read_notifications = Notification.query.filter_by(
        user_id=current_user.id, 
        is_read=True
    ).all()
    
    for notification in read_notifications:
        db.session.delete(notification)
    
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': f'تم حذف {len(read_notifications)} إشعار مقروء'
    })
