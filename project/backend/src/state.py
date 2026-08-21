from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  
    from world import World


class State:

    __slots__ = (
        "zone",
        "battery",
        "payload",
        "ground_keys",
        "ground_tools",
        "ground_materials",
        "doors_open",
        "panels_ok",
        "stations_online",
        "_key",
        "_hash",
    )

    def __init__(
        self,
        zone: str,
        battery: int,
        payload: tuple[str, ...],
        ground_keys: tuple[tuple[str, str], ...],
        ground_tools: tuple[tuple[str, str], ...],
        ground_materials: tuple[tuple[str, str, int], ...],
        doors_open: tuple[str, ...],
        panels_ok: tuple[str, ...],
        stations_online: tuple[str, ...],
    ) -> None:
        self.zone = zone
        # nivel de bateria: forma parte de la situacion fisica (enunciado §2.1)
        self.battery = battery
        # multiconjunto ORDENADO de tokens (KEY1, MULTITOOL, FUSE, ...)
        self.payload = payload
        # ((key_id, zona), ...) ordenado — solo llaves VIVAS
        self.ground_keys = ground_keys
        # ((tool_id, zona), ...) ordenado — solo herramientas VIVAS
        self.ground_tools = ground_tools
        # ((tipo, zona, cantidad), ...) ordenado — solo materiales VIVOS
        self.ground_materials = ground_materials
        self.doors_open = doors_open
        self.panels_ok = panels_ok
        self.stations_online = stations_online
        # clave de MUNDO: todo menos la bateria (usada por la dominancia)
        self._key = (
            zone,
            payload,
            ground_keys,
            ground_tools,
            ground_materials,
            doors_open,
            panels_ok,
            stations_online,
        )
        self._hash = hash((self._key, battery))

    def world_key(self) -> tuple:
        """Todo menos la bateria: clave para la dominancia energetica."""
        return self._key

    def __eq__(self, other) -> bool:  # noqa: D105
        return (
            self.battery == other.battery
            and self._key == other._key
            and isinstance(other, State)
        )

    def __hash__(self) -> int:  # noqa: D105
        return self._hash

    def __repr__(self) -> str:  # pragma: no cover - solo para depuracion
        return (
            f"State(zone={self.zone}, bat={self.battery}, "
            f"payload={self.payload}, panels_ok={self.panels_ok}, "
            f"stations={self.stations_online})"
        )


# Vivacidad / relevancia
def key_is_live(world: "World", key_id: str, doors_open: tuple[str, ...]) -> bool:
    #Una llave sirve solo si su puerta sigue cerrada
    door = world.door_of_key.get(key_id)
    return door is not None and door not in doors_open


def tool_is_live(world: "World", tool_id: str, panels_ok: tuple[str, ...]) -> bool:
    #Una herramienta sirve solo si queda algun panel NECESARIO que la exija
    ck = (tool_id, panels_ok)
    hit = world._tool_live_cache.get(ck)
    if hit is not None:
        return hit
    val = any(
        pid not in panels_ok and world.panels[pid]["requires"]["tool"] == tool_id
        for pid in world.needed_panels
    )
    world._tool_live_cache[ck] = val
    return val


def material_demand(world: "World", mat_type: str, panels_ok: tuple[str, ...]) -> int:
    # Unidades de ese material que todavia faltan por consumir
    ck = (mat_type, panels_ok)
    hit = world._mat_demand_cache.get(ck)
    if hit is not None:
        return hit
    n = 0
    for pid in world.needed_panels:
        if pid in panels_ok:
            continue
        if world.panels[pid]["requires"]["material"] == mat_type:
            n += 1
    world._mat_demand_cache[ck] = n
    return n


def payload_weight(world: "World", payload: tuple[str, ...]) -> int:
    hit = world._weight_cache.get(payload)
    if hit is None:
        hit = sum(world.weight_of(t) for t in payload)
        world._weight_cache[payload] = hit
    return hit



def prune_dead(world: "World", s: State) -> State:
    gk = tuple(e for e in s.ground_keys if key_is_live(world, e[0], s.doors_open))
    gt = tuple(e for e in s.ground_tools if tool_is_live(world, e[0], s.panels_ok))
    gm = tuple(
        e for e in s.ground_materials if material_demand(world, e[0], s.panels_ok) > 0
    )
    if gk == s.ground_keys and gt == s.ground_tools and gm == s.ground_materials:
        return s
    return State(
        s.zone,
        s.battery,
        s.payload,
        gk,
        gt,
        gm,
        s.doors_open,
        s.panels_ok,
        s.stations_online,
    )


def initial_state(world: "World") -> State:
    ground_keys = tuple(sorted((k, v["zone"]) for k, v in world.keys.items()))
    ground_tools = tuple(sorted((t, v["zone"]) for t, v in world.tools.items()))
    ground_materials = tuple(
        sorted(
            (m["type"], m["zone"], int(m["count"]))
            for m in world.scenario["materials"]
            if int(m["count"]) > 0
        )
    )
    doors_open = tuple(
        sorted(d for d, v in world.doors.items() if v.get("state") == "OPEN")
    )
    panels_ok = tuple(
        sorted(p for p, v in world.panels.items() if v.get("state") == "OK")
    )
    stations_online = tuple(
        sorted(s for s, v in world.stations.items() if v.get("state") == "ONLINE")
    )
    return prune_dead(
        world,
        State(
            world.start_zone,
            world.battery_start,
            (),
            ground_keys,
            ground_tools,
            ground_materials,
            doors_open,
            panels_ok,
            stations_online,
        ),
    )