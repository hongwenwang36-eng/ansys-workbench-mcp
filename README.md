# Ansys Workbench MCP

Minimal local MCP server for controlling Ansys Workbench and solver automation
from Codex.

This is not an official Ansys project. It wraps supported automation entry
points:

- `RunWB2.exe -B -R <journal.wbjn>` for Workbench journals.
- Workbench scripting to create a real `Steady-State Thermal` analysis system.
- MAPDL batch runs for solver-level scripted examples.

## Local paths

This machine is configured for Ansys 2025 R1:

- Workbench: `D:\Program Files\ANSYS Inc\v251\Framework\bin\Win64\RunWB2.exe`
- Mechanical: `D:\Program Files\ANSYS Inc\v251\aisol\bin\winx64\AnsysWBU.exe`
- MAPDL: `D:\Program Files\ANSYS Inc\v251\ansys\bin\winx64\ANSYS251.exe`

Override with environment variables:

- `ANSYS_RUNWB2`
- `ANSYS_MECHANICAL`
- `ANSYS_MAPDL`

## Tools

- `check_ansys_installation`
- `run_workbench_journal`
- `create_steady_state_thermal_system`
- `run_mapdl_input`
- `create_and_run_thermal_bar_demo`

## Codex config

Add this to `C:\Users\yangy\.codex\config.toml`:

```toml
[mcp_servers.ansys-workbench]
command = 'D:\ansys-workbench-mcp\.venv\Scripts\python.exe'
args = ['D:\ansys-workbench-mcp\mcp_server.py']
cwd = 'D:\ansys-workbench-mcp'
startup_timeout_sec = 30
tool_timeout_sec = 600
enabled = true

[mcp_servers.ansys-workbench.env]
ANSYS_RUNWB2 = 'D:\Program Files\ANSYS Inc\v251\Framework\bin\Win64\RunWB2.exe'
ANSYS_MECHANICAL = 'D:\Program Files\ANSYS Inc\v251\aisol\bin\winx64\AnsysWBU.exe'
ANSYS_MAPDL = 'D:\Program Files\ANSYS Inc\v251\ansys\bin\winx64\ANSYS251.exe'
```

Restart Codex after editing the config so it loads the new MCP server.
