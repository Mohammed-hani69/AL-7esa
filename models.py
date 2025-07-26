"""
نماذج قاعدة البيانات للمنصة التعليمية
يحتوي على تعريف جميع الجداول وعلاقاتها
"""

from datetime import datetime, timedelta
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
import hashlib
import os
import binascii

# Initialize db here to avoid circular imports
db = SQLAlchemy()

# User roles
class Role:
    STUDENT = 'student'
    TEACHER = 'teacher'
    ASSISTANT = 'assistant'
    ADMIN = 'admin'

"""
نموذج المستخدم (User)
يمثل جميع المستخدمين في النظام (مدرسين، طلاب، مشرفين)
"""
class User(UserMixin, db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    alt_phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(100), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=True)
    role = db.Column(db.String(20), nullable=False)
    profile_picture = db.Column(db.String(255), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    interests = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    firebase_uid = db.Column(db.String(100), unique=True, nullable=True)
    
    # أرقام المحافظ الإلكترونية للمعلم
    ewallet_number_1 = db.Column(db.String(50), nullable=True)  # رقم المحفظة الأول
    ewallet_number_2 = db.Column(db.String(50), nullable=True)  # رقم المحفظة الثاني
    
    # التحقق من وجود أرقام محافظ للمعلم
    def has_ewallet_numbers(self):
        """التحقق من وجود رقم محفظة واحد على الأقل"""
        return bool(self.ewallet_number_1 or self.ewallet_number_2)
    
    def get_ewallet_numbers_display(self):
        """الحصول على أرقام المحافظ في تنسيق عرض مناسب"""
        numbers = []
        if self.ewallet_number_1:
            numbers.append(self.ewallet_number_1)
        if self.ewallet_number_2:
            numbers.append(self.ewallet_number_2)
        
        if not numbers:
            return "لم يتم إضافة أرقام محافظ"
        
        return " / ".join(numbers)

    # Relationships
    classrooms = db.relationship('ClassroomEnrollment', back_populates='user')
    teacher_classrooms = db.relationship('Classroom', back_populates='teacher', foreign_keys='Classroom.teacher_id')
    assistant_classrooms = db.relationship('Classroom', back_populates='assistant', foreign_keys='Classroom.assistant_id')
    payments = db.relationship('Payment', back_populates='user')
    live_streams = db.relationship('LiveStream', back_populates='teacher')

    def set_password(self, password):
        """
        يحفظ كلمة المرور مشفرة بـ scrypt
        التنسيق: scrypt:16384:8:1$salt$hash
        """
        # توليد ملح عشوائي (16 بايت)
        salt = os.urandom(16)
        salt_b64 = binascii.b2a_base64(salt).decode('ascii').strip()
        
        # تشفير كلمة المرور باستخدام scrypt
        # N=16384, r=8, p=1 - معايير آمنة مع استهلاك ذاكرة أقل
        key = hashlib.scrypt(
            password.encode('utf-8'), 
            salt=salt, 
            n=16384, 
            r=8, 
            p=1, 
            dklen=32
        )
        key_hex = binascii.hexlify(key).decode('ascii')
        
        # تكوين التنسيق النهائي
        self.password_hash = f"scrypt:16384:8:1${salt_b64}${key_hex}"

    def check_password(self, password):
        """
        يتحقق من كلمة المرور المشفرة بـ scrypt
        """
        try:
            # تحليل التنسيق
            parts = self.password_hash.split('$')
            if len(parts) != 3 or not parts[0].startswith('scrypt:'):
                return False
            
            # استخراج المعايير
            params = parts[0].split(':')
            if len(params) != 4:
                return False
            
            n, r, p = int(params[1]), int(params[2]), int(params[3])
            salt_b64 = parts[1]
            stored_key_hex = parts[2]
            
            # فك تشفير الملح
            salt = binascii.a2b_base64(salt_b64.encode('ascii'))
            
            # تشفير كلمة المرور المدخلة بنفس المعايير
            key = hashlib.scrypt(
                password.encode('utf-8'),
                salt=salt,
                n=n,
                r=r,
                p=p,
                dklen=32
            )
            key_hex = binascii.hexlify(key).decode('ascii')
            
            # مقارنة آمنة
            return key_hex == stored_key_hex
            
        except Exception:
            return False

    def __repr__(self):
        return f'<User {self.name}>'

# Subscription plans
class SubscriptionPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    duration_days = db.Column(db.Integer, nullable=False)
    max_classrooms = db.Column(db.Integer, nullable=False)
    has_chat = db.Column(db.Boolean, default=False)
    allow_assistant = db.Column(db.Boolean, default=False)
    advanced_analytics = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subscriptions = db.relationship('Subscription', back_populates='plan')

    def __repr__(self):
        return f'<SubscriptionPlan {self.name}>'

# User subscriptions
class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plan.id'), nullable=False)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_trial = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('subscriptions', lazy=True))
    plan = db.relationship('SubscriptionPlan', back_populates='subscriptions')

    def __repr__(self):
        return f'<Subscription {self.user.name} - {self.plan.name}>'
    



"""
نموذج الفصل الدراسي (Classroom)
يمثل الفصول الدراسية التي ينشئها المدرسون
"""
class Classroom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    subject = db.Column(db.String(100), nullable=False)
    grade = db.Column(db.String(50), nullable=False)
    academic_year = db.Column(db.String(20), nullable=False)
    color = db.Column(db.String(20), nullable=True)
    image = db.Column(db.String(255), nullable=True)
    is_free = db.Column(db.Boolean, default=True)
    price = db.Column(db.Float, nullable=True)
    duration_days = db.Column(db.Integer, nullable=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assistant_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # إعدادات المحادثة
    chat_enabled = db.Column(db.Boolean, default=True)
    allow_file_sharing = db.Column(db.Boolean, default=True)
    allow_emoji = db.Column(db.Boolean, default=True)
    max_message_length = db.Column(db.Integer, default=500)

    # Relationships
    teacher = db.relationship('User', back_populates='teacher_classrooms', foreign_keys=[teacher_id])
    assistant = db.relationship('User', back_populates='assistant_classrooms', foreign_keys=[assistant_id])
    enrollments = db.relationship('ClassroomEnrollment', back_populates='classroom', cascade='all, delete-orphan')
    contents = db.relationship('ClassroomContent', back_populates='classroom', cascade='all, delete-orphan')
    assignments = db.relationship('Assignment', back_populates='classroom', cascade='all, delete-orphan')
    quizzes = db.relationship('Quiz', back_populates='classroom', cascade='all, delete-orphan')
    chat_messages = db.relationship('ChatMessage', back_populates='classroom', cascade='all, delete-orphan')
    chat_participants = db.relationship('ChatParticipant', back_populates='classroom', cascade='all, delete-orphan')
    payments = db.relationship('Payment', back_populates='classroom', cascade='all, delete-orphan')
    chat_settings = db.relationship('ChatSettings', back_populates='classroom', uselist=False, cascade='all, delete-orphan')
    live_streams = db.relationship('LiveStream', back_populates='classroom', cascade='all, delete-orphan')

    @property
    def interaction_rate(self):
        """حساب معدل تفاعل الطلاب في الفصل"""
        total_activities = 0
        total_possible = 0
        
        # حساب التفاعل من خلال الواجبات المكتملة
        for enrollment in self.enrollments:
            completed = sum(1 for submission in enrollment.assignment_submissions if submission.grade is not None)
            total_activities += completed
            total_possible += Assignment.query.filter_by(classroom_id=self.id).count()
            
        # حساب التفاعل من خلال الاختبارات المكتملة
        for enrollment in self.enrollments:
            completed = sum(1 for attempt in enrollment.quiz_attempts if attempt.is_completed)
            total_activities += completed
            total_possible += Quiz.query.filter_by(classroom_id=self.id).count()
        
        if total_possible == 0:
            return 0
        
        return round((total_activities / total_possible) * 100)

    @property
    def average_grade(self):
        """حساب متوسط درجات الطلاب في الفصل"""
        total_grades = []
        
        # جمع درجات الواجبات
        for enrollment in self.enrollments:
            grades = [submission.grade for submission in enrollment.assignment_submissions if submission.grade is not None]
            total_grades.extend(grades)
            
        # جمع درجات الاختبارات
        for enrollment in self.enrollments:
            grades = [attempt.score for attempt in enrollment.quiz_attempts if attempt.is_completed]
            total_grades.extend(grades)
        
        if not total_grades:
            return 0
            
        return sum(total_grades) / len(total_grades)

    @property
    def assignments_completion_rate(self):
        """حساب نسبة إكمال الواجبات في الفصل"""
        total_assignments = Assignment.query.filter_by(classroom_id=self.id).count()
        if total_assignments == 0:
            return 0
            
        completed = 0
        for enrollment in self.enrollments:
            completed += sum(1 for submission in enrollment.assignment_submissions if submission.grade is not None)
            
        expected_submissions = total_assignments * len(self.enrollments)
        if expected_submissions == 0:
            return 0
            
        return round((completed / expected_submissions) * 100)

    @property
    def attendance_rate(self):
        """حساب نسبة حضور الطلاب في الفصل"""
        # يمكن تنفيذ هذه الخاصية لاحقاً عندما نضيف نظام تتبع الحضور
        return 95  # قيمة افتراضية للعرض

    def __repr__(self):
        return f'<Classroom {self.name}>'

"""
نموذج عضوية الفصل (ClassroomMembership)
يربط بين المستخدمين والفصول الدراسية
"""
class ClassroomEnrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classroom.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    points = db.Column(db.Integer, default=0)
    payment_status = db.Column(db.String(20), nullable=True)  # 'paid', 'pending', 'free'
    payment_date = db.Column(db.DateTime, nullable=True)

    # Relationships
    user = db.relationship('User', back_populates='classrooms')
    classroom = db.relationship('Classroom', back_populates='enrollments')
    assignment_submissions = db.relationship('AssignmentSubmission', back_populates='enrollment', cascade='all, delete-orphan')
    quiz_attempts = db.relationship('QuizAttempt', back_populates='enrollment', cascade='all, delete-orphan')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'classroom_id', name='unique_enrollment'),
    )

    def __repr__(self):
        return f'<ClassroomEnrollment {self.user.name} - {self.classroom.name}>'

# Content types
class ContentType:
    FILE = 'file'
    IMAGE = 'image'
    AUDIO = 'audio'
    VIDEO = 'video'
    TEXT = 'text'

# Classroom content
class ClassroomContent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classroom.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    content_type = db.Column(db.String(20), nullable=False)
    content_url = db.Column(db.String(255), nullable=True)
    content_text = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    classroom = db.relationship('Classroom', back_populates='contents')

    def __repr__(self):
        return f'<ClassroomContent {self.title}>'

# Assignment model
class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classroom.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    due_date = db.Column(db.DateTime, nullable=True)
    points = db.Column(db.Integer, default=0)
    attachment_url = db.Column(db.String(255), nullable=True)  # URL للملف المرفق
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    classroom = db.relationship('Classroom', back_populates='assignments')
    submissions = db.relationship('AssignmentSubmission', back_populates='assignment', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Assignment {self.title}>'

# Assignment submission
class AssignmentSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    enrollment_id = db.Column(db.Integer, db.ForeignKey('classroom_enrollment.id'), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    content = db.Column(db.Text, nullable=True)  # النص اختياري الآن
    file_path = db.Column(db.String(255), nullable=True)  # مسار الملف المرفوع
    file_name = db.Column(db.String(255), nullable=True)  # اسم الملف الأصلي
    file_type = db.Column(db.String(50), nullable=True)   # نوع الملف
    submission_type = db.Column(db.String(20), nullable=False)  # 'text' أو 'file'
    submission_date = db.Column(db.DateTime, default=datetime.utcnow)
    grade = db.Column(db.Integer, nullable=True)
    feedback = db.Column(db.Text, nullable=True)

    # Relationships
    enrollment = db.relationship('ClassroomEnrollment', back_populates='assignment_submissions')
    assignment = db.relationship('Assignment', back_populates='submissions')

    def __repr__(self):
        return f'<AssignmentSubmission {self.enrollment.user.name} - {self.assignment.title}>'

"""
نموذج الاختبارات (Quiz)
يمثل الاختبارات التي ينشئها المدرسون
"""
class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classroom.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    total_points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    classroom = db.relationship('Classroom', back_populates='quizzes')
    questions = db.relationship('QuizQuestion', back_populates='quiz', cascade='all, delete-orphan')
    attempts = db.relationship('QuizAttempt', back_populates='quiz', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Quiz {self.title}>'

"""
نموذج أسئلة الاختبار (QuizQuestion)
يخزن الأسئلة المرتبطة بكل اختبار
"""
class QuizQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), nullable=False)
    points = db.Column(db.Integer, default=1)
    position = db.Column(db.Integer, default=0)

    # Relationships
    quiz = db.relationship('Quiz', back_populates='questions')
    options = db.relationship('QuizQuestionOption', back_populates='question', cascade='all, delete-orphan')
    answers = db.relationship('QuizAnswer', back_populates='question', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<QuizQuestion {self.id}>'

# Quiz question options (for multiple choice questions)
class QuizQuestionOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('quiz_question.id'), nullable=False)
    option_text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    position = db.Column(db.Integer, default=0)

    # Relationships
    question = db.relationship('QuizQuestion', back_populates='options')

    def __repr__(self):
        return f'<QuizQuestionOption {self.id}>'

"""
نموذج محاولات الاختبار (QuizAttempt)
يخزن محاولات الطلاب للاختبارات
"""
class QuizAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    enrollment_id = db.Column(db.Integer, db.ForeignKey('classroom_enrollment.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    score = db.Column(db.Integer, default=0)
    is_completed = db.Column(db.Boolean, default=False)
    is_graded = db.Column(db.Boolean, default=False)

    # Relationships
    enrollment = db.relationship('ClassroomEnrollment', back_populates='quiz_attempts')
    quiz = db.relationship('Quiz', back_populates='attempts')
    answers = db.relationship('QuizAnswer', back_populates='attempt', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<QuizAttempt {self.id}>'

"""
نموذج إجابات الطلاب (StudentAnswer)
يخزن إجابات الطلاب على الاختبارات
"""
class QuizAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('quiz_attempt.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('quiz_question.id'), nullable=False)
    selected_option_id = db.Column(db.Integer, db.ForeignKey('quiz_question_option.id'), nullable=True)
    text_answer = db.Column(db.Text, nullable=True)
    is_correct = db.Column(db.Boolean, nullable=True)
    points_earned = db.Column(db.Integer, nullable=True)

    # Relationships
    attempt = db.relationship('QuizAttempt', back_populates='answers')
    question = db.relationship('QuizQuestion', back_populates='answers')
    selected_option = db.relationship('QuizQuestionOption', backref=db.backref('answers', lazy=True))

    def __repr__(self):
        return f'<QuizAnswer {self.id}>'

# Notification model
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('notifications', lazy=True))

    def __repr__(self):
        return f'<Notification {self.id}>'

"""
نموذج المحادثات (Chat)
يخزن رسائل المحادثة في الفصول الدراسية
"""
class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classroom.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)

    # Relationships
    classroom = db.relationship('Classroom', back_populates='chat_messages')
    user = db.relationship('User', backref=db.backref('chat_messages', lazy=True))

    def __repr__(self):
        return f'<ChatMessage {self.id}>'

# Chat settings model
class ChatSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classroom.id', ondelete='CASCADE'), nullable=False)
    background_color = db.Column(db.String(20), nullable=True)
    image_url = db.Column(db.String(255), nullable=True)
    is_enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    classroom = db.relationship('Classroom', back_populates='chat_settings', uselist=False)

    def __repr__(self):
        return f'<ChatSettings {self.classroom.name}>'

# Chat participants model
class ChatParticipant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classroom.id'), nullable=False)
    enrollment_id = db.Column(db.Integer, db.ForeignKey('classroom_enrollment.id'), nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)
    added_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    classroom = db.relationship('Classroom', back_populates='chat_participants')
    enrollment = db.relationship('ClassroomEnrollment', backref=db.backref('chat_participant', uselist=False))
    added_by = db.relationship('User', backref=db.backref('chat_participants_added', lazy=True))

    __table_args__ = (
        db.UniqueConstraint('classroom_id', 'enrollment_id', name='unique_chat_participant'),
    )

    def __repr__(self):
        return f'<ChatParticipant {self.enrollment.user.name} - {self.classroom.name}>'

# Payment model
class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classroom.id'), nullable=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscription.id'), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='SAR')
    payment_method = db.Column(db.String(50), nullable=True)
    transaction_id = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), nullable=False)  # 'success', 'pending', 'failed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # New fields for e-wallet payments
    screenshot_path = db.Column(db.String(255), nullable=True)
    transfer_note = db.Column(db.String(255), nullable=True)
    ewallet_number = db.Column(db.String(50), nullable=True)

    # Relationships
    user = db.relationship('User', back_populates='payments')
    classroom = db.relationship('Classroom', back_populates='payments')
    subscription = db.relationship('Subscription', backref=db.backref('payment', lazy=True))

    def __repr__(self):
        return f'<Payment {self.id} - {self.amount} {self.currency}>'

"""
نموذج مدفوعات الاشتراكات (SubscriptionPayment)
يخزن عمليات دفع اشتراكات المعلمين
"""
class SubscriptionPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plan.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)  # bank_transfer, credit_card, etc
    payment_proof = db.Column(db.String(255), nullable=True)  # صورة إثبات الدفع
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    notes = db.Column(db.Text, nullable=True)  # ملاحظات الدفع
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    user = db.relationship('User', backref=db.backref('subscription_payments', lazy=True))
    plan = db.relationship('SubscriptionPlan', backref=db.backref('payments', lazy=True))

    def __repr__(self):
        return f'<SubscriptionPayment {self.id} - {self.user.name} - {self.plan.name}>'

"""
نموذج الاتصال (Contact)
يخزن رسائل الاتصال المرسلة من صفحة اتصل بنا
"""
class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='new')  # new, read, replied
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Contact {self.name} - {self.subject}>'

"""
نموذج إعدادات النظام (SystemSettings)
يخزن الإعدادات العامة للنظام مثل اسم النظام واللغة والعملة وغيرها
"""
class SystemSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    group = db.Column(db.String(50), nullable=False)  # general, appearance, contact
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<SystemSettings {self.key}>'

    @staticmethod
    def get_setting(key, default=None):
        setting = SystemSettings.query.filter_by(key=key).first()
        return setting.value if setting else default

    @staticmethod
    def set_setting(key, value, group='general'):
        setting = SystemSettings.query.filter_by(key=key).first()
        if not setting:
            setting = SystemSettings(key=key, group=group)
        setting.value = value
        db.session.add(setting)
        try:
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            return False

"""
نموذج الأسئلة الشائعة (FAQ)
يخزن الأسئلة الشائعة وإجاباتها
"""
class FAQ(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(500), nullable=False)
    answer = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=True)  # تصنيف السؤال (تقني، مالي، أكاديمي، إلخ)
    order = db.Column(db.Integer, default=0)  # ترتيب ظهور السؤال
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<FAQ {self.question[:50]}...>'

"""
نموذج البث المباشر (LiveStream)
يخزن جلسات البث المباشر للمدرسين
"""
class LiveStream(db.Model):
    __tablename__ = 'live_stream'
    
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classroom.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stream_url = db.Column(db.String(500), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    ended_at = db.Column(db.DateTime, nullable=True)
    auto_end_at = db.Column(db.DateTime, nullable=True)  # Auto-end after 24 hours
    
    # Relationships
    classroom = db.relationship('Classroom', back_populates='live_streams')
    teacher = db.relationship('User', back_populates='live_streams')
    
    @property
    def is_expired(self):
        """Check if the stream has expired (24 hours passed)"""
        if self.auto_end_at and datetime.utcnow() > self.auto_end_at:
            return True
        return False
    
    @property
    def is_currently_active(self):
        """Check if the stream is currently active and not expired"""
        return self.is_active and not self.is_expired and not self.ended_at
    
    def end_stream(self):
        """Manually end the live stream"""
        self.is_active = False
        self.ended_at = datetime.utcnow()
        db.session.commit()
    
    def __repr__(self):
        return f'<LiveStream {self.title} - {self.classroom.name}>'


"""
نموذج البانرات الإعلانية (Banner)
يمثل البانرات الإعلانية التي تظهر في أعلى الصفحات
"""
class Banner(db.Model):
    __tablename__ = 'banner'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=False)
    link_url = db.Column(db.String(500), nullable=True)
    target_roles = db.Column(db.String(100), nullable=True)  # "student,teacher,admin" or "all"
    is_active = db.Column(db.Boolean, default=True)
    priority = db.Column(db.Integer, default=0)  # أولوية العرض
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    click_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    creator = db.relationship('User', backref='created_banners')
    
    def is_valid_for_user(self, user_role):
        """Check if banner is valid for user role"""
        if not self.is_active:
            return False
            
        # Check date range
        now = datetime.utcnow()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
            
        # Check role targeting
        if not self.target_roles or self.target_roles == 'all':
            return True
            
        target_roles = [role.strip() for role in self.target_roles.split(',')]
        return user_role in target_roles
    
    def increment_click(self):
        """Increment click counter"""
        self.click_count += 1
        db.session.commit()
    
    def __repr__(self):
        return f'<Banner {self.title}>'
