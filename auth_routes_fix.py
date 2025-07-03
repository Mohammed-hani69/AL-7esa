"""
ملف إصلاح مؤقت لمسارات المصادقة
يزيل Rate Limiting من مسارات تسجيل الدخول والتسجيل
"""

def fix_auth_routes():
    """إصلاح مسارات المصادقة لتعمل بدون Rate Limiting"""
    # هذا الملف يحتوي على النسخة المبسطة للمسارات
    # يمكن استخدامه مؤقتاً إذا استمرت المشكلة
    pass

AUTH_ROUTES_SIMPLE = {
    'login': """
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'POST' and form.validate_on_submit():
        user = User.query.filter_by(phone=form.phone.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        else:
            flash('فشل تسجيل الدخول. الرجاء التحقق من رقم الهاتف وكلمة المرور', 'danger')

    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    firebase_api_key = os.environ.get("FIREBASE_API_KEY", "")
    firebase_project_id = os.environ.get("FIREBASE_PROJECT_ID", "")
    firebase_app_id = os.environ.get("FIREBASE_APP_ID", "")

    template = 'auth/auth-mobile/login.html' if is_mobile() else 'auth/login.html'
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')

    return render_template(template,
                          form=form,
                          primary_color=primary_color,
                          secondary_color=secondary_color,
                          firebase_api_key=firebase_api_key,
                          firebase_project_id=firebase_project_id,
                          firebase_app_id=firebase_app_id)
""",
    'register': """
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        password = request.form.get('password')
        role = request.form.get('role')

        if role not in [Role.STUDENT, Role.TEACHER, Role.ASSISTANT]:
            flash('دور المستخدم غير صالح', 'danger')
            return redirect(url_for('auth.register'))

        existing_user = User.query.filter_by(phone=phone).first()
        if existing_user:
            flash('رقم الهاتف مسجل بالفعل', 'danger')
            return redirect(url_for('auth.register'))

        new_user = User(name=name, phone=phone, role=role)
        new_user.set_password(password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('تم إنشاء الحساب بنجاح. يمكنك الآن تسجيل الدخول', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash('حدث خطأ أثناء إنشاء الحساب. يرجى المحاولة مرة أخرى', 'danger')

    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    firebase_api_key = os.environ.get("FIREBASE_API_KEY", "")
    firebase_project_id = os.environ.get("FIREBASE_PROJECT_ID", "")
    firebase_app_id = os.environ.get("FIREBASE_APP_ID", "")

    template = 'auth/auth-mobile/register.html' if is_mobile() else 'auth/register.html'
    primary_color = SystemSettings.get_setting('primary_color', '#3498db')
    secondary_color = SystemSettings.get_setting('secondary_color', '#2ecc71')

    return render_template(template,
                          primary_color=primary_color,
                          secondary_color=secondary_color,
                          firebase_api_key=firebase_api_key,
                          firebase_project_id=firebase_project_id,
                          firebase_app_id=firebase_app_id)
"""
}

if __name__ == "__main__":
    print("ملف مساعد لإصلاح مسارات المصادقة")
    print("يحتوي على نسخ مبسطة بدون Rate Limiting")
