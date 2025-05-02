from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app import db
from models import User, Role, Classroom, ClassroomEnrollment, Assignment, AssignmentSubmission
from models import ChatMessage

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
