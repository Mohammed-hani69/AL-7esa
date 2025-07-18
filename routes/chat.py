# routes/chat.py
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from models import User, Classroom, ClassroomEnrollment, ChatMessage, ChatParticipant, ChatSettings, db
from datetime import datetime
import logging

chat = Blueprint('chat', __name__, url_prefix='/chat')

# تسجيل الأخطاء
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@chat.route('/classroom/<int:classroom_id>')
@login_required
def classroom_chat(classroom_id):
    """صفحة المحادثة الرئيسية للفصل"""
    try:
        # التحقق من وجود الفصل
        classroom = Classroom.query.get_or_404(classroom_id)
        
        # التحقق من صلاحية الوصول
        if current_user.role == 'student':
            enrollment = ClassroomEnrollment.query.filter_by(
                user_id=current_user.id,
                classroom_id=classroom_id,
                is_active=True
            ).first()
            if not enrollment:
                return jsonify({'error': 'غير مسموح لك بدخول هذا الفصل'}), 403
        
        elif current_user.role == 'assistant':
            # التحقق من أن المساعد مخصص لهذا الفصل
            if classroom.assistant_id != current_user.id:
                return jsonify({'error': 'غير مسموح لك بدخول هذا الفصل'}), 403
        
        elif current_user.role == 'teacher':
            # التحقق من أن المعلم هو صاحب الفصل أو له صلاحية الوصول
            if classroom.teacher_id != current_user.id:
                return jsonify({'error': 'غير مسموح لك بدخول هذا الفصل'}), 403
        
        # حساب عدد المشاركين
        participants_count = get_participants_count(classroom_id)
        
        # تحديد القالب المناسب حسب الدور والجهاز
        is_mobile = is_mobile_device(request)
        
        if current_user.role == 'teacher':
            template = 'teacher/mobile-theme/chat.html' if is_mobile else 'teacher/chat.html'
        elif current_user.role == 'assistant':
            template = 'classroom/mobile-theme/chat.html' if is_mobile else 'classroom/chat.html'
        else:  # student
            template = 'student/mobile-theme/chat.html' if is_mobile else 'student/chat.html'
        
        return render_template(template, 
                             classroom=classroom,
                             participants_count=participants_count)
    
    except Exception as e:
        logger.error(f"خطأ في تحميل صفحة المحادثة: {str(e)}")
        return jsonify({'error': 'حدث خطأ في تحميل المحادثة'}), 500

@chat.route('/classroom/<int:classroom_id>/participants')
@login_required
def get_participants(classroom_id):
    """الحصول على قائمة المشاركين في الفصل"""
    try:
        classroom = Classroom.query.get_or_404(classroom_id)
        
        # التحقق من صلاحية الوصول
        if not has_access_to_classroom(current_user, classroom_id):
            return jsonify({'error': 'غير مسموح لك بالوصول'}), 403
        
        participants = []
        
        # إضافة المعلم
        if classroom.teacher:
            participants.append({
                'id': classroom.teacher.id,
                'name': classroom.teacher.name,
                'role': 'teacher',
                'avatar': classroom.teacher.name[0].upper()
            })
        
        # إضافة المساعد إذا كان موجوداً
        if classroom.assistant:
            participants.append({
                'id': classroom.assistant.id,
                'name': classroom.assistant.name,
                'role': 'assistant',
                'avatar': classroom.assistant.name[0].upper()
            })
        
        # إضافة الطلاب
        enrollments = ClassroomEnrollment.query.filter_by(
            classroom_id=classroom_id,
            is_active=True
        ).join(User).all()
        
        for enrollment in enrollments:
            participants.append({
                'id': ClassroomEnrollment.student.id,
                'name': ClassroomEnrollment.student.name,
                'role': 'student',
                'avatar': ClassroomEnrollment.student.name[0].upper()
            })
        
        return jsonify({'participants': participants})
    
    except Exception as e:
        logger.error(f"خطأ في جلب المشاركين: {str(e)}")
        return jsonify({'error': 'فشل في جلب المشاركين'}), 500

@chat.route('/classroom/<int:classroom_id>/add_student', methods=['POST'])
@login_required
def add_student_to_chat(classroom_id):
    """إضافة طالب إلى المحادثة"""
    try:
        # التحقق من الصلاحيات (معلم أو مساعد فقط)
        if current_user.role not in ['teacher', 'assistant']:
            return jsonify({'error': 'غير مسموح لك بهذا الإجراء'}), 403
        
        classroom = Classroom.query.get_or_404(classroom_id)
        
        # التحقق من صلاحية الوصول للفصل
        if current_user.role == 'teacher' and classroom.teacher_id != current_user.id:
            return jsonify({'error': 'غير مسموح لك بإدارة هذا الفصل'}), 403
        elif current_user.role == 'assistant' and classroom.assistant_id != current_user.id:
            return jsonify({'error': 'غير مسموح لك بإدارة هذا الفصل'}), 403
        
        data = request.get_json()
        student_id = data.get('student_id')
        
        if not student_id:
            return jsonify({'error': 'معرف الطالب مطلوب'}), 400
        
        # التحقق من وجود الطالب
        student = User.query.filter_by(id=student_id, role='student').first()
        if not student:
            return jsonify({'error': 'الطالب غير موجود'}), 404
        
        # التحقق من عدم وجود تسجيل مسبق
        existing_enrollment = ClassroomEnrollment.query.filter_by(
            user_id=student_id,
            classroom_id=classroom_id
        ).first()
        
        if existing_enrollment:
            if existing_enrollment.is_active:
                return jsonify({'error': 'الطالب مسجل بالفعل في الفصل'}), 400
            else:
                # إعادة تفعيل التسجيل
                existing_enrollment.is_active = True
                existing_enrollment.joined_at = datetime.utcnow()
        else:
            # إنشاء تسجيل جديد
            enrollment = ClassroomEnrollment(
                user_id=student_id,
                classroom_id=classroom_id,
                is_active=True,
                joined_at=datetime.utcnow()
            )
            db.session.add(enrollment)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم إضافة الطالب بنجاح',
            'student': {
                'id': student.id,
                'name': student.name
            }
        })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"خطأ في إضافة طالب: {str(e)}")
        return jsonify({'error': 'فشل في إضافة الطالب'}), 500

@chat.route('/classroom/<int:classroom_id>/remove_student', methods=['POST'])
@login_required
def remove_student_from_chat(classroom_id):
    """إزالة طالب من المحادثة"""
    try:
        # التحقق من الصلاحيات (معلم أو مساعد فقط)
        if current_user.role not in ['teacher', 'assistant']:
            return jsonify({'error': 'غير مسموح لك بهذا الإجراء'}), 403
        
        classroom = Classroom.query.get_or_404(classroom_id)
        
        # التحقق من صلاحية الوصول للفصل
        if current_user.role == 'teacher' and classroom.teacher_id != current_user.id:
            return jsonify({'error': 'غير مسموح لك بإدارة هذا الفصل'}), 403
        elif current_user.role == 'assistant' and classroom.assistant_id != current_user.id:
            return jsonify({'error': 'غير مسموح لك بإدارة هذا الفصل'}), 403
        
        data = request.get_json()
        student_id = data.get('student_id')
        
        if not student_id:
            return jsonify({'error': 'معرف الطالب مطلوب'}), 400
        
        # البحث عن التسجيل
        enrollment = ClassroomEnrollment.query.filter_by(
            user_id=student_id,
            classroom_id=classroom_id,
            is_active=True
        ).first()
        
        if not enrollment:
            return jsonify({'error': 'الطالب غير مسجل في الفصل'}), 404
        
        # إلغاء تفعيل التسجيل بدلاً من الحذف
        ClassroomEnrollment.status = 'inactive'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم إزالة الطالب بنجاح'
        })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"خطأ في إزالة طالب: {str(e)}")
        return jsonify({'error': 'فشل في إزالة الطالب'}), 500

@chat.route('/search_students')
@login_required
def search_students():
    """البحث عن الطلاب لإضافتهم"""
    try:
        # التحقق من الصلاحيات
        if current_user.role not in ['teacher', 'assistant']:
            return jsonify({'error': 'غير مسموح لك بهذا الإجراء'}), 403
        
        query = request.args.get('q', '').strip()
        
        if len(query) < 2:
            return jsonify({'students': []})
        
        # البحث في الطلاب
        students = User.query.filter(
            User.role == 'student',
            User.name.contains(query)
        ).limit(10).all()
        
        students_data = []
        for student in students:
            students_data.append({
                'id': student.id,
                'name': student.name,
                'phone': student.phone or 'غير محدد'
            })
        
        return jsonify({'students': students_data})
    
    except Exception as e:
        logger.error(f"خطأ في البحث عن الطلاب: {str(e)}")
        return jsonify({'error': 'فشل في البحث'}), 500

@chat.route('/classroom/<int:classroom_id>/settings')
@login_required
def chat_settings(classroom_id):
    """صفحة إعدادات المحادثة"""
    try:
        classroom = Classroom.query.get_or_404(classroom_id)
        
        # التحقق من الصلاحيات
        if current_user.role == 'teacher' and classroom.teacher_id != current_user.id:
            return jsonify({'error': 'غير مسموح لك بالوصول'}), 403
        elif current_user.role == 'assistant' and classroom.assistant_id != current_user.id:
            return jsonify({'error': 'غير مسموح لك بالوصول'}), 403
        elif current_user.role == 'student':
            enrollment = ClassroomEnrollment.query.filter_by(
                user_id=current_user.id,
                classroom_id=classroom_id,
                is_active=True
            ).first()
            if not enrollment:
                return jsonify({'error': 'غير مسموح لك بالوصول'}), 403
        
        # إعدادات المحادثة
        chat_settings = {
            'chat_enabled': getattr(classroom, 'chat_enabled', True),
            'allow_file_sharing': getattr(classroom, 'allow_file_sharing', True),
            'allow_emoji': getattr(classroom, 'allow_emoji', True),
            'max_message_length': getattr(classroom, 'max_message_length', 500)
        }
        
        return jsonify({
            'settings': chat_settings,
            'classroom': {
                'id': classroom.id,
                'name': classroom.name
            }
        })
    
    except Exception as e:
        logger.error(f"خطأ في جلب إعدادات المحادثة: {str(e)}")
        return jsonify({'error': 'فشل في جلب الإعدادات'}), 500

@chat.route('/classroom/<int:classroom_id>/update_settings', methods=['POST'])
@login_required
def update_chat_settings(classroom_id):
    """تحديث إعدادات المحادثة"""
    try:
        # التحقق من الصلاحيات (معلم فقط)
        if current_user.role != 'teacher':
            return jsonify({'error': 'غير مسموح لك بهذا الإجراء'}), 403
        
        classroom = Classroom.query.get_or_404(classroom_id)
        
        if classroom.teacher_id != current_user.id:
            return jsonify({'error': 'غير مسموح لك بإدارة هذا الفصل'}), 403
        
        data = request.get_json()
        
        # تحديث الإعدادات
        classroom.chat_enabled = data.get('chat_enabled', True)
        classroom.allow_file_sharing = data.get('allow_file_sharing', True)
        classroom.allow_emoji = data.get('allow_emoji', True)
        classroom.max_message_length = data.get('max_message_length', 500)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم تحديث إعدادات المحادثة بنجاح'
        })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"خطأ في تحديث إعدادات المحادثة: {str(e)}")
        return jsonify({'error': 'فشل في تحديث الإعدادات'}), 500

# دالات مساعدة
def has_access_to_classroom(user, classroom_id):
    """التحقق من صلاحية الوصول للفصل"""
    try:
        classroom = Classroom.query.get(classroom_id)
        if not classroom:
            return False
        
        if user.role == 'teacher':
            return classroom.teacher_id == user.id
        elif user.role == 'assistant':
            return classroom.assistant_id == user.id
        elif user.role == 'student':
            enrollment = ClassroomEnrollment.query.filter_by(
                user_id=user.id,
                classroom_id=classroom_id,
                is_active=True
            ).first()
            return enrollment is not None
        
        return False
    except:
        return False

def get_participants_count(classroom_id):
    """حساب عدد المشاركين في الفصل"""
    try:
        classroom = Classroom.query.get(classroom_id)
        if not classroom:
            return 0
        
        count = 0
        
        # المعلم
        if classroom.teacher:
            count += 1
        
        # المساعد
        if classroom.assistant:
            count += 1
        
        # الطلاب النشطين
        students_count = ClassroomEnrollment.query.filter_by(
            classroom_id=classroom_id,
            is_active=True
        ).count()
        
        count += students_count
        
        return count
    except:
        return 0

def is_mobile_device(request):
    """التحقق من نوع الجهاز"""
    user_agent = request.headers.get('User-Agent', '').lower()
    mobile_indicators = ['mobile', 'android', 'iphone', 'ipad', 'windows phone']
    return any(indicator in user_agent for indicator in mobile_indicators)

# معالج الأخطاء
@chat.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'الصفحة غير موجودة'}), 404

@chat.route('/classroom/<int:classroom_id>/send_message', methods=['POST'])
@login_required  
def send_message_api(classroom_id):
    """API بديل لإرسال الرسائل عند فشل Firebase"""
    try:
        classroom = Classroom.query.get_or_404(classroom_id)
        
        # التحقق من صلاحية الوصول
        if not has_access_to_classroom(current_user, classroom_id):
            return jsonify({'error': 'غير مسموح لك بالوصول'}), 403
        
        data = request.get_json()
        
        if not data or not data.get('text'):
            return jsonify({'error': 'نص الرسالة مطلوب'}), 400
        
        # إنشاء رسالة جديدة
        message = ChatMessage(
            classroom_id=classroom_id,
            user_id=current_user.id,
            content=data['text'],
            message_type='text'
        )
        
        db.session.add(message)
        db.session.commit()
        
        logger.info(f"تم حفظ رسالة جديدة: {message.id} من المستخدم {current_user.id}")
        
        return jsonify({
            'success': True,
            'message_id': message.id,
            'message': 'تم إرسال الرسالة بنجاح'
        })
        
    except Exception as e:
        logger.error(f"خطأ في إرسال الرسالة: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'فشل في إرسال الرسالة'}), 500

@chat.errorhandler(403)
def forbidden(error):
    return jsonify({'error': 'غير مسموح لك بالوصول'}), 403

@chat.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'حدث خطأ في الخادم'}), 500
