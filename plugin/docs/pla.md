---
title: 传说 阿尔宙斯
nav_order: 8
has_children: true
---

# 传说 阿尔宙斯

Pokemon Legends: Arceus（标题 id `01001f5010dfa000`）是原生 Switch 游戏，Pia 6.16-6.23 被静态
链接进 `main`。地址是更新 1.1.1 解压后 `main` 里的偏移，按 `tools/switch/nso_read.py` 的排布方式
（text `0x0..0x32a5690`，rodata 从 `0x32a6000` 起，data 从 `0x401a000` 起）。

## 无线层

| | 值 |
|---|---|
| Pia 头部版本号 | 11（剑 4，BDSP 9，GBA 应用 15/16） |
| 头部大小 | 0x1C |
| 线上 GCM 标签 | 8 字节，从 16 字节截断 |
| LDN 口令 | 剑/盾的口令，即 `HGhG` 这种拼写（wiki 的 `HGHG` 行是错的）；rodata `0x3985319` |
| Pia 游戏密钥 | `p1frXqxmeCZWFv0X`，与剑/盾和朱/紫相同；rodata `0x3985308` |
| LDN 本地通信 id | `0x01001f5010dfa000`，也就是标题 id |

LDN 初始化 `0x2c1e684` 从 `x3` 取本地通信 id（在 `0x264082c` 构造），并在 `0x2c1e880` 装入游戏
密钥。头部初始化器 `0x6f0744` 把 magic 存到对象 `+8`、把 `0x0b` 存到 `+0xc`；校验器 `0x6f07d0`
检查 magic、`(byte & 0x7f) == 11` 以及长度减 0x1C 小于 0x5a5。数据包缓冲区在 `+0x30`（容量
0x5c0），长度在 `+0x5f8`；字段大小来自拷贝赋值 `0x6f0878`：

    wire  object  size  field
    0x00  +0x08   4     magic 0x32AB9864, big-endian
    0x04  +0x0c   1     0x80 (encrypted) | version (0x7F) = 11
    0x05  +0x0e   2     destination variable id
    0x07  +0x10   2     source variable id
    0x09  +0x12   2     packet id
    0x0b  +0x14   1     footer size
    0x0c  +0x15   8     AES-GCM nonce
    0x14  +0x1d   8     AES-GCM tag, truncated from the 16 the object holds
    0x1c                ciphertext, then the plaintext footer

加密路径 `0x6f09f4` 减去 footer，用 0xFF 填充到块大小，从缓冲区 `+0x4c` 开始加密，经 GCM 入口
`0x6e68d0` 以标签长度 8 写入标签（`0x6f0b24`），然后把 `0x80` 按位或进版本。

断点：套接字读取 `0x6ff6d8`，校验器 `0x6f07d0`，解密 `0x6f0b84`（在这里失败，原因不是密钥、
IV 就是标签），`LdnBackgroundProcessJob::WaitConnected` `0x7015b4`。

分派键是数据包的源变量 id：来自注册表中不存在的站的消息会被跳过，而变量 id 每个会话都会重新
生成。消息标志 `0x01` 跳过源变量 id 检查；`bin/pla_host.py` 在两个探测上都设置了它。

## 数据包加密

| | |
|---|---|
| 会话密钥 | 对网络 SSID 的一个块做 `AES-128-ECB(game key)` |
| 网络 id | `ssid[1:16]` 的 CRC-32 |
| GCM IV | `u32be(network id XOR source IP)`，然后是头部的八个 nonce 字节 |
| 头部 nonce | 每包递增的大端计数器 |
| 标签 | GCM 标签的前 8 字节 |

`0x70d61c` 导出会话密钥；`LocalOutputStream::vfunc3`（`0x711710`）构造 IV。`pokeldn/ldn/crypto.py`
覆盖 6.16 到 6.42。

## 数据包之上的协议

Pia 6.16 到 6.30 把 5.29 到 5.45 的 id 保留在会话层之下，并用一个会话协议取代站协议和网格
协议：

| 协议 | 5.29-5.45 | 6.16-6.30 | 6.32-6.40 |
|---|---|---|---|
| Net | 无 | 0x2C | 1 |
| RTT | 0x58 | 0x58 | 3 |
| 不可靠 | 0x68 | 0x68 | 5 |
| Clone，对时钟原子 | 0x74-0x77 | 0x74-0x77 | 6-9 |
| 可靠 | 0x7C | 0x7C | 10 |
| 广播可靠 | 0x80 | 0x80 | 11 |
| 会话 | 0x94 | 0x98 | 13 |
| 监控数据 | 0xA4 | 0xA4 | 15 |
| 站、网格、同步时钟、本地 | 0x14, 0x18, 0x1C, 0x24 | 无 | 无 |

`pia_connect.py` 以重新编号的 id 适配这个区段。游戏主机的加入请求列出：

    Net 0x2c v0   RTT 0x58 v3   Unreliable 0x68 v1   Clone 0x74 v0   Clock 0x77 v0
    Reliable 0x7c v2   BroadcastReliable 0x80 v3   0x81 v3   Session 0x98 v0   Monitoring 0xa4 v0

一条消息在它的载荷结束处结束；这个区段不把消息对齐到四字节（5.27-5.45 会）。填充字节在每一层
都是 0xFF：消息遍历读到存在字节 0x00 时，会把它当成一个继承上一条消息字段的一字节头部，所以
零填充会让数据包失败（`0x74419c`）。游戏主机在 `0x6f0af8` 处用 0xFF 预填它的加密缓冲区；
`0x6e6cb0` 把块大小设为 16。`pokeldn/ldn/pia6.py` 讲版本 11，`pia5.parse_messages` 读取成帧。
`tests/test_pia6.py` 固定了布局、密钥导出、两个抓到的广播，以及每一个从 `main` 读出的常量。

| 协议 | 头部目的地 | 尾部 |
|---|---|---|
| 会话、Clone Clock、可靠 | 对端的变量 id | 无 |
| RTT、可靠广播流 | 网格目的地 0x0001 | 接收方的变量 id，明文 |

在头部寻址到对端变量 id 的 0x81 消息永远到不了游戏。

### Net 协议

游戏主机在托管自己的网络时，以 `NetUpdateNetworkConnectionStatusMessage`（0x2C 类型 0x11）开场，
即 wiki 的 6.16 到 6.39 布局：

    01 11 002a          header version 1, type 0x11, payload size 0x2a
    00000002            sequence id
    eb6f                host variable id, fresh every session
    ac56011000020000    host constant id, ldn_constant_id of 02:00:ac:10:56:01
    000000004f264487    network id, the low four bytes crc32(ssid[1:16])
    01                  is network open
    0002                number of stations
    00                  is migrating host
    ...                 NetStation entries, 21 bytes each (6.39 has 22)

    NetStation  +0x00 1 migration state   +0x01 1 migration ranking
                +0x02 1 one byte where 6.39 has two (disconnection candidate, kicking)
                +0x03 18 16-byte address then big-endian u16 port (12345)

### 会话加入请求

一个 115 字节的会话类型 0：类型字节、一个协议计数、十个 `(id, version)` 对，然后是：

    +22  4   random, fresh on every repeat (docs/sv.md, The Session join request)
    +26  8   source constant id
    +34  2   zero
    +36  2   source variable id, fresh per session
    +38  1   NAT mapping
    +39  1   private-IPv6 flag
    +40  32  identification token, zero on a codeless join
    +72  1   address kind, 0 for IPv4
    +73  4   source IPv4 address
    +77  2   source port, 12345
    +79  8   destination constant id
    +87  2   zero
    +89  2   destination variable id
    +91  1   player count, 1
    +92  1   a flag, 1
    +93  22  one player record: id (two big-endian u64, 1 and 0), big-endian u32 name length 1,
             kind byte 1, the name, a single space

位置 id 是 12 字节：大端 u64 常量 id、两个零字节、大端 u16 变量 id。消息标志是 `0x01`。
`pokeldn.ldn.pia6.build_session_join` 复现它（`tests/test_pla_session_v11.py`）。

游戏主机的 `ClusterPacketReader` 门 `0x744644`（vfunc `0x98`，在 `0x743ec0` 调用）在它的站列表里
查找单播数据包的源变量 id（`0x744718`），没有匹配时丢弃它（`0x7447a8`）；发往目的地 0 或 1 且
没有尾部的数据包，或源变量 id 为 0 的数据包，跳过查找。加入请求必须发往头部目的地 0；寻址到
游戏主机的变量 id 时，它会在解密后被丢弃。

### 会话加入回复

加入方在 `0x737534` 解析 ack、在 `0x7379c0` 解析加入响应，二者由 `0x7353a0` 经类型表 `0x3973f19`
分派。每个都会丢弃四个 id 不匹配的消息：主机的 id 是请求的目的地 id，游戏主机的则是它的源 id。

ack 是类型 1、25 字节：类型、主机位置 id、游戏主机位置 id。它设置 `JoinMeshJob+0x69` 并把截止
时间 `+0x80` 延长 8000 ms。加入响应是类型 2、43 字节：

    +0x00  1   02
    +0x01  2   protocol id 0x98 and Session version, read only when status is 3
    +0x03  1   status, 1 accepts
    +0x04  8   unread on accept
    +0x0c  12  host location id
    +0x18  12  console location id
    +0x24  2   route bytes, to self station +0x90, +0x91
    +0x26  1   station index
    +0x27  2   join order, big-endian
    +0x29  2   sequence id, big-endian

分配字段不做校验（第一个加入者得到路由 `00 01`、索引 1、次序 1）。状态 1 会停止重复。当一条
类型 5 更新到达 `+0x29` 的序列并被应用时，加入完成；加入方用一个 13 字节的类型 6 作答：类型、
自己的常量 id、两个零字节、序列。

### 类型 5 的站列表更新

`0x7404a8` 在 `0x73897c` 读取它之前重组它。分片头部是 7 字节：类型、大端 u16 序列、计数、索引、
大端 u16 偏移（单分片时为 3）。正文：

    +0x00  1   05
    +0x01  2   sequence id
    +0x03  8   host constant id
    +0x0b  4   host variable id as [0000, u16]
    +0x0f  1   station count, at most 0x18
    +0x10  n   IPv6 bitmap, (count + 31) / 32 * 4 bytes, little-endian words
       ...     station entries (0x739050), IPv4 form:
    +0x00  8   constant id         +0x15  2   join order
    +0x08  4   [0000, u16] var id  +0x17  1   NAT mapping
    +0x0c  4   IPv4 address        +0x18  1   private-IPv6 flag
    +0x10  2   port                +0x19  32  identification token
    +0x12  1   route byte A        +0x39  1   player count
    +0x13  1   route byte B        +0x3a  1   participant count
    +0x14  1   station index       +0x3b  ..  player records (16-byte id, u32 name length,
                                              encoding byte, name)

IPv6 站用 18 个地址字节代替六个。主机是路由 `00 00`、索引 0、次序 0。

`0x738bc0` 按常量 id 更新或创建每个站。已加入的游戏主机随后运行 RTT、Clone Clock 和可靠广播流。

### 主机迁移

一台托管交换的游戏主机不会回应寻址到它变量 id 的加入请求，而是要求已加入的站接管主机角色：

| 加入方 | 游戏主机 |
|---|---|
| 用 0x12 回应 0x11 | 再次 0x11，`is migrating host` 置 1，然后约每秒两次 `01 40 00 00`（`NetStartHostMigrationMessage`） |
| 发送加入请求，从不回应 0x11 | 每 0.5 s 一次 0x11，然后迁移，然后 0x40，然后网络断开 |
| 用 `NetUpdateNetworkHostMessage` 回应 | 持续重复 0x40 |

托管中的游戏主机离开时总会迁移（`NetProtocol+0x248`，由其构造函数置 1）：`NetDestroyNetworkJob`
（`0x7069d0`）发送一条迁移中的 0x11，最多等 4000 ms 等每个 0x12，随后在 4000 ms 内每 300 ms
发送 0x40（0x11 未被确认时为 2000 ms），然后销毁网络。`LeaveMeshWithHostMigrationJob`
（`0x73eee4`）先最多轮询 8000 ms 找下一个主机；路由字节在 0xfd 的站永远不合格。

点名继任者的类型 7 出现于游戏主机的 WaitMember 在加入被接受之前就结束的时候，朱的情况就是
如此（[docs/sv.md](sv.md#what-decides-a-seat)）；`bin/pla_join.py --join-delay 4.5` 能引出它。
游戏主机每秒重发它，直到收到类型 8。类型 8 处理器 `0x739b08` 只接受第二个位置 id 是游戏主机
自己的 25 字节消息；当第一个 id 等于 `+0x68` 处的目标时，`0x73f0a8` 置任务的完成标志 `+0xb0`：

    08 | joiner location id (12) | host location id (12)

新主机在同一代码上创建网络来完成迁移；游戏主机加入它并以加入方身份交换。`bin/pla_join.py` 在
收到第一个 0x40 时让出席位，并在相同的代码和信道上运行 `bin/pla_host.py`，或用 `--ip-join` 走
IP（`--take-host`，默认开启）。

## 静默站检查

每次会话更新（`0x73564c`）都会列出静默时间超过 `SessionProtocol+0xd8`（10000 ms）的每个
站（来自启动设置 `+0x28c`，没有下限；Z-A 有 4000 ms 的下限）。再过 3000 ms 后主机把每个站踢出
（`KickoutManageJob`），而加入方会把被列出的主机视为已离开。盒子界面上的静默主机会在约 13 s 时
引出伙伴离开的消息。

## 游戏的读取器与前置处理器阶段

游戏在 `main+0x2ca4f30`（`0x741494`）轮询它的读取器：循环处理 0x7C 和 0x80，两者共用一个处理器
表。消息的前八个字节是一个由两个 u32 组成的处理器键；匹配到的处理器接收其余部分，未匹配的键被
丢弃。0x81 上的主机数据永远到不了这里。游戏里的九个 Pia 调用点只解析 0x68、0x7C 和 0x80；0x77
的时钟流量是 Pia 自己的。

在搜索界面，表是空的，每条消息都被读取后丢弃；处理器在流程步骤 0x1e（`0x2ca5264`）注册。

交换流程是 `0x13d5bfc`（步骤 `[flow+0xa4]`，表 `0x397c118`）。步骤 0x17 构造匹配序列
（`0x26bdcac`）；步骤 0x18 轮询它和网络菜单的页面结果（`0x13de870`）。序列的步骤：

    LoginRelayServer     looked up before the sequence is built; missing returns false
    Matching             from TradeMatchmakingConfig (0x26be354)
    DataExchangeStart    the two-round data exchange, 10.0 s deadline (0x26be3f0)
    OnCancelDataExchange
    OnSuccess            the trade scene (0x26d5f64)
    OnFailure            event 8, flow step 0x23 (table 0x397c134), the leave
    OnCancel
    Cleanup

DataExchangeStart（`0x26c5288`）在会话建立后开始，一旦至少两个站的记录到达就完成；超过 10.0 s
（`0x26c6a94`）则以 `net_contents::p2p::ErrorLeaveAnyone` 失败（vtable `0x416c628`，
`0x26c6d30`）。失败路径走 `0x13d654c -> 0x13d6384 -> 0x2c43d78 -> 0x2ca0a10 ->
Session::LeaveAsync (0x72a6dc)`，然后是错误 7 对话框；主机带着迁移离开。

`Error::Timeout` 的唯一来源是监视器 `0x2bdb754`，它在匹配的两个 WaitMember 步骤里被武装：
25000 ms（`0x2bda24c`）和 `3000 + rand % 1000` ms（`0x2c491b8`，目标是匹配记录的 `+0x22` 半字，
在代码 00000000 下为 2）。当成员数（`[Session+0xe0]`，即 Pia 会话的成员列表）达到目标时
WaitMember 完成；没有任何东西延长这个计时器。列表里存本机站以及每次被接受的会话加入各一条
（对加入方来说，是每个类型 5 的站）；仅有 LDN 关联或 Net 0x11 不计入。没有成员时搜索会在这个
计时器上重新托管，每 2.4 到 4.3 s 换一个新网络、新会话 id，所以加入方只有一个网络计时器剩余的
时间被计入。

### 数据交换

DataExchangeStart 在可靠广播流（0x81）的端口 0 和 1 上等待两轮交换：每个站用
类型 0x0f 的消息打开流，在标志 0xa0 下用 44 字节的 `0000002c ffff` 消息确认，并发送一条 74 字节
的类型 0x1f 记录，其中携带 64 字节、以 `484b6264` 开头的载荷。这一步在对端的第二轮记录到达时
完成。加入的游戏主机会主动打开自己的流，并在主机之后发送自己的记录；托管中的游戏主机会先发，
在加入方打开时发。主机回应游戏主机的打开时，会把端口 0 上的记录和端口 1 上自己的打开捆在一个
数据包里；`bin/pla_host.py` 每次加入发送一次，若在空气中丢失就以错误 7 结束。

这 64 字节载荷是 139 字节记录（`pokeldn.pla.data_exchange`）的 zlib 压缩（4 KB 窗口，级别 5），
位于 Pia 的 StreamData 头部之下的一个块里（[协议 0x81](pia.md#protocol-0x81-the-stream-broadcast-reliable-transfer-pia-6)）：

    +0x00  1   StreamData kind, 1: first chunk
    +0x01  1   transfer id, 0
    +0x02  1   percent delivered, 0x64
    +0x03  4   zero
    +0x07  4   big-endian u32 0x80
    +0x0b  128 the MyStatus block (PKHeX MyStatus8a): trainer id pair +0x1b, version +0x1f (47),
               gender +0x20, language +0x22, UTF-16LE name +0x2b

游戏只把这一个块交给 Pia（`0x26bfd28` 处的 `0x753554`）。为接收方玩家生成的神秘礼物会读取游戏
主机的训练家（`data_exchange.read_trainer`，[为接收方玩家生成](gift_simulated.md#made-for-the-receiving-player)）。

块 +0x3c 是玩家外观，取自开场 4x2 的 `grid_player` 的列 + 4 x 行（设置器 `0x1023f94`），列 2 和 3
为女性；它必须与 +0x15 的性别一致。`data_exchange.build_record` 由 `--gender` 决定发送 5（男）
或 7（女）。块 +0x50 是 1，由初始化器 `0x10230e4` 写入。

## 维持网格

RTT（0x58）是 11 字节：kind、八字节时间戳、两字节目标；目标为 0 的 kind-1 回显会被接受。

可靠广播流（0x81）承载 `pokeldn/ldn/reliable5.py` 的窗口：9 或 13 字节的头部，
然后是数据，或在数据标志清除时是 `2 + 21 * count` 字节的批量确认（类型字节，读取位 0；条目为站
字节、u16 ack id、u16、16 字节掩码）。消费者（vf13 `0x742730`）读取自己站索引处的条目，并要求
其站字节等于发送者的索引：主机确认索引 1 的加入方时会发送两个站字节为 0 的条目。id 通过
`0x74f0ec` 生效。游戏主机的 0x81 消息携带序列 1，所以主机确认 `ack_id 2`。

游戏主机用 INITIALIZED 消息打开它的流（标志 `0x0f`，序列 1）；主机数据需要游戏主机站索引对应的
目的地位图位（位 1，计数 2）。

## 游戏的可靠信道

交换之后流程到达 `0x13d5cac`，它检查 `[net+0xb8] > 1`：状态 0 经 `0x26d9170` 到 1，1 在
`[net+0x78]` 上到 2，该字段由接收处理器 `0x26da310` 在选择器 1 上设置（`0x26da3a4`）。

分派器 `0x2ca4a88` 把消息的键与每个信道的 `+0x6c` 匹配。存在两个信道：键
`00 00 00 00 00 00 00 00` 用于交换盒（`0x26d8c2c`），`01 00 00 00 00 00 00 00` 用于阶段协议
（`0x26d7aa0`）。0x7c 的端口 0 和 1 是两个可靠实例；端口 1 是信道表。

两个端口都用 `reliable5` 流打开（无位图，发往对端的变量 id，序列 1，start、end 和 initialized
标志）；每侧都确认并发回同样的东西：

    port 0    key eight zero bytes      body 0100        the host opens it
    port 1    b9 01 01 b9 02 b9 02 00 00 01              the joiner announces the zero key open

### 确认

`ReliableSlidingWindow`（vtable `0xc5b4d98`）在 vf12 `0x74ee1c` 中构造它的 ack：id 为接收窗口的
`+0x50`，其后每个持有的条目在 16 字节掩码中占一位（`0x74ef18..0x74efb8`），当 `[window+0x54]`
置位时为空。vf13 `0x74efbc` 解析它（`0x742da0`），要求 `2 + 21 * count` 字节且条目的流字节等于
`+0x36`，并调用 `0x74f0ec(window, station, ack_id, mask)`。一个发送条目是 0x5d0 字节，序列在
`+0x24`，每站待决位图在 `+0x2c`：

| 条目序列 | 待决位 |
|---|---|
| 低于 `ack_id` | 清除（`0x74f274`） |
| 等于 | 保留 |
| 高于 | 当掩码位 `seq - ack_id - 1` 置位时清除，偏移最大到 0x7f（`0x74f280..0x74f2a8`） |

| `ack_id` | 效果 |
|---|---|
| 0 | 无（`0x74f0fc`） |
| 低于基址 | 设置 `[window+0x4b8]`（`0x74f17c`，`0x74f2d0`） |
| `base + count`（`[window+0x32]`） | 释放全部 |
| 超出 | vf6 `0x74f2e8`，一个裸 `ret`：忽略 |
| `0xffff` | 应用整个窗口（`0x74f104`） |

id 是累积的；掩码是 128 位小端整数的第 n 位（`pokeldn.ldn.reliable5.build_mask`）。

接收方根据每条消息的最低待决字段移动窗口基址，ack 也算在内（`0x74c250`）。绝不要把最低待决
宣告到一条未确认消息之后：它的重传会落在基址之下并被丢弃。

`bin/pla_host.py` 和 `pokeldn.pla.joiner` 使用 `reliable5`（`SendWindow`、`ReceiveWindow`）：
保留每条 0x7c 消息直到被确认，0.4 s 后以相同序列和新 nonce 重传，最多只宣告自己的最低未确认
序列，确认连续段之后的一个，按序只交付一次。加入方的 0x81 消息每 1 s 重传一次。游戏主机在某个
端口上的第一条 0x7c 消息携带序列 1（66/66）。

游戏主机对 0x7c 和 0x81 一视同仁地重传（`0x74c9c8`），间隔为 33 ms + 1.4 x 最大往返时间
（`0x74d06c`），没有重试上限，直到收到窗口内的 ack 或该站离开。

## 端口 1 上的信道表

0x7c 的端口 1 承载信道表：每个站宣告自己已打开的处理器键，而一个站只有在对端宣告该键已打开后
才在它上面发送。

表对象（`0x2ca36f0`，vtable `0x41997d8`）保存自己的信道（`+0xa0`）和对端宣告的信道（`+0xd8`），
每个条目是一个八字节键和一个站掩码；帧轮询 `0x2ca82d0` 负责收发。

发送方把已存在的信道宣告为打开、把已销毁的信道宣告为关闭。接收方（`0x2ca9800`）在打开时把
发送方的位或进对端条目、在关闭时清除它，遇到未知键则追加一个条目；回收器擦除零掩码的条目，
离开的站的位在各处都被清除（`0x2ca90e0`）。创建信道（`0x2bcb8c8 -> 0x2ca5264 -> 0x2ca3024`）
时把表的接口保存在 `+0xb8`。每个信道发送方都询问接口槽 3（`0x2ca92e0`，经 `0x2ca9360`）对端
是否宣告了它的键，只有答案为是才发送：主机在端口 1 上沉默会让交换界面一直等待。

一条消息是游戏的带标签序列化：小于 0x80 的整数就是它自己那一个字节；0x80 到 0x83 前缀一个小端
的 1、2、4、8 字节值（写入器 `0x2661ec4`、`0x26619cc`、`0x2661f78`）。尺寸表 `0x397dfcc` 给
0x84 到 0x87 同样的宽度，0x88 四字节，0x89 八字节，0xb5 到 0xbf 一字节。0xb9 打开一个元组，
后面跟着字段计数。

    b9 01  NN  { b9 02  b9 02 LO HI  01|00 }    list of NN (key as two u32, open 1 / closed 0)

| 消息 | 含义 | 时机 |
|---|---|---|
| `b9 01 01 b9 02 b9 02 00 00 01` | 交换盒键打开 | 随端口 1 的打开，在交换步骤 |
| `b9 01 01 b9 02 b9 02 01 00 01` | 阶段键打开 | 确认之后，`0x26d7aa0` 创建它时 |
| `b9 01 01 b9 02 b9 02 01 00 00` | 阶段键关闭 | 交换写入之后 |

`pokeldn.ldn.channel_table` 构造并解析这些。主机对每个键只回应一次打开，并不回应关闭，所以它
常驻的条目服务于下一次交换。

## 交换盒

在端口 0 上零键之后，处理器 `0x26da310` 读取一个选择器和一个计数器，经 `0x397e388` 分派，丢弃
大于 7 的任何值，并且除非它的第四个参数等于 `[net+0x88]`（即伙伴）就中止。

    1   ready                0x26da3a4   sets [net+0x78]; the port-0 open body 01 00, once a session
    2   showing a Pokemon    0x26da3f0   stored at [net+0x98] by 0x26da1d8
    3   showing no record    0x26da430   -> 0x26d93c8
    4   offering a Pokemon   0x26da3b0   stored at [net+0xb0] by 0x26da23c, phase 0xbc := 3
    5   confirmed            0x26da43c   counter check, -> 0x26da2c0
    6   withdrawn            0x26da458   state 4|5 := 3, phase 0xbc := 2, counters moved
    7                        0x26da49c   counter check, phase 0xbc := 5

`0x26d9458` 发送选择器 2 并附带光标下的记录（从 `0x2b65514` 起的 0x178 字节），或对空槽位发送
无载荷的选择器 3（`03 00`）。选择器 2 和 4 携带相同的载荷；只有 4 会推进阶段。主机必须用报价
回应报价：若用展示来回应，游戏主机会显示一个空的伙伴六边形。

选择器 6 撤回一次报价或一次确认（发送方 `0x26d9898`，计数器 `[net+0xf8] + 1`）。接收分支把
状态退回 3 且不发送任何东西：回显的 6 会取消游戏主机的确认。

载荷（`0x26dac6c`，`0x26662fc`，`0x26dacbc`）：

    0x00  1   selector
    0x01  1   counter, 0 on both record-carrying selectors
    0x02  1   0xbc
    0x03  1   0x81
    0x04  2   record length, 0x178
    0x06  376 the record

九字节头部之下 390 字节，标志 0x07，序列 2。它只依赖存档，所以抓包可以重放。

记录是第八世代的实体（`pokeldn.gen8` 头部、LCG、块置换、16 位校验和），块大小为 0x58 字节：
存储时 0x168，在队伍中 0x178。解密时 `gen8.BLOCK_ORDER[(ec >> 13) & 31]` 按原样应用，加密时取反；
校验和分辨不出这两者，名字可以（昵称在 0x60，训练家名在 0x110）。0x0c 处的训练家 id 和训练家名
就是数据交换所携带的那些。

## 确认交换

交换时它发送选择器 5 和 `[net+0xf8]`。发送方 `0x26d9770` 要求状态 3 并置 4。消费者 `0x26da2c0`
置阶段 4，当状态已是 4 时分配 `[net+0xc8]`：第二个确认的站继续。选择器 5 和 7 会丢弃低于
`[net+0xfa]` 的计数器（`0x26da440`，`0x26da4a0`）。游戏主机随后在端口 1 上宣告阶段键打开，并在
阶段 5 等待，直到主机也宣告它。

tick `0x26d9094` 推进 `[net+0xb8]`：

    0     if [net+0x90] is set, 0x26d9170 -> 1
    1     once [net+0x78] is set, one store of 0x200000002: state 2, phase [net+0xbc] 2
    3, 4  while [net+0xc0]: past 1.5 s on [net+0xc8] with phase 4 or 5, 0x26d9254 sends
          selector 7, state 5
    5     finished; the save is untouched until the job below

## 执行交换的任务

这个任务（`0x26d9a90`，vtable `0x416c8f8`，更新 `0x26dc71c`，执行器 `[job+0x130]`）携带被报价的
记录 `[net+0xb0]`。

| 状态 | 动作 |
|---|---|
| 1 | 发送阶段 3（`0x26d7d8c`）；只有发送成功才到状态 2 |
| 2 | 等待主机的 `02 03`（`0x26d7e5c`） |
| 3 | 交换限制已设置并保存（vf `+0x50` `0x26dd910`） |
| 4, 5 | 发送阶段 6，等待 `02 06` |
| 6 | 交换已应用，限制已清除（vf `+0x58`） |
| 7 到 10 | 发送 `0x0b`（状态 9 中随机 2 到 302 帧之后），等待 `02 0b` |
| 11, 12 | 提交存档（`nn::fs::Commit`），发送 `0x0e` |
| 13 | 等待 `02 0e` |
| 14 | 成功（`[net+0xb8] = 6`）或失败（7） |

发送门失败会重试下一次更新；停在状态 1 或 2 的任务没有超时，并显示 `msg_ui_box_p2ptrd_09`，
“正在通信。请稍候……”。它只能通过取消请求 `0x26dc640` 结束，来源是场景监视器 `0x1109d00` 在会话
错误或伙伴离开（站计数低于 2）时，或来自模式 9。游戏主机在等待期间没有待办：主机重发它十一个
回答中任何在空气中丢失的（端口 0 打开、两次信道打开、展示、报价、选择器 5 和 7、四个阶段）。

取消在状态 `0x3ff7 >> state & 1` 中接受（0 到 2，4 到 13）。在阶段 2 到 4 被取消时，执行器先
完成存档；vf `+0x48` `0x26dd5f8` 只在 `[executor+0xb0]` 置位时写入，该标志在状态 6 完成。在
状态 1 或 2 被取消的任务什么也不写。

## 交换限制

限制是存档块 `0x96993D83` 中一个 u64 的分钟计数，位于 `[game manager+0x2b8]` 对象的字段 `+0x70`
（vtable `0x40f2048`）。块 `0x24E0D195`（字段 `+0x78`，0x2F2 字节）保存一个标志字节，然后是最近
换入的记录。

`+0x78` 处的字节标记一条已收到但尚未放置的记录：在任务状态 6 置位（`0x10251c8`，记录在 `+0x79`，
进化形态在 `+0x1f1`），由 `0x26dcc74` 清除，后者放置记录、把它登记进图鉴并保存。

| 位置 | 调用者 | 值 | 时机 |
|---|---|---|---|
| `0x26dd9a0` | vf `+0x50`，任务状态 3 | 10 | 伙伴的 `02 03` 之后，在任一记录移动之前 |
| `0x26ddaf0` | vf `+0x58`，任务状态 6 | 0 | 交换已应用 |
| `0x26dd704` | vf `+0x48`，取消 | 10 | 仅在 `[executor+0xb0]` 置位时 |
| `0x26bd5d0` | 计时器 `0x26bd434` | 减 1 | 每 60 s |

状态 3 在设置 10 之后保存。在状态 3 之前被停止的交换不会留下限制；在状态 3 与状态 6 之后的保存
之间被停止的交换，会在存档里留下 10。

计时器（`0x26bd434`）每 60.0 s 的系统 tick（`0x26bd5b4`）减一次：游戏运行十分钟即可清零。时钟
设置不起作用，游戏关闭期间的时间不计入。

当计数非零时，连接交换的伙伴菜单（`0x13d55fc`，`0x13d56ac`）会显示 `common/net` 的
`matching_win_03`（上次连接被中断），而不是警告 `matching_win_06`。

## 阶段协议

任务在键 `01 00 00 00 00 00 00 00` 上宣告阶段，该键在任务创建时注册。宣告对象保存三对
标志/半字：

    [obj+0x94] / [obj+0x96]   own announced phase, written by 0x26d7d8c (selector 1)
    [obj+0x98] / [obj+0x9a]   the peer's, on receiving selector 1
    [obj+0x90] / [obj+0x92]   written by 0x26d7e84 (selector 2), and on receiving selector 2

接收处理器 `0x26d7f90` 镜像发送方；选择器 0 中止。消息就是选择器和阶段。`0x26d7e5c(obj, n)` 在
`+0x90` 置位时返回 `[obj+0x92] == n`。

选择器 2 由主机发送：`0x26d7e84` 只在 `[obj+0x78]` 之后可达，该字段在任务创建时由 `0x26d7aa0`
设置，条件是本站是会话的主机。加入方的任务只在主机的选择器 2 上离开状态 2；只镜像选择器 1 的
主机会让交换界面一直等待。

一个站在某个端口上发起的每条消息（包括镜像）都取自己下一个序列 id；复用对端 id 的镜像会被
确认，但一旦计数出现分歧就被丢弃。

## 完成的交换

游戏主机宣告 3、6、0xb 和 0xe；主机用选择器 2 和相同的阶段逐个作答：

    <-  0x7c p0  01 03      ->  01 03   the mirror     ->  02 03   the host's
    <-  0x7c p0  01 06      ->  02 06
    <-  0x7c p0  01 0b      ->  02 0b
    <-  0x7c p0  01 0e      ->  02 0e

动画之后，盒子把主机的玩家记为原始伙伴。八个存档文件发生变化：两个槽位里的 `main`、`main2`、
`backup`，以及两个 ExtraData 文件。游戏主机随后发送一个新的选择器 2（主机用一次展示回应），以及
阶段键关闭（无人回应）。

## 同一会话中的第二次交换

一次交换完成后，场景重置交换对象（`0x26d8fd0`，在 `0x110aa04`）：任务的输入和记录被释放，任务
被释放，状态和阶段为 2，计数器 `[net+0xf8]` 归零。`[net+0x78]` 和 `[net+0x88]` 保留：下一轮从
状态 2 开始，没有新的选择器 1。场景（更新 `0x1109a68`，模式 `[scene+0xb0]`：0 盒子，5 交换，
6 伙伴离开，7 和 8 会话错误，9 离开）在会话保持的情况下回到模式 0。`0x10fb178` 清除盒子控制器
的有效标志，所以盒子会发送一次新的展示；否则它只在光标移动时发送一次。

下一个任务再次用键 1 创建它的阶段信道，并使用相同的阶段。第二次交换逐字节重复 `05 00`、
`07 00`、各个阶段和阶段键打开；只有序列 id 不同，所以按载荷去重的对端一个都不回应。回应了游戏
主机关闭的主机，会让第二个 `01 03` 卡在门里：任务停在状态 1，无超时，无限制。

## 一次交换改写了什么

一条收到的记录在这些字段上与发出的那条不同（对一条以 70 级队伍尾部发送的 50 级记录，共 23
字节）：

    0x006  2   checksum
    0x092  1   current HP
    0x0b8  26  handling trainer's name, the receiver's own
    0x0d3  1   handling trainer's language (3 French, 2 English)
    0x0d4  1   current handler, 1
    0x0d8  1   handling trainer's friendship, the species' base friendship
    0x16a  12  the six party stats, recomputed

高于等级的相遇等级会被保留。块起点是 `pokeldn.gen8` 的起点加上每个前置块八字节：昵称 0x60，处理
训练家名 0xb8，训练家名 0x110，队伍尾部 0x168。第一块是第八世代的块，但招式在 0x54（PP 0x5c），
第二块加 8，第三块加 0x10，第四块加 0x18，球在相遇日期之后。`pokeldn/pla/trade_box.py` 和
`pokemon.py` 复现游戏主机的字节。

## 选择要报价的内容

游戏读取 PKHeX 的 PA8：

| 偏移 | 字段 | 偏移 | 字段 |
|---|---|---|---|
| 0x08 | 物种 | 0x92 | 当前 HP |
| 0x0a | 持有物 | 0x94 | 打包的个体值 |
| 0x0c | 训练家 id，32 位（显示为对 1000000 取模） | 0xa4 | 成长值 |
| 0x10 | 经验 | 0xac, 0xb0 | 绝对身高、体重（浮点） |
| 0x14 | 特性 | 0xb8 | 处理训练家 |
| 0x16 | 头目标志位 | 0xee | 版本 |
| 0x1c | 性格值 | 0xf2 | 语言 |
| 0x20 | 性格（9 是 Lax） | 0x110 | 训练家名 |
| 0x24 | 形态 | 0x134 | 相遇日期 |
| 0x26 | 努力值 | 0x137 | 球 |
| 0x3e | 头目招式 | 0x138, 0x13a | 蛋与相遇地点 |
| 0x50, 0x51, 0x52 | 身高系数、体重系数、体型系数 | 0x13d | 相遇等级与训练家性别 |
| 0x54, 0x5c | 招式、PP | 0x159 | 已购招式记录 |
| 0x60 | 昵称 | 0x15d | 已掌握招式位图 |
| 0x8a | 重新学习招式 | 0x168, 0x16a | 等级、六项能力 |

在 47 条抓到的记录中，头目在 0x50 到 0x52 携带 0xff，体型系数等于身高系数，0x94 的蛋和昵称位
为清除，每条记录都携带版本 47、语言 2、sanity 0 和 affixed ribbon 0xff。`pokemon.build` 在 376
个零字节和校验和之上写入给定字段。合成的记录（异色、头目、有昵称、存档从未有过的物种）能换入
并按要求显示。加密常量和 PID 已被存档持有的记录会被存储（盒子块 `0x47E1CEAB`）；`--fresh-pid`
会重掷两者。

`bin/pla_host.py` 按顺序对每个 `(port, sequence id)` 只处理一次，并重发未确认的回答；被取消的
报价会以 `04 01` 重新报价。它在两次报价之间重读它的报价文件。

### 已掌握招式

0x15d 处的八个字节是游戏 61 个招式掌握列表上的位图；一个物种只能掌握它的 personal 条目允许的
那些（0xa8 处的 u64）。更改招式界面允许使用掌握等级（`mastery_la`）等于或低于当前等级的招式，
或位已置位的招式。

### 游戏计算的能力

`pokeldn/pla/stats.py` 复现它们。每项能力是一个成长项，取整的
`(sqrt(base) * multiplier + level) / 2.5`，加上一个基础项：HP 是截断的 `((level / 100 + 1) * base)`
再加等级，其余是截断的 `((level / 50 + 1) * base / 1.5)` 再乘性格的 110% 或 90%。倍率由成长值
加个体值偏置读出（31 及以上为 3，26 为 2，20 为 1），上限截到 10。用十二个等级 68、性格 14、
耿鬼的主机数字验证：273/210/199/322/345/220（IV 31，成长 10）和 239/136/121/322/304/133。

0xac 和 0xb0 处的身高与体重是物种平均值乘以每个系数各自的
`(scalar / 255) * 0.40000004 + 0.8`，体重用两个系数，以 32 位浮点计算（系数 111、221，平均值
150、405 得到 146.11766052246094 和 452.38031005859375）。表来自 PKHeX：`personal_la`（每条目
0xB0 字节；0x21 的位 6 标记游戏中的 264 个物种）、`lvlmove_la.pkl`、`MoveInfo8a`、`Experience`。

## Clone Clock 与 Atomic 协议

Clone Clock（0x77）消息是 18 字节：kind、序列、大端 u64 起始 tick、大端 u64 响应方时钟（毫秒）。
kind 0 是请求（非主控时忽略）；kind 1 是回复，推进 ClockProtocol `+0x5c`（0 复位，1 请求中，
2 已同步，3 主控，4 停驻）。加入的游戏主机停在 4 并发送请求；回显序列和 tick 并带上主机时钟的
kind-1 回复会让它同步。

Clone Atomic（0x74）消息是 14 字节：kind（0 宣告，1 提交，2 确认）、generation、大端 u32 元素
索引（小于 33）、大端 u64 值。只有交换场景创建元素；主机的 kind-0 宣告会引来一个 kind-2 回显，
它不填充任何槽位。

## LAN 模式

传说 阿尔宙斯 1.1.1 有一条它的代码从不走的 LAN 路径。网络启动 `0x2bb9a10` 为模式 1 构造本地
服务、为 2 构造互联网服务、为 3 构造 LAN 服务（`0x711ab4`）。模式从网络任务的 `+0x78`
（构造函数 `0x2bbe7f4`）传到那里，其唯一的创建链终结于 `0x2629258(.., mode)`；它的两个调用者
传 1（`0x2628b74`）和 2（`0x262a020`），而没有任何指针指向那条链上的任何函数。

## 托管

`bin/pla_host.py` 广播标题、口令、场景 id 和连接码；`pokeldn.pla.build_advertise_data(code)` 逐
字节复现一个零售广播（`app_version` 0，`security_mode` 1）。

    POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/pla_host.py --keys PROD_KEYS \
        --code 00000000 --seconds 240

搜索界面上的游戏主机交替地作为站扫描和在新的 SSID 下托管，约五秒一个循环。已关联的加入方保持
沉默，直到主机每 500 ms 发送一次 Net 0x2C 连接请求（`--no-net-probe` 会阻止它）。

## 加入游戏主机的网络

`pokeldn.pla.joiner` 回应一台托管中的游戏主机：

| 主机发送 | 加入方回应 |
|---|---|
| Net 0x11 | Net 0x12，回显序列，标志 `0x11`，头部目的地 0；第一次时附带会话加入请求，标志 `0x01`，目的地 0 |
| Net 0x50 | Net 0x51，回显序列，目的地 0 |
| 点名加入方的会话类型 7 | 类型 8 |
| 会话类型 5 | 类型 6 |
| 第一个类型 5 | 端口 0 上的 0x81 流打开，`0f00000b 0001 0001 01 00000001 0000000000008000000000` |
| 它在端口 0 上的 0x81 记录 | ack，端口 1 上自己的记录（标志 `0x1f`，序列 1，位图 `0x01`），然后 0x7c 端口 1 上的零键打开 |
| 0x7c 端口 0 的打开 `0000000000000000 0100` | 同样的发回，序列 1 |
| 一次展示或一次报价 | 自己的，相同的选择器和计数器 |
| 选择器 5 和 7 | 相同的；7 之后是阶段键打开 |
| 阶段键打开 | 阶段 3、6、11、14（选择器 1），每个都在主机的回答之后，然后是键关闭 |
| RTT kind 0 | kind 1，回显时间戳，最后是请求方的变量 id |

零售的加入方把它的 0x12 发往目的地 0（108/108）；寻址到主机的变量 id 时读取器门会丢弃它。
托管中的零售游戏主机会在加入方之后 0.02 到 0.04 s 用选择器 2 回应每个阶段。绝不要因游戏主机
自己的 `01 0e` 就关闭阶段键：`02 0e` 永远不来，游戏主机在离开时显示 2-AW7KA-0007 并保持限制。
`bin/pla_join.py` 在 `02 0e` 时关闭它，保持席位直到玩家退出或 `--hold` 结束（`--hold-after-trade N`
在最后一次排队的交换之后 N 秒离开），并在每次交换后忘记已回答的步骤。它大约每秒在端口 0 和 1
上重复它的 0x81 确认：

    0000002c ffff 0002 01 00000001       header: size 0x2c, lowest pending 2, bitmap 1
    00 02                                type 0 the first time, then 1; two entries
    00 0002 0001 00*16                   the host's stream
    00 0001 0001 00*16                   its own stream

`tests/test_pla_joiner.py` 扮演一个脚本化的主机；`tests/test_esp32.py` 在两块模拟板子上运行它。

## 在游戏主机上进入本地交换

    title screen, A -> Jubilife Village, the trading post -> talk to Simona (Trado in French), A
    -> "echanger des pokemon !" -> local -> the restriction warning -> an eight-digit code
    -> "Echange en reseau ! Recherche d'un partenaire en cours..."

`0x397e1b8` 处的分钟表（`30 30 60 60 ... 2160 2160`）是丢失挎包用的（`0x2686a0c`，基于网络时钟），
与交换无关。

## 广播

| | |
|---|---|
| 本地通信 id | `0x01001f5010dfa000` |
| LDN 协议 | 1：AES-CTR 广播，与剑相同 |
| 场景 id | 1 |
| 广播帧版本 | 4（GBA 应用 3，剑 2） |
| 接受策略 | 全部 |
| 参与者 | 1 / 2 |
| SSID | 16 字节，会话密钥的输入 |
| 应用数据 | 112 字节 |

应用数据是 0x5C 的系统属性块（`docs/ldn.md`，6.16 到 6.41：系统通信版本 21、应用版本 0、一个
16 字节的用户口令、玩家上限开启、一名玩家、名字为一个空格），然后是明文中的连接码：16 字节
ASCII、以 NUL 填充，然后它的长度作为小端 u32（`0000 0000` 得到 `3030303030303030`、八个 NUL、8）。

### 广播中的连接码

用户口令是连接码经 Pia 的设置器 `0x6fc454` 加密的结果：在模式 1（`+0x234`）下开启加密（会话
`+0x230`）时，它用 0xFE 填满 16 字节，把 NUL 填充的连接码拷到其上，并用 `0x6e68d0` 就地加密：
游戏密钥下的 AES-128-GCM（会话 `+0x238`，经 `0x6fc8a4` 设置），无附加数据，标签丢弃，IV 为
`key[1] key[8] key[7] key[2]`（`0x6fc4e4..0x6fc4fc`），这里是 `1emf`：

    password  = KEYSTREAM XOR (the code's ASCII, NUL-padded to 16)
    KEYSTREAM = AES-128-GCM(key = p1frXqxmeCZWFv0X, iv = 1emf).encrypt(16 zero bytes)
              = e5ab19ed742b6d40885998bf968aa166

密钥流是固定的。`pokeldn.pla` 里有 `link_code_keystream`、`user_password`、`link_code` 和
`parse_advertise_data`。设置器是 Pia 的，所以这个区段里的每个标题都这样加密
（[无线层](ldn.md)）。

其主机在其运行期间重启的游戏主机，会在下一次搜索时显示错误 2318-0006；离开交换菜单并重新
搜索即可清除。

## 离开

游戏主机退出时运行 `nn::pia::session::LeaveMeshJob`：它发送会话类型 3 的离开请求，最多
发送四次、每次等 500 ms 等类型 4 响应，然后离开网络。步骤：SendLeaveRequest `0x73b898`（写入器
`0x737ee8`，截止在 `0x73b9a8`），WaitLeaveResponse `0x73bab8`（计数器 `[job+0x6c]`，超过 3 就在
`0x73bbf0` 放弃），CompleteProcess `0x73ba54`。

    03 | u32 random | location id (12) | address kind | IPv4 (4) | port big-endian (2)
    04 | u32 random | location id (12)                          the response, 17 bytes

随机字每次都不同。类型 3 处理器 `0x738000` 用 `04`、一个新的随机字和请求的第 5 到 16 字节作答，
然后移除该站；类型 4 处理器 `0x738280` 只接受离开者自己的 id。

无人回答时，游戏主机在四次请求（约 2 s）后离开；有回答时，一次后离开。`bin/pla_host.py` 回应
每个类型 3（`tests/test_pla_host_loss.py`，该回答在 unicorn 下经过 `0x738280`）。

退出、伙伴离开消息和会话错误都会进入场景模式 9（`0x110b72c`）：它放置一条待处理的接收记录，
启动离开（`0x26be890`），取消任务，并至少等 3.0 s（`0x110b7d8`）等离开和任务，所以无论主机是否
回答，退出后约 3.7 s 野外就回来了。`Session::LeaveAsync` 唯一的调用者是游戏的离开请求
`0x2ca0a10`；第一个类型 3 之前没有 Pia 计时器（[pia.md](pia.md)，离开会话）。

一条收到的离开不会改变屏幕上的任何东西。当游戏主机在盒子界面时：

| 主机 | 游戏主机 |
|---|---|
| 网络断开 | 一秒内出现“错误代码 2318-0006” |
| 网络在线但沉默（`--leave-sends 0`） | 约 13 s 时出现“你的交换伙伴选择不再继续交换”，然后正在通信，然后 `DisconnectedByUser`，无错误码 |

`--leave-after SECONDS` 向每个已加入的站发送离开并结束运行；`--stay-after-leave` 保持网络在线但
沉默。`bin/pla_host.py --hold-after-trade N` 向每个站发送同样的离开，并在最后一次排队的交换之后
N 秒结束运行。

## 未解决

- 场景析构函数与屏幕上的野外之间那 0.4 s 由什么填充。
- 盒子代码的哪些流程调用 `0x26dcc74`（`0xc17ce0`，`0xc17e8c`）。
