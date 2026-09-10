# Módulo 11 - Secuencias de diseño

Los diagramas siguen la separación Vista / Controlador / Persistencia definida para Triverde.
Las fuentes entregables están versionadas individualmente como `.puml` en
`docs/trabajo-grupal/diagramas/secuencias/`, junto con sus versiones renderizadas en PNG y SVG.

## CU-78 - Registrando una máquina o vehículo mantenible

### Flujo normal

```mermaid
sequenceDiagram
    actor A as Administrador
    participant V as V_FormularioMaquinaria
    participant C as C_Maquinaria
    participant DB as ORM / PostgreSQL
    A->>V: Ingresa activo y datos técnicos
    V->>C: POST /maquinaria/ o PATCH /vehiculos/{id}/
    C->>C: Valida datos y horómetro inicial
    C->>DB: Guarda activo operativo y activo
    DB-->>C: Activo creado/actualizado
    C-->>V: 201/200 con activo
    V-->>A: Confirma registro
```

### Excepción

```mermaid
sequenceDiagram
    actor A as Administrador
    participant V as V_FormularioMaquinaria
    participant C as C_Maquinaria
    A->>V: Omite nombre/tipo o ingresa horómetro negativo
    V->>C: Envía formulario
    C->>C: Detecta dato inválido
    C-->>V: 400 con campos observados
    V-->>A: Solicita corregir los datos
```

## CU-79 - Editando o dando de baja una máquina

### Flujo normal

```mermaid
sequenceDiagram
    actor A as Administrador
    participant V as V_FormularioMaquinaria
    participant C as C_Maquinaria
    participant DB as ORM / PostgreSQL
    A->>V: Edita datos o solicita baja
    V->>C: PATCH o DELETE /maquinaria/{id}/
    C->>DB: Actualiza datos o estado=inactivo
    C->>DB: Registra auditoría
    C-->>V: Operación exitosa
    V-->>A: Confirma sin borrar historial
```

### Excepción

```mermaid
sequenceDiagram
    actor A as Administrador
    participant V as V_FormularioMaquinaria
    participant C as C_Maquinaria
    participant DB as ORM / PostgreSQL
    A->>V: Solicita baja
    V->>C: DELETE /maquinaria/{id}/
    C->>DB: Busca mantenciones pendientes
    DB-->>C: Existe pendiente o está en mantención
    C-->>V: 409 requiere confirmación
    V-->>A: Advierte la situación
```

## CU-80 - Registrando las horas de uso

### Flujo normal

```mermaid
sequenceDiagram
    actor O as Operador
    participant V as V_RegistroUso
    participant C as C_Maquinaria
    participant DB as ORM / PostgreSQL
    O->>V: Ingresa lectura actual
    V->>C: POST /registros-uso/
    C->>DB: Bloquea y consulta activo
    C->>C: Calcula horas transcurridas
    C->>DB: Crea RegistroUso y actualiza horómetro
    C-->>V: 201 con lectura
    V-->>O: Confirma registro
```

### Excepción

```mermaid
sequenceDiagram
    actor O as Operador
    participant V as V_RegistroUso
    participant C as C_Maquinaria
    participant DB as ORM / PostgreSQL
    O->>V: Ingresa lectura menor
    V->>C: POST /registros-uso/
    C->>DB: Consulta horómetro vigente
    DB-->>C: Lectura anterior mayor
    C-->>V: 400 el horómetro no retrocede
    V-->>O: Mantiene formulario para corregir
```

## CU-81 - Programando una mantención preventiva

### Flujo normal

```mermaid
sequenceDiagram
    actor A as Administrador
    participant V as V_ProgramarMantencion
    participant C as C_Mantenimiento
    participant DB as ORM / PostgreSQL
    A->>V: Define activo, criterio y tarea
    V->>C: POST /mantenciones/
    C->>C: Valida fecha futura o umbral mayor
    C->>DB: Crea Mantencion preventiva/programada
    C-->>V: 201 con programación
    V-->>A: Confirma programación
```

### Excepción

```mermaid
sequenceDiagram
    actor A as Administrador
    participant V as V_ProgramarMantencion
    participant C as C_Mantenimiento
    participant DB as ORM / PostgreSQL
    A->>V: Programa con criterio repetido
    V->>C: POST /mantenciones/
    C->>DB: Busca programación equivalente
    DB-->>C: Ya existe una pendiente
    C-->>V: 400 requiere confirmación
    V-->>A: Solicita confirmación explícita
```

## CU-82 - Registrando una mantención correctiva

### Flujo normal

```mermaid
sequenceDiagram
    actor O as Operador
    participant V as V_ProgramarMantencion
    participant C as C_Mantenimiento
    participant DB as ORM / PostgreSQL
    O->>V: Ingresa falla, reparación y costo
    V->>C: POST /mantenciones/ tipo correctiva
    C->>DB: Crea Mantencion realizada
    C->>DB: Actualiza activo a operativa
    C->>DB: Registra auditoría
    C-->>V: 201 con mantención
    V-->>O: Confirma reparación
```

### Excepción

```mermaid
sequenceDiagram
    actor O as Operador
    participant V as V_ProgramarMantencion
    participant C as C_Mantenimiento
    O->>V: Omite falla o ingresa costo negativo
    V->>C: POST /mantenciones/
    C->>C: Valida campos de correctiva
    C-->>V: 400 con detalle
    V-->>O: Solicita corregir el registro
```

## CU-83 - Consultando el historial

### Flujo normal

```mermaid
sequenceDiagram
    actor U as Administrador u Operador
    participant V as V_HistorialMantenimiento
    participant C as C_Mantenimiento
    participant DB as ORM / PostgreSQL
    U->>V: Selecciona activo y filtros
    V->>C: GET /mantenciones/ y /registros-uso/
    C->>DB: Consulta por activo, tipo y fechas
    DB-->>C: Mantenciones y lecturas ordenadas
    C-->>V: 200 con historial
    V-->>U: Presenta historial unificado
```

### Excepción

```mermaid
sequenceDiagram
    actor U as Administrador u Operador
    participant V as V_HistorialMantenimiento
    participant C as C_Mantenimiento
    participant DB as ORM / PostgreSQL
    U->>V: Aplica un filtro sin coincidencias
    V->>C: GET con filtros
    C->>DB: Consulta historial
    DB-->>C: Colección vacía
    C-->>V: 200 []
    V-->>U: Informa que no hay registros
```

## CU-84 - Generando la alerta de mantención

### Flujo normal

```mermaid
sequenceDiagram
    actor S as Sistema
    participant C as C_Mantenimiento
    participant DB as ORM / PostgreSQL
    S->>C: Dispara revisión periódica
    C->>DB: Lee mantenciones programadas
    DB-->>C: Criterios y activos vigentes
    C->>C: Compara fecha/horas con anticipación
    C->>DB: Crea o actualiza Alerta de mantención
    DB-->>C: Alerta activa única
```

### Excepción

```mermaid
sequenceDiagram
    actor S as Sistema
    participant C as C_Mantenimiento
    participant DB as ORM / PostgreSQL
    S->>C: Repite revisión
    C->>DB: Busca alerta activa por mantención
    DB-->>C: Alerta ya existente
    C->>DB: Actualiza nivel/mensaje sin duplicar
    DB-->>C: Una sola alerta activa
```

## CU-85 - Consultando el estado de la flota

### Flujo normal

```mermaid
sequenceDiagram
    actor A as Administrador
    participant V as V_EstadoFlota
    participant C as C_Maquinaria
    participant DB as ORM / PostgreSQL
    A->>V: Abre estado de la flota
    V->>C: GET /maquinaria/estado-flota/
    C->>C: Ejecuta revisión de alertas
    C->>DB: Consulta activos y próximas mantenciones
    DB-->>C: Estado consolidado
    C-->>V: 200 con maquinaria y vehículos
    V-->>A: Presenta panel y filtros
```

### Excepción

```mermaid
sequenceDiagram
    actor A as Administrador
    participant V as V_EstadoFlota
    participant C as C_Maquinaria
    participant DB as ORM / PostgreSQL
    A->>V: Abre estado de la flota
    V->>C: GET /maquinaria/estado-flota/
    C->>DB: Consulta activos mantenibles
    DB-->>C: Colección vacía
    C-->>V: 200 []
    V-->>A: Invita a registrar el primer activo
```
