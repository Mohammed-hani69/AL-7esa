
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
