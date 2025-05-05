// وظائف مساعدة للتطبيق
document.addEventListener('DOMContentLoaded', function() {
    // تهيئة عناصر واجهة المستخدم
    setupSidebar();
    setupDropdowns();
    setupTooltips();
    setupFormValidation();
    setupThemeToggle();

    // دعم الرجوع للخلف في المتصفح
    setupBackButton();
});

// إعداد الشريط الجانبي
function setupSidebar() {
    const sidebarToggle = document.querySelector('#sidebarToggle');
    const sidebar = document.querySelector('.sidebar');

    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function(e) {
            e.preventDefault();
            document.body.classList.toggle('sidebar-toggled');
            sidebar.classList.toggle('toggled');
        });
    }

    // إغلاق الشريط الجانبي عند تصغير النافذة
    window.addEventListener('resize', function() {
        if (window.innerWidth < 768 && sidebar) {
            document.body.classList.add('sidebar-toggled');
            sidebar.classList.add('toggled');
        }
    });

    // التحقق من حجم النافذة عند التحميل
    if (window.innerWidth < 768 && sidebar) {
        document.body.classList.add('sidebar-toggled');
        sidebar.classList.add('toggled');
    }
}

// إعداد القوائم المنسدلة
function setupDropdowns() {
    const dropdowns = document.querySelectorAll('.dropdown-toggle');

    if (dropdowns && dropdowns.length > 0) {
        dropdowns.forEach(dropdown => {
            dropdown.addEventListener('click', function(e) {
                e.preventDefault();
                const menu = this.nextElementSibling;
                if (menu) {
                    menu.classList.toggle('show');
                }
            });
        });

        // إغلاق القائمة عند النقر خارجها
        document.addEventListener('click', function(e) {
            if (!e.target.matches('.dropdown-toggle')) {
                const dropdowns = document.querySelectorAll('.dropdown-menu.show');
                if (dropdowns && dropdowns.length > 0) {
                    dropdowns.forEach(dropdown => {
                        dropdown.classList.remove('show');
                    });
                }
            }
        });
    }
}

// إعداد التلميحات
function setupTooltips() {
    const tooltips = document.querySelectorAll('[data-toggle="tooltip"]');
    if (tooltips && tooltips.length > 0) {
        tooltips.forEach(tooltip => {
            tooltip.title = tooltip.getAttribute('data-title') || tooltip.title;
            tooltip.addEventListener('mouseenter', showTooltip);
            tooltip.addEventListener('mouseleave', hideTooltip);
        });
    }
}

// عرض التلميح
function showTooltip(e) {
    const element = e.target;
    const title = element.getAttribute('data-title') || element.title;

    if (!title) return;

    const tooltipEl = document.createElement('div');
    tooltipEl.className = 'tooltip';
    tooltipEl.innerHTML = `<div class="tooltip-inner">${title}</div>`;
    document.body.appendChild(tooltipEl);

    const rect = element.getBoundingClientRect();
    const tooltipRect = tooltipEl.getBoundingClientRect();

    tooltipEl.style.position = 'absolute';
    tooltipEl.style.top = `${rect.top - tooltipRect.height - 5}px`;
    tooltipEl.style.left = `${rect.left + (rect.width / 2) - (tooltipRect.width / 2)}px`;
    tooltipEl.style.zIndex = 1070;

    element._tooltip = tooltipEl;
}

// إخفاء التلميح
function hideTooltip(e) {
    const element = e.target;
    if (element._tooltip) {
        element._tooltip.remove();
        delete element._tooltip;
    }
}

// التحقق من صحة النماذج
function setupFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');

    if (forms && forms.length > 0) {
        forms.forEach(form => {
            form.addEventListener('submit', function(e) {
                if (!form.checkValidity()) {
                    e.preventDefault();
                    e.stopPropagation();
                }
                form.classList.add('was-validated');
            }, false);
        });
    }
}

// تبديل السمة (داكن/فاتح)
function setupThemeToggle() {
    const themeToggle = document.querySelector('#themeToggle');

    if (themeToggle) {
        // استرجاع السمة من التخزين المحلي
        const currentTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', currentTheme);

        if (currentTheme === 'dark') {
            themeToggle.checked = true;
        }

        themeToggle.addEventListener('change', function() {
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

// دعم زر الرجوع للخلف
function setupBackButton() {
    const backButtons = document.querySelectorAll('.back-button');

    if (backButtons && backButtons.length > 0) {
        backButtons.forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                window.history.back();
            });
        });
    }
}

// التحقق من وجود أخطاء في الصفحة
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