"""Publication and cross-part reference tools for CATIA V5.

Publications expose geometry from a Part document so it can be referenced
from another Part inside an Assembly (CATProduct). This enables true
parametric cross-part design — when the source geometry moves, downstream
parts that project the publication follow automatically.

Workflow:
  1. In the source Part, call catia_publish_geometry on a sketch element
     (circle, point, line) to create a named publication.
  2. Insert both Parts as components in an Assembly (CATProduct).
  3. With the destination Part active, call
     catia_project_publication_into_sketch from inside an open sketch.
     The tool creates a projected curve referencing the source publication.

Also exposes catia_get_sketch_element_position as a numeric fallback when
parametric linking is overkill — returns the world XYZ coordinates of the
center (Circle) / endpoints (Line) / position (Point) of a sketch element.
"""

from __future__ import annotations

import json
from typing import Any

from catia_mcp.connection import CATIAConnection


class PublicationTools:
    """Cross-part publication and reference tools."""

    def __init__(self, connection: CATIAConnection) -> None:
        self.conn = connection

    # ── Tool definitions ────────────────────────────────────────────

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "catia_publish_geometry",
                "description": (
                    "Publish a geometric element from a sketch in a Part. "
                    "Creates a named entry in the Part's Publications collection that "
                    "can be referenced from another Part in an Assembly. "
                    "Works when active document is the Part itself, or an Assembly "
                    "containing the Part (pass part_name to disambiguate). "
                    "Use catia_project_publication_into_sketch from another Part to "
                    "consume the publication."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "sketch_name": {
                            "type": "string",
                            "description": (
                                "Full name or simple name of the sketch containing the "
                                "element (e.g. 'Sketch_Aimants_v2' or 'Pad.1\\Sketch.1')."
                            ),
                        },
                        "element_index": {
                            "type": "integer",
                            "description": (
                                "1-based index of the geometry element inside the sketch "
                                "as returned by catia_sketch_get_geometry."
                            ),
                        },
                        "publication_name": {
                            "type": "string",
                            "description": "Name of the new publication.",
                        },
                        "part_name": {
                            "type": "string",
                            "description": (
                                "Optional. Required when the active document is an "
                                "Assembly (CATProduct). Name or part number of the "
                                "component whose Part should host the publication "
                                "(e.g. 'Boite_Magic_Corps')."
                            ),
                        },
                    },
                    "required": ["sketch_name", "element_index", "publication_name"],
                },
            },
            {
                "name": "catia_publish_feature",
                "description": (
                    "Publish a whole feature (Pad, Pocket, Sketch, Plane, etc.) from "
                    "a Part. Use this when you want to expose an entire entity "
                    "rather than a sub-element. Works from the Part document or from "
                    "an Assembly (pass part_name)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "feature_name": {
                            "type": "string",
                            "description": (
                                "Name of the feature to publish "
                                "(e.g. 'Sketch_Aimants_v2', 'Plane_Aimants')."
                            ),
                        },
                        "publication_name": {
                            "type": "string",
                            "description": "Name of the new publication.",
                        },
                        "part_name": {
                            "type": "string",
                            "description": (
                                "Optional. Required when the active document is an "
                                "Assembly. Name or part number of the component."
                            ),
                        },
                    },
                    "required": ["feature_name", "publication_name"],
                },
            },
            {
                "name": "catia_list_publications",
                "description": (
                    "List publications with their names and the type of geometry they "
                    "expose. Works from the Part document (lists that part's "
                    "publications) or from an Assembly (lists publications of every "
                    "component, or only part_name if provided)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "part_name": {
                            "type": "string",
                            "description": (
                                "Optional. Restrict listing to a single component "
                                "when the active document is an Assembly."
                            ),
                        },
                    },
                },
            },
            {
                "name": "catia_get_sketch_element_position",
                "description": (
                    "Return the world-coordinate position of a sketch element. "
                    "For a Circle: center (X,Y,Z) and radius. For a Point: (X,Y,Z). "
                    "For a Line: start and end (X,Y,Z). Numeric fallback when a "
                    "parametric publication link is overkill — caller can hard-code "
                    "the same coords in another Part."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "sketch_name": {
                            "type": "string",
                            "description": (
                                "Name of the sketch containing the element "
                                "(e.g. 'Sketch_Aimants_v2')."
                            ),
                        },
                        "element_index": {
                            "type": "integer",
                            "description": "1-based index from catia_sketch_get_geometry.",
                        },
                    },
                    "required": ["sketch_name", "element_index"],
                },
            },
            {
                "name": "catia_project_publication_into_sketch",
                "description": (
                    "Inside the currently open sketch (in the active Part of an "
                    "Assembly), create a projected curve linked to a publication "
                    "from another component. The destination Part must be the "
                    "in-work object of the assembly. Returns the index of the new "
                    "projected element. Requires an open sketch — use "
                    "catia_create_sketch or catia_create_sketch_on_plane first."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "source_component": {
                            "type": "string",
                            "description": (
                                "Name of the source component (assembly child) that "
                                "owns the publication, as it appears in "
                                "catia_list_components."
                            ),
                        },
                        "publication_name": {
                            "type": "string",
                            "description": (
                                "Name of the publication in the source component."
                            ),
                        },
                    },
                    "required": ["source_component", "publication_name"],
                },
            },
        ]

    # ── Dispatch ────────────────────────────────────────────────────

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> str:
        match tool_name:
            case "catia_publish_geometry":
                return self._publish_geometry(arguments)
            case "catia_publish_feature":
                return self._publish_feature(arguments)
            case "catia_list_publications":
                return self._list_publications(arguments)
            case "catia_get_sketch_element_position":
                return self._get_sketch_element_position(arguments)
            case "catia_project_publication_into_sketch":
                return self._project_publication_into_sketch(arguments)
            case _:
                raise ValueError(f"Unknown publication tool: {tool_name}")

    # ── Helpers ─────────────────────────────────────────────────────

    def _resolve_part_context(self, part_name: str | None) -> tuple[Any, Any]:
        """Return (part, part_doc) for the targeted Part.

        Active doc may be either a PartDocument or a ProductDocument.
        When it is a Product, part_name is required to pick the component.
        """
        doc = self.conn.active_document
        # PartDocument exposes .Part directly
        try:
            part = doc.Part
            return part, doc
        except Exception:
            pass

        # Otherwise must be a ProductDocument
        try:
            product = doc.Product
        except Exception as e:
            raise RuntimeError(
                "Active document is neither a Part nor a Product."
            ) from e

        if not part_name:
            raise RuntimeError(
                "Active document is an Assembly. Provide part_name to pick the "
                "component (e.g. 'Boite_Magic_Corps')."
            )

        comps = product.Products
        for i in range(1, comps.Count + 1):
            c = comps.Item(i)
            try:
                if c.Name == part_name or c.PartNumber == part_name:
                    part_doc = c.ReferenceProduct.Parent
                    return part_doc.Part, part_doc
            except Exception:
                continue
        raise RuntimeError(
            f"Component '{part_name}' not found in active assembly."
        )

    def _find_sketch(self, part: Any, sketch_name: str) -> Any:
        """Locate a Sketch by simple or composite name in the active Part."""
        # 1) Direct hit under MainBody.Sketches
        body = part.MainBody
        try:
            return body.Sketches.Item(sketch_name)
        except Exception:
            pass

        # 2) Recursive search through bodies / features / sub-sketches
        def search_in_collection(coll: Any) -> Any:
            try:
                count = coll.Count
            except Exception:
                return None
            for i in range(1, count + 1):
                item = coll.Item(i)
                try:
                    if item.Name == sketch_name:
                        return item
                except Exception:
                    pass
                # Drill into Shapes that hold sub-sketches (e.g. Pad.X\Sketch.N)
                for child_attr in ("Sketches", "Shapes"):
                    child = getattr(item, child_attr, None)
                    if child is None:
                        continue
                    found = search_in_collection(child)
                    if found is not None:
                        return found
            return None

        for collection_name in ("Bodies", "HybridBodies"):
            coll = getattr(part, collection_name, None)
            if coll is None:
                continue
            found = search_in_collection(coll)
            if found is not None:
                return found

        # 3) Walk every body's Shapes collection (consumed sketches live there)
        bodies = part.Bodies
        for i in range(1, bodies.Count + 1):
            b = bodies.Item(i)
            shapes = getattr(b, "Shapes", None)
            if shapes is None:
                continue
            for j in range(1, shapes.Count + 1):
                shape = shapes.Item(j)
                sketches = getattr(shape, "Sketches", None)
                if sketches is None:
                    continue
                try:
                    return sketches.Item(sketch_name)
                except Exception:
                    pass

        raise RuntimeError(f"Sketch '{sketch_name}' not found in active part.")

    def _find_feature(self, part: Any, feature_name: str) -> Any:
        """Locate any named feature (sketch, pad, pocket, plane, ...) in the part."""
        # Bodies
        bodies = part.Bodies
        for i in range(1, bodies.Count + 1):
            b = bodies.Item(i)
            try:
                if b.Name == feature_name:
                    return b
            except Exception:
                pass
            shapes = getattr(b, "Shapes", None)
            if shapes is not None:
                for j in range(1, shapes.Count + 1):
                    s = shapes.Item(j)
                    try:
                        if s.Name == feature_name:
                            return s
                    except Exception:
                        pass
            sketches = getattr(b, "Sketches", None)
            if sketches is not None:
                for j in range(1, sketches.Count + 1):
                    sk = sketches.Item(j)
                    try:
                        if sk.Name == feature_name:
                            return sk
                    except Exception:
                        pass

        # Hybrid bodies (geometrical sets)
        hbs = part.HybridBodies
        for i in range(1, hbs.Count + 1):
            hb = hbs.Item(i)
            try:
                if hb.Name == feature_name:
                    return hb
            except Exception:
                pass
            shapes = hb.HybridShapes
            for j in range(1, shapes.Count + 1):
                s = shapes.Item(j)
                try:
                    if s.Name == feature_name:
                        return s
                except Exception:
                    pass

        raise RuntimeError(f"Feature '{feature_name}' not found in active part.")

    def _sketch_local_to_world(self, sketch: Any, h: float, v: float) -> tuple[float, float, float]:
        """Map sketch-local (H, V) coords to world (X, Y, Z) via sketch axis."""
        axis = sketch.AbsoluteAxis
        origin = [0.0, 0.0, 0.0]
        h_dir = [0.0, 0.0, 0.0]
        v_dir = [0.0, 0.0, 0.0]
        axis.GetOriginPosition(origin)
        axis.GetXAxis(h_dir)
        axis.GetYAxis(v_dir)
        x = origin[0] + h * h_dir[0] + v * v_dir[0]
        y = origin[1] + h * h_dir[1] + v * v_dir[1]
        z = origin[2] + h * h_dir[2] + v * v_dir[2]
        return (round(x, 6), round(y, 6), round(z, 6))

    # ── Tool implementations ────────────────────────────────────────

    def _publish_geometry(self, args: dict[str, Any]) -> str:
        self.conn.ensure_connected()
        part, part_doc = self._resolve_part_context(args.get("part_name"))

        sketch = self._find_sketch(part, args["sketch_name"])
        idx = int(args["element_index"])
        elem = sketch.GeometricElements.Item(idx)

        ref = part.CreateReferenceFromObject(elem)

        pubs = part_doc.Product.Publications
        # If a publication with that name already exists, replace its valuation
        name = args["publication_name"]
        existing = None
        for i in range(1, pubs.Count + 1):
            p = pubs.Item(i)
            if p.Name == name:
                existing = p
                break
        if existing is not None:
            existing.Valuate(ref)
            part.InWorkObject = part.MainBody
            part.Update()
            return f"Publication '{name}' updated → {args['sketch_name']}[{idx}] ({elem.Name})"

        pub = pubs.Add(name)
        pub.Valuate(ref)
        part.InWorkObject = part.MainBody
        part.Update()
        return f"Publication '{name}' created → {args['sketch_name']}[{idx}] ({elem.Name})"

    def _publish_feature(self, args: dict[str, Any]) -> str:
        self.conn.ensure_connected()
        part, part_doc = self._resolve_part_context(args.get("part_name"))

        feat = self._find_feature(part, args["feature_name"])
        ref = part.CreateReferenceFromObject(feat)

        pubs = part_doc.Product.Publications
        name = args["publication_name"]
        for i in range(1, pubs.Count + 1):
            p = pubs.Item(i)
            if p.Name == name:
                p.Valuate(ref)
                part.InWorkObject = part.MainBody
                part.Update()
                return f"Publication '{name}' updated → feature '{args['feature_name']}'"

        pub = pubs.Add(name)
        pub.Valuate(ref)
        part.InWorkObject = part.MainBody
        part.Update()
        return f"Publication '{name}' created → feature '{args['feature_name']}'"

    def _list_publications(self, args: dict[str, Any]) -> str:
        self.conn.ensure_connected()
        part_name = args.get("part_name") if args else None
        doc = self.conn.active_document

        # PartDocument: list its own publications
        try:
            _ = doc.Part
            is_part = True
        except Exception:
            is_part = False

        targets: list[tuple[str, Any]] = []
        if is_part:
            targets.append((doc.Name, doc.Product.Publications))
        else:
            try:
                product = doc.Product
            except Exception as e:
                raise RuntimeError(
                    "Active document is neither a Part nor a Product."
                ) from e
            comps = product.Products
            for i in range(1, comps.Count + 1):
                c = comps.Item(i)
                if part_name and not (
                    c.Name == part_name or c.PartNumber == part_name
                ):
                    continue
                try:
                    part_doc = c.ReferenceProduct.Parent
                    targets.append((c.Name, part_doc.Product.Publications))
                except Exception:
                    continue
            if not targets:
                raise RuntimeError(
                    f"No matching component for part_name='{part_name}'."
                    if part_name
                    else "No part components found in active assembly."
                )

        result: list[dict[str, Any]] = []
        for comp_label, pubs in targets:
            comp_entry: dict[str, Any] = {"component": comp_label, "publications": []}
            for i in range(1, pubs.Count + 1):
                p = pubs.Item(i)
                entry: dict[str, Any] = {"index": i, "name": p.Name}
                try:
                    val = p.Valuation
                    entry["valuation_display"] = (
                        val.DisplayName if hasattr(val, "DisplayName") else "<reference>"
                    )
                except Exception:
                    entry["valuation_display"] = "<unbound>"
                comp_entry["publications"].append(entry)
            result.append(comp_entry)

        empty = all(not c["publications"] for c in result)
        if empty:
            return "No publications found."
        return json.dumps(result, indent=2, ensure_ascii=False)

    def _get_sketch_element_position(self, args: dict[str, Any]) -> str:
        self.conn.ensure_connected()
        part = self.conn.get_active_part()

        sketch = self._find_sketch(part, args["sketch_name"])
        idx = int(args["element_index"])
        elem = sketch.GeometricElements.Item(idx)

        # Try Circle (Geometry2D.Circle has CenterPoint)
        info: dict[str, Any] = {
            "sketch": sketch.Name,
            "element_index": idx,
            "element_name": elem.Name,
        }

        try:
            center = elem.CenterPoint
            coords = [0.0, 0.0]
            center.GetCoordinates(coords)
            wx, wy, wz = self._sketch_local_to_world(sketch, coords[0], coords[1])
            info["type"] = "circle"
            info["center_local"] = {"h": round(coords[0], 6), "v": round(coords[1], 6)}
            info["center_world"] = {"x": wx, "y": wy, "z": wz}
            try:
                info["radius"] = round(elem.Radius, 6)
            except Exception:
                pass
            return json.dumps(info, indent=2, ensure_ascii=False)
        except Exception:
            pass

        # Try Line (Geometry2D.Line has StartPoint / EndPoint)
        try:
            sp = elem.StartPoint
            ep = elem.EndPoint
            sc = [0.0, 0.0]
            ec = [0.0, 0.0]
            sp.GetCoordinates(sc)
            ep.GetCoordinates(ec)
            sx, sy, sz = self._sketch_local_to_world(sketch, sc[0], sc[1])
            ex, ey, ez = self._sketch_local_to_world(sketch, ec[0], ec[1])
            info["type"] = "line"
            info["start_world"] = {"x": sx, "y": sy, "z": sz}
            info["end_world"] = {"x": ex, "y": ey, "z": ez}
            return json.dumps(info, indent=2, ensure_ascii=False)
        except Exception:
            pass

        # Try Point (Geometry2D.Point2D directly)
        try:
            coords = [0.0, 0.0]
            elem.GetCoordinates(coords)
            wx, wy, wz = self._sketch_local_to_world(sketch, coords[0], coords[1])
            info["type"] = "point"
            info["world"] = {"x": wx, "y": wy, "z": wz}
            return json.dumps(info, indent=2, ensure_ascii=False)
        except Exception:
            pass

        info["type"] = "unknown"
        info["note"] = "Element does not expose CenterPoint / Start+End / GetCoordinates."
        return json.dumps(info, indent=2, ensure_ascii=False)

    def _project_publication_into_sketch(self, args: dict[str, Any]) -> str:
        """Project a publication from another component into the active sketch.

        Active document must be a Product (assembly). The sketch must already
        be open (via catia_create_sketch / catia_create_sketch_on_plane on the
        destination part).
        """
        self.conn.ensure_connected()

        # Locate active sketch via the sketcher tool's cached state
        # (avoid circular import — read it through the shared connection container)
        # Use the global Server instance? Instead expose a class-level resolver.
        sketcher = _SHARED.get("sketcher")
        if sketcher is None or sketcher._active_sketch is None or sketcher._active_factory is None:
            raise RuntimeError(
                "No active sketch. Call catia_create_sketch or "
                "catia_create_sketch_on_plane on the destination part first."
            )

        # Active document = assembly
        product = self.conn.get_active_product()

        comp_name = args["source_component"]
        pub_name = args["publication_name"]

        # Find source component in the product tree
        source_comp = None
        comps = product.Products
        for i in range(1, comps.Count + 1):
            c = comps.Item(i)
            if c.Name == comp_name or c.PartNumber == comp_name:
                source_comp = c
                break
        if source_comp is None:
            raise RuntimeError(
                f"Source component '{comp_name}' not found in active assembly."
            )

        # Drill into the underlying Part document of the source component
        try:
            source_part_doc = source_comp.ReferenceProduct.Parent
            source_part = source_part_doc.Part
        except Exception as e:
            raise RuntimeError(
                f"Could not access Part of component '{comp_name}': {e}"
            ) from e

        # Look up the publication in the source part (Publications live on Product, not Part)
        pubs = source_part_doc.Product.Publications
        source_pub = None
        for i in range(1, pubs.Count + 1):
            p = pubs.Item(i)
            if p.Name == pub_name:
                source_pub = p
                break
        if source_pub is None:
            raise RuntimeError(
                f"Publication '{pub_name}' not found in component '{comp_name}'."
            )

        # Build a contextual reference that resolves from the destination part's
        # point of view. CATIA exposes Selection-based copy/paste-with-link as
        # the supported route; here we go through CreateReferenceFromName so
        # the link is created without UI interaction.
        ref_name = f"{source_comp.Name}/!{source_pub.Name}"
        dest_part = self.conn.get_active_part()
        try:
            external_ref = dest_part.CreateReferenceFromName(ref_name)
        except Exception:
            # Fallback: use Valuation directly. Works when both parts share the
            # same in-memory session even without an explicit assembly link.
            external_ref = source_pub.Valuation

        # Insert as projection into the active sketch's Factory2D
        factory_2d = sketcher._active_factory
        try:
            projection = factory_2d.CreateProjection(external_ref)
        except Exception as e:
            raise RuntimeError(
                "Factory2D.CreateProjection failed. The destination part may "
                "need to be the in-work object of the assembly, and the source "
                "publication must resolve in this context. "
                f"Underlying error: {e}"
            ) from e

        # Track the projected element in the sketcher's geometry cache so
        # subsequent constraints can reference it by index.
        sketcher._sketch_geometry.append(projection)
        new_index = len(sketcher._sketch_geometry) + 1  # +1 to account for AbsoluteAxis
        return (
            f"Projection created in active sketch from "
            f"'{comp_name}/!{pub_name}' (sketch element index ~{new_index}). "
            "Add a coincidence/concentricity constraint between your circle "
            "and this projected element to lock parametric position."
        )


# Shared registry so publication tool can reach the sketcher's open-sketch state
# without importing it directly (avoids module-level circular import).
_SHARED: dict[str, Any] = {}


def register_sketcher(sketcher_tools: Any) -> None:
    _SHARED["sketcher"] = sketcher_tools
