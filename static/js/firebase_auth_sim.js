
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
