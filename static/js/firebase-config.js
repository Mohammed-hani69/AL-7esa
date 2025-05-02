// Firebase configuration
const initFirebase = () => {
  // Check if firebase is already initialized
  if (firebase.apps.length === 0) {
    const firebaseConfig = {
      apiKey: document.getElementById('firebase-api-key').value,
      authDomain: document.getElementById('firebase-project-id').value + ".firebaseapp.com",
      projectId: document.getElementById('firebase-project-id').value,
      storageBucket: document.getElementById('firebase-project-id').value + ".appspot.com",
      messagingSenderId: document.getElementById('firebase-messaging-sender-id').value || "893628750909",
      appId: document.getElementById('firebase-app-id').value,
      measurementId: document.getElementById('firebase-measurement-id').value || "G-B026ZL6KXG"
    };
    
    // Initialize Firebase
    firebase.initializeApp(firebaseConfig);
    
    // Initialize Analytics if available
    if (typeof firebase.analytics === 'function') {
      firebase.analytics();
    }
    
    console.log("Firebase initialized");
  }
  
  return firebase;
};

// Initialize Firebase Auth
const initAuth = () => {
  const auth = firebase.auth();
  
  // Set language to Arabic
  auth.languageCode = 'ar';
  
  return auth;
};

// Initialize Firestore
const initFirestore = () => {
  return firebase.firestore();
};

// Initialize Cloud Messaging
const initMessaging = () => {
  if (firebase.messaging.isSupported()) {
    return firebase.messaging();
  }
  return null;
};

// Setup phone authentication
const setupPhoneAuth = (phoneNumber, recaptchaContainerId) => {
  const auth = firebase.auth();
  
  // Create recaptcha verifier
  window.recaptchaVerifier = new firebase.auth.RecaptchaVerifier(recaptchaContainerId, {
    'size': 'normal',
    'callback': (response) => {
      // reCAPTCHA solved, enable sign-in button
      document.getElementById('auth-submit-btn').disabled = false;
    },
    'expired-callback': () => {
      // Response expired. Ask user to solve reCAPTCHA again.
      document.getElementById('auth-submit-btn').disabled = true;
    }
  });
  
  return auth.signInWithPhoneNumber(phoneNumber, window.recaptchaVerifier);
};

// Sign out user
const signOut = () => {
  return firebase.auth().signOut()
    .then(() => {
      console.log('User signed out successfully');
      return true;
    })
    .catch((error) => {
      console.error('Error signing out:', error);
      return false;
    });
};

// Get current user
const getCurrentUser = () => {
  return firebase.auth().currentUser;
};

// Get user token
const getUserToken = async () => {
  const user = getCurrentUser();
  if (!user) return null;
  
  try {
    return await user.getIdToken(true);
  } catch (error) {
    console.error('Error getting user token:', error);
    return null;
  }
};

// Listen for auth state changes
const onAuthStateChanged = (callback) => {
  return firebase.auth().onAuthStateChanged(callback);
};
