from app import app, socketio

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, allow_unsafe_werkzeug=True)


#if __name__ == '__main__':
 #   app.run(port=5000, host='0.0.0.0', debug=True)