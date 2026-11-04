---
title: 模拟神秘礼物
---
# 模拟神秘礼物

模拟神秘礼物会把一只官方礼物宝可梦带给一款无法通过本地无线接收神秘礼物卡片的游戏：游戏的交换 Host
以收到该礼物的训练家的身份提供一份全新的合法副本，主机的玩家则交换一只宝可梦回去，这只宝可梦会进入
Received。指定接收者的礼物会为主机自己的存档生成（[为接收玩家而生成](#made-for-the-receiving-player)）。

| 游戏 | 工具 | 对应的 Host | 提供标志 |
|---|---|---|---|
| Let's Go | `lgpe-gift-host` | Trade (Host)，`bin/lgpe_host.py` | `--offer` |
| 晶灿钻石/明亮珍珠 | `bdsp-gift-host` | Trade (Host)，`bin/bdsp_host.py` | `--offer` |
| 传说 阿尔宙斯 | `pla-gift-host` | Trade (Host)，`bin/pla_host.py` | `--trade-box-record` |
| 朱/紫 | `sv-gift-host` | Trade (Host)，`bin/sv_host.py`（[为主机承载](sv.md#hosting-for-a-console)） | `--trade-offer` |
| 传说 Z-A | `za-gift-host` | Trade (Host)，`bin/za_host.py` | `--trade-offer` |

每个工具都是其游戏中的 Trade (Host)，按交换顺序最多六只活动宝可梦（`catalog.simulated_gift`）；
Host 在多次交换之间保持会话。

## 礼物

PKHeX.Core 内嵌了其合法性检查所知的每一个分发内容，每款游戏一张表；不会下载任何东西。PKHeX 服务的
`gift_events` 会列出某张表中的宝可梦卡片（不含蛋和道具卡），按
`EncounterServerDate.GetDistributionWindow` 从新到旧排列，无日期的卡片排在最后。PKHeX.Core 26.10.18
中有：

| 游戏 | 表 | 礼物宝可梦 | 开放时间 | HOME 的 | Your OT |
|---|---|---:|---|---|---:|
| Let's Go | `MGDB_G7GG` | 15 | 无日期，但 HOME 的美录坦除外（2025 年 2 月 11 日） | 美录坦（9028） | 3 |
| 晶灿钻石/明亮珍珠 | `MGDB_G8B` | 9 | 2022 年 5 月 18 日到 2025 年 1 月 27 日，5 张无日期 | 草苗龟、小火焰猴、波加曼（9015 到 9017）、玛纳霏（9026） | 3 |
| 传说 阿尔宙斯 | `MGDB_G8A` | 11 | 2022 年 1 月 27 日到 2025 年 1 月 27 日 | 木木枭、火球鼠、水水獭（9018 到 9020）、眷恋云（9027） | 3 |
| 朱/紫 | `MGDB_G9` | 106 | 2022 年 11 月 17 日到 2026 年 6 月 5 日 | 新叶喵、呆火鳄、润水鸭（9021 到 9023）、美洛耶塔（9024）、烈咬陆鲨（9035） | 29 |
| 传说 Z-A | `MGDB_G9A` | 9 | 2025 年 10 月 14 日到 2026 年 8 月 28 日 | 菊草叶、暖暖猪、小锯鳄（9031 到 9033）、波尔凯尼恩（9034） | 5 |

礼物的键是 `card-species-form`，在朱/紫中还要加上太晶属性（`0503-964-0-10` 是 Gavin 的海豚侠）。
朱/紫的卡片 1521 包含十八只梦幻，每种太晶属性一只。

工具会按设置中的训练家收到它时的样子列出每个礼物（PKHeX 的 `ConvertToPKM`）：卡片固定了 OT 和语言时
用卡片的，否则用 Your OT，并带上等级、太晶属性、是否闪光、携带道具和开放日期
（[神秘礼物 - 模拟](gui.md#mystery-gift---simulated)）。如果一张 Your OT 卡片从未在设置中训练家的
语言下发放过，则列为非法。

### 卡片发放到过的存档

Your OT 副本把接收的存档作为其 OT，因此它必须是卡片发放到过的存档。`gift_event` 会以 `refused` 回复
并给出原因，允许时原因为空（`services/pkhex/Program.cs`）：

- 语言：副本使用存档的语言。如果卡片固定了另一种语言，则由 PKHeX 的 `CanHaveLanguage` 决定
  （`InTrainerLanguage`）。
- 版本：在 `"only_version"` 下，卡片会拒绝它从未发放到的版本（`ReachedVersion`）。HOME 的卡片
  （9000 起）发放到了任一版本；另一张固定了来源的卡片只发放到该版本；否则由 `RestrictVersion`
  （Let's Go 的 `IRestrictVersion`）决定。

自带训练家的卡片永远不会被拒绝：它的副本是交换来的宝可梦。在 PKHeX.Core 26.10.18 中，唯一被拒绝的
Your OT 卡片是 Let's Go 的美录坦和美录梅塔（1501、1502），它们仅在简体中文下合法
（`WB7.IsMainlandChinaGift`）。

### HOME 的礼物

PKHeX 的 HOME 卡片重建了 HOME 所发放的内容：

| OT | 图鉴 | 卡片 | 为接收玩家而生成 |
|---|---|---|---|
| HOME | "Simulated HOME" | Let's Go 的美录坦（9028）、玛纳霏（9026）、眷恋云（9027）、美洛耶塔（9024）、波尔凯尼恩（9034） | 否：按生成的样子发出 |
| 接收训练家的 | "Simulated (Trainer)" | 草苗龟、小火焰猴、波加曼（9015 到 9017）；木木枭、火球鼠、水水獭（9018 到 9020） | 是 |
| 接收训练家的，带经手人 | "Simulated (Trainer)" | 新叶喵、呆火鳄、润水鸭（9021 到 9023）；菊草叶、暖暖猪、小锯鳄（9031 到 9033） | 否：随设置中的训练家发出 |
| PJCS26，日文 | "Simulated PJCS26" | 朱/紫的烈咬陆鲨（9035） | 否：按生成的样子发出 |

在 Let's Go 之外，HOME 礼物带有 HOME 追踪码，由 [HOME 追踪码设置](gui.md#the-home-tracker-setting)
设置：`empty` 下没有（这是 PKHeX 唯一的抱怨，会被接受），`made` 下为生成的追踪码（Pokemon HOME
会拒绝它）。每个回复都会指明它（`home_tracker`）；列表用琥珀色描出这类礼物，Host 会继承该设置
（`POKELDN_HOME_TRACKER`）。

有两个 HOME 礼物需要在 `services/pkhex/Program.cs` 中修正：

- Let's Go 的美录坦（9028）保留 HOME 的身高和体重（`WB7.IsHeightWeightFixed`、`ResetSizes`）。
- 传说 Z-A 的菊草叶、暖暖猪和小锯鳄（9031 到 9033）获得 HOME 的个体值，三项满值，其余为 20
  （`WA9.HomeBaseIV`、`SetHomeIVs`）。

## 交换所提供的副本

`gift_event` 会为设置中的训练家在该游戏的每个版本上生成一份全新副本，直到有一份合法。按原样非法的
副本会得到经手人 POKELDN。招式从不重新适配，被拒绝的 PID 会在每个版本上最多重掷八次。Host 会以提供
的形式再次检查副本；New PID each run 会在卡片会掷出 PID 的地方给出新的 PID 和加密常数。每个礼物在
两种 HOME 追踪码设置下都能通过（`tests/test_pokemon_service.py`）。

主机收到：

- 卡片固定了训练家和语言时，用卡片自己的训练家和语言；
- 否则用主机自己的存档作为训练家（[为接收玩家而生成](#made-for-the-receiving-player)），若关闭该选项
  则用设置中的训练家；
- 使用卡片的或设置中的训练家时，以主机的玩家作为经手人。

## 为接收玩家而生成

`--for-receiver`（应用中默认开启）会在交换期间为主机自己的存档生成一份 Your OT 礼物。自带训练家的
礼物按生成的样子发出。只有在带经手人时才合法的礼物（`handled`：HOME 的新叶喵、呆火鳄、润水鸭、
菊草叶、暖暖猪、小锯鳄）随设置中的训练家发出，因为接收自己 OT 的存档会清除经手人，PKHeX 随后会拒绝它
（[交换会改写什么](sv.md#what-a-trade-rewrites)）。应用把每个提供以 `--gift-event KEY` 传入
（`command._args`）。

启动时，Host 以探测训练家 `receiver_gift.PROBE` 向 `gift_event` 询问该卡片，由此得知卡片是否指定
接收者（`your_ot`），并启动服务。五个 Host 共享 `pokeldn.receiver_gift`，其中的 `ReceiverGift` 站在
在线伙伴的位置上（[在启动器中](online.md#in-a-launcher)）。

### 这是谁的存档

当存档自己捕获了这只宝可梦时，所提供的宝可梦会指明该存档：初训家（经手人为 0）、属于该游戏的某个
版本、不是蛋。它给出 OT 名称、16 位 TID 和 SID、性别、语言和版本（`receiver_gift.own_trainer`），在
工作线程上读取（`Service.owner`；朱/紫用 Python，`receiver_gift.sv_owner`）。

| 游戏 | Your OT 卡片 | 主机的提供 | 版本 |
|---|---|---|---|
| Let's Go | 美录坦（1501）、美录梅塔（1502），两者仅限简体中文存档；梦幻（2001） | 交换 r 中的 kind 2 + 2r，一个加密的 232 字节 PB7 | 42 皮卡丘、43 伊布 |
| 晶灿钻石/明亮珍珠 | HOME 的草苗龟、小火焰猴、波加曼（9015 到 9017） | 0x13，一个加密的 328 字节 PB8 | 48 晶灿钻石、49 明亮珍珠 |
| 传说 阿尔宙斯 | HOME 的木木枭、火球鼠、水水獭（9018 到 9020） | 选择器 4，一个加密的 376 字节 PA8 | 47 |
| 朱/紫 | 9 张卡片，其中包括梦幻（1521）和皮卡丘（1501） | `80 00 02 00` 的 348 字节主体（[交换消息携带的记录](sv.md#the-record-a-trade-message-carries)） | 50 朱、51 紫 |
| 传说 Z-A | 喷火龙（1607）、拉鲁拉丝（1601） | 354 字节的选择 | 52 |

否则，主机的会话会在任何宝可梦之前指明存档（`receiver_gift.hear`）：

| 游戏 | 主机的消息 | 指明的内容 |
|---|---|---|
| Let's Go | kind 1，存档的 MyStatus 块（[Kind 1](lgpe_session.md#the-games-messages-on-the-reliable-protocol)，`pb7.first_trainer`） | id 对、版本、性别、语言、名称 |
| 晶灿钻石/明亮珍珠 | 0x24 `TradeTranerData`，在交换开始时（[宝可梦](bdsp_trade.md#the-pokemon)，`room.traner_trainer`） | id 对、版本、语言、名称 |
| 传说 阿尔宙斯 | 其 0x81 数据交换记录，即存档的 MyStatus 块（[游戏的读取器](pla.md#the-games-reader-and-the-pre-handler-phase)，`data_exchange.read_trainer`） | id 对、版本、性别、语言、名称 |
| 朱/紫 | 其身份块的第 1 条记录，位于其站点索引的 0x81 端口（[记录](sv.md#the-records)，`sv_host.identity_chunk`，`reference.identity_trainer`） | id 对、版本、性别、语言、名称 |
| 传说 Z-A | 1400 身份（[游戏自身的交换](za.md#the-games-own-exchange)，`reference.identity_trainer`） | id 对、性别、语言、名称 |

晶灿钻石/明亮珍珠的会话从不指明性别（[模型](bdsp_protocol.md#the-model)）；所提供的宝可梦则会，作为
初训家，或作为游戏写在每只收到宝可梦上的经手人
（[主机对收到的宝可梦做了什么](bdsp_trade.md#what-the-console-does-to-a-received-pokemon)）。会话缺少的
字段，如果所提供的宝可梦的初训家（经手人 0）或经手人（经手人 1）与会话的名称和 id 对匹配，就取自该
宝可梦；否则取自设置。日志会指明每个这样的字段
（`[gift] the console's Pokemon ... cannot name the save`）。传说 阿尔宙斯和传说 Z-A 只有一个版本。
后续交换中提供的已捕获宝可梦优先于会话，副本会重新生成。

`gift_event` 只在存档所属的版本上生成卡片（`"only_version"`），并拒绝没有此类存档接收过的卡片
（[卡片发放到过的存档](#saves-a-card-reached)）。HOME 的草苗龟、小火焰猴和波加曼是晶灿钻石的。

### 交换

交换按在线交换的方式运行（[在线交换](online.md)）：

1. 主机先提供。
2. 如果宝可梦和会话都没有指明存档，礼物就随设置中的训练家发出；Host 会记录原因，并按每种原因各弹一次
   弹窗（[弹窗](gui.md#pop-ups)）。
3. `gift_event` 为该存档生成卡片，然后在工作线程上，副本通过 Host 的提供检查（`pokemon.prepare_offer`，
   在 HOME 追踪码设置下）及其加载器。
4. 副本在主机的提供之后上传，并保持到交换结束。
5. Host 在主机之后确认。

| 游戏 | 加载器 | 检查的内容 |
|---|---|---|
| Let's Go | `lgpe_host.boxed` | 一个加密的 232 字节盒子结构，其校验和与合理性字成立 |
| 晶灿钻石/明亮珍珠 | `bdsp.pokemon.build_from` | 加密的 PB8 |
| 传说 阿尔宙斯 | 交换盒子的 `box_offer` | 其编辑内容，然后 PKHeX 对加密记录的检查（`pokemon.validate`） |
| 朱/紫 | `trade.load_offer` | 交换消息携带的 348 字节主体 |
| 传说 Z-A | `za_host.gift_offer` | 一个能解密的 354 字节提供；礼物绝不会以坏蛋的形式发送 |

PKHeX 无法生成或未通过检查的副本，会按应用生成的样子发出；日志（`[gift] could not be made ...`）和
弹窗会指明存档与阶段（`receiver_gift.maker`）：

| 位置 | 原因文字 |
|---|---|
| 卡片 | 该存档不可能收到这张卡片：卡片 1502 只在简体中文下发放过，从未发放给英文存档 |
| PKHeX | PKHeX 从卡片 ... 生成了非法的 ...：其检查的发现 |
| 提供检查 | 副本未通过 Host 的提供检查：... |
| 加载器 | Host 无法发送副本：... |

朱/紫、传说 阿尔宙斯和传说 Z-A 为每台主机保留一个 `ReceiverGift`；Let's Go 和晶灿钻石/明亮珍珠只
承载一台主机。同一席位上的下一次交换会在前一次完成后立刻进行；最后一个礼物服务于之后的所有交换。

在这五款游戏的零售版主机上，无论主机提供的是捕获的还是交换来的宝可梦，礼物都会以存档自己的训练家
送达。交换回主机的礼物会以经手人 0 送达，就像存档自己捕获的一样
（[交换会改写什么](sv.md#what-a-trade-rewrites)）。

## 其他游戏

火红和叶绿通过自己的神秘礼物接收活动宝可梦（[活动宝可梦](frlg_gift.md#event-pokemon)）。剑和盾通过
本地无线接收真实卡片（[官方活动卡片](swsh_gift.md#official-event-cards)）。
