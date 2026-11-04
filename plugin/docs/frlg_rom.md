---
title: 在主机上运行代码
parent: 火红与叶绿
nav_order: 3
---

# 在主机上运行代码

神秘礼物客户端通过两个解释器运行发送给它的代码：`CLI_RUN_MEVENT_SCRIPT`（操作码 15）把字节交给神秘事件 VM，`CLI_RUN_BUFFER_SCRIPT`（操作码 21）则交给 CPU。两者都不需要故障注入、预先准备的存档或任何设置；主机始终停在神秘礼物菜单上。

本页的地址针对法语火红、卡带 BPRF、软件版本 0x0A。叶绿的地址见[叶绿](frlg_leafgreen.md)，各张表见[ROM 映射](frlg_rom_map.md)。

# 神秘事件 VM

这是一个独立的解释器 [src/mystery_event_script.c]，带有自己的 17 条命令表 [data/mystery_event_script_cmd_table.s]，与神秘卡片的配送脚本所编译到的场地脚本 VM 不同。`pokeldn/frlg/rom/mystery_event.py` 负责汇编每一条命令（`MysteryEventScript.blob()` 保存数据，汇编器解析指针）。每个操作码都在零售硬件上验证过。

## 命令表

| # | 命令 | 操作码字节之后的操作数 | 返回 | 效果 |
|---|---|---|---|---|
| 0 | `nop` |  | FALSE | 无 |
| 1 | `checkcompat` | u32 base, u16, u32, u16, u32 | TRUE | 兼容性门闸 |
| 2 | `end` |  | TRUE | `StopScript` |
| 3 | `setmsg` | u8 selector, ptr | FALSE | 当选择子为 `0xFF` 或等于状态值时，调用 `StringExpandPlaceholders(gStringVar4, str)` |
| 4 | `setstatus` | u8 | FALSE | `ctx->data[2] = value` |
| 5 | `runscript` | ptr | FALSE | 对场地脚本调用 `RunScriptImmediately` |
| 6 | `initramscript` | u8 group, u8 map, u8 object, ptr, ptr | FALSE | 绑定到任意地图与对象的 `InitRamScript` |
| 7 | `setenigmaberry` | ptr | FALSE | 写入 `gSaveBlock1Ptr->enigmaBerry` |
| 8 | `giveribbon` | u8 index, u8 ribbonId | FALSE | 给队伍中每只非蛋宝可梦一枚礼物缎带 |
| 9 | `givenationaldex` |  | FALSE | `EnableNationalPokedex()` |
| 10 | `addrareword` | u8 | FALSE | `EnableRareWord`（一句 Easy Chat 流行语） |
| 11 | `setrecordmixinggift` |  | TRUE | 已废弃：`SetIncompatible` |
| 12 | `givepokemon` | ptr | FALSE | 把完整的 `struct Pokemon` 连同附带的邮件放入队伍 |
| 13 | `addtrainer` | ptr | FALSE | 一个 188 字节的 `BattleTowerEReaderTrainer` |
| 14 | `enableresetrtc` |  | TRUE | 已废弃：`SetIncompatible` |
| 15 | `checksum` | u32, ptr, ptr | TRUE | 若该范围内的 `CalcByteArraySum` 不匹配则返回状态 1 |
| 16 | `crc` | u32, ptr, ptr | TRUE | 同上，改用 `CalcCRC16` |

## `checkcompat` 是可选的

`checkcompat` 出现在每个官方脚本的开头，用于校验语言与版本掩码（反编译产物里的 `LANGUAGE_MASK` 为英语）。脚本可以跳过它：

```c
bool32 RunMysteryEventScriptCommand(struct ScriptContext *ctx)
{
    if (RunScriptCommand(ctx) && ctx->data[3])   // data[3] is set only by checkcompat
        return TRUE;
    return FALSE;
}
...
while (MEventScript_Run(&ret));
```

`RunScriptCommand` [script.c:107] 在一次调用内部循环，直到某条命令返回 TRUE。没有 `checkcompat` 时，`data[3]` 保持为 0：脚本一直跑到第一条返回 TRUE 的命令（通常是 `end`），外层的 `while` 随即停止。掩码从不生效，指针按 `operand - ctx->data[1] + ctx->data[0]` 重定位，其中 `data[1]` 为 0（只有 `checkcompat` 会设置它），`data[0]` 是主机的 1024 字节 `client->recvBuffer`：操作数 N 表示所发送内容中的第 N 个字节。`checkcompat` 是汇编器唯一允许在其后继续写代码的命令。

## 返回通道

`MEventScript_Run` 把状态写入 `client->param` [mystery_event_script.c:75]；`CLI_LOAD_TOSS_RESPONSE` 再把它装载进 `MG_LINKID_RESPONSE` [mystery_gift_client.c:204]。以下四条客户端命令会返回一个由脚本决定的 u32：

    CLI_RECV MG_LINKID_RAM_SCRIPT
    CLI_RUN_MEVENT_SCRIPT
    CLI_LOAD_TOSS_RESPONSE
    CLI_SEND_LOADED

`setstatus` 可以设置任意值。内置的几种状态：

| 状态 | 含义 |
|---|---|
| 0 | 没有命令设置过 |
| 1 | `setenigmaberry` 无法校验该树果，或 `checksum`/`crc` 不匹配 |
| 2 | 成功；每个完成本职工作的操作码都会设置它 |
| 3 | `SetIncompatible`，或 `givepokemon` 发现队伍已满 |

`CLI_COPY_RECV_IF` 与 `CLI_COPY_RECV_IF_N` 可以据此让客户端脚本分支 [mystery_gift_client.c:170]（未使用）。

菜单从 `CLI_RETURN` [`GetClientResultMessage`，mystery_gift_menu.c:884] 打印结果，所以 `setmsg` 在这里不可见。只有成功消息才会到达 `MG_STATE_SAVE_LOAD_GIFT` [:1379]，否则事件写入的内容会在重置时丢失；因此 `CLIENT_SCRIPT_MEVENT_DONE` 即使没有卡片也返回 `CLI_MSG_CARD_RECEIVED`。另一个成功出口 `CLI_MSG_BUFFER_SUCCESS`（13）会打印 `CLI_COPY_MSG` 压入的 64 字节。

### 自检脚本

`--gift mystery-event-probe` 是无害的：全国图鉴打开后 `givenationaldex` 就是空操作，而 `checksum` 只读取。

    givenationaldex; setstatus 42; checksum 1026, 16, 31

| 状态 | 含义 |
|---|---|
| 42 | 命令链跑到了末尾，且指针操作数是已发送缓冲区内的偏移 |
| 1 | 命令链跑完了，但重定位后的指针没有落在测试字节上 |
| 2 | `givenationaldex` 执行了，其后的命令都没有执行 |
| 0 | 进入了 VM，但没有命令被执行 |
| 无 | 客户端脚本的形态不对，而不是 VM 的问题 |

`checksum` 是终结性的，匹配时保留之前的状态。零售版火红会返回 42。

## `givepokemon`

`pokeldn/frlg/save/mevent_pokemon.py` 构建载荷：先是一个 100 字节的加密队伍个体，然后是 34 字节的 `struct Mail`，主机在 `pointer + sizeof(struct Pokemon)` 处读取它。`--gift mystery-event-celebi` 会送出这样一只。与场地脚本的 `givemon` 不同，它会：

- 附带邮件。`ItemIsMail` 会做校验，所以携带道具必须是十二种邮件之一 [mail_data.c:167]；`GiveMailToMon2` 把整个结构体（文字、寄件人名字、训练家 id、物种、道具）复制进 `gSaveBlock1Ptr->mail` [:100]；
- 按全国编号设置 `FLAG_SET_SEEN` 与 `FLAG_SET_CAUGHT`；
- 落在神秘礼物菜单：菜单关闭时该宝可梦已在队伍中。

状态 2 表示成功，3 表示队伍已满且什么都没写入。绝不要在它之后放 `setstatus`。

构建器强制规避的陷阱：

- 该个体的 `mail` 字节必须是 `MAIL_NONE`（0xFF）；0 表示邮件槽 0，会被当作真实邮件读取；
- `personality == otId` 会使加密密钥为 0，于是无论打乱与否都能通过校验，可能发出一个未打乱的个体；
- 队伍尾部是推导出来的；全零的尾部读回来等级为 0；
- 携带道具与邮件的 `itemId` 必须一致：`GiveMailToMon2` 会用邮件来设置携带道具。

## `initramscript`

`initramscript 3, 0, 2` 把一个场地脚本绑定到组 3、地图 0、对象 2，即真新镇南部的那位胖男士。重启后他会说出脚本里的台词，其中 `{PLAYER}` 会被展开。

`CLI_SAVE_RAM_SCRIPT` 使用 `InitRamScript_NoObjectEvent`（MAP_UNDEFINED，对象 0xFF）[script.c:578]，只有配送员的 `GetSavedRamScriptIfValid` [:554] 会读取它，而且必须持有一张有效的神秘卡片。真实坐标会走 `GetRamScript(gSpecialVar_LastTalked, script)` [:514, field_control_avatar.c:458]，它用该脚本替代对象自带的脚本，并且无视卡片。`gSpecialVar_LastTalked` 是对象的本地 id，按 `map.json` 顺序从 1 起。

它会消耗掉那张神秘卡片（[唯一的 RAM 脚本槽位](frlg_gift.md#the-one-ram-script-slot)）；会话会记录 "holding no Wonder Card"，直到下一张普通卡片夺回该槽位。绑定期内对象会失去自带的脚本：若绑定到某个固定遭遇的对象上，脚本会取代那个遭遇。

## 陷阱

- `setenigmaberry` 无法设置道具效果。`struct ReceivedEnigmaBerry` [berry.c:944] 有 1322 字节：`Berry2`（28 字节）、`u8 unk_001C[0x4FA]`，然后是 `itemEffect[18]`、位于 0x516 的 `holdEffect` 与 `holdEffectParam`，都超出了 1024 字节的缓冲区；尾部内容是堆上 `recvBuffer` 之后的数据（`build_enigma_berry_blob`；模拟器会报告 `read_past_buffer`）。
- `struct Berry2` 里的两个 ROM 描述指针必须从卡带读出并原样送回：树果袋会永远从存档中解引用它们。
- `giveribbon` 的 index 7..10：`GiveGiftRibbonToParty` [pokemon_size_record.c:193] 接受 `index < 11`，但 `sGiftRibbonsMonDataIds` 只有七项被复制进 `u8[8]`，因此 7..10 会用未初始化栈上的字段 id 去 `SetMonData`。汇编器拒绝 6 以上的值。FRLG 没有缎带界面；缎带只有在传送之后才可见。
- 没有终结命令的脚本会把缓冲区剩余的全零内容当作操作码解码。`assemble()` 与服务端都会拒绝这种脚本。
- `setrecordmixinggift` 与 `enableresetrtc` 各自只做一次调用 `SetIncompatible`，然后中止命令链 [mystery_event_script.c:227, :291]。礼物编排器会拒绝它们。
- `addrareword` 与 `setenigmaberry` 在游戏内不可见；要从存档读回来：`additionalPhrases`（SaveBlock1 + 0x2F10，多出一个 Easy Chat 词）与 `enigmaBerry`（+0x30EC）。它设置的 `VAR_ENIGMA_BERRY_AVAILABLE` 在 FRLG 中没有别处读取。

## 接线方式

- `pokeldn/frlg/rom/mystery_event.py`：操作码、汇编器、反汇编器（`describe`），以及离线客户端所用的模拟器 `run()`。
- `pokeldn/frlg/gift/mg_script.py`：`CLIENT_SCRIPT_SAVE_CARD_AND_MEVENT`（未持卡：卡片、配送脚本、事件）、`CLIENT_SCRIPT_RUN_MEVENT`（已持卡：只跑事件，不丢弃任何东西）、`CLIENT_SCRIPT_MEVENT_DONE`（共用的成功尾部）。
- `pokeldn/frlg/gift/mg_server.py`：`SCRIPT_SEND_MYSTERY_EVENT` 配合 `SVR_LOAD_MEVENT` 与 `SVR_READ_MEVENT_STATUS`；状态落在 `server.mevent_status` 与主机日志里。
- `pokeldn/frlg/gift/gift_composer.py`：`WonderGift.mevent` 校验汇编后的字节。

# 原生 ARM 代码

```c
case CLI_RUN_BUFFER_SCRIPT:
    memcpy(gDecompressionBuffer, client->recvBuffer, MG_LINK_BUFFER_SIZE);
    client->funcId = FUNC_RUN_BUFFER;
    ...
static u32 Client_RunBufferScript(struct MysteryGiftClient * client)
{
    u32 (*func)(u32 *, struct SaveBlock2 *, struct SaveBlock1 *) = (void *)gDecompressionBuffer;
    if (func(&client->param, gSaveBlock2Ptr, gSaveBlock1Ptr) == 1)
```

[mystery_gift_client.c:237,276]。每个载荷都建立在五个事实之上：

- 无论发送了什么，都会复制 1024 字节（`MG_LINK_BUFFER_SIZE`），所以载荷运行时身后是上一次接收的尾部，必须自包含。
- `r0 = &client->param`，`r1 = gSaveBlock2Ptr`，`r2 = gSaveBlock1Ptr`：两个存档块都可读可写。
- `client->param` 就是 `CLI_LOAD_TOSS_RESPONSE` 作为 `MG_LINKID_RESPONSE` 送回的东西 [:204]。
- 它每帧被调用一次，直到返回 1；永不返回 1 的载荷会卡死神秘礼物菜单且无法退出。`memcpy` 只在 `CLI_RUN_BUFFER_SCRIPT` [:239] 处执行一次，因此载荷可以跨帧保持状态。
- ARM 状态：调用方通过 `bx` 跳到一个字对齐的地址进入。

`gDecompressionBuffer` 位于 0x0201C000（由 `anchors` 实测）。载荷是位置无关的。

## 构建

应用的神秘礼物构建器用同一套工具链汇编 ARM 源码（`pokeldn/frlg/rom/custom_code.py`），也可以直接接收原始 `.bin`，并在发送前先让它在模拟主机上跑一遍。`.pokegift` 文件携带编译后的 ARM 字节、卡带目标与响应设置。[神秘礼物文件](gifts.md#console-code) 记载了打包与分享方式。

- `asm/*.s`，每个载荷一份 ARM 源码，由 `scripts/gen_buffer_scripts.py` 汇编进已提交的 `pokeldn/frlg/rom/buffer_payloads.py`；装了 `arm-none-eabi-as` 时，`tests/test_buffer_script.py` 会重新汇编并比对。
- `pokeldn/frlg/rom/buffer_script.py`：注册表、校验，以及 `emulate()` / `emulate_repeating`，它们在 unicorn 里按 GBA 内存映射、带着主机的三个参数运行载荷；出错或永不返回 1 的载荷上不了天。
- `pokeldn/frlg/gift/mg_script.py`：`CLIENT_SCRIPT_RUN_BUFFER`（接收、运行、装载返回通道、发送、接收下一个脚本）与 `CLIENT_SCRIPT_BUFFER_SUCCESS`。
- `pokeldn/frlg/gift/mg_server.py`：`SCRIPT_RUN_BUFFER_SCRIPT`。没有卡片，也没有丢弃提示；已持有的神秘卡片会保留。
- 两个模拟主机都独立依据反编译产物写成，都以逐帧重入的方式执行载荷：`pokeldn/frlg/gift/mg_client.py` 与 `tests/test_mystery_gift_flow.py` 里的 `ConsoleClientModel`。

每次都先离线验证：

    ./.venv/bin/python -m pytest tests/test_buffer_script.py -q
    ./.venv/bin/python scratchpad/mg_client_harness.py --buffer-script -v

在真实硬件上，主机停在神秘礼物 -> 神秘卡片 -> 好友，然后加入主持端。下面的运行命令里，`HOST` 代指
`POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live --keys PROD_KEYS --dump-file DUMP.bin`，
`IP_HOST` 代指 `./.venv/bin/python -u bin/frlg_mg_host.py --over-ip --dump-file DUMP.bin`，后者通过局域网服务一个模拟主机，不需要无线电也不需要密钥。在 `DUMP.bin` 出现之前绝不要 SIGTERM 主持端；它是在 `Buffer script dump: N bytes` 之后几秒才写出的：

    until ls DUMP.bin >/dev/null 2>&1; do sleep 2; done

## 载荷可以放在哪里

缓冲区脚本每帧都会被重新复制，所以它写进自身镜像的任何东西都留不下来。要比菜单活得更久的代码，得放在游戏从不写入的地方：

    0x0203FC00 .. 0x02040000    1024 bytes, above every symbol the game links

最高的有尺寸 EWRAM 符号结束于 0x0203FBAC（[EWRAM 在两个构建中位于相同地址](frlg_rom_map.md)）。按反编译产物命名（`gHeap` 的 114688 字节在符号表里没有尺寸），这是唯一未被占用的 EWRAM 区段；其余都只是三字节和八字节的对齐空洞。

    0x0203F768 .. 0x0203FBAC    1092 bytes, newlib's malloc state

`__malloc_av_` 及其后的 malloc 计数器只被 newlib 的 stdio 访问，而 stdio 只有 `AGBPrintf` 会调用，后者在发布构建里并不使用（pokefirered_switch.elf：指向 `_malloc_r`、`_calloc_r` 与 `_free_r` 的 `bl` 全在 libc 内部）。在 mGBA 下跑法语火红时，在那里填入 0xA5 后经历了菜单、行走和一整场野生战斗仍然存在。GB-Link Team 卡片就把重定位后的脚本放在那里（[frlg_gift.md](frlg_gift.md#gb-link-team-cards)）。`scratchpad/ewram_symbol.py ADDR LEN` 可以检查某个地址。

绝不要因为某个地址读出来是零就选它。0x0202B280、0x020185C4 与 0x0203B0E9 会读出数十 KB 的零，它们分别是战斗与箱子缓冲区、`gDecompressionBuffer` 之前的一段，以及分配器的记账区；0x02012304 位于 `gHeap` 内。0x0202B280 落在 `gPokemonStorage` 之中：写那里可能落到某只箱中宝可梦的校验和上，存档随后就会留下一个坏蛋。

软复位会清空 EWRAM 两次：`DoSoftReset` 调用 `SoftReset(RESET_ALL & ~RESET_SIO_REGS)` [main.c:488]（先 `svc 0x1` 再 `svc 0` [libagbsyscall.s:69]），随后 `AgbMain` 调用 `RegisterRamReset(RESET_ALL)` [main.c:134]；0xFF 的 bit 0 就是 `RESET_EWRAM` [include/gba/syscall.h:4,12]。Switch 封装层还会重启模拟主机，所以 `AgbMain` 会跑两次：每次启动 `gIntrTable` 与 `INTR_VECTOR`（0x03007FFC）都被清空并重建两次，其间条目 1、2、7 取无线相关的值（以每秒 328000 次采样：33.3 ms，再 133.6 ms 到第二次清空，33.6 ms 到其重建）。启动过程不会重建 0x0203B0E8 以上的任何东西。两次启动之间没有任何东西写 0x0203FC00..0x02040000：放在那里的标记能挺过标题画面、重载、菜单、存档、地图切换、战斗和 PC 箱子，而软复位（A+B+START+SELECT）会清掉它。

## 逐帧钩子

`gIntrTable` 在法语卡带上位于 0x03002720；条目 4 即 V-blank 处理函数，存放 `VBlankIntr`（0x0800071D）。它是十四个函数指针，由 `InitIntrHandlers` 依据 `gIntrTableTemplate` [main.c:339] 一次性写入，BIOS 通过 `IntrMain` 抵达它，而 0x03007FFC 处的向量保存着 `IntrMain` 的地址。替换条目 4 就能让代码在每种游戏状态下每帧获得一次调用；`gMain.vblankCallback` 与 `gMain.callback2` 则每当菜单或战斗开始时被重写。

在某台主机的 IWRAM 中实测：`IntrMain_Buffer` 为 0x03002760（英文版 0x03002810），`gSaveBlock1Ptr` 为 0x03004228（英文版 0x030042D8），因此在这些地址上卡带的 IWRAM 比英文构建低 0xB0。IWRAM 不像 EWRAM 那样能在构建之间平移。

| 条目 | 卡带 | 英文 | |
|---|---|---|---|
| 0 VCount | 0x08000805 | 0x0800081C | `VCountIntr` |
| 1 Serial | 0x03004B34 | | 链路建立期间的一个 IWRAM 处理函数 |
| 2 Timer3 | 0x08005AE1 | | `Timer3Intr`，位于另一个 ROM 段，偏移也不同 |
| 3 HBlank | 0x080007D5 | 0x080007EC | `HBlankIntr` |
| 4 VBlank | 0x0800071D | 0x08000734 | `VBlankIntr` |
| 5, 6, 8-13 | 0x08000885 | 0x0800089C | `IntrDummy`，共八次 |
| 7 | 0x081E0D35 | | RFU 定时器处理函数，`sTimerIntrFunc = gIntrTable + 0x7` [main.c:85] |

无线运行期间，条目 1 与 7 与反编译产物预测的模板不同；一次会话之后，条目 1 与 2 会保留其无线相关的值，直到复位。游戏只在 `InitIntrHandlers` 中写条目 4，而它只在软复位时重跑。

### 比会话活得更久的代码

放在暂存区的一段二十字节桩代码被装进条目 4，会话关闭之后它在每种游戏状态下每帧运行。`asm/resident/vblank-hook.s`：

```arm
    ldr     r0, .Lcounter
    ldr     r1, [r0]
    add     r1, #1
    str     r1, [r0]
    ldr     r0, .Loriginal
    bx      r0                      @ tail branch: lr still points at intr_return
```

`IntrMain` 以 SYS 模式进入处理函数，此时 `lr` 指向 `intr_return`，并允许它覆写 r0-r3 [crt0.s, `jump_intr`]，所以被替换的处理函数通过自己的 `bx lr` 返回。两个字面量在发送前都会被打上补丁。

一个 `call-chain` 会安装它：先写那五个字，最后写条目 4，每次写入都读回校验。

    read32  [0x03002730]                gIntrTable[4], 0x0800071D
    write32 [0x0203FC00] = 0x68014802   the stub
    write32 [0x0203FC04] = 0x60013101
    write32 [0x0203FC08] = 0x47004801
    write32 [0x0203FC0C] = 0x0203FC40   the counter's address
    write32 [0x0203FC10] = 0x0800071D   the handler being replaced
    write32 [0x03002730] = 0x0203FC01   the hook, THUMB bit set
    read32  [0x0203FC40]                the counter

钩子在每种游戏状态下每帧运行一次：在 19995 帧里，它在菜单、标题画面、大地图、队伍菜单、一场野生战斗以及一次游戏内重启之间测得每秒 59.0 到 63.3 次调用。软复位会终止它：`InitIntrHandlers` 重写条目 4 [main.c:339]（`gIntrTable[4]` 先读出零，随后为 0x0800071D）。只有在一次启动之后才能进入神秘礼物，而启动会清空 EWRAM，因此一个必须在不开启新会话的前提下就存在的载荷，需要把安装器放进存档。

### 复位之后重新安装

`--gift resident-hook` 送出一张神秘卡片，其神秘事件脚本用 `initramscript` 把一个场地脚本绑定到玩家的母亲身上。该绑定存在存档里，能挺过断电（[唯一的 RAM 脚本槽位](frlg_gift.md#the-one-ram-script-slot)）；在任何一次启动之后与她对话即可安装钩子，不需要链路，也不需要主持端。

`asm/field/install-vblank-hook.s`，68 字节，用 `setptr` 每次六个脚本字节暂存，再用 `callnative` 运行：占 RAM 脚本体 995 字节中的 418 字节。

    read  gIntrTable[4]
    if it already names the stub: return, writing nothing
    write the five words of the V-blank stub to the staging area
    write the handler just read into the stub's fifth word
    zero the counter
    write the staging area, Thumb bit set, into gIntrTable[4], last

尾部目标取自该表，因此钩子会接上当时在场的任何处理函数。开头那次检查是必需的：装两次会让桩代码尾跳到自己，从而在中断处理函数内部空转，冻结大地图。

位于 `SaveBlock1 + 0x32E0` 的脚本块在软复位后仍留在重算后的指针处（已在模拟器上验证）。

脚本每次安装都会重建代码，所以代码受脚本体大小限制：暂存 162 字节，或者在最后一条命令之后追加约 755 字节并用一段跳板抵达。

### 大于脚本体的载荷

`asm/field/save-loader.s`，64 字节，无论载荷多重，RAM 脚本暂存的都是它：它重新读取 `gSaveBlock2Ptr`，加 0xB20，把 N 个字复制到暂存区，用魔数校验第一个字（从未写过的存档，或后续卡片抵达过的区域），然后跳入。它只用 r0-r3，从不压栈，因此载荷直接返回 `ScrCmd_callnative` 的调用方。

blob 为 936 字节，一次 `save-write`（`MAX_SAVE_WRITE_BYTES`，即 1024 字节接收缓冲区减去写入器）：

    +0x000  magic 0x444C4B50
    +0x004  installer
    +0x054  the V-blank hook
    +0x068  filler
    +0x3A4  checksum over the filler

除非填充区之和正确，否则安装器什么都不装（[证明尺寸](frlg_rng.md#proving-the-size-rather-than-the-jump)）。

存档副本里钩子的尾部目标必须是实测的 `VBlankIntr`，绝不能是零：加载器会在一个可能仍活着的钩子上覆盖，而第二次到访时安装器会发现钩子已装好、什么都不补。那里若是零，主机在第二次对话之后就会崩溃成黑屏。

无论载荷多大，RAM 脚本都占 995 字节中的 394 字节。`filler_B20` 有 1024 字节，存档里其他未用区域约 700 字节。更大的 blob 按每块 936 字节分次写入，一次会话写一个载荷（[`save-write`](#save-write)）。到满 1024 时，blob 抵达 EWRAM 顶端，计数器则移入暂存区下方的 84 字节。除钩子的第五个字外，暂存的副本与存档一致；每次安装暂存的都是同样的字节（已在模拟器上验证，计数器以每秒 60.0 次运行）。

### 调用封装层

GBA 代码经由 Sloop 系统调用抵达 Switch 模拟器：`swi 0x40` 到 `swi 0x62` 之间有 23 个，缺口在 0x46、0x4E、0x52 以及 0x58 到 0x60 [src/sloopsvc.c]。常驻载荷可以发出其中任意一个：构建器会把一段 `swi N ; bx lr` 的 thunk 连同补进去的编号汇编进 blob。标记在调用之前写下，因为不返回的系统调用不会留下任何可读的东西：

    +0x00  0xB0B00001   the call was reached
    +0x04  the syscall number
    +0x08  0xB0B00002   it returned, and zero until it does
    +0x0C  r0, r1, r2, r3 as the syscall left them

编号较小的那些会运行内嵌的 BIOS：`main` 在文件偏移 `0x177BAC` 处携带 16,384 字节的 GBA BIOS 映像，其向量表在 `+0`，字符串 `Coded by Kawasedo` 在 `+0x2D34`。`swi 0x00..0x2A` 在模拟 CPU 中作为客户 ARM 代码执行。位于 `main+0x57014` 的分派器接管 `0x40..0x62`，把 0x2B 以下的编号留给那份映像。

`swi 0x54`，即 `svc_CommsAllowedByParentalControls` [sloopsvc.c:182]，在没有家长控制的主机上返回非零。

#### 分派器及其跳转表

分派器位于 `main + 0x057014`，其跳转表位于 `main + 0x17D7F6`。它接受 0x40..0x62 范围内的 `N`：

    cmp   w2, #0x2b ; b.lo default       below 0x2B, the BIOS syscalls
    sub   w9, w19, #0x40 ; cmp w9, #0x22 ; b.hi default
    ldrh  w12, [table, w9, lsl #1]       a u16 word-offset from 0x05706C
    br    base + offset * 4

三十五条表项，二十三个不同的处理函数。`sloopsvc.c` 点名的每个编号都有自己的处理函数。0x46、0x4E 与 0x58 到 0x60 共用默认项，正好是反编译产物的缺口。0x48 与 0x56 共用一个处理函数（`WriteSector`、`ReplaceSector`）；0x40 与 0x41 共用一个，按编号分支。分派器的 `x0` 是 CPU 对象，`w2` 是编号，`x3` 是其处理函数要读的寄存器上下文：客户机的 `r0` 在 `+0x48`，`r1` 在 `+0x4C`（`0x52` 的处理函数在 `mov x20, x3` 之后执行 `ldp w1, w22, [x20, #0x48]`）。

默认项是 `cmp w19, #0x2a ; cset w0, hi ; ret`。那个 `w0` 是封装层自己的「已处理」布尔值，不是客户机的 r0，所以未实现的编号是无害的（不会卡住），且不动客户的任何寄存器。传零进去、读零出来，等于什么都没测。

绝不要在 r0 未选定的情况下单步 0x40..0x62：0x48 与 0x56 要一个扇区号和一个指针，0x4C 结束一次存档，0x55 交出 SaveBlock2 指针，0x43、0x57、0x61 与 0x62 都要参数。r0 里的标记会变成垃圾的 flash 来源。

载荷在每次调用前重写自己的 `swi`（没有指令缓存），先写编号，这样卡住时能自报家门，并在七个头部字之后按编号记录 `r0`（35 个结果，140 字节）。`p_probe_num_step` 逐步改变编号；`p_probe_a0_step` 在编号步进为零的情况下改变 `r0`。

| 编号 | 输入 r0 | 输出 r0 |
| --- | --- | --- |
| `swi 0x52` | `0xA5A00052` | `0` |
| `swi 0x53` | `0xA5C00052` | `1` |
| `swi 0x54` | `0xA5E00052` | `1` |
| `swi 0x55` | `0xA6000052` | `0xA6000052`，未变 |
| `swi 0x56` | `0xA6200052` | 封装层触发了故障 |

`swi 0x56`（`ReplaceSector`）若目标被区域表拒绝（r0 里放标记），模拟器会在 `0xFF8`（`main+0x573F8`）处故障，存档毫发无损：

    Invalid memory access at virtual address 0x0000000000000FF8
    PC  = main+0x573F8     LR = main+0x573EC
    x19 = 0x56                  the syscall number
    x22 = 0xA6200052            the guest's r0
    x13 = 0x0203FFC2            the guest's PC, the halfword after the thunk's `swi`
    x03 = 0x655DB09BE8          0x2D0 above the object 0x52's index 45 resolves to

日志把 `0x0855D3F8` 标为 `gba-app:0x573f8`，据此可定出 `main` 的基址为 0x08506000。

#### `swi 0x52` 与 `swi 0x55`：内存总线

0x52 有一个反编译产物里没有的处理函数，位于 `main + 0x05728C`：

    ldp   w1, w22, [x20, #0x48]     guest r0 into w1, guest r1 into w22
    lsr   x9, x1, #0x15             r0 >> 21
    ldr   x8, [x21, #0xe0]!         the region table
    and   x9, x9, #0x7f8            bits 3..10, so x9 is a BYTE OFFSET, not an index
    add   x8, x8, x9
    ldr   x0, [x8, #0x50]           the object for this selector
    ldr   x8, [x0]                  its vtable
    ldr   x8, [x8, #0x48]           slot 9
    blr   x8
    mov   x0, x20 ; mov w1, wzr ; mov w2, wzr ; b 0x0855D584

返回值被丢弃：`main + 0x057584` 处的回写拿到的是 `w1 = wzr`，所以客户机读到的永远是 r0 = 0，r1 到 r3 不变。从大地图出发、在 45 到 54 号选择子上（`r0` 以 `1 << 21` 步进），`swi 0x52` 返回 r0 = 0，r1 到 r3 与存档都不变。`swi 0x55` 位于 `main + 0x057304`，用同样的移位索引同一张表，调用 slot 9，并从 `main + 0x057588` 退出，那里跳过了回写；这就是它原样返回 r0 的原因。

要读出对象与目标，停在 `blr x8`，即 `main + 0x0572AC`（虚拟地址 `0x0855D2AC`）：`x0` 是对象，`x8` 是 slot 9 的目标，`w1` 是客户机的 r0。再执行一条指令，返回值仍在 `x0` 中。要普查全部 256 个表项，停在 `ldr x8, [x0]`，即 `main + 0x0572A4`，此时尚未解引用任何东西：空对象或未映射的对象会在那里故障。

`0x7f8` 用一条指令同时完成掩码与缩放：

    entry = (r0 >> 24) & 0xFF        and the byte offset is entry * 8

若按 `(r0 >> 21) & 0xFF` 去读，每个表项都会大八倍。`r0` 是 GBA 地址，而这张表就是内存总线：最高字节选择区域，slot 9 负责该区域的地址折叠。

| 表项 | 区域 | 对象 | slot 9 |
| --- | --- | --- | --- |
| 0x00 | BIOS | 自有 | `and w0, w1, #0xffffff` |
| 0x01 | 未映射 | 默认对象 | `and w0, w1, #0xffffff` |
| 0x02 | EWRAM，256 KB | 自有 | `and w0, w1, #0x3ffff` |
| 0x03 | IWRAM，32 KB | 自有 | `and w0, w1, #0x7fff` |
| 0x04 | I/O | 自有 | |
| 0x05 | 调色板，1 KB | 自有 | `and w0, w1, #0x3ff` |
| 0x06 | VRAM，96 KB | 自有 | `and w8, w1, #0x1ffff`，随后把 `0x18000..0x1FFFF` 向下折 `0x8000` |
| 0x07 | OAM，1 KB | 自有 | `and w0, w1, #0x3ff` |
| 0x08, 0x09 | ROM 等待状态 0 | 两者共用一个对象 | `ldr w8, [x0, #0x34] ; and w0, w8, w1`，即卡带的尺寸掩码 |
| 0x0A, 0x0B | ROM 等待状态 1 | 两者共用一个对象 | 同一张 vtable |
| 0x0C | ROM 等待状态 2 | 自有 | 同一张 vtable |
| 0x0D | 等待状态 2 的顶部，EEPROM 所在处 | 自有 | 默认 vtable |
| 0x0E | SRAM | 与其他所有区域对象分开分配 | |
| 0x0F | SRAM 镜像 | 自有 | |
| 0x10 到 0xFF | 未映射 | 默认对象 | `and w0, w1, #0xffffff` |

表项 0 到 15 给出 14 个对象和 11 张 vtable。VRAM 的折叠就是硬件镜像（`0x18000` 读到 `0x10000`，`0x1FFFF` 读到 `0x17FFF`）。默认对象是 `0x655DB09918`，vtable 为 `main + 0x1C1FB0`，slot 9 为 `main + 0x01F7D8`；它的 slot 10 是 `mov x0, xzr ; ret`，11 是一条裸 `ret`，2 是一个两次写入的 setter。每张 vtable 在 `-0x08` 处都有一个空的 typeinfo 指针：没有 RTTI，也没有类名。

EWRAM 的 vtable 在 `main + 0x1C21A0`（`x0` 是区域对象，`x1` 是周期计数器，`x2` 是地址，`x3` 是值）：

| slot | 内容 |
| --- | --- |
| 2 | 把两个字写进对象 `+0x24` 与 `+0x2C` |
| 3, 4, 5 | 读 16、32、8 位 |
| 6, 7, 8 | 写 16、32、8 位 |
| 9 | 把地址折叠进该区域 |
| 10, 11 | 返回空，以及一个空操作 |

访问器先计入周期计数器（半字或字节三次，字六次），然后以 `+0x10` 处的主机后备指针为索引。尺寸在 `+0x20`，ROM 尺寸掩码在 `+0x34`。

有七个系统调用抵达这张表（0x45、0x47、0x48 与 0x56、0x4D、0x52、0x55、0x62），且每个只调用 slot 9；读写访问器属于模拟器的 CPU 核心。`swi 0x62` 是四条递增计数器的指令。

要按处理函数自身的控制流来界定它：有几个在最后一条表项之后还带着一段行外延续代码，若以下一个处理函数的起点为界，就会把它归错。

### flash 扇区路径

`swi 0x48` 与 `swi 0x56` 共用位于 `main + 0x057084` 的处理函数，延续代码在 `main + 0x057364`。客户机的 `r0` 是 4 KB 扇区号，`r1` 是源：

    source      = r1, resolved through the region table and folded
    destination = 0x0E000000 + r0 * 0x1000, resolved the same way

目标地址用 32 位算术生成 [main + 0x05737C]：`0x0E000000 + ((r0 & 0xFFFFF) << 12)`，而区域表项是该地址的最高字节 [main + 0x057384]：`0x0E + ((r0 & 0xFFFFF) >> 12)` 再对 256 取模，所以实际上是 `r0` 在选择区域。目标落在 EWRAM、IWRAM 或卡带缓冲区时能通过两道边界检查（`fold < size`、`size - fold >= 0x1000`）；令 `r0 = 0xFA000 + n`，目标就从任意源区域折进 ROM 副本中 `n * 0x1000` 处的 4 KB（`n` 为 0..0xFFF）。

ROM 目的地址就是对卡带缓冲区的实时写入，这一点在 IP 主机下的模拟主机上实测过（未接触零售主机）：令 `r0 = 0xFA3FF`（`dest` 0x083FF000，`n` = 0x3FF，区域表项 0x08）、源为 EWRAM（`r1` 0x0201C400，fold 0x1C400，掩码 0x3ffff），两道门都通过，复制确实落地：卡带缓冲区 0x3FF000 处的字节与源自身的 0x1000 字节完全一致（0x3FF000..0x3FF31F 是选定图案的 200 个字，随后 0x3FF320+ 处带过去的是源自身的尾部字节，例如第 200 个字在两处都是 0x11111000）。客户机随后在 0x083FF000 处加载，便通过折叠后的 ROM 窗口读到该图案。主机会话保持完好：载荷返回 1，`client->param` 带着图案自己的第一个字，主机打印成功消息并干净地关闭链路。

以同样方式复制过来的代码可以执行。把源的第 0 个字换成一个两条指令的 THUMB 例程（`0x47706001`：`str r1,[r0]; bx lr`），第 1..199 个字是图案；复制完成后载荷读回折叠处（`0x47706001`，即那个例程），并带着 `r1` 里的 nonce 和 `r0` 里自己结果字的地址跳到 `0x083FF001`：主机的应答带回了该 nonce，说明封装层的取指读到的正是系统调用写过的同一份实时后备内存，复制过来的字节经由正常取指路径当作代码运行。会话以成功消息结束，游戏完成了存档。

该写入能挺过软复位。按 A+B+START+SELECT 之后，折叠处 0x3FF000 的同一段 4 KB 经调试器读回逐字节一致（4096 字节中 0 字节变化），而 EWRAM 源暂存区已被清空。复位后开启的第二次会话读到 0x083FF000（`0x47706001`）并带着新的 nonce 跳到 0x083FF001；常驻例程返回了那个 nonce。完整重启应用则会从模拟器的 ROM 文件恢复这些字节：新进程在折叠处持有的是文件的原始字节。写入的生命周期就是模拟器进程的生命周期。

若区域在 `+0x10` 处的后备指针为空、折叠偏移等于或超过 `+0x20` 处的尺寸，或剩余不足 `0x1000` 字节，则该侧被拒绝（指针置空）。两侧都在复制 `0x1000` 字节之前解析完毕。随后 `swi 0x56` 会在目标 `+0xFF8` 处写入 `0xFF`，且没有空指针检查：

    cmp   w19, #0x56
    b.ne  exit
    mov   w8, #0xff
    strb  w8, [x21, #0xff8]

`+0xFF8` 是扇区签名 [pokeldn/frlg/save/save_inject.py]：`0x08012025` 变成 `0x080120FF`，该扇区即作废。`ReplaceSector` 写入并作废，`WriteSector` 只写入。被拒绝的目标会让 `x21` 为空，于是 `swi 0x56` 在 `0xFF8` 处故障，即上面那次中止。

在模拟主机上用 `swi 0x48` 实测：

| 调用 | 结果 |
| --- | --- |
| `r0` 为超出 flash 尺寸的扇区，`r1` 为未映射区域 | 什么都没写，flash 逐字节不变，无故障，无冻结 |
| `r0 = 30`，`r1 = 0x08000000`（ROM 头） | 30 号扇区变成卡带的前 4 KB，4096/4096 字节，相邻扇区未动 |
| `r0 = 30`，`r1` 为载荷填满的 EWRAM 缓冲区 | 30 号扇区变成那些字节；缓冲区读回不变 |
| `r0 = 0xFA3FF`（dest 0x083FF000），`r1` 为 EWRAM 缓冲区 | 复制落在卡带缓冲区：其折叠处 0x3FF000 的字节逐字节变成源的 4 KB；客户机在 0x083FF000 读取返回该图案；会话干净结束 |
| 同样的复制，但源的第 0 个字是 THUMB 例程，然后带着 `r1` 里的 nonce 跳到 `0x083FF001` | 复制过去的例程返回了该 nonce；主机显示成功、存档并干净关闭 |
| 软复位之后，用调试器读同一折叠处 | 那 4 KB 逐字节一致（4096 字节中 0 字节不同），而 EWRAM 源暂存区已被清空 |
| 复位之后，第二次会话先读该例程再跳到 `0x083FF001` | 常驻例程返回了一个新的 nonce，并在同一进程内跨复位仍可调用 |
| 完整重启应用之后，用调试器读同一折叠处 | 折叠处恢复为 ROM 文件的原始字节；写入的生命周期即进程的生命周期 |

它不改动任何客户寄存器，也不返回状态：只有读一次 flash 才能分辨调用是被接受还是被拒绝。

模拟器只在游戏存档时才提交它 128 KiB 的 flash 映像，顺手把外来扇区一起带上。系统调用写入之后强杀进程，主机上的文件不会变。在神秘礼物会话内部写入，只要会话以成功消息结束（该路径会存档 [mystery_gift_menu.c:1379]）就是持久的；若是其他结果，或者来自常驻钩子，则要等下一次存档。

### 断点钩子

封装层的 GBA CPU 对象在 `cpu + 0x170` 处有 256 个钩子槽，每个对应一个 `bkpt` 立即数。ARM 解码测试 `(insn & 0xFFF000FF) == 0xE1200070`，THUMB 解码在 `main + 0x01FCE4` 处测试 `(insn & 0xFF00) == 0xBE00`；`main + 0x01EFC0` 处的 THUMB 处理函数通过 `main + 0x01F820` 调用 `imm8` 槽中钩子的 vtable slot 2（参数为 hook、`&insn`、`bkpt` 的地址、CPU）。返回 1 的钩子会让核心执行它存进 `insn` 的指令；返回 0 或空槽则让该 `bkpt` 成为空操作。`main + 0x022A2C` 注册钩子，并拒绝已占用的槽。有两个槽被占用：

| slot | 归属 | 钩子 | 作用 |
| --- | --- | --- | --- |
| `bkpt #0x52` | Sloop 组件，vtable `main + 0x1C3878` | `main + 0x05499C` -> `main + 0x056368` -> `main + 0x03E850` | 下面那些 librfu 补丁 |
| `bkpt #0xFF` | 应用对象，vtable `main + 0x1B4078` | `main + 0x001140` | 以参数 1 投递事件 `0x82EF0054`，该事件会退出应用 |

加载时封装层会往客户机的 ROM 副本里写入三处补丁，这是 `0x08000000..0x09000000` 范围内仅有的十个与卡带不同的字节，v0 与 1.0.1 上都是如此（块校验和，加上经神秘礼物客户端的一次读取，零售与模拟两边都验过）：

| 地址 | 卡带 | 客户机 |
| --- | --- | --- |
| `0x081E1696` | THUMB `mov ip, r1`（`468c`） | `bkpt #0x52`（`be52`） |
| `0x081E187C` | ARM `ldr r3, [pc, #0x50]`（`e59f3050`） | `bkpt #0x52`（`e1200572`） |
| `0x081E1F90` | ARM `mov lr, r0, lsr #14`（`e1a0e720`） | `b 0x081E1FB8`（`ea000008`） |

第三处补丁去掉了一个等待循环。`0x081E1F74` 处的函数把 `REG_SIOCNT`（`0x04000128`）的 bit 2 与调用者的 `r0` 比较（`r0` 先掩到 u16，`lr = r0 >> 14`），当 `[*(0x03000030) + 0x10]` 处的字节为 1 时提前返回，清掉它并应答 1。在模拟环境里这个轮询永远不匹配，于是封装层用 `mov r0, #0; return` 替换了函数体：等待立刻应答 0。

`bkpt #0x52` 按地址索引：它的钩子在 `+0x120` 与 `+0x148` 处各持一条记录 `{u32 pc, u32 original insn, ..., u32 hits at +0x0C}`，由 `main + 0x0546C0` 匹配地址并返回原始指令。在 `Sio32IDMain` 补丁处（`0x081E1696`）它会解析客户机的 `r0`（`&gRfuSIO32Id`），并在 `+0x0A` 处写入 `0x8001`，即 `AgbRFU_checkID` 所等待的适配器 id [librfu_sio32id.c]。在其他任何地址上执行 `bkpt #0x52`，都会把第二条记录（`0x081E187C` 补丁）指向自己，并在本次会话余下的时间里一直如此。

#### 记录解析器（`main + 0x03E850`）

钩子 `main + 0x05499C` 先把 `bkpt` 本身写进 `insn`，然后以 `x0 - 0x60` 为 `this` 调用 `[[x0 - 0x60] + 0x98]` 处的虚函数（反汇编，`main + 0x549c4`-`0x549cc`）；对 Sloop 组件而言这解析到 `main + 0x056368`，它推导出记录持有者 `[component + 0x40] -> [+0xA8] + 0x68`，并带着它、`&insn`、`bkpt` 的地址和 CPU 尾调解析器 `main + 0x03E850`（整个映像里 `0x3e850` 只有一个调用者，`0x56378`）。客户机 `r0` 的最高字节要到后面、在解析器的 Sio32ID 模拟内部才用于选择区域。解析器：

- 通过 `main + 0x0546C0` 匹配记录 1（持有者 `+0x120`）：匹配则把 `+0x0C` 处的命中计数加一，并把 `+0x4` 处的原始指令复制进 `insn`，随后核心执行它；
- 记录 1 匹配后继续进入 Sio32ID 模拟：客户机的 `r0` 经区域表折叠，折叠偏移只按 `offset < region size`（`+0x20`）做边界检查，且当持有者 `+0x108` 处的标志字节置位时，`strh` 把 `0x8001` 存到 `backing + offset + 0xA`，`main + 0x2209C` 把 `backing + offset + 1` 处的字节写进客户机的 `r1`（`str w2, [regfile + 4 + 0x48]`）。`+0xA` 不在边界检查覆盖范围内，因此区域最后 `0xA` 字节内的偏移会写到该区域后备分配之外，最多超出其末尾 11 字节；标志置位而偏移越界时后备指针为空，封装层会在读取地址 `0x1` 时故障。标志清零时解析器直接返回，不做写入。持有者 `+0x108` 是 `[+0xA8] + 0x170`（持有者为 `[+0xA8] + 0x68`），与下面适配器的电源开关是同一个字节：在主机自身的神秘礼物搜索期间经 `main + 0x03E850` 做了三次实时读取，每次都发现它是 `0x1`，所以单是 `swi 0x40` 就能打开写入路径。
- 记录 1 不匹配时重指记录 2（持有者 `+0x148`）：`record2.pc := the bkpt address`，随后匹配它，于是核心执行记录 2 的原始指令，而那条永远不会被更新：陈旧的 `0x081E187C` 原始指令 `e59f3050`（`ldr r3, [pc, #0x50]`），无论在客户机从哪个地址、以哪种 CPU 模式执行 `bkpt #0x52`。在主机自身的神秘礼物搜索中，每次分派都经由这条路径重指：三次实时读取期间，记录 2 的命中计数（持有者 `+0x154`）每 0.33 s 前进约 20，记录 1 的则不动，说明搜索画面每帧跑的是 STWI 驱动自己在 `0x081E187C` 的运行时 IWRAM 副本上的 `bkpt #0x52`，而不是 `Sio32IDMain` 的 ROM 位置。
- 记录 2 匹配且 `+0x108` 标志置位时，落入 `main + 0x03E954`：它折叠持有者 `+0x170` 处存放的地址，在折叠后的地址读一个字，用该字的最高字节作为区域选择子、用该字本身作为再次折叠的地址，做边界检查，并把持有者 `+0x42B8 + 0x7C` 处的计数器减一。
- 记录 2 匹配且 `+0x108` 标志清零时，落入 `main + 0x03E960`：它折叠持有者 `+0x170` 处存放的地址，在那里读一个字，并把其 bit 15 到 26 与 `0x600` 比较。匹配时经同一张区域表折叠该字的低 24 位，做边界检查，并把持有者 `+0x42B8 + 0x7C` 处的计数器减一；不匹配则什么都不做。

整个触发器都由客户机掌控：一个带着选定 `r0` 跳到 `0x081E1696`（被打补丁的位置，THUMB）的载荷，会让封装层在 `fold(r0) + 0xA` 写入 `0x8001`，并把 `r1` 设为 `fold(r0) + 1` 处的字节；在其他任何地方执行 `bkpt #0x52` 的载荷，则会在那里执行陈旧的 `e59f3050`。两者都是相对客户机的；`+0xA` 那次写入是唯一离开客户机各区域的路径：它能把 `0x8001` 这两个常量字节写到任何区域后备分配之外，最多超出 11 字节，包括 16 MB ROM 副本的。

#### ROM 缓冲区之后是什么：Sloop 组件

ROM 对象的掩码（`+0x34`）是 `0x1ffffff`，而卡带只占 `0x1000000` 字节，因此 `0xFFFFF6..0xFFFFFF` 这些折叠能通过边界检查，把写入放到 ROM 缓冲区紧后面的十个字节上。那里的对象就是 Sloop 组件（[断点钩子](#the-breakpoint-hooks)）：它的第一个字是 vtable 指针 `main + 0x1C3878`，`+8` 是 `0x000004bf`，`+0xC` 是 `0x0A828400`，`+0x18` 与 `+0x20` 是 `main + 0x16EB83`，`+0x28` 是一个 `0x655db` 堆指针，`+0x60` 与 `+0x88` 是更多 vtable（`main + 0x1C3948`、`main + 0x1C3978`），`+0xE0` 是 CPU 总线对象。

邻居在每次启动之间会变：某次启动时 ROM 的邻居是一个首字为 vtable `main + 0x1C36D8`、`+0x60` 为 vtable `main + 0x1C3790` 的对象。构造函数 `main + 0x547CC` 写的正是这一对，它读取 `main + 0x86D67E8` 处的静态指针（加数 `main + 0x1C36C8` [main_relocs.json]）。该类的字段由它自己的构造函数和它自己的代码写入；客户会话的任何存储都到不了那里。

在被打补丁的位置上，卡带自身的代码会停放它自己的 `r0`（`ldr r0, [pc, #0x10]` 装载 `0x0300744A`，即它自己的 `&gRfuSIO32Id`，位于 IWRAM），所以游戏自身的分派总是折到游戏自己的结构体上：封装层写入的 `0x8001` 就是抵达 `gRfuSIO32Id.lastId` 的适配器 id（`RFU_ID = 0x8001` [librfu.h]），也就是 `AgbRFU_checkID` 等待的那个值。若载荷直接跳到 `0x081E1696`，就跳过了那次装载并停放自己的 `r0`，这正是让写入挪位的原因。

在 strh 本身（`main + 0x3E928`）及其延续代码上插桩：直接跳转并令 `r0 = 0x08FFFFF6` 时，这次存储的 `x8` 为 `backing + 0xFFFFF6`（`0x66209f9ff6`，其后是尾部的 `ff` 填充），前后转储显示 `0x66209fa000` 在存储前是 `78 98 6c 08 ...`，存储后是 `01 80 6c 08 ...`：两次写入相隔约 90 ms（先是载荷的触发，随后是带着停放的 `r0` 经同一位置的一次分派）。

写完组件前两个字节后，vtable 指针变成 `0x086C8001`，随后分派器 `main + 0x1F820` 从它读取钩子槽 19（偏移 `+0x98`）：`main + 0x1C2099` 处的八个字节是 `f7 01 00 00 00 00 00 00`，于是封装层的下一次虚调用会在客户 PC `0x1F7` 处执行，那是一个没有其他客户路径能抵达的未映射地址。在模拟器上这会中止进程（`Unhandled guest exception InstructionAbortLowerEl`）；同样的触发若折叠落在某区域内，会话只以该区域内的那次写入收场，不会出现这样的分派。该位置卡带自身的代码排除了另一个候选：`mov ip, r1` 是把 `ip` 当值存（`mov r0, ip; strh r0, [r4]`），从不经它跳转。

钩子只在 `[component + 0x40] -> [+0xA8] + 0x170` 处的字节置位时起作用：那是虚拟适配器的电源开关。`swi 0x40` 置位，`swi 0x41` 清零（处理函数 `main + 0x05706C` 存入 `number == 0x40`；[sloopsvc.c:23] 里的「未被引用的标志设置器」）。从神秘礼物菜单发出 `swi 0x41` 会停掉 RFU 帧：游戏抛出链路错误并离开 LDN。适配器在软复位后仍保持关闭，所以下一次进无线菜单会报 "L'adaptateur sans fil GBA n'est pas connecté"。该字节能挺过软复位；重启应用或 `swi 0x40` 会恢复它。它每帧被读取：在一个载荷里先 `swi 0x41` 再 `swi 0x40` 是无害的。

#### 从 bkpt 到解析器的链条

NSO 的 vtable 槽在文件里存的是未重定位的加数；加载器再加上映像基址（`main` 在 `0x8506000`）。加上基址之后，客户机的一条 `bkpt #0x52` 会跑这样一条链：

- 两条解码路径（THUMB `main + 0x1EFE0`，ARM `main + 0x1B7B8`）都以 `(CPU, bkpt address, immediate, &insn)` 调用分派器 `main + 0x1F820`；
- 分派器取 hook = `[CPU + (imm & 0xff) * 8 + 0x170]`；对 `bkpt #0x52` 而言那是 `component + 0x60`，即组件的一个子对象（组件就是 GBA CPU 对象：`+0x84` 当前 pc，`+0x170` 钩子表，`+0x960` 第二张总线表，`+0xE0` 总线对象）。它读钩子自己的 vtable（`main + 0x1C3948`）的槽 `+0x10`，并以 `f(hook, &insn, bkpt address, CPU)` 调用它。槽 `+0x10` 直接就是 `main + 0x5499C`；
- `main + 0x5499C` 把 `0xE1200572` 写进 `insn`，然后装载 `[component]`，并以 `(component, &insn, bkpt address, CPU)` 尾调 `[that pointer + 0x98]` 处的虚函数：`main + 0x1C3878` 的槽 `+0x98` 是 `main + 0x56368`，它推导出记录持有者并抵达解析器 `main + 0x03E850`。

因此对组件前十个字节的一次存储会在槽 `+0x98` 处被消费；`+0x10` 的读取发生在钩子子对象上，在那十个字节之外。解析器的写入目标是 `buffer_data + fold + 0xA`，其中的折叠就是所选区域的 slot 9（[`swi 0x52` 与 `swi 0x55`：内存总线](#swi-0x52-and-swi-0x55-the-memory-bus)）。

#### 跨区域边缘的写入会怎样

当 `fold = size - 0xB`（在范围内）时，写入的一对字节是 `(size-1, size)`：区域最后一个字节得到 `0x01`，相邻分配的第一个字节得到 `0x80`。当 `fold = size - 0xA` 时，一对是 `(size, size+1)`：`0x01 0x80` 落在邻居的前两个字节上。一次神秘礼物会话每次访问只允许一次选定的折叠。

该位置后面的函数体通过一个五字帧返回：它在 `0x081E177C` 的尾声是 `movs r0,#0 ; pop {r4,r5,r6,r7} ; pop {r1} ; bx r1`。跳到该位置的载荷跳过了函数的序言，必须自己压入那个帧，并把 `lr` 设在一段延续代码上；函数体随后返回载荷，载荷可以继续跑代码并正常结束会话。压入其他任何帧的载荷会经由其调用者的栈展开，实测运行里它们会带着同一个停放的 `r0` 再次进入该位置。

窗口 4 即 GBA IO 寄存器，映射到一个 0x400 字节的区域对象，它紧挨在自己后备分配之后：后备在总线 `+0x14C0`，对象在 `+0x18C0`，按键中断子对象嵌在对象 `+0x88` 处。因此写入落在总线每次 IO 访问都要经过的那个对象上。映像的 CPU 核心里有 210 个访问器形态的调用点（[`swi 0x52` 与 `swi 0x55`：内存总线](#swi-0x52-and-swi-0x55-the-memory-bus)）。

在模拟主机上：

| 写入 | 读取处 | 结果 |
| --- | --- | --- |
| 组件字节对 `01 80`（`0x086C8001`） | 在 `main + 0x1C2099` 读取槽 `+0x98`，未重定位，为 `0x1f7`（[上文](#what-follows-the-rom-buffer-the-sloop-component)） | |
| 组件字节 0 为 `0x80`（`0x086C9880`） | `main + 0x5492C`，同一个方法，但没有 `-0x60` | 它会在已被改写的组件上重读 `[x0] + 0x98` 并递归进自己；线程栈耗尽，进程因数据中止（`InvalidMemoryRegionException`）而死 |
| IO 对象字节 0 为 `0x80`（`0x086C8480`） | 总线的存储槽 `+0x38`/`+0x40`，它们被替换的目标是裸值 `0xffffffffffffe5e0` 与 `0` | 写入之后的第一次 IO 存储会在约 30 ms 内中止进程；那三个加载目标（`main + 0x30EAC`、`main + 0x31114`、`main + 0x36D54`）从不执行 |
| 名称哈希块字节 0（`0x80`） | 该块是 SDK 的 binder/surface 描述符对象（`android.gui.IGraphicBufferProducer` 之流是 SDK 映像里的静态字符串），不是可被分派的对象 | 没有反应；游戏跑到自己干净的退出 |

写入 `0x086C8080`（字节 `80 80`：此后每条 `bkpt #0x52` 都跑纯计数器 getter `main + 0x1F7F0`，于是每次 bkpt 都成了空操作）需要两次写入且中间不得有分派；一次会话只允许一次写入，而途中的两个单写状态都会杀死进程。若改用调试器写入，该指针能在游戏运行、进程存活的情况下保持五分钟。映像里没有任何代码位置会在初始化之后写封装层对象的头部。

#### 一次写入能造成的全部落点

一次写入会在邻居上留下两种字节形态之一：首字节 `80`（区域自己的最后一个字节拿到 `01`），或在字节 `k` 与 `k+1` 上写 `01 80`，`k` 取 0..9。邻居的前八个字节是它的 vtable 指针，所以消费者随后读到的指针是在文件映像及其重定位之上解析的。有四种落点会读到主存的实时内容：

| 对象 | 写入的字节 | 改写后的指针 | 消费者 |
| --- | --- | --- | --- |
| 组件（vtable `main + 0x1C3878`） | `+0` 处为 `80` | `0x086C9880` | `bkpt #0x52` 链的 `[P + 0x98]` = `main + 0x1C3918` = `main + 0x5492C` |
| 组件 | `+0..1` 处为 `01 80` | `0x086C8001` | `[P + 0x98]` = `main + 0x1C2099` = 裸值 `0x1F7` |
| IO 对象（vtable `main + 0x1C2408`） | `+0` 处为 `80` | `0x086C8480` | 总线访问器槽，见下文 |
| IO 对象 | `+0..1` 处为 `01 80` | `0x086C8001` | 总线访问器槽：`0x1F7`、零、裸加数 |

其余落点解析到映像之外。`+1` 处的 `01 80` 给出 `0x08800178`（组件）与 `0x08800108`（IO 对象），都在 main 的 bss 里。一个按零填充建模的 bss 会预测那里是空调用；仅凭文件映像无法确定实时会话期间的内容。`+2` 到 `+7` 的 `01 80` 会移动字节 2 或字节 3，于是消费者自己的读取就会故障。在 `+8` 与 `+9` 上，这一对落在 `+8` 处的字段上（组件的 `0x000004BF` 在 `+8` 变成 `0x00008001`，在 `+9` 变成 `0x008001BF`），vtable 指针原地不动，因此分派的是对象自己的方法。

两次到访同一位置时，若其间没有 `0x04` 访问发生，就能在 IO 对象上把两对字节叠加起来；载荷从 ROM 或 EWRAM 取指本身不访问该对象。重复同一落点是幂等的，而在 `+8` 或 `+9` 写入不会改动 vtable 指针。仅限字节 0 与 1 的不同落点仍可能留下上面某个映像内的指针；改到指针更高字节的组合需要单独分析。在组件上，下一次 `bkpt #0x52` 会消费掉当前的写入。链路建立期间 STWI 驱动每秒产生约 60 次这样的调用，但仅凭这个速率并不能断定每两次载荷访问之间一定有一次调用介入。

IO 对象被改写的块，按总线槽列出。访问类别来自调用者的结果掩码（16 位加载为 `main + 0x18378` 处的 `and #0xffff`，32 位加载为 `main + 0xBDB8` 处的按字循环移位，8 位加载为 `main + 0xD914` 处的 `and #0xff`）。

| 总线槽 | 访问 | 改写后的目标 | 以 IO 对象为 `this` 时 |
| --- | --- | --- | --- |
| `+0x18` | 16 位加载 | `main + 0x30EAC` | 按键处理函数的默认分支：`w2` 是完整的 `0x04xxxxxx` 地址，高于该处理函数所 switch 的任何寄存器 id，于是它把 `w3 & 0xffff` 存到 `[x1]`；`main + 0x18330` 处的调用点传入 `x1 = CPU + 0x20` 与 `w3 = 1`，客户机这次加载返回该处理函数残留的 `w0` |
| `+0x20` | 32 位加载 | `main + 0x31114` | 以 `(x1 from the site, IO + 0x20)` 调用 `main + 0x3580C`，随后以 `x0 = [[IO + 8] + 0x90]` 尾调 `main + 0x22404` |
| `+0x28` | 8 位加载 | `main + 0x36D54` | 一个 0x76000 字节对象的一组清理函数：`[x0 + 0x76C70]`、`+0x76C30`、`+0x76C00`、`[x0 + 0x4E68]` |
| `+0x30` | 存储 | `main + 0x36E40` | `x0 -= 0x1A10`，然后 `main + 0x3664C`，即在重定基后的指针上跑同一组清理函数 |
| `+0x38` | 存储 | 裸值 `0xFFFFFFFFFFFFE5E0` | 调用故障 |
| `+0x40` | 存储 | `0` | 空调用 |
| `+0x48` | | `main + 0x36E4C` | 清理那一组：`+0x76C60`、`+0x76C20`、`+0x76BF0`、`[x0 + 0x4E58]` |
| `+0x68` | | `main + 0x310A8` | `x0 -= 0x10`，然后 `main + 0x30EAC` |

上面这些落点都没有抵达由客户内存提供的分派目标：四个映像内的落点读的是 main 自己的数据，IO 对象的那块则以总线的参数调用 main 自己的处理函数。

在零售机上（一台 Switch Lite、英文火红，载荷由 XIAO ESP32S3 无线电经 LDN 送达），组件写入与范围内写入是靠链路拆除来区分的，而不是靠屏幕。每次运行都在脚本之后约两秒带着「发生错误，软件已关闭」回到 HOME，所以这条消息是通用的；而优雅的 Pia 离开（`Session type 3`）不是：

- 折叠越过卡带缓冲区一个位置时（组件，`r0 = 0x08FFFFF6`），主机离开 LDN 时没有 `Session type 3`，正是模拟器分派里显示的那种突然中止，如今出现在硬件上；
- 折叠在范围内时（`r0 = 0x08FFFFF0`，写在缓冲区 `+0xFFFFFA`），以及让 EWRAM 越尾落到 VRAM 上时（`r0 = 0x0203FFF6`），主机都发出了 `Session type 3` 并优雅离开；普通卡片会话同样如此。

可见在零售机上，当折叠越过 ROM 缓冲区末尾时，记录解析器的这次写入会触到一个活的封装层对象，应用随即在那里中止；同样的写入留在客户可见内存里则不会。压入函数体那个帧的载荷在零售机上也能从该位置返回。

仅凭广播本身也能结束标题画面。若主持端信标那个 8 字节显示名字段里没有任何 `0xFF`（第三代字符串的终止符），标题画面会在好友列表打开的同时以同样的消息关闭，此时主机还没发出任何数据报，也还没加入；主持端的扫描抓包里没有 `udp_in`。只要这八个字节里任意位置有 `0xFF` 就不会发生，放在字段外几个字节处则不起作用，可见搜索只在字段内部进行。正常编码的名字总以 `0xFF` 结尾，所以这需要一条构造过的广播；它属于封装层一侧的中止，与组件写入无关。

写入之后的那次分派就是应用的下一条 `bkpt #0x52`。游戏从两个地方产生它们：STWI 驱动的 IWRAM 副本，链路建立期间每秒约 60 次（对其命中计数的实时读取）；以及它自己在那个位置对 `Sio32IDMain` 的调用（对记录 1 的一次实时读取里 12 次命中）。当 vtable 的低字节为 `0x80` 时，那次分派抵达 `main + 0x5492C`，它在被改写的指针上重读 `[component] + 0x98` 并递归，直到线程栈越出所在区域；主机回到 HOME 且没有 `Session type 3`。若载荷把卡带自己的指令盖回 IWRAM 副本的 `bkpt #0x52`，并回退卡带副本的两处加载期补丁（含两处位置的那个 4 KB 块，经 `swi 0x48`），就同时去掉了两个来源：主机随后显示游戏自己的通信错误，带着 `Session type 3` 离开 LDN，提交网络报告并继续运行。那种状态下被改写的指针是惰性的，而不是被修复：没有任何代码位置会恢复 vtable。回退后的卡带副本同样是进程生命周期的状态：无线菜单此后会报告适配器未连接，而完整重启会重新应用封装层的加载期补丁。

#### 把候选者副本当作 vtable 写入

`swi 0x45` 是通过候选者列表而不是单个落点来组织它的存储的。列表里只有一个候选者（`owner + 0x2770 == 0xB`，计数 1）且 `r0 = 0x08FFFFD7` 时，候选者那 8 字节显示名落在 `component + 0` 上，而 `+0x60` 处的 `bkpt #0x52` 钩子对象仍在这笔写入范围之外。那个名字是 slot 字节 `+0x10..+0x17`（[封装层自己的扫描流水线](#the-wrappers-own-scan-pipeline)），所以组件的 vtable 指针来自对端的广播记录。

下一条 `bkpt #0x52` 会读 `[component]` 并调用 `[component + 0x98]`，因此那种状态下广播来的名字就是调用目标。这种状态需要客户机自己选定的折叠：游戏自己的 `swi 0x45` 交出的是 IWRAM 里的 `gRfuLinkStatus`（[`swi 0x45` 的参数](#the-remaining-syscalls)），这会让写入留在 RFU API 缓冲区内，所以仅凭一条广播到不了任何 vtable。在模拟的法语火红上实测：广播名为 `08 01 df 1f 66 00 00 00`（`0x661FDF0108`，落在 ROM 副本内），经 `swi 0x48` 把一整块 4 KB 的 `0xDEADBEEF` 写到折叠 `0xFA3F6`（`ROM + 0x3F6000`），列表里一个候选者，然后载荷执行 `bkpt #0x52`：

```
Unhandled guest exception PcAlignmentFault at ELR 0xDEADBEEFDEADBEEF (ESR 0x8A000000)
```

`ESR 0x8A000000` 的异常类别为 `0x22`，即 PC 对齐故障，而 `ELR` 持有的是 `[P + 0x98]` 处的八个字节，此处 `P` 等于广播来的名字。分支目标是客户数据。

### 覆盖范围

本页梳理出的客户路径包括一次越过区域后备的写入：解析器在 `fold + 0xA` 处的 `0x8001` strh；被改写指针的读取者，其目标取自静态地址上 `main` 自己的数据（[一次写入能造成的全部落点](#every-placement-a-single-write-can-make)）。读到实时内存的那四种落点，以及其余落点会留下什么，都在那里列出；低字节 `80` 写入之后、会话期间的组件消费者是 `main + 0x5492C`，来自 `bkpt #0x52` 钩子链。单次写入的普查没有发现由客户字节提供的调用目标；它并不覆盖所有写入序列。去掉这条链的两个客户来源后，观测到的分派就消失了。系统调用对组件的存储及其读取者见[其余系统调用](#the-remaining-syscalls)；`main + 0x1C36C8` 那个类的字段由其自身构造函数与自身代码写入（[ROM 缓冲区之后是什么](#what-follows-the-rom-buffer-the-sloop-component)）。第三处加载期补丁替换了一个等待循环。坏词过滤器的两个缓冲区在分派器自己的帧内都有长度限制（[坏词过滤器](#the-bad-word-filter)）；flash 扇区路径的边界见 [flash 扇区路径](#the-flash-sector-path)。

Pia 一侧两端都已解析：客户机的 `RfuGameData` 与用户名会被重新打包进广播记录并做 base85 编码（[广播记录](#the-advertisement-record)）；对端的 `NetworkInfo` 字节原样进入候选者列表（[封装层自己的扫描流水线](#the-wrappers-own-scan-pipeline)）；对端的会话消息在某个处理函数读取它们之前先通过按类型的边界检查（[Pia 会话消息分派器](#the-pia-session-message-dispatcher)）。下面的[线路解析一节](#the-pia-librarys-own-wire-parsing)追踪静态链接的 `PiaCommon-6_42_1` 从 UDP 套接字到会话队列的路径；那条追踪只描绘路径，并不覆盖其中每一次长度检查和每一个消息处理函数。

#### 其余系统调用

处理函数地址由 `main + 0x17D7F6` 处的跳转表给出，即 `main + 0x05706C + entry * 4`。最后一列是一次从神秘礼物客户端经 `sloop-svc` 发出该调用时观察到的结果。

| swi | 处理函数、被调用者 | 作用 | 单次发出时观察到的结果 |
| --- | --- | --- | --- |
| 0x40, 0x41 | `main + 0x05706C` | 适配器的电源开关：把 `r0 == 0x40` 存到 `[component + 0x40] -> [+0xA8] + 0x170` | 从神秘礼物菜单发出 swi 0x41 会触发链路错误并离开 LDN（[上文](#what-follows-the-rom-buffer-the-sloop-component)） |
| 0x42 | 模式切换 `main + 0x0588A0` | `rfu_REQ_startSearchChild` [sloopsvc.c:49]；把网络管理器设为模式 2 | 以链路错误结束会话；没有接入点打开 |
| 0x43 | `main + 0x0570EC` -> `main + 0x058AD0` | `rfu_REQ_startConnectParent`，`r0` 中是 16 位 PID [sloopsvc.c:91]；同一个模式切换 | 缓冲区脚本作出了回应，随后在关闭时报 Erreur de connexion |
| 0x44 | `main + 0x057100` -> `main + 0x058B0C` | `rfu_REQ_stopMode`，无参数 [sloopsvc.c:102] | 在 0x43 之后，没有可见变化 |
| 0x45 | `main + 0x057110` -> `main + 0x058900` | `rfu_REQ_startSearchParent`，用 `gRfuLinkStatus` 调用 `rfu_STC_readParentCandidateList` [sloopsvc.c:67-75]；游戏装载 IWRAM `0x03003110` 处的指针变量（`0x0800C6EA`，Switch ROM 里是三条指令），`rfu_initializeAPI` 把它设为 `0x03004710` 的 `sRfuAPIBuffer`；经区域表把封装层的扫描结果复制进 `struct RfuLinkStatus`，偏移 8 处先是 `findParentCount` [include/librfu.h] | 220 个清零字节保持为零（礼物会话里没有父端搜索） |
| 0x46 | 跳转表项 `0x147` | 落到分派器的出口：该调用什么也不做 | |
| 0x47 | `main + 0x05715C` -> `main + 0x058680` | `rfu_REQ_configGameData`，`r0` 指向 `struct RfuGameData`（16 字节）与用户名（8 字节，`RFU_USER_NAME_LENGTH`）[sloopsvc.c:34-46; include/link_rfu.h:103-115,232]；若 `activity`（第二个 64 位字的 16-22 位）有变化，就把全部 24 字节复制到 `component + 0x6050D8`，并把 `activity` 复制到 `component + 0x605360` | `activity` 0x30 在两处都逐字节落地 |
| 0x48, 0x56 | `main + 0x057084` | flash 扇区拷贝：目标扇区是客户 `r0`，源是经同一区域表折叠、并针对区域大小做边界检查的 `fold(guest r1)`，最多 4 KB | [flash 扇区路径](#the-flash-sector-path) |
| 0x49 | `main + 0x0571A8` -> `main + 0x0588D0` | 在 `component + 0xD0` 对象上调用 `main + 0x0588D0`；不接受客户参数 | 返回 0 |
| 0x4A | `main + 0x0571B8` -> `main + 0x058AB8` | 在 `component + 0xD0` 上同样形态 | 返回 0 |
| 0x4B | `main + 0x0572C4` | 无参数；bit 1 令 `RfuMain1` 从 `gHostRfuGameData->compatibility.playerTrainerId` 重播种 RNG，bit 0 清零令 `SpawnGroupLeaderAndMembers` 对组长提前退出 [sloopsvc.c:132-145] | 0 |
| 0x4C | `main + 0x0571CC` | 在 `[component + 0xE8] + 0xA0` 上调用 `main + 0x05D930`，它回 0 时再对某个全局指针调用 `main + 0x049D28`；没有客户数据抵达两者 | 返回 0 |
| 0x4D | `main + 0x0571FC` | 坏词过滤器：解析 `r0` 并最多读取 `fold(r0)` 处的 256 字节，[见下文](#the-bad-word-filter) | |
| 0x4E | 跳转表项 `0x147` | 落到分派器的出口：该调用什么也不做 | |
| 0x4F | `main + 0x057248` -> `main + 0x058B54` | 在栈上构造 `{u16 tag 0x4757; u32 value = r0}`；带标签属性的分派器 `main + 0x4EBD0` 与设置器 `main + 0x058BB4` 把该值未经校验地存到 `component + 0x6052A0` | 写入 3 与 `0x7FFFFFFF`，各自后跟 0x49 与 0x4A，没有观察到任何变化 |
| 0x50 | getter `main + 0x058BA4` | 读回同一个 4 字节计数 | |
| 0x51 | `main + 0x057270` -> `main + 0x0511BC` | 把 `component + 0x3404` 读进一个出参并清零；该出参总是分派器自己的栈槽 | |
| 0x52 | `main + 0x05728C` | 把客户 `r0` 经总线对象的区域表（`[component + 0xE0] + 0x50`）折叠，并调用该区域的 `+0x48` 折叠。客户 `r1` 非零时还会跑指针解析器 `main + 0x562CC`：它以 0..255 的不设界索引读 `[[bus] + 0x50 + (r1 >> 24) * 8]`，把该值的 `+0x48` 当作虚函数调用，然后在 `offset < size` 时返回 `backing + offset`。该处理函数是解析器唯一的调用者，丢弃其结果并返回 `r0 = 0`，所以客户 `r1` 读回 0。实时读到的 256 项都是 main 自己的方法指针、负值与零，没有一个对象带 `+0x48` 方法 | |
| 0x53 | `main + 0x0572D4` | 回答 `component + 0x2770 == 0`（经 `[component + 0xD0]`） | |
| 0x54 | `main + 0x0572EC` | `svc_CommsAllowedByParentalControls` [sloopsvc.c:182] | 返回 1 |
| 0x55 | `main + 0x057304` | 把 `r0` 存到 `component + 0xE1BC`，把存入的字经区域表折叠并读回一个字节（[游戏报告的素材](#what-the-play-reports-are-built-from)） | |
| 0x57 | `main + 0x057330` | 把 `MonsSelect` 写入 `component + 0x140` 处的报告副本 | |
| 0x58 到 0x60 | 跳转表项 `0x147` | 落到分派器的出口：该调用什么也不做 | |
| 0x61 | `main + 0x057340` -> `main + 0x058B2C` | `svc_SetActivity`；只在 0x41 到 0x48（Union Room 的活动码）时把 `r0` 写到 `component + 0x605360` | 0x45：在被调用者的 `ret`（`main + 0x058B50`）上下断点，读到 `w1` 与该字段都是 0x45；正常关闭 |
| 0x62 | `main + 0x057354` | 把 `component + 0xE1B0` 加 1，即下一份报告的 `CommsError` | |

应答经 `main + 0x2209C` 返回：编号高于 0x2A 时客户 `r0` = 1，客户 `r1` = 处理函数的应答字。没有任何处理函数的应答携带封装层地址。

`component + 0x6052A0` 是 16 字节：4 字节计数，4 字节未使用，一个指向 main 内的 8 字节指针。刚启动时：计数 1，指针 `main + 0x1E8D20`，那是一个指针数组，在唯一有值的槽之后跟着两个空值。

带标签属性的分派器 `main + 0x4EBD0` 遍历组件上的监听者列表：表项 `0xd0` 字节，在 `component + 0x10`，计数在 `+0x688`，启用字节在 `+0x690`；对每个首字为 2 的表项，它以 `entry - 8` 处的 8 字节与那条带标签表项调用组件 vtable 的槽 `+0x50`。设置器 `main + 0x058BB4` 就是 `0x4757` 监听者。`main + 0x50618` 处的 `0x59` 监听者把 `[tagged entry + 4]` 处的值写到 `component + 0x3324 + index * 4`，索引取自 `[x2]` 并由 `main + 0x4DB0C` 限制在 0..7。没有哪个系统调用会构造 `0x59` 表项或提供那个第三参数，分派器的十二次调用都从封装层内部字段构造表项。`0x4757` 监听者存到 `component + 0x6052A0` 的计数除 getter `main + 0x058BA4`（`swi 0x50`）之外没有读者：映像里其余构成 `0x6052A0` 或 `0x6052A8` 偏移的代码位置，都在初始化时写入它或它旁边的指针。`0x4F` 调用者提供的值是惰性的。

主机自己的神秘礼物搜索会在任何缓冲区脚本之前发出 `swi 0x47`，广播 `activity` 0x15（`ACTIVITY_WONDER_CARD` [include/constants/union_room.h:46]）；载荷的调用会覆盖它。在 `main + 0x0586B4` 下断点，经 `x8 + 0x280` 读到 `component + 0x605360`。游戏数据对象（vtable `main + 0x1C3B30`）与 CPU/总线对象是兄弟：`bkpt #0x52` 的钩子表解析在后者上（vtable `main + 0x1C3878`、区域表、系统调用 0x45、0x48、0x52、0x55、0x62）；两者的实时地址相差 `0x100000000`。

`swi 0x45` 为每个候选者写一条定长记录，而不是复制 `sizeof(struct RfuTgtData)`：在 `dest + 0x14 + n*0x20` 处写 id、slot、序列号、`+6` 处 15 字节游戏名与 `+0x15` 处 8 字节用户名，`+3` 处是 `mbootFlag`，该 slot 的最后三个字节保持原样。剩余候选者数量写到 `dest + 8`。一次调用最多写四条记录然后推进游标，所以更长的列表需要第二次调用。因此 `0x18` 这道门在只有一个候选者时越界 `0x19` 字节，四个候选者时越界 `0x79`；计数从不会让单次调用写得更宽。

`component + 0x6050D8`，即 `swi 0x47` 复制的那 24 字节（[main + 0x058694]，一次源自客户 `r0` 缓冲区的预索引存储），会被同一个处理函数读回并重新打包进广播记录。`component + 0x605360` 的读者是 activity 差分 `main + 0x058698`（经 `component + 0x6050E0`）与 `svc_SetActivity` 的设置器 `main + 0x058B40`；两者都只比较或存储活动码。

#### 广播记录

`swi 0x47` 处理函数用客户自己的 `RfuGameData`（16 字节）与 `gHostRfuUsername`（8 字节）拼出广播所携带的 24 字节 RFU 记录 [include/link_rfu.h:103-115, src/sloopsvc.c:34-46]：

| 记录 | 来源 |
| --- | --- |
| `[0:2]` | `RfuGameData[2:4]`，训练家 id（`compatibility.playerTrainerId`） |
| `[2:10]` | 用户名 |
| `[10:12]` | 封装层的 RFU 会话 id，`main + 0x3F2E0([component + 0x6050D0])` |
| `[12:16]` | `RfuGameData[4:8]`，`partnerInfo` |
| `[16:20]` | 搜索字，由 `RfuGameData[0:2]` 与 `[8:12]` 打包而成 |
| `[22:24]` | `RfuGameData[8:10]`，`tradeSpecies` |

搜索字的位，来自两个源字：0-6 是 activity（`RfuGameData` 第 16-22 位），7 是性别（第 24 位），8-10 是版本（`RfuGameData[0:2]` 第 10-12 位），11-14 是语言（第 0-3 位），15 是 `startedActivity`（第 23 位），16 是 `canLinkNationally`（第 7 位），17 是 `hasNationalDex`（第 8 位），18-23 是 `tradeType`（第 10-15 位），24 是 `gameClear`（第 9 位），25-31 是 `tradeLevel`（第 25-31 位）。`hasNews` 与 `hasCard`（第 4、5 位）不被复制。`[20:22]` 这两个字节保持该帧当时的内容。

编码器 `main + 0x2A90` 每 4 字节组写五个字符，低位数字在前，字母表从 `0x23` 起并跳过 `0x5C`，当输出会超出给定容量时拒绝。处理函数按 24 字节以容量 `0x20` 调用它，于是 30 个字符放得下；文本存到 `component + 0x6C0`，其 `strlen` 存到 `component + 0x700`（`main + 0x15FAE0` 与 `main + 0x15FB20`，即 `strlen`/`memcpy` 的 PLT 桩）。

主机信标克隆的、被捕获的应用数据（`pokeldn/frlg/link/host_beacon.py`）是 122 字节：`0x5C` 的 Pia 系统头，加上 30 个字符，读回为训练家 id `0x1050`、名字 `GREEN`、RFU 会话 id `0xac65` 与搜索字 `0x1584`（activity 4、版本 5、语言 2、第 7 位置位）。

记录文本进入一个专为这次投递而建的 advertise-data 构造器（类 vtable `main + 0x1CB8C8`，构造函数 `main + 0x87514`）：`+0x1C` 处是 `0x180` 字节的 Pia 广播区，已用大小在 `+0x18`，从 `0x5C` 的头部起算，应用数据指针 `main + 0xA2C70` = `+0x78`，应用数据大小 `main + 0xA2C90` = 已用大小减 `0x5C`，上限钳到 `0x124`（槽 `+0x28`，`main + 0x875AC`；头部偏移 `0x5C` 是槽 `+0x30`，`main + 0x875A4`）。`main + 0xA3480` 经它 `+8` 处持有的缓冲区对象把 30 个字符追加到应用数据偏移处（其容量是缓冲区的 vtable 槽 `+0x28`，已用大小在缓冲区的 `+0x18`，追加会置位缓冲区 `+8` 的第 1 位）；它唯一的调用者就是该处理函数（`main + 0x58838`）。处理函数随后在 `main + 0x58854` 投递该构造器：`x0 = [component + 0x3528]`，`main + 0xB1304`。那个方法对 `[session + 0xD0]` 调一个方法，把它作为参数传下去，把 `+0xD8` 处的 u32 清零，并调用 `main + 0xD4DD0(x0 = [session + 0x70], x1 = [session + 0xD0], x2 = [session + 0x30], x3 = the builder)`。投递取 `X = [session + 0x30]`，先过 `X` 的槽 `+0xD8`（须返回 true）与 `+0xE8`（须返回 false）两道门，再以 `(X, [session + 0x70] + 0x90, builder)` 调用 `X` 的 vtable 槽 `+0xA8`。会话的 `+0x30` 由 `main + 0xAF760` 从 `[[session + 8] + 0xB8]` 设置，那是会话所有者的 `+0xB8`。

`X` 具有门面类的形态：`nn::pia::local::LocalFacade`（vtable `main + 0x1CB548`）与 `nn::pia::net::NetFacade`（`main + 0x1CBE60`）共用同一实现，其槽为 `+0xA8` = `main + 0x8D4AC`、`+0xD8` = `main + 0x8D84C`（门面的 `+0x28` 已置位且其 `+0x30` 非空时为 true）、`+0xE8` = `main + 0x8D920`（`[[facade + 0x30] + 0x12D8]` 非零时为 true）。门面的 `main + 0x8D4AC` 经 `main + 0x8C6FC` 校验，锁定管理器（从 `[facade + 0x30] + 0x2B8` 经 `main + 0x94B78`，可见门面把管理器放在 `+0x30`），取构造器 `+8` 处的值（`main + 0xA3710`）交给管理器的 `main + 0x99C3C`，然后把传输层记到 `[facade + 0x48]`、状态 8 记到 `[facade + 0x40]`。管理器把缓冲区交给该任务的接收半（见下文），任务的发布半则经管理器的 blob 构造器抵达 `nn::ldn::SetAdvertiseData`。

组件在 `[component + 0x3528]` 处持有的对象是一个 `nn::pia::session::Session`：填充 `main + 0xAF4E0` 到 `0xB23xx` 的那批方法所属的类（主 vtable `main + 0x1CE300`，第二个在 `main + 0x1CE330`，构造函数 `main + 0xAF4E0`，它从 `+0x10` 起初始化字段，并把 `+0xD8` 当 u32 处理）。它的方法设置 `+0x30`（`main + 0xAF760`）、`+0x70`（由 `main + 0xAF9F0` 设置；实时它是一个 `UpdateSessionPropertyJob` 单例，其 `+0x10` 处的 u16 由该设置器维护）与 `+0xD0`（`main + 0xAFA94`），并在 `main + 0xAFB44` 清除它们；投递调用方读取 `+0x150`、`+0x528`、`+0x70`、`+0x30`、`+0xD0` 与 `+0xD8`，全是 Session 的字段。组件在 `main + 0x528F8` 处挑选它：从它嵌在 `+0x34A0` 的对象（取其首字）或从重定位槽 `main + 0x1D1AB0` 的全局（它指向映像之外的 `0x41FB1C8`），并用 `main + 0xB14E0` 打开，后者把回调 `main + 0x52BB4` 存到 `+0x88`、把组件存到 `+0x90`。Session 的构造函数在映像里没有调用者，其 vtable 指针槽只被该构造函数与析构函数装载，所以这个实例来自本模块之外。实时的形态（模拟的法语火红、神秘礼物会话；同一个 `main` 映像）：该层是一组 bss 单例：`Session` 在 `main + 0x1029950`，`SessionProtocol` 在 `main + 0x1032000`，所有者在 `main + 0x9E1798`，`LocalFacade` 在 `main + 0x9E15B8`，以及三个会话任务单例在 `main + 0x103FBB0`、`+0x103FCE8` 与 `+0x1040180`（`LeaveMeshWithHostMigrationJob`、`ProcessHostMigrationJob`、`KickoutManageJob`）。会话进行中，`[component + 0x3528]` 正是那个 `Session`，其中 component = `[session + 0x90]`，即系统调用分派器收到的对象（它在 `+0x6050D8` 的 RFU 影子持有最后一条记录：activity `0x15`、用户名各字节）。`[session + 8]`（所有者；对每个协议也是 `[protocol + 8]`，以及 `[reader + 0x60]`）没有 vtable：`+0xB8` 是门面，`+0xC8` 是协议管理器。`[session + 0x30]` = `LocalFacade`（已用 typeinfo 核实）。会话任务的 `+0x80` 是 `[SessionProtocol + 0x130]`，即该 Session，它们的 `+0x88` 是 SessionProtocol（其构造函数 `main + 0xCB0D0`：`stp x9, x19, [x20, #0x80]`，`x9 = [x19 + 0x130]`）。

广播机制属于另一个对象，`nn::pia::local::LdnBackgroundProcessJob`（类 vtable `main + 0x1CAC48`，`0xA60` 字节，工厂 `main + 0x7EED8` = 管理器的 vtable 槽 `+0x278`，构造函数 `main + 0x83A88`），它派生自 `nn::pia::net::NetBackgroundProcessJob`（vtable `main + 0x1CB928`），并在 `+0xD8` 嵌入一个 `nn::pia::common::StepSequenceJob::Step`（vtable `main + 0x1C9770`）、在 `+0x320` 嵌入一个 `nn::pia::local::LocalConnectNetworkSetting`（vtable `main + 0x1CA2D0`）。其基类构造函数 `main + 0x875BC` 把网络管理器存到 `+0xA8` 并构建各子对象；它自己的构造函数在 `+0x8C0` 构建 advertise-data 构造器（`main + 0x87514`）。该任务的方法 `main + 0x84260`（vtable 槽 `+0x60`）是接收半：它锁定管理器（`+0x2B8`），触碰持有者（对 `[manager + 0x200] + 0xA8` 与 `[manager + 0x2D8]` 调 `main + 0x87374`），经 `main + 0x8885C` 校验入站缓冲区（缓冲区大小 `main + 0xA2C90` 需在管理器槽 `+0x100` 的限制内，缓冲区 `+0x8` 的第 1 位须置位，`[manager + 0x12D8]` 须为零，`w2 = 8` 的 `main + 0x879C0` 检查，以及 `[job + 0xA0]` 处的时间戳），把缓冲区 `+0x1C` 处的 `0x180` 字节广播区复制进任务 `+0x8C0` 的构造器（`main + 0x87578`），并把任务的下一个步骤设为槽 `0x130`。这条路径是经任务的 vtable 抵达的：管理器的 `main + 0x99C3C` 把缓冲区交给它存在 `+0x250` 的对象（一个派生自 `StepSequenceJob::Step` 的委托，构造函数 `main + 0xA2824`，`0x98` 字节，`+0x88` 处有一个 `0x38` 字节的辅助对象，管理器在 `+0x90`），后者的 `main + 0xA28E4` 以 `(job, helper, buffer)` 调用任务的槽 `+0x60`。发布半是任务的 `+0x130`（`main + 0x84360`），它把任务 `+0x8C0` 的构造器交给管理器的槽 `+0xD0`，在 `main + 0x8445C`。Pia 自己会话任务的步骤里有八个位置（`main + 0xCB0CC`-`0xCC738`；`nn::pia::session::LeaveMeshWithHostMigrationJob`（vtable `main + 0x1CEB70`）、`nn::pia::session::ProcessHostMigrationJob`（`main + 0x1CEBA0`）、`nn::pia::session::KickoutManageJob`，以及构造槽 `main + 0x1D26F8`-`0x1D2728` 处的那些类）各自以任务 `+0x90` 处的状态字节为门，读取 `+0x80` 处的持有者（即 `[SessionProtocol + 0x130]`，那个 `Session`；已实时核实），并调用 `[holder + 0x30]` 的 vtable 槽 `+0x130`；`[holder + 0x30]` 就是 `LocalFacade`（实时 typeinfo），其 `+0x130` 项是 `main + 0x8E0B4`。

这条链以封装层的网络状态为门，而且是组长一侧的路径。`swi 0x47` 的函数体只在会话非空、`component + 0x690` 的字节已置位、`component + 0x2770` 至少为 10、且会话谓词 `main + 0xB06BC` 回答 false 时才投递（`main + 0x5879C`-`0x587DC`）。`+0x690` 处的字节就是监听者列表的启用标志：它只在 `[component + 0x6A0] == [component + 0x6A4]`（封装层那一对扫描与加入）时于 `main + 0x53A58` 置位，并由带标签属性分派器的遍历（`main + 0x4EBB0`，模式 `-2`）以及向两者都写入 `-1` 的拆除流程清除。投递自身的各道门随后比较管理器里的两个 Pia 地址结构：`X` 的槽 `+0xD8` 尾调到 `main + 0x95C90`，它要求 `[manager + 0x1268]` 与 `[manager + 0x1288]` 都通过 `main + 0x74BE0`（有效地址），并在 `main + 0x74C18` 中比较相等（先比 `+0x18` 的 u16，再比 `+8` 处的 0x10 字节）；槽 `+0xE8` 要求 `[manager + 0x12D8]` 为零。这两个结构分别持有封装层的本地地址（模拟器上是 `127.0.0.1`）与对端地址（主机的 IP），所以这条链只在主机是所在网络组长时才跑通。加入方主机的记录留在影子里；它的游戏数据仍经会话抵达父端。

在模拟器上于同一帧内实时确认了全部八跳：`swi 0x47` 携带版本 5、语言 2、训练家 id `0x1234`、activity `0x45` 与用户名 `PKLDNTST`：处理函数的影子接下了那 24 字节；把门字节与地址对 poke 成相等后，会话的 `main + 0xB1304` 运行，门面的 `main + 0x8D4AC` 接下栈上的构造器（其应用数据携带 30 字符的记录文本 ``Z8J4;Vk.+>`.uN;#####<P?>######``），管理器的 `main + 0x99C3C` 与其 `+0x250` 委托的 `main + 0xA28E4` 把它传下去，任务的 `+0x60` 校验它并把 `0x180` 字节区域复制进任务 `+0x8C0` 的构造器（`main + 0x87578`），任务的 `+0x130` 由状态机运行到，管理器的 blob 构造器 `main + 0x80C3C` 带着同一段记录文本收到任务的构造器。任务本身作为状态机运行：它的 `+0x38`/`+0x40` 持有当前步骤（一个带单比特虚标志的 vtable 槽，或一个直接函数），基类方法 `main + 0x6EAA0`（“ExecuteCore”，任务的槽 `+0x20`）分派它；观察到的步骤是 vtable 槽 `0xB8`、`0xC8`、`0xD8`、`0xE8`、`0xF8`、`0x108`、`0x118`、`0x138`、`0x148` 以及 `main + 0x891F0` 之类的直接函数。

管理器类（`nn::pia::local::LdnProtocol`；vtable `main + 0x1CA5B0`，指针在 `main + 0x7E244` 处由重定位槽 `main + 0x1D1E98` 构成）把自己的 `NetworkInfo` 放在 `[manager + 0x2D8] + 0xB8`：广播大小是 `NetworkInfo + 0x26A`（`+0x322`），blob 是 `NetworkInfo + 0x26C`（`+0x324`），`NetworkInfo + 0x282` 在 `+0x33A`。它的方法 `main + 0x80C3C`（构造器应用数据的唯一消费者；`main + 0xA2C70` 只有这一个调用者）清零 `+0x380`（`NetworkInfo + 0x2C8`），把应用数据复制过去，把大小设为应用数据加 `0x5C` 并写到 `+0x322`，用持有者自己的方法（其 vtable 槽 `+0x68`）把 `0x5C` 字节的 Pia 系统头写到 `+0x324`，然后调用 `nn::ldn::SetAdvertiseData(holder + 0x324, size)`（PLT `main + 0x160A90`，GOT `0x1d3800`）。另外两个管理器方法广播第二个对象的数据（`main + 0x7F990`、`0x81140`：`[object + 0x18]`，大小为其 vtable 槽 `+0x38` 加 `main + 0x8AC20`），而 `main + 0x80EBC` 在广播前由 `[manager + 0x128]` 重建持有者。

`component + 0x2770`（经 `[component + 0xD0]`）的读者是 `swi 0x53`（布尔）与 `main + 0x0511CC`、`main + 0x0511F4`，后者没有系统调用能抵达。`main + 0x0511F4` 把它与 10 比较，达到或超过时原子装载 `component + 0x2790` 处的一个标志；标志置位则进入 `main + 0x057250` 的延续代码，那里检测第三个参数是否为空。其调用者尚未确认。

`bkpt #0x52` 的组件还拥有分派器（其 vtable 的槽 21）与 2324 个物种名，各六种语言，用 djb2 哈希（`main + 0x056540`，字符串在 `main + 0x1C4470`）。分派器的帧由所有处理函数共用，是 `0x40` 字节的保存寄存器加 `0x310`。

载荷发出 `bkpt #0xFF` 会关闭游戏：封装层提交本次会话的游戏报告、终结 LDN、停止音频、提交一份由存档构造的报告、提交存档并退出。没有任何应答抵达主机。报告在模拟主机上由 `prepo` 服务打印出来，形如：

| 房间 | 字段 |
| --- | --- |
| `network`，每个链路会话一条 | `Flavor` 66、`Trainer`（32 位训练家 id）、`Zone`（链路活动，神秘礼物为 21 `ACTIVITY_WONDER_CARD`）、`Duration`、`Players`、`Slot`、`Rtt` |
| `game`，退出时 | `Flavor`、`TimeStamp`、`Trainer`、`Gender`、`Duration`、`Badges`（一个位掩码）、`TotalBadges`、`HallOfFame`、`TotalHallOfFame`、`CompleteRegionalPokedex`、`RegionalPokedexCnt`、`RegionalPokedexCap`、`CompleteNationalPokedex`、`NationalPokedexCnt`、`NationalPokedexCap`、`Distributed`、`LinkExchange`、`LinkBattle`、`MonsNo1..5` 与 `MonsNoNLevel`、`Money`、`CommsError` |

### 游戏报告的素材

游戏报告是从 flash 映像解析出来的。`main + 0x05A280` 按扇区页脚（签名 `0x08012025`）找最新的槽，把它的 14 个扇区（0xE000 字节）复制到 `component + 0x140 + 0x70`，`main + 0x05A370` 再用一张按游戏而定的描述表遍历它：徽章标志位、名人堂与图鉴标志、与存档密钥异或的钱。每个偏移与位索引都来自那张静态表；复制来的存档提供的唯一计数 `playerPartyCount`（一个字节）限制 `main + 0x05AAE0` 处的队伍遍历，255 条 0x64 字节的记录仍在 0xE000 的副本内。`swi 0x57` 填充 `MonsSelect`（初始宝可梦，经 `main + 0x17DA8C` 的内部编号到全国编号表）；打印出的 JSON 只带该表的一个固定子集，省略 `MonsSelect`。`swi 0x62` 自增 `component + 0xE1B0`，它会成为 `CommsError`：每次调用都让模拟主机 `prepo` 服务（`ProcessPlayReport`）写到主机日志里的下一份报告中 `CommsError` 加一。`swi 0x55` 存到 `component + 0xE1BC` 的 SaveBlock2 指针，其唯一读者是 `main + 0x0577D8`，它检测 `optionsButtonMode == 2`（L=A）。存储位置就是处理函数本身 `main + 0x057308`：分派器在 `main + 0x057058` 设 `x8 = component + 0xE1B0`，处理函数把客户的原始 `r0` 存到 `[x8 + 0xC]`。读者把存入的字经区域表折叠、做边界检查并读一个字节，即折叠区域内的 `+0x13`：两者都是客户相对且做过边界检查的。

`main + 0x059CE4` 从游戏代码挑选表；应用携带全部五张：

| 游戏代码 | 表 | `Flavor` 基值 |
| --- | --- | --- |
| `AXV?` | Ruby | 0x10 |
| `AXP?` | Sapphire | 0x20 |
| `BPE?` | Emerald | 0x30 |
| `BPR?` | FireRed | 0x40 |
| `BPG?` | LeafGreen | 0x50 |

`Flavor` 再加上该语言在 `JEFIDS` 中的索引，所以法语火红报 `0x42`（66）。

表按 id 顺序寻址那 14 个扇区，每个 0x1000：字节偏移 `o` 对应 SaveBlock1 偏移 `((o >> 12) - 1) * 0xF80 + (o & 0xFFF)`。一个标志是 `(bit, byte)` 对；位号高于 7 表示不存在。对照三个反编译项目解码如下：

| 字段 | 红宝石 / 蓝宝石 | 绿宝石 | 火红 / 叶绿 |
| --- | --- | --- | --- |
| 徽章，8 个标志起于 | 字节 `0x23A0` 第 7 位，`FLAG_BADGE01_GET` 0x807 | `0x23FC` 第 7 位，0x867 | `0x2064` 第 0 位，0x820 |
| `HallOfFame` | `0x23A0` 第 4 位，`FLAG_SYS_GAME_CLEAR` 0x804 | `0x23FC` 第 4 位，0x864 | `0x2065` 第 4 位，0x82C |
| `Money` | `0x1490`（SaveBlock1 + 0x490），无密钥 | `0x1490`，异或 `0x00AC`（SaveBlock2 `encryptionKey`） | `0x1290`（+0x290），异或 `0x0F20` |
| 队伍计数、队伍 | `0x1234`、`0x1238` | `0x1234`、`0x1238` | `0x1034`、`0x1038` |
| `TotalHallOfFame` | `0x25E8`，`GAME_STAT_ENTERED_HOF` | `0x2644` | `0x22A8` |
| `LinkExchange` | `0x2614`，`GAME_STAT_POKEMON_TRADES` | `0x2670` | `0x22D4` |
| `LinkBattle`，取和 | `0x261C..0x2624`，链接胜、负、平 | `0x2678..0x2680` | `0x22DC..0x22E4` |
| 地区图鉴规模 | 202 | 202 | 151 |

在有密钥的游戏里，游戏统计量与钱用的密钥异或。

`Distributed` 是四个位，每一位都是开通前往凭票岛屿的渡船的那个标志：

| 位 | 标志 | 红宝石 / 蓝宝石 | 绿宝石 | 火红 / 叶绿 |
| --- | --- | --- | --- | --- |
| 0 | 肚脐岩（神秘票） | 不存在 | `0x240C` 第 0 位，`FLAG_ENABLE_SHIP_NAVEL_ROCK` 0x8E0 | `0x2069` 第 2 位，0x84A |
| 1 | 诞生岛（极光票） | 不存在 | 不存在 | `0x2069` 第 3 位，0x84B |
| 2 | 南方孤岛（无限票） | `0x23AA` 第 3 位，`FLAG_SYS_HAS_EON_TICKET` 0x853 | `0x2406` 第 3 位，`FLAG_ENABLE_SHIP_SOUTHERN_ISLAND` 0x8B3 | 不存在 |
| 3 | 遥远岛屿（古老海图） | 不存在 | `0x240A` 第 6 位，`FLAG_ENABLE_SHIP_FARAWAY_ISLAND` 0x8D6 | 不存在 |

在火红与叶绿里，两个标志都由票的神秘事件脚本置位 [mystery_event_msg.s:222,281]，也由 Switch 版的名人堂授予置位 [post_battle_event_funcs.c:58]；一份已经进过名人堂的存档被带过来时报 0。

### 坏词过滤器

`swi 0x4D`，处理函数 `main + 0x0571FC`，把 `r0` 解析为 GBA 地址，要求其后面有 256 字节，把 ASCII 字符串转成 UTF-16 并跑平台的脏词检查，就地改写字符串。`r1` 非零会选第二种模式，游戏从不用（`r1` = 1 以同样方式掩码）。游戏经 `svc_BadWordCheck` 调用它，先把名字转成 ASCII 再转回 [sloopsvc.c:211]。命名画面只在它回答 0 时才保存输入的名字 [naming_screen.c:686]。

| 送出的字符串 | `r0` | 之后的字符串 |
| --- | --- | --- |
| `hello world` | 0 | `hello world` |
| `hello fuck` | 1 | `hello ` 然后四个 `0xA1` 字节 |
| `POKELDN` | 0 | 不变 |
| `ASSASSIN` | 0 | 不变 |
| `NINTENDO` | 0 | 不变 |

路径 [main + 0x0571FC -> main + 0x057458]：处理函数折叠 `r0`，要求折叠处后面有 `0x100` 字节，并把字符串复制进帧 `-0x100` 处的 `0x100` 字节栈缓冲区（`main + 0x85645F0` 处的复制以其 `w1 = 0x100` 参数为界）。到 UTF-16 的转换从该缓冲区进行到 `sp + 0x10` 处的 `0x200` 字节缓冲区（[main + 0x855F100]，`w2 = 0x200`），脏词检查经一个全局指针进行 [main + 0x574AC，被调用者 `main + 0x86664C0`]，被掩码的字符串再复制回客户的折叠处。两个缓冲区的末端都在分派器自己 `0x310` 字节的帧内（`sp + 0x210` 与 `sp + 0x310`）；复制既碰不到保存寄存器，也越不出帧。替换字节是常量 `0xA1`。

### 封装层自己的扫描流水线

封装层经自己的 PLT 用 `nn::ldn::Scan` 扫描网络（`main + 0x160B70`；`ScanPrivate` 在 `main + 0x160B60`），调用点 `main + 0x80944`/`0x8095C` 上的管理器对象是 `x23`，`w2 = 0x18` 个网络，结果进入 `manager + 0x14C0` 处的内联数组，24 条 x `0x480`（初始化时清零一次，`main + 0x7E290`）。模拟器自己的 ldn 服务把线路上的 `ScanResponse` 主体直接转型为 `NetworkInfo` 而不做长度检查，所以另一席的字段值原样抵达封装层。

一个消费循环（`main + 0x80A20..0x80B9C`）遍历该数组：它把 `sp + 0x128` 处的 `0x480` 字节记录清零（`main + 0x874A0`），把表项转换进去（`main + 0x87374`：先整块 `0x480` memcpy 到 `record + 0xB8`，再按位精确读取字段：源 `+0xA`、`+0x11`（一次 15 字节整数解析，`main + 0xA9830`，十/十六/八/二进制，带 `b`/`x` 前缀，每次推进都做边界检查）、`+0x26A`（广播数据大小）、`+0x281`/`+0x282`、`+0x11A..0x11F`；写入 record 的 `+0x90`、`+0xA0`、`+0xA2`、`+0xA4`、`+0xA6`、`+0xB0`），然后让记录通过一个过滤虚函数（`main + 0x80A70`，`LocalSearchNetworkSetting::vfunc2` 在 `main + 0xA0F48`；该设置是 `LdnBackgroundProcessJob` 在 `+0x300` 的子对象，vtable `0x1CB408`）与一个接受虚函数（`main + 0x80A94`，站点列表的 `LocalSessionProperty::vfunc11` 在 `main + 0x87420`，它复制记录并调用 `main + 0xA1BAC` 处的 `vfunc17`）。过滤器把设置 `+0x14` 的标志字节与属性的会话 id（`+0x98`）比对，把 u16 `+0xa2` 与 `[setting + 0x12, setting + 0x10]` 比对，把 `+0xa6` 的布尔值比对；接受函数复制记录，把 record `+0x11` 处的 15 字节哈希进 `+0x90`，并把标志存到 `+0xa7`。两者都不读显示名。

被接受的网络进入父端候选者列表：16 个槽 x `0x1A` 字节在 `owner + 0x6050F2`，写索引在 `owner + 0x605294`，上限 15（`cmp w8, #0xf; b.le` [main + 0x58C3C]）；数组止于 `+0x605292`，紧贴索引。填充是所有者类（vtable `main + 0x1C3B30`）的槽 `+0xA0`，即 `main + 0x58BF8`，由 `main + 0x536A4` 对每个扫描结果站点调用；站点的名字长度来自站点自己的虚函数 [槽 `+0x50`]，而 `sub w8, w0, #1; cmp w8, #0x3f; b.hi` [main + 0x5364C] 在调用前丢开 `x6 > 0x40` 的情况。填充内部，`sp + 7` 处的 `0x41` 字节栈缓冲区接收 `memcpy(sp + 7, x5, x6)`，`x6 > 0x40` 时跳过尾部补零的 memset [main + 0x58C68]：于是 `x6 > 0x40` 时复制会触及该帧保存的 `x29`/`x30`（缓冲区偏移 `0x59`/`0x61`）。已解码的那个调用者先做了限幅，所以经它进来的长度最多 `0x40`；映像里装载某类槽 `+0xA0` 的八个位置中，`main + 0x536A4` 是唯一确认在该类上分派的。

在模拟主机上实测，一个主机在做广播：计数 1，slot 0 = 该主机的广播逐字节相同：16 字节游戏数据（activity `0x15`）、8 字节显示名、父端 id u16（`0x59f1`）。

在 `main` 里，该列表只经填充那一族函数写入（`main + 0x58BB4`、`0x58BE4`、`0x58BF8`），全是虚函数；映像里其余以组件为锚的访问都是读。所有者类的 vtable 指针 `main + 0x1C3B30` 在 `main` 里由装载重定位槽 `main + 0x1D1B38`（值为 `main + 0x1C3B20`）再加 `0x10` 构成：`main + 0x58558` 在清零 `component + 0x6050F0` 候选者列表时存入它，两个组件初始化函数里的 `main + 0x58FD8`/`0x59054` 同样如此。同样的写法构成管理器类的指针（槽 `main + 0x1D1E98`；`main + 0x7E244`、`0x7E4D0`）与会话类的指针（槽 `main + 0x1D2770`；`main + 0xB7D24`、`0xB7E78`）。

### Pia 会话消息分派器

封装层原生的 Pia 会话接收是 `main + 0xB9FC0` 处的一个类型 switch。它遍历一条节点链：`[node + 0x10]` 是消息体，其首字节是类型，而节点自己的前三个字节是用作队列键的协议地址。当管理器对象的 `[x0 + 0xA0]` 非零且类型不超过 `0x11` 时，节点被分派；switch 是 `adr x8, main + 0xB9FD0`（`main + 0xB9FCC`）、`ldrb w9, [main + 0x180FC9 + type]`（`main + 0xB9FC4`；`main + 0xB9EFC` 处是 `adr x27, main + 0x180FC9`）、`add x8, x8, w9, lsl #2`、`br x8`。`main + 0x180FC9` 处的字节表每个类型一项；十八个 case 块位于 `main + 0xB9FD0 + index * 4`，每块以无条件的 `b main + 0xB9F80` 结束，并各自调用其处理函数（`main + 0xBCB60`、`main + 0xBE438`、`main + 0xBE8BC` 等）。

每个处理函数都在触碰消息前按消息长度做边界检查：类型 1 的处理函数 `main + 0xBE438` 以 `cmp w2, #0x15; b.ne` 开头（只有 `0x15` 字节的消息才走到复制），审计解码出的各类型测试为：类型 2 `>= 4`，类型 3 `== 0x16 or 0x22`，类型 4 `== 0xf`，类型 6 `>= 0xf`，类型 9 `== 0x1e or 0x2a`，类型 10 与 12 `== 0x15`，类型 11 `>= 0xe`，类型 13 `== 0xa`，类型 14 `>= 0x4d`，类型 17 `>= 0xd`。变长读取函数 `main + 0xC0D90` 由位计数推字节数，与声明长度比较，不足即拒绝。这一组里没有发现哪个处理函数会把消息控制的长度复制进定长缓冲区。

这些类型就是 Pia 会话协议自己的消息类型；主机的会话层（`pokeldn/ldn/pia_connect.py`）把它们编号为 0 加入请求、1 加入确认、2 加入响应、3 离开请求、4 离开响应、5 更新、6 更新确认、7 开始主机迁移、8 迁移确认。类型 1 的处理函数 `main + 0xBE438` 把 21 字节的消息读作 `[0]` 类型、`[1:9]` 与 `[9:0xB]` 源站点的常量 id 与变量 id、`[0xB:0x13]` 与 `[0x13:0x15]` 目的站点的对应值，除非目的这一对与传输层自己的（`[transport + 0x1B8]`、`+0x1C0`）相符，否则拒绝，然后查出源站点并在其上调用 `main + 0xC9B4C`。类型 2 的处理函数 `main + 0xBE8BC` 接受 4 字节及以上，以管理器的状态字节（`+0x30 == 0xFD`）为门，并按消息第 3 字节在 3 到 0x10 之间 switch。

接收路径的所有者是会话类（`nn::pia::session::SessionProtocol`；vtable 基址 `main + 0x1CE8E0`；其 vtable 指针在 `main + 0xB7D24`/`0xB7E78` 处由重定位槽 `main + 0x1D2770` 构成，构造函数是 `main + 0xB7E70`）。泵是该类 vtable 的槽 `+0x50`，即 `main + 0xB9CA0`，它调用遍历器 `main + 0xB9DB0`；这条链挂在 `[protocol + 0xF8]` 处的对象（会话包读取器，由协议管理器挂上）的 `+0x70` 表上（`main + 0xD6D68` 返回该地址）。消息对象由 `main + 0xD4430` 构造（其 vtable 指针来自重定位槽 `main + 0x1D27B0`）。Pia 库本身静态链接在 `main` 里（映像带有 `SDK MW+Nintendo+PiaCommon-6_42_1-Release` 与会话任务名）。

### Pia 库自己的线路解析

`main` 链接了整套 Pia 6.42.1 栈（映像带有 `PiaCommon`、`PiaLocal`、`PiaNet`、`PiaSession`、`PiaTransport` 与 `Pia_ZStandard` 的 `SDK MW+Nintendo+...` 发行字符串，以及改写后的类名）。上文只按 vtable 指称的类对应如下：

| 上文说法 | 类（vtable typeinfo 里的改写名） | vtable |
| --- | --- | --- |
| 网络管理器 | `nn::pia::local::LdnProtocol` | `main + 0x1CA5B0` |
| 会话对象（构造器在 `+0x8C0`） | `nn::pia::local::LdnBackgroundProcessJob` | `main + 0x1CAC48` |
| 会话类（接收路径） | `nn::pia::session::SessionProtocol` | `main + 0x1CE8E0` |
| 包对象 | `nn::pia::common::Packet::Header` | `main + 0x1CA100` |
| 本地接收流 | `nn::pia::local::LocalInputStream` | `main + 0x1CA540` |
| 网络接收流 | `nn::pia::net::NetInputStream` | `main + 0x1CC1D0` |

传输类的 vtable 是 `PacketReader` `main + 0x1CF1A8`（第二个在 `main + 0x1CE7E8`）、`PacketWriter` `main + 0x1CF258`、`ProtocolManager` `main + 0x1CF3A0`、`ProtocolMessageReader` `main + 0x1CF458`、`ProtocolMessageWriter` `main + 0x1CF490`、`ReliableProtocol` `main + 0x1CF4C8`、`Station` `main + 0x1CF8C8`、`StationManager` `main + 0x1CF938`、`ReceiveThreadStream` `main + 0x1CFB20`、`SendThreadStream` `main + 0x1CFB68`；会话类的是 `Session` `main + 0x1CE300`、`SessionPacketReader` `main + 0x1CE748`、`SessionPacketWriter` `main + 0x1CE7F8`、`SessionStation` `main + 0x1CED20`；本地类的是 `LocalProtocol` `main + 0x1CA9B0`、`LocalService` `main + 0x1CB460`、`LocalFacade` `main + 0x1CB548`。

**包。** 包对象是 `0x1D18` 字节：解析后的头部在 `+8` 到 `+0x24`，数据报缓冲区在 `+0x30`（容量 `0x1C5C`，即追加辅助函数 `main + 0x75664` 与 `main + 0x75694` 中的界，后者在 `+0x14` 记录页脚大小），收到的大小在 `+0x1C90`（本地接收路径在 `main + 0x7DE40` 处、一次 `0x5AC` 字节接收并针对该上限检查之后写入）。它的解析（`main + 0x752D4`，vtable 槽 `+0x18`；入口 `main + 0x752C8` 提供对象自己的缓冲区与常量 `0x1C5C`）要求多于 `0x1C` 字节，并读取 `0x1D` 字节的头部：

| 位置 | 大小 | 含义 | 落到 |
| --- | --- | --- | --- |
| 0x00 | 4 | 魔数 `0x32AB9864`，大端 | `+0x08` |
| 0x04 | 1 | 版本在第 0-6 位，加密标志 `0x80` | `+0x0C` |
| 0x05 | 1 | 一个字节，原样保留 | `+0x0D` |
| 0x06 | 2 | 目的变量 id，大端 | `+0x0E` |
| 0x08 | 2 | 源变量 id，大端 | `+0x10` |
| 0x0A | 2 | 包 id，大端 | `+0x12` |
| 0x0C | 1 | 页脚大小 | `+0x14` |
| 0x0D | 8 | nonce，原样保留 | `+0x15` |
| 0x15 | 8 | GCM 标签，原样保留 | `+0x1D` |

本应用使用的版本是 `0x10`（16）：有效性检查 `main + 0x75610` 要求魔数、`([+0xC] & 0x7F) == 0x10` 且 `size - 0x1D < 0x1C40`。载荷指针是 `+0x4D`（缓冲区越过头部之处，`main + 0x75474`）；`main + 0x75458` 返回 `buffer + t`，其中 `t = (n + 0x1D)` 按 32 位算术计算，当 `(t >> 2) > 0x716` 时返回空。该容量检查允许 `t` 到 `0x1C5B`；消息遍历器则另行按收到的大小减去头尾页脚来检查（`main + 0xDE278`）。

**套接字与接收流。** 套接字是一个小的持有者（构造函数 `main + 0x6D93C`：`+0` 处 fd `-1`，`+4` 处一个计数，`+8` 协议族，`+0xC` 协议）；`main + 0x6D95C` 打开它（`nn::socket::Socket`，PLT `main + 0x160940`），`main + 0x6DBF4` 关闭（`main + 0x160950`），`main + 0x6DCD0` 绑定（`main + 0x160960`），`main + 0x6DE6C`、`0x6DF44`、`0x6E00C`、`0x6E0F0` 设置选项（`main + 0x160970`）。数据报调用是 `main + 0x6E1D0`（`nn::socket::RecvFrom`，PLT `main + 0x160980`，标志 `0x80`，源地址由 `main + 0x6E9D0` 转回）与 `main + 0x6E538`（`nn::socket::SendTo`，`main + 0x160990`）。本地接收流（变量 id 在 `+0x88`，锁在 `+0x68`，套接字持有者指针在 `+0x18`）跑泵 `main + 0x7DD10`（vtable 槽 `+0x10`）：它接进一个包的缓冲区并把头部解析进去（`main + 0x7DDEC`；`main + 0x6E1C8` 是 thunk）；包过滤器 `main + 0x91280`（槽 `+0x20`）首先要求包有效。当版本至少为 7、页脚非空、目的变量 id 至多为 1 时，页脚必须至少含两个字节，且流自己的 id（`+0x88`）必须非零并出现在它的那些大端 u16 收件 id 中（`footer_size >> 1` 项）。另外，当 `([+0xC] & 0x7E) >= 6` 且目的为 2 或更大时，它必须等于流自己的 `+0x88`。

过滤器把收件指针算作 `packet + (size - footer) + 0x30`，那是 `main + 0x912EC` 处 `sub w8, w8, w9` 之后；消息遍历器 `main + 0xD6460` 与解析器 `main + 0xDE278` 把遍历上界算作 `size - footer - 0x1d`（`main + 0xD651C`、`main + 0xDE298`）。这两个减法都不以页脚大小是否装得进数据报为条件。页脚大小字节是数据报偏移 12，在明文头部里，所以对端可以随意设置它。页脚大小超过数据报大小不会让过滤器故障：六个 31 字节、页脚 `0x40` 的数据报都到达了套接字，会话继续跑下去（在模拟器上实测）。

**线程。** 传输层的接收与发送循环是名为 "Pia ReceiveThreadStream"（在 `main + 0xE9020` 启动，名字经 `main + 0xE9034` 的 `adr`）与 "Pia SendThreadStream"（`main + 0xEA758`）的 `nn::os` 线程，经 `main + 0xF6010` 创建（`nn::os::CreateThread`，PLT `main + 0x15FDF0`，以及 `StartThread`，`main + 0x15FE00`）。

**从线路到会话处理函数。** 收到的会话消息由会话包读取器解析，并留在按地址索引的表里，会话协议每次更新都遍历该表。

`nn::pia::session::SessionPacketReader`（vtable `main + 0x1CE748`）继承 `nn::pia::transport::PacketReader`（vtable `main + 0x1CF1A8`）。读取器的 `+0x30` 方法（`main + 0xD5DE0`）处理收到的包，并调用 `main + 0xD6460(reader, packet)` 遍历其中的消息。遍历器从数据报偏移 `0x1D` 开始，在 `packet_size - footer_size` 之前停下（`main + 0xDE278`、`0xD6510`-`0xD6538`）；页脚跟在载荷之后。它用 `main + 0x74EA8` 解析每条消息，并经读取器的 `+0x78` 虚函数取用作队列键的协议地址（`main + 0xD6D0C`：消息 `+0x2C` 处的 u16，外加 `+0x2E` 处的字节作为其高位），然后调用 `main + 0xD6944(table, address, message)`。

该表内嵌在 `reader + 0x70`：`+0` 处是 u32 桶数，`+8` 处是指向桶数组的指针（每桶 0x18 字节，链头在 `+0`，链尾在 `+8`），`+0x40` 处是可选的哈希回调。`main + 0xD6944` 先装载数组指针，再加 `index * 0x18`；桶并不内联在表里。桶索引是 `callback(address) % count`，没有设置回调时是 `(address[0] + address[1] + address[2]) % count`。`main + 0xD71F0(bucket, address, message)` 取一个节点，把消息复制进去（三个地址字节在 `+0`，消息体指针在 `+0x10`，id 在 `+0x18`，更多字段在 `+0x20` 到 `+0x30`，其余经 `main + 0x74C54`），并把它追加到该桶的双向链表（next 在 `+0x78`，prev 在 `+0x80`）。

协议一侧：`nn::pia::session::SessionProtocol` 的 `+0x50` 虚函数（`main + 0xB9CA0`）每次更新都跑 `main + 0xB9DB0`。它读取 `[protocol + 0xF8]`（即读取器，挂接方式见下），取读取器 `+0x70` 处的表，为协议自己的三字节地址算出桶（`+0x120` 处的 u16 加 `+0x122` 处的字节，由 `+0x18` 虚函数 `main + 0x828E4` 读取；这一对是 `nn::pia::transport::Protocol` 的字段，由 `main + 0xDA614` 设置），遍历链，并按 `[node + 0x10]` 处消息体的首字节经跳转表把每个节点分派给各处理函数（`main + 0xBCB60`、`main + 0xBE438`、`main + 0xBE8BC`、`main + 0xBF2D4` 等），参数是 `(protocol, node, id)`。

挂接：协议管理器（内嵌在所有者 `+0xC8`，其协议表在 `+0x18`）遍历自己的表，用所有者的 `+0xF8` 与 `+0x100` 设置每个协议的 `+0xF0` 与 `+0xF8`（设置器 `main + 0xDA8C8` 与 `main + 0xDA8D0`，广播 `main + 0xDB740`，在 `main + 0xEC0E4` 以那一对调用；任一参数为零即拒绝）。`+0xF8` 那个对象就是读取器，这就是遍历器用的表是读取器 `+0x70` 的原因。

实时情形：管理器位于 `[session + 8] + 0xC8`（即上面的所有者），它在 `[manager + 0x18]` 的表里 `+0` 是 u32 桶数、`+8` 是桶数组指针。每个桶 `0x18` 字节：`+0` 是一个节点，节点的 `+8` 是协议，节点的 `+0x30` 链向下一个节点。在模拟的会话里，该表计数为 `19`，正好六个协议，每种一个，以协议地址为键（u16；`+0x122` 处的字节为零，每个协议的 `+0x108` 持有网络的 Pia var，`0x8fa2`/`0x0766`）：`0xfd01` `nn::pia::local::LdnProtocol`、`0xfd03` `nn::pia::transport::RttProtocol`、`0xfd05` `nn::pia::transport::UnreliableProtocol`、`0xfd0a` `nn::pia::transport::ReliableProtocol`、`0xfd0d` `nn::pia::session::SessionProtocol`、`0xfd0f` `nn::pia::transport::MonitoringDataProtocol`。这些协议每种一个，不是每站点一个：`SessionProtocol` 的泵在 8 次里 8 次都追踪到同一个实例，读取器表的节点也归在协议地址下（`0xfd0a`，消息 id `0x60`）。实例由 `main + 0xB1F60` 创建并注册（经 `main + 0xDB114` 分配 `0xD8E8` 字节，构造函数 `main + 0xB7D0C`，以地址对为键插入管理器的映射）；Session 的构造函数调用它一次，并把返回的地址存到 `+0x12`/`+0x14`。

`nn::pia::transport::Protocol` 基类（vtable `main + 0x1CF308`，构造函数 `main + 0xDA548`，vtable 指针来自重定位槽 `main + 0x1D2808`）携带三字节地址在 `+0x120`/`+0x122`，锁在 `+0xC8`，挂接的那一对在 `+0xF0`/`+0xF8`，两个 8 字节加 u16 的配置值在 `+0x100`/`+0x108` 与 `+0x110`/`+0x118`，状态字节在 `+0x123`，标志在 `+0xD8`。

## 改指主机的出站消息

`r0` 就是 `&client->param`，所以 `struct MysteryGiftClient` [include/mystery_gift_client.h:71] 相对它有固定偏移：

| 字段 | 相对 `r0` |
| --- | --- |
| `client->sendBuffer` | 0x10 |
| `client->link.sendSize` | 0x34 |
| `client->link.sendBuffer` | 0x3C |

`MysteryGiftLink_InitSend` 会存下传给它的指针 [mystery_gift_link.c:59]；CRC 在发送时对 `link->sendBuffer` 的 `link->sendSize` 字节计算 [:166]。在 InitSend 与发送之间运行的载荷，可以把主机的出站消息指向任意地址：

    CLI_RECV -> CLI_LOAD_TOSS_RESPONSE -> CLI_RUN_BUFFER_SCRIPT -> CLI_SEND_LOADED

顺序反过来时，InitSend 会覆盖载荷的改动。

绝不要导出在 CRC 帧与发送帧之间会变的区域：

```c
case 0:  header.crc = CalcCRC16WithTable(link->sendBuffer, link->sendSize);   // one frame
case 1:  SendBlock(0, link->sendBuffer + blocksize, ...);                     // the next
case 2:  if (CalcCRC16WithTable(...) != link->sendCRC) LinkRfu_FatalError();  // the one after
```

[mystery_gift_link.c:155]。`gRngValue`（0x03004220）每帧推进两步；对它的导出会让消息体 CRC 失败，主机报「erreur de connexion」。`buffer_script.build_memory_dump` 会拒绝任何与它重叠的范围；绕开它导出，或改用 `rng-trace`，后者经 4 字节通道把它返回。其他任何易变区域也得用同样办法找。

## 各载荷

### `trainer-id-probe`

24 字节，只读。主机几秒前就已在 `MysteryGiftLinkGameData` 里送出了自己的 `playerTrainerId` [mystery_gift.c:337]，所以答案是已知的。

```arm
    ldrh    r3, [r1, #0x0A]         @ SaveBlock2.playerTrainerId[0..1]
    ldrh    ip, [r1, #0x0C]         @ SaveBlock2.playerTrainerId[2..3]
    orr     r3, r3, ip, lsl #16
    str     r3, [r0]                @ *param
    mov     r0, #1
    bx      lr
```

若相符，说明它确实以 ARM 状态运行、用的是反编译里的参数、指向真的 `gSaveBlock2Ptr`，并返回 1；值不同说明参数或偏移不对；没有 `Buffer script status:` 行，说明客户端脚本的形态不对，或调用根本没到。7 个字符的玩家名，其终止符会覆盖游戏数据里的 `playerTrainerId[0]` [mystery_gift.c:364]；主机于是比较高三个字节。

### `save-dump` 与 `memory-dump`

`memory-dump` 取绝对地址。`save-dump` 经 r1 与 r2 在任意构建上按任意偏移读任一存档块。每次运行最多 1024 字节；再多 `MGL_Receive` 会拒绝 [mystery_gift_link.c:102]。

    HOST --buffer-script save-dump --dump-block sav2 --dump-size 256 --version firered
    HOST --buffer-script memory-dump --dump-address 0x0201C000 --version firered

它们能到达 0x0038 处的 `SaveBlock1.playerParty`、0x0290 处与 0xF20 的 `SaveBlock2.encryptionKey` 异或的 `money`、背包、flags 与 vars，以及 IWRAM（`gRngValue`）。

### `memory-dump-multi` 与 `memory-dump-scatter`

`MG_LINK_BUFFER_SIZE` 限的是一条消息，不是一次会话。客户端从其 1024 字节接收缓冲区里跑一串命令 [mystery_gift_client.c:140]，而导出那三步

    CLI_LOAD_TOSS_RESPONSE -> CLI_RUN_BUFFER_SCRIPT -> CLI_SEND_LOADED

会尽可能多地重复：每条命令 8 字节、循环外还有三条固定命令时，能跑 41 轮。`mg_script.MAX_DUMP_BLOCKS` 把它压在 32，因为中途死掉的会话会丢掉所有块。16 KB 的导出在 ESP32 无线电上花了约 57 秒，块间隔约 2.5 秒。

`CLI_RUN_BUFFER_SCRIPT` 每一轮都会重新复制映像 [:238]，所以游标放在 `client->param` 里：每轮发送 `base + index * 1024` 并传出下一个索引。高半字里没有 `0x5A5A0000` 的 `param` 视为第零轮。

`memory-dump-scatter` 改为索引一张基址表：

    adr     r3, .Ltable
    ldr     r3, [r3, r1, lsl #2]    @ this block's own base
    str     r3, [r0, #0x3C]         @ client->link.sendBuffer

`adr` 是 PC 相对的。32 个槽全部填写，未用的填成最后一个地址，于是多跑一轮只会重发一个已持有的块，而不是把消息指向 0。分散的块每次加入能抓到的短函数体约为连续块的四倍；对某一组超过一兆字节、166 个从未读到的函数体：

| 一次加入、从线路上取 16 KB | 抓到的函数体 |
|---|---|
| `memory-dump-multi`，在最佳基址处取十六个连续块 | 22 |
| `memory-dump-scatter`，最密的十六个 KB | 83 |
| `memory-dump-scatter`，32 块 | 119 / 166 |

可读性检查覆盖每个分散块。各块端到端落到一个文件里；`--dump-scatter A,B,C` 让 `script_read.dumps` 把每块放到它自己的基址，标记为 `<run>[0]`、`<run>[1]`……`--dump-blocks 1` 会逐字节返回 `CLIENT_SCRIPT_DUMP_MEMORY`。

### `anchors`

把十一个字写进 `client->sendBuffer`，并把 `link->sendSize` 加宽到 44；不需要改指，因为 `CLI_LOAD_TOSS_RESPONSE` 已经把 `link->sendBuffer` 指向那里 [MysteryGiftClient_InitSendWord, mystery_gift_client.c:91]。

| 字 | 内容 | 某次启动 |
| --- | --- | --- |
| 0 | `sub ip, pc, #8`：主机把代码放在哪 | 0x0201C000 |
| 1 | `lr`：调用之后的 ROM 地址 [mystery_gift_client.c:276]，第 0 位置位，因为调用者是 THUMB | 0x08148C75 |
| 2 | `sp` | 0x03007DB8 |
| 3 | `r0` = `&client->param`，即 `AllocZeroed` 把客户端放进 `gHeap` 的位置 | 0x020020D4 |
| 4-5 | gSaveBlock2Ptr、gSaveBlock1Ptr | 0x02024598、0x0202553C |
| 6-9 | 四个 AllocZeroed 缓冲区：send、recv、script、msg | 0x02006510 .. 0x02007140 |
| 10 | InitSend 留下的 `link->sendBuffer`；必须等于字 6 | 0x02006510 |

字 4-5 在每场战斗与每次读取后都会变 [load_save.c:75]；字 3 与 6-9 取决于堆状态。字 1 锚定一个反编译调用点；字 10 等于字 6 证实结构体偏移。各缓冲区相隔 0x410（1024 字节加 16 字节块头），与 `malloc.c` 的描述一致。`buffer_script.describe_anchors` 会连同它的一致性检查打印全部十一个字。

### `save-write`

把载荷尾部复制进块，然后把 `link->sendBuffer` 指向目标，于是应答就是存档现在持有的内容。会话以 `CLI_MSG_BUFFER_SUCCESS` 结束，它抵达 `MG_STATE_SAVE_LOAD_GIFT` 并把写入提交到 flash；从标题画面重新读取后它依然存在。

    HOST --buffer-script save-write --dump-block sav2 --dump-offset 0xB20 \
        --write-text "some text" --version firered

一条载荷携带 936 字节。更长的数据按 936 分片，每片一条载荷，全都在同一次会话里依次运行；客户端按其命令表接收并运行它们 [mystery_gift_client.c:145, 236]。应答就是最后一片之下存档持有的内容。

`build_save_write` 拒绝 `struct SaveBlock2` 中 0x090 的 `filler_90[8]` 与 0xB20 的 `filler_B20[0x400]` 之外的任何区间 [global.h:345,357]，而 `src/` 里没有任何东西引用它们。`filler_B20` 之后四个字节就是 `encryptionKey`，钱会与它异或。`--write-unsafe` 可以强制覆盖。块落到 flash 的哪里是轮换的（[id 住在哪里](#where-an-id-lives-and-which-sector-carries-the-slots-counter)）。

一次 `save-write` 只改动它点名的区间：一次 256 字节写入改动了 SaveBlock2 的 196 字节，全在区间内，SaveBlock1 一个字节没动。游戏里没有任何东西写 `filler_B20`：写在那里能跨存档留存（实测十代），跨神秘事件、神秘卡片、软复位与游玩留存（一分钟游玩中 SaveBlock1 有 1456 字节变动，而那 256 字节未变）。

### `memory-scan`

取一个 32 位搜索值和一段范围。每次调用扫完它那批 32 字节块，把游标写回自己的映像并返回 0；走到尽头的那次调用把 `link->sendBuffer` 改指结果并返回 1。映像开头是一条跳过其参数的分支：

| 偏移 | |
|---|---|
| 0x000 | `b .Lcode` |
| 0x004 | 游标：起始地址，由载荷推进 |
| 0x008 | 结束 |
| 0x00C | 搜索值 |
| 0x010 | 每次调用的块数 |
| 0x014 | max_calls，看门狗 |
| 0x018 | 结果：命中数、最终游标、用掉的调用数、已存命中 |
| 0x028 | 结果：64 × (地址, 值) |
| 0x228 | 代码 |

这个预算保护需要帧的 RFU 链路。内层循环是一次八字的 `ldmia` 与八条链式 `cmpne`，每八字约 14 条指令；默认的 512 块在 unicorn 上每次调用是 7703 条指令，从 EWRAM 取指（16 位总线，一次 ARM 取指约 6 周期）约占一帧 280896 周期里的 60000。16 MB 卡带是 1024 次调用，约 17 秒。`--scan-blocks` 可以改它；全程主机每秒读约 60 个子帧。

`max_calls` 默认是范围所需次数加二；看门狗叫停时会以一个短游标作答，说明从哪里继续。应答总是 528 字节，所以 `len(dump) == buffer_dump_size` 就证明改指成功。`found` 统计所有命中，`hits` 保留前 64 个。`ldmia` 只看字对齐的命中：若搜索值相对于真实步长从不对齐，就只会返回零。

### `table-scan`

按形状找表：每一段最长的 `runlen` 字连续段，其中每个字恰好比前一个高 `delta`，以该段起点与首值作答。`gSpecialVars` [data/event_scripts.s:51] 列出 `gSpecialVar_0x8000` 到 `0x800B`，十二个连续的 `u16` [event_data.c:16]，所以它的前十二个字步长为 2，首值是 `&gSpecialVar_0x8000`。

    HOST --buffer-script table-scan --table-delta 2 --table-runlen 12 \
        --table-start 0x08140000 --table-end 0x08400000 --version firered

第 12 项是 `gSpecialVar_Facing`，声明在 `Result` 与 `LastTalked` 之后，比第 11 项高 6，所以该段恰好是十二个，13 就找不到任何东西。

形状测试每个字约 7 条指令，按值找约 1.75 条，所以 `TABLE_SCAN_DEFAULT_BLOCKS` 是 192 个 16 字节块，负载与 `memory-scan` 的 512 个 32 字节块相同。`run`、`runstart` 与 `expect` 放在 0x22C..0x234，紧挨游标，每次让出都会保存，因为一段可能横跨 `ldmia` 与帧边界。`expect` 从 0 起，所以首字为零会被记给一段未写 `runstart` 的段；`read_table_scan` 会丢弃范围外的命中。

同一形状能找到活动的 `struct ScriptContext`：`InitScriptContext` 把命令表及其末尾存在 +0x5C 与 +0x60 [include/script.h]，17 项的表相差 68，所以对 EWRAM 用 `--table-delta 0x44 --table-runlen 2` 会以该 context 的地址与该表的地址作答。context 在脚本跑过之前全是零，所以扫描必须在同一次启动里跟在神秘事件礼物之后。`--table-delta 0x358`（214 项）能找到野外脚本的 context，其 `cmdTable` 就是已知的 `gScriptCmdTable`。

### `rom-checksum`

按最多 128 块对一段求范围，每块一个和，于是主机就能点名卡带上与它的 ROM 映像不同的块；对某一块再用更小的块跑第二次，就能缩小范围。帧循环、预算、看门狗与改指发送都沿用 `memory-scan` 的。每块从 0 起按升序把字相加：

    acc = w + ror(acc, 31)          one `add r0, rN, r0, ror #31` per word, mod 2^32

`rom_checksum_reference` 从 ROM 文件算出同样的和。XOR 会互相抵消（重复的字和为 0；相隔 32 字的等量变化会抵消）。超出参照映像的块按它的和命名：全零、全 0xFF、开总线（每个半字各自取地址的一半）、镜像，或 CONTENT。

| 偏移 | |
|---|---|
| 0x000 | `b .Lcode` |
| 0x004 | 游标：起始地址，由载荷推进 |
| 0x008 | 结束 |
| 0x00C | 起始 |
| 0x010 | 每次调用的 32 字节块数 |
| 0x014 | max_calls，看门狗 |
| 0x018 | shift：块大小的 log2，5 到 25 |
| 0x01C | 进行中那块的累计和，跨调用携带 |
| 0x020 | 结果：最终游标、用掉的调用数、已存的和、回显的 shift |
| 0x030 | 结果：128 × u32 块和 |
| 0x230 | 代码 |

应答是从 0x020 起的 528 字节。构造器拒绝起点不对齐到块、范围不是整数块、超过 128 块、以及不是 32 字节到 2 的幂的块大小。每八字 13 条指令；512 个块每次调用 6688 条指令。默认的 0x08000000..0x09000000 按 128 KiB 分块是 1024 次调用，约 17 秒。

    HOST --buffer-script rom-checksum --version firered
    HOST --buffer-script rom-checksum --sum-start 0x08120000 --sum-end 0x08140000 \
        --sum-block 0x400 --version firered

主机会记录每块的范围、两个和，以及 `SAME` 或 `DIFF`，最后是 `rom-checksum: N of M blocks differ from <image>`。映像是 `config.REFERENCE_ROMS[game code]`，或用 `--sum-reference` 指定任意构建。超出映像的块会列出但不计数。

### `rng-trace`

每帧采一个字，并在每次采样的两次读取之间调用一个 ROM 函数（`--trace-call 0` 就是单纯采样）。

    HOST --buffer-script rng-trace --trace-address 0x03004220 --trace-call 0x080486B1 \
        --trace-samples 96 --version firered

调用形如 `mov lr, pc; bx r2`：pc 读作 `bx` 之后那条指令，第 0 位清零，于是被调者返回到 ARM 状态。零售版火红上，`Random` 跟踪的每个采样都遵循 LCG（实测的 96 个里有 96 个）。结果见 [RNG](frlg_rng.md)。

### `string-gather`

给定第一个指针的地址、一个步长与一个计数，把每个被指向的字符串（含 0xFF 终止符）复制进同一份应答，并报告下一轮从哪里继续。

    HOST --buffer-script string-gather --gather-address 0x083E0D54 --gather-count 69 \
        --gather-stride 12 --version firered

`--gather-stride` 对 `struct EasyChatWordInfo`（`text` 在 0）是 12，对 `const u8 *` 数组是 4。应答是 776 字节：四个头部字，最多 760 字节字符串。它从不截断：装不下的字符串会结束本轮，`next` 点名它。`--gather-maxlen`（默认 64）限制不是字符串的指针。

### `create-mon`

```c
void CreateMon(struct Pokemon *mon, u16 species, u8 level, u8 fixedIV,
               u8 hasFixedPersonality, u32 fixedPersonality, u8 otIdType, u32 fixedOtId)
```

四个参数在 `r0..r3`，四个在栈上。`asm/create-mon.s` 沿用主机自己的序言：

    08041150  push {r4,r5,r6,r7,lr}    ; sp -= 20
    08041152  mov  r7, r8
    08041154  push {r7}                ; sp -= 4
    08041156  sub  sp, #28             ; sp -= 28, so entry sp is now sp + 52
    0804115c  ldr  r4, [sp, #52]       -> entry sp +  0   hasFixedPersonality  (masked to u8)
    0804115e  ldr  r7, [sp, #56]       -> entry sp +  4   fixedPersonality     (NOT masked: u32)
    08041160  ldr  r5, [sp, #60]       -> entry sp +  8   otIdType             (masked to u8)
    08041184  ldr  r0, [sp, #64]       -> entry sp + 12   fixedOtId            (u32)

这四个按整字放在 `sp+0..sp+12`，载荷自己弹出。宝可梦建在载荷的映像里，代码之前有 32 字节填充；`--create-mon-destination ADDR` 把它复制出去，需要 `--write-unsafe`。

    HOST --buffer-script create-mon \
        --create-mon-species 151 --create-mon-level 30 --create-mon-iv 31 \
        --create-mon-personality 0x3ADE0000 --version firered

`--create-mon-call` 默认是 `rom_map.py` 里的 `CreateMon | 1`；`0` 表示不调用，答以清零的缓冲区。应答是 116 字节（四个头部字加 100 字节的 `struct Pokemon`），`*param` 是个性值。

各子结构用 `personality ^ otId` 加密并带校验和，所以校验和有效就证明这两个字。`check_create_mon` 检查物种、等级与个体值；`scratchpad/verify_create_mon.py` 预测十三个派生字段：经验值来自 `gExperienceTables[growthRate][level]`，亲密度与特性槽来自 `gSpeciesInfo`，招式与 PP 来自学习表，六项能力来自 `CalculateMonStats`。昵称来自 `gSpeciesNames` [pokemon.c:1810]，即卡带上的法语表，是读出来的，从不预测。三个字段度量主机：

| 字段 | 值 | 说明 |
| --- | --- | --- |
| `language` | 3 | `gGameLanguage` 是 LANGUAGE_FRENCH [global.h:22] |
| `metGame` | 4 | `gGameVersion` 是 VERSION_FIRE_RED [global.h:11] |
| `metLocation` | 91 | `GetCurrentRegionMapSectionId()` [overworld.c:1265]，即玩家当时所在处 |

`buffer_script.shiny_personality(tid, sid)` 给出闪光的 `fixedPersonality`。`CreateMon` 的离线桩：`CREATE_MON_ARG_MODEL` 把八个参数写进目标，`create_mon_copy_model(source)` 复制 100 个预备字节。

#### `--create-mon-append`

它写 `gPlayerParty`，不是存档块里的队伍：

```c
void SavePlayerParty(void)
{
    gSaveBlock1Ptr->playerPartyCount = gPlayerPartyCount;
    for (i = 0; i < PARTY_SIZE; i++)
        gSaveBlock1Ptr->playerParty[i] = gPlayerParty[i];
}
```

往存档块里追加会报成功，并在下次保存时丢失 [load_save.c:160,196]。它在 `slot == playerPartyCount` 处写入并提高计数，与捕获一样；已占用的槽绝不碰，队伍满时什么都不写。应答的第五个字报告 `countBefore | slot << 8 | status << 16`（0 未询问、1 已追加、2 队伍满、3 试运行）。带绝对 `--create-mon-destination` 的追加，或带 `--create-mon-call 0` 的追加，会被拒绝。

    # dry run first: the same code with the two stores left out
    HOST --buffer-script create-mon --create-mon-append-dry-run \
        --create-mon-species 59 --create-mon-level 30 --version firered
    HOST --buffer-script create-mon --create-mon-append \
        --write-unsafe --create-mon-species 59 --create-mon-level 30 --version firered

试运行报告计数、目标地址与该槽当前那 100 字节，能抓出与队伍不符的 `playerPartyCount`。空槽不是全零：`ZeroMonData` 以 `SetMonData(mon, MON_DATA_MAIL, &MAIL_NONE)` 结尾 [pokemon.c:1737]，所以偏移 0x55 是 `0xFF`（`buffer_script.EMPTY_PARTY_SLOT`、`is_empty_party_slot`）。

| | 会移动吗？ | 所以 |
| --- | --- | --- |
| `gSaveBlock1Ptr` | 会，一个随机 4 对齐偏移，每场战斗与每次读取都重掷 [`SetSaveBlocksPointers`, load_save.c:75] | 每次调用都从 `r1`/`r2` 取 |
| `gPlayerParty` | 不会，是链接期 EWRAM 全局量 | 地址是合法的 |

`gPlayerParty` 是 0x02024280，`gPlayerPartyCount` 是 0x02024025：EWRAM 转储里唯一一个 4 对齐窗口，能解码成带校验和的 `struct Pokemon`。

### `call`

一个地址、最多八个参数字、返回的 `r0`，以及调用前后各读一个地址。

    HOST --buffer-script call \
        --call-address 0x080486D1 --call-arg 0xC0DE --call-watch 0x03004220 --version firered

    0x000  b .Lcode
    0x004  function    THUMB pointer (bit 0 set), or 0 to call nothing
    0x008  argc        how many of the eight words below are meant
    0x00C  args[0..7]  r0, r1, r2, r3, then [sp+0], [sp+4], [sp+8], [sp+12]
    0x02C  watch       a word to read before and after the call, or 0
    0x030  result      calls used, function, argc, r0, *watch before, *watch after

`asm/call.s` 总是压入那十六个栈字节；被调者从不弹出。`SeedRng` 不返回东西（`gRngValue = seed` [random.c:15]），所以 watch 字就是证据。只调用已经读作代码的地址。`tests/test_buffer_script.py` 在 unicorn 下把主机自己的 `SeedRng` 字节跑过载荷，并用 2 的幂测八参数路径。

### `flash-write`

在 EWRAM 里拼出一个 4 KB 扇区，用 [`swi 0x48`](#the-flash-sector-path) 写进 flash，而不走游戏的存档代码。临时区是 `gDecompressionBuffer + 0x400`，比载荷自己的映像高 0x400。

    --flash-sector N            the sector, 0..31; 0..27 are the save bands and need --write-unsafe
    --flash-fill-base WORD      word[i] = base + i * step, the data pattern
    --flash-footer              compose a well-formed sector instead of a raw pattern
    --flash-id N                the sector id at +0xFF4
    --flash-derive              read the save globals and place it where that id actually lives
    --flash-position N          aim at band position N and derive the id from it instead
    --flash-counter-bias N      added to gSaveCounter for the footer

`--flash-footer` 像游戏那样从图案末尾清零到 `+0xFF4`，算出游戏的校验和，并铺下 id、校验和、签名与计数器。状态字是物理扇区（高半）与校验和（低半）。`--flash-derive` 在写入时读 `gLastWrittenSector` 与 `gSaveCounter`：两者每次保存都前进，而以成功消息结束的礼物会话会保存 [mystery_gift_menu.c:1379]。

### `sloop-svc`

一次会话最多八个 Sloop 系统调用，操作数由主机选择，经结果块作答。

    IP_HOST --buffer-script sloop-svc --svc-number 0x4d --svc-text "hello fuck" \
        --svc-data-in r0 --version firered

    0x000  b .Lcode
    0x004  flags       bit 0: r0 = &copy, bit 1: r1 = &copy
    0x008  r0..r3
    0x018  scratch     gDecompressionBuffer + 0x400
    0x01C  length      of the data, at most 256
    0x020  thunk       swi N ; bx lr (THUMB), or bkpt N ; bx lr with --svc-bkpt
    0x024  count       1..8
    0x028  numbers     eight bytes, one per call
    0x030  data

每次调用前，载荷重新复制数据，并把编号写进 thunk 的低字节。结果块：标记 `0x53565331`、计数、标记 `0x53565332`、长度、八个 20 字节记录（thunk 字、之后的 `r0..r3`），以及最后一次调用留下时的数据。只读值的编号（0x46、0x49..0x4B、0x4D、0x4E、0x50..0x54、0x58..0x60）原样放行；0x48、0x56、0x4C 与 0x55 被拒绝；其余的以及 `--svc-bkpt` 需要 `--write-unsafe`；`--svc-bkpt` 拒绝 `#0x52`。

### `install-resident`

把常驻 THUMB 钩子复制到 `0x0203FC00`，并在一次会话里装进 `gIntrTable[4]`。它每帧运行，穿过 CONTINUER 与野外，直到软复位。

    IP_HOST --buffer-script install-resident --resident turbo \
        --resident-param extra=4 --resident-param field=1 --resident-param battle=1 \
        --resident-param overlay=0x03004220 --resident-param hold=0x100 \
        --resident-param budget=228 --write-unsafe --version firered

    0x000  b .Lcode
    0x004  dest          0x0203FC00
    0x008  length        of the hook, whole words
    0x00C  table         &gIntrTable[4], 0x03002730
    0x010  entry_off     the hook's entry inside it
    0x014  original_off  its p_original word
    0x018  blob_off      where the hook starts in this image, after the installer's code

THUMB 安装器是 148 字节，给钩子留 876 字节，钩子的数据（`p_frames`、`p_ring`、`p_state`）不得与代码重叠，也不得越过 `0x02040000`。复制与写表期间会清 `REG_IME`。第一次安装把被替换的处理函数留在 `0x0203FBFC`；之后的安装链到那个字，它为空时以 `0xBAD0BAD0` 拒绝。应答是找到的处理函数：干净安装上是 `0x0800071D`。同一时间只有一个钩子常驻；它们共用 `0x0203FC00` 处的 1 KB。

#### `turbo`

`asm/resident/turbo.s` 先跑 `VBlankIntr`，然后在空闲帧里把野外回调多跑 `field` 次、战斗的多跑 `battle` 次，并把 `RunTextPrinters`（`0x08002D51`）多跑 `extra` 次。只有 `callback1`/`callback2` 恰好是 `CB1_Overworld`（`0x08059E49`）/`CB2_Overworld`（`0x08059EC9`）或 `BattleMainCB1`（`0x08015B6D`，由战斗初始化在 `0x08013FDE` 存下）/`BattleMainCB2`（`0x08014889`）时才跑一轮，两次调用之间会重新检查。先清 `newKeys` 与 `newAndRepeatedKeys`，使一次按键只被处理一次。

`gPaletteFade.active`（`0x02037AB4`）置位时不跑任何一轮：硬件淡出在 `UpdatePaletteFade` 置上一位的 `hardwareFadeFinishing`、下一个 V-blank 看到它时结束 [palette.c:701, 743]；一帧内第二次更新会把该位翻回 0，于是 `CompleteWhenChoseItem` 在战斗里合上背包后永远等下去。另有两道门：

- `gMain.intrCheck`（`0x030022EC`）第 0 位清零，在 `VBlankIntr` 之前读：主循环停在 `WaitForVBlank` [main.c:462]。置位说明是掉帧，放过。
- `sTextPrinters`（`0x02020034`，32 个 0x24 字节）里没有在其原位的活动打印器（`currentX == x`、`currentY == y`）：野外消息在框画出来之前就加进打印器 [field_message_box.c:44]，在框画出之前跑一轮会把字打进框随后清掉的窗口。

实测（模拟器上）：每秒 60 帧、97% 空闲、文本每帧五个字形；`field=1` 让野外快一倍，`battle=1` 让战斗及其菜单快一倍。

`hold=MASK` 只在 `gMain.heldKeys`（`gMain + 0x2C`）按住掩码里的每个键时才跑回调那几轮；文本的额外次数照跑。用 `hold=0x100`（R）时，钩子每帧往 `gHelpSystemToggleWithRButtonDisabled`（`0x0203F171`，字面量在 `RunHelpSystemCallback` 的 `0x0813F6FC`，函数在 `0x0813F65C`）写 1，于是 R 不再打开帮助系统 [help_system_util.c:50]；L 仍然可以。

`budget=LINES` 按时间限制轮数。Switch 模拟器在一帧的代码运行时推进 `REG_VCOUNT`（0 到 227，V-blank 从 160 起）；只有自 V-blank 以来的行数加上上一轮开销的两倍能塞进 `LINES` 时才开一轮。上一轮开销在计数器 `+0x0C`，被拦下的轮次计在 `+0x10`；每拦一次就把保留的开销缩小八分之一。

实测（模拟器上）：

| 设置，按住 R | 每帧额外轮数 | 备注 |
|---|---|---|
| `field=2 battle=2` | 2 里 1.70 到 1.90 | 约 2.9 倍，无可见掉帧 |
| `field=3 battle=3` | 3 里最多 2.38 | 约四分之一的帧掉帧；可见卡顿 |
| `field=3 battle=3 budget=228` | 最多 2.48 | 流畅；走路一轮 36 到 42 行，战斗 100 到 108 行 |

`overlay=ADDRESS` 把 `ADDRESS` 处的字以八个十六进制位画在野外的右上角（`0x03004220` 是 `gRngValue`）。这些项写进 `gMain.oamBuffer[120..127]`（`0x030026C8`），两种颜色写进 `gPlttBufferFaded`（`0x020375F4`）与 `gPlttBufferUnfaded`（`0x020371F4`）的 OBJ 调色板 15，都在 `VBlankIntr` 的 `LoadOam` 与 `TransferPlttBuffer` 之前（之后的话，最上面几行会晚一帧）。一套 128 字节的 1bpp 字体（十六个 3x5 数字，像素在第 1 到 5 行的第 2 到 4 列，`asm/resident/overlay.inc`）在两个哨兵字不同时展开到 OBJ 图块 1008 到 1023。覆盖层会盖掉游戏在调色板 15 与那些图块里放的东西。

`ring=ADDRESS`（140 字节；`0x0203FF74` 到 EWRAM 顶端结束）按 `VBlankIntr` 看到的样子保存 `gRngValue`，每帧一个字、共 32 帧，`watch`（`gEnemyParty[0]` 的个性值，`0x02024028`）变化时冻结。草丛遇敌的个性值由保留的每个种子推出。实测（模拟器上在草丛里走动）：每帧两次 `Random` 调用，从前一帧的种子数起，性格抽取是第五次调用（`VBlankIntr` 的 [main.c:412]、本帧自己的、slot、等级、性格）。

#### `shiny`、`shiny-press`、`ivs`、`noencounter`

`shiny`（`asm/resident/shiny.s`）倒计数到下一次闪光野生个体的抽取。`VBlankIntr` 每帧调用一次 `Random` [main.c:412]；野生宝可梦先以 `Random() % 25` 抽性格，再反复抽 `Random() | Random() << 16` 直到性格相符 [wild_encounter.c:233, pokemon.c:1864]；`method=1` 取第一对（脚本化的 `CreateMon`）。闪光的判据是 `TID ^ SID ^ high ^ low < 8`，TID 与 SID 取自 `gSaveBlock2Ptr`（`0x0300422C`）的 `+0x0A`。钩子逐帧跟随 `gRngValue`（最多 64 步，否则重启），每个空闲帧搜索 `search` 个候选，并以十进制显示目标的性格与 `target - current - offset`（`offset=4`，草丛的情形），或显示 `FF` 与搜索距离。按住 `slow`（R）时它每帧多等 `slow_frames` 个 V-blank：`IntrMain` 在处理函数里让 VCount 保持使能 [crt0.s]，所以 `m4aSoundVSync` 会跑，钩子每等一个 V-blank 就调用 `m4aSoundMain`（`0x081DF53D`，`gPcmDmaCounter` `0x03002F68` 来自 `gSoundInfo` `0x03005F80`），并在 `REG_IF` 里清掉它。状态是 `0x0203FF80` 处的 36 字节。

`shiny-press`（`asm/resident/shiny-press.s`，872 字节）是同一份源码加上 `SHINY_PRESS` 汇编出来的：没有慢动作、`method=1`，A 由钩子按下。在倒计数为 0 的空闲帧上，若 `callback1`/`callback2` 是 `CB1_Overworld`/`CB2_Overworld`，且 `sGlobalScriptContext`（十二张卡带上都是 `0x03000FB0`，`ScriptContext_SetupScript` 的第一个字面量）处于模式 2、`nativePtr` 是 `WaitForAorBPress`（`ScrCmd_waitbuttonpress` 的字面量，`gScriptCmdTable[0x6D]`；法语是 `0x0806F159`），或在按住 B 时没跑脚本（模式 0），它就把一个垫片（用 `adr` 找到）写进 `callback1`。下一轮主循环先跑 `ReadKeys` [main.c:81]；垫片把 `CB1_Overworld` 放回去，把 A 或进 `gMain.newKeys` 并调用它。等待中的脚本会立刻返回 [scrcmd.c:1313]；没有脚本时，A 对玩家面前的东西说话。等待时按住 B 不算新按键，站着不动什么也不做。

| 宝可梦 | 造出它的那次按键 | `offset` mGBA | `offset` 零售版 Switch |
|---|---|---|---|
| 超梦 | 它的 `waitbuttonpress`；`setwildbattle` 紧随其后 [CeruleanCave_B1F/scripts.inc:37] | 1 | 3 |
| 急冻鸟、闪电鸟、火焰鸟 | 那次对话：`lock`、`faceplayer`、`setwildbattle`，然后是等待 | 2 | 5 |

在 Switch 2 上的零售版英文火红里，超梦叫声处 `offset=1` 按一次，得到的个性值是 `0x9C9D9DC5`，比目标闪光值晚两次调用抽出；`offset=2` 得到非闪光的超梦，`offset=3` 得到闪光的。面对闪电鸟，对话那次按键用 `offset=4` 得到 `0xC2C9758B`，比目标闪光值晚一次调用，`offset=5` 得到闪光的闪电鸟（`tests/test_shiny.py`）。应用发送的是 3 与 5。

Switch 的模拟器每个 V-blank 调用两次 `Random`，而 mGBA 只调用一次：在模拟主机上站在华蓝洞窟 B1F，法语火红，600 个 V-blank 里 1200 次调用，每个 V-blank 的 `intrCheck` 第 0 位都清零。每帧两次调用时，奇数倒计数会从 1 跳到 -1，永远按不下；在零售主机上，这让闪电鸟的对话按键在三次倒计数里丢了两次。钩子在状态 `+32` 处保留上一帧的 `64 - calls`。当它是 62 且被追踪目标的倒计数为奇数时，钩子自己花掉一次 `Random` 调用（`gRngValue` 与所跟随的种子都前进一步），于是它显示的每个倒计数都能走到 0。用这个钩子加 `offset=3`，模拟主机在超梦叫声处的第一个倒计数上就给出了闪光超梦（`0xA893924D`）。

有野生宝可梦的地图每 1200 到 3600 帧播放一次环境叫声；叫声花 2 次调用，除非叫声来自水属性宝可梦而玩家不在水上，下一帧再花 1 次决定下一个间隔 [overworld.c:1131-1172]。在 mGBA 里用法语火红站在双子岛急冻鸟面前，3599 帧里只有一帧是 2 次调用，其余都是 1 次。多出来的那次奇偶调用会让每帧两次调用下的倒计数变成奇数；花掉的那次调用把它抵消回来，mGBA 于是就在倒计数期间的一次叫声里按出了闪光急冻鸟（`0xFF0AFD1B`，offset 2）。

在 mGBA 里，CONTINUE 之后的回顾画面会让玩家对象朝南（`gObjectEvents[0]` 的 `+0x18` = `0x11`，法语与英文火红上都是 `0x02036E34`），回顾期间按的方向不会被接受；钩子发出的 A 于是只进了 `gMain.newKeys`，对着空气说话。回顾之后按一帧上，就把方向设为 `0x22`（北），下一次按键就说得上话。应用让玩家去和超梦对话；在叫声处不需要按任何键。野生战斗之后，钩子保留倒计数，但在叫声处不按任何东西，直到它被重新下发。

`offset` 数的是从按键那一帧钩子的种子到个性值之前那次调用的调用数，在 mGBA 上用法语火红测得（A 按一帧，每种三次，`tests/test_shiny.py`），并在玩家按住 B 时用应用的载荷端到端跑过：在闪电鸟处 offset 从 0 到 8，只有一个取 2 时是闪光。用表里的偏移，应用的载荷在七张卡带上都给出了四个闪光：法语、英语、西班牙语、德语火红，法语、英语、意大利语叶绿。日语未试。

`ivs`（`asm/resident/ivs.s`）分两行显示队首的个体值（`OVERLAY_TWO_ROWS`，第二行在 `gMain.oamBuffer[112..117]`，y 为 10）：HP、攻击、防御、速度，然后是特攻、特防与 `personality % 25`。`GetMonData(mon, MON_DATA_IVS)`（66，`0x080432E5`）返回六个五位个体值，HP 最低 [pokemon.c:3250]；`GetBoxMonData` 就地解密再加密 [pokemon.c:2992, 3327]，所以只在野外空闲帧调用它。

`noencounter`（`asm/resident/noencounter.s`）每帧往 `sWildEncountersDisabled`（`0x020386D8`）写 1，`StandardWildEncounter`（`0x08086528`）最先检查它 [wild_encounter.c:360]；`DisableWildEncounters`（`0x08085FAC`）是它唯一的另一个写入者。草丛、水面与游荡宝可梦的遇敌都会停；钓鱼与甜香走各自的路径。

#### `noclip`

`noclip`（`asm/resident/noclip.s`，304 字节）在按住 `hold`（默认 `0x100`，R）里的每个键时让玩家穿墙。在每个野外空闲帧（`gMain.intrCheck` 第 0 位清零、`callback2` 为 `CB2_Overworld`），它把地图网格 `VMap.map`（`gBackupMapData`，`0x02031DF8`）里玩家 `currentCoords` 周围的四个块改写为碰撞 0、海拔 15，并保留 metatile id。`VMap` 是 `0x03004260`（法语）或 `0x03004310`（英语）处的 `{s32 Xsize, s32 Ysize, u16 *map}`，也就是 `MapGridGetCollisionAt` 里的那个字面量。一个块是 `metatile | collision << 10 | elevation << 12` [global.fieldmap.h:7]；`GetCollisionAtCoords` 先按碰撞位拦，再按 `IsElevationMismatchAt` 拦，而海拔 15 能过，`ObjectEventUpdateElevation` 在 15 的图块上不改变玩家自己的海拔 [event_object_movement.c:4830, 8346, 8400]。

下一个空闲帧会把每个块放回去，但只在 `gMapHeader.mapLayout`（`0x02036DF8`）仍是它改过的那个布局、且该块仍是它的 metatile id 加海拔 15、碰撞 0 时才放：传送或游戏自己改写过的 metatile 会保留新块。等于 `MAPGRID_UNDEFINED`（`0x3FF`）的块保持不动，否则玩家会走出地图。对象事件仍然会挡（`DoesObjectCollideWithObjectAt`），台阶仍然会跳，玩家旁边的游荡对象事件也可能踏上被打开的块。按住 R 会打开帮助系统，所以钩子每帧往 `0x0203F171` 写 1（见 `turbo`）。状态是 `0x0203FF80` 处的 24 字节：布局、一个计数与四个 `{u16 index, u16 block}`。

`tests/test_noclip.py` 用每张卡带自己的客户端安装它，并用卡带自己的 `MapGridGetCollisionAt` 与 `MapGridGetElevationAt` 读结果。在 mGBA 上用法语卡带在真新镇实测：向南走，不按 R 玩家会停在栅栏前，按住 R 能穿过六个图块；对象事件仍然会挡住它。

#### `follower`

`asm/resident/follower.s` 把队首宝可梦作为一个真正的对象事件跟在玩家身后一格，用游戏自己的移动动作驱动，于是步、跑、跳台阶（弧线、影子、落地尘土）、门淡出与精灵优先级都由游戏画出。设计沿用 GB-Link 的 `cards/follow.s`（GPL-3.0）。它有 984 字节，超过一次 `install-resident` 会话，所以从存档里安装（[常驻钩子留在存档里](#a-resident-hook-kept-in-the-save)）。

在每个野外空闲帧（`gMain.intrCheck` 第 0 位清零、`callback2` 为 `CB2_Overworld`），在 `VBlankIntr` 之后：

| 步骤 | 钩子做什么 |
| --- | --- |
| 找到它 | 局部 id `0xF0` 的活动对象事件，没有地图用这个局部 id；地图加载后不存在 |
| 生成 | 在玩家脚下调 `SpawnSpecialObjectEventParameterized(gfx, MOVEMENT_TYPE_NONE, 0xF0, x, y, elevation)`，隐藏到玩家走出第一步 |
| 每帧 | 把它的当前海拔设为 14，没有任何图块是这个海拔：玩家能走回去，也没有东西和它对话 [event_object_movement.c:4899]；野外被锁时置 `fixedPriority`，让存档保留那个海拔 |
| 玩家走一步 | 玩家离开的那格成为它的目标；隔一格时它拿到玩家自己的动作族（跑会变成 `WALK_FAST`），不在一条线上就用 `MoveObjectEventToMapCoords` 直接移过去 |
| 台阶 | 玩家的 `JUMP_2` 会把它的坐标移两次：第一次把跟随者带到边缘，第二次把它留在那里；玩家下一步时它自己做 `JUMP_2`，两格；一条线上两格且没有待处理的台阶时，它用 `WALK_FASTER`（0x35）每次一格地跟上 |
| 菜单 | `sGlobalScriptContextStatus`（`0x03000FA8`）为 `CONTEXT_SHUTDOWN` 时置 `sLockFieldControls`（`0x0300109C`）：`RemoveObjectEvent`，于是存档绝不会带着它；之后会重新生成 |
| 自行车、冲浪、潜水 | 隐藏在玩家脚下 |
| 换队首 | 移除并重新生成 |
| 撞上 | 玩家在海拔 0 的图块上撞到它时，它被放到玩家脚下 |

| 队首 | 对象 |
| --- | --- |
| 42 个有野外精灵的物种之一（`OBJ_EVENT_GFX_SNORLAX` 109 到 `DEOXYS_N`；代欧奇希斯用它所在版本的形态，构造器的 `deoxys=`） | 它自己的图形 id |
| 其他任何物种、蛋、按字母区分的未知图腾 | 卡比兽的 32x32 帧（109，`sAnimTable_Standard`）；它精灵的 `images` 指向 `0x0203FBB4` 处的九个 `SpriteFrameImage`（站立 0..2：图标帧 0，走路 3..8：帧 1，每个 0x200 字节，来自 `GetMonIconPtr`），用 OBJ 调色板 15 |

图标的调色板每空闲帧写进 `gPlttBufferUnfaded` 的 OBJ 调色板 15（`0x020375D4`），只在混合的 `y`（`gPaletteFade + 4`，第 6..10 位）为 0 时才写进 `gPlttBufferFaded`（`0x020379D4`）。门的淡出会把 `BeginNormalPaletteFade` 跑到 `y` 16，然后在屏幕仍黑时清掉 `active` [field_weather.c:740, palette.c]；在 mGBA 上走进门实测，`active` 保持 21 帧，然后 `y` 为 16、`active` 清零持续四帧，之后 `callback2` 离开野外。

在野外按 A，且玩家面前的图块是跟随者、野外又没被锁时（游戏自己的 A、脚本或菜单会先占这一帧）：把 `gSelectedObjectEvent` 设成它，跑 `ScriptContext_SetupScript`，并把物种写进去（`SPECIES_EGG` 即 412 不写，它没有叫声）：

    6A                lock
    A1 SPEC 0000      playmoncry SPECIES, CRY_MODE_NORMAL
    5A                faceplayer
    4F F000 PTR       applymovement 0xF0: 66 FE (MOVEMENT_ACTION_EMOTE_SMILE, step_end)
    51 0000           waitmovement 0
    C5                waitmoncry
    7F 00 0000        bufferpartymonnick STR_VAR_1, 0
    67 PTR            message: "{STR_VAR_1} saute\nde joie !" (French), "{STR_VAR_1} jumps\nfor joy!" (English)
    66 6D 6C 02       waitmessage, waitbuttonpress, release, end

状态是 `0x0203FFDC` 处的 17 字节（`state=`）：`+0` 它的对象事件或 `0xFF`，`+1` 有待走的步，`+2` 正在显示图标，`+3` 动作族，`+4` 上次看到的玩家坐标，`+8` 它的目标，`+12` 队首的物种，`+14` 它被生成时对应的物种，`+16` 有待处理的台阶。图标的帧表是 `0x0203FBB4` 处的 72 字节（`images=`），在安装器保留于 `0x0203FBFC` 的处理函数之下。

| 卡带 | `SpawnSpecialObjectEventParameterized` | `ObjectEventSetHeldMovement` | `ObjectEventClearHeldMovement` | `MoveObjectEventToMapCoords` | `RemoveObjectEvent` | `ScriptContext_SetupScript` | `gSelectedObjectEvent` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BPRF, BPGF | `0x08062130` | `0x080675A4` | `0x08067634` | `0x08063024` | `0x08061DB4` | `0x0806D3D4` | `0x03004294` |
| BPRE, BPGE | `0x08061FD4` | `0x08067448` | `0x080674D8` | `0x08062EC8` | `0x08061C58` | `0x0806D270` | `0x03004344` |

| 卡带 | `gMonIconPaletteIndices` | `gMonIconPalettes` | `GetMonIconPtr` |
| --- | --- | --- | --- |
| BPRF | `0x083CBEE8` | `0x083CB7A8` | `0x0809AA74` |
| BPGF | `0x083CBD24` | `0x083CB5E4` | `0x0809AA48` |
| BPRE | `0x083D197C` | `0x083D123C` | `0x0809A7B8` |
| BPGE | `0x083D17B8` | `0x083D1078` | `0x0809A78C` |

英语的值来自 `pokefirered_switch.elf`；法语的值是在各个映像里找到的同样字节。`tests/test_follower.py` 按 `install-kept` 安装的方式在各个映像上跑这个钩子，对象函数用桩替代：生成、走路、图标帧与调色板、台阶等待与单次跳、对话脚本、菜单下的移除。

`AddSpritesToOamBuffer` 只用 `gDummyOamData` 填到 `gOamLimit` 为止的未用 OAM 项 [sprite.c:487]，`ResetSpriteData` 把它设为 64 [sprite.c:297]，野外读出来也是 64（`0x02021B44`）：钩子写进 64 以上的项会一直留在屏幕上，直到某个画面重置自己的精灵。

#### 已验证

| 钩子 | 零售版法语火红，ESP32 无线电（每次安装都答 `0x0800071D`） | 模拟器 |
| --- | --- | --- |
| `turbo` `extra=4 field=3 battle=3 hold=0x100 budget=228` | 按住 R 能快进 | |
| `overlay` | 画出八个数字，每帧变化 | 在 CONTINUE 之后的回顾画面里也画 |
| `shiny` | 在草丛里倒计数；R 让它变慢 | 跟随的种子与 `gRngValue` 相符；Python 模型对闪光的判断一致 |
| `ivs` | 队首的个体值字与 `personality % 25` 与 `SaveBlock1 + 0x34` 的 `save-dump` 相符 | 与 `gPlayerParty`（`0x02024280`）相符 |
| `noencounter` | 在草丛里走时没有野生遇敌 | 无；软复位后遇敌恢复 |
| `turbo-lite+noclip+noencounter`，`turbo-lite.field=2 battle=2 hold=0x2`，`noclip.hold=0x100` | 一次会话答 `0x0800071D`；按住 B 快进、按住 R 穿墙、草丛无遇敌，两个键一起按则快速穿墙 | |
| `follower` | 跟在一格之后，在台阶边缘等待，玩家离开落点那一格后跳上去，带游戏的影子与尘土；跑动与跑着越过台阶都不闪；面对它按 A：叫声、微笑、台词；开始菜单与门；一次会话把它写进存档并安装 | 在 mGBA 上相同，用吉利蛋的精灵与水箭龟的图标 |

未解决：在模拟器上，覆盖层在 CONTINUE 之后的回顾画面里画出来了，但在可操作游玩中没画，而 `field` 仍能让游戏加速。

每个钩子在叶绿上只需改一个地址就能跑：`m4aSoundMain` 是 `0x081DF518`（它在 `VBlankIntr` 里的 `bl` 在 `0x08000772`）；其余常量都通过火红自己的引用同样映射。`follower` 还读 ROM 表与会移动的函数，都在它那一节里列出。构造器接受 `version=`，主机用 `--version leafgreen`。在模拟的叶绿上验证过：turbo 与 `shiny`，音乐完好。

### 同时装多个钩子

每个钩子都把它替换掉的处理函数当作函数调用（`bl` 到 `p_original` 上的 `bx r3`），并通过自己压入的 `lr` 返回，所以一个钩子的 `p_original` 可以指向另一个钩子。`--resident turbo-lite+noclip+noencounter` 把这些钩子从 `0x0203FC00` 起首尾相接排好，把每个钩子的 `p_original` 写成下一个的入口（Thumb 位置位），并交给安装器一个 blob，其入口是第一个钩子的、`p_original` 是最后一个的。`install-resident`、`install-kept` 与 MOM 的加载器都不变。某个设置用名字指定它的钩子：`--resident-param turbo-lite.hold=2`。

| 规则 | 原因 |
|---|---|
| 顺序为 turbo、noclip、shiny、ivs、noencounter | turbo 的回调轮次在其他钩子用完这一帧之后才跑 |
| 每个钩子的数据先放在 `0x0203FBB4..0x0203FBFC`，再放到代码之上 | 默认值会重叠：`shiny`、`ivs` 与 `noclip` 都把状态放在 `0x0203FF80` |
| `shiny`、`ivs` 与 turbo 的 `overlay` 最多只能有一个 | 它们都画在 `gMain.oamBuffer[120..127]` 与 OBJ 调色板 15 |
| `follower` 单独运行 | 984 字节：配上任何其他钩子就超过存档能放的 1004 |
| 代码要装进 `0x0203FC00..0x02040000` | 1024 字节；超过 876 就得走存档，超过 1004 无处可放 |

`turbo-lite`（`asm/resident/turbo-lite.s`）是设了 `TURBO_LITE` 的 `turbo.s`：同样的轮次、门、hold 与 budget，没有覆盖层也没有 RNG 历史，356 字节对 696 字节。每个 turbo 帧测试都在它上面跑（`tests/test_turbo_lite.py`）；穿过一条链的一帧会把每个钩子与 `VBlankIntr` 各跑一次（`tests/test_resident_chain.py`）。

### `install-kept`

`asm/install-kept.s`，192 字节，把存在 `filler_B20` 里的钩子按 `install-resident` 装自己那一套的方式装起来：它读 `gSaveBlock2Ptr`（块每次读取都会移动），检查魔数、长度（要保证校验和仍在 `filler_B20` 内）与和，然后清 `REG_IME`，把游戏的处理函数留在 `0x0203FBFC`，复制钩子，写它的 `p_original`，并把 `gIntrTable[4]` 指向它。应答是表里找到的处理函数，什么都没装时是 `0xBAD0BAD0`。`+0` 处的 ARM 入口是缓冲区脚本的；MOM 的 RAM 脚本跑 `+8` 处的 THUMB 入口，把应答指向映像里的一个字。最后两个字按卡带打补丁：`&gSaveBlock2Ptr` 与 `&gIntrTable[4]`。

    IP_HOST --buffer-script install-kept --version firered

### 常驻钩子留在存档里

任何常驻钩子都能住在 `filler_B20` 里，并在启动后通过与 MOM 对话重新安装，不需要链路，也不需要主机。两次礼物会话就能建好：

    IP_HOST --buffer-script save-write --resident follower --version firered
    IP_HOST --gift resident-save --version firered

第一次把这段 blob 写到 `SaveBlock2 + 0xB20`，并在同一次会话里从它安装钩子：

    +0x00  magic     0x32524B50, "PKR2"
    +0x04  length    the hook's bytes, whole words
    +0x08  dest      0x0203FC00
    +0x0C  entry     u16 offset of the hook's entry
    +0x0E  original  u16 offset of its p_original word
    +0x10  the hook
    +len   checksum  the sum of every word before it

超过一次 `save-write`（936 字节）的 blob 由两次写入完成。会话依次跑每次写入，然后是 [`install-kept`](#install-kept)，各自是一条载荷：客户端按命令表依次接收并运行缓冲区脚本 [mystery_gift_client.c:145, 236]，只有最后的应答回传。

    client  RECV RUN  RECV RUN  RECV RUN LOAD_TOSS_RESPONSE SEND_LOADED  RECV COPY_RECV
    host    script    write 1   write 2  install-kept   <- the handler found

会话以 `CLI_MSG_BUFFER_SUCCESS` 结束，它会保存，于是 `filler_B20` 落到 flash。

第二次把一个 RAM 脚本绑到 MOM 上，该脚本布置 36 字节的 [RAM 跳板](#a-payload-larger-than-a-script-body) 并跳进 `install-kept` 的 THUMB 入口，后者逐字节带着（995 字节里的 428 字节）。和 MOM 对话就安装钩子；第二次拜访会链到已保留的处理函数，软复位会移除钩子，直到再和 MOM 对话。

| 钩子 | blob | `save-write` 载荷数 |
| --- | --- | --- |
| `noencounter` | 48 | 1 |
| `ivs` | 520 | 1 |
| `turbo-lite` | 376 | 1 |
| `turbo` | 716 | 1 |
| `shiny` | 888 | 1 |
| `follower` | 1004 | 2 |

`tests/test_resident_save.py` 在主机与模拟客户端之间跑完整个会话，并在启动过的主机上跑 MOM 的 body 脚本：翻一个字节、少一次写入、长度超过 `filler_B20`，都装不上任何东西。一台零售版火红从它的 `PKR2` blob 装上了跟随者。

新的神秘卡片会撤销绑定：`SaveWonderCard` 调用 `ClearSavedWonderCardAndRelated`，后者调用 `ClearRamScript` [mystery_gift.c:172, 160]。`filler_B20` 仍保持写入时的样子。

### `call-chain`

一帧内按顺序最多十六步，每步一个应答字。

    HOST --buffer-script call-chain \
        --chain-step call:FlagGet,0x828 \
        --chain-step call:FlagSet,0x828 \
        --chain-step call:FlagGet,0x828 --version firered

一步是 24 字节（op、target、四个参数），写作 `OP:TARGET[,ARG]...`，op 为 `call`、`read32/16/8`、`write32/16/8`。调用目标可以是 `rom_map.CALLABLE` 里的名字（绝不是反编译地址）。

一步可以从上一个结果 `prev` 取它的目标或第一个参数：

    --chain-step call:GetVarPointer,0x4024      prev = the address the GAME computed
    --chain-step read16+keep:prev               the value before, prev untouched
    --chain-step write16:prev,7                 the store, read back by the payload itself
    --chain-step read16:prev                    the value after

`ScrCmd_setvar` 通过 `GetVarPointer` 的返回值写入 [scrcmd.c:472]；没有哪个 ScrCmd 工作者是 `VarSet`（见 [ROM 映射表](frlg_rom_map.md)）。写入永远不会成为 `prev`；读取会，除非带上 `+keep`。每次写入都会把自己读回应答里。

    0x000  b .Lcode
    0x004  count       how many steps are meant, 0..16
    0x010  steps[16]   {op, target, a0, a1, a2, a3}, 24 bytes each
    0x190  result      calls, count, steps executed, the op word that stopped it
    0x1A0  values[16]  one word per step, in order

未知 opcode 会中止运行，并在应答里点名；ARM 侧也会限制步数。构造器拒绝空链、超过十六步、调用 ARM 指针或卡带之外的地址、从 `prev` 取调用目标（取错会让菜单卡死）、不对齐或不可达的读取、超过四个参数，以及任何不带 `--write-unsafe` 的写入（之后主机会提交它的存档）。

    call GetVarPointer(0x4024)   -> 0x020265B4
    read16 [prev] keep           -> 0
    write16 [prev] = 3           -> 3        the store, read back by the payload
    read16 [prev]                -> 3
    call VarGet(0x4024)          -> 3        the game's own reader, same frame

`gSaveBlock1Ptr` 换基址之后，该变量读出来仍是 3。钱是 `*moneyPtr ^ gSaveBlock2Ptr->encryptionKey` [money.c:14]：

    read32 [0x03004228]              -> 0x02025554     gSaveBlock1Ptr
    read32 [prev + 0x290] keep       -> 0x5A5A198C     the ciphertext, before
    call GetMoney(prev + 0x290) keep -> 0x00000BB8     3000, the plaintext
    call AddMoney(prev + 0x290, 1234) keep
    call GetMoney(prev + 0x290) keep -> 0x0000108A     4234, exactly +1234
    read32 [prev + 0x290]            -> 0x5A5A02BE     the ciphertext, after

（示例值。）两组 XOR 都给出密钥，这里是 0x5A5A1234，即 SaveBlock2 + 0xF20 处的那个字（`rom_map.SAV1_MONEY`、`SAV2_ENCRYPTION_KEY`）。特殊函数从特殊变量里取操作数：把 `gSpecialVar_Result` 设为 `GET_CARD_BATTLES_WON` 后，特殊函数 390 答以卡片的 `battlesWon`，即同一帧里 `SaveBlock1 + 0x3434` 持有的值。

绝不要在缓冲区脚本里调用传送或消息工作者：神秘礼物菜单没有野外。它们属于 [野外桩](frlg_rng.md#the-payload-in-the-script-body)。

## 写一个游戏会读入的扇区

以下内容全部在模拟器上实测。

### 校验和覆盖 id 自己的那块

`CalculateChecksum(data, size)` 把 `size` 字节按小端 u32 相加，并把 `(sum >> 16) + sum` 折叠成 u16 [decomp:src/save.c]。`size` 是 `sSaveSlotLayout` 里 id 自己那一块的大小，14 个 {u16 offset, u16 size} 项在法语卡带的 `0x083F58C4` 处：

| id | 大小 | id | 大小 |
| --- | --- | --- | --- |
| 0 | 3876 | 4 | 3816 |
| 1-3 | 3968 | 5-12 | 3968 |
| 13 | 2000 | | |

`HandleWriteSector` 在复制该块之前把整个扇区缓冲区清零 [save.c:181-183]，所以游戏写的扇区在其块之后是零，对全部 3968 字节求和得到同一个校验和；而在块之后带数据的自拼扇区会被拒绝。只填那一块。id 在主机上决定时，最多填 2000 字节，即最小的块：这样一个校验和对任何 id 都有效。

### id 住在哪里，哪个扇区携带该 slot 的计数器

一个 slot 是 14 个扇区；游戏在两个 slot 之间交替并轮换 id [decomp:src/save.c:174]：

    physical = ((gLastWrittenSector + id) % 14) + 14 * (gSaveCounter % 2)

`gLastWrittenSector` 每次完整保存前进一，在 14 处回绕 [:147]。普通游玩中它与计数器一致，但在一次写入被标为损坏时会分开：游戏从 `gLastKnownGoodSector` 恢复它 [save.c:159]，而 `Save_ResetSaveCounters` [:104] 会独立重置它。`gLastKnownGoodSector` 与 `gLastSaveCounter` 在它前进之前取走当前这一对，所以它们精确地描述上一代。要找一个扇区，解析页脚，绝不要靠固定的文件偏移。

`GetSaveValidStatus` 在扇区的签名为 `0x08012025` 且按 `locations[id].size` 算出的校验和相符时计入该扇区，id 取自它自己的页脚：

- 只有 14 个 id 都在且有效时，一个 slot 才算 OK；同一 slot 内的计数器不必一致；
- `slotNsaveCounter` 按物理顺序在每个有效扇区上赋值，所以它持有最后一个有效扇区的计数器。

所以一个完整 band 若其最后一个扇区携带更高的计数器，就会赢过所有扇区都携带更低计数器的 band（十三个 129 加一个 131 胜过十四个 130）。

| 地址 | 符号 | 宽度 |
| --- | --- | --- |
| `0x030045A0` | `gLastWrittenSector` | u16 |
| `0x030045A4` | `gLastSaveCounter` | u32 |
| `0x030045A8` | `gLastKnownGoodSector` | u16 |
| `0x030045AC` | `gDamagedSaveSectors` | u32 |
| `0x030045B0` | `gSaveCounter` | u32 |

法语构建的 IWRAM。读取之后，`gLastWrittenSector` 描述被采纳的 slot。

### 本次会话自己的保存不会写的那个 band

一次完整保存先分配上一对，前进 `gLastWrittenSector` 与 `gSaveCounter`，然后写入递增后的计数器所选的那个 band [save.c:144-153]。以成功消息结束的礼物会话会保存 [mystery_gift_menu.c:1379]；以其他任何结果结束的会话回到菜单，不保存。当会话将以成功结束时，现在就写 `gSaveCounter % 2` 选中的那个 band：会话的保存会写另一个。要被采纳，一个扇区要落在 band 位置 13，计数器为 `gSaveCounter + 2`，比会话的 `gSaveCounter + 1` 高一个。位置 13 处的 id 是 `(13 - gLastWrittenSector) % 14`，在主机上推导。

### 从 RAM 快照拼一个扇区

存档例程在保存时才序列化，所以 SaveBlock2 的实时内容与它会写出的内容不同。下面两种情况下每个校验和都通过、`gDamagedSaveSectors` 都保持 0：

- 加密密钥在读取时重掷。`LoadGameSave` 恢复各块，造一个新密钥，把它作用到 RAM 里每个加密字段，并把它存进 SaveBlock2 [decomp:src/load_save.c:126-128]。用 RAM 拼出的 SaveBlock2 配一个未动过的 SaveBlock1 时，钱会读成 `raw ^ flash_key ^ ram_key`。加密的字段集 [ApplyNewEncryptionKeyToAllEncryptedData] 包括：SaveBlock2 里的训练家塔时间、游戏统计、背包数量与树果粉，以及钱与游戏币。
- 保存的地图视图是 SaveBlock2 `+0x898` 处的 420 字节（210 个 u16 metatile id，`0x03FF` 为空白），只在保存时填充，在 RAM 里是零；拼出的扇区会把野外画成空白网格。

正常保存一次写全部十四个扇区，所以密钥与密文一起动；部分写入必须保住这一点。

### 读 flash：128 KiB 芯片上的 64 KiB 窗口

`swi 0x48` 线性寻址芯片。guest 读取看到 `0x0E000000` 处一个 64 KiB 的窗口，而 1 Mbit 的器件以两个 bank 到达它：

    sector N is bank N / 16 at 0x0E000000 + (N % 16) * 0x1000

窗口以上的地址会别名：`0x0E01E000`（扇区 30）读到 `0x0E00E000`，即所选 bank 的扇区 14，通常是零。从扇区算出 bank 与窗口位置。选择 bank 用游戏自己的四条存储 [decomp:src/agb_flash.c SwitchFlashBank, `0x081E0C74`，七条指令，无循环，不碰 `REG_WAITCNT`]，内联进来，于是载荷不发起 ROM 调用：

    strb 0xAA -> 0x0E005555 ; strb 0x55 -> 0x0E002AAA ; strb 0xB0 -> 0x0E005555 ; strb bank -> 0x0E000000

读取按字节进行；flash 总线是 8 位。

`ReadFlash` 唯一持久的效果，是把 `REG_WAITCNT` 的 SRAM 字段设为 3（`WAITCNT_SRAM_8` [decomp:src/agb_flash.c:149]），在启动后已经就位：`AgbMain` 清掉它 [main.c:143]，启动时的存档读取调用 `ReadFlash` [intro.c:1006]，而每个 flash 例程都写 3（`gFlash->wait[0]` [agb_flash_mx.c:28, agb_flash_le.c:28]）。

绝不要把出站消息指向 flash。头部与消息体以不同宽度读那个窗口：

| 步骤 | 代码 | 读法 | 它读到了什么 |
|---|---|---|---|
| 头部 CRC | `CalcCRC16WithTable` [mystery_gift_link.c:166] | `ldrb` | flash：`0xDEC2` 是物理 `0x1BC00..0x1BFFF` 的 CRC，`0x5907` 是 `0x1E000..0x1E0FB` 的（已选 bank 1） |
| 消息体 | `Rfu_InitBlockSend` 把每段不超过 252 字节的数据用 `memcpy` `0x081E44F4` 复制进 `gBlockSendBuffer` [link_rfu_2.c:1357] | 源与目标都字对齐且还剩 16 字节以上时用 `ldm`，一次一字 | 其他字节：成串的字节对 `01 cb`、`10 3a` 与 `04 3a`，对 `0x0E01BC00` 与 `0x0E01E000` 都一样 |

消息体 CRC 失败，主机丢弃它，礼物菜单在 RFU 链路仍连着的情况下卡住。消息体字节从哪里来不明。`build_memory_dump` 及其两个同族函数拒绝任何触及 `0x0E000000..0x0FFFFFFF` 的范围。`flash-read` 用 `ldrb` 把扇区复制进 EWRAM 并发送副本，能原样取回该扇区。

### 改动真实存档的一个字段

`flash-patch` 读一个真实保存写下的扇区，改一个字段再写回去，于是密钥与地图视图保持一致。一次编辑涉及两个扇区：

    A   the target id's sector: patch the field, recompute the checksum over the id's own chunk,
        set the counter to gSaveCounter + 2
    B   the sector at band position 13: set its counter to gSaveCounter + 2 and nothing else, not
        even the checksum, because +0xFFC is outside the summed data area

加载器会取这个 band（十二个扇区是旧计数器，两个是新的），因为 14 个 id 都有效，且最后一个有效扇区携带更高的计数器。对玩家名做一次 `flash-patch`，只改扇区 A 的字段与校验和、扇区 B 的计数器；读取采纳该 band，没有坏校验和，钱与野外不变，密钥副本与地图视图正是游戏写下的那些。

### 整条链，端到端

在模拟主机上实测：缓冲区脚本从实时全局量拼出一个扇区，`swi 0x48` 写入它，游戏下一次保存提交该映像，下一次读取采纳该 band，`gDamagedSaveSectors` 干净。交付的图案（与加载器的预检图案不同，后者哪里都没出现）在两个位置的各 500 个连续字上从 EWRAM 读回。

### 存档容器

Switch 版的存档数据只有一个文件 `save:/FireRed_f.sav`（英文为 `FireRed_e.sav`，其他语言同理），即原始 128 KiB 的 GBA flash 映像。封装层不在那个存储里创建任何脚本、配置或状态文件；模拟主机的存档目录里只有这个映像。存档路径与 `.sav` 后缀出现在封装层的 `main` 里，而它不带任何 Lua 或脚本解释器。因此存档的导入或导出只带走 guest 的 flash 映像，不带任何会被封装层当作代码或配置读取的东西。

# 读取存档

神秘礼物会话读取实时存档：里 ID，以及每只队伍宝可梦的 PID、个体值与性格。不写任何东西，也没有卡片易手。主机的日志用 `pokeldn.frlg.save.readout` 解码从偏移 0 起的 SaveBlock2 `save-dump`（名字、性别、TID、SID、游玩时间），或覆盖 0x38 起的 SaveBlock1 `save-dump`（每只队伍宝可梦的性格、个体值与努力值），并把 `trainer-id-probe` 的应答解成 TID 与 SID。

## 训练家 ID 与里 ID

SaveBlock2 偏移 0 处存着玩家名、性别、32 位训练家 id 与游玩时间 [global.h:327]。低半是训练家卡上的 TID；高半是里 ID，哪里都不显示，也不在任何链路消息里发送。

    POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live --keys PROD_KEYS \
        --buffer-script save-dump --dump-block sav2 --dump-size 64 --dump-file dump.bin

    ./.venv/bin/python tools/frlg/dump_read.py dump.bin --block sav2

    dump.bin: 64 bytes from sav2 + 0x0
      playerName    'PLAYER'
      gender        boy
      trainerId     0x12345678  TID 22136  SID 4660
      playTime      12h 34m 56s

TID 与训练家卡不符说明读取有问题。

## 队伍

SaveBlock1 0x34 是 `playerPartyCount`，然后 0x38 起是 `playerParty[6]`，每只 100 字节 [global.h:772]：六只共 604 字节。

    POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live --keys PROD_KEYS \
        --buffer-script save-dump --dump-block sav1 --dump-offset 0x34 \
        --dump-size 608 --dump-file party.bin

    ./.venv/bin/python tools/frlg/dump_read.py party.bin --block sav1 --offset 0x34

    party.bin: 608 bytes from sav1 + 0x34
      playerPartyCount 5
      slot 1: PIKACHU   Lv25 nick='PIKACHU' OT='PLAYER' PID=0x00000019 Hardy   IVs=[10,20,30,15,5,25] checksum ok
      slot 2: ...

（示例值。）

个体值按 HP、攻击、防御、速度、特攻、特防的顺序读。闪光那一列把每只的 PID 与它自己的 OTID 比较。每个槽都 `checksum ok` 说明是真实的队伍。队伍宝可梦按 `.pk3`/`.ek3` 的存法存（`pokeldn.frlg.save.mon`）：0x20 处的 48 字节与 `PID ^ OTID` 异或，四个子结构按 `PID % 24` 排序。

SaveBlock1 持有的是上次保存时的队伍（`SavePlayerParty` [load_save.c:160]，见 `--create-mon-append`）。要导出实时队伍，用 `gPlayerParty`，两张实测卡带上都是 0x02024280：

    --buffer-script memory-dump --dump-address 0x02024280 --dump-size 600

绝不要在两次运行之间沿用绝对的存档块地址；`save-dump` 每次都重新取指针。IWRAM 与 `gRngValue` 见 [随机数生成器](frlg_rng.md)。
