# Instrucciones de Ejecución para Emergency Control

## 1. Instalar dependencias

**Backend**

```bash
cd project/backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
# source .venv/bin/activate
pip install -r requirements.txt
```

**Frontend** (en otra terminal)

```bash
cd project/frontend
npm install
```

## 2. Iniciar el backend

```bash
cd project/backend/src
uvicorn main:app --reload --port 8000
```

## 3. Iniciar el frontend

Con el backend corriendo, en otra terminal:

```bash
cd project/frontend
npm run dev
```

Abra la URL que imprime Vite (normalmente <http://localhost:5173>).

## 4. Ejecutar el agente

El agente se ejecutara una vez sean iniciados tanto el backend como el frontend y ahi se podra visualizar su funcionamiento

**La búsqueda tarda unos 26 segundos.** Durante ese tiempo no imprime nada y la interfaz se queda esperando, no está bloqueado.

## 5. Probar una misión

En la interfaz, pulse **EXECUTE PLAN**. El frontend pide el plan a
`/api/solve`, aplicando las reglas del mundo
(puertas, batería, capacidad, materiales) y anima el resultado. Con **SPEED**
se ajusta la velocidad y con **RESET** se vuelve al estado inicial.

Para verificar el funcionamiento del agente mediante tests:

```bash
cd project/backend/tests
py test_demo_plan.py    # para correr el demo del agente simulado
py tests_agentes.py # para correr el agente funcionando
```

## 6. Interpretar el resultado

- Podra notar que encontrara en el panel derecho un numero de color naranja que hace referencia a coste de energia que le tomo a nuestro robot completar la meta, ademas de esto, debajo encontrara el paso a paso que siguio el robot para llegar a la meta. Los objetos que recogio, solto, hacia donde se movio entre otros, por otro lado, en el panel derecho encontrara la bateria del robot y el payload (inventario), esta información sera de gran importancia para determinar que tan optimo fue nuestor agente.