import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Leaf, LogIn } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/Button";
import { Campo, Input } from "@/components/ui/Field";
import { isAxiosError } from "axios";

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      await login(username, password);
      navigate("/");
    } catch (err) {
      if (isAxiosError(err) && err.response?.status === 400) {
        setError("Usuario o clave incorrectos, o la cuenta esta inactiva.");
      } else {
        setError("No se pudo conectar con el servidor. Intenta de nuevo.");
      }
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="flex min-h-full items-center justify-center bg-gradient-to-br from-brand-900 via-brand-800 to-brand-950 p-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-700 text-white shadow-lg">
            <Leaf className="h-7 w-7" />
          </div>
          <h1 className="text-2xl font-semibold text-white">Triverde</h1>
          <p className="text-sm text-brand-200">Gestion operativa de la planta</p>
        </div>

        <form
          onSubmit={onSubmit}
          className="space-y-4 rounded-2xl bg-white p-6 shadow-xl"
        >
          <Campo label="Usuario" htmlFor="username" requerido>
            <Input
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              autoFocus
              required
            />
          </Campo>
          <Campo label="Clave" htmlFor="password" requerido>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </Campo>

          {error && (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </p>
          )}

          <Button type="submit" className="w-full" disabled={enviando}>
            <LogIn className="h-4 w-4" />
            {enviando ? "Ingresando..." : "Ingresar"}
          </Button>
        </form>

        <p className="mt-4 text-center text-xs text-brand-300">
          Quilapilun, Colina - Region Metropolitana
        </p>
      </div>
    </div>
  );
}
