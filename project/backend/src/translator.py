from __future__ import annotations

from typing import Any

from problem import Action
from world import World

_INTERACT_KINDS = ("OPEN_DOOR", "REPAIR", "ACTIVATE", "RECHARGE")


def _corridor_cost(world: World, frm: str, to: str) -> int:
    for dest, cost, _door in world.adj.get(frm, []):
        if dest == to:
            return cost
    raise ValueError(f"No existe corredor {frm}->{to} en el escenario")


def action_to_steps(world: World, action: Action) -> list[dict[str, Any]]:
    kind = action.kind

    if kind == "MOVE":
        path = action.path or ()
        steps: list[dict[str, Any]] = []
        for frm, to in zip(path, path[1:]):
            steps.append(
                {
                    "op": "MOVE",
                    "from": frm,
                    "to": to,
                    "cost": _corridor_cost(world, frm, to),
                }
            )
        return steps

    if kind == "PICKUP":
        return [{"op": "PICKUP", "item": action.arg, "cost": world.cost_pickup}]

    if kind == "DROP":
        return [{"op": "DROP", "item": action.arg, "cost": world.cost_drop}]

    if kind == "SWAP":
        # soltar `arg` para hacer hueco y recoger `extra`
        return [
            {"op": "DROP", "item": action.arg, "cost": world.cost_drop},
            {"op": "PICKUP", "item": action.extra, "cost": world.cost_pickup},
        ]

    if kind in _INTERACT_KINDS:
        cost = world.cost_recharge if kind == "RECHARGE" else world.cost_interact
        step: dict[str, Any] = {
            "op": "INTERACT",
            "target": action.arg,
            "action": kind,
            "cost": cost,
        }
        if kind == "REPAIR":
            step["consumes"] = action.extra
        return [step]

    raise ValueError(f"Accion interna sin traduccion al contrato: {kind}")


def plan_to_steps(world: World, plan: list[Action]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for action in plan:
        steps.extend(action_to_steps(world, action))
    return steps