import axios from "axios";

// Cliente HTTP unico. En desarrollo, baseURL vacia -> usa el proxy /api de Vite
// (vite.config.ts) hacia el backend Django. En produccion, VITE_API_URL fija el
// origen real. El token de DRF se guarda en localStorage y viaja en cada peticion.
const TOKEN_KEY = "triverde_token";

export const api = axios.create({
  baseURL: `${import.meta.env.VITE_API_URL ?? ""}/api/v1`,
  headers: { "Content-Type": "application/json" },
});

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Token ${token}`;
  }
  return config;
});
