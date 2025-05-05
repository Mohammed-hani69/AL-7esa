// Chat functionality for classrooms

// Initialize chat functionality
document.addEventListener('DOMContentLoaded', function() {
  const chatContainer = document.getElementById('chat-container');
  if (!chatContainer) return;
  
  // Check if user has chat access
  const hasAccess = chatContainer.getAttribute('data-has-access') === 'true';
  if (!hasAccess) return;
  
  initializeChat();
  
  // Chat message form submission
  const chatForm = document.getElementById('chat-form');
  if (chatForm) {
    chatForm.addEventListener('submit', function(e) {
      e.preventDefault();
      sendChatMessage();
    });
  }
  
  // Chat scroll to bottom
  scrollChatToBottom();
});

// Initialize the chat
function initializeChat() {
  // Get classroom data
  const chatContainer = document.getElementById('chat-container');
  if (!chatContainer) return;
  
  const classroomId = chatContainer.getAttribute('data-classroom-id');
  const userId = chatContainer.getAttribute('data-user-id');
  const userName = chatContainer.getAttribute('data-user-name');
  const userRole = chatContainer.getAttribute('data-user-role');
  
  if (!classroomId || !userId) {
    console.error('Missing required chat data');
    return;
  }
  
  // Initialize Firebase if available
  if (typeof firebase !== 'undefined' && firebase.database) {
    // Initialize Firebase
    initFirebase();
    
    // Get database reference
    const db = firebase.database();
    const chatRef = db.ref(`chats/${classroomId}/messages`);
    
    // Listen for new messages
    chatRef.on('child_added', function(snapshot) {
      const message = snapshot.val();
      displayChatMessage(message, userId);
      scrollChatToBottom();
    });
    
    // Listen for deleted messages
    chatRef.on('child_changed', function(snapshot) {
      const message = snapshot.val();
      
      if (message.isDeleted) {
        const messageElement = document.getElementById(`message-${snapshot.key}`);
        if (messageElement) {
          messageElement.querySelector('.message-content').textContent = 'تم حذف هذه الرسالة';
          messageElement.classList.add('text-muted');
        }
      }
    });
  } else {
    // Fallback for when Firebase is not available
    console.warn('Firebase not available, using fallback chat mechanism');
    
    // Load initial messages via AJAX
    loadInitialMessages(classroomId);
    
    // Set up polling for new messages
    setInterval(() => {
      loadNewMessages(classroomId, getLastMessageTimestamp());
    }, 5000);
  }
}

// Load initial messages via AJAX
function loadInitialMessages(classroomId) {
  fetch(`/classroom/${classroomId}/chat/messages`)
    .then(response => response.json())
    .then(data => {
      const messages = data.messages || [];
      const userId = document.getElementById('chat-container').getAttribute('data-user-id');
      
      // Clear existing messages
      const chatMessages = document.querySelector('.chat-messages');
      chatMessages.innerHTML = '';
      
      // Display messages
      messages.forEach(message => {
        displayChatMessage(message, userId);
      });
      
      scrollChatToBottom();
    })
    .catch(error => {
      console.error('Error loading chat messages:', error);
    });
}

// Load new messages since last timestamp
function loadNewMessages(classroomId, since) {
  if (!since) return;
  
  fetch(`/classroom/${classroomId}/chat/messages?since=${since}`)
    .then(response => response.json())
    .then(data => {
      const messages = data.messages || [];
      const userId = document.getElementById('chat-container').getAttribute('data-user-id');
      
      // Display new messages
      messages.forEach(message => {
        displayChatMessage(message, userId);
      });
      
      if (messages.length > 0) {
        scrollChatToBottom();
      }
    })
    .catch(error => {
      console.error('Error loading new chat messages:', error);
    });
}

// Get timestamp of last message
function getLastMessageTimestamp() {
  const messages = document.querySelectorAll('.message');
  if (messages.length === 0) return null;
  
  const lastMessage = messages[messages.length - 1];
  return lastMessage.getAttribute('data-timestamp');
}

// Send a chat message
function sendChatMessage() {
  const chatContainer = document.getElementById('chat-container');
  const messageInput = document.getElementById('chat-message');
  
  if (!chatContainer || !messageInput) return;
  
  const message = messageInput.value.trim();
  if (!message) return;
  
  const classroomId = chatContainer.getAttribute('data-classroom-id');
  const userId = chatContainer.getAttribute('data-user-id');
  const userName = chatContainer.getAttribute('data-user-name');
  const userRole = chatContainer.getAttribute('data-user-role');
  
  if (!classroomId || !userId) {
    console.error('Missing required chat data');
    return;
  }
  
  // Clear input
  messageInput.value = '';
  
  // Create message object
  const newMessage = {
    userId: userId,
    userName: userName,
    userRole: userRole,
    message: message,
    timestamp: Date.now(),
    isDeleted: false
  };
  
  // Send message to Firebase if available
  if (typeof firebase !== 'undefined' && firebase.database) {
    const db = firebase.database();
    const chatRef = db.ref(`chats/${classroomId}/messages`);
    
    chatRef.push(newMessage)
      .catch(error => {
        console.error('Error sending message to Firebase:', error);
        
        // Fallback to AJAX
        sendMessageViaAjax(classroomId, newMessage);
      });
  } else {
    // Fallback to AJAX
    sendMessageViaAjax(classroomId, newMessage);
  }
}

// Send message via AJAX
function sendMessageViaAjax(classroomId, message) {
  fetch(`/classroom/${classroomId}/chat/send`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken()
    },
    body: JSON.stringify({ message: message.message })
  })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Message was saved, display it
        displayChatMessage(data.message, message.userId);
        scrollChatToBottom();
      } else {
        console.error('Error sending message:', data.error);
      }
    })
    .catch(error => {
      console.error('Error sending message via AJAX:', error);
    });
}

// Display a chat message in the UI
function displayChatMessage(message, currentUserId) {
  const chatMessages = document.querySelector('.chat-messages');
  if (!chatMessages) return;
  
  const messageDiv = document.createElement('div');
  messageDiv.className = 'message';
  messageDiv.id = `message-${message.id || message.key || Date.now()}`;
  messageDiv.setAttribute('data-timestamp', message.timestamp);
  
  const isSelf = message.userId === currentUserId;
  
  if (isSelf) {
    messageDiv.classList.add('message-self');
  } else {
    messageDiv.classList.add('message-other');
  }
  
  const userRoleBadge = message.userRole ? `<span class="badge badge-${getRoleBadgeClass(message.userRole)}">${getRoleDisplay(message.userRole)}</span>` : '';
  
  const messageTime = formatChatTime(message.timestamp);
  
  let messageContent = message.message;
  if (message.isDeleted) {
    messageContent = 'تم حذف هذه الرسالة';
    messageDiv.classList.add('text-muted');
  }
  
  // Check if user can delete this message
  const userRole = document.getElementById('chat-container')?.getAttribute('data-user-role');
  const canDelete = userRole === 'teacher' || userRole === 'assistant' || isSelf;
  
  const deleteButton = canDelete && !message.isDeleted ? 
    `<button class="btn btn-sm text-danger" onclick="deleteChatMessage('${message.id || message.key || ''}', ${isSelf})">
        <i class="fas fa-trash-alt"></i>
     </button>` : '';
  
  messageDiv.innerHTML = `
    <div class="message-header">
      <strong>${message.userName || 'مستخدم'} ${userRole}</strong>
      <span class="message-time">${messageTime}</span>
    </div>
    <div class="message-content">${messageContent}</div>
    <div class="message-actions">
      ${deleteButton}
    </div>
  `;
  
  chatMessages.appendChild(messageDiv);
}

// Delete a chat message
function deleteChatMessage(messageId, isSelf) {
  const chatContainer = document.getElementById('chat-container');
  if (!chatContainer || !messageId) return;
  
  const classroomId = chatContainer.getAttribute('data-classroom-id');
  
  if (confirm('هل أنت متأكد من حذف هذه الرسالة؟')) {
    // Delete via Firebase if available
    if (typeof firebase !== 'undefined' && firebase.database) {
      const db = firebase.database();
      const messageRef = db.ref(`chats/${classroomId}/messages/${messageId}`);
      
      messageRef.update({ isDeleted: true })
        .catch(error => {
          console.error('Error deleting message from Firebase:', error);
          
          // Fallback to AJAX
          deleteMessageViaAjax(classroomId, messageId);
        });
    } else {
      // Fallback to AJAX
      deleteMessageViaAjax(classroomId, messageId);
    }
  }
}

// Delete message via AJAX
function deleteMessageViaAjax(classroomId, messageId) {
  fetch(`/classroom/${classroomId}/chat/delete/${messageId}`, {
    method: 'POST',
    headers: {
      'X-CSRFToken': getCsrfToken()
    }
  })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Update UI to show message as deleted
        const messageElement = document.getElementById(`message-${messageId}`);
        if (messageElement) {
          messageElement.querySelector('.message-content').textContent = 'تم حذف هذه الرسالة';
          messageElement.classList.add('text-muted');
          messageElement.querySelector('.message-actions').innerHTML = '';
        }
      } else {
        console.error('Error deleting message:', data.error);
      }
    })
    .catch(error => {
      console.error('Error deleting message via AJAX:', error);
    });
}

// Scroll chat to bottom
function scrollChatToBottom() {
  const chatMessages = document.querySelector('.chat-messages');
  if (chatMessages) {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }
}

// Format chat timestamp
function formatChatTime(timestamp) {
  if (!timestamp) return '';
  
  const date = new Date(timestamp);
  const now = new Date();
  
  // Check if message is from today
  if (date.toDateString() === now.toDateString()) {
    return date.toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' });
  }
  
  // Check if message is from yesterday
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (date.toDateString() === yesterday.toDateString()) {
    return 'الأمس ' + date.toLocaleTimeString('ar-SA', { hour: '2-digit', minute: '2-digit' });
  }
  
  // Otherwise show full date
  return date.toLocaleDateString('ar-SA', { 
    year: 'numeric', 
    month: 'short', 
    day: 'numeric',
    hour: '2-digit', 
    minute: '2-digit'
  });
}

// Get CSRF token
function getCsrfToken() {
  const csrfInput = document.querySelector('input[name="csrf_token"]');
  return csrfInput ? csrfInput.value : '';
}

// Get badge class for user role
function getRoleBadgeClass(role) {
  switch (role) {
    case 'teacher':
      return 'primary';
    case 'assistant':
      return 'info';
    case 'student':
      return 'success';
    case 'admin':
      return 'danger';
    default:
      return 'secondary';
  }
}

// Get display text for user role
function getRoleDisplay(role) {
  switch (role) {
    case 'teacher':
      return 'معلم';
    case 'assistant':
      return 'مساعد';
    case 'student':
      return 'طالب';
    case 'admin':
      return 'مدير';
    default:
      return role;
  }
}
