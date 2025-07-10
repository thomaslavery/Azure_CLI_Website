import { ChatManager } from './chat-manager.js';
declare class AzureChatApp {
    private chatManager;
    constructor();
    private initializeApp;
    private setupApp;
    private getUIElements;
    private getConfig;
    private setupGlobalHandlers;
    private handleResize;
    private handleVisibilityChange;
    private handleGlobalKeydown;
    private handleBeforeUnload;
    private showInitializationError;
    getChatManager(): ChatManager | null;
}
declare global {
    interface Window {
        azureChatApp: AzureChatApp;
    }
}
export {};
//# sourceMappingURL=app.d.ts.map