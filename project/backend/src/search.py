"""Uniform Cost Search (Dijkstra) sobre grafo, con dominancia de bateria.

Por que UCS y no BFS/DFS:
  - los corredores tienen costos HETEROGENEOS (4, 3, 5, 6, 8, 12...), asi que
    "menos acciones" != "menor costo": BFS optimiza pasos, no costo;
  - se pide el plan de MENOR COSTO ACUMULADO;
  - todos los costos son positivos y el espacio (canonicalizado) es finito,
    asi que UCS es completo y optimo;
  - la estrategia elegida en `design.md` es UCS y es la que corre aqui.

Propiedades implementadas explicitamente:
  - La PRUEBA DE META se hace al EXTRAER de OPEN, no al generar. Con costos
    heterogeneos, hacerla al generar rompe la optimalidad.
  - CLOSED sobre estados CANONICOS: la misma situacion fisica alcanzada por
    dos historias distintas no se re-expande.
  - DOMINANCIA DE BATERIA: si dos caminos llegan al mismo mundo (zona, carga,
    suelo, puertas, paneles, estaciones) y uno trae MAS bateria a un costo
    MENOR O IGUAL, el otro esta dominado y se descarta. Es correcto porque
    mas bateria nunca habilita menos acciones (RECHARGE con bateria llena es
    ilegal, pero tampoco aporta nada: costaria energia para quedar igual).
"""

from __future__ import annotations

import heapq
import time
from dataclasses import dataclass, field
from typing import Any

from problem import Action, EmergencyControlProblem
from state import State


@dataclass(slots=True)
class Node:
    state: State
    parent: "Node | None" = None
    action: Action | None = None
    g: int = 0


@dataclass
class SearchResult:
    found: bool
    plan: list[Action] = field(default_factory=list)
    cost: int = 0
    stats: dict[str, Any] = field(default_factory=dict)
    reason: str = ""


def _reconstruct(node: Node) -> list[Action]:
    plan: list[Action] = []
    cur: Node | None = node
    while cur is not None and cur.action is not None:
        plan.append(cur.action)
        cur = cur.parent
    plan.reverse()
    return plan


def uniform_cost_search(
    problem: EmergencyControlProblem,
    initial: State,
    max_expansions: int = 3_000_000,
    time_limit_s: float = 60.0,
) -> SearchResult:
    t0 = time.perf_counter()

    if problem.is_goal(initial):
        return SearchResult(True, [], 0, {"expanded": 0, "generated": 0}, "initial")

    counter = 0
    root = Node(initial)
    frontier: list[tuple[int, int, Node]] = [(0, counter, root)]
    closed: set[State] = set()
    best_g: dict[State, int] = {initial: 0}
    # clave de mundo (sin bateria) -> pares (g, bateria) no dominados
    dominance: dict[tuple, list[tuple[int, int]]] = {
        initial.world_key(): [(0, initial.battery)]
    }

    expanded = 0
    generated = 0
    peak_frontier = 1

    while frontier:
        if expanded % 4096 == 0:
            if time.perf_counter() - t0 > time_limit_s:
                return SearchResult(
                    False,
                    [],
                    0,
                    _stats(expanded, generated, peak_frontier, len(closed), t0),
                    "time_limit",
                )
        if expanded > max_expansions:
            return SearchResult(
                False,
                [],
                0,
                _stats(expanded, generated, peak_frontier, len(closed), t0),
                "expansion_limit",
            )

        g, _, node = heapq.heappop(frontier)
        s = node.state
        if s in closed:
            continue
        # nodo obsoleto (habia una entrada mejor en OPEN)
        if g > best_g.get(s, g):
            continue

        # prueba de meta AL EXTRAER: garantiza optimalidad 
        if problem.is_goal(s):
            return SearchResult(
                True,
                _reconstruct(node),
                g,
                _stats(expanded, generated, peak_frontier, len(closed), t0),
                "optimal",
            )

        closed.add(s)
        expanded += 1

        for action, child in problem.successors(s):
            generated += 1
            if child in closed:
                continue
            new_g = g + action.cost
            prev = best_g.get(child)
            if prev is not None and prev <= new_g:
                continue
            if _dominated(dominance, child, new_g):
                continue
            best_g[child] = new_g
            counter += 1
            heapq.heappush(frontier, (new_g, counter, Node(child, node, action, new_g)))
            if len(frontier) > peak_frontier:
                peak_frontier = len(frontier)

    # si open esta vacio quiere decir que el espacio alcanzable se agoto sin encontrar meta y lo lleva a failure
    return SearchResult(
        False,
        [],
        0,
        _stats(expanded, generated, peak_frontier, len(closed), t0),
        "exhausted",
    )


def _dominated(
    store: dict[tuple, list[tuple[int, int]]], child: State, new_g: int
) -> bool:
    wkey = child.world_key()
    bat = child.battery
    entries = store.get(wkey)
    if entries is None:
        store[wkey] = [(new_g, bat)]
        return False
    for og, ob in entries:
        if og <= new_g and ob >= bat:
            return True
    kept = [(og, ob) for og, ob in entries if not (new_g <= og and bat >= ob)]
    kept.append((new_g, bat))
    store[wkey] = kept
    return False


def _stats(
    expanded: int, generated: int, peak: int, closed: int, t0: float
) -> dict[str, Any]:
    return {
        "expanded": expanded,
        "generated": generated,
        "peak_frontier": peak,
        "closed": closed,
        "elapsed_s": round(time.perf_counter() - t0, 3),
    }