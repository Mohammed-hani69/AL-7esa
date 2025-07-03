/**
 * نظام Loading Indicators الموحد المحسن
 * نظام شامل ومتطور لإدارة حالات التحميل في التطبيق
 * @version 2.0
 * @author AL-7esa Platform
 */

class LoadingManager {
    constructor(options = {}) {
        this.activeLoaders = new Map();
        this.loadingQueue = new Set();
        this.options = {
            autoInit: true,
            defaultTimeout: 30000, // 30 ثانية
            enableDebug: false,
            defaultSpinnerType: 'spinner',
            defaultTheme: 'light',
            ...options
        };
        
        // إحصائيات Loading
        this.stats = {
            totalLoadings: 0,
            currentLoadings: 0,
            averageLoadTime: 0,
            errors: 0
        };
        
        if (this.options.autoInit) {
            this.init();
        }
    }

    init() {
        // إنشاء overlay التحميل العام
        this.createPageOverlay();
        
        // ربط الأحداث
        this.bindEvents();
        
        // تهيئة loading states للنماذج
        this.initFormLoading();
        
        // تهيئة image loading
        this.initImageLoading();
        
        // تهيئة AJAX interceptors
        this.initAjaxInterceptors();
        
        // تهيئة navigation loading
        this.initNavigationLoading();
        
        // تهيئة error handlers
        this.initErrorHandlers();
        
        // إعداد cleanup للصفحة
        this.initPageCleanup();
        
        this.log('LoadingManager initialized successfully');
    }

    /**
     * إنشاء overlay التحميل للصفحة كاملة
     */
    createPageOverlay() {
        if (document.getElementById('page-loading-overlay')) return;

        const overlay = document.createElement('div');
        overlay.id = 'page-loading-overlay';
        overlay.className = 'page-loading-overlay';
        overlay.innerHTML = `
            <div class="loading-content">
                <div class="loading-spinner xl"></div>
                <div class="loading-text">جاري التحميل...</div>
            </div>
        `;
        document.body.appendChild(overlay);
    }

    /**
     * إظهار loading للصفحة كاملة
     */
    showPageLoading(text = 'جاري التحميل...') {
        const overlay = document.getElementById('page-loading-overlay');
        const textElement = overlay.querySelector('.loading-text');
        
        if (textElement) {
            textElement.textContent = text;
        }
        
        overlay.classList.add('active');
        document.body.style.overflow = 'hidden';
        this.activeLoaders.add('page');
    }

    /**
     * إخفاء loading الصفحة
     */
    hidePageLoading() {
        const overlay = document.getElementById('page-loading-overlay');
        overlay.classList.remove('active');
        document.body.style.overflow = '';
        this.activeLoaders.delete('page');
    }

    /**
     * إظهار loading لقسم معين
     */
    showSectionLoading(element, text = '') {
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        
        if (!element) return;

        // التأكد من position relative
        const computedStyle = window.getComputedStyle(element);
        if (computedStyle.position === 'static') {
            element.style.position = 'relative';
        }

        // إنشاء overlay
        let overlay = element.querySelector('.section-loading-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'section-loading-overlay';
            overlay.innerHTML = `
                <div class="loading-content">
                    <div class="loading-spinner lg"></div>
                    ${text ? `<div class="loading-text">${text}</div>` : ''}
                </div>
            `;
            element.appendChild(overlay);
        }

        overlay.classList.add('active');
        const id = element.id || `section-${Date.now()}`;
        this.activeLoaders.add(id);
    }

    /**
     * إخفاء loading القسم
     */
    hideSectionLoading(element) {
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        
        if (!element) return;

        const overlay = element.querySelector('.section-loading-overlay');
        if (overlay) {
            overlay.classList.remove('active');
            setTimeout(() => {
                if (!overlay.classList.contains('active')) {
                    overlay.remove();
                }
            }, 300);
        }

        const id = element.id || 'section';
        this.activeLoaders.delete(id);
    }

    /**
     * إظهار loading للأزرار
     */
    showButtonLoading(button, text = '') {
        if (typeof button === 'string') {
            button = document.querySelector(button);
        }
        
        if (!button) return;

        button.setAttribute('data-original-text', button.innerHTML);
        button.classList.add('loading');
        button.disabled = true;
        
        if (text) {
            button.innerHTML = text;
        }
    }

    /**
     * إخفاء loading الأزرار
     */
    hideButtonLoading(button) {
        if (typeof button === 'string') {
            button = document.querySelector(button);
        }
        
        if (!button) return;

        const originalText = button.getAttribute('data-original-text');
        if (originalText) {
            button.innerHTML = originalText;
            button.removeAttribute('data-original-text');
        }
        
        button.classList.remove('loading');
        button.disabled = false;
    }

    /**
     * إظهار progress bar
     */
    showProgress(element, progress = 0) {
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        
        if (!element) return;

        let progressBar = element.querySelector('.loading-progress');
        if (!progressBar) {
            progressBar = document.createElement('div');
            progressBar.className = 'loading-progress';
            progressBar.innerHTML = '<div class="progress-bar"></div>';
            element.appendChild(progressBar);
        }

        const bar = progressBar.querySelector('.progress-bar');
        bar.style.width = `${Math.max(0, Math.min(100, progress))}%`;
    }

    /**
     * إظهار progress indeterminate
     */
    showIndeterminateProgress(element) {
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        
        if (!element) return;

        let progressBar = element.querySelector('.loading-progress');
        if (!progressBar) {
            progressBar = document.createElement('div');
            progressBar.className = 'loading-progress indeterminate';
            element.appendChild(progressBar);
        } else {
            progressBar.classList.add('indeterminate');
        }
    }

    /**
     * إخفاء progress bar
     */
    hideProgress(element) {
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        
        if (!element) return;

        const progressBar = element.querySelector('.loading-progress');
        if (progressBar) {
            progressBar.remove();
        }
    }

    /**
     * إظهار typing indicator
     */
    showTypingIndicator(container, userName = 'مستخدم') {
        if (typeof container === 'string') {
            container = document.querySelector(container);
        }
        
        if (!container) return;

        let indicator = container.querySelector('.typing-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'typing-indicator';
            indicator.innerHTML = `
                <span>${userName} يكتب</span>
                <div class="typing-dots">
                    <div class="dot"></div>
                    <div class="dot"></div>
                    <div class="dot"></div>
                </div>
            `;
            container.appendChild(indicator);
        }

        indicator.style.display = 'flex';
    }

    /**
     * إخفاء typing indicator
     */
    hideTypingIndicator(container) {
        if (typeof container === 'string') {
            container = document.querySelector(container);
        }
        
        if (!container) return;

        const indicator = container.querySelector('.typing-indicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
    }

    /**
     * إظهار skeleton loading
     */
    showSkeleton(element, config = {}) {
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        
        if (!element) return;

        const {
            lines = 3,
            avatar = false,
            height = '16px'
        } = config;

        let skeleton = element.querySelector('.skeleton-container');
        if (!skeleton) {
            skeleton = document.createElement('div');
            skeleton.className = 'skeleton-container';
            
            let skeletonHTML = '';
            
            if (avatar) {
                skeletonHTML += '<div class="loading-skeleton avatar"></div>';
            }
            
            for (let i = 0; i < lines; i++) {
                const width = i === lines - 1 ? '60%' : '100%';
                skeletonHTML += `<div class="loading-skeleton text" style="height: ${height}; width: ${width};"></div>`;
            }
            
            skeleton.innerHTML = skeletonHTML;
            element.appendChild(skeleton);
        }

        element.style.minHeight = element.offsetHeight + 'px';
        skeleton.style.display = 'block';
    }

    /**
     * إخفاء skeleton loading
     */
    hideSkeleton(element) {
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        
        if (!element) return;

        const skeleton = element.querySelector('.skeleton-container');
        if (skeleton) {
            skeleton.remove();
        }
        element.style.minHeight = '';
    }

    /**
     * تهيئة loading للنماذج
     */
    initFormLoading() {
        document.addEventListener('submit', (e) => {
            const form = e.target;
            if (form.tagName === 'FORM' && !form.classList.contains('no-loading')) {
                const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
                if (submitBtn) {
                    this.showButtonLoading(submitBtn);
                }
            }
        });
    }

    /**
     * تهيئة loading للصور
     */
    initImageLoading() {
        // تطبيق loading على الصور الجديدة
        const images = document.querySelectorAll('img[data-loading]');
        images.forEach(img => {
            if (!img.complete) {
                img.classList.add('image-loading');
                
                img.addEventListener('load', () => {
                    img.classList.remove('image-loading');
                });
                
                img.addEventListener('error', () => {
                    img.classList.remove('image-loading');
                });
            }
        });
    }

    /**
     * ربط الأحداث
     */
    bindEvents() {
        // Loading للروابط
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a[data-loading]');
            if (link && !link.getAttribute('href').startsWith('#')) {
                this.showPageLoading('جاري تحميل الصفحة...');
            }
        });

        // Loading للنماذج AJAX
        document.addEventListener('ajaxStart', () => {
            this.showPageLoading('جاري إرسال البيانات...');
        });

        document.addEventListener('ajaxComplete', () => {
            this.hidePageLoading();
        });

        // Loading للفيتش requests
        this.interceptFetch();
    }

    /**
     * اعتراض fetch requests لإظهار loading
     */
    interceptFetch() {
        const originalFetch = window.fetch;
        const loadingManager = this;

        window.fetch = function(...args) {
            const url = args[0];
            const options = args[1] || {};

            // تجاهل بعض الطلبات
            if (options.noLoading || url.includes('/api/heartbeat')) {
                return originalFetch.apply(this, args);
            }

            // إظهار loading
            loadingManager.showPageLoading('جاري تحميل البيانات...');

            return originalFetch.apply(this, args)
                .then(response => {
                    loadingManager.hidePageLoading();
                    return response;
                })
                .catch(error => {
                    loadingManager.hidePageLoading();
                    throw error;
                });
        };
    }

    /**
     * إظهار loading للجداول
     */
    showTableLoading(table) {
        if (typeof table === 'string') {
            table = document.querySelector(table);
        }
        
        if (!table) return;

        table.classList.add('table-loading');
    }

    /**
     * إخفاء loading الجداول
     */
    hideTableLoading(table) {
        if (typeof table === 'string') {
            table = document.querySelector(table);
        }
        
        if (!table) return;

        table.classList.remove('table-loading');
    }

    /**
     * تنظيف جميع loading states
     */
    clearAllLoading() {
        this.hidePageLoading();
        
        // إزالة جميع section overlays
        document.querySelectorAll('.section-loading-overlay').forEach(overlay => {
            overlay.classList.remove('active');
        });

        // إزالة loading من الأزرار
        document.querySelectorAll('.btn.loading').forEach(btn => {
            this.hideButtonLoading(btn);
        });

        // إزالة loading من الجداول
        document.querySelectorAll('.table-loading').forEach(table => {
            this.hideTableLoading(table);
        });

        this.activeLoaders.clear();
    }

    /**
     * فحص حالة Loading
     */
    isLoading(id = null) {
        if (id) {
            return this.activeLoaders.has(id);
        }
        return this.activeLoaders.size > 0;
    }
}

// إنشاء instance عام
const loadingManager = new LoadingManager();

// تصدير للاستخدام العام
window.LoadingManager = LoadingManager;
window.loading = loadingManager;

// دوال مساعدة سريعة
window.showLoading = (text) => loadingManager.showPageLoading(text);
window.hideLoading = () => loadingManager.hidePageLoading();
window.showSectionLoading = (element, text) => loadingManager.showSectionLoading(element, text);
window.hideSectionLoading = (element) => loadingManager.hideSectionLoading(element);
window.showButtonLoading = (button, text) => loadingManager.showButtonLoading(button, text);
window.hideButtonLoading = (button) => loadingManager.hideButtonLoading(button);

// تطبيق loading على النماذج الموجودة
document.addEventListener('DOMContentLoaded', () => {
    // إضافة loading indicators لجميع النماذج
    document.querySelectorAll('form').forEach(form => {
        if (!form.classList.contains('no-loading')) {
            form.addEventListener('submit', (e) => {
                const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
                if (submitBtn && !submitBtn.classList.contains('loading')) {
                    loadingManager.showButtonLoading(submitBtn, 'جاري الإرسال...');
                    
                    // إزالة loading بعد timeout كـ failsafe
                    setTimeout(() => {
                        loadingManager.hideButtonLoading(submitBtn);
                    }, 10000);
                }
            });
        }
    });

    // إضافة loading للروابط الخارجية
    document.querySelectorAll('a[href^="http"], a[data-loading="true"]').forEach(link => {
        link.addEventListener('click', (e) => {
            if (!link.getAttribute('href').startsWith('#') && link.target !== '_blank') {
                loadingManager.showPageLoading('جاري التحميل...');
            }
        });
    });

    // تطبيق loading على الصور
    document.querySelectorAll('img:not([data-no-loading])').forEach(img => {
        if (!img.complete && img.src) {
            img.classList.add('image-loading');
            
            const onLoad = () => {
                img.classList.remove('image-loading');
                img.removeEventListener('load', onLoad);
                img.removeEventListener('error', onLoad);
            };
            
            img.addEventListener('load', onLoad);
            img.addEventListener('error', onLoad);
        }
    });
});

// معالجة beforeunload
window.addEventListener('beforeunload', () => {
    if (loadingManager.isLoading()) {
        loadingManager.clearAllLoading();
    }
});
