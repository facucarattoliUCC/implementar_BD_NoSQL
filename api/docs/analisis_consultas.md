# Análisis de rendimiento de consultas

## 1. Computadoras más vendidas

`report_repository.py` → `top_computers(self, limit)`

| Métrica | Valor | Descripción |
|---|---|---|
| Documentos analizados | 250 | Todos los documentos de la colección `sales` |
| Documentos agrupados (`$group` ≡ `GROUP BY`) | 40 | Cantidad de `id_computer` distintos encontrados en las ventas |
| Documentos devueltos | 5 | Cantidad fijada por `$limit` |
| Tiempo de ejecución | 48 ms | |
| Índice utilizado | `id_computer_1` | Lo usa el `$lookup` (≡ `JOIN`) para buscar cada computadora en `computers` |
| Etapas | `$group` → `$sort` → `$limit` → `$lookup` → `$project` | |

## 2. Cantidad de computadoras que usan un componente

`computer_repository.py` → `count_using_component(self, id_component)`

| Métrica | Valor | Descripción |
|---|---|---|
| Documentos analizados | 40 | Todos los documentos de la colección `computers` |
| Documentos devueltos | 5 | Computadoras que usan el componente buscado |
| Tiempo de ejecución | 3 ms | |
| Filtro aplicado | `{ id_component: "cmp-003" }` | |
| Índice utilizado | Ninguno | No existe un índice sobre `id_component` |
| Etapa | `COLLSCAN` | Recorre la colección `computers` completa |

## 3. Búsqueda de ventas por cliente

`sale_repository.py` → `search(self, id_client=None, id_seller=None, id_computer=None)`

| Métrica | Valor | Descripción |
|---|---|---|
| Documentos analizados | 250 | Todos los documentos de la colección `sales` |
| Documentos devueltos | 4 | Ventas del cliente `cli-001` |
| Tiempo de ejecución | 716 µs | |
| Filtro aplicado | `{ "Client.id_client": "cli-001" }` | |
| Índice utilizado | Ninguno | No existe un índice sobre `Client.id_client` |
| Etapa | `COLLSCAN` | Recorre la colección `sales` completa para devolver solo 4 documentos |
