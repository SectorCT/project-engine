import { useEffect, useRef, useState, useCallback } from 'react';
import { api } from '@/lib/api';

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000';
const ALLOW_WS_TOKEN_QUERY = import.meta.env.VITE_ALLOW_WS_TOKEN_QUERY !== 'false';

export interface WebSocketMessage {
  kind: 'jobStatus' | 'agentDialogue' | 'stageUpdate' | 'prdReady' | 'error';
  jobId?: string;
  role?: 'user' | 'agent' | 'system';
  sender?: string;
  content?: string;
  metadata?: Record<string, any>;
  status?: string;
  message?: string;
  agent?: string;
  order?: number;
  spec?: Record<string, any>;
  prdMarkdown?: string;
  timestamp?: string;
}

export interface UseWebSocketOptions {
  jobId: string;
  onMessage?: (message: WebSocketMessage) => void;
  onError?: (error: Event) => void;
  onOpen?: () => void;
  onClose?: () => void;
  enabled?: boolean;
}

export function useWebSocket({
  jobId,
  onMessage,
  onError,
  onOpen,
  onClose,
  enabled = true,
}: UseWebSocketOptions) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = useCallback(() => {
    if (!enabled || !jobId) return;

    const token = api.getToken();
    if (!token) {
      console.error('No authentication token available for WebSocket connection');
      return;
    }

    // Build WebSocket URL
    let wsUrl = `${WS_BASE_URL}/ws/jobs/${jobId}/`;
    
    // Add token to query string if allowed (dev mode)
    if (ALLOW_WS_TOKEN_QUERY) {
      wsUrl += `?token=${encodeURIComponent(token)}`;
    }

    try {
      const ws = new WebSocket(wsUrl);

      // Set Authorization header if possible (some browsers support this)
      // Note: WebSocket API doesn't support custom headers in browser, so we rely on query param

      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        reconnectAttempts.current = 0;
        onOpen?.();
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          setLastMessage(message);
          onMessage?.(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        onError?.(error);
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        onClose?.();

        // Attempt to reconnect
        if (enabled && reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current += 1;
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
          reconnectTimeoutRef.current = window.setTimeout(() => {
            console.log(`Reconnecting... (attempt ${reconnectAttempts.current})`);
            connect();
          }, delay);
        }
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
    }
  }, [jobId, enabled, onMessage, onError, onOpen, onClose]);

  const sendMessage = useCallback((message: { kind: string; content?: string; [key: string]: any }) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected. Message not sent:', message);
    }
  }, []);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  useEffect(() => {
    if (enabled && jobId) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [enabled, jobId, connect, disconnect]);

  return {
    isConnected,
    lastMessage,
    sendMessage,
    disconnect,
    reconnect: connect,
  };
}

