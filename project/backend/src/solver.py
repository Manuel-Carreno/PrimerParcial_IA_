from __future__ import annotations
from typing import Any

from problem import Action, EmergencyControlProblem
from search import SearchResult, uniform_cost_search
from state import State, initial_state
from translator import plan_to_steps
from world import World

__all__ = [ # lista de las piezas del agente
    "solve_scenario",
    "Action",
    "EmergencyControlProblem",
    "State",
    "World",
    "initial_state",
    "plan_to_steps",
    "uniform_cost_search",
]

_REASON_MESSAGE = {
    "optimal": "UCS: plan de costo minimo encontrado.",
    "initial": "El estado inicial ya satisface la meta.",
    "exhausted": (
        "FAILURE: se agoto el espacio de estados alcanzable. "
        "La mision no tiene solucion con este escenario."
    ),
    "time_limit": "FAILURE: se alcanzo el limite de tiempo de busqueda.",
    "expansion_limit": "FAILURE: se alcanzo el limite de expansiones.",
}


def solve_scenario( 
    scenario: dict[str, Any], 
    time_limit_s: float = 300.0,
    max_expansions: int = 5_000_000,
) -> dict[str, Any]:
    
    world = World(scenario)
    problem = EmergencyControlProblem(world)

    result: SearchResult = uniform_cost_search(
        problem,
        initial_state(world),
        max_expansions=max_expansions,
        time_limit_s=time_limit_s,
    )

    stats = dict(result.stats)
    stats["strategy"] = "UCS"

    if not result.found:
        return {
            "solution_found": False,
            "total_cost": 0,
            "steps": [],
            "message": _REASON_MESSAGE.get(result.reason, "FAILURE"),
            "stats": stats,
        }

    steps = plan_to_steps(world, result.plan)
    total = sum(int(s["cost"]) for s in steps)
    return {
        "solution_found": True,
        "total_cost": total,
        "steps": steps,
        "message": (
            f"{_REASON_MESSAGE.get(result.reason, '')} "
            f"{len(steps)} pasos, costo total {total}, "
            f"{stats.get('expanded', 0)} nodos expandidos en "
            f"{stats.get('elapsed_s', 0)}s."
        ).strip(),
        "stats": stats,
    }