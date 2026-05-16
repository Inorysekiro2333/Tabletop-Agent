import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器 - 添加 token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器 - 处理错误
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth
export const authAPI = {
  register: (username: string, password: string) =>
    api.post('/auth/register', { username, password }),
  login: (username: string, password: string) =>
    api.post('/auth/login', { username, password }),
  getMe: () => api.get('/auth/me'),
};

// AI Configs
export interface AIConfig {
  id: number;
  user_id: number;
  provider: 'claude' | 'deepseek' | 'minimax';
  api_key_masked: string;
  base_url?: string;
  model_name: string;
  is_active: boolean;
  created_at: string;
}

export const aiConfigAPI = {
  list: () => api.get<AIConfig[]>('/ai-configs'),
  create: (data: { provider: string; api_key: string; base_url?: string; model_name: string }) =>
    api.post('/ai-configs', data),
  update: (id: number, data: Partial<AIConfig>) => api.put(`/ai-configs/${id}`, data),
  delete: (id: number) => api.delete(`/ai-configs/${id}`),
  activate: (id: number) => api.put(`/ai-configs/${id}/activate`),
};

// Characters
export interface Character {
  id: number;
  user_id: number;
  name: string;
  race?: string;
  character_class?: string;
  level: number;
  attributes: { STR: number; DEX: number; CON: number; INT: number; WIS: number; CHA: number };
  hp: number;
  ac: number;
  skills: string[];
  equipment: string[];
  backstory?: string;
  personality: Record<string, string>;
  relationships?: Array<{ name: string; type: string; description: string; attitude: string }>;
  faction?: string;
  goals?: Array<{ name: string; description: string; status: string }>;
  ideals?: string[];
  flaws?: string[];
  personal_traits?: string[];
  created_at: string;
  updated_at: string;
}

export const characterAPI = {
  list: () => api.get<Character[]>('/characters'),
  create: (data: Partial<Character>) => api.post('/characters', data),
  generate: (data: { race_preference?: string; class_preference?: string; personality_hints?: string }) =>
    api.post('/characters/generate', data),
  get: (id: number) => api.get<Character>(`/characters/${id}`),
  update: (id: number, data: Partial<Character>) => api.put(`/characters/${id}`, data),
  delete: (id: number) => api.delete(`/characters/${id}`),
};

// Campaigns
export interface Campaign {
  id: number;
  user_id: number;
  title: string;
  description?: string;
  ai_config_id?: number;
  character_id?: number;
  system_prompt?: string;
  current_session: number;
  status: 'active' | 'archived';
  created_at: string;
  updated_at: string;
  last_played_at: string | null;
}

export const campaignAPI = {
  list: () => api.get<Campaign[]>('/campaigns'),
  create: (data: Partial<Campaign>) => api.post('/campaigns', data),
  get: (id: number) => api.get<Campaign>(`/campaigns/${id}`),
  update: (id: number, data: Partial<Campaign>) => api.put(`/campaigns/${id}`, data),
  delete: (id: number) => api.delete(`/campaigns/${id}`),
};

// Saves
export interface Save {
  id: number;
  campaign_id: number;
  name: string;
  description?: string;
  snapshot: Record<string, unknown>;
  created_at: string;
}

export const saveAPI = {
  list: (campaignId: number) => api.get<Save[]>(`/saves/campaign/${campaignId}/saves`),
  create: (campaignId: number, data: { name: string; description?: string; snapshot: Record<string, unknown> }) =>
    api.post(`/saves/campaign/${campaignId}/saves`, data),
  load: (saveId: number) => api.get<Save>(`/saves/${saveId}/load`),
  delete: (saveId: number) => api.delete(`/saves/${saveId}`),
};

export default api;
