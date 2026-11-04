---
title: 连接协议
parent: 火红与叶绿
nav_order: 1
---

# GBA 连接，以及其上运行的东西

本页讲火红／叶绿在 Pia 之上的链路层：RFU 帧、席位屏障、联盟室、对战与竞技场。引用均指向 [pret/pokefirered](https://github.com/pret/pokefirered)。

# RFU 链路层

## 每次父轮询只有一个子槽位

`RfuMain2_Parent` 每次轮询只保留一个子槽位，并检查其滚动的 `childSendCmdId` 标签是上一个 `+1 mod 8` [link_rfu_2.c:876-892]。标签不符会递增 `numChildRecvErrors[i]`；连续四次以上则调用 `RfuSetErrorParams` 并终止链路。一次轮询里出现第二个槽位就算丢了一个标签。子端若自由发送、或每次轮询发两个槽位，会在房间走位开始后 0.3 s 内被丢弃；每次轮询一个槽位时，每个标签都按序。这条规则在每个阶段都成立，席位走位也不例外。

## 父端表格的第一行是游戏主机自己的命令，被镜像回送

游戏主机发送期间的每一次卡顿都受这条规则支配。

`MGL_Send` 按 252 字节分块，在每个分块之前以及结束时都等待 `MGL_HasReceived(link->sendPlayerId)`（即自己的 id 1）[mystery_gift_link.c:176,205; mystery_gift_client.c:33]：它要等到自己的块经父端 `gRecvCmds` 的第一行完整回送，而这一行由主机镜像 [link_rfu_2.c:970,1125]。`HandleBlockSend` 一直扣住 INIT 直到被镜像，`SendLastBlock` 重复最后一个分片直到被镜像，随后把镜像位图中缺失的每个分片重新排队 [link_rfu_2.c:1366-1416]。

`rfu_leader.ChildEcho`：

- 从不丢弃一条不同的命令；丢掉一个分片就要重发整块，再丢一次就终止链路；
- 合并仍在等待中的重复（`SendLastBlock` 每帧重发）；镜像已经发出之后的重复才会被应答。

子端每收到一个父帧就发一条命令 [link_rfu_2.c:600]，因此镜像队列不会自行增长。

## 一步地格恰好是 16 次链路更新

`FacingHandler_DpadMovement` 置 `directionSequenceIndex = 16`，每次链路更新递减一次 [overworld.c:3432-3470]。按下 N 个方向键之后，脚本化行走的间隔还需要 `16 - (N mod 16)` 次更新。

## 玩家的输入并不总是被发送

当 `GetLinkSendQueueLength() > 1` 时，`UpdateHeldKeyCode` 把 EMPTY、方向键码、START 与 A 改写成 `LINK_KEY_CODE_NULL` [overworld.c:2786-2810]。`LINK_KEY_CODE_READY`（0x16）不受影响：要以 0x16 为准，绝不要以方向键码缺席为准。

## 席位是一道相互屏障

`Task_EnterCableClubSeat` 调用 `SetInCableClubSeat()`（下一次按键发出的是 READY），并在 `GetCableClubPartnersReady()` 上自旋 [cable_club.c:827-869]，只有每个玩家都为 READY 时才为真 [overworld.c:2988-2999]。随后 `Task_StartWirelessTrade` 运行 `SetLinkStandbyCallback()` [cable_club.c:910-943]。只在双方都为 READY 之后才驱动待机轮次；对处于 `CABLE_SEAT_WAITING` 的游戏主机驱动它们，会让其席位状态机出错。

## 真实的子端发出什么，端到端

一台法版零售火红子端；IDLE 计数取自一次交换：

```
IDLE x8
SEND_BLOCK_INIT w1=0x0011 x4   + 17 fragments      (LinkPlayer)
IDLE x31
SEND_BLOCK_INIT w1=0x0009 x4   + 9 fragments       (trainer card)
IDLE x262   READY_EXIT_STANDBY w1=0x0000 x1
IDLE x72    READY_EXIT_STANDBY w1=0x0001 x1
IDLE x45    <room: SEND_HELD_KEYS 0x1b x24, EMPTY, 0x1a once, the walk, READY, then EMPTY x13>
IDLE x22    READY_EXIT_STANDBY w1=0x0002 x1
IDLE x28    READY_EXIT_STANDBY w1=0x0003 x1
IDLE x75    -> the host pulls the party
```

- 每个待机轮次是一帧，由 Pia Reliable 重传直到落地。
- 轮次之间子端全零 IDLE。队伍交换之前，主端的静默帧计数器只在恰好空闲的槽位上推进；发一个 EMPTY 保活会让它死锁。
- `LINK_KEY_CODE_IDLE`（0x1a）把对端的链路状态置为 IDLE [overworld.c:2755]；只有处于该状态的玩家才会运行地格脚本。

## 双方只有在听到对方之后才前进

只有当某个 `gRecvCmds` 条目非零时，`CB1_UpdateLinkState` 才运行 `UpdateAllLinkPlayers` [link_rfu_2.c:787-800]；循环最终稳定为每个往返一次交换。主机 `SEND_HELD_KEYS` 的高字节是 `heldKeyCount`，每条准备好的命令计一个。

## 席位之后的待机闸门与走出

双方坐下之后，游戏主机先把主机的计数反射回去，再在 mpId 0 上广播自己的 `READY_EXIT_STANDBY` count=2。它只在子端计数等于自己的计数时才接受 [link_rfu_2.c:1577-1591]。count=3 要以主机自己的 mp0 count=2 为闸门再发一次，间隔大于 `HostTradeTiming.entry_final_standby_quiet_frames`（75 个槽位，比子端 60 帧的重发更长 [link_rfu_2.c:1529]）。

走出：主机发出 `LINK_KEY_CODE_EXIT_ROOM`（0x17）并阻塞，直到每个玩家都为 EXITING_ROOM [overworld.c:2962-2981]；子端在按住键流上以自己的 0x17 应答。

## 离开房间

游戏主机走出交换中心时——无论坐下之前还是对战之后——都会发出按住键 0x17，并在 "Please wait" 上等待每个玩家 [overworld.c:2977]。主机在 `H_ENTRY_SEAT`、`H_RETURN_FIELD` 与各对战状态下以自己的 0x17 应答（`host_trade._child_send_held_keys`）。

### 静默闸门

当游戏主机已有 `QUIET_GATE_SECONDS`（0.25 s）什么都没发时，主机丢掉自己的重传，只保留每 `QUIET_RETRANSMIT_SECONDS`（1 s）一次（`tests/test_host_quiet_gate.py`）。

## 交换之后的取消

`BufferTradeParties` 在礼物缎带交换之后、菜单命令被读取之前清除已接收块标志 [trade.c:1549]，[1593-1633]，因此在其中完成的取消可能丢失。`bin/frlg_trade_join.py` 在选择「取消」之后，等主端的 `REQUEST_CANCEL` 到达时再补发一次 `REQUEST_CANCEL`（`0xEEAA`）（`trade.py`，`_on_linkcmd`）。跟随方在 YES 之后发出 `REQUEST_CANCEL`，随后空转直到 `BOTH_CANCEL_TRADE` [trade.c:2049, 1643]；主机对游戏主机的 `REQUEST_CANCEL` 立即应答。

## 单方取消会把双方送回菜单

`PLAYER_CANCEL_TRADE` / `PARTNER_CANCEL_TRADE` 回到 `CB_MAIN_MENU` [trade.c:2094-2113]；只有 `BOTH_CANCEL_TRADE` 结束会话 [1715-1722]。用 `PARTNER_CANCEL_TRADE` 应答 `REQUEST_CANCEL` 会让游戏主机在 "votre ami veut échanger des Pokémon" 上循环；`bin/frlg_trade_host.py` 改用 `BOTH_CANCEL_TRADE` 应答。主端自己的选择不发送任何内容 [trade.c:1811-1828]。先发出过 `READY_TO_TRADE` 的加入方，会在主端第一次取消时收到 `PLAYER_CANCEL_TRADE`；`bin/frlg_trade_join.py` 随后在菜单处取消。

## 链路上的版本与语言

`IsTryingToTradeAcrossVersionTooSoon` [union_room.c:1499] 只对既非火红也非叶绿的伙伴触发。`ConvertInternationalString` 对日文名字做特例；法版火红接受英文神秘卡片。联盟室搜索会跳过日文候选 [union_room.c:3726]；神秘礼物的 `Task_ListenForCompatiblePartners` 则不会。日文卡带使用另一套神秘卡片与神秘新闻的 activity 编号（[日文版式](frlg_rom_map.md#japanese-layout)），并把广播国际编号的主机排除在好友列表之外。要服务所有卡带的主机，只在 `--language japanese` 下才广播日文编号；应用会传入神秘礼物工具的语言，默认取设置中的训练家语言。在神秘礼物好友列表里，游戏主机在 GameData 中发出其 ROM 的游戏代码，主机据此在配送前选取该卡带的地址。

## 模拟器可以自行关闭链路

`HandleLinkConnection` 在 Switch 构建上调用 `svc_51` [link.c:1654]；返回非零即执行 `CloseLink()`，随后在神秘礼物下软复位或调用 `RfuReloadSave()` [link.c:1674]：Switch 错误 2318-0006。若崩溃而主机在 RFU 层面一切正常，问题就指向 LDN/Pia。

| SVC | 调用位置 | 作用 |
|---|---|---|
| `swi 0x45` | librfu_rfu.c:667,749 | 把 `gRfuLinkStatus` 交给模拟器 |
| `swi 0x49` | AgbRfu_LinkManager.c:657 | 非零期间，在 SEARCH_CHILD 中保持 `connect_period` 打开 |
| `swi 0x4a` | AgbRfu_LinkManager.c:720 | 同上，在 SEARCH_PARENT 中 |
| `swi 0x4b` | link_rfu_2.c:2114, union_room_player_avatar.c:518 | `SVC4B_EXIT_EARLY` 提前退出 SpawnGroupLeader；`SVC4B_RESEED_RNG` 用主机的训练家 id 重新播种 |
| `swi 0x51` | link.c:1654 | 立刻关闭链路（神秘礼物下软复位） |
| `swi 0x53` | wireless_communication_status_screen.c:328 | 由模拟器驱动退出状态画面 |

# 无线层，以及这款游戏如何用到它

## 广播的速率集

不含 6、9、12 Mbit/s 的关联响应，会让游戏主机在关联后 2.9 到 3.9 s、Pia 会话一完成就离开 LDN：76 次这类关联中有 42 次离开，而带这些速率的 284 次中 0 次。信标的请求速率集与游戏主机的请求速率集都无关紧要。游戏主机究竟需要其中哪几个速率尚不清楚。ESP32 softAP 携带全部十二个（[hardware_esp32.md](hardware_esp32.md)）。

主机广播 Switch 的速率集（1B 2B 5.5B 11B 6 9 12 18，扩展 24 36 48 54）。信标头部携带元素 0、1 与 3（41 字节）；Switch 的其它元素可选。带 WMM 的信标会让游戏主机发送 QoS 数据帧，其 TID 会进入 CCMP 的 nonce 与 AAD。在 privacy 能力下不含 RSN 的探测响应，会让游戏主机的关联请求得不到应答。`host_pia` 以单播发送类型 5 的 Update Session。

## 游戏主机作为 Pia 子端

- 游戏主机子端需要类型 2 的 Join Response：只有类型 5 时，它每 0.5 s 重发一次加入请求，并在加入后 3.05-3.20 s 离开。
- 主持神秘礼物的游戏主机在 50-66 ms 内以类型 5 应答游戏主机子端；它对 `bin/frlg_mg_client.py` 的应答没有类型 2，类型 5 要等到 2.0 s 之后，原因不明。主持交换的游戏主机在 34 ms 内发出类型 5 与类型 2。

一台主持神秘礼物的游戏主机对接收客户端，从其 Net 0x11 开始：

    0.000  Net 0x11 (once)
    0.006  client: Net 0x12 + Session join
    0.252  RTT request, then every 316ms
    2.038  Session type 5, no type 2
    2.040  client: type 6 (finalize); 2.159 reliable open
    4.63   host's own NI (the player's YES)
    6.82   SEND_PLAYER_IDS, 6.87 BLOCK_REQ
    8.15   Net 0x50 property update every ~0.5s, acked 0x51

## 离开 Pia 会话

游戏主机子端在发出 RFU 的 `D` 帧之后离开：先暂停，再发会话类型 3 的离开请求，然后是其 LDN 解除认证（原因码 3）。在没有类型 4 应答的情况下：

| 间隔 | 实测 |
|---|---|
| `D` 到第一个类型 3 | 1.97-2.02 s |
| 类型 3 到类型 3，共发四次 | 0.48-0.54 s |
| 第一个类型 3 到 LDN 离开 | 2.03-2.08 s |

    type 3, 22 bytes:  03 | random u32 | constant id (8) | variable id (2) | kind 0 | IPv4 | port
    type 4, 15 bytes:  04 | random u32 | the request's constant id and variable id

偏移在 GBA 应用的 `main` 中：`LeaveMeshJob` 在 `0xcacf4` 处发出该请求，期限 500 ms；`WaitLeaveResponse`（`0xcaf38`）在响应标志 `+0x99` 出现时结束，否则最多重发四次（`0xcb06c`..`0xcb08c`）。类型 4 的分支（`0xba028`，表 `0x180fc9`）为携带该站点自身 id 的 15 字节消息置起该标志。主机的类型 3 处理函数（`0xbf2d4`）接受 22 或 34 字节，并以请求的第 5 到 14 字节作为类型 4 应答（`0xbf454`..`0xbf4e4`）。`HostPeerProtocol` 对每个类型 3 都这样应答，单播，首部为 `(console variable, 0x00C6)`，按发往该游戏主机的单播计数器编号；编号低于该计数器的类型 4 会被忽略。游戏主机为每个目的地各保留一个计数器。

该暂停是一个固定的 120 tick 倒计时（每秒 60 tick，`0x4ff64`）。`TryDisconnectRfu` 与 `LinkRfu_Shutdown` 发出 `swi 0x44` [link_rfu_2.c:1446-1455, 625]；处理函数 `0x58b0c` 投递断开请求 1（`0x53d98` -> `0x4f0ec`，`+0x730`），tick `0x4ee34` 置 `+0x734 = 0x78`（`0x4ef00`），归零时调用槽位 `0x78`（`0x4ef60`），由 `Session::LeaveAsync`（`0xb1060`，来自 `0x537e0`）发出类型 3（[pia.md](pia.md)，离开会话）。收到任何东西都不会缩短它；只有请求 2 或 3（`swi 0x42`，或在 PID 0 下的 `swi 0x43`）或置起 `+0x277c` 的 Pia 错误才会。

## 802.11 行为

- 游戏主机作为站点：不省电，每个数据帧前发 RTS，离开时解除认证一次。
- Switch 作为主机时以 11M 发信标，以 48-54M 发数据。

## Pia 首部 nonce 是游戏主机会强制执行的计数器

游戏主机会丢弃 8 字节首部 nonce 不严格大于该信道上最后一次已接受值的任何数据报。`Sim._next_nonce` 与主机都会计数。

## 前向携带

每个可靠帧都会在随后的 4 个数据报中重复。空口丢包率为 1-2% 且成簇；一个空洞会扣住其后每个槽位直到它重传，而这次重传会把游戏主机 8 层深的 RFU 接收队列灌过其深度。没有前向携带时，丢一个槽位就会让游戏主机断开。主机按序号去重。

## 游戏主机的确认延迟是 512 ms 的节拍器

游戏主机的累积 ACK 在 CTRL 帧载荷中（`parse_bulk_ack`）；可靠首部的 `ack` 是发送方最低的待确认序号。每 16 或 17 个 512 ms 的槽位（与 LDN 加入相位锁定），游戏主机会停 50-70 ms，重传其最后几帧，随后其 ACK 一次跳过好几帧。负载之下，这次停顿会落在已经填满的发送窗口上。是哪个模拟器或 Pia/LDN 定时器驱动它，尚不清楚。

## ident-25 卡死：一个空洞加上无界积压

当空洞在一个无界积压之后闭合时，游戏主机一次性交付所有积压帧，其 8 层深的 RFU 队列丢掉 ident-25（`MG_LINKID_RAM_SCRIPT`）分片，链路仍在却停在 "Transmission..." 上。父块从未被反射，因此这次丢失在抓包里看不出来。`HostSession` 在有 `HOST_OUTSTANDING_MAX`（6）个未确认帧时扣住新帧，`--ram-script-block-repeat 3` 则把 ident 25 发三次。究竟是空口丢包还是游戏主机侧交接丢了分片，尚不清楚。

## 卡片之后的传输阶段崩溃

在确认停顿之后每 tick 重发每个未确认帧，会杀死会话。以下检查默认开启：

- `HOST_RTX_LIMIT` 限制每个 VBlank 的 Reliable 重传次数。
- `FRLG_ECHO_MAX` 限定子端块槽位的 FIFO 回显。
- 发送套接字是非阻塞的，`FRLG_QUIET_GATE_MS` 在游戏主机静默期间扣住重传（接受卡片之后约 0.5 s，是其闪存存档）。

## 扣在套接字与空口之间的数据报

主机的数据报在上空口之前被扣住 0.1-1.1 s，会让游戏显示 "erreur de connexion, rapprochez-vous" [link_rfu_2.c:2312, link.c:1521]。在 ESP32 板子上，测得的最长等待是 265 ms（[ESP32 无线](hardware_esp32.md)，TX_DONE）。

# 联盟室

## 进入列表：广播的 activity 字节

搜索中的游戏主机只在候选的 activity 位于其 link group 的接受列表里时才留下它 [`IsPartnerActivityAcceptable`，union_room.c:1590；src/data/union_room.h:398-456]。在联盟室中，游戏主机先搜索 `{ACTIVITY_SEARCH, 0xFF}`，再搜索 `IN_UNION_ROOM | activity`（`IN_UNION_ROOM = 1 << 6`）[union_room.c:2664]。记录的第 16 字节是 activity：21 会在神秘卡片画面上列出这台主机，22 则在神秘新闻上。

## 连接：必须恰好且仅为 IN_UNION_ROOM

`IsPartnerActivityIncompatible` 要求 `partner->activity == IN_UNION_ROOM` 严格相等 [link_rfu_2.c:2933]。0x44 会生成头像，但连接被拒（"le DRESSEUR est occupé"）；0x40 能连上，交换意图在链路建立之后再协商。

## 没有父端 NI，以及五帧规则

联盟室子端设置的是 TYPE_UNI 接收缓冲，从不设 TYPE_NI [link_rfu_2.c:2526, 533]。父端的 NI 体是致命的：它会以 ERR_RECV_BUFF_OVER 失败 [librfu_rfu.c:2300]，并以 "erreur de connexion" 结束 [link_rfu_2.c:2585]。`RFULeader(skip_parent_ni=True)`（`--union-room`）会跳过它。

游戏主机会在它第 5 个未应答的父帧上断开（`maxMFrame = 4` [link_rfu_2.c:128]）。`--union-room-keepalive N`（120 可用）会在 UNI 之前把第一个 NI_START 重现 N 个 VBlank。游戏主机随后还要等约八秒：只要 NI_START 仍待处理，`rfu_UNI_setSendData` 就以 ERR_SUBFRAME_SIZE 失败 [librfu_rfu.c:2262, 1449]，直到 `NI_failCounter_limit`，即最后一个 NI_START 之后 480 帧 [link_rfu_2.c:139, AgbRfu_LinkManager.c:1328]。

## 连上之后游戏主机做什么

链路建立后，游戏主机交换训练家卡片 [union_room.c:2858-2879]，并显示 Salut / Combat / Tchat / Retour。每个选择都发一个 `SEND_PACKET` 并等待 [union_room.c:3151]：

| 游戏主机发出 | activity | 主机的应答 |
|---|---|---|
| 0x48 | CARD（Salut） | 0x51 ACCEPT |
| 0x44 | TRADE（交易板） | 0x51 ACCEPT |
| 0x41 | BATTLE（Combat） | 0x51 ACCEPT |
| 0x45 | CHAT（Tchat） | 0x51 ACCEPT |
| 0x40 | EXIT（Retour） | 视为游戏主机主动关闭 |

每项活动之后双方都 `SetLinkStandbyCallback` [union_room.c:2995, :3012]。接受方以 `svc_CommsAllowedByParentalControls()` 为闸门 [union_room.c:3159, :3037]。Retour 先发 0x40，再发 READY_CLOSE_LINK，然后正常断开。

## 交易板

交易板读取记录的第 18 字节（`type << 2`）、第 19 字节（`gameClear | level << 1`，[广播记录](frlg_rom.md#the-advertisement-record)）以及 22:24 处的（`tradeSpecies:10`）[union_room.c:3400；include/link_rfu.h:107]。

一次交易板交换就是每条链路一场：`Task_StartUnionRoomTrade` 保存 `CB2_ReturnToField` [union_room.c:1744]，而 `CB2_SaveAndEndTrade` 只为交易中心的回调保留链路 [trade_scene.c:2722-2725]。时序：游戏主机的宝可梦块（count 9）、主机的、它的邮件块（count 19）、主机的、动画、READY_FINISH、CONFIRM_FINISH、各存档屏障、双向 READY_CLOSE_LINK、断开。没有队伍交换，没有菜单，也没有房间流程。

## 聊天

聊天走 `SendBlock(0, buf, 0x28)`（count 4），未经请求，也没有 `BLOCK_REQ` [union_room_chat.c:429, :823]：

    [0]      command: 0 NULL, 1 CHAT, 2 JOIN, 3 LEAVE, 4 DROP, 5 DISBAND
    [1..8]   player name, EOS-terminated
    [9]      multiplayer id            (JOIN / LEAVE / DROP / DISBAND)
    [9..39]  message text, EOS-terminated (CHAT)

[union_room_chat.c:1256-1283]。0x45 的 ACCEPT 会保留链路 [union_room.c:1938]；两个成员进入时都发 JOIN。一行是 15 个条目 [union_room_chat.c:21]；接收方会画到屏幕外，而主机会在启动时拒绝过长的行（`uroom_chat.entry_count`）。收到 LEAVE 时主端必须断开链路 [union_room_chat.c:596-660]：主机在 0.1 s 后发 DROP 并关闭。追加到 `--chat-file` 的行会在写入后约 1.7 s 抵达游戏主机。

## 连接对战（UR_BATTLE 0x41）

`HasAtLeastTwoMonsOfLevel30OrLower` [union_room.c:4565] 要求每方队伍里至少有两只是 30 级或以下的非蛋宝可梦，在提供与接受时各检查一次 [union_room.c:2923, 3176]。

双方各选两只之后，每方发一个 0x20 字节的块，首字节 0x51（取消时为 0x52），其余为零（`CB2_UnionRoomBattle`）；发任何别的内容都会关闭链路。Switch 路径额外加两次链路任务等待，中间夹一段待机（分支 50-52）。`StartUnionRoomBattle(BATTLE_TYPE_LINK | BATTLE_TYPE_TRAINER)` [union_room.c:1811] 置 `linkType = 0x2211` [link.h:92；battle_controllers.c:520]。随后 [battle_main.c:934]：

    state 1  SendBlock struct LinkBattlerHeader {versionSignatureLo, versionSignatureHi,
             vsScreenHealthFlagsLo, vsScreenHealthFlagsHi, struct BattleEnigmaBerry}
    state 3  SendBlock gPlayerParty[0..1]   200 bytes      state 4  recv -> gEnemyParty
    state 7  SendBlock gPlayerParty[2..3]   200 bytes      state 8  recv
    state 11 SendBlock gPlayerParty[4..5]   200 bytes      state 12 recv
    state 15 InitBattleControllers

### 主站选举

只有 `BATTLE_TYPE_IS_MASTER` 一方运行回合结算、伤害与 RNG [battle_controllers.c:141, :45]；作为非主站的主机只是一个对战控制器。`LinkBattleComputeBattleTypeFlags` [battle_main.c:886]：若 `gBlockRecvBuffer[0][0] == 0x100` 或双方签名相等，玩家 0 为主站，否则版本高者为主站。主机发送 0x200，从而让游戏主机成为主站。

### 链路缓冲协议

每条控制器命令都是一个带 8 字节首部的 SendBlock [battle_controllers.c:401-435]：`BUFFER_ID, ACTIVE_BATTLER, ATTACKER, TARGET, SIZE_LO, SIZE_HI, ABSENT_BATTLER_FLAGS, EFFECT_BATTLER`，载荷按 `size - size % 4 + 4` 存放。`bufferId` 0 = BUFFER_A（命令），1 = BUFFER_B（应答），2 = 清除执行标志并携带发送方的多人 id [:566-594]。战斗位 0 属于主站。

`MarkBattlerForControllerExec` 置位 `28+battler`；命令的回送块置起每个玩家的半字节，各玩家再用 bufferId 2 清除自己那一位 [battle_util.c:185-201]。主站只在 `gBattleControllerExecFlags == 0` 时前进。

需要超过一次 ACK 的命令 [battle_controller_player.c]：

    CONTROLLER_GETMONDATA    -> EmitDataTransfer(BUFFER_B, size, data)   [player.c:1515]
    CONTROLLER_CHOOSEACTION  -> EmitTwoReturnValues(1, B_ACTION_*, 0)    [player.c:232-241]
    CONTROLLER_CHOOSEMOVE    -> EmitTwoReturnValues(1, 10, move | target << 8) [player.c:342]
    CONTROLLER_CHOOSEPOKEMON -> EmitChosenMonReturnValue(1, partyId, order)    [player.c:1316]
    CONTROLLER_OPENBAG       -> EmitOneReturnValue(1, itemId)            [player.c:1340]
    CONTROLLER_EXPUPDATE     -> EmitTwoReturnValues(1, RET_VALUE_LEVELED_UP, exp) [player.c:1051]
    CONTROLLER_ENDLINKBATTLE -> gBattleOutcome = payload[1], then ack     [player.c:2876]

`B_ACTION_USE_MOVE` 为 0、`USE_ITEM` 为 1、`SWITCH` 为 2、`RUN` 为 3 [battle.h:34]。第一个 `GETMONDATA` 用一个 0x58 字节的 `struct BattlePokemon` 应答 [pokemon.h:170]；重算得来的字段可能为零。战斗位 0 的 BUFFER_B 应答可以省略 [link_opponent.c:444]。连接对战中的战斗位可以享有最高行动顺序 [battle_main.c:3239, 3548-3560]。

### 反编译中看不到的两条规则

- 对战中状态机按块路由，从不按大小路由：每个 ACK 与短命令都是 16 字节、两个分片的记录。
- ACK 绝不能越过它所确认的块的回显。迟到的回显会再次置起执行位 [battle_util.c:193]，游戏主机就会永远等在 `gBattleControllerExecFlags == 0` 上 [battle_script_commands.c:2041]。`HostTradeEngine._echo_owed` 在子端命令等待镜像期间扣住新块，`rfu_leader.echo_blocks` 则让 ACK 等到回显的 0..count-1 每个分片都到齐。

### 节奏由 RFU 的 VBlank 预算决定

一个对战步骤约需一秒：按 `HOST_VBLANK_SECONDS = 1/59.727` 每个 VBlank 一个 RFU 槽位，一个命令块横跨约二十帧，再加上回程。相邻的 `bufferA` 命令中位间隔为 800 ms。

## 两台真实游戏主机放到空口上的内容

一台通过 Direct Corner 主持的火红，向叶绿发 25.5 帧/秒，向主机发 161.8 帧/秒。它在 `application_data` 的 0x11 偏移处以 ASCII 携带 Switch 的档案名，而不是训练家名字。

## 主机 tick 率与游戏主机的输出速率

`--tick-hz` 设置主机每秒的 RFU 槽位数；默认每个 VBlank 一个。在 20 Hz 下，一次交换耗时约为两倍，游戏主机发出的数据报多 80%。

# 电缆俱乐部竞技场

`frlg_trade_host.py --colosseum` 主持宝可梦中心 2 楼、第三个 NPC、竞技场、单打对战、JOIN。只有 `CB2_ReturnFromCableClubBattle` 会递增神秘卡片的 `battlesWon` [cable_club.c:792]。

`Task_StartActivity` 把 `ACTIVITY_BATTLE_SINGLE` 当作 `ACTIVITY_TRADE` 处理 [union_room.c:1903]，只是地图（`MAP_BATTLE_COLOSSEUM_2P`，位于 (6, 8)）与 `HealPlayerParty()` 不同。与交换路径的差别：

1. `LINK_GROUP_SINGLE_BATTLE` 接受 `{ACTIVITY_BATTLE_SINGLE, 0xFF}` [src/data/union_room.h:398]；`build_colosseum_app_data` 只改这一个字节。
2. 2 人席位脚本没有队伍检查 [data/scripts/cable_club.inc:576]。
3. `Task_StartWirelessCableClubBattle` 的分支 2 由双方主动发出裸的 28 字节 `struct LinkPlayer` [cable_club.c:701]，随后分支 4-6 在 `CB2_InitBattle` 之前加一段待机。
4. 整支队伍参战 [union_room_battle.c:47]。

从 `CB2_InitBattle` 起，它就是没有 0x51 选择块的联盟室对战。席位只需要 READY 键，且席位之后没有待机轮次；停在分支 3 的游戏主机发出 count 3 的 `SEND_BLOCK_INIT` 与 `04 40 00 80 65 df | bb c8 ff 00 11 00 | 01 00 03 00 00 00`，该块的到达即完成进入。对战之后主机欠一个退出键 [overworld.c:2977]。

## 什么决定一次竞技场之行是否算数

认输对另一方就是胜利：`HandleAction_Run` 在带 `B_OUTCOME_LINK_BATTLE_RAN` 时置 `B_OUTCOME_WON` [battle_main.c:4300]，该标志在返回前被清除 [:3734]。被计数的 id 是对方 28 字节记录中的训练家 id [cable_club.c:794]，每个各计一次，每项统计五次 [mystery_gift.c:630]。对三个不同的 `--id` 值各认输一次，即可拿到对战计数卡的伤药：

    save 0x3434:  0100 0000 0000 2300    battlesWon 1, lost 0, trades 0, icon 35 CARD_TYPE_LINK_STAT

# 两条主机侧约束

- 关闭定时器跑在 `activity.tick()` 里，而 `HostSession.tick` 在空洞守卫生效期间会跳过它，因此停止确认的游戏主机会把它卡住；在确认退出之后游戏主机一离开 LDN，运行时即停止。
- 全零的 `easyChatProfile` 会在训练家卡片上打出 "??? ???" [easy_chat.c:166-171]。一个词是 `(group & 0x7F) << 9 | (index & 0x1FF)` [easy_chat.h:1089]，每张卡四个；用 `EC_WORD_UNDEFINED`（0xFFFF）填充。
