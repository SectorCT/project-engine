const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export interface ApiError {
  detail?: string;
  message?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name?: string;
}

export interface AuthResponse {
  access: string;
  refresh: string;
  user: {
    id: string;
    email: string;
    name?: string;
  };
}

export interface Job {
  id: string;
  initial_prompt: string;
  prompt: string;
  requirements_summary: string;
  status: 'collecting' | 'queued' | 'running' | 'done' | 'failed';
  error_message: string;
  created_at: string;
  updated_at: string;
  steps?: JobStep[];
  messages?: JobMessage[];
}

export interface JobStep {
  id: string;
  agent_name: string;
  message: string;
  order: number;
  created_at: string;
}

export interface JobMessage {
  id: string;
  role: 'user' | 'agent' | 'system';
  sender: string;
  content: string;
  metadata: Record<string, any>;
  created_at: string;
}

export interface App {
  id: string;
  job_id: string;
  spec: Record<string, any>;
  created_at: string;
  updated_at: string;
}

class ApiClient {
  private baseURL: string;
  private token: string | null = null;
  private refreshTokenValue: string | null = null;
  private isRefreshing: boolean = false;
  private refreshPromise: Promise<string | null> | null = null;

  constructor(baseURL: string) {
    this.baseURL = baseURL;
    // Load tokens from localStorage on initialization
    this.token = localStorage.getItem('access_token');
    this.refreshTokenValue = localStorage.getItem('refresh_token');
  }

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem('access_token', token);
    } else {
      localStorage.removeItem('access_token');
    }
  }

  setRefreshToken(refreshToken: string | null) {
    this.refreshTokenValue = refreshToken;
    if (refreshToken) {
      localStorage.setItem('refresh_token', refreshToken);
    } else {
      localStorage.removeItem('refresh_token');
    }
  }

  getToken(): string | null {
    return this.token || localStorage.getItem('access_token');
  }

  getRefreshToken(): string | null {
    return this.refreshTokenValue || localStorage.getItem('refresh_token');
  }

  clearTokens() {
    this.token = null;
    this.refreshTokenValue = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }

  async refreshToken(): Promise<AuthResponse> {
    const refresh = this.getRefreshToken();
    if (!refresh) {
      throw new Error('No refresh token available');
    }
    return this.request<AuthResponse>('/api/auth/token/refresh/', {
      method: 'POST',
      body: JSON.stringify({ refresh }),
    });
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    retryOn401: boolean = true
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const token = this.getToken();

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    // Handle 401 Unauthorized - try to refresh token
    if (response.status === 401 && retryOn401 && this.getRefreshToken()) {
      // If already refreshing, wait for that promise
      if (this.isRefreshing && this.refreshPromise) {
        await this.refreshPromise;
        // Retry the request with new token
        return this.request<T>(endpoint, options, false);
      }

      // Start refresh process
      this.isRefreshing = true;
      this.refreshPromise = this.refreshToken()
        .then((authResponse) => {
          this.setToken(authResponse.access);
          this.setRefreshToken(authResponse.refresh);
          this.isRefreshing = false;
          this.refreshPromise = null;
          return authResponse.access;
        })
        .catch((error) => {
          this.isRefreshing = false;
          this.refreshPromise = null;
          // Refresh failed, clear tokens
          this.clearTokens();
          throw error;
        });

      await this.refreshPromise;
      // Retry the request with new token
      return this.request<T>(endpoint, options, false);
    }

    if (!response.ok) {
      let error: ApiError;
      try {
        error = await response.json();
      } catch {
        error = { detail: `HTTP ${response.status}: ${response.statusText}` };
      }
      throw error;
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return null as T;
    }

    return response.json();
  }

  // Authentication
  async login(data: LoginRequest): Promise<AuthResponse> {
    return this.request<AuthResponse>('/api/auth/login/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async register(data: RegisterRequest): Promise<AuthResponse> {
    return this.request<AuthResponse>('/api/auth/register/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getCurrentUser() {
    return this.request<AuthResponse['user']>('/api/auth/me/');
  }

  async logout(refreshToken?: string) {
    const refresh = refreshToken || this.getRefreshToken();
    if (refresh) {
      try {
        await this.request('/api/auth/logout/', {
          method: 'POST',
          body: JSON.stringify({ refresh }),
        });
      } catch (error) {
        // Even if logout fails, clear tokens locally
        console.error('Logout request failed:', error);
      }
    }
    this.clearTokens();
  }

  // Jobs
  async getJobs(): Promise<Job[]> {
    return this.request<Job[]>('/api/jobs/');
  }

  async getJob(jobId: string): Promise<Job> {
    return this.request<Job>(`/api/jobs/${jobId}/`);
  }

  async createJob(prompt: string): Promise<Job> {
    return this.request<Job>('/api/jobs/', {
      method: 'POST',
      body: JSON.stringify({ prompt }),
    });
  }

  async updateJob(jobId: string, initial_prompt: string): Promise<Job> {
    return this.request<Job>(`/api/jobs/${jobId}/`, {
      method: 'PATCH',
      body: JSON.stringify({ initial_prompt }),
    });
  }

  async deleteJob(jobId: string): Promise<void> {
    return this.request<void>(`/api/jobs/${jobId}/`, {
      method: 'DELETE',
    });
  }

  async purgeJobs(): Promise<{ deleted: number }> {
    return this.request<{ deleted: number }>('/api/jobs/purge/', {
      method: 'DELETE',
    });
  }

  // Job Messages
  async getJobMessages(jobId: string): Promise<JobMessage[]> {
    return this.request<JobMessage[]>(`/api/job-messages/?job_id=${jobId}`);
  }

  async deleteJobMessage(messageId: string): Promise<void> {
    return this.request<void>(`/api/job-messages/${messageId}/`, {
      method: 'DELETE',
    });
  }

  // Apps
  async getApps(): Promise<App[]> {
    return this.request<App[]>('/api/apps/');
  }

  async getApp(appId: string): Promise<App> {
    return this.request<App>(`/api/apps/${appId}/`);
  }

  async getAppByJob(jobId: string): Promise<App | null> {
    try {
      return await this.request<App>(`/api/apps/by-job/${jobId}/`);
    } catch (error: any) {
      // 204 means no app yet
      if (error?.detail?.includes('204') || error?.detail?.includes('No Content')) {
        return null;
      }
      throw error;
    }
  }
}

export const api = new ApiClient(API_BASE_URL);

