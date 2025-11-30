import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { api, AuthResponse } from '@/lib/api';
import { toast } from 'sonner';

interface AuthContextType {
  user: AuthResponse['user'] | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name?: string) => Promise<void>;
  loginWithGoogle: (credential: string) => Promise<void>;
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

  // Handle session expiration - show alert and redirect to login
  const handleSessionExpired = useCallback(() => {
    setUser(null);
    toast.error('Your session has expired. Please log in again.', {
      duration: 5000,
    });
    // Redirect to login page
    if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
      window.location.href = '/login';
    }
  }, []);

  useEffect(() => {
    // Set up session expiration handler
    api.setOnSessionExpired(handleSessionExpired);

    // Check if user is already authenticated
    const token = api.getToken();
    if (token) {
      // Check if token is already expired
      const expiration = getTokenExpiration(token);
      if (expiration && Date.now() >= expiration) {
        // Token is expired, try to refresh
        api.refreshToken()
          .then((response) => {
            api.setToken(response.access);
            api.setRefreshToken(response.refresh);
            return api.getCurrentUser();
          })
          .then((userData) => {
            setUser(userData);
          })
          .catch(() => {
            // Refresh failed, session expired
            handleSessionExpired();
          })
          .finally(() => {
            setIsLoading(false);
          });
      } else {
        // Token is valid, fetch user
        api.getCurrentUser()
          .then((userData) => {
            setUser(userData);
          })
          .catch(() => {
            // Token invalid, try to refresh first
            const refreshToken = api.getRefreshToken();
            if (refreshToken) {
              api.refreshToken()
                .then((response) => {
                  api.setToken(response.access);
                  api.setRefreshToken(response.refresh);
                  return api.getCurrentUser();
                })
                .then((userData) => {
                  setUser(userData);
                })
                .catch(() => {
                  handleSessionExpired();
                })
                .finally(() => {
                  setIsLoading(false);
                });
            } else {
              handleSessionExpired();
              setIsLoading(false);
            }
          })
          .finally(() => {
            setIsLoading(false);
          });
      }
    } else {
      setIsLoading(false);
    }
  }, [handleSessionExpired]);

  // Set up automatic token refresh
  useEffect(() => {
    if (!user) return; // Only check if user is logged in

    const checkAndRefreshToken = async () => {
      // Get fresh token each time we check
      const token = api.getToken();
      if (!token) {
        handleSessionExpired();
        return;
      }

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
          // Refresh failed, session expired
          handleSessionExpired();
        }
      }
      
      // If token is already expired, handle session expiration
      if (timeUntilExpiration <= 0) {
        handleSessionExpired();
      }
    };

    // Check immediately
    checkAndRefreshToken();

    // Check every minute
    const interval = setInterval(checkAndRefreshToken, 60 * 1000);

    return () => clearInterval(interval);
  }, [user, handleSessionExpired]);

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

  const loginWithGoogle = async (credential: string) => {
    const response = await api.googleLogin(credential);
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
        loginWithGoogle,
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

