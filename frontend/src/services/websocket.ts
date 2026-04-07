export interface ChatMessage {
  type: 'player_message' | 'kp_response' | 'kp_thinking' | 'kp_thinking_chunk' | 'dice_result' | 'system' | 'error' | 'save_loaded' | 'history_clear';
  role: string;
  content: string;
  username?: string;
  dice_type?: string;
  rolls?: number[];
  modifier?: number;
  total?: number;
  success?: boolean;
  timestamp?: string;
  id?: string;
  thinking_id?: string;
}

type MessageHandler = (message: ChatMessage) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private campaignId: number | null = null;
  private token: string | null = null;
  private handlers: Set<MessageHandler> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  connect(campaignId: number, token: string): Promise<void> {
    return new Promise((resolve, reject) => {
      this.campaignId = campaignId;
      this.token = token;

      const wsUrl = `ws://localhost:8000/ws/chat/${campaignId}?token=${token}`;
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        resolve();
      };

      this.ws.onmessage = (event) => {
        try {
          const message: ChatMessage = JSON.parse(event.data);
          this.handlers.forEach((handler) => handler(message));
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        reject(error);
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          console.log(`Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
          setTimeout(() => {
            if (this.campaignId && this.token) {
              this.connect(this.campaignId, this.token).catch(console.error);
            }
          }, 2000);
        }
      };
    });
  }

  send(message: { type: string; content?: string; save_id?: number }) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  sendPlayerMessage(content: string) {
    this.send({ type: 'player_message', content });
  }

  sendRollDice(diceStr: string) {
    this.send({ type: 'roll_dice', content: diceStr });
  }

  loadSave(saveId: number) {
    this.send({ type: 'load_save', save_id: saveId });
  }

  onMessage(handler: MessageHandler) {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.campaignId = null;
    this.token = null;
    this.handlers.clear();
  }
}

export const wsService = new WebSocketService();
