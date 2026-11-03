# Ejecución del entorno con Docker Compose

## 1. Requisitos previos

- Docker Desktop instalado y en ejecución. <br>
`docker -v` #muestra version disponible de docker  
- Docker Compose disponible. <br>
`docker compose version` #muestra version disponible de docker compose

## 2. Configuración inicial

**2.1 API como servicio del mismo entorno**


Para cumplir esto, a la carpeta `/api` que esta dentro de la raiz del proyecto.

en `dockeer_run.py` utiliza la logica de `app.py` para crear la API como servicio interno de docker.


**2.2 Desde la raíz del proyecto, ingresar a la carpeta `docker/`:**

```zsh
cd docker
```

Crear el archivo de configuración local a partir del ejemplo:

```zsh
cp .env.example .env
```

Completar las variables de entorno en `.env` con las credenciales y parámetros correspondientes.

## 3. Iniciar el entorno

Ejecutar desde la carpeta `docker/`:

```bash
docker compose up -d --build
```

Este comando construye la imagen de la API, crea los contenedores e inicia los servicios de MongoDB y Flask en segundo plano.

Para verificar el estado:

```bash
docker compose ps
```

Para consultar los registros:

```bash
docker compose logs api
docker compose logs mongo
```

## 4. Cargar los datos de prueba

Con los servicios iniciados, ejecutar:

Cargar datos. 
```bash
docker compose exec api python -c "import seed; from app import get_db; seed.load(get_db(), verbose=True)"
``` 

Salida esperada

```bash
components: 60 documents
computers: 40 documents
sales: 250 documents
total: 350 documents
```

Comprobar existencia de volumen (almacenamiento persistente)
```bash
docker volume ls
```

**Nota:** La carga elimina previamente los documentos existentes en estas tres colecciones y los reemplaza por los datos definidos en `seed.py`.

## 5. Acceder a la API

La API Flask queda disponible en:

http://localhost:5001

MongoDB queda accesible desde el host en el puerto `27018`.

La API se conecta a MongoDB utilizando el nombre del servicio de Compose (`mongo`) y el puerto interno `27017`.

## 6. Detener el entorno

Para detener los servicios y eliminar los contenedores:

```bash
docker compose down
```

Detiene docker y los datos almacenados en el volumen `mongo_data` se conservan.

Para deterner y eliminar el volumen y todos los datos persistidos:

```bash
docker compose down -v
```

**Advertencia: este último comando elimina permanentemente los datos almacenados en el volumen.**

