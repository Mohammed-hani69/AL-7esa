from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app, session
from flask_login import login_required, current_user
from flask_wtf.csrf import validate_csrf, CSRFError
from functools import wraps
from datetime import datetime, timedelta
import os
import re
from werkzeug.utils import secure_filename
from models import LiveStream, Subscription, SubscriptionPlan, User, Role, Classroom, ClassroomEnrollment, ClassroomContent
from models import Assignment, AssignmentSubmission, Quiz, QuizQuestion, QuizAttempt, QuizAnswer, QuizQuestionOption
from models import Payment, ChatParticipant, SystemSettings, Notification, Banner

# استيراد db بطريقة آمنة
try:
    from app import db
except ImportError:
    from flask_sqlalchemy import SQLAlchemy
    db = SQLAlchemy()

student_bp = Blueprint('student', __name__)

# الملفات المسموح بها للمرفقات والتسليمات
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png'}

def allowed_file(filename):
    """التحقق من أن امتداد الملف مسموح به"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_mobile():
    """Check if current request is from a mobile device"""
    user_agent = request.headers.get('User-Agent', '').lower()
    return any(device in user_agent for device in ['android', 'iphone', 'ipad', 'mobile'])

# Student required decorator
def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'student':
            flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

# Chat access middleware
def check_chat_access(f):
    @wraps(f)
    def decorated_function(classroom_id, *args, **kwargs):
        # Check if student is enrolled and active
        enrollment = ClassroomEnrollment.query.filter_by(
            classroom_id=classroom_id,
            user_id=current_user.id,
            is_active=True
        ).first_or_404()

        # Check if student has chat access
        chat_participant = ChatParticipant.query.filter_by(
            classroom_id=classroom_id,
            enrollment_id=enrollment.id,
            is_enabled=True
        ).first()

        if not chat_participant:
            flash('غير مصرح لك بالوصول إلى المحادثة', 'danger')
            return redirect(url_for('student.classroom', classroom_id=classroom_id))

        return f(classroom_id, *args, **kwargs)
    return decorated_function

@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    # الحصول على تسجيلات الطالب في الفصول
    enrollments = ClassroomEnrollment.query.filter_by(user_id=current_user.id).all()
    
    # الحصول على الواجبات القادمة
    upcoming_assignments = []
    for enrollment in enrollments:
        assignments = Assignment.query.filter_by(
            classroom_id=enrollment.classroom_id
        ).filter(
            Assignment.due_date > datetime.utcnow()
        ).all()
        for assignment in assignments:
            # إضافة معلومات التسليم
            assignment.submission = AssignmentSubmission.query.filter_by(
                assignment_id=assignment.id,
                enrollment_id=enrollment.id
            ).first()
            upcoming_assignments.append(assignment)

    # الحصول على الاختبارات المتاحة
    upcoming_quizzes = []
    for enrollment in enrollments:
        quizzes = Quiz.query.filter_by(
            classroom_id=enrollment.classroom_id
        ).filter(
            Quiz.end_time > datetime.utcnow()
        ).all()
        for quiz in quizzes:
            # إضافة معلومات محاولة الاختبار
            quiz.attempt = QuizAttempt.query.filter_by(
                quiz_id=quiz.id,
                enrollment_id=enrollment.id
            ).first()
            upcoming_quizzes.append(quiz)

    # بيانات الرسم البياني للواجبات
    completed_assignments = []
    for enrollment in enrollments:
        submissions = AssignmentSubmission.query.join(Assignment).filter(
            AssignmentSubmission.enrollment_id == enrollment.id,
            Assignment.classroom_id == enrollment.classroom_id
        ).order_by(AssignmentSubmission.submission_date).all()
        completed_assignments.extend(submissions)
    
    assignment_dates = [sub.submission_date.strftime('%Y-%m-%d') for sub in completed_assignments]
    assignment_scores = [sub.grade if sub.grade is not None else 0 for sub in completed_assignments]

    # بيانات الرسم البياني للاختبارات
    completed_quizzes = []
    for enrollment in enrollments:
        attempts = QuizAttempt.query.filter_by(
            enrollment_id=enrollment.id,
            is_completed=True
        ).order_by(QuizAttempt.start_time).all()
        completed_quizzes.extend(attempts)
    
    quiz_titles = [attempt.quiz.title for attempt in completed_quizzes]
    quiz_scores = [attempt.score for attempt in completed_quizzes]

    # بيانات الرسم البياني للنقاط في كل فصل
    classroom_names = [enrollment.classroom.name for enrollment in enrollments]
    classroom_points = [enrollment.points for enrollment in enrollments]

    # تحديد القالب بناءً على نوع الجهاز
    template = 'dashboard/mobile-theme/student.html' if is_mobile() else 'dashboard/student.html'

    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي

    # جلب الإشعارات للطالب
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(5).all()
    unread_notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).all()

    # جلب البانرات النشطة للطلاب
    active_banners = Banner.query.filter(
        Banner.is_active == True,
        (Banner.start_date.is_(None)) | (Banner.start_date <= datetime.utcnow()),
        (Banner.end_date.is_(None)) | (Banner.end_date >= datetime.utcnow())
    ).filter(
        (Banner.target_roles == 'all') |
        (Banner.target_roles.like('%student%'))
    ).order_by(Banner.priority.desc()).all()
    
    # فلترة البانرات للطلاب
    student_banners = [banner for banner in active_banners if banner.is_valid_for_user('student')]

    return render_template(template,
        enrollments=enrollments,
        primary_color=primary_color,
        secondary_color=secondary_color,
        upcoming_assignments=upcoming_assignments,
        upcoming_quizzes=upcoming_quizzes,
        notifications=notifications,
        unread_notifications=unread_notifications,
        banners=student_banners,
        now=datetime.utcnow(),
        # بيانات الرسوم البيانية
        assignment_dates=assignment_dates,
        assignment_scores=assignment_scores,
        quiz_titles=quiz_titles,
        quiz_scores=quiz_scores,
        classroom_names=classroom_names,
        classroom_points=classroom_points
    )

@student_bp.route('/classrooms')
@login_required
@student_required
def classrooms():
    # Get student's enrolled classrooms
    enrollments = ClassroomEnrollment.query.filter_by(
        user_id=current_user.id, 
        is_active=True
    ).all()

    template = 'student/mobile-theme/classrooms.html' if is_mobile() else 'student/classrooms.html'

    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي

    # جلب الإشعارات للطالب
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(5).all()
    unread_notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).all()

    return render_template(template, enrollments=enrollments,
                           primary_color=primary_color,
                           secondary_color=secondary_color,
                           notifications=notifications,
                           unread_notifications=unread_notifications)

@student_bp.route('/join', methods=['GET', 'POST'])
@login_required
@student_required
def join_classroom():

    if request.method == 'POST':
        
        classroom_code = request.form.get('classroom_code')

        if not classroom_code:
            flash('الرجاء إدخال كود الفصل', 'danger')
            return redirect(url_for('student.join_classroom'))

        # التحقق من وجود رقم هاتف ولي الأمر
        if not current_user.parent_phone or current_user.parent_phone.strip() == '':
            flash('يجب إضافة رقم هاتف ولي الأمر أولاً قبل الانضمام للفصل. يرجى إضافة الرقم في النافذة المنبثقة التي ستظهر.', 'warning')
            return redirect(url_for('student.join_classroom'))

        code = classroom_code.strip().upper()

        # Check if classroom exists
        classroom = Classroom.query.filter_by(code=code).first()

        if not classroom:
            flash('كود الفصل غير صالح. الرجاء التحقق والمحاولة مرة أخرى', 'danger')
            return redirect(url_for('student.join_classroom'))

        # Check if already enrolled
        existing_enrollment = ClassroomEnrollment.query.filter_by(
            user_id=current_user.id,
            classroom_id=classroom.id
        ).first()

        if existing_enrollment:
            if existing_enrollment.is_active:
                flash('أنت مسجل بالفعل في هذا الفصل', 'info')
                return redirect(url_for('student.classroom', classroom_id=classroom.id))
            else:
                # Reactivate enrollment
                existing_enrollment.is_active = True
                db.session.commit()
                flash('تم إعادة تفعيل اشتراكك في الفصل بنجاح', 'success')
                return redirect(url_for('student.classroom', classroom_id=classroom.id))

        # Check if classroom is free or paid
        if classroom.is_free:
            # Free classroom, enroll directly
            enrollment = ClassroomEnrollment(
                user_id=current_user.id,
                classroom_id=classroom.id,
                payment_status='free'
            )
            db.session.add(enrollment)
            db.session.commit()

            flash('تم الانضمام إلى الفصل بنجاح', 'success')
            return redirect(url_for('student.classroom', classroom_id=classroom.id))
        else:
            # Paid classroom, redirect to payment
            return redirect(url_for('student.payment', classroom_id=classroom.id))

    template = 'student/mobile-theme/join.html' if is_mobile() else 'student/join.html'

    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي

    return render_template(template,
                           primary_color=primary_color,
                           secondary_color=secondary_color,
                           current_user=current_user)

@student_bp.route('/update_parent_phone', methods=['POST'])
@login_required
@student_required
def update_parent_phone():
    """تحديث رقم هاتف ولي الأمر"""
    try:
        # التحقق من CSRF token
        try:
            csrf_token = request.headers.get('X-CSRFToken') or request.form.get('csrf_token')
            if csrf_token:
                validate_csrf(csrf_token)
        except CSRFError:
            return jsonify({'success': False, 'message': 'انتهت صلاحية الجلسة، يرجى إعادة تحميل الصفحة'})
        
        parent_phone = request.form.get('parent_phone', '').strip()
        
        if not parent_phone:
            return jsonify({'success': False, 'message': 'يرجى إدخال رقم هاتف ولي الأمر'})
        
        # التحقق من صحة رقم الهاتف
        phone_pattern = r'^01[0-9]{9}$'
        if not re.match(phone_pattern, parent_phone):
            return jsonify({
                'success': False, 
                'message': 'رقم الهاتف غير صحيح. يجب أن يبدأ بـ 01 ويتكون من 11 رقم'
            })
        
        # تحديث رقم هاتف ولي الأمر في كلا الحقلين للتوافق
        current_user.parent_phone = parent_phone
        current_user.alt_phone = parent_phone  # للتوافق مع الحقول القديمة
        current_user.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'تم حفظ رقم هاتف ولي الأمر بنجاح'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating parent phone: {str(e)}")
        return jsonify({
            'success': False, 
            'message': 'حدث خطأ أثناء حفظ البيانات. يرجى المحاولة مرة أخرى.'
        })

@student_bp.route('/payment/<int:classroom_id>')
@login_required
@student_required
def payment(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)

    # Check if already enrolled
    existing_enrollment = ClassroomEnrollment.query.filter_by(
        user_id=current_user.id,
        classroom_id=classroom.id,
        is_active=True
    ).first()

    if existing_enrollment:
        flash('أنت مسجل بالفعل في هذا الفصل', 'info')
        return redirect(url_for('student.classroom', classroom_id=classroom.id))

    # الحصول على رقم المحفظة الإلكترونية من ملف المعلم الشخصي
    teacher = classroom.teacher
    if not teacher.has_ewallet_numbers():
        flash('عذراً، لا يمكن إجراء عملية الدفع حالياً. المعلم لم يقم بإضافة أرقام المحافظ الإلكترونية.', 'warning')
        return redirect(url_for('student.classroom', classroom_id=classroom.id))
    
    # استخدام رقم المحفظة الأول للمعلم
    ewallet_number = teacher.ewallet_number_1

    template = 'student/mobile-theme/payment.html' if is_mobile() else 'student/payment.html'

    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي

    return render_template(template,
                         classroom=classroom,
                         ewallet_number=ewallet_number,
                         primary_color=primary_color,
                         secondary_color=secondary_color,)

@student_bp.route('/process_payment/<int:classroom_id>', methods=['POST'])
@login_required
@student_required
def process_payment(classroom_id):

    
    classroom = Classroom.query.get_or_404(classroom_id)

    # Verify file was uploaded
    if 'screenshot' not in request.files:
        flash('يجب إرفاق لقطة شاشة التحويل', 'danger')
        return redirect(url_for('student.payment', classroom_id=classroom.id))
    
    file = request.files['screenshot']
    if file.filename == '':
        flash('لم يتم اختيار ملف', 'danger')
        return redirect(url_for('student.payment', classroom_id=classroom.id))

    if not allowed_file(file.filename):
        flash('نوع الملف غير مسموح به. يجب أن يكون الملف صورة (PNG, JPG, JPEG)', 'danger')
        return redirect(url_for('student.payment', classroom_id=classroom.id))

    # Save screenshot
    filename = secure_filename(f"payment_{classroom_id}_{current_user.id}_{int(datetime.utcnow().timestamp())}.{file.filename.rsplit('.', 1)[1].lower()}")
    screenshots_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'payments')
    os.makedirs(screenshots_dir, exist_ok=True)
    file_path = os.path.join(screenshots_dir, filename)
    file.save(file_path)
    
    # الحصول على رقم المحفظة الإلكترونية من ملف المعلم الشخصي
    teacher = classroom.teacher
    ewallet_number = teacher.ewallet_number_1 if teacher.ewallet_number_1 else teacher.ewallet_number_2

    # Create payment record
    payment = Payment(
        user_id=current_user.id,
        classroom_id=classroom.id,
        amount=classroom.price,
        status='pending',
        payment_method='ewallet',
        screenshot_path=f'uploads/payments/{filename}',
        transfer_note=request.form.get('transfer_note'),
        ewallet_number=ewallet_number
    )

    # Create enrollment with pending status
    enrollment = ClassroomEnrollment(
        user_id=current_user.id,
        classroom_id=classroom.id,
        payment_status='pending',
        payment_date=datetime.utcnow()
    )

    db.session.add(payment)
    db.session.add(enrollment)
    db.session.commit()

    flash('تم إرسال طلب الدفع بنجاح. سيتم تفعيل اشتراكك في الفصل بعد مراجعة عملية الدفع', 'success')
    return redirect(url_for('student.classroom', classroom_id=classroom.id))

@student_bp.route('/classroom/<int:classroom_id>')
@login_required
@student_required
def classroom(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)

    # Check if student is enrolled
    enrollment = ClassroomEnrollment.query.filter_by(
        user_id=current_user.id,
        classroom_id=classroom.id,
        is_active=True
    ).filter(
        ClassroomEnrollment.payment_status.in_(['paid', 'free'])
    ).first()

    if not enrollment:
        flash('يجب أن تكون مسجلاً في الفصل للوصول إليه', 'danger')
        return redirect(url_for('student.dashboard'))

    # Check if this is a paid classroom and verify enrollment status
    if not classroom.is_free:
        if not enrollment.is_active:
            # Check if there's a pending payment
            payment = Payment.query.filter_by(
                enrollment_id=enrollment.id,
                status='pending'
            ).first()
            
            if payment:
                flash('في انتظار تأكيد عملية الدفع. سيتم إخطارك عند اكتمال المراجعة', 'warning')
                return redirect(url_for('student.dashboard'))
            elif payment and payment.status == 'failed':
                flash('فشلت عملية الدفع. يرجى المحاولة مرة أخرى', 'danger')
                return redirect(url_for('student.payment', classroom_id=classroom.id))

    # Get classroom content
    contents = ClassroomContent.query.filter_by(classroom_id=classroom.id).order_by(ClassroomContent.created_at.desc()).all()

    # Get assignments
    assignments = Assignment.query.filter_by(classroom_id=classroom.id).all()

    # Get quizzes
    quizzes = Quiz.query.filter_by(classroom_id=classroom.id).all()

    # Get chat participants info
    chat_participants = ChatParticipant.query.filter_by(classroom_id=classroom.id).all()

    # التحقق مما إذا كانت المحادثة مفعلة لهذا الفصل
    has_chat = False
    if classroom.teacher:
        active_subscription = Subscription.query.filter_by(
            user_id=classroom.teacher.id,
            is_active=True
        ).join(SubscriptionPlan).filter(
            Subscription.end_date > datetime.utcnow(),
            SubscriptionPlan.has_chat == True
        ).first()
        
        if active_subscription:
            # التأكد من أن المحادثة مفعلة في إعدادات الفصل
            chat_settings = classroom.chat_settings
            has_chat = chat_settings and chat_settings.is_enabled

    template = 'classroom/mobile-theme/student_view.html' if is_mobile() else 'classroom/student_view.html'

    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي

    return render_template(template,
                         classroom=classroom,
                         primary_color=primary_color,
                         secondary_color=secondary_color,
                         enrollment=enrollment,
                         has_chat=has_chat,
                         chat_participants=chat_participants,
                         teacher=classroom.teacher,
                         contents=contents,
                         assignments=assignments,
                         quizzes=quizzes)

@student_bp.route('/classroom/<int:classroom_id>/assignments')
@login_required
@student_required
def assignments(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)

    # Check if student is enrolled
    enrollment = ClassroomEnrollment.query.filter_by(
        user_id=current_user.id,
        classroom_id=classroom.id,
        is_active=True
    ).first()

    if not enrollment:
        flash('يجب أن تكون مسجلاً في الفصل للوصول إليه', 'danger')
        return redirect(url_for('student.dashboard'))

    # Get assignments
    assignments = Assignment.query.filter_by(classroom_id=classroom.id).order_by(Assignment.due_date.desc()).all()

    # Get student's submissions
    submissions = AssignmentSubmission.query.filter_by(enrollment_id=enrollment.id).all()

    # Create a map of assignment ID to submission for easy lookup
    submission_map = {sub.assignment_id: sub for sub in submissions}

    template = 'student/mobile-theme/student_assignments.html' if is_mobile() else 'student/student_assignments.html'

    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي


    return render_template(template,
                           primary_color=primary_color,
                           secondary_color=secondary_color,
                           classroom=classroom,
                           enrollment=enrollment,
                           assignments=assignments,
                           submission_map=submission_map,
                           now=datetime.utcnow())

@student_bp.route('/classroom/<int:classroom_id>/assignment/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
@student_required
def view_assignment(classroom_id, assignment_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    assignment = Assignment.query.get_or_404(assignment_id)

    # Check if student is enrolled and active
    enrollment = ClassroomEnrollment.query.filter_by(
        user_id=current_user.id,
        classroom_id=classroom.id,
        is_active=True
    ).first()

    if not enrollment:
        flash('غير مصرح لك بالوصول إلى هذا الفصل', 'danger')
        return redirect(url_for('student.dashboard'))

    # For paid classrooms, verify enrollment is active
    if not classroom.is_free and not enrollment.is_active:
        flash('يجب تفعيل اشتراكك في الفصل للوصول إلى المحتوى', 'warning')
        return redirect(url_for('student.dashboard'))

    if assignment.classroom_id != classroom.id:
        flash('غير مصرح لك بالوصول إلى هذا الواجب', 'danger')
        return redirect(url_for('student.dashboard'))

    # Check if student has already submitted
    submission = AssignmentSubmission.query.filter_by(
        enrollment_id=enrollment.id,
        assignment_id=assignment.id
    ).first()

    if request.method == 'POST':

     
        # Check if past due date
        if assignment.due_date and assignment.due_date < datetime.utcnow():
            flash('انتهت مهلة تسليم الواجب', 'danger')
            return redirect(url_for('student.view_assignment', classroom_id=classroom.id, assignment_id=assignment.id))

        submission_type = request.form.get('submission_type', 'text')
        content = None
        file_path = None
        file_name = None
        file_type = None

        if submission_type == 'text':
            content = request.form.get('content')
            if not content or content.strip() == '':
                flash('يرجى كتابة الحل قبل التسليم', 'danger')
                return redirect(url_for('student.view_assignment', classroom_id=classroom.id, assignment_id=assignment.id))

        else:  # submission_type == 'file'
            submitted_file = request.files.get('submission_file')
            if not submitted_file or not submitted_file.filename:
                flash('يرجى اختيار ملف للتسليم', 'danger')
                return redirect(url_for('student.view_assignment', classroom_id=classroom.id, assignment_id=assignment.id))

            # التحقق من امتداد الملف
            if not allowed_file(submitted_file.filename):
                flash('نوع الملف غير مسموح به. يجب أن يكون الملف PDF, Word, Excel أو صورة', 'danger')
                return redirect(url_for('student.view_assignment', classroom_id=classroom.id, assignment_id=assignment.id))
            
            # التحقق من نوع الملف باستخدام الامتداد
            file_type = submitted_file.filename.rsplit('.', 1)[1].lower()
            
            allowed_types = {
                'pdf',
                'doc', 'docx',
                'xls', 'xlsx',
                'jpg', 'jpeg', 'png'
            }
            
            if file_type not in allowed_types:
                flash('نوع الملف غير مسموح به. يجب أن يكون الملف PDF, Word, Excel أو صورة', 'danger')
                return redirect(url_for('student.view_assignment', classroom_id=classroom.id, assignment_id=assignment.id))

            # حفظ الملف
            original_filename = submitted_file.filename
            file_type = original_filename.rsplit('.', 1)[1].lower()
            filename = secure_filename(f"submission_{assignment_id}_{enrollment.id}_{int(datetime.utcnow().timestamp())}.{file_type}")
            
            submissions_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'submissions')
            os.makedirs(submissions_dir, exist_ok=True)
            # تحويل مسار الملف إلى تنسيق Unix-style
            file_path = 'uploads/submissions/' + filename
            # استخدام os.path.join لإنشاء المسار الكامل للحفظ
            full_path = os.path.join(current_app.root_path, 'static', file_path.replace('/', os.sep))
            submitted_file.save(full_path)
            file_name = original_filename

        if submission:
            # تحديث التسليم الحالي
            if submission_type != submission.submission_type:
                # إذا تغير نوع التسليم، نحذف البيانات القديمة
                if submission.file_path:
                    old_file = os.path.join(current_app.root_path, 'static', submission.file_path)
                    if os.path.exists(old_file):
                        os.remove(old_file)
                submission.content = None
                submission.file_path = None
                submission.file_name = None
                submission.file_type = None

            submission.submission_type = submission_type
            if submission_type == 'text':
                submission.content = content
            else:
                submission.file_path = file_path
                submission.file_name = file_name
                submission.file_type = file_type

            submission.submission_date = datetime.utcnow()
            db.session.commit()
            flash('تم تحديث الحل بنجاح', 'success')
        else:
            # إنشاء تسليم جديد
            new_submission = AssignmentSubmission(
                enrollment_id=enrollment.id,
                assignment_id=assignment.id,
                submission_type=submission_type,
                content=content,
                file_path=file_path,
                file_name=file_name,
                file_type=file_type
            )
            db.session.add(new_submission)
            db.session.commit()
            flash('تم تسليم الحل بنجاح', 'success')

        return redirect(url_for('student.assignments', classroom_id=classroom.id))
    
    template = 'student/mobile-theme/view_assignment.html' if is_mobile() else 'student/view_assignment.html'

    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي


    return render_template(template,
                           primary_color=primary_color,
                           secondary_color=secondary_color,
                           classroom=classroom,
                           assignment=assignment,
                           submission=submission,
                           now=datetime.utcnow())

@student_bp.route('/classroom/<int:classroom_id>/quizzes')
@login_required
@student_required
def quizzes(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)

    # Check if student is enrolled
    enrollment = ClassroomEnrollment.query.filter_by(
        user_id=current_user.id,
        classroom_id=classroom.id,
        is_active=True
    ).first()

    if not enrollment:
        flash('يجب أن تكون مسجلاً في الفصل للوصول إليه', 'danger')
        return redirect(url_for('student.dashboard'))

    # Get quizzes
    quizzes = Quiz.query.filter_by(classroom_id=classroom.id).all()

    # Get student's attempts
    attempts = QuizAttempt.query.filter_by(enrollment_id=enrollment.id).all()

    # Create a map of quiz ID to attempt for easy lookup
    attempt_map = {att.quiz_id: att for att in attempts}

    # Current time for quiz availability check
    now = datetime.utcnow()

    template = 'student/mobile-theme/student_quizzes.html' if is_mobile() else 'student/student_quizzes.html'

    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي

    return render_template(template,
                           primary_color=primary_color,
                           secondary_color=secondary_color,
                           classroom=classroom,
                           enrollment=enrollment,
                           quizzes=quizzes,
                           attempt_map=attempt_map,
                           now=now)

@student_bp.route('/classroom/<int:classroom_id>/quiz/<int:quiz_id>/start', methods=['GET', 'POST'])
@login_required
@student_required
def start_quiz(classroom_id, quiz_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # التحقق من تسجيل الطالب
    enrollment = ClassroomEnrollment.query.filter_by(
        user_id=current_user.id,
        classroom_id=classroom.id,
        is_active=True
    ).first()

    if not enrollment:
        flash('يجب أن تكون مسجلاً في الفصل للوصول إليه', 'danger')
        return redirect(url_for('student.dashboard'))

    # للفصول المدفوعة، تحقق من حالة الدفع
    if not classroom.is_free:
        payment = Payment.query.filter_by(
            user_id=current_user.id,
            classroom_id=classroom.id,
            status='success'
        ).order_by(Payment.created_at.desc()).first()
        
        if not payment:
            flash('يجب دفع رسوم الفصل للوصول إلى المحتوى', 'warning')
            return redirect(url_for('student.payment', classroom_id=classroom.id))
    
    # التحقق من وجود محاولة حالية
    attempt = QuizAttempt.query.filter_by(
        enrollment_id=enrollment.id,
        quiz_id=quiz.id
    ).first()

    # إنشاء محاولة جديدة إذا لم تكن موجودة
    if not attempt:
        attempt = QuizAttempt(
            enrollment_id=enrollment.id,
            quiz_id=quiz.id,
            start_time=datetime.utcnow()
        )
        db.session.add(attempt)
        db.session.commit()
    
    # التحقق من انتهاء المحاولة
    if attempt.is_completed:
        flash('تم تسليم هذا الاختبار مسبقاً', 'warning')
        return redirect(url_for('student.view_quiz_result', classroom_id=classroom.id, quiz_id=quiz.id))
    
    # التحقق من وقت الاختبار
    now = datetime.utcnow()
    if quiz.start_time and now < quiz.start_time:
        flash('لم يبدأ وقت الاختبار بعد', 'warning')
        return redirect(url_for('student.quizzes', classroom_id=classroom.id))
    
    if quiz.end_time and now > quiz.end_time:
        flash('انتهى وقت الاختبار', 'warning')
        return redirect(url_for('student.quizzes', classroom_id=classroom.id))
    
    if request.method == 'POST':
        if attempt.is_completed:
            flash('تم تسليم هذا الاختبار مسبقاً', 'warning')
            return redirect(url_for('student.view_quiz_result', classroom_id=classroom.id, quiz_id=quiz.id))

        total_points_possible = 0  # مجموع الدرجات الكلي للاختبار
        total_points_earned = 0    # مجموع الدرجات المكتسبة
        answered_questions = 0      # عدد الأسئلة المجاب عنها
        
        try:
            # معالجة كل سؤال في الاختبار
            for question in quiz.questions:
                answer_value = request.form.get(f'question_{question.id}')
                
                # تخطي الأسئلة الفارغة للأسئلة متعددة الخيارات
                if not answer_value and question.question_type in ['multiple_choice', 'true_false']:
                    continue
                    
                answered_questions += 1
                total_points_possible += question.points
                
                # العثور على أو إنشاء إجابة جديدة
                answer = QuizAnswer.query.filter_by(
                    attempt_id=attempt.id,
                    question_id=question.id
                ).first()
                
                if not answer:
                    answer = QuizAnswer(
                        attempt_id=attempt.id,
                        question_id=question.id
                    )
                    db.session.add(answer)
                
                if question.question_type in ['multiple_choice', 'true_false']:
                    # معالجة الأسئلة متعددة الخيارات
                    try:
                        selected_option_id = int(answer_value)
                        selected_option = QuizQuestionOption.query.get(selected_option_id)
                        
                        if selected_option and selected_option.question_id == question.id:
                            answer.selected_option_id = selected_option_id
                            answer.is_correct = selected_option.is_correct
                            if selected_option.is_correct:
                                answer.points_earned = question.points
                                total_points_earned += question.points
                            else:
                                answer.points_earned = 0
                        else:
                            answer.selected_option_id = None
                            answer.is_correct = False
                            answer.points_earned = 0
                            
                    except (ValueError, TypeError):
                        answer.selected_option_id = None
                        answer.is_correct = False
                        answer.points_earned = 0
                        
                else:
                    # معالجة الأسئلة المقالية
                    answer.text_answer = answer_value
                    answer.is_correct = None
                    answer.points_earned = None

            if answered_questions == 0:
                flash('يجب الإجابة على سؤال واحد على الأقل', 'danger')
                return redirect(url_for('student.start_quiz', classroom_id=classroom.id, quiz_id=quiz.id))
            
            # تحديث المحاولة
            attempt.end_time = datetime.utcnow()
            attempt.is_completed = True
            
            # حساب النتيجة النهائية بالنقاط الفعلية وليس كنسبة مئوية
            attempt.score = total_points_earned  # حفظ النقاط المكتسبة مباشرة
            attempt.total_possible = total_points_possible  # حفظ إجمالي النقاط الممكنة
                
            # تحديث نقاط الطالب
            enrollment.points += total_points_earned  # إضافة النقاط الفعلية وليس النسبة المئوية
            
            # حفظ التغييرات
            db.session.commit()
            flash(f'تم تسليم الاختبار بنجاح. النتيجة: {total_points_earned}/{total_points_possible}', 'success')
            return redirect(url_for('student.view_quiz_result', classroom_id=classroom.id, quiz_id=quiz.id))
            
        except Exception as e:
            db.session.rollback()
            flash('حدث خطأ أثناء حفظ إجاباتك. يرجى المحاولة مرة أخرى.', 'danger')
            print(f"Error saving quiz answers: {str(e)}")
            return redirect(url_for('student.start_quiz', classroom_id=classroom.id, quiz_id=quiz.id))
    
    # استرجاع الإجابات السابقة إن وجدت
    existing_answers = QuizAnswer.query.filter_by(attempt_id=attempt.id).all()
    answered_texts = {ans.question_id: ans.text_answer for ans in existing_answers}
    answered_options = {ans.question_id: ans.selected_option_id for ans in existing_answers}
    
    template = 'student/mobile-theme/take_quiz.html' if is_mobile() else 'student/take_quiz.html'

    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي

    return render_template(template,
                       primary_color=primary_color,
                       secondary_color=secondary_color,
                       classroom=classroom,
                       quiz=quiz,
                       attempt=attempt,
                       questions=quiz.questions,
                       answered_texts=answered_texts,
                       answered_options=answered_options,
                       now=datetime.utcnow())

@student_bp.route('/classroom/<int:classroom_id>/quiz/<int:quiz_id>/result')
@login_required
@student_required
def view_quiz_result(classroom_id, quiz_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    quiz = Quiz.query.get_or_404(quiz_id)

    # Check if student is enrolled
    enrollment = ClassroomEnrollment.query.filter_by(
        user_id=current_user.id,
        classroom_id=classroom.id,
        is_active=True
    ).first()

    if not enrollment or quiz.classroom_id != classroom.id:
        flash('غير مصرح لك بالوصول إلى هذا الاختبار', 'danger')
        return redirect(url_for('student.dashboard'))

    # Get completed attempt
    attempt = QuizAttempt.query.filter_by(
        enrollment_id=enrollment.id,
        quiz_id=quiz.id,
        is_completed=True
    ).first()

    if not attempt:
        flash('لم تكمل هذا الاختبار بعد', 'warning')
        return redirect(url_for('student.quizzes', classroom_id=classroom.id))

    # Get questions and answers
    questions = QuizQuestion.query.filter_by(quiz_id=quiz.id).order_by(QuizQuestion.position).all()

    # Create a map of question ID to answer for easy lookup
    answers = QuizAnswer.query.filter_by(attempt_id=attempt.id).all()
    answer_map = {ans.question_id: ans for ans in answers}

    template = 'student/mobile-theme/quiz_result.html' if is_mobile() else 'student/quiz_result.html'

    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي

    return render_template(template,
                       classroom=classroom,
                       primary_color=primary_color,
                       secondary_color=secondary_color,
                       quiz=quiz,
                       attempt=attempt,
                       questions=questions,
                       answer_map=answer_map)

@student_bp.route('/classroom/<int:classroom_id>/live')
@login_required
@student_required
def live_classroom(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)

    # Check if student is enrolled
    enrollment = ClassroomEnrollment.query.filter_by(
        user_id=current_user.id,
        classroom_id=classroom.id,
        is_active=True
    ).first()

    if not enrollment:
        flash('يجب أن تكون مسجلاً في الفصل للوصول إليه', 'danger')
        return redirect(url_for('student.dashboard'))

    # Get current active live stream for this classroom
    active_stream = LiveStream.query.filter_by(
        classroom_id=classroom_id,
        is_active=True
    ).first()
    
    # Check if the stream has expired and auto-end it
    if active_stream and active_stream.is_expired:
        active_stream.end_stream()
        active_stream = None
    
    # Get recent streams for this classroom (last 5 for students)
    recent_streams = LiveStream.query.filter_by(
        classroom_id=classroom_id
    ).filter(LiveStream.ended_at.isnot(None))\
     .order_by(LiveStream.created_at.desc()).limit(5).all()

    template = 'student/mobile-theme/live_class.html' if is_mobile() else 'student/live_class.html'

    # Get system colors
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي

    return render_template(template,
                         classroom=classroom,
                         active_stream=active_stream,
                         recent_streams=recent_streams,
                         current_time=datetime.utcnow(),
                         primary_color=primary_color,
                         secondary_color=secondary_color,
                         enrollment=enrollment,
                         user_type='student')

@student_bp.route('/classroom/<int:classroom_id>/chat')
@login_required
@student_required
@check_chat_access
def chat(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    enrollment = ClassroomEnrollment.query.filter_by(
        classroom_id=classroom.id,
        user_id=current_user.id,
        is_active=True
    ).first_or_404()

    chat_participant = ChatParticipant.query.filter_by(
        classroom_id=classroom.id,
        enrollment_id=enrollment.id
    ).first()

    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي


    return render_template('student/chat.html',
                         classroom=classroom,
                         primary_color=primary_color,
                         secondary_color=secondary_color,
                         enrollment=enrollment,
                         is_chat_participant=chat_participant is not None and chat_participant.is_enabled)

@student_bp.route('/classroom/<int:classroom_id>/participants')
@login_required
@student_required
@check_chat_access
def chat_participants(classroom_id):
    """جلب قائمة المشاركين في المحادثة"""
    try:
        classroom = Classroom.query.get_or_404(classroom_id)
        
        # جلب جميع المشاركين في المحادثة
        participants = []
        
        # إضافة المعلم
        if classroom.teacher:
            participants.append({
                'id': classroom.teacher.id,
                'name': classroom.teacher.name,
                'role': 'teacher',
                'status': 'online'  # يمكن تحديث هذا لاحقاً
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
        
        # إضافة الطلاب المسجلين
        enrollments = ClassroomEnrollment.query.filter_by(
            classroom_id=classroom.id,
            is_active=True
        ).all()
        
        for enrollment in enrollments:
            # التحقق من أن الطالب مسموح له بالمحادثة
            chat_participant = ChatParticipant.query.filter_by(
                classroom_id=classroom.id,
                enrollment_id=enrollment.id,
                is_enabled=True
            ).first()
            
            if chat_participant:
                participants.append({
                    'id': enrollment.user.id,
                    'name': enrollment.user.name,
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

# Student notifications routes
@student_bp.route('/notifications')
@login_required
@student_required
def notifications():
    """صفحة الإشعارات للطالب"""
    # جلب الإشعارات الخاصة بالطالب الحالي مرتبة بالتاريخ
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
        template = 'student/mobile-theme/notifications.html'
    else:
        template = 'student/notifications.html'
    
    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')
    
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

@student_bp.route('/notifications/mark_read/<int:notification_id>', methods=['POST'])
@login_required
@student_required
def mark_notification_read(notification_id):
    """تعيين إشعار كمقروء"""
    notification = Notification.query.filter_by(
        id=notification_id, 
        user_id=current_user.id
    ).first_or_404()
    
    notification.is_read = True
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'تم تعيين الإشعار كمقروء'})

@student_bp.route('/notifications/mark_all_read', methods=['POST'])
@login_required
@student_required
def mark_all_notifications_read():
    """تعيين جميع الإشعارات كمقروءة"""
    Notification.query.filter_by(
        user_id=current_user.id, 
        is_read=False
    ).update({'is_read': True})
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'تم تعيين جميع الإشعارات كمقروءة'})

@student_bp.route('/notifications/delete/<int:notification_id>', methods=['POST'])
@login_required
@student_required
def delete_notification(notification_id):
    """حذف إشعار"""
    notification = Notification.query.filter_by(
        id=notification_id, 
        user_id=current_user.id
    ).first_or_404()
    
    db.session.delete(notification)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'تم حذف الإشعار بنجاح'})

@student_bp.route('/notifications/delete_all_read', methods=['POST'])
@login_required
@student_required
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
