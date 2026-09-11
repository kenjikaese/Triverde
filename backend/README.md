# Backend Triverde — Incremento 1

Django 4.2 + DRF + PostgreSQL, empaquetado en Docker Compose. Cubre el **núcleo de datos
del Incremento 1**: los 15 objetos de dominio de los Módulos 1–4, operables desde el panel
de administración de Django.

## Levantar el sistema

Requiere Docker Desktop corriendo.

```bash
cd backend
docker compose up -d --build
```

Esto levanta PostgreSQL, aplica las migraciones, siembra los datos mínimos y arranca el
servidor. Cuando termine:

- Admin: <http://localhost:8000/admin/>  ·  usuario `admin` / clave `admin` (**cambiar**).
- API DRF: <http://localhost:8000/api/v1/> (lista todos los endpoints; requiere token).

Para detenerlo: `docker compose down` (agrega `-v` para borrar también la base de datos).

### Correr sin Docker (opcional)

Con un entorno virtual y `pip install -r requirements.txt`, copiar `.env.example` a `.env`
(sin `DATABASE_URL` usa SQLite) y correr:

```bash
python manage.py migrate && python manage.py seed_inicial && python manage.py runserver
```

## Estructura

| App | Módulo | Modelos |
|-----|--------|---------|
| `acceso` | 1 — Acceso y auditoría | `Rol`, `Usuario` (custom, extiende `AbstractUser`), `BitacoraAuditoria` |
| `configuracion` | 2 — Configuración | `ParametroConversion`, `TarifaRecepcion`, `HistorialCambioParametro` |
| `mantenedores` | 3 — Mantenedores | `Cliente`, `Transportista`, `Vehiculo`, `Material`, `Producto` |
| `recepcion` | 4 — Recepción | `Recepcion`, `DetalleRecepcion`, `FotoRecepcion`, `Multa` |
| `mezcla` | 6 — Alertas compartidas | `Alerta` y servicio genérico de activación/deduplicación usado por M11 y preparado para M6 |
| `mantenimiento` | 11 — Mantenimiento | `Maquinaria`, `RegistroUso`, `Mantencion` |
| `common` | — | `SincronizableModel` (mixin de la capa offline) |

Los modelos son traducción directa de **`docs/11 - Modelo de Datos.md` §11.6** (nivel físico).
Decisiones de diseño aplicadas (docs/11 §11.7):

- **Capa offline** — `Recepcion` y sus partes heredan `id_local` (UUID) + `estado_sincronizacion`
  de `SincronizableModel`; el `id_local` hace idempotente la sincronización (CU-33).
- **Baja lógica** en mantenedores (`estado = inactivo`) → FK con `PROTECT`/`SET_NULL`, nunca `CASCADE`.
- **`CASCADE` sólo dentro del agregado** `Recepcion` (detalles, fotos, multas).
- **Peso derivado persistido** en `DetalleRecepcion` (hecho histórico, no recomputable).

## API

La API expone los 15 objetos del Incremento 1 bajo el prefijo `/api/v1/`. Sin token responde
`401`; con token, `200`. Los endpoints que no se listan (detalles, fotos y multas de recepción)
se manejan anidados dentro de `/recepciones/` y del endpoint de sincronización.

| Endpoint | Métodos | Quién | Notas |
|---|---|---|---|
| `/api/v1/auth/login/` | POST | público | `{username, password}` → `{token, usuario}`. Rechaza cuentas inactivas. |
| `/api/v1/auth/logout/` | POST | autenticado | Invalida el token del request. |
| `/api/v1/auth/perfil/` | GET | autenticado | Devuelve el usuario actual. |
| `/api/v1/usuarios/` | CRUD | Administrador | `DELETE` = baja lógica (`estado=inactivo`). |
| `/api/v1/roles/` | GET | Administrador | Catálogo de roles (solo lectura). |
| `/api/v1/auditoria/` | GET | Administrador | Bitácora de auditoría (solo lectura). |
| `/api/v1/parametros/` | CRUD | Admin escribe / Operador lee | Al cambiar el valor se registra el historial y la auditoría. |
| `/api/v1/tarifas/` | CRUD | Admin escribe / Operador lee | |
| `/api/v1/historial-parametros/` | GET | Admin/Operador | Historial de cambios (solo lectura). |
| `/api/v1/clientes/` | CRUD | Admin escribe / Operador lee | `DELETE` = baja lógica. |
| `/api/v1/transportistas/` | CRUD | Admin escribe / Operador lee | `DELETE` = baja lógica. |
| `/api/v1/vehiculos/` | CRUD | Admin escribe / Operador lee | `DELETE` = baja lógica. |
| `/api/v1/materiales/` | CRUD | Admin escribe / Operador lee | `DELETE` = baja lógica. |
| `/api/v1/productos/` | CRUD | Admin escribe / Operador lee | `DELETE` = baja lógica. |
| `/api/v1/recepciones/` | CRUD | Admin/Operador; Transportista solo crea y ve las suyas (CU-28) | Acepta `detalles`, `fotos` y `multas` anidados. Sin `DELETE` físico. |
| `/api/v1/sincronizacion/` | POST | Admin/Operador | Lote de operaciones offline, idempotente por `id_local` (CU-33). |
| `/api/v1/maquinaria/` | CRUD | Admin escribe / Operador lee | Activos no vehiculares; `DELETE` aplica baja lógica. |
| `/api/v1/maquinaria/estado-flota/` | GET | Administrador | Consolida maquinaria y vehículos mantenibles; revisa alertas M11. |
| `/api/v1/registros-uso/` | GET, POST | Admin/Operador | Lectura monótona de horómetro y horas transcurridas. |
| `/api/v1/mantenciones/` | GET, POST, PATCH | Admin/Operador | Admin programa/reprograma preventivas; Operador registra correctivas. |
| `/api/v1/mantenciones/{id}/realizar/` | POST | Administrador | Ejecuta una preventiva y resuelve su alerta. |
| `/api/v1/alertas/` | GET | Admin/Operador | Bandeja transversal; admite filtros `estado` y `origen`. |
| `/api/v1/alertas/{id}/resolver/` | POST | Admin/Operador | Resuelve una alerta conservando su historial. |

### Obtener un token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'
```

Respuesta (ejemplo):

```json
{"token": "abc123...", "usuario": {"id": 1, "username": "admin",
 "nombre_completo": "Administrador Triverde", "rol": 1, "rol_nombre": "Administrador"}}
```

Usar el token en las demás peticiones: `Authorization: Token <token>`. La PWA guarda el token
para operar offline y reautentica al reconectar.

### Sincronización (CU-33)

`POST /api/v1/sincronizacion/` recibe el lote acumulado en la cola local (IndexedDB) mientras el
dispositivo estaba sin señal:

```json
{"operaciones": [
  {"id_local": "uuid-de-la-recepcion", "tipo": "recepcion",
   "capturado_en": "2026-08-20T14:03:00-04:00",
   "datos": {"cliente": 3, "transportista": 5, "vehiculo": 2, "conductor": "Juan Perez",
             "fecha": "2026-08-20", "hora": "14:03", "estado": "pendiente de inspeccion",
             "detalles": [{"id_local": "uuid-det-1", "material": 1, "volumen_m3": "20.00",
                           "destino_sugerido": "a pila"}]}}
]}
```

Se aplica en orden de `capturado_en`, cada operación en su propia transacción, con
crear-si-no-existe por `id_local` (reenviar el lote dos veces da el mismo resultado que una).
`peso_derivado_kg` y `chip_derivado_m3` se calculan en el servidor a partir de la densidad y el
factor del material; si el material no tiene densidad configurada, la operación se rechaza con el
motivo (no se inventa una densidad). La respuesta reporta por operación: `sincronizada`,
`en conflicto` o `rechazada` (con motivo); el dispositivo vacía de su cola lo sincronizado y
conserva el resto.

**Fotos (CU-27) en el sync:** viajan embebidas como **base64** dentro de cada operación
(`"fotos": [{"id_local": "...", "archivo": "data:image/png;base64,...."}]`). La cola local en
IndexedDB guarda la imagen en base64 y la envía en el mismo lote; el servidor la decodifica,
valida que sea una imagen real (Pillow) y la persiste. Una foto base64 corrupta rechaza la
operación completa (agregado atómico). El mismo campo `archivo` acepta un archivo por multipart
en el CRUD online contra `/recepciones/`.

## Limitaciones conocidas

**(menor, Inc 1):** el `PATCH` de una recepción reemplaza sus partes
(`detalles`/`fotos`/`multas`) borrándolas y recreándolas, por lo que el `id_local` de las partes
no es estable entre ediciones. Aceptable para el Inc 1; si se necesita edición fina de partes,
migrar a un upsert por `id_local`.

## Pruebas

Con el sistema levantado:

```bash
docker compose exec web python manage.py test
```

Los tests cubren: la derivación de `peso_derivado_kg`/`chip_derivado_m3`, la **idempotencia del
sync** (el mismo lote dos veces crea una sola recepción), el rechazo y continuación de
operaciones inválidas, el conflicto (CU-33), los permisos por rol y la baja lógica.

## Notas

- Los valores del seed marcados como provisorios (factores de reducción, tarifas de 10 y 40 m³) esperan
  confirmación del cliente.
