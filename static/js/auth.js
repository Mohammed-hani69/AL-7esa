// Auth related functionality

// Initialize Firebase when page loads
let firebaseApp = null;
let firebaseAuth = null;

// Firebase configuration
const firebaseConfig = {
    apiKey: "AIzaSyCB_GPRRlb6BCe1Mlv7rTIbtnD-Y3vpAj8",
    authDomain: "al-7esa.firebaseapp.com",
    projectId: "al-7esa",
    storageBucket: "al-7esa.appspot.com",
    messagingSenderId: "893628750909",
    appId: "1:893628750909:web:3cd09924c12987b3ef9e54"
};

// Initialize Firebase
function initFirebase() {
    try {
        if (!firebaseApp && typeof firebase !== 'undefined') {
            firebaseApp = firebase.initializeApp(firebaseConfig);
            firebaseAuth = firebase.auth();
            firebaseAuth.languageCode = 'ar';
            console.log("Firebase initialized successfully");
            return firebaseApp;
        }
        return firebaseApp;
    } catch (error) {
        console.error("Error initializing Firebase:", error);
        return null;
    }
}

// Setup phone authentication
async function setupPhoneAuth(phoneNumber, recaptchaContainerId) {
    try {
        if (!firebaseAuth) {
            throw new Error('Firebase Auth not initialized');
        }

        // Create recaptcha verifier
        window.recaptchaVerifier = new firebase.auth.RecaptchaVerifier(recaptchaContainerId, {
            'size': 'normal',
            'callback': (response) => {
                console.log('reCAPTCHA solved');
            },
            'expired-callback': () => {
                console.warn('reCAPTCHA expired');
            }
        });

        return await firebaseAuth.signInWithPhoneNumber(phoneNumber, window.recaptchaVerifier);
    } catch (error) {
        console.error("Error setting up phone auth:", error);
        throw error;
    }
}

// Initialize phone authentication
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
      }        try {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> جاري التحقق...';
            
            // Initialize Firebase if not already done
            const app = initFirebase();
            if (!app) {
                throw new Error('تعذر تهيئة Firebase. يرجى التحقق من إعدادات الموقع.');
            }
            
            // Start phone verification
            const confirmationResult = await setupPhoneAuth(phone, recaptchaContainerId);
            
            // Store confirmation result for later use
            window.confirmationResult = confirmationResult;
        
        // Show verification code input
        document.getElementById('phone-auth-step-1').classList.add('d-none');
        document.getElementById('phone-auth-step-2').classList.remove('d-none');
        
      } catch (error) {
        console.error('Error during phone auth:', error);
        let errorMessage = 'حدث خطأ أثناء التحقق من رقم الهاتف';
        
        if (error.code === 'auth/invalid-api-key') {
          errorMessage = 'خطأ في مفتاح API. يرجى التحقق من إعدادات الموقع.';
        } else if (error.message) {
          errorMessage += ': ' + error.message;
        }
        
        showAlert(errorMessage, 'danger');
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
        // Make sure Firebase is initialized
        if (!firebaseAuth) {
            initFirebase();
        }
        
        // Sign out from Firebase
        if (firebaseAuth) {
            await firebaseAuth.signOut();
        }
        
        // Redirect to server logout endpoint
        window.location.href = '/logout';
    } catch (error) {
        console.error('Error during logout:', error);
        showAlert('حدث خطأ أثناء تسجيل الخروج. يرجى المحاولة مرة أخرى', 'danger');
    }
};

// Show alert message
window.showAlert = (message, type = 'info') => {
    // Create alert container if it doesn't exist
    let alertsContainer = document.getElementById('alerts-container');
    if (!alertsContainer) {
        alertsContainer = document.createElement('div');
        alertsContainer.id = 'alerts-container';
        alertsContainer.style.position = 'fixed';
        alertsContainer.style.top = '20px';
        alertsContainer.style.right = '20px';
        alertsContainer.style.zIndex = '9999';
        alertsContainer.style.maxWidth = '400px';
        document.body.appendChild(alertsContainer);
    }
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.style.marginBottom = '10px';
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    alertsContainer.appendChild(alert);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alert.classList.remove('show');
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 150);
    }, 5000);
};
