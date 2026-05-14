"""Reference geometry tools for CATIA V5.

Creation of construction geometry: offset planes, geometrical sets.
These references are used as sketch supports for features that cannot
be built on the canonical XY/YZ/ZX planes alone.
"""

from __future__ import annotations

import json
from typing import Any

from catia_mcp.connection import CATIAConnection

# Map shorthand to canonical-plane attribute names
_BASE_PLANES = {
    "xy": "PlaneXY",
    "yz": "PlaneYZ",
    "zx": "PlaneZX",
    "xz": "PlaneZX",
}


class ReferenceTools:
    """Construction geometry: planes, axes, geometrical sets."""

    def __init__(self, connection: CATIAConnection) -> None:
        self.conn = connection

    # ── Tool definitions ────────────────────────────────────────────

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "catia_create_geometrical_set",
                "description": (
                    "Create a Geometrical Set (HybridBody) in the active Part. Construction "
                    "geometry such as offset planes is stored inside a geometrical set."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Optional name. Defaults to 'Geometrical Set.N'.",
                        },
                    },
                },
            },
            {
                "name": "catia_create_plane_offset",
                "description": (
                    "Create a reference plane parallel to an existing plane at a given offset. "
                    "Reference can be a base plane ('xy', 'yz', 'zx') or the name of any "
                    "existing plane in a geometrical set. The new plane is stored in a "
                    "geometrical set (auto-created if none exists) and named. Returns the "
                    "plane name. Use it as 'plane_name' in catia_create_sketch_on_plane."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "reference": {
                            "type": "string",
                            "description": (
                                "Reference plane. 'xy', 'yz', 'zx' for canonical planes, "
                                "or the name of an existing plane (e.g. 'Plane.1')."
                            ),
                        },
                        "offset": {
                            "type": "number",
                            "description": "Offset distance in mm (signed).",
                        },
                        "reverse": {
                            "type": "boolean",
                            "description": (
                                "Reverse direction of offset (default: false). "
                                "If true, plane is offset in the opposite normal direction."
                            ),
                            "default": False,
                        },
                        "name": {
                            "type": "string",
                            "description": "Optional name for the new plane.",
                        },
                        "set_name": {
                            "type": "string",
                            "description": (
                                "Optional geometrical set to store the plane in. "
                                "Defaults to first existing set or new one."
                            ),
                        },
                    },
                    "required": ["reference", "offset"],
                },
            },
            {
                "name": "catia_list_planes",
                "description": (
                    "List all reference planes in the Part: canonical (xy, yz, zx) plus "
                    "any planes stored in geometrical sets, with their names."
                ),
                "inputSchema": {"type": "object", "properties": {}},
            },
        ]

    # ── Dispatch ────────────────────────────────────────────────────

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> str:
        match tool_name:
            case "catia_create_geometrical_set":
                return self._create_geometrical_set(arguments)
            case "catia_create_plane_offset":
                return self._create_plane_offset(arguments)
            case "catia_list_planes":
                return self._list_planes()
            case _:
                raise ValueError(f"Unknown reference tool: {tool_name}")

    # ── Helpers ─────────────────────────────────────────────────────

    def _get_or_create_geomset(self, name: str | None = None) -> Any:
        part = self.conn.get_active_part()
        hbs = part.HybridBodies

        if name:
            for i in range(1, hbs.Count + 1):
                hb = hbs.Item(i)
                if hb.Name == name:
                    return hb
            new_hb = hbs.Add()
            new_hb.Name = name
            return new_hb

        if hbs.Count == 0:
            new_hb = hbs.Add()
            return new_hb
        return hbs.Item(1)

    def _resolve_plane_reference(self, identifier: str) -> Any:
        """Return a Reference to a base plane or named hybrid plane."""
        part = self.conn.get_active_part()
        key = identifier.lower()

        if key in _BASE_PLANES:
            base = getattr(part.OriginElements, _BASE_PLANES[key])
            return part.CreateReferenceFromObject(base)

        # Search hybrid bodies for a plane with that name
        hbs = part.HybridBodies
        for i in range(1, hbs.Count + 1):
            hb = hbs.Item(i)
            shapes = hb.HybridShapes
            for j in range(1, shapes.Count + 1):
                s = shapes.Item(j)
                if s.Name == identifier:
                    return part.CreateReferenceFromObject(s)

        raise RuntimeError(
            f"Plane '{identifier}' not found. Use 'xy'/'yz'/'zx' or the name of "
            "an existing reference plane."
        )

    # ── Tool implementations ────────────────────────────────────────

    def _create_geometrical_set(self, args: dict[str, Any]) -> str:
        self.conn.ensure_connected()
        part = self.conn.get_active_part()
        hb = part.HybridBodies.Add()
        if args.get("name"):
            hb.Name = args["name"]
        part.Update()
        return f"Geometrical set created: '{hb.Name}'"

    def _create_plane_offset(self, args: dict[str, Any]) -> str:
        self.conn.ensure_connected()
        part = self.conn.get_active_part()
        hsf = part.HybridShapeFactory

        ref_id = args["reference"]
        offset = float(args["offset"])
        reverse = bool(args.get("reverse", False))
        plane_name = args.get("name", "")
        set_name = args.get("set_name")

        ref = self._resolve_plane_reference(ref_id)

        # AddNewPlaneOffset(refPlane, offset, orientation_bool)
        plane = hsf.AddNewPlaneOffset(ref, offset, reverse)

        target_set = self._get_or_create_geomset(set_name)
        target_set.AppendHybridShape(plane)

        if plane_name:
            plane.Name = plane_name

        part.InWorkObject = part.MainBody
        part.Update()

        return f"Offset plane created: '{plane.Name}' ({offset} mm from {ref_id})"

    def _list_planes(self) -> str:
        self.conn.ensure_connected()
        part = self.conn.get_active_part()

        result: list[dict[str, Any]] = [
            {"name": "xy", "kind": "canonical"},
            {"name": "yz", "kind": "canonical"},
            {"name": "zx", "kind": "canonical"},
        ]

        hbs = part.HybridBodies
        for i in range(1, hbs.Count + 1):
            hb = hbs.Item(i)
            shapes = hb.HybridShapes
            for j in range(1, shapes.Count + 1):
                s = shapes.Item(j)
                # Heuristic: planes have 'Plane' in their type name
                kind = "unknown"
                try:
                    type_name = type(s).__name__
                    if "Plane" in type_name:
                        kind = "plane"
                except Exception:
                    pass
                result.append({
                    "name": s.Name,
                    "set": hb.Name,
                    "kind": kind,
                })

        return json.dumps(result, indent=2, ensure_ascii=False)
