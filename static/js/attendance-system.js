// نظام التحقق من رقم هاتف ولي الأمر والحضور
// Parent Phone and Attendance Validation System

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
                        
                        <div class="text-center">
                            <i class="fas fa-phone fa-3x text-warning mb-3"></i>
                            <p><strong>لماذا نحتاج رقم هاتف ولي الأمر؟</strong></p>
                            <ul class="list-unstyled text-start">
                                <li><i class="fas fa-check text-success me-2"></i>إشعارات الحضور والغياب</li>
                                <li><i class="fas fa-check text-success me-2"></i>التواصل في حالات الطوارئ</li>
                                <li><i class="fas fa-check text-success me-2"></i>إشعارات الدرجات والواجبات</li>
                                <li><i class="fas fa-check text-success me-2"></i>المتابعة الأكاديمية</li>
                            </ul>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                            <i class="fas fa-times me-2"></i>إلغاء
                        </button>
                        <a href="/auth/profile" class="btn btn-primary">
                            <i class="fas fa-user-edit me-2"></i>
                            إضافة رقم ولي الأمر
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
async function joinClassroomWithValidation(classroomCode) {
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

// إشعار تنبيهي للطلاب بدون رقم ولي أمر
function showParentPhoneAlert() {
    checkParentPhoneBeforeJoin().then(hasPhone => {
        if (!hasPhone) {
            const alertHtml = `
                <div class="alert alert-warning alert-dismissible fade show m-3" role="alert" id="parentPhoneAlert">
                    <div class="d-flex align-items-center">
                        <i class="fas fa-exclamation-triangle fa-2x me-3"></i>
                        <div class="flex-grow-1">
                            <strong>تنبيه مهم:</strong> يجب إضافة رقم هاتف ولي الأمر في ملفك الشخصي لتتمكن من الانضمام للفصول الدراسية.
                        </div>
                        <a href="/auth/profile" class="btn btn-outline-warning btn-sm ms-2">
                            <i class="fas fa-user-edit me-1"></i>تحديث الملف الشخصي
                        </a>
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                </div>
            `;
            
            const container = document.querySelector('.container-fluid') || document.querySelector('.container') || document.body;
            if (container && !document.getElementById('parentPhoneAlert')) {
                container.insertAdjacentHTML('afterbegin', alertHtml);
            }
        }
    });
}

// نظام الحضور والغياب - دوال المعلم/المساعد
const AttendanceSystem = {
    // حفظ بيانات الحضور
    saveAttendance: function(classroomId, attendanceData, date) {
        return fetch('/attendance/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                classroom_id: parseInt(classroomId),
                attendance_data: attendanceData,
                date: date
            })
        })
        .then(response => response.json());
    },

    // الحصول على معلومات الطالب
    getStudentInfo: function(studentId) {
        return fetch(`/attendance/student-info/${studentId}`)
            .then(response => response.json());
    },

    // تسجيل حضور سريع لجميع الطلاب
    markAllPresent: function() {
        const allRadios = document.querySelectorAll('input[type="radio"][value="present"]');
        allRadios.forEach(radio => {
            radio.checked = true;
        });
        showNotification('تم تحديد جميع الطلاب كحاضرين', 'info');
    },

    // تسجيل غياب سريع لجميع الطلاب
    markAllAbsent: function() {
        const allRadios = document.querySelectorAll('input[type="radio"][value="absent"]');
        allRadios.forEach(radio => {
            radio.checked = true;
        });
        showNotification('تم تحديد جميع الطلاب كغائبين', 'info');
    },

    // البحث في قائمة الطلاب
    searchStudents: function(searchTerm) {
        const rows = document.querySelectorAll('tbody tr');
        rows.forEach(row => {
            const studentName = row.querySelector('td strong').textContent.toLowerCase();
            const studentPhone = row.querySelectorAll('td')[1].textContent.toLowerCase();
            
            if (studentName.includes(searchTerm.toLowerCase()) || 
                studentPhone.includes(searchTerm.toLowerCase())) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }
};

// تهيئة نظام الحضور عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', function() {
    // تشغيل التحقق للطلاب
    if (typeof userRole !== 'undefined' && userRole === 'student') {
        showParentPhoneAlert();
    }

    // إضافة أزرار سريعة لتسجيل الحضور (للمعلمين)
    if (document.querySelector('.attendance-radio')) {
        addQuickAttendanceButtons();
    }

    // إضافة خاصية البحث في قائمة الطلاب
    addStudentSearchBox();
});

// إضافة أزرار التحكم السريع في الحضور
function addQuickAttendanceButtons() {
    const attendanceForm = document.getElementById('attendanceForm');
    if (attendanceForm) {
        const quickActionsHtml = `
            <div class="card mb-3">
                <div class="card-body">
                    <h6 class="card-title">
                        <i class="fas fa-bolt me-2"></i>إجراءات سريعة
                    </h6>
                    <div class="btn-group" role="group">
                        <button type="button" class="btn btn-success btn-sm" onclick="AttendanceSystem.markAllPresent()">
                            <i class="fas fa-check-double me-1"></i>تحديد الكل حاضر
                        </button>
                        <button type="button" class="btn btn-danger btn-sm" onclick="AttendanceSystem.markAllAbsent()">
                            <i class="fas fa-times-circle me-1"></i>تحديد الكل غائب
                        </button>
                        <button type="button" class="btn btn-info btn-sm" onclick="toggleSearchBox()">
                            <i class="fas fa-search me-1"></i>البحث في الطلاب
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        attendanceForm.insertAdjacentHTML('afterbegin', quickActionsHtml);
    }
}

// إضافة خاصية البحث
function addStudentSearchBox() {
    const quickActions = document.querySelector('.btn-group');
    if (quickActions) {
        const searchHtml = `
            <div class="mt-2" id="searchBox" style="display: none;">
                <input type="text" class="form-control" placeholder="البحث بالاسم أو رقم الهاتف..." 
                       oninput="AttendanceSystem.searchStudents(this.value)">
            </div>
        `;
        
        quickActions.parentElement.insertAdjacentHTML('beforeend', searchHtml);
    }
}

function toggleSearchBox() {
    const searchBox = document.getElementById('searchBox');
    if (searchBox) {
        if (searchBox.style.display === 'none') {
            searchBox.style.display = 'block';
            searchBox.querySelector('input').focus();
        } else {
            searchBox.style.display = 'none';
            searchBox.querySelector('input').value = '';
            AttendanceSystem.searchStudents(''); // إظهار جميع الطلاب
        }
    }
}

// تصدير الدوال للاستخدام العام
window.AttendanceSystem = AttendanceSystem;
window.checkParentPhoneBeforeJoin = checkParentPhoneBeforeJoin;
window.joinClassroomWithValidation = joinClassroomWithValidation;
