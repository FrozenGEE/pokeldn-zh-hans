---
title: Switch 版构建
parent: 红宝石、蓝宝石与绿宝石
nav_order: 3
nav_exclude: true
search_exclude: true
app_exclude: true
---

# 给 Switch 火红应用用的绿宝石

这个 Switch 版构建就是 pret/pokeemerald，加上从 pokefirered 移植过来的 `REVISION >= 0xA` 改动，链接时让火红/叶绿应用的载入期补丁正好落在绿宝石的无线驱动上。它代替火红卡带运行：在模拟主机上它能存档、收神秘礼物、交换，也能对着 pokeldn 的主持端用联盟室。`tools/rse/pokeemerald_switch.patch` 是针对 pret 提交 `731ad5bf` 的移植补丁；`tools/rse/emerald_switch_build.py` 负责应用并构建它。

## 应用对卡带的要求

英文 Switch 火红 ROM 就是 pret/pokefirered 的 `make compare_firered_switch`（见 [ROM 映射表](frlg_rom_map.md#the-cartridge-image)）；移植就是那个构建与 REVISION 1 之间的差异，施加到绿宝石里同一批文件上。

- **系统调用。** 应用提供 `swi 0x40..0x62`（Sloop 调用，见[在主机上运行代码](frlg_rom.md)）。`src/sloopsvc.c` 是 pokefirered 的原样文件：无线适配器调用（`0x42..0x53`）、`WriteSector`（`0x48`）、`ReplaceSector`（`0x56`）、`FinishSave`（`0x4C`）、家长控制（`0x54`）、脏词过滤（`0x4D`）、`SetSaveBlock2`（`0x55`）、`SetStarter`（`0x57`）、`SetActivity`（`0x61`）和 `IncrementLinkError`（`0x62`）。
- **存档。** 应用只在 `svc_FinishSave` 时把闪存镜像写进存储。这个构建通过 `svc_WriteSector`/`svc_ReplaceSector` 写扇区，并在 pokefirered 调用 `svc_FinishSave` 的地方调用它：`HandleSavingData` 末尾、特殊的存档扇区、最后一个链路存档扇区。
- **固定地址上的驱动。** 载入时应用会在卡带自己的 `Sio32IDMain + 0x12E`、`IntrSIO32 + 8` 和 `IntrSIO32 + 0x71C` 处打三个指令补丁（见[断点钩子](frlg_rom.md#the-breakpoint-hooks)）。`ld_script_switch.ld` 把 `librfu_sio32id.o` 与 `librfu_intr.o`（`+0x30C`）放进一个位于卡带对应地址的 `sloop_rfu` 段；除字面量指针与 `bl` 偏移外，这些代码字节就是火红的。

| 卡带 | `librfu_sio32id.o` | | 卡带 | `librfu_sio32id.o` |
|---|---|---|---|---|
| BPRE | `0x081E2814` | | BPGE | `0x081E27F0` |
| BPRF | `0x081E1568` | | BPGF | `0x081E1544` |
| BPRD | `0x081E702C` | | BPGD | `0x081E7008` |
| BPRI | `0x081E0200` | | BPGI | `0x081E01DC` |
| BPRS | `0x081E28C8` | | BPGS | `0x081E28A4` |
| BPRJ | `0x081C66EC` | | BPGJ | `0x081C66C8` |

日版的这两个地址落在绿宝石的 `.text` 里面，所以那两版卡带不做构建。

## 补丁改了什么

每处改动都包在 `#if REVISION >= 0xA` 里，所以 `make compare` 仍然与 pret 的 ROM 一致。

| 区域 | 文件 |
|---|---|
| 构建 | `Makefile`（`REVISION`、`SWITCH_CART`、地址表、`make emerald_switch`）、`ld_script_switch.ld`、`sym_common.txt` |
| 系统调用 | `include/sloopsvc.h`、`src/sloopsvc.c` |
| 适配器库与链路管理 | `librfu.h`（版本 1028）、`librfu_rfu.c`、`AgbRfu_LinkManager.{c,h}`：那批 svc 调用、更长的周期、关闭链路恢复 |
| 链路层 | `link_rfu_2.c`（rev10 的超时、重新播种、`svc_51` 上的重载与软复位）、`link_rfu_3.c`（ASCII 表）、`link.c`（错误画面、`HandleLinkConnection`） |
| 联盟室 | `union_room.c`（主持与加入组的状态机、活动上报、家长控制）、`union_room_chat.c` 与 `naming_screen.c`（脏词过滤）、`union_room_player_avatar.c`、`union_room_battle.c` |
| 存档 | `save.c`、`load_save.c`、`main.c`（`svc_SetSaveBlock2`、黑色背板、软复位时不等待适配器） |
| 保护性检查 | `cable_club.c`、`trade.c`、`field_screen_effect.c`、`menu.c`、`task.c`、`wireless_communication_status_screen.c`、`mystery_gift_menu.c`、`battle_setup.c`（`svc_SetStarter`） |

没有移植的部分：pokefirered 的片头配色、状态画面的计数、链路测试的移除、名人堂票券、树果修复、中毒闪屏速度、多选默认值和 `NDEBUG`。交换仍保留绿宝石的五轮交换后待机（见[交换](rse_link.md#trade)）。

## 构建

需要 pret/agbcc、arm-none-eabi binutils 和一个 C 预处理器。

    ./.venv/bin/python tools/rse/emerald_switch_build.py --tree ~/pokeemerald_switch --agbcc ~/agbcc \
        --cart BPRE --cpp /opt/homebrew/bin/cpp-16 --compare

`--tree` 指定的目录不存在时会自动克隆，并检出到基线提交。`--agbcc` 会把 agbcc 的 `install.sh` 跑进那个目录。`--compare` 还会额外构建 REVISION 0 并跑 pret 的 sha1 校验。如果链接脚本把 `librfu_sio32id.o` 放到了卡带地址以外，工具会拒绝这个 ROM。Homebrew 里没有 `arm-none-eabi-cpp`；用 `--cpp` 指定另一个。

从一个全新克隆出发，BPRE 构建的 sha1 是 `4e0a7e203e761cbb861ec65e98b31d6657083865`，REVISION 0 构建则通过 `pokeemerald.gba: OK`。

## 运行它

应用每次启动都从自己的 RomFS 载入 ROM（见 [ROM 映射表](frlg_rom_map.md)），所以在那个路径上放一个 LayeredFS 文件就能替换卡带，直到把它删掉。`tools/rse/rom_mod.py` 可以把这样一个文件装进模拟器的 mod 目录或 Atmosphere 的 SD 卡：

    ./.venv/bin/python tools/rse/rom_mod.py install pokeemerald_switch_BPRE.gba --title 0100554023408000
    ./.venv/bin/python tools/rse/rom_mod.py install pokeemerald_switch_BPRE.gba --title 0100554023408000 --sd /Volumes/SWITCH
    ./.venv/bin/python tools/rse/rom_mod.py remove --title 0100554023408000

ROM 必须与该标题的卡带相符：英文火红用 BPRE（`0100554023408000`），法版火红用 BPRF（`01004B3023412000`）。游戏沿用该标题的存档文件名（`FireRed_e.sav`）；绿宝石存档与火红存档不能共用同一个文件，所以先把火红的存档备份好。

在模拟主机上（英文火红，BPRE 构建），绿宝石以 60 FPS 启动，不显示电池耗尽提示，能存档，重启后也能读回存档。把模拟器的 LDN 指向 Mac 时，主持端的 `--over-ip` 可以为它服务（见[交换与联盟室](rse_link.md)、[神秘礼物](rse_gift.md)）。

## 测试存档

这些链路功能都藏在剧情标志位后面。`tools/rse/emerald_save.py` 会编辑游戏实际载入的那个槽位并重算校验和（见[存档](rse.md#the-save)）：

    ./.venv/bin/python tools/rse/emerald_save.py FireRed_e.sav --link-ready --copy-party-mon 0

| 标志位 | 打开什么 |
|---|---|
| `FLAG_SYS_POKEDEX_GET` `0x861` | 宝可梦中心 2 楼的店员 |
| `FLAG_SYS_MYSTERY_GIFT_ENABLE` `0x8DB` | 标题菜单里的 MYSTERY GIFT |

`--link-ready` 会把两者都置上，并设一个到古辰镇宝可梦中心 2 楼（地图组 2、地图 3、x 5、y 4）的继续传送点。`--copy-party-mon N` 会用新的 PID 复制一份第 N 号队伍的宝可梦追加到队尾，这样只有一只宝可梦的存档也能交换。图鉴标志位只让 POKéDEX 菜单出现，里面没有任何见过或捕捉的记录。

## 不用 Atmosphere 的投递方式

装了 Atmosphere 的主机可以直接吃 LayeredFS 文件（见[运行它](#running-it)）。未破解的主机只读该标题签过名的 RomFS，所以只能在游戏内部、每次启动时，通过存档传输所用的同一条神秘礼物原生代码通路，把 ROM 写进正在运行的那份 ROM 副本（见[存档备份与恢复](frlg_gift.md#save-backup-and-restore)）。

三个机制都已实测，支撑起整个设计：

- 带 `r0 = 0xFA000 + n`（n 在 0..0xFFF）的 `swi 0x48` 会把 4 KB 从客户机内存里的源地址写进 ROM 副本的 `0x08000000 + n * 0x1000`，覆盖全部 16 MB（见[闪存扇区通路](frlg_rom.md#the-flash-sector-path)）。
- 这样写进去的代码能跑：一份复制到 `0x083FF000` 的例程在被跳转过去时执行了（见 [frlg_rom.md](frlg_rom.md#the-flash-sector-path)）。
- 存档传输把压缩数据拆成许多条神秘礼物消息，流进 EWRAM 里一块常驻区域，每次解压 `0x800` 字节并写入一个扇区，每条消息大约 1 KB 的 token（见[存档备份与恢复](frlg_gift.md#save-backup-and-restore)）。

ROM 传输就是那条流水线，只是把写入目标从闪存扇区（0..13）换成 ROM 折叠区（`0xFA000 + n`），并且最后是启动而不是存档。每次启动都要重来一遍，因为应用每次启动都会从 RomFS 重新载入 ROM 副本。

### ROM 传输

`bin/frlg_mg_host.py --rom-transfer ROM` 会跑它（`pokeldn.frlg.gift.rom_transfer`、`asm/rom-transfer.s`；`--rom-no-boot` 在校验后停下）。一次会话是：

1. 装载负载，同时停掉 m4a 引擎（把 `gSoundInfo.ident` 和 `SOUNDCNT_X` 清零）：否则音乐会去读正在被替换的那份 ROM 里的歌曲与波形数据；
2. 对 ROM 副本的全部 4096 个块做哈希（`h = rotl(h, 1) ^ word`，每帧 32 个块）；
3. 把哈希与镜像不同的每个块写下去，每 62 条消息一个确认，每块都经 ROM 窗口读回校验；连续的同字节块会合并成一条填充消息，一次最多八块；
4. 再对所有块哈希一遍并比对；
5. 发送启动操作：关掉 `IME` 与四个 DMA 通道，把暂存的块移到正确位置，镜像之后的块变成 `0xFF`，然后 `swi 0x00`。

因为有哈希这一遍，被打断的会话能在同一次应用启动内续传：下一次会话只写仍然不同的那些块。

在模拟的英文火红上经 IP 主持端实测：把火红镜像的三个标题画面调色板改色（块 `0xEAB`、`0xEAD`、`0xEAE`），这三个块被就地写入，151 个活动块被暂存到 `0xEB1`，校验通过，启动操作之后主机经过片头重启，进了改过色的标题画面。

完整的 BPRE 绿宝石构建也曾在模拟英文火红上流式传输并启动成功：3073 个块就地写入，157 个活动块暂存到 `0xE3D`，3,691,122 字节的 LZMA 分成 4268 条消息（`--block-repeat 1 --inter-block-gap-frames 8`，消息按 10 帧解码量切分），校验一次通过，启动操作在 3 小时 12 分时发出，随后是绿宝石的片头和它在火红应用里的标题画面。过了标题，绿宝石打印了「内部电池已耗尽。游戏仍可进行。」和「但基于时钟的事件将不再发生。」，然后是一个主菜单，在火红的存档文件上提供 CONTINUE（玩家名与游戏时间都读了回来，0 枚徽章）。通过 LayeredFS 在启动时载入的绿宝石不显示电池提示；应用启动流程里哪一步设置了时钟目前不明。

ROM 副本带着应用打的三个 librfu 补丁（见[断点钩子](frlg_rom.md#the-breakpoint-hooks)），而卡带文件本身没有这些补丁。写镜像时会在卡带的 `librfu_sio32id.o` 对应位置（`builds.SIO32ID`，偏移 `+0x12E`、`+0x314`、`+0xA28`；十二版卡带都核对过那里的字节）施加同样的补丁。如果镜像里那几处的字节不是该卡带的指令，就会被拒绝：补丁会落到别的代码上。

### LZMA 流

用 `--rom-base` 指定主机自己的卡带 ROM 后，块会以 LZMA（lc 0、lp 0、pb 2，`pokeldn.frlg.gift.rom_lzma`）编码，而不是用游程与字面量 token。字典就是主机上那份副本本身：16 MB 以下的虚拟位置指向副本的字节，超出部分指向流的输出。从 0 到仍需写入的最高块，每一块都要产出，按主持端先写 `0xFFD` 与 `0xFFE` 两个 ROM 块这样的顺序排列：先做一遍不限可用性的扫描，记下每个块从哪些副本块复制，然后让一个块排在它取用 8 字节以上的任何副本块之前（拓扑排序，块号大的优先）。只有当某个副本块仍保持着扫描时看到的内容时，匹配才允许指向它：还没被流覆盖、是活动块，或者从未被触碰。匹配会在它不得读取的块之前停下；匹配之后的一个字面量，按主机在那个位置的字节编码。

解码器（`asm/rom-lzma.c`，用 clang 编译出的 1768 字节 Thumb）从 ROM 块 `0xFFF` 运行，那一块由主持端最先写入，启动时的填充会用顺序表把它清掉。它的状态连同 5.2 KB 概率表共 6.9 KB，放在 `gDecompressionBuffer + 0x2000`。它每帧解大约一千字节（在 unicorn 下每次调用最多 98,000 条指令），在一条消息被消费完之前返回 0，于是客户端下一帧再调它。解完的块用 `swi 0x48` 写入并读回校验。主持端在工作进程里编码，同时用单块扫描让链路保持忙碌。

主机在还在跑上一条消息时会丢掉新到的链路块。编码器记录解码器每字节流的开销（一个符号 6 单位，一个复制的字节 1 单位，每帧 1000 单位）；一个符号要等解码器攒够 20 字节的前瞻才开始解，也就是比编码器的计数超前 25 字节，所以它的工作量落在送来这些字节的那条消息上。每条数据消息携带它引起的解码帧数再加 6 帧；下一条消息的头块可以在解码期间到达，它的第二块只能更晚。一小段流如果对应一长串 `0xFF`，可能解上一百多帧。

| 绿宝石（BPRE）的编码方式 | 字节 |
|---|---|
| 游程与字面量 | 11,667,649 |
| 游程与字面量，外加从任何仍有效的 ROM 字节取用的复制 token（离线） | 9,081,120 |
| 对着主机副本的 LZMA，降序排列（57 段，编码耗时 26 秒） | 3,691,122 |
| 同一种编码，参照顺序（离线） | 3,206,459 |
| 不限可用性的 LZMA，贪心（离线下界） | 3,027,095 |

### 活动块

会话要运行火红自己的链路与神秘礼物代码，而它正在覆盖这份副本。这些块最后写：新字节先写进两份镜像之外的暂存块（BPRE 上是 `0xEB1` 到 `0xFFF`，共 335 块），再由启动操作搬过去。

英文火红（BPRE）的这套集合是 157 块，见 `pokeldn/frlg/data/rom_live_blocks.json`：一次模拟会话会执行的函数（传输过程中对 GBA `pc` 采了 2.16 亿次宿主侧样本，落在 327 个函数、53 个块里）、它们的直接被调者，以及它们字面量池指到的数据。把副本其余所有块都填成 `0xFF` 后，一次模拟英文火红会话照样完成了写入和校验，并打印了结束消息。再顺着数据指针往外收，几乎能覆盖整个 ROM（两级就到 3380 块）。其余十一版卡带没有实测集合，会被拒绝。

### 速率

模拟英文火红经 IP 主持端：完整哈希一遍要 120 秒（每 32 块的回答 0.6 秒）；一条 1 KB 的数据消息要 6.3 秒（160 B/s）；2077 个块作为填充消息花了 400 秒。在默认节奏下，一个 252 字节的链路块约耗 80 帧：21 个分片各发两遍（`block_repeat`），加一个 36 帧的间隔（`inter_block_gap_frames`），而链路上本来是每帧一个分片。

绿宝石（BPRE）在它的 `0xFF` 尾巴之前是 14,929,764 字节，3645 个 4 KB 扇区，且每一个都与火红 Switch 镜像同偏移的扇区不同，所以没有扇区可以跳过。一条消息携带 1012 字节 token（1 KiB 链路缓冲减去 12 字节头）：

| 编码方式 | 流大小 | 消息数 | 解码器 |
|---|---|---|---|
| 存档传输用的游程与字面量 | 11,667,649 字节 | 14,566 | GBA 侧已有，已测试 |
| 不做过熵编码的复制/字面量格式，对着整个火红镜像与绿宝石自身的输出做匹配，字节对齐 token | 8,470,154 字节 | 8370 | 未实现 |
| LZMA2，64 KB 窗口 | 6,169,577 字节 | 6097 | 未实现 |
| LZMA2，不限窗口 | 5,747,728 字节 | 5680 | 未实现 |
| 以火红镜像为字典的 LZMA2 | 2,561,046 字节 | 2531 | 未实现 |

DEFLATE 的 32 KiB 窗口看不穿两个 ROM 之间 15 MB 共用的库与引擎代码，所以在 `zlib` 下用火红当字典几乎没用（6,991,630 字节，完全不用字典是 6,975,681 字节）：字典带来的收益只对跟 ROM 一样大的窗口成立。而解码器的复杂度不必随窗口增长：一个复制 token 可以不加额外成本地写明任意 32 位源地址，所以不限窗口的匹配器所需的解码器和存档传输现有的那个一样，都是分发加 memcpy，只多一种 token 类型。在火红镜像与绿宝石自身输出上对着哈希链匹配器（6 个候选，5 字节键）实测，这种格式仍比 LZMA2 差约 3.3 MB：LZMA2 在窗口之外的大部分优势来自它的区间编码器把短匹配和字面量打包成几分之一字节，这是字节对齐格式做不到的。要达到 LZMA2 的数字，GBA 侧需要真正的熵编码器，而不只是更大的窗口。`tools/rse/emerald_switch_build.py` 已经为这个目标带着一套可用的 agbcc / arm-none-eabi 工具链，所以那个解码器更适合从现成的小型 C 语言 LZMA 或 LZMA2 参考解码器改造并交叉编译，而不是从零手写汇编；目前还没有这样的实现。

在板子上做一次正版机恢复，每秒约 150 字节 token，再加每扇区约 3.5 秒：19 个扇区花了 107 秒、6182 字节 token，27 个扇区花了 249 秒、27,421 字节 token，两点拟合，未经第三次运行确认。按这个速率，整条流在存档传输编码下约需 22 小时，在无熵编码格式下 16 小时，LZMA2 下 11 小时，用火红当字典则 5 小时；3645 个扇区按每扇区 3.5 秒再给上述任一数字加上 3.5 小时——前提是每个扇区仍沿用恢复流程里每扇区一次往返的确认。恢复现在每条确认最多发 62 条数据消息（见[恢复](frlg_gift.md#restore)），ROM 传输用的是同样的批处理。目前测到的最长会话持续了 269 秒。

启动会写入 GBA 的 SoftReset 标志并执行 `swi 0x00`：BIOS 清空 RAM 后跳到 `0x08000000` 的 ROM 复位向量，于是绿宝石自己的 `AgbMain` 从刚写好的字节开始初始化。BIOS 软复位在核内完成，不算一次应用启动，所以对 ROM 副本的写入能活过它。rom-reset-probe 负载（`asm/rom-reset-probe.s`）往 ROM 副本块 0xF00（0x08F00000，在火红的 `0xFF` 尾巴里）写了 `word[i] = 0x454D4552 + i`，执行 `swi 0x00`，重启后第二次神秘礼物会话导出了 0x08F00000：16 个字全部原样读回（英文火红，模拟主机，经 IP 主持端）。RomFS 的重载发生在应用启动时而不是软复位时，所以写进去的 ROM 能挺过这次启动，进入新游戏。

## 尚未解决

- 应用是否模拟绿宝石读取的 GPIO 实时时钟：在启动时载入的绿宝石主菜单不显示电池提示，而流式传输进去的会显示。
- 正版主机能否运行这个构建：目前只有模拟主机上的测量。
- 流式启动之后的实时时钟，以及绿宝石在继续火红存档时会做什么。
- 正版主机上经板子的传输流，以及那里的节奏。
- 错误路径所需的活动块。在一次模拟流写到第 2816 块时出现链路错误，在错误画面按 A 得到黑屏：回到标题的路径位于已被覆盖的块上，所以被打断的流只能从重启应用开始。
- 为什么模拟主机的链路在流式传输中途停了两次（一次在 20 分钟后，一次在 1 小时 49 分后），而帧率直到最后一秒都稳定。后一次停止时，主机自己的链路层在开启一批的那条短消息之后 0.27 秒发出了 RFU 断开帧（`0x44`），在此之前两个方向都是满速；究竟是什么让它放弃仍不清楚。
- 其余十一版卡带的活动块。
- 持续数小时的会话能否稳定维持。
- 绿宝石往火红存档文件里存过之后，火红会怎么处理它。
- 日版卡带的构建。
