#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
إصلاح مشكلة Google OAuth وإضافة نظام الحضور والغياب
Fix Google OAuth authentication issue and add attendance system
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from models import db, User
from flask_migrate import upgrade
import sqlite3

def fix_google_auth_issue():
    """إصلاح مشكلة Google OAuth بإضافة العمود المفقود"""
    try:
        # إنشاء تطبيق Flask
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/al-7esa.db'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        db.init_app(app)
        
        with app.app_context():
            # التحقق من وجود عمود google_id
            connection = db.engine.connect()
            try:
                # محاولة الاستعلام عن العمود
                result = connection.execute("PRAGMA table_info(user);")
                columns = [column[1] for column in result.fetchall()]
                
                if 'google_id' not in columns:
                    print("إضافة عمود google_id...")
                    # إضافة العمود
                    connection.execute("ALTER TABLE user ADD COLUMN google_id VARCHAR(100);")
                    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_user_google_id ON user (google_id);")
                    print("تم إضافة عمود google_id بنجاح!")
                else:
                    print("عمود google_id موجود بالفعل")
                    
                connection.commit()
                
            except Exception as e:
                print(f"خطأ في إضافة العمود: {e}")
            finally:
                connection.close()
                
        print("تم إصلاح مشكلة Google OAuth بنجاح!")
        return True
        
    except Exception as e:
        print(f"خطأ في إصلاح Google OAuth: {e}")
        return False

def create_attendance_functions():
    """إنشاء ملف نظام الحضور والغياب"""
    
    attendance_routes_content = '''"""
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
'''
    
    try:
        # إنشاء مجلد routes إذا لم يكن موجوداً
        routes_dir = 'routes'
        if not os.path.exists(routes_dir):
            os.makedirs(routes_dir)
        
        # كتابة ملف نظام الحضور
        with open(os.path.join(routes_dir, 'attendance.py'), 'w', encoding='utf-8') as f:
            f.write(attendance_routes_content)
        
        print("تم إنشاء ملف نظام الحضور بنجاح!")
        return True
        
    except Exception as e:
        print(f"خطأ في إنشاء ملف نظام الحضور: {e}")
        return False

def create_attendance_templates():
    """إنشاء قوالب HTML لنظام الحضور"""
    
    # قالب تسجيل الحضور
    mark_attendance_template = '''{% extends "base.html" %}

{% block title %}تسجيل الحضور - {{ classroom.name }}{% endblock %}

{% block content %}
<div class="container-fluid">
    <div class="row">
        <div class="col-12">
            <div class="card">
                <div class="card-header bg-primary text-white">
                    <h4 class="mb-0">
                        <i class="fas fa-calendar-check me-2"></i>
                        تسجيل الحضور - {{ classroom.name }}
                    </h4>
                    <small>{{ moment().format('dddd، DD MMMM YYYY') }}</small>
                </div>
                <div class="card-body">
                    <form id="attendanceForm">
                        <input type="hidden" id="classroomId" value="{{ classroom.id }}">
                        <input type="hidden" id="attendanceDate" value="{{ moment().format('YYYY-MM-DD') }}">
                        
                        <div class="table-responsive">
                            <table class="table table-striped">
                                <thead class="table-dark">
                                    <tr>
                                        <th>الطالب</th>
                                        <th>رقم الهاتف</th>
                                        <th>حاضر</th>
                                        <th>متأخر</th>
                                        <th>غائب</th>
                                        <th>غياب بعذر</th>
                                        <th>ملاحظات</th>
                                        <th>معلومات الاتصال</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for enrollment in enrollments %}
                                    {% set student = enrollment.user %}
                                    {% set attendance = today_attendance.get(student.id) %}
                                    <tr>
                                        <td>
                                            <div class="d-flex align-items-center">
                                                {% if student.profile_picture %}
                                                <img src="{{ url_for('static', filename='uploads/profile_pictures/' + student.profile_picture) }}" 
                                                     class="rounded-circle me-2" width="32" height="32" alt="{{ student.name }}">
                                                {% else %}
                                                <div class="bg-secondary rounded-circle me-2 d-flex align-items-center justify-content-center" 
                                                     style="width: 32px; height: 32px;">
                                                    <i class="fas fa-user text-white"></i>
                                                </div>
                                                {% endif %}
                                                <strong>{{ student.name }}</strong>
                                            </div>
                                        </td>
                                        <td>{{ student.phone }}</td>
                                        <td>
                                            <input type="radio" name="attendance_{{ student.id }}" value="present" 
                                                   {% if attendance and attendance.status == 'present' %}checked{% endif %}
                                                   class="form-check-input attendance-radio" data-student="{{ student.id }}">
                                        </td>
                                        <td>
                                            <input type="radio" name="attendance_{{ student.id }}" value="late" 
                                                   {% if attendance and attendance.status == 'late' %}checked{% endif %}
                                                   class="form-check-input attendance-radio" data-student="{{ student.id }}">
                                        </td>
                                        <td>
                                            <input type="radio" name="attendance_{{ student.id }}" value="absent" 
                                                   {% if attendance and attendance.status == 'absent' %}checked{% endif %}
                                                   class="form-check-input attendance-radio" data-student="{{ student.id }}">
                                        </td>
                                        <td>
                                            <input type="radio" name="attendance_{{ student.id }}" value="excused" 
                                                   {% if attendance and attendance.status == 'excused' %}checked{% endif %}
                                                   class="form-check-input attendance-radio" data-student="{{ student.id }}">
                                        </td>
                                        <td>
                                            <input type="text" class="form-control form-control-sm" 
                                                   id="notes_{{ student.id }}" 
                                                   value="{% if attendance %}{{ attendance.notes or '' }}{% endif %}"
                                                   placeholder="ملاحظات">
                                        </td>
                                        <td>
                                            <button type="button" class="btn btn-info btn-sm" 
                                                    onclick="showStudentInfo({{ student.id }})">
                                                <i class="fas fa-info-circle"></i>
                                            </button>
                                        </td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                        
                        <div class="text-end mt-3">
                            <button type="button" class="btn btn-success btn-lg" onclick="saveAttendance()">
                                <i class="fas fa-save me-2"></i>حفظ الحضور
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- معلومات الطالب Modal -->
<div class="modal fade" id="studentInfoModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header bg-info text-white">
                <h5 class="modal-title">معلومات الطالب</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body" id="studentInfoContent">
                <!-- سيتم تحميل المحتوى هنا -->
            </div>
        </div>
    </div>
</div>

<script>
function saveAttendance() {
    const classroomId = document.getElementById('classroomId').value;
    const attendanceDate = document.getElementById('attendanceDate').value;
    const attendanceData = {};
    
    // جمع بيانات الحضور
    document.querySelectorAll('.attendance-radio:checked').forEach(radio => {
        const studentId = radio.dataset.student;
        const status = radio.value;
        const notes = document.getElementById(`notes_${studentId}`).value;
        
        attendanceData[studentId] = {
            status: status,
            notes: notes
        };
    });
    
    // إرسال البيانات
    fetch('/attendance/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            classroom_id: parseInt(classroomId),
            attendance_data: attendanceData,
            date: attendanceDate
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('تم حفظ الحضور بنجاح', 'success');
        } else {
            showNotification(data.message, 'error');
        }
    })
    .catch(error => {
        showNotification('حدث خطأ في حفظ البيانات', 'error');
    });
}

function showStudentInfo(studentId) {
    fetch(`/attendance/student-info/${studentId}`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const student = data.student;
            const contactInfo = data.contact_info;
            const attendanceStats = data.attendance_stats;
            
            const content = `
                <div class="row">
                    <div class="col-md-4 text-center">
                        ${student.profile_picture ? 
                            `<img src="/static/uploads/profile_pictures/${student.profile_picture}" class="rounded-circle" width="100" height="100">` :
                            `<div class="bg-secondary rounded-circle mx-auto d-flex align-items-center justify-content-center" style="width: 100px; height: 100px;">
                                <i class="fas fa-user fa-2x text-white"></i>
                            </div>`
                        }
                        <h5 class="mt-2">${student.name}</h5>
                    </div>
                    <div class="col-md-8">
                        <div class="row mb-3">
                            <div class="col-12">
                                <h6 class="text-primary">معلومات الاتصال</h6>
                                <div class="contact-buttons">
                                    ${contactInfo.student_phone ? 
                                        `<a href="tel:${contactInfo.student_phone}" class="btn btn-outline-primary btn-sm me-2 mb-2">
                                            <i class="fas fa-phone"></i> اتصال بالطالب
                                        </a>` : ''
                                    }
                                    ${contactInfo.whatsapp_student ? 
                                        `<a href="${contactInfo.whatsapp_student}" target="_blank" class="btn btn-outline-success btn-sm me-2 mb-2">
                                            <i class="fab fa-whatsapp"></i> واتساب الطالب
                                        </a>` : ''
                                    }
                                    ${contactInfo.parent_phone ? 
                                        `<a href="tel:${contactInfo.parent_phone}" class="btn btn-outline-primary btn-sm me-2 mb-2">
                                            <i class="fas fa-phone"></i> اتصال بولي الأمر
                                        </a>` : ''
                                    }
                                    ${contactInfo.whatsapp_parent ? 
                                        `<a href="${contactInfo.whatsapp_parent}" target="_blank" class="btn btn-outline-success btn-sm me-2 mb-2">
                                            <i class="fab fa-whatsapp"></i> واتساب ولي الأمر
                                        </a>` : ''
                                    }
                                </div>
                            </div>
                        </div>
                        
                        <div class="row">
                            <div class="col-12">
                                <h6 class="text-success">إحصائيات الحضور</h6>
                                <div class="row text-center">
                                    <div class="col-3">
                                        <div class="card bg-success text-white">
                                            <div class="card-body p-2">
                                                <h5>${attendanceStats.present_days}</h5>
                                                <small>أيام حضور</small>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-3">
                                        <div class="card bg-danger text-white">
                                            <div class="card-body p-2">
                                                <h5>${attendanceStats.absent_days}</h5>
                                                <small>أيام غياب</small>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-3">
                                        <div class="card bg-warning text-white">
                                            <div class="card-body p-2">
                                                <h5>${attendanceStats.late_days}</h5>
                                                <small>أيام تأخير</small>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-3">
                                        <div class="card bg-info text-white">
                                            <div class="card-body p-2">
                                                <h5>${attendanceStats.attendance_rate}%</h5>
                                                <small>نسبة الحضور</small>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            document.getElementById('studentInfoContent').innerHTML = content;
            new bootstrap.Modal(document.getElementById('studentInfoModal')).show();
        } else {
            showNotification(data.message, 'error');
        }
    })
    .catch(error => {
        showNotification('حدث خطأ في تحميل معلومات الطالب', 'error');
    });
}
</script>
{% endblock %}'''
    
    try:
        # إنشاء مجلد templates/attendance
        templates_dir = 'templates/attendance'
        if not os.path.exists(templates_dir):
            os.makedirs(templates_dir)
        
        # كتابة قالب تسجيل الحضور
        with open(os.path.join(templates_dir, 'mark_attendance.html'), 'w', encoding='utf-8') as f:
            f.write(mark_attendance_template)
        
        print("تم إنشاء قوالب HTML لنظام الحضور بنجاح!")
        return True
        
    except Exception as e:
        print(f"خطأ في إنشاء قوالب HTML: {e}")
        return False

def add_parent_phone_notification():
    """إضافة إشعار للطلاب بضرورة إضافة رقم هاتف ولي الأمر"""
    
    notification_js = '''
// التحقق من رقم هاتف ولي الأمر للطلاب
function checkParentPhoneRequirement() {
    if (userRole === 'student') {
        fetch('/attendance/check-parent-phone')
        .then(response => response.json())
        .then(data => {
            if (data.success && !data.has_parent_phone) {
                showParentPhoneModal();
            }
        })
        .catch(error => {
            console.error('Error checking parent phone:', error);
        });
    }
}

function showParentPhoneModal() {
    const modalHtml = `
        <div class="modal fade" id="parentPhoneModal" tabindex="-1" data-bs-backdrop="static" data-bs-keyboard="false">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header bg-warning text-dark">
                        <h5 class="modal-title">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            إضافة رقم هاتف ولي الأمر مطلوب
                        </h5>
                    </div>
                    <div class="modal-body text-center">
                        <div class="alert alert-warning">
                            <i class="fas fa-phone fa-2x mb-3"></i>
                            <h6>يجب إضافة رقم هاتف ولي الأمر قبل الانضمام لأي فصل دراسي</h6>
                            <p class="mb-0">هذا مطلوب للتواصل مع ولي الأمر في حالات الطوارئ أو لإبلاغه بحالة الحضور والغياب</p>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <a href="/auth/profile" class="btn btn-primary">
                            <i class="fas fa-user-edit me-2"></i>
                            إضافة رقم هاتف ولي الأمر
                        </a>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // إضافة المودال إلى الصفحة
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // إظهار المودال
    new bootstrap.Modal(document.getElementById('parentPhoneModal')).show();
}

// تشغيل التحقق عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', function() {
    checkParentPhoneRequirement();
});
'''
    
    try:
        # إضافة الكود إلى ملف JavaScript الموجود
        js_file_path = 'static/js/main.js'
        
        # إنشاء الملف إذا لم يكن موجوداً
        if not os.path.exists('static/js'):
            os.makedirs('static/js')
        
        with open(js_file_path, 'a', encoding='utf-8') as f:
            f.write('\n\n' + notification_js)
        
        print("تم إضافة نظام التحقق من رقم هاتف ولي الأمر بنجاح!")
        return True
        
    except Exception as e:
        print(f"خطأ في إضافة نظام التحقق: {e}")
        return False

def main():
    """تشغيل جميع الإصلاحات والتحديثات"""
    print("بدء إصلاح مشكلة Google OAuth وإضافة نظام الحضور...")
    print("=" * 60)
    
    # إصلاح مشكلة Google OAuth
    if fix_google_auth_issue():
        print("✅ تم إصلاح مشكلة Google OAuth")
    else:
        print("❌ فشل في إصلاح مشكلة Google OAuth")
    
    # إنشاء نظام الحضور
    if create_attendance_functions():
        print("✅ تم إنشاء نظام الحضور")
    else:
        print("❌ فشل في إنشاء نظام الحضور")
    
    # إنشاء قوالب HTML
    if create_attendance_templates():
        print("✅ تم إنشاء قوالب HTML")
    else:
        print("❌ فشل في إنشاء قوالب HTML")
    
    # إضافة نظام التحقق من رقم ولي الأمر
    if add_parent_phone_notification():
        print("✅ تم إضافة نظام التحقق من رقم ولي الأمر")
    else:
        print("❌ فشل في إضافة نظام التحقق")
    
    print("=" * 60)
    print("تم الانتهاء من جميع التحديثات!")
    print("\nالخطوات التالية:")
    print("1. أعد تشغيل الخادم")
    print("2. تأكد من تسجيل blueprint الحضور في app.py")
    print("3. اختبر تسجيل الدخول بـ Google")
    print("4. اختبر نظام الحضور والغياب")

if __name__ == "__main__":
    main()
