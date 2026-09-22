# 魔女兵器单机保存版

这是《魔女兵器》国服 Android 2.0.1 的单机化工程。客户端通过本地响应和本地存档运行，不依赖已经停运的游戏服务器。

目前已接入的主要内容：

- 本地建号、登录、存档和重启恢复
- 149 个可见剧情入口，缺失演出资源从 PC 保存版补回
- 一轮 12 关结界迷宫和训练营
- 角色与武器战斗、四武器能量、主动技能、部分专属技能和敌人机制
- 角色养成、升阶、升星、羁绊、装备和背包
- 本地抽卡、免费补给、材料回收与礼包
- 主界面角色展示、服装和动作保存

最新测试包的信息见 [STATUS.md](STATUS.md)。

## 环境

- Windows 10/11
- Python 3.13
- JDK 17
- Android SDK Platform 34
- Android Build Tools 36.1.0
- Il2CppDumper，用于从原 APK 生成 `script.json` 和 `dump.cs`
- 雷电模拟器 9，可选，仅用于运行验收

安装 Python 依赖：

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## 输入文件

把原始文件放在以下位置：

```text
inputs/20240516161158_mnbq.apk
inputs/Witch Weapon.exe
```

文件校验值和可选环境变量见 [INPUTS.md](INPUTS.md)。原 APK、PC 程序、生成资源、签名文件和 APK 成品不放在源码提交中。

## 处理顺序

剧情资源首次准备：

```powershell
python inspect_game.py
python decode_config.py
python pc_story_source.py
python pc_story_content_match.py
python pc_story_match.py
python pc_exact_alignment.py
python pc_role_restore.py
python pc_graph_repairs.py
python pc_story_restore.py
python pc_lesson_convert.py
python pc_story_restore.py
```

生成离线配置并构建：

```powershell
python prepare_offline.py
python build_apk.py
```

输出文件为 `build/witchweapon-stage1-test.apk`。构建脚本会生成独立包名 `com.codex.witchweapon.local`，不会覆盖原游戏安装。

## 代码分工

- `OfflineApplication.java`：本地 HTTP 响应入口
- `LocalSave.java`：本地账号和进度存档
- `LocalEconomy.java`：养成、背包、抽卡和补给事务
- `offline_combat.py`、`offline_enemies.py`、`offline_weapon_rules.py`：战斗和技能数据
- `offline_maze.py`、`offline_maze_round.py`：12 关迷宫流程
- `offline_story.py`、`pc_*.py`：剧情目录和 PC 资源转换
- `offline_progression.py`、`offline_roster.py`：角色、武器和养成数据
- `offline_responses.json`：生成后的本地服务响应集
