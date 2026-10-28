# Catálogo y gestión de productos

## 1. Requerimientos del proyecto

### 1.1. Análisis y diseño de la base de datos 
- La problematica es la administracion y gestion de una tienda e-commerce de computadoras. <br>
Diagrama tentativo incial el cual debe transformarse para obtener un diseño NoSQL. Se muestran entidades con sus atributos y como se conectan. Los comentarios en las uniones de tablas denotan que entidades podrian ser referenciadas y cuales incrustadas.     

``` mermaid 
erDiagram
    
    COMPUTER ||--|{ COMPONENT : "embedded"
    COMPUTER ||--o{ SALE : "referenced"
    CLIENT ||--o{ SALE : "embedded"
    SELLER ||--O{ SALE : "embedded"

    COMPONENT {
        string id PK
        string name
        string description
        decimal price
        decimal stock
        boolean state
    }
    COMPUTER {
		string id PK
		string name
		string description
		COMPONENT components
		decimal price
		decimal stock
		boolean state
	}
	CLIENT {
		string id PK
		string full_name
        string address
        int tel_contact
        string email
	}
	SALE {
		string id PK
		COMPUTER computer
		decimal amount
		CLIENT client
        tinyint quantity 
	}

    SELLER{
        string id PK
        string full_name
        decimal commission

    }
```
----------------
---------------- 
<br>

- Entidades principales: `Sale`, `Computer`. 
- Colecciones: `Seller`, `Client`, `Component`  

- Requerimientos funcionales principales: 
    - Gestion Ventas online 
    - Administracion de stock 
    - Cliente pueda armar su propia computadora 

<br>

- Atributos obligatorios: 
    - Computer: id, name, descripcion, price, stock
    - Client: id, full_name, address, tel_contact, email
    - Seller: id, full_name, commission
    - Component: id, name, description, price, stock
    - Sale: id, computer, amount 

<br>

- Atributos opcionales: 
    - Computer: state (se puede controlar desde stock)
    - Component: state (se puede controlar desde stock)
    - Sale: client (no es necesario ya que lo incrustaremos en la venta)
----------------
---------------- 
<br>

### Estructura documento JSON
```
    Computer {
        "id_computer":
        "id_component" 
        "name_computer": 
        "description_computer": 
        "price_computer":
        "stock_computer":
    } 
```

```
"Component":{
        "id_component":
        "name_component": 
        "description_component":
        "price_component":
        "stock_component":
    }
```
```
    Sale {
        "id_sale":
        "id_computer": 
        "amount":  
        "quantity:"
        "Client":[
            {
                "id_client": 
                "full_name_client": 
                "address": 
                "tel_contact":
                "email":
            }
        ]

        "Seller":[
            {
                "id_seller": 
                "full_name_seller": 
                "commission":
            }
        ]
    }
```

-----------
-----------
<br>

- Relaciones entre documentos:
    - `Component`es referenciada por `Computer` ya que cada computadora tiene una lista de componentes con la cual sera armada. Por lo tanto dependiendo la computadora sera los componentes que utilizara. <br>

    Decidimos no vender componentes de manera individual por cuestiones de tiempo y para que el diagrama sea mas sencillo y evitar el problema de tener que incrustar/embeber a `Component` en `Sale`            

    - En cambio con `Client`, `Seller` y `Sale` resulta logico embeber las coleeciones Cliente y Seller en Sale por dos motivos, uno es que son relaciones 1 venta contra muchos clientes y vendedores, y dos venta tendra obligatoriamente un cliente y vendedor. Estos dos motivos justifica la incrustacion de Cliente y Seller en Sale.  
        

    