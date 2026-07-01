"""mcp-pandapower server — power systems analysis tool handlers.

Provides tools for running load flow, short-circuit, and optimal power flow
analyses on electrical networks using pandapower.

Requires: pandapower (pip install pandapower).
"""

from __future__ import annotations

import json
import sys
import traceback


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def run_load_flow(args: dict) -> str:
    """
    Run a load flow analysis on a pandapower network defined by JSON description.
    Returns bus voltages, line loadings, and violation summary.
    """
    try:
        import pandapower as pp
        import pandapower.networks as pn
        import numpy as np
    except ImportError:
        return json.dumps({
            "error": "pandapower not installed",
            "install": "pip install pandapower",
            "alternative": (
                "Use the power-systems skill which documents pandapower workflows "
                "directly in the Python kernel."
            )
        })

    network_type = args.get("network_type", "custom")

    # Support loading a named test network
    if network_type.startswith("ieee"):
        case_map = {
            "ieee9": pn.case9, "ieee14": pn.case14,
            "ieee30": pn.case30, "ieee57": pn.case57,
            "ieee118": pn.case118,
        }
        case_fn = case_map.get(network_type.replace("-", "").lower())
        if case_fn is None:
            return json.dumps({"error": f"Unknown IEEE test case: {network_type}",
                               "available": list(case_map.keys())})
        net = case_fn()
    else:
        # Build network from JSON description
        net = _build_network_from_json(args, pp)

    try:
        pp.runpp(net, algorithm=args.get("algorithm", "nr"),
                 calculate_voltage_angles=True)
    except Exception as e:
        return json.dumps({"error": f"Load flow failed: {e}",
                           "tip": "Check network connectivity and slack bus definition."})

    # Extract results
    bus_results = net.res_bus[["vm_pu", "va_degree", "p_mw", "q_mvar"]].to_dict(orient="records")
    line_results = net.res_line[["p_from_mw", "q_from_mvar", "loading_percent"]].to_dict(orient="records")

    # Violations
    v_violations = net.res_bus[(net.res_bus.vm_pu < 0.95) | (net.res_bus.vm_pu > 1.05)]
    overload = net.res_line[net.res_line.loading_percent > 100]

    return json.dumps({
        "status": "converged",
        "network_type": network_type,
        "summary": {
            "n_buses": len(net.bus),
            "n_lines": len(net.line),
            "total_load_mw": float(net.res_load.p_mw.sum()),
            "total_generation_mw": float(net.res_gen.p_mw.sum()) if len(net.gen) > 0 else None,
            "max_vm_pu": float(net.res_bus.vm_pu.max()),
            "min_vm_pu": float(net.res_bus.vm_pu.min()),
            "max_line_loading_pct": float(net.res_line.loading_percent.max()),
        },
        "voltage_violations": v_violations.to_dict(orient="records"),
        "thermal_overloads": overload.to_dict(orient="records"),
        "bus_results": bus_results,
        "line_results": line_results,
    }, indent=2, default=str)


def run_short_circuit(args: dict) -> str:
    """
    Run a short-circuit analysis on a named IEEE test network or a custom network.
    Returns fault currents (ikss_ka) and fault level (skss_mw) at each bus.
    """
    try:
        import pandapower as pp
        import pandapower.networks as pn
        import pandapower.shortcircuit as sc
    except ImportError:
        return json.dumps({
            "error": "pandapower not installed",
            "install": "pip install pandapower",
        })

    network_type = args.get("network_type", "ieee14")
    fault_type = args.get("fault_type", "3ph")

    case_map = {
        "ieee9": pn.case9, "ieee14": pn.case14,
        "ieee30": pn.case30, "ieee57": pn.case57,
    }
    case_fn = case_map.get(network_type.replace("-", "").lower(), pn.case14)
    net = case_fn()

    try:
        sc.calc_sc(net, fault=fault_type, branch_results=False)
    except Exception as e:
        return json.dumps({"error": f"Short-circuit calculation failed: {e}"})

    sc_results = net.res_bus_sc.to_dict(orient="records")
    return json.dumps({
        "status": "completed",
        "network_type": network_type,
        "fault_type": fault_type,
        "max_fault_current_kA": float(net.res_bus_sc.ikss_ka.max()),
        "max_fault_level_MVA": float(net.res_bus_sc.skss_mw.max()),
        "bus_results": sc_results,
    }, indent=2, default=str)


def get_ieee_test_case(args: dict) -> str:
    """
    Return summary information about an IEEE test network without running a simulation.
    Useful for understanding network topology before analysis.
    """
    try:
        import pandapower.networks as pn
    except ImportError:
        return json.dumps({"error": "pandapower not installed", "install": "pip install pandapower"})

    case_map = {
        "ieee9":  pn.case9,  "ieee14": pn.case14,
        "ieee30": pn.case30, "ieee57": pn.case57,
        "ieee118": pn.case118,
    }
    name = args.get("name", "ieee14").replace("-", "").lower()
    if name not in case_map:
        return json.dumps({"error": f"Unknown case: {name}",
                           "available": list(case_map.keys())})

    net = case_map[name]()
    return json.dumps({
        "name": name,
        "n_buses": len(net.bus),
        "n_lines": len(net.line),
        "n_transformers": len(net.trafo),
        "n_generators": len(net.gen) + len(net.ext_grid),
        "n_loads": len(net.load),
        "voltage_levels_kV": sorted(net.bus.vn_kv.unique().tolist()),
        "total_load_mw": float(net.load.p_mw.sum()),
    }, indent=2)


def _build_network_from_json(args: dict, pp) -> "pandapower.pandapowerNet":
    """Build a pandapower network from a JSON description in args."""
    net = pp.create_empty_network(
        sn_mva=float(args.get("sn_mva", 100)),
        f_hz=float(args.get("f_hz", 50))
    )
    # buses
    for b in args.get("buses", []):
        pp.create_bus(net, vn_kv=b["vn_kv"], name=b.get("name", ""))
    # ext_grid (slack)
    for eg in args.get("ext_grids", []):
        pp.create_ext_grid(net, bus=eg["bus"],
                           vm_pu=eg.get("vm_pu", 1.0),
                           name=eg.get("name", "Grid"))
    # loads
    for ld in args.get("loads", []):
        pp.create_load(net, bus=ld["bus"],
                       p_mw=ld["p_mw"], q_mvar=ld.get("q_mvar", 0),
                       name=ld.get("name", ""))
    # generators
    for gen in args.get("generators", []):
        pp.create_gen(net, bus=gen["bus"], p_mw=gen["p_mw"],
                      vm_pu=gen.get("vm_pu", 1.0), name=gen.get("name", ""))
    # lines (by std_type)
    for ln in args.get("lines", []):
        pp.create_line(net, from_bus=ln["from_bus"], to_bus=ln["to_bus"],
                       length_km=ln["length_km"],
                       std_type=ln.get("std_type", "NAYY 4x50 SE"),
                       name=ln.get("name", ""))
    # transformers
    for tr in args.get("transformers", []):
        pp.create_transformer(net, hv_bus=tr["hv_bus"], lv_bus=tr["lv_bus"],
                              std_type=tr.get("std_type", "40 MVA 110/20 kV"),
                              name=tr.get("name", ""))
    return net


# ---------------------------------------------------------------------------
# Tool registry and schemas
# ---------------------------------------------------------------------------

TOOLS = {
    "run_load_flow": run_load_flow,
    "run_short_circuit": run_short_circuit,
    "get_ieee_test_case": get_ieee_test_case,
}

SCHEMAS = {
    "run_load_flow": {
        "description": (
            "Run a Newton-Raphson load flow analysis on an electrical network. "
            "Accepts a named IEEE test case (ieee9, ieee14, ieee30, ieee57, ieee118) "
            "or a custom network description. Returns bus voltages, line loadings, "
            "and a summary of voltage violations and thermal overloads."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "network_type": {
                    "type": "string",
                    "description": "Named IEEE test case (ieee14, ieee30, etc.) or 'custom'",
                    "default": "ieee14"
                },
                "algorithm": {
                    "type": "string",
                    "description": "Load flow algorithm: 'nr' (Newton-Raphson) or 'bfsw' (Backward/Forward Sweep)",
                    "default": "nr"
                },
                "sn_mva": {"type": "number", "description": "System base MVA (for custom network)", "default": 100},
                "f_hz": {"type": "number", "description": "System frequency Hz (for custom network)", "default": 50},
                "buses": {
                    "type": "array",
                    "description": "List of buses for custom network: [{vn_kv, name}]",
                    "items": {"type": "object"}
                },
                "ext_grids": {
                    "type": "array",
                    "description": "Slack bus definitions: [{bus, vm_pu, name}]",
                    "items": {"type": "object"}
                },
                "loads": {
                    "type": "array",
                    "description": "Load definitions: [{bus, p_mw, q_mvar, name}]",
                    "items": {"type": "object"}
                },
                "lines": {
                    "type": "array",
                    "description": "Line definitions: [{from_bus, to_bus, length_km, std_type}]",
                    "items": {"type": "object"}
                },
                "transformers": {
                    "type": "array",
                    "description": "Transformer definitions: [{hv_bus, lv_bus, std_type}]",
                    "items": {"type": "object"}
                },
            },
        },
    },
    "run_short_circuit": {
        "description": (
            "Run a short-circuit analysis on a named IEEE test network. "
            "Returns maximum fault currents (ikss_ka) and fault levels (skss_mw) "
            "at each bus for 3-phase or single-phase faults."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "network_type": {
                    "type": "string",
                    "description": "IEEE test case: ieee9, ieee14, ieee30, ieee57",
                    "default": "ieee14"
                },
                "fault_type": {
                    "type": "string",
                    "description": "Fault type: '3ph' (three-phase) or '1ph' (single-phase)",
                    "default": "3ph"
                },
            },
        },
    },
    "get_ieee_test_case": {
        "description": (
            "Return topology summary for a named IEEE test network without running "
            "a simulation. Use to understand network size and voltage levels before analysis."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "IEEE test case name: ieee9, ieee14, ieee30, ieee57, ieee118",
                    "default": "ieee14"
                },
            },
            "required": ["name"],
        },
    },
}


# ---------------------------------------------------------------------------
# MCP server entry point
# ---------------------------------------------------------------------------

def main() -> None:
    def respond(id_, result=None, error=None):
        msg = {"jsonrpc": "2.0", "id": id_}
        if error:
            msg["error"] = error
        else:
            msg["result"] = result
        sys.stdout.write(json.dumps(msg) + "\n")
        sys.stdout.flush()

    for raw_line in sys.stdin:
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            req = json.loads(raw_line)
        except json.JSONDecodeError:
            continue

        req_id = req.get("id")
        method = req.get("method", "")
        params = req.get("params", {})

        if method == "initialize":
            respond(req_id, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "mcp-pandapower", "version": "1.0.0"},
            })
        elif method == "tools/list":
            tools = [
                {"name": name, "description": schema["description"],
                 "inputSchema": schema["inputSchema"]}
                for name, schema in SCHEMAS.items()
            ]
            respond(req_id, {"tools": tools})
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            if tool_name not in TOOLS:
                respond(req_id, error={"code": -32601, "message": f"Unknown tool: {tool_name}"})
                continue
            try:
                result_text = TOOLS[tool_name](tool_args)
                respond(req_id, {"content": [{"type": "text", "text": result_text}]})
            except Exception as exc:
                respond(req_id, error={"code": -32603, "message": str(exc),
                                        "data": traceback.format_exc()})
        else:
            respond(req_id, error={"code": -32601, "message": f"Method not found: {method}"})


if __name__ == "__main__":
    main()
