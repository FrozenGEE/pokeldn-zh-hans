---
title: 叶绿
parent: 火红与叶绿
nav_order: 6
---

# 叶绿，以及两版卡带的偏移对照

法版叶绿（BPGF，版本 0x0A，`POKEMON LEAF`）跑的是法版火红的代码，只是 ROM 偏移呈分段常数。所有负载代码在它上面都能原样工作；ROM 地址则不能。

## 实测地址

| 符号 | 叶绿 | 火红 |
|---|---|---|
| `gDecompressionBuffer` | 0x0201C000 | 相同 |
| 神秘礼物调用点 | 0x08148C50 | 0x08148C74 |
| `Random` | 0x080486B0 | 相同 |
| `SeedRng` | 0x080486D0 | 相同 |
| `gRngValue` | 0x03004220 | 相同 |
| `gPlayerParty` | 0x02024280 | 相同 |
| `gPlayerPartyCount` | 0x02024025 | 相同 |
| `gEnemyParty` | 0x02024028 | 相同 |
| `gSpeciesInfo` | 0x0824CDD8 | 0x0824CDFC |
| `CreateMon` | 0x08041150 | 相同 |
| `sEasyChatGroups` | 0x083E353C | 0x083E3700 |
| `gSpecialVar_0x8000` | 0x020370B4 | 相同 |
| `gSpecialVars` | 0x08163984 | 0x081639A8 |
| `gSaveBlock1Ptr` | 0x03004228 | 相同 |
| `gSaveBlock2Ptr` | 0x0300422C | 相同 |

`rom_map.LEAFGREEN` 连同证据一起保存这些条目；对不在表里的符号，`rom_map.leafgreen(symbol)` 会抛出异常。所有 IWRAM 和 EWRAM 地址完全一致；0x080486C8 以上的 ROM 地址则都有差异。新符号要实测，绝不要预测。

## 按区域看偏移增量

火红到叶绿的偏移是分段常数，而且不单调：

    +0x0   -0x2C   -0x28   -0x24   -0x20   -0x1C4   -0x124C   -0x1240   -0x12D8

`rom_map.leafgreen_guess(firered_address)` 只在已实测的分段内作答，落在空隙里就拒绝。`pokeldn/frlg/rom/leafgreen_twins.py` 保存着 738 对实测地址（约 200 个具名函数）；`leafgreen_twins.leafgreen(address)` 在有配对时精确作答，否则退回猜测。

### 分叉的区段

    步进           区间                          内容
    0     -> -0x2c   644 B, 0x0807CF68..0x0807D1EC  title_screen.o
    -0x2c -> -0x28    62 B, 0x080DE2E4..0x080DE322  mystery_event_script.o
    -0x28 -> -0x24    90 B, 0x081480CE..0x08148128  mystery_gift.o
    -0x24 -> -0x20    31 B, 0x08251D8E..0x08251DAD  pokemon.o rodata
    -0x20 -> -0x1c4 1209 B, 0x083B7B47..0x083B8000  title_screen.o rodata
    -0x1c4 -> -0x124c  30 KB, 0x0843AFFF..0x08442800  graphics
    -0x124c -> -0x1240 17 KB, 0x08442BFF..0x08447000  graphics
    -0x1240 -> -0x12d8 63 KB, 0x0844F3FF..0x0845F000  graphics

每个区段都是版本分叉段，段内不存在统一的增量。`rom_map.LEAFGREEN_DELTA_BOUNDARIES` 保存这些边界，有测试会用分段表核对它们。0x0843C800 以上两版卡带装的是不同的图形数据。`gMPlayTable` 在火红上是 0x0849758C，在叶绿上是 0x084962B4，`gSongTable` 在两者上都在它之后 0x30 处。

## 配对两版卡带

`tools/frlg/cartridge_pair.py` 从两版卡带共有的每个窗口里读取字面量池和 `bl` 目标并配对（1592 个点，每个位置都配上了）。`memory-dump-scatter` 把同样的地址同时发给两台主机；对两个块做互相关就能读出增量，再逐个窗口比较哪个增量吻合，从而把步进定位到字节。拿一台主机导出里唯一的四字节互异字去另一台扫描，就能得到 ROM 里任意位置的对应点。

坑：

- 按代码偏移配对字面量池，绝不要按序号配：序号配对在第一次错位之后就会凭空造出增量。
- 增量 0 也是扫错主机时的答案；务必在某个步进边界上方放一个控制点，它必须返回位移后的地址。
- 图形数据自己像自己：把每个候选增量互相打分，得分接近的一律记为「无结论」。

## 用火红的表读叶绿的导出

`tools/frlg/rom_functions.py --console leafgreen` 会把条目、函数体和名称都经 twins 换算过去，并丢弃落在分叉段里的条目。脚本层在 0x0807AF04 以下完全相同（`rom_map.SHARED_WITH_LEAFGREEN_THROUGH`）：`gScriptCmdTable` 的处理函数块（0x0806D7C0..0x080700B8）、脚本引擎、`GetVarPointer`、`VarGet`、`FlagSet`、`FlagClear`、`FlagGet` 和 `_call_via_r0`。

## 地上世界，以及一只异色超梦

[寻址桩](frlg_rng.md) 未移植也能跑。`initramscript` 把一段 RAM 脚本绑定到地图对象上，之后 `GetRamScript` 会运行它而不跑对象自带的脚本 [field_control_avatar.c:458]。华蓝洞窟 B1F 是第 1 组第 74 张地图；超梦是 3 号对象 [data/maps/CeruleanCave_B1F/map.json]。用 `setwildbattle` 把 150 号物种以 70 级绑到那里，就会触发一场指向超梦的对战（在正版叶绿上就是一只异色超梦）。

- 该绑定能跨掉电保留。
- 神秘礼物会话会通过 `InitRamScript_NoObjectEvent` 重新绑定这个槽位，超梦自己的脚本随之恢复；而缓冲区脚本不会动它。
- 绑定期内主机报告没有神秘卡片（见[那一个 RAM 脚本槽位](frlg_gift.md#the-one-ram-script-slot)）。

## 会变的区域不能做导出

对逐帧变化的区域（例如 `gRngValue`）做 `memory-dump`，会因为 CRC 与发送发生在不同的帧而校验失败，最后停在*erreur de connexion*（见[重新指向主机的出站消息](frlg_rom.md#repointing-the-consoles-outgoing-message)）。上方两个存档块指针会一起移动 0..124 内的一个 4 字节对齐偏移 [load_save.c:75]。

## 英文版

`pret/pokefirered` 用 binutils 和 `pret/agbcc` 在 REVISION 10 上编译两版卡带：

    make firered_switch     -> pokefirered_switch.gba    baa452d0b24629dd7782cfc07a8984085dde1311
    make leafgreen_switch   -> pokeleafgreen_switch.gba  62b9fc77549dbc67032eb6cbd0ea6ad3b825690f

与这两个 sha1 对不上的构建一律不可用；ROM 永远不提交进仓库。它也是英文版，是第二对已知全部符号的卡带。

### 偏移：法版地址到英文地址

法版到英文的偏移也是分段常数，在某个对象因语言而改变大小的地方跳变。`gSpecials`、`gScriptCmdTable` 和 `gMysteryEventScriptCmdTable` 的条目（675 个点）以及唯一的 16 字节窗口，在两者都适用的地方处处吻合。

    ./.venv/bin/python tools/frlg/english_build.py --offsets

### 对照验证

经该偏移换算后，英文 ELF 与 `worker_names` 里的全部 232 个名字一致，没有一个不符。

    ./.venv/bin/python tools/frlg/english_build.py --check

`pokeldn/frlg/rom/english_names.py`（由 `scripts/gen_english_names.py` 生成）用这种方式命名了 7573 个法版函数地址，由 `rom_functions` 最后读取并标为 `[english]`，因此从英文版推断出的名字永远不会覆盖主机实际命名的函数体（`gen_worker_names` 传 `with_english=False`）。落在两段偏移之间的目标，只有在恰好一个相邻偏移落到某个函数起点时，才会进 `english_names.BRACKETED`（`[english?]`）。`__divsi3`、`__modsi3` 和 `__umodsi3` 是 agbcc 的除法辅助函数。

### 英文版这一对自己的增量图

两个英文 ROM 给出同样的六个增量、同样的顺序，每个步进都落在一个版本分叉对象内部：

    +0x0   -0x2c   -0x28   -0x24   -0x20   -0x1c4

五个预测出的法版步进位置全部落在硬件上实测到的括号区间内。

    ./.venv/bin/python tools/frlg/english_build.py --boundaries

### 坑

- `.gcc2_compiled.` 符号会遮蔽它所在文件的第一个函数；跳过以 `.` 或 `$` 开头的名字。
- 填充数据与任何增量都吻合。窗口里必须有 16 个互不相同的字节值，匹配才算数。
- 偏移（法版到英文，在同一版卡带内）不是增量（火红到叶绿）：`法版增量 = offsetFR - offsetLG + 英文增量`。
- 每次新导出之后都要重新生成 `english_names.py`。

## 不能用的参照

`gSongTable` 把 122 个歌曲头压进 9 KB，所以它只能固定一个位置。火红的 ROM 数据在 0x086ABE68 到 0x08800000 之间结束；0x08800000 读出来全是 `0xFF`，0x08E00000 全是 `0x00`。
