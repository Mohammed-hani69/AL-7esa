# Educational Platform with Firebase Integration | منصة تعليمية مع دمج Firebase

## Project Overview | نظرة عامة على المشروع

This is an educational platform built with Flask and Firebase integration that enables interactive learning between teachers and students.

هذه منصة تعليمية مبنية باستخدام Flask مع دمج Firebase تتيح التعلم التفاعلي بين المعلمين والطلاب.

## Features | المميزات

- User Authentication (Firebase & Google OAuth) | تسجيل الدخول (Firebase و Google OAuth)
- Real-time Streaming | البث المباشر
- Classroom Management | إدارة الفصول الدراسية
- Student-Teacher Interaction | التفاعل بين الطلاب والمعلمين
- Admin Dashboard | لوحة تحكم المسؤول
- File Upload System | نظام رفع الملفات
- Chat System | نظام المحادثة
- **Attendance Management System | نظام إدارة الحضور والغياب**
- **Student Contact Information | معلومات الاتصال بالطلاب**
- **Parent Phone Validation | التحقق من رقم هاتف ولي الأمر**
- **Teacher-Parent Communication | التواصل بين المعلم وولي الأمر**

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
- Create a `.env` file with your Firebase credentials (see `.env` example)
- قم بإنشاء ملف `.env` مع بيانات اعتماد Firebase الخاصة بك (انظر مثال `.env`)
- Optionally, add Firebase Admin SDK service account for server-side operations
- اختيارياً، أضف ملف خدمة Firebase Admin SDK للعمليات من جانب الخادم

4. For future changes:
```bash
git add .
git commit -m "update to v 1.1.4 تحسينات جديدة ومميزات إضافية"
git push origin main
```

5. Run the application | تشغيل التطبيق
```bash
python app.py
```

## Environment Variables | متغيرات البيئة

Create a `.env` file with the following variables | قم بإنشاء ملف `.env` بالمتغيرات التالية:

```
# Flask Configuration
FLASK_APP=app.py
FLASK_ENV=development
SESSION_SECRET=your-secret-key

# Database Configuration
DATABASE_URL=sqlite:///al-7esa.db

# Firebase Configuration
FIREBASE_API_KEY=your_api_key
FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
FIREBASE_PROJECT_ID=your_project_id
FIREBASE_STORAGE_BUCKET=your_project.appspot.com
FIREBASE_MESSAGING_SENDER_ID=your_sender_id
FIREBASE_APP_ID=your_app_id
FIREBASE_MEASUREMENT_ID=your_measurement_id
FIREBASE_DATABASE_URL=https://your_project-default-rtdb.firebaseio.com

# Firebase Admin SDK (Optional)
FIREBASE_SERVICE_ACCOUNT_PATH=path/to/service-account-key.json
FIREBASE_SERVER_KEY=your_server_key
```

## Firebase Setup | إعداد Firebase

### 1. Create Firebase Project | إنشاء مشروع Firebase
1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project | إنشاء مشروع جديد
3. Enable Authentication, Firestore, and Realtime Database | تفعيل المصادقة و Firestore وقاعدة البيانات المباشرة

### 2. Get Configuration | الحصول على التكوين
1. Go to Project Settings > General | اذهب إلى إعدادات المشروع > عام
2. Add a web app | أضف تطبيق ويب
3. Copy the configuration values to your `.env` file | انسخ قيم التكوين إلى ملف `.env`

### 3. Set up Firestore Rules | إعداد قواعد Firestore
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Allow read/write access to classroom messages for authenticated users
    match /classrooms/{classroomId}/messages/{messageId} {
      allow read, write: if request.auth != null;
    }

    // Allow read/write access to presence for authenticated users
    match /classrooms/{classroomId}/presence/{userId} {
      allow read, write: if request.auth != null;
    }
  }
}
```

### 4. Test Firebase Connection | اختبار اتصال Firebase
Visit `/test-firestore` route to test the Firebase connection | زر مسار `/test-firestore` لاختبار اتصال Firebase

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
