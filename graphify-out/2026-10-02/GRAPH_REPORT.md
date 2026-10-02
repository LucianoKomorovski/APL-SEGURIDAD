# Graph Report - APL-SEGURIDAD  (2026-10-02)

## Corpus Check
- 58 files · ~33,980 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: (none) 3, .css 2, .mdc 1)

## Summary
- 520 nodes · 1260 edges · 24 communities (12 shown, 12 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 169 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a885df0c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- views.py
- models.py
- package.json
- App.jsx
- admin.py
- TotemApiTests
- simulador_hardware.py
- Texto del informe
- django_db
- React + Vite
- apps.py
- AGENTS.md
- RETIRADA_SELECTIVA.md
- ApiSessionAuthentication
- incidentes.py
- .get_queryset
- IncidentesApiTests
- HistorialAsignacionSerializer

## God Nodes (most connected - your core abstractions)
1. `TotemApiTests` - 36 edges
2. `ControladorAcceso` - 25 edges
3. `IncidentesApiTests` - 25 edges
4. `IncidenteTecnico` - 24 edges
5. `CuentaSistema` - 22 edges
6. `Texto del informe` - 22 edges
7. `Meta` - 21 edges
8. `Credencial` - 21 edges
9. `OperadorSistema` - 19 edges
10. `MotorReglasTests` - 19 edges

## Surprising Connections (you probably didn't know these)
- `CredencialInline` --uses--> `Credencial`  [INFERRED]
  backend/accesos/admin.py → backend/accesos/models.py
- `HorarioInline` --uses--> `HorarioPermitido`  [INFERRED]
  backend/accesos/admin.py → backend/accesos/models.py
- `CredencialForm` --uses--> `Credencial`  [INFERRED]
  backend/accesos/admin.py → backend/accesos/models.py
- `ResolucionInline` --uses--> `ResolucionAlerta`  [INFERRED]
  backend/accesos/admin.py → backend/accesos/models.py
- `_operador()` --uses--> `OperadorSistema`  [INFERRED]
  backend/accesos/incidentes.py → backend/accesos/models.py

## Import Cycles
- None detected.

## Communities (24 total, 12 thin omitted)

### Community 0 - "views.py"
Cohesion: 0.06
Nodes (37): ResolucionAlerta, AlertaSeguridadSerializer, CambioEstadoIncidenteSerializer, CambioEstadoOrdenSerializer, ComponenteZonaSerializer, ControladorAccesoSerializer, CredencialSerializer, EdificioSerializer (+29 more)

### Community 1 - "models.py"
Cohesion: 0.05
Nodes (32): Command, Command, _edificio_con_ingreso(), _totem(), AlertaSeguridad, ComponenteZona, ControladorAcceso, Credencial (+24 more)

### Community 2 - "package.json"
Cohesion: 0.06
Nodes (34): dependencies, lucide-react, react, react-dom, devDependencies, eslint, @eslint/js, eslint-plugin-react-hooks (+26 more)

### Community 3 - "App.jsx"
Cohesion: 0.14
Nodes (35): api, armarArbolZonas(), cookie(), DIAS, formatFecha(), onUnauthorized(), parseJson(), request() (+27 more)

### Community 4 - "admin.py"
Cohesion: 0.08
Nodes (22): AlertaAdmin, ArchivoHistoricoAdmin, ClienteAdmin, ControladorAdmin, CredencialAdmin, CredencialInline, CuentaSistemaAdmin, EdificioAdmin (+14 more)

### Community 5 - "TotemApiTests"
Cohesion: 0.08
Nodes (3): CredencialForm, Meta, TotemApiTests

### Community 6 - "simulador_hardware.py"
Cohesion: 0.13
Nodes (8): main(), demo_automatica(), emitir_evento(), heartbeat(), main(), menu_interactivo(), pasar_tarjeta(), post()

### Community 7 - "Texto del informe"
Cohesion: 0.06
Nodes (35): 1.10 Restricciones, 1.1 Nombre, 1.2 Siglas, 1.3 Descripción, 1.4 Objetivos, 1.5 Alcance, 1.6 Interesados, 1.7 Hitos (+27 more)

### Community 8 - "django_db"
Cohesion: 0.11
Nodes (9): Migration, Migration, Migration, Migration, Migration, Migration, Migration, Migration (+1 more)

### Community 9 - "React + Vite"
Cohesion: 0.50
Nodes (3): Expanding the ESLint configuration, React Compiler, React + Vite

### Community 20 - "incidentes.py"
Cohesion: 0.11
Nodes (28): asignar_intervencion(), _cambiar_incidente(), _cambiar_orden(), cancelar_orden(), cerrar_incidente(), descartar_incidente(), evaluar_incidente(), informar_orden() (+20 more)

### Community 21 - ".get_queryset"
Cohesion: 0.17
Nodes (5): cuenta_activa(), EsTecnico, EsUsuarioSGCA, _id_query(), _inicio_del_dia_local()

## Knowledge Gaps
- **73 isolated node(s):** `Meta`, `Migration`, `Migration`, `Migration`, `Migration` (+68 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 197 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TotemApiTests` connect `TotemApiTests` to `models.py`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Why does `hora_dentro_de_ventana()` connect `models.py` to `simulador_hardware.py`?**
  _High betweenness centrality (0.059) - this node is a cross-community bridge._
- **Why does `IncidentesApiTests` connect `IncidentesApiTests` to `models.py`, `incidentes.py`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `TotemApiTests` (e.g. with `CredencialForm` and `AlertaSeguridad`) actually correct?**
  _`TotemApiTests` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `ControladorAcceso` (e.g. with `Command` and `_totem()`) actually correct?**
  _`ControladorAcceso` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `IncidentesApiTests` (e.g. with `AlertaSeguridad` and `ComponenteZona`) actually correct?**
  _`IncidentesApiTests` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `IncidenteTecnico` (e.g. with `asignar_intervencion()` and `cancelar_orden()`) actually correct?**
  _`IncidenteTecnico` has 15 INFERRED edges - model-reasoned connections that need verification._