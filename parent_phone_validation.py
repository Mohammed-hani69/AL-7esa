"""
تحديث مسارات الطلاب لإضافة التحقق من رقم هاتف ولي الأمر
Update student routes to add parent phone validation
"""

from flask import Blueprint, request, jsonify, flash, redirect, url_for, render_template
from flask_login import login_required, current_user
from models import db, User, Classroom, ClassroomEnrollment
from datetime import datetime

# يجب إضافة هذا إلى ملف routes/student.py الموجود

def validate_parent_phone_before_enrollment():
    """التحقق من وجود رقم هاتف ولي الأمر قبل الانضمام للفصل"""
    if current_user.role == 'student' and not current_user.has_parent_phone():
        return False
    return True

def add_parent_phone_validation_to_join_classroom():
    """
    هذه الدالة يجب إضافتها إلى مسار الانضمام للفصل في routes/student.py
    """
    # هذا المثال يوضح كيفية إضافة التحقق
    example_join_route = '''
@student_bp.route('/join-classroom', methods=['POST'])
@login_required
def join_classroom():
    """انضمام الطالب لفصل دراسي"""
    
    # التحقق من رقم هاتف ولي الأمر أولاً
    if not current_user.has_parent_phone():
        return jsonify({
            'success': False, 
            'message': 'يجب إضافة رقم هاتف ولي الأمر قبل الانضمام لأي فصل دراسي. يرجى تحديث ملفك الشخصي أولاً.',
            'require_parent_phone': True,
            'redirect_url': url_for('auth.profile')
        })
    
    try:
        data = request.get_json()
        classroom_code = data.get('classroom_code')
        
        if not classroom_code:
            return jsonify({'success': False, 'message': 'كود الفصل مطلوب'})
        
        # البحث عن الفصل بالكود
        classroom = Classroom.query.filter_by(code=classroom_code).first()
        
        if not classroom:
            return jsonify({'success': False, 'message': 'كود الفصل غير صحيح'})
        
        # التحقق من عدم انضمام الطالب مسبقاً
        existing_enrollment = ClassroomEnrollment.query.filter_by(
            user_id=current_user.id,
            classroom_id=classroom.id,
            is_active=True
        ).first()
        
        if existing_enrollment:
            return jsonify({'success': False, 'message': 'أنت منضم لهذا الفصل بالفعل'})
        
        # إنشاء تسجيل جديد
        new_enrollment = ClassroomEnrollment(
            user_id=current_user.id,
            classroom_id=classroom.id,
            joined_at=datetime.utcnow(),
            is_active=True,
            payment_status='pending' if not classroom.is_free else 'free'
        )
        
        db.session.add(new_enrollment)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'تم انضمامك لفصل {classroom.name} بنجاح!',
            'classroom': {
                'id': classroom.id,
                'name': classroom.name,
                'subject': classroom.subject
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'حدث خطأ في الانضمام للفصل'})
    '''
    
    return example_join_route

# إضافة JavaScript للتحقق من رقم ولي الأمر في الفرونت إند
def get_parent_phone_check_javascript():
    """JavaScript للتحقق من رقم هاتف ولي الأمر"""
    
    js_code = '''
// التحقق من رقم هاتف ولي الأمر قبل الانضمام للفصول
function checkParentPhoneBeforeJoin() {
    return fetch('/attendance/check-parent-phone')
        .then(response => response.json())
        .then(data => {
            if (data.success && !data.has_parent_phone) {
                showParentPhoneRequiredModal();
                return false;
            }
            return true;
        })
        .catch(error => {
            console.error('Error checking parent phone:', error);
            return true; // في حالة الخطأ، اسمح بالمتابعة
        });
}

function showParentPhoneRequiredModal() {
    const modalHtml = `
        <div class="modal fade" id="parentPhoneRequiredModal" tabindex="-1" data-bs-backdrop="static">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header bg-warning text-dark">
                        <h5 class="modal-title">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            رقم هاتف ولي الأمر مطلوب
                        </h5>
                    </div>
                    <div class="modal-body">
                        <div class="alert alert-warning">
                            <h6 class="alert-heading">لا يمكن الانضمام للفصل</h6>
                            <p>يجب إضافة رقم هاتف ولي الأمر في ملفك الشخصي قبل الانضمام لأي فصل دراسي.</p>
                            <hr>
                            <p class="mb-0">هذا الرقم مطلوب للتواصل مع ولي الأمر حول حالة الحضور والغياب والإشعارات المهمة.</p>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">إلغاء</button>
                        <a href="/auth/profile" class="btn btn-primary">
                            <i class="fas fa-user-edit me-2"></i>
                            تحديث الملف الشخصي
                        </a>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // إزالة أي مودال سابق
    const existingModal = document.getElementById('parentPhoneRequiredModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // إضافة المودال الجديد
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // إظهار المودال
    new bootstrap.Modal(document.getElementById('parentPhoneRequiredModal')).show();
}

// تحديث دالة الانضمام للفصل لتتضمن التحقق
async function joinClassroom(classroomCode) {
    // التحقق من رقم ولي الأمر أولاً
    const hasParentPhone = await checkParentPhoneBeforeJoin();
    if (!hasParentPhone) {
        return; // إيقاف العملية إذا لم يكن رقم ولي الأمر موجود
    }
    
    // متابعة عملية الانضمام العادية
    fetch('/student/join-classroom', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            classroom_code: classroomCode
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message, 'success');
            // إعادة تحميل قائمة الفصول أو التوجه للفصل
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        } else {
            if (data.require_parent_phone) {
                showParentPhoneRequiredModal();
            } else {
                showNotification(data.message, 'error');
            }
        }
    })
    .catch(error => {
        showNotification('حدث خطأ في الانضمام للفصل', 'error');
    });
}

// تشغيل التحقق عند تحميل صفحات الطلاب
if (typeof userRole !== 'undefined' && userRole === 'student') {
    document.addEventListener('DOMContentLoaded', function() {
        // إضافة إشعار تنبيهي في أعلى الصفحة للطلاب بدون رقم ولي أمر
        checkParentPhoneBeforeJoin().then(hasPhone => {
            if (!hasPhone) {
                const alertHtml = `
                    <div class="alert alert-warning alert-dismissible fade show m-3" role="alert">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        <strong>تنبيه:</strong> يجب إضافة رقم هاتف ولي الأمر في ملفك الشخصي لتتمكن من الانضمام للفصول الدراسية.
                        <a href="/auth/profile" class="btn btn-sm btn-outline-warning ms-2">
                            تحديث الملف الشخصي
                        </a>
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                `;
                
                const container = document.querySelector('.container-fluid') || document.querySelector('.container') || document.body;
                container.insertAdjacentHTML('afterbegin', alertHtml);
            }
        });
    });
}
'''
    
    return js_code

if __name__ == "__main__":
    print("تم إنشاء كود التحقق من رقم هاتف ولي الأمر")
    print("يجب إضافة هذا الكود إلى:")
    print("1. ملف routes/student.py للتحقق من جانب الخادم")
    print("2. ملف JavaScript للتحقق من جانب العميل")
    print("3. تحديث قوالب HTML لتتضمن التحقق")
