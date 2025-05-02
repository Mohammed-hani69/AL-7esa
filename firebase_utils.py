import os
import requests
import json
import logging
from firebase_admin import credentials, auth, initialize_app

# Initialize Firebase Admin SDK
try:
    # Initialize Firebase Admin SDK with credentials from environment variables
    firebase_project_id = os.environ.get("FIREBASE_PROJECT_ID", "")
    firebase_api_key = os.environ.get("FIREBASE_API_KEY", "")
    
    if firebase_project_id and firebase_api_key:
        # For production, you would use a service account JSON file
        # For simplicity, we'll use the project ID and API key directly
        cred = credentials.Certificate({
            "type": "service_account",
            "project_id": firebase_project_id,
            # In a real app, you'd have proper credentials from a service account JSON file
        })
        firebase_app = initialize_app(cred)
        firebase_initialized = True
    else:
        firebase_initialized = False
        logging.warning("Firebase credentials not found. Some features may not work.")
except Exception as e:
    firebase_initialized = False
    logging.error(f"Failed to initialize Firebase: {str(e)}")

def verify_firebase_token(id_token):
    """
    Verify the Firebase ID token and return the decoded token
    """
    if not firebase_initialized:
        logging.error("Firebase not initialized. Cannot verify token.")
        return None
    
    try:
        # Verify the ID token
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        logging.error(f"Error verifying Firebase token: {str(e)}")
        return None

def get_firebase_user(uid):
    """
    Get user information from Firebase Auth
    """
    if not firebase_initialized:
        logging.error("Firebase not initialized. Cannot get user.")
        return None
    
    try:
        user = auth.get_user(uid)
        return user
    except Exception as e:
        logging.error(f"Error getting Firebase user: {str(e)}")
        return None

def send_firebase_notification(token, title, body, data=None):
    """
    Send a notification using Firebase Cloud Messaging
    """
    if not firebase_initialized or not firebase_api_key:
        logging.error("Firebase not initialized. Cannot send notification.")
        return False
    
    url = "https://fcm.googleapis.com/fcm/send"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"key={firebase_api_key}"
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
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            return True
        else:
            logging.error(f"Error sending notification: {response.text}")
            return False
    except Exception as e:
        logging.error(f"Error sending notification: {str(e)}")
        return False
