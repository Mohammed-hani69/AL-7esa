# دليل إعداد Firebase للمنصة التعليمية

## نظرة عامة
تستخدم منصة الحصة التعليمية Firebase لتوفير:
- المصادقة (Authentication)
- قاعدة بيانات Firestore للرسائل والبيانات المنظمة
- قاعدة البيانات المباشرة (Realtime Database) للتحديثات الفورية
- التخزين السحابي (Cloud Storage)
- الإشعارات (Cloud Messaging)

## الخطوات المطلوبة

### 1. إنشاء مشروع Firebase
1. اذهب إلى [Firebase Console](https://console.firebase.google.com/)
2. انقر على "إنشاء مشروع" (Create Project)
3. أدخل اسم المشروع: `al-7esa`
4. اختر إعدادات Google Analytics (اختياري)
5. انقر على "إنشاء مشروع"

### 2. إعداد التطبيق
1. في لوحة تحكم المشروع، انقر على أيقونة الويب `</>`
2. أدخل اسم التطبيق: `AL-7esa Web App`
3. اختر "إعداد Firebase Hosting" (اختياري)
4. انقر على "تسجيل التطبيق"
5. انسخ كود التكوين

### 3. تفعيل الخدمات المطلوبة

#### أ. Authentication
1. اذهب إلى Authentication > Sign-in method
2. فعّل الطرق المطلوبة:
   - Phone (للمصادقة بالهاتف)
   - Anonymous (للمستخدمين المجهولين)
   - Email/Password (اختياري)

#### ب. Firestore Database
1. اذهب إلى Firestore Database
2. انقر على "إنشاء قاعدة بيانات"
3. اختر "البدء في وضع الاختبار" (Test mode)
4. اختر الموقع الجغرافي (يفضل أقرب منطقة)

#### ج. Realtime Database
1. اذهب إلى Realtime Database
2. انقر على "إنشاء قاعدة بيانات"
3. اختر "البدء في وضع الاختبار"
4. اختر الموقع الجغرافي

#### د. Cloud Storage
1. اذهب إلى Storage
2. انقر على "البدء"
3. اختر قواعد الأمان (يمكن تعديلها لاحقاً)

### 4. إعداد قواعد الأمان

#### قواعد Firestore
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // قواعد الفصول الدراسية
    match /classrooms/{classroomId} {
      // السماح بالقراءة للمستخدمين المصادق عليهم
      allow read: if request.auth != null;
      // السماح بالكتابة للمعلمين والمساعدين فقط
      allow write: if request.auth != null && 
        (resource.data.teacherId == request.auth.uid || 
         request.auth.uid in resource.data.assistants);
      
      // رسائل الفصل
      match /messages/{messageId} {
        allow read: if request.auth != null;
        allow create: if request.auth != null && 
          request.auth.uid == request.resource.data.userId;
        allow update, delete: if request.auth != null && 
          (request.auth.uid == resource.data.userId || 
           request.auth.uid in get(/databases/$(database)/documents/classrooms/$(classroomId)).data.moderators);
      }
      
      // حالة الحضور
      match /presence/{userId} {
        allow read: if request.auth != null;
        allow write: if request.auth != null && 
          request.auth.uid == userId;
      }
    }
    
    // بيانات المستخدمين
    match /users/{userId} {
      allow read, write: if request.auth != null && 
        request.auth.uid == userId;
    }
  }
}
```

#### قواعد Realtime Database
```json
{
  "rules": {
    "classrooms": {
      "$classroomId": {
        ".read": "auth != null",
        "messages": {
          ".write": "auth != null"
        },
        "presence": {
          "$userId": {
            ".write": "auth != null && auth.uid == $userId"
          }
        },
        "typing": {
          "$userId": {
            ".write": "auth != null && auth.uid == $userId"
          }
        }
      }
    }
  }
}
```

#### قواعد Cloud Storage
```javascript
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    // ملفات الفصول الدراسية
    match /classrooms/{classroomId}/{allPaths=**} {
      allow read: if request.auth != null;
      allow write: if request.auth != null && 
        request.resource.size < 50 * 1024 * 1024; // 50MB max
    }
    
    // صور الملفات الشخصية
    match /profile_pictures/{userId}/{allPaths=**} {
      allow read: if request.auth != null;
      allow write: if request.auth != null && 
        request.auth.uid == userId &&
        request.resource.size < 5 * 1024 * 1024; // 5MB max
    }
  }
}
```

### 5. الحصول على مفاتيح التكوين

#### من إعدادات المشروع
1. اذهب إلى Project Settings (⚙️)
2. في تبويب "General"، انزل إلى "Your apps"
3. انقر على تطبيق الويب الخاص بك
4. انسخ كود التكوين

#### مثال على التكوين
```javascript
const firebaseConfig = {
  apiKey: "AIzaSyCB_GPRRlb6BCe1Mlv7rTIbtnD-Y3vpAj8",
  authDomain: "al-7esa.firebaseapp.com",
  databaseURL: "https://al-7esa-default-rtdb.firebaseio.com",
  projectId: "al-7esa",
  storageBucket: "al-7esa.appspot.com",
  messagingSenderId: "893628750909",
  appId: "1:893628750909:web:3cd09924c12987b3ef9e54",
  measurementId: "G-B026ZL6KXG"
};
```

### 6. إعداد ملف .env
انسخ القيم من التكوين إلى ملف `.env`:

```env
FIREBASE_API_KEY=AIzaSyCB_GPRRlb6BCe1Mlv7rTIbtnD-Y3vpAj8
FIREBASE_AUTH_DOMAIN=al-7esa.firebaseapp.com
FIREBASE_PROJECT_ID=al-7esa
FIREBASE_STORAGE_BUCKET=al-7esa.appspot.com
FIREBASE_MESSAGING_SENDER_ID=893628750909
FIREBASE_APP_ID=1:893628750909:web:3cd09924c12987b3ef9e54
FIREBASE_MEASUREMENT_ID=G-B026ZL6KXG
FIREBASE_DATABASE_URL=https://al-7esa-default-rtdb.firebaseio.com
```

### 7. اختبار الإعداد
1. شغّل التطبيق: `python app.py`
2. اذهب إلى: `http://localhost:5000/test-firestore`
3. اختبر العمليات المختلفة:
   - تهيئة Firebase
   - إنشاء مستند
   - قراءة مستند
   - المصادقة
   - إرسال رسائل

### 8. إعداد Firebase Admin SDK (اختياري)
للعمليات المتقدمة من جانب الخادم:

1. اذهب إلى Project Settings > Service accounts
2. انقر على "Generate new private key"
3. احفظ الملف في مجلد المشروع
4. أضف المسار إلى `.env`:
```env
FIREBASE_SERVICE_ACCOUNT_PATH=path/to/service-account-key.json
```

## استكشاف الأخطاء

### مشاكل شائعة:
1. **خطأ في المصادقة**: تأكد من تفعيل طرق المصادقة المطلوبة
2. **خطأ في الصلاحيات**: راجع قواعد Firestore والـ Realtime Database
3. **خطأ في التكوين**: تأكد من صحة قيم `.env`
4. **مشاكل الشبكة**: تأكد من الاتصال بالإنترنت

### أدوات المراقبة:
- Firebase Console > Usage
- Browser Developer Tools > Console
- Network tab لمراقبة الطلبات

## الميزات المتقدمة

### 1. الإشعارات (FCM)
- إعداد Service Worker
- طلب إذن الإشعارات
- إرسال إشعارات مخصصة

### 2. التحليلات
- تفعيل Google Analytics
- تتبع الأحداث المخصصة
- تقارير الاستخدام

### 3. الأداء
- Firebase Performance Monitoring
- تحسين استعلامات Firestore
- استخدام الفهرسة المناسبة

## الأمان

### أفضل الممارسات:
1. استخدم قواعد أمان صارمة
2. لا تعرض مفاتيح API الحساسة
3. استخدم HTTPS دائماً
4. راقب الاستخدام بانتظام
5. حدّث Firebase SDK بانتظام

### مراجعة دورية:
- راجع قواعد الأمان شهرياً
- راقب سجلات الوصول
- تحقق من الاستخدام غير المعتاد
- حدّث كلمات المرور والمفاتيح

## الدعم والمساعدة

### الموارد:
- [Firebase Documentation](https://firebase.google.com/docs)
- [Firebase Console](https://console.firebase.google.com/)
- [Firebase Support](https://firebase.google.com/support)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/firebase)

### المجتمع:
- [Firebase Slack](https://firebase.community/)
- [Firebase Reddit](https://www.reddit.com/r/Firebase/)
- [Firebase YouTube](https://www.youtube.com/firebase)
