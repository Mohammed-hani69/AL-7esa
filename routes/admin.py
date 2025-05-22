from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app import db
from models import User, Role, SubscriptionPlan, Subscription, Classroom, Notification, Payment, SystemSettings, SubscriptionPayment
import re
from flask_wtf.csrf import CSRFProtect

admin_bp = Blueprint('admin', __name__)


# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != Role.ADMIN:
            flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

# دالة للتحقق من نوع الجهاز (موبايل أو جهاز مكتبي)
def is_mobile():
    user_agent = request.headers.get('User-Agent', '').lower()
    mobile_patterns = [
        'android', 'iphone', 'ipod', 'windows phone', 'mobile', 'tablet',
        'blackberry', 'opera mini', 'opera mobi', 'webos', 'fennec'
    ]
    return any(pattern in user_agent for pattern in mobile_patterns)

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # Get counts for dashboard statistics
    users_count = User.query.count()
    teachers_count = User.query.filter_by(role=Role.TEACHER).count()
    students_count = User.query.filter_by(role=Role.STUDENT).count()
    classrooms_count = Classroom.query.count()
    active_subscriptions = Subscription.query.filter(Subscription.end_date > datetime.utcnow()).count()

    # Calculate monthly revenue from subscription payments only
    start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_of_month = (start_of_month + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)

    # Get all approved subscription payments for current month
    monthly_revenue = db.session.query(db.func.sum(SubscriptionPayment.amount))\
        .filter(SubscriptionPayment.created_at.between(start_of_month, end_of_month))\
        .filter(SubscriptionPayment.status == 'approved')\
        .scalar() or 0

    # Get recent users
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()

    # Sample data for enrollment chart
    now = datetime.utcnow()
    enrollment_dates = [(now - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30, 0, -1)]
    enrollment_counts = [0] * 30  # Will be populated with actual data in a real implementation

    template = 'admin/admin-mobile/dashboard.html' if is_mobile() else 'admin/dashboard.html'

    return render_template(template,
                        user_count=users_count,
                        teacher_count=teachers_count,
                        student_count=students_count,
                        classroom_count=classrooms_count,
                        subscription_count=active_subscriptions,
                        recent_users=recent_users,
                        enrollment_dates=enrollment_dates,
                        enrollment_counts=enrollment_counts,
                        revenue=monthly_revenue)

@admin_bp.route('/users', methods=['GET', 'POST'])
@login_required
@admin_required
def users():
    # إذا كان طلب POST، فقم بمعالجة تحديث أو إضافة المستخدم
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update':
            user_id = request.form.get('user_id', type=int)
            if user_id:
                user = User.query.get_or_404(user_id)
                user.name = request.form.get('name')
                user.email = request.form.get('email')
                user.phone = request.form.get('phone')
                user.role = request.form.get('role')

                db.session.commit()
                flash('تم تحديث بيانات المستخدم بنجاح', 'success')
                return redirect(url_for('admin.users'))

        elif action == 'add':
            # إضافة مستخدم جديد
            from werkzeug.security import generate_password_hash

            name = request.form.get('name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            role = request.form.get('role')
            password = request.form.get('password')

            # التحقق من البريد الإلكتروني
            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                flash('البريد الإلكتروني مسجل بالفعل', 'danger')
                return redirect(url_for('admin.users'))

            # إنشاء مستخدم جديد
            new_user = User(
                name=name,
                email=email,
                phone=phone,
                role=role,
                password=generate_password_hash(password),
                is_active=True
            )

            db.session.add(new_user)
            db.session.commit()

            flash('تمت إضافة المستخدم بنجاح', 'success')
            return redirect(url_for('admin.users'))

    # Get filter parameters
    role_filter = request.args.get('role', '')
    status_filter = request.args.get('status', '')
    search = request.args.get('search', '')

    # Base query
    query = User.query

    # Apply filters
    if role_filter and role_filter in [Role.STUDENT, Role.TEACHER, Role.ASSISTANT, Role.ADMIN]:
        query = query.filter_by(role=role_filter)

    if status_filter:
        if status_filter == 'active':
            query = query.filter_by(is_active=True)
        elif status_filter == 'inactive':
            query = query.filter_by(is_active=False)

    if search:
        query = query.filter(
            (User.name.ilike(f'%{search}%')) | 
            (User.phone.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%'))
        )

    # Get paginated results
    page = request.args.get('page', 1, type=int)
    users = query.order_by(User.created_at.desc()).paginate(page=page, per_page=20)

    template = 'admin/admin-mobile/users.html' if is_mobile() else 'admin/users.html'
    
    # Add current time for template filters
    from datetime import datetime

    return render_template(template, users=users, role=role_filter, status=status_filter, search=search, current_time=datetime.now())

@admin_bp.route('/user/<int:user_id>/toggle_status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)

    # Don't allow deactivating the current admin
    if user.id == current_user.id:
        flash('لا يمكنك تعطيل حسابك الخاص', 'danger')
        return redirect(url_for('admin.users'))

    user.is_active = not user.is_active
    db.session.commit()

    status = "تفعيل" if user.is_active else "تعطيل"
    flash(f'تم {status} المستخدم بنجاح', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/user/<int:user_id>/reset_password', methods=['POST'])
@login_required
@admin_required
def reset_user_password(user_id):
    user = User.query.get_or_404(user_id)

    # إعادة تعيين كلمة المرور (مثال: كلمة مرور عشوائية أو كلمة مرور افتراضية)
    # يمكنك تغيير كلمة المرور حسب احتياجاتك
    default_password = "Password123"

    # في حالة استخدام bcrypt
    from werkzeug.security import generate_password_hash
    user.password = generate_password_hash(default_password)

    db.session.commit()

    flash(f'تم إعادة تعيين كلمة المرور للمستخدم {user.name} بنجاح', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/subscriptions')
@login_required
@admin_required
def subscriptions():
    # Get filter parameters
    status = request.args.get('status', '')
    plan_id = request.args.get('plan_id', type=int)
    search = request.args.get('search', '')
    
    # Get subscription plans
    plans = SubscriptionPlan.query.all()

    # Get active subscriptions
    active_subs = Subscription.query.filter(Subscription.end_date > datetime.utcnow()).order_by(Subscription.start_date.desc()).all()

    # Get all subscriptions for the comprehensive table with pagination
    page = request.args.get('page', 1, type=int)
    subscriptions = Subscription.query.order_by(Subscription.start_date.desc()).paginate(page=page, per_page=10)

    # Get all subscription payments
    payments = SubscriptionPayment.query.order_by(SubscriptionPayment.created_at.desc()).all()

    # حساب إجمالي الإيرادات
    total_revenue = 0
    if payments:
        for payment in payments:
            if payment.status == 'approved' and payment.amount:
                total_revenue += payment.amount

    # Calculate monthly revenue
    start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_of_month = (start_of_month + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)

    # Get all approved subscription payments for current month
    month_revenue = db.session.query(db.func.sum(SubscriptionPayment.amount))\
        .filter(SubscriptionPayment.created_at.between(start_of_month, end_of_month))\
        .filter(SubscriptionPayment.status == 'approved')\
        .scalar() or 0

    # Get current time for template
    now = datetime.utcnow()
    current_time = now  # نسخة من الوقت الحالي لاستخدامها في القالب

    # قم بحساب عدد المدفوعات قيد الانتظار
    pending_payments = SubscriptionPayment.query.filter_by(status='pending').count()

    template = 'admin/admin-mobile/subscriptions.html' if is_mobile() else 'admin/subscriptions.html'

    return render_template(template, 
                         plans=plans, 
                         active_subs=active_subs, 
                         subscriptions=subscriptions, 
                         all_subscriptions=Subscription.query.order_by(Subscription.start_date.desc()).all(),
                         payments=payments,
                         now=now,
                         current_time=now,  # إضافة متغير current_time ليكون متاحًا في القالب
                         total_revenue=total_revenue,
                         month_revenue=month_revenue,
                         pending_payments=pending_payments,
                         subscription_plans=plans,
                         status=status,
                         plan_id=plan_id,
                         search=search)

@admin_bp.route('/subscription_plan/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_subscription_plan():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price', 0))
        duration_days = int(request.form.get('duration_days', 30))
        max_classrooms = int(request.form.get('max_classrooms', 1))
        has_chat = 'has_chat' in request.form
        allow_assistant = 'allow_assistant' in request.form
        advanced_analytics = 'advanced_analytics' in request.form

        new_plan = SubscriptionPlan(
            name=name,
            description=description,
            price=price,
            duration_days=duration_days,
            max_classrooms=max_classrooms,
            has_chat=has_chat,
            allow_assistant=allow_assistant,
            advanced_analytics=advanced_analytics
        )

        db.session.add(new_plan)
        db.session.commit()

        flash('تم إنشاء باقة الاشتراك بنجاح', 'success')
        return redirect(url_for('admin.subscriptions'))

    return render_template('admin/edit_subscription_plan.html')

@admin_bp.route('/subscription_plan/<int:plan_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_subscription_plan(plan_id):
    plan = SubscriptionPlan.query.get_or_404(plan_id)

    if request.method == 'POST':
        plan.name = request.form.get('name')
        plan.description = request.form.get('description')
        plan.price = float(request.form.get('price', 0))
        plan.duration_days = int(request.form.get('duration_days', 30))
        plan.max_classrooms = int(request.form.get('max_classrooms', 1))
        plan.has_chat = 'has_chat' in request.form
        plan.allow_assistant = 'allow_assistant' in request.form
        plan.advanced_analytics = 'advanced_analytics' in request.form

        db.session.commit()

        flash('تم تحديث باقة الاشتراك بنجاح', 'success')
        return redirect(url_for('admin.subscriptions'))

    return render_template('admin/edit_subscription_plan.html', plan=plan)

@admin_bp.route('/subscription_plan/<int:plan_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_subscription_plan(plan_id):
    plan = SubscriptionPlan.query.get_or_404(plan_id)

    # Check if plan is in use
    if plan.subscriptions:
        flash('لا يمكن حذف الباقة لأن هناك مستخدمين مشتركين بها', 'danger')
        return redirect(url_for('admin.subscriptions'))

    db.session.delete(plan)
    db.session.commit()

    flash('تم حذف باقة الاشتراك بنجاح', 'success')
    return redirect(url_for('admin.subscriptions'))

@admin_bp.route('/subscription/<int:subscription_id>/cancel', methods=['GET'])
@login_required
@admin_required
def cancel_subscription(subscription_id):
    subscription = Subscription.query.get_or_404(subscription_id)

    # Set end date to now to effectively cancel the subscription
    subscription.end_date = datetime.utcnow()
    subscription.is_active = False
    db.session.commit()

    flash(f'تم إلغاء اشتراك {subscription.user.name} في باقة {subscription.plan.name} بنجاح', 'success')
    return redirect(url_for('admin.subscriptions'))

@admin_bp.route('/subscription/delete', methods=['POST'])
@login_required
@admin_required
def delete_subscription():
    subscription_id = request.form.get('subscription_id', type=int)
    if not subscription_id:
        flash('معرف الاشتراك غير صالح', 'danger')
        return redirect(url_for('admin.subscriptions'))

    subscription = Subscription.query.get_or_404(subscription_id)

    # Save the subscription info for flash message
    user_name = subscription.user.name
    plan_name = subscription.plan.name

    # Delete the subscription
    db.session.delete(subscription)
    db.session.commit()

    flash(f'تم حذف اشتراك {user_name} في باقة {plan_name} بنجاح', 'success')
    return redirect(url_for('admin.subscriptions'))

@admin_bp.route('/subscription/<int:subscription_id>/extend', methods=['POST'])
@login_required
@admin_required
def extend_subscription(subscription_id):
    subscription = Subscription.query.get_or_404(subscription_id)
    
    # الحصول على عدد الأيام المراد إضافتها من النموذج
    days = request.form.get('days', type=int, default=30)
    note = request.form.get('note', '')
    
    if days <= 0:
        flash('يجب أن يكون عدد الأيام أكبر من صفر', 'danger')
        return redirect(url_for('admin.subscriptions'))
    
    # إذا كان الاشتراك منتهي، يتم تعيين تاريخ البدء الجديد من الآن
    if subscription.end_date < datetime.utcnow():
        subscription.start_date = datetime.utcnow()
        subscription.end_date = datetime.utcnow() + timedelta(days=days)
    else:
        # إذا كان الاشتراك نشطًا، يتم إضافة الأيام إلى تاريخ الانتهاء الحالي
        subscription.end_date = subscription.end_date + timedelta(days=days)
    
    # تنشيط الاشتراك
    subscription.is_active = True
    
    # إضافة ملاحظة للإدارة (يمكن إضافة حقل في النموذج)
    # يمكن إضافة حقل notes في جدول الاشتراكات في المستقبل
    
    db.session.commit()
    
    flash(f'تم تمديد اشتراك {subscription.user.name} بنجاح لمدة {days} يوم', 'success')
    return redirect(url_for('admin.subscriptions'))

@admin_bp.route('/assign_trial/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def assign_trial(user_id):
    user = User.query.get_or_404(user_id)

    # Only assign trial to teachers
    if user.role != Role.TEACHER:
        flash('يمكن تعيين فترة تجريبية للمعلمين فقط', 'danger')
        return redirect(url_for('admin.users'))

    # Get the premium plan
    premium_plan = SubscriptionPlan.query.order_by(SubscriptionPlan.price.desc()).first()

    if not premium_plan:
        flash('لا توجد باقات اشتراك بعد', 'danger')
        return redirect(url_for('admin.subscriptions'))

    # Check if user already has an active subscription
    active_sub = Subscription.query.filter(
        Subscription.user_id == user.id,
        Subscription.end_date > datetime.utcnow()
    ).first()

    if active_sub:
        flash('المستخدم لديه اشتراك فعال بالفعل', 'warning')
        return redirect(url_for('admin.users'))

    # Create trial subscription
    trial_days = int(request.form.get('trial_days', 14))
    trial_subscription = Subscription(
        user_id=user.id,
        plan_id=premium_plan.id,
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=trial_days),
        is_active=True,
        is_trial=True
    )

    db.session.add(trial_subscription)
    db.session.commit()

    flash(f'تم تعيين فترة تجريبية لمدة {trial_days} يوم للمستخدم بنجاح', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/notifications')
@login_required
@admin_required
def notifications():
    # Get recent notifications
    recent_notifications = Notification.query.order_by(Notification.created_at.desc()).limit(50).all()

    # Get all users for the notification form
    users = User.query.order_by(User.name).all()

    # Get current time for template
    now = datetime.utcnow()

    template = 'admin/admin-mobile/notifications.html' if is_mobile() else 'admin/notifications.html'

    return render_template(template, notifications=recent_notifications, users=users, now=now)

@admin_bp.route('/send_notification', methods=['POST'])
@login_required
@admin_required
def send_notification():
    title = request.form.get('title')
    message = request.form.get('message')
    recipient_type = request.form.get('recipient_type')
    user_id = request.form.get('user_id')

    if not title or not message:
        flash('الرجاء إدخال العنوان والرسالة', 'danger')
        return redirect(url_for('admin.notifications'))

    notifications = []

    if recipient_type == 'all':
        # Send to all users
        users = User.query.all()
        for user in users:
            notification = Notification(
                user_id=user.id,
                title=title,
                message=message
            )
            notifications.append(notification)

    elif recipient_type == 'role':
        role = request.form.get('role')
        if role in [Role.STUDENT, Role.TEACHER, Role.ASSISTANT, Role.ADMIN]:
            # Send to users with specific role
            users = User.query.filter_by(role=role).all()
            for user in users:
                notification = Notification(
                    user_id=user.id,
                    title=title,
                    message=message
                )
                notifications.append(notification)

    elif recipient_type == 'user':
        # Send to specific user
        if user_id:
            user = User.query.get(user_id)
            if user:
                notification = Notification(
                    user_id=user.id,
                    title=title,
                    message=message
                )
                notifications.append(notification)

    elif recipient_type == 'phone':
        phone = request.form.get('phone')
        if phone:
            user = User.query.filter_by(phone=phone).first()
            if user:
                notification = Notification(
                    user_id=user.id,
                    title=title,
                    message=message
                )
                notifications.append(notification)

    if notifications:
        db.session.add_all(notifications)
        db.session.commit()
        flash(f'تم إرسال {len(notifications)} إشعار بنجاح', 'success')
    else:
        flash('لم يتم العثور على مستخدمين للإرسال إليهم', 'warning')

    return redirect(url_for('admin.notifications'))

@admin_bp.route('/classrooms')
@login_required
@admin_required
def classrooms():
    # Get filter parameters
    teacher_id = request.args.get('teacher_id', type=int)
    is_free = request.args.get('is_free')
    search = request.args.get('search', '')

    # Get counts for stats
    student_count = User.query.filter_by(role=Role.STUDENT).count()
    teacher_count = User.query.filter_by(role=Role.TEACHER).count()

    # Base query
    query = Classroom.query

    # Apply filters
    if teacher_id:
        query = query.filter_by(teacher_id=teacher_id)

    if is_free is not None:
        is_free_bool = (is_free == 'true')
        query = query.filter_by(is_free=is_free_bool)

    if search:
        query = query.filter(
            (Classroom.name.ilike(f'%{search}%')) | 
            (Classroom.code.ilike(f'%{search}%')) |
            (Classroom.subject.ilike(f'%{search}%'))
        )

    # Get paginated results
    page = request.args.get('page', 1, type=int)
    pagination = query.order_by(Classroom.created_at.desc()).paginate(page=page, per_page=20)
    classrooms = pagination

    # Get all teachers for the filter dropdown
    teachers = User.query.filter_by(role=Role.TEACHER).all()

    template = 'admin/admin-mobile/classrooms.html' if is_mobile() else 'admin/classrooms.html'

    return render_template(template, 
                         classrooms=classrooms,
                         teachers=teachers, 
                         currency="ريال",
                         pagination=pagination,
                         teacher_id=teacher_id or 0,  # توفير قيمة افتراضية
                         is_free=is_free,
                         search=search,
                         student_count=student_count,
                         teacher_count=teacher_count)

@admin_bp.route('/classroom/<int:classroom_id>/confirm_delete')
@login_required
@admin_required
def confirm_delete_classroom(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    return render_template('admin/delete_classroom_confirm.html', classroom=classroom)

@admin_bp.route('/classroom/delete', methods=['POST'])
@login_required
@admin_required
def delete_classroom():
    classroom_id = request.form.get('classroom_id', type=int)
    if not classroom_id:
        flash('معرف الفصل غير صالح', 'danger')
        return redirect(url_for('admin.classrooms'))

    classroom = Classroom.query.get_or_404(classroom_id)

    # Save the classroom name for the flash message
    classroom_name = classroom.name

    # Delete the classroom (will cascade delete all related records)
    db.session.delete(classroom)
    db.session.commit()

    flash(f'تم حذف الفصل "{classroom_name}" بنجاح', 'success')
    return redirect(url_for('admin.classrooms'))

@admin_bp.route('/classroom/<int:classroom_id>/view')
@login_required
@admin_required
def view_classroom(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)
    
    # Get students of this classroom
    students = classroom.students
    
    # Get assignments for this classroom
    assignments = classroom.assignments
    
    # Get quizzes for this classroom
    quizzes = classroom.quizzes if hasattr(classroom, 'quizzes') else []
    
    # Get teacher information
    teacher = classroom.teacher
    
    template = 'admin/view_classroom.html'
    
    return render_template(template, 
                           classroom=classroom,
                           students=students,
                           assignments=assignments,
                           quizzes=quizzes,
                           teacher=teacher)

@admin_bp.route('/classroom/<int:classroom_id>/toggle_status')
@login_required
@admin_required
def toggle_classroom_status(classroom_id):
    classroom = Classroom.query.get_or_404(classroom_id)

    classroom.is_active = not classroom.is_active
    db.session.commit()

    status = "تفعيل" if classroom.is_active else "تعطيل"
    flash(f'تم {status} الفصل بنجاح', 'success')
    return redirect(url_for('admin.classrooms'))

@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    if request.method == 'POST':
        # General settings
        settings_map = {
            'system_name': ('general', request.form.get('system_name')),
            'system_description': ('general', request.form.get('system_description')),
            'default_language': ('general', request.form.get('default_language')),
            'default_currency': ('general', request.form.get('default_currency')),
            'trial_days': ('general', request.form.get('trial_days')),
            'max_file_size': ('general', request.form.get('max_file_size')),

            # Appearance settings
            'primary_color': ('appearance', request.form.get('primary_color')),
            'secondary_color': ('appearance', request.form.get('secondary_color')),
            'logo_url': ('appearance', request.form.get('logo_url')),

            # Contact settings
            'contact_email': ('contact', request.form.get('contact_email')),
            'contact_phone': ('contact', request.form.get('contact_phone'))
        }

        # Save all settings
        success = True
        for key, (group, value) in settings_map.items():
            if not SystemSettings.set_setting(key, value, group):
                success = False

        if success:
            flash('تم حفظ الإعدادات بنجاح', 'success')
        else:
            flash('حدث خطأ أثناء حفظ الإعدادات', 'danger')

        return redirect(url_for('admin.settings'))

    # Load current settings
    settings = {
        'system_name': SystemSettings.get_setting('system_name', 'الحصة'),
        'system_description': SystemSettings.get_setting('system_description', 'منصة تعليمية متكاملة لإدارة العملية التعليمية بكفاءة'),
        'default_language': SystemSettings.get_setting('default_language', 'ar'),
        'default_currency': SystemSettings.get_setting('default_currency', 'SAR'),
        'trial_days': SystemSettings.get_setting('trial_days', '14'),
        'max_file_size': SystemSettings.get_setting('max_file_size', '16'),
        'primary_color': SystemSettings.get_setting('primary_color', '#4e73df'),
        'secondary_color': SystemSettings.get_setting('secondary_color', '#1cc88a'),
        'logo_url': SystemSettings.get_setting('logo_url', '/static/img/logo.png'),
        'contact_email': SystemSettings.get_setting('contact_email', 'support@alhesa.com'),
        'contact_phone': SystemSettings.get_setting('contact_phone', '+966 55 555 5555')
    }

    now = datetime.utcnow()

    template = 'admin/admin-mobile/settings.html' if is_mobile() else 'admin/settings.html'

    return render_template(template, settings=settings, now=now)