# Módulo 11 - Mantenimiento de maquinaria y vehículos

## Alcance implementado

| Caso de uso | Implementación |
|---|---|
| CU-78 | Alta de maquinaria y habilitación de vehículos existentes como mantenibles. |
| CU-79 | Edición y baja lógica; se exige confirmación si hay mantención pendiente o el activo está en mantención. |
| CU-80 | Registro de lectura de horómetro, cálculo de horas transcurridas y rechazo de lecturas decrecientes. |
| CU-81 | Preventiva por fecha futura o por un umbral superior al horómetro vigente; confirmación de duplicados. |
| CU-82 | Correctiva con falla, reparación y costo; deja el activo operativo o fuera de servicio. |
| CU-83 | Historial por activo, con filtros por tipo y rango de fechas, más lecturas de uso. |
| CU-84 | Servicio de revisión con anticipación predeterminada de 7 días o 50 horas; crea o actualiza una sola alerta activa por mantención. |
| CU-85 | Panel consolidado de maquinaria y vehículos mantenibles con estado, horómetro, próxima mantención y alerta. |

## Decisiones de integración

- `RegistroUso` y `Mantencion` usan dos claves foráneas nulas con una restricción `CHECK` que exige exactamente un activo, según la decisión polimórfica del modelo de datos.
- `Vehiculo` incorpora `es_mantenible`, `datos_tecnicos` y `horometro`. Esto permite habilitar el objeto ya existente sin duplicarlo.
- `Mantencion` incorpora los campos de criterio, umbral, falla y reparación que los casos de uso requieren, aunque el resumen relacional solo enumera los campos base.
- `Alerta` vive en la app `mezcla`, como objeto transversal de M6. M11 no crea una entidad de alerta propia. La clave de deduplicación es genérica (`mantencion:<id>` o `mezcla:pila:<id>:<categoria>`) para que M6 reutilice el mismo servicio.
- La relación de `Alerta` con `Pila` se agrega cuando la app de M5 llegue a `main`; no se declara antes para evitar una dependencia de migración hacia un modelo que todavía no existe en esta rama.
- CU-84 se ejecuta al registrar horas y al consultar el estado de la flota. El servicio queda listo para invocarse también desde una tarea programada. Usa por defecto 7 días y 50 horas, ambos editables como parámetros globales por el administrador.
- La interfaz permite filtrar el historial por tipo y fechas, y reprogramar una preventiva pendiente; al reprogramarla, la alerta anterior se resuelve y el nuevo criterio se vuelve a evaluar.
- Altas, bajas, edición de maquinaria, registros de horas, mantenciones y resolución de alertas dejan rastro en `BitacoraAuditoria`.

## Permisos

- Administrador: alta, edición y baja de activos; preventivas; ejecución/reprogramación; estado de flota.
- Operador: consulta de activos e historial; registro de horas y correctivas; consulta/resolución de alertas.
- Transportista: sin acceso al módulo.

## Verificación

Ejecutar desde `backend/`:

```bash
python manage.py makemigrations --check --dry-run
python manage.py test
```

Ejecutar desde `frontend/`:

```bash
npm run typecheck
npm run build
```
