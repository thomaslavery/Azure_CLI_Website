export class ChatManager {
    constructor(ui, config) {
        this.messages = [];
        this.conversationId = null;
        this.connectionStatus = { connected: false };
        this.isProcessing = false;
        this.ui = ui;
        this.config = config;
        this.initializeEventListeners();
        this.checkConnection();
    }
    initializeEventListeners() {
        // Send button click
        this.ui.sendButton.addEventListener('click', () => {
            this.handleSendMessage();
        });
        // Enter key handling
        this.ui.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSendMessage();
            }
        });
        // Auto-resize textarea and character count
        this.ui.messageInput.addEventListener('input', () => {
            this.autoResizeTextarea();
            this.updateCharacterCount();
            this.updateSendButton();
        });
        // Focus management
        this.ui.messageInput.addEventListener('focus', () => {
            this.ui.messageInput.parentElement?.classList.add('focused');
        });
        this.ui.messageInput.addEventListener('blur', () => {
            this.ui.messageInput.parentElement?.classList.remove('focused');
        });
    }
    autoResizeTextarea() {
        const textarea = this.ui.messageInput;
        textarea.style.height = 'auto';
        const scrollHeight = Math.min(textarea.scrollHeight, 120); // Max height 120px
        textarea.style.height = `${scrollHeight}px`;
    }
    updateCharacterCount() {
        const length = this.ui.messageInput.value.length;
        const max = this.config.maxMessageLength;
        this.ui.characterCount.textContent = `${length}/${max}`;
        if (length > max * 0.9) {
            this.ui.characterCount.style.color = 'var(--error-color)';
        }
        else if (length > max * 0.7) {
            this.ui.characterCount.style.color = 'var(--warning-color)';
        }
        else {
            this.ui.characterCount.style.color = 'var(--text-muted)';
        }
    }
    updateSendButton() {
        const hasText = this.ui.messageInput.value.trim().length > 0;
        const isValid = this.ui.messageInput.value.length <= this.config.maxMessageLength;
        this.ui.sendButton.disabled = !hasText || !isValid || this.isProcessing || !this.connectionStatus.connected;
    }
    async handleSendMessage() {
        const message = this.ui.messageInput.value.trim();
        if (!message || this.isProcessing)
            return;
        try {
            this.isProcessing = true;
            this.updateSendButton();
            this.showLoading(true);
            // Add user message
            const userMessage = {
                id: this.generateId(),
                role: 'user',
                content: message,
                timestamp: new Date()
            };
            this.addMessage(userMessage);
            this.ui.messageInput.value = '';
            this.autoResizeTextarea();
            this.updateCharacterCount();
            // Send to API
            const response = await this.sendToAPI(message);
            if (response.success && response.data) {
                const assistantMessage = {
                    id: response.data.message_id,
                    role: 'assistant',
                    content: response.data.response,
                    timestamp: new Date(),
                    isMarkdown: true
                };
                this.conversationId = response.data.conversation_id;
                this.addMessage(assistantMessage, { animate: true });
            }
            else {
                this.addErrorMessage(response.error || 'Failed to get response');
            }
        }
        catch (error) {
            console.error('Error sending message:', error);
            this.addErrorMessage('Network error. Please check your connection.');
        }
        finally {
            this.isProcessing = false;
            this.updateSendButton();
            this.showLoading(false);
        }
    }
    async sendToAPI(message) {
        const request = {
            message,
            ...(this.conversationId && { conversation_id: this.conversationId })
        };
        const response = await fetch(this.config.apiEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(request)
        });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    }
    addMessage(message, options = {}) {
        this.messages.push(message);
        const messageElement = this.createMessageElement(message);
        this.ui.chatMessages.appendChild(messageElement);
        // Hide welcome message if it exists
        const welcomeMessage = this.ui.chatMessages.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.style.display = 'none';
        }
        if (options.animate !== false) {
            requestAnimationFrame(() => {
                messageElement.classList.add('animate-in');
            });
        }
        if (options.scrollToBottom !== false) {
            this.scrollToBottom();
        }
    }
    createMessageElement(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${message.role}`;
        messageDiv.setAttribute('data-message-id', message.id);
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = message.role === 'user' ? 'U' : 'AI';
        const content = document.createElement('div');
        content.className = 'message-content';
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        const text = document.createElement('div');
        text.className = 'message-text';
        if (message.isMarkdown) {
            text.innerHTML = this.formatMarkdown(message.content);
            // Highlight code blocks
            text.querySelectorAll('pre code').forEach((block) => {
                if (typeof window !== 'undefined' && window.hljs) {
                    window.hljs.highlightElement(block);
                }
            });
        }
        else {
            text.textContent = message.content;
        }
        const time = document.createElement('div');
        time.className = 'message-time';
        time.textContent = this.formatTime(message.timestamp);
        bubble.appendChild(text);
        bubble.appendChild(time);
        content.appendChild(bubble);
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);
        return messageDiv;
    }
    formatMarkdown(content) {
        // Simple markdown formatting
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>')
            .replace(/\n/g, '<br>');
    }
    formatTime(date) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    addErrorMessage(error) {
        const errorMessage = {
            id: this.generateId(),
            role: 'assistant',
            content: `❌ Error: ${error}`,
            timestamp: new Date()
        };
        this.addMessage(errorMessage);
    }
    scrollToBottom() {
        this.ui.chatMessages.scrollTop = this.ui.chatMessages.scrollHeight;
    }
    showLoading(show) {
        if (show) {
            this.ui.loadingOverlay.classList.add('active');
        }
        else {
            this.ui.loadingOverlay.classList.remove('active');
        }
    }
    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }
    async checkConnection() {
        try {
            const response = await fetch('/health', { method: 'GET' });
            this.updateConnectionStatus({
                connected: response.ok,
                lastPing: new Date()
            });
        }
        catch (error) {
            this.updateConnectionStatus({
                connected: false,
                error: 'Connection failed',
                lastPing: new Date()
            });
        }
        // Check connection every 30 seconds
        setTimeout(() => this.checkConnection(), 30000);
    }
    updateConnectionStatus(status) {
        this.connectionStatus = status;
        this.ui.statusIndicator.className = `status-indicator ${status.connected ? 'connected' : 'error'}`;
        this.ui.statusText.textContent = status.connected
            ? 'Connected'
            : status.error || 'Disconnected';
        this.updateSendButton();
    }
    // Public methods
    clearChat() {
        this.messages = [];
        this.conversationId = null;
        const messages = this.ui.chatMessages.querySelectorAll('.message');
        messages.forEach(msg => msg.remove());
        const welcomeMessage = this.ui.chatMessages.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.style.display = 'block';
        }
    }
    getMessages() {
        return [...this.messages];
    }
    isConnected() {
        return this.connectionStatus.connected;
    }
}
//# sourceMappingURL=chat-manager.js.map