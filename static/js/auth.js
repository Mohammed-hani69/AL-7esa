// Auth related functionality

// Initialize phone authentication
// Using window object to declare globally
window.initPhoneAuth = (phoneInputId, recaptchaContainerId, submitBtnId) => {
  const phoneInput = document.getElementById(phoneInputId);
  const submitBtn = document.getElementById(submitBtnId);
  
  // Format phone number with Saudi Arabia prefix if needed
  phoneInput.addEventListener('blur', () => {
    let phone = phoneInput.value.trim();
    
    // Add Saudi Arabia code if not present
    if (phone && !phone.startsWith('+')) {
      if (phone.startsWith('0')) {
        phone = '+966' + phone.substring(1);
      } else {
        phone = '+966' + phone;
      }
      phoneInput.value = phone;
    }
  });
  
  // Setup submit event
  if (submitBtn) {
    submitBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      
      const phone = phoneInput.value.trim();
      if (!phone) {
        showAlert('يرجى إدخال رقم الهاتف', 'danger');
        return;
      }
      
      try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> جاري التحقق...';
        
        // Initialize Firebase if not already done
        initFirebase();
        
        // Start phone verification
        const confirmationResult = await setupPhoneAuth(phone, recaptchaContainerId);
        
        // Store confirmation result for later use
        window.confirmationResult = confirmationResult;
        
        // Show verification code input
        document.getElementById('phone-auth-step-1').classList.add('d-none');
        document.getElementById('phone-auth-step-2').classList.remove('d-none');
        
      } catch (error) {
        console.error('Error during phone auth:', error);
        showAlert('حدث خطأ أثناء التحقق من رقم الهاتف: ' + error.message, 'danger');
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'إرسال';
      }
    });
  }
};

// Verify confirmation code
window.verifyCode = async (codeInputId, verifyBtnId) => {
  const codeInput = document.getElementById(codeInputId);
  const verifyBtn = document.getElementById(verifyBtnId);
  
  if (!window.confirmationResult) {
    showAlert('حدث خطأ. يرجى المحاولة مرة أخرى', 'danger');
    return;
  }
  
  const code = codeInput.value.trim();
  if (!code) {
    showAlert('يرجى إدخال رمز التحقق', 'danger');
    return;
  }
  
  try {
    verifyBtn.disabled = true;
    verifyBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> جاري التحقق...';
    
    // Verify the code
    const result = await window.confirmationResult.confirm(code);
    
    // User is signed in
    const user = result.user;
    
    // Get user token
    const idToken = await user.getIdToken();
    
    // Send token to server for verification and session creation
    await verifyTokenWithServer(idToken);
    
  } catch (error) {
    console.error('Error during code verification:', error);
    showAlert('رمز التحقق غير صحيح. يرجى المحاولة مرة أخرى', 'danger');
    verifyBtn.disabled = false;
    verifyBtn.innerHTML = 'تحقق';
  }
};

// Verify token with server
window.verifyTokenWithServer = async (idToken) => {
  try {
    const response = await fetch('/auth/verify-token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ idToken }),
    });
    
    const data = await response.json();
    
    if (data.error) {
      showAlert(data.error, 'danger');
      return;
    }
    
    // Success! Redirect to appropriate page
    if (data.redirect) {
      window.location.href = data.redirect;
    } else {
      window.location.href = '/';
    }
    
  } catch (error) {
    console.error('Error verifying token with server:', error);
    showAlert('حدث خطأ أثناء التحقق من الحساب. يرجى المحاولة مرة أخرى', 'danger');
  }
};

// Logout function
window.logout = async () => {
  try {
    // Initialize Firebase if not already done
    initFirebase();
    
    // Sign out from Firebase
    await signOut();
    
    // Redirect to server logout endpoint
    window.location.href = '/auth/logout';
  } catch (error) {
    console.error('Error during logout:', error);
    showAlert('حدث خطأ أثناء تسجيل الخروج. يرجى المحاولة مرة أخرى', 'danger');
  }
};

// Show alert message
const showAlert = (message, type = 'info') => {
  const alertsContainer = document.getElementById('alerts-container');
  if (!alertsContainer) return;
  
  const alert = document.createElement('div');
  alert.className = `alert alert-${type} alert-dismissible fade show`;
  alert.innerHTML = `
    ${message}
    <button type="button" class="close" data-dismiss="alert" aria-label="Close">
      <span aria-hidden="true">&times;</span>
    </button>
  `;
  
  alertsContainer.appendChild(alert);
  
  // Auto-dismiss after 5 seconds
  setTimeout(() => {
    alert.classList.remove('show');
    setTimeout(() => {
      alert.remove();
    }, 150);
  }, 5000);
};
