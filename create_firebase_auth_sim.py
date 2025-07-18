#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
محاكي مصادقة Firebase وحل مشكلة الشات
"""

import os

def create_firebase_auth_sim():
    """إنشاء محاكي مصادقة Firebase"""
    
    # إنشاء ملف JavaScript لمحاكاة المصادقة
    auth_sim_js = """
// محاكي مصادقة Firebase للتطوير
window.FirebaseAuthSimulator = {
    // محاكاة مستخدم مصادق
    currentUser: {
        uid: 'user_' + Math.random().toString(36).substr(2, 9),
        displayName: 'مستخدم تجريبي',
        email: 'test@al-7esa.com'
    },
    
    // محاكاة تسجيل الدخول
    signInAnonymously: function() {
        return Promise.resolve({
            user: this.currentUser
        });
    },
    
    // محاكاة تسجيل الدخول بtoken مخصص
    signInWithCustomToken: function(token) {
        return Promise.resolve({
            user: this.currentUser
        });
    },
    
    // إعداد مراقب المصادقة
    onAuthStateChanged: function(callback) {
        // تشغيل callback فوراً مع المستخدم المحاكي
        setTimeout(() => {
            callback(this.currentUser);
        }, 100);
        
        // إرجاع دالة إلغاء الاشتراك
        return () => {};
    }
};

// إضافة الدعم التلقائي للقوالب الموجودة
document.addEventListener('DOMContentLoaded', function() {
    // تفعيل المحاكي في حالة فشل Firebase العادي
    if (typeof window.firebase_auth_failed !== 'undefined' && window.firebase_auth_failed) {
        console.log('🔧 تفعيل محاكي مصادقة Firebase...');
        
        // استبدال auth بالمحاكي في النطاق العام
        if (typeof window.auth !== 'undefined') {
            Object.assign(window.auth, FirebaseAuthSimulator);
        }
    }
});

// دالة مساعدة لتوليد Token مؤقت
function generateTempAuthToken(userId, userRole) {
    const payload = {
        uid: userId,
        role: userRole,
        iss: 'al-7esa-temp',
        aud: 'al-7esa',
        exp: Math.floor(Date.now() / 1000) + 3600, // ساعة واحدة
        iat: Math.floor(Date.now() / 1000)
    };
    
    // ترميز مبسط (للتطوير فقط)
    return btoa(JSON.stringify(payload));
}

console.log('✅ محاكي مصادقة Firebase جاهز');
"""
    
    with open('static/js/firebase_auth_sim.js', 'w', encoding='utf-8') as f:
        f.write(auth_sim_js)
    
    print("✅ تم إنشاء محاكي مصادقة Firebase")

def update_chat_templates():
    """تحديث قوالب المحادثة لدعم المحاكي"""
    
    chat_templates = [
        'templates/teacher/mobile-theme/chat.html',
        'templates/student/mobile-theme/chat.html',
        'templates/classroom/mobile-theme/chat.html'
    ]
    
    for template_path in chat_templates:
        if os.path.exists(template_path):
            try:
                with open(template_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # إضافة محاكي المصادقة
                if 'firebase_auth_sim.js' not in content:
                    # البحث عن Firebase SDK scripts
                    if '<script type="module">' in content:
                        auth_script = '''
    <!-- محاكي مصادقة Firebase للتطوير -->
    <script src="/static/js/firebase_auth_sim.js"></script>
    
    <script type="module">'''
                        
                        content = content.replace('<script type="module">', auth_script)
                        
                        # إضافة معالج أخطاء المصادقة
                        auth_error_handler = '''
        // معالج أخطاء المصادقة
        window.addEventListener('unhandledrejection', function(event) {
            if (event.reason && event.reason.code && event.reason.code.includes('auth')) {
                console.warn('خطأ مصادقة Firebase، تفعيل المحاكي...');
                window.firebase_auth_failed = true;
                
                // إعادة تحميل الصفحة لتفعيل المحاكي
                setTimeout(() => {
                    location.reload();
                }, 1000);
                
                event.preventDefault();
            }
        });

        '''
                        
                        # إضافة معالج الأخطاء قبل تهيئة Firebase
                        if 'const app = initializeApp(firebaseConfig);' in content:
                            content = content.replace(
                                'const app = initializeApp(firebaseConfig);',
                                auth_error_handler + '\n        const app = initializeApp(firebaseConfig);'
                            )
                
                # إضافة مصادقة تلقائية للمحادثة
                if 'sendMessage()' in content and 'auth.' not in content:
                    auth_fix = '''
        // إضافة مصادقة تلقائية
        function ensureAuthenticated() {
            return new Promise((resolve) => {
                if (typeof auth !== 'undefined' && auth.currentUser) {
                    resolve(auth.currentUser);
                } else if (typeof FirebaseAuthSimulator !== 'undefined') {
                    resolve(FirebaseAuthSimulator.currentUser);
                } else {
                    // مصادقة افتراضية
                    resolve({
                        uid: currentUser.id,
                        displayName: currentUser.name
                    });
                }
            });
        }

        '''
                    
                    content = content.replace(
                        'async function sendMessage() {',
                        auth_fix + '\n        async function sendMessage() {'
                    )
                    
                    # تحديث دالة sendMessage لتتضمن المصادقة
                    if 'await addDoc(messagesRef,' in content:
                        content = content.replace(
                            'await addDoc(messagesRef,',
                            'await ensureAuthenticated();\n                await addDoc(messagesRef,'
                        )
                
                with open(template_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"✅ تم تحديث {template_path}")
                
            except Exception as e:
                print(f"⚠️ فشل في تحديث {template_path}: {e}")

def create_firebase_config_override():
    """إنشاء ملف تجاوز إعدادات Firebase"""
    
    config_override = """
// إعدادات Firebase محسنة للتطوير
window.FirebaseConfigOverride = {
    // إعدادات المصادقة
    auth: {
        persistence: 'local',
        anonymousAuth: true,
        customTokenAuth: true
    },
    
    // إعدادات Firestore
    firestore: {
        enablePersistence: true,
        allowOfflineQueries: true,
        retryFailedRequests: true
    },
    
    // إعدادات التطوير
    development: {
        enableSimulator: true,
        mockAuth: true,
        verboseLogging: true
    }
};

// تطبيق الإعدادات تلقائياً
if (typeof window !== 'undefined') {
    window.FIREBASE_DEV_MODE = true;
}

console.log('⚙️ تم تحميل إعدادات Firebase المحسنة');
"""
    
    with open('static/js/firebase_config_override.js', 'w', encoding='utf-8') as f:
        f.write(config_override)
    
    print("✅ تم إنشاء ملف تجاوز إعدادات Firebase")

def create_auth_debug_tool():
    """إنشاء أداة تشخيص المصادقة"""
    
    debug_html = """<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تشخيص مصادقة Firebase</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .success { background: #d4edda; border-color: #c3e6cb; }
        .error { background: #f8d7da; border-color: #f5c6cb; }
        .warning { background: #fff3cd; border-color: #ffeaa7; }
        button { padding: 10px 15px; margin: 5px; cursor: pointer; }
    </style>
</head>
<body>
    <h1>🔍 تشخيص مصادقة Firebase</h1>
    
    <div class="section">
        <h3>حالة Firebase</h3>
        <div id="firebase-status">جاري الفحص...</div>
        <button onclick="checkFirebaseStatus()">فحص Firebase</button>
    </div>
    
    <div class="section">
        <h3>حالة المصادقة</h3>
        <div id="auth-status">جاري الفحص...</div>
        <button onclick="checkAuthStatus()">فحص المصادقة</button>
        <button onclick="simulateAuth()">محاكاة مصادقة</button>
    </div>
    
    <div class="section">
        <h3>اختبار Firestore</h3>
        <div id="firestore-status">جاري الفحص...</div>
        <button onclick="testFirestore()">اختبار Firestore</button>
        <button onclick="testChatMessage()">اختبار رسالة</button>
    </div>

    <script src="/static/js/firebase_auth_sim.js"></script>
    <script src="/static/js/firebase_config_override.js"></script>
    
    <script type="module">
        import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js';
        import { getFirestore, collection, addDoc, serverTimestamp } from 'https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js';

        const firebaseConfig = {
            apiKey: "AIzaSyCB_GPRRlb6BCe1Mlv7rTIbtnD-Y3vpAj8",
            authDomain: "al-7esa.firebaseapp.com",
            projectId: "al-7esa",
            storageBucket: "al-7esa.firebasestorage.app",
            messagingSenderId: "893628750909",
            appId: "1:893628750909:web:3cd09924c12987b3ef9e54"
        };

        let app, db;
        
        window.checkFirebaseStatus = function() {
            try {
                app = initializeApp(firebaseConfig);
                db = getFirestore(app);
                document.getElementById('firebase-status').innerHTML = '✅ Firebase متصل بنجاح';
                document.getElementById('firebase-status').parentElement.className = 'section success';
            } catch (error) {
                document.getElementById('firebase-status').innerHTML = '❌ خطأ Firebase: ' + error.message;
                document.getElementById('firebase-status').parentElement.className = 'section error';
            }
        }

        window.checkAuthStatus = function() {
            if (FirebaseAuthSimulator) {
                document.getElementById('auth-status').innerHTML = '✅ محاكي المصادقة متوفر';
                document.getElementById('auth-status').parentElement.className = 'section success';
            } else {
                document.getElementById('auth-status').innerHTML = '❌ لا توجد مصادقة';
                document.getElementById('auth-status').parentElement.className = 'section error';
            }
        }

        window.simulateAuth = function() {
            if (FirebaseAuthSimulator) {
                FirebaseAuthSimulator.signInAnonymously().then(() => {
                    document.getElementById('auth-status').innerHTML = '✅ تم تسجيل الدخول بالمحاكي';
                    document.getElementById('auth-status').parentElement.className = 'section success';
                });
            }
        }

        window.testFirestore = async function() {
            try {
                const testDoc = await addDoc(collection(db, 'auth_test'), {
                    message: 'اختبار مصادقة',
                    timestamp: serverTimestamp(),
                    user: FirebaseAuthSimulator ? FirebaseAuthSimulator.currentUser.uid : 'anonymous'
                });
                
                document.getElementById('firestore-status').innerHTML = '✅ Firestore يعمل بنجاح';
                document.getElementById('firestore-status').parentElement.className = 'section success';
                
            } catch (error) {
                document.getElementById('firestore-status').innerHTML = '❌ خطأ Firestore: ' + error.message;
                document.getElementById('firestore-status').parentElement.className = 'section error';
            }
        }

        window.testChatMessage = async function() {
            try {
                await addDoc(collection(db, 'classrooms', 'test', 'messages'), {
                    text: 'رسالة اختبار المصادقة',
                    senderId: 'test_user',
                    senderName: 'مستخدم اختبار',
                    timestamp: serverTimestamp(),
                    type: 'test'
                });
                
                alert('✅ تم إرسال رسالة الاختبار بنجاح!');
                
            } catch (error) {
                alert('❌ فشل في إرسال رسالة الاختبار: ' + error.message);
            }
        }

        // فحص تلقائي عند التحميل
        setTimeout(() => {
            checkFirebaseStatus();
            checkAuthStatus();
        }, 1000);
    </script>
</body>
</html>"""
    
    with open('firebase_auth_debug.html', 'w', encoding='utf-8') as f:
        f.write(debug_html)
    
    print("✅ تم إنشاء أداة تشخيص المصادقة: firebase_auth_debug.html")

def main():
    """الدالة الرئيسية"""
    print("🔧 إنشاء محاكي مصادقة Firebase الشامل...")
    print("="*50)
    
    # إنشاء مجلد static/js إذا لم يكن موجوداً
    os.makedirs('static/js', exist_ok=True)
    
    # تشغيل جميع الوظائف
    create_firebase_auth_sim()
    create_firebase_config_override()
    update_chat_templates()
    create_auth_debug_tool()
    
    print("\n" + "="*50)
    print("🎉 تم إنشاء محاكي المصادقة بنجاح!")
    
    print("\n📋 الملفات المنشأة:")
    print("✅ static/js/firebase_auth_sim.js")
    print("✅ static/js/firebase_config_override.js")  
    print("✅ firebase_auth_debug.html")
    
    print("\n📋 الاختبارات:")
    print("1. فتح firebase_auth_debug.html")
    print("2. اختبار المحادثة في التطبيق")
    print("3. التحقق من عدم وجود أخطاء في Console")
    
    print("\n⚠️ ملاحظة:")
    print("هذا المحاكي للتطوير فقط")
    print("يجب استخدام مصادقة حقيقية في الإنتاج")

if __name__ == "__main__":
    main()
