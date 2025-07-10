import { 
  ChatMessage, 
  ChatRequest, 
  ChatResponse, 
  ConnectionStatus, 
  UIElements, 
  ChatConfig,
  MessageOptions 
} from './types.js';

export class ChatManager {
  private messages: ChatMessage[] = [];
  private conversationId: string | null = null;
  private ui: UIElements;
  private config: ChatConfig;
  private connectionStatus: ConnectionStatus = { connected: false };
  private isProcessing = false;

  constructor(ui: UIElements, config: ChatConfig) {
    this.ui = ui;
    this.config = config;
    this.initializeEventListeners();
    this.checkConnection();
  }

  private initializeEventListeners(): void {
    // Send button click
    this.ui.sendButton.addEventListener('click', () => {
      this.handleSendMessage();
    });

    // Enter key handling
    this.ui.messageInput.addEventListener('keydown', (e: KeyboardEvent) => {
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

  private autoResizeTextarea(): void {
    const textarea = this.ui.messageInput;
    textarea.style.height = 'auto';
    const scrollHeight = Math.min(textarea.scrollHeight, 120); // Max height 120px
    textarea.style.height = `${scrollHeight}px`;
  }

  private updateCharacterCount(): void {
    const length = this.ui.messageInput.value.length;
    const max = this.config.maxMessageLength;
    this.ui.characterCount.textContent = `${length}/${max}`;
    
    if (length > max * 0.9) {
      this.ui.characterCount.style.color = 'var(--error-color)';
    } else if (length > max * 0.7) {
      this.ui.characterCount.style.color = 'var(--warning-color)';
    } else {
      this.ui.characterCount.style.color = 'var(--text-muted)';
    }
  }

  private updateSendButton(): void {
    const hasText = this.ui.messageInput.value.trim().length > 0;
    const isValid = this.ui.messageInput.value.length <= this.config.maxMessageLength;
    this.ui.sendButton.disabled = !hasText || !isValid || this.isProcessing || !this.connectionStatus.connected;
  }

  private async handleSendMessage(): Promise<void> {
    const message = this.ui.messageInput.value.trim();
    if (!message || this.isProcessing) return;

    try {
      this.isProcessing = true;
      this.updateSendButton();
      this.showLoading(true);

      // Add user message
      const userMessage: ChatMessage = {
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
        const assistantMessage: ChatMessage = {
          id: response.data.message_id,
          role: 'assistant',
          content: response.data.response,
          timestamp: new Date(),
          isMarkdown: true
        };
        
        this.conversationId = response.data.conversation_id;
        this.addMessage(assistantMessage, { animate: true });
      } else {
        this.addErrorMessage(response.error || 'Failed to get response');
      }
    } catch (error) {
      console.error('Error sending message:', error);
      this.addErrorMessage('Network error. Please check your connection.');
    } finally {
      this.isProcessing = false;
      this.updateSendButton();
      this.showLoading(false);
    }
  }

  private async sendToAPI(message: string): Promise<ChatResponse> {
    const request: ChatRequest = {
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

    return response.json() as Promise<ChatResponse>;
  }

  private addMessage(message: ChatMessage, options: MessageOptions = {}): void {
    this.messages.push(message);
    
    const messageElement = this.createMessageElement(message);
    this.ui.chatMessages.appendChild(messageElement);

    // Hide welcome message if it exists
    const welcomeMessage = this.ui.chatMessages.querySelector('.welcome-message');
    if (welcomeMessage) {
      (welcomeMessage as HTMLElement).style.display = 'none';
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

  private createMessageElement(message: ChatMessage): HTMLElement {
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
          window.hljs.highlightElement(block as HTMLElement);
        }
      });
    } else {
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

  private formatMarkdown(content: string): string {
    // Simple markdown formatting
    return content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>')
      .replace(/\n/g, '<br>');
  }

  private formatTime(date: Date): string {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  private addErrorMessage(error: string): void {
    const errorMessage: ChatMessage = {
      id: this.generateId(),
      role: 'assistant',
      content: `❌ Error: ${error}`,
      timestamp: new Date()
    };
    this.addMessage(errorMessage);
  }

  private scrollToBottom(): void {
    this.ui.chatMessages.scrollTop = this.ui.chatMessages.scrollHeight;
  }

  private showLoading(show: boolean): void {
    if (show) {
      this.ui.loadingOverlay.classList.add('active');
    } else {
      this.ui.loadingOverlay.classList.remove('active');
    }
  }

  private generateId(): string {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
  }

  private async checkConnection(): Promise<void> {
    try {
      const response = await fetch('/health', { method: 'GET' });
      this.updateConnectionStatus({ 
        connected: response.ok, 
        lastPing: new Date() 
      });
    } catch (error) {
      this.updateConnectionStatus({ 
        connected: false, 
        error: 'Connection failed',
        lastPing: new Date() 
      });
    }

    // Check connection every 30 seconds
    setTimeout(() => this.checkConnection(), 30000);
  }

  private updateConnectionStatus(status: ConnectionStatus): void {
    this.connectionStatus = status;
    
    this.ui.statusIndicator.className = `status-indicator ${
      status.connected ? 'connected' : 'error'
    }`;
    
    this.ui.statusText.textContent = status.connected 
      ? 'Connected' 
      : status.error || 'Disconnected';
    
    this.updateSendButton();
  }

  // Public methods
  public clearChat(): void {
    this.messages = [];
    this.conversationId = null;
    
    const messages = this.ui.chatMessages.querySelectorAll('.message');
    messages.forEach(msg => msg.remove());
    
    const welcomeMessage = this.ui.chatMessages.querySelector('.welcome-message');
    if (welcomeMessage) {
      (welcomeMessage as HTMLElement).style.display = 'block';
    }
  }

  public getMessages(): ChatMessage[] {
    return [...this.messages];
  }

  public isConnected(): boolean {
    return this.connectionStatus.connected;
  }
} 