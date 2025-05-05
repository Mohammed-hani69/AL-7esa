"""
منصة الحصة التعليمية - ملف التطبيق الرئيسي
يحتوي على إعداد تطبيق Flask وتكوين المسارات الأساسية
"""

import os
import logging
from datetime import datetime

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager
from flask_socketio import SocketIO

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy
db = SQLAlchemy(model_class=Base)

"""
إعداد تطبيق Flask
تكوين قاعدة البيانات وإعداد الجلسات ونظام المصادقة
"""

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "al-hesa-default-secret")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "mysql://root:@localhost/al-7esa")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

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

"""
تسجيل وحدات المسارات (Blueprints)
تنظيم مسارات التطبيق في وحدات منفصلة
"""

# Import and register blueprints
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.teacher import teacher_bp
from routes.student import student_bp
from routes.assistant import assistant_bp

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(teacher_bp, url_prefix='/teacher')
app.register_blueprint(student_bp, url_prefix='/student')
app.register_blueprint(assistant_bp, url_prefix='/assistant')

# Create tables
with app.app_context():
    db.create_all()

# Route for favicon
@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('img/favicon.ico')

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

"""
معالجة الأخطاء والاستثناءات
تعريف الصفحات المخصصة للأخطاء مثل 404 و500
"""

# Import routes 
from routes import *

# Import socket events
from streaming import *

# تشغيل التطبيق
if __name__ == '__main__':
    socketio.run(app, debug=True)
