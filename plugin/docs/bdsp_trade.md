---
title: 联盟室交换
parent: 晶灿钻石与明亮珍珠
nav_order: 3
---

# BDSP 的交换

一场 BDSP 联盟室交换用五条消息在两个站点之间换一只宝可梦，然后跑一个写入存档的安全阶段。靠近与问候见
[游戏协议](bdsp_protocol.md)。地址均为 1.3.0 的 `main`。

## 消息序列

    NetDataTransitionData{transitionType: 18}     entering the trade
    NetDataTradeTranerData        32 B            who they are
    NetTradePokeData             328 B            the Pokemon
    NetDataTradePokeCheckOkData    1 B, value 1   "yours is fine"
    NetDataTradeReadyOkData        2 B            the last message before the exchange

每一条都用一个客户端自己的对应消息作答。主机的 check-ok 永远是 1；它从不通过这条消息拒绝一只宝可梦。

在本地无线下，主机只按存档的非法标记检查玩家自己选的那只（[重复检测](#duplicate-detection)）。
`SS_box_182`（「Un problème avec votre Pokémon rend tout échange impossible.」）会拒绝被标记的选择。
只有在 `UnionFrontDeskStateController.isGlobal` 被置位时才跑服务器校验：
`NetworkManager$$RequestValidateTrade` [0x02251cb0] 把每个 `CoreParam` 放进一条 0x148 字节的请求里
发出（`IlcaNetServerValidate.CheckRequestAutoAsync` [0x027318c0]）；回复的 `ValidateResultID` 为
None、InvalidData、SignatureError 或 ProcessError，后两种会弹出错误对话框。`SS_box_181` 拒绝对方
被标记的宝可梦。

## 交换状态机

`UnionTradeManager.currentState`（+0x80）是
`TradeFlowState {NONE 0, SELECT_WINDOW 1, SECURIY_TRADE 2, PLAY_DEMO 3, END 4}`。只有在
SELECT_WINDOW 才会取走一只宝可梦。ready-ok（0x21）在 SELECT_WINDOW 进入
`TradeSelectPokeModel$$ReciveReadyOk` [0x1c27d40]，在 SECURIY_TRADE 进入
`TradeSecurityController$$ReciveState`，其他状态下一律丢弃。

当自己与对方的 `tradeState`（0x21 的第二个字节）都为 2（`WAIT`）时，主机离开 SELECT_WINDOW，然后
发送自己 `tradeState` 为 0 的 0x21。只有对方的 0x21 才能把它推出去。

### 交换盒阶段，以及会重置一轮的消息

`BoxWindow.NetTradePhase`：

    None 0, WaitSave 1, PlayerSelecting 2, WaitSend 3, OtherPokeConfirm 4, WaitOtherDecide 5,
    LastConfirm 6, WaitTrading 7, Complete 8, WaitClose 9, CancelOther 10, Error 11

重置（`TradeSelectPokeModel$$ReciveReturnSelectPoke` [0x1c27f00]）清空双方的宝可梦和双方的交换状态；
从阶段 3 起，交换盒回到阶段 2 并显示 `SS_box_588`（「L'autre joueur a choisi d'annuler l'échange.」）。
收到 `NetDataReturnSelectData{1}` 就用 `{0}` 作答。

| 对方发来的消息 | 交换盒阶段 | 主机做什么 |
|---|---|---|
| check-ok（0x46） | 低于 6 | 记下对方的检查 |
| check-ok（0x46） | 6 `LastConfirm` 或更后 | 执行重置 |
| ready-ok（0x21），SELECT_WINDOW | 阶段 5 或更低 | 执行重置 |
| ready-ok（0x21），SELECT_WINDOW | 阶段 6 或更后 | 记下对方的状态；之后的副本被丢弃 |
| return-select（0x45），任一值 | 任意阶段，PLAY_DEMO 之外 | 执行重置 |

这个闩锁（+0x71，`<isLoadingBox>k__BackingField`；在 [0x1c342e4] 处清除，在 [0x1c3435c] 处置位）由
`Init`、`WaitBoxWindowComplete`、`Cancel`、`RecivePokeData` 和 `ReciveCancelData` 清除；它的 setter
[0x1c33040] 没有调用者。重置把 `UnionWork` +0x50（`boxState`）设为 6 `CANCEL_SELECT` [0x1c28030]，
由 `BoxWindow$$UpdateNetworkTrade` [0x2121628] 消费 [0x2121c64]。

当玩家退出（`onCancelSelect`，`b__54_5` 0x1c28620；发送在 [0x1c286a4]），主机会发出 `{1}` 并等待
一条新的 `NetTradePokeData`；对方的 `{0}` 不能把它放行。

- 每条主机的 check-ok 只应答一次；在 `LastConfirm` 之后才应答的副本会重置这一轮。接收方会丢弃已经
  投递过的可靠 id（`pokeldn.ldn.reliable5.Reassembler`）。
- 用 `45 0001 00` 应答 `45 0001 01`。替换的宝可梦发出之后、或主机重新挑选之后，绝不要再发 0x45：
  它会把这一轮抹掉。
- 在选择窗口里，主机最后一次确认之前的 0x21 等于取消。要在主机可能回到选择窗口之前停掉安全状态
  重发器。

## 安全阶段

`TradeStateModel` 掌管存档：

    NONE 0, INIT 1, WAIT 2, SEND_POKE 3, WAIT_POKE 4,
    SEND_READYOK 5, WAIT_READYOK 6, START_WRITE_SAVE 7, WRITEING_SAVE 8

在这个阶段，对方的宝可梦消息只触发下一步：主机用的是玩家在全屏界面上确认过的那只宝可梦，而
WAIT_POKE 绝不会在那次确认之前结束。

### 谁主导：更稀有的那只宝可梦

角色 PARENT 或 CHILD 在对方的宝可梦到达时确定（`TradeSecurityController$$CheckPokeRarity`
[0x1c25060]），依据每个物种的稀有度：

| 稀有度 | 物种 |
|---|---|
| 3 | 151、251、385、386、489、490、491、492、493（幻之宝可梦） |
| 2 | 150、249、250、382、383、384、483、484、487（封面传说宝可梦） |
| 1 | 144、145、146、243、244、245、377-381、480、481、482、485、486、488 |
| 0 | 其他 |

`Dpr.SubContents.Utils$$GetPokeRarityNum` [0x1cbe560] 遍历三个 `MonsNo[]` 列表（稀有度 3 在
0x1cbe614，2 在 0x1cbe698，1 在 0x1cbe71c，都没有时 0x1cbe730），由 `Utils$$.cctor` [0x1cbe9a0] 从
`global-metadata.dat` 的 `0x666aa6`、`0x666b06`、`0x667c39` 填充（静态字段 +0x78、+0x80、+0x88）。
更稀有的一方是 PARENT；平手时招募者是 PARENT。拿帝牙卢卡去换一台主机的梦幻，主机仍是 PARENT。

`TradeParentStateModel$$StateProc` [0x1c23350]，表 0x3d80f2f，与
`TradeSecurityController$$ReciveState` [0x1c24f10]，表 0x3d80f39，共同驱动它：

    2 WAIT            peer at WAIT                           -> 3
    3 SEND_POKE       send the Pokemon                       -> 4
    4 WAIT_POKE       peer Pokemon confirmed                 -> 5
    5 SEND_READYOK    PARENT sends its state; CHILD waits for a peer 5 or 6   -> 6
    6 WAIT_READYOK    one more peer message                  -> 7
    7 START_WRITE_SAVE, 8 WRITEING_SAVE

处于 SEND_READYOK 的 CHILD 主机会静默等待，所以把 WAIT_POKE 原样回显的客户端会把它卡死。
`room.mirror_trade_state` 用 SEND_READYOK 应答 WAIT_POKE，两种角色下都可行
（`tests/test_bdsp_trade_states.py` 在随机时延下对这两个函数都做了建模）。

每个可靠序列 id 只发一条消息：同一个 id 下的后续消息看起来像重传，会被丢弃。

## 完成的交换

主机的状态，然后是客户端的应答：

    their READY-OK {tradeState 2}  ->  the client's READY-OK
    INIT          ->  WAIT
    WAIT          ->  WAIT
    SEND_POKE     ->  SEND_POKE, and its Pokemon
    WAIT_POKE     ->  WAIT_POKE
    SEND_READYOK  ->  SEND_READYOK
    WAIT_READYOK  ->  SEND_READYOK

随后主机写入存档、播放动画，并且只发 `NetCharacterStateData`。客户端每秒重复一次自己的状态，但只到
主机的 SEND_READYOK 为止（`room.repeats_trade_state`）；此后的一条 0x21 会落进下一个选择窗口并重置
这一轮。站点不能在这个窗口里离开：掉线会让主机停在 `FirstSave` 与 `SecondSave` 之间
（[断线惩罚](#the-disconnect-penalty)）。

动画在 `tradeState` 6 之后约 2.7 s 开始，收到的宝可梦在约 18.6 s 出现，玩家在约 29 s 重新获得操作权。
完成的交换不发任何消息就结束；下一轮从主机的下一条 `NetTradePokeData` 开始。两种角色下交换都能在
一次关联中接续。

## 宝可梦

`NetTradePokeData` 携带 328 字节，是一个加密的 PB8，格式见[剑与盾页](swsh_protocol.md#the-pk8)
（`pokeldn/gen8.py`、`pokeldn/bdsp/pokemon.py`）。0x06 处的校验和无法发现区块顺序错误。

`NetDataTradeTranerData`（[分帧](bdsp_protocol.md#framing)）：

    0x00  26  tranerName, UTF-16LE, NUL-terminated
    0x1a   4  tranerId, the full 32-bit id, secret id in its high half
    0x1e   1  cassetVersion, the save's version (49)
    0x1f   1  langId, the save's language (3)

主机在任何宝可梦之前先发它；为接收玩家生成的礼物会读它（`room.traner_trainer`，
[为接收玩家而生成](gift_simulated.md#made-for-the-receiving-player)）。它不带性别。交换界面用它来
称呼对方；问候用的是 Pia 玩家名（[协议页](bdsp_protocol.md#the-name-in-the-greeting)）。名字终止符
之后的十个字节是堆残渣；`room.build_trade_traner` 照抄主机自己的那十个字节。

提供的宝可梦是一只真宝可梦，只是改动了具名字段（`pokemon.build_from`）。

## 主机对收到的宝可梦做什么

`TradeStateModel$$ReplacePoke` [0x1c29120] 把这只宝可梦的初训家性别、32 位 id 和初训家名字与接收方
存档比较（`CoreParam$$UpdateOwnerInfo` [0x2495920]）：

| 比较结果 | 效果 |
|---|---|
| 三者都相同 | 处理者标志被清除；名字与物种名不同时置位 `IsNicknamed`（0x08F 的第 7 位） |
| 否则 | 按存档设置处理者：名字 0x0A8、性别 0xC2、语言 0x0C3、`CurrentHandler` 0x0C4 = 1、亲密度 0x0C8 = 物种基础值、记忆字段清零 |

随后更新校验和。`ot_name` 和 0xC6 不动。GTS、游戏内交换和神秘礼物也用同样的方式写处理者。游戏里没有
宝可梦 HOME 的代码。

### 重复检测

`PokeDupeChecker`（1.3.0）会给重复的宝可梦打标记：解密后 PB8 第 0x52 字节的第 0 位，即 PKHeX 的
`PB8.IsDprIllegal`。被标记的宝可梦不能交换，标记也永远不会被清除。

这项检查（`UpdateIllegalFlagAll` [`0x01de5860`]）按顺序走一遍队伍、1 到 40 号盒子以及寄放屋，在存档
载入时和交换盒里每次挑选时运行；收到交换时什么也不跑。它覆盖非蛋的、且不是游戏内交换所得的晶灿钻石
与明亮珍珠宝可梦。当以下各项都与更早的一只相符时，较晚的那只被标记：

| 字段 | 取值函数 | PB8 偏移 |
|---|---|---|
| 加密常数 | `GetPersonalRnd` | 0x00 |
| PID | `GetColorRnd` | 0x1C |
| 训练家 id（TID16、SID16） | `GetID` | 0x0C |
| 性格 | `GetSeikaku` | 0x20 |
| 六项个体值 | `GetTalentHp` .. | 0x8C |

比较：`IsDuplicatedPokemonParam` [`0x01de62f0`]，对每只宝可梦 `CheckDuplicate` [`0x01de59d0`]；游戏内
交换判定 `IsLocalKoukanPokemonParam` [`0x01de66d0`]；极限特训检查
`UpdateIllegalSpecialTraining` [`0x01de6830`]；交换盒调用点 [`0x01c28310`]；置标函数
`CoreDataBlockA.set_dpr_illegal_flag` `0x027bb040`。

铁面忍者（291）与脱壳忍者（292）这一对永远不算重复。等级 99 或更低、且置了任何极限特训位的 BDSP
宝可梦也会被标记。

永远不要提供这样一条 BDSP 记录：它的加密常数、PID、训练家 id、性格和个体值全都与接收方存档里的某只
宝可梦相符。`bin/bdsp_host.py --fresh-pid` 会重新抽一个加密常数和 PID，异色状态保留。

## 断线惩罚

站点在 `FirstSave`（惩罚计数 30，并记录时间）与 `SecondSave`（计数 0）之间掉线，会让主机拒绝新的本地
交换，提示「vous ne pouvez pas faire d'echange en reseau pour le moment」
（`UnionFrontDeskStateController$$CheckPenarty` 0x1fcc400）。出现惩罚说明主机已经写了存档。

这个惩罚时钟（`UnionWork$$CheckDateTime` [0x1dd3e30]、`SetPenartyTime` [0x1dd32d0]；`FirstSave`
0x1cd4fc0、`SecondSave` 0x1cd5030）是一个不加权的和，`Year + Month + Day + Hour + Minute + Second`，
一旦超过记录的和 30 就解除。分钟或小时进位时，这个和会下降 58，所以在某个小时末段触发的惩罚可能持续
到第二天甚至更久。

不要为了解除它而改动主机的时钟或系统设置：BDSP 能检测到这种改动，并会锁住基于时间的功能一天。把时钟
往回调会让惩罚回来；只有 `SecondSave` 才能把计数清零。
