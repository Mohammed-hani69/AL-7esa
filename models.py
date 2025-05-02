from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# User roles
class Role:
    STUDENT = 'student'
    TEACHER = 'teacher'
    ASSISTANT = 'assistant'
    ADMIN = 'admin'

# User model
class User(UserMixin, db.Model):
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
    firebase_uid = db.Column(db.String(100), unique=True, nullable=True)
    
    # Relationships
    classrooms = db.relationship('ClassroomEnrollment', back_populates='user')
    teacher_classrooms = db.relationship('Classroom', back_populates='teacher', foreign_keys='Classroom.teacher_id')
    assistant_classrooms = db.relationship('Classroom', back_populates='assistant', foreign_keys='Classroom.assistant_id')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
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

# Classroom model
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
    
    # Relationships
    teacher = db.relationship('User', back_populates='teacher_classrooms', foreign_keys=[teacher_id])
    assistant = db.relationship('User', back_populates='assistant_classrooms', foreign_keys=[assistant_id])
    enrollments = db.relationship('ClassroomEnrollment', back_populates='classroom', cascade='all, delete-orphan')
    contents = db.relationship('ClassroomContent', back_populates='classroom', cascade='all, delete-orphan')
    assignments = db.relationship('Assignment', back_populates='classroom', cascade='all, delete-orphan')
    quizzes = db.relationship('Quiz', back_populates='classroom', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Classroom {self.name}>'

# Classroom enrollments (student -> classroom)
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
    content = db.Column(db.Text, nullable=False)
    attachment_url = db.Column(db.String(255), nullable=True)
    submission_date = db.Column(db.DateTime, default=datetime.utcnow)
    grade = db.Column(db.Integer, nullable=True)
    feedback = db.Column(db.Text, nullable=True)
    
    # Relationships
    enrollment = db.relationship('ClassroomEnrollment', back_populates='assignment_submissions')
    assignment = db.relationship('Assignment', back_populates='submissions')
    
    def __repr__(self):
        return f'<AssignmentSubmission {self.enrollment.user.name} - {self.assignment.title}>'

# Quiz model
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

# Quiz question types
class QuestionType:
    MULTIPLE_CHOICE = 'multiple_choice'
    TRUE_FALSE = 'true_false'
    SHORT_ANSWER = 'short_answer'
    ESSAY = 'essay'

# Quiz question
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

# Quiz attempt
class QuizAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    enrollment_id = db.Column(db.Integer, db.ForeignKey('classroom_enrollment.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    score = db.Column(db.Integer, nullable=True)
    is_completed = db.Column(db.Boolean, default=False)
    
    # Relationships
    enrollment = db.relationship('ClassroomEnrollment', back_populates='quiz_attempts')
    quiz = db.relationship('Quiz', back_populates='attempts')
    answers = db.relationship('QuizAnswer', back_populates='attempt', cascade='all, delete-orphan')
    
    __table_args__ = (
        db.UniqueConstraint('enrollment_id', 'quiz_id', name='unique_quiz_attempt'),
    )
    
    def __repr__(self):
        return f'<QuizAttempt {self.enrollment.user.name} - {self.quiz.title}>'

# Quiz answer
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

# Chat message model
class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classroom.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)
    
    # Relationships
    classroom = db.relationship('Classroom', backref=db.backref('chat_messages', lazy=True))
    user = db.relationship('User', backref=db.backref('chat_messages', lazy=True))
    
    def __repr__(self):
        return f'<ChatMessage {self.id}>'

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
    
    # Relationships
    user = db.relationship('User', backref=db.backref('payments', lazy=True))
    classroom = db.relationship('Classroom', backref=db.backref('payments', lazy=True))
    subscription = db.relationship('Subscription', backref=db.backref('payment', lazy=True))
    
    def __repr__(self):
        return f'<Payment {self.id}>'
