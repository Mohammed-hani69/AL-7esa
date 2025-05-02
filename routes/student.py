from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime
from app import db
from models import User, Role, Classroom, ClassroomEnrollment, ClassroomContent
from models import Assignment, AssignmentSubmission, Quiz, QuizQuestion, QuizAttempt, QuizAnswer
from models import Payment

student_bp = Blueprint('student', __name__)

# Student required decorator
def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != Role.STUDENT:
            flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    # Get student's enrolled classrooms
    enrollments = ClassroomEnrollment.query.filter_by(
        user_id=current_user.id, 
        is_active=True
    ).all()
    
    # Get upcoming assignments
    enrolled_classroom_ids = [enrollment.classroom_id for enrollment in enrollments]
    
    if enrolled_classroom_ids:
        upcoming_assignments = Assignment.query.filter(
            Assignment.classroom_id.in_(enrolled_classroom_ids),
            Assignment.due_date > datetime.utcnow()
        ).order_by(Assignment.due_date).limit(5).all()
        
        # Upcoming quizzes
        upcoming_quizzes = Quiz.query.filter(
            Quiz.classroom_id.in_(enrolled_classroom_ids),
            Quiz.end_time > datetime.utcnow(),
            Quiz.is_active == True
        ).order_by(Quiz.start_time).limit(5).all()
    else:
        upcoming_assignments = []
        upcoming_quizzes = []
    
    return render_template('dashboard/student.html',
                           enrollments=enrollments,
                           upcoming_assignments=upcoming_assignments,
                           upcoming_quizzes=upcoming_quizzes)

@student_bp.route('/join', methods=['GET', 'POST'])
@login_required
@student_required
def join_classroom():
    if request.method == 'POST':
        code = request.form.get('code').strip().upper()
        
        if not code:
            flash('الرجاء إدخال كود الفصل', 'danger')
            return redirect(url_for('student.join_classroom'))
        
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
    
    return render_template('student/join.html')

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
    
    return render_template('student/payment.html', classroom=classroom)

@student_bp.route('/process_payment/<int:classroom_id>', methods=['POST'])
@login_required
@student_required
def process_payment(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    
    # Here you would typically integrate with a payment gateway
    # For now, we'll simulate a successful payment
    
    # Create payment record
    payment = Payment(
        user_id=current_user.id,
        classroom_id=classroom.id,
        amount=classroom.price,
        status='success',
        payment_method='credit_card'
    )
    
    # Create enrollment
    enrollment = ClassroomEnrollment(
        user_id=current_user.id,
        classroom_id=classroom.id,
        payment_status='paid',
        payment_date=datetime.utcnow()
    )
    
    db.session.add(payment)
    db.session.add(enrollment)
    db.session.commit()
    
    flash('تم الدفع والانضمام إلى الفصل بنجاح', 'success')
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
    ).first()
    
    if not enrollment:
        flash('يجب أن تكون مسجلاً في الفصل للوصول إليه', 'danger')
        return redirect(url_for('student.dashboard'))
    
    # Get classroom content
    contents = ClassroomContent.query.filter_by(classroom_id=classroom.id).order_by(ClassroomContent.created_at.desc()).all()
    
    # Get assignments
    assignments = Assignment.query.filter_by(classroom_id=classroom.id).all()
    
    # Get quizzes
    quizzes = Quiz.query.filter_by(classroom_id=classroom.id, is_active=True).all()
    
    # Get teacher info
    teacher = User.query.get(classroom.teacher_id)
    
    # Check if the classroom has chat enabled
    has_chat = False
    if classroom.teacher:
        teacher_subs = classroom.teacher.subscriptions
        for sub in teacher_subs:
            if sub.is_active and sub.end_date > datetime.utcnow() and sub.plan.has_chat:
                has_chat = True
                break
    
    return render_template('student/student_view.html',
                           classroom=classroom,
                           enrollment=enrollment,
                           contents=contents,
                           assignments=assignments,
                           quizzes=quizzes,
                           teacher=teacher,
                           has_chat=has_chat)

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
    
    return render_template('student/student_assignments.html',
                           classroom=classroom,
                           enrollment=enrollment,
                           assignments=assignments,
                           submission_map=submission_map)

@student_bp.route('/classroom/<int:classroom_id>/assignment/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
@student_required
def view_assignment(classroom_id, assignment_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    assignment = Assignment.query.get_or_404(assignment_id)
    
    # Check if student is enrolled
    enrollment = ClassroomEnrollment.query.filter_by(
        user_id=current_user.id,
        classroom_id=classroom.id,
        is_active=True
    ).first()
    
    if not enrollment or assignment.classroom_id != classroom.id:
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
        
        content = request.form.get('content')
        
        if submission:
            # Update existing submission
            submission.content = content
            submission.submission_date = datetime.utcnow()
            db.session.commit()
            flash('تم تحديث الحل بنجاح', 'success')
        else:
            # Create new submission
            new_submission = AssignmentSubmission(
                enrollment_id=enrollment.id,
                assignment_id=assignment.id,
                content=content
            )
            db.session.add(new_submission)
            db.session.commit()
            flash('تم تسليم الحل بنجاح', 'success')
        
        return redirect(url_for('student.assignments', classroom_id=classroom.id))
    
    return render_template('student/view_assignment.html',
                           classroom=classroom,
                           assignment=assignment,
                           submission=submission)

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
    
    return render_template('student/student_quizzes.html',
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
    
    # Check if student is enrolled
    enrollment = ClassroomEnrollment.query.filter_by(
        user_id=current_user.id,
        classroom_id=classroom.id,
        is_active=True
    ).first()
    
    if not enrollment or quiz.classroom_id != classroom.id or not quiz.is_active:
        flash('غير مصرح لك بالوصول إلى هذا الاختبار', 'danger')
        return redirect(url_for('student.dashboard'))
    
    # Check if quiz is available
    now = datetime.utcnow()
    if quiz.start_time and now < quiz.start_time:
        flash('لم يبدأ الاختبار بعد', 'warning')
        return redirect(url_for('student.quizzes', classroom_id=classroom.id))
    
    if quiz.end_time and now > quiz.end_time:
        flash('انتهى وقت الاختبار', 'warning')
        return redirect(url_for('student.quizzes', classroom_id=classroom.id))
    
    # Check if student already completed this quiz
    existing_attempt = QuizAttempt.query.filter_by(
        enrollment_id=enrollment.id,
        quiz_id=quiz.id,
        is_completed=True
    ).first()
    
    if existing_attempt:
        flash('لقد أكملت هذا الاختبار بالفعل', 'info')
        return redirect(url_for('student.view_quiz_result', classroom_id=classroom.id, quiz_id=quiz.id))
    
    # Create or get an existing attempt
    attempt = QuizAttempt.query.filter_by(
        enrollment_id=enrollment.id,
        quiz_id=quiz.id,
        is_completed=False
    ).first()
    
    if not attempt:
        attempt = QuizAttempt(
            enrollment_id=enrollment.id,
            quiz_id=quiz.id
        )
        db.session.add(attempt)
        db.session.commit()
    
    # Get questions
    questions = QuizQuestion.query.filter_by(quiz_id=quiz.id).order_by(QuizQuestion.position).all()
    
    if request.method == 'POST':
        # Process quiz submission
        score = 0
        
        for question in questions:
            if question.question_type in ['multiple_choice', 'true_false']:
                # Get selected option
                option_id = request.form.get(f'question_{question.id}')
                
                if option_id:
                    option_id = int(option_id)
                    selected_option = next((o for o in question.options if o.id == option_id), None)
                    
                    if selected_option:
                        # Create answer
                        answer = QuizAnswer(
                            attempt_id=attempt.id,
                            question_id=question.id,
                            selected_option_id=selected_option.id,
                            is_correct=selected_option.is_correct,
                            points_earned=question.points if selected_option.is_correct else 0
                        )
                        
                        if selected_option.is_correct:
                            score += question.points
                        
                        db.session.add(answer)
            
            elif question.question_type in ['short_answer', 'essay']:
                # Get text answer
                text_answer = request.form.get(f'question_{question.id}')
                
                if text_answer:
                    # For short answer/essay, grade will be assigned by teacher later
                    answer = QuizAnswer(
                        attempt_id=attempt.id,
                        question_id=question.id,
                        text_answer=text_answer
                    )
                    db.session.add(answer)
        
        # Update attempt with score and completion
        attempt.end_time = datetime.utcnow()
        attempt.score = score
        attempt.is_completed = True
        
        # Update student points
        enrollment.points += score
        
        db.session.commit()
        
        flash('تم تسليم الاختبار بنجاح', 'success')
        return redirect(url_for('student.view_quiz_result', classroom_id=classroom.id, quiz_id=quiz.id))
    
    return render_template('student/take_quiz.html',
                           classroom=classroom,
                           quiz=quiz,
                           questions=questions,
                           attempt=attempt)

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
    
    return render_template('student/quiz_result.html',
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
    
    return render_template('student/live_class.html', classroom=classroom, enrollment=enrollment)
