from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app, session
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename
from app import db
from models import Subscription, SubscriptionPlan, User, Role, Classroom, ClassroomEnrollment, ClassroomContent
from models import Assignment, AssignmentSubmission, Quiz, QuizQuestion, QuizAttempt, QuizAnswer, QuizQuestionOption
from models import Payment, ChatParticipant, SystemSettings

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
        if not current_user.is_authenticated or current_user.role != Role.STUDENT:
            flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
            return redirect(url_for('index'))
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

    return render_template(template,
        enrollments=enrollments,
        upcoming_assignments=upcoming_assignments,
        upcoming_quizzes=upcoming_quizzes,
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
    return render_template(template, enrollments=enrollments)

@student_bp.route('/join', methods=['GET', 'POST'])
@login_required
@student_required
def join_classroom():
    if request.method == 'POST':
        classroom_code = request.form.get('classroom_code')

        if not classroom_code:
            flash('الرجاء إدخال كود الفصل', 'danger')
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
    return render_template(template)

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

    # Get e-wallet number from system settings
    ewallet_number = SystemSettings.get_setting('ewallet_number', '01145425207')

    template = 'student/mobile-theme/payment.html' if is_mobile() else 'student/payment.html'
    return render_template(template,
                         classroom=classroom,
                         ewallet_number=ewallet_number)

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
    
    # Get e-wallet number from system settings
    ewallet_number = SystemSettings.get_setting('ewallet_number', '01145425207')

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
    return render_template(template,
                         classroom=classroom,
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

    return render_template(template,
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

    return render_template(template,
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
    return render_template(template,
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
    return render_template(template,
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
    return render_template(template,
                       classroom=classroom,
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

    template = 'student/mobile-theme/live_class.html' if is_mobile() else 'student/live_class.html'
    return render_template(template,
                         classroom=classroom,
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

    return render_template('classroom/chat.html',
                         classroom=classroom,
                         enrollment=enrollment,
                         is_chat_participant=chat_participant is not None and chat_participant.is_enabled)