---
title: 主持端实现
parent: 火红与叶绿
nav_order: 7
---

# 主持端实现

`bin/frlg_trade_host.py` 是火红/叶绿的直连角主持人：一台 Switch 加入主持端开的 LDN 网络，Pia 建立对等会话，再由 Reliable 承载一条模拟的父端 RFU 链路，终点是主持人一侧的交换状态机。`bin/frlg_mg_host.py` 复用了活动层以下的全部内容。

## 组件与职责

| 组件 | 负责 |
|---|---|
| `TradeRunConfig` | 不可变的运行配置：`TrainerProfile`、`TradePlan`、`LdnConfig`、`HostOptions` 或 `JoinerOptions` |
| `HostApplication` | 资源顺序：校验、启动传输、广播信标、事件循环、中断、清理；活动钩子只提供消息与持久化，所以交换与神秘礼物共用同一个循环 |
| `HostTransport` | LDN 热点、虚拟网卡、参与者事件、UDP :12345；不解析 Pia |
| `HostPeerProtocol` | 单个对端的 Pia 状态：Net、Session 接受、RTT、包 id、nonce 选择、加密、封帧、Reliable 分批；产出 `OutboundDatagram` |
| `HostSession` | Reliable + `RFULeader` + 活动引擎（`engine=` 选交换或神秘礼物）；不碰套接字，离线端到端测试用的就是这一层 |
| `HostTradeEngine` | 主持人进房、队伍与卡片交换、选择、确认、动画与存档屏障、取消、退房、关闭宽限；`HostTradeTiming` 给出各处的帧数 |
| `BeaconInjector` | 它的原始监听套接字与工作线程 |

数据报的流向是 Switch → `HostTransport` → `HostPeerProtocol` → `HostSession` → `RFULeader` → `HostTradeEngine`（子进程命令行进、父进程命令行出），然后再反向回到 Switch。定时截止时间由对端协议给出，所以 Net/Session 重试、RTT 探测、重传和约 59.727 Hz 的节拍都不依赖轮询延时。

## 启动与建立会话

1. CLI 把 `TradeRunConfig` 交给 `HostApplication`，后者启动一个未激活的直连角网络和周期性信标。
2. Switch 加入；`on_participant_joined()` 发送 Pia Net 连接请求，未收到 ACK 就一直重试。
3. Switch 回复 Net ACK 并发起 Session 加入请求；主持端发出一个 Session 更新和一条单播加入响应（有个诊断开关能把这两条的先后反过来），Switch 再确认。
4. RTT 与 Reliable/RFU 流量开始跑，应用数据属性被置为有效。

畸形的 Pia 包、填充错误、认证失败、Reliable 拼接不完整、Session 身份不符，都只记日志并丢弃。只有当常量 id、Pia 变量、来源 IP 和加密头都与当前 LDN 对端吻合时，Session 请求才会被接受。

## 交换与退房过程

```mermaid
stateDiagram-v2
    [*] --> PlayerExchange
    PlayerExchange --> RoomEntry: LinkPlayer and trainer card
    RoomEntry --> PartyExchange: seat route and entry barriers
    PartyExchange --> Selection: party, mail, ribbons
    Selection --> Confirmation: Switch selects; leader offers configured slot
    Confirmation --> Animation: both confirm
    Animation --> Save: trade committed
    Save --> PartyExchange: another configured trade
    Save --> MenuExit: final party refresh
    MenuExit --> RoomExit: both cancel; five-second field wait
    RoomExit --> CloseGrace: Switch confirms room exit
    CloseGrace --> Disconnect: fifteen seconds of peer traffic
    Disconnect --> [*]
```

最后一笔交换完成后，主持端等 Switch 打开交换菜单；玩家选 CANCEL 再确认 YES，主持端立刻回 `BOTH_CANCEL_TRADE`。主持端走完待机屏障，等五秒再离开房间（Switch 先走的话就不用等），并在 Switch 确认关闭（`READY_CLOSE_LINK`）之后继续维持正常对端流量十五秒，然后排入 RFU 断开。对主机发来的 Session 离开请求，它用类型 4 回应（见 [frlg_link.md](frlg_link.md) 里「离开 Pia 会话」一节）。收到 LDN 离开事件会立刻停止对端输出。

只有双方都选 CANCEL，房间才会结束 [trade.c:1716]，所以主持端发什么都无法把主机踢出房间。用 `--hold-after-trade N` 时，`bin/frlg_trade_host.py` 和 `bin/frlg_trade_join.py` 会在最后一笔排队的交换之后再等 N 秒，如果那时主机的玩家还没取消，就走与 Ctrl-C 相同的拆解流程强行关闭链路；主机随后显示无线链路错误，按 A 会带着重新载入的存档回到柜台 [link.c:1540-1560]。那些交换已经在存档里了。

## 关闭与清理

断开之后，如果收到过宝可梦，主持端会先保存它，然后等信标线程结束、关闭套接字与网络、移除 LDN 虚拟网卡。正常完成、`KeyboardInterrupt`、启动中途失败、信标线程崩溃，走的都是同一套清理。

所有主持端——交换、对战、神秘礼物都一样——在主机离开 LDN 时停止（`HostApplication.run`）：没有确认过关闭就立刻停，确认过则等 2 秒稳定期（`HOST_CLOSE_SETTLE_SECONDS`）。`--end-on-success` 让神秘礼物主持端在一次成功投递的断开发出后立刻停止，不等主机离开；它的 `--idle-timeout` 则在连续若干秒没有 Switch 流量后停止。

## 训练家资料的传递

`pokeldn.config.DEFAULT_TRAINER` 是默认身份。每个 CLI 都从 `--ot`、`--version`、十进制的 `--id TID[:SID]` 推出本次运行专属的不可变 `TrainerProfile`，校验第三世代的名字与取值范围，然后从它派生出每一处展示：

| 展示位置 | 携带内容 |
|---|---|
| LDN 发现 | 名字与公开的 TID |
| Pia Session | UTF-8 参与者名 |
| LinkPlayer | `SID << 16 \| TID`、版本、语言、性别与进度标志；第三世代名字 |
| 训练家卡 | 第三世代名字；主持端用 `0xFF` 填充，加入方保留原生 `0x00` |

## 失败处理

- 预检会拒绝不支持热点模式的无线网卡。
- 在 Linux 无线网卡上，LDN 认证之后热点必须把该站点标记为 `NL80211_STA_FLAG_AUTHORIZED`。驱动配置与标志见[适配器](hardware_adapters.md)。
- 传输层或信标线程出错会中止本次运行，并把已创建的东西全部回收。
- 参与者意外离开会立刻停止输出。那十五秒宽限只有在参与者仍在线时才会走完。
- 宽限（`HostTradeTiming.post_client_close_grace_frames`）只在 RFU 主持人处于 UNI 状态时计时；主机发来的 `D` 会把它切到 DISCONNECTED（`pokeldn/gba/rfu_leader.py`），引擎随即停止走帧。在 13 次正版火红主持交换中，主机都在发出第一个 `READY_CLOSE_LINK` 之后 0.1 秒发 `D`，并在其后 0.5 到 4.0 秒离开 LDN，所以正常关闭时宽限根本不会生效。
- 只有完整收到的宝可梦才会被写出；输入的 `.pk3`/`.ek3` 文件永远不被修改。

## 扩展主持端

把新行为加在最懂它的那一层：设置放进运行配置，操作系统与网络的事放进应用或传输层，Pia 的事放进 `HostPeerProtocol`，RFU 的事放进 `RFULeader`，直连角的判定放进 `HostTradeEngine`。每一层都用它自己产出的数据报、负载、帧或命令行来测。

主持端只服务一台 Switch。要多接几个对端，就得给每个对端配一个 `HostPeerProtocol`（各自的 Pia 变量、nonce、包 id），再加一套游戏层的 RFU 策略；只提高 LDN 的参与者上限是不够的。

## 源码地图

| 源码 | 职责 |
|---|---|
| `bin/frlg_trade_host.py` | CLI、配置、入口 |
| `pokeldn/frlg/host_cli.py` | 共用的主持端 CLI 选项 |
| `pokeldn/frlg/link/host_app.py` | `HostApplication` |
| `pokeldn/frlg/config.py` | 训练家、交换计划、神秘礼物负载、LDN、角色与运行配置 |
| `pokeldn/frlg/link/trade_runtime.py` | CLI 日志、队伍载入、槽位解析、输出保存 |
| `pokeldn/frlg/link/host_beacon.py` | 抓包得到的交换信标、发现信息改写、`BeaconInjector` |
| `pokeldn/host_support.py` | 面向操作系统的支持（能识别 sudo 的密钥路径解析） |
| `pokeldn/ldn/transport.py` | `HostTransport` |
| `pokeldn/ldn/host_pia.py` | Pia 封帧、`HostPeerProtocol` |
| `pokeldn/frlg/link/host_session.py` | `HostSession` |
| `pokeldn/ldn/reliable.py` | Reliable |
| `pokeldn/gba/rfu_leader.py` | `RFULeader`：父端封帧、NI/UNI 握手、回显表 |
| `pokeldn/frlg/link/host_trade.py` | `HostTradeEngine`、`HostTradeTiming` |
| `pokeldn/frlg/link/linkplayer.py` | LinkPlayer 与训练家卡编码器 |
| `pokeldn/ldn/ldntrace.py` | 可选的 JSONL 诊断输出 |
