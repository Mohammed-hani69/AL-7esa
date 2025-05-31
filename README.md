# Educational Platform with Firebase Integration | منصة تعليمية مع دمج Firebase

## Project Overview | نظرة عامة على المشروع

This is an educational platform built with Flask and Firebase integration that enables interactive learning between teachers and students.

هذه منصة تعليمية مبنية باستخدام Flask مع دمج Firebase تتيح التعلم التفاعلي بين المعلمين والطلاب.

## Features | المميزات

- User Authentication (Firebase) | تسجيل الدخول (Firebase)
- Real-time Streaming | البث المباشر
- Classroom Management | إدارة الفصول الدراسية
- Student-Teacher Interaction | التفاعل بين الطلاب والمعلمين
- Admin Dashboard | لوحة تحكم المسؤول
- File Upload System | نظام رفع الملفات
- Chat System | نظام المحادثة

## Technologies Used | التقنيات المستخدمة

- Python/Flask | بايثون/فلاسك
- Firebase | فايربيس
- SQLAlchemy | SQLAlchemy
- Jinja2 Templates | قوالب Jinja2
- JavaScript | جافاسكريبت
- CSS | CSS

## Project Structure | هيكل المشروع

```
├── app.py                 # Main application file | الملف الرئيسي للتطبيق
├── config.py             # Configuration settings | إعدادات التكوين
├── models.py             # Database models | نماذج قاعدة البيانات
├── firebase_utils.py     # Firebase utilities | أدوات Firebase
├── streaming.py          # Streaming functionality | وظائف البث المباشر
├── routes/               # Application routes | مسارات التطبيق
├── static/              # Static files (CSS, JS) | الملفات الثابتة
├── templates/           # HTML templates | قوالب HTML
└── migrations/          # Database migrations | ترحيلات قاعدة البيانات
```

## Setup Instructions | تعليمات الإعداد

1. Clone the repository | نسخ المستودع
```bash
git clone [repository-url]
```

2. Install dependencies | تثبيت المتطلبات
```bash
pip install -r requirements.txt
```

3. Set up Firebase configuration | إعداد تكوين Firebase
- Configure `firebase_utils.py` with your Firebase credentials
- قم بتكوين `firebase_utils.py` مع بيانات اعتماد Firebase الخاصة بك

4. For future changes:
```bash
git add .
git commit -m "update to v 1.0.7 mobile theme"
git push origin main
```

5. Run the application | تشغيل التطبيق
```bash
python app.py
```

## Environment Variables | متغيرات البيئة

Create a `.env` file with the following variables | قم بإنشاء ملف `.env` بالمتغيرات التالية:

```
FLASK_APP=app.py
FLASK_ENV=development
DATABASE_URL=your_database_url
FIREBASE_CONFIG=your_firebase_config
```

## User Roles | أدوار المستخدمين

- Admin | المسؤول
- Teacher | المعلم
- Student | الطالب

Each role has specific permissions and access levels | لكل دور صلاحيات ومستويات وصول محددة

## Contributing | المساهمة

Contributions are welcome! Please feel free to submit a Pull Request.
المساهمات مرحب بها! لا تتردد في تقديم طلب سحب.

## License | الرخصة

This project is licensed under the MIT License - see the LICENSE file for details.
هذا المشروع مرخص تحت رخصة MIT - راجع ملف LICENSE للتفاصيل."# AL-7esa"
