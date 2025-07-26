/**
 * Enhanced File Upload Manager
 * إدارة متقدمة لرفع الملفات مع شريط التقدم وتحسينات الأداء
 */

class EnhancedFileUpload {
    constructor(options = {}) {
        this.options = {
            maxFileSize: 2048 * 1024 * 1024, // 2GB default (زيادة كبيرة)
            chunkSize: 1024 * 1024, // 1MB chunks
            allowedTypes: {
                'image': ['jpg', 'jpeg', 'png', 'gif', 'webp'],
                'video': ['mp4', 'webm', 'mov', 'avi'],
                'audio': ['mp3', 'wav', 'ogg', 'm4a'],
                'file': ['pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt']
            },
            sizeLimits: {
                'image': 200 * 1024 * 1024,     // 200MB للصور (زيادة)
                'video': 2048 * 1024 * 1024,    // 2GB للفيديو (زيادة كبيرة)
                'audio': 500 * 1024 * 1024,     // 500MB للصوت (زيادة)
                'file': 500 * 1024 * 1024       // 500MB للمستندات (زيادة)
            },
            ...options
        };
        
        this.uploadQueue = [];
        this.activeUploads = 0;
        this.maxConcurrentUploads = 2;
    }

    /**
     * تهيئة مدير رفع الملفات
     */
    init() {
        this.setupEventListeners();
        this.createProgressContainer();
    }

    /**
     * إعداد مستمعي الأحداث
     */
    setupEventListeners() {
        // منع السحب والإفلات في النافذة
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            document.addEventListener(eventName, this.preventDefaults, false);
        });

        // إعداد منطقة السحب والإفلات
        this.setupDropZone();
    }

    /**
     * منع الأحداث الافتراضية
     */
    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    /**
     * إعداد منطقة السحب والإفلات
     */
    setupDropZone() {
        const fileInput = document.getElementById('content_file');
        if (!fileInput) return;

        const dropZone = this.createDropZone(fileInput);
        
        // أحداث السحب والإفلات
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.add('drag-over');
            });
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.remove('drag-over');
            });
        });

        dropZone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                fileInput.dispatchEvent(new Event('change'));
            }
        });
    }

    /**
     * إنشاء منطقة السحب والإفلات
     */
    createDropZone(fileInput) {
        const container = fileInput.parentElement;
        container.classList.add('file-drop-zone');
        
        // إضافة CSS للمنطقة
        if (!document.getElementById('drop-zone-styles')) {
            const style = document.createElement('style');
            style.id = 'drop-zone-styles';
            style.textContent = `
                .file-drop-zone {
                    position: relative;
                    border: 2px dashed #dee2e6;
                    border-radius: 8px;
                    padding: 20px;
                    text-align: center;
                    transition: all 0.3s ease;
                    background-color: #f8f9fa;
                }
                
                .file-drop-zone.drag-over {
                    border-color: #007bff;
                    background-color: #e3f2fd;
                    transform: scale(1.02);
                }
                
                .file-drop-zone .drop-text {
                    color: #6c757d;
                    font-size: 0.9rem;
                    margin-top: 10px;
                }
                
                .upload-progress-enhanced {
                    margin-top: 15px;
                    padding: 15px;
                    background: #f8f9fa;
                    border-radius: 8px;
                    border: 1px solid #dee2e6;
                }
                
                .progress-bar-enhanced {
                    height: 8px;
                    border-radius: 4px;
                    background: linear-gradient(90deg, #007bff, #0056b3);
                    transition: width 0.3s ease;
                }
                
                .upload-stats {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 10px;
                    font-size: 0.85rem;
                    color: #495057;
                }
                
                .upload-speed {
                    color: #28a745;
                    font-weight: 500;
                }
                
                .file-preview-enhanced {
                    margin-top: 15px;
                    padding: 15px;
                    background: #fff;
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                }
                
                .preview-thumbnail {
                    max-width: 150px;
                    max-height: 150px;
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }
            `;
            document.head.appendChild(style);
        }
        
        // إضافة نص الإرشاد
        const dropText = document.createElement('div');
        dropText.className = 'drop-text';
        dropText.innerHTML = '<i class="fas fa-cloud-upload-alt"></i> اسحب الملف هنا أو انقر للاختيار';
        container.appendChild(dropText);
        
        return container;
    }

    /**
     * إنشاء حاوية شريط التقدم
     */
    createProgressContainer() {
        const progressHtml = `
            <div id="enhanced-upload-progress" class="upload-progress-enhanced" style="display: none;">
                <div class="upload-stats">
                    <span class="file-info">
                        <i class="fas fa-file"></i>
                        <span id="upload-filename">اسم الملف</span>
                        <span id="upload-filesize" class="text-muted">(حجم الملف)</span>
                    </span>
                    <span class="upload-speed" id="upload-speed">0 KB/s</span>
                </div>
                <div class="progress" style="height: 8px;">
                    <div id="enhanced-progress-bar" class="progress-bar progress-bar-enhanced progress-bar-striped progress-bar-animated" 
                         role="progressbar" style="width: 0%"></div>
                </div>
                <div class="d-flex justify-content-between align-items-center mt-2">
                    <span id="upload-status" class="text-muted small">جاري الإعداد...</span>
                    <span id="upload-percentage" class="badge bg-primary">0%</span>
                </div>
                <div id="upload-eta" class="text-center small text-muted mt-1" style="display: none;">
                    الوقت المتبقي: <span id="eta-time">--:--</span>
                </div>
            </div>
        `;
        
        // إدراج شريط التقدم في النموذج
        const modal = document.getElementById('addContentModal');
        if (modal) {
            const modalBody = modal.querySelector('.modal-body');
            modalBody.insertAdjacentHTML('beforeend', progressHtml);
        }
    }

    /**
     * التحقق من صحة الملف
     */
    validateFile(file, contentType) {
        const errors = [];
        
        if (!file) {
            errors.push('لم يتم اختيار ملف');
            return errors;
        }

        // فحص الامتداد
        const extension = file.name.split('.').pop().toLowerCase();
        const allowedExtensions = this.options.allowedTypes[contentType] || [];
        
        if (!allowedExtensions.includes(extension)) {
            errors.push(`نوع الملف غير مدعوم. الأنواع المدعومة: ${allowedExtensions.join(', ')}`);
        }

        // فحص الحجم
        const sizeLimit = this.options.sizeLimits[contentType] || this.options.maxFileSize;
        if (file.size > sizeLimit) {
            const sizeMB = Math.round(sizeLimit / (1024 * 1024));
            errors.push(`حجم الملف كبير جداً. الحد الأقصى: ${sizeMB}MB`);
        }

        return errors;
    }

    /**
     * رفع ملف مع شريط التقدم
     */
    uploadFile(file, url, formData, onProgress, onComplete, onError) {
        const xhr = new XMLHttpRequest();
        const startTime = Date.now();
        let lastLoaded = 0;
        let lastTime = startTime;

        // إعداد شريط التقدم
        this.showProgress(file);

        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const currentTime = Date.now();
                const timeDiff = currentTime - lastTime;
                const loadedDiff = e.loaded - lastLoaded;
                
                // حساب السرعة
                const speed = timeDiff > 0 ? (loadedDiff / timeDiff) * 1000 : 0;
                
                // حساب النسبة المئوية
                const percentComplete = Math.round((e.loaded / e.total) * 100);
                
                // حساب الوقت المتبقي
                const remainingBytes = e.total - e.loaded;
                const eta = speed > 0 ? remainingBytes / speed : 0;
                
                // تحديث واجهة المستخدم
                this.updateProgress({
                    percent: percentComplete,
                    loaded: e.loaded,
                    total: e.total,
                    speed: speed,
                    eta: eta
                });
                
                lastLoaded = e.loaded;
                lastTime = currentTime;
                
                if (onProgress) onProgress(e);
            }
        });

        xhr.addEventListener('load', () => {
            if (xhr.status === 200 || xhr.status === 302) {
                this.showSuccess();
                if (onComplete) onComplete(xhr);
            } else if (xhr.status === 413) {
                this.showError('حجم الملف كبير جداً. يرجى المحاولة بملف أصغر أو التحقق من سرعة الإنترنت.');
                if (onError) onError(xhr);
            } else if (xhr.status === 408 || xhr.status === 0) {
                this.showError('انقطع الاتصال. يرجى التحقق من الإنترنت والمحاولة مرة أخرى.');
                if (onError) onError(xhr);
            } else {
                this.showError('حدث خطأ أثناء الرفع. يرجى المحاولة مرة أخرى.');
                if (onError) onError(xhr);
            }
        });

        xhr.addEventListener('error', () => {
            this.showError('فشل في الرفع. يرجى التحقق من اتصال الإنترنت.');
            if (onError) onError(xhr);
        });

        xhr.addEventListener('timeout', () => {
            this.showError('انتهت مهلة الرفع. سرعة الإنترنت بطيئة أو الملف كبير جداً.');
            if (onError) onError(xhr);
        });

        // إعداد المهلة الزمنية (10 دقائق للملفات الكبيرة)
        xhr.timeout = 10 * 60 * 1000;

        xhr.open('POST', url);
        xhr.send(formData);

        return xhr;
    }

    /**
     * إظهار شريط التقدم
     */
    showProgress(file) {
        const progressContainer = document.getElementById('enhanced-upload-progress');
        const filename = document.getElementById('upload-filename');
        const filesize = document.getElementById('upload-filesize');
        
        if (progressContainer) {
            progressContainer.style.display = 'block';
            filename.textContent = file.name;
            filesize.textContent = `(${this.formatFileSize(file.size)})`;
        }
    }

    /**
     * تحديث شريط التقدم
     */
    updateProgress(data) {
        const progressBar = document.getElementById('enhanced-progress-bar');
        const percentage = document.getElementById('upload-percentage');
        const status = document.getElementById('upload-status');
        const speed = document.getElementById('upload-speed');
        const etaContainer = document.getElementById('upload-eta');
        const etaTime = document.getElementById('eta-time');

        if (progressBar) {
            progressBar.style.width = `${data.percent}%`;
            progressBar.setAttribute('aria-valuenow', data.percent);
        }

        if (percentage) {
            percentage.textContent = `${data.percent}%`;
        }

        if (status) {
            status.textContent = `تم رفع ${this.formatFileSize(data.loaded)} من ${this.formatFileSize(data.total)}`;
        }

        if (speed) {
            speed.textContent = this.formatSpeed(data.speed);
        }

        if (data.eta > 0 && etaContainer && etaTime) {
            etaContainer.style.display = 'block';
            etaTime.textContent = this.formatTime(data.eta / 1000);
        }
    }

    /**
     * إظهار نجاح الرفع
     */
    showSuccess() {
        const status = document.getElementById('upload-status');
        const progressBar = document.getElementById('enhanced-progress-bar');
        
        if (status) {
            status.innerHTML = '<i class="fas fa-check-circle text-success"></i> تم الرفع بنجاح!';
        }
        
        if (progressBar) {
            progressBar.classList.remove('progress-bar-animated');
            progressBar.classList.add('bg-success');
        }
    }

    /**
     * إظهار خطأ في الرفع
     */
    showError(message) {
        const status = document.getElementById('upload-status');
        const progressBar = document.getElementById('enhanced-progress-bar');
        
        if (status) {
            status.innerHTML = `<i class="fas fa-exclamation-triangle text-danger"></i> ${message}`;
        }
        
        if (progressBar) {
            progressBar.classList.remove('progress-bar-animated');
            progressBar.classList.add('bg-danger');
        }
    }

    /**
     * إخفاء شريط التقدم
     */
    hideProgress() {
        const progressContainer = document.getElementById('enhanced-upload-progress');
        if (progressContainer) {
            progressContainer.style.display = 'none';
            
            // إعادة تعيين العناصر
            const progressBar = document.getElementById('enhanced-progress-bar');
            const percentage = document.getElementById('upload-percentage');
            const status = document.getElementById('upload-status');
            
            if (progressBar) {
                progressBar.style.width = '0%';
                progressBar.classList.remove('bg-success', 'bg-danger');
                progressBar.classList.add('progress-bar-animated');
            }
            
            if (percentage) percentage.textContent = '0%';
            if (status) status.textContent = 'جاري الإعداد...';
        }
    }

    /**
     * تنسيق حجم الملف
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * تنسيق السرعة
     */
    formatSpeed(bytesPerSecond) {
        if (bytesPerSecond === 0) return '0 KB/s';
        
        const k = 1024;
        const sizes = ['B/s', 'KB/s', 'MB/s'];
        const i = Math.floor(Math.log(bytesPerSecond) / Math.log(k));
        
        return parseFloat((bytesPerSecond / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    /**
     * تنسيق الوقت
     */
    formatTime(seconds) {
        if (seconds < 60) {
            return `${Math.round(seconds)}ث`;
        } else if (seconds < 3600) {
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = Math.round(seconds % 60);
            return `${minutes}د ${remainingSeconds}ث`;
        } else {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return `${hours}س ${minutes}د`;
        }
    }

    /**
     * إنشاء معاينة للملف
     */
    createFilePreview(file, contentType) {
        const previewContainer = document.getElementById('file-preview');
        if (!previewContainer) return;

        const previewContent = previewContainer.querySelector('#preview-content') || 
                              previewContainer.querySelector('.border');

        if (!previewContent) return;

        let previewHTML = '';

        if (contentType === 'image' && file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = (e) => {
                previewHTML = `
                    <div class="file-preview-enhanced text-center">
                        <img src="${e.target.result}" alt="معاينة الصورة" class="preview-thumbnail img-fluid">
                        <div class="mt-2">
                            <strong>${file.name}</strong><br>
                            <small class="text-muted">${this.formatFileSize(file.size)}</small>
                        </div>
                    </div>
                `;
                previewContent.innerHTML = previewHTML;
            };
            reader.readAsDataURL(file);
        } else {
            // معاينة عامة للملفات الأخرى
            let iconClass = 'fa-file';
            let colorClass = 'text-secondary';

            if (contentType === 'video') {
                iconClass = 'fa-file-video';
                colorClass = 'text-danger';
            } else if (contentType === 'audio') {
                iconClass = 'fa-file-audio';
                colorClass = 'text-warning';
            } else if (file.type.includes('pdf')) {
                iconClass = 'fa-file-pdf';
                colorClass = 'text-danger';
            } else if (file.type.includes('word')) {
                iconClass = 'fa-file-word';
                colorClass = 'text-primary';
            }

            previewHTML = `
                <div class="file-preview-enhanced d-flex align-items-center">
                    <i class="fas ${iconClass} fa-3x ${colorClass} me-3"></i>
                    <div>
                        <strong>${file.name}</strong><br>
                        <small class="text-muted">${this.formatFileSize(file.size)}</small><br>
                        <small class="text-muted">${file.type || 'نوع غير معروف'}</small>
                    </div>
                </div>
            `;
            previewContent.innerHTML = previewHTML;
        }

        previewContainer.style.display = 'block';
    }
}

// إنشاء مثيل عالمي
window.enhancedFileUpload = new EnhancedFileUpload();

// تهيئة عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', () => {
    window.enhancedFileUpload.init();
});
