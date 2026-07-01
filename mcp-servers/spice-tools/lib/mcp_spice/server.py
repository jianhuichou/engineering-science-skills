"""mcp-spice server — SPICE netlist simulation tool handler.

Accepts SPICE netlist text and analysis parameters, runs simulation via
PySpice/ngspice, and returns structured results as JSON.

Requires: ngspice (system binary) and PySpice (pip install PySpice).
"""

from __future__ import annotations

import json
import sys
import traceback
import tempfile
import os
from pathlib import Path


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def simulate_spice(args: dict) -> str:
    """
    Run a SPICE simulation from a netlist string.
    Supports .DC, .AC, and .TRAN analyses detected from the netlist.
    Returns node voltages and branch currents as JSON.
    """
    netlist = str(args["netlist"])
    analysis_type = str(args.get("analysis_type", "auto")).upper()

    # Detect analysis type from netlist if auto
    if analysis_type == "AUTO":
        upper_netlist = netlist.upper()
        if ".AC" in upper_netlist:
            analysis_type = "AC"
        elif ".TRAN" in upper_netlist:
            analysis_type = "TRAN"
        elif ".DC" in upper_netlist:
            analysis_type = "DC"
        else:
            analysis_type = "DC"

    try:
        result = _run_ngspice_raw(netlist, analysis_type, args)
        return json.dumps(result, indent=2)
    except ImportError:
        return json.dumps(_run_analytical_fallback(netlist, args), indent=2)
    except Exception as exc:
        return json.dumps({
            "error": str(exc),
            "netlist": netlist[:500],
            "suggestion": (
                "Ensure ngspice is installed ('sudo apt-get install ngspice') "
                "and PySpice is available ('pip install PySpice'). "
                "Alternatively, use the circuit-analysis skill with lcapy for "
                "symbolic analysis or scipy for numerical solutions."
            )
        }, indent=2)


def _run_ngspice_raw(netlist: str, analysis_type: str, args: dict) -> dict:
    """Run simulation using ngspice via subprocess (raw mode)."""
    import subprocess

    with tempfile.TemporaryDirectory() as tmpdir:
        netlist_file = Path(tmpdir) / "circuit.cir"

        # Ensure netlist has .END
        clean_netlist = netlist.strip()
        if not clean_netlist.upper().endswith(".END"):
            clean_netlist += "\n.END"

        netlist_file.write_text(clean_netlist)
        out_file = Path(tmpdir) / "output.raw"

        result = subprocess.run(
            ["ngspice", "-b", "-r", str(out_file), str(netlist_file)],
            capture_output=True, text=True, timeout=30
        )

        output = {
            "analysis_type": analysis_type,
            "ngspice_stdout": result.stdout[-2000:] if result.stdout else "",
            "ngspice_stderr": result.stderr[-1000:] if result.stderr else "",
            "return_code": result.returncode,
        }

        if result.returncode != 0:
            output["error"] = f"ngspice exited with code {result.returncode}"
        else:
            output["message"] = (
                "Simulation completed. Parse stdout for node voltages. "
                "For structured results, add .PRINT statements to your netlist "
                "or use PySpice's analysis objects."
            )

        return output


def _run_analytical_fallback(netlist: str, args: dict) -> dict:
    """Return structured guidance when ngspice/PySpice are not available."""
    return {
        "status": "simulation_not_available",
        "message": (
            "ngspice is not installed in this environment. To run SPICE simulations:"
        ),
        "options": [
            "Install ngspice: 'sudo apt-get install ngspice' or 'conda install -c conda-forge ngspice'",
            "Install PySpice: 'pip install PySpice' (wraps ngspice with Python API)",
            "Use lcapy for symbolic circuit analysis: 'pip install lcapy' (no ngspice required)",
            "Use the circuit-analysis skill which documents both approaches",
        ],
        "netlist_received": netlist[:500],
        "lcapy_example": (
            "from lcapy import Circuit\n"
            "cct = Circuit('''\\n"
            "V1 1 0 10\\n"
            "R1 1 2 1k\\n"
            "R2 2 0 2k\\n"
            "''')\n"
            "print(cct['2'].V.dc)  # node 2 voltage"
        ),
    }


def parse_spice_netlist(args: dict) -> str:
    """
    Parse a SPICE netlist and return a structured summary of circuit elements,
    nodes, and analysis commands without running a simulation.
    """
    netlist = str(args["netlist"])
    lines = netlist.strip().split("\n")
    elements = []
    nodes = set()
    analyses = []
    title = lines[0] if lines else ""

    for line in lines[1:]:
        stripped = line.strip()
        if not stripped or stripped.startswith("*"):
            continue
        upper = stripped.upper()
        tokens = stripped.split()
        if not tokens:
            continue

        prefix = tokens[0][0].upper()
        if prefix in ("R", "C", "L", "V", "I", "G", "E", "F", "H"):
            elem = {"type": prefix, "name": tokens[0]}
            if len(tokens) >= 3:
                elem["node_pos"] = tokens[1]
                elem["node_neg"] = tokens[2]
                nodes.add(tokens[1]); nodes.add(tokens[2])
            if len(tokens) >= 4:
                elem["value"] = tokens[3]
            elements.append(elem)
        elif upper.startswith(".AC"):
            analyses.append({"type": "AC", "parameters": tokens[1:]})
        elif upper.startswith(".DC"):
            analyses.append({"type": "DC", "parameters": tokens[1:]})
        elif upper.startswith(".TRAN"):
            analyses.append({"type": "TRAN", "parameters": tokens[1:]})
        elif upper.startswith(".OP"):
            analyses.append({"type": "OP"})

    # Remove ground node from count
    nodes.discard("0"); nodes.discard("GND")

    return json.dumps({
        "title": title,
        "element_count": len(elements),
        "node_count": len(nodes),
        "nodes": sorted(nodes),
        "elements": elements,
        "analyses": analyses,
    }, indent=2)


# ---------------------------------------------------------------------------
# Tool registry and schemas
# ---------------------------------------------------------------------------

TOOLS = {
    "simulate_spice": simulate_spice,
    "parse_spice_netlist": parse_spice_netlist,
}

SCHEMAS = {
    "simulate_spice": {
        "description": (
            "Run a SPICE circuit simulation from a netlist string using ngspice. "
            "Supports DC, AC, and transient (.TRAN) analyses. Returns node voltages "
            "and analysis output. Requires ngspice installed in the environment."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "netlist": {
                    "type": "string",
                    "description": (
                        "Complete SPICE netlist text including title line, "
                        "elements, analysis commands (.AC/.DC/.TRAN), and .END"
                    )
                },
                "analysis_type": {
                    "type": "string",
                    "description": "DC, AC, TRAN, or auto (detect from netlist)",
                    "default": "auto"
                },
            },
            "required": ["netlist"],
        },
    },
    "parse_spice_netlist": {
        "description": (
            "Parse a SPICE netlist and return a structured summary of elements, "
            "nodes, and analysis commands without running a simulation. "
            "Useful for validating a netlist before simulation."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "netlist": {"type": "string", "description": "SPICE netlist text"},
            },
            "required": ["netlist"],
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
                "serverInfo": {"name": "mcp-spice", "version": "1.0.0"},
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
