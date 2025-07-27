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

@chat.route('/redirect/<int:classroom_id>')
@login_required 
def chat_redirect(classroom_id):
    """توجيه تلقائي للنظام المحسن"""
    from urllib.parse import urlencode
    
    # بناء رابط النظام المحسن
    improved_url = f"/chat/classroom/{classroom_id}?use_improved=true"
    fallback_url = f"/chat/classroom/{classroom_id}?legacy=true"
    
    return render_template('chat_redirect.html', 
                         improved_url=improved_url,
                         fallback_url=fallback_url)

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
        
        # التحقق من وجود النظام المحسن وتوجيه المستخدم إليه
        if request.args.get('use_improved') == 'true' or not request.args.get('legacy'):
            if current_user.role == 'teacher':
                template = 'teacher/mobile-theme/chat_improved.html' if is_mobile else 'teacher/chat_improved.html'
            elif current_user.role == 'assistant':
                template = 'classroom/mobile-theme/chat_improved.html' if is_mobile else 'classroom/chat_improved.html'
            else:  # student
                template = 'student/mobile-theme/chat_improved.html' if is_mobile else 'student/chat_improved.html'
        else:
            # النظام القديم
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
            if enrollment.user.role == 'student':  # التأكد من أن المستخدم طالب
                participants.append({
                    'id': enrollment.user.id,
                    'name': enrollment.user.name,
                    'role': 'student',
                    'avatar': enrollment.user.name[0].upper()
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
        enrollment.is_active = False
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

@chat.route('/classroom/<int:classroom_id>/messages', methods=['GET'])
@login_required  
def get_messages(classroom_id):
    """جلب رسائل الفصل"""
    try:
        classroom = Classroom.query.get_or_404(classroom_id)
        
        # التحقق من صلاحية الوصول
        if not has_access_to_classroom(current_user, classroom_id):
            return jsonify({'error': 'غير مسموح لك بالوصول'}), 403
        
        since = request.args.get('since')
        
        # بناء الاستعلام
        query = ChatMessage.query.filter_by(
            classroom_id=classroom_id,
            is_deleted=False
        ).join(User).add_columns(
            User.name.label('user_name'),
            User.role.label('user_role')
        )
        
        if since:
            try:
                since_date = datetime.fromisoformat(since.replace('Z', '+00:00'))
                query = query.filter(ChatMessage.created_at > since_date)
            except:
                pass
        
        messages = query.order_by(ChatMessage.created_at.asc()).limit(100).all()
        
        messages_data = []
        for message, user_name, user_role in messages:
            messages_data.append({
                'id': message.id,
                'message': message.message,
                'user_id': message.user_id,
                'user_name': user_name,
                'user_role': user_role,
                'created_at': message.created_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'messages': messages_data
        })
        
    except Exception as e:
        logger.error(f"خطأ في جلب الرسائل: {str(e)}")
        return jsonify({'error': 'فشل في جلب الرسائل'}), 500

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
            message=data['text'],
            created_at=datetime.utcnow()
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

# API endpoints للنظام الموحد
@chat.route('/api/send', methods=['POST'])
@login_required
def unified_send_message():
    """API موحد لإرسال الرسائل"""
    try:
        data = request.get_json()
        classroom_id = data.get('classroomId')
        
        if not classroom_id:
            return jsonify({'error': 'معرف الفصل مطلوب'}), 400
            
        if not data or not data.get('text'):
            return jsonify({'error': 'نص الرسالة مطلوب'}), 400
        
        # التحقق من صلاحية الوصول
        classroom = Classroom.query.get_or_404(classroom_id)
        if not has_chat_access(current_user, classroom):
            return jsonify({'error': 'غير مسموح لك بالدردشة في هذا الفصل'}), 403
        
        # إنشاء رسالة جديدة
        message = ChatMessage(
            classroom_id=classroom_id,
            user_id=current_user.id,
            message=data['text'],
            created_at=datetime.utcnow()
        )
        
        db.session.add(message)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message_id': message.id,
            'data': {
                'id': message.id,
                'text': message.message,
                'senderId': message.user_id,
                'senderName': message.user.name,
                'senderRole': message.user.role,
                'timestamp': message.created_at.isoformat(),
                'classroomId': classroom_id
            }
        })
        
    except Exception as e:
        logger.error(f"خطأ في إرسال الرسالة الموحدة: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'فشل في إرسال الرسالة'}), 500

@chat.route('/api/messages/<int:classroom_id>')
@login_required
def unified_get_messages(classroom_id):
    """API موحد لجلب الرسائل"""
    try:
        classroom = Classroom.query.get_or_404(classroom_id)
        if not has_chat_access(current_user, classroom):
            return jsonify({'error': 'غير مسموح لك بالوصول'}), 403
        
        messages = ChatMessage.query.filter_by(classroom_id=classroom_id)\
                                  .order_by(ChatMessage.created_at.desc())\
                                  .limit(50).all()
        
        messages_data = []
        for msg in reversed(messages):
            messages_data.append({
                'id': msg.id,
                'text': msg.message,
                'senderId': msg.user_id,
                'senderName': msg.user.name,
                'senderRole': msg.user.role,
                'timestamp': msg.created_at.isoformat(),
                'classroomId': classroom_id
            })
        
        return jsonify({
            'success': True,
            'messages': messages_data
        })
        
    except Exception as e:
        logger.error(f"خطأ في جلب الرسائل: {str(e)}")
        return jsonify({'error': 'فشل في جلب الرسائل'}), 500

@chat.route('/api/settings', methods=['POST'])
@login_required
def update_chat_settings_api():
    """تحديث إعدادات الدردشة عبر API"""
    try:
        data = request.get_json()
        classroom_id = data.get('classroomId')
        
        if not classroom_id:
            return jsonify({'error': 'معرف الفصل مطلوب'}), 400
            
        classroom = Classroom.query.get_or_404(classroom_id)
        
        # التحقق من الصلاحية (معلم أو مساعد فقط)
        if current_user.role not in ['teacher', 'assistant']:
            return jsonify({'error': 'غير مسموح لك بتعديل الإعدادات'}), 403
            
        if current_user.role == 'teacher' and classroom.teacher_id != current_user.id:
            return jsonify({'error': 'غير مسموح لك بتعديل إعدادات هذا الفصل'}), 403
            
        if current_user.role == 'assistant' and classroom.assistant_id != current_user.id:
            return jsonify({'error': 'غير مسموح لك بتعديل إعدادات هذا الفصل'}), 403
        
        # تحديث الإعدادات
        settings = ChatSettings.query.filter_by(classroom_id=classroom_id).first()
        if not settings:
            settings = ChatSettings(classroom_id=classroom_id)
            db.session.add(settings)
        
        # تحديث الإعدادات المختلفة
        if 'enabled' in data:
            settings.is_enabled = data['enabled']
        if 'allowStudentMessages' in data:
            settings.allow_student_messages = data['allowStudentMessages']
        if 'moderateMessages' in data:
            settings.moderate_messages = data['moderateMessages']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'تم تحديث الإعدادات بنجاح'
        })
        
    except Exception as e:
        logger.error(f"خطأ في تحديث الإعدادات: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'فشل في تحديث الإعدادات'}), 500

@chat.route('/api/export')
@login_required
def export_chat():
    """تصدير رسائل الدردشة"""
    try:
        classroom_id = request.args.get('classroomId')
        if not classroom_id:
            return jsonify({'error': 'معرف الفصل مطلوب'}), 400
            
        classroom = Classroom.query.get_or_404(classroom_id)
        
        # التحقق من الصلاحية (معلم أو مساعد فقط)
        if current_user.role not in ['teacher', 'assistant']:
            return jsonify({'error': 'غير مسموح لك بتصدير الرسائل'}), 403
        
        messages = ChatMessage.query.filter_by(classroom_id=classroom_id)\
                                  .order_by(ChatMessage.created_at.asc()).all()
        
        from flask import make_response
        import io
        
        output = io.StringIO()
        output.write(f"تصدير رسائل الدردشة - {classroom.name}\n")
        output.write(f"تاريخ التصدير: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        output.write("="*50 + "\n\n")
        
        for msg in messages:
            timestamp = msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
            output.write(f"[{timestamp}] {msg.user.name} ({msg.user.role}): {msg.message}\n")
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/plain; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename=chat-export-{classroom_id}.txt'
        
        return response
        
    except Exception as e:
        logger.error(f"خطأ في تصدير الرسائل: {str(e)}")
        return jsonify({'error': 'فشل في تصدير الرسائل'}), 500

def has_chat_access(user, classroom):
    """التحقق من صلاحية الوصول للدردشة"""
    if user.role == 'teacher':
        return classroom.teacher_id == user.id
    elif user.role == 'assistant':
        return classroom.assistant_id == user.id
    elif user.role == 'student':
        enrollment = ClassroomEnrollment.query.filter_by(
            user_id=user.id,
            classroom_id=classroom.id,
            is_active=True
        ).first()
        return enrollment is not None
    return False

@chat.errorhandler(403)
def forbidden(error):
    return jsonify({'error': 'غير مسموح لك بالوصول'}), 403

@chat.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'حدث خطأ في الخادم'}), 500
