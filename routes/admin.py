from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app import db
from models import User, Role, SubscriptionPlan, Subscription, Classroom, Notification, Payment

admin_bp = Blueprint('admin', __name__)

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != Role.ADMIN:
            flash('غير مصرح لك بالوصول إلى هذه الصفحة', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

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
    
    # Get recent users
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    
    # Get recent payments
    recent_payments = Payment.query.order_by(Payment.created_at.desc()).limit(10).all()
    
    # Sample data for enrollment chart
    now = datetime.utcnow()
    enrollment_dates = [(now - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30, 0, -1)]
    enrollment_counts = [0] * 30  # Will be populated with actual data in a real implementation
    
    return render_template('admin/dashboard.html',
                           user_count=users_count,
                           teacher_count=teachers_count,
                           student_count=students_count,
                           classroom_count=classrooms_count,
                           subscription_count=active_subscriptions,
                           recent_users=recent_users,
                           recent_payments=recent_payments,
                           enrollment_dates=enrollment_dates,
                           enrollment_counts=enrollment_counts,
                           revenue=0)

@admin_bp.route('/users')
@login_required
@admin_required
def users():
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
    
    return render_template('admin/users.html', users=users)

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

@admin_bp.route('/subscriptions')
@login_required
@admin_required
def subscriptions():
    # Get subscription plans
    plans = SubscriptionPlan.query.all()
    
    # Get active subscriptions
    active_subs = Subscription.query.filter(Subscription.end_date > datetime.utcnow()).order_by(Subscription.start_date.desc()).all()
    
    # Get current time for template
    now = datetime.utcnow()
    
    return render_template('admin/subscriptions.html', plans=plans, active_subs=active_subs, now=now)

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
    
    return render_template('admin/notifications.html', notifications=recent_notifications)

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
    classrooms = query.order_by(Classroom.created_at.desc()).paginate(page=page, per_page=20)
    
    # Get all teachers for the filter dropdown
    teachers = User.query.filter_by(role=Role.TEACHER).all()
    
    return render_template('admin/classrooms.html', classrooms=classrooms, teachers=teachers, currency="ريال")

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

@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    # This would typically load settings from a database table
    # For now, we'll just show a form placeholder
    if request.method == 'POST':
        # Save settings to database
        flash('تم حفظ الإعدادات بنجاح', 'success')
        return redirect(url_for('admin.settings'))
    
    return render_template('admin/settings.html')
