---
title: Let's Go 卡带与会话
parent: Let's Go 皮卡丘与伊布
nav_order: 1
---

# 卡带、它的密钥与会话

本页覆盖 Let's Go 皮卡丘与伊布从卡带密钥到交换提交的全过程。地址都是 Let's Go 皮卡丘 1.0.2 解压后 `main` 的偏移，按 `tools/switch/nso_read.py` 给出的布局：text 为 `0..0xd32ba8`，rodata 从 `0xd33000` 起，data 从 `0x1527000` 起。

## 这个标题由什么构建

更新 NSP 携带 Program NCA `2b7730a9e56498bbafac2002d4908c6b`（标题 ID `010003f003a34000`，rights id `010003f003a348000000000000000007`，密钥世代 6）。所有 `nn::pia` 和 `gflnet3` 引用都在它的 exefs `main` 里。

    ./.venv/bin/python tools/switch/xci_read.py "<the .nsp>" --keys prod.keys \
        --nca 2b7730a9e56498bbafac2002d4908c6b --exefs 0 --extract main
    ./.venv/bin/python tools/switch/nso_read.py main main.bin
    ./.venv/bin/python tools/switch/rtti_names.py main.bin 0xd32ba8

Pia 是静态链接的：269 个 `nn::pia` 类、2112 个具名虚函数，`nn::pia::local` 里含有 `LdnCreateNetworkJob`、`LdnCreateSessionSetting`、`LdnJoinSessionSetting` 和 `LocalProtocol`。`nn::ldn` 从 nnSdk 导入，GOT 槽位 `0x15fa1e0..0x15fa2a8`。Pia 之上，`gflnet3` 打包了协议缓冲区。

## LDN 口令

    W3GoSMEn7RIIUQ89rzqBHGhGferRNb7K18ZBq2aNuj8Us9RO9Q9JYyGOZlLy8MYL

`0xf73a50` 处的 64 字节，原样使用，与剑与盾的相同。`0x004db6b4` 连同长度 `0x40` 把它传给 `LdnCreateSessionSetting` 的 setter `0x5c0fb0`，`0x004dbba4` 传给 `LdnJoinSessionSetting` 的 setter `0x5c1280`。`LdnCreateNetworkJob`（`0x5ce640`）把它保存在 +0xC4，长度保存在 +0x104，并在 `nn::ldn::CreateNetwork`（`0x5ce988`，PLT 桩 `0xd31c78`）之前构建 `nn::ldn::SecurityConfig`。

## Pia 游戏密钥

    p1frXqxmeCZWFv0X

`0xefd659` 处的十六个 ASCII 字节，也就是剑与盾、传说 阿尔宙斯和朱与紫所用的密钥。当模式字段 `[x19+0x98]` 为 0 或 2 时，`0x0011a364..0x0011a384` 把它写入加密设置的 +0x24c。

## Pia 头

版本 3（即 wiki 的 Pia 5.11-5.17）。初始化函数 `0xd122d4` 写入 `0x00000003_32AB9864`；校验函数 `0xd12400` 检查魔数以及 `(byte & 0x7f) == 3`。布局就是剑与盾的版本 4，只有版本字节不同（`pokeldn/ldn/pia4.py`）：

    0x00  4  magic 0x32AB9864, big-endian
    0x04  1  0x80 (encrypted) | version = 3
    0x05  1  connection id
    0x06  2  packet id
    0x08  8  AES-GCM nonce
    0x10  16 AES-GCM tag
    0x20     ciphertext

## 消息分帧

固定的 22 字节消息头（Pia 5.11-5.12；反序列化函数 `0x5ae870`，写入函数 `0x5aeb00`），见 `pokeldn/ldn/pia3.py`：

    0x00  1  flags: 1 destination is a bitmap, 2 relay needed, 4 relayed, 8 unbundled
    0x01  1  version, 1
    0x02  2  payload size, big-endian
    0x04  1  protocol type
    0x05  1  protocol port
    0x06  8  destination, big-endian: a constant id, or a station bitmap under flag 1
    0x0E  8  source constant id, big-endian
    0x16     payload, padded to a multiple of 4

## 会话密钥

`LocalProtocol` 的派生函数 `0x5cd560` 与 BDSP、剑与盾的相同：以会话参数（`0x57cfc0`）为种子做 SEAD xorshift128，取四次，在 `LocalProtocol+0x49c` 的游戏密钥下做 AES-128-ECB。`pokeldn.ldn.pia5.ldn_session_key`。IV 沿用 pia4：`crc32(网络 id 小端 || 主机 MAC)` 的三个字节、一个源 id 字节 0、头部的 nonce。

广播的应用数据以一个 24 字节头开始：

    0x00  4  network id, random per session
    0x04  4  CRC32 of the user password, 0
    0x08  1  system communication version, 4
    0x09  1  header size, 0x18
    0x0C  4  session param, the key seed
    0x18     the game's application data

## LAN 模式

Let's Go 1.0.2 中有一条代码从不进入的 LAN 路径。网络建立函数 `0x5dabb0` 为模式 0 构建本地工厂、为 1 构建 Nex、为 2 构建 Lan 工厂（`0x5ddaf0`，LanNetworkFactory 构造函数 `0xd14a20`），与之配套的启动函数 `0x4da710` 接受 1 或 2。但所有写入模式的代码都只传 0 或 1：`0x115818` 传 1，会话对象的构造函数在 `+0xa4` 处把模式清零，它唯一的 setter `0x348eb0` 也只存 0 或 1。英文的选项、匹配、菜单和错误消息里没有任何 LAN 文字。

## 连接码

连接码就是 NetworkInfo 的 scene id，`1000a + 100b + 10c + 1`，每一位取它在选择器中的序号（皮卡丘 0、伊布 1、妙蛙种子 2、小火龙 3、杰尼龟 4、波波 5、绿毛虫 6、小拉达 7、胖丁 8、地鼠 9）；SSID 始终是 `01000000000000000000000000000000`。`0x891580` 把三次选择合并，`0x978080` 算出 `10 * number + mode`（模式 1 为交换），会话构造函数 `0x4db1e0` 把它写进 `LdnCreateSessionSetting+0x60`（`0x4db6ac`），Pia 再把它复制到 `NetworkConfig.intentId.sceneId`。

同一个构造函数还决定正在搜索的游戏主机在哪个通道上托管：`{1, 6, 11}[scene % 3]`，表在 `0xf73a44`；`pokeldn.lgpe.search_channel(code)`。三只皮卡丘是 scene 1、通道 6；妙蛙种子、小火龙、杰尼龟是 2341、通道 6；皮卡丘、皮卡丘、妙蛙种子是 21、通道 1。

正在搜索的游戏主机只有在某个网络于它自己的通道上广播了它的 scene id 时才加入。`bin/lgpe_host.py --code NAMES` 就在该通道上托管（`--channel auto` 会扫描游戏主机的网络）。`bin/lgpe_join.py` 不发送连接码。

## 本地协议

会话状态走协议 0x24、端口 0：即 wiki 的 5.7-5.45 更新会话消息（`pokeldn.ldn.local_protocol.parse_update_session`），本地头版本 1、类型 0x11、八个节点：主机 `169.254.105.1` 排名 0，加入方 `169.254.105.2` 排名 1，其余为 255。消息体以小端携带主机的常量 id（MAC `48:f1:eb:20:9b:22` 对应 `000048f120229beb`）；消息头则以大端携带它。

## 站点协议（用于加入网格）

先走协议 0x14 的连接请求，再走 0x18 的网格加入。处理函数 `0x5b8800` 按 wiki 的 5.10-5.18 布局读取，站点协议版本 9：

    [0]     message type            1
    [1]     connection id
    [2]     version number          must be 9 (0x5b8848)
    [3]     is inverse connection request; rejected above 1
    [4]     target constant id      big-endian u64, the console's own (0x5b6830)
    [0xC]   target variable id      big-endian u32, checked only when [3] is 1
    [0x10]  inverse connection id
    [0x11]  station location        36 bytes for a joiner: no public address, zero NAT fields
    [...]   ack id                  u32, the message size minus four

零售游戏主机会带着反向请求跑完整套序列：

    ->  connection request (is_inverse 0)
    <-  ack; inverse connection request (is_inverse 1) with the host's location
    ->  ack; connection response (type 2, result 0, padded to 0x38)
    <-  connection response, 840 bytes, repeated until acknowledged
    ->  ack

### 站点发送的连接响应

0x348 字节（解析函数 `0x5b9270` 接受 0x3C）：

    0x00  1  message type 2
    0x01  1  result
    0x02  1  version 9
    0x03  1  platform 4
    0x05  8  the receiver's constant id, big-endian
    0x0D  4  the receiver's variable id, big-endian
    0x31  4  the network id, big-endian
    0x35  2  01 01
    0x37  0xC3  a PlayerInfo (`station_protocol.player_info`); its first byte must be below 5
    0x344 4  the ack id

见 `station9.build_connection_response`；`bin/lgpe_join.py --player-name NAME`。游戏主机若收到 0x3C 字节的响应，就永远不会发送自己的克隆数据，并离开克隆会话。

## 加入网格

0x18 上的网格加入请求（`mesh_protocol.build_join_request`，本机站点索引 253）换来一个 148 字节的加入响应（主机索引 0、加入方索引 1、最大活跃 2、最大总数 8），在 0x14 上确认，然后是一个更新网格（类型 0x20）。随后主机依次推送更新会话（0x24，用 0x21 确认）、RTT（0x58）、同步时钟（0x1C）和克隆（0x73）。保活是协议 0x08，无消息体，以同样的方式应答。

## RTT 协议（0x58），版本 3

十六字节：[0] 处是大端 u32 的 kind，[8] 处是发送方 19.2 MHz 计时数的 u64；应答把 kind 置 1 并原样带回该计时数。`rtt_protocol.build_v3`；`--no-rtt` 关闭它。

## 同步时钟协议（0x1C）

由主机控制的一个网格时钟。请求：[0] 是 u64 计时数，[8] 为零。应答：[0] 原样返回计时数，[8] 是以毫秒计的网格时钟 u64。站点从收到加入响应起每两秒请求一次，并加上往返时间的一半。克隆协议的时钟就是这个时钟；主机若在加入方自己的运行时长上收到克隆时钟，就会释放该克隆并离开。`pokeldn.ldn.sync_clock`。

## 可靠协议（0x7C），游戏数据所在之处

Pia 5.11 的头是 24 字节；序列 id 从 0xFFFFF82F 开始。

    0x00  1  flags
    0x01  1  stream id, 3 for the game, 0 on an acknowledgement
    0x02  2  payload size, big-endian
    0x08  4  sequence id, big-endian
    0x0C  4  the next sequence id expected from the peer
    0x18     the payload

确认就是只有头部。`pokeldn.ldn.reliable3`。

## 克隆协议（0x73）

`nn::pia::clone::CloneProtocol`（`PiaCommon-5_11_4`）承载对端同步。每条消息都以版本 3、一个类型字节（高半字节是结构，低半字节是变体）和发送方以大端 u16 表示的帧计数器开头。

### 时钟同步，最初两秒

双方每秒约发 5 个时钟请求（类型 0x11，18 字节，`0x51f9b0`），并以应答回复（类型 0x21，22 字节，`0x51fab0`）：

    clock request                              clock reply
    [4]   4  sender message count              [4]   4  sender message count
    [8]   2  destination bitmap                [8]   2  destination bitmap
    [0xA] 8  sender system tick                [0xA] 4  sender clone clock, ms
                                               [0xE] 8  the request's tick, echoed

消息计数从 1 起，统计发送方的请求、应答和参与消息。位图是 `1 << station index`。克隆时钟为 0 的应答会让零售游戏主机一直请求下去。

### 参与

在十个请求被应答之后，加入方发送一条参与消息（类型 0x31，10 字节，位图 0x0003）；主机应答 0x33 并发来自己的一条，加入方再应答 0x33。之后时钟应答变为 0x22，时钟请求停止。

### 克隆元素

一个克隆由克隆类型（1 到 4）、所属站点（0xFD 表示无）和一个 u32 克隆 id 共同标识。两个站点各自发布自己的副本。

    every command message   [4] u8 clone type, [5] u8 owning station, [8] u32 clone id
    types 0x81 to 0xc4      [0xC] u32 message count, [0x10] u16 destination bitmap, then fields
    types 0xd1 to 0xf4      [0xC] the data

低半字节是命令令牌加一：1 宣告、2 请求、3 结束、4 加锁。`0x51c110` 通过表 `0xf769c4` 分派高半字节：

| 类型 | 附加内容 | 长度 |
|---|---|---|
| 0x8N | 无 | 0x12 |
| 0x9N | [0x12] 处的 u32 毫秒时钟 | 0x16 |
| 0xaN | 时钟，[0x16] 处的 u8 计数 | 0x1a |
| 0xbN | 时钟，[0x16] 处的 u32 参与者位图 | 0x1a |
| 0xcN | 时钟、计数、[0x1A] 处的位图 | 0x1e |
| 0xeN | [0xD] 处的 zlib 流 | 确认状态 |
| 0xfN | [0xD] 处的一个字节、[0xE] 处的 zlib 流 | 带数据的状态 |

zlib 流解压后是一条记录，tag 为 0x20：

    0x20 0x06 u16 clone id  0x01  0x00                               empty copy
    0x20 len  u16 clone id  0x03  u8 station  u16 0  u16 participants  u32 clock  data
    0x20 0x0A u16 clone id  0x05  u8 the station acknowledged  u32 clock

`clone.pack_record` 能复现每一条抓到的流（一次压缩、一次同步刷新、一个末尾空块）。

| 交互 | 消息 |
|---|---|
| 拥有者宣告 | 0xa1 和 0xb1；对端在数据之前应答 0xa2 和 0xc1 |
| 接管 | 对端用 0x91 应答 0xa1 |
| 数据 | 拥有者的 0xf3；对端的 0xe3，携带同一时钟 |
| 释放 | 0x83；0x84 确认 |
| 离开克隆会话 | 0x32；0x41 应答 |

0xa2 携带网格时钟和计数，克隆类型 4 上计数为 1、克隆类型 2 上为 0。0xaN 的 `0x17..0x19` 字节是栈残留，没有接收方读取（`01 2808ab`）。克隆类型 3 和 4 的 0xa1 处理函数（`0x522a60`）会以 0xa2、0x91 或什么都不回；针对未知克隆的 0xa1 会引出 0x91。`0x51c110` 在遇到目标不符、消息计数不高于发送方上一条（`0x51c1e0`）、长度或类型越界时静默丢弃。当协议的待处理掩码 `+0xc0` 清空时，参与握手完成。

### 克隆 0 这一对

克隆类型 3 上克隆 0 的拥有者用 0xa1 和 0xb1 宣告它，并且只有在收到对端的 0xa2 和 0xc1 之后才发布。应答丢失的主机会让游戏主机停在「vous allez bientôt être connecté」；`bin/lgpe_host.py` 每 110 ms 重发这一对，最多 20 次，直到收到 0xa2、0xc1 或 0x91。

### 宣告的目标字段决定什么

首次宣告某个克隆的 0x81 携带整个网格（0x0003）；它后面的 0xa1 只携带对端（0x0001）。若 0x81 上给的是对端位图，对端既不会应答 0xa2，闸门 `0x11b080` 也就永远不会放行。

### 可靠协议上的游戏消息

`0x7c` 上的每条消息都是一个 16 字节的头加一个消息体：

```
+0x00  4  kind: the channel id
+0x04  4  body length: 0x168 kind 1, 0xe8 kinds 2 and 4, 4 kind 3
+0x08  4  step, counting every message a station sends from 1
+0x0c  1  tag, 0 on every trade message
+0x0d  1  destination station index, 0xff for every station
+0x10     the body
```

`0x116f30` 构建头部；交换的发送方走 `0x4d94e0`。接收函数 `0x1171d0` 取队列中第一条 step 等于本站下一个值的消息，丢弃发往别处或类型未注册的消息，而把类型或 tag 不同的消息留在队列里，挡住它后面的一切。

kind 是该会话的一个从 1 开始的 u32 计数器（`0x116e80`）给出的通道 id，同时最多注册 16 个。一次交换注册 1（交换会话）、2（提供）、3（提交）和 4（交换后存档重建的提供对象）。每次注册都会宣告一组克隆，所以克隆 id 与通道 id 并不相同。死通道每帧都会被压实，因此一个席位大约只占用四个，可以无限连续交换。

kind 1，消息体 0x168，身份：存档的 MyStatus 块（PKHeX 的 `MyStatus7b`，名字为 UTF-16LE），由两个站点在任意一方收到任何东西之前发出：

```
+0x00  4  trainer id, then secret id
+0x04  1  version: 42 Pikachu, 43 Eevee
+0x05  1  gender
+0x35  1  language
+0x38 26  trainer name; --trainer-name on both launchers
+0x52 16  Pokemon name
+0x90  4  the trade lock
```

为接收方玩家制作的礼物会从这里读训练家（[为接收方玩家制作](gift_simulated.md#made-for-the-receiving-player)）。`pokeldn.lgpe.reference` 自带一份训练家为 `POKELDN` 的礼物；`--our-trainer` 替换它的 id 对。

kind 2，消息体 0xe8，提供：当站点已发布的状态字到达 2 时发出，之后玩家每改变一次选择，就在新的 step 下再发一次。新的 step 会被应答；重复的 step 是重传。若用一个新的 step 而不是它自己的 step 去应答提供，就会开启一轮没有结束的新回合。发送方是队伍提供对象（`0x349bf0`，位于 `mgr+0x68`），`0x34a3d0` 在交换状态允许时于每次选择变化后重新填充它。

kind 3，消息体 4，提交（[提交与交换锁](#the-commit-and-the-trade-lock)）：每个站点发一个 1，其中一个在收到对端的 1 后发一个 2。收到 2 即提交；1 之后的任何其他消息体都被忽略。

kind 4，消息体 0xe8，搭载正常存档在其存档 3000 ms 之后、交换演示之后重建的提供对象：先是站点的第一个槽位，然后每选一次一个。它开启下一次交换。

| step | kind | 消息体 |
|---|---|---|
| 1 | 1 | 身份 |
| 2 | 2 | 提供，每次选择再发一次 |
| 5 | 3 | 提交，1 |
| 6 | 3 | 提交，2 |
| 7 | 4 | 第一个槽位，每次选择再发一次 |

从 0 开始计的第 r 次交换，在 kind 2 + 2r 上提供、在 3 + 2r 上提交、在 4 + 2r 上结束。它的队伍克隆是 2 + 3r 和 3 + 3r，提交克隆是 4 + 3r。

| 启动器 | 连续交换 |
|---|---|
| `bin/lgpe_host.py --next-offer` | 用下一条记录应答之后每次交换的选择 |
| `bin/lgpe_join.py --offer ...` | 用下一条记录应答游戏主机的 kind 4；最后一条之后再不应答 |
| `bin/lgpe_host.py --lead` | 为 `bin/lgpe_join.py` 扮演游戏主机的角色；`tests/test_esp32.py` |

两个启动器都在 2 交换完成时写出收到的记录；撤回的提供不写任何东西。

kind 2 和 4 的消息体是 232 字节的盒结构：第 7 世代的布局套上第 6 世代的加密，从 +0x08 起的四个 56 字节块按 `((ec >> 13) & 0x1F) % 24` 置换，并与以加密常量为种子的 LCRNG 流异或。`pokeldn.lgpe.pb7`。游戏主机不校验就保存它：一只异色、100 级、隐藏特性的百变怪，各项 IV 均为 31、各项 AV 均为 200，在概要界面上显示如常。

### 什么闸住游戏自己的第一条消息

连接交换对象的状态机是 `0x349200`（跳转表 `0xf4e994`，基于 +0x68）。

| 状态 | 做什么 |
|---|---|
| 3 | 宣告克隆 1 的集合（`0x11aec0`），置 4 |
| 4 | 等待闸门 `0x11b080` |
| 6 | 在没有网络输入的情况下发送 kind 1 |
| 7 | 统计 kind 1 消息，包含自己的回环；到两个时进入 8 |
| 8 | 终态；界面显示已找到玩家 |

当 +0x90 的 SendClone 和 +0x1258 的 SharingClone 的已确认集合 `clone+0xA8` 包含每个参与站点、每个队伍克隆的完成字节 `+0x110` 都已置位、且 +0x1430 的站点索引不是 0xFD 时，闸门才放行。一个站点的位只有通过来自该站点的、克隆类型 2 上的 0xa2 才能进入 `clone+0xA8`。

`0x11aec0` 在一帧内宣告一个站点的克隆集合：克隆类型 2 上的 `0x81`、类型 4 上的 `0xa1` 和类型 1 上的 `0xa1`。克隆 id 2 和 3 在 id 1 之后约 3.2 s 由交换调度器 `0x886530` 发出，而它只在模式字 `+0x8C` 为 3 时发布；那个 3 是谁写的仍然不明。

### 把零售游戏主机托管到它的交换界面

- 本地协议的消息体以小端携带主机的常量 id；若用大端，游戏主机无法解析发送方，会停在状态 7。
- 更新会话在会话变化时发出，之后再多发一次，从不按定时器发送。
- 主机在发布克隆 0 的那一帧宣告克隆 1；游戏主机约 31 ms 后宣告自己的，等待的主机会输掉这场竞争，角色随之互换。
- 应答对端宣告主机所拥有的克隆的 0xa2，要携带对端 0xa1 的时钟；若用主机自己的时钟，游戏主机会永远重新宣告。
- 两个站点都要用自己的一份副本应答每一次克隆类型 2 的发布。
- 主机必须在克隆类型 4 和 1 上发布克隆数据，否则加入的游戏主机会一直停在搜索界面。

### 一次接管必须携带的序列

`0x520c30` 在宣告时把一个序列分配到 `+0x10C`；完成函数 `0x520ce0`（一个 `0xa2`）只在值等于 `+0x10C` 时才置 `+0x110`，而 `0x520d30`（一个 `0x91`）只解除链接、不置位。该值是对方站点针对该克隆最近一次 `0xa1` 的时钟。用加入方自己的时钟构造的 `0xa2` 会错过，状态字永远离不开 4。入站的 `0x82` 同样会分配序列，所以用一串 `0x82` 去应答每次重新宣告，会无休止地制造序列。

### 加入方对每个克隆跑一次的接管交互

接管会取消对端的宣告，并在加入方自己的时钟下宣告该克隆：

```
+0 ms   host    0x81 clone 2, 0x81 clone 3, dest 0x0003
        host    0xa1 x2 per clone                        clock 0x197e, the host's
+5 ms   joiner  0x82, 0x91 x2, 0x82, 0x91 x2, 0x84 x2    echoing 0x197e
+75 ms  joiner  0x81 clone 2, 0x81 clone 3, 0xa1 x2 each clock 0x19c1, the joiner's own
+102 ms host    0xa2 per clone                           clock 0x19c1
        host    0xa1 per clone                           clock 0x19e2, the host's own
+141 ms joiner  0xa2 per clone                           clock 0x19e2
```

加入方对每个克隆只接管一次。之后每次重新宣告都只得到一条携带该宣告时钟的 `0xa2`，位于加入方站点下的克隆类型 2 上，载荷为 `<clock> 00 00 00 02`；第二次接管会让对端无限制地重新宣告。

只针对对端的重新宣告会引出对端在克隆类型 1 上的 `0x82`，而它又引出主机的类型 4 副本，游戏主机以 `1 1 1` 应答。若主机收不到针对提交克隆的 `0x82`，就会带着已保存的交换锁停在确认界面；`pokeldn.ldn.clone` 每 100 ms 重发一次只针对对端的 `0x81`，最多 20 次，直到 `0x82` 到达。

### 一次交换走过的两条克隆记录

克隆类型 2 副本的 20 字节数据：

```
+0x00  4  state: 1 a vote, 2 a vote withdrawn, 4 a forced leave
+0x04  4  argument, 1 on selection and 2 on confirmation
+0x08  4  a counter, incremented on each call
+0x0c  4  the station's own step
+0x10  4  the trailing word
```

克隆类型 4 副本的 32 字节数据是会话主机（权威方）的视图：

```
+0x00  4  A, the agreed argument
+0x04  4  B
+0x08 16  per station index: the counter of the vote it last saw withdrawn
+0x18  4  the station's step
+0x1c  4  the trailing word
```

权威方 `0x11b6c0` 只有在每个站点都针对当前尾字以参数 X 发布状态 1 时才把 A 移到 X，同时发布 A 和加一的尾字；状态 4 则立即移动 A。对处于状态 2、且参数与 A 不同的站点，它记录计数器并把尾字继续推进。副本只会被时钟严格更新的记录替换；`pokeldn.ldn.clone.Participant.record_clock` 让每条记录的时钟保持在上一份之上。主机在类型 4 上发布 32 个零，会让游戏主机停在「communication en cours」。

交换界面的状态（`0x34a300`）由 A 和本地状态得出：

| A | 本地状态 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| 0 | 0 | 1 | 1 | 0 | 0 |
| 1 | 2 | 3 | 3 | 0 | 2 |
| 2 | 4 | 4 | 4 | 4 | 4 |
| 3 | 5 | 5 | 5 | 5 | 5 |

状态 4 开始同步存档，状态 2 回到选择，5 表示对端离开。

被提供的队伍克隆走过 `1 1 1`、尾字 1，然后 `x 2 2`、尾字 2。比它大一号的提交克隆先接下前两个，然后是一个零：

```
+0 ms     type 4 data, 32 zeros, with the announcement
          the peer publishes 1 1 1 step 0 once its player has confirmed
          1 1 1 step 0                 the host's own confirmation
+30 ms    1 1 1 step 1                 type 4 data 1, zeros, step, 1
+8 ms     the peer answers 0 1 1 step 1
+27 ms    0 1 1 step+1 1               the offered clone goes 0 2 2 step+1 2,
                                       and the kind 3 carrying 1 goes under that step
+3 ms     the peer's kind 3 carrying 1
+63 ms    kind 3 carrying 2 under the next step, every copy republished under it
after the trade demo and the normal save:
          two more clones announced, 32 zeros on type 4; the peer publishes 0 0 0 on each
then      kind 4 under the next step
```

只有当类型 4 副本的第一个字是 1 时，对端才应答尾字 1。游戏主机宣告每个克隆并先投票；加入方若接管每个克隆，并在自己的状态字下重新发布主机的头三个字和尾字，就能完成这次交换。

在确认界面再按一次 A 会撤回投票：在 `1 2 2` 之后是 `2 2 3`。以 A 2 应答它，会在未完成交换的情况下提交交换锁（[未解决](lgpe.md#unresolved)）。应答 `1 0 0 3 0 0 step T+1` 会让游戏主机回到选择；A 0 下撤回的选择 `2 1 4` 得到 `0 0 0 4 0 0 step T+1`。`bin/lgpe_host.py` 就是这样应答的；`tests/test_lgpe_host_withdraw.py` 让这两种情形都跑过游戏的代码。

### 交换动画

游戏主机在自己的 step `0e` 之后播放交换动画，其间不发送任何交换载荷。从该 step 起：动画约在 1.7 s 开始，收到的宝可梦约在 15.3 s 出现，游戏主机的类型 4 载荷（248 字节）在 27.0 s 到达，玩家约在 28.8 s 拿回控制权。

### 提交与交换锁

交换锁是 MyStatus `+0x90` 处一个以秒为单位的 u32 倒计时（`savedata.bin` 的 `0x1090`；setter `0x1c9d40`）。一次交换的同步存档把它置为 600，并在提交交互之前提交一次；交互完成后再把它提交回 0。交换菜单的检查 `0x9765f4` 在它非零时拒绝交换（`0x976634`，消息 `0x0248810f825b1fee`）。只有在游戏处于前台且计入游戏时间时，锁才会倒计时，每秒一秒，每次更新至多一秒。

`0x347190` 构建三种存档序列之一：正常存档、同步存档、致命错误。一次交换使用同步存档（更新函数 `0x838070`，跳转表 `0xf867c4`）：

| 状态 | 做什么 |
|---|---|
| 0 | 等待 `SaveThread`（已提交 600），决定本机是否发送那个 2（`0x838660`），应用收到的宝可梦并在内存中把锁清零（`0x838800`），启动 `FirstSaveThread` |
| 1 | 等待 `FirstSaveThread` 写完，然后随机延迟 `2000 + r % 6000` ms |
| 2 | 注册提交通道 |
| 3 | 在提交克隆上投票 1，等待该通道的闸门 |
| 4 | 发送一条携带 1 的 kind 3 |
| 5 | 接收对端的 kind 3；消息体不是 1 就中止；发送方站点发一个 2 |
| 6 | 收到 2 即表示提交；任何其他消息体都被忽略 |
| 7 | 等待 `FirstSaveThread` 提交 |

没有任何状态带超时。在状态 0 结束到那个 2 之间记录到的任何网络错误都会中止：`FirstSaveThread` 不提交，存档保留 600，调度器抛出致命错误 `error_fatal_save`（“An error occurred. You couldn't trade Pokémon. Press the HOME Button to end the game.”，标签 id `0x191615296121e064`，位于 `common/message_error.dat`），游戏从此不再返回。提交期间对端离开网格也会记录这样一个错误。

| 对端的行为 | 后果 |
|---|---|
| 权威方发布 A 2 | 游戏主机提交 600；权威方欠下整个提交交互 |
| 第一条携带 1 以外内容的 kind 3 | 中止，锁已置位 |
| 在接收方注册提交通道之前发出的 kind 3 | 被丢弃；状态 3 的投票会把它压住，直到双方都注册完毕 |

`0x838660` 决定由谁发送那个 2：若一方交出急冻鸟、闪电鸟、火焰鸟、超梦、梦幻、美录坦或美录梅坦来换任何其他宝可梦，就由它发送；反向则不由它发送；其余情况由会话开始时担任主机的站点（`mgr+0x128c`）发送。

`0x838800` 把收到的宝可梦写到本方提供的盒槽位上，并施加交换的副作用：图鉴登记、通信进化（方式 5 总是成立，方式 6 需持有道具；方式 7 是盖盖虫与小嘴蜗，永远不会匹配，因为到达的副本被同时当作两只宝可梦传入；方式 6、19、20 会清空持有道具），以及游戏记录 476（本地交换）或 477（联网状态下的交换）。

### 交换调度器

`0x886530` 从菜单运行链路直到其退出，通过 `0xf87bc4` 对 `[obj+0x68]` 做分支：

| 状态 | 做什么 |
|---|---|
| 0 | 初始化；交换菜单进程写入模式字 `+0x8c` |
| 1 | 模式 1 或 2 开始连接对战，随后到 6；模式 3 等待队伍提供对象就绪；网络错误转到 8 |
| 2 | `[obj+0x100]` 为 5，即交换界面的继续，开始同步存档；其他值转到 8 |
| 3 | 等待同步存档；结果为 2 时抛出致命错误；否则销毁提供对象并开始交换演示 |
| 4 | 释放演示，进入状态 5 |
| 5 | 把收到的宝可梦写入盒槽位，开始正常存档，进入状态 7 |
| 6 | 进入状态 8 |
| 7 | 等待存档；结果为 1 转到 8，其他转到 1 |
| 8 | 销毁提供对象并离开 |

存档进程在 `obj+0x178` 处得到一块空间：

```
+0x00  save type: 0 sync save, 1 normal save, 2 or 3 fatal error
+0x04  result: 0 done, 2 aborted, 1 the link ends
+0x08  box index of the own offered Pokemon
+0x10  the received Pokemon
```

正常存档在其 `SaveThread` 之后等待 3000 ms，然后在新通道上重建队伍提供对象。调度器从状态 7 回到状态 1，因此一个席位可以一次接一次地交换。交换菜单的选项 1（交换）存模式 3；选项 2 和 3 存 1 和 2，即单打和双打连接对战，它们各自注册带 tag 1 和 3 的通道，并计入 `local_btl_single_cnt` 和 `local_btl_double_cnt`。交换则计入 `local_trade_cnt`（`0x1dc`）或 `net_trade_cnt`（`0x1dd`）。

### 加入方离开

游戏主机按 Retour 退出时，在被提供的克隆上发布状态 4，参数先是 0 后是 3；主机对每一次都以头三个字为零、尾字加一、并把该参数作为类型 4 副本的第一个字来应答。双方释放各自的克隆（0x83，由 0x84 应答）。一旦它的克隆协议空闲（[离开前的等待](#the-wait-before-leaving)），游戏主机就在网格协议的可靠端口上发送网格离开请求 `04 01`。

它应当收到可靠确认，以及不可靠端口上的离开响应 `08 00`（网格主机的索引）。`LeaveMeshJob` 每 40 ms 重发该请求，最多 5000 ms。收到 `08 00` 后，游戏主机发送自己的断开请求，并在 0.1 s 内取消认证；若无人应答，它在 5.0 s 时取消认证。Retour 之后，主机会发送类型 3 的站点断开请求；游戏主机以类型 4 应答。

游戏主机对加入方的离开请求连答两次 `08 00`，然后每 0.3 s 重复一次本地协议的开始主机迁移（类型 0x13）。加入方的断开请求会把主机的玩家送回菜单。`bin/lgpe_join.py --leave-after SECONDS` 执行该退出（`pokeldn.lgpe.leave`）；`--stall-leave`（默认 5）在任何 kind 3 之前有投票未达成一致时执行它，`--hold-after-trade N` 在最后一条排队的交换之后 N 秒执行它，而在交换之外的 `--connect-seconds` 或 `--hold` 结束时也会执行。若无人应答，我们的离开请求会在第一次之后 5.0 s 放弃，与 `LeaveMeshJob` 的放弃方式相同。该退出不会解除交换锁。

### 主机离开

玩家按退出的游戏主机会发布状态 4、参数 3，释放自己的克隆，并在空闲后发送网格迁移开始 `44 00 01`（主机索引、下一任主机的索引），每 45 ms 重传一次，最多 5000 ms，直到每个站点应答 `48 <index>`。随后它广播一条携带主机迁移状态 1 的更新会话，并每 301 ms 重复一次开始主机迁移（类型 0x13），直到没有其他站点连接或已过 10000 ms，然后销毁网络（八个 LDN 断开帧，原因 3）。`bin/lgpe_join.py` 应答该 ack 和 `48 01`，并在第一个 0x13 上离开（`pokeldn.lgpe.leave.host_departure`）。

`bin/lgpe_host.py` 在 `--seconds`、`--hold-after-trade N`（游戏主机对最后一条排队交换给出结果之后 N 秒）和 Ctrl-C 时以同样的方式离开（`pokeldn.lgpe.leave.HostLeaver`）：状态 4、在被提供的克隆上参数 3、每 100 ms 重发一次释放，最多 2.5 s，直到每一个都被确认，然后是迁移开始，最后是更新会话和开始主机迁移。这两条消息与录到的逐字节相同。游戏主机离开后，或 20 s 之后，它停止网络；再按一次 Ctrl-C 会立即停止。

### 离开前的等待

拆除步骤 `0x116bc0` 结束克隆会话，并在克隆协议空闲时立即离开；否则它等待 150 次调用，约 2.5 s。当没有克隆存在未确认的数据、且每个站点都用 0x41 应答了它的 0x32 时，协议到达空闲。释放克隆 0 之后，游戏主机仍会约每 100 ms 发布一次克隆类型 2 的副本；对端若在克隆类型 1、站点 0xFD 上以携带发布方站点和时钟的 0xe3 逐条应答，就能让它进入空闲并在 0.3 s 内离开。若对端用自己的副本应答，则会让它等满整个等待时间。`pokeldn.ldn.clone.Participant` 在对端释放克隆 0 之后应答。
