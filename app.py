"""
منصة الحصة التعليمية - ملف التطبيق الرئيسي
يحتوي على إعداد تطبيق Flask وتكوين المسارات الأساسية
"""

import os
import logging
from datetime import datetime

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager
from flask_socketio import SocketIO
from config import Config

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy
db = SQLAlchemy(model_class=Base)

# Create Flask app
app = Flask(__name__)
app.config.from_object(Config)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialize database
db.init_app(app)

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Add global context processor for datetime
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

# Add custom Jinja filters
@app.template_filter('slice')
def slice_filter(value, start, end):
    return value[start:end]

@app.template_filter('nl2br')
def nl2br_filter(value):
    if not value:
        return ''
    return value.replace('\n', '<br>')

@app.template_filter('format_math')
def format_math_filter(value):
    if not value:
        return ''
    # Remove unnecessary line breaks between mathematical expressions
    value = value.replace('= \n', '=')
    value = value.replace('\n+', '+')
    value = value.replace('\n=', '=')
    value = value.replace('\n​', '')  # Remove zero-width spaces
    value = value.replace('​\n', '')
    # Preserve intended line breaks
    value = value.replace('\n\n', '<br><br>')
    value = value.replace('\n', ' ')
    return value

# Configure login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'الرجاء تسجيل الدخول للوصول إلى هذه الصفحة'
login_manager.login_message_category = 'info'

# Import models (after db initialization)
from models import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create upload directories
def create_upload_directories():
    upload_dirs = [
        'static/uploads',
        'static/uploads/classroom_content',
        'static/uploads/profile_pictures',
        'static/uploads/chat_images',
    ]
    
    for directory in upload_dirs:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created directory: {directory}")

# Create upload directories
create_upload_directories()

# Route for favicon
@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('img/favicon.ico')

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# Import and register blueprints
from routes import main_bp
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.teacher import teacher_bp
from routes.student import student_bp
from routes.assistant import assistant_bp

# Register blueprints
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(teacher_bp, url_prefix='/teacher')
app.register_blueprint(student_bp, url_prefix='/student')
app.register_blueprint(assistant_bp, url_prefix='/assistant')

# Create tables
with app.app_context():
    db.create_all()

# Import socket events
from streaming import *

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(error):
    app.logger.error(f"Server Error: {error}")
    # عند حدوث استثناء في جينجا بسبب تعريف كتلة مكررة
    if "block 'content' defined twice" in str(error):
        return render_template('500.html', error="حدث خطأ في قوالب الموقع. يرجى المحاولة مرة أخرى أو الاتصال بمسؤول النظام."), 500
    return render_template('500.html', error=str(error)), 500