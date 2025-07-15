/**
 * ==============================================
 * نظام الإشعارات والرسائل الموحد
 * Unified Notifications & Messages System
 * ==============================================
 */

// منع التحميل المتعدد للنظام
if (window.UnifiedNotificationSystem) {
    console.warn('UnifiedNotificationSystem already exists. Skipping redefinition.');
} else {

class UnifiedNotificationSystem {
    constructor() {
        this.container = null;
        this.flashContainer = null;
        this.notifications = new Map();
        this.defaultDuration = 5000;
        this.maxNotifications = 5;
        this.sounds = {
            success: null,
            warning: null,
            error: null,
            info: null
        };
        
        // إعدادات جديدة
        this.settings = {
            enableSounds: true,
            enableBrowserNotifications: true,
            enableVibration: true,
            rtlSupport: true,
            darkModeSupport: true,
            animationSpeed: 'normal', // fast, normal, slow
            position: 'top-left', // top-left, top-right, bottom-left, bottom-right
            mobileOptimized: true
        };
        
        // كاش للقوالب المحسنة
        this.templates = {
            toast: null,
            flash: null,
            notificationItem: null
        };
        
        this.init();
    }

    /**
     * تهيئة النظام
     */
    init() {
        this.createContainers();
        this.setupEventListeners();
        this.processExistingFlashMessages();
        this.enableNotificationPermissions();
    }

    /**
     * إنشاء الحاويات الأساسية
     */
    createContainers() {
        // حاوي الإشعارات المنبثقة
        if (!document.getElementById('notification-container')) {
            this.container = document.createElement('div');
            this.container.id = 'notification-container';
            this.container.className = 'notification-container';
            document.body.appendChild(this.container);
        } else {
            this.container = document.getElementById('notification-container');
        }

        // حاوي رسائل Flash
        if (!document.getElementById('flash-messages')) {
            this.flashContainer = document.createElement('div');
            this.flashContainer.id = 'flash-messages';
            this.flashContainer.className = 'flash-messages';
            document.body.appendChild(this.flashContainer);
        } else {
            this.flashContainer = document.getElementById('flash-messages');
        }
    }

    /**
     * إعداد مستمعي الأحداث
     */
    setupEventListeners() {
        // إغلاق الإشعارات عند النقر خارجها
        document.addEventListener('click', (e) => {
            const panels = document.querySelectorAll('.notifications-panel.show');
            panels.forEach(panel => {
                if (!panel.contains(e.target) && !e.target.closest('.notifications-toggle')) {
                    this.hideNotificationPanel(panel);
                }
            });
        });

        // مراقبة تغييرات DOM لمعالجة الإشعارات الجديدة
        const observer = new MutationObserver(() => {
            this.processExistingFlashMessages();
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        // معالجة الأخطاء العامة
        window.addEventListener('error', (event) => {
            console.error('JavaScript Error:', event.error);
        });
        
        // معالجة الأخطاء غير المعالجة في الـ Promises
        window.addEventListener('unhandledrejection', (event) => {
            console.error('Unhandled Promise Rejection:', event.reason);
        });
    }

    /**
     * معالجة رسائل Flash الموجودة في الصفحة
     */
    processExistingFlashMessages() {
        const existingAlerts = document.querySelectorAll('.alert:not(.processed)');
        existingAlerts.forEach(alert => {
            alert.classList.add('processed');
            const type = this.getAlertType(alert);
            const message = alert.textContent.trim();
            
            if (message) {
                this.showFlashMessage(message, type);
                alert.remove();
            }
        });
    }

    /**
     * تحديد نوع التنبيه من الكلاسات
     */
    getAlertType(alert) {
        if (alert.classList.contains('alert-success')) return 'success';
        if (alert.classList.contains('alert-warning')) return 'warning';
        if (alert.classList.contains('alert-danger') || alert.classList.contains('alert-error')) return 'error';
        if (alert.classList.contains('alert-info')) return 'info';
        return 'info';
    }

    /**
     * طلب إذن الإشعارات من المتصفح
     */
    async enableNotificationPermissions() {
        if ('Notification' in window && Notification.permission === 'default') {
            try {
                await Notification.requestPermission();
            } catch (error) {
                console.warn('Could not request notification permission:', error);
            }
        }
    }

    /**
     * عرض إشعار منبثق (Toast)
     */
    showToast(title, message, type = 'info', options = {}) {
        const id = 'toast_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        const duration = options.duration || this.defaultDuration;
        const persistent = options.persistent || false;
        const showProgress = options.showProgress !== false;

        // إزالة الإشعارات الزائدة
        this.limitNotifications();

        // إنشاء عنصر الإشعار
        const toast = this.createToastElement(id, title, message, type, persistent, showProgress);
        
        // إضافة الإشعار للحاوي
        this.container.appendChild(toast);
        this.notifications.set(id, toast);

        // إظهار الإشعار مع تأخير بسيط للحركة
        setTimeout(() => {
            toast.classList.add('show', 'animate-in');
        }, 50);

        // إعداد الإغلاق التلقائي إذا لم يكن دائماً
        if (!persistent && duration > 0) {
            this.scheduleToastRemoval(id, duration, showProgress);
        }

        // تشغيل صوت الإشعار
        this.playNotificationSound(type);

        // إظهار إشعار المتصفح
        if (options.browserNotification) {
            this.showBrowserNotification(title, message, type);
        }

        return id;
    }

    /**
     * إنشاء عنصر Toast
     */
    createToastElement(id, title, message, type, persistent, showProgress) {
        const toast = document.createElement('div');
        toast.id = id;
        toast.className = `notification-toast ${type}`;
        
        const icon = this.getTypeIcon(type);
        
        toast.innerHTML = `
            <div class="notification-icon">
                <i class="${icon}"></i>
            </div>
            <div class="notification-content">
                <div class="notification-title">${title}</div>
                <div class="notification-message">${message}</div>
            </div>
            <button class="notification-close" data-id="${id}">
                <i class="fas fa-times"></i>
            </button>
            ${showProgress && !persistent ? '<div class="notification-progress"><div class="notification-progress-bar"></div></div>' : ''}
        `;

        // إضافة مستمع الإغلاق
        const closeBtn = toast.querySelector('.notification-close');
        closeBtn.addEventListener('click', () => this.removeToast(id));

        return toast;
    }

    /**
     * جدولة إزالة الإشعار
     */
    scheduleToastRemoval(id, duration, showProgress) {
        const toast = this.notifications.get(id);
        if (!toast) return;

        const progressBar = toast.querySelector('.notification-progress-bar');
        
        if (showProgress && progressBar) {
            progressBar.style.transition = `width ${duration}ms linear`;
            progressBar.style.width = '0%';
        }

        setTimeout(() => {
            this.removeToast(id);
        }, duration);
    }

    /**
     * إزالة إشعار Toast
     */
    removeToast(id) {
        const toast = this.notifications.get(id);
        if (!toast) return;

        toast.classList.add('animate-out');
        toast.classList.remove('show');

        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
            this.notifications.delete(id);
        }, 400);
    }

    /**
     * تحديد عدد الإشعارات المعروضة
     */
    limitNotifications() {
        const toasts = this.container.querySelectorAll('.notification-toast');
        if (toasts.length >= this.maxNotifications) {
            // إزالة أقدم إشعار
            const oldestToast = toasts[0];
            const id = oldestToast.id;
            this.removeToast(id);
        }
    }

    /**
     * عرض رسالة Flash
     */
    showFlashMessage(message, type = 'info', duration = 6000) {
        const id = 'flash_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        
        const flash = this.createFlashElement(id, message, type);
        this.flashContainer.appendChild(flash);

        // إظهار الرسالة
        setTimeout(() => {
            flash.classList.add('show', 'animate-in');
        }, 50);

        // إزالة تلقائية
        if (duration > 0) {
            setTimeout(() => {
                this.removeFlashMessage(id);
            }, duration);
        }

        return id;
    }

    /**
     * إنشاء عنصر Flash Message
     */
    createFlashElement(id, message, type) {
        const flash = document.createElement('div');
        flash.id = id;
        flash.className = `flash-message ${type}`;
        
        const icon = this.getTypeIcon(type);
        
        flash.innerHTML = `
            <div class="flash-message-icon">
                <i class="${icon}"></i>
            </div>
            <div class="flash-message-content">${message}</div>
            <button class="flash-message-close" data-id="${id}">
                <i class="fas fa-times"></i>
            </button>
        `;

        // إضافة مستمع الإغلاق
        const closeBtn = flash.querySelector('.flash-message-close');
        closeBtn.addEventListener('click', () => this.removeFlashMessage(id));

        return flash;
    }

    /**
     * إزالة رسالة Flash
     */
    removeFlashMessage(id) {
        const flash = document.getElementById(id);
        if (!flash) return;

        flash.classList.add('animate-out');
        flash.classList.remove('show');

        setTimeout(() => {
            if (flash.parentNode) {
                flash.parentNode.removeChild(flash);
            }
        }, 400);
    }

    /**
     * إظهار/إخفاء قائمة الإشعارات
     */
    toggleNotificationPanel(panelId) {
        const panel = document.getElementById(panelId);
        if (!panel) return;

        if (panel.classList.contains('show')) {
            this.hideNotificationPanel(panel);
        } else {
            this.showNotificationPanel(panel);
        }
    }

    /**
     * إظهار قائمة الإشعارات
     */
    showNotificationPanel(panel) {
        // إخفاء قوائم أخرى مفتوحة
        document.querySelectorAll('.notifications-panel.show').forEach(p => {
            if (p !== panel) this.hideNotificationPanel(p);
        });

        panel.classList.add('show');
        this.updateNotificationBadge(panel);
    }

    /**
     * إخفاء قائمة الإشعارات
     */
    hideNotificationPanel(panel) {
        panel.classList.remove('show');
    }

    /**
     * تحديث شارة عدد الإشعارات
     */
    updateNotificationBadge(panel) {
        const badge = panel.parentElement.querySelector('.notifications-badge');
        const unreadItems = panel.querySelectorAll('.notification-item.unread');
        
        if (badge) {
            if (unreadItems.length > 0) {
                badge.textContent = unreadItems.length > 99 ? '99+' : unreadItems.length;
                badge.classList.add('show');
                
                if (unreadItems.length > 0) {
                    badge.classList.add('pulse');
                }
            } else {
                badge.classList.remove('show', 'pulse');
            }
        }
    }

    /**
     * تعليم جميع الإشعارات كمقروءة
     */
    markAllAsRead(panelId) {
        const panel = document.getElementById(panelId);
        if (!panel) return;

        const unreadItems = panel.querySelectorAll('.notification-item.unread');
        unreadItems.forEach(item => {
            item.classList.remove('unread');
        });

        this.updateNotificationBadge(panel);

        // إرسال طلب للخادم
        fetch('/api/notifications/mark-all-read', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        }).catch(error => {
            console.warn('Could not mark notifications as read:', error);
        });
    }

    /**
     * تعليم إشعار واحد كمقروء
     */
    markAsRead(notificationId, itemElement) {
        if (!itemElement) return;

        itemElement.classList.remove('unread');
        
        const panel = itemElement.closest('.notifications-panel');
        if (panel) {
            this.updateNotificationBadge(panel);
        }

        // إرسال طلب للخادم
        fetch(`/api/notifications/${notificationId}/mark-read`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        }).catch(error => {
            console.warn('Could not mark notification as read:', error);
        });
    }

    /**
     * إضافة إشعار جديد لقائمة الإشعارات
     */
    addNotificationToPanel(panelId, notification) {
        const panel = document.getElementById(panelId);
        if (!panel) return;

        const list = panel.querySelector('.notifications-list');
        if (!list) return;

        const item = this.createNotificationItem(notification);
        list.insertBefore(item, list.firstChild);

        // إزالة حالة "لا توجد إشعارات"
        const emptyState = list.querySelector('.notifications-empty');
        if (emptyState) {
            emptyState.remove();
        }

        this.updateNotificationBadge(panel);
    }

    /**
     * إنشاء عنصر إشعار للقائمة
     */
    createNotificationItem(notification) {
        const item = document.createElement('div');
        item.className = `notification-item ${notification.unread ? 'unread' : ''}`;
        item.dataset.id = notification.id;
        item.dataset.link = notification.link || '#';

        const icon = notification.icon || 'bell';
        
        item.innerHTML = `
            <div class="notification-item-icon">
                <i class="fas fa-${icon}"></i>
            </div>
            <div class="notification-item-content">
                <div class="notification-item-title">${notification.title}</div>
                <div class="notification-item-text">${notification.text}</div>
                <div class="notification-item-time">${this.formatTime(notification.time)}</div>
            </div>
        `;

        // إضافة مستمع النقر
        item.addEventListener('click', () => {
            if (notification.unread) {
                this.markAsRead(notification.id, item);
            }
            
            if (notification.link && notification.link !== '#') {
                window.location.href = notification.link;
            }
        });

        return item;
    }

    /**
     * إظهار إشعار المتصفح
     */
    showBrowserNotification(title, message, type) {
        if ('Notification' in window && Notification.permission === 'granted') {
            const icon = this.getBrowserNotificationIcon(type);
            
            const notification = new Notification(title, {
                body: message,
                icon: icon,
                tag: 'unified-notification-' + Date.now(),
                requireInteraction: type === 'error'
            });

            notification.onclick = () => {
                window.focus();
                notification.close();
            };

            // إغلاق تلقائي
            setTimeout(() => {
                notification.close();
            }, this.defaultDuration);
        }
    }

    /**
     * تشغيل صوت الإشعار
     */
    playNotificationSound(type) {
        if (this.sounds[type]) {
            try {
                this.sounds[type].currentTime = 0;
                this.sounds[type].play().catch(() => {
                    // تجاهل أخطاء تشغيل الصوت
                });
            } catch (error) {
                // تجاهل أخطاء تشغيل الصوت
            }
        }
    }

    /**
     * الحصول على أيقونة النوع
     */
    getTypeIcon(type) {
        const icons = {
            success: 'fas fa-check-circle',
            warning: 'fas fa-exclamation-triangle',
            error: 'fas fa-times-circle',
            info: 'fas fa-info-circle'
        };
        return icons[type] || icons.info;
    }

    /**
     * الحصول على أيقونة إشعار المتصفح
     */
    getBrowserNotificationIcon(type) {
        const baseUrl = window.location.origin + '/static/img/';
        const icons = {
            success: baseUrl + 'notification-success.png',
            warning: baseUrl + 'notification-warning.png',
            error: baseUrl + 'notification-error.png',
            info: baseUrl + 'notification-info.png'
        };
        return icons[type] || (baseUrl + 'logo.png');
    }

    /**
     * تنسيق الوقت
     */
    formatTime(timestamp) {
        if (!timestamp) return '';
        
        const now = new Date();
        const time = new Date(timestamp);
        const diff = now - time;
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (days > 0) {
            return `منذ ${days} ${days === 1 ? 'يوم' : 'أيام'}`;
        } else if (hours > 0) {
            return `منذ ${hours} ${hours === 1 ? 'ساعة' : 'ساعات'}`;
        } else if (minutes > 0) {
            return `منذ ${minutes} ${minutes === 1 ? 'دقيقة' : 'دقائق'}`;
        } else {
            return 'الآن';
        }
    }

    /**
     * إزالة جميع الإشعارات
     */
    clearAllToasts() {
        this.notifications.forEach((toast, id) => {
            this.removeToast(id);
        });
    }

    /**
     * إزالة جميع رسائل Flash
     */
    clearAllFlashMessages() {
        const messages = this.flashContainer.querySelectorAll('.flash-message');
        messages.forEach(message => {
            message.remove();
        });
    }

    /**
     * تحديث إعدادات النظام
     */
    updateSettings(settings) {
        if (settings.duration) this.defaultDuration = settings.duration;
        if (settings.maxNotifications) this.maxNotifications = settings.maxNotifications;
        if (settings.sounds) Object.assign(this.sounds, settings.sounds);
    }
}

// إنشاء نسخة عامة من النظام
window.NotificationSystem = new UnifiedNotificationSystem();

// دوال مساعدة سريعة
window.showToast = function(title, message, type = 'info', options = {}) {
    return window.NotificationSystem.showToast(title, message, type, options);
};

window.showSuccess = function(title, message, options = {}) {
    return window.NotificationSystem.showToast(title, message, 'success', options);
};

window.showWarning = function(title, message, options = {}) {
    return window.NotificationSystem.showToast(title, message, 'warning', options);
};

window.showError = function(title, message, options = {}) {
    return window.NotificationSystem.showToast(title, message, 'error', options);
};

window.showInfo = function(title, message, options = {}) {
    return window.NotificationSystem.showToast(title, message, 'info', options);
};

window.showFlash = function(message, type = 'info', duration = 6000) {
    return window.NotificationSystem.showFlashMessage(message, type, duration);
};

// دوال مساعدة محسنة جديدة
window.showQuickSuccess = function(message) {
    return window.showSuccess('نجح', message, { duration: 3000 });
};

window.showQuickError = function(message) {
    return window.showError('خطأ', message, { duration: 4000 });
};

window.showQuickInfo = function(message) {
    return window.showInfo('معلومة', message, { duration: 3000 });
};

window.showQuickWarning = function(message) {
    return window.showWarning('تنبيه', message, { duration: 4000 });
};

// دوال للإشعارات المستمرة (لا تختفي تلقائياً)
window.showPersistentError = function(title, message) {
    return window.showError(title, message, { persistent: true, showProgress: false });
};

window.showPersistentWarning = function(title, message) {
    return window.showWarning(title, message, { persistent: true, showProgress: false });
};

// دوال للإشعارات مع أصوات
window.showSoundNotification = function(title, message, type = 'info') {
    return window.showToast(title, message, type, { 
        browserNotification: true, 
        playSound: true 
    });
};

// دالة لإظهار إشعارات الحالة (مثل حفظ، تحميل، إلخ)
window.showStatusNotification = function(status, message) {
    const statusMap = {
        'loading': { type: 'info', title: 'جاري التحميل...', icon: 'fas fa-spinner fa-spin' },
        'saving': { type: 'info', title: 'جاري الحفظ...', icon: 'fas fa-save' },
        'saved': { type: 'success', title: 'تم الحفظ', icon: 'fas fa-check' },
        'error': { type: 'error', title: 'حدث خطأ', icon: 'fas fa-exclamation-triangle' },
        'success': { type: 'success', title: 'تم بنجاح', icon: 'fas fa-check-circle' },
        'uploading': { type: 'info', title: 'جاري الرفع...', icon: 'fas fa-upload' },
        'uploaded': { type: 'success', title: 'تم الرفع', icon: 'fas fa-check' },
        'connecting': { type: 'warning', title: 'جاري الاتصال...', icon: 'fas fa-wifi' },
        'connected': { type: 'success', title: 'تم الاتصال', icon: 'fas fa-wifi' },
        'disconnected': { type: 'error', title: 'انقطع الاتصال', icon: 'fas fa-wifi' }
    };
    
    const config = statusMap[status] || statusMap['info'];
    return window.showToast(config.title, message, config.type, {
        persistent: status === 'loading' || status === 'saving' || status === 'uploading' || status === 'connecting'
    });
};

// دالة لإظهار تقدم العمليات
window.showProgressNotification = function(title, progress = 0) {
    const id = 'progress_' + Date.now();
    const toast = window.showToast(title, `التقدم: ${progress}%`, 'info', {
        persistent: true,
        showProgress: true,
        customId: id
    });
    
    return {
        id: id,
        update: function(newProgress) {
            const element = document.getElementById(id);
            if (element) {
                const progressBar = element.querySelector('.notification-progress-bar');
                const messageEl = element.querySelector('.notification-message');
                if (progressBar) progressBar.style.width = newProgress + '%';
                if (messageEl) messageEl.textContent = `التقدم: ${newProgress}%`;
                
                if (newProgress >= 100) {
                    setTimeout(() => window.NotificationSystem.removeToast(id), 1000);
                }
            }
        },
        complete: function(successMessage = 'تم الانتهاء بنجاح') {
            window.NotificationSystem.removeToast(id);
            window.showQuickSuccess(successMessage);
        },
        error: function(errorMessage = 'حدث خطأ') {
            window.NotificationSystem.removeToast(id);
            window.showError('خطأ', errorMessage);
        }
    };
};

// إعداد مستمعي الأحداث للقوائم المنسدلة
document.addEventListener('DOMContentLoaded', function() {
    // تفعيل قوائم الإشعارات
    document.querySelectorAll('.notifications-toggle').forEach(toggle => {
        toggle.addEventListener('click', (e) => {
            e.stopPropagation();
            const panelId = toggle.dataset.panel || toggle.getAttribute('data-panel');
            if (panelId) {
                window.NotificationSystem.toggleNotificationPanel(panelId);
            }
        });
    });

    // تفعيل أزرار "تعليم الكل كمقروء"
    document.querySelectorAll('.mark-all-read-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const panelId = btn.dataset.panel || btn.getAttribute('data-panel');
            if (panelId) {
                window.NotificationSystem.markAllAsRead(panelId);
            }
        });
    });

    // تحديث شارات الإشعارات عند تحميل الصفحة
    document.querySelectorAll('.notifications-panel').forEach(panel => {
        window.NotificationSystem.updateNotificationBadge(panel);
    });
});

// دعم WebSocket للإشعارات الفورية
if (typeof io !== 'undefined') {
    const socket = io();
    
    socket.on('notification', function(data) {
        window.NotificationSystem.showToast(
            data.title,
            data.message,
            data.type || 'info',
            { browserNotification: true }
        );
        
        // إضافة للقائمة إذا كانت موجودة
        if (data.panelId) {
            window.NotificationSystem.addNotificationToPanel(data.panelId, data);
        }
    });
    
    socket.on('flash_message', function(data) {
        window.NotificationSystem.showFlashMessage(
            data.message,
            data.type || 'info',
            data.duration || 6000
        );
    });
}

// إشعار عند انقطاع الاتصال
window.addEventListener('offline', function() {
    window.showWarning('انقطع الاتصال', 'تحقق من اتصال الإنترنت', { persistent: true });
});

window.addEventListener('online', function() {
    window.showSuccess('تم الاتصال', 'تم استعادة الاتصال بالإنترنت');
});

// تصدير للاستخدام كوحدة
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UnifiedNotificationSystem;
}

// إغلاق الشرطة للتحقق من التحميل المتعدد
}
