# Diseño del agente

Este documento debe completarse **antes** de la implementación principal del agente.

Use sus propias palabras y notación. No reemplace este archivo por una transcripción
del enunciado. Las subsecciones existen para que no se le olvide una decisión;
usted decide el contenido.

El entorno, según las propiedades vistas en clase, es totalmente observable,
determinista, secuencial, estático, discreto y de agente único. Bajo esas
condiciones la solución es un **plan completo** y el marco correcto es la
búsqueda clásica. Justifique cada componente con ese marco (AIMA, cap. 3).

---

## Estado

### Definición formal

Escriba la tupla de estado. Cada componente debe ser una variable que el robot
necesita para saber qué podrá hacer después.

```text
s = ⟨ … ⟩
```

**Para el estado lo definiria como:**
Zona actual del robot, Bateria restante, Carga, Ubicación de cada llave, Ubicación de cada herramienta, Estado de las puertas, Estado de los paneles y el estado de las estaciones. Para definrilo como una tupla lo haria asi:

```text
s = ⟨robot_zone, battery, payload, ground_keys, ground_tools, ground_materials, doors, panels, stations⟩
```

### Por qué cada variable es necesaria

Criterio de clase (`Applicable`): una variable pertenece al estado **si y solo si**
dos configuraciones que difieran en ella pueden diferir en las acciones legales
futuras o en su resultado.

Pase ese filtro con cada variable. En particular:

- la **batería** forma parte de la situación física (§2.1 del enunciado);
- la **posición de los objetos** no se deduce del escenario inicial si el robot
  puede soltarlos (`DROP`);
- los cambios permanentes (puertas, paneles, estaciones) condicionan el futuro.

**Respuesta:** Considero que cada variable es necesaria por que nos da un entendimiento mas amplio sobre el entorno que nos rodea y sobre las variables en el estado, cada una de estas es necesaria para llegar a completar la meta (reparar los panales y activar las estaciones). Por ejemplo, con el robot_zone nos indica en que zona esta el robot y nos ayuda a determinar que objetos puede recoger o que acciones puede hacer, con panels podemos saber el estado de los paneles y saber si ya ha sido reparado o no, esto nos ayuda particularmente ya que es una de las metas del programa y por ultimo el payload nos dice "el inventario" del robot ya con esto podemos saber que objetos lleva y no exceder la capacidad de 3 objetos max.
En conlusión, tanto estas variables como las demas que hay y junto con las acciones son necesarias por que nos permiten la situación actual del robot y completar la meta.

### Qué información se deriva y NO se almacena

Peso de la carga, grafo de corredores, costos, capacidad, batería máxima, etc.
Si se puede calcular a partir del estado y de las constantes del escenario, no
es una variable de estado.

**Respuesta:** No es necesario guardar como variables del estado información que puede obtenerse de otras variables o de las constantes del escenario. Por ejemplo, el peso total de la carga se puede calcular a partir de payload, el grafo de corredores y sus costos hacen parte del escenario, y cargo_capacity y battery_max son constantes

### Qué pertenece al historial de búsqueda y no al estado físico

`g(n)`, el padre y la acción que trajo aquí describen *cómo llegó*, no *dónde
está*. Viven en el **Nodo**. Si se meten en el estado, CLOSED no puede reconocer
la misma situación física alcanzada por dos rutas.

**Respuesta:** Lo que vendria a pertenecer al historial de busqueda es toda cosa aquella relacionada con el nodo, su estado fisico + lo que ha hecho para llegar hasta ahi, como puede ser: Sale de Z1 → Pasa a Z2 → Recoge una soldadura ... 
Por otro lado, el estado fisico es para este caso y siguiendo el ejemplo: robot_zone: Z1 → robot_zone: Z2 → payload: [soldadura] ...

### Cuándo dos configuraciones son el mismo estado

Materiales equivalentes por tipo (§2.2): no les ponga ids artificiales.
Estructuras canónicas (conjuntos, contadores) para que `==` y el hash coincidan
con la equivalencia física. Sin eso Graph Search explota.

**Respuesta:** Dos configuraciones son el mismo estado cuando representan la misma equivalencia. Por ejemplo, algo puntual puede ser el de entorno_preparcial.py en donde no importaba si era [Tarjeta_Acceso, Fusible] o [Fusible, Tarjeta_Acceso] la funcion __eq__ las reconocia como iguales ya que esos elementos no tienen ids unicos, para este caso seria como tener [FUSE, KEY1]= [KEY1, FUSE]

### Relevancia: objetos que ya no cambian el futuro

Los cambios del entorno son **monótonos** (una puerta abierta no se cierra).
Pregúntese: una llave cuya puerta ya está abierta, o una herramienta cuyo panel
ya está reparado, ¿sigue distinguiendo estados si solo cambia *dónde* está en
el suelo? Si no habilita ninguna acción futura, incluirla multiplica el espacio
con permutaciones de objetos muertos. Justifique si las ignora y por qué eso
no pierde el óptimo.

**Respuesta:** Considero que lo mejor para que el programa sea mas optimo y eficiente es ignorarlas ya que asi estoy seria como un objeto "muerto" por que para la funcion que estaba diseñado ya ha sido cumplida, tomando como ejemplo lo de la llave como ya fue usada no tiene sentido tenerla en cuenta ya que la puerta ya fue abierta, ignorarlas no pierde lo optimo porque estos objetos ya no pueden afectar las acciones hechas en el futuro por el robot ni cambiar el costo de llegar a la meta


---

## Acciones

Defina las acciones **internas** del agente (nombres libres). Para cada una:
precondiciones, efectos, costo. Toda acción del mundo exige además
`batería ≥ costo`.

Puede usar una tabla:

| Acción | Precondiciones | Efectos | Costo |
|---|---|---|---|
| `MOVE` | Existe un corredor desde `robot_zone` hasta `to`; la puerta asociada está abierta o no existe; batería suficiente. | `robot_zone` pasa a ser `to` y se descuenta el costo de la batería. | Costo del corredor |
| `PICKUP` | El objeto está en `robot_zone`; `peso(payload) + peso(item) ≤ cargo_capacity`; batería suficiente. | El objeto pasa del suelo a `payload` y se descuenta el costo de la batería. | 1 |
| `DROP` | El objeto está en `payload` y hay batería suficiente. | El objeto sale de `payload` y queda en el suelo de `robot_zone`; se descuenta el costo de la batería. | 1 |
| `OPEN_DOOR` | `robot_zone` está junto a `door`; `door` está cerrada; la llave correspondiente está en `payload`; batería suficiente. | `door` pasa a `OPEN` y se descuenta el costo de la batería. | 2 |
| `REPAIR` | `robot_zone` coincide con la zona del panel; `panel` está dañado; la herramienta y el material requeridos están en `payload`; batería suficiente. | `panel` pasa a `OK`, se consume el material y se descuenta la batería. | 2 |
| `ACTIVATE` | `robot_zone` coincide con la zona de la estación; `station` está `OFFLINE`; se cumplen sus requisitos; batería suficiente. | `station` pasa a `ONLINE` y se descuenta la batería. | 2 |
| `RECHARGE` | `robot_zone` coincide con la zona del cargador; `battery < battery_max`; batería suficiente para el costo. | `battery` pasa a `battery_max`. | 3 |

Todas las acciones son deterministas: si una acción es legal, produce un único
estado siguiente. Para reducir el espacio de búsqueda, `DROP` solo se genera
cuando es necesario liberar capacidad, dejar un material o conservar una carga
útil para una acción posterior. No se genera automáticamente en cualquier zona.



### `Applicable` interno vs legalidad del contrato

El simulador dice cuándo un paso es **legal**. Su generador de sucesores dice
qué acciones son **relevantes para buscar**. No tienen que ser el mismo conjunto.

El contrato **permite** `DROP` en cualquier zona si el objeto está en la carga.
Si su agente genera ese `DROP` en cada estado con carga, el espacio deja de ser
«5 zonas y unas tareas» y pasa a ser «en cuál de las 5 zonas quedó cada objeto».
Eso no se arregla cambiando `cargo_capacity` ni apagando la batería: el escenario
es la fuente de verdad y el profesor probará otras instancias.

Usted puede (y se espera que) restrinja `DROP` —y cualquier otra acción— a los
casos que un plan **óptimo** podría necesitar. Justifique que ningún plan de
costo mínimo usa una acción que usted dejó de generar.

**Respuesta:** Considero que generaria la acción de DROP unicamente cuando necesita el espacio en el payload para recoger otro objeto o cuando el objeto ya no sea util en el futuro, con esto no se pierde la solución optima, ya que nunca se eliminaria un objeto que aun me sea util en el futuro como abrir una puerta, reparar un panel o activar una estación 


---

## Modelo de transición

```text
s  --a-->  s'     solo si a ∈ Applicable(s)
```

`Result` es determinista y parcial. Qué puede cambiar: zona, carga/suelo,
batería, entorno persistente. Qué se preserva. Si canonicaliza el estado tras
una acción, dígalo aquí.

**Respuesta**: Las acciones pueden modificar la zona, batería, carga, objetos del suelo, puertas, paneles y estaciones. Las demás variables permanecen iguales. La batería se reduce según el costo de la acción y RECHARGE la restaura al maximo la bateria

---

## Prueba de meta

```text
Goal(s) ⟺ …
```

La misión se verifica sobre el **estado final del mundo**, no sobre haber
ejecutado una lista de tareas. ¿Las puertas y los paneles son parte de la meta
o solo medios?

**Respuesta:**
```text
Goal(s) ⟺  GENERATOR, ARTILLERY, COMMAND == ONLINE
```
Los paneles y las puertas no son parte de la meta, son solo medios por que como podemos notar en el scenario.json el goal es que GENERATOR, ARTILLERY Y COMMAND esten ONLINE y la meta se verifica sobre el estado final mas no sobre una lista de tareas.

---

## Función de costo

```text
g(n) = …
```

Debe ser la suma de los **costos oficiales** del escenario (no el número de
pasos). Explique por qué minimizar pasos no es lo mismo que minimizar costo
en este mundo (hay corredores baratos y caros).

**Respuesta:** 
```text
g(n) = Σ costo(aᵢ)
```
Ya que de esta manera representamos la suma de los costos de todas las acciones realizadas desde el estado inicial hasta el nodo actual, dependiendo del camino que elija.

---

## Estrategia de búsqueda

Elija una estrategia **vista en clase** y justifíquela con las propiedades
reales del problema (costos heterogéneos, plan de menor costo, espacio finito).

Discuta:

- completitud
- optimalidad (¿la prueba de meta se hace al extraer o al generar?)
- costo de camino
- tiempo y espacio (el `b` peligroso no es el grado del mapa: es cuántos
  `DROP`/`PICKUP` genera por estado)
- cuándo se rompen las garantías (costos 0 o negativos, estados mal
  canonicalizados, OPEN que no se vacía)

Graph Search exige una lista CLOSED sobre estados **canónicos**. Explique cómo
evita reexplorar la misma situación física.

**Respuesta:** Para este ejercicio en particular usare UCS / Dijkstra, por que como cada accion tiene costos distintos y el objetivo es encontrar el plan de menor costo, como este usa anillos concentricos los cuales se expanden como "una onda" para buscar el de menor costo, es ideal para este caso.

- Completitud: Como los costos son positivos, el algoritmo podrá encontrar una solución si existe.

- Optimalidad: UCS es óptimo porque expande los nodos en orden de g(n). La prueba de meta se hace cuando el nodo es extraído de OPEN, no cuando es generado. De esta forma, cuando se encuentra una meta, se garantiza que no existe otro camino de menor costo pendiente por explorar

- Costo de Camino: Como el costo de un nodo corresponde a la suma de los costos de todas las acciones realizadas, entonces ucs puede elegir un plan de busqueda con más acciones asi su costo total es menor

- Tiempo y espacio: El espacio de busqueda puede crecer bastante debido a las diferentes configuraciones de los objetos, por eso es importante limitar algunas acciones como las de drop que no aporten a una solución optima 

- Cuando se rompen las garantias: Se rompen las acciones con costo 0 o si es negativo ya que puede entrar en bucles infinitos.

### Batería como recurso

La batería **sí** va en el estado (§2.1). Eso no implica explorar todos los
paseos que solo gastan energía. Si dos caminos llegan a la **misma**
configuración del mundo (zona, carga, suelo, entorno) y uno trae **más batería
residual** a un **costo menor o igual**, el | otro no puede mejorar ningún plan
futuro: está dominado. Tratar cada nivel de batería como un mundo distinto,
sin esa observación, hace que UCS recorra detours inútiles hasta agotar
memoria. Justifique cómo CLOSED aprovecha (o no) esta dominancia.

**Respuesta:** Con la lista CLOSED podemos ver cuáles estados ya fueron explorados. Además, si dos estados tienen la misma configuración del mundo, podemos comparar cuál tiene más batería y un costo menor o igual. Así podemos considerar que el otro estado que tiene más batería y menor o igual costo es mejor, mientras que el otro estado está dominado y no es necesario seguir explorándolo.

---

## Formulación y tamaño del espacio (obligatorio)

El mapa visible es pequeño. El espacio de estados **no** lo es, si se formula
mal. Responda con sus palabras:

1. ¿Por qué «5 zonas, ~10 objetos, capacidad 3» puede generar millones de nodos
   en un UCS ingenuo?
2. ¿Qué papel tiene `DROP` en esa explosión?
3. ¿Qué podas o abstracciones aplicó y por qué **no pierden el óptimo**
   (*sound*)?
4. ¿Por qué **no** es solución subir la capacidad, bajar las estaciones o
   ignorar la batería?

**Respuesta**: 
1. Aunque el mapa solo tiene cinco zonas, los objetos pueden estar en el suelo o
en el `payload`, y existen muchas combinaciones posibles de carga, ubicaciones,
puertas, paneles, estaciones y batería. Por eso un UCS ingenuo puede generar
millones de estados.

2. `DROP` aumenta la explosión porque permite dejar cada objeto en distintas
zonas. Si se genera sin restricciones, el buscador explora muchas configuraciones
que no ayudan a cumplir la meta.

3. Para reducir el espacio, solo genero `DROP` cuando es necesario liberar
capacidad o cuando el objeto ya no será útil. También ignoro objetos que ya no
pueden afectar ninguna acción futura. Estas podas no pierden el óptimo porque no
eliminan ninguna acción necesaria para alcanzar la meta.

4. Aumentar la capacidad o ignorar la batería no representa correctamente el
escenario. La capacidad forma parte de las restricciones reales del robot y la
batería determina qué acciones son legales. Reducir el número de estaciones
cambiaría la meta original, por lo que ninguna de estas opciones soluciona el
problema de formulación.
