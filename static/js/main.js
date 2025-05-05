// Main JavaScript functionality for Al-Hesa platform

document.addEventListener('DOMContentLoaded', function() {
  // Initialize theme
  initTheme();
  
  // Setup sidebar toggle
  setupSidebarToggle();
  
  // Setup dropdown menus
  setupDropdowns();
  
  // Initialize tooltips
  initTooltips();
  
  // Setup alerts auto-dismiss
  setupAlerts();
  
  // Sidebar Toggle
  const sidebarToggleTop = document.getElementById('sidebarToggleTop');
  const sidebar = document.querySelector('.sidebar');
  const body = document.body;
  
  // إنشاء عنصر overlay للخلفية
  const overlay = document.createElement('div');
  overlay.className = 'sidebar-overlay';
  body.appendChild(overlay);
  
  function toggleSidebar() {
      sidebar.classList.toggle('show');
      overlay.classList.toggle('show');
      body.style.overflow = sidebar.classList.contains('show') ? 'hidden' : '';
  }
  
  sidebarToggleTop.addEventListener('click', toggleSidebar);
  
  // إغلاق السايدبار عند النقر على الـ overlay
  overlay.addEventListener('click', toggleSidebar);
  
  // إغلاق السايدبار عند تغيير حجم النافذة إلى شاشة كبيرة
  window.addEventListener('resize', function() {
      if (window.innerWidth >= 768 && sidebar.classList.contains('show')) {
          toggleSidebar();
      }
  });
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

// Setup dropdown menus
function setupDropdowns() {
  const dropdowns = document.querySelectorAll('.dropdown-toggle');
  
  dropdowns.forEach(dropdown => {
    dropdown.addEventListener('click', function(e) {
      e.preventDefault();
      const menu = this.nextElementSibling;
      if (menu) {
        menu.classList.toggle('show');
      }
    });
  });
  
  // Close dropdown when clicking outside
  document.addEventListener('click', function(e) {
    if (!e.target.matches('.dropdown-toggle')) {
      const dropdowns = document.querySelectorAll('.dropdown-menu');
      dropdowns.forEach(dropdown => {
        if (dropdown.classList.contains('show')) {
          dropdown.classList.remove('show');
        }
      });
    }
  });
}

// Initialize tooltips
function initTooltips() {
  const tooltips = document.querySelectorAll('[data-toggle="tooltip"]');
  tooltips.forEach(tooltip => {
    const title = tooltip.getAttribute('title') || tooltip.getAttribute('data-original-title');
    if (title) {
      tooltip.setAttribute('data-original-title', title);
      tooltip.setAttribute('title', '');
      
      tooltip.addEventListener('mouseenter', function() {
        const tooltipId = 'tooltip-' + Math.random().toString(36).substring(2, 9);
        
        const tooltipEl = document.createElement('div');
        tooltipEl.className = 'tooltip fade show';
        tooltipEl.id = tooltipId;
        tooltipEl.innerHTML = `<div class="tooltip-inner">${title}</div>`;
        document.body.appendChild(tooltipEl);
        
        const rect = this.getBoundingClientRect();
        tooltipEl.style.top = (rect.top - tooltipEl.offsetHeight - 5) + 'px';
        tooltipEl.style.left = (rect.left + (rect.width / 2) - (tooltipEl.offsetWidth / 2)) + 'px';
        
        this.setAttribute('aria-describedby', tooltipId);
      });
      
      tooltip.addEventListener('mouseleave', function() {
        const tooltipId = this.getAttribute('aria-describedby');
        if (tooltipId) {
          const tooltipEl = document.getElementById(tooltipId);
          if (tooltipEl) {
            tooltipEl.remove();
          }
          this.removeAttribute('aria-describedby');
        }
      });
    }
  });
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
