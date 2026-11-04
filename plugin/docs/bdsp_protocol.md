---
title: 游戏协议
parent: 晶灿钻石与明亮珍珠
nav_order: 2
---

# BDSP 自己的协议，以及控制一个角色

BDSP 在它的 Pia 载荷里跑一套带类型的消息协议。`TeamLumi/opendpr`（一份反编译的 C# 复刻）中的
`Dpr.NetworkUtils.NetDataParser` 列出了每一条消息：一个 `ANetData<T>`，用一字节的 `DataID` 包住一个
普通结构体 `T`。标注 1.3.0 main 的地址位于明亮珍珠的镜像中。

## 分帧

    0x0  1  data id
    0x1  2  payload length, big-endian
    0x3  .  the struct, little-endian, packed

`JoinData`（`byte, byte, byte, short, Vector3`）在线上是 17 字节。

`NetDataParser` 注册了 65 条消息，全部在 `pokeldn/bdsp/netdata.py` 中（由
`scripts/gen_bdsp_netdata.py` 生成）。源码里能确定 53 种布局；有十二种带 C# 的 string、数组或列表
（`netdata.OPAQUE`），靠二进制确定：载荷就是被 marshal 的结构体（`ANetData<T>.ConvertStructToBytes`
[main.bin 0x27bb0e0]），字符串与数组作为定长字段，长度由 `Il2CppTypeDefinitionSizes` 与
`fieldMarshaledSizes` 决定，由 `CodeRegistration.interopData` 中的 `marshalToNative` 写入
[1.3.0 main 0x4acd0c8]。抓到的载荷与之相符（`room.NATIVE_SIZES`、`room.MEASURED`）。

| id | 载荷 | 字节 | 布局 |
|---|---|---|---|
| 0x02 | `PosListData` | 72 | 12 个 `PosData`（ushort posX、ushort posZ、short rotY） |
| 0x13 | `TradePokeData` | 328 | 一个按存档尺寸的加密 PB8 |
| 0x14 | `NetRecodeData` | 694 | `RECORD` 120、`RANDOM_SEED` 132、`TvRecodeData` 204、4 个 `TV_STR_DATA` 36、`RECORD_HEAD` 48、十个 int、六个字节 |
| 0x15 | `BallDecoData` | 143 | affixSealCount、Is3DEditMode、IsAppliedTemplate，然后是 20 个 `SealParam{short x, y, z; byte id}` |
| 0x18, 0x54 | `UgSecretBase` | 616 | short zoneID、posX、posY；byte direction、expansionStatus；int goodCount；30 个 `UgStoneStatue` 20；bool isEnable（4） |
| 0x22 | `StanbyListData` | 20 | 5 个 `StandbyData`（isAddPlayer、hostIndex、myIndex、langId） |
| 0x24 | `TradeTranerData` | 32 | 13 个 UTF-16 字符、uint tranerId、byte cassetVersion、byte langId |
| 0x29, 0x61 | `UgStationID_to_DigFossilIDList` | 8 | `byte DigFossilIDs[8]`，0..7 的一个排列 |
| 0x38 | `BattleMatchingPokeData` | 481 | 一个 328 字节的 PB8、20 个 7 字节的 `SealParam`、uint attachPokemonId、uint attachPersonalRnd、byte index、num、is3DEditMode、isAppliedTemplate、affixSealCount |
| 0x42 | `NetPlayerName` | 28 | 13 个 UTF-16 字符、byte genderid、byte languageId |

`SendStandbyPlayerData` [1.3.0 main 0x01e52fa0] 用 `unionMatchWaitDataList` 填充 0x22；空列表是二十个
零字节。站点用 `NetDataStandbyWaitData` 把自己加进去（0x59，同样四个字节，`isAddPlayer = 0` 表示
移除）：发出 `59 0004 01 00 01 03` 之后，下一条 0x22 是 `22 0014 01 00 01 03` 加十六个零。屏幕不会有
变化。

marshal 过程不清空缓冲区：定长字段在它的值之后带着堆残渣（[交换页](bdsp_trade.md)）。

## 空口上出现过什么

独占房间的主机发送 `NetJoinData`（0x01，可靠，17 字节）、`NetPosData`（0x02，不可靠，72）、
`NetRequestData`（0x12，1）和 `NetDataIsMatchWaitData`（0x23，可靠，1）。收到请求时它还会发 0x09 和
0x22；有活动时发 0x14 和 0x15。交换消息见[交换页](bdsp_trade.md)。一条 0x23 可能藏在一个存在字节
0x00 之后；走一遍消息时必须把 0x00 也当作一条消息（[消息分帧](pia.md#message-framing)）。

## 主机会重复发送的消息

`NetJoinData` 就是 `JoinData` 的全部：

| 偏移 | 大小 | 字段 |
|---|---|---|
| 0x00 | 1 | `avatarId`（[模型](#the-model)） |
| 0x01 | 1 | `colorId`，0 |
| 0x02 | 1 | `cassetVersion`，0x31 |
| 0x03 | 2 | `InitRotY`，度，小端，非对齐 |
| 0x05 | 12 | `InitPos`，三个小端 float，x、y、z |

`NetRequestData` 是一字节，即想要的 id。主机会反复请求 0x23，直到客户端确认它的可靠窗口；它创建一个
角色时会请求 `NetCharacterStateData`（0x04）：一条 0x04 请求意味着角色已经存在，`bin/bdsp_connect.py`
把它当作判定依据打印出来。

`UnionRoomManager$$SetNetData` [1.3.0 main 0x01e50700] 应答六个 id 的请求，其余忽略：

| 请求 | 主机发送 |
|---|---|
| 0x01 `NetJoinData` | 它的加入记录 |
| 0x04 `NetCharacterStateData` | 它的角色状态 |
| 0x09 `NetDataBattleTypeData` | 它的对战规则 |
| 0x13 `NetTradePokeData` | 它提供的宝可梦；没有选中时什么也不发 |
| 0x22 `NetDataStandbyWaitListData` | 它的待机列表 |
| 0x23 `NetDataIsMatchWaitData` | 它是否在等待匹配 |

应答走可靠流，在 30 到 130 ms 内到达房间里已有角色的站点。

### 压缩

可靠头部的标志 0x10 表示整个游戏消息（含头部）是一条 zlib 流。`ReliableSlidingWindow` 的 push
[1.3.0 main `0x15a10d0`] 在窗口的开关（+0x7ac）打开时做 deflate，结果没有变小时就发原文
（`0x159a5b0`）。产生的字节等于 Python 的 `zlib.compressobj(5, zlib.DEFLATED, 12, 5)` 加一次 sync
flush 再 finish。加入消息发原文；记录（0x14）、球壳（0x15）和全零的 0x22 会变小。`bin/bdsp_connect.py`
按这个标志决定是否解压。

### 其余不透明消息的发送方

| id | 类 | 发送方 |
|---|---|---|
| 0x14 | `NetDataRecodeData` | `RecodeMatching$$SendRecodeData`、`UnionStateController$$SendRecodeData` |
| 0x15 | `NetDataAttachSealNetData` | `BallDecoMatching$$SendBallDecoData` |
| 0x18 | `NetSecretBaseData` | `UgNetworkManager$$SendMySecretBaseData`；按请求发送 |
| 0x61 | `NetDigTableData` | 按请求发送 |
| 0x38 | `NetDataBattleMatchingSelectPokemon` | `BattleMatchingManager$$SendSelectPokemonData` |
| 0x42 | `NetPlayerNameData` | `UgNetworkManager$$SendOnJoinNewPlayer`、`SendPlayerNameData` |
| 0x54 | `NetSecretBaseUpdate` | 没有可靠的发送方 |

### 不可靠流

| 字节 | 消息 |
|---|---|
| `04 0002 00 00` | `NetCharacterStateData{NONE, 0}`，每两秒一次 |
| `12 0001 04` | 请求 0x04 的 `NetRequestData` |
| `02 0048 <72 B>` | 角色行走时的 `NetPosData` |

`room.build_state()` 和 `room.build_match_wait(False)` 构造状态与 0x23 的应答。主机会每秒重传一条可靠
消息五次，直到被确认；比它最后一个序列还多出两个的确认会被忽略。

## 发送游戏会照做的消息

可靠序列 id 与主机自己的发送共享；低于已确认 id 的消息会被静默丢弃。每次发送前立刻读取该 id。一台
零售明亮珍珠会照做落在它自己最后一条消息那个 id 下的回复，而丢掉 id 更低的回复：在它的状态消息（27）
和它的宝可梦（28）之后，一条 27 之下的回归宝可梦被确认了，却从未被检查。落在已确认序列上的加入会被
照做；`--room-pattern fixed` 在第一条 0x04 请求处停止，`--join-wait` 以秒为间隔（默认 1.0）。

`UnionOpcManager` 在每次加入时调用 `CreateCharacter(joinData)`：四十次加入就是四十次登场。背后没有
会话的角色会跟着玩家跨地图，直到游戏重启。`OpcManager$$RemoveCharacter` [0x02279ee4] 接收一个站点
索引。

## 角色记录

`OpcManager.CharaData` 是
`{int stationIndex, string assetName, int colorId, int avatarId, int sexId, int cassetVersion}`，以站点
为键。

### 模型

    NetJoinData.avatarId  ->  CreateCharaData  ->  CharaData.avatarId
                          ->  UnionCharacterTable.SheetSheet1{ID, AssetName}
                          ->  OpLoadCharacter("persons/field/" + assetName)

`CreateCharaData` [1.3.0 main 0x022796b0] 设置 `sexId = avatarId > 7 && avatarId != 16`：8 到 15 是
女孩，0 到 7 和 16 是男孩。8 是女孩，0 是戴蓝帽子的男孩（`--join-avatar N`）。

主机自己的加入携带 work 360（`GetAvaterId` [0x01e54030]）。新存档里是 0。外观计数器
（`ev_union_character_select_*`）对男孩存 16 或 1 到 7，对女孩存 8 到 15；否则，在 work 360 为 0 时，
`ev_traner_other_see_random` 把它设成 1 + 一个小于 16 的随机值，性别随机。所以只有当这个计数器被用过
之后，加入消息才会带上存档的性别。

`NetDataTranerCardData`（0x05，75 字节）在联盟室里什么也不绘制。

### 状态字节

`StateData` 是 `{byte state, byte isRecruiment}`，`state` 是一个 `OpcState.OnlineState`：

| 值 | 名称 | 值 | 名称 |
|---|---|---|---|
| 0 | `NONE` | 5 | `RECRUITMENT_RECORD` |
| 1 | `DIG_FOSILL` | 6 | `RECRUITMENT_GREETINGS` |
| 2 | `SECRETBASE_ACTION` | 7 | `RECRUITMENT_BALL_DECORATION` |
| 3 | `RECRUITMENT_BATTLE` | 8 | `COMMUNICATE` |
| 4 | `RECRUITMENT_TRADE` | | |

17 到 21 是 `NOW_*` 状态（[transitionType 表](#talkstate-and-the-value-that-crashes-the-game)）。
`RECRUITMENT_*` 的值会竖起一个对话气泡：`StateData{RECRUITMENT_TRADE, 1}` 显示交换气泡。

收到的 0x04 到达 `UnionOpcController$$SetNetData` [1.3.0 main 0x01e48c50]（站点没有角色时被丢弃），
它设置状态，按 `isRecruiment` 选主持表情或普通表情，并在状态非零时播放动画 0。远端角色的状态只会在
它自己的站点发来 0x04 时、或它被移除时改变。在该角色的 `Start` 运行之前，setter 会丢掉这个值
[0x02277c50]，而 0x04 请求在它之前就发出去了 [0x01e49854]：所以要像主机那样每两秒重发一次状态。

`OnlinePlayerCharacter$$IsCanTalkState` [0x02277af0]：状态 1、3 到 8、17 到 21 可以搭话。

### 行走

主机自己的 `NetPosData` 每 0.410 s 一次，跨 0.935 单位（`room.POS_PERIOD`、`room.POS_STRIDE`）。
`pos = (-posX * 0.05, posZ * 0.05)`。远端角色会与墙碰撞；玩家不会与它碰撞。`--room-walk-steps 8`
会留在房间内；交换不需要走动（`--room-walk-steps 0`，交换路径的默认值）。

## 被搭话

挂着表情的玩家会停在原地等人靠近，状态非零时按 A 什么也不做。交换表情是
`NetCharacterStateData{4, 1}`，用 `{0, 0}` 清除。用 `isRecruiment` 做闸门：状态 18 是已经进入交换的
主机。

搭话是 `NetDataTalkReserveData`（0x63），`63 00 01 00`（`bin/bdsp_connect.py --initiate-talk`；
`bin/bdsp_host.py --approach-delay`）。主机靠近客户端时：

    cli ->  64 0003 00 01 04      NetDataTalkReserveResultData{IsCanTalk, IsRecruitment, emoticonStateType}
    con ->  06 0005 00 01000000   NetDataTalkData{talkOpcSexId: 0, talkState: GREETING}
    con ->  10 0002 01 04         NetDataTalkCancelEndData{IsRecruitment: 1, emoticonStateType: 4}

没有 0x64，玩家就一直僵着。`IsCanTalk` 为 0 会跑问候并把它停在「one second!」上；为 1 则显示
「sorry, I have other plans」。丢掉该站点会释放被停住的问候。

### 主机主动靠近

`UnionRoomManager$$MyUpdate` [1.3.0 main 0x01e49fb0] 只在玩家状态为 0、没有对话或窗口打开、且玩家
在所有 `EnterCollision` 之外时才处理 A 键。对 10.0 单位内最近的角色：

| 角色的状态 | A 键做什么 |
|---|---|
| 0、2、9 到 16 | 什么也不做 |
| 8、17 到 21 | `StartTalk(opc, 0, 0, 0)` [0x01e4c2d0] |
| 4 | `CheckErrorMessageTrade`，然后同最后一行 |
| 7 | `CheckBallDeco`，然后同最后一行 |
| 1、3、5、6 | 发送 0x63，把状态存进 `nowTalkReserveState`（+0x188），`CreateSelectStateModel(state, 1)` |

主机读到 0x64 时 [0x01e50dec]，除非 `emoticonStateType` 等于 `nowTalkReserveState`（那就把它清掉），
否则发送 `NetDataTalkCancelEndData{0, 0}`；所以一个对外宣称 `{4, 1}` 的角色会用 `64 0003 00 01 04`
作答，每条 0x63 一次，忽略重传的副本。

当主机是搭话的一方时，客户端的角色就是招募者。招募者的「是」是 `NetDataTransitionData{18, 0}`，即
`07 0002 12 00`（[交换页](bdsp_trade.md#the-message-sequence)）。在 0x64 之后发送它，会在搭话的主机上
开始交换，而无需它自己的玩家点「是」（`SwitchTransitionMessage` [0x01e53bf0] -> `TransitionTradePoke`
[0x01e5c1c0]）：主机会发出它的 0x24 并打开交换盒。`SwitchTransitionMessage` 读取该类型的模型时没有
空指针检查；若一条 0x07 发给自进入以来没在交换招募者上按过 A 的主机，就会穿过空指针读取。

### 问候里的名字

问候用角色所在站点的 Pia 玩家名来称呼它（`NetworkManager$$GetGamerData` [1.3.0 main 0x02250e50]），
从 PlayerInfo 按 UTF-8 解码。当名字为空、被 `CheckNgWords` 标记、或按 UTF-16 单元超过该语言的上限时，
`Utils$$CheckNGTrainerName` [0x01cbdc30] 会替换成一个版本名：

| `lang` | 上限 |
|---|---|
| 1、8、9、10 | 6 |
| 任何其他正值 | 12 |
| 0 或以下 | 由界面的当前语言决定 |

PlayerInfo 是 195 字节（解析器 [0x0154f044..0x0154f5e0]）：

| 偏移 | 字段 |
|---|---|
| 0x00 | 名字编码：2 表示 20 个 UTF-16 单元，其他值为 80 字节 |
| 0x01..0x50 | 名字 |
| 0x51 | 第二个字符串的编码 |
| 0x52..0x79 | 第二个字符串，40 字节 |
| 0x7A | 语言，一个 `MsgLangId` |
| 0x7B..0xBA | 64 字节 |
| 0xBB..0xC2 | u64 |

    MsgLangId  JPN 1, USA 2, FRA 3, ITA 4, DEU 5, ESP 7, KOR 8, SCH 9, TCH 10

主机在 0x7A 处发送它的游戏文本语言（存档 `CONFIG.msg_lang_id`，`get_msgLangID` [0x0237e100]），以及它
检查过的名字，编码 1。站点协议的写入方把它放在那里 [0x01550e98]。`bin/bdsp_connect.py` 和
`bin/bdsp_host.py` 用 `pokeldn/bdsp/host.py` 的 `player_info` 构造 PlayerInfo 并发送 `--language`，
默认 3；桌面应用传的是自己的训练家语言。在 3 之下，11 个字符的名字会完整显示。在 1 之下，一台零售法版
明亮珍珠把 11 个字符的名字显示成「Perlo.」，问候是「Konnichiwa!」。

替换用的名字取决于被搭话角色 `NetJoinData` 的第 2 个字节：0x31 用 `dp_characters` 的第 247 号标签，
其他情况用第 206 号，再加一个句点：

| bundle | 0x31（明亮珍珠） | 其他值 |
|---|---|---|
| english | `Pearl.` | `Diamond.` |
| french | `Perlo.` | `Diamant.` |
| german | `Perl.` | `Diamant.` |
| italian | `Perl.` | `Diaman.` |
| spanish | `Perla.` | `Diamant.` |
| jpn, jpn_kanji | `パール.` | `ダイヤ.` |
| korean | `펄.` | `다이아몬드.` |
| simp_chinese | `帕尔.` | `戴亚.` |
| trad_chinese | `帕爾.` | `戴亞.` |

### talkState，以及会让游戏崩溃的那个值

`TalkState` 是 `{CHECK = 0, GREETING = 1, NONE = 2}`。CHECK 会让
`UnionStateController$$SwitchSpokenStateMine` 在没有空指针保护的情况下解引用 `msgWindow`
（0x1fd5ec0）；挂表情站着的玩家没有这个窗口，所以 CHECK 会让游戏崩溃。`pokeldn/bdsp/room.py` 拒绝
发送它。

`NetDataTransitionData{transitionType, isRecruitment}`（0x07）把停住的问候推进成一项活动。它是以尾调用
发出的，只扫 BL 指令的调用方扫描看不到它（[查找调用方](switch_re.md#finding-callers)）。
`SwitchTransition` [1.3.0 main 0x01e5ba70] 按它分发：

| transitionType | 活动 | 进入方式 | `UnionStateController` + 处的模型 |
|---|---|---|---|
| 3、17 | 对战 | `TransitionBattle` | 0x38 或 0x40，看 `isRecruiment` |
| 4、18 | 交换 | `TransitionTradePoke` | 0x50 |
| 5、19 | 记录混合 | `RecodeMatching$$Open` | 0x60 |
| 6、20 | 训练家卡片 | `TransitionShowTrainerCard` | 0x70 |
| 7、21 | 球壳 | `BallDecoMatching$$Open` | 0x80 |
| 8 到 16 | 无 | | |

`RecodeMatching$$Open` 和 `BallDecoMatching$$Open` 会立刻把主机自己的记录发出去然后等待；只有对方的
记录才会写入存档。

### 记录混合

主机用「Échanger des données」（状态 5）招募。自己的玩家点「是」之后，它发送
`NetDataTransitionData{5, 0}`，然后是 694 字节的 `NetDataRecodeData`（zlib），并停在状态 19 等待。没人
应答时，它约 44 s 后回到房间。`room.parse` 把记录的头作为 `recode` 返回：

    RECORD.record[30]        thirty uint counters indexed by RECORD_ID
    RANDOM_SEED              group_name (16 chars), name (32 chars), int sex, int region_code,
                             ulong seed, ulong random, long time_stmp (FILETIME), int user_id
    TvRecodeData             five TV records, each `bool isEmpty` (4 bytes), ints, a TV_STR_DATA
    4 x TV_STR_DATA          {16-char value, byte language, genderId, two reserved}
    RECORD_HEAD              13-char username, int language, byte sex, int body_type, uint uniqueID
    ten ints, six bytes      per-TV branch values, myVersion (0x31), five *IsNotEmpty flags

未写入的字段里是堆指针。`RECORD_HEAD.sex` 与 `RANDOM_SEED.sex` 可能不一致。

### 对战阶梯

一场对战（招募时状态为 3）走一段阶梯；招募的主机在每一级上都等加入方：

| 加入方发送 | 主机做什么 |
|---|---|
| `NetDataTalkData{GREETING}` | 显示「Un combat ? OK !」并等待 |
| `NetDataSelectData{0}`（0x08） | 显示「... est en train de choisir quoi faire...」并等待 |
| `NetDataBattleTypeData{0}`（0x09，Single） | 问它自己的玩家；点「是」后发送 `NetDataTransitionData{17, 0}` 并打开大厅 |
| `NetDataBattleMatchingJoin`（0x30）`{uint id, byte stationIndex, index, language, colorId, avatarId, sexId, cassetVersion}` | 用自己的加入消息作答并转发加入方的；加入方出现在第二个槽位 |
| `NetDataBattleMatchingReady`（0x32，空） | `NetDataBattleMatchingState{0, 6}`（0x33，`SelectBattleTeam`） |
| 什么也不发 | 在选好队伍时发六条 0x38，然后「en attente d'autres personnes」 |

每条 0x38 装一个加密 PB8（按顺序的已选队伍），残渣里的贴纸 `affixSealCount` 为 0，`index` 为 0 到 5，
`num` 为 6。没有找到对 0x30 `id` 的任何检查。`MatchingState`：None 0、Initialize 1、Load 2、
RecruitmentMember 3、SelectTeamMember 4、SelectRule 5、SelectBattleTeam 6、SelectPokemon 7、
GoBattle 8、Result 9、Resume 10、Closing 11、LeavedOtherMembers 12。

`NetDataSelectData`（0x08）是 `{byte index}`；它的接收方 [0x01e52a30] 忽略 index，把
`UnionStateController+0x38`（对战招募模型）驱动到 `BATTLE_RULE_SELECT_WAIT`，不管当前开着哪个对话，
也没有空指针检查。该模型只在玩家招募一场对战时才被设置，并且在每次进入联盟室时都是空的
（离开房间的各区域时 `UnionRoomManager` 会被销毁，`NetUseManager.OnZoneChange` [0x026cfef0]）。
按这种读法，向本次进入还没招募过对战的主机发 0x08 会写到地址 0x18 [0x023e2604]。一台从未招募过的
零售明亮珍珠在其交换盒上和训练家卡片交换时都确认了 `08 00 01 00`，屏幕没有变化；接收方究竟有没有运行
并不清楚。除非主机自己的 0x04 表明状态 3 且 `isRecruiment` 为 1，否则永远不要发 0x08。

### 地下大洞窟

地下在场景 id 12608 下广播同一个 `local_communication_id`；同一套会话代码就能关联，不需要加入记录
（`--room-walk 0`）。站点到来时 `UgNetworkManager` 发送：

| id | 类 | 字节 | 内容 |
|---|---|---|---|
| 0x17 | `NetZoneData` | 16 | `Vector3 pos`、`int zoneID` |
| 0x42 | `NetPlayerNameData` | 28 | 13 个 UTF-16 字符、byte genderid、byte languageId |
| 0x50 | `NetKousekiCount` | 4 | `int Value` |
| 0x41 | `NetSecretBaseInfo` | 16 | 在秘密基地内部代替 0x17：入口的 `Vector3 pos`、`int zoneID` |

一条指明玩家所在区域的 `NetUgJoinData`（0x16，18 字节：
`byte avatarId, colorId; short zoneID, InitRotY; Vector3 InitPos`）会把一个角色放到玩家旁边；主机会
请求它的 0x04 和 `NetNaminoriData`（0x55），并每 0.41 s 发一次 `NetPosData`
（`--ug-join --room-walk-steps N`）。

`UgNetworkManager$$OnReceiveRequestData` [1.3.0 main 0x01f7c050] 应答对 0x01、0x04、0x18、0x19、
0x54、0x55 和 0x61 的请求——前提是主机的窗口已经承载过东西：

| 请求 | 字节 | 内容 |
|---|---|---|
| 0x18、0x54 | 616 | 玩家自己的 `UgSecretBase`；其 `zoneID` 为 0 时什么也不发 |
| 0x61 `NetDigTableData` | 8 | 挖掘化石表，0..7 的一个排列，就绪之后才有 |

非主持的站点在加入时请求 0x61。`OnReceiveDigTableData` [0x01f7dad0] 在其表标志（+0xA8）为 0 期间
采纳第一条到达的 0x61，不看是哪个站点发的，也不做检查，重建挖掘点并置位标志；之后的都被忽略。
`CreateDigPoints` 用 `MyStationIndex` 索引该表，并不做空指针检查地查那个组 id：只发 0..7 的排列，
因为更大的字节会让主机出错。每个 `UgFieldManager` 会话都会新建一个 `UgNetworkManager`，所以每次都
重新采纳一张表。0x29 `NetDigGroupIdData` 既没有发送方也没有接收分支。

`bin/bdsp_connect.py --inject-file PATH` 会可靠地发送文件中每一行新的 `ID:HEX`。

### 球壳

主机用「Déco Capsule」（状态 7）招募。它发送 `NetDataTransitionData{7, 0}`，进入状态 21，然后发送
143 字节的 `NetDataAttachSealNetData`（zlib）。没人应答时，它约 45 s 后回到房间。若用 143 字节应答
（`bin/bdsp_connect.py --answer-with 0x15:FILE`），它会应用这些数据并回到房间。应答要从自己的任务里
发出：在接收方内部发时，它等待的确认永远读不到。

`BallDecoMatching$$ReceiveBallDecoData`（`0x021ca5e0`）写入 99 个球壳槽位中第一个没有贴纸的，若全都
有贴纸就什么也不写。`BallDecoWork$$CopyTradeCapsuleData`（`0x01f23eb0`）清空该槽位，并在存档里有现货时
把每个贴纸放到 `(x, y, z) / 100`，同时消耗掉它，否则丢弃。所有贴纸都放好时收尾消息是
`DLP_net_union_room_090`，否则是 `_114`。数量超过 20、或贴纸 id 为 200 及以上会抛异常。

位置是球壳半径的百分之一。3D 模式把每个贴纸画在它所在的位置。2D 模式只在网格单元的
`BallDecoWork$$Convert2DPosition`（`0x01f24da0`）处画贴纸：半径 1，正面（+z）行列间隔 28 度，背面
25 度，每个分量取整到 0.01。正面和背面的网格都是 7 × 7 的方格减去 `(|x|, |y|)` 属于
`{(3, 2), (2, 3), (3, 3)}` 的部分（`Capsule2DViewController$$Initialize` `0x01e909b0`，零售
1280 × 720 缩放）：

    row  3   columns -1..1
    row  2   columns -2..2
    row  1   columns -3..3
    row  0   columns -3..3
    row -1   columns -3..3
    row -2   columns -2..2
    row -3   columns -1..1

落在网格之外的 2D 设计会占用一个标记为已装饰的槽位，但什么也不画。
