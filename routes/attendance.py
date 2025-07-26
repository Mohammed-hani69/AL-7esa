"""
نظام الحضور والغياب للطلاب
Attendance System for Students
"""

from flask import Blueprint, render_template, request, jsonify, flash
from flask_login import login_required, current_user
from models import db, User, Classroom, ClassroomEnrollment, Attendance
from datetime import datetime, date
from sqlalchemy import and_, desc

attendance_bp = Blueprint('attendance', __name__, url_prefix='/attendance')

@attendance_bp.route('/mark/<int:classroom_id>')
@login_required
def mark_attendance(classroom_id):
    """صفحة تسجيل الحضور للمعلم أو المساعد"""
    if current_user.role not in ['teacher', 'assistant']:
        flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'error')
        return redirect(url_for('main.index'))
    
    classroom = Classroom.query.get_or_404(classroom_id)
    
    # التحقق من صلاحية الوصول للفصل
    if current_user.role == 'teacher' and classroom.teacher_id != current_user.id:
        if classroom.assistant_id != current_user.id:
            flash('غير مصرح لك بالوصول إلى هذا الفصل', 'error')
            return redirect(url_for('main.index'))
    elif current_user.role == 'assistant' and classroom.assistant_id != current_user.id:
        flash('غير مصرح لك بالوصول إلى هذا الفصل', 'error')
        return redirect(url_for('main.index'))
    
    # الحصول على قائمة الطلاب المسجلين
    enrollments = ClassroomEnrollment.query.filter_by(
        classroom_id=classroom_id,
        is_active=True
    ).join(User).filter(User.role == 'student').all()
    
    # الحصول على تسجيلات الحضور لليوم الحالي
    today = date.today()
    today_attendance = {}
    for attendance in Attendance.query.filter_by(
        classroom_id=classroom_id,
        date=today
    ).all():
        today_attendance[attendance.student_id] = attendance
    
    return render_template('attendance/mark_attendance.html', 
                         classroom=classroom, 
                         enrollments=enrollments,
                         today_attendance=today_attendance)

@attendance_bp.route('/save', methods=['POST'])
@login_required
def save_attendance():
    """حفظ تسجيلات الحضور"""
    if current_user.role not in ['teacher', 'assistant']:
        return jsonify({'success': False, 'message': 'غير مصرح لك بهذا الإجراء'})
    
    data = request.get_json()
    classroom_id = data.get('classroom_id')
    attendance_data = data.get('attendance_data')
    attendance_date = data.get('date', date.today().isoformat())
    
    if not classroom_id or not attendance_data:
        return jsonify({'success': False, 'message': 'بيانات غير مكتملة'})
    
    # التحقق من صلاحية الوصول للفصل
    classroom = Classroom.query.get(classroom_id)
    if not classroom:
        return jsonify({'success': False, 'message': 'الفصل غير موجود'})
    
    if current_user.role == 'teacher' and classroom.teacher_id != current_user.id:
        if classroom.assistant_id != current_user.id:
            return jsonify({'success': False, 'message': 'غير مصرح لك بالوصول إلى هذا الفصل'})
    elif current_user.role == 'assistant' and classroom.assistant_id != current_user.id:
        return jsonify({'success': False, 'message': 'غير مصرح لك بالوصول إلى هذا الفصل'})
    
    try:
        attendance_date_obj = datetime.strptime(attendance_date, '%Y-%m-%d').date()
        
        for student_id, status_data in attendance_data.items():
            student_id = int(student_id)
            status = status_data.get('status')
            notes = status_data.get('notes', '')
            
            # البحث عن تسجيل حضور موجود
            existing_attendance = Attendance.query.filter_by(
                classroom_id=classroom_id,
                student_id=student_id,
                date=attendance_date_obj
            ).first()
            
            if existing_attendance:
                # تحديث التسجيل الموجود
                existing_attendance.status = status
                existing_attendance.notes = notes
                existing_attendance.updated_at = datetime.utcnow()
            else:
                # إنشاء تسجيل جديد
                new_attendance = Attendance(
                    classroom_id=classroom_id,
                    student_id=student_id,
                    date=attendance_date_obj,
                    status=status,
                    notes=notes,
                    recorded_by=current_user.id
                )
                db.session.add(new_attendance)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'تم حفظ الحضور بنجاح'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'حدث خطأ في حفظ البيانات: {str(e)}'})

@attendance_bp.route('/student-info/<int:student_id>')
@login_required
def get_student_info(student_id):
    """الحصول على معلومات الطالب للمعلم/المساعد"""
    if current_user.role not in ['teacher', 'assistant']:
        return jsonify({'success': False, 'message': 'غير مصرح لك بهذا الإجراء'})
    
    student = User.query.get_or_404(student_id)
    
    if student.role != 'student':
        return jsonify({'success': False, 'message': 'المستخدم ليس طالباً'})
    
    # الحصول على إحصائيات الحضور العامة
    attendance_stats = student.get_attendance_stats()
    
    # إعداد أرقام الاتصال
    contact_info = {
        'student_phone': student.phone,
        'student_alt_phone': student.alt_phone,
        'parent_phone': student.parent_phone,
        'whatsapp_student': f"https://wa.me/2{student.phone}" if student.phone else None,
        'whatsapp_parent': f"https://wa.me/2{student.parent_phone}" if student.parent_phone else None
    }
    
    return jsonify({
        'success': True,
        'student': {
            'id': student.id,
            'name': student.name,
            'phone': student.phone,
            'alt_phone': student.alt_phone,
            'parent_phone': student.parent_phone,
            'email': student.email,
            'profile_picture': student.profile_picture
        },
        'contact_info': contact_info,
        'attendance_stats': attendance_stats
    })

@attendance_bp.route('/report/<int:classroom_id>')
@login_required
def attendance_report(classroom_id):
    """تقرير الحضور والغياب للفصل"""
    if current_user.role not in ['teacher', 'assistant']:
        flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'error')
        return redirect(url_for('main.index'))
    
    classroom = Classroom.query.get_or_404(classroom_id)
    
    # التحقق من صلاحية الوصول للفصل
    if current_user.role == 'teacher' and classroom.teacher_id != current_user.id:
        if classroom.assistant_id != current_user.id:
            flash('غير مصرح لك بالوصول إلى هذا الفصل', 'error')
            return redirect(url_for('main.index'))
    elif current_user.role == 'assistant' and classroom.assistant_id != current_user.id:
        flash('غير مصرح لك بالوصول إلى هذا الفصل', 'error')
        return redirect(url_for('main.index'))
    
    # الحصول على قائمة الطلاب مع إحصائيات الحضور
    enrollments = ClassroomEnrollment.query.filter_by(
        classroom_id=classroom_id,
        is_active=True
    ).join(User).filter(User.role == 'student').all()
    
    students_data = []
    for enrollment in enrollments:
        student = enrollment.user
        attendance_stats = student.get_attendance_stats(classroom_id)
        students_data.append({
            'student': student,
            'enrollment': enrollment,
            'attendance_stats': attendance_stats
        })
    
    return render_template('attendance/attendance_report.html', 
                         classroom=classroom, 
                         students_data=students_data)

@attendance_bp.route('/check-parent-phone')
@login_required
def check_parent_phone():
    """التحقق من وجود رقم هاتف ولي الأمر للطالب"""
    if current_user.role != 'student':
        return jsonify({'success': False, 'message': 'هذه الخدمة للطلاب فقط'})
    
    has_parent_phone = current_user.has_parent_phone()
    
    return jsonify({
        'success': True,
        'has_parent_phone': has_parent_phone,
        'message': 'يجب إضافة رقم هاتف ولي الأمر قبل الانضمام لأي فصل' if not has_parent_phone else 'تم التحقق بنجاح'
    })
