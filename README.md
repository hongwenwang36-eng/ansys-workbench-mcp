# Ansys Workbench MCP

一个用于连接 **Codex / MCP 客户端** 和 **Ansys Workbench** 的本地桥接项目。它通过文件队列 IPC 让外部 AI 助手向 Workbench 发送命令，并由 Workbench 侧 journal 执行脚本、创建系统、保存项目和返回结果。

本项目不是 Ansys 官方项目，也不通过鼠标点击 GUI。它封装的是 Ansys 已支持的自动化入口：Workbench journal、Workbench scripting、MAPDL batch、Fluent journal 和 CFX solver batch。

## 最新更新

- **通用 Workbench 分析系统创建**：通过 `create_workbench_analysis_system_live` 创建指定模板的分析系统
- **分析模板探测**：通过 `probe_workbench_analysis_templates_live` 检查当前 Ansys 安装中可用的 Workbench 模板
- **热分析封装**：支持稳态热和瞬态热系统创建
- **结构和动力学封装**：支持静力、瞬态结构、模态、谐响应、响应谱、随机振动系统创建
- **CFX 封装**：支持 Workbench CFX 系统创建，也支持直接运行 CFX `.def`
- **Fluent 封装**：支持直接运行 Fluent journal；如果本机 Workbench 有 Fluent 模板，也可以用模板名覆盖方式创建系统
- **安装检查增强**：`check_ansys_installation` 会同时检查 Workbench、Mechanical、MAPDL、Fluent、CFX 路径
- **README 重构**：按安装、连接、使用、工具、协议和排错的顺序组织

## 架构

```text
+--------------+     MCP stdio      +---------------+      file IPC       +--------------------+
| MCP Client   |  ----------------> | mcp_server.py |  ----------------> | Ansys Workbench    |
| Codex        |  <---------------- | FastMCP       |  <---------------- | bridge journal     |
+--------------+                    +---------------+                     +--------------------+
                                           |
                                           v
                                  commands/*.json  ->  Workbench reads
                                  results/*.json   <-  Workbench writes
                                  status.json      <-  bridge heartbeat
```

Workbench 侧由 `ansys_workbench_bridge.wbjn` 轮询 `commands/` 目录。MCP server 写入命令文件，Workbench 执行后把结果写入 `results/`，Codex 再读取结果并返回给用户。

## 功能

- 检查本机 Ansys Workbench、Mechanical、MAPDL、Fluent、CFX 路径
- 启动、停止和检查 Workbench bridge
- 在正在运行的 Workbench 会话中执行脚本
- 读取当前 Workbench 项目的系统和组件信息
- 打开、保存、更新 Workbench 项目
- 探测 Workbench 分析模板
- 创建 Workbench 分析系统
- 创建稳态热、瞬态热、静力、瞬态结构、模态、谐响应、响应谱、随机振动、CFX 系统
- 尝试创建 Fluent Workbench 系统
- 直接运行任意 Workbench journal
- 直接运行 MAPDL 输入文件
- 直接运行 Fluent journal
- 直接运行 CFX solver input
- 创建并求解一个简单稳态热示例

## 安装

### 1. 克隆项目

推荐安装到 `D:\ansys-workbench-mcp`：

```powershell
cd D:\
git clone https://github.com/hongwenwang36-eng/ANSYS-Workbench-mcp.git ansys-workbench-mcp
cd D:\ansys-workbench-mcp
```

也可以在 GitHub 页面下载 ZIP，然后解压到：

```text
D:\ansys-workbench-mcp
```

### 2. 安装 Python 依赖

推荐使用虚拟环境：

```powershell
cd D:\ansys-workbench-mcp
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

如果没有 Python 3.13，先查看本机 Python：

```powershell
py -0p
```

然后把 `py -3.13` 换成实际版本，例如 `py -3.11`。

### 3. 确认 Ansys 路径

默认按 Ansys 2025 R1 配置：

```text
Workbench:  D:\Program Files\ANSYS Inc\v251\Framework\bin\Win64\RunWB2.exe
Mechanical: D:\Program Files\ANSYS Inc\v251\aisol\bin\winx64\AnsysWBU.exe
MAPDL:      D:\Program Files\ANSYS Inc\v251\ansys\bin\winx64\ANSYS251.exe
Fluent:     D:\Program Files\ANSYS Inc\v251\fluent\ntbin\win64\fluent.exe
CFX solve:  D:\Program Files\ANSYS Inc\v251\CFX\bin\cfx5solve.exe
CFX pre:    D:\Program Files\ANSYS Inc\v251\CFX\bin\cfx5pre.exe
```

如果你的安装路径不同，后续在 Codex MCP 配置里改对应环境变量。

### 4. 配置 Codex MCP

打开 Codex 配置文件：

```text
%USERPROFILE%\.codex\config.toml
```

加入：

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

修改后重启 Codex，让 MCP server 重新加载。

## 使用

### 检查安装

在 Codex 中调用：

```text
check_ansys_installation
```

该工具会检查 Workbench、Mechanical、MAPDL、Fluent、CFX 和 bridge journal 是否存在。

### 启动 Workbench bridge

在 Codex 中调用：

```text
start_workbench_bridge
```

它会用 `RunWB2.exe` 加载：

```text
D:\ansys-workbench-mcp\ansys_workbench_bridge.wbjn
```

然后 Workbench bridge 开始轮询 `commands/`。

### 检查连接状态

```text
check_workbench_connection
```

如果连接正常，会返回 Workbench bridge 版本、状态、PID 和命令计数。

### 手动加载 bridge

也可以先打开 Workbench，然后手动运行：

```text
File -> Run Script... -> D:\ansys-workbench-mcp\ansys_workbench_bridge.wbjn
```

该 journal 会进入 `mcp_loop()` 并监听 MCP 命令。

### 停止 bridge

方式一，在 Codex 中调用：

```text
stop_workbench_bridge
```

方式二，在 PowerShell 中运行：

```powershell
cd D:\ansys-workbench-mcp
.\.venv\Scripts\python.exe .\stop_mcp.py
```

### 工作模式

| 模式 | 是否需要 Workbench bridge | 适用场景 |
| --- | --- | --- |
| 常驻 bridge | 需要 | 在一个 Workbench 会话中持续创建系统、执行脚本、查询项目 |
| 直接 Workbench batch | 不需要 | 一次性运行 `.wbjn` 或创建项目 |
| MAPDL batch | 不需要 | 直接运行 APDL `.dat` 输入文件 |
| Fluent journal | 不需要 | 直接运行 Fluent TUI/journal 自动化 |
| CFX solver | 不需要 | 直接运行 CFX `.def` solver input |

## MCP 工具

这些工具由 `mcp_server.py` 暴露给 Codex 或其他 MCP 客户端。

| 工具 | 说明 |
| --- | --- |
| `check_ansys_installation` | 检查 Ansys 可执行文件和 bridge journal 路径 |
| `start_workbench_bridge` | 启动 Workbench bridge |
| `stop_workbench_bridge` | 停止 Workbench bridge |
| `check_workbench_connection` | 检查 Workbench bridge 是否在线并响应 |
| `execute_workbench_script` | 在 Workbench bridge 会话内执行脚本 |
| `get_project_info` | 获取当前 Workbench 项目系统和组件信息 |
| `open_project` | 在 Workbench bridge 会话内打开 `.wbpj` |
| `save_project` | 保存当前 Workbench 项目 |
| `update_project` | 执行 Workbench `Update()` |
| `probe_workbench_analysis_templates_live` | 探测当前 Workbench 可用分析模板 |
| `create_workbench_analysis_system_live` | 在 bridge 会话中创建通用分析系统 |
| `create_steady_state_thermal_system_live` | 创建稳态热系统 |
| `create_transient_thermal_system_live` | 创建瞬态热系统 |
| `create_static_structural_system_live` | 创建静力结构系统 |
| `create_transient_structural_system_live` | 创建瞬态结构系统 |
| `create_modal_analysis_system_live` | 创建模态分析系统 |
| `create_harmonic_response_system_live` | 创建谐响应系统 |
| `create_response_spectrum_system_live` | 创建响应谱系统 |
| `create_random_vibration_system_live` | 创建随机振动系统 |
| `create_cfx_flow_system_live` | 创建 CFX 流体系统 |
| `create_fluent_flow_system_live` | 尝试创建 Fluent Workbench 系统 |
| `create_thermal_bar_demo_live` | 通过 bridge 创建并求解稳态热示例 |
| `run_workbench_journal` | 直接运行 Workbench journal |
| `create_workbench_analysis_system` | 直接批处理创建 Workbench 分析系统 |
| `create_steady_state_thermal_system` | 直接批处理创建稳态热系统 |
| `run_mapdl_input` | 直接运行 MAPDL 输入文件 |
| `run_fluent_journal` | 直接运行 Fluent journal |
| `run_cfx_solver` | 直接运行 CFX solver input |
| `create_and_run_thermal_bar_demo` | 直接批处理创建并求解稳态热示例 |

## MCP 资源

| URI | 说明 |
| --- | --- |
| `ansys-workbench://status` | 当前 bridge 状态、PID、命令计数和时间戳 |
| `ansys-workbench://installation` | 当前配置的 Ansys 可执行文件路径 |

## 分析系统类型

`create_workbench_analysis_system_live` 和 `create_workbench_analysis_system` 支持：

| `analysis_type` | Workbench 模板 |
| --- | --- |
| `steady_state_thermal` | `Steady-State Thermal` |
| `transient_thermal` | `Transient Thermal` |
| `static_structural` | `Static Structural` |
| `transient_structural` | `Transient Structural` |
| `modal` | `Modal` |
| `harmonic_response` | `Harmonic Response` |
| `response_spectrum` | `Response Spectrum` |
| `random_vibration` | `Random Vibration` |
| `cfx` | `Fluid Flow (CFX)` 或 `CFX` |
| `fluent` | `Fluid Flow (Fluent)` 或 `Fluent`，取决于本机 Workbench 模板是否可用 |

如果本机模板名不同，可以用 `template_name` 和 `solver` 参数覆盖。

## Fluent 和 CFX 说明

在当前测试机器上：

- CFX 的 Workbench 模板可用：`Fluid Flow (CFX)`
- Fluent 的 `fluent.exe` 可用
- 常见 Workbench Fluent 模板名 `Fluid Flow (Fluent)` 和 `Fluent` 没有被当前 Workbench 模板接口找到

因此：

- CFX 可以通过 Workbench 系统创建，也可以通过 `run_cfx_solver` 直接运行 `.def`
- Fluent 推荐先通过 `run_fluent_journal` 运行 journal/TUI 自动化
- 如果你的 Workbench 安装中 Fluent 模板名不同，可以用 `create_workbench_analysis_system_live` 的 `template_name` 参数覆盖

## 文件 IPC 协议

MCP server 会向 `commands/` 写入 JSON 命令文件：

```python
import json
import time
from pathlib import Path

command = {
    "id": "my_command",
    "type": "execute_script",
    "script": "print('Hello from Workbench')",
    "timestamp": time.time(),
}

cmd_path = Path(r"D:\ansys-workbench-mcp\commands\cmd_my_command.json")
cmd_path.write_text(json.dumps(command, indent=2), encoding="utf-8")
```

Workbench bridge 执行后，会把结果写入：

```text
D:\ansys-workbench-mcp\results\my_command.json
```

### 命令类型

| type | 参数 | 说明 |
| --- | --- | --- |
| `ping` | 无 | 测试 bridge 是否在线 |
| `execute_script` | `script` | 在 Workbench 会话内执行脚本 |
| `get_project_info` | 无 | 获取项目系统和组件信息 |
| `open_project` | `project_file` | 打开 Workbench 项目 |
| `save_project` | `project_file`, `overwrite` | 保存项目 |
| `update_project` | 无 | 执行 `Update()` |
| `probe_analysis_templates` | `analysis_templates` | 探测模板是否存在 |
| `create_analysis_system` | `project_dir`, `project_name`, `template_candidates` 等 | 创建 Workbench 分析系统 |
| `create_steady_state_thermal_system` | `project_dir`, `project_name`, `geometry_file` | 创建稳态热系统 |
| `create_thermal_bar_demo` | `project_dir` | 创建并求解稳态热示例 |
| `stop` | 无 | 请求 bridge 停止 |

## 目录结构

```text
D:\ansys-workbench-mcp\
├── mcp_server.py                  # MCP server，运行在 Codex 外部进程中
├── ansys_workbench_bridge.wbjn    # Workbench 侧 bridge journal
├── stop_mcp.py                    # 发送停止信号
├── requirements.txt               # Python 依赖
├── .mcp.json                      # MCP 客户端配置示例
├── commands\                      # MCP server 写入命令
├── results\                       # Workbench bridge 写回结果
├── scripts\                       # bridge 执行临时脚本
├── runs\                          # 示例工程和求解输出
├── status.json                    # bridge heartbeat 状态
├── mcp.log                        # bridge 日志
└── stop.flag                      # 停止信号文件
```

运行时目录和文件可能会随使用增加。`mcp.log` 和 `status.json` 是状态文件，不建议作为业务代码改动提交。

## 故障排查

- **Codex 看不到工具**
  - 检查 `%USERPROFILE%\.codex\config.toml` 是否配置了 `mcp_servers.ansys-workbench`
  - 确认 `command` 指向 `.venv\Scripts\python.exe`
  - 重启 Codex

- **`check_ansys_installation` 显示路径不存在**
  - 检查 Ansys 实际安装路径
  - 修改 `ANSYS_RUNWB2`、`ANSYS_MECHANICAL`、`ANSYS_MAPDL`、`ANSYS_FLUENT`、`ANSYS_CFX_SOLVE`、`ANSYS_CFX_PRE`

- **bridge 状态是 running 但命令超时**
  - 调用 `stop_workbench_bridge`
  - 再调用 `start_workbench_bridge`
  - 查看 `D:\ansys-workbench-mcp\status.json` 的时间戳是否更新
  - 查看 `D:\ansys-workbench-mcp\mcp.log`

- **Workbench 启动了但没有响应**
  - 手动在 Workbench 中运行 `File -> Run Script... -> ansys_workbench_bridge.wbjn`
  - 确认没有旧的 `stop.flag`
  - 确认 `ANSYS_WORKBENCH_MCP_HOME` 指向项目目录

- **Fluent Workbench 模板找不到**
  - 先使用 `run_fluent_journal`
  - 或调用 `probe_workbench_analysis_templates_live` 查看本机模板名
  - 如果知道实际模板名，用 `template_name` 参数覆盖

- **直接批处理运行时间很长**
  - 增大工具的 `timeout_seconds`
  - 对 Fluent/CFX/MAPDL 先用小模型验证 journal 或输入文件

## 已验证

在本机已经验证：

- MCP stdio 可以列出工具
- Ansys 2025 R1 路径检查正常
- Workbench bridge 可以启动并通过 ping 响应
- Workbench 会话内脚本可以执行并返回输出
- 可探测 Workbench 分析模板
- 可创建稳态热、瞬态热、静力、瞬态结构、模态、谐响应、响应谱、随机振动和 CFX 系统
- Fluent 可执行文件存在，推荐通过 journal/TUI 自动化
- CFX solver 可执行文件存在，可通过 `.def` 直接运行
- 稳态热 demo 可以创建并求解

## 许可证

本项目使用 MIT License，详见 [LICENSE](LICENSE)。
