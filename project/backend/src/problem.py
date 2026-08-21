from __future__ import annotations

import heapq
from dataclasses import dataclass

from state import State, material_demand, payload_weight, prune_dead, tool_is_live
from world import World


@dataclass(frozen=True, slots=True)
class Action:

    kind: str  # MOVE | PICKUP | DROP | OPEN_DOOR | REPAIR | ACTIVATE | RECHARGE
    arg: str  # zona destino / token / id de puerta, panel, estacion o cargador
    cost: int
    extra: str | None = None  # REPAIR: material consumido
    path: tuple[str, ...] = ()  # MOVE: ruta completa de zonas (macro-movimiento)

    def __str__(self) -> str:  # pragma: no cover - solo para logs
        if self.kind == "MOVE":
            return f"MOVE {'->'.join(self.path)} (c={self.cost})"
        if self.kind == "REPAIR":
            return f"REPAIR {self.arg} consume={self.extra} (c={self.cost})"
        return f"{self.kind} {self.arg} (c={self.cost})"


def _insert_sorted(items: tuple, value) -> tuple:
    lst = list(items)
    lst.append(value)
    lst.sort()
    return tuple(lst)


class EmergencyControlProblem:
    def __init__(
        self,
        world: World,
        macro_moves: bool = True,
        allow_live_drop: bool = True,
    ) -> None:
        self.w = world
        self.macro_moves = macro_moves
        self.allow_live_drop = allow_live_drop
        self._dist_cache: dict[tuple[str, tuple[str, ...]], dict] = {}

    
    # en la prueba de meta se verifica sobre el estado y que se cumpla
    def is_goal(self, s: State) -> bool:
        online = set(s.stations_online)
        return all(sid in online for sid in self.w.goal_stations)


    # rutas minimias entre las zonas
    def _shortest_paths(self, origin: str, doors_open: tuple[str, ...]) -> dict:
        cache_key = (origin, doors_open)
        cached = self._dist_cache.get(cache_key)
        if cached is not None:
            return cached
        open_set = set(doors_open)
        dist: dict[str, tuple[int, tuple[str, ...]]] = {origin: (0, (origin,))}
        pq: list[tuple[int, str]] = [(0, origin)]
        while pq:
            d, z = heapq.heappop(pq)
            if d > dist[z][0]:
                continue
            for to, cost, door in self.w.adj.get(z, []):
                if door is not None and door not in open_set:
                    continue
                nd = d + cost
                cur = dist.get(to)
                if cur is None or nd < cur[0]:
                    dist[to] = (nd, dist[z][1] + (to,))
                    heapq.heappush(pq, (nd, to))
        self._dist_cache[cache_key] = dist
        return dist

    # objetos "utiles" que el robot aun puede recoger
    def _available_here(self, s: State) -> list[str]:
        out: list[str] = []
        zone = s.zone
        for k, z in s.ground_keys:
            if z == zone:
                out.append(k)
        for t, z in s.ground_tools:
            if z == zone:
                out.append(t)
        for mt, z, n in s.ground_materials:
            if z == zone and n > 0:
                if s.payload.count(mt) < material_demand(self.w, mt, s.panels_ok):
                    out.append(mt)
        return out

  
    def _apply_pickup(self, s: State, token: str) -> State:
        gk, gt, gm = s.ground_keys, s.ground_tools, s.ground_materials
        kind = self.w.kind_of(token)
        if kind == "key":
            gk = tuple(e for e in gk if e[0] != token)
        elif kind == "tool":
            gt = tuple(e for e in gt if e[0] != token)
        else:
            gm = tuple(
                (mt, z, n - 1 if (mt == token and z == s.zone) else n)
                for mt, z, n in gm
                if not (mt == token and z == s.zone and n - 1 <= 0)
            )
        return State(
            s.zone,
            s.battery,
            _insert_sorted(s.payload, token),
            gk,
            gt,
            gm,
            s.doors_open,
            s.panels_ok,
            s.stations_online,
        )

    def _apply_drop(self, s: State, token: str) -> State:
        gk, gt, gm = s.ground_keys, s.ground_tools, s.ground_materials
        kind = self.w.kind_of(token)
        # un objeto "muerto" no vuelve al estado: en el suelo ya no habilita
        # ninguna accion futura y solo generaria movimientos inutiles
        if not self._is_dead(s, token):
            if kind == "key":
                gk = _insert_sorted(gk, (token, s.zone))
            elif kind == "tool":
                gt = _insert_sorted(gt, (token, s.zone))
            elif any(mt == token and z == s.zone for mt, z, _ in gm):
                gm = tuple(
                    (mt, z, n + 1 if (mt == token and z == s.zone) else n)
                    for mt, z, n in gm
                )
            else:
                gm = _insert_sorted(gm, (token, s.zone, 1))
        rest = list(s.payload)
        rest.remove(token)
        return State(
            s.zone,
            s.battery,
            tuple(rest),
            gk,
            gt,
            gm,
            s.doors_open,
            s.panels_ok,
            s.stations_online,
        )

    def _useful_zones(self, s: State) -> set[str]:
        w = self.w
        out: set[str] = set()
        for _k, z in s.ground_keys:
            out.add(z)
        for _t, z in s.ground_tools:
            out.add(z)
        for _mt, z, _n in s.ground_materials:
            out.add(z)
        for pid in w.needed_panels:
            if pid not in s.panels_ok:
                out.add(w.panels[pid]["zone"])
        for sid in w.needed_stations:
            if sid not in s.stations_online:
                out.add(w.stations[sid]["zone"])
        if s.battery < w.battery_max:
            out.update(w.charger_in_zone)
            out.update(z for z, v in w.zones.items() if v.get("recharge"))
        for did, door in w.doors.items():
            if did not in s.doors_open and door["key"] in s.payload:
                out.update(door["between"])
        return out

    def _is_dead(self, s: State, token: str) -> bool:
        w = self.w
        kind = w.kind_of(token)
        if kind == "key":
            door = w.door_of_key.get(token)
            return door is None or door in s.doors_open
        if kind == "tool":
            return not tool_is_live(w, token, s.panels_ok)
        return s.payload.count(token) > material_demand(w, token, s.panels_ok)

 
    def successors(self, s: State) -> list[tuple[Action, State]]:
        w = self.w
        out: list[tuple[Action, State]] = []
        load = payload_weight(w, s.payload)
        open_doors = set(s.doors_open)

        
        if self.macro_moves:
            useful = self._useful_zones(s)
            for to, (cost, path) in self._shortest_paths(s.zone, s.doors_open).items():
                if to == s.zone or cost > s.battery:
                    continue
                # PODA: viajar hasta una zona donde no se puede hacer NADA es
                # inutil. Como el macro-movimiento usa distancias minimas y
                # estas cumplen la desigualdad triangular, parar en una zona
                # muerta nunca abarata el viaje siguiente.
                if to not in useful:
                    continue
                out.append(
                    (
                        Action("MOVE", to, cost, path=path),
                        State(
                            to,
                            s.battery - cost,
                            s.payload,
                            s.ground_keys,
                            s.ground_tools,
                            s.ground_materials,
                            s.doors_open,
                            s.panels_ok,
                            s.stations_online,
                        ),
                    )
                )
        else:
            for to, cost, door in w.adj.get(s.zone, []):
                if (door is not None and door not in open_doors) or s.battery < cost:
                    continue
                out.append(
                    (
                        Action("MOVE", to, cost, path=(s.zone, to)),
                        State(
                            to,
                            s.battery - cost,
                            s.payload,
                            s.ground_keys,
                            s.ground_tools,
                            s.ground_materials,
                            s.doors_open,
                            s.panels_ok,
                            s.stations_online,
                        ),
                    )
                )

        available = self._available_here(s)

        
        if s.battery >= w.cost_pickup:
            for token in available:
                if load + w.weight_of(token) > w.capacity:
                    continue
                st = self._apply_pickup(s, token)
                out.append(
                    (
                        Action("PICKUP", token, w.cost_pickup),
                        State(
                            st.zone,
                            s.battery - w.cost_pickup,
                            st.payload,
                            st.ground_keys,
                            st.ground_tools,
                            st.ground_materials,
                            st.doors_open,
                            st.panels_ok,
                            st.stations_online,
                        ),
                    )
                )

   
        blocked = [y for y in available if load + w.weight_of(y) > w.capacity]
        if blocked and s.payload and s.battery >= w.cost_drop + w.cost_pickup:
            for x in sorted(set(s.payload)):
                wx = w.weight_of(x)
                for y in blocked:
                    if y == x or load - wx + w.weight_of(y) > w.capacity:
                        continue
                    st = self._apply_drop(s, x)
                    st = self._apply_pickup(st, y)
                    out.append(
                        (
                            Action(
                                "SWAP",
                                x,
                                w.cost_drop + w.cost_pickup,
                                extra=y,
                            ),
                            State(
                                st.zone,
                                s.battery - w.cost_drop - w.cost_pickup,
                                st.payload,
                                st.ground_keys,
                                st.ground_tools,
                                st.ground_materials,
                                st.doors_open,
                                st.panels_ok,
                                st.stations_online,
                            ),
                        )
                    )
        # Caso general (pesos > 1): si NINGUN objeto por si solo deja espacio
        # suficiente, hace falta soltar varios. Ahi si se genera un DROP suelto.
        if blocked and s.payload and s.battery >= w.cost_drop:
            need_multi = [
                y
                for y in blocked
                if all(
                    load - w.weight_of(x) + w.weight_of(y) > w.capacity
                    for x in set(s.payload)
                    if x != y
                )
            ]
            if need_multi:
                for x in sorted(set(s.payload)):
                    st = self._apply_drop(s, x)
                    out.append(
                        (
                            Action("DROP", x, w.cost_drop),
                            State(
                                st.zone,
                                s.battery - w.cost_drop,
                                st.payload,
                                st.ground_keys,
                                st.ground_tools,
                                st.ground_materials,
                                st.doors_open,
                                st.panels_ok,
                                st.stations_online,
                            ),
                        )
                    )

        # OPEN_DOOR
        if s.battery >= w.cost_interact:
            for did in w.doors_by_zone.get(s.zone, []):
                if did in open_doors or w.doors[did]["key"] not in s.payload:
                    continue
                out.append(
                    (
                        Action("OPEN_DOOR", did, w.cost_interact),
                        prune_dead(
                            w,
                            State(
                                s.zone,
                                s.battery - w.cost_interact,
                                s.payload,
                                s.ground_keys,
                                s.ground_tools,
                                s.ground_materials,
                                _insert_sorted(s.doors_open, did),
                                s.panels_ok,
                                s.stations_online,
                            ),
                        ),
                    )
                )

        # REPAIR
        if s.battery >= w.cost_interact:
            for pid in w.panels_by_zone.get(s.zone, []):
                if pid not in w.needed_panels or pid in s.panels_ok:
                    continue
                req = w.panels[pid]["requires"]
                if req["tool"] not in s.payload or req["material"] not in s.payload:
                    continue
                rest = list(s.payload)
                rest.remove(req["material"])  # el material SE CONSUME
                out.append(
                    (
                        Action("REPAIR", pid, w.cost_interact, extra=req["material"]),
                        prune_dead(
                            w,
                            State(
                                s.zone,
                                s.battery - w.cost_interact,
                                tuple(rest),
                                s.ground_keys,
                                s.ground_tools,
                                s.ground_materials,
                                s.doors_open,
                                _insert_sorted(s.panels_ok, pid),
                                s.stations_online,
                            ),
                        ),
                    )
                )

        # ACTIVATE 
        if s.battery >= w.cost_interact:
            online = set(s.stations_online)
            ok_panels = set(s.panels_ok)
            for sid in w.stations_by_zone.get(s.zone, []):
                if sid not in w.needed_stations or sid in online:
                    continue
                req = w.stations[sid]["requires"]
                if not all(p in ok_panels for p in req.get("panels_ok", [])):
                    continue
                if not all(x in online for x in req.get("stations_online", [])):
                    continue
                out.append(
                    (
                        Action("ACTIVATE", sid, w.cost_interact),
                        State(
                            s.zone,
                            s.battery - w.cost_interact,
                            s.payload,
                            s.ground_keys,
                            s.ground_tools,
                            s.ground_materials,
                            s.doors_open,
                            s.panels_ok,
                            _insert_sorted(s.stations_online, sid),
                        ),
                    )
                )

        # RECHARGE 
        target = w.recharge_target(s.zone)
        if (
            target is not None
            and s.battery < w.battery_max
            and s.battery >= w.cost_recharge
        ):
            out.append(
                (
                    Action("RECHARGE", target, w.cost_recharge),
                    State(
                        s.zone,
                        w.battery_max,  # el costo se paga ANTES de recargar
                        s.payload,
                        s.ground_keys,
                        s.ground_tools,
                        s.ground_materials,
                        s.doors_open,
                        s.panels_ok,
                        s.stations_online,
                    ),
                )
            )

        return out