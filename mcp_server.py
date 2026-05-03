#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP bridge for Ansys Workbench automation.

The server supports two modes:

1. File-IPC bridge mode, similar to Abaqus MCP:
   mcp_server.py writes command JSON files and ansys_workbench_bridge.wbjn
   runs inside Workbench to execute them.
2. Direct batch mode:
   mcp_server.py invokes RunWB2/MAPDL directly for one-shot jobs.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP


__version__ = "0.2.0"

SERVER_ROOT = Path(__file__).resolve().parent
DEFAULT_MCP_HOME = SERVER_ROOT
MCP_HOME = Path(os.environ.get("ANSYS_WORKBENCH_MCP_HOME", DEFAULT_MCP_HOME)).expanduser().resolve()

COMMANDS_DIR = MCP_HOME / "commands"
RESULTS_DIR = MCP_HOME / "results"
SCRIPTS_DIR = MCP_HOME / "scripts"
RUNS_DIR = MCP_HOME / "runs"
STATUS_FILE = MCP_HOME / "status.json"
STOP_FILE = MCP_HOME / "stop.flag"
LOG_FILE = MCP_HOME / "mcp.log"
BRIDGE_JOURNAL = SERVER_ROOT / "ansys_workbench_bridge.wbjn"

DEFAULT_RUNWB2 = r"D:\Program Files\ANSYS Inc\v251\Framework\bin\Win64\RunWB2.exe"
DEFAULT_MECHANICAL = r"D:\Program Files\ANSYS Inc\v251\aisol\bin\winx64\AnsysWBU.exe"
DEFAULT_MAPDL = r"D:\Program Files\ANSYS Inc\v251\ansys\bin\winx64\ANSYS251.exe"

RUNWB2 = Path(os.environ.get("ANSYS_RUNWB2", DEFAULT_RUNWB2))
MECHANICAL = Path(os.environ.get("ANSYS_MECHANICAL", DEFAULT_MECHANICAL))
MAPDL = Path(os.environ.get("ANSYS_MAPDL", DEFAULT_MAPDL))

DEFAULT_TIMEOUT = 30.0

mcp = FastMCP("ansys-workbench-mcp")


def _ensure_dirs() -> None:
    for path in [COMMANDS_DIR, RESULTS_DIR, SCRIPTS_DIR, RUNS_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def _as_path(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _run_process(args: list[str], cwd: Path, timeout_seconds: int) -> dict[str, Any]:
    started = time.time()
    proc = subprocess.run(
        args,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
    )
    return {
        "returncode": proc.returncode,
        "elapsed_seconds": round(time.time() - started, 3),
        "stdout": proc.stdout[-12000:],
        "stderr": proc.stderr[-12000:],
    }


def _workbench_command(journal_path: Path, batch: bool) -> list[str]:
    args = [str(RUNWB2)]
    if batch:
        args.append("-B")
    args.extend(["-R", str(journal_path)])
    return args


def _read_status() -> dict[str, Any]:
    return _read_json(STATUS_FILE)


def _send_command(cmd_type: str, timeout: float = DEFAULT_TIMEOUT, **kwargs: Any) -> dict[str, Any]:
    _ensure_dirs()
    cmd_id = uuid.uuid4().hex[:8]
    command = {"id": cmd_id, "type": cmd_type, "timestamp": time.time(), **kwargs}
    cmd_path = COMMANDS_DIR / f"cmd_{cmd_id}.json"
    result_path = RESULTS_DIR / f"{cmd_id}.json"

    _write_json(cmd_path, command)
    deadline = time.time() + float(timeout)
    while time.time() < deadline:
        if result_path.exists():
            result = _read_json(result_path)
            try:
                result_path.unlink()
            except Exception:
                pass
            return result
        time.sleep(0.05)

    try:
        cmd_path.unlink()
    except Exception:
        pass
    return {"success": False, "error": f"Timeout: no response from Workbench bridge in {timeout}s"}


def _format_bridge_result(result: dict[str, Any]) -> str:
    if result.get("success"):
        data = result.get("data")
        output = result.get("output", "")
        if data is not None:
            return _json(data if isinstance(data, dict) else {"data": data, "output": output})
        return output if output else "(Command executed successfully, no output)"
    error = result.get("error", "Unknown error")
    tb = result.get("traceback", "")
    return f"Error: {error}\n{tb}".strip()


def _wait_for_log_marker(log_path: Path, marker: str, timeout_seconds: int) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if log_path.exists():
            try:
                if marker in log_path.read_text(encoding="utf-8", errors="replace"):
                    return True
            except OSError:
                pass
        time.sleep(0.5)
    return False


@mcp.resource("ansys-workbench://status")
def workbench_status_resource() -> str:
    """Current Ansys Workbench bridge status."""
    status = _read_status()
    if not status:
        return _json({"connected": False, "detail": "status.json not found", "mcp_home": str(MCP_HOME)})
    return _json(status)


@mcp.resource("ansys-workbench://installation")
def installation_resource() -> str:
    """Configured Ansys executable paths for this MCP server."""
    return check_ansys_installation()


@mcp.tool()
def check_ansys_installation() -> str:
    """Check configured Workbench, Mechanical, MAPDL, and bridge paths."""
    data = {
        "version": __version__,
        "runwb2": str(RUNWB2),
        "runwb2_exists": RUNWB2.exists(),
        "mechanical": str(MECHANICAL),
        "mechanical_exists": MECHANICAL.exists(),
        "mapdl": str(MAPDL),
        "mapdl_exists": MAPDL.exists(),
        "bridge_journal": str(BRIDGE_JOURNAL),
        "bridge_journal_exists": BRIDGE_JOURNAL.exists(),
        "mcp_home": str(MCP_HOME),
        "server_root": str(SERVER_ROOT),
    }
    return _json(data)


@mcp.tool()
def start_workbench_bridge(batch: bool = True, wait_seconds: int = 20) -> str:
    """Launch Workbench with the file-IPC bridge journal loaded.

    The bridge journal keeps Workbench alive and polls commands/*.json.
    Use stop_workbench_bridge to stop it.
    """
    if not RUNWB2.exists():
        return _json({"ok": False, "error": f"RunWB2 not found: {RUNWB2}"})
    if not BRIDGE_JOURNAL.exists():
        return _json({"ok": False, "error": f"Bridge journal not found: {BRIDGE_JOURNAL}"})

    status = _read_status()
    if status.get("status") == "running":
        ping_result = _send_command("ping", timeout=5.0)
        if ping_result.get("success"):
            return _json({"ok": True, "already_running": True, "status": status, "ping": ping_result})

    _ensure_dirs()
    try:
        if STOP_FILE.exists():
            STOP_FILE.unlink()
    except Exception:
        pass

    env = os.environ.copy()
    env["ANSYS_WORKBENCH_MCP_HOME"] = str(MCP_HOME)
    proc = subprocess.Popen(
        _workbench_command(BRIDGE_JOURNAL, batch=batch),
        cwd=str(SERVER_ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    deadline = time.time() + max(1, int(wait_seconds))
    ping_result: dict[str, Any] = {}
    while time.time() < deadline:
        status = _read_status()
        if status.get("status") == "running":
            ping_result = _send_command("ping", timeout=5.0)
            if ping_result.get("success"):
                return _json({"ok": True, "pid": proc.pid, "status": status, "ping": ping_result})
        time.sleep(0.5)

    return _json({"ok": False, "pid": proc.pid, "status": _read_status(), "detail": "Bridge did not answer before timeout"})


@mcp.tool()
def stop_workbench_bridge(timeout_seconds: int = 10) -> str:
    """Signal the Workbench bridge loop to stop."""
    result = _send_command("stop", timeout=min(float(timeout_seconds), 5.0))
    if not result.get("success"):
        try:
            STOP_FILE.write_text("stop", encoding="utf-8")
        except Exception:
            pass

    deadline = time.time() + max(1, int(timeout_seconds))
    while time.time() < deadline:
        status = _read_status()
        if status.get("status") in {"stopped", "ready"}:
            return _json({"ok": True, "status": status, "command_result": result})
        time.sleep(0.25)

    return _json({"ok": False, "status": _read_status(), "command_result": result})


@mcp.tool()
def check_workbench_connection() -> str:
    """Check whether the Workbench bridge journal is running and responding."""
    status = _read_status()
    if not status:
        return "Workbench bridge status not found. Run start_workbench_bridge() or load ansys_workbench_bridge.wbjn in Workbench."

    if status.get("status") != "running":
        return f"Workbench bridge is not running: {_json(status)}"

    result = _send_command("ping", timeout=10.0)
    if result.get("success"):
        data = result.get("data", {})
        version = data.get("version", "?") if isinstance(data, dict) else "?"
        return f"Connected to Ansys Workbench bridge v{version}.\nStatus: {_json(status)}"
    return f"Workbench bridge status exists but ping failed: {_json(result)}"


@mcp.tool()
def execute_workbench_script(script: str, timeout_seconds: int = 60) -> str:
    """Execute Python/Workbench journal code inside the running Workbench bridge."""
    result = _send_command("execute_script", timeout=float(timeout_seconds), script=script)
    return _format_bridge_result(result)


@mcp.tool()
def get_project_info(timeout_seconds: int = 30) -> str:
    """Get project/system/component information from the running Workbench bridge."""
    result = _send_command("get_project_info", timeout=float(timeout_seconds))
    return _format_bridge_result(result)


@mcp.tool()
def open_project(project_file: str, timeout_seconds: int = 120) -> str:
    """Open a Workbench project in the running Workbench bridge."""
    result = _send_command("open_project", timeout=float(timeout_seconds), project_file=project_file)
    return _format_bridge_result(result)


@mcp.tool()
def save_project(project_file: str = "", overwrite: bool = True, timeout_seconds: int = 120) -> str:
    """Save the current Workbench project through the running bridge."""
    result = _send_command(
        "save_project",
        timeout=float(timeout_seconds),
        project_file=project_file,
        overwrite=overwrite,
    )
    return _format_bridge_result(result)


@mcp.tool()
def update_project(timeout_seconds: int = 600) -> str:
    """Run Workbench Update() in the running bridge."""
    result = _send_command("update_project", timeout=float(timeout_seconds))
    return _format_bridge_result(result)


@mcp.tool()
def create_steady_state_thermal_system_live(
    project_dir: str,
    project_name: str = "steady_state_thermal",
    geometry_file: str = "",
    refresh_model: bool = False,
    timeout_seconds: int = 180,
) -> str:
    """Create a Steady-State Thermal system in the running Workbench bridge."""
    result = _send_command(
        "create_steady_state_thermal_system",
        timeout=float(timeout_seconds),
        project_dir=project_dir,
        project_name=project_name,
        geometry_file=geometry_file,
        refresh_model=refresh_model,
    )
    return _format_bridge_result(result)


@mcp.tool()
def create_thermal_bar_demo_live(
    project_dir: str = r"D:\ansys-workbench-mcp\runs\thermal_bar_demo_live",
    timeout_seconds: int = 600,
) -> str:
    """Create and solve a simple thermal bar demo through the running Workbench bridge."""
    result = _send_command("create_thermal_bar_demo", timeout=float(timeout_seconds), project_dir=project_dir)
    return _format_bridge_result(result)


@mcp.tool()
def run_workbench_journal(
    journal_path: str,
    workdir: str = "",
    batch: bool = True,
    timeout_seconds: int = 600,
) -> str:
    """Run an Ansys Workbench journal through RunWB2 as a direct batch job."""
    if not RUNWB2.exists():
        return _json({"ok": False, "error": f"RunWB2 not found: {RUNWB2}"})

    journal = _as_path(journal_path)
    if not journal.exists():
        return _json({"ok": False, "error": f"Journal not found: {journal}"})

    cwd = _as_path(workdir) if workdir else journal.parent
    cwd.mkdir(parents=True, exist_ok=True)

    try:
        result = _run_process(_workbench_command(journal, batch=batch), cwd, timeout_seconds)
        return _json({"ok": result["returncode"] == 0, "journal": str(journal), **result})
    except subprocess.TimeoutExpired:
        return _json({"ok": False, "error": f"Timed out after {timeout_seconds}s", "journal": str(journal)})


@mcp.tool()
def create_steady_state_thermal_system(
    project_dir: str,
    project_name: str = "steady_state_thermal",
    geometry_file: str = "",
    refresh_model: bool = False,
    timeout_seconds: int = 600,
) -> str:
    """Create a Workbench Steady-State Thermal system using a direct batch journal.

    This one-shot tool does not require the bridge to be running.
    """
    if not RUNWB2.exists():
        return _json({"ok": False, "error": f"RunWB2 not found: {RUNWB2}"})

    out_dir = _as_path(project_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    project_file = out_dir / f"{project_name}.wbpj"
    journal_file = out_dir / f"{project_name}_create_steady_thermal.wbjn"
    log_file = out_dir / f"{project_name}_create_steady_thermal.log"

    geom_line = ""
    if geometry_file:
        geom = _as_path(geometry_file)
        if not geom.exists():
            return _json({"ok": False, "error": f"Geometry file not found: {geom}"})
        geom_line = (
            "geometry = system.GetContainer(ComponentName='Geometry')\n"
            f"geometry.SetFile(FilePath={str(geom)!r})\n"
        )

    refresh_line = "model.Refresh()\n" if refresh_model else ""
    marker = "ANSYS_WORKBENCH_MCP_DONE"
    journal = f"""# encoding: utf-8
import traceback

log = open({str(log_file)!r}, "w")

def w(message):
    log.write(str(message) + "\\n")
    log.flush()

try:
    Reset()
    ClearMessages()
    template = GetTemplate(TemplateName="Steady-State Thermal", Solver="ANSYS")
    system = template.CreateSystem()
{geom_line}    model = system.GetContainer(ComponentName="Model")
{refresh_line}    Save(FilePath={str(project_file)!r}, Overwrite=True)
    w("Project saved: " + {str(project_file)!r})
    for message in GetMessages():
        try:
            w("%s: %s" % (message.MessageType, message.Summary))
        except:
            w(str(message))
    w("{marker}")
except Exception:
    w("ERROR")
    w(traceback.format_exc())
    raise
finally:
    log.close()
"""
    journal_file.write_text(journal, encoding="utf-8")

    try:
        process_result = _run_process(_workbench_command(journal_file, batch=True), out_dir, timeout_seconds)
    except subprocess.TimeoutExpired:
        return _json({"ok": False, "error": f"Timed out after {timeout_seconds}s", "journal": str(journal_file)})

    marker_seen = _wait_for_log_marker(log_file, marker, min(timeout_seconds, 120))
    log_text = log_file.read_text(encoding="utf-8", errors="replace") if log_file.exists() else ""
    ok = project_file.exists() and marker_seen and "ERROR" not in log_text
    return _json(
        {
            "ok": ok,
            "project_file": str(project_file),
            "journal_file": str(journal_file),
            "log_file": str(log_file),
            "marker_seen": marker_seen,
            "process": process_result,
            "log_tail": log_text[-8000:],
        }
    )


@mcp.tool()
def run_mapdl_input(
    input_file: str,
    workdir: str = "",
    job_name: str = "ansys_mcp_job",
    timeout_seconds: int = 600,
) -> str:
    """Run a Mechanical APDL input file with MAPDL."""
    if not MAPDL.exists():
        return _json({"ok": False, "error": f"MAPDL not found: {MAPDL}"})

    inp = _as_path(input_file)
    if not inp.exists():
        return _json({"ok": False, "error": f"Input file not found: {inp}"})

    cwd = _as_path(workdir) if workdir else inp.parent
    cwd.mkdir(parents=True, exist_ok=True)
    out_file = cwd / f"{job_name}.out"
    args = [str(MAPDL), "-b", "-i", str(inp), "-o", str(out_file), "-j", job_name]

    try:
        result = _run_process(args, cwd, timeout_seconds)
    except subprocess.TimeoutExpired:
        return _json({"ok": False, "error": f"Timed out after {timeout_seconds}s", "input_file": str(inp)})

    out_tail = out_file.read_text(encoding="utf-8", errors="replace")[-12000:] if out_file.exists() else ""
    return _json(
        {
            "ok": result["returncode"] == 0,
            "input_file": str(inp),
            "out_file": str(out_file),
            "process": result,
            "out_tail": out_tail,
        }
    )


@mcp.tool()
def create_and_run_thermal_bar_demo(
    project_dir: str = r"D:\ansys-workbench-mcp\runs\thermal_bar_demo",
    timeout_seconds: int = 600,
) -> str:
    """Create and solve a small steady thermal bar demo through direct Workbench batch."""
    out_dir = _as_path(project_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    inp = out_dir / "thermal_bar.dat"
    result_txt = out_dir / "thermal_nodal_temperatures.txt"
    wbjn = out_dir / "run_thermal_bar.wbjn"
    wbpj = out_dir / "thermal_bar_demo.wbpj"
    log_file = out_dir / "workbench_run.log"
    marker = "ANSYS_WORKBENCH_MCP_DONE"

    apdl = f"""/TITLE,Workbench MCP thermal bar demo
/PREP7
ET,1,SOLID70
MP,KXX,1,45
BLOCK,0,0.1,0,0.02,0,0.02
ESIZE,0.005
VMESH,ALL
FINISH

/SOLU
ANTYPE,STATIC
NSEL,S,LOC,X,0
D,ALL,TEMP,100
NSEL,S,LOC,X,0.1
D,ALL,TEMP,20
ALLSEL,ALL
SOLVE
FINISH

/POST1
SET,LAST
ALLSEL,ALL
/OUTPUT,{str(result_txt.with_suffix('')).replace(chr(92), '/')!r},txt
PRNSOL,TEMP
/OUTPUT
FINISH
"""
    inp.write_text(apdl, encoding="utf-8")

    journal = f"""# encoding: utf-8
import traceback

log = open({str(log_file)!r}, "w")

def w(message):
    log.write(str(message) + "\\n")
    log.flush()

try:
    Reset()
    ClearMessages()
    template = GetTemplate(TemplateName="Mechanical APDL")
    system = template.CreateSystem()
    setup = system.GetContainer(ComponentName="Setup")
    setup.AddInputFile(FilePath={str(inp)!r})
    Save(FilePath={str(wbpj)!r}, Overwrite=True)
    Update()
    Save(FilePath={str(wbpj)!r}, Overwrite=True)
    w("Project saved: " + {str(wbpj)!r})
    w("{marker}")
except Exception:
    w("ERROR")
    w(traceback.format_exc())
    raise
finally:
    log.close()
"""
    wbjn.write_text(journal, encoding="utf-8")

    try:
        process_result = _run_process(_workbench_command(wbjn, batch=True), out_dir, timeout_seconds)
    except subprocess.TimeoutExpired:
        return _json({"ok": False, "error": f"Timed out after {timeout_seconds}s", "journal": str(wbjn)})

    marker_seen = _wait_for_log_marker(log_file, marker, min(timeout_seconds, 180))
    log_text = log_file.read_text(encoding="utf-8", errors="replace") if log_file.exists() else ""
    temp_text = result_txt.read_text(encoding="utf-8", errors="replace") if result_txt.exists() else ""
    temps: list[float] = []
    for line in temp_text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0].isdigit():
            try:
                temps.append(float(parts[1]))
            except ValueError:
                pass
    ok = result_txt.exists() and marker_seen and "ERROR" not in log_text
    return _json(
        {
            "ok": ok,
            "project_file": str(wbpj),
            "input_file": str(inp),
            "journal_file": str(wbjn),
            "log_file": str(log_file),
            "result_file": str(result_txt),
            "node_count": len(temps),
            "min_temperature": min(temps) if temps else None,
            "max_temperature": max(temps) if temps else None,
            "process": process_result,
            "log_tail": log_text[-8000:],
        }
    )


if __name__ == "__main__":
    _ensure_dirs()
    mcp.run()
