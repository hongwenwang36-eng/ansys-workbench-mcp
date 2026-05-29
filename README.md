# Ansys Workbench MCP

这个项目用于把 Codex 连接到本机 Ansys Workbench，让 Codex 可以通过 MCP 工具启动 Workbench bridge、创建分析系统、运行 Workbench journal、运行 MAPDL、运行 Fluent journal 和 CFX solver。

它不是 Ansys 官方项目，也不是鼠标点击自动化。它封装的是 Ansys 已支持的脚本和批处理入口。

## 快速开始

### 1. 准备环境

需要先安装：

- Windows
- Ansys Workbench，当前项目默认按 Ansys 2025 R1 路径配置
- Python 3.13 或其他可创建虚拟环境的 Python
- Codex，支持 MCP server 配置
- Git，或直接从 GitHub 下载 ZIP

默认 Ansys 路径：

```text
Workbench:  D:\Program Files\ANSYS Inc\v251\Framework\bin\Win64\RunWB2.exe
Mechanical: D:\Program Files\ANSYS Inc\v251\aisol\bin\winx64\AnsysWBU.exe
MAPDL:      D:\Program Files\ANSYS Inc\v251\ansys\bin\winx64\ANSYS251.exe
Fluent:     D:\Program Files\ANSYS Inc\v251\fluent\ntbin\win64\fluent.exe
CFX solve:  D:\Program Files\ANSYS Inc\v251\CFX\bin\cfx5solve.exe
CFX pre:    D:\Program Files\ANSYS Inc\v251\CFX\bin\cfx5pre.exe
```

如果你的 Ansys 不是这个路径，后面可以通过环境变量覆盖。

### 2. 下载项目

推荐放在 `D:\ansys-workbench-mcp`：

```powershell
cd D:\
git clone https://github.com/hongwenwang36-eng/ANSYS-Workbench-mcp.git ansys-workbench-mcp
cd D:\ansys-workbench-mcp
```

也可以在 GitHub 页面下载 ZIP，解压到：

```text
D:\ansys-workbench-mcp
```

### 3. 安装 Python 依赖

```powershell
cd D:\ansys-workbench-mcp
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

如果你的机器没有 Python 3.13，可以先查看可用版本：

```powershell
py -0p
```

然后把 `py -3.13` 换成你的版本，例如 `py -3.11`。

### 4. 配置 Codex MCP

打开 Codex 配置文件：

```text
%USERPROFILE%\.codex\config.toml
```

加入下面配置：

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
ANSYS_FLUENT = 'D:\Program Files\ANSYS Inc\v251\fluent\ntbin\win64\fluent.exe'
ANSYS_CFX_SOLVE = 'D:\Program Files\ANSYS Inc\v251\CFX\bin\cfx5solve.exe'
ANSYS_CFX_PRE = 'D:\Program Files\ANSYS Inc\v251\CFX\bin\cfx5pre.exe'
```

如果 Ansys 或项目安装路径不同，改成你本机的实际路径。

修改配置后，重启 Codex，让 MCP server 重新加载。

### 5. 在 Codex 中验证连接

重启 Codex 后，可以让 Codex 调用这些 MCP 工具。

先检查路径：

```text
check_ansys_installation
```

启动 Workbench bridge：

```text
start_workbench_bridge
```

检查 Workbench bridge 是否在线：

```text
check_workbench_connection
```

探测当前 Workbench 可用的分析模板：

```text
probe_workbench_analysis_templates_live
```

如果这些命令正常返回，就说明 Codex 已经通过本项目连接到 Ansys Workbench。

### 6. 基本使用方式

创建一个稳态热分析系统：

```text
create_steady_state_thermal_system_live
```

创建一个通用 Workbench 分析系统：

```text
create_workbench_analysis_system_live
```

支持的 `analysis_type`：

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

直接运行 Fluent journal：

```text
run_fluent_journal
```

直接运行 CFX solver input：

```text
run_cfx_solver
```

停止 Workbench bridge：

```text
stop_workbench_bridge
```

也可以在 PowerShell 里停止：

```powershell
cd D:\ansys-workbench-mcp
.\.venv\Scripts\python.exe .\stop_mcp.py
```

### 7. 手动在 Workbench 中加载 bridge

如果不想让 Codex 自动启动 bridge，也可以先打开 Workbench，然后手动运行：

```text
File -> Run Script... -> D:\ansys-workbench-mcp\ansys_workbench_bridge.wbjn
```

该 journal 会进入 `mcp_loop()`，开始监听 MCP 命令。

## 项目介绍

本项目参考文件队列 IPC 思路：

- MCP server 写入 `commands/*.json`
- Workbench 侧 `ansys_workbench_bridge.wbjn` 轮询命令
- Workbench 执行命令后写回 `results/*.json`
- `status.json` 暴露 bridge heartbeat

项目封装的 Ansys 自动化入口包括：

- `RunWB2.exe -B -R <journal.wbjn>`：运行 Workbench journal
- Workbench scripting：在 Workbench 会话中创建系统、保存、打开、更新项目
- MAPDL batch：运行 Mechanical APDL 输入文件
- Fluent batch：运行 Fluent journal
- CFX solver batch：运行 CFX `.def` solver input

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
- 探测 Workbench 分析模板。
- 创建 Workbench 分析系统。
- 创建稳态热、瞬态热、静力、瞬态结构、模态、谐响应、响应谱、随机振动、CFX 分析系统。
- 尝试创建 Fluent Workbench 分析系统。
- 创建并求解一个简单稳态热长方体示例。

### 直接批处理模式

不启动常驻 bridge，也能执行：

- 运行任意 Workbench journal。
- 创建 Workbench 分析系统。
- 创建 Workbench `Steady-State Thermal` 项目。
- 运行 MAPDL 输入文件。
- 运行 Fluent journal。
- 运行 CFX solver input。
- 创建并求解一个简单稳态热示例。

## Fluent 和 CFX 说明

在当前测试机器上：

- CFX 的 Workbench 模板可用：`Fluid Flow (CFX)`
- Fluent 的 `fluent.exe` 可用
- 常见 Workbench Fluent 模板名 `Fluid Flow (Fluent)` 和 `Fluent` 没有被当前 Workbench 模板接口找到

因此：

- CFX 可以通过 Workbench 系统创建，也可以通过 `run_cfx_solver` 直接运行 `.def`
- Fluent 推荐先通过 `run_fluent_journal` 运行 journal/TUI 自动化
- 如果你的 Workbench 安装中 Fluent 模板名不同，可以用 `create_workbench_analysis_system_live` 的 `template_name` 参数覆盖

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

`mcp.log`、`status.json`、`commands/`、`results/`、`scripts/`、`runs/` 都是运行状态或示例输出相关内容，不是 MCP server 的核心代码。

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
- `probe_workbench_analysis_templates_live` 可以探测 Workbench 分析模板。
- `create_workbench_analysis_system_live` 可以创建热、结构、动力学和 CFX 分析系统。
- `create_steady_state_thermal_system_live` 可以通过 bridge 创建真实 Workbench 稳态热项目。
- `create_thermal_bar_demo_live` 可以通过 bridge 完成简单稳态热求解，结果为 525 个节点，温度范围 20 到 100。
- `run_fluent_journal` 可以定位 Fluent 可执行文件并执行 journal。
- `run_cfx_solver` 可以定位 CFX solver 可执行文件并运行 `.def`。
- 直接批处理模式可以创建真实 Workbench `Steady-State Thermal` 项目。
- 直接批处理模式可以完成简单稳态热求解并导出节点温度。

## 后续计划

- 增加 Mechanical 脚本执行入口。
- 增加导入几何、设置材料、生成网格、施加载荷、施加温度和对流边界条件的高级工具。
- 增加结果图片、温度极值、应力极值、节点和单元表格导出。
- 增加更多 Workbench、Mechanical、Fluent、CFX 示例脚本。
