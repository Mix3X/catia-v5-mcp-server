"""Knowledge Advisor tools for CATIA V5.

User parameter creation (Integer, Length, Real, Boolean, String),
parameter sets, formulas (relations), and feature renaming.
"""

from __future__ import annotations

import json
from typing import Any

from catia_mcp.connection import CATIAConnection


# Magnitude strings accepted by Parameters.CreateDimension
_MAGNITUDES = {
    "length": "LENGTH",
    "angle": "ANGLE",
    "mass": "MASS",
    "time": "TIME",
    "volume": "VOLUME",
    "area": "AREA",
    "force": "FORCE",
}


class KnowledgeTools:
    """Tools for CATIA Knowledge Advisor: parameters, sets, formulas."""

    def __init__(self, connection: CATIAConnection) -> None:
        self.conn = connection

    # ── Tool definitions ────────────────────────────────────────────

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "catia_create_parameter",
                "description": (
                    "Create a new user parameter in the active Part and expose it in the "
                    "specification tree. Supported types: 'integer', 'length' (mm), 'real', "
                    "'angle' (deg), 'boolean', 'string'. Optionally place inside a parameter "
                    "set with 'set_path' (e.g. 'PARAMETRES_UTILISATEUR'). Returns the full "
                    "parameter name (with path)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Parameter name (no backslashes).",
                        },
                        "type": {
                            "type": "string",
                            "description": "Parameter type",
                            "enum": [
                                "integer", "length", "real", "angle",
                                "boolean", "string",
                            ],
                        },
                        "value": {
                            "description": (
                                "Initial value. number for integer/length/real/angle, "
                                "bool for boolean, string for string."
                            ),
                        },
                        "set_path": {
                            "type": "string",
                            "description": (
                                "Optional parameter set path (e.g. "
                                "'PARAMETRES_UTILISATEUR'). The set must already exist "
                                "(create it first with catia_create_parameter_set)."
                            ),
                        },
                    },
                    "required": ["name", "type", "value"],
                },
            },
            {
                "name": "catia_create_parameter_set",
                "description": (
                    "Create a parameter set (folder) in the active Part's specification tree. "
                    "Parameter sets group user parameters under a named node. "
                    "Use 'parent_path' to nest under another set; omit to place at root."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the new parameter set.",
                        },
                        "parent_path": {
                            "type": "string",
                            "description": (
                                "Optional parent set path. Omit for root-level set."
                            ),
                        },
                    },
                    "required": ["name"],
                },
            },
            {
                "name": "catia_set_parameter_value",
                "description": (
                    "Set the value of an existing user parameter by full name "
                    "(supports paths like 'PARAMETRES_UTILISATEUR\\\\nb_colonnes'). "
                    "Accepts number, bool, or string depending on the parameter type."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Full parameter name (path included).",
                        },
                        "value": {
                            "description": "New value (number, bool, or string).",
                        },
                    },
                    "required": ["name", "value"],
                },
            },
            {
                "name": "catia_create_formula",
                "description": (
                    "Create a Knowledge Advisor formula binding a target parameter to an "
                    "expression. Example: target_parameter='largeur_col_15', "
                    "expression='largeur_15 + 2 * jeu_paquet'. The expression follows CATIA "
                    "Knowledge syntax: bare parameter names if at root, full path otherwise."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "target_parameter": {
                            "type": "string",
                            "description": "Full name of the parameter that receives the formula.",
                        },
                        "expression": {
                            "type": "string",
                            "description": (
                                "Knowledge expression (right-hand side). Use mm/deg as "
                                "implicit units for Length/Angle parameters."
                            ),
                        },
                        "name": {
                            "type": "string",
                            "description": "Optional formula name (defaults to 'Formula.N').",
                        },
                        "comment": {
                            "type": "string",
                            "description": "Optional comment shown in the tree.",
                        },
                    },
                    "required": ["target_parameter", "expression"],
                },
            },
            {
                "name": "catia_rename_parameter",
                "description": (
                    "Rename a parameter. Use backslash in new_name to move into/out of a "
                    "parameter set (e.g. 'PARAMETRES_UTILISATEUR\\\\nb_colonnes')."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Current full name."},
                        "new_name": {
                            "type": "string",
                            "description": (
                                "New name (use '\\\\' to place inside a parameter set)."
                            ),
                        },
                    },
                    "required": ["name", "new_name"],
                },
            },
            {
                "name": "catia_rename_feature",
                "description": (
                    "Rename a feature (Pad, Pocket, Sketch, Pattern, etc.) in the active "
                    "Part body. Useful for tree clarity."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "old_name": {
                            "type": "string",
                            "description": "Current feature name (e.g. 'Pad.1').",
                        },
                        "new_name": {
                            "type": "string",
                            "description": "New feature name.",
                        },
                    },
                    "required": ["old_name", "new_name"],
                },
            },
            {
                "name": "catia_list_parameter_sets",
                "description": "List parameter sets in the active Part with their full paths.",
                "inputSchema": {"type": "object", "properties": {}},
            },
        ]

    # ── Dispatch ────────────────────────────────────────────────────

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> str:
        match tool_name:
            case "catia_create_parameter":
                return self._create_parameter(arguments)
            case "catia_create_parameter_set":
                return self._create_parameter_set(arguments)
            case "catia_set_parameter_value":
                return self._set_parameter_value(arguments)
            case "catia_create_formula":
                return self._create_formula(arguments)
            case "catia_rename_parameter":
                return self._rename_parameter(arguments)
            case "catia_rename_feature":
                return self._rename_feature(arguments)
            case "catia_list_parameter_sets":
                return self._list_parameter_sets()
            case _:
                raise ValueError(f"Unknown knowledge tool: {tool_name}")

    # ── Helpers ─────────────────────────────────────────────────────

    def _find_set(self, path: str) -> Any:
        """Locate a ParameterSet by its slash/backslash separated path."""
        part = self.conn.get_active_part()
        root = part.Parameters.RootParameterSet
        if not path:
            return root

        # Accept both '\' and '/' as separators
        norm = path.replace("/", "\\").strip("\\")
        current = root
        for segment in norm.split("\\"):
            if not segment:
                continue
            found = None
            sets = current.ParameterSets
            for i in range(1, sets.Count + 1):
                s = sets.Item(i)
                if s.Name == segment:
                    found = s
                    break
            if found is None:
                raise RuntimeError(
                    f"Parameter set '{segment}' not found under '{current.Name}'. "
                    "Create it with catia_create_parameter_set first."
                )
            current = found
        return current

    # ── Tool implementations ────────────────────────────────────────

    def _create_parameter(self, args: dict[str, Any]) -> str:
        self.conn.ensure_connected()
        part = self.conn.get_active_part()
        params = part.Parameters

        name = args["name"]
        ptype = args["type"].lower()
        value = args["value"]
        set_path = args.get("set_path", "")

        if "\\" in name or "/" in name:
            raise ValueError(
                "Parameter 'name' must not contain backslashes. Use 'set_path' "
                "to place the parameter inside a parameter set."
            )

        if ptype == "integer":
            param = params.CreateInteger(name, int(value))
        elif ptype == "length":
            param = params.CreateDimension(name, "LENGTH", float(value))
        elif ptype == "angle":
            param = params.CreateDimension(name, "ANGLE", float(value))
        elif ptype == "real":
            param = params.CreateReal(name, float(value))
        elif ptype == "boolean":
            param = params.CreateBoolean(name, bool(value))
        elif ptype == "string":
            param = params.CreateString(name, str(value))
        else:
            raise ValueError(f"Unknown parameter type: {ptype}")

        if set_path:
            target_set = self._find_set(set_path)
            params.MoveParameterUnderSet(param, target_set)

        full_name = param.Name
        part.Update()
        return f"Parameter created: '{full_name}' = {value} ({ptype})"

    def _create_parameter_set(self, args: dict[str, Any]) -> str:
        self.conn.ensure_connected()
        part = self.conn.get_active_part()

        name = args["name"]
        parent_path = args.get("parent_path", "")

        parent = self._find_set(parent_path)
        
        # Try creating via the parent's ParameterSets collection
        # CATIA V5 API: ParameterSets.CreateSetOfParameters(iFather)
        try:
            new_set = parent.ParameterSets.CreateSetOfParameters(parent)
        except Exception:
            # Fallback for some COM dispatch issues
            root_params = part.Parameters
            new_set = root_params.RootParameterSet.ParameterSets.CreateSetOfParameters(parent)

        new_set.Name = name

        part.Update()
        return f"Parameter set created: '{new_set.Name}' under '{parent.Name}'"

    def _set_parameter_value(self, args: dict[str, Any]) -> str:
        self.conn.ensure_connected()
        part = self.conn.get_active_part()
        name = args["name"]
        value = args["value"]

        param = part.Parameters.Item(name)
        # Handle different value types
        if isinstance(value, bool):
            param.Value = value
        elif isinstance(value, (int, float)):
            try:
                param.Value = value
            except Exception:
                # Some dimension params want ValuateFromString
                param.ValuateFromString(str(value))
        else:
            try:
                param.Value = value
            except Exception:
                param.ValuateFromString(str(value))

        part.Update()
        return f"Parameter '{name}' set to {value}"

    def _create_formula(self, args: dict[str, Any]) -> str:
        self.conn.ensure_connected()
        part = self.conn.get_active_part()

        target_name = args["target_parameter"]
        expression = args["expression"]
        formula_name = args.get("name", "")
        comment = args.get("comment", "")

        target = part.Parameters.Item(target_name)
        relations = part.Relations

        formula = relations.CreateFormula(
            formula_name, comment, target, expression
        )

        part.Update()
        return f"Formula created: '{target_name}' = {expression}"

    def _rename_parameter(self, args: dict[str, Any]) -> str:
        self.conn.ensure_connected()
        part = self.conn.get_active_part()
        name = args["name"]
        new_name = args["new_name"]

        param = part.Parameters.Item(name)
        param.Rename(new_name)
        part.Update()
        return f"Parameter '{name}' renamed to '{new_name}'"

    def _rename_feature(self, args: dict[str, Any]) -> str:
        self.conn.ensure_connected()
        part = self.conn.get_active_part()
        body = self.conn.get_active_part_body()
        old_name = args["old_name"]
        new_name = args["new_name"]

        # Search sketches first, then shapes
        for collection_name in ("Sketches", "Shapes"):
            collection = getattr(body, collection_name)
            for i in range(1, collection.Count + 1):
                item = collection.Item(i)
                if item.Name == old_name:
                    item.Name = new_name
                    part.Update()
                    return f"Feature '{old_name}' renamed to '{new_name}'"

        # Also try hybrid bodies (geometrical sets)
        try:
            hbs = part.HybridBodies
            for i in range(1, hbs.Count + 1):
                hb = hbs.Item(i)
                shapes = hb.HybridShapes
                for j in range(1, shapes.Count + 1):
                    s = shapes.Item(j)
                    if s.Name == old_name:
                        s.Name = new_name
                        part.Update()
                        return f"Feature '{old_name}' renamed to '{new_name}'"
        except Exception:
            pass

        raise RuntimeError(f"Feature '{old_name}' not found in active body.")

    def _list_parameter_sets(self) -> str:
        self.conn.ensure_connected()
        part = self.conn.get_active_part()
        root = part.Parameters.RootParameterSet

        result: list[dict[str, Any]] = []

        def _walk(node: Any, prefix: str) -> None:
            full = f"{prefix}{node.Name}" if prefix else node.Name
            result.append({
                "name": node.Name,
                "path": full,
                "parameter_count": node.DirectParameters.Count,
            })
            sets = node.ParameterSets
            for i in range(1, sets.Count + 1):
                _walk(sets.Item(i), full + "\\")

        _walk(root, "")
        return json.dumps(result, indent=2, ensure_ascii=False)
