import { useEffect, useRef, useState, useCallback } from 'react';
import { api } from '@/lib/api';

// Derive WebSocket URL from API base URL
function getWebSocketUrl(): string {
  // If explicitly set, use it (ensure it's the correct protocol)
  if (import.meta.env.VITE_WS_BASE_URL) {
    const wsUrl = import.meta.env.VITE_WS_BASE_URL;
    // Ensure protocol matches - if API is HTTPS, WebSocket should be WSS
    const apiUrl = import.meta.env.VITE_API_BASE_URL || '';
    if (apiUrl.startsWith('https://') && wsUrl.startsWith('ws://')) {
      console.warn('WebSocket URL uses ws:// but API uses https://. This may cause connection issues.');
      return wsUrl.replace('ws://', 'wss://');
    }
    return wsUrl;
  }
  
  // Otherwise, derive from API base URL
  const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  try {
    const url = new URL(apiUrl);
    // Convert http -> ws, https -> wss
    const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${url.host}`;
  } catch {
    // Fallback to default
    return 'ws://localhost:8000';
  }
}

const WS_BASE_URL = getWebSocketUrl();
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
      onError?.(new Event('no_token'));
      return;
    }

    // Build WebSocket URL
    let wsUrl = `${WS_BASE_URL}/ws/jobs/${jobId}/`;
    
    // Always add token to query string (browsers can't set custom headers for WebSocket)
    // The server middleware will check for query token if ALLOW_WS_TOKEN_QUERY is enabled
      wsUrl += `?token=${encodeURIComponent(token)}`;

    // Clean up any existing connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    try {
      console.log('Connecting to WebSocket:', wsUrl.replace(token, '***'));
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

      ws.onclose = (event) => {
        console.log('WebSocket disconnected', { code: event.code, reason: event.reason, wasClean: event.wasClean });
        setIsConnected(false);
        onClose?.();

        // Don't reconnect on normal closure (1000) or authentication errors
        if (event.code === 1000 && event.wasClean) {
          console.log('WebSocket closed normally');
          return;
        }

        // Don't reconnect on authentication errors (403) or unauthorized (4001, 4003)
        if (event.code === 4003 || event.code === 4001 || event.code === 1008) {
          console.error('WebSocket connection closed due to authentication/authorization error. Please check your token.');
          onError?.(event);
          return;
        }

        // Attempt to reconnect for other errors
        if (enabled && reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current += 1;
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
          reconnectTimeoutRef.current = window.setTimeout(() => {
            console.log(`Reconnecting... (attempt ${reconnectAttempts.current})`);
            connect();
          }, delay);
        } else if (reconnectAttempts.current >= maxReconnectAttempts) {
          console.error('Max reconnection attempts reached. Please refresh the page.');
          onError?.(event);
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, jobId]); // Only depend on enabled and jobId to avoid recreating connections

  return {
    isConnected,
    lastMessage,
    sendMessage,
    disconnect,
    reconnect: connect,
  };
}

