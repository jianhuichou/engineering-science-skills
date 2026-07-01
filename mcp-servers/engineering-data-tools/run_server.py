#!/usr/bin/env python3
"""Launcher for engineering-data-tools MCP servers (stdio).

Usage: python run_server.py <package>   e.g. python run_server.py mcp_engineering

Registered in core/src/mcp/bundledRegistry.ts as
  command: "python", args: ["${MCP_SERVERS_DIR}/engineering-data-tools/run_server.py", "<pkg>"]
MCPPool resolves `python` to the shared operon-mcp conda env.
All packages live flat under lib/ next to this file.
"""

import importlib
import sys
from pathlib import Path


def main() -> None:
    lib = Path(__file__).resolve().parent / "lib"
    servers = sorted(
        p.name for p in lib.iterdir()
        if p.name.startswith("mcp_") and (p / "server.py").is_file()
    )
    if len(sys.argv) != 2 or sys.argv[1] not in servers:
        sys.stderr.write(
            "usage: run_server.py <server package>\n"
            f"valid: {', '.join(servers)}\n")
        raise SystemExit(2)
    sys.path.insert(0, str(lib))
    mod = importlib.import_module(f"{sys.argv[1]}.server")
    mod.main()


if __name__ == "__main__":
    main()
