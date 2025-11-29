import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api, AuthResponse } from '@/lib/api';

interface AuthContextType {
  user: AuthResponse['user'] | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name?: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Helper function to decode JWT and get expiration time
function getTokenExpiration(token: string): number | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.exp ? payload.exp * 1000 : null; // Convert to milliseconds
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthResponse['user'] | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check if user is already authenticated
    const token = api.getToken();
    if (token) {
      api.getCurrentUser()
        .then((userData) => {
          setUser(userData);
        })
        .catch(() => {
          // Token invalid, clear it
          api.clearTokens();
        })
        .finally(() => {
          setIsLoading(false);
        });
    } else {
      setIsLoading(false);
    }
  }, []);

  // Set up automatic token refresh
  useEffect(() => {
    const token = api.getToken();
    if (!token) return;

    const checkAndRefreshToken = async () => {
      const expiration = getTokenExpiration(token);
      if (!expiration) return;

      const now = Date.now();
      const timeUntilExpiration = expiration - now;
      const refreshBeforeMs = 5 * 60 * 1000; // Refresh 5 minutes before expiration

      // If token expires soon, refresh it
      if (timeUntilExpiration > 0 && timeUntilExpiration < refreshBeforeMs) {
        try {
          const response = await api.refreshToken();
          api.setToken(response.access);
          api.setRefreshToken(response.refresh);
        } catch (error) {
          // Refresh failed, user will need to login again
          console.error('Token refresh failed:', error);
          api.clearTokens();
          setUser(null);
        }
      }
    };

    // Check immediately
    checkAndRefreshToken();

    // Check every minute
    const interval = setInterval(checkAndRefreshToken, 60 * 1000);

    return () => clearInterval(interval);
  }, [user]);

  const login = async (email: string, password: string) => {
    const response = await api.login({ email, password });
    api.setToken(response.access);
    api.setRefreshToken(response.refresh);
    setUser(response.user);
  };

  const register = async (email: string, password: string, name?: string) => {
    const response = await api.register({ email, password, name });
    api.setToken(response.access);
    api.setRefreshToken(response.refresh);
    setUser(response.user);
  };

  const logout = async () => {
    await api.logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

