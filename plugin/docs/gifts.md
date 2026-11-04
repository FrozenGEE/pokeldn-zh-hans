---
title: 神秘礼物文件
---
# 神秘礼物文件

`.pokegift` 文件保存一份完整的、面向火红/叶绿或剑/盾的神秘礼物分发内容，或一段 FRLG ARM 主机载荷，并附带其目标游戏与原生记录。

## 桌面应用

同一个构建器服务于两款游戏（`pokeldn/app/gift_builder.py`；表单位于
`pokeldn/frlg/gift/builder.py`、`pokeldn/swsh/gift_builder.py`）。

| 模式 | 发送的内容 |
|---|---|
| Use a preset | 内置礼物；FRLG 的神秘卡片、神秘新闻和主机代码以标志形式传给启动器 |
| Official events | 真实的剑/盾活动卡片（[官方活动卡片](swsh_gift.md#official-event-cards)），像构建好的礼物一样编译 |
| Build your own | 表单，在 Start 时编译为 `session/gifts/<tool>.pokegift` 并以 `--gift-file` 传入 |
| Open a file | 分享的 `.pokegift`，或剑/盾上的 `.wc8` |

FRLG 的 Game boosts 是常驻钩子（[`install-resident`](frlg_rom.md#install-resident)），作为一条链
（[同时使用多个钩子](frlg_rom.md#several-hooks-at-once)）在 1024 字节内运行；各项设置会变成
`--resident-param` 标志。

| 强化 | 设置 | 参数 |
|---|---|---|
| 加速游戏（`turbo-lite`） | 速度 x1 到 x4；大地图、对战或两者；始终开启，或按住 R、B 或 Select 时开启；更快的文本 | `field` 和 `battle` = speed - 1，x3 起 `budget=228`，`hold`，`extra=4` |
| 穿墙 | R、B 或 Select | `hold` |
| 闪光倒计时 | 减速按钮；慢 x2、x4 或 x8 | `slow`，`slow_frames` 1、3 或 7 |
| 闪光传说宝可梦（`shiny-press`） | 超梦；急冻鸟、闪电鸟或火焰鸟 | `offset` 1 或 2 |
| 无野生遭遇、屏幕上显示队首的个体值、宝可梦跟随者 | 无 | |

不提供 L：只有 R 的帮助系统开关带有一个钩子能压住的标志。Save boosts for later 会把这组强化写入
`filler_B20`（`save-write --resident`）并安装它；超过 876 字节的强化组以及跟随者，始终走存档。
Mom restores your boosts 会让与妈妈对话在任何一次启动后安装已保存的强化组。再次发送强化会替换正在
运行的那一组。

Read the save 提供训练家 ID（TID）与里 ID（SID）、训练家详情与游戏时间，以及上次保存的队伍的性格、
个体值与努力值，并保持存档不变（[读取存档](frlg_rom.md#reading-the-save)）。

`.wc3` 和 `.wc8` 文件按二进制读取，即使它们以 `{` 开头。当表单能够表达某个预设时，Customize 会把它
复制进表单：所有剑/盾预设，以及仅由无条件表单步骤构成的 FRLG 卡片。

FRLG 表单构建神秘卡片、神秘新闻或主机代码。

| 部分 | 内容 |
|---|---|
| 卡片 | 标题、副标题、四行文本、图标种类、卡片 id 1000 到 1019、可再次接收、可分享 |
| 交付者 | 任意宝可梦中心里的配送员、玩家家中的妈妈，或真新镇南边的那个人 |
| 步骤 | 宝可梦（种类、等级、携带道具、四个招式）、道具与数量、蛋、野生对战、消息 |
| 新闻 | 标题、最多十行、新闻 id |
| 主机代码 | ARM 源码或预编译的 `.bin`、它为其构建的卡带、期望的应答、回传的字节 |

每个步骤是一个独立的交付阶段：队伍或背包满时就此停止，重试会给出剩下的部分。另一个人通过
`initramscript` 绑定持有这些步骤，这会隐藏卡片，并在被替换之前每次都给出这些步骤。种类使用内部编号
（`pokeldn/frlg/save/species_names.py`）。

主机代码需要 `arm-none-eabi-as`（PATH、Homebrew 或 Arm 的 Windows 文件夹），或预编译的 `.bin`：

| 系统 | 命令 |
|---|---|
| macOS | `brew install arm-none-eabi-binutils` |
| Fedora | `sudo dnf install arm-none-eabi-binutils-cs` |
| Debian、Ubuntu 及其衍生版 | `sudo apt install binutils-arm-none-eabi` |
| Windows | `winget install Arm.ArmGnuToolchain` |

Check 会离线在模拟主机上运行这段代码（`pokeldn/frlg/rom/custom_code.py`），Start 和保存时也是如此；
出错或永不返回 1 的代码会被拒绝。

剑/盾表单构建一只宝可梦（可选超极巨化）、一颗蛋、最多六件道具、服装
（[服装](swsh_gift.md#clothing)，每个性别六件）、对战点数或金钱，布局与
[零售版剑兑换的记录](swsh_gift.md#a-card-delivered-to-a-retail-console)一致。

Save gift file 会写入一个包含所有卡带变体的 `.pokegift`，无需板子或密钥。主机的游戏代码会选择变体；
文件中没有的卡带会在发送前被拒绝。

## 命令行

两个礼物启动器都接受 `--gift-file FILE`；在剑/盾上 `--record` 是它的别名。
`--export-gift FILE` 会保存所选礼物并在使用无线之前退出。

```bash
./.venv/bin/python bin/frlg_mg_host.py --gift celebi --export-gift celebi.pokegift
./.venv/bin/python bin/frlg_mg_host.py --news berry --export-gift news.pokegift
./.venv/bin/python bin/swsh_gift_host.py --species 25 --level 25 --export-gift pikachu.pokegift
./.venv/bin/python -m pokeldn.gifts inspect celebi.pokegift
```

FRLG 礼物文件会一并定义卡片标志 ID、脚本、问卷和拒绝消息。诸如 `--flag-id`、`--questionnaire` 和
`--hunt-*` 之类的载荷覆盖项会被它拒绝；无线、训练家和卡带选择选项仍然生效。

### 主机代码

内置载荷会连同其应答设置一起导出：

```bash
./.venv/bin/python bin/frlg_mg_host.py --buffer-script save-dump --dump-size 64 \
  --export-gift save-dump.pokegift
```

原始 ARM 代码会带明确的卡带目标打包：

```bash
arm-none-eabi-as -march=armv4t -mcpu=arm7tdmi -o payload.o payload.s
arm-none-eabi-objcopy -O binary -j .text payload.o payload.bin
./.venv/bin/python -m pokeldn.gifts import --game frlg --code payload.bin \
  --build BPRF --name "Custom payload" --expect 66 -o custom.pokegift
```

一个最小的 `payload.s` 会把 66 写入应答参数，并在一次调用中完成：

```asm
.syntax unified
.arm
.text
.global _start
_start:
    mov r3, #66
    str r3, [r0]
    mov r0, #1
    bx lr
```

代码是与位置无关的 ARMv4T，字对齐，最多 1024 字节，每帧调用一次，调用时 `r0 = &param`、
`r1 = gSaveBlock2Ptr`、`r2 = gSaveBlock1Ptr`，直到它返回 1（[主机代码](frlg_rom.md)）。没有
`--expect` 时接受任何应答；字节缓冲区应答需要 `--dump-size N`。

接收方在 FRLG 神秘礼物工具中打开该文件，或传入 `--gift-file`；`--dump-file PATH` 选择返回的转储写到
哪里。打包只检查结构和大小：在实机运行之前，用 `buffer_script.emulate_repeating` 离线运行新的载荷。

### 原生格式

转换器可导入 WC8、FRLG `.wc3` 以及 `pokemon-gen3-mysterygift-tool` 的卡片/脚本对；`.wc3` 和 `.wc8`
也可以直接打开。

不含绝对地址的 FRLG 脚本（只有相对 `setvaddress` 的 `vgoto`/`vmessage` [scrcmd.c:171]，道具通过
`callstd`）可服务于其布局下的每一张卡带。含有 `goto`、`call`、`message`、`callnative` 或其他绝对指针的
脚本需要 `--build`，直接打开时会被拒绝。

```bash
./.venv/bin/python -m pokeldn.gifts import --game swsh --record event.wc8 -o event.pokegift
./.venv/bin/python -m pokeldn.gifts import --game frlg --wc3 "FL - Item AuroraTicket (FRE).wc3" -o aurora.pokegift
./.venv/bin/python -m pokeldn.gifts import --game frlg --card WonderCard.bin \
  --script Script.bin --name "Event gift" -o event.pokegift
./.venv/bin/python -m pokeldn.gifts export celebi.pokegift --build BPRF --out-dir native-gift
./.venv/bin/python -m pokeldn.gifts export celebi.pokegift --wc3 --build BPRJ --out-dir native-gift
./.venv/bin/python bin/frlg_mg_host.py --gift celebi --console-build BPRJ --export-gift celebi.wc3
```

保存到 `.wc3` 或 `.wc8` 路径会写入原生文件。一个 `.wc3` 只包含一张卡带；不同变体需要 `--build`。
除图标（重复卡片的图标）外，其元数据全为零。每个被接受的国际版图鉴文件都能往返转换，卡片、脚本和图标
字节完全一致。

国际版 `.wc3` 为 1420 字节（`0x58C`）：

| 偏移 | 大小 | 内容 |
| --- | --- | --- |
| `0x000` | 336 | 卡片的 CRC16、2 个填充字节、332 字节的 `struct WonderCard` |
| `0x150` | 80 | 存档侧的卡片元数据；不读取 |
| `0x1A0` | 1004 | CRC16、2 个填充字节、`struct RamScriptData`（magic 51、地图组、地图编号、对象 id、995 字节脚本）、1 个填充字节 |

图鉴文件的脚本 CRC 覆盖 1000 字节；游戏自身的覆盖 999 字节 [script.c:488]；导入接受两者。
`--icon N`（应用中的 Card icon）设置 `iconSpecies`（卡片偏移 2），取值 0 到 411；0 表示不绘制
[mystery_gift_show_card.c:466]。

日文 `.wc3` 文件为 1252 字节（`0x4E4`）：卡片结构为 164 字节，其 CRC 包装为 168 字节，元数据从
`0x0A8` 开始，1004 字节的 RAM 脚本结构从 `0x0F8` 开始。日文文件服务于 `BPRJ` 和 `BPGJ`，国际版文件
服务于十种拉丁字母卡带。超出 1000 到 1019 的标志 id 会被拒绝 [mystery_gift.c:241]。

原生对（卡片加 1004 字节脚本）无法携带印章、来访训练家、神秘事件脚本、问卷门槛或神秘新闻；导出会拒绝
这些内容。导入会检查两个 CRC。

## 版本 2

该文件是带五个必填字段的 UTF-8 JSON：

| 字段 | 值 |
| --- | --- |
| `format` | `pokeldn.gift` |
| `version` | 整数 `2` |
| `game` | `frlg` 或 `swsh` |
| `name` | 非空显示名称，最多 180 个字符 |
| `variants` | 将目标代码映射到原生数据与选项的对象 |

每个变体有 `data` 和 `options` 对象。`data` 中的组件有 `hex`（以十六进制编码的原生字节）和 `sha256`
（其小写 SHA-256 摘要）。导出会对字段排序。

| 游戏 | 变体键 | 数据组件 | 选项 |
| --- | --- | --- | --- |
| FRLG 礼物 | 支持的卡带代码 | `card`、`ram_script`、`stamp`、`activation_script`、`install_activation_script`、`trainer`、`news`、`mevent` | `questionnaire`、`denied_message` |
| FRLG 主机代码 | 支持的卡带代码 | `buffer_code`、`buffer_lead_1`.. | 下方的应答设置 |
| 剑/盾 | `swsh` | `wc8` | 无 |

FRLG 卡片变体共享标志 ID 和礼物类型；新闻和主机代码单独传输。主机代码变体有一个 `buffer_code`，以及
最多八个在它之前运行的 `buffer_lead_N`，编号连续无空缺。应答设置：`buffer_expect`（u32 或
`trainer-id`）、`buffer_dump_size`（1 到 1024）、`buffer_dump_blocks`（最多 32）、
`buffer_dump_address`、`buffer_dump_addresses`（每个块一个）、`buffer_decode`。

读取器接受版本 1 文件（卡片、新闻、WC8）；导出为版本 2，它增加了主机代码。版本 1 的读取器会拒绝
版本 2 文件。

读取器会拒绝未知的版本、字段和代码、重复字段、错误的哈希、超过 256 KiB 的文件、错误的原生大小以及
错误的组合；FRLG 还会检查卡片字段、训练家校验和与神秘事件终止。哈希只用于检测损坏；它们不认证任何
身份。

## 实现

`pokeldn.gifts` 负责外层封装、校验分发、读取器、写入器和转换器。各游戏专用的编解码器位于
`pokeldn.frlg.gift.file` 和 `pokeldn.swsh.gift_file`。FRLG 适配器构建 `MysteryGiftDistribution`，
包含其卡带选择与拒绝路径；剑/盾适配器则喂给 WC8 通告构建器。
