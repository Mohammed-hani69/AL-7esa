import os
import requests
import json
import logging
from typing import Optional, Dict, Any

# Firebase configuration from environment variables
FIREBASE_CONFIG = {
    'apiKey': os.environ.get("FIREBASE_API_KEY", "AIzaSyCB_GPRRlb6BCe1Mlv7rTIbtnD-Y3vpAj8"),
    'authDomain': os.environ.get("FIREBASE_AUTH_DOMAIN", "al-7esa.firebaseapp.com"),
    'projectId': os.environ.get("FIREBASE_PROJECT_ID", "al-7esa"),
    'storageBucket': os.environ.get("FIREBASE_STORAGE_BUCKET", "al-7esa.appspot.com"),
    'messagingSenderId': os.environ.get("FIREBASE_MESSAGING_SENDER_ID", "893628750909"),
    'appId': os.environ.get("FIREBASE_APP_ID", "1:893628750909:web:3cd09924c12987b3ef9e54"),
    'measurementId': os.environ.get("FIREBASE_MEASUREMENT_ID", "G-B026ZL6KXG"),
    'databaseURL': os.environ.get("FIREBASE_DATABASE_URL", "https://al-7esa-default-rtdb.firebaseio.com")
}

# Firebase Admin SDK configuration (optional)
FIREBASE_ADMIN_CONFIG = {
    'service_account_path': os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH"),
    'database_url': FIREBASE_CONFIG['databaseURL']
}

# Flag to track if Firebase is initialized
firebase_initialized = False
firebase_admin_initialized = False

# Try to initialize Firebase Admin SDK if service account is available
try:
    if FIREBASE_ADMIN_CONFIG['service_account_path'] and os.path.exists(FIREBASE_ADMIN_CONFIG['service_account_path']):
        import firebase_admin
        from firebase_admin import credentials, firestore, auth as admin_auth

        cred = credentials.Certificate(FIREBASE_ADMIN_CONFIG['service_account_path'])
        firebase_admin.initialize_app(cred, {
            'databaseURL': FIREBASE_ADMIN_CONFIG['database_url']
        })
        firebase_admin_initialized = True
        logging.info("Firebase Admin SDK initialized successfully.")
    else:
        logging.info("Firebase Admin SDK service account not found. Using REST API for authentication.")
except ImportError:
    logging.warning("Firebase Admin SDK not installed. Install with: pip install firebase-admin")
except Exception as e:
    logging.error(f"Error initializing Firebase Admin SDK: {str(e)}")

# Check if basic Firebase configuration is available
if all(FIREBASE_CONFIG[key] for key in ['apiKey', 'projectId', 'appId']):
    firebase_initialized = True
    logging.info("Firebase client configuration found. Client-side authentication enabled.")
else:
    logging.warning("Firebase configuration incomplete. Some features may not work.")

def get_firebase_config() -> Dict[str, str]:
    """
    Get Firebase configuration for client-side use
    """
    return FIREBASE_CONFIG.copy()

def verify_firebase_token(id_token: str) -> Optional[Dict[str, Any]]:
    """
    Verify the Firebase ID token using Admin SDK or REST API
    """
    if not firebase_initialized:
        logging.warning("Firebase not initialized, skipping token verification")
        return None

    try:
        # Try using Admin SDK first (more secure)
        if firebase_admin_initialized:
            try:
                decoded_token = admin_auth.verify_id_token(id_token)
                return {
                    'uid': decoded_token.get('uid'),
                    'phone_number': decoded_token.get('phone_number'),
                    'email': decoded_token.get('email'),
                    'name': decoded_token.get('name'),
                    'picture': decoded_token.get('picture')
                }
            except Exception as e:
                logging.error(f"Error verifying token with Admin SDK: {str(e)}")
                # Fall back to REST API

        # Fallback to REST API
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={FIREBASE_CONFIG['apiKey']}"
        payload = {"idToken": id_token}
        response = requests.post(url, json=payload)

        if response.status_code == 200:
            user_data = response.json().get('users', [])
            if user_data:
                return {
                    'uid': user_data[0].get('localId'),
                    'phone_number': user_data[0].get('phoneNumber'),
                    'email': user_data[0].get('email'),
                    'name': user_data[0].get('displayName'),
                    'picture': user_data[0].get('photoUrl')
                }

        logging.error(f"Error verifying token: {response.text}")
        return None
    except Exception as e:
        logging.error(f"Error verifying Firebase token: {str(e)}")
        return None

def get_firebase_user(uid: str) -> Optional[Dict[str, Any]]:
    """
    Get user information from Firebase Auth using Admin SDK or REST API
    """
    if not firebase_initialized:
        logging.error("Firebase not initialized. Cannot get user.")
        return None

    try:
        # Try using Admin SDK first
        if firebase_admin_initialized:
            try:
                user_record = admin_auth.get_user(uid)
                return {
                    'uid': user_record.uid,
                    'phone_number': user_record.phone_number,
                    'email': user_record.email,
                    'display_name': user_record.display_name,
                    'photo_url': user_record.photo_url,
                    'disabled': user_record.disabled,
                    'email_verified': user_record.email_verified
                }
            except Exception as e:
                logging.error(f"Error getting user with Admin SDK: {str(e)}")
                # Fall back to REST API

        # Fallback to REST API
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={FIREBASE_CONFIG['apiKey']}"
        payload = {"localId": [uid]}
        response = requests.post(url, json=payload)

        if response.status_code == 200:
            user_data = response.json().get('users', [])
            if user_data:
                return {
                    'uid': user_data[0].get('localId'),
                    'phone_number': user_data[0].get('phoneNumber'),
                    'email': user_data[0].get('email'),
                    'display_name': user_data[0].get('displayName'),
                    'photo_url': user_data[0].get('photoUrl'),
                    'email_verified': user_data[0].get('emailVerified', False)
                }

        logging.error(f"Error getting user: {response.text}")
        return None
    except Exception as e:
        logging.error(f"Error getting Firebase user: {str(e)}")
        return None

def send_firebase_notification(token: str, title: str, body: str, data: Optional[Dict[str, Any]] = None) -> bool:
    """
    Send a notification using Firebase Cloud Messaging
    """
    if not firebase_initialized:
        logging.error("Firebase not initialized. Cannot send notification.")
        return False

    try:
        # Try using Admin SDK first (recommended)
        if firebase_admin_initialized:
            try:
                from firebase_admin import messaging

                message = messaging.Message(
                    notification=messaging.Notification(
                        title=title,
                        body=body
                    ),
                    data=data or {},
                    token=token
                )

                response = messaging.send(message)
                logging.info(f"Successfully sent message: {response}")
                return True
            except Exception as e:
                logging.error(f"Error sending notification with Admin SDK: {str(e)}")
                # Fall back to REST API

        # Fallback to legacy FCM REST API (requires server key)
        server_key = os.environ.get("FIREBASE_SERVER_KEY")
        if not server_key:
            logging.warning("Firebase server key not found. Cannot send notifications via REST API.")
            return False

        url = "https://fcm.googleapis.com/fcm/send"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"key={server_key}"
        }

        payload = {
            "to": token,
            "notification": {
                "title": title,
                "body": body
            }
        }

        if data:
            payload["data"] = data

        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            return True
        else:
            logging.error(f"Error sending notification: {response.text}")
            return False

    except Exception as e:
        logging.error(f"Error sending notification: {str(e)}")
        return False

def get_firestore_client():
    """
    Get Firestore client instance
    """
    if firebase_admin_initialized:
        return firestore.client()
    else:
        logging.warning("Firebase Admin SDK not initialized. Firestore operations require Admin SDK.")
        return None

def create_firestore_document(collection: str, document_id: str, data: Dict[str, Any]) -> bool:
    """
    Create a document in Firestore
    """
    try:
        db = get_firestore_client()
        if not db:
            return False

        doc_ref = db.collection(collection).document(document_id)
        doc_ref.set(data)
        logging.info(f"Document created successfully in {collection}/{document_id}")
        return True
    except Exception as e:
        logging.error(f"Error creating Firestore document: {str(e)}")
        return False

def update_firestore_document(collection: str, document_id: str, data: Dict[str, Any]) -> bool:
    """
    Update a document in Firestore
    """
    try:
        db = get_firestore_client()
        if not db:
            return False

        doc_ref = db.collection(collection).document(document_id)
        doc_ref.update(data)
        logging.info(f"Document updated successfully in {collection}/{document_id}")
        return True
    except Exception as e:
        logging.error(f"Error updating Firestore document: {str(e)}")
        return False

def get_firestore_document(collection: str, document_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a document from Firestore
    """
    try:
        db = get_firestore_client()
        if not db:
            return None

        doc_ref = db.collection(collection).document(document_id)
        doc = doc_ref.get()

        if doc.exists:
            return doc.to_dict()
        else:
            logging.info(f"Document {collection}/{document_id} does not exist")
            return None
    except Exception as e:
        logging.error(f"Error getting Firestore document: {str(e)}")
        return None

def delete_firestore_document(collection: str, document_id: str) -> bool:
    """
    Delete a document from Firestore
    """
    try:
        db = get_firestore_client()
        if not db:
            return False

        doc_ref = db.collection(collection).document(document_id)
        doc_ref.delete()
        logging.info(f"Document deleted successfully from {collection}/{document_id}")
        return True
    except Exception as e:
        logging.error(f"Error deleting Firestore document: {str(e)}")
        return False