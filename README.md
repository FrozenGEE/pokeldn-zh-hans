# pokeldn-zh-hans

> **AI 制作声明**：本语言包的翻译全部由 AI 生成与校对（配合 AI 核对官方译名 [52poke](https://wiki.52poke.com)）。翻译可能存在细微不准确或用语不统一之处，欢迎提交 [Issue](https://github.com/ZsyzLahz/pokeldn-zh-hans/issues) 或 [Pull Request](https://github.com/ZsyzLahz/pokeldn-zh-hans/issues) 修正。

[POKELDN](https://github.com/Decryptu/pokeldn) 的社区中文语言包（language pack 插件），同时提供 **简体中文（zh-Hans）** 与 **繁體中文（zh-Hant）** 两个版本。

pokeldn 通过本地无线（LDN）让 ESP32 与 Switch 上的宝可梦游戏通信，用于交换与神秘礼物等。其界面默认只有英文，本插件把它完整汉化——包括所有界面文案（1898 条）、模块内写死的英文（神秘礼物模式/预设等 587 条）以及内置文档（48 篇）。

## 功能

- **界面全中文化**：`strings.toml`（1898 条），覆盖所有菜单、设置、设备、银行、GTS、会话等页面。
- **硬编码文案汉化**：`messages.toml`（587 条），覆盖神秘礼物页的 MODES/PRESETS、活动礼物道具，以及部分游戏内写死的英文（如“神秘卡片”“性格薄荷”“10 ANIV”等）。
- **带变量文案汉化**：`templates.toml`（49 条），覆盖礼物摘要、游戏增益说明、校验错误等含动态内容的句子。
- **文档全中文化**：`docs/`（48 篇 markdown），与官方站点文档逐篇对应，标题层级、链接、表格结构完全一致。
- **官方译名**：宝可梦名、招式、特性、道具、树果、性格、证章等均按 [神奇宝贝百科（52poke）](https://wiki.52poke.com) 官方简体译名校对。

## 安装

pokeldn 的语言包通过「社区插件」机制加载，无需修改应用本体，退出后用重启生效。有三种方式。简体与繁体分别对应 `community-zh-hans`、`community-zh-hant` 两个插件，可任选其一：

### 方式一：通过软件内置的插件源安装（推荐）

在软件内即可一键安装，无需手动复制文件：

1. 打开 pokeldn → 侧边菜单底部 **Plugins**。
2. 在 **Sources** 下输入：
   ```
   ZsyzLahz/pokeldn-zh-hans
   ```
   并按回车（Sources 会自动读取该仓库根目录的 `pokeldn-source.json`，列出简体与繁体两个包）。
3. 回到 **Browse** 列表，找到 **简体中文**（community-zh-hans 1.0.2）或 **繁體中文**（community-zh-hant 1.0.2），点 **Install**，确认风险提示。
4. 打开 **Settings → App language**，选择对应的 **简体中文** 或 **繁體中文**。
5. 按提示重启 pokeldn。

之后界面、神秘礼物、文档全部为所选语言。

> `.pokeplugin` 包会经 SHA-256 强校验：下载哈希与列出值不符即拒绝安装，可放心使用。

### 方式二：拖入 `.pokeplugin` 文件

1. 从 [Release 页面](https://github.com/ZsyzLahz/pokeldn-zh-hans/releases) 下载 `community-zh-hans-1.0.2.pokeplugin`（简体）或 `community-zh-hant-1.0.2.pokeplugin`（繁体）。
2. 打开 pokeldn → **Plugins**，把该文件拖到 **Installed** 区，或点 **Add a plugin** 选择它，确认风险提示。
3. 同方式一共 4-5 步启用语言包。

### 方式三：手动复制目录（离线）

1. 关闭 pokeldn（托盘图标 → Quit）。
2. 把本仓库 `plugin/` 或 `zh-hant/` 目录整体复制到语言包目录：
   - 简体（`plugin/`）：Windows `%APPDATA%\pokeldn\plugins\community-zh-hans\`；其它 `~/.config/pokeldn/plugins/community-zh-hans/`
   - 繁体（`zh-hant/`）：Windows `%APPDATA%\pokeldn\plugins\community-zh-hant\`；其它 `~/.config/pokeldn/plugins/community-zh-hant/`
3. 打开 pokeldn → **Settings → App language**，选择 **简体中文** 或 **繁體中文**。
4. 按提示重启 pokeldn。

## 目录结构

```
pokeldn-zh-hans/
├── plugin/                 # 简体中文语言包（zh-Hans）
│   ├── plugin.toml      # 语言包元数据（id/name/api/locale）
│   ├── strings.toml     # 界面文案，1898 条
│   ├── messages.toml    # 模块内写死的英文文案，587 条
│   ├── templates.toml   # 带变量文案模板，49 条
│   └── docs/            # 内置文档，48 篇（全中文）
├── zh-hant/                # 繁體中文语言包（zh-Hant）
│   ├── plugin.toml      # id=community-zh-hant, locale=zh-Hant
│   ├── strings.toml     # 界面文案，1898 条（繁体）
│   ├── messages.toml    # 模块内写死的英文文案，587 条（繁体）
│   ├── templates.toml   # 带变量文案模板，49 条（繁体）
│   └── docs/            # 内置文档，48 篇（繁体）
├── scripts/
│   ├── build.py            # 由英文 strings.en.toml + 分片合并生成 strings.toml
│   ├── build_messages.py   # 合并 msg_*.json 生成 messages.toml
│   └── verify_docs.py      # 校验 docs 标题层级/链接/围栏/英文残留
├── pokeldn-source.json   # 插件源清单（简繁两个条目，软件内 Sources 自动读取）
├── community-zh-hans-1.0.2.pokeplugin   # 简体插件包（拖入即装）
├── community-zh-hant-1.0.2.pokeplugin   # 繁体插件包（拖入即装）
├── community-zh-hans.zip  # 简体现成打包
└── README.md
```

## 语言包元数据

`plugin.toml` 采用 pokeldn 官方[语言包规范](https://github.com/Decryptu/pokeldn/blob/main/docs/plugins.md)（API 1.9）：

```toml
id = "community-zh-hans"
name = "简体中文"
version = "1.0.2"
api = "1.9"
locale = "zh-Hans"
strings = "strings.toml"
messages = "messages.toml"
templates = "templates.toml"
documents = "docs"
description = "POKELDN 界面简体中文语言包（社区翻译）。"
author = "community"
```

## 简体中文 / 繁体说明

本仓库同时提供 **简体中文（zh-Hans）** 与 **繁體中文（zh-Hant）** 两个语言包：

- `plugin/`：简体（`community-zh-hans`，`locale=zh-Hans`）
- `zh-hant/`：繁体（`community-zh-hant`，`locale=zh-Hant`）

两个版本共用同一套按 [52poke](https://wiki.52poke.com) 官方译名校对的宝可梦专名（简繁为字形差异，任天堂官方简繁译名同源）。繁体版是在简体版基础上做字形级简→繁转换生成。

> 简体版为人工逐条翻译并核对；繁体版由简→繁自动转换生成，可能有个别繁体用词可再优化，欢迎提交 Issue/PR。

## 更新

- 版本号在 `plugin.toml` 中维护，遵守 pokeldn 的语义化版本约定。
- 升级 pokeldn 后若出现新的英文文案，属正常——把新 key 补进 `strings.toml`/`messages.toml`（带变量的句子放 `templates.toml`）再发版即可。

## 从源码重建

本仓库自带重建脚本（用当前环境的 Python 3.10+，需要 `tomllib`）：

```bash
# 1. strings.toml —— 需要官方 strings.en.toml 作为源
#    把英文串放到与脚本同层，作为 part_*.toml 的分片源，
#    然后：
python scripts/build.py

# 2. messages.toml —— 需要模块内英文文案的 msg_*.json
python scripts/build_messages.py

# 3. 校验文档
python scripts/verify_docs.py
```

> 重建主要是为了维护者核对与回归，普通用户直接使用发布包即可。

## 授权与致谢

- 语言包机制与插件规范来自 [pokeldn（Decryptu）](https://github.com/Decryptu/pokeldn)。
- 官方译名校对参考 [神奇宝贝百科（52poke）](https://wiki.52poke.com)。
- 本语言包为社区贡献，与 pokeldn 官方无直接关联。

## License

社区语言包，文本内容按 pokeldn 生态的宽松许可分发（具体见上游仓库条款）。