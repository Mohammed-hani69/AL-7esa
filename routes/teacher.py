import random
import string
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime
from app import db
from models import User, Role, Classroom, ClassroomEnrollment, ClassroomContent, ContentType
from models import Assignment, AssignmentSubmission, Quiz, QuizQuestion, QuizQuestionOption
from models import Subscription, SubscriptionPlan

teacher_bp = Blueprint('teacher', __name__)

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

@teacher_bp.route('/dashboard')
@login_required
@teacher_required
def dashboard():
    # Get teacher's classrooms
    classrooms = Classroom.query.filter_by(teacher_id=current_user.id).all()
    
    # Get current subscription
    active_sub = Subscription.query.filter(
        Subscription.user_id == current_user.id,
        Subscription.end_date > datetime.utcnow(),
        Subscription.is_active == True
    ).first()
    
    # Get all subscription plans
    plans = SubscriptionPlan.query.all()
    
    return render_template('dashboard/teacher.html', 
                           classrooms=classrooms, 
                           subscription=active_sub,
                           plans=plans,
                           can_create_classroom=can_create_classroom())

@teacher_bp.route('/classroom/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_classroom():
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
    plan = get_current_plan()
    if plan and plan.has_chat:
        can_use_chat = True
    
    return render_template('classroom/view.html',
                           classroom=classroom,
                           contents=contents,
                           enrollments=enrollments,
                           assignments=assignments,
                           quizzes=quizzes,
                           assistant=assistant,
                           can_use_chat=can_use_chat)

@teacher_bp.route('/classroom/<int:classroom_id>/live')
@login_required
@teacher_required
def live_classroom(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    
    # Ensure the teacher owns this classroom
    if classroom.teacher_id != current_user.id:
        flash('غير مصرح لك بالوصول إلى هذا الفصل', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    return render_template('teacher/live_class.html', classroom=classroom)

@teacher_bp.route('/classroom/<int:classroom_id>/add_content', methods=['POST'])
@login_required
@teacher_required
def add_content(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    
    # Ensure the teacher owns this classroom
    if classroom.teacher_id != current_user.id:
        flash('غير مصرح لك بالوصول إلى هذا الفصل', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    title = request.form.get('title')
    description = request.form.get('description', '')
    content_type = request.form.get('content_type')
    
    if content_type not in [ContentType.FILE, ContentType.IMAGE, ContentType.AUDIO, ContentType.VIDEO, ContentType.TEXT]:
        flash('نوع المحتوى غير صالح', 'danger')
        return redirect(url_for('teacher.classroom', classroom_id=classroom.id))
    
    # Handle different content types
    content_url = None
    content_text = None
    
    if content_type == ContentType.TEXT:
        content_text = request.form.get('content_text', '')
    else:
        # Here you would typically upload the file to Firebase Storage
        # and get the URL, but we'll just use a placeholder for now
        content_url = f"/static/uploads/{content_type}_{classroom_id}_{datetime.utcnow().timestamp()}"
    
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
        
        # Create assignment
        new_assignment = Assignment(
            classroom_id=classroom.id,
            title=title,
            description=description,
            due_date=due_date,
            points=points
        )
        
        db.session.add(new_assignment)
        db.session.commit()
        
        flash('تم إنشاء الواجب بنجاح', 'success')
        return redirect(url_for('teacher.assignments', classroom_id=classroom.id))
    
    return render_template('classroom/create_assignment.html', classroom=classroom)

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
    
    return render_template('classroom/assignment_submissions.html',
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
    
    return render_template('classroom/quizzes.html',
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
    
    return render_template('classroom/create_quiz.html', classroom=classroom)

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
    
    # Get existing questions
    questions = QuizQuestion.query.filter_by(quiz_id=quiz.id).order_by(QuizQuestion.position).all()
    
    return render_template('classroom/edit_quiz.html',
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
    
    return render_template('classroom/students.html',
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
