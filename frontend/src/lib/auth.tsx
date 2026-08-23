import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { api, getToken, setToken } from "@/lib/api";
import type { LoginResponse, Usuario } from "@/lib/types";

interface AuthState {
  usuario: Usuario | null;
  cargando: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [cargando, setCargando] = useState(true);

  // Al montar: si hay token guardado, restaurar la sesion pidiendo el perfil.
  useEffect(() => {
    const token = getToken();
    if (!token) {
      setCargando(false);
      return;
    }
    api
      .get<Usuario>("/auth/perfil/")
      .then((res) => setUsuario(res.data))
      .catch(() => setToken(null))
      .finally(() => setCargando(false));
  }, []);

  async function login(username: string, password: string) {
    const res = await api.post<LoginResponse>("/auth/login/", {
      username,
      password,
    });
    setToken(res.data.token);
    setUsuario(res.data.usuario);
  }

  async function logout() {
    try {
      await api.post("/auth/logout/");
    } finally {
      setToken(null);
      setUsuario(null);
    }
  }

  return (
    <AuthContext.Provider value={{ usuario, cargando, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  return ctx;
}
