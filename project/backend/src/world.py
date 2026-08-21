from __future__ import annotations

from typing import Any


class World:
    """Constantes de la instancia. Nunca se modifica durante la busqueda."""

    def __init__(self, scenario: dict[str, Any]) -> None:
        self.scenario = scenario

        robot = scenario["robot"]
        self.start_zone: str = robot["start"]
        self.battery_start: int = int(robot["battery_start"])
        self.battery_max: int = int(robot["battery_max"])
        self.capacity: int = int(robot["cargo_capacity"])

        costs = scenario.get("action_costs", {})
        self.cost_pickup: int = int(costs.get("pickup", 1))
        self.cost_drop: int = int(costs.get("drop", 1))
        self.cost_interact: int = int(costs.get("interact", 2))
        self.cost_recharge: int = int(costs.get("recharge", 3))

        # zonas y grafo de corredores 
        self.zones: dict[str, dict[str, Any]] = {z["id"]: z for z in scenario["zones"]}
        # adyacencia: zona -> [(destino, costo, puerta|None)]
        self.adj: dict[str, list[tuple[str, int, str | None]]] = {
            z["id"]: [] for z in scenario["zones"]
        }
        for c in scenario["corridors"]:
            self.adj.setdefault(c["from"], []).append(
                (c["to"], int(c["cost"]), c.get("door"))
            )

        # puertas y llaves 
        self.doors: dict[str, dict[str, Any]] = {d["id"]: d for d in scenario["doors"]}
        self.door_of_key: dict[str, str] = {d["key"]: d["id"] for d in scenario["doors"]}
        self.keys: dict[str, dict[str, Any]] = {k["id"]: k for k in scenario["keys"]}

        # herramientas y materiales 
        self.tools: dict[str, dict[str, Any]] = {t["id"]: t for t in scenario["tools"]}
        self.material_weight: dict[str, int] = {
            m["type"]: int(m.get("weight", 1)) for m in scenario["materials"]
        }

        # paneles y estaciones 
        self.panels: dict[str, dict[str, Any]] = {p["id"]: p for p in scenario["panels"]}
        self.stations: dict[str, dict[str, Any]] = {
            s["id"]: s for s in scenario["stations"]
        }

        # cargadores 
        self.charger_in_zone: dict[str, str] = {
            c["zone"]: c["id"] for c in scenario.get("chargers", [])
        }

        # meta 
        self.goal_stations: tuple[str, ...] = tuple(
            scenario["goal"].get("stations_online", [])
        )

        # Cierre de dependencias: estaciones que REALMENTE hay que activar
        # (las de la meta + las que ellas exigen, transitivamente).
        self.needed_stations: frozenset[str] = self._closure_stations()
        # Paneles que hay que reparar para esas estaciones.
        needed_panels: set[str] = set()
        for sid in self.needed_stations:
            needed_panels.update(self.stations[sid]["requires"].get("panels_ok", []))
        self.needed_panels: frozenset[str] = frozenset(needed_panels)

        # Peso de cada token, precalculado (constante del escenario)
        self._weights: dict[str, int] = {}
        for kid, k in self.keys.items():
            self._weights[kid] = int(k.get("weight", 1))
        for tid, tl in self.tools.items():
            self._weights[tid] = int(tl.get("weight", 1))
        self._weights.update(self.material_weight)

        # Memos (no son estado: solo aceleran consultas derivadas)
        self._mat_demand_cache: dict = {}
        self._tool_live_cache: dict = {}
        self._weight_cache: dict = {}

        # Indices utiles
        self.panels_by_zone: dict[str, list[str]] = {}
        for pid, p in self.panels.items():
            self.panels_by_zone.setdefault(p["zone"], []).append(pid)
        self.stations_by_zone: dict[str, list[str]] = {}
        for sid, s in self.stations.items():
            self.stations_by_zone.setdefault(s["zone"], []).append(sid)
        self.doors_by_zone: dict[str, list[str]] = {}
        for did, d in self.doors.items():
            for z in d["between"]:
                self.doors_by_zone.setdefault(z, []).append(did)

    
    def _closure_stations(self) -> frozenset[str]:
        pending = list(self.goal_stations)
        seen: set[str] = set()
        while pending:
            sid = pending.pop()
            if sid in seen or sid not in self.stations:
                continue
            seen.add(sid)
            pending.extend(self.stations[sid]["requires"].get("stations_online", []))
        return frozenset(seen)


    def kind_of(self, token: str) -> str:
        if token in self.keys:
            return "key"
        if token in self.tools:
            return "tool"
        return "material"

    def weight_of(self, token: str) -> int:
        return self._weights.get(token, 1)

    def recharge_target(self, zone: str) -> str | None:
        """Id de cargador a emitir en el plan, o None si la zona no recarga."""
        if zone in self.charger_in_zone:
            return self.charger_in_zone[zone]
        if self.zones.get(zone, {}).get("recharge"):
            return zone  # zona marcada como recharge sin cargador explicito
        return None