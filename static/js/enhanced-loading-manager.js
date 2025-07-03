/**
 * نظام Loading Indicators المحسن والموحد
 * نظام شامل ومتطور لإدارة حالات التحميل في التطبيق
 * @version 2.0
 * @author AL-7esa Platform
 */

class EnhancedLoadingManager {
    constructor(options = {}) {
        this.activeLoaders = new Map();
        this.loadingQueue = new Set();
        this.options = {
            autoInit: true,
            defaultTimeout: 30000,
            enableDebug: false,
            defaultSpinnerType: 'spinner',
            defaultTheme: 'light',
            maxConcurrentLoadings: 3,
            ...options
        };
        
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
        this.createPageOverlay();
        this.bindEvents();
        this.initFormLoading();
        this.initImageLoading();
        this.initAjaxInterceptors();
        this.initNavigationLoading();
        this.initErrorHandlers();
        this.initPageCleanup();
        this.log('Enhanced LoadingManager initialized successfully');
    }

    /**
     * إنشاء overlay التحميل للصفحة
     */
    createPageOverlay() {
        if (document.getElementById('enhanced-page-loading-overlay')) return;

        const overlay = document.createElement('div');
        overlay.id = 'enhanced-page-loading-overlay';
        overlay.className = `page-loading-overlay ${this.options.defaultTheme}`;
        overlay.innerHTML = `
            <div class="loading-content">
                <div class="loading-spinner xl"></div>
                <div class="loading-text">جاري التحميل...</div>
                <div class="loading-progress-container" style="display: none;">
                    <div class="loading-progress">
                        <div class="progress-bar"></div>
                    </div>
                    <div class="progress-text">0%</div>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);
    }

    /**
     * إظهار loading للصفحة كاملة
     */
    showPageLoading(options = {}) {
        if (typeof options === 'string') {
            options = { text: options };
        }
        
        const {
            text = 'جاري التحميل...',
            type = 'spinner',
            theme = this.options.defaultTheme,
            timeout = this.options.defaultTimeout,
            progress = false,
            id = 'page'
        } = options;

        const overlay = document.getElementById('enhanced-page-loading-overlay');
        if (!overlay) {
            this.createPageOverlay();
            return this.showPageLoading(options);
        }

        const textElement = overlay.querySelector('.loading-text');
        const spinnerElement = overlay.querySelector('.loading-spinner');
        const progressContainer = overlay.querySelector('.loading-progress-container');
        
        if (textElement) textElement.textContent = text;
        if (type !== 'spinner' && spinnerElement) {
            spinnerElement.className = `loading-${type} xl`;
        }
        
        overlay.className = `page-loading-overlay ${theme}`;
        
        if (progress && progressContainer) {
            progressContainer.style.display = 'block';
        }
        
        overlay.classList.add('active');
        document.body.style.overflow = 'hidden';
        
        const loadingData = {
            id,
            startTime: Date.now(),
            text,
            type,
            timeout: timeout ? setTimeout(() => {
                this.log(`Loading timeout for ${id}`, 'warn');
                this.hidePageLoading();
            }, timeout) : null
        };
        
        this.activeLoaders.set(id, loadingData);
        this.stats.totalLoadings++;
        this.stats.currentLoadings++;
        
        this.log(`Page loading started: ${text}`);
        return id;
    }

    /**
     * إخفاء loading الصفحة
     */
    hidePageLoading(id = 'page') {
        const overlay = document.getElementById('enhanced-page-loading-overlay');
        if (!overlay) return;

        const loadingData = this.activeLoaders.get(id);
        if (loadingData) {
            const loadTime = Date.now() - loadingData.startTime;
            this.updateAverageLoadTime(loadTime);
            
            if (loadingData.timeout) {
                clearTimeout(loadingData.timeout);
            }
            
            this.activeLoaders.delete(id);
            this.stats.currentLoadings = Math.max(0, this.stats.currentLoadings - 1);
            this.log(`Page loading finished in ${loadTime}ms`);
        }

        overlay.classList.remove('active');
        document.body.style.overflow = '';
        
        const progressContainer = overlay.querySelector('.loading-progress-container');
        if (progressContainer) {
            progressContainer.style.display = 'none';
        }
    }

    /**
     * إظهار loading لقسم معين
     */
    showSectionLoading(element, options = {}) {
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        
        if (!element) {
            this.log('Element not found for section loading', 'error');
            return null;
        }

        if (typeof options === 'string') {
            options = { text: options };
        }

        const {
            text = '',
            type = 'spinner',
            theme = 'light',
            size = 'lg',
            timeout = this.options.defaultTimeout,
            blur = false
        } = options;

        const computedStyle = window.getComputedStyle(element);
        if (computedStyle.position === 'static') {
            element.style.position = 'relative';
        }

        if (blur) element.classList.add('loading-blur');

        let overlay = element.querySelector('.section-loading-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = `section-loading-overlay ${theme}`;
            
            let loadingHTML = this.getLoadingHTML(type, size);
            
            overlay.innerHTML = `
                <div class="loading-content">
                    ${loadingHTML}
                    ${text ? `<div class="loading-text">${text}</div>` : ''}
                </div>
            `;
            element.appendChild(overlay);
        }

        overlay.classList.add('active');

        const id = element.id || `section-${Date.now()}`;
        const loadingData = {
            id,
            element,
            startTime: Date.now(),
            text,
            type,
            timeout: timeout ? setTimeout(() => {
                this.log(`Section loading timeout for ${id}`, 'warn');
                this.hideSectionLoading(element);
            }, timeout) : null
        };
        
        this.activeLoaders.set(id, loadingData);
        this.stats.totalLoadings++;
        this.stats.currentLoadings++;
        
        this.log(`Section loading started for ${id}: ${text}`);
        return id;
    }

    /**
     * إخفاء loading القسم
     */
    hideSectionLoading(element, force = false) {
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        
        if (!element) return;

        const overlay = element.querySelector('.section-loading-overlay');
        if (overlay) {
            overlay.classList.remove('active');
            
            if (force) {
                overlay.remove();
            } else {
                setTimeout(() => {
                    if (!overlay.classList.contains('active')) {
                        overlay.remove();
                    }
                }, 300);
            }
        }

        element.classList.remove('loading-blur');

        const id = element.id || 'section';
        const loadingData = this.activeLoaders.get(id);
        if (loadingData) {
            const loadTime = Date.now() - loadingData.startTime;
            this.updateAverageLoadTime(loadTime);
            
            if (loadingData.timeout) {
                clearTimeout(loadingData.timeout);
            }
            
            this.activeLoaders.delete(id);
            this.stats.currentLoadings = Math.max(0, this.stats.currentLoadings - 1);
            this.log(`Section loading finished for ${id} in ${loadTime}ms`);
        }
    }

    /**
     * إظهار loading للأزرار
     */
    showButtonLoading(button, options = {}) {
        if (typeof button === 'string') {
            button = document.querySelector(button);
        }
        
        if (!button) {
            this.log('Button not found for loading', 'error');
            return;
        }

        if (typeof options === 'string') {
            options = { text: options };
        }

        const {
            text = '',
            keepText = false,
            type = 'spinner',
            size = this.getButtonSize(button)
        } = options;

        if (!button.hasAttribute('data-original-text')) {
            button.setAttribute('data-original-text', button.innerHTML);
        }
        
        button.classList.add('loading');
        button.disabled = true;
        
        if (keepText && text) {
            button.innerHTML = `
                <span class="btn-text">${text}</span>
                <span class="loading-spinner ${size}"></span>
            `;
            button.classList.add('loading-text');
        } else if (text) {
            button.innerHTML = text;
        }
        
        const id = button.id || `button-${Date.now()}`;
        this.activeLoaders.set(id, {
            id,
            element: button,
            startTime: Date.now(),
            text,
            type
        });
        
        this.stats.totalLoadings++;
        this.stats.currentLoadings++;
        this.log(`Button loading started for ${id}`);
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
        
        button.classList.remove('loading', 'loading-text');
        button.disabled = false;

        const id = button.id || 'button';
        const loadingData = this.activeLoaders.get(id);
        if (loadingData) {
            const loadTime = Date.now() - loadingData.startTime;
            this.updateAverageLoadTime(loadTime);
            this.activeLoaders.delete(id);
            this.stats.currentLoadings = Math.max(0, this.stats.currentLoadings - 1);
            this.log(`Button loading finished for ${id} in ${loadTime}ms`);
        }
    }

    /**
     * تحديث progress
     */
    updateProgress(progress, text = null) {
        const overlay = document.getElementById('enhanced-page-loading-overlay');
        if (!overlay) return;

        const progressBar = overlay.querySelector('.progress-bar');
        const progressText = overlay.querySelector('.progress-text');
        const textElement = overlay.querySelector('.loading-text');

        if (progressBar) {
            progressBar.style.width = `${Math.max(0, Math.min(100, progress))}%`;
        }
        
        if (progressText) {
            progressText.textContent = `${Math.round(progress)}%`;
        }
        
        if (text && textElement) {
            textElement.textContent = text;
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
            height = '16px',
            animated = true
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
                const width = i === lines - 1 ? '60%' : ['100%', '90%', '80%'][i % 3];
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
     * ربط الأحداث
     */
    bindEvents() {
        // Loading للنماذج
        document.addEventListener('submit', (e) => {
            const form = e.target;
            if (form.tagName === 'FORM' && !form.classList.contains('no-loading')) {
                const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
                if (submitBtn) {
                    this.showButtonLoading(submitBtn, 'جاري الإرسال...');
                }
            }
        });

        // Loading للروابط
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a[data-loading]');
            if (link && !link.getAttribute('href').startsWith('#') && link.target !== '_blank') {
                const loadingText = link.getAttribute('data-loading-text') || 'جاري التحميل...';
                this.showPageLoading(loadingText);
            }
        });
    }

    /**
     * تهيئة loading للنماذج
     */
    initFormLoading() {
        document.querySelectorAll('form:not([data-no-loading])').forEach(form => {
            form.addEventListener('submit', (e) => {
                const submitBtn = form.querySelector('[type="submit"]');
                if (submitBtn && !submitBtn.disabled) {
                    this.showButtonLoading(submitBtn, 'جاري المعالجة...');
                }
            });
        });
    }

    /**
     * تهيئة loading للصور
     */
    initImageLoading() {
        document.querySelectorAll('img[data-loading]').forEach(img => {
            if (!img.complete && img.src) {
                img.classList.add('image-loading');
                
                const handleLoad = () => {
                    img.classList.remove('image-loading');
                    img.removeEventListener('load', handleLoad);
                    img.removeEventListener('error', handleLoad);
                };
                
                img.addEventListener('load', handleLoad);
                img.addEventListener('error', handleLoad);
            }
        });
    }

    /**
     * تهيئة AJAX interceptors
     */
    initAjaxInterceptors() {
        const originalFetch = window.fetch;
        const loadingManager = this;

        window.fetch = function(...args) {
            const url = args[0];
            const options = args[1] || {};

            if (options.noLoading || 
                url.includes('/api/heartbeat') || 
                url.includes('/ping')) {
                return originalFetch.apply(this, args);
            }

            const loadingId = loadingManager.showPageLoading({
                text: options.loadingText || 'جاري تحميل البيانات...',
                timeout: options.loadingTimeout || 30000
            });

            return originalFetch.apply(this, args)
                .then(response => {
                    loadingManager.hidePageLoading(loadingId);
                    return response;
                })
                .catch(error => {
                    loadingManager.hidePageLoading(loadingId);
                    loadingManager.handleError(error, 'fetch');
                    throw error;
                });
        };

        // jQuery support
        if (typeof $ !== 'undefined') {
            $(document).ajaxStart(() => {
                if (!this.isLoading('page')) {
                    this.showPageLoading('جاري معالجة الطلب...');
                }
            });
            
            $(document).ajaxStop(() => {
                this.hidePageLoading();
            });
        }
    }

    /**
     * تهيئة navigation loading
     */
    initNavigationLoading() {
        window.addEventListener('beforeunload', () => {
            if (this.isLoading()) {
                this.clearAllLoading();
            }
        });
    }

    /**
     * تهيئة error handlers
     */
    initErrorHandlers() {
        window.addEventListener('error', (e) => {
            this.handleError(e.error, 'global');
        });

        window.addEventListener('unhandledrejection', (e) => {
            this.handleError(e.reason, 'promise');
        });
    }

    /**
     * تهيئة page cleanup
     */
    initPageCleanup() {
        window.addEventListener('pagehide', () => {
            this.clearAllLoading();
        });
    }

    /**
     * معالجة الأخطاء
     */
    handleError(error, source = 'unknown') {
        this.stats.errors++;
        this.log(`Error in ${source}: ${error.message || error}`, 'error');
    }

    /**
     * تحديث متوسط وقت التحميل
     */
    updateAverageLoadTime(loadTime) {
        const totalTime = this.stats.averageLoadTime * (this.stats.totalLoadings - 1);
        this.stats.averageLoadTime = (totalTime + loadTime) / this.stats.totalLoadings;
    }

    /**
     * الحصول على HTML للـ loading
     */
    getLoadingHTML(type, size) {
        switch (type) {
            case 'dots':
                return `<div class="loading-dots ${size}">
                    <div class="dot"></div>
                    <div class="dot"></div>
                    <div class="dot"></div>
                </div>`;
            case 'bars':
                return `<div class="loading-bars ${size}">
                    <div class="bar"></div>
                    <div class="bar"></div>
                    <div class="bar"></div>
                    <div class="bar"></div>
                    <div class="bar"></div>
                </div>`;
            case 'wave':
                return `<div class="loading-wave ${size}">
                    <div class="wave-bar"></div>
                    <div class="wave-bar"></div>
                    <div class="wave-bar"></div>
                    <div class="wave-bar"></div>
                    <div class="wave-bar"></div>
                </div>`;
            case 'pulse':
                return `<div class="loading-pulse ${size}"></div>`;
            default:
                return `<div class="loading-spinner ${size}"></div>`;
        }
    }

    /**
     * تحديد حجم الزر
     */
    getButtonSize(button) {
        if (button.classList.contains('btn-sm')) return 'sm';
        if (button.classList.contains('btn-lg')) return 'lg';
        return 'md';
    }

    /**
     * تنظيف جميع loading states
     */
    clearAllLoading(force = false) {
        this.log('Clearing all loading states');

        this.activeLoaders.forEach((loadingData) => {
            if (loadingData.timeout) {
                clearTimeout(loadingData.timeout);
            }
        });

        this.hidePageLoading();
        
        document.querySelectorAll('.section-loading-overlay').forEach(overlay => {
            if (force) {
                overlay.remove();
            } else {
                overlay.classList.remove('active');
            }
        });

        document.querySelectorAll('.btn.loading').forEach(btn => {
            this.hideButtonLoading(btn);
        });

        document.querySelectorAll('.skeleton-container').forEach(skeleton => {
            skeleton.remove();
        });

        document.querySelectorAll('.loading-blur').forEach(element => {
            element.classList.remove('loading-blur');
        });

        this.activeLoaders.clear();
        this.stats.currentLoadings = 0;
        document.body.style.overflow = '';
        
        this.log('All loading states cleared');
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

    /**
     * الحصول على إحصائيات
     */
    getStats() {
        return {
            ...this.stats,
            activeLoadings: this.activeLoaders.size,
            activeLoadingIds: Array.from(this.activeLoaders.keys())
        };
    }

    /**
     * تسجيل الأحداث
     */
    log(message, level = 'info') {
        if (!this.options.enableDebug) return;
        
        const timestamp = new Date().toISOString();
        const prefix = `[EnhancedLoadingManager ${timestamp}]`;
        
        switch (level) {
            case 'error':
                console.error(prefix, message);
                break;
            case 'warn':
                console.warn(prefix, message);
                break;
            default:
                console.log(prefix, message);
        }
    }
}

// إنشاء instance عام
const enhancedLoading = new EnhancedLoadingManager({
    enableDebug: true,
    defaultTheme: 'light'
});

// تصدير للاستخدام العام
window.EnhancedLoadingManager = EnhancedLoadingManager;
window.enhancedLoading = enhancedLoading;

// دوال مساعدة سريعة
window.showLoading = (text) => enhancedLoading.showPageLoading(text);
window.hideLoading = () => enhancedLoading.hidePageLoading();
window.showSectionLoading = (element, text) => enhancedLoading.showSectionLoading(element, text);
window.hideSectionLoading = (element) => enhancedLoading.hideSectionLoading(element);
window.showButtonLoading = (button, text) => enhancedLoading.showButtonLoading(button, text);
window.hideButtonLoading = (button) => enhancedLoading.hideButtonLoading(button);
window.showSkeleton = (element, config) => enhancedLoading.showSkeleton(element, config);
window.hideSkeleton = (element) => enhancedLoading.hideSkeleton(element);
window.updateProgress = (progress, text) => enhancedLoading.updateProgress(progress, text);

// تطبيق loading على العناصر الموجودة عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', () => {
    // تطبيق loading للصور
    document.querySelectorAll('img:not([data-no-loading])').forEach(img => {
        if (!img.complete && img.src) {
            img.classList.add('image-loading');
            
            const handleLoad = () => {
                img.classList.remove('image-loading');
                img.removeEventListener('load', handleLoad);
                img.removeEventListener('error', handleLoad);
            };
            
            img.addEventListener('load', handleLoad);
            img.addEventListener('error', handleLoad);
        }
    });
    
    // تطبيق data attributes
    document.querySelectorAll('[data-loading-on-click]').forEach(element => {
        element.addEventListener('click', function() {
            const loadingText = this.getAttribute('data-loading-text') || 'جاري التحميل...';
            const loadingType = this.getAttribute('data-loading-type') || 'spinner';
            
            if (this.tagName === 'BUTTON') {
                enhancedLoading.showButtonLoading(this, {
                    text: loadingText,
                    type: loadingType
                });
            } else {
                enhancedLoading.showPageLoading({
                    text: loadingText,
                    type: loadingType
                });
            }
        });
    });
});

console.log('✅ Enhanced Loading Manager loaded successfully');
