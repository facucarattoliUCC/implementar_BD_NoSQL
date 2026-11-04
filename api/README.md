# TechCore API

API REST para la gestión de un e-commerce de computadoras: catálogo de componentes, computadoras armadas, ventas, stock y reportes.

**Stack:** Python · Flask · MongoDB (PyMongo) · pytest

---

## 1. Puesta en marcha

```bash
pip install -r requirements.txt
python seed.py      # borra y carga 350 documentos de ejemplo
python app.py       # levanta la API en http://localhost:5000
pytest -v           # corre los tests (no necesita MongoDB)
```

MongoDB debe estar corriendo en `localhost:27017`. Para usar otra instancia o base:

```bash
MONGO_URI="mongodb://usuario:clave@host:27017" DB_NAME="techcore" python app.py
```

Prueba rápida: abrir `http://localhost:5000/` en el navegador. La página de inicio muestra si la base está conectada, cuántos documentos tiene cada colección y la lista de endpoints; los `GET` sin parámetros se pueden abrir con un clic.

---

## 2. Modelo de datos

La base `techcore` tiene **3 colecciones**. Clientes y vendedores no tienen colección propia: se guardan dentro de cada venta.

```mermaid
erDiagram
    COMPUTER }o--|{ COMPONENT : "referencia (id_component[])"
    SALE }o--|| COMPUTER : "referencia (id_computer)"
    SALE ||--|{ CLIENT : "incrustado"
    SALE ||--|{ SELLER : "incrustado"
```

| Colección | Qué guarda | Relación |
|---|---|---|
| `components` | Piezas sueltas (CPU, GPU, RAM, SSD…) con precio y stock | — |
| `computers` | Equipos armados | **Referencia** a sus componentes por `id_component` (lista de IDs) |
| `sales` | Ventas | **Referencia** a la computadora vendida; **incrusta** `Client` y `Seller` |

**¿Por qué referenciar o incrustar?**
- Los componentes se **referencian** porque tienen vida propia: se venden, cambian de stock y una misma pieza la usan varias computadoras.
- Cliente y vendedor se **incrustan** porque son datos de la venta en ese momento: siempre se leen juntos y no se consultan por separado.

Ejemplo de una venta:

```json
{
  "id_sale": "sale-001",
  "id_computer": "pc-001",
  "quantity": 1,
  "amount": 835.0,
  "date": "2026-10-20T15:00:00+00:00",
  "Client": [{ "id_client": "cli-001", "full_name_client": "Laura Gómez", "address": "...", "tel_contact": 3514567890, "email": "laura@mail.com" }],
  "Seller": [{ "id_seller": "sel-001", "full_name_seller": "Ana Torres", "commission": 0.05 }]
}
```

### IDs

Usamos IDs propios legibles en lugar del `_id` de Mongo, que nunca se expone en las respuestas. El formato es `<prefijo>-<alfanumérico>`:

| Entidad | Prefijo | Ejemplo |
|---|---|---|
| Component | `cmp` | `cmp-001` |
| Computer | `pc` | `pc-001` |
| Sale | `sale` | `sale-001` |
| Client | `cli` | `cli-001` |
| Seller | `sel` | `sel-001` |

Si en un POST no se envía ID, la API genera uno (`cmp-3fa2b1c9`).

---

## 3. Arquitectura

El proyecto está separado en **capas**, y cada una tiene una única responsabilidad:

```
         Pedido HTTP
              │
              ▼
┌───────────────────────────┐
│  routes/                  │  Recibe el pedido, valida, aplica reglas de negocio
│  (Flask Blueprints)       │  y decide el código de estado (200, 400, 404...)
└─────────────┬─────────────┘
              │ usa
              ▼
┌───────────────────────────┐
│  validators.py            │  Valida formato de IDs, cuerpos JSON y parámetros.
│                           │  Si algo está mal lanza ApiError → 400
└───────────────────────────┘
              │
              ▼
┌───────────────────────────┐
│  repositories/            │  Único lugar donde se usa PyMongo.
│  (patrón Repositorio)     │  Expone métodos como find_by_id, insert, update...
└─────────────┬─────────────┘
              ▼
           MongoDB
```

**Regla principal:** las rutas **nunca** acceden a una colección de Mongo directamente; siempre pasan por un repositorio. Así, si cambia la forma de consultar la base, se toca un solo lugar.

### Estructura de carpetas

```
techcore-api/
├── app.py                 # Punto de entrada: create_app() arma la aplicación
├── validators.py          # Validaciones y la excepción ApiError
├── seed.py                # Datos de ejemplo
├── templates/
│   └── index.html         # Página de inicio (/)
├── analysis/
│   └── reports_analysis.ipynb   # Análisis con gráficos de los reportes
├── requirements.txt
├── repositories/
│   ├── base_repository.py       # CRUD genérico que heredan todos
│   ├── component_repository.py  # + búsqueda con filtros, stock bajo
│   ├── computer_repository.py   # + $lookup de componentes, manejo atómico de stock
│   ├── sale_repository.py       # + búsqueda por cliente, vendedor o computadora
│   └── report_repository.py     # Reportes (aggregation) que cruzan las 3 colecciones; solo lectura
├── routes/
│   ├── __init__.py        # repos(): acceso a los repositorios desde cualquier ruta
│   ├── home.py            # / : estado de la base y lista de endpoints (se arma sola desde las rutas)
│   ├── components.py      # /components
│   ├── computers.py       # /computers
│   ├── sales.py           # /sales
│   └── reports.py         # /stock/low y /reports/*
└── tests/
    └── test_api.py
```

### Recorrido de un pedido: `PATCH /components/cmp-003`

1. Flask dirige el pedido a `update_component()` en `routes/components.py`.
2. `_get_or_404()` valida el formato del ID. Si es inválido responde **400**; si no existe, **404**.
3. `validate_body(..., partial=True)` revisa que los campos enviados existan y tengan el tipo correcto. Si algo falla, **400**.
4. Se llama a `repos().components.update(id, cambios)`. El repositorio ejecuta el `find_one_and_update` en Mongo.
5. La ruta devuelve el documento actualizado con **200**.

Los errores no se manejan con `try/except` en cada ruta. Se lanza `ApiError(mensaje, código)` y los manejadores registrados en `app.py` lo convierten en una respuesta JSON.

---

## 4. Endpoints

`/components`, `/computers` y `/sales` siguen el mismo patrón:

| Método | Ruta | Qué hace | Éxito |
|---|---|---|---|
| GET | `/<recurso>` | Lista, con filtros opcionales | 200 |
| GET | `/<recurso>/<id>` | Obtiene uno | 200 |
| POST | `/<recurso>` | Crea | 201 |
| PUT | `/<recurso>/<id>` | Reemplaza el documento completo (todos los campos obligatorios) | 200 |
| PATCH | `/<recurso>/<id>` | Modifica solo los campos enviados | 200 |
| DELETE | `/<recurso>/<id>` | Elimina | 200 |

**Filtros de listado**
- `/components` y `/computers`: `?name=ryzen`, `?min_price=100`, `?max_price=500`, `?in_stock=true`. En computers, `?expand=true` incluye el detalle de los componentes.
- `/sales`: `?client=cli-001`, `?seller=sel-001`, `?computer=pc-001`

**Otros endpoints**

| Método | Ruta | Qué hace |
|---|---|---|
| POST | `/computers/build` | Cotiza una PC a medida: recibe `{"id_component": [...]}` y devuelve el precio total y si hay stock. No guarda nada. |
| GET | `/stock/low?threshold=5` | Componentes y computadoras con stock bajo |

### Reportes

Son de solo lectura y se calculan con *aggregation pipelines* en `report_repository.py`. Todos devuelven una lista de filas planas (o un objeto, en `summary`), así que se pueden cargar directo en pandas:

```python
import pandas as pd, requests
df = pd.DataFrame(requests.get("http://localhost:5000/reports/sales-by-month").json())
```

| Ruta | Qué devuelve (una fila por…) | Columnas |
|---|---|---|
| `/reports/summary` | Indicadores generales (un objeto) | `sales_count`, `units_sold`, `total_revenue`, `average_ticket`, `first_sale`, `last_sale`, `clients_count`, `sellers_count`, `computers_count`, `components_count` |
| `/reports/sales-by-month` | Mes | `month`, `sales_count`, `units_sold`, `revenue` |
| `/reports/sellers` | Vendedor | `id_seller`, `full_name_seller`, `commission_rate`, `sales_count`, `total_amount`, `commission_earned` |
| `/reports/top-computers?limit=5` | Computadora más vendida | `id_computer`, `name_computer`, `units_sold`, `total_amount` |
| `/reports/top-clients?limit=10` | Cliente que más gastó | `id_client`, `full_name_client`, `purchases`, `units_bought`, `total_spent`, `average_ticket` |
| `/reports/sales-by-line` | Línea de producto (Gamer, Office, Creator…) | `line`, `sales_count`, `units_sold`, `revenue` |
| `/reports/quantity-distribution` | Cantidad de unidades por venta (1, 2, 3…) | `quantity`, `sales_count`, `revenue` |
| `/reports/price-ranges` | Rango de precio de las computadoras | `price_range`, `computers_count`, `stock`, `average_price` |
| `/reports/component-usage?limit=10` | Componente más usado en las computadoras | `id_component`, `name_component`, `category`, `used_in_computers`, `stock_component` |
| `/reports/inventory-by-category` | Categoría de componente (CPU, GPU, RAM…) | `category`, `components_count`, `out_of_stock`, `units_in_stock`, `inventory_value`, `average_price` |

Dos datos no se guardan como campo y se derivan del texto: la **línea** de una computadora es la segunda palabra de su nombre (`TechCore Gamer 004` → `Gamer`), y la **categoría** de un componente es la primera palabra de su descripción (`GPU 12GB GDDR6` → `GPU`). Si se agrega un campo `type` o `category` a los documentos, alcanza con cambiar ese agrupamiento en `report_repository.py`.

El redondeo a 2 decimales se aplica en Python y no con `$round`, para que los pipelines funcionen también en MongoDB anterior a 4.2 y en `mongomock`.

### Reglas de negocio

- **Computadoras:** todos los `id_component` deben existir. Si no se envía `price_computer`, se calcula como la suma de los componentes.
- **Ventas:** crear una venta descuenta el stock de la computadora de forma atómica; si no alcanza, responde 400. Cambiar la computadora o la cantidad con PUT/PATCH reajusta el stock, y DELETE lo devuelve. El `amount` lo calcula la API.
- **Borrado protegido:** no se puede borrar un componente que una computadora usa, ni una computadora que tiene ventas (400).

### Códigos de estado

Todos los errores tienen el mismo formato: `{"error": "mensaje", "status": código}`

| Código | Cuándo |
|---|---|
| 200 / 201 | Operación correcta (201 al crear) |
| 400 | ID mal formado, JSON inválido, campo faltante, desconocido o de tipo incorrecto, PATCH vacío, stock insuficiente, ID duplicado, borrado de algo en uso |
| 404 | El ID tiene formato válido pero no existe, o la ruta no existe |
| 405 | Método no permitido en esa ruta |
| 500 | Error de MongoDB o error inesperado (se registra en el log y no se expone el detalle) |

### Ejemplos

```bash
# Crear una venta
curl -X POST localhost:5000/sales -H "Content-Type: application/json" -d '{
  "id_computer": "pc-001", "quantity": 1,
  "Client": {"id_client": "cli-050", "full_name_client": "Sofía Díaz", "address": "Calle 1, Córdoba", "tel_contact": 3511111111, "email": "sofia@mail.com"},
  "Seller": {"id_seller": "sel-001", "full_name_seller": "Ana Torres", "commission": 0.05}
}'

# Actualizar solo el stock de un componente
curl -X PATCH localhost:5000/components/cmp-003 -H "Content-Type: application/json" -d '{"stock_component": 20}'
```

---

## 5. Cómo hacer cambios

**Agregar un campo a una entidad** (por ejemplo, `brand` en componentes):
1. Agregarlo al esquema en `validators.py` (`COMPONENT_SCHEMA`), indicando el validador y si es obligatorio.
2. Agregarlo a los datos de `seed.py`.
3. Agregar o ajustar los tests.

No hace falta tocar rutas ni repositorios: los esquemas definen qué campos se aceptan.

**Agregar una consulta nueva** (por ejemplo, ventas por día de la semana):
1. Crear el método en el repositorio correspondiente con la consulta de PyMongo. Si es un reporte, va en `report_repository.py`.
2. Crear la ruta en `routes/` que valide los parámetros y llame a ese método.
3. Agregar un test.

Las rutas nuevas aparecen solas en la página de inicio. Para darles una descripción corta, agregarla a `DESCRIPTIONS` en `routes/home.py`; si no, se usa la primera línea del docstring de la función.

**Agregar una colección nueva:**
1. Crear `repositories/xxx_repository.py` heredando de `BaseRepository`, con `collection_name` e `id_field`.
2. Registrarlo en `create_app()` dentro de `app.py`.
3. Crear `routes/xxx.py` con su Blueprint y registrarlo en `create_app()`.
4. Agregar el prefijo de ID y el esquema en `validators.py`.

### Convenciones

- Código, nombres y mensajes de la API en **inglés**.
- Los campos llevan el nombre de su entidad como sufijo (`name_component`, `price_computer`) para que no haya ambigüedad al combinar documentos.
- Las respuestas nunca incluyen el `_id` de Mongo.
- Antes de subir cambios, correr `pytest` y verificar que todo pase.

---

## 6. Análisis de los reportes

`analysis/reports_analysis.ipynb` es un notebook de Jupyter que consulta los endpoints de `/reports`, arma tablas con pandas y gráficos con matplotlib, y cierra cada sección con una lectura de los resultados y unas conclusiones generales.

```bash
python seed.py && python app.py        # en una terminal: la API tiene que estar corriendo
jupyter lab analysis/                  # en otra terminal
```

Se puede apuntar a otra instancia cambiando `API_URL` en la celda de configuración. Como consulta la API en cada ejecución, los gráficos e indicadores se recalculan solos si cambian los datos, pero los textos de lectura están escritos sobre los datos del seed.

---

## 7. Datos de ejemplo y tests

**`seed.py`** carga 60 componentes, 40 computadoras y 250 ventas. Los primeros documentos de cada colección están escritos a mano (`cmp-001` a `cmp-008`, `pc-001` a `pc-003`, `sale-001` a `sale-003`) y los tests dependen de ellos. El resto se genera con una semilla fija, así que siempre se obtienen los mismos datos. Las computadoras generadas siempre combinan piezas compatibles: el procesador y la motherboard tienen el mismo socket.

**`tests/test_api.py`** usa `mongomock`, una MongoDB simulada en memoria, así que se puede correr sin tener la base instalada. Cubre:
- el CRUD completo de las tres colecciones;
- el manejo de stock en ventas;
- los errores 400, 404 y 500;
- los reportes, comparando cada resultado con el mismo cálculo hecho en Python sobre los datos del seed;
- la validez de los datos del seed.

```bash
pytest -v                       # todos
pytest -v -k sale               # solo los que contienen "sale" en el nombre
```
