from __future__ import annotations

import sys
import copy
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from problem import EmergencyControlProblem
from simulator import load_scenario, goal_satisfied, simulate 
from state import initial_state
from world import World
from solver import solve_scenario 



def paso (problem, estado, tipo, arg):
    for accion, hijo in problem.successors(estado):
        if accion.kind == tipo and accion.arg == arg:
            return hijo
    raise AssertionError(f"{tipo} {arg} no es aplicable en {estado}")


# caso 1: estados equivalentes
def estados_equivalentes() -> None:
    world = World(load_scenario())
    problem = EmergencyControlProblem(world)
    s0 = initial_state(world)

    # llegar a Z2: hay que abrir DOOR1 con KEY1, que esta en Z1
    base = paso(problem, s0, "PICKUP", "KEY1")
    base = paso(problem, base, "OPEN_DOOR", "DOOR1")
    base = paso(problem, base, "MOVE", "Z2")

    # dos historias distintas desde el mismo punto de partida
    historia_a = paso(problem, paso(problem, base, "PICKUP", "CABLE"), "PICKUP", "CHIP")
    historia_b = paso(problem, paso(problem, base, "PICKUP", "CHIP"), "PICKUP", "CABLE")

    assert historia_a == historia_b, "misma situacion fisica, estados distintos"
    assert hash(historia_a) == hash(historia_b), "hash incoherente con __eq__"

    # el payload sale ORDENADO, no en el orden en que se recogieron los objetos
    assert historia_a.payload == ("CABLE", "CHIP", "KEY1")

    # consecuencia practica: CLOSED reconoce el duplicado y no lo re-expande
    assert len({historia_a, historia_b}) == 1


# caso 2: informacion relevante
def acciones(problem, estado, tipo):
    return {a.arg for a, _ in problem.successors(estado) if a.kind == tipo}

def informacion_relevante() -> None: #aca probamos si DOOR1 esta abierta o cerrada ya que eso puede cambiar hacia donde se mueve el robot
    world = World(load_scenario())
    problem = EmergencyControlProblem(world)
    s0 = initial_state(world)

    cerrada = paso(problem, s0, "PICKUP", "KEY1")
    abierta = paso(problem, cerrada, "OPEN_DOOR", "DOOR1")

    assert cerrada != abierta
    assert "DOOR1" not in cerrada.doors_open
    assert "DOOR1" in abierta.doors_open

    
    destinos_antes = acciones(problem, cerrada, "MOVE")
    destinos_despues = acciones(problem, abierta, "MOVE")
    assert destinos_despues > destinos_antes, "abrir la puerta debe habilitar rutas"


# caso 3: costos diferentes
def instancia_minima() -> dict:
    """Z1--(12)--Z3 en un movimiento, o Z1--(4)--Z2--(4)--Z3 en dos."""
    return {
        "zones": [{"id": "Z1"}, {"id": "Z2"}, {"id": "Z3"}],
        "corridors": [  # dirigidos: hay que declarar los dos sentidos
            {"from": "Z1", "to": "Z3", "cost": 12, "door": None},
            {"from": "Z3", "to": "Z1", "cost": 12, "door": None},
            {"from": "Z1", "to": "Z2", "cost": 4, "door": None},
            {"from": "Z2", "to": "Z1", "cost": 4, "door": None},
            {"from": "Z2", "to": "Z3", "cost": 4, "door": None},
            {"from": "Z3", "to": "Z2", "cost": 4, "door": None},
        ],
        "doors": [],
        "keys": [],
        "tools": [{"id": "TOOL", "zone": "Z1", "weight": 1, "repairs": ["PANEL"]}],
        "materials": [{"type": "MAT", "zone": "Z1", "count": 1, "weight": 1}],
        "panels": [{
            "id": "PANEL", "zone": "Z3", "state": "DAMAGED",
            "requires": {"tool": "TOOL", "material": "MAT"},
        }],
        "stations": [{
            "id": "STATION", "zone": "Z3", "state": "OFFLINE",
            "requires": {"panels_ok": ["PANEL"], "stations_online": []},
        }],
        "chargers": [],
        "robot": {
            "start": "Z1", "battery_start": 100,
            "battery_max": 100, "cargo_capacity": 2,
        },
        "action_costs": {"pickup": 1, "drop": 1, "interact": 2, "recharge": 3},
        "goal": {"stations_online": ["STATION"]},
    }


PLAN_CORTO = [  # 5 pasos usando el atajo: legal, pero cuesta 18
    {"op": "PICKUP", "item": "TOOL", "cost": 1},
    {"op": "PICKUP", "item": "MAT", "cost": 1},
    {"op": "MOVE", "from": "Z1", "to": "Z3", "cost": 12},
    {"op": "INTERACT", "target": "PANEL", "action": "REPAIR",
     "cost": 2, "consumes": "MAT"},
    {"op": "INTERACT", "target": "STATION", "action": "ACTIVATE", "cost": 2},
]


def costos_diferentes() -> None:
    escenario = instancia_minima()
    optimo = solve_scenario(escenario)

    # el agente da el rodeo barato
    assert optimo["total_cost"] == 14
    assert [s["to"] for s in optimo["steps"] if s["op"] == "MOVE"] == ["Z2", "Z3"]

    # el atajo era LEGAL y cumplia la meta: se descarto por caro, no por invalido
    final = simulate(escenario, PLAN_CORTO)
    assert goal_satisfied(escenario, final)
    assert final["energy_spent"] == 18

    # la propiedad: menos acciones, mas costo
    assert len(PLAN_CORTO) < len(optimo["steps"])
    assert final["energy_spent"] > optimo["total_cost"]


# caso 4: sin solucion
def escenario_sin_solucion() -> dict:
    escenario = copy.deepcopy(load_scenario())
    escenario["keys"] = [k for k in escenario["keys"] if k["id"] != "KEY3"]
    escenario["corridors"] = [
        c for c in escenario["corridors"] if {c["from"], c["to"]} != {"Z2", "Z5"}
    ]
    return escenario


def test_sin_solucion() -> None:
    resultado = solve_scenario(escenario_sin_solucion(), time_limit_s=120)

    # forma exacta que exige el contrato
    assert resultado["solution_found"] is False
    assert resultado["steps"] == []
    assert resultado["total_cost"] == 0
    assert "FAILURE" in resultado["message"]

    # termino por AGOTAR el espacio, no por corte de tiempo
    assert "no tiene solucion" in resultado["message"], resultado["message"]
    assert resultado["stats"]["expanded"] > 0
    assert resultado["stats"]["elapsed_s"] < 120



# caso 5: rutas alternativas
def rutas_alternativas() -> None:
    escenario = instancia_minima()
    world = World(escenario)
    # el agente solo genera la ruta minima y no habria dos alternativas que comparar
    problem = EmergencyControlProblem(world, macro_moves=False)

    cargado = paso(problem, initial_state(world), "PICKUP", "TOOL")
    cargado = paso(problem, cargado, "PICKUP", "MAT")

    atajo = paso(problem, cargado, "MOVE", "Z3")                      
    rodeo = paso(problem, paso(problem, cargado, "MOVE", "Z2"), "MOVE", "Z3") 

    # misma configuracion del mundo por las dos rutas...
    assert atajo.world_key() == rodeo.world_key()
    # ...pero distinto estado, porque la bateria forma parte de el
    assert atajo != rodeo
    assert rodeo.battery > atajo.battery

    # el agente completo conserva la ruta barata
    resultado = solve_scenario(escenario)
    assert [s["to"] for s in resultado["steps"] if s["op"] == "MOVE"] == ["Z2", "Z3"]
    assert resultado["total_cost"] == 14

if __name__ == "__main__":
    estados_equivalentes()
    informacion_relevante()
    costos_diferentes()
    test_sin_solucion()
    rutas_alternativas()
    print("Todos los tests pasaron")
