# Ansys Workbench MCP

这是一个用于 Codex / MCP 客户端的 Ansys Workbench 本地桥接项目。它参考了队列 IPC 思路：MCP server 写入命令文件，Workbench 侧 bridge journal 轮询命令并写回结果。

它不是 Ansys 官方项目，也不是通过鼠标点击 Workbench 界面。它封装的是 Ansys 已支持的自动化入口：

- `RunWB2.exe -B -R <journal.wbjn>`：运行 Workbench journal。
- Workbench scripting：在 Workbench 会话中创建系统、保存/打开/更新项目。
- MAPDL batch：运行 Mechanical APDL 输入文件，用于求解器级自动化验证。

## 架构

```text
MCP Client / Codex
        |
        | MCP stdio
        v
mcp_server.py
        |
        | file IPC
        v
commands/*.json  --->  ansys_workbench_bridge.wbjn  --->  Workbench
results/*.json   <---  ansys_workbench_bridge.wbjn  <---  Workbench
status.json      <---  bridge heartbeat
```

## 当前能力

### 常驻 bridge 模式

这一模式最接近 Abaqus MCP：

- 启动 Workbench bridge。
- 检查 Workbench bridge 是否在线。
- 在 Workbench 会话内执行脚本。
- 查询当前项目系统和组件信息。
- 打开 Workbench 项目。
- 保存 Workbench 项目。
- 更新 Workbench 项目。
- 创建真实的 `Steady-State Thermal` 系统。
- 创建并求解一个简单稳态热长方体示例。
- 通过 `status.json` 暴露 bridge 状态。

### 直接批处理模式

不启动常驻 bridge，也能执行：

- 运行任意 Workbench journal。
- 创建一个 Workbench `Steady-State Thermal` 项目。
- 运行 MAPDL 输入文件。
- 创建并求解一个简单稳态热示例。

## 文件结构

```text
ansys-workbench-mcp/
  mcp_server.py                  # MCP server，负责 stdio 工具和文件 IPC
  ansys_workbench_bridge.wbjn    # Workbench 侧 bridge journal
  stop_mcp.py                    # 从外部停止 bridge
  .mcp.json                      # MCP 客户端示例配置
  requirements.txt               # Python 依赖
  README.md
```

运行时会生成：

```text
commands/       # MCP server 写入命令
results/        # Workbench bridge 写回结果
scripts/        # 临时脚本
runs/           # 示例工程和求解输出
status.json     # bridge 状态
mcp.log         # bridge 日志
stop.flag       # 停止信号
```

这些运行时文件不会提交到 Git。

## 安装

建议安装在：

```powershell
D:\ansys-workbench-mcp
```

创建虚拟环境并安装依赖：

```powershell
cd D:\ansys-workbench-mcp
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Ansys 路径

本机当前按 Ansys 2025 R1 配置：

```text
Workbench:  D:\Program Files\ANSYS Inc\v251\Framework\bin\Win64\RunWB2.exe
Mechanical: D:\Program Files\ANSYS Inc\v251\aisol\bin\winx64\AnsysWBU.exe
MAPDL:      D:\Program Files\ANSYS Inc\v251\ansys\bin\winx64\ANSYS251.exe
```

如果安装路径不同，用环境变量覆盖：

- `ANSYS_WORKBENCH_MCP_HOME`
- `ANSYS_RUNWB2`
- `ANSYS_MECHANICAL`
- `ANSYS_MAPDL`

## Codex 配置

把下面内容加入 Codex 配置文件：

```text
%USERPROFILE%\.codex\config.toml
```

```toml
[mcp_servers.ansys-workbench]
command = 'D:\ansys-workbench-mcp\.venv\Scripts\python.exe'
args = ['D:\ansys-workbench-mcp\mcp_server.py']
cwd = 'D:\ansys-workbench-mcp'
startup_timeout_sec = 30
tool_timeout_sec = 600
enabled = true

[mcp_servers.ansys-workbench.env]
ANSYS_WORKBENCH_MCP_HOME = 'D:\ansys-workbench-mcp'
ANSYS_RUNWB2 = 'D:\Program Files\ANSYS Inc\v251\Framework\bin\Win64\RunWB2.exe'
ANSYS_MECHANICAL = 'D:\Program Files\ANSYS Inc\v251\aisol\bin\winx64\AnsysWBU.exe'
ANSYS_MAPDL = 'D:\Program Files\ANSYS Inc\v251\ansys\bin\winx64\ANSYS251.exe'
```

修改配置后重启 Codex，让 MCP server 重新加载。

## 使用方式

### 自动启动 Workbench bridge

在 MCP 客户端里调用：

```text
start_workbench_bridge
```

它会用 `RunWB2.exe` 加载 `ansys_workbench_bridge.wbjn`，然后 bridge 会开始轮询 `commands/` 目录。

检查连接：

```text
check_workbench_connection
```

停止 bridge：

```text
stop_workbench_bridge
```

### 手动在 Workbench 中加载 bridge

也可以在 Workbench 中手动运行：

```text
File -> Run Script... -> D:\ansys-workbench-mcp\ansys_workbench_bridge.wbjn
```

该 journal 默认会进入 `mcp_loop()`，开始监听 MCP 命令。

### 外部停止 bridge

```powershell
cd D:\ansys-workbench-mcp
.\.venv\Scripts\python.exe .\stop_mcp.py
```

## MCP 工具

### 连接和状态

- `check_ansys_installation`
- `start_workbench_bridge`
- `stop_workbench_bridge`
- `check_workbench_connection`
- `ansys-workbench://status`
- `ansys-workbench://installation`

### Workbench 会话内工具

- `execute_workbench_script`
- `get_project_info`
- `open_project`
- `save_project`
- `update_project`
- `probe_workbench_analysis_templates_live`
- `create_workbench_analysis_system_live`
- `create_steady_state_thermal_system_live`
- `create_transient_thermal_system_live`
- `create_static_structural_system_live`
- `create_transient_structural_system_live`
- `create_modal_analysis_system_live`
- `create_harmonic_response_system_live`
- `create_response_spectrum_system_live`
- `create_random_vibration_system_live`
- `create_cfx_flow_system_live`
- `create_fluent_flow_system_live`
- `create_thermal_bar_demo_live`

### 直接批处理工具

- `run_workbench_journal`
- `create_workbench_analysis_system`
- `create_steady_state_thermal_system`
- `run_mapdl_input`
- `run_fluent_journal`
- `run_cfx_solver`
- `create_and_run_thermal_bar_demo`

### Analysis wrappers added in v0.2.x

The generic Workbench wrapper `create_workbench_analysis_system_live` accepts:

- `steady_state_thermal`
- `transient_thermal`
- `static_structural`
- `transient_structural`
- `modal`
- `harmonic_response`
- `response_spectrum`
- `random_vibration`
- `cfx`
- `fluent`

`probe_workbench_analysis_templates_live` checks which Workbench templates are available in the current Ansys installation. On this workstation, Workbench templates are available for thermal, structural/dynamics, and CFX. Fluent is installed as `fluent.exe`, but the Workbench Fluent template was not found by the common template names, so Fluent automation is exposed through `run_fluent_journal`.

## 与 Abaqus MCP 的差异

Abaqus MCP 可以通过 Abaqus/CAE 插件菜单和 Abaqus Python 环境长时间保持 GUI 会话内通信。Workbench 这边没有同等成熟的公开插件模板，所以本项目使用 Workbench journal 作为 bridge。

这意味着：

- 能实现类似的文件 IPC 和会话内脚本执行。
- 可以控制 Workbench 项目原理图、系统创建、保存、更新等。
- Mechanical 细粒度树对象操作还需要继续扩展 Mechanical 脚本接口。
- 复杂 GUI 交互不通过鼠标模拟完成，而应继续封装为脚本工具。

## 已验证

在本机已经验证：

- MCP stdio 可以列出工具。
- Ansys 2025 R1 路径检查正常。
- `start_workbench_bridge` 可以启动 Workbench bridge，并通过 `ping` 响应。
- `execute_workbench_script` 可以在 Workbench 会话内执行脚本并返回输出。
- `get_project_info` 可以读取当前 Workbench 项目系统信息。
- `create_steady_state_thermal_system_live` 可以通过 bridge 创建真实 Workbench 稳态热项目。
- `create_thermal_bar_demo_live` 可以通过 bridge 完成简单稳态热求解，结果为 525 个节点，温度范围 20 到 100。
- 直接批处理模式可以创建真实 Workbench `Steady-State Thermal` 项目。
- 直接批处理模式可以完成简单稳态热求解并导出节点温度。

## 后续计划

- 增加 Mechanical 脚本执行入口。
- 增加导入几何、设置材料、生成网格、施加温度/对流边界条件的高级工具。
- 增加结果图片、温度极值、节点/单元表格导出。
- 增加更多 Workbench/Mechanical 示例脚本。
