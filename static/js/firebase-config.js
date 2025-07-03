/**
 * Firebase Configuration and Initialization
 * Unified Firebase setup for the AL-7esa platform
 */

// Default Firebase configuration
const DEFAULT_FIREBASE_CONFIG = {
    apiKey: "AIzaSyCB_GPRRlb6BCe1Mlv7rTIbtnD-Y3vpAj8",
    authDomain: "al-7esa.firebaseapp.com",
    projectId: "al-7esa",
    storageBucket: "al-7esa.appspot.com",
    messagingSenderId: "893628750909",
    appId: "1:893628750909:web:3cd09924c12987b3ef9e54",
    measurementId: "G-B026ZL6KXG",
    databaseURL: "https://al-7esa-default-rtdb.firebaseio.com"
};

// Global Firebase instances
let firebaseApp = null;
let firebaseAuth = null;
let firebaseFirestore = null;
let firebaseDatabase = null;
let firebaseMessaging = null;

/**
 * Initialize Firebase with configuration
 * @param {Object} config - Firebase configuration object
 * @returns {Object} Firebase app instance
 */
const initFirebase = (config = null) => {
    try {
        // Use provided config or default
        const firebaseConfig = config || DEFAULT_FIREBASE_CONFIG;

        // Check if Firebase is already initialized
        if (firebase.apps.length === 0) {
            firebaseApp = firebase.initializeApp(firebaseConfig);
            console.log("Firebase initialized successfully");
        } else {
            firebaseApp = firebase.app();
            console.log("Firebase already initialized");
        }

        return firebaseApp;
    } catch (error) {
        console.error("Error initializing Firebase:", error);
        return null;
    }
};

/**
 * Initialize Firebase Authentication
 * @returns {Object} Firebase Auth instance
 */
const initAuth = () => {
    try {
        if (!firebaseApp) {
            initFirebase();
        }

        firebaseAuth = firebase.auth();

        // Set language to Arabic
        firebaseAuth.languageCode = 'ar';

        // Configure auth settings
        firebaseAuth.settings = {
            appVerificationDisabledForTesting: false
        };

        console.log("Firebase Auth initialized successfully");
        return firebaseAuth;
    } catch (error) {
        console.error("Error initializing Firebase Auth:", error);
        return null;
    }
};

/**
 * Initialize Firestore
 * @returns {Object} Firestore instance
 */
const initFirestore = () => {
    try {
        if (!firebaseApp) {
            initFirebase();
        }

        firebaseFirestore = firebase.firestore();

        // Enable offline persistence
        firebaseFirestore.enablePersistence({
            synchronizeTabs: true
        }).catch((err) => {
            if (err.code === 'failed-precondition') {
                console.warn('Multiple tabs open, persistence can only be enabled in one tab at a time.');
            } else if (err.code === 'unimplemented') {
                console.warn('The current browser does not support all of the features required to enable persistence');
            }
        });

        console.log("Firestore initialized successfully");
        return firebaseFirestore;
    } catch (error) {
        console.error("Error initializing Firestore:", error);
        return null;
    }
};

/**
 * Initialize Realtime Database
 * @returns {Object} Database instance
 */
const initDatabase = () => {
    try {
        if (!firebaseApp) {
            initFirebase();
        }

        firebaseDatabase = firebase.database();

        // Enable offline persistence
        firebase.database().setPersistenceEnabled(true);

        console.log("Firebase Realtime Database initialized successfully");
        return firebaseDatabase;
    } catch (error) {
        console.error("Error initializing Firebase Database:", error);
        return null;
    }
};

/**
 * Initialize Cloud Messaging
 * @returns {Object} Messaging instance or null
 */
const initMessaging = () => {
    try {
        if (!firebaseApp) {
            initFirebase();
        }

        if (firebase.messaging.isSupported()) {
            firebaseMessaging = firebase.messaging();
            console.log("Firebase Messaging initialized successfully");
            return firebaseMessaging;
        } else {
            console.warn("Firebase Messaging is not supported in this browser");
            return null;
        }
    } catch (error) {
        console.error("Error initializing Firebase Messaging:", error);
        return null;
    }
};

/**
 * Setup phone authentication
 * @param {string} phoneNumber - Phone number to authenticate
 * @param {string} recaptchaContainerId - ID of the reCAPTCHA container
 * @returns {Promise} Authentication promise
 */
const setupPhoneAuth = (phoneNumber, recaptchaContainerId) => {
    try {
        const auth = firebaseAuth || initAuth();

        // Create recaptcha verifier
        window.recaptchaVerifier = new firebase.auth.RecaptchaVerifier(recaptchaContainerId, {
            'size': 'normal',
            'callback': (response) => {
                // reCAPTCHA solved, enable sign-in button
                const submitBtn = document.getElementById('auth-submit-btn');
                if (submitBtn) submitBtn.disabled = false;
                console.log('reCAPTCHA solved');
            },
            'expired-callback': () => {
                // Response expired. Ask user to solve reCAPTCHA again.
                const submitBtn = document.getElementById('auth-submit-btn');
                if (submitBtn) submitBtn.disabled = true;
                console.warn('reCAPTCHA expired');
            }
        });

        return auth.signInWithPhoneNumber(phoneNumber, window.recaptchaVerifier);
    } catch (error) {
        console.error("Error setting up phone auth:", error);
        throw error;
    }
};

/**
 * Firestore Helper Functions
 */

/**
 * Create a document in Firestore
 * @param {string} collection - Collection name
 * @param {string} docId - Document ID (optional)
 * @param {Object} data - Document data
 * @returns {Promise} Promise with document reference
 */
const createFirestoreDocument = async (collection, docId, data) => {
    try {
        const db = firebaseFirestore || initFirestore();

        if (docId) {
            await db.collection(collection).doc(docId).set(data);
            console.log(`Document created: ${collection}/${docId}`);
            return { id: docId };
        } else {
            const docRef = await db.collection(collection).add(data);
            console.log(`Document created: ${collection}/${docRef.id}`);
            return docRef;
        }
    } catch (error) {
        console.error("Error creating document:", error);
        throw error;
    }
};

/**
 * Update a document in Firestore
 * @param {string} collection - Collection name
 * @param {string} docId - Document ID
 * @param {Object} data - Data to update
 * @returns {Promise} Promise
 */
const updateFirestoreDocument = async (collection, docId, data) => {
    try {
        const db = firebaseFirestore || initFirestore();
        await db.collection(collection).doc(docId).update(data);
        console.log(`Document updated: ${collection}/${docId}`);
    } catch (error) {
        console.error("Error updating document:", error);
        throw error;
    }
};

/**
 * Get a document from Firestore
 * @param {string} collection - Collection name
 * @param {string} docId - Document ID
 * @returns {Promise} Promise with document data
 */
const getFirestoreDocument = async (collection, docId) => {
    try {
        const db = firebaseFirestore || initFirestore();
        const doc = await db.collection(collection).doc(docId).get();

        if (doc.exists) {
            return { id: doc.id, ...doc.data() };
        } else {
            console.log(`Document not found: ${collection}/${docId}`);
            return null;
        }
    } catch (error) {
        console.error("Error getting document:", error);
        throw error;
    }
};

/**
 * Delete a document from Firestore
 * @param {string} collection - Collection name
 * @param {string} docId - Document ID
 * @returns {Promise} Promise
 */
const deleteFirestoreDocument = async (collection, docId) => {
    try {
        const db = firebaseFirestore || initFirestore();
        await db.collection(collection).doc(docId).delete();
        console.log(`Document deleted: ${collection}/${docId}`);
    } catch (error) {
        console.error("Error deleting document:", error);
        throw error;
    }
};

/**
 * Listen to real-time updates for a document
 * @param {string} collection - Collection name
 * @param {string} docId - Document ID
 * @param {Function} callback - Callback function for updates
 * @returns {Function} Unsubscribe function
 */
const listenToFirestoreDocument = (collection, docId, callback) => {
    try {
        const db = firebaseFirestore || initFirestore();
        return db.collection(collection).doc(docId).onSnapshot(callback);
    } catch (error) {
        console.error("Error listening to document:", error);
        throw error;
    }
};

/**
 * Listen to real-time updates for a collection
 * @param {string} collection - Collection name
 * @param {Function} callback - Callback function for updates
 * @param {Object} queryOptions - Query options (optional)
 * @returns {Function} Unsubscribe function
 */
const listenToFirestoreCollection = (collection, callback, queryOptions = {}) => {
    try {
        const db = firebaseFirestore || initFirestore();
        let query = db.collection(collection);

        // Apply query options
        if (queryOptions.where) {
            queryOptions.where.forEach(condition => {
                query = query.where(condition.field, condition.operator, condition.value);
            });
        }

        if (queryOptions.orderBy) {
            query = query.orderBy(queryOptions.orderBy.field, queryOptions.orderBy.direction);
        }

        if (queryOptions.limit) {
            query = query.limit(queryOptions.limit);
        }

        return query.onSnapshot(callback);
    } catch (error) {
        console.error("Error listening to collection:", error);
        throw error;
    }
};

/**
 * Initialize all Firebase services
 * @param {Object} config - Firebase configuration (optional)
 * @returns {Object} Object with all Firebase instances
 */
const initializeAllFirebaseServices = (config = null) => {
    try {
        const app = initFirebase(config);
        const auth = initAuth();
        const firestore = initFirestore();
        const database = initDatabase();
        const messaging = initMessaging();

        return {
            app,
            auth,
            firestore,
            database,
            messaging
        };
    } catch (error) {
        console.error("Error initializing Firebase services:", error);
        return null;
    }
};

// Export functions for global use
window.FirebaseConfig = {
    initFirebase,
    initAuth,
    initFirestore,
    initDatabase,
    initMessaging,
    setupPhoneAuth,
    createFirestoreDocument,
    updateFirestoreDocument,
    getFirestoreDocument,
    deleteFirestoreDocument,
    listenToFirestoreDocument,
    listenToFirestoreCollection,
    initializeAllFirebaseServices,
    DEFAULT_FIREBASE_CONFIG
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
