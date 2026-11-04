---
title: 随机数生成器
parent: 火红与叶绿
nav_order: 5
---

# gRngValue：读出它、预测它、并对准它

火红的 `gRngValue` 可以被读出、可以从一只宝可梦反推出来，还可以用一段地图桩对准，让下一次脚本触发的遭遇变成异色，且性格与个体值都任你挑。地址取法版火红（BPRF，0x0A）。

## 生成器

```c
u16 Random(void) { gRngValue = 1103515245 * gRngValue + 24691; return gRngValue >> 16; }
void SeedRng(u16 seed) { gRngValue = seed; }
```

[src/random.c, include/random.h:18]

| 符号 | 地址 |
|---|---|
| `gRngValue` | `0x03004220` |
| `Random` | `0x080486B0` |
| `SeedRng` | `0x080486D0` |
| `gSpecialVar_0x8000` | `0x020370B4` |

`pokeldn/frlg/rom/lcg.py` 负责算术部分；`distance(a, b)` 用大小步算法精确求解。这个映射在全部 2<sup>32</sup> 个状态上是一个置换，所以只有当距离很小时它才算证据（概率约 N / 2<sup>32</sup>）。`gRngValue` 与 `gSpecialVar_0x8000` 从不移动；存档块则在每次对战与载入时移动 [load_save.c:75]。

## 速率：每帧正好 2 步

状态每帧正好前进 2 步：`--gift rng-rate-probe`（读、`delay` N 帧 [scrcmd.c:651]、再读）测得 `2N + 2` 步，多出的 2 步是 `delay` 前后各一帧。读完之后再过 n 帧的状态是 `advance(S, 2n)`。一步约 8 毫秒。

## 种子从哪来，以及为什么带不过去

`SeedRngAndSetTrainerId` [main.c:264] 从定时器 1（`REG_TM1CNT_L`）取种子，取样点是标题画面按下 START 的那一刻 [title_screen.c:735]，共 65536 个取值；读取有亚帧抖动，所以靠掐时间按 START 是选不出种子的。从神秘礼物退出会回到标题画面 [mystery_gift_menu.c:463]，因此在链路上设下的种子永远到不了地上世界。

| `SeedRng` 调用点 | 时机 |
|---|---|
| `SeedRngAndSetTrainerId` [title_screen.c:735] | 标题画面 |
| `LinkTestScreen` [link.c:318] | 未使用的调试画面 |
| `Debug_RfuIdle` [link_rfu_2.c:2670] | 未使用的调试画面 |
| `RfuMain1` [link_rfu_2.c:2116] | 仅 Switch 版，条件为 `svc_4b() & SVC4B_RESEED_RNG`，种子取自主机广播的 `playerTrainerId` |

没有任何实测状态来自 `RfuMain1` 的重新播种；这一位何时被置上目前不明。

## 从一只宝可梦反推产生它的状态

野生宝可梦是四次取值：性格低半、性格高半、HP/攻击/防御、速度/特攻/特防 [wild_encounter.c:233]。个体值再提供 30 位校验，所以 `lcg.recover_wild_state` 能唯一定出一个状态。个体值那两次取值之前或之间可能还夹着一次杂散取值；其来源不明，因此两个间隙都要搜：

| 方式 | 个体值之前的间隙 | 个体值之间的间隙 |
|---|---|---|
| 1 | 0 | 0 |
| 2 | 1 | 0 |
| 4 | 0 | 1 |

在提出任何 RNG 结论之前，先用一只宝可梦的 PID、个体值与其六项能力值互相对照。

## 脚本触发的对战

```
setptr b0..b3 -> 0x03004220      gRngValue = seed          (opcode 0x11)
setwildbattle <species> <level>  CreateMon rolls PID, PID, IV, IV   (0xB6)
dowildbattle                     the battle starts          (0xB7)
```

`setwildbattle` 调用 `CreateMon(..., 32, 0, 0, OT_ID_PLAYER_ID, 0)` [script_pokemon_util.c:128]：就是干净的四次取值方式 1，没有草丛或遭遇抽取。两条命令都返回 FALSE，所以写入与生成在同一帧内完成；两者之间不能有任何会让出执行的命令（有测试断言这一点）。这段 RAM 脚本由 `initramscript` 绑定，并以 `end`（0x02）结尾而不是 `endram`，所以会重复触发。一只预测出来的异色 50 级百变怪，其 PID、性格与个体值完全吻合。

若先读出实时状态再生成宝可梦，四次取值从读到的那个状态开始；这只宝可梦花掉 4 步（`Random32()` 2 步，个体值 2 步 [pokemon.c:1796,1836,1845]），再加上地上世界的一帧 2 步。

## 读种子的 NPC

`--gift rng-seed-reader`，标志位 id 1015，一段绑定的 RAM 脚本：

```
copybyte gSpecialVar_0x8000+0, 0x03004220      (opcode 0x15)
copybyte gSpecialVar_0x8000+1, 0x03004221
copybyte gSpecialVar_0x8001+0, 0x03004222
copybyte gSpecialVar_0x8001+1, 0x03004223
buffernumberstring 0, VAR_0x8000               (0x83)
msgbox                                          the NPC prints the value
```

`rng_script.seed_from_printed(low, high)` 把两个字重新拼回来，`rng_script.check_two_readings` 给两次读数打分。

- 六条命令都返回 FALSE 并在同一帧内跑完，所以读取不会被撕开。
- 文本指针是相对的：`setvaddress`（0xB8）与 `vmessage`（0xBD）[scrcmd.c:171] 会把操作数当成脚本体内的偏移，而脚本体随存档块一起移动。
- `buffernumberstring` 打印一个 `u16` [scrcmd.c:1678]：两个变量就是两行。

绑到玩家的妈妈身上（第 4 组、第 0 张地图、1 号对象，`MOVEMENT_TYPE_FACE_LEFT`，永不隐藏）。真新镇的对象事件会到处走动。

## 人手按 A 能有多准

提前 30 秒瞄准的玩家，落点相对某个固定偏移的标准差是 4.5 帧，所以一次按键大约只有 9% 的概率命中选定帧；而异色帧每约 8192 帧才出现一次。`pokeldn/frlg/rom/rng_countdown.py` 是那个倒计时；`--aimed-at STATE` 以帧为单位测出偏差。当 RAM 脚本槽被神秘卡片占着时，走的就是这条路线。

在脚本的按键等待处，钩子可以代你按下，正好落在那一帧，而且不写 `gRngValue`：[`shiny-press`](frlg_rom.md#shiny-shiny-press-ivs-noencounter)，也就是应用里的「异色传说宝可梦」。

## 做搜索的那段桩

`--gift rng-shiny-hunt`、`pokeldn/frlg/rom/native_script.py`、`asm/field/`。四段桩在正版卡带上都能用：

| 桩 | 礼物 |
|---|---|
| `shiny-seek.s` | `rng-shiny-hunt` |
| `mon-seek.s` | `rng-mon-hunt` |
| `mon-seek-far.s` | `rng-mon-hunt-far` |
| `mon-seek-both.s` | `rng-mon-hunt-both` |

```c
bool8 ScrCmd_setptr(struct ScriptContext * ctx)          // 0x11
{ u8 value = ScriptReadByte(ctx); *(u8 *)ScriptReadWord(ctx) = value; }
bool8 ScrCmd_callnative(struct ScriptContext * ctx)      // 0x23
{ void (*func)(void) = ((void (*)(void))ScriptReadWord(ctx)); func(); return FALSE; }
```

[scrcmd.c:300, :120]。`setptr` 把代码暂存进 EWRAM，`callnative` 在地上世界里运行它，这是 `CLI_RUN_BUFFER_SCRIPT` 到不了的地方（`notblisy/RUBYSAPPHIREDLC` 在红宝石/蓝宝石上做的是同一件事）。`CreateScriptedWildMon` 没有固定性格，`OT_ID_PLAYER_ID` 也不消耗取值，所以是否异色只取决于桩留下的那个状态之后的头两次取值。

桩在 `gSaveBlock2Ptr + 0x0A` 处读 `playerTrainerId`，并且只写 `gRngValue`。搜索是有界的；耗尽之后遭遇就是普通遭遇。每段桩在暂存之前都会在 unicorn 下跑一遍（`tests/test_native_script.py`）。

### RAM 脚本未必能从对战中回来

`CB2_InitBattle` 与 `InitOverworldBgs` 会调用 `MoveSaveBlocks_ResetHeap` [battle_main.c:614, overworld.c:1337]，把 `gSaveBlock1` 在 0..124 内按 4 的倍数移动 [load_save.c:75]，而脚本引擎仍握着自己的指针指向 `ramScript.data.script` [script.c:514]。`dowildbattle` 之后的东西全都不可达：恢复执行会落到一场莫名其妙的战斗、一段零填充，或一条让地上世界卡死的命令上。

所以对战从存档块之外启动 [`rng_script.battle_and_exit`]：

    setvar 0x8000, 0x02B7      ->  0x020370B4: B7 02  =  dowildbattle ; end
    goto   0x020370B4

对战中没有任何东西会写 `gSpecialVar_0x8000`，而 `end` 会把控制权交还 [script.c:335]。任何 RAM 脚本都不能指望跨过一场对战或一次地图载入后存档块地址还不变。

## 挑选性格与个体值

`--gift rng-mon-hunt`、`asm/field/mon-seek.s`、标志位 id 1019，检查是否异色、性格（`personality % 25` [pokemon.c:5020]）以及个体值下限（第 3、4 次取值 [pokemon.c:1836]）：

    --hunt-nature adamant,jolly   --hunt-iv speed=31 --hunt-iv attack=20   --hunt-cap N

| 要求 | 命中率 | 典型卡顿 | 达到上限时最坏 |
|---|---|---|---|
| 异色 | 1 / 8,192 | 0.02 秒 | 0.10 秒 |
| 异色 + 指定性格 | 1 / 204,800 | 0.55 秒 | 2.5 秒 |
| 异色 + 性格 + 一项个体值 >= 20 | 1 / 546,133 | 1.5 秒 | 6.7 秒 |
| 异色 + 两项个体值 = 31 | 1 / 8,388,608 | 22 秒 | 拒绝执行 |

`native_script.search_cost` 会算出这些数；最坏情况超过 `--hunt-freeze-frames`（默认 900）时主持端直接拒绝。玩家看到的是一帧静止画面和音乐。`mon-seek.s` 占 163 字节暂存预算里的 160 字节。

## 脚本体里的负载

`setptr` 每写入一个代码字节就要花掉六个脚本字节。脚本引擎在原地运行那 995 字节的 RAM 脚本体，并且从不读最后一条命令之后的内容 [script.c:514]，所以它之后的字节可以按一字节一个当存储用。`&gSaveBlock1Ptr`（0x03004228）给出该帧脚本体的地址；只有 `asm/field/ram-jump.s`（36 字节）需要暂存：

    setptr x36    the trampoline, into gDecompressionBuffer        216 bytes
    callnative    -> trampoline -> payload -> back                   5
    setwildbattle / setvar / goto                                   16
    pad to a multiple of four                                        3
    payload                                                        755

跳板的尾部用 `bx r0` 跳转，所以负载的 `pop {r4-r7, pc}` 会直接返回到 `ScrCmd_callnative` 的调用者。除非 `ramScript.data.magic` 等于 51，否则它会提前返回 [script.c:12]。

### 四字节对齐

THUMB 的 `ldr rN, [pc, #imm]` 使用 `Align(PC, 4)`。脚本体是按字对齐的：存档块偏移是 `& 0x7C` [load_save.c:75]，而 `RAMSCRIPT_BODY_OFFSET` 是 0x3624。`native_script.emulate_body_script` 会走一遍真实的脚本字节，以便抓出未对齐。

### 用大小来证明，而不是靠跳转

`asm/field/mon-seek-far.s` 之后填满非零数据直到第 995 字节；只有填充校验和正确时桩才会搜索。`InitRamScript` 会零填充剩下的部分 [script.c:495]，所以交付的字节短了就等于完全不碰 `gRngValue`。`--gift rng-mon-hunt-far` 带 196 字节的桩和 559 字节填充。

## 让搜索不受杂散取值影响

`asm/field/mon-seek-both.s`（232 字节，`--gift rng-mon-hunt-both`，标志位 id 1001）在两个落点上检查下限。设性格之后的取值为 d3、d4、d5：

| 方式 | 第一组（HP/攻击/防御） | 第二组（速度/特攻/特防） |
|---|---|---|
| 1（干净） | d3 | d4 |
| 2 | d4 | d5 |
| 4 | d3 | d5 |

同时要求 `d3 | d4<<15` 与 `d4 | d5<<15` 两个词，就覆盖了全部三种方式。异色 + 开朗 + 速度 >= 20 变成 1 / 1,456,000，典型耗时约 4 秒；上限是 95%。

## 搜索把报告写在哪

`asm/field/mon-seek-log.s`（288 字节，`--gift rng-mon-hunt-log`，标志位 id 1002）把 `{marker, start, found, iterations, cap}` 写到 `gSaveBlock1Ptr + 0x348C`，也就是 `u8 unused_348C[400]` [include/global.h]，没有任何代码写那里。它能熬过对战，并在存档时进到闪存；搜索耗尽时会写 `found` 为 0。

    --buffer-script save-dump --dump-block sav1 --dump-offset 0x348C --dump-size 32

`native_script.decode_hunt_log` 负责解读它。一次记录在案的 603,745 次迭代搜索与 `lcg.distance(start, found)` 完全吻合，耗时 2–3 秒，每条指令 3.7–5.6 个周期，而模型的 `CYCLES_PER_INSTRUCTION_FROM_EWRAM` 取的是 3。

## 叶绿

这些桩不用移植就能跑：每个字面量要么是链接期的 IWRAM 字，要么是常量，而 `TID ^ SID` 是运行时读的。见[叶绿](frlg_leafgreen.md)。
