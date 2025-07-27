"""
نظام الحضور والغياب للطلاب
Attendance System for Students
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, g
from flask_login import login_required, current_user
from models import db, User, Classroom, ClassroomEnrollment, Attendance, SystemSettings
from datetime import datetime, date
from sqlalchemy import and_, desc
from routes.auth import csrf_exempt

attendance_bp = Blueprint('attendance', __name__, url_prefix='/attendance')

def is_mobile():
    """Check if current request is from a mobile device"""
    user_agent = request.headers.get('User-Agent', '').lower()
    return any(device in user_agent for device in ['android', 'iphone', 'ipad', 'mobile'])

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
    
    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي
    
    template = 'attendance/mobile-theme/mark_attendance.html' if is_mobile() else 'attendance/mark_attendance.html'
    
    return render_template(template, 
                         classroom=classroom, 
                         enrollments=enrollments,
                         today_attendance=today_attendance,
                         primary_color=primary_color,
                         secondary_color=secondary_color)

@attendance_bp.route('/save', methods=['POST'])
@login_required
def save_attendance():
    """حفظ تسجيلات الحضور"""
    if current_user.role not in ['teacher', 'assistant']:
        return jsonify({'success': False, 'message': 'غير مصرح لك بهذا الإجراء'})
    
    try:
        # التحقق من نوع المحتوى
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
            
        classroom_id = data.get('classroom_id')
        attendance_data = data.get('attendance_data')
        attendance_date = data.get('date', date.today().isoformat())
        
        # تحويل النصوص إلى أرقام إذا لزم الأمر
        if isinstance(classroom_id, str):
            classroom_id = int(classroom_id)
            
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
        
        attendance_date_obj = datetime.strptime(attendance_date, '%Y-%m-%d').date()
        
        for student_id, status_data in attendance_data.items():
            student_id = int(student_id)
            
            # إذا كانت البيانات في شكل نص، فهي حالة مباشرة
            if isinstance(status_data, str):
                status = status_data
                notes = ''
            else:
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
    
    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')  # اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')  # اللون الافتراضي
    
    template = 'attendance/mobile-theme/attendance_report.html' if is_mobile() else 'attendance/attendance_report.html'
    
    return render_template(template, 
                         classroom=classroom, 
                         students_data=students_data,
                         primary_color=primary_color,
                         secondary_color=secondary_color)

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

@attendance_bp.route('/student-details/<int:student_id>')
@login_required
def get_student_details(student_id):
    """الحصول على تفاصيل الطالب وسجل الحضور للمعلم/المساعد"""
    if current_user.role not in ['teacher', 'assistant']:
        return jsonify({'success': False, 'message': 'غير مصرح لك بهذا الإجراء'})
    
    student = User.query.get_or_404(student_id)
    
    if student.role != 'student':
        return jsonify({'success': False, 'message': 'المستخدم ليس طالباً'})
    
    # الحصول على إحصائيات الحضور
    total_attendance = Attendance.query.filter_by(student_id=student.id).count()
    present_days = Attendance.query.filter_by(student_id=student.id, status='present').count()
    late_days = Attendance.query.filter_by(student_id=student.id, status='late').count()
    absent_days = Attendance.query.filter_by(student_id=student.id, status='absent').count()
    excused_days = Attendance.query.filter_by(student_id=student.id, status='excused').count()
    
    attendance_rate = ((present_days + late_days) / total_attendance * 100) if total_attendance > 0 else 0
    
    # الحصول على سجل الحضور التفصيلي
    attendance_history = Attendance.query.filter_by(student_id=student.id)\
        .order_by(desc(Attendance.date))\
        .limit(20).all()
    
    attendance_records = []
    for attendance in attendance_history:
        attendance_records.append({
            'date': attendance.date.strftime('%Y-%m-%d'),
            'status': attendance.status,
            'time': attendance.time.strftime('%H:%M') if attendance.time else None,
            'notes': attendance.notes
        })
    
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
        'stats': {
            'present_days': present_days,
            'late_days': late_days,
            'absent_days': absent_days,
            'excused_days': excused_days,
            'attendance_rate': round(attendance_rate, 1)
        },
        'attendance_history': attendance_records
    })

@attendance_bp.route('/standalone-report/<int:classroom_id>')
@login_required
def standalone_report(classroom_id):
    """تقرير الحضور المستقل - صفحة منفصلة بتصميم موحد"""
    if current_user.role not in ['teacher', 'assistant', 'admin']:
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
    
    # الحصول على قائمة الطلاب وإحصائيات الحضور
    enrollments = ClassroomEnrollment.query.filter_by(
        classroom_id=classroom_id,
        is_active=True
    ).join(User).filter(User.role == 'student').all()
    
    students_data = []
    distribution_data = {
        'present': 0,
        'late': 0,
        'absent': 0,
        'excused': 0
    }
    
    for enrollment in enrollments:
        student = enrollment.user
        
        # حساب إحصائيات الحضور للطالب
        attendances = Attendance.query.filter_by(
            student_id=student.id,
            classroom_id=classroom_id
        ).all()
        
        present_days = len([a for a in attendances if a.status == 'present'])
        late_days = len([a for a in attendances if a.status == 'late'])
        absent_days = len([a for a in attendances if a.status == 'absent'])
        excused_days = len([a for a in attendances if a.status == 'excused'])
        total_days = len(attendances)
        
        # تحديث البيانات التوزيعية
        distribution_data['present'] += present_days
        distribution_data['late'] += late_days
        distribution_data['absent'] += absent_days
        distribution_data['excused'] += excused_days
        
        # حساب نسبة الحضور
        if total_days > 0:
            attendance_rate = ((present_days + late_days) / total_days) * 100
        else:
            attendance_rate = 0
        
        # حساب متوسط الدرجات إذا كان متاحاً
        try:
            average_grade = '-'  # يمكن إضافة منطق حساب الدرجات هنا
        except:
            average_grade = '-'
        
        students_data.append({
            'student': student,
            'attendance_stats': {
                'present_days': present_days,
                'late_days': late_days,
                'absent_days': absent_days,
                'excused_days': excused_days,
                'total_days': total_days,
                'attendance_rate': round(attendance_rate, 1),
                'average_grade': average_grade
            }
        })
    
    # إعداد بيانات الاتجاه الزمني (مثال بسيط)
    trend_data = {
        'dates': ['الأسبوع 1', 'الأسبوع 2', 'الأسبوع 3', 'الأسبوع 4'],
        'rates': [85, 90, 88, 92]  # يمكن حساب القيم الفعلية
    }
    
    # إعداد الإحصائيات العامة
    stats = {
        'distribution_data': distribution_data,
        'trend_data': trend_data
    }
    
    # الحصول على إعدادات النظام للألوان
    primary_color = SystemSettings.get_setting('primary_color', '#6366f1')
    secondary_color = SystemSettings.get_setting('secondary_color', '#8b5cf6')
    
    # اختيار القالب المناسب حسب نوع الجهاز
    if is_mobile():
        template = 'attendance/mobile-theme/standalone_report.html'
    else:
        template = 'attendance/standalone_report.html'
    
    return render_template(template,
                         classroom=classroom,
                         students_data=students_data,
                         stats=stats,
                         primary_color=primary_color,
                         secondary_color=secondary_color)
