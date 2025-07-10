export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    isMarkdown?: boolean;
}
export interface ApiResponse {
    success: boolean;
    message?: string;
    data?: unknown;
    error?: string;
}
export interface ChatRequest {
    message: string;
    conversation_id?: string | undefined;
}
export interface ChatResponse extends ApiResponse {
    data?: {
        response: string;
        conversation_id: string;
        message_id: string;
    };
}
export interface ConnectionStatus {
    connected: boolean;
    error?: string;
    lastPing?: Date;
}
export interface UIElements {
    chatMessages: HTMLElement;
    messageInput: HTMLTextAreaElement;
    sendButton: HTMLButtonElement;
    loadingOverlay: HTMLElement;
    statusIndicator: HTMLElement;
    statusText: HTMLElement;
    characterCount: HTMLElement;
}
export interface ChatConfig {
    apiEndpoint: string;
    maxMessageLength: number;
    reconnectAttempts: number;
    reconnectDelay: number;
    typing: {
        enabled: boolean;
        speed: number;
    };
}
export interface MessageOptions {
    animate?: boolean;
    scrollToBottom?: boolean;
    showTime?: boolean;
}
declare global {
    interface Window {
        hljs?: {
            highlightElement: (element: HTMLElement) => void;
        };
    }
    const hljs: {
        highlightElement: (element: HTMLElement) => void;
    } | undefined;
}
//# sourceMappingURL=types.d.ts.map