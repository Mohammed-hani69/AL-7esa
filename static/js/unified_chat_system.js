/**
 * نظام الشات الموحد لجميع الصفحات
 * يحتوي على جميع الوظائف اللازمة لعمل الشات بكفاءة
 */

class UnifiedChatSystem {
    constructor(config) {
        this.classroomId = config.classroomId;
        this.currentUser = config.currentUser;
        this.db = config.db;
        this.messageContainer = config.messageContainer;
        this.messageInput = config.messageInput;
        this.sendButton = config.sendButton;
        this.isTyping = false;
        this.typingTimeout = null;
        this.lastMessageTime = new Date().toISOString();
        this.displayedMessages = new Set(); // تجنب الرسائل المكررة
        
        console.log('🚀 تهيئة نظام الشات الموحد...');
        console.log('📍 معرف الفصل:', this.classroomId);
        console.log('👤 المستخدم الحالي:', this.currentUser);
        
        this.init();
    }

    async init() {
        try {
            // التحقق من العناصر المطلوبة
            if (!this.validateElements()) {
                console.error('❌ عناصر الشات مفقودة');
                return;
            }

            // تحميل الرسائل المحفوظة أولاً
            await this.loadSavedMessages();

            // تهيئة Firebase أو Fallback
            await this.initializeRealtime();

            // إعداد event listeners
            this.setupEventListeners();

            console.log('✅ تم تهيئة نظام الشات بنجاح');
        } catch (error) {
            console.error('❌ خطأ في تهيئة الشات:', error);
        }
    }

    validateElements() {
        const missing = [];
        if (!this.messageContainer) missing.push('messageContainer');
        if (!this.messageInput) missing.push('messageInput');
        if (!this.sendButton) missing.push('sendButton');

        if (missing.length > 0) {
            console.error('العناصر المفقودة:', missing);
            return false;
        }
        return true;
    }

    async loadSavedMessages() {
        try {
            console.log('📂 تحميل الرسائل المحفوظة...');
            const response = await fetch(`/chat/classroom/${this.classroomId}/messages`);
            
            if (response.ok) {
                const data = await response.json();
                if (data.messages && Array.isArray(data.messages)) {
                    console.log(`📄 تم العثور على ${data.messages.length} رسالة محفوظة`);
                    
                    // مسح الرسائل الموجودة
                    this.messageContainer.innerHTML = '';
                    this.displayedMessages.clear();
                    
                    data.messages.forEach(message => {
                        this.displayMessage({
                            id: message.id,
                            text: message.message,
                            senderId: message.user_id,
                            senderName: message.user_name,
                            senderRole: message.user_role,
                            timestamp: { seconds: new Date(message.created_at).getTime() / 1000 }
                        });
                    });
                    
                    this.scrollToBottom();
                    console.log('✅ تم تحميل الرسائل المحفوظة');
                }
            }
        } catch (error) {
            console.warn('⚠️ فشل في تحميل الرسائل المحفوظة:', error);
        }
    }

    async initializeRealtime() {
        try {
            if (this.db) {
                console.log('🔗 محاولة الاتصال بـ Firebase...');
                
                // الاستماع للرسائل الجديدة
                const messagesRef = window.firebaseModules.collection(this.db, 'classrooms', this.classroomId, 'messages');
                const q = window.firebaseModules.query(messagesRef, window.firebaseModules.orderBy('timestamp', 'asc'));

                window.firebaseModules.onSnapshot(q, (snapshot) => {
                    console.log('📨 تحديثات Firebase وصلت...');
                    snapshot.docChanges().forEach((change) => {
                        if (change.type === 'added') {
                            const messageData = change.doc.data();
                            this.displayMessage({
                                id: change.doc.id,
                                ...messageData
                            });
                        }
                    });
                    this.scrollToBottom();
                });

                console.log('✅ Firebase Real-time مفعل');
            } else {
                console.log('⚠️ Firebase غير متاح، استخدام Polling...');
                this.startPolling();
            }
        } catch (error) {
            console.warn('⚠️ Firebase فشل، استخدام Polling:', error);
            this.startPolling();
        }
    }

    startPolling() {
        console.log('🔄 بدء نظام Polling للرسائل...');
        
        setInterval(async () => {
            try {
                const response = await fetch(`/chat/classroom/${this.classroomId}/messages?since=${this.lastMessageTime}`);
                if (response.ok) {
                    const data = await response.json();
                    if (data.messages && data.messages.length > 0) {
                        console.log(`📬 رسائل جديدة: ${data.messages.length}`);
                        data.messages.forEach(message => {
                            this.displayMessage({
                                id: message.id,
                                text: message.message,
                                senderId: message.user_id,
                                senderName: message.user_name,
                                senderRole: message.user_role,
                                timestamp: { seconds: new Date(message.created_at).getTime() / 1000 }
                            });
                            this.lastMessageTime = message.created_at;
                        });
                    }
                }
            } catch (error) {
                console.warn('⚠️ Polling error:', error);
            }
        }, 3000);
    }

    setupEventListeners() {
        // زر الإرسال
        this.sendButton.addEventListener('click', () => this.sendMessage());
        
        // Enter للإرسال
        this.messageInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                this.sendMessage();
            }
        });

        // Auto-resize للنصوص الطويلة
        this.messageInput.addEventListener('input', () => {
            this.messageInput.style.height = 'auto';
            this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 100) + 'px';
        });
    }

    async sendMessage() {
        const messageText = this.messageInput.value.trim();
        
        if (!messageText) {
            console.log('⚠️ لا يوجد نص للإرسال');
            return;
        }

        console.log('📤 بدء إرسال الرسالة:', messageText);

        // تعطيل الزر مؤقتاً
        this.sendButton.disabled = true;
        const originalHTML = this.sendButton.innerHTML;
        this.sendButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

        try {
            const messageData = {
                text: messageText,
                senderId: this.currentUser.id,
                senderRole: this.currentUser.role,
                senderName: this.currentUser.name,
                timestamp: window.firebaseModules?.serverTimestamp?.() || new Date(),
                classroomId: this.classroomId
            };

            let messageSent = false;

            // محاولة Firebase أولاً
            if (this.db && window.firebaseModules) {
                try {
                    console.log('🔥 محاولة إرسال عبر Firebase...');
                    const messagesRef = window.firebaseModules.collection(this.db, 'classrooms', this.classroomId, 'messages');
                    const docRef = await window.firebaseModules.addDoc(messagesRef, messageData);
                    console.log('✅ تم إرسال الرسالة عبر Firebase:', docRef.id);
                    messageSent = true;

                    // عرض فوري كـ backup
                    setTimeout(() => {
                        this.displayMessage({
                            id: docRef.id,
                            text: messageText,
                            senderId: this.currentUser.id,
                            senderRole: this.currentUser.role,
                            senderName: this.currentUser.name,
                            timestamp: { seconds: Math.floor(Date.now() / 1000) }
                        });
                    }, 100);

                } catch (firebaseError) {
                    console.warn('⚠️ Firebase فشل:', firebaseError);
                }
            }

            // البديل: API
            if (!messageSent) {
                try {
                    console.log('🌐 محاولة إرسال عبر API...');
                    const response = await fetch(`/chat/classroom/${this.classroomId}/send_message`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': document.querySelector('meta[name=csrf-token]')?.content || ''
                        },
                        body: JSON.stringify(messageData)
                    });

                    if (response.ok) {
                        console.log('✅ تم إرسال الرسالة عبر API');
                        messageSent = true;

                        this.displayMessage({
                            id: 'api_' + Date.now(),
                            text: messageText,
                            senderId: this.currentUser.id,
                            senderRole: this.currentUser.role,
                            senderName: this.currentUser.name,
                            timestamp: { seconds: Math.floor(Date.now() / 1000) }
                        });
                    } else {
                        throw new Error('API request failed');
                    }
                } catch (apiError) {
                    console.error('❌ فشل API:', apiError);
                }
            }

            // الحل الأخير: عرض محلي
            if (!messageSent) {
                console.log('💾 عرض محلي كحل أخير');
                this.displayMessage({
                    id: 'local_' + Date.now(),
                    text: messageText,
                    senderId: this.currentUser.id,
                    senderRole: this.currentUser.role,
                    senderName: this.currentUser.name + ' (محلي)',
                    timestamp: { seconds: Math.floor(Date.now() / 1000) }
                });
                
                alert('تم عرض الرسالة محلياً - قد تحتاج لتحديث الصفحة');
            }

            // مسح الحقل
            this.messageInput.value = '';
            this.messageInput.style.height = 'auto';

        } catch (error) {
            console.error('❌ خطأ في إرسال الرسالة:', error);
            alert('حدث خطأ في إرسال الرسالة. يرجى المحاولة مرة أخرى.');
        } finally {
            // إعادة تفعيل الزر
            this.sendButton.disabled = false;
            this.sendButton.innerHTML = originalHTML;
        }
    }

    displayMessage(messageData) {
        console.log('📥 عرض رسالة جديدة:', messageData);

        // التعامل مع البيانات المختلفة
        const senderId = messageData.senderId || messageData.userId;
        const senderName = messageData.senderName || messageData.userName;
        const senderRole = messageData.senderRole || messageData.userRole;
        const messageText = messageData.text || messageData.message;

        if (!messageText || !senderId) {
            console.error('❌ بيانات الرسالة غير مكتملة:', messageData);
            return;
        }

        // تجنب عرض نفس الرسالة مرتين
        const messageId = messageData.id || 'msg_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        if (this.displayedMessages.has(messageId)) {
            console.log('⚠️ الرسالة موجودة مسبقاً:', messageId);
            return;
        }
        
        this.displayedMessages.add(messageId);

        const isOwnMessage = senderId === this.currentUser.id;
        const canDelete = this.currentUser.role === 'teacher' || this.currentUser.role === 'assistant' || isOwnMessage;

        const messageElement = document.createElement('div');
        messageElement.className = `message ${isOwnMessage ? 'own' : ''} ${senderRole}`;
        messageElement.setAttribute('data-message-id', messageId);

        const timestamp = this.formatTimestamp(messageData.timestamp);

        const deleteButton = canDelete ? 
            `<div class="message-actions" style="position: absolute; top: 0.5rem; left: 0.5rem; opacity: 0; transition: opacity 0.3s;">
                <button class="delete-btn" onclick="chatSystem.deleteMessage('${messageId}')" 
                        style="background: #dc3545; border: none; color: white; padding: 0.2rem 0.4rem; border-radius: 4px; font-size: 0.7rem; cursor: pointer;">
                    <i class="fas fa-trash"></i>
                </button>
            </div>` : '';

        messageElement.innerHTML = `
            <div class="message-avatar">
                ${senderName.charAt(0).toUpperCase()}
            </div>
            <div class="message-content" style="position: relative;" 
                 onmouseenter="this.querySelector('.message-actions')?.style && (this.querySelector('.message-actions').style.opacity='1')" 
                 onmouseleave="this.querySelector('.message-actions')?.style && (this.querySelector('.message-actions').style.opacity='0')">
                <div class="message-header">
                    <span class="message-sender">${senderName}</span>
                    ${senderRole === 'teacher' ? '<span class="badge bg-danger">معلم</span>' : ''}
                    ${senderRole === 'assistant' ? '<span class="badge bg-warning">مساعد</span>' : ''}
                    <span class="message-time">${timestamp}</span>
                </div>
                <div class="message-text">${messageText}</div>
                ${deleteButton}
            </div>
        `;

        this.messageContainer.appendChild(messageElement);
        console.log('✅ تم إضافة الرسالة للواجهة:', messageId);
        this.scrollToBottom();
    }

    formatTimestamp(timestamp) {
        if (!timestamp) return 'الآن';
        
        const date = timestamp.seconds ? 
            new Date(timestamp.seconds * 1000) : 
            new Date(timestamp);
            
        return date.toLocaleTimeString('ar-EG', {
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    scrollToBottom() {
        if (this.messageContainer) {
            this.messageContainer.scrollTop = this.messageContainer.scrollHeight;
        }
    }

    // طريقة لإرسال رسائل خاصة (مثل رفع اليد)
    async sendSpecialMessage(text, type) {
        const messageData = {
            text: text,
            senderId: this.currentUser.id,
            senderRole: this.currentUser.role,
            senderName: this.currentUser.name,
            timestamp: window.firebaseModules?.serverTimestamp?.() || new Date(),
            classroomId: this.classroomId,
            type: type || 'special'
        };

        // محاولة Firebase أولاً
        if (this.db && window.firebaseModules) {
            try {
                const messagesRef = window.firebaseModules.collection(this.db, 'classrooms', this.classroomId, 'messages');
                const docRef = await window.firebaseModules.addDoc(messagesRef, messageData);
                console.log('✅ تم إرسال الرسالة الخاصة عبر Firebase:', docRef.id);
                return true;
            } catch (error) {
                console.warn('⚠️ فشل Firebase في إرسال الرسالة الخاصة:', error);
            }
        }

        // البديل: API
        try {
            const response = await fetch(`/chat/classroom/${this.classroomId}/send_message`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name=csrf-token]')?.content || ''
                },
                body: JSON.stringify(messageData)
            });

            if (response.ok) {
                console.log('✅ تم إرسال الرسالة الخاصة عبر API');
                return true;
            }
        } catch (error) {
            console.error('❌ فشل في إرسال الرسالة الخاصة:', error);
        }

        return false;
    }

    // طريقة لتحديث إعدادات الشات
    updateChatSettings(settings) {
        const chatEnabled = settings.enabled !== false;
        
        if (this.messageInput) {
            this.messageInput.disabled = !chatEnabled;
        }
        
        if (this.sendButton) {
            this.sendButton.disabled = !chatEnabled;
        }
        
        if (this.elements.chatDisabledId) {
            const chatDisabled = document.getElementById(this.elements.chatDisabledId);
            if (chatDisabled) {
                chatDisabled.style.display = chatEnabled ? 'none' : 'block';
            }
        }
        
        if (this.elements.inputContainerId) {
            const inputContainer = document.getElementById(this.elements.inputContainerId);
            if (inputContainer) {
                inputContainer.classList.toggle('disabled', !chatEnabled);
            }
        }
        
        console.log('⚙️ تم تحديث إعدادات الشات:', chatEnabled ? 'مفعل' : 'معطل');
    }

    // طريقة لمسح رسالة
    async deleteMessage(messageId) {
        if (!messageId) return false;

        try {
            // محاولة Firebase أولاً
            if (this.db && window.firebaseModules) {
                try {
                    const messageRef = window.firebaseModules.doc(this.db, 'classrooms', this.classroomId, 'messages', messageId);
                    await window.firebaseModules.deleteDoc(messageRef);
                    console.log('✅ تم حذف الرسالة من Firebase');
                    return true;
                } catch (error) {
                    console.warn('⚠️ فشل حذف الرسالة من Firebase:', error);
                }
            }

            // البديل: API
            const response = await fetch(`/chat/classroom/${this.classroomId}/delete_message/${messageId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name=csrf-token]')?.content || ''
                }
            });

            if (response.ok) {
                console.log('✅ تم حذف الرسالة عبر API');
                
                // إزالة الرسالة من الواجهة
                const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
                if (messageElement) {
                    messageElement.remove();
                }
                
                return true;
            }
        } catch (error) {
            console.error('❌ فشل في حذف الرسالة:', error);
        }

        return false;
    }

    // دالة لتنظيف الموارد
    destroy() {
        this.displayedMessages.clear();
        if (this.typingTimeout) {
            clearTimeout(this.typingTimeout);
        }
    }

    // إرسال رسالة خاصة (مثل رفع اليد)
    async sendSpecialMessage(type, content) {
        console.log('🎯 إرسال رسالة خاصة:', type, content);
        
        const specialMessage = {
            senderId: this.currentUser.id,
            senderName: this.currentUser.name,
            senderRole: this.currentUser.role,
            text: content,
            type: type,
            timestamp: new Date(),
            classroomId: this.config.classroomId,
            special: true
        };

        await this.sendMessage(content, specialMessage);
    }

    // تحديث إعدادات الدردشة
    async updateChatSettings(settings) {
        console.log('⚙️ تحديث إعدادات الدردشة:', settings);
        
        try {
            const response = await fetch('/api/chat/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    classroomId: this.config.classroomId,
                    ...settings
                })
            });

            if (response.ok) {
                console.log('✅ تم تحديث إعدادات الدردشة');
                this.showSuccess('تم تحديث الإعدادات بنجاح');
                return true;
            } else {
                throw new Error('فشل في تحديث الإعدادات');
            }

        } catch (error) {
            console.error('❌ خطأ في تحديث الإعدادات:', error);
            this.showError('فشل في تحديث الإعدادات');
            return false;
        }
    }

    // تصدير البيانات
    async exportMessages() {
        console.log('💾 تصدير الرسائل');
        
        try {
            const response = await fetch(`/api/chat/export?classroomId=${this.config.classroomId}`, {
                headers: {
                    'X-CSRFToken': this.csrfToken
                }
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = `chat-export-${new Date().toISOString().split('T')[0]}.txt`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                this.showSuccess('تم تصدير الرسائل بنجاح');
            }

        } catch (error) {
            console.error('❌ خطأ في تصدير الرسائل:', error);
            this.showError('فشل في تصدير الرسائل');
        }
    }
}

// تصدير للاستخدام العام
window.UnifiedChatSystem = UnifiedChatSystem;
