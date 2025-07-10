import { ChatManager } from './chat-manager.js';
import { UIElements, ChatConfig } from './types.js';

class AzureChatApp {
  private chatManager: ChatManager | null = null;

  constructor() {
    this.initializeApp();
  }

  private initializeApp(): void {
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.setupApp());
    } else {
      this.setupApp();
    }
  }

  private setupApp(): void {
    try {
      const ui = this.getUIElements();
      const config = this.getConfig();
      
      this.chatManager = new ChatManager(ui, config);
      this.setupGlobalHandlers();
      
      console.log('Azure CLI Chat Assistant initialized successfully');
    } catch (error) {
      console.error('Failed to initialize chat app:', error);
      this.showInitializationError();
    }
  }

  private getUIElements(): UIElements {
    const elements = {
      chatMessages: document.getElementById('chat-messages'),
      messageInput: document.getElementById('message-input') as HTMLTextAreaElement,
      sendButton: document.getElementById('send-button') as HTMLButtonElement,
      loadingOverlay: document.getElementById('loading-overlay'),
      statusIndicator: document.getElementById('status-indicator'),
      statusText: document.getElementById('status-text'),
      characterCount: document.getElementById('character-count')
    };

    // Validate all elements exist
    for (const [key, element] of Object.entries(elements)) {
      if (!element) {
        throw new Error(`Required UI element not found: ${key}`);
      }
    }

    return elements as UIElements;
  }

  private getConfig(): ChatConfig {
    return {
      apiEndpoint: '/api/chat',
      maxMessageLength: 2000,
      reconnectAttempts: 3,
      reconnectDelay: 5000,
      typing: {
        enabled: true,
        speed: 50
      }
    };
  }

  private setupGlobalHandlers(): void {
    // Handle window resize
    window.addEventListener('resize', this.handleResize.bind(this));

    // Handle visibility change (tab switching)
    document.addEventListener('visibilitychange', this.handleVisibilityChange.bind(this));

    // Handle keyboard shortcuts
    document.addEventListener('keydown', this.handleGlobalKeydown.bind(this));

    // Handle unload (cleanup)
    window.addEventListener('beforeunload', this.handleBeforeUnload.bind(this));
  }

  private handleResize(): void {
    // Trigger scroll to bottom if needed
    if (this.chatManager) {
      const messages = this.chatManager.getMessages();
      if (messages.length > 0) {
        // Small delay to ensure layout is updated
        setTimeout(() => {
          const chatMessages = document.getElementById('chat-messages');
          if (chatMessages) {
            chatMessages.scrollTop = chatMessages.scrollHeight;
          }
        }, 100);
      }
    }
  }

  private handleVisibilityChange(): void {
    if (!document.hidden && this.chatManager) {
      // Tab became visible, check connection
      const input = document.getElementById('message-input') as HTMLTextAreaElement;
      if (input && this.chatManager.isConnected()) {
        input.focus();
      }
    }
  }

  private handleGlobalKeydown(event: KeyboardEvent): void {
    // Ctrl/Cmd + K to clear chat
    if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
      event.preventDefault();
      if (this.chatManager) {
        this.chatManager.clearChat();
      }
    }

    // Escape to focus input
    if (event.key === 'Escape') {
      const input = document.getElementById('message-input') as HTMLTextAreaElement;
      if (input) {
        input.focus();
      }
    }
  }

  private handleBeforeUnload(): void {
    // Clean up resources if needed
    console.log('Azure CLI Chat Assistant shutting down');
  }

  private showInitializationError(): void {
    document.body.innerHTML = `
      <div style="
        display: flex; 
        flex-direction: column; 
        align-items: center; 
        justify-content: center; 
        height: 100vh; 
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background: var(--background-color, #faf9f8);
        color: var(--text-primary, #323130);
        text-align: center;
        padding: 2rem;
      ">
        <div style="
          background: var(--surface-color, #ffffff);
          border: 1px solid var(--border-color, #edebe9);
          border-radius: 12px;
          padding: 3rem;
          box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
          max-width: 500px;
        ">
          <div style="
            width: 64px;
            height: 64px;
            margin: 0 auto 1.5rem;
            background: var(--error-color, #d13438);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2rem;
            color: white;
          ">⚠️</div>
          <h1 style="margin: 0 0 1rem; font-size: 1.5rem; font-weight: 600;">
            Initialization Error
          </h1>
          <p style="margin: 0 0 2rem; color: var(--text-secondary, #605e5c); line-height: 1.5;">
            Failed to initialize the Azure CLI Chat Assistant. Please check the console for details and refresh the page to try again.
          </p>
          <button onclick="window.location.reload()" style="
            background: var(--primary-color, #0078d4);
            color: white;
            border: none;
            border-radius: 6px;
            padding: 0.75rem 1.5rem;
            font-size: 1rem;
            cursor: pointer;
            transition: background-color 0.2s;
          ">
            Refresh Page
          </button>
        </div>
      </div>
    `;
  }

  // Public API
  public getChatManager(): ChatManager | null {
    return this.chatManager;
  }
}

// Initialize the application
const app = new AzureChatApp();

// Export for global access if needed
declare global {
  interface Window {
    azureChatApp: AzureChatApp;
  }
}

window.azureChatApp = app; 