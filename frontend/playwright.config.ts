import { defineConfig, devices } from "@playwright/test";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { existsSync } from "node:fs";

const aqui = dirname(fileURLToPath(import.meta.url));
const backend = join(aqui, "..", "backend");

// Interprete del backend: el venv local si existe, si no el del sistema (en
// Docker o en un equipo donde Python este en el PATH).
const venvWindows = join(backend, ".venv", "Scripts", "python.exe");
const venvUnix = join(backend, ".venv", "bin", "python");
const python = existsSync(venvWindows)
  ? venvWindows
  : existsSync(venvUnix)
    ? venvUnix
    : "python";

// Las pruebas e2e corren contra una base propia (db.e2e.sqlite3), nunca contra
// la de desarrollo, y con las trazas de caso de uso encendidas.
const entornoBackend = {
  DATABASE_URL: "sqlite:///db.e2e.sqlite3",
  TRIVERDE_TRAZAS: "1",
  DJANGO_DEBUG: "true",
  DJANGO_SECRET_KEY: "clave-solo-para-pruebas-e2e",
};

export default defineConfig({
  testDir: "./e2e",
  // Un worker: los escenarios comparten la base y el archivo de trazas, y el
  // orden importa para las aserciones sobre totales y saldos.
  workers: 1,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  timeout: 45_000,
  expect: { timeout: 10_000 },
  reporter: [
    ["list"],
    ["html", { outputFolder: "e2e-reporte", open: "never" }],
  ],
  use: {
    baseURL: "http://localhost:5173",
    trace: "retain-on-failure",
    video: "off",
    locale: "es-CL",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: [
    {
      // Migra y siembra antes de levantar: cada corrida parte del mismo estado.
      command: [
        `"${python}" manage.py migrate --noinput`,
        `"${python}" manage.py seed_e2e`,
        `"${python}" manage.py runserver 8000 --noreload`,
      ].join(" && "),
      cwd: backend,
      env: entornoBackend,
      url: "http://localhost:8000/api/v1/",
      reuseExistingServer: false,
      timeout: 120_000,
      stdout: "pipe",
      stderr: "pipe",
    },
    {
      command: "npm run dev",
      cwd: aqui,
      url: "http://localhost:5173",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
