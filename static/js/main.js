// وظائف مساعدة للتطبيق
document.addEventListener('DOMContentLoaded', function() {
    // التبديل بين الثيمات (داكن/فاتح)
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', toggleTheme);
    }

    // تبديل القائمة الجانبية
    const sidebarToggleBtn = document.getElementById('sidebarToggleBtn');
    if (sidebarToggleBtn) {
        const sidebar = document.querySelector('.sidebar');
        sidebarToggleBtn.addEventListener('click', function() {
            if (sidebar) {
                sidebar.classList.toggle('show');
            }
        });
    }

    // تنشيط توست آلياً إذا وجد
    const toastElements = document.querySelectorAll('.toast');
    if (toastElements.length > 0 && typeof bootstrap !== 'undefined') {
        toastElements.forEach(toast => {
            new bootstrap.Toast(toast).show();
        });
    }

    // تنشيط التلميحات (tooltips) إذا وجدت
    if (typeof bootstrap !== 'undefined' && typeof bootstrap.Tooltip !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        if (tooltipTriggerList.length > 0) {
            tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
        }
    }

    // وظائف القائمة المنسدلة
    const dropdownToggles = document.querySelectorAll('.dropdown-toggle');
    if (dropdownToggles.length > 0) {
        dropdownToggles.forEach(toggle => {
            toggle.addEventListener('click', function(e) {
                e.preventDefault();
                const dropdownMenu = this.nextElementSibling;
                if (dropdownMenu) {
                    dropdownMenu.classList.toggle('show');
                }
            });
        });

        // إغلاق القائمة المنسدلة عند النقر خارجها
        document.addEventListener('click', function(e) {
            if (!e.target.matches('.dropdown-toggle')) {
                const dropdowns = document.querySelectorAll('.dropdown-menu.show');
                dropdowns.forEach(dropdown => {
                    dropdown.classList.remove('show');
                });
            }
        });
    }

    // تنشيط عناصر المودال إذا وجدت
    if (typeof bootstrap !== 'undefined' && typeof bootstrap.Modal !== 'undefined') {
        const modalTriggers = document.querySelectorAll('[data-bs-toggle="modal"]');
        if (modalTriggers.length > 0) {
            modalTriggers.forEach(trigger => {
                trigger.addEventListener('click', function() {
                    const targetModal = document.querySelector(this.getAttribute('data-bs-target'));
                    if (targetModal) {
                        const modal = new bootstrap.Modal(targetModal);
                        modal.show();
                    }
                });
            });
        }
    }

    // معالجة النقر على أزرار التبديل في الأقسام المبوبة
    const tabButtons = document.querySelectorAll('[data-bs-toggle="tab"]');
    if (tabButtons.length > 0) {
        tabButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                const targetId = this.getAttribute('data-bs-target') || this.getAttribute('href');
                if (targetId) {
                    // إزالة الكلاس active من كل التبويبات
                    document.querySelectorAll('.tab-pane').forEach(tab => {
                        tab.classList.remove('show', 'active');
                    });
                    document.querySelectorAll('.nav-link').forEach(link => {
                        link.classList.remove('active');
                    });

                    // إضافة الكلاس active للتبويب المختار
                    const target = document.querySelector(targetId);
                    if (target) {
                        target.classList.add('show', 'active');
                        this.classList.add('active');
                    }
                }
            });
        });
    }
});

/**
 * تبديل بين الثيمات (داكن/فاتح)
 */
function toggleTheme() {
    const body = document.body;
    const currentTheme = body.getAttribute('data-theme') || 'light';
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';

    body.setAttribute('data-theme', newTheme);

    // حفظ التفضيل في localStorage
    if (typeof localStorage !== 'undefined') {
        localStorage.setItem('theme', newTheme);
    }

    // تغيير أيقونة زر التبديل
    const themeIcon = document.getElementById('themeIcon');
    if (themeIcon) {
        if (newTheme === 'dark') {
            themeIcon.classList.remove('fa-moon');
            themeIcon.classList.add('fa-sun');
        } else {
            themeIcon.classList.remove('fa-sun');
            themeIcon.classList.add('fa-moon');
        }
    }
}

/**
 * نسخ النص إلى الحافظة
 * @param {string} text - النص المراد نسخه
 * @param {HTMLElement} button - زر النسخ (اختياري)
 */
function copyToClipboard(text, button) {
    if (typeof navigator.clipboard !== 'undefined') {
        navigator.clipboard.writeText(text).then(() => {
            if (button) {
                const originalText = button.innerHTML;
                button.innerHTML = 'تم النسخ!';
                setTimeout(() => {
                    button.innerHTML = originalText;
                }, 2000);
            }
        }).catch(err => {
            console.error('فشل نسخ النص: ', err);
        });
    } else {
        // دعم احتياطي لمتصفحات أقدم
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();

        try {
            document.execCommand('copy');
            if (button) {
                const originalText = button.innerHTML;
                button.innerHTML = 'تم النسخ!';
                setTimeout(() => {
                    button.innerHTML = originalText;
                }, 2000);
            }
        } catch (err) {
            console.error('فشل نسخ النص: ', err);
        }

        document.body.removeChild(textArea);
    }
}

/**
 * تحقق من حالة الثيم عند تحميل الصفحة
 */
(function() {
    if (typeof localStorage !== 'undefined') {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            document.body.setAttribute('data-theme', savedTheme);

            // تحديث أيقونة زر التبديل إذا وجدت
            const themeIcon = document.getElementById('themeIcon');
            if (themeIcon) {
                if (savedTheme === 'dark') {
                    themeIcon.classList.remove('fa-moon');
                    themeIcon.classList.add('fa-sun');
                } else {
                    themeIcon.classList.remove('fa-sun');
                    themeIcon.classList.add('fa-moon');
                }
            }
        }
    }
})();

// إعداد التحقق من وجود أخطاء في الصفحة
window.addEventListener('error', function(e) {
    console.error('حدث خطأ في JavaScript:', e.message);
});

// Initialize theme based on user preference or system setting
function initTheme() {
  const storedTheme = localStorage.getItem('theme');
  const systemDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const themeSwitcher = document.getElementById('theme-switcher');
  
  if (storedTheme === 'dark' || (!storedTheme && systemDarkMode)) {
    document.documentElement.setAttribute('data-theme', 'dark');
    if (themeSwitcher) themeSwitcher.checked = true;
  } else {
    document.documentElement.setAttribute('data-theme', 'light');
    if (themeSwitcher) themeSwitcher.checked = false;
  }
  
  // Setup theme switcher
  if (themeSwitcher) {
    themeSwitcher.addEventListener('change', function() {
      if (this.checked) {
        document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('theme', 'dark');
      } else {
        document.documentElement.setAttribute('data-theme', 'light');
        localStorage.setItem('theme', 'light');
      }
    });
  }
}

// Setup sidebar toggle functionality
function setupSidebarToggle() {
  const sidebarToggle = document.getElementById('sidebar-toggle');
  
  if (sidebarToggle) {
    sidebarToggle.addEventListener('click', function(e) {
      e.preventDefault();
      document.body.classList.toggle('sidebar-toggled');
      const sidebar = document.querySelector('.sidebar');
      if (sidebar) sidebar.classList.toggle('toggled');
      
      // Save preference
      if (document.body.classList.contains('sidebar-toggled')) {
        localStorage.setItem('sidebar', 'collapsed');
      } else {
        localStorage.setItem('sidebar', 'expanded');
      }
    });
    
    // Apply saved state
    const sidebarState = localStorage.getItem('sidebar');
    if (sidebarState === 'collapsed') {
      document.body.classList.add('sidebar-toggled');
      const sidebar = document.querySelector('.sidebar');
      if (sidebar) sidebar.classList.add('toggled');
    }
    
    // Auto-collapse sidebar on small screens
    if (window.innerWidth < 768) {
      document.body.classList.add('sidebar-toggled');
      const sidebar = document.querySelector('.sidebar');
      if (sidebar) sidebar.classList.add('toggled');
    }
  }
}


// Setup alerts auto-dismiss
function setupAlerts() {
  const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
  
  alerts.forEach(alert => {
    setTimeout(() => {
      const closeBtn = alert.querySelector('.close');
      if (closeBtn) {
        closeBtn.click();
      } else {
        alert.classList.add('fade');
        setTimeout(() => {
          alert.remove();
        }, 150);
      }
    }, 5000);
  });
  
  // Setup close buttons
  const closeButtons = document.querySelectorAll('.alert .close');
  closeButtons.forEach(button => {
    button.addEventListener('click', function() {
      const alert = this.closest('.alert');
      alert.classList.remove('show');
      setTimeout(() => {
        alert.remove();
      }, 150);
    });
  });
}

// Generate a random classroom code
function generateClassroomCode(length = 6) {
  const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  let result = '';
  
  for (let i = 0; i < length; i++) {
    result += characters.charAt(Math.floor(Math.random() * characters.length));
  }
  
  return result;
}

// Copy text to clipboard
function copyToClipboard(text, messageElement) {
  navigator.clipboard.writeText(text)
    .then(() => {
      if (messageElement) {
        const originalText = messageElement.innerHTML;
        messageElement.innerHTML = 'تم النسخ!';
        
        setTimeout(() => {
          messageElement.innerHTML = originalText;
        }, 2000);
      }
    })
    .catch(err => {
      console.error('Failed to copy text: ', err);
    });
}

// Format date and time
function formatDateTime(dateString) {
  if (!dateString) return '';
  
  const date = new Date(dateString);
  const options = { 
    year: 'numeric', 
    month: 'short', 
    day: 'numeric', 
    hour: '2-digit', 
    minute: '2-digit' 
  };
  
  return date.toLocaleDateString('ar-SA', options);
}

// Format date only
function formatDate(dateString) {
  if (!dateString) return '';
  
  const date = new Date(dateString);
  const options = { 
    year: 'numeric', 
    month: 'short', 
    day: 'numeric'
  };
  
  return date.toLocaleDateString('ar-SA', options);
}

// Calculate time remaining
function getTimeRemaining(endtime) {
  const total = Date.parse(endtime) - Date.parse(new Date());
  const seconds = Math.floor((total / 1000) % 60);
  const minutes = Math.floor((total / 1000 / 60) % 60);
  const hours = Math.floor((total / (1000 * 60 * 60)) % 24);
  const days = Math.floor(total / (1000 * 60 * 60 * 24));
  
  return {
    total,
    days,
    hours,
    minutes,
    seconds
  };
}

// Show a confirmation dialog
function confirmAction(message, callback) {
  if (confirm(message)) {
    callback();
  }
}

// Debounce function to limit how often a function can be called
function debounce(func, wait) {
  let timeout;
  
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Show a notification
function showNotification(title, message, type = 'info') {
  // Check if the browser supports notifications
  if ('Notification' in window) {
    // Check if permission is already granted
    if (Notification.permission === 'granted') {
      createNotification(title, message, type);
    } 
    // Otherwise, request permission
    else if (Notification.permission !== 'denied') {
      Notification.requestPermission().then(permission => {
        if (permission === 'granted') {
          createNotification(title, message, type);
        }
      });
    }
  }
  
  // Create an in-app notification as fallback
  const notificationContainer = document.getElementById('notification-container');
  if (notificationContainer) {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show`;
    notification.innerHTML = `
      <strong>${title}</strong><br>${message}
      <button type="button" class="close" data-dismiss="alert" aria-label="Close">
        <span aria-hidden="true">&times;</span>
      </button>
    `;
    
    notificationContainer.appendChild(notification);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
      notification.classList.remove('show');
      setTimeout(() => {
        notification.remove();
      }, 150);
    }, 5000);
  }
}

// Create a browser notification
function createNotification(title, message, type) {
  const notification = new Notification(title, {
    body: message,
    icon: '/static/img/logo.svg'
  });
  
  notification.onclick = function() {
    window.focus();
    this.close();
  };
  
  setTimeout(notification.close.bind(notification), 5000);
}