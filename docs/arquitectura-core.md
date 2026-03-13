# Arquitectura principal de Zenoytdl

Zenoytdl es una capa de alto nivel sobre `ytdl-sub`. No pretende reemplazar el motor subyacente, sino encapsularlo con contratos propios, validación, observabilidad, persistencia y orquestación.

## Principios rectores
1. Motor vs capa de producto.
2. Configuración declarativa.
3. Separación estricta de responsabilidades.
4. Validación temprana.
5. Overrides explícitos.
6. Persistencia como fuente de verdad.
7. Rendimiento como diseño.
8. UX visual diferida hasta estabilizar el core.

## Capas del sistema
### 1. Configuración

**Núcleo obligatorio (Hito 3):**
- `general.yaml`
- `profiles.yaml`
- `subscriptions.yaml`
- `ytdl-sub-conf.yaml`

**Bloques opcionales en archivos separados (decisión formal Hito 3):**
- `cache.yaml`
- `queues.yaml`
- `logging.yaml`

`general.yaml` queda reservado para contexto global. La integración con la capa inferior se centraliza en `ytdl-sub-conf.yaml` (Hito 9) para evitar acoplamientos dispersos.

### 2. Modelo interno
Representación normalizada del dominio y la configuración efectiva.

### 3. Validación y traducción
- parsing
- validación estructural
- validación semántica
- resolución de herencias
- traducción a la capa inferior

### 4. Procesamiento operativo
- colas
- caché
- deduplicación
- reintentos
- mantenimiento

### 5. Persistencia
SQLite con migraciones y eventos operativos.

### 6. Interfaz
CLI y API inicialmente; TUI/GUI después.

## Regla de gobierno documental
El `README.md` refleja exclusivamente estado verificado por hito. La arquitectura puede evolucionar durante un hito, pero su disponibilidad pública no se refleja en el README hasta cerrar el hito con pruebas y regresión acumulada.
