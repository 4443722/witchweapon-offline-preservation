# 构建输入

| 文件 | 大小 | SHA-256 |
|---|---:|---|
| `inputs/20240516161158_mnbq.apk` | 1,406,878,325 字节 | `fbb3de112015fadac90adc6e0637c3fefd8bf0d46601d3fcf287c2e4d16c11fc` |
| `inputs/Witch Weapon.exe` | 588,135,016 字节 | `521e1533e38c27660701ea4406fff839c63eea8beae5f34b10779a49bde602ea` |

脚本默认读取 `inputs` 目录，也可以用环境变量指定现有位置：

```powershell
$env:WW_SOURCE_APK = 'C:\path\to\20240516161158_mnbq.apk'
$env:WW_PC_EXE = 'D:\path\to\Witch Weapon.exe'
$env:WW_ANDROID_SDK = "$env:LOCALAPPDATA\Android\Sdk"
$env:WW_ANDROID_BUILD_TOOLS = "$env:LOCALAPPDATA\Android\Sdk\build-tools\36.1.0"
$env:WW_JAVA_BIN = 'C:\Program Files\Microsoft\jdk-17.0.11.9-hotspot\bin'
```

如需运行雷电模拟器验收：

```powershell
$env:WW_LDPLAYER = 'D:\leidian\LDPlayer9\ld.exe'
$env:WW_LD_INDEX = '6'
$env:WW_LD_SHARED = "$HOME\Documents\leidian9"
```

`decoded`、`original_parts`、`pc_story_source`、`overrides`、`build` 和 `evidence` 都是生成目录。
