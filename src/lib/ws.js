/**
 * SplatMaker — WebSocket manager with auto-reconnect
 */
const WS_URL = 'ws://127.0.0.1:8420/ws/pipeline';

class WebSocketManager {
  constructor() {
    this.ws = null;
    this.listeners = {};
    this.reconnectDelay = 1000;
    this.maxReconnectDelay = 10000;
    this.shouldReconnect = true;
  }

  connect() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) return;
    
    try {
      this.ws = new WebSocket(WS_URL);
      
      this.ws.onopen = () => {
        this.reconnectDelay = 1000;
        this.emit('connected');
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.emit(data.type, data);
          this.emit('message', data);
        } catch (e) {
          console.warn('[WS] Failed to parse message:', e);
        }
      };

      this.ws.onclose = () => {
        this.emit('disconnected');
        if (this.shouldReconnect) {
          setTimeout(() => this.connect(), this.reconnectDelay);
          this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, this.maxReconnectDelay);
        }
      };

      this.ws.onerror = () => {
        // onclose will fire after this
      };
    } catch (e) {
      setTimeout(() => this.connect(), this.reconnectDelay);
    }
  }

  disconnect() {
    this.shouldReconnect = false;
    if (this.ws) this.ws.close();
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  on(event, callback) {
    if (!this.listeners[event]) this.listeners[event] = [];
    this.listeners[event].push(callback);
    return () => this.off(event, callback);
  }

  off(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
    }
  }

  emit(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(cb => cb(data));
    }
  }
}

export const wsManager = new WebSocketManager();
