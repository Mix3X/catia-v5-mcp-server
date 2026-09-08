"""Sketcher tools for CATIA V5.

2D sketch creation and editing: lines, circles, rectangles, arcs, splines, constraints.
All dimensions are in millimeters. CATIA COM API uses millimeters natively.
"""

from __future__ import annotations

import json
from typing import Any

from catia_mcp.connection import CATIAConnection

# Plane name mapping
PLANE_MAP = {
    "xy": "PlaneXY",
    "yz": "PlaneYZ",
    "zx": "PlaneZX",
    "xz": "PlaneZX",  # alias
}


class SketcherTools:
    """Tools for 2D sketch operations in CATIA V5."""

    def __init__(self, connection: CATIAConnection) -> None:
        self.conn = connection
        self._active_sketch: Any | None = None
        self._active_factory: Any | None = None
        # Cache of typed 2D geometry objects returned by factory.Create*.
        # Needed because Sketch.GeometricElements.Item(i) returns a generic
        # GeometricElement wrapper whose Reference is rejected by AddBiEltCst.
        self._sketch_geometry: list[Any] = []

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "catia_create_sketch",
                "description": (
                    "Create a new 2D sketch on a reference plane (xy, yz, or zx). "
                    "The sketch is opened for editing. You must close it with catia_close_sketch "
                    "before creating 3D features."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "plane": {
                            "type": "string",
                            "description": "Reference plane: 'xy' (front), 'yz' (right), 'zx' (top)",
                            "enum": ["xy", "yz", "zx"],
                            "default": "xy",
                        },
                    },
                },
            },
            {
                "name": "catia_create_sketch_on_plane",
                "description": (
                    "Create a new 2D sketch on a named reference plane (e.g. an offset "
                    "plane created with catia_create_plane_offset). For canonical planes "
                    "use catia_create_sketch with 'xy'/'yz'/'zx' instead. The sketch is "
                    "opened for editing; close it with catia_close_sketch before applying "
                    "3D features."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "plane_name": {
                            "type": "string",
                            "description": (
                                "Name of an existing reference plane (e.g. 'Plane.1' or a "
                                "custom name)."
                            ),
                        },
                    },
                    "required": ["plane_name"],
                },
            },
            {
                "name": "catia_edit_sketch",
                "description": (
                    "Open an EXISTING sketch by name for editing (activates it as the "
                    "current sketch). Use to add constraints or geometry to a sketch that "
                    "already exists in the part. The geometry cache is rebuilt from the "
                    "sketch's existing elements so catia_sketch_constraint can reference "
                    "them by index. Close with catia_close_sketch when done."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "sketch_name": {
                            "type": "string",
                            "description": "Name of the existing sketch (e.g. 'Sketch_Sep').",
                        },
                    },
                    "required": ["sketch_name"],
                },
            },
            {
                "name": "catia_close_sketch",
                "description": (
                    "Close the active sketch and return to Part Design. "
                    "Must be called after finishing sketch geometry before applying 3D features."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "catia_sketch_line",
                "description": (
                    "Draw a line in the active sketch from (x1, y1) to (x2, y2). "
                    "Coordinates in mm."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "x1": {"type": "number", "description": "Start X coordinate (mm)"},
                        "y1": {"type": "number", "description": "Start Y coordinate (mm)"},
                        "x2": {"type": "number", "description": "End X coordinate (mm)"},
                        "y2": {"type": "number", "description": "End Y coordinate (mm)"},
                    },
                    "required": ["x1", "y1", "x2", "y2"],
                },
            },
            {
                "name": "catia_sketch_rectangle",
                "description": (
                    "Draw a rectangle in the active sketch defined by two opposite corners. "
                    "Creates 4 lines forming a closed profile. Coordinates in mm."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "x1": {"type": "number", "description": "First corner X (mm)"},
                        "y1": {"type": "number", "description": "First corner Y (mm)"},
                        "x2": {"type": "number", "description": "Opposite corner X (mm)"},
                        "y2": {"type": "number", "description": "Opposite corner Y (mm)"},
                    },
                    "required": ["x1", "y1", "x2", "y2"],
                },
            },
            {
                "name": "catia_sketch_centered_rectangle",
                "description": (
                    "Draw a rectangle centered at (cx, cy) with given width and height. "
                    "Coordinates and dimensions in mm."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "cx": {"type": "number", "description": "Center X (mm)", "default": 0},
                        "cy": {"type": "number", "description": "Center Y (mm)", "default": 0},
                        "width": {"type": "number", "description": "Width in mm"},
                        "height": {"type": "number", "description": "Height in mm"},
                    },
                    "required": ["width", "height"],
                },
            },
            {
                "name": "catia_sketch_circle",
                "description": "Draw a circle in the active sketch. Coordinates and radius in mm.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "cx": {"type": "number", "description": "Center X (mm)", "default": 0},
                        "cy": {"type": "number", "description": "Center Y (mm)", "default": 0},
                        "radius": {"type": "number", "description": "Radius in mm"},
                    },
                    "required": ["radius"],
                },
            },
            {
                "name": "catia_sketch_arc",
                "description": (
                    "Draw a circular arc defined by center, radius, and start/end angles (degrees). "
                    "Angles are measured counter-clockwise from the positive X axis."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "cx": {"type": "number", "description": "Center X (mm)"},
                        "cy": {"type": "number", "description": "Center Y (mm)"},
                        "radius": {"type": "number", "description": "Radius (mm)"},
                        "start_angle": {"type": "number", "description": "Start angle (degrees)"},
                        "end_angle": {"type": "number", "description": "End angle (degrees)"},
                    },
                    "required": ["cx", "cy", "radius", "start_angle", "end_angle"],
                },
            },
            {
                "name": "catia_sketch_spline",
                "description": (
                    "Draw a spline through a list of control points. "
                    "Each point is [x, y] in mm."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "points": {
                            "type": "array",
                            "items": {
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 2,
                                "maxItems": 2,
                            },
                            "description": "List of [x, y] control points in mm",
                            "minItems": 2,
                        },
                        "closed": {
                            "type": "boolean",
                            "description": "Whether to close the spline (default: false)",
                            "default": False,
                        },
                    },
                    "required": ["points"],
                },
            },
            {
                "name": "catia_sketch_point",
                "description": "Create a point in the active sketch. Coordinates in mm.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "number", "description": "X coordinate (mm)"},
                        "y": {"type": "number", "description": "Y coordinate (mm)"},
                    },
                    "required": ["x", "y"],
                },
            },
            {
                "name": "catia_sketch_constraint",
                "description": (
                    "Add a dimensional constraint to the active sketch. "
                    "Supported types: distance, radius, angle, coincidence, tangent, "
                    "perpendicular, parallel, horizontal, vertical, fix."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": "Constraint type",
                            "enum": [
                                "distance", "radius", "angle",
                                "coincidence", "tangent", "perpendicular",
                                "parallel", "horizontal", "vertical", "fix",
                            ],
                        },
                        "value": {
                            "type": "number",
                            "description": "Constraint value (mm or degrees). Required for distance, radius, angle.",
                        },
                        "geometry_index_1": {
                            "type": "integer",
                            "description": "Index of first geometry element (1-based, from sketch geometry list)",
                        },
                        "geometry_index_2": {
                            "type": "integer",
                            "description": "Index of second geometry element (for relational constraints)",
                        },
                    },
                    "required": ["type"],
                },
            },
            {
                "name": "catia_sketch_get_geometry",
                "description": "List all geometry elements in the active sketch with their indices and types.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> str:
        match tool_name:
            case "catia_create_sketch":
                return self._create_sketch(arguments.get("plane", "xy"))
            case "catia_create_sketch_on_plane":
                return self._create_sketch_on_named_plane(arguments["plane_name"])
            case "catia_edit_sketch":
                return self._edit_sketch(arguments["sketch_name"])
            case "catia_close_sketch":
                return self._close_sketch()
            case "catia_sketch_line":
                return self._draw_line(
                    arguments["x1"], arguments["y1"],
                    arguments["x2"], arguments["y2"],
                )
            case "catia_sketch_rectangle":
                return self._draw_rectangle(
                    arguments["x1"], arguments["y1"],
                    arguments["x2"], arguments["y2"],
                )
            case "catia_sketch_centered_rectangle":
                return self._draw_centered_rectangle(
                    arguments.get("cx", 0), arguments.get("cy", 0),
                    arguments["width"], arguments["height"],
                )
            case "catia_sketch_circle":
                return self._draw_circle(
                    arguments.get("cx", 0), arguments.get("cy", 0),
                    arguments["radius"],
                )
            case "catia_sketch_arc":
                return self._draw_arc(
                    arguments["cx"], arguments["cy"], arguments["radius"],
                    arguments["start_angle"], arguments["end_angle"],
                )
            case "catia_sketch_spline":
                return self._draw_spline(
                    arguments["points"], arguments.get("closed", False),
                )
            case "catia_sketch_point":
                return self._draw_point(arguments["x"], arguments["y"])
            case "catia_sketch_constraint":
                return self._add_constraint(arguments)
            case "catia_sketch_get_geometry":
                return self._get_geometry()
            case _:
                raise ValueError(f"Unknown sketcher tool: {tool_name}")

    def _ensure_sketch_open(self) -> None:
        if self._active_sketch is None:
            raise RuntimeError(
                "No active sketch. Use catia_create_sketch first to open a sketch."
            )

    def _create_sketch(self, plane: str = "xy") -> str:
        self.conn.ensure_connected()
        part = self.conn.get_active_part()
        body = self.conn.get_active_part_body()

        # Get the reference plane
        origin = part.OriginElements
        plane_key = plane.lower()
        if plane_key not in PLANE_MAP:
            raise ValueError(f"Unknown plane '{plane}'. Use 'xy', 'yz', or 'zx'.")

        plane_attr = PLANE_MAP[plane_key]
        ref_plane = getattr(origin, plane_attr)
        ref = part.CreateReferenceFromObject(ref_plane)

        # Create the sketch on the plane
        sketches = body.Sketches
        sketch = sketches.Add(ref)

        # Open the sketch for editing
        self._active_sketch = sketch
        self._active_factory = sketch.OpenEdition()
        self._sketch_geometry = []

        plane_names = {"xy": "XY (front)", "yz": "YZ (right)", "zx": "ZX (top)"}
        return f"Sketch created on {plane_names.get(plane_key, plane)} plane. Ready for geometry."

    def _create_sketch_on_named_plane(self, plane_name: str) -> str:
        self.conn.ensure_connected()
        part = self.conn.get_active_part()
        body = self.conn.get_active_part_body()

        # Search hybrid bodies for the named plane
        plane_shape = None
        hbs = part.HybridBodies
        for i in range(1, hbs.Count + 1):
            hb = hbs.Item(i)
            shapes = hb.HybridShapes
            for j in range(1, shapes.Count + 1):
                s = shapes.Item(j)
                if s.Name == plane_name:
                    plane_shape = s
                    break
            if plane_shape is not None:
                break

        if plane_shape is None:
            raise RuntimeError(
                f"Plane '{plane_name}' not found in any geometrical set. "
                "Create it with catia_create_plane_offset first."
            )

        ref = part.CreateReferenceFromObject(plane_shape)
        sketch = body.Sketches.Add(ref)

        self._active_sketch = sketch
        self._active_factory = sketch.OpenEdition()
        self._sketch_geometry = []
        return f"Sketch created on plane '{plane_name}'. Ready for geometry."

    def _edit_sketch(self, sketch_name: str) -> str:
        self.conn.ensure_connected()
        part = self.conn.get_active_part()

        # Search every body for a sketch matching the given name.
        sketch = None
        bodies = part.Bodies
        for i in range(1, bodies.Count + 1):
            sketches = bodies.Item(i).Sketches
            for j in range(1, sketches.Count + 1):
                s = sketches.Item(j)
                if s.Name == sketch_name:
                    sketch = s
                    break
            if sketch is not None:
                break

        if sketch is None:
            raise RuntimeError(
                f"Sketch '{sketch_name}' not found in any body of the active part."
            )

        self._active_sketch = sketch
        self._active_factory = sketch.OpenEdition()

        # Rebuild the geometry cache from the sketch's existing elements.
        # GeometricElements index 1 is the AbsoluteAxis; user geometry starts at 2.
        # The cache holds user geometry only (cache[0] == GeometricElements.Item(2)),
        # matching the `cache_idx = idx - 2` convention used by _add_constraint.
        self._sketch_geometry = []
        geom = sketch.GeometricElements
        for i in range(2, geom.Count + 1):
            self._sketch_geometry.append(geom.Item(i))

        return (
            f"Sketch '{sketch_name}' opened for editing "
            f"({geom.Count} geometry elements). "
            "Use catia_sketch_get_geometry to list them, then add constraints. "
            "Close with catia_close_sketch."
        )

    def _close_sketch(self) -> str:
        self._ensure_sketch_open()
        sketch = self._active_sketch
        sketch.CloseEdition()
        self.conn.get_active_part().UpdateObject(sketch)
        self._active_sketch = None
        self._active_factory = None
        self._sketch_geometry = []
        self.conn.refresh_display()
        return "Sketch closed. You can now apply Part Design features (pad, pocket, etc.)."

    def _draw_line(self, x1: float, y1: float, x2: float, y2: float) -> str:
        self._ensure_sketch_open()
        factory = self._active_factory
        line = factory.CreateLine(x1, y1, x2, y2)
        self._sketch_geometry.append(line)
        return f"Line created from ({x1}, {y1}) to ({x2}, {y2}) mm"

    def _draw_rectangle(self, x1: float, y1: float, x2: float, y2: float) -> str:
        self._ensure_sketch_open()
        factory = self._active_factory
        part = self.conn.get_active_part()
        constraints = self._active_sketch.Constraints

        # Create 4 lines forming a closed rectangle
        l1 = factory.CreateLine(x1, y1, x2, y1)  # bottom
        l2 = factory.CreateLine(x2, y1, x2, y2)  # right
        l3 = factory.CreateLine(x2, y2, x1, y2)  # top
        l4 = factory.CreateLine(x1, y2, x1, y1)  # left

        self._sketch_geometry.extend([l1, l2, l3, l4])

        # Helper to add coincidence
        def add_coincidence(elem1, elem2):
            ref1 = part.CreateReferenceFromObject(elem1)
            ref2 = part.CreateReferenceFromObject(elem2)
            cst = constraints.AddBiEltCst(2, ref1, ref2) # 2 = catCstTypeOn
            cst.Mode = 1 # catCstModeDriving

        # Connect the lines at corners
        add_coincidence(l1.EndPoint, l2.StartPoint)
        add_coincidence(l2.EndPoint, l3.StartPoint)
        add_coincidence(l3.EndPoint, l4.StartPoint)
        add_coincidence(l4.EndPoint, l1.StartPoint)
        
        # Add horizontal/vertical constraints
        constraints.AddMonoEltCst(8, part.CreateReferenceFromObject(l1)) # 8 = catCstTypeHorizontality
        constraints.AddMonoEltCst(9, part.CreateReferenceFromObject(l2)) # 9 = catCstTypeVerticality
        constraints.AddMonoEltCst(8, part.CreateReferenceFromObject(l3))
        constraints.AddMonoEltCst(9, part.CreateReferenceFromObject(l4))

        return (
            f"Rectangle created from ({x1}, {y1}) to ({x2}, {y2}) mm "
            f"[{abs(x2-x1):.1f} x {abs(y2-y1):.1f} mm] with constraints"
        )

    def _draw_centered_rectangle(
        self, cx: float, cy: float, width: float, height: float
    ) -> str:
        hw, hh = width / 2, height / 2
        return self._draw_rectangle(cx - hw, cy - hh, cx + hw, cy + hh)

    def _draw_circle(self, cx: float, cy: float, radius: float) -> str:
        self._ensure_sketch_open()
        factory = self._active_factory
        circle = factory.CreateClosedCircle(cx, cy, radius)
        self._sketch_geometry.append(circle)
        return f"Circle created at ({cx}, {cy}) with radius {radius} mm"

    def _draw_arc(
        self, cx: float, cy: float, radius: float,
        start_angle: float, end_angle: float,
    ) -> str:
        self._ensure_sketch_open()
        factory = self._active_factory
        import math
        # CATIA CreateArc expects angles in radians
        start_rad = math.radians(start_angle)
        end_rad = math.radians(end_angle)
        arc = factory.CreateArc(cx, cy, radius, start_rad, end_rad)
        self._sketch_geometry.append(arc)
        return (
            f"Arc created at ({cx}, {cy}), radius={radius} mm, "
            f"from {start_angle}° to {end_angle}°"
        )

    def _draw_spline(self, points: list[list[float]], closed: bool = False) -> str:
        self._ensure_sketch_open()
        factory = self._active_factory

        # Create a spline using control points
        # CATIA V5 Sketch.OpenEdition() returns a Factory2D
        # Factory2D.CreateSpline expects an array of 2D points
        spline_pts = []
        for pt in points:
            ctrl_pt = factory.CreatePoint(pt[0], pt[1])
            self._sketch_geometry.append(ctrl_pt)
            spline_pts.append(ctrl_pt)

        spline = factory.CreateSpline(spline_pts)
        self._sketch_geometry.append(spline)

        if closed and len(points) >= 3:
            # Close the spline by adding a line from last to first point
            closing_line = factory.CreateLine(
                points[-1][0], points[-1][1], points[0][0], points[0][1]
            )
            self._sketch_geometry.append(closing_line)

        pts_str = ", ".join(f"({p[0]}, {p[1]})" for p in points)
        return f"Spline created through {len(points)} points: {pts_str}" + (
            " (closed)" if closed else ""
        )

    def _draw_point(self, x: float, y: float) -> str:
        self._ensure_sketch_open()
        factory = self._active_factory
        point = factory.CreatePoint(x, y)
        self._sketch_geometry.append(point)
        return f"Point created at ({x}, {y}) mm"

    def _add_constraint(self, args: dict[str, Any]) -> str:
        self._ensure_sketch_open()
        sketch = self._active_sketch
        constraint_type = args["type"]
        value = args.get("value")
        idx1 = args.get("geometry_index_1")
        idx2 = args.get("geometry_index_2")

        constraints = sketch.Constraints
        geom = sketch.GeometricElements
        part = self.conn.get_active_part()
        selection = self.conn.hso

        def make_ref(idx: int):
            # Index 1 in GeometricElements is the AbsoluteAxis; user geometry starts at 2.
            # The cache holds the typed 2D dispatch objects (Line2D, Circle2D, ...) that
            # factory.Create* returned — those produce References that AddBiEltCst accepts.
            cache_idx = idx - 2
            elem = None
            if 0 <= cache_idx < len(self._sketch_geometry):
                elem = self._sketch_geometry[cache_idx]
            if elem is None:
                # Fallback for geometry created before the cache existed (e.g. reload mid-sketch).
                elem = geom.Item(idx)

            try:
                ref = part.CreateReferenceFromObject(elem)
                if ref is not None:
                    return ref
            except Exception:
                pass
            # Last-resort: route through the document Selection. Rarely needed once the
            # cache is populated, but kept for robustness on edge cases.
            selection.Clear()
            try:
                selection.Add(elem)
                if selection.Count == 0:
                    raise RuntimeError(
                        f"Selection.Add returned empty for sketch element index {idx} "
                        f"(name={getattr(elem, 'Name', '?')})."
                    )
                ref = selection.Item(1).Reference
            finally:
                selection.Clear()
            return ref

        # Dimensional constraints (need a geometry reference + value)
        if constraint_type in ("distance", "radius", "angle"):
            if value is None:
                raise ValueError(f"Constraint type '{constraint_type}' requires a 'value' parameter.")
            if idx1 is None:
                raise ValueError(f"Constraint type '{constraint_type}' requires 'geometry_index_1'.")

            ref1 = make_ref(idx1)

            if constraint_type == "distance" and idx2 is not None:
                ref2 = make_ref(idx2)
                cst = constraints.AddBiEltCst(1, ref1, ref2)  # catCstTypeDistance
                cst.Dimension.Value = value
            elif constraint_type == "distance":
                cst = constraints.AddMonoEltCst(5, ref1)  # catCstTypeLength
                cst.Dimension.Value = value
            elif constraint_type == "radius":
                cst = constraints.AddMonoEltCst(12, ref1)  # catCstTypeRadius
                cst.Dimension.Value = value
            elif constraint_type == "angle":
                if idx2 is None:
                    raise ValueError("Angle constraint requires 'geometry_index_2'.")
                ref2 = make_ref(idx2)
                cst = constraints.AddBiEltCst(10, ref1, ref2)  # catCstTypeAngle
                cst.Dimension.Value = value

            return f"{constraint_type.capitalize()} constraint added: {value} {'mm' if constraint_type != 'angle' else '°'}"

        # Geometric constraints (no value needed)
        cst_type_map = {
            "coincidence": 2,   # catCstTypeOn
            "tangent": 4,       # catCstTypeTangency
            "perpendicular": 7, # catCstTypePerpendicularity
            "parallel": 6,      # catCstTypeParallelism
            "horizontal": 8,    # catCstTypeHorizontality
            "vertical": 9,      # catCstTypeVerticality
            "fix": 18,          # catCstTypeFix
        }

        cst_code = cst_type_map.get(constraint_type)
        if cst_code is None:
            raise ValueError(f"Unknown constraint type: {constraint_type}")

        if constraint_type in ("horizontal", "vertical", "fix"):
            if idx1 is None:
                raise ValueError(f"Constraint '{constraint_type}' requires 'geometry_index_1'.")
            ref1 = make_ref(idx1)
            constraints.AddMonoEltCst(cst_code, ref1)
        else:
            if idx1 is None or idx2 is None:
                raise ValueError(
                    f"Constraint '{constraint_type}' requires both 'geometry_index_1' and 'geometry_index_2'."
                )
            ref1 = make_ref(idx1)
            ref2 = make_ref(idx2)
            constraints.AddBiEltCst(cst_code, ref1, ref2)

        return f"{constraint_type.capitalize()} constraint added"

    def _get_geometry(self) -> str:
        self._ensure_sketch_open()
        sketch = self._active_sketch
        geom = sketch.GeometricElements

        elements = []
        for i in range(1, geom.Count + 1):
            elem = geom.Item(i)
            info = {
                "index": i,
                "name": elem.Name,
            }
            # Try to get the geometry type
            try:
                info["type"] = elem.GeometricType
            except Exception:
                pass
            elements.append(info)

        if not elements:
            return "No geometry elements in the active sketch"
        return json.dumps(elements, indent=2)
