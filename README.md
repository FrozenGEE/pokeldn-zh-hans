# pokeldn-zh-hans

[POKELDN](https://github.com/Decryptu/pokeldn) 的官方简体中文语言包（language pack 插件）。

pokeldn 通过本地无线（LDN）让 ESP32 与 Switch 上的宝可梦游戏通信，用于交换与神秘礼物等。其界面默认只有英文，本插件把它完整汉化——包括所有界面文案（1896 条）、模块内写死的英文（神秘礼物模式/预设等 453 条）以及内置文档（48 篇）。

## 功能

- **界面全中文化**：`strings.toml`（1896 条），覆盖所有菜单、设置、设备、银行、GTS、会话等页面。
- **硬编码文案汉化**：`messages.toml`（453 条），覆盖神秘礼物页的 MODES/PRESETS、活动礼物道具，以及部分游戏内写死的英文（如“神秘卡片”“性格薄荷”“10 ANIV”等）。
- **文档全中文化**：`docs/`（48 篇 markdown），与官方站点文档逐篇对应，标题层级、链接、表格结构完全一致。
- **官方译名**：宝可梦名、招式、特性、道具、树果、性格、证章等均按 [神奇宝贝百科（52poke）](https://wiki.52poke.com) 官方简体译名校对。

## 安装

pokeldn 的语言包通过「社区插件」机制加载，无需修改应用本体，退出后用重启生效。

1. 关闭 pokeldn（托盘图标 → Quit）。
2. 把本仓库 `plugin/` 目录整体复制到语言包目录：
   - Windows：`%APPDATA%\pokeldn\plugins\community-zh-hans\`
   - 其它平台：`~/.config/pokeldn/plugins/community-zh-hans/`（若 DATA 目录不同，按官方文档定位）
3. 打开 pokeldn → **Settings → App language**，选择 **简体中文**。
4. 按提示重启 pokeldn。

之后界面、神秘礼物、文档全部为中文。

> 也可以直接下载发布页的 `community-zh-hans.zip`，解压后同样放入上面的插件目录。

## 目录结构

```
pokeldn-zh-hans/
├── plugin/
│   ├── plugin.toml      # 语言包元数据（id/name/api/locale）
│   ├── strings.toml     # 界面文案，1896 条
│   ├── messages.toml    # 模块内写死的英文文案，453 条
│   └── docs/            # 内置文档，48 篇（全中文）
├── scripts/
│   ├── build.py            # 由英文 strings.en.toml + 分片合并生成 strings.toml
│   ├── build_messages.py   # 合并 msg_*.json 生成 messages.toml
│   └── verify_docs.py      # 校验 docs 标题层级/链接/围栏/英文残留
├── community-zh-hans.zip  # 现成打包，解压即装
└── README.md
```

## 语言包元数据

`plugin.toml` 采用 pokeldn 官方[语言包规范](https://github.com/Decryptu/pokeldn/blob/main/docs/plugins.md)（API 1.9）：

```toml
id = "community-zh-hans"
name = "简体中文"
version = "1.0.0"
api = "1.9"
locale = "zh-Hans"
strings = "strings.toml"
messages = "messages.toml"
documents = "docs"
description = "POKELDN 界面简体中文语言包（社区翻译）。"
author = "community"
```

## 简体中文 / 繁体说明

本包定位 **简体中文（zh-Hans）**。若需要繁体中文，可在此基础上改造：复制本仓库，把 `locale` 改为 `zh-Hant`，并按官方规范逐条调整用语。

## 更新

- 版本号在 `plugin.toml` 中维护，遵守 pokeldn 的语义化版本约定。
- 升级 pokeldn 后若出现新的英文文案，属正常——把新 key 补进 `strings.toml`/`messages.toml` 再发版即可。

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