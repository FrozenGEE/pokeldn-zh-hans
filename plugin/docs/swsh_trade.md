---
title: 连接交换
parent: 剑与盾
nav_order: 3
---

# 与零售版剑与盾交换

剑与盾的连接交换，从快照交换一直到存档。帧结构、内容注册与 PK8 见[同步框架](swsh_protocol.md)。

## 时序

    1  the console broadcasts its 3456-byte snapshot on protocol 0x84, port 0
    2  the client acknowledges the fragments (0x21) and the transfer (0x19 / 0x28)
    3  the client sends its own snapshot on 0x84 port 1 and reports it complete
    4  the trade screen opens
    5  the console sends the 40030 RPC pair on 0x7C port 1, several times a second
    6  the client answers the pair and sends `imReady` on 20030
    7  the console offers a Pokemon on 20030; the client offers one on 10050
    8  the player accepts (box command 4)
    9  the confirmation ladder runs on content 40
    10 the console writes its save

主持中的游戏主机不会确认加入方发在端口 0 上的快照；加入方的快照走端口 1。在它的 0x84 得到应答之前，游戏主机不发送任何其它内容，并无限重传该快照。`pokeldn/ldn/broadcast4.py` 实现了全部四种。

## 交换 RPC

ping、块消息与提供使用端口 0，40030 对使用端口 1；发到错误端口上的应答不会被读取。

    id 40030 = 40000 + 30
      1  offset      30
      2  base        10000, and 20000 in the other member
      3  station id  the sender's, equal to the host_constant of the seat record
      4  clock       a counter advancing between messages
      5  bytes(4)    00000000 for the 10000 member, 000018fc for the 20000 one

`000018fc` 是哨兵值 `0xfc18`（[步骤体](#the-step-body)）。`3e4e000012020801` 是 20030 上携带 `imReady{isReady:true}` 的消息，由加入的客户端发出。这些消息可由解析出的字段逐字节重建（`pokeldn/swsh/trade.py`）。

- 每个应答只发一次（`--answer-once`）；按定时器重新推导应答会重发提供内容。
- 读取器遇到非交换消息时返回 `None`。可靠窗口上的 mesh 消息（`44 00 01`，[主机迁移](#host-migration)）若抛出异常，会终止接收任务与这场交换。

## 主机迁移

主持中的剑离开会话时，会在协议 0x18 端口 1 上请求主机迁移（`nn::pia::mesh::LeaveWithHostMigrationJob`）：先发可靠首部 `0f 00 00 03 00 01 00 01`，再发 mesh 消息 `44 00 01`，即 MIGRATION_START `[0x44, host index 0, new host index 1]`。被指定的客户端必须在 mesh 端口 1 的可靠窗口上广播 `MIGRATION_FINISH`（[Pia 层](pia.md#host-migration)）。`--answer-migration --update-mesh` 会发出该完成消息，并以新的主机索引发布 mesh 更新。交接之后能否保住会话尚未验证。

主持中的零售版剑只在两种情形下各发一次 MIGRATION_START：

| 时机 | 条件 |
|---|---|
| 盒命令 3 之后 0.8 s | 一场交换完成之后 |
| 玩家接受后数秒，游戏主机以 `2-ALZAA-0016` 断开之前 | 在确认阶梯之前就失败的交换，加入方未发出确认命令 |

`bin/swsh_host.py --migrate` 以盒命令 3 与 MIGRATION_START 结束其主持的交换。默认情况下主机保留会话。

## 主持一场交换

`bin/swsh_host.py` 负责主持，`pokeldn/swsh/host_trade.py` 按主持中的剑的方式主导流程。法版零售剑 1.3.2 与模拟的盾 1.3.2 都能加入并完成交换。

主机构造站点广播，使用新的 network id、device id 与 account uid。在 0x84 上它确认加入方的三个快照分片，用自身的训练家身份与 `--offer-file` 指定的 PK8 改写这份在线快照，再把结果发到端口 0。游戏主机提供的 PK8 写入 `--received`。`--advert FILE` 与 `--snapshot FILE` 则改用已保存的记录。

站点握手双向确认，主机的请求在 [0x10] 处携带加入方的随机字节；未获确认时，加入方会重复其请求。主机应答加入方的 Sync Clock（0x1C，每两秒一次）与 Clone Clock（0x77）。

应用层则在两个方向的 [ping 握手](swsh_session.md)之后：

    0x84  each side's snapshot on the port of its station index (joiner 1, host 0), each acked on the
          same port; a retail host sends first, `host_trade.py` second
    110   the joiner pings first once its trade screen is up; the host answers with its own ping
          and the reply (a host ping before that screen is acked and dropped)
    30    the host opens content 30; each side offers on 20030 and sends box command 1; each
          acceptance is box command 4
    130   the joiner pings first
    50    the host publishes its Pokemon as element 0 and relays the joiner's 10050 as element 1
    120   the host pings first
    40    the ladder: host commands as element 0, the joiner's 10040 as element 1, phases 0 to 4

## 交换动画

游戏主机在最后一个 syncCommand 40（`3`）之后播放交换动画，期间没有任何交换消息。一台加入 `bin/swsh_host.py` 的零售版剑在发出该 syncCommand 后 1.2 s 开始播放，约 24 s 时把控制权交回玩家。

## 同一会话上的连续交换

一个会话可以一场接一场地交换：交换状态 9 发出事件 7（成功）或 8（失败），写入状态 0，玩家回到盒界面。内容 30 与 ping 110 在整个会话期间存活（初始化 `0x010c9280`）；内容 50 配 ping 130（交换状态 1，`0x010d5440`）与内容 40 配 ping 120（状态 6，`0x010dabc0`）每场交换都重建，每个元素都以新的 SyncPing 铸出。已达 synced 的 SyncPing 从不在原地重置，因此在游戏主机尚未持有内容 50 时发出的 ping 130 找不到任何持有者。

盒界面的步骤机（`0x00aa5160`，表 `0x2059218`）读取由监听者 `0x00c8d900` 设置的对方盒命令标志。在步骤 3，收到对方的标志 1（其提供）时，它一并清除标志 1 与 4（`0x00aa5688..0x00aa569c`）；步骤 7 等待标志 4（`0x00aa5628`），只有步骤 10 才发出动作 6，从而启动交换状态 1。与提供在同一突发里发出的盒命令 4 会被抹掉，游戏主机随后停在步骤 7，显示 "En attente d'une réponse"。对方的 4 必须在游戏主机处理完其提供之后到达：`pokeldn.swsh.host_trade` 只在加入方的 4 之后才发出自己的 4，而加入方启动器则以 4 应答主机的 4。

步骤 7 只在玩家按 B 时结束（没有计时器）：按键会清除对方的标志，发出盒命令 5（撤回接受）并离开该序列（`0x00aa57d0`）；在步骤 3 中则发出盒命令 2。在该盒命令 5 之前到达的对方提供与盒命令 1 会随其标志一起被清除，因此 `pokeldn.swsh.host_trade` 与 `bin/swsh_connect.py` 在盒命令 5 之后会再次发出自己的提供与盒命令 1。缺了这第二次发送，游戏主机就停在 "En attente d'une réponse"。

后续每一场交换都重复属于交换本身的那部分：双方的提供与盒命令 1、依序的两个盒命令 4、ping 130（加入方先 ping）、相位 0 处的新内容 50、ping 120、从相位 0 到 4 的新内容 40。交换与交换之间不再出现 0x84 快照、ping 97 或 110、盒命令 3，也不再发布内容 30。`bin/swsh_host.py` 与 `bin/swsh_connect.py` 配合重复给出的 `--offer-file`，可在一个会话上每场交换用掉一条排队记录——前者面对作为加入方的零售版剑，后者面对作为主机的零售版剑；主机在游戏主机离开时关闭。

`bin/swsh_connect.py` 在确认阶梯走完（40040 上到相位 4）之后，把游戏主机的提供当作下一场交换，并清除自己每场交换的状态；40030 对与 ping 应答则继续沿用。`bin/swsh_host.py --accept-first --lead SECONDS` 扮演主机端的玩家（先接受，交换后提供其下一条排队记录）；在模拟板子上，两个启动器在一个会话里各换出两条记录（`tests/test_esp32.py`）。

零售版加入方的玩家在盒界面按 B 时，游戏主机会发出盒命令 2 与 3、mesh `0401`，并无错误地解除认证；它下一次搜索仍可加入同一个被主持的网络。搜索中的游戏主机会加入任何通过[匹配规则](swsh_session.md#how-a-searching-sword-finds-a-partner)的网络。

## 盒状态机

内容 30 承载从交换界面到提供的全部过程。`onBoxSyncStateCommand` `0x010ce180` 丢弃线路命令 0 以及 7 及以上，并以事件 *N* 通知每个监听者对应线路命令 *N*（跳转表 `0x2067bec`）。监听者 `0x00c8d900` 设置 `[owner + 0x218 + code] = 1`；1 表示提供，2 表示撤回提供；4 表示确认，5 表示撤回一个 4。发送函数 `0x010cda70(content, command)` 由场景的跳转表 `0x00a96d10` 按其动作 `+0x78` 驱动：

    action 1  ->  command 3
    action 2  ->  the Pokemon (0x010ca430), then command 1
    action 3  ->  command 2
    action 4  ->  command 5
    action 5  ->  command 4
    action 6  ->  0x010ca640, which stores its Pokemon and sets the trade state to 1

命令暂存在 `[content+0x48]` 中，直到通道就绪字节 `[content+0x4c]` 被置位；其间若到达另一条不同的命令，会置起错误字节 `[content+0x4d]`，什么也不发。

命令 3 只由一方发出：初始化 `0x010c9280` 设置 `[session+0x419] = 0x00dceea0() & 1`（取自玩家列表），每帧更新 `0x010c9bb0` 在该字节为 0 时发出它。`--box-open` 在收到 0x84 确认时发出盒命令。

## 交换状态机

`[session+0x140]`，取值范围 1..10，表 `0x2067b68`：1 启动内容 50 并发出自己的宝可梦（`0x010ca0a0`），2 等待，3 是宝可梦交换（`0x010d54b0`），4 做决定（`0x01109320`），6 安装四个委托并启动内容 40（`0x010ca1ac`），8 释放它（`0x010dac90`），9 是终态（`[+0x144]` 置位表示失败；监听者收到事件 8）。盒回调 `0x010ca800` 在状态不为 0 时丢弃事件。状态 2 在委托 `0x010cc380` 中结束：对方的宝可梦写入 `session+0x70`，即一条 0x60 字节的记录（`0x010f5cc0`）。内容 50 的初始化 `0x010d4d90` 失败时，调用方置 `[session+0x144] = 1`，进入状态 9：通信中断提示。

## 确认阶梯

内容 40 是一道屏障，每条命令上一级。

### 相位到状态的映射

状态存于 `delegate+0x5c`。状态机 `0x010dae70` 把 `state - 1` 分派进表 `0x2067ed0`；状态 2、4、7、9 只能经由 `0x010dbf40` 离开，该函数忽略大于 4 的 u16，否则索引表 `0x2067f4c`：

    phase 0  -> state 1              -> send(0), announcing 1     0x010db308
    phase 1  -> state 3              -> send(1), announcing 2     0x010db0b0
    phase 2  -> state 5 -> 6 or 8    -> send(2), announcing 3     0x010db0dc / 0x010db104
    phase 3  -> state 10 or 11 -> 12 -> send(3), announcing 4     0x010db16c
    phase 4  -> state 13 -> 14       -> 0x010db970 tears down, content+0x84 = 0xfc18; no send

`[delegate+0x58]`（`0x110e620(...) & 1`）是角色：状态 7 立刻发出 2，状态 9 则在倒计时 `[delegate+0x60]` 之后发出，该值由 xorshift 在 2..302 中抽取。初始化把该委托安装为 10040 持有者的监听者（`0x010da6d0`），并在 `[content+0x2c0]` 处安装其第二个接口（`0x010da6bc`）。

### 交换中的传说宝可梦

状态 1（`0x010daf3c`）根据 `[delegate+0x48]` 与 `[delegate+0x50]` 处的两只宝可梦，经两个物种检查 `0x008fc280(species, form)` 与 `0x008fc310(species)` 重算角色。`0x008fc280` 对物种 150、151 与 249 到 251 为真，对跳转表 `0x02052aec`（382 到 494）与 `0x02052cb0`（643 及以上）中的条目也为真。角色为 0 时，状态 6 转到状态 8，其倒计时会推迟游戏主机的命令 2。

在一台主持中的模拟盾 1.3.2 上，以 `bin/swsh_connect.py` 加入，测得：

| 提供的宝可梦 | 角色字节 | 游戏主机在 `02000200` 之后 |
|---|---|---|
| 水箭龟、皮卡丘 | 1 | 发出命令 2，0.6 s 后发出 `02000300` |
| 灵幽马、苍响，我方的一对只应答一次 | 0 | 53 s 内无命令，内容 40 停在状态 9，泵停在状态 3（`0x010db48c`，其发送 `0x010de080` 未完成），随后提示 "L'échange de Pokémon n'a pas pu être effectué" |
| 灵幽马，我方的一对每秒重发 | 0 | `02000300` 出现在 `02000200` 之后 2.4 s；交换完成 |

重发的一对携带游戏主机最后一次的时钟值加上其后的流逝时间，按每秒 60 计（抓包中信封时钟的速率）；`--ladder-refresh` 设置该周期。反方向（`bin/swsh_host.py` 主持、游戏主机加入）在毫无改动的情况下完成了一次灵幽马交换：其主机按自己的帧时钟发布。泵状态 3 中究竟是哪个检查读取加入方的时钟，尚未确定。

### 泵

`0x010db3e0` 由内容 40 的 tick 在状态机之前运行，是一个作用于 `[content+0x80]` 的 17 状态机，带一段共享尾部。尾部通过 `0x010de310` 提交内容的相位 `[content+0x17c]`（该函数丢弃待处理的体并清空作业队列 `content+0x310`），并在相位等于已宣告值时调用委托的状态设置函数，随后运行排队的作业 `0x010ddf40` 与元素更新 `0x006d4b80(content+0xd0)`。

| 字段 | 含义 |
|---|---|
| `+0x84` | 已提交的相位；构造函数置为 `0xfc18` |
| `+0x86` | 随最后一条命令宣告的相位，在全部五个发送点均为 `data + 1`（`0x010dbab0`） |
| `+0x17c` | 相位，即 `element+0xac` |

相位到达 `+0x86` 时，阶梯上升一级。泵状态（表 `0x2067f08`；`[+0x1c0]` 是元素的 `+0xf0` 通道）：

    1   element ready -> 2; delegate slot 0 with the phase (command 0, announcing 1)
    2   a pending body at +0x88 -> 3
    3   all ready, every pair's low half == phase: send the body -> 4
    4   0x006d3690 publishes the high half; the master goes to 8, others to 7
    8   every station has sent a command -> 9
    9   no resend byte set -> 10
    10  every high half == announced: the master writes shared value = announced -> 7
    11  clears every flag (a station left); [+0x374] ? 12 : 2
    14  the gated commit

状态 8 到 10 只在主站上运行（`0x018407f0`）；其它站点跟随共享值。内容 40 的注册者在 `[+0x374]` 处存 1：有站点离开时进入 11、12 并终止阶梯（`0x010dc720`）。

### 相位就是元素的字段

相位就是 `element+0xac`（`0xd0 + 0xac = 0x17c`）：注册者在 `content+0xd0` 处以 `0x006d44e0(element, 0)` 铸出 40040 元素，而 `0x010c0000..0x010e0000` 区间内没有任何代码向它写入。

它只在 `0x006d4ca0` 中前进，即元素更新 `0x006d4b80` 的尾部：一旦共享值 `0x006d3260([element+0xf0])`（没有时为 `0xfc18`）作为该站点自己的低半部分发布出去，相位就变为该值，并通知内容。

`0x018407f0` 在主持 Pia mesh 的游戏主机上为真（[会话](swsh_session.md#the-pia-session-object)）。只有它会播种共享值，即 `+0xf0` 通道的 16 位子元素（[子元素种类](swsh_protocol.md#sub-element-kinds)）；每个站点都会采纳它。内容还会发出另外几种形态，见[下文](#shapes-the-confirmation-content-also-sends)：

    0x006d3260  read            ready [sub+0x61] ? [sub+0x88] : 0xfc18
    0x006d33b0  write(v)        0x006d3570 when not ready or body != v
    0x006d3570  publish         body [sub+0x88] = v and queue it per station
    0x006d3060  all high == v   every pair's [sub+0x8a] == v

写入不会碰就绪字节（只有接收路径 `0x006d6a08` 会存入 `+0x60`），因此在收到消息之前读取返回 `0xfc18`；在主站上，那条消息就是它自己发的。

### 步骤体

内容 40 的 elementId 20000 上的四字节体，低半部分为相位，高半部分为最后宣告的值：

    0x006d3980(channel, v)   body = <u16 v><u16 [sub+0x8a]>    low; from the element update
    0x006d3690(channel, v)   body = <u16 [sub+0x88]><u16 v>    high; from pump state 4, [content+0x86]

一次观测到的阶梯：

    000018fc   phase 0, announced 0xfc18   the birth sentinel
    00000100   phase 0, announced 1        the cue; command 0 already sent
    01000100   phase 1, announced 1        caught up, committed
    01000200   phase 1, announced 2        state 3 sent command 1
    02000200   phase 2, announced 2        caught up
    02000300   phase 2, announced 3        committed, sent command 2
    04000400   phase 4                     the teardown rung

`trade.parse_sync_step`、`SYNC_LADDER` 与 `sync_announced_phase` 负责解析它。

### 命令

`SyncSaveDataHolder{syncCommand{data:N}}`，位于 10040、可靠端口 0。处理函数 `0x010dbc90` 会丢弃 `0x006b5850` 无法解析的发送方（`0xfd`），把 `[arg1+0x14]` 处的 int32 转交中转函数 `0x010dbe20`，然后总是对 `[content+0x2a0]` 调用 `0x006a24a0(obj, sender, 1)`（`0x010dbdf8..0x010dbe08`）：阶梯从不读取该值，因此任何命令都能推进一级。状态只经由 `0x010dbf40` 改变，由泵以其自己的相位调用。

`[content+0x2a0]` 是按站点记录标志的映射（`0x006a24a0` 置位，`0x006a2840` 在所列站点全部置位时返回 1，`0x006a2760` 清除）；状态 8 等待它，提交与状态 11 会清除它。该标志在网络更新的排空函数 `0x006db3b0` 中置位，帧函数 `0x00f1df30` 围绕游戏更新运行它两次。内容 40 的命令 tick `0x010dae70` 跑在两次排空之间。

一级需要一条在上次提交之后到达主站的命令。在第 0 级，任何命令都算，包括落在提示体 `00000100` 上的那条；此后落在提示体（`01000200`、`02000300`、`03000400`）上的命令会在提交之前落地并被清除，只有落在追平体（`01000100`、`02000200`、`03000300`）上的那条才算数：

| 命令，每个新体一条 | 最后一个体 |
|---|---|
| 1 条，落在 `00000100` 上 | `01000200`：第 0 级 |
| 4 条，从 `000018fc` 到 `01000200` | `02000300`：第 0 与第 1 级 |
| 9 条，从 `000018fc` 到 `04000400` | `04000400`：完成交换 |

`--confirm-commands 0,1,2,3,0,1,2,3,0,1,2,3` 每出现一个新体弹出一条，`000018fc` 也算在内；队列不能见底。`answer_rpc` 原样回显体，不动任何一半；`--confirm-phase N` 写入低半部分。

### 取消与继续消息

30040，即 `SequenceDataHolder`（[协议页](swsh_protocol.md#the-30000-holder)），存放在 `[content+0x2b8]`，监听者为 `content+0x68`（虚表 `0x02580030`）：

| 分支 | 消息 | 处理函数 |
|---|---|---|
| 1 | CancelAccepted | `0x010dce70` |
| 2 | RequestCancel | `0x010dc920` |
| 3 | RequestCancelAll | `0x010dcaa0` |
| 4 | RequestForcedProceed | `0x010dc7b0` |

三者都只在 `currentSeqNo` 等于已提交相位 `(s16)[content+0x84]` 时动作。RequestCancel 以 `CancelAccepted{[+0x84], isForced: 0}` 应答发送方并清除其标志；RequestCancelAll 以 `isForced: 1` 应答所列的每个站点并清除所有标志。CancelAccepted 重跑状态 2 到 4 并留在该相位。RequestForcedProceed（作业 `0x010dd040`）执行 `0x006d33b0([content+0x1c0], targetSeqNo)`，即状态 10 的写入，但不经状态 8 与 9，也不做主站判定。

RequestForcedProceed 在没有 `syncCommand` 的情况下推进共享相位（一台模拟的盾）。若阶梯后续的命令都是这类请求，流程会停在 "Communicating"，进不到存档。

### 确认内容还会发出的其它形态

不带 ownerId、且体不是四字节的 40040 信封：

    elementId 20000, no owner, 2 bytes   0000   then   0100
    elementId 1,     no owner, 4 bytes   00000000        after a syncCommand{data:0}
    no elementId,    no owner, 4 bytes   00000000  then  01000000

该对的接收函数 `0x006d6490` 丢弃两字节的那些（`cmp x2,#4`）；它们就是共享值（[相位就是元素的字段](#the-phase-is-the-elements-field)）。

## 联盟卡

交换结束后，每台游戏主机都会询问是否保留对方的联盟卡，即其快照 0x924 处的 TrainerCard（[协议](swsh_protocol.md#the-party-payload-on-protocol-0x84)）；该回答不发送任何内容。

回答 "Oui" 时会把它原样存入存档块 `0x28e707f5`：自 `album+0x230` 起 300 个 0x1d0 大小的槽位，`+0x1c8` 非零即表示还有空位（`0x013fbab0` 填入第一个空位；`0x013fbc00` 在全部用满时返回 1）。

`0x013fbc40(album, card)` 在某个已用槽位匹配卡上 0x1C 处的 u32 与 0x1A8 处的八个字节时跳过提问。0x1C 是 PKHeX 的 `TrainerCard8.TrainerID`，即 `(SID << 16 | TID) mod 10**6`；0x1A8 是 `TimestampPrinted`，一个 Unix 时间。对一台模拟的盾而言，训练家 id 改变或 0x1A8 处某个字节改变会再次提问并存进第二个槽位；图鉴数量或名字改变则不会。`pokeldn.swsh.league_card` 负责映射一个 u32；`trade_payload.rewrite` 设置训练家 id。

零售版剑会绘制收到日期、`game`（0x24）的 Logo、0x39 处的三个 ASCII 字节、`dex_complete`（0x30）为真时的洛托姆图鉴王冠，以及七个星格中的 `count + 1` 个，其中 `count = card[0x177] + (card[0x1b6] != 0) + (card[0x1b7] != 0)`。构建函数 `0x0158eef0` 从存档填入 0x177（`DesignLevel`：带 `FSYS_GAME_CLEAR` 时为 4，否则按徽章数 > 6、> 3、> 0、0 分别为 3、2、1、0）、0x1B1（`FSYS_SEED_CHALLENGE`）、0x1B3（`FSYS_INPUT_SHIRT_NUMBER`）以及 0x1B6、0x1B7 处的星（`FSYS_R1_GAME_CLEAR`、`FSYS_R2_GAME_CLEAR`）；标志键是名称的 FNV-1a 64（[协议](swsh_protocol.md#the-player-profile)）。

`0x0158f5e0` 会拒收某些卡（DesignLevel 5、language 6、GlossIndex 9），改以默认卡替代。`bin/swsh_host.py --card-set FIELD=VALUE` 可编辑送出的卡（`pokeldn.swsh.league_card` 的字段）；换一个新的 `trainer_id` 会让游戏主机重新提问。

## 提供的记录

20030 上的提供就是快照中的队伍槽位 `--offer-slot`，就地编辑，因此显示的队伍与提供的内容一致；身份改写先运行，`party_matches_trainer` 成立。`pokeldn.swsh.pokemon.build_from` 重写校验和，按新的加密常量重排，并保留每个未命名的字节。构建出的皮卡丘换给零售版剑再换回来，等级、性格、特性、性别、球种、携带道具、个体值与努力值都不变，并通过 PKHeX 的合法性检查。

法版剑 1.3.2 在四次交换中都接受了其存档已持有的记录（PID 与 EC 相同）。盾 1.3.2 在所读路径上没有重复检查：PID 与加密常量的取值函数不会走到盒遍历，盒代码只读物种与蛋标志。晶灿钻石在 PK8 字节 0x52 处的非法标志没有任何访问器读取（[BDSP 交换页](bdsp_trade.md#duplicate-detection)）。`bin/swsh_host.py` 与 `bin/swsh_connect.py` 的 `--fresh-pid` 会抽取新的加密常量与 PID。

    --offer-slot 1 --offer-nickname POKELDN --offer-ivs 31,31,31,31,31,31

| 标志 | 作用 |
|---|---|
| `--offer-nickname`、`--offer-ot` | 26 字节的 UTF-16 字段，至多 12 个字符；设了昵称就置上已起昵称标志，否则取物种名 |
| `--offer-species` | 只写物种字；其余保持模板的值 |
| `--offer-ability ID`、`--offer-moves A,B,C,D` | 这两个字段；PP 与再学习招式保持不变 |
| `--offer-level N` | 0x148 处的等级字节 |
| `--offer-experience N` | 0x10 处的经验字 |
| `--offer-ivs` | 六项个体值 |
| `--offer-file FILE` | 四种形态之一的 `.pk8`（存储或队伍、加密或 PKHeX 的解密导出，按首部校验和区分）；OT 名与 id 改为快照中的训练家 |
| `--offer-file-as-is` | 保留文件自带的 OT |
| `--save-offer FILE` | 在触碰无线之前先写出构建好的记录 |

法版剑 1.3.2 不校验特性或招式与物种是否匹配，等级取自经验字（0x10），能力值由个体值、努力值、性格与极限特训（0x126）重算，初训家 id 显示为 `(SID << 16 | TID) mod 1000000`，不与 MyStatus 比对任何初训家 id，并把 PID 高半部分满足 `low ^ TID ^ SID` 的显示为异色。无数据的物种（152）以皮卡丘的模型、黑色的精灵球图标与全零的种族值存入。

未解决：其它不存在的物种会绘制成什么，以及名字取的是名称字段还是查找失败的结果。

## 一次完整交换的命令行

`swsh_connect.py --preset trade` 携带一场交换所需的标志；其后给出的标志会覆盖该预设。在游戏主机上按本地连接交换的方式搜索（Y-Comm → 连接交换 → 本地，两条提示都按 A）：

    POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/swsh_connect.py --keys PROD_KEYS \
        --preset trade --save-offered offered.pk8 --capture trade.jsonl

回发的快照是同一会话中游戏主机自己的那份（`--send-snapshot live`，即预设的默认值）：三个 0x84 分片被重组，训练家名字、TID 与 SID 被改写为 `--snapshot-name/-tid/-sid`，并在游戏主机的快照重组完成之后发出。`--send-snapshot FILE` 改为发送一份保存好的 3456 字节载荷（先 `--preset capture`，再用 `tools/switch/swsh_snapshot.py` 写出一份）。

`--offer-file FILE` 把一个 `.pk8` 放进提供的队伍槽位。重复给出时，它在会话上为每场交换排队一条记录；最后一条用于之后每一场交换，配合 `--fresh-pid` 时换用新的 PID，第 N 场交换会以 `-N` 后缀写出 `--save-offered`。游戏主机已提供、但确认阶梯尚未走完的交换，会把会话在 `--hold` 之后再多留至多 `--grace` 秒（300）。任一启动器上的 `--hold-after-trade SECONDS` 会在最后一场排队交换结束那么久之后终止运行（[离开](swsh_session.md#leaving)）。存储格式、不带队伍能力值的记录也能用于交换；游戏主机会由经验算出等级。

## 惩罚，以及干净地结束一次运行

链路仍在而交换超时，会被记为一次失败的交换，并禁止游戏主机再交换（`msg_ui_live_comm_app_alert_00`，`/bin/message/French/common/live_comm.dat` 第 331 行）；该禁令持续多久尚未读出。在 `04000400` 之后 15 s、存档进行中切断链路，会显示通信错误 `2-ALZAA-0016`，不触发交换禁令，并立刻开始新的本地搜索。

`bin/swsh_connect.py --abort-on-stall SECONDS` 在确认阶梯开始后、连续 SECONDS 秒没有新体时切断链路。它在相位 4——静默拆除的那一级——就停手（`stall_abort()`、`final_phase_seen`、`LADDER_FINAL_PHASE`），因此存档期间绝不会切断链路。

## 验证一次完成的交换

收到的宝可梦在 0xC4 处带 `CurrentHandler` 1，0xA8 处的 `HandlingTrainerName` 是接收方的名字，覆盖发送方的初训家。`--offer-echo` 会把游戏主机自己的记录原样送回，因此只有物种不同才能证明真的发生了转移。
