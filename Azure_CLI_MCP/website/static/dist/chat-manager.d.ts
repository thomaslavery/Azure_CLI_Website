import { ChatMessage, UIElements, ChatConfig } from './types.js';
export declare class ChatManager {
    private messages;
    private conversationId;
    private ui;
    private config;
    private connectionStatus;
    private isProcessing;
    constructor(ui: UIElements, config: ChatConfig);
    private initializeEventListeners;
    private autoResizeTextarea;
    private updateCharacterCount;
    private updateSendButton;
    private handleSendMessage;
    private sendToAPI;
    private addMessage;
    private createMessageElement;
    private formatMarkdown;
    private formatTime;
    private addErrorMessage;
    private scrollToBottom;
    private showLoading;
    private generateId;
    private checkConnection;
    private updateConnectionStatus;
    clearChat(): void;
    getMessages(): ChatMessage[];
    isConnected(): boolean;
}
//# sourceMappingURL=chat-manager.d.ts.map