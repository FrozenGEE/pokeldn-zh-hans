---
title: 神秘礼物
parent: 火红与叶绿
nav_order: 2
---

# 神秘礼物

火红与叶绿通过好友模式接收的神秘礼物可以是一张神秘卡片、一段配送脚本、一份神秘新闻、一位来访的对战塔训练家，或一只直接放进队伍的宝可梦，全程不需要宝可梦中心。神秘事件 VM 与原生 ARM 代码见[游戏主机上的代码](frlg_rom.md)。

## 会话

游戏主机的客户端以 `{CLI_RECV, MG_LINKID_CLIENT_SCRIPT}, {CLI_COPY_RECV}` 启动 [mystery_gift_scripts.c:15]，并执行它收到的任何 `MysteryGiftClientCmd` 数组 [mystery_gift_client.c:87]。

    console joins  ->  SEND_PLAYER_IDS  ->  LinkPlayer block exchange  ->  one standby barrier
      server -> CLIENT_SCRIPT (sClientScript_SendGameData, 32 B)
      client -> GAME_DATA     (MysteryGiftLinkGameData, 96 B)   -- validated, card flag compared
      server -> CLIENT_SCRIPT (sClientScript_SaveCard, 48 B)
      server -> CARD          (struct WonderCard, 332 B)
      server -> RAM_SCRIPT    (1024 B: the delivery bytecode, zero-padded)
      client -> READY_END     (1024 B)
    close-link handshake  ->  disconnect

### 分帧规则

- 大小为 0 表示 1024 [mystery_gift_link.c:55]；`SVR_COPY_SAVED_RAM_SCRIPT` 从不设置 `ramScriptSize` [mystery_gift_server.c:275]，因此 RAM 脚本和 READY_END 都是完整的 1024 字节消息。CRC 覆盖填充后的缓冲区。
- 块节奏没有确认：除非接收方的槽位是 `RECV_STATE_READY`，`SEND_BLOCK_INIT` 会被忽略 [link_rfu_2.c:1146]。`MysteryGiftTiming.inter_block_gap_frames` 为 36；丢一个块就会让游戏主机永远等下去。客户端要用若干帧才收完的载荷会占用槽位那么久：服务器发这类消息时要带上 `after`，即最后一个块发出后游戏主机仍忙的帧数。下一条消息的头块可能就落在这段时间里；主机会压住自己的第二个块，直到游戏主机空闲。
- 游戏主机发送期间的停顿遵循[镜像规则](frlg_link.md#row-one-of-the-parents-table-is-the-consoles-own-command-mirrored-back)。

### 模块

除非另有说明，均位于 `pokeldn/frlg/gift/` 下：

| 文件 | 作用 |
|---|---|
| `mg_link.py` | 分帧：6 字节 `{ident, crc, size}` 头块 + 每块不超过 252 字节 |
| `mg_script.py` | 客户端脚本汇编器、反编译产物中的现成脚本、`MysteryGiftLinkGameData` 读取器 |
| `mg_server.py` | 服务器脚本解释器（`SVR_*`） |
| `host_mystery_gift.py` | 主导端引擎：`tick()` → 父进程 gSendCmd，`feed_child_slot()` ← 子行 |
| `host_mg_app.py` | 挂在主机运行时之上的应用钩子 |
| `wonder_card.py` | 逐字节精确的时拉比与传说三圣兽卡片／RAM 脚本构建器 |
| `stamp_rally.py` | 印章拉力卡片、印章、激活包装、配送脚本 |
| `gift_composer.py` | 动作定义、游标状态校验、RAM 脚本编译器 |
| `gift_registry.py` | 目录 |
| `gift_to_bin.py` | 供外部第三世代神秘礼物工具使用的 `.bin` 导出器 |
| `pokeldn/frlg/save/save_inject.py` | 带卡片、RAM 脚本和扇区校验和的存档礼物写入 |
| `bin/frlg_mg_host.py` | 命令行入口 |

## 运行它

    (them) Mystery Gift -> Wonder Cards (Recevoir) -> Friend (Ami), wait on the search screen
    (you)  POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live --phy auto \
               --keys PROD_KEYS --gift beast-cutscene --flag-id 1005
    (them) join the host when it appears; YES on the replace-card prompt if one shows

无线电设置见 [ESP32 无线模块](hardware_esp32.md)。每次运行只服务一台游戏主机；主机在它离开 LDN 后停止（[主机实现](frlg_host.md)）。`tests/test_mystery_gift_flow.py` 和 `tests/test_mystery_gift_end_to_end.py` 模拟了游戏主机的接收路径。

`--save-to-board` 改为把礼物存到 ESP32 板子上然后退出；此后板子只要接上任意 USB 充电器供电，就会自己对每一台加入的游戏主机重放这个会话，一次一台，使用每张卡带自己的字节（[主机镜像](hardware_esp32.md#a-host-image)）。

    (you)  POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live \
               --keys PROD_KEYS --gift celebi --save-to-board

## 链路能承载什么

22 条客户端指令中有三条 [include/mystery_gift_client.h:18] 会真正执行东西：

| 指令 | 游戏主机做什么 |
|---|---|
| `CLI_SAVE_RAM_SCRIPT` (17) | 存下一段场地脚本；它在下次与 NPC 交互时运行 |
| `CLI_RUN_MEVENT_SCRIPT` (15) | 运行一段神秘事件字节码脚本（17 条操作码的 VM） |
| `CLI_RUN_BUFFER_SCRIPT` (21) | `func = (void *)gDecompressionBuffer; func(&param, gSaveBlock2Ptr, gSaveBlock1Ptr)`；最多 1024 字节 ARM |

## 唯一的 RAM 脚本槽位

游戏主机要么持有一张神秘卡片，要么持有一段绑定 RAM 脚本，绝不会两者兼有。`ValidateSavedWonderCard` 以 `ValidateRamScript` 收尾 [mystery_gift.c:186]，后者要求 `RAM_SCRIPT_MAGIC`、地图为 `MAP_UNDEFINED` 且 `objectId == 0xFF` [script.c:538]；场地只会在与之对话的对象的坐标上运行这样一段脚本 [field_control_avatar.c:458]。`CLI_SAVE_RAM_SCRIPT` 写入的是 MAP_UNDEFINED/0xFF [script.c:578]；神秘事件 VM 的 `initramscript` 写入真实坐标。绑定脚本存在时，卡片仍留在存档里，但菜单会把它藏起来，GameData 报告的 `flagId` 为 0 [mystery_gift.c:349]。

下一张神秘卡片会重新绑定该槽位，卡片随之恢复；缓冲区脚本则不碰这个槽位。一张卡片会重写 SaveBlock1 的 +0x32E0（卡片）和 +0x361C（RAM 脚本），只涉及一个扇区，SaveBlock2 不动。

存档本身也能带上同样的一对：`pokeldn/frlg/save/save_inject.py` 会把一张有效卡片和一个 RamScript 写进原始存档（`inject_gift`、`build_ram_script_struct`），因此通过神秘卡片导入的存档无需在线主机，就能在它的 NPC 处运行该脚本。脚本的 `callnative` 操作码可以触达客户机 ARM，`resident-save` 礼物正是用它绑定妈妈的加载器。

`ramScript.checksum` 是对 1000 字节做的 `CalcCRC16WithTable`，即声明的 999 字节加一个置零的填充字节 [script.c:500]（`CalculateRamScriptChecksum`，BPRE 为 `0x0806D43C`，BPRF 为 `0x0806D5A0`）。若某个槽位的 CRC 只覆盖 999 字节，它会在对象第一次被对话时被清掉 [script.c:526]。

## 礼物目录

`--gift NAME`；`--help` 会列出 flag id（1000..1019）。只有当前持有的卡片才有意义：相同的 id 就意味着「已有这张卡片」（`MysteryGift_CompareCardFlags`）。已经持有该卡片的游戏主机只收下神秘事件礼物，不会出现提示。

| 礼物 | 做什么 |
|---|---|
| `beast-cutscene-share` | 可重复的传说三圣兽过场；默认演示卡片 |
| `celebi` | 由组合器生成的 50 级时拉比卡片 |
| `porygon-tm-gift` | 多边兽卡片、皮皮场景，先给 TM29 精神强念再给 TM46 小偷 |
| `solrock-stamp` / `lunatone-stamp` | 同一张印章拉力卡片的两半 |
| `altering-cave` | 移植来的官方变化洞窟活动 |
| `wish-egg`、`pokepark-egg`、`pc-japan-egg` | 官方配送的蛋 |
| `event-pokemon` | 一只第三世代配送宝可梦，直接放进队伍 |
| `starter-egg` | 九只初始伙伴之一的蛋，由 `random` 抽取 |
| `rare-berries` | 谜之果、龙睛果和星桃果各一，每阶段一个 |
| `national-dex` | 除非 `IsNationalPokedexEnabled`（403）返回 1，否则调用 `EnableNationalPokedex`（special 367） |
| `nature-mint`、`pc-anywhere` 以及另外 42 个 | GB-Link 团队的卡片 |
| `battle-count-card` | 官方对战计数卡片 |
| `visiting-trainer` | 以 ident 26 传入的对战塔训练家（仅火红） |
| `mystery-event-probe` | `givenationaldex; setstatus 42; checksum`，即 VM 的自检 |
| `mystery-event-celebi` | `givepokemon`：一只携带信件的 30 级时拉比，直接放进队伍 |
| `mystery-event-npc` | `initramscript`：把一段场地脚本绑定到真新镇的胖男人身上 |
| `rng-seed-reader`、`rng-rate-probe`、`rng-shiny-hunt`、`rng-mon-hunt`、`rng-mon-hunt-both`、`rng-mon-hunt-log` | 见[随机数生成器](frlg_rng.md) |

### 传说三圣兽

一位配送员给出龙睛果、枝荔果和大师球，然后开启一场可重复的 65 级对战：存档选了妙蛙种子就是水君，选了杰尼龟就是炎帝，选了小火龙就是雷公。

### 多边兽招式学习器礼物

一张带多边兽图标的卡片，加上玩家右侧三格处的皮皮立绘，会在两个不同的检查点分别给出 TM29 和 TM46。默认 flag id 为 1007；查看器显示 `flag_id % 100`。

### 印章拉力

两个活动共用一张 `SUN AND MOON RALLY` 卡片（念力土偶图标、两个印章槽位、flag id 1006），先后顺序随意。每个印章给一只 30 级的太阳岩或月石；两个都给则给一只 50 级的时拉比。

| 状态 | 含义 |
|---|---|
| `VAR_MYSTERY_GIFT_1` | 时拉比的完成游标 |
| `VAR_MYSTERY_GIFT_2 = 0/1/2` | 太阳岩 无／进行中／已收到 |
| `VAR_MYSTERY_GIFT_3 = 0/1/2` | 月石 无／进行中／已收到 |
| `FLAG_MYSTERY_GIFT_DONE` | 拉力完成 |

```text
matching = saved flag ID == distribution flag ID and max stamps == 2 and icon species == CLAYDOL
if no card:                install shared card + delivery script + selected stamp, run activation
else if not matching:      offer the toss prompt; on accept, install as above
else if stamp species or ID already exists:   HAS_STAMP
else if neither slot empty:                   NO_ROOM_STAMPS
else:                      save the stamp, run activation, STAMP_RECEIVED
```

激活部分是一段神秘事件包装。`IsStampInMetadata` [mystery_gift.c:272] 会拒绝冲突的印章；`CLI_SAVE_STAMP` 只写入 `cardMetadata.stampData` [mystery_gift.c:307]。

### 变化洞窟

官方脚本 [data/mystery_event_msg.s:325] 给 `VAR_ALTERING_CAVE_WILD_SET`（0x4024，SaveBlock1 + 0x1048）加 1，在 10 处回绕；值为 9 及以上时读表 0 [wild_encounter.c:192]。

| 变量 | 物种 | | 变量 | 物种 |
|---|---|---|---|---|
| 0 | 超音蝠 | | 5 | 长尾怪手 |
| 1 | 咩利羊 | | 6 | 壶壶 |
| 2 | 榛果球 | | 7 | 惊角鹿 |
| 3 | 戴鲁比 | | 8 | 图图犬 |
| 4 | 熊宝宝 | | | |

### 配送的蛋

三个日本配送活动，来自 GB-Link-Switch-LDN 的 `web/js/gift/official.js`。卡片用 `random` 抽取一枚蛋 [scrcmd.c:455]；它会带上该配送的招式、命运邂逅位和 0xFF 的相遇地点。队伍已满时会在抽取之前拒绝。

| 卡片 | 蛋 |
|---|---|
| `wish-egg`（Pokemon Center New York） | 吉利蛋、催眠貘、蛋蛋、大葱鸭、袋兽、大舌头；各自都会许愿 |
| `pokepark-egg`（PokePark Market Fantasia） | 刺球仙人掌、龙虾小兵、太阳珊瑚、宝宝丁、负电拍拍、皮丘、正电拍拍、可达鸭、向尾喵、晃晃斑、跳跳猪、溜溜糖球、傲骨燕、咕妞妞、小果然 |
| `pc-japan-egg`（Pokemon Center Japan） | 喇叭芽（摇晃舞）、喵喵（花瓣舞）、走路草（寄生种子）、蚊香蝌蚪（天使之吻） |

### 活动宝可梦

`--gift event-pokemon --event-pokemon NAME` 发送一只由 PKHeX.Core 依 `EncounterGift3`（非蛋、非日本）按其 PID/IV 方式生成、并通过合法性检查的第三世代配送宝可梦；卡片保存时经神秘事件的 `givepokemon` 给出。队伍已满时返回状态 3，卡片可以再次接收。默认是 WISHMKR 的基拉祈。

`NAME` 由训练家名和物种组成：`WISHMKR Jirachi`、`CHANNEL Jirachi`、`Aura Mew`、`MYSTRY Mew`、`DOEL Deoxys`、`SPACE C Deoxys`、`ROCKS Metang`、所有 `10 ANIV` 物种，以及欧版的 `10ANNIV`、`10JAHRE`、`10ANNI` 和 `10ANIV` 发布；`--language` 用于在语言间选择。

该卡片与构建无关；`tests/test_frlg_english_cartridges.py` 会让它在每张卡带的 `RunMysteryEventScript` 上跑一遍。

### GB-Link 团队卡片

GB-Link 团队的自定义卡片（GB-Link-Switch-LDN 的 `cards/`，GPL-3.0）由一张神秘卡片加一段通过 `callnative` 调用 THUMB 代码的 RAM 脚本组成。源码在 `vendor/gblink-cards/`；`scripts/gen_team_cards.py` 生成 `pokeldn/frlg/data/team_cards.json`，逐字节复现他们全部 44 个 `BPRE 1.10` 载荷，`team_cards.py` 则注册每个去掉 `custom-` 前缀的 id。`starter-egg`、`rare-berries`（道具 173-175）和 `national-dex`（`FLAG_SYS_NATIONAL_DEX` 0x840）是用组合器重建的。

| 分组 | 卡片 |
|---|---|
| 改变一只宝可梦 | `nature-mint`、`ability-capsule`、`poke-ball-changer`、`pokemon-gender`、`nickname`、`stat-judge`、`hidden-power`、`hidden-power-type`、`ev-training`、`friendship`、`pp-max`、`max-conditions`、`pokerus`、`unown-letters`、`trade-evolution`、`espeon-umbreon`、`move-tutor` |
| 逐帧钩子 | `speed-2`、`speed-3`、`speed-4`、`speed-0-75`、`speed-0-5`、`fast-text`、`travel-anywhere`、`pc-anywhere`、`hm-moves`、`reusable-tms`、`physical-special-split`、`exp-share`、`shiny-hunting`、`roamer` |
| 其他 | `no-encounters`、`legendary-respawn`、`instant-eggs`、`gift-box`、`pocket-casino`、`gift-ribbons`、`trainer-ids`、`gender-swap`、`rival-name` |
| 活动宝可梦 | `box-eggs`、`colosseum-pikachu`、`ageto-celebi`、`mattle-ho-oh` |

与他们构建版的差异：

- 全部十二张 `0x0A` 修订版卡带：`vendor/gblink-cards/symbols.json` 保存每张 ROM 的 167 个地址，`tests/test_team_cards.py` 校验它们，每段脚本还会检查头部的游戏、语言和修订版（[卡带映射](frlg_rom_map.md#the-international-revision-0x0a-cartridges)）。
- 搬迁后的脚本（996 字节）和菜单列表（80 字节）位于 `0x0203F768` 和 `0x0203FB50`，在 `0x0203FC00` 的常驻钩子之下（[载荷能放在哪里](frlg_rom.md#where-a-payload-can-live)）。
- 钩子安装器链到 `VBlankIntr`，存放于 `0x0203FBFC`，因此钩子卡片和游戏增益会互相替换。它们的状态在 `0x0203FF60`。
- 大于 1019 的 id 没有 `sReceivedGiftFlags` 位；注册表发送 `1000 + id mod 20`。
- `hm-moves` 和 `physical-special-split` 的文本被缩短，以塞进 995 字节。

十二张卡带上，每张卡片都能在 mGBA 下以绑定妈妈的形式运行。在另一款游戏的卡带上，载荷会回应「This gift doesn't work with this version of the game.」（日文为「Wrong game.」）。`colosseum-pikachu` 和 `ageto-celebi` 携带日文训练家名，在欧洲卡带上会显示为圆点。

### 对战计数卡片

`MysteryEventScript_BattleCard` [data/mystery_event_msg.s:162] 在 `GET_CARD_BATTLES_WON`（special 390）恰好为三时给一个伤药；移植版按自己的变量设闸，所以可以重复。只有当 96 字节训练家卡片之后的 u16 等于当前卡片的 flag id 时，计数器才会推进 [union_room.c:1777]（`frlg_trade_host.py --card-flag-id N`）。

| 什么会推进 | 在哪里 | 规则 |
|---|---|---|
| `numTrades` | 一次完成的交换 [trade_scene.c:2609] | 卡片尚未计过的训练家 id |
| `battlesWon` / `battlesLost` | 一场电缆俱乐部对战 [cable_club.c:792] | 同上，每项 5 个 id |

联盟室的对战不计入任何东西；只有[电缆俱乐部竞技场](frlg_link.md#the-cable-club-colosseum)计入。计数器位于 SaveBlock1 + 0x3434，没有 CRC [mystery_gift.c:490]：

    0x3434: 0000 0000 0100 2300     trades 1, icon 35 (CARD_TYPE_LINK_STAT)

`CARD_TYPE_GIFT` 类型的卡片即使 special 运行过也保持为零。

### 来访训练家

`CLI_RECV_EREADER_TRAINER`（18，ident 26）把缓冲区复制到 `gSaveBlock2Ptr->battleTower.ereaderTrainer` [mystery_gift_client.c:233]。该结构为 188 字节 [global.h:286]：

    0x00 u8  unk0                  0x10 u16 greeting[6]            0x34 BattleTowerPokemon party[3]
    0x01 u8  trainerClass          0x1C u16 farewellPlayerLost[6]  0xB8 u32 checksum
    0x02 u16 winStreak             0x28 u16 farewellPlayerWon[6]
    0x04 u8  name[8]
    0x0C u8  trainerId[4]

当前 46 个字不全为零、且那个 u32 是它们的和时才有效 [battle_tower.c:1354, :1384]。随后 `SevenIsland_House_Room1` 里的老妇人会提供一场由 `CreateBattleTowerMon` 构建的可重复 3v3 对战 [battle_tower.c:928]；不适用等级规则，也没有禁用名单。FRLG 只显示名字的五个字节 [battle_tower.c:1343]。`--gift visiting-trainer` 会一起发送卡片、RAM 脚本和训练家；若已持有同一张卡片，则只发训练家。

## 神秘新闻

`struct WonderNews` [global.h:646] 为 444 字节：

| 偏移 | 大小 | 字段 | 说明 |
|---|---|---|---|
| 0x000 | 2 | `id` | 不能为 0，这是唯一的检查 [mystery_gift.c:113] |
| 0x002 | 1 | `sendType` | `SEND_TYPE_DISALLOWED` 会隐藏「Send」 [mystery_gift.c:120] |
| 0x003 | 1 | `bgType` | `>= NUM_WONDER_BGS` 时读作 0 [mystery_gift_show_news.c:110] |
| 0x004 | 40 | `titleText` | 在 224 px 的窗口中居中 |
| 0x02C | 400 | `bodyText[10][40]` | 屏幕上显示八行；索引超过 7 的行会点亮滚动指示符 [:346] |

`IsWonderNewsSameAsSaved` 会比较全部 444 字节 [mystery_gift.c:140]（`--news-id N` 可让新闻变新）。新闻和卡片从不互相顶替。

- `build_wonder_news_app_data` 广播活动号 22 [src/data/union_room.h:406]。
- 游戏主机以 `MG_LINKID_RESPONSE`（ident 19）应答：`FALSE` 表示已保存，`TRUE` 表示已持有 [mystery_gift_client.c:210; mystery_gift_scripts.c:126]。
- 来自好友模式的新闻会在 `ITEM_RAZZ_BERRY` 与 `ITEM_NOMEL_BERRY` 之间抽一种树果，由 `CeruleanCity_House4` 里的男人给出，最多五个，然后走 500 步 [mystery_gift_menu.c:1367, wonder_news.c:21]。四个树果的奖励需要那条被封锁的无线路径。

`--news`（`--news berry`、`--news-id N`）。消息顺序（约 18 s）：

    ident 16  sClientScript_SendGameData
    ident 17  MysteryGiftLinkGameData
    ident 16  sClientScript_SaveNews
    ident 23  MG_LINKID_NEWS - 444 bytes in three blocks
    ident 19  MG_LINKID_RESPONSE - FALSE: the console saved it
    ident 16  sClientScript_NewsReceived
    ident 20  READY_END                              -> SVR_MSG_NEWS_SENT

## 问卷作为口令闸门

`SVR_CHECK_QUESTIONNAIRE` 会比较友好商店问卷的四个词 [mystery_gift.c:422]；`mg_server.gate_on_questionnaire(script)` 把它接在游戏数据前缀之后：

    bin/frlg_mg_host.py --gift ... --questionnaire species:55,FEELINGS/60,move:177,why

一个词可以是英文名、`species:N`、`move:N`、`GROUP/INDEX` 或原始 id。短语不对时，游戏主机会收到主机发来的 64 字节消息（`CLIENT_SCRIPT_DYNAMIC_ERROR`），别的什么都不发。每次会话都会从 GameData 记录游戏主机的四个词 [mystery_gift.c:361]：

    questionnaire: POKEMON/55  done [FEELINGS/60]  MOVE_1/177  why [MISC/37]

`EC_GROUP_POKEMON` 按物种索引，`EC_GROUP_MOVE_1` 按招式 id 索引；见[法语 Easy Chat 词表](frlg_rom_map.md#the-french-easy-chat-vocabulary)。

## 游戏主机会主动交出什么

GameData 携带 Easy Chat 档案和卡片统计 [mystery_gift.c:361]。`--game-data-log PATH`（`game_data_log.py`）会把每次会话追加到一份 JSONL 台账，并打印该游戏主机上一次以来的变化；`tools/frlg/game_data_read.py PATH` 可读取它。计数器只有在同一卡片 flag id 上作为差值才构成证据。

## 存档备份与恢复

一次「神秘卡片、好友」会话会把游戏主机整个 128 KiB 的存档芯片复制到主机，或者把一个 `.sav` 写进去并让游戏加载再保存它；期间不发送卡片。`asm/save-backup.s` 和 `asm/save-restore.s` 移植自 GB-Link 团队的 `cards/savebackup.s` 和 `cards/saverestore.s`（GPL-3.0）；主机侧是 `pokeldn.frlg.gift.save_transfer`（`--save-backup FILE`、`--save-restore FILE`），以及应用里的「你的存档」标签页（[你的存档](gui.md#your-saves)）。两者都能在全部十二张卡带上运行（[存档备份与恢复](frlg_rom_map.md#save-backup-and-restore)）。

### 令牌编码

字节 `n < 0x80` 后面跟 `n + 1` 个原样字节；`n >= 0x80` 则把一个字节重复 `n - 0x80 + 3` 次（游程 3 到 130，原样字节最多 128 个）。

### 备份

客户端脚本会把 `CLI_LOAD_TOSS_RESPONSE, CLI_RUN_BUFFER_SCRIPT, CLI_SEND_LOADED` 每段最多重复 32 次。每一趟为芯片上至多 8 KiB 的内容发送至多 1 KiB 的令牌，绝不跨越 64 KiB 的 bank 边界；芯片偏移是 `client->param = 0x5A << 24 | offset` [mystery_gift_client.c:276]，不带 `0x5A` 的 `param` 会从 `first` 开始。

| 载荷字 | 偏移 | 值 |
|---|---|---|
| `first` | `0x004` | 第一趟起始的芯片偏移 |
| `send_queue` | `0x008` | `&gRfu.sendQueue.count` |

一趟会每帧把 `0x800` 字节搬进 `gDecompressionBuffer + 0x800`，压缩到 `+ 0x400`，并设置 `link.sendBuffer`（`param + 0x3C`）和 `link.sendSize`（`param + 0x34`）。当 `gRfu.sendQueue.count` 不为零时它等待。会话以 `CLI_MSG_BUFFER_FAILURE` 加一条消息结束，因此游戏主机不会存档 [mystery_gift_menu.c:1379]。被截断的备份按游戏代码和训练家 id 续传。

### 恢复

1. 第一条消息是 620 字节的镜像；`install` 把它复制到 `gDecompressionBuffer + 0x400`，并以 28 个槽位扇区的 12 字节尾部（id、校验和、签名、`+0xFF4` 处的计数器）作答。
2. 主机按 `GetSaveValidStatus` 的方式找出最新的完整槽位，把文件里的副本写进另一个槽位、计数器为 `newest + 1`，然后照文件所写写入扇区 28 到 31。
3. 它先擦除目标槽位的 id-0 扇区，最后才写新的 id 0，这样在新的那份完整之前，芯片自己的副本仍能加载。
4. 之后的消息以 `b RESIDENT + 4`（`0xEA0000FF`）开头，然后是一个 op。`OP_DATA`（1）把扇区、写入标志、u16 偏移、u16 令牌长度和令牌带进一个 4 KiB 缓冲区；该扇区的最后一条消息用 `swi 0x48` 写入并校验，不匹配时置一个失败掩码位。一段客户端脚本最多携带 62 条数据消息、涉及若干扇区，游戏主机在它结束时一次性报告累积的失败掩码。新的 id 0 会自开一批，因此只有在其槽位其余部分读回完整之后才会发送。
5. `OP_FINISH`（2）在没有失败时调用 `LoadGameSave(SAVE_NORMAL)` [save.c:803]。结果为 `SAVE_STATUS_OK` 时会话以 `CLI_MSG_BUFFER_SUCCESS` 结束，游戏主机保存加载后的游戏；否则以 `CLI_MSG_BUFFER_FAILURE` 结束，旧存档保留。

| 载荷字 | 偏移 | 值 |
|---|---|---|
| `b install` | `0x000` | 第一条消息的入口 |
| `b entry` | `0x004` | 之后每条消息的入口，位于 `gDecompressionBuffer + 0x404` |
| `load_game_save` | `0x008` | `LoadGameSave \| 1` |

若加载到的副本不完整或属于另一种布局，主机会拒绝该存档：日文 SaveBlock1 短 40 字节，这一点从训练家自己那只宝可梦的语言字节（`+0x12`）读出。

`tests/test_save_transfer.py` 针对脚本化的游戏主机覆盖备份、续传、恢复和被中断的恢复。在零售硬件上，备份在法版和英版火红上可用，恢复在英版火红上可用（包括法版存档）。游戏主机的下一次存档会在扇区 1 到 7 与文件不同，那些扇区承载 `LoadGameSave` 重新掷出的加密密钥。

## 创作礼物

`pokeldn.frlg.gift.gift_composer` 从 `WonderGift` 定义构建卡片和配送脚本：

```python
MEWTWO_GIFT = WonderGift(
    slug="mewtwo-encounter",
    card=WonderCardSpec(icon_species=150, title="MYSTERIOUS ENCOUNTER",
                        body=("Visit the deliveryman.",), default_flag_id=1008),
    intro_message="A powerful presence is waiting!",
    event=GiftSpec(shareable="once"),          # or StampRallySpec(...)
    delivery=DeliveryPlan(delivery=(
        DeliveryStage(Message("Take this."), GiveItem(1)),  # Master Ball
        DeliveryStage(ShowSprite(0, RelativeToPlayer(dx=1)), BattleLegendary(150, level=70)),
    )),
    completed_message="That mysterious encounter is over.",
)
```

`WonderGift.delivery` 使用 `delivery`；`StampSlot.delivery` 和 `StampRallySpec.completion` 使用 `pre_stages` 和 `post_stages`。编译器从 `VAR_MYSTERY_GIFT_1` 恢复阶段，成功时置 `FLAG_MYSTERY_GIFT_DONE` 和收据标志；`GiftSpec(repeatable=True)` 会重置游标。

### 阶段与条件

每个 `DeliveryStage` 就是一个检查点；绝不要把两个可能失败的奖励（`GiveItem`、`GivePokemon`、`GiveEgg`）放进同一个阶段。携带招式的 `GiveEgg` 需要一个队伍空位。`GiveRandomEgg(eggs)` 通过跳转表抽取一个（十五枚四招式的蛋可以塞进 944 字节）。`condition=`（`VarEquals`、`FlagSet`、`Not`、`AllOf`、`AnyOf`）会跳过某个阶段但推进游标；`RequireSpecialResult(...)` 在失败时停下且不推进。

```python
DeliveryStage(ShowSprite(142, RelativeToPlayer(dx=1)),
              condition=VarEquals(0x4031, 0))  # VAR_STARTER_MON == Bulbasaur
DeliveryStage(RequireSpecialResult(SPECIAL_HAS_ALL_KANTO_MONS, 1, "Finish the KANTO POKEDEX first."),
              GivePokemon(251, level=50))
```

`SetVar`（`setvar` 0x16）和 `AddVar`（`addvar` 0x17）接受存档变量 0x4000..0x40FF 和特殊变量 0x8000..0x8011。

### 对战

`BattleLegendary` 会发出 `setwildbattle`、`special StartLegendaryBattle`、`end`，且不带 `waitstate`（[RAM 脚本可能无法从对战中返回](frlg_rng.md#a-ram-script-may-not-come-back-from-a-battle)）；`BattlePokemon` 发出 `dowildbattle`。两者都会结束自己的阶段。印章槽位路径中拒绝放置对战，除非作为带条件的终结备选。

### 共享

`GiftSpec.shareable` 设置卡片的 `sendType`：`"never"`、`"once"`（接收方的那份变得不可共享）或 `"always"`。

### 命运邂逅标记

`GivePokemon(..., fateful_encounter=True)`（以及 `GiveEgg`）会发出 `setmonmodernfatefulencounter`（`0xCD`）和 `setmonmetlocation`（`0xD2`，0xFF）[data/mystery_event_msg.s:71]。第一条命令不检查索引边界 [scrcmd.c:2239]；索引是给出之前的队伍数量，队伍已满时会跳到失败标签。概要界面那一行只来自相遇地点 [pokemon_summary_screen.c:2665, 2799]；`modernFatefulEncounter` 是 Misc+0x08 的第 31 位 [include/pokemon.h:40-82]。

### 组合器中的 `initramscript`

`gift_composer.build_bound_script(actions)` 和 `build_mevent_npc_script(actions=...)` 把动作编译成 `initramscript` 所绑定的场地脚本。它没有阶段游标，每次都会整个重跑，所以只应发生一次的效果需要自己的 `SetVar` 或条件。

### 注册与校验

```python
from pokeldn.frlg.gift.gift_registry import GIFT_REGISTRY
GIFT_REGISTRY.register_definition(MEWTWO_GIFT)
```

注册时会校验并编译：卡片文本与标志、计划结构、动作范围、游标边界、印章唯一性、对战放置、指针以及 995 字节的 RAM 脚本上限，出错时会指出路径（`example-rally.event.slots[1].delivery.post_stages[0].actions[1]: ...`）。

## 静态工具

```bash
./.venv/bin/python -m pokeldn.frlg.gift.gift_to_bin --gift beast-cutscene --flag-id 1005 --out-dir exported-gift
./.venv/bin/python -m pokeldn.frlg.save.save_inject game.sav --gift beast-cutscene --flag-id 1005
```

`gift_to_bin` 会为 `pokemon-gen3-mysterygift-tool` 写出 336 字节的神秘卡片和 1004 字节的 RAM 脚本。`save_inject` 把两者写进活动槽位，修正卡片、RAM 脚本和扇区的校验和，并另存为 `<save>.gift.sav`（`--in-place` 会覆盖原文件；`--make-artifact` 会在 `artifacts/` 下写出一个 `.ram.lst` 清单）。

## 被封锁的路径

### 无线通信（JoySpot）

无线路径在 RFU 序列号闸门上被挡住：

| | 好友 | 无线通信 |
|---|---|---|
| 监听函数 | `Task_ListenForCompatiblePartners` [union_room.c:3757] | `Task_ListenForWonderDistributor` [union_room.c:3799] |
| 接受的 RFU 序列号 | `{0x0002, 0x7F7D}` | 仅 `== 0x7F7D` [link_rfu_3.c:920] |
| 选择 | 玩家从列表中选择 | 自动连接 |
| 能否从 Switch 到达 | 可以 | 不行 |

`Task_CardOrNewsOverWireless` [union_room.c:2415] 只在候选 0 的 `serialNo` 为 `0x7F7D` 时保留它，然后检查生成状态、`hasCard` 位（失败时为 SE_BOO）并重连。Switch 桥报告的是 `0x0002`，而广播里没有序列号字段；`svc_47` [sloopsvc.c:34] 接收 24 字节且不含序列号。一条原生广播：

```
50 10 | c1 cc bf bf c8 ff 00 00 | 65 ac | 00 00 00 00 | 84 15 | 00 00 00 00 00 00
TID   | uname                   | parent| unexplained | search| unexplained
```

`record[16:18]` 处的搜索字是 `activity:7 | bit7 | version:3 | language:3 | hasCard?:1 | startedActivity:1`。

试过的每一种广播变体（scene id、应用版本、在每个空闲偏移放 `0x7F7D`、活动号、`hasCard`、第 7 位）都没能从无线路径换来一次认证。未测试：`local_communication_id`、暴力枚举 scene、各种组合。

### e-Reader 本身

训练家之塔的 e-Reader 套件走 GBA 串行链路（`ereader_screen.c`）上的 `LINKTYPE_EREADER_FRLG`，不走无线适配器。

### 极光票与神秘票

Switch 版在首次进入名人堂时就会给出两张票及它们的 `FLAG_RECEIVED_*` 标志 [post_battle_event_funcs.c:52, `REVISION >= 0xA`]，所以此后的票据卡片不再给任何东西。卡片的 `iconSpecies` 若不是 `SPECIES_NONE` 就会画一个图标；超过 `SPECIES_UNOWN_B - 1` 则画问号 [mystery_gift_show_card.c:466, pokemon_icon.c:1102]。古代海图仅限绿宝石 [mystery_gift.c:30]。

## 陷阱

- `charmap.encode` 会丢弃未知字符，换行符也在内。换行是 0xFE；`mg_server` 拒绝第三行，或宽度超过 31 个字符的行 [strings.c:1291]（窗口 28 格宽 4 格高，[mystery_gift_menu.c:97,524]）。
- 新的载荷要同时加进 `buffer_script.py` 的 `DUMP_SCRIPTS` 和 `DECODED_SCRIPTS`，以及启动器的 `--dump-file` 行。
