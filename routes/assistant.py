import os
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app import db
from models import User, Role, Classroom, ClassroomEnrollment, Assignment, AssignmentSubmission
from models import ChatMessage, ChatSettings, ChatParticipant
from models import Quiz, QuizQuestion, QuizAnswer, QuizAttempt

# Allowed file extensions for uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

assistant_bp = Blueprint('assistant', __name__)

# Assistant required decorator
def assistant_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != Role.ASSISTANT:
            flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@assistant_bp.route('/dashboard')
@login_required
@assistant_required
def dashboard():
    # Get classrooms where the user is assigned as an assistant
    assigned_classrooms = Classroom.query.filter_by(assistant_id=current_user.id).all()
    
    return render_template('dashboard/assistant.html', classrooms=assigned_classrooms)

@assistant_bp.route('/classroom/<int:classroom_id>')
@login_required
@assistant_required
def classroom(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    
    # Ensure the assistant is assigned to this classroom
    if classroom.assistant_id != current_user.id:
        flash('غير مصرح لك بالوصول إلى هذا الفصل', 'danger')
        return redirect(url_for('assistant.dashboard'))
    
    # Get enrolled students
    enrollments = ClassroomEnrollment.query.filter_by(classroom_id=classroom.id).all()
    
    # Get assignments
    assignments = Assignment.query.filter_by(classroom_id=classroom.id).all()
    
    # Get teacher info
    teacher = User.query.get(classroom.teacher_id)
    
    return render_template('classroom/assistant_view.html',
                           classroom=classroom,
                           enrollments=enrollments,
                           assignments=assignments,
                           teacher=teacher)

@assistant_bp.route('/classroom/<int:classroom_id>/chat')
@login_required
@assistant_required
def chat(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    
    # Ensure the assistant is assigned to this classroom
    if classroom.assistant_id != current_user.id:
        flash('غير مصرح لك بالوصول إلى هذا الفصل', 'danger')
        return redirect(url_for('assistant.dashboard'))
    
    # Get chat messages
    messages = ChatMessage.query.filter_by(classroom_id=classroom.id, is_deleted=False).order_by(ChatMessage.created_at).all()
    
    # Get enrolled students for chat management
    enrollments = ClassroomEnrollment.query.filter_by(classroom_id=classroom.id, is_active=True).all()
    
    return render_template('classroom/chat.html',
                           classroom=classroom,
                           messages=messages,
                           enrollments=enrollments,
                           user_type='assistant')

@assistant_bp.route('/classroom/<int:classroom_id>/chat/delete_message/<int:message_id>', methods=['POST'])
@login_required
@assistant_required
def delete_message(classroom_id, message_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    message = ChatMessage.query.get_or_404(message_id)
    
    # Ensure the assistant is assigned to this classroom
    if classroom.assistant_id != current_user.id or message.classroom_id != classroom.id:
        flash('غير مصرح لك بحذف هذه الرسالة', 'danger')
        return redirect(url_for('assistant.chat', classroom_id=classroom.id))
    
    # Mark message as deleted
    message.is_deleted = True
    db.session.commit()
    
    flash('تم حذف الرسالة بنجاح', 'success')
    return redirect(url_for('assistant.chat', classroom_id=classroom.id))

@assistant_bp.route('/classroom/<int:classroom_id>/chat/manage_students', methods=['POST'])
@login_required
@assistant_required
def manage_chat_students(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    
    # Ensure the assistant is assigned to this classroom
    if classroom.assistant_id != current_user.id:
        flash('غير مصرح لك بإدارة الطلاب في هذا الفصل', 'danger')
        return redirect(url_for('assistant.dashboard'))
    
    action = request.form.get('action')
    student_id = request.form.get('student_id')
    
    if not action or not student_id:
        flash('بيانات غير كاملة', 'danger')
        return redirect(url_for('assistant.chat', classroom_id=classroom.id))
    
    enrollment = ClassroomEnrollment.query.filter_by(
        classroom_id=classroom.id,
        user_id=student_id
    ).first()
    
    if not enrollment:
        flash('الطالب غير مسجل في الفصل', 'danger')
        return redirect(url_for('assistant.chat', classroom_id=classroom.id))
    
    if action == 'remove':
        # This wouldn't actually remove the student from the classroom,
        # but would prevent them from seeing the chat (managed via frontend visibility)
        # You would typically have a separate "can_access_chat" field in the enrollment model
        flash('تم منع الطالب من الوصول إلى المحادثة', 'success')
    elif action == 'add':
        flash('تم السماح للطالب بالوصول إلى المحادثة', 'success')
    
    return redirect(url_for('assistant.chat', classroom_id=classroom.id))

@assistant_bp.route('/classroom/<int:classroom_id>/assignments')
@login_required
@assistant_required
def assignments(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    
    # Ensure the assistant is assigned to this classroom
    if classroom.assistant_id != current_user.id:
        flash('غير مصرح لك بالوصول إلى هذا الفصل', 'danger')
        return redirect(url_for('assistant.dashboard'))
    
    # Get assignments
    assignments = Assignment.query.filter_by(classroom_id=classroom.id).all()
    
    return render_template('classroom/assistant_assignments.html',
                           classroom=classroom,
                           assignments=assignments)

@assistant_bp.route('/classroom/<int:classroom_id>/assignment/<int:assignment_id>/submissions')
@login_required
@assistant_required
def assignment_submissions(classroom_id, assignment_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Ensure the assistant is assigned to this classroom
    if classroom.assistant_id != current_user.id or assignment.classroom_id != classroom.id:
        flash('غير مصرح لك بالوصول إلى هذا الواجب', 'danger')
        return redirect(url_for('assistant.dashboard'))
    
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
    
    return render_template('classroom/assistant_submissions.html',
                           classroom=classroom,
                           assignment=assignment,
                           submissions=submissions,
                           missing_submissions=missing_submissions)

@assistant_bp.route('/classroom/<int:classroom_id>/assignment/<int:assignment_id>/grade/<int:submission_id>', methods=['POST'])
@login_required
@assistant_required
def grade_submission(classroom_id, assignment_id, submission_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    assignment = Assignment.query.get_or_404(assignment_id)
    submission = AssignmentSubmission.query.get_or_404(submission_id)
    
    # Ensure the assistant is assigned to this classroom
    if classroom.assistant_id != current_user.id or assignment.classroom_id != classroom.id:
        flash('غير مصرح لك بالوصول إلى هذا الواجب', 'danger')
        return redirect(url_for('assistant.dashboard'))
    
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
    return redirect(url_for('assistant.assignment_submissions', classroom_id=classroom.id, assignment_id=assignment.id))

@assistant_bp.route('/classroom/<int:classroom_id>/students')
@login_required
@assistant_required
def students(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    
    # Ensure the assistant is assigned to this classroom
    if classroom.assistant_id != current_user.id:
        flash('غير مصرح لك بالوصول إلى هذا الفصل', 'danger')
        return redirect(url_for('assistant.dashboard'))
    
    # Get enrollments with students
    enrollments = ClassroomEnrollment.query.filter_by(classroom_id=classroom.id).all()
    
    return render_template('classroom/assistant_students.html',
                           classroom=classroom,
                           enrollments=enrollments)

@assistant_bp.route('/classroom/<int:classroom_id>/chat/settings', methods=['GET', 'POST'])
@login_required
@assistant_required
def chat_settings(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    
    # Ensure the assistant is assigned to this classroom
    if classroom.assistant_id != current_user.id:
        flash('غير مصرح لك بالوصول إلى هذا الفصل', 'danger')
        return redirect(url_for('assistant.dashboard'))

    # Get chat settings
    settings = ChatSettings.query.filter_by(classroom_id=classroom.id).first()
    if not settings:
        flash('لم يتم تكوين إعدادات المحادثة بعد', 'warning')
        return redirect(url_for('assistant.classroom', classroom_id=classroom.id))

    if request.method == 'POST':
        settings.background_color = request.form.get('background_color')
        
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
        return redirect(url_for('assistant.chat_settings', classroom_id=classroom.id))

    # Get enrolled students
    enrollments = ClassroomEnrollment.query.filter_by(classroom_id=classroom.id).all()
    
    # Get chat participants
    chat_participants = ChatParticipant.query.filter_by(classroom_id=classroom.id).all()
    
    return render_template('classroom/chat_settings.html',
                         classroom=classroom,
                         settings=settings,
                         enrollments=enrollments,
                         chat_participants=chat_participants,
                         user_type='assistant')

@assistant_bp.route('/classroom/<int:classroom_id>/chat/manage_participants', methods=['POST'])
@login_required
@assistant_required
def manage_chat_participants(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    
    # Ensure the assistant is assigned to this classroom
    if classroom.assistant_id != current_user.id:
        flash('غير مصرح لك بالوصول إلى هذا الفصل', 'danger')
        return redirect(url_for('assistant.dashboard'))

    action = request.form.get('action')
    enrollment_id = request.form.get('enrollment_id')
    
    if not action or not enrollment_id:
        flash('بيانات غير كاملة', 'danger')
        return redirect(url_for('assistant.chat_settings', classroom_id=classroom.id))

    enrollment = ClassroomEnrollment.query.get_or_404(enrollment_id)
    if enrollment.classroom_id != classroom.id:
        flash('الطالب غير مسجل في هذا الفصل', 'danger')
        return redirect(url_for('assistant.chat_settings', classroom_id=classroom.id))

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
    return redirect(url_for('assistant.chat_settings', classroom_id=classroom.id))

@assistant_bp.route('/classroom/<int:classroom_id>/quizzes')
@login_required
@assistant_required
def quizzes(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    
    # Ensure the assistant is assigned to this classroom
    if classroom.assistant_id != current_user.id:
        flash('غير مصرح لك بالوصول إلى هذا الفصل', 'danger')
        return redirect(url_for('assistant.dashboard'))
    
    # Get quizzes
    quizzes = Quiz.query.filter_by(classroom_id=classroom.id).order_by(Quiz.created_at.desc()).all()
    
    return render_template('classroom/assistant_quizzes.html',
                         classroom=classroom,
                         quizzes=quizzes)

@assistant_bp.route('/classroom/<int:classroom_id>/quiz/<int:quiz_id>/results')
@login_required
@assistant_required
def quiz_results(classroom_id, quiz_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Ensure the assistant is assigned to this classroom
    if classroom.assistant_id != current_user.id or quiz.classroom_id != classroom.id:
        flash('غير مصرح لك بالوصول إلى هذا الاختبار', 'danger')
        return redirect(url_for('assistant.dashboard'))
    
    # Get all attempts for this quiz, including user information through enrollment
    attempts = QuizAttempt.query.filter_by(quiz_id=quiz.id).order_by(QuizAttempt.start_time.desc()).all()
    
    return render_template('classroom/assistant_quiz_results.html',
                         classroom=classroom,
                         quiz=quiz,
                         attempts=attempts)

@assistant_bp.route('/classroom/<int:classroom_id>/quiz/<int:quiz_id>/grade')
@login_required
@assistant_required
def grade_quiz(classroom_id, quiz_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Ensure the assistant is assigned to this classroom
    if classroom.assistant_id != current_user.id or quiz.classroom_id != classroom.id:
        flash('غير مصرح لك بالوصول إلى هذا الاختبار', 'danger')
        return redirect(url_for('assistant.dashboard'))
    
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
    
    return render_template('classroom/assistant_grade_quiz.html',
                         classroom=classroom,
                         quiz=quiz,
                         attempts=attempts)

@assistant_bp.route('/classroom/<int:classroom_id>/quiz/<int:quiz_id>/attempt/<int:attempt_id>/grade', methods=['POST'])
@login_required
@assistant_required
def grade_quiz_attempt(classroom_id, quiz_id, attempt_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    quiz = Quiz.query.get_or_404(quiz_id)
    attempt = QuizAttempt.query.get_or_404(attempt_id)
    
    # Ensure the assistant is assigned to this classroom
    if classroom.assistant_id != current_user.id or quiz.classroom_id != classroom.id or attempt.quiz_id != quiz.id:
        flash('غير مصرح لك بالوصول إلى هذا الاختبار', 'danger')
        return redirect(url_for('assistant.dashboard'))
    
    # Process grades
    total_points = 0
    all_graded = True
    
    for answer in attempt.answers:
        if answer.question.question_type in ['essay', 'short_answer']:
            points = request.form.get(f'points_{answer.id}')
            feedback = request.form.get(f'feedback_{answer.id}')
            
            if points is not None:
                points = int(points)
                if 0 <= points <= answer.question.points:
                    answer.points_earned = points
                    answer.feedback = feedback
                    total_points += points
                else:
                    flash(f'النقاط يجب أن تكون بين 0 و {answer.question.points}', 'danger')
                    return redirect(url_for('assistant.grade_quiz', classroom_id=classroom.id, quiz_id=quiz.id))
            else:
                all_graded = False
    
    # Update attempt score if all questions are graded
    if all_graded:
        # Add points from automatically graded questions
        for answer in attempt.answers:
            if answer.question.question_type in ['multiple_choice', 'true_false']:
                total_points += answer.points_earned or 0
        
        attempt.score = total_points
        attempt.is_graded = True
        
        # Update student points
        attempt.enrollment.points += total_points
        
        flash('تم حفظ التصحيح بنجاح', 'success')
    else:
        flash('يرجى تصحيح جميع الأسئلة', 'danger')
        return redirect(url_for('assistant.grade_quiz', classroom_id=classroom.id, quiz_id=quiz.id))
    
    db.session.commit()
    return redirect(url_for('assistant.grade_quiz', classroom_id=classroom.id, quiz_id=quiz.id))

@assistant_bp.route('/classroom/<int:classroom_id>/quiz/<int:quiz_id>/attempt/<int:attempt_id>/view')
@login_required
@assistant_required
def view_student_attempt(classroom_id, quiz_id, attempt_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    quiz = Quiz.query.get_or_404(quiz_id)
    attempt = QuizAttempt.query.get_or_404(attempt_id)
    
    # Ensure the assistant is assigned to this classroom and the attempt belongs to this quiz
    if classroom.assistant_id != current_user.id or quiz.classroom_id != classroom.id or attempt.quiz_id != quiz.id:
        flash('غير مصرح لك بالوصول إلى هذا الاختبار', 'danger')
        return redirect(url_for('assistant.dashboard'))
    
    # Get answers with their questions, ordered by question position
    answers = QuizAnswer.query\
        .join(QuizQuestion)\
        .filter(QuizAnswer.attempt_id == attempt.id)\
        .order_by(QuizQuestion.position)\
        .all()
    
    return render_template('classroom/assistant_view_attempt.html',
                         classroom=classroom,
                         quiz=quiz,
                         attempt=attempt,
                         answers=answers)
