#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal MCP bridge for Ansys Workbench and Mechanical automation.

This server intentionally wraps supported script entry points instead of
driving the Workbench GUI by mouse. It can create real Workbench analysis
systems, run Workbench journals, and execute simple Mechanical APDL jobs.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP


SERVER_ROOT = Path(__file__).resolve().parent
DEFAULT_RUNWB2 = r"D:\Program Files\ANSYS Inc\v251\Framework\bin\Win64\RunWB2.exe"
DEFAULT_MECHANICAL = r"D:\Program Files\ANSYS Inc\v251\aisol\bin\winx64\AnsysWBU.exe"
DEFAULT_MAPDL = r"D:\Program Files\ANSYS Inc\v251\ansys\bin\winx64\ANSYS251.exe"

RUNWB2 = Path(os.environ.get("ANSYS_RUNWB2", DEFAULT_RUNWB2))
MECHANICAL = Path(os.environ.get("ANSYS_MECHANICAL", DEFAULT_MECHANICAL))
MAPDL = Path(os.environ.get("ANSYS_MAPDL", DEFAULT_MAPDL))

mcp = FastMCP("ansys-workbench-mcp")


def _as_path(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


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


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _workbench_command(journal_path: Path, batch: bool) -> list[str]:
    args = [str(RUNWB2)]
    if batch:
        args.append("-B")
    args.extend(["-R", str(journal_path)])
    return args


@mcp.tool()
def check_ansys_installation() -> str:
    """Check configured Workbench, Mechanical, and MAPDL executable paths."""
    data = {
        "runwb2": str(RUNWB2),
        "runwb2_exists": RUNWB2.exists(),
        "mechanical": str(MECHANICAL),
        "mechanical_exists": MECHANICAL.exists(),
        "mapdl": str(MAPDL),
        "mapdl_exists": MAPDL.exists(),
        "server_root": str(SERVER_ROOT),
    }
    return _json(data)


@mcp.tool()
def run_workbench_journal(
    journal_path: str,
    workdir: str = "",
    batch: bool = True,
    timeout_seconds: int = 600,
) -> str:
    """Run an Ansys Workbench journal through RunWB2.

    The journal should be a .wbjn file. If batch=True, Workbench runs with -B.
    """
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
    """Create a real Workbench Steady-State Thermal system and save the project.

    This is equivalent to placing the Workbench toolbox item "Steady-State Thermal"
    on the project schematic. Optionally attaches an existing geometry file.
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
    _write_text(journal_file, journal)

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
    """Run a Mechanical APDL input file with MAPDL.

    This is useful for solver-level checks and scripted validation jobs.
    """
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
    """Create and solve a small steady thermal bar demo through Workbench.

    The Workbench project uses a Mechanical APDL system as the solver container.
    Use create_steady_state_thermal_system when you specifically want the
    Workbench schematic Steady-State Thermal system.
    """
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
    _write_text(inp, apdl)

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
    _write_text(wbjn, journal)

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


@mcp.resource("ansys-workbench://installation")
def installation_resource() -> str:
    """Configured Ansys executable paths for this MCP server."""
    return check_ansys_installation()


if __name__ == "__main__":
    mcp.run()
