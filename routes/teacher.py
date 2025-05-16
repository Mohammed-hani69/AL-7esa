"""
مسارات المعلم (Teacher Routes)
التحكم في إدارة الفصول الدراسية والمحتوى التعليمي
"""

import random
import string
import os
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, timedelta
from app import db
from models import QuizAnswer, QuizAttempt, User, Role, Classroom, ClassroomEnrollment, ClassroomContent, ContentType
from models import Assignment, AssignmentSubmission, Quiz, QuizQuestion, QuizQuestionOption
from models import Subscription, SubscriptionPlan, ChatSettings, ChatParticipant, Payment

teacher_bp = Blueprint('teacher', __name__)

# Allowed file extensions for uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'mp4', 'mp3', 'wav'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    # Get teacher's classrooms
    classrooms = Classroom.query.filter_by(teacher_id=current_user.id).all()

    # Get total number of students across all classrooms
    total_students = db.session.query(db.func.count(ClassroomEnrollment.id))\
        .join(Classroom)\
        .filter(Classroom.teacher_id == current_user.id)\
        .scalar()

    # Get current subscription
    active_sub = Subscription.query.filter(
        Subscription.user_id == current_user.id,
        Subscription.end_date > datetime.utcnow(),
        Subscription.is_active == True
    ).first()

    # Get all subscription plans
    plans = SubscriptionPlan.query.all()

    # تحديد عدد الأيام المتبقية في الاشتراك
    subscription_days_left = 0
    has_active_sub = False
    
    active_subscription = next((sub for sub in current_user.subscriptions if sub.is_active), None)
    if active_subscription and active_subscription.end_date:
        subscription_days_left = (active_subscription.end_date - datetime.utcnow()).days
        has_active_sub = subscription_days_left > 0
    
    return render_template('dashboard/teacher.html', 
                           classrooms=classrooms, 
                           subscription=active_sub,
                           plans=plans,
                           can_create_classroom=can_create_classroom(),
                           subscription_days_left=subscription_days_left,
                           has_active_subscription=has_active_sub,
                           total_students=total_students,
                           now=datetime.utcnow())

@teacher_bp.route('/subscribe/<int:plan_id>', methods=['POST'])
@login_required
@teacher_required
def subscribe_to_plan(plan_id):
    """
    مسار لاشتراك المعلم في باقة محددة
    """
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

    return render_template('teacher/teacher_plans.html',
                         plans=plans,
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

    return render_template('classroom/create.html')

@teacher_bp.route('/classroom/<int:classroom_id>')
@login_required
@teacher_required
def classroom(classroom_id):
    # التحقق من وجود اشتراك نشط للمعلم
    has_subscription = has_active_subscription()
    if not has_subscription:
        flash('يجب أن يكون لديك اشتراك نشط للوصول إلى هذه الميزة', 'warning')
        return redirect(url_for('teacher.subscriptions'))
        
    # Get current subscription plan
    plan = get_current_plan()
    if not plan:
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
    if plan and plan.has_chat:
        can_use_chat = True

    return render_template('teacher/classroom.html',
                       classroom=classroom,
                       contents=contents,
                       enrollments=enrollments,
                       assignments=assignments,
                       quizzes=quizzes,
                       assistant=assistant,
                       can_use_chat=can_use_chat,
                       plan=plan)

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

    return render_template('teacher/classrooms.html',
                         classrooms=classrooms,
                         classroom_stats=classroom_stats,
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

    return render_template('classroom/live_class.html', 
                         classroom=classroom,
                         user_type='teacher')

@teacher_bp.route('/classroom/<int:classroom_id>/add_content', methods=['POST'])
@login_required
@teacher_required
def add_content(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)

    # Ensure the teacher owns this classroom
    if classroom.teacher_id != current_user.id:
        flash('غير مصرح لك بالوصول إلى هذا الفصل', 'danger')
        return redirect(url_for('teacher.classroom', classroom_id=classroom.id))

    title = request.form.get('title')
    description = request.form.get('description', '')
    content_type = request.form.get('content_type')

    if not title:
        flash('يجب إدخال عنوان المحتوى', 'danger')
        return redirect(url_for('teacher.classroom', classroom_id=classroom.id))

    if content_type not in [ContentType.FILE, ContentType.IMAGE, ContentType.AUDIO, ContentType.VIDEO, ContentType.TEXT]:
        flash('نوع المحتوى غير صالح', 'danger')
        return redirect(url_for('teacher.classroom', classroom_id=classroom.id))

    # Handle different content types
    content_url = None
    content_text = None

    if content_type == ContentType.TEXT:
        content_text = request.form.get('content_text', '')
        if not content_text.strip():
            flash('يجب إدخال محتوى نصي', 'danger')
            return redirect(url_for('teacher.classroom', classroom_id=classroom.id))
    else:
        # Handle file upload
        if content_type != ContentType.TEXT:
            if 'content_file' not in request.files:
                flash('لم يتم تحديد ملف', 'danger')
                return redirect(url_for('teacher.classroom', classroom_id=classroom.id))

            file = request.files['content_file']

            if file.filename == '':
                flash('لم يتم اختيار ملف. الرجاء اختيار ملف صالح', 'danger')
                return redirect(url_for('teacher.classroom', classroom_id=classroom.id))

        if file and allowed_file(file.filename):
            try:
                # طباعة معلومات تصحيح للملف
                print(f"محاولة تحميل ملف: {file.filename}, النوع: {file.content_type}")
                # Create upload directory if it doesn't exist
                upload_dir = os.path.join('static', 'uploads', 'classroom_content', str(classroom_id))
                if not os.path.exists(upload_dir):
                    try:
                        os.makedirs(upload_dir, exist_ok=True)
                        print(f"تم إنشاء مجلد التحميل بنجاح: {upload_dir}")
                    except Exception as e:
                        print(f"خطأ في إنشاء مجلد التحميل: {e}")

                # Generate a secure filename with timestamp
                original_name, file_extension = os.path.splitext(file.filename)
                timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
                saved_filename = f"{timestamp}_{file_extension}"  # إضافة underscore قبل الامتداد

                # Save the file
                file_path = os.path.join(upload_dir, saved_filename)
                file.save(file_path)
                
                # التحقق من نجاح حفظ الملف
                if os.path.exists(file_path):
                    print(f"تم حفظ الملف بنجاح في: {file_path}")
                    print(f"حجم الملف: {os.path.getsize(file_path)} بايت")
                else:
                    print(f"فشل في حفظ الملف، الملف غير موجود: {file_path}")
                
                # Store the relative path to the file
                content_url = f"/{upload_dir}/{saved_filename}"
                print(f"URL المحتوى: {content_url}")
            except Exception as e:
                print(f"خطأ في تحميل الملف: {e}")
                flash(f'حدث خطأ أثناء تحميل الملف: {e}', 'danger')
                return redirect(url_for('teacher.classroom', classroom_id=classroom.id))
        else:
            flash('الملف غير صالح', 'danger')
            return redirect(url_for('teacher.classroom', classroom_id=classroom.id))

    try:
        # Create content
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
        print(f"خطأ في حفظ المحتوى في قاعدة البيانات: {e}")
        flash(f'حدث خطأ أثناء حفظ المحتوى: {e}', 'danger')

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

    db.session.delete(content)
    db.session.commit()

    flash('تم حذف المحتوى بنجاح', 'success')
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

    return render_template('classroom/assignments.html',
                           classroom=classroom,
                           assignments=assignments)

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
                            os.makedirs(upload_dir, exist_ok=True)

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

    return render_template('classroom/assignments.html', classroom=classroom)

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

    return render_template('classroom/edit_assignment.html',
                         classroom=classroom,
                         assignment=assignment)

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

    return render_template('teacher/assignment_submissions.html',
                           classroom=classroom,
                           assignment=assignment,
                           submissions=submissions,
                           missing_submissions=missing_submissions)

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

    return render_template('teacher/quizzes.html',
                           classroom=classroom,
                           quizzes=quizzes)

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

    return render_template('teacher/create_quiz.html', classroom=classroom)

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

    return render_template('teacher/edit_quiz.html',
                         classroom=classroom,
                         quiz=quiz,
                         questions=questions)

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

    return render_template('teacher/grade_quiz.html',
                           classroom=classroom,
                           quiz=quiz,
                           attempts=attempts)

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

    return render_template('teacher/quiz_results.html',
                         classroom=classroom,
                         quiz=quiz,
                         attempts=attempts)

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

    return render_template('teacher/view_student_attempt.html',
                         classroom=classroom,
                         quiz=quiz,
                         attempt=attempt,
                         answers=answers)

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

    return render_template('teacher/students.html',
                           classroom=classroom,
                           enrollments=enrollments)

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
                filepath = os.path.join('static', 'uploads', 'chat_images', filename)
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

    return render_template('classroom/chat_settings.html',
                         classroom=classroom,
                         settings=settings,
                         enrollments=enrollments,
                         chat_participants=chat_participants,
                         user_type='teacher')

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

    return render_template('teacher/payments.html',
                         classrooms=classrooms,
                         pending_payments=pending_payments,
                         completed_payments=completed_payments)

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