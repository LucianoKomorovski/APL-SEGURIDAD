# Graph Report - APL-SEGURIDAD  (2026-10-01)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 337 nodes · 792 edges · 17 communities (9 shown, 8 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 99 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a885df0c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- views.py
- tests.py
- package.json
- App.jsx
- admin.py
- TotemApiTests
- simulador_hardware.py
- CredencialViewSet
- django_db
- ciclo_credencial.py
- apps.py

## God Nodes (most connected - your core abstractions)
1. `TotemApiTests` - 25 edges
2. `Credencial` - 21 edges
3. `ControladorAcceso` - 19 edges
4. `MotorReglasTests` - 19 edges
5. `Presencia` - 17 edges
6. `NivelAcceso` - 16 edges
7. `SujetoAcceso` - 16 edges
8. `Meta` - 15 edges
9. `CredencialViewSet` - 15 edges
10. `PageHead()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `CredencialInline` --uses--> `Credencial`  [INFERRED]
  backend/accesos/admin.py → backend/accesos/models.py
- `HorarioInline` --uses--> `HorarioPermitido`  [INFERRED]
  backend/accesos/admin.py → backend/accesos/models.py
- `TotemApiTests` --uses--> `AlertaSeguridad`  [INFERRED]
  backend/accesos/tests.py → backend/accesos/models.py
- `ResolucionInline` --uses--> `ResolucionAlerta`  [INFERRED]
  backend/accesos/admin.py → backend/accesos/models.py
- `ComponenteZonaSerializer` --uses--> `ComponenteZona`  [INFERRED]
  backend/accesos/serializers.py → backend/accesos/models.py

## Import Cycles
- None detected.

## Communities (17 total, 8 thin omitted)

### Community 0 - "views.py"
Cohesion: 0.07
Nodes (34): AlertaSeguridad, ResolucionAlerta, AlertaSeguridadSerializer, ComponenteZonaSerializer, ControladorAccesoSerializer, EdificioSerializer, HorarioPermitidoSerializer, Meta (+26 more)

### Community 1 - "tests.py"
Cohesion: 0.09
Nodes (25): Command, _edificio_con_ingreso(), _totem(), ComponenteZona, ControladorAcceso, Credencial, Edificio, HorarioPermitido (+17 more)

### Community 2 - "package.json"
Cohesion: 0.06
Nodes (34): dependencies, lucide-react, react, react-dom, devDependencies, eslint, @eslint/js, eslint-plugin-react-hooks (+26 more)

### Community 3 - "App.jsx"
Cohesion: 0.19
Nodes (23): API, armarArbolZonas(), DIAS, formatFecha(), App(), Login(), VISTAS, EdificioSelect() (+15 more)

### Community 4 - "admin.py"
Cohesion: 0.10
Nodes (18): AlertaAdmin, ClienteAdmin, ControladorAdmin, CredencialAdmin, CredencialInline, EdificioAdmin, HorarioAdmin, HorarioInline (+10 more)

### Community 6 - "simulador_hardware.py"
Cohesion: 0.13
Nodes (8): main(), demo_automatica(), emitir_evento(), heartbeat(), main(), menu_interactivo(), pasar_tarjeta(), post()

### Community 7 - "CredencialViewSet"
Cohesion: 0.19
Nodes (3): CredencialSerializer, CredencialViewSet, SujetoAccesoViewSet

### Community 8 - "django_db"
Cohesion: 0.17
Nodes (6): Migration, Migration, Migration, Migration, Migration, Migration

### Community 9 - "ciclo_credencial.py"
Cohesion: 0.35
Nodes (8): declarar_perdida(), entregar(), exigir_unica_activa(), _registrar(), reponer(), TransicionIlegal, vencer(), MovimientoCredencial

## Knowledge Gaps
- **31 isolated node(s):** `Migration`, `Migration`, `Migration`, `Migration`, `Migration` (+26 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 118 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `hora_dentro_de_ventana()` connect `tests.py` to `simulador_hardware.py`?**
  _High betweenness centrality (0.093) - this node is a cross-community bridge._
- **Why does `TotemApiTests` connect `TotemApiTests` to `views.py`, `tests.py`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._
- **Why does `Credencial` connect `tests.py` to `views.py`, `admin.py`, `TotemApiTests`, `CredencialViewSet`, `ciclo_credencial.py`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `TotemApiTests` (e.g. with `AlertaSeguridad` and `Credencial`) actually correct?**
  _`TotemApiTests` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `Credencial` (e.g. with `CredencialInline` and `exigir_unica_activa()`) actually correct?**
  _`Credencial` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `ControladorAcceso` (e.g. with `Command` and `_totem()`) actually correct?**
  _`ControladorAcceso` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `MotorReglasTests` (e.g. with `ComponenteZona` and `Credencial`) actually correct?**
  _`MotorReglasTests` has 7 INFERRED edges - model-reasoned connections that need verification._