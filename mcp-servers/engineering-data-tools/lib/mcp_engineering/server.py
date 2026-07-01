"""mcp-engineering server — engineering data retrieval tool handlers.

Provides tools for retrieving engineering material properties, thermophysical
data (NIST WebBook), seismic hazard parameters (USGS), and standards-based
constants. All data is fetched from authoritative public sources at runtime.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from functools import lru_cache


# ---------------------------------------------------------------------------
# Shared HTTP helper
# ---------------------------------------------------------------------------

def _get_json(url: str, timeout: float = 15) -> dict:
    """GET url and return parsed JSON. Raises RuntimeError on failure."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "ClaudeScience-engineering-data/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} fetching {url}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to fetch {url}: {e}") from e


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def get_seismic_hazard(args: dict) -> str:
    """
    Retrieve ASCE 7 seismic design parameters (SDS, SD1, Ss, S1) from USGS
    for a given latitude/longitude, site class, and risk category.
    """
    lat = float(args["latitude"])
    lon = float(args["longitude"])
    site_class = args.get("site_class", "D")
    risk_cat = args.get("risk_category", "II")
    edition = args.get("edition", "asce7-22")

    params = urllib.parse.urlencode({
        "latitude": lat, "longitude": lon,
        "riskCategory": risk_cat, "siteClass": site_class,
        "title": "Engineering site",
    })
    url = f"https://earthquake.usgs.gov/ws/designmaps/{edition}.json?{params}"
    data = _get_json(url)
    result = data.get("response", {}).get("data", data)
    return json.dumps({"source": url, "edition": edition,
                       "latitude": lat, "longitude": lon,
                       "site_class": site_class, "risk_category": risk_cat,
                       "parameters": result}, indent=2)


def get_usgs_streamflow(args: dict) -> str:
    """
    Retrieve daily mean streamflow from the USGS National Water Information
    System (NWIS) for a given station number and date range.
    """
    site = str(args["site_no"])
    start = str(args["start_date"])  # YYYY-MM-DD
    end = str(args["end_date"])      # YYYY-MM-DD
    param = args.get("parameter_cd", "00060")   # 00060 = discharge in cfs

    url = (f"https://waterservices.usgs.gov/nwis/dv/"
           f"?format=json&sites={site}"
           f"&startDT={start}&endDT={end}"
           f"&parameterCd={param}")
    data = _get_json(url)
    try:
        series = data["value"]["timeSeries"][0]["values"][0]["value"]
        unit = data["value"]["timeSeries"][0]["variable"]["unit"]["unitCode"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected NWIS response structure: {e}") from e

    records = [
        {"date": v["dateTime"][:10], "value": v["value"], "unit": unit}
        for v in series if v["value"] != "-999999"
    ]
    return json.dumps({
        "source": "USGS NWIS", "site_no": site,
        "start": start, "end": end, "parameter": param,
        "records": records
    }, indent=2)


def get_nist_fluid_properties(args: dict) -> str:
    """
    Retrieve thermophysical properties of a pure fluid from the NIST WebBook
    Thermophysical Properties of Fluid Systems interface.
    Returns saturation or single-phase properties at specified conditions.
    """
    fluid_id = str(args["fluid"])    # NIST fluid ID, e.g. "C2H5OH" or "Water"
    T_K = float(args.get("T_K", 298.15))
    P_Pa = float(args.get("P_Pa", 101325))
    prop_type = args.get("type", "saturation")  # "saturation" or "isochoric"

    # NIST WebBook provides a form-based interface; the REST-like URL for
    # saturation data follows this pattern for the NIST Fluids engine.
    params = urllib.parse.urlencode({
        "Action": "Load",
        "ID": fluid_id,
        "Type": "SatT" if prop_type == "saturation" else "IsoBar",
        "Digits": 5,
        "THigh": T_K, "TLow": T_K, "TInc": 0.1,
        "RefState": "DEF",
        "TUnit": "K", "PUnit": "Pa", "DUnit": "kg/m3",
        "HUnit": "kJ/kg", "WUnit": "m/s",
        "VisUnit": "uPa*s", "STUnit": "N/m",
    })
    url = f"https://webbook.nist.gov/cgi/fluid.cgi?{params}"
    req = urllib.request.Request(
        url, headers={"User-Agent": "ClaudeScience-engineering-data/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            content = r.read().decode("utf-8", errors="replace")
    except Exception as e:
        raise RuntimeError(f"NIST WebBook request failed: {e}") from e

    return json.dumps({
        "source": "NIST WebBook Thermophysical Properties",
        "fluid": fluid_id, "T_K": T_K, "P_Pa": P_Pa,
        "type": prop_type, "raw_response": content[:4000],
        "note": ("Parse the raw_response CSV/table for property values. "
                 "Columns: Temperature, Pressure, Density, Volume, "
                 "Internal Energy, Enthalpy, Entropy, Cv, Cp, "
                 "Sound Speed, Viscosity, Thermal Conductivity, Phase.")
    }, indent=2)


def get_materials_project_properties(args: dict) -> str:
    """
    Retrieve crystal structure and computed properties from the Materials Project.
    Requires MP_API_KEY environment variable.
    Returns structure summary, band gap, formation energy, and bulk modulus.
    """
    import os
    formula = str(args["formula"])
    api_key = args.get("api_key") or os.environ.get("MP_API_KEY")
    if not api_key:
        return json.dumps({
            "error": "MP_API_KEY not set",
            "message": (
                "Set the MP_API_KEY environment variable with your Materials "
                "Project API key from https://materialsproject.org/api"
            )
        })
    # Materials Project v2 REST API
    url = (f"https://api.materialsproject.org/materials/summary/"
           f"?formula={urllib.parse.quote(formula)}&fields="
           "material_id,formula_pretty,symmetry,energy_per_atom,"
           "formation_energy_per_atom,band_gap,bulk_modulus,nsites")
    req = urllib.request.Request(url, headers={
        "User-Agent": "ClaudeScience-engineering-data/1.0",
        "X-API-KEY": api_key,
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
    except Exception as e:
        raise RuntimeError(f"Materials Project API error: {e}") from e

    entries = data.get("data", [])
    if not entries:
        return json.dumps({"formula": formula, "results": [],
                           "message": "No entries found"})
    # Sort by formation energy (most stable first)
    entries.sort(key=lambda e: e.get("formation_energy_per_atom", 0))
    return json.dumps({
        "source": "Materials Project (materialsproject.org)",
        "formula": formula, "results": entries[:10]
    }, indent=2)


def get_noaa_precipitation(args: dict) -> str:
    """
    Provide instructions and a direct URL for retrieving NOAA Atlas 14
    precipitation frequency data for a given lat/lon location.
    The NOAA PFDS does not expose a public JSON API; this tool returns
    the correct URL and download instructions.
    """
    lat = float(args["latitude"])
    lon = float(args["longitude"])
    return json.dumps({
        "source": "NOAA Atlas 14 Precipitation Frequency Data Server",
        "instructions": (
            "Navigate to the URL below to retrieve precipitation depth and "
            "intensity estimates for return periods from 1 to 1000 years and "
            "durations from 5 minutes to 60 days. Download the data as a CSV "
            "or use the tabular HTML output. The rational method design storm "
            "intensity i (mm/hr) for a given return period and duration is "
            "available from the retrieved table."
        ),
        "pfds_url": (
            f"https://hdsc.nws.noaa.gov/cgi-bin/hdsc/new/fe_text_mean.csv"
            f"?lat={lat}&lon={lon}&type=pf&data=depth&units=metric&series=pds"
        ),
        "interactive_url": (
            f"https://hdsc.nws.noaa.gov/hdsc/pfds/pfds_map_cont.html"
            f"?bkmrk={lat},{lon}"
        ),
        "latitude": lat, "longitude": lon,
    }, indent=2)


# ---------------------------------------------------------------------------
# MCP server entry point
# ---------------------------------------------------------------------------

TOOLS = {
    "get_seismic_hazard": get_seismic_hazard,
    "get_usgs_streamflow": get_usgs_streamflow,
    "get_nist_fluid_properties": get_nist_fluid_properties,
    "get_materials_project_properties": get_materials_project_properties,
    "get_noaa_precipitation": get_noaa_precipitation,
}

SCHEMAS = {
    "get_seismic_hazard": {
        "description": (
            "Retrieve ASCE 7 seismic design parameters (Ss, S1, SDS, SD1) from "
            "USGS for a site location, site class, and risk category."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "latitude":  {"type": "number", "description": "Site latitude (decimal degrees)"},
                "longitude": {"type": "number", "description": "Site longitude (decimal degrees)"},
                "site_class": {"type": "string", "description": "ASCE 7 site class (A-F)", "default": "D"},
                "risk_category": {"type": "string", "description": "Risk category (I-IV)", "default": "II"},
                "edition": {"type": "string", "description": "ASCE 7 edition (asce7-22, asce7-16)", "default": "asce7-22"},
            },
            "required": ["latitude", "longitude"],
        },
    },
    "get_usgs_streamflow": {
        "description": (
            "Retrieve daily mean streamflow (discharge) from the USGS National "
            "Water Information System for a gauged stream site."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "site_no":    {"type": "string",  "description": "USGS station number (e.g. '01646500')"},
                "start_date": {"type": "string",  "description": "Start date YYYY-MM-DD"},
                "end_date":   {"type": "string",  "description": "End date YYYY-MM-DD"},
                "parameter_cd": {"type": "string", "description": "USGS parameter code (default 00060 = discharge)", "default": "00060"},
            },
            "required": ["site_no", "start_date", "end_date"],
        },
    },
    "get_nist_fluid_properties": {
        "description": (
            "Retrieve thermophysical properties of a pure fluid from the NIST "
            "WebBook at specified temperature and pressure conditions."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "fluid": {"type": "string", "description": "NIST fluid identifier (e.g. 'Water', 'CO2', 'C2H5OH', 'Nitrogen')"},
                "T_K":   {"type": "number", "description": "Temperature (K)", "default": 298.15},
                "P_Pa":  {"type": "number", "description": "Pressure (Pa)", "default": 101325},
                "type":  {"type": "string", "description": "'saturation' or 'isochoric'", "default": "saturation"},
            },
            "required": ["fluid"],
        },
    },
    "get_materials_project_properties": {
        "description": (
            "Retrieve crystal structure and computed materials properties "
            "(formation energy, band gap, bulk modulus) from the Materials Project."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "formula": {"type": "string", "description": "Chemical formula (e.g. 'Fe2O3', 'TiO2', 'Al2O3')"},
                "api_key": {"type": "string", "description": "Materials Project API key (optional if MP_API_KEY env var set)"},
            },
            "required": ["formula"],
        },
    },
    "get_noaa_precipitation": {
        "description": (
            "Get NOAA Atlas 14 precipitation frequency data URL and instructions "
            "for a site location. Returns the direct CSV download URL for "
            "design storm intensities at all return periods."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "latitude":  {"type": "number", "description": "Site latitude (decimal degrees)"},
                "longitude": {"type": "number", "description": "Site longitude (decimal degrees)"},
            },
            "required": ["latitude", "longitude"],
        },
    },
}


def main() -> None:
    """Run the engineering-data MCP server over stdio (JSON-RPC 2.0)."""
    import sys
    import traceback

    def respond(id_, result=None, error=None):
        msg = {"jsonrpc": "2.0", "id": id_}
        if error:
            msg["error"] = error
        else:
            msg["result"] = result
        line = json.dumps(msg) + "\n"
        sys.stdout.write(line)
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
                "serverInfo": {"name": "mcp-engineering", "version": "1.0.0"},
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
                respond(req_id, error={
                    "code": -32601,
                    "message": f"Unknown tool: {tool_name}"
                })
                continue
            try:
                result_text = TOOLS[tool_name](tool_args)
                respond(req_id, {
                    "content": [{"type": "text", "text": result_text}]
                })
            except Exception as exc:
                respond(req_id, error={
                    "code": -32603,
                    "message": str(exc),
                    "data": traceback.format_exc()
                })
        else:
            respond(req_id, error={
                "code": -32601,
                "message": f"Method not found: {method}"
            })


if __name__ == "__main__":
    main()
