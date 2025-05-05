import os
import requests
import json
import logging

# Initialize Firebase for client-side authentication
firebase_project_id = os.environ.get("al-7esa")  # Replace with your actual project ID
firebase_api_key = os.environ.get("AIzaSyCB_GPRRlb6BCe1Mlv7rTIbtnD-Y3vpAj8")  # Replace with your actual API key
firebase_app_id = os.environ.get("1:893628750909:web:3cd09924c12987b3ef9e54")  # Replace with your actual app ID

# Flag to track if Firebase is initialized
firebase_initialized = False

# We won't use Firebase Admin SDK for this application
# Instead, we'll use the Firebase client SDK for authentication
# Firebase Admin SDK would require a service account JSON file
if firebase_project_id and firebase_api_key and firebase_app_id:
    # Mark as initialized if we have the necessary credentials
    firebase_initialized = True
    logging.info("Firebase credentials found. Client-side authentication enabled.")
else:
    logging.warning("Firebase credentials not found. Some features may not work.")

def verify_firebase_token(id_token):
    """
    Verify the Firebase ID token through the Firebase REST API
    """
    if not firebase_initialized or not firebase_api_key:
        logging.error("Firebase not initialized. Cannot verify token.")
        return None
    
    try:
        # Using the Firebase Auth REST API to verify token
        # In a production app, you'd use a more robust method
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={firebase_api_key}"
        payload = {"idToken": id_token}
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            user_data = response.json().get('users', [])
            if user_data:
                return {
                    'uid': user_data[0].get('localId'),
                    'phone_number': user_data[0].get('phoneNumber'),
                    'email': user_data[0].get('email')
                }
        
        logging.error(f"Error verifying token: {response.text}")
        return None
    except Exception as e:
        logging.error(f"Error verifying Firebase token: {str(e)}")
        return None

def get_firebase_user(uid):
    """
    Get user information from Firebase Auth using REST API
    """
    if not firebase_initialized or not firebase_api_key:
        logging.error("Firebase not initialized. Cannot get user.")
        return None
    
    try:
        # Get user info using the REST API
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={firebase_api_key}"
        payload = {"localId": [uid]}
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            user_data = response.json().get('users', [])
            if user_data:
                return {
                    'uid': user_data[0].get('localId'),
                    'phone_number': user_data[0].get('phoneNumber'),
                    'email': user_data[0].get('email'),
                    'display_name': user_data[0].get('displayName')
                }
            
        logging.error(f"Error getting user: {response.text}")
        return None
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
