"""
المسارات الرئيسية للتطبيق
"""

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app
from flask_login import current_user, login_required
from models import Role, SystemSettings, User, ClassroomEnrollment, Classroom, SubscriptionPlan, Contact, FAQ
from app import db

# تعريف المسارات الأساسية
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """الصفحة الرئيسية"""
    try:
        # الحصول على قيم الألوان من إعدادات النظام
        primary_color = SystemSettings.get_setting('primary_color')  # يمكن أن يكون اللون الافتراضي
        secondary_color = SystemSettings.get_setting('secondary_color')  # اللون الافتراضي

        # عرض الصفحة الرئيسية للزائر
        if not current_user.is_authenticated:
            featured_classrooms = Classroom.query.filter_by(is_free=True).limit(3).all()
            plans = SubscriptionPlan.query.all()
            return render_template('index.html', featured_classrooms=featured_classrooms, plans=plans, primary_color=primary_color, secondary_color=secondary_color)
        
        # توجيه المستخدم بناءً على دوره
        if current_user.role == Role.ADMIN:
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == Role.TEACHER:
            return redirect(url_for('teacher.dashboard'))
        elif current_user.role == Role.STUDENT:
            return redirect(url_for('student.dashboard'))
        elif current_user.role == Role.ASSISTANT:
            return redirect(url_for('assistant.dashboard'))
        
        # في حالة وجود خطأ في الدور
        return render_template('index.html', primary_color=primary_color, secondary_color=secondary_color)
    except Exception as e:
        current_app.logger.error(f"خطأ في الصفحة الرئيسية: {str(e)}")
        return render_template('index.html', primary_color=primary_color, secondary_color=secondary_color)
    


@main_bp.route('/about')
def about():
    """صفحة من نحن"""

    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color')  # يمكن أن يكون اللون الافتراضي
    secondary_color = SystemSettings.get_setting('secondary_color')  # اللون الافتراضي

    return render_template('about.html', primary_color=primary_color, secondary_color=secondary_color)




@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """صفحة اتصل بنا"""
    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color')
    secondary_color = SystemSettings.get_setting('secondary_color')

    if request.method == 'POST':
        try:
            # إنشاء نموذج اتصال جديد
            new_contact = Contact(
                name=request.form.get('name'),
                email=request.form.get('email'),
                phone=request.form.get('phone'),
                subject=request.form.get('subject'),
                message=request.form.get('message'),
                status='new'
            )
            
            # حفظ في قاعدة البيانات
            db.session.add(new_contact)
            db.session.commit()
            
            flash('تم إرسال رسالتك بنجاح! سنتواصل معك قريباً.', 'success')
            return redirect(url_for('main.contact'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"خطأ في حفظ نموذج الاتصال: {str(e)}")
            flash('عذراً، حدث خطأ أثناء إرسال الرسالة. يرجى المحاولة مرة أخرى.', 'error')
            return redirect(url_for('main.contact'))

    return render_template('contact.html', primary_color=primary_color, secondary_color=secondary_color)



@main_bp.route('/privacy')
def privacy():
    """صفحة سياسة الخصوصية"""
    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color')
    secondary_color = SystemSettings.get_setting('secondary_color')
    
    return render_template('privacy.html', 
                         primary_color=primary_color, 
                         secondary_color=secondary_color)

@main_bp.route('/faq')
def faq():
    """صفحة الأسئلة الشائعة"""
    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color')
    secondary_color = SystemSettings.get_setting('secondary_color')
    
    # جلب الأسئلة الشائعة المفعلة مرتبة حسب التصنيف والترتيب
    faqs = FAQ.query.filter_by(is_active=True).order_by(FAQ.category, FAQ.order).all()
    
    # تجميع الأسئلة حسب التصنيف
    faq_by_category = {}
    for faq in faqs:
        category = faq.category or 'عام'
        if category not in faq_by_category:
            faq_by_category[category] = []
        faq_by_category[category].append(faq)

    return render_template('faq.html', 
                         faq_by_category=faq_by_category,
                         primary_color=primary_color, 
                         secondary_color=secondary_color)

@main_bp.route('/support')
def support():
    """صفحة الدعم الفني"""
    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color')
    secondary_color = SystemSettings.get_setting('secondary_color')
    
    return render_template('support.html', 
                         primary_color=primary_color, 
                         secondary_color=secondary_color)

@main_bp.route('/terms')
def terms():
    """صفحة شروط الاستخدام"""
    # الحصول على قيم الألوان من إعدادات النظام
    primary_color = SystemSettings.get_setting('primary_color')
    secondary_color = SystemSettings.get_setting('secondary_color')
    
    return render_template('terms.html', 
                         primary_color=primary_color, 
                         secondary_color=secondary_color)
