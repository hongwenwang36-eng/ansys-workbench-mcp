# Ansys Workbench MCP

这是一个用于 Codex 的本地 MCP server，用来通过脚本方式控制 Ansys Workbench、Mechanical 和 MAPDL。

它不是 Ansys 官方项目，也不是通过鼠标点击 Workbench 界面。它封装的是 Ansys 已支持的自动化入口：

- `RunWB2.exe -B -R <journal.wbjn>`：批处理运行 Workbench journal。
- Workbench scripting：创建真实的 `Steady-State Thermal` 项目系统。
- MAPDL batch：运行 Mechanical APDL 输入文件，用于求解器级自动化验证。

## 当前状态

当前版本是最小可用版，可以验证 Codex 到 Workbench 的控制链路：

- 检查 Workbench、Mechanical、MAPDL 路径。
- 运行任意 Workbench journal。
- 创建一个真实的 Workbench `Steady-State Thermal` 系统。
- 运行 MAPDL 输入文件。
- 创建并求解一个简单稳态热长方体示例。

它还不是 Abaqus MCP 那种完整双端结构。Abaqus MCP 里有 Abaqus/CAE 插件、命令目录、结果目录和更多会话内查询工具；Workbench 这个版本目前先走 journal / 批处理接口，后续可以继续扩展 Mechanical 脚本执行、模型树查询、网格/载荷封装和结果导出工具。

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

如果你的安装路径不同，可以用环境变量覆盖：

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
ANSYS_RUNWB2 = 'D:\Program Files\ANSYS Inc\v251\Framework\bin\Win64\RunWB2.exe'
ANSYS_MECHANICAL = 'D:\Program Files\ANSYS Inc\v251\aisol\bin\winx64\AnsysWBU.exe'
ANSYS_MAPDL = 'D:\Program Files\ANSYS Inc\v251\ansys\bin\winx64\ANSYS251.exe'
```

修改配置后重启 Codex，让 MCP server 重新加载。

## MCP 工具

### `check_ansys_installation`

检查 Workbench、Mechanical、MAPDL 可执行文件路径是否存在。

### `run_workbench_journal`

通过 `RunWB2.exe` 执行指定的 `.wbjn` Workbench journal。

### `create_steady_state_thermal_system`

创建一个真实的 Workbench `Steady-State Thermal` 系统，并保存 `.wbpj` 项目文件。这个动作等价于在 Workbench 工具箱里放置“稳态热”分析系统。

### `run_mapdl_input`

用 MAPDL 批处理运行一个 Mechanical APDL 输入文件。

### `create_and_run_thermal_bar_demo`

创建并求解一个简单稳态热长方体示例，用来验证 Workbench / MAPDL 自动化链路是否可用。

## 已验证

在本机已经验证：

- MCP stdio 握手可以列出工具。
- `check_ansys_installation` 可以检查到 Ansys 2025 R1 路径。
- `create_steady_state_thermal_system` 可以创建真实 Workbench 稳态热项目。
- `create_and_run_thermal_bar_demo` 可以完成简单稳态热求解并导出节点温度结果。

## 后续计划

- 增加 Mechanical 脚本执行入口。
- 增加导入几何、设置材料、生成网格、施加温度/对流边界条件的高级工具。
- 增加结果图片、温度极值、节点/单元表格导出。
- 增加更完整的示例和测试脚本。
