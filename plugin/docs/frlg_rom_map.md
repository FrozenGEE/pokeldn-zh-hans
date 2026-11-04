---
title: ROM 映射表
parent: 火红与叶绿
nav_order: 4
---

# ROM 映射表

本页把火红/叶绿卡带的 ROM 映射出来：镜像、函数表、脚本读取器、物种表、法语的快捷聊天词库，以及十二个国际版构建。除表格另有说明外，地址一律是法版火红（BPRF，版本 0x0A）；叶绿的地址见[叶绿](frlg_leafgreen.md)。`pokeldn/frlg/rom/rom_map.py` 记录了每个地址是怎么得到的，`tests/test_rom_map.py` 用主机导出核对它。

## 卡带镜像

Switch 版把 GBA ROM 作为 RomFS 里唯一的文件带着。

| 标题 id | RomFS 文件 | 大小 | sha1 |
|---|---|---|---|
| 01004B3023412000 | `/FireRed_f.gba` | 16777216 | `07566b82dbd2a91321698f730f6400ae4c56ddf1` |
| 010087C02342E000 | `/LeafGreen_f.gba` | 16777216 | `9f774956dfbad7f69ddb91fb91d2c26e54408f75` |
| 0100554023408000 | `/FireRed_e.gba` | 16777216 | `baa452d0b24629dd7782cfc07a8984085dde1311` |
| 010034D02340E000 | `/LeafGreen_e.gba` | 16777216 | `62b9fc77549dbc67032eb6cbd0ea6ad3b825690f` |

0xA0 处的头部读出来是 `POKEMON FIRE` `BPRF` 和 `POKEMON LEAF` `BPGF`，版本 0x0A，校验和有效。法版火红 1.0.1 更新除了外壳的三处载入期补丁外不改动客户 ROM（见 [frlg_rom.md](frlg_rom.md) 的「断点钩子」一节）；`0x09000000..0x0A000000` 读出来是开放总线（每个半字都是它自己的地址减半）。英文这一对（`BPRE`、`BPGE`）与 `pret/pokefirered` 的 `pokefirered_switch.gba`、`pokeleafgreen_switch.gba` 逐字节相同。

`scratchpad/base_romfs.py` 读取 Program NCA 里那个唯一的 CTR RomFS 段：

    ./.venv/bin/python scratchpad/base_romfs.py "$NSP" --list
    ./.venv/bin/python scratchpad/base_romfs.py "$NSP" --extract /FireRed_f.gba --out scratchpad/FireRed_f.gba

## 两个构建的 EWRAM 地址相同

英文 ELF 里的 EWRAM 符号就是法版卡带的那一套（`gDecompressionBuffer` 0x0201C000、`gPlayerParty` 0x02024280、`gPlayerPartyCount` 0x02024025）。IWRAM 则不同。从 0x0203FBAC（最高符号结束处）到 0x02040000 之间没有任何符号占用（`scratchpad/ram_survey.py`）。

## 英文版卡带

`pokeldn/frlg/rom/builds.py` 为每版卡带保存一张表（`BPRF`、`BPGF`、`BPRE`、`BPGE`、`BPRS`、`BPGS`、`BPRD`、`BPGD`、`BPRI`、`BPGI`、`BPRJ`、`BPGJ`）：IWRAM 全局变量、ROM 函数负载、钩子、桩，以及 `call-chain` 用到的和礼物携带的数据指针。主持端在发送任何依赖地址的东西之前，先从 `MysteryGiftLinkGameData` 里的游戏代号选表 [mystery_gift.c:369]；没有对应表，或被 `--console-build CODE` 或 `--version` 排除的主机，会被拒绝，什么都不发。

英文地址来自 ELF，每一处都与正版镜像核对过。

| 区域 | 法版到英文 |
|---|---|
| EWRAM | 不变 |
| IWRAM 0x03000000..0x03001B6F | 不变 |
| IWRAM 0x03002370..0x0300602F（英文），起点是 `gMain`（法版 0x030022D0，英文 0x03002380） | +0xB0 |
| IWRAM 0x03006090..0x03007583（英文），从 `gSoundInfo`（法版 0x03005F80）到 `gFlash` | +0x110 |
| IWRAM 0x03007590 以上：栈、中断向量 | 不变 |
| ROM | 没有统一偏移；每个函数单独查表 |

英文版取值：`gRngValue` 0x030042D0、`gSaveBlock1Ptr` 0x030042D8、`gSaveBlock2Ptr` 0x030042DC、`gIntrTable[4]` 0x030027E0、`gLastWrittenSector` 0x03004650、`gSaveCounter` 0x03004660。英文版叶绿的 RAM 就是英文版火红的；常驻钩子的地址里只有 `m4aSoundMain` 会移动（0x081E07C4 对 0x081E07E8）。`tests/test_frlg_english_cartridges.py` 会把各负载放进对应镜像的 `Client_RunBufferScript` 里跑（没有 `scratchpad/frlg_en/` 时跳过）。

## BIOS 包装函数

`libagbsyscall.s` 按反编译源码的顺序链接成 THUMB 的 `svc N ; bx lr` 对，叶绿上整体低 0x24：

| 包装 | svc | 火红 | 叶绿 |
|---|---|---|---|
| `ArcTan2` | 0x0A | 0x081E21D4 | 0x081E21B0 |
| `BgAffineSet` | 0x0E | 0x081E21D8 | 0x081E21B4 |
| `CpuFastSet` | 0x0C | 0x081E21DC | 0x081E21B8 |
| `CpuSet` | 0x0B | 0x081E21E0 | 0x081E21BC |
| `Div` | 0x06 | 0x081E21E4 | 0x081E21C0 |
| `LZ77UnCompVram` | 0x12 | 0x081E21E8 | 0x081E21C4 |
| `LZ77UnCompWram` | 0x11 | 0x081E21EC | 0x081E21C8 |

游戏里的 LZ77 数据流对 VRAM 安全，且与 `gbagfx` 的输出一致。LZ77 不会让负载代码变小，只有超过 1024 字节的数据才值得用。

## 第一个锚点

`anchors` 返回 `0x08148C75`，即 `Client_RunBufferScript` 里的返回地址 [mystery_gift_client.c:274]。它的字面量池是：

    0x08148C88 -> 0x0201C000   gDecompressionBuffer
    0x08148C8C -> 0x0300422C   &gSaveBlock2Ptr
    0x08148C90 -> 0x03004228   &gSaveBlock1Ptr

0x08148C94 处的 `MysteryGiftClient_CallFunc` 用 `client->funcId` 索引 `sClientFuncs`（0x0845DBD0，八个条目）。其余所有地址都是从字面量池、`bl` 目标和指针表一路追下来的，每一处都落在已知的函数序言上（`scratchpad/rom_read.py`）。

## 四张函数表

    gScriptCmdTable              0x08163650   214 entries   the field script commands
    gSpecialVars                 0x081639A8    21 entries
    gSpecials                    0x081639FC   444 entries   gSpecialsEnd 0x081640EC
    gStdScripts                  0x081640EC    10 entries
    gMysteryEventScriptCmdTable  0x081DE144    17 entries

`script_data` 从 0x08163650 一直到 0x081DE188，那里是 `lib_text`（`libgcnmultiboot`）的起点 [ld_script_rev10.ld:318-330]。

- `gSpecialVars`：十二个字，每个比前一个高 2（`gSpecialVar_0x8000` = 0x020370B4，一个 `EWRAM_DATA` 全局变量）[event_data.c:16]。
- `gScriptCmdTable`：214 个 THUMB 指针；第 0 和第 213 条都是 `ScrCmd_nop`。`pokeldn/frlg/rom/scrcmd_names.py` 给每一条都起了名（`scrcmd_names.handler("additem")`）。

      0x23 callnative   0x0806D854      0x44 additem      0x0806DED0
      0x25 special      0x0806D7EC      0x79 givemon      0x0806F834
      0x29 setflag      0x0806E0EC      0x90 addmoney     0x0806F998

- `gSpecials`：444 个条目，来自 `ScrCmd_special` 的字面量池 [scrcmd.c:101]，经 0x081E2224 调用；其中 171 个是 `NullFieldSpecial`。`rom_map.SPECIAL_ADDRESSES` 保存它们，`rom_map.special_function("HealPlayerParty")` 可以解析出单个函数。
- `gStdScripts`：十个字，指向 0x081A76xx..0x081AB5xx。
- `gMysteryEventScriptCmdTable`：通过 `sMysteryEventScriptContext`（0x0203AA38）找到，它的表对位于 +0x5C/+0x60 [mystery_event_script.c:27,52]（在同一次启动里先领一次神秘事件礼物，然后在 EWRAM 上跑 `table-scan --table-delta 0x44 --table-runlen 2`）。

| # | 命令 | 处理函数 | | # | 命令 | 处理函数 |
|---|---|---|---|---|---|---|
| 0 | `nop` | 0x080DE451 | | 9 | `givenationaldex` | 0x080DE61D |
| 1 | `checkcompat` | 0x080DE401 | | 10 | `addrareword` | 0x080DE641 |
| 2 | `end` | 0x080DE3F5 | | 11 | `setrecordmixinggift` | 0x080DE66D |
| 3 | `setmsg` | 0x080DE465 | | 12 | `givepokemon` | 0x080DE681 |
| 4 | `setstatus` | 0x080DE455 | | 13 | `addtrainer` | 0x080DE78D |
| 5 | `runscript` | 0x080DE49D | | 14 | `enableresetrtc` | 0x080DE7D5 |
| 6 | `initramscript` | 0x080DE5B5 | | 15 | `checksum` | 0x080DE7E9 |
| 7 | `setenigmaberry` | 0x080DE4B9 | | 16 | `crc` | 0x080DE831 |
| 8 | `giveribbon` | 0x080DE581 | | | | |

## 从表项到它背后的函数

按地址顺序排一个处理函数的 `bl` 目标，得到的就是反编译源码里按源码顺序的调用 [scrcmd.c:463-590]：

    ScriptReadHalfword   0x0806D1E8      AddBagItem           0x0809DA70
    VarGet               0x08071DDC      RemoveBagItem        0x0809DBC4
    GetVarPointer        0x08071CC8      CheckBagHasSpace     0x0809D9EC
    FlagSet              0x08071EF4      CheckBagHasItem      0x0809D92C
    FlagClear            0x08071F1C      AddPCItem            0x0809DDB4
    FlagGet              0x08071F44      IncrementGameStat    0x080587A4

`gSpecialVar_Result` 是 0x020370CC；`Random` 是 0x080486B0。`scratchpad/handler_workers.py` 会打印某个处理函数的 `bl` 目标；`tools/frlg/rom_functions.py --table specials|field|mystery-event|callable` 则跨整张表来做，并规划下一批 `--dump-address` 窗口。

ROM 是 agbcc 编译的，一个 THUMB 函数以 `pop {r4,r5,r6}; pop {r1}; bx r1`（BC70 BC02 4708）结尾，从不用 `pop {..., pc}`。`pokeldn/frlg/rom/thumb.py` 匹配 `bx Rn`，并且只有当后面跟着函数序言时才把一次返回当作块的结束。

### 离线命名 300 个函数

`scripts/gen_worker_names.py` 把每份导出的函数体与反编译源码做拉链比对，写出 `pokeldn/frlg/rom/worker_names.py`，并受四道检查约束：

| 检查 | 排除了什么 |
|---|---|
| 长度 | 内联、`__umodsi3`、把宏当成调用 |
| 锚点 | 未对齐的函数体：每个实测地址都必须落回它自己的名字 |
| 一致 | 同一个目标被两个调用者起了不同的名字 |
| 链接顺序 | 名字在 ROM 里位置不对（保留最长的递增链） |

如果两个锚点之间只夹着一个未命名目标和一个源码调用，那就唯一确定了。读源码时要注意：

- `firered_switch` 是 `GAME_REVISION=10 MODERN=0` [Makefile:227]：那些 `#if REVISION >= 0xA` 的块是生效的。
- `VarGet(ScriptReadHalfword(ctx))` 是 `bl ScriptReadHalfword` 再 `bl VarGet`。
- `ScriptReadByte` 是宏，不产生 `bl` [include/script.h:24]。
- `NDEBUG` 处于定义状态：没有断言调用。

| `rom_map` 里的名字 | 反编译源码 | 吻合的函数体数 |
|---|---|---|
| `GET_MON_DATA` | `GetMonData3` | 15 |
| `SCRIPT_CONTEXT_SET_NATIVE` | `SetupNativeScript` | 11 |
| `SET_RESPAWN` | `SetLastHealLocationWarp` | 1 |
| `SCRIPT_MOVEMENT_START` | `ScriptMovement_StartObjectMovementScript` | 2 |
| `CHANGE_AMOUNT_MONEY_BOX` | `ChangeAmountInMoneyBox` | 2 |
| `ME_CHECK_COMPATIBILITY` / `ME_SET_INCOMPATIBLE` | `CheckCompatibility` / `SetIncompatible` | 1 / 3 |

`GetMonData2` 是 `GetMonData3` 的别名 [pokemon.c:2970]。`0x0806D0EC` 是 `StopScript(ctx)` [script.c:76]；`ScriptContext_Stop(void)` [:360] 是 0x0806D418。

### 混用镜像的两个陷阱

- 绝不能把两版卡带的导出当成一个镜像来读：叶绿这段代码整体低 0x2C，混在一起的镜像会把调用错认。`script_read.every_dump` 一次只认一版卡带。
- 要一次读入全部导出：`scrcmd.Memory` 会合并互相重叠的导出（`tools/frlg/script_read.py --with-every-dump`）。

### 实测了什么

每张表背后的每个函数体都读过了：213 条野外脚本命令、17 个神秘事件操作码、27 个可调用函数、272 个 special。`NullFieldSpecial` 是 0x080CE8DC 处的 `bx lr`；`GetLeadMonIndex` 是 0x080CE818；`DoDiveWarp` 是 0x08081CC8，`DoFallWarp` 是 0x08081DA0。

神秘事件虚拟机的干活的函数：

| 函数 | 地址 | 被谁调用 |
|---|---|---|
| `StringExpandPlaceholders` | 0x0800CADC | 每个会留下消息的处理函数的最后一次调用 |
| `RunScriptImmediately` | 0x0806D438 | `runscript` |
| `InitRamScript` | 0x0806D5F0 | `initramscript` |
| `GiveGiftRibbonToParty` | 0x080A43B0 | `giveribbon` |
| `EnableRareWord` | 0x080C1658 | `addrareword` |
| `CheckCompatibility` | 0x080DE300 | `checkcompat` |
| `SetIncompatible` | 0x080DE330 | `checkcompat` 的 else 分支 |
| `memcpy` | 0x081E44F4 | `addtrainer` |
| `CalcCRC16` | 0x080489A0 | `crc` |
| `StringCopyN` | 0x0800C8CC | `setenigmaberry`、`givepokemon` |
| `StringCompare`、`SetEnigmaBerry` | 0x0800C938、0x080A01B0 | `setenigmaberry` |
| `VarSet` | 0x08071DF8 | `setenigmaberry`；没有任何 ScrCmd 调用它 |
| `SpeciesToNationalPokedexNum` | 0x08046994 | `givepokemon` |
| `GetSetPokedexFlag` | 0x0808C860 | `givepokemon` |
| `ItemIsMail`、`GiveMailToMon2`、`CompactPartySlots` | 0x0809BB18、0x0809B964、0x080971FC | `givepokemon` |

调用跳板从 0x081E2224 的 `_call_via_r0` 起每个四字节（r4 是 0x081E2234，r6 是 0x081E223C）。

## 存档备份与恢复

每版卡带上都要用的 `LoadGameSave` [save.c:803] 和 `gRfu.sendQueue.count` [link_rfu_2.c:3131]。`LoadGameSave` 以 `70 b5 00 06` 开头并把 `gDecompressionBuffer` 放进字面量池；队列计数由一个叶子函数读出来：`ldr r0, =gRfu; ldr r1, =0x8D2; adds r0, r0, r1; ldrb r0, [r0]; bx lr`。

| 卡带 | `LoadGameSave` | `gRfu` | `gRfu.sendQueue.count` |
|---|---|---|---|
| `BPRE` | `0x080DDBF4` | `0x03005590` | `0x03005E62` |
| `BPGE` | `0x080DDBC8` | `0x03005590` | `0x03005E62` |
| `BPRF` | `0x080DDFD4` | `0x030054E0` | `0x03005DB2` |
| `BPGF` | `0x080DDFA8` | `0x030054E0` | `0x03005DB2` |
| `BPRD`、`BPRI` | `0x080DDF14` | `0x030054E0` | `0x03005DB2` |
| `BPGD`、`BPGI` | `0x080DDEE8` | `0x030054E0` | `0x03005DB2` |
| `BPRS` | `0x080DDFFC` | `0x030054E0` | `0x03005DB2` |
| `BPGS` | `0x080DDFD0` | `0x030054E0` | `0x03005DB2` |
| `BPRJ` | `0x080DED68` | `0x03005520` | `0x03005DF2` |
| `BPGJ` | `0x080DED3C` | `0x03005520` | `0x03005DF2` |

十二版卡带的 `sSaveSlotLayout` 都一致，只有扇区 id 4 例外：拉丁语系卡带是 3816 字节，日版是 3776 字节。

# 读主机的脚本

`scripts/gen_scrcmd_args.py` 从反编译源码的宏生成操作数宽度，写进 `pokeldn/frlg/rom/scrcmd_args.py`；之后用 `memory-dump` 加 `scrcmd.disassemble` 就能读任何脚本：

    0x081A7624  6A  lock
    0x081A7625  5A  faceplayer
    0x081A7626  67  message 0x00000000
    0x081A762B  66  waitmessage
    0x081A762C  6D  waitbuttonpress
    0x081A762D  6C  release
    0x081A762E  03  return

这就是 `Std_MsgboxNPC`。从每个 `gStdScripts` 条目往下走，都会在下一个条目之前的那一字节上遇到终止符。

## 条件宏

| 命令 | 宽度 | 结构 |
|---|---|---|
| `applymovement` | 7 字节 | `.ifb \map` 分支 |
| `waitmovement`、`removeobject`、`addobject` | 3 字节 | `.ifb \map` 分支 |
| `applymovementat`、`waitmovementat`、`removeobjectat`、`addobjectat` | 9、5、5、5 字节 | 另一条分支 |
| `warp` 及其余八个传送命令 | 8 字节 | `formatwarp` 子宏 |
| 十个 `buffer*` 命令 | 4 字节 | `stringvar` 子宏 |
| `showobjectat`、`hideobjectat`、`resetobjectsubpriority` | 5 字节 | `map` 子宏 |
| `trainerbattle` | 6 + 4..16 字节 | 依类型分支 |

只有当每条分支都以自己的操作码字节开头、且不落到别的命令宏时，一个宏才算命令宏（`giveitem` 是两条指令）。`trainerbattle` 是 `scrcmd_args.VARIABLE`；遇到未知类型，`scrcmd.shape` 会返回 `None`。`goto` 与 `end`、`return` 一样是终止符。0x081A7699..0x081A77A3 这段 266 字节的训练家对战区域是 `tests/test_script_cmd_table.py` 里的固定样例。

## 给操作数命名

`tools/frlg/script_read.py DUMP.bin --base ADDR`：

    0x081A76A8  4F  applymovement 0x800F (VAR_LAST_TALKED), 0x081A77B0
    0x081A76B2  26  specialvar 0x800D (VAR_RESULT), 0x0036 (Script_HasTrainerBeenFought)
    0x081A76BC  06  goto_if 0x05 (!=), 0x081A76CD
    0x081A76C2  25  special 0x0038 (PlayTrainerEncounterMusic)

- 任何命令里 0x4000 及以上的操作数都是变量引用 [event_data.c:214,235]。`pokeldn/frlg/rom/symbol_names.py` 里有 274 个变量名和 1470 个标志位名。
- `scrcmd_args.PARAMS` 给每个操作数命名，并据此选表（`special` 的 u16 查 `gSpecials`，`callstd` 的 u8 查 `gStdScripts`）。
- 条件有 <、=、>、<=、>=、!= 六种 [scrcmd.c:65]。

## 顺着脚本走到它够得着的地方

`scrcmd.follow` 会追每一个 `goto`、`call`、`goto_if` 和 `call_if`，收集还没导出的地址；数据指针只报告，不追。`scrcmd.dump_plan` 把缺的部分变成 `--dump-address` 行。`charmap.decode` 用于名字，`charmap.decode_message` 用于对白。如果一条命令跑过了导出的末尾，会报告为导出过短。

# 物种表

`gSpeciesInfo` = 0x0824CDFC，步长 28（反编译源码里的 26 字节加上两个 `00 00` 填充字节）。它的数据与英文反编译一致。解析反编译源码时的坑：`[SPECIES_NONE] = {0},` 写在一行里、`PERCENT_FEMALE(x)`、`noFlip` 位域，以及十六进制的 `#define`。

## 由它找到 `CreateMon`

`pokemon.o` 里第一个 `&gSpeciesInfo` 字面量池属于 `CreateMon` [pokemon.c:1755]：

| 符号 | 地址 | 依据 |
|---|---|---|
| `CreateMon` | `0x08041150` | 反汇编（`f0b5 4746 80b4 87b0`） |
| `ZeroMonData` | `0x08041090` | 它的第一次调用 |
| `CreateBoxMon` | `0x080411C0` | ZeroMonData 与 SetMonData 之间的那次调用 |
| `SetMonData` | `0x08043A78` | 以 56（`MON_DATA_LEVEL`）调用，再以 64（`MON_DATA_MAIL`）和 255 调用 |
| `CalculateMonStats` | `0x08041B78` | 它的最后一次调用 |

## 西班牙语火红卡带

西语火红基础版 v0（`0100EB702342C000`）里装着 `FireRed_s.gba`，游戏代号 `BPRS`，修订号 0x0A。`builds.BPRS` 与 `vendor/gblink-cards/symbols.json`（语言 id 7）保存它的地址。

| 符号 | 西语火红 |
|---|---|
| `gRngValue`、`gSaveBlock1Ptr`、`gSaveBlock2Ptr` | 0x03004220、0x03004228、0x0300422C |
| `gMain`、`gIntrTable[4]`、`gSoundInfo` | 0x030022D0、0x03002730、0x03005F80 |
| `VBlankIntr`、`Client_RunBufferScript` | 0x0800071C、0x08148CD0 |
| `CreateMon`、`GetMonData3`、`Random` | 0x08041164、0x080432F8、0x080486C4 |
| `CB1_Overworld`、`CB2_Overworld`、`RunTextPrinters` | 0x08059E5C、0x08059EDC、0x08002D50 |
| `m4aSoundMain`、`ReadFlash` | 0x081E089C、0x081E224C |
| `MapGridGetElevationAt`、`MapGridGetCollisionAt` | 0x0805C658、0x0805C6D8 |
| 居合斩、碎岩、怪力的消息返回指针 | 0x081C1909、0x081C19FD、0x081C1AE6 |
| `GetMoney`、`SpeciesToNationalPokedexNum`（表） | 0x080A376C、0x080469A8（0x0824B9DE） |

徽章检查指向 0x081C1901、0x081C19F5 和 0x081C1ADE 处的消息脚本；`EventScript_CurrentTooFast` 从 `0x081AA346`（`lockall`）开始。翻译过的文本会让每个恢复脚本的位置发生变化。`tests/test_frlg_english_cartridges.py`、`tests/test_noclip.py` 和 `tests/test_follower.py` 在有 `scratchpad/frlg_es/FireRed_s.gba` 时用它。

# 法语快捷聊天词库

全部 1006 个随语言变化的快捷聊天词都从主机 ROM 里读出来，写进 `pokeldn/frlg/text/easychat_french_words.py`；`easychat_french.french(id)` 从那里作答。

## 槽位问题

一个快捷聊天 id 是 `(group << 9) | index`。`pokeldn/frlg/text/easychat_words.py` 记录英文 ROM 在每个槽位放了什么；法版 ROM 放的是别的词（`EC_WORD_ENJOY` 显示为 STRESSE，`EC_WORD_DONE` 是 FURAX，`SPEECH/12` 是 LES）。邮件、训练家卡上的签名、来访训练家、`--denied-message` 以及问卷入口都依赖法语这张表。

## 找到这张表

`sEasyChatGroups[]` 是 22 个 `{ const void *wordData; u16 numWords; u16 numEnabledWords; }` [src/data/easy_chat/easy_chat_groups.h:26]，位于 0x083E3700。它的计数与英文版相同，所以同一个 id 在两种语言里都是同一个槽位。词数组与文本跨 0x083DE2C8..0x083E3700。`tests/test_easychat_french.py` 要求渲染结果与 ROM 证据一致。`TRAINER/11` 是 DRESSEUR；DRESSEURS 不在表里。

## 这张表说了什么

- `EC_GROUP_STATUS`（109 个特性）几乎是直译（`stench` PUANTEUR、`thick_fat` ISOGRAISSE、`air_lock` AIR LOCK）。
- `EC_GROUP_FEELINGS` 重新分箱：槽位 13（`disappoints`）是 RAVI，44（`eat`）是 HUMILIE，51（`drink`）是 HONTEUX。
- `EC_GROUP_SPEECH`：LES 和 L' 占了英文用来放 `case` 和 `miss` 的槽位。

807 个槽位（`EC_GROUP_POKEMON`、`POKEMON_2`、`MOVE_1`、`MOVE_2`）由 `gSpeciesNames` / `gMoveNames` 打印 [easy_chat.c:155]，由主机本地化；`easychat.species_word(55)`、`easychat.move_word(177)` 和 `easychat.is_language_safe` 负责处理它们。

## 用法

```python
from pokeldn.frlg.text import easychat, easychat_french
easychat_french.french(easychat.WORDS["enjoy"])     # 'STRESSE'
easychat_french.render(ids)                          # the line as the console will print it
easychat_french.check(ids, strict=True)              # raises on anything unread or out of range
```

    POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live --keys PROD_KEYS \
        --buffer-script string-gather --gather-address 0x083DF5C0 --gather-count 42 \
        --gather-stride 12 --dump-file DUMP.bin --version firered    # one group per run
    ./.venv/bin/python scratchpad/ec_words.py --group 4 DUMP.bin

叶绿的快捷聊天区域就是火红的减 0x1C4，词库完全相同。

## 国际版修订 0x0A 卡带

主持端为英文、法文、德文、意大利文、西班牙文和日文两个版本都准备了地址表。函数通过与英文 ELF 的唯一指令窗口配对（相对调用和指针字面量都做掩码）；RAM 全局变量来自字面量池；野外移动脚本按命令序列配对。`SpeciesToNationalPokedexNum` 是通过共享指令序列的邻居配出来的。

| 卡带 | ROM 文件 | SHA-256 |
|---|---|---|
| `BPRD` | `FireRed_d.gba` | `04f43a43f7cf9109561cd1744d108f50202c931ce31b30abaa6f18950824d20d` |
| `BPRE` | `FireRed_e.gba` | `d32c8df8702293716ad8de68755fe5903161f4829a0a2e486bfa7e74a0b62e94` |
| `BPRF` | `FireRed_f.gba` | `9edf7a3137536b0ccf024a732025da9a0ea1330eb9fd13b2ffed19f5e008c147` |
| `BPRI` | `FireRed_i.gba` | `cf7fa25cf57fbf12f24709efdd1d1aa8056efb4e9b6520ac7d068d3de13ff135` |
| `BPRJ` | `FireRed_j.gba` | `e2cdfb0415ef09e887e9d27b925ff02a713a92f004843490cf6b88b68db6cd01` |
| `BPRS` | `FireRed_s.gba` | `d4dee5aeb5313e073d6067bee37278b0204886958467633978bb746bbe3d5b76` |
| `BPGD` | `LeafGreen_d.gba` | `eb0e340b5efb3ccb7bab104183d2050fa834261dd816c5ad8221e4e98c04342b` |
| `BPGE` | `LeafGreen_e.gba` | `993a8a5695a4f7e4dfe8ceec55beb43e020e82b492854d457d4aa3f864d20f08` |
| `BPGF` | `LeafGreen_f.gba` | `751346c16c0cf3a3ec601d6c2d3c482b54609c5d00ca74f2f668d75b31b8efde` |
| `BPGI` | `LeafGreen_i.gba` | `b99b9c58c83a61b5bd8a1a69b6f21ce0cfab8d1f6065b53b81a323801c9b2895` |
| `BPGJ` | `LeafGreen_j.gba` | `a2aa939a23a36610902be51169042efac78f2f6db6a433e06443a2ee09d4f19e` |
| `BPGS` | `LeafGreen_s.gba` | `a943ecfd6560115b184dc244daed71ba328a67334f343eb35b39932c3ce7c731` |

| 符号 | 德语火红 | 德语叶绿 | 意语火红 | 意语叶绿 | 西语叶绿 |
|---|---|---|---|---|---|
| `gmain` | `0x030022D0` | `0x030022D0` | `0x030022D0` | `0x030022D0` | `0x030022D0` |
| `sb1ptr` | `0x03004228` | `0x03004228` | `0x03004228` | `0x03004228` | `0x03004228` |
| `sb2ptr` | `0x0300422C` | `0x0300422C` | `0x0300422C` | `0x0300422C` | `0x0300422C` |
| `rng` | `0x03004220` | `0x03004220` | `0x03004220` | `0x03004220` | `0x03004220` |
| `vblank_intr` | `0x08000730` | `0x08000730` | `0x08000730` | `0x08000730` | `0x0800071C` |
| `create_mon` | `0x08041178` | `0x08041178` | `0x08041164` | `0x08041164` | `0x08041164` |
| `client_run_buffer_script` | `0x08148BA4` | `0x08148B80` | `0x08148BE4` | `0x08148BC0` | `0x08148CAC` |
| `save_slot_layout` | `0x083FCEC0` | `0x083FCCFC` | `0x083F464C` | `0x083F4488` | `0x083F7674` |

依赖 ROM 的测试会在 Unicorn 下跑每版卡带的 `Client_RunBufferScript`、`CreateMon`、`GetVarPointer`、`VBlankIntr`、存档钩子加载器和碰撞函数，并在 mGBA 下跑每张卡。

### 日版布局

日版火红与叶绿用的是另一套 EWRAM 布局：

| 符号 | 日版 |
|---|---|
| 队伍、队伍数量 | `0x020241E0`、`0x02023F85` |
| 玩家头像、对象事件 | `0x02036FA8`、`0x02036D68` |
| 调色板淡入淡出、禁用野生遭遇的字节 | `0x020379E8`、`0x02038624` |
| `gSpecialVar_0x8000` | `0x02036FE8` |
| `gMain`、`gIntrTable[4]` | `0x030022E0`、`0x03002740` |
| `gRngValue`、`gSaveBlock1Ptr`、`gSaveBlock2Ptr` | `0x03004230`、`0x03004238`、`0x0300423C` |

`RunTextPrinters`（`0x08002D38`）读的是 `0x02020030` 处的数组，步长 `0x20`（国际版是 `0x24`）。

SaveBlock1 是 `0x3D40` 字节（国际版 `0x3D68`）；扇区 id 4 覆盖 `0xEC0` 字节（`0xEE8`）。`RamScript` 保持校验和 `0x361C`、magic `0x3620`、脚本体 `0x3624`。

神秘卡片是 164 字节，神秘新闻是 224 字节。`SaveWonderCard` 是 `0x081481F4`（`BPRJ`）/ `0x081481CC`（`BPGJ`），校验是 `0x08148250` / `0x08148228`。卡片 CRC 在 SaveBlock1 的 `+0x3204`，数据在 `+0x3208`，新闻在 `+0x3124`。`BufferCardText`（`0x08149934`）读取标题第 10..27 字节、副标题 28..40、正文四行每行 20 字节（41..120）、两行页脚每行 20 字节（121..160）。原生 `.wc3` 布局见[礼物文件](gifts.md#native-formats)。

日版的神秘卡片与神秘新闻可接受列表保存的是活动 6 和 7（`BPRJ` `0x08410EC4`、`0x08410EC8`；`BPGJ` `0x08410E4C`、`0x08410E50`），而其他每版卡带保存的是 21 和 22 [src/data/union_room.h:405-406]。可接受的 RFU 串行值是 `{0x0002, 0x7F7F}`（`BPRJ` `0x083FC378`）。十二个标题都把 `0x01006fa0233f8000` 列为它们的第一个本地通信 id。

日版名字用假名表，训练家名字限五个字符；拉丁重音与假名共用字节值，所以内置礼物文案会去掉重音，并在 26 个字符处折行，一页两行。`CreateMon` 把 25 号物种命名为 ピカチュウ。日版队伍卡沿用其来源的日版结构体大小；有两处提示被缩短了。

### 正版机验证

| 卡带 | 在正版硬件上验证过 | 来源 |
|---|---|---|
| 意语叶绿（`BPGI`，修订 `0x0A`） | 全部 41 个 `Build` 字段与主机内存一致；随行宝可梦安装；大师球卡片与道具投递 | [贡献者验证](https://github.com/Decryptu/pokeldn/issues/13) |
