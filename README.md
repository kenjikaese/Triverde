# TRIVERDE — Sistema de gestión operativa

Repositorio de trabajo del equipo. Proyecto anual de **Ingeniería de Software** (UNAB) con
cliente real: **Triverde**, planta de procesamiento de material orgánico en Quilapilún, Colina.

El sistema gestiona la operación: recepción de camiones, inventario por material y estado,
lotes de compostaje, proyecciones, comercial y trazabilidad ambiental para SINADER.

---

## Cómo está organizado este repo

| Carpeta | Qué hay | Para qué |
|---|---|---|
| `docs/referencia/` | PDFs de cada componente de las entregas (casos de uso, contexto, requerimientos, modelo de datos, arquitectura, etc.) | **Material para trabajar.** Tienes todo aquí para tomar una tarea sin pedir nada. |
| `docs/trabajo-grupal/` | Archivos que editamos en conjunto y aún no están cerrados (draw.io, diagramas en curso, borradores) | Trabajo colaborativo en progreso. |
| `docs/entregables/` | Documentos finales ensamblados (Documento 0, Incrementos) | Se llena a medida que se cierra cada entrega. |
| `docs/guias/` | Guía de GitHub, "Cómo trabajamos + índice de tareas" y las specs de cada tarea | Cómo trabajar y qué hacer. Empieza por aquí. |
| `backend/` | Django + DRF | Código del servidor. |
| `frontend/` | React + Vite + Tailwind (PWA) | Código de la interfaz. |

> Los archivos fuente en Markdown, el pipeline de generación y el material privado del cliente
> **no viven aquí**: son taller de mantención del proyecto. Este repo tiene lo que el equipo
> necesita para trabajar, en formato consumible.

---

## Cómo trabajamos (resumen)

1. **No se trabaja sobre `main` directo.** `main` está protegido: los cambios entran por Pull Request.
2. Para cada tarea: crear una **rama** (`git switch -c mi-tarea`), hacer commits, `push`, abrir **PR**.
3. Un compañero revisa y se hace **merge** a `main`.
4. Antes de empezar el día: `git pull` para traer lo último.

> La **guía de GitHub para el equipo** (clonar, ramas, PR, merge) y **"Cómo trabajamos + índice de
> tareas"** están en `docs/guias/`. Empieza por esas dos. La **guía de levantamiento de entornos**
> (`docker compose up`, correr front y back) llegará junto con el scaffold de código.

---

## Equipo

Product Owner: **Kenji Kimura**. Equipo de desarrollo: 6 integrantes.
Cliente (Product Owner externo): **Javier**. Socio de operaciones: **José**.
Profesor: **Quinsacara**.
