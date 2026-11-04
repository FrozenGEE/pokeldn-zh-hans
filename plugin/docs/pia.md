---
title: Pia 层
parent: 无线层
nav_order: 1
---

# Pia 层

Pia 是任天堂的点对点会话中间件，在检查过的每款作品中都用 UDP 端口 12345。每个数据报都以魔数
`32 AB 98 64` 开头。Pia 版本决定头部布局：

| | 火红/叶绿（GBA 应用） | 晶灿钻石/明亮珍珠 | 剑/盾 |
|---|---|---|---|
| Pia 版本字节 | 15/16（6.32+） | 9（5.27-5.45） | 4 |
| 头大小 | 0x1D | 0x20 | 0x20 |
| 可变 id | 各 2 字节 | 各 4 字节 | 1 字节 + 一个半字 |
| 线上的 GCM 标签 | | 8，从 16 截断 | 全部 16 |
| 模块 | `pokeldn/ldn/pia_connect.py` | `pokeldn/ldn/pia5.py` | `pokeldn/ldn/pia4.py` |

除非某节指名别的构建，`0x01...` 地址是 盾 1.3.2 解压后的 `main`（按 `tools/switch/nso_read.py`
的布局），而 `main.bin 0x01...` 地址是 BDSP 1.3.0 的。

## 数据包头

### 版本 9（Pia 5.27-5.45）

来自 `nn::pia::common::Packet::Header`：

    0x00  4  magic 0x32AB9864, big-endian
    0x04  1  0x80 (encrypted) | version (0x7F)
    0x05  4  destination variable id, big-endian   (0 = broadcast to the mesh)
    0x09  4  source variable id, big-endian
    0x0d  2  packet id, big-endian
    0x0f  1  footer size
    0x10  8  AES-GCM nonce, a monotonic counter
    0x18  8  AES-GCM tag, truncated from 16
    0x20     ciphertext: the plaintext padded to a multiple of 16

### 版本 4

来自反序列化器 `0x01774730`（要求超过 0x1f 字节）：

    0x00  4  magic 0x32AB9864, big-endian
    0x04  1  0x80 (encrypted) | version (0x7F) = 4
    0x05  1  connection id
    0x06  2  packet id, big-endian
    0x08  8  AES-GCM nonce, a monotonic counter
    0x10  16 AES-GCM tag, not truncated
    0x20     ciphertext

这两个小字段都按目标站点取值，对不特定发给某个站点的数据包为 0；零售 剑 在两者中都发 0，这能
通过每条接收路径。

- 连接 id：接收器（`0x017bdbd0`）会丢弃大于等于 2 且与它所持值不同的 id；0 与 1 通过。
- 数据包 id：接收器（`0x0185dd20`）把 0 当作无序号放行，并丢弃不高于该站点上一个序号的非零 id。

在头部之下，版本 4 与版本 9 共用会话密钥、IV 与分帧。

### 版本 11：接收器丢弃什么（朱 4.0.0）

`0x6e9744` 在任何协议读取之前就接受或丢弃整个数据包。设 `st` 为源地址处的站点，`V` 为接收器的
可变 id，`D` 为头部目标，`S` 为源：

| 检查 | 丢弃条件 |
|---|---|
| 发送方 | `st` 被标记（`+0x78`）或处于状态 3 |
| 目标 | `D >= 2` 且 `D != V` |
| 源 id | `S != 0` 指名不了任何站点、`D == V`、或 `D` 为 0 或 1 且带尾部 |
| 数据包 id，`D == 1` | 不比 `st` 在其目标 1 计数器（`st+0x60`）上的上一个更新 |
| 数据包 id，其他 `D` | 不比 `st` 在其另一个计数器（`st+0x48`）上的上一个更新 |

数据包 id 0 总是通过且不存任何东西；否则要求 `(int16)(id - last) >= 1`，所以同 id 的重发会被
丢弃。源地址处没有站点时（一次加入），不检查数据包 id。零售发送方用同一个计数器给目标 1 的
数据包编号，单播则用按接收方的计数器；两者都跳过 0。

## 消息分帧

一个 Pia 载荷携带一条或多条消息，每条以一个存在字节开头，说明后面跟着哪些头字段。省略的字段从
数据包中的上一条消息继承（`0x01853050`）。遍历只在 `0xFF` 处停止，别的都不停：`0x00` 是合法的
单字节头，继承所有字段。

| 头版本 | 读取的作品 | 读取者 | 下一条消息开始于 |
|---|---|---|---|
| 4 | 剑 | `0x01852da0` | 四的倍数处 |
| 9（5.27-5.45） | 明亮珍珠 1.3.0 | `0x159b980` | 四的倍数处 |
| 11（6.16-6.30） | 传说 阿尔宙斯 1.1.1 | `0x7484cc` | 载荷结束处 |
| 11 | 朱 4.0.0 | `0x6ed2d0` | 载荷结束处 |
| 16（6.39-7.2） | 传说 Z-A | `0x256e088`；无 `0xFF` 终止，数据包头声明其填充 | 载荷结束处 |

站点会把一串大小相同的消息捆在存在字节 0x00 之后（朱 的零填充记录分块、明亮珍珠 的可靠消息、
阿尔宙斯 的第二份 24 字节记录）。绝不要在 0x00 处停止遍历。`tests/test_pia_bundled.py` 固定了
每款作品的一个数据包。

版本 3（Let's Go 1.0.2）没有存在字节：固定的 0x16 字节头，其第二个字节必须为 1（`0x5ae7d0`），
遍历在 `0xFF` 处停止。

版本 4 的头是一个字节加五个条件字段：

    bit 0x01  +1  message flags
    bit 0x02  +2  payload size, big-endian
    bit 0x04  +4  protocol id and a 3-byte port
    bit 0x08  +8  destination
    bit 0x10  +8  the sender's station constant id

存在字节 0x7F 给出 24 字节（版本 9 为 16）；位 0x20/0x40 不增加任何东西。常量 id 是对发送方 MAC
计算的 `station_protocol.ldn_constant_id`，此处为大端，而在 Local Protocol 主体中为小端。

版本 16（Z-A）的 flags、protocol（0x04）、port（0x08）各占一个字节，位 0x10 另有自己的字节，
size 占两个；位 0x10 的字节位于 protocol 与 port 之间（`0x256df54`）。0x590 及以上的大小会被
拒绝。`pokeldn.ldn.reliable.parse_messages` 读取它。

在版本 4 与 9 中，每条消息都填充到四的倍数；数据包尾部是 `0xFF`。`pia4.parse_packet()` 解析继承，
`pia4.parse_messages()` 按发送时的样子返回每个头。当消耗的字节加上 `0xFF` 填充正好等于整个明文
时，一次遍历才是正确的。

### 压缩

一个载荷可以是一条 zlib 流，在消息 flags 中标记：5.27-5.45 为 0x20，版本 4 为 0x10。版本 5 的
可靠头有自己的 zlib 标志 0x10，BDSP 在某些游戏消息上会置它（[BDSP 的协议](bdsp_protocol.md)）。
BDSP 会在会话中途打开压缩。zlib 流的前两个字节按大端半字读，是 31 的倍数。

### 尾部

发给多台主机的数据包带一个尾部：每个接收方一个两字节的大端半字，即其可变 id 的低半部分，长度在
头部字节 0x0f。GCM 标签不覆盖它：密文是 `data[0x20 : len(data) - footer_size]`
（`pia5.ciphertext()`）。把尾部留在里面会导致认证失败，且没有其他症状。

## 会话密钥

| 网络类型 | 类 | 派生方式 |
|---|---|---|
| LDN（本地无线） | `nn::pia::local::LocalProtocol` | 在游戏密钥下的 AES-128-ECB，作用于由会话值播种的 xorshift128 产生的 16 字节 |
| LAN | `nn::pia::lan::LanProtocol` | HMAC-SHA256(游戏密钥, 一个 32 字节参数，其最后一个字节递增) 的前 16 字节（[LAN 模式](#lan-mode)） |
| NEX（互联网） | `nn::pia::nex::*` | 来自匹配服务器的会话密钥 |

### 游戏密钥

    key = cryptoKeyDataSeed                     the game's own 16-byte constant
    key[1]  = (version >> 8) & 0xFF
    key[3]  = (version >> 4) & 0xFF             version = the local communication version,
    key[7]  = (version >> 1) & 0xFF                       which the advertisement carries
    key[12] = (version >> 0) & 0xFF

`ldn_game_key()` 计算它。剑/盾 的密钥是一个 16 字节的 ASCII 字面量，原样使用，没有种子也没有
版本替换。

### LDN 会话密钥

对 Pia 5.9-5.45：

    rnd = four SEAD draws, seeded with the session parameter from the advertisement (+0x0c),
          packed little-endian into 16 bytes
    session key = AES-128-ECB(game key).encrypt(rnd)

SEAD 以 `s[i] = (prev ^ (prev >> 30)) * 0x6C078965 + i` 播种，并运行移位为 11、8 与 19 的
xorshift128（`pokeldn/ldn/sead.py`；`pia5.ldn_session_key()`）。对 Pia 6.16+，会话密钥是在游戏
密钥下对 SSID 做 AES（[无线层](ldn.md#hosting-for-an-emulator)）。

### AES-GCM IV

对 Pia 5.27-5.45 与版本 4（`ldn_nonce_crc()`、`gcm_iv()`）：

    IV[0..2]  = first three bytes of crc32( network id (little-endian) || source MAC address )
    IV[3]     = source variable id & 0xFF        from the packet header
    IV[4..11] = the packet's 8-byte header nonce

明文的 `0xFF` 填充是已知明文，可以在一个 AES 分组内检验候选密钥。

## LAN 模式

LAN 模式在普通 IP 网络上用 UDP 承载 Pia：站点通过广播找到会话，不使用无线，也不用 LDN。
`pokeldn/ldn/pia_lan.py` 实现 Pia 5.45 及更早的版本；下面每一条事实都是对着模拟的 盾 1.3.2
测得的（`tests/test_swsh_lan.py` 把它们固定在其字节上）。

| 端口 | 承载 |
|---|---|
| 30000 | 浏览请求（广播）与浏览应答（单播给请求方），不包在 Pia 中 |
| 49152-49155 | 一个站点的 Pia 数据包；一台主机占用第一个空闲的 |
| 40000 | 站点发往子网广播地址的广播可靠（0x80）消息 |

朱 4.0.0（Pia 6）在 UDP 35000 上浏览，请求 317 字节、应答 620 字节，其站点端口是 49152
（[LAN 模式](sv.md#lan-mode)）。

### 哪些作品能进入 LAN 模式

每款宝可梦作品都链接 `nn::pia::lan`，并某个模式值之后构建其 LAN 网络工厂；只有当某段代码传入
该值时，作品才能进入 LAN 模式。以下读自各作品的 `main`：

| 作品 | LAN 模式值 | 其代码传入的值 | 页面 |
|---|---|---|---|
| 剑/盾 1.3.2 | 3 | 0、2、3（在选项中按 L + R + 左摇杆） | [LAN 模式](swsh_session.md#lan-mode) |
| Let's Go 1.0.2 | 2 | 0、1 | [LAN 模式](lgpe_session.md#lan-mode) |
| BDSP 1.3.0 | Pia 插件的 LAN 设置 | 无；该 LAN 设置从未被注册 | [LAN 模式](bdsp_session.md#lan-mode) |
| 传说 阿尔宙斯 1.1.1 | 3 | 1、2 | [LAN 模式](pla.md#lan-mode) |
| 朱 4.0.0 | 3 | 1、2、3（实测：在 Combats en réseau 上按住 ZL + ZR；从交换菜单永远到不了） | [LAN 模式](sv.md#lan-mode) |
| 传说 Z-A 2.0.2 | 3 | 1、2 | [LAN 模式](za.md#lan-mode) |

### 浏览请求与应答

浏览请求是 `00`、一个 u32 大小 `0x23A`、0x23A 字节的搜索条件以及 0x12A 字节的加密质询。应答是
`01`、一个 u32 大小 `0x511`、会话信息以及 0x3A 字节的质询应答。

| 条件偏移 | 字段 |
|---|---|
| 0x00 | 最少参与者，一对 (maximum, minimum) u16 |
| 0x04 | 最多参与者，同一对 |
| 0x08 | 仅已开放、仅空缺 |
| 0x0A | 结果偏移、结果大小（各为 u32） |
| 0x12 | 游戏模式（u32） |
| 0x16 | 会话类型（u32） |
| 0x236 | 搜索标志：0x1 最少、0x2 最多、0x4 已开放、0x8 空缺、0x10 游戏模式、0x20 会话类型 |

| 会话信息偏移 | 字段 |
|---|---|
| 0x00 | 游戏模式、network id（各为 u32） |
| 0x08 | 六个 u32 属性 |
| 0x20 | 参与者、最少、最多（各为 u16） |
| 0x26 | 系统通信版本、应用程序通信版本（各为 u8；剑 中为 7 与 7） |
| 0x28 | 会话类型（u16） |
| 0x2A | 384 字节的应用程序数据，然后是其 u32 大小，位于 0x1AA |
| 0x1AE | 已开放 |
| 0x1AF | 主机地址：IPv4、12 个零字节、u16 端口 |
| 0x1C1 | 主机常量 id（u64）、可变 id（u32）、服务可变 id（u32） |
| 0x1D1 | 十六个 50 字节站点：角色（1 主机，2 玩家）、名字编码（1 UTF-8）、40 字节名字、u64 常量 id |
| 0x4F1 | 32 字节的会话密钥参数 |

站点的 id 来自其地址：常量 id 是 IPv4 地址接上端口（192.168.1.31:49153 对应
`c0a8011f0000c001`），服务可变 id 是地址的低半部分接上端口，network id 等于主机的服务可变 id。

### 质询

    challenge  = version 2, enabled 1, u64 counter, 16-byte challenge key, 16-byte tag,
                 256 random bytes under AES-GCM(AES-ECB(game key, challenge key),
                                                 nonce = receiver's broadcast address || counter)
    reply      = HMAC-SHA256(game key, the 256 bytes)[:16]
                 under AES-GCM(HMAC-SHA256(game key, reply key || request key)[:16], the same nonce)
    key param  = the first answered reply's challenge key || its request's challenge key
    session key = HMAC-SHA256(game key, key param with its last byte plus one)[:16]

nonce 以接收方子网的广播地址（`local | ~mask`）开头。主机为每次应答抽一个新的 16 字节质询密钥，
并用它和它所应答请求的质询密钥加密响应；key param 存在会话信息的 0x4F1 处，保留它所应答的第一个
请求的那一对（剑 1.3.2 `0x0178b464`）。搜索中的站点用应答的质询密钥和自己最新请求的质询密钥来
校验应答，从不用 key param（`0x0178ab2c`），并丢弃校验失败的应答。主机只应答其会话满足条件的
请求（`0x0178e590`）：游戏模式、会话类型、两个参与者范围（0xFFFF 的边界表示不限）、仅已开放与
仅空缺。

站点从浏览的应答中挑一个会话（`0x01778c80`）：条件匹配、已开放、不是加入已经失败的会话、系统与
应用程序通信版本相同，且能容纳加入的站点。一个都没有时，它创建自己的会话。

### 主持请求与 AES-GCM IV

浏览之后，加入方发送一条主持请求，协议 0x44 类型 3：`03`、11 个零字节、u32 network id。主机以
类型 4 应答：`04`、11 个零字节、network id、其站点位置。随后的站点握手与 LDN 上相同；没有
Local Protocol（0x24）。零售 剑 的主持请求携带源常量 id 0；它的常量 id 是其地址接上其站点端口，
而主机发给任何其他 id 的连接请求都不会得到应答。

进入网格后，零售 剑 发送一条会话请求，类型 5：`05`、11 个零字节、network id。主机用会话消息中
的会话信息作答，类型 6：`06`、11 个零字节、由各分片共享的一个 u32 值、一个 u16 序号、分片索引
与分片数（各为 u8）、一个 u32 分片大小，然后是最多 800 字节的会话信息。没收到它的 剑 会在 5 s
后沉默并离开网格。

站点每两秒发送一条 keep-alive，类型 7（`07` 与 11 个零字节），在会话之外以明文发送；接收器
忽略它。

    IV[0..3]  = the sender's IPv4 address
    IV[4]     = the connection id from the packet header
    IV[5..11] = the last seven bytes of the header nonce

## 协议

来自 `GetProtocolId`（每个 `nn::pia` 协议对象上的 vfunc4）：

| id | 类 | 备注 |
|---|---|---|
| 0x14 | MeshStationProtocol | 连接握手；网格的每一次确认 |
| 0x18 | MeshProtocol | 加入、更新网格、主机迁移 |
| 0x1c | SyncClockProtocol | |
| 0x24 | LocalProtocol | 主机重播的更新会话 |
| 0x54 | BandwidthCheckProtocol | |
| 0x58 | RttProtocol | 往返计时 |
| 0x68 | UnreliableProtocol | |
| 0x77 | ClockProtocol | |
| 0x7c | ReliableProtocol | 可靠滑动窗口 |
| 0x80 | BroadcastReliableProtocol | |
| 0x84 | ReliableBroadcastProtocol | 与 0x80 不同的类 |
| 0x94 | SessionProtocol | |
| 0xa4 | MonitoringDataProtocol | |

BDSP 注册九个：0x14 v2、0x18 v3、0x1c v0、0x24 v0、0x58 v3、0x68 v1、0x7c v3、0x94 v1、0xa4
v0，这把它的库限定在 Pia 5.31-5.43。

### 加入网格

站点依次通过更新会话（0x24）、连接请求（0x14）与加入请求（0x18）加入；每一者每 500 ms 重传
一次，直到被确认。

网格消息在 0x14 上用八字节的类型 5 确认来应答，即 `05 00 00 00` 加上大端的 ack id；ack id 是
该消息的最后四个字节（`mesh_protocol.ack_for()`）。主机在发送加入响应之前先确认加入请求；接收器
确认每一份副本。

### 离开会话（Pia 6）

`Session::LeaveAsync` 运行 `LeaveSessionJob`，其 LeaveMesh 步骤在非主机上启动 `LeaveMeshJob`
（在主机上启动 `LeaveMeshWithHostMigrationJob`）。它的 SendLeaveRequest 步骤发送 Session 类型 3
的离开请求，并等待主机的类型 4 响应 500 ms，最多发送四次。第一个类型 3 之前的任何延迟都属于
游戏。

| | 传说 阿尔宙斯 1.1.1 | GBA 应用（Pia 6.39） |
|---|---|---|
| `Session::LeaveAsync` | `0x72a6dc` | `0xb1060` |
| SendLeaveRequest | `0x73b898` | `0xcacf4` |

## Local Protocol（0x24）

主机大约每 100 ms 广播一次更新会话（类型 0x11），直到每个站点都确认它：

    local message header  version 1, type 0x11, size 73
    sequence id
    network id            random, not the advertisement's network id
    host variable id      the packet header's source variable id
    host constant id
    allow participating
    node 0..7             address:port and a ranking byte each
    host migration state

Pia 消息头为大端，这些字段为小端，其中的本地地址为大端。`pokeldn/ldn/local_protocol.py` 解析它
以及版本 4 的。

### 确认

确认（类型 0x21）为 20 字节（`LocalAckMessage::Serialize`，`main.bin 0x016bc0f4`）：0 处为 `1`，
1 处为类型，2 处为载荷大小半字，六个零字节，0x0C 处为序号，四个零字节。它的分帧与更新会话相同：
存在字节 `0x7F`、flags `0x11`、协议 36、端口 0、目标 0。客户端广播它；重播停止就是通过信号。

主机按发送方的地址与端口归属确认（`0x016aec94`）。客户端的可变 id 会影响 IV，因此它在一次运行
中必须稳定且非零。

## Mesh Station Protocol（0x14）

字节 0 是类型：1 连接请求，2 响应，3 与 4 断开请求与响应，5 确认，6 与 7 中继连接请求与响应
（分发器：版本 4 `0x017c5f50`，BDSP `0x0154e848`）。

### 版本 9 的连接请求

按顺序检查：

| 偏移 | 字段 | 失败时 |
|---|---|---|
| | 大小 15..949 | 丢弃 |
| 0x0 | 消息类型、连接结果、平台 id | 丢弃 |
| 0x3 | 目标常量 id，大端 u64，即主机自己的 | 沉默 |
| 0xB | 目标可变 id，大端 u32，即主机自己的 | 沉默 |
| 0xF | 协议数量，即主机自己的数量 | 沉默 |
| 0x10 | 相应数量的 (id, version) 对 | 版本偏低 → 结果 2，偏高 → 结果 3 |
| | 站点位置大小，大端 u16，0x20..0x40 | 丢弃 |
| | 站点位置 | 丢弃 |

协议 id 从不检查。站点位置的地址大小字节必须是 2、6 或 18；格式错误的位置会被读成可变 id 0。

结果码（`0x0154f5e8`）：

| 结果 | 含义 |
|---|---|
| 2 | 请求方的版本太低 |
| 3 | 太高 |
| 7 | 所有版本都匹配而第二阶段拒绝了它，或该可变 id 已是主机某个站点的（站点离开时清除，或用一个新的 id） |

大小：确认 8 字节，拒绝 15，断开响应 1。

### 版本 4 的连接请求

处理器 `0x017c62a0`：

    [0]     message type            1
    [1]     nat flags
    [2]     platform id             must be 9
    [3]     0 or 1; 1 means the request also names a target variable id
    [4]     target constant id      big-endian u64, the console's own
    [0xC]   target variable id      big-endian u32, checked only when [3] is 1
    [0x10]  nat location / protocol count
    [0x11]  the sender's station location (deserializer `0x0185ee20`)

没有协议列表。[3] = 1 时主机不应答。平台错误会以 `02 02 09 00` 加 13 个零字节作答（结果 2）；
之后的检查都是沉默。

握手，[3] 清零：

    ->   the console's connection request
    <-   the joiner's connection response, result 0, carrying the console's constant and variable ids
    ->   a type-5 ack
    ->   its own connection response, ~600 bytes, carrying the joiner's ids and the player's name,
         repeated until acknowledged

发送主机请求的类型 5 确认会停止其重传（`--ack-request`）；没有它也能接受响应。

### 连接响应要被读取必须满足什么

类型 2 与 7 到达 `0x017c6e70`。结果不为 2 的响应会被静默丢弃，除非：

| 字段 | 要求 |
|---|---|
| `[5]` 大端 u64 | 接收器自己的常量 id |
| `[0xD]` 大端 u32 | 接收器自己的可变 id |
| 站点位置 | 能解析到一个它认识的站点 |
| `[0x37]`，仅结果 0 | 小于 5 |
| 站点状态 | 为 4，在发出确认之后检查；接受时为 5 |

主机在 `[0x37]` 检查之后才确认响应：从未被确认的响应是在 id、位置或 `[0x37]` 上失败。17 字节的
响应会让 `[0x37]` 落在其末尾之后的陈旧缓冲字节里；
`station4.build_connection_response(..., min_size=ACCEPTED_RESPONSE_SIZE)` 会填充到 0x38，并在
那里写入 1。这一层的接受并不会启动其上的游戏
（[到达游戏层](swsh_session.md#reaching-the-game-layer)）。

主机自己的连接响应就是接受；它每 500 ms 带着相同尾部计数器重传请求就是拒绝；只有沉默则两者
都不是。

## Mesh Protocol（0x18）

字节 0 减一用于索引一张 129 项的表格（版本 4：`0x017c0c80`）；版本 4 缺少 BDSP 的 0x22
DUMMY_MESSAGE 与 0x23 DUMMY_ACK。

加入请求是六字节：类型 1、站点索引 253（「还不在网格中」）、一个 ack id。Pia 会重传它约十秒。

加入响应的头是十六字节。拒绝是 `[1] == 0`、`[2] == [3] == 0xFF`，原因在 [4]；否则 [1] 是站点数，
0xC 处是大端的更新计数器。站点条目：

| 版本 | 条目 | 布局 |
|---|---|---|
| 5.31-5.45 | 68 字节 | 64 字节站点位置、站点索引、大端加入顺序 |
| 4 | 64 字节 | 索引在 0x3E，没有加入顺序，最多 32 个站点 |

版本 4 在未分片时遍历 `stations` 条目，分片时遍历 [6] 个条目放进槽 [7]；5.31-5.45 在两种情况下
都取 [6]。`parse_join_response(version4=True)` 走这两条路径。

UPDATE_MESH（0x20）大约每秒一次，列出网格中有谁；BDSP 总是发送 556 字节，未用的座位为零，所以
要按 `entries` 字节遍历（`mesh_protocol.parse_update_mesh()`）。

### 主机迁移

0x18 端口 1 上的网格消息在可靠头之下到达。被指名为下一任主机的站点必须应答。

| 消息 | 字节 | 处理器要求 |
|---|---|---|
| MIGRATION_START (0x44) | `[0x44, 主机索引, 新主机索引]` | 大小 3，[1] 为网格的主机索引，[2] <= 0x1F 且不是主机索引（`0x017c1f00`） |
| MIGRATION_RESPONSE (0x48) | `[0x48, 自己的站点索引]` | 大小 2（`0x017c10ac`） |
| MIGRATION_FINISH (0x41) | `[0x41, 主机索引, flag & 1]` | 大小 3，[1] 为主机索引（`0x017c0fb0`） |

应答发往新主机，由它广播 MIGRATION_FINISH。`pokeldn/ldn/mesh_protocol.py` 构建并解析这三者。

## RTT 协议（0x58）

主机从每个站点进入网格时开始计时。版本 9 的消息是十三字节：

    u8   kind        0 = request, 1 = response
    u64  timestamp   big-endian, the sender's own clock
    u32  target      big-endian, whose reply this is; zero is accepted by everyone

版本 4 读取平铺的十六字节，并忽略十三字节的应答；`rtt_protocol.response_for_v4()` 回显请求，只
设置 kind。

站点以回显时间戳的方式应答 kind 1。主机为每个站点保留一个九样本的环形缓冲，其中位数即 RTT；
BDSP 的时间戳约以 31.36 MHz 运行。沉默的站点不会被丢弃，只是不再采样。BDSP 在未应答时每 410 ms
请求一次，每个环形缓冲填满后每 508 ms 一次（`0x015ace54`）；可靠重传间隔跟随 RTT。

## 可靠滑动窗口（0x7c）

### 版本 9（Pia 5.29-5.43）

    0x0  1  flags     1 application data, 2 message start, 4 message end, 8 is initialized,
                      16 zlib, 32 reset, 64 reset ack
    0x1  1  stream id
    0x2  2  payload size, big-endian
    0x4  2  sequence id, big-endian
    0x6  2  lowest sequence id pending ack, big-endian
    0x8  1  number of destination bits (N)
    0x9  4 * ceil(N / 32)  destination bitmap words, big-endian
            payload

0x20 及以上的 N 与 0x5a1 及以上的载荷会被拒绝。

应用程序数据标志未置位时，载荷是一份批量确认：

    0x0  1   a bitfield, 0 in every captured ack
    0x1  1   entry count, refused at 0x21 or more
    0x2  21 * n  entries: u8 stream id, u16be ack id, u16be `ack id - 1`, 16-byte ack mask

一台零售主机对序号 0 与 1 的确认：

    00 00 0017 ffff 0003 00   00 01   00 0002 0001  00 * 16

控制消息的序号是 0xFFFF。`ack id` 是收到的最高序号加一。`reliable5.build_ack_message()` 逐字节
复现它。序号 0 的数据消息不会引来确认；序号 1 的会。

### 接收器静默丢弃什么

接收路径（朱 4.0.0 `0x006f0330`，BDSP 1.3.0 `0x159fb98`）在以下情况丢弃一条消息却仍返回成功：

| 消息被丢弃的条件 | 朱 | 仍发送确认 |
|---|---|---|
| 窗口未初始化且 flags 缺少 `is initialized` | `0x6f037c` | 否 |
| 序号低于窗口基址 | `0x6f03cc` | 是 |
| 目标数非零且位图中没有接收器的位 | `0x6f0430` | 否 |
| 流 id 与初始化时锁定的不同 | `0x6f0454` | 否 |
| 环形槽位已被占用 | `0x6f0540` | 是 |

那两个仍确认的情况会让发送方读到一条针对应用从未收到的消息的确认。超出窗口末尾的序号返回
`0x4c0d`，重组超过 `0x5a1` 字节返回 `0x10407`，无法解压的 zlib 载荷返回 `0x2c03`。

一条流上的第一条消息把基址设为自己的序号。接收器还会把基址推进到发送方的 `lowest pending`
（朱 `0x6eff24`）。发送方声明的 `lowest pending` 高于其下一个序号时，在 朱 与 BDSP 上都会让
对端带确认地丢弃那些消息。确认在头部与条目的第二个半字中携带发送方自己最低的未确认序号。BDSP
在定时器上以及随数据一起，向每个仍在线的对端发送欠下的确认。

### 窗口发给谁（Pia 6）

`ReliableSlidingWindow` 的目标是按站点索引的站点指针，由 Pia 在站点加入与离开事件时填充，无需
游戏代码（朱 4.0.0：注册 `0x6ef588`）。一个站点只在其加入事件之前、离开之后、协议持有站点索引
0xfd 时，或注册拒绝它时（索引已被占用，或该站点已注册）才不在列表中。批量确认的组装器
`0x6f2138` 读取同一张列表：确认中的某一位只表明窗口注册了该站点，与发给它的消息无关。

### 版本 4

一个头类同时服务 0x7C 与 0x80（`ReliableSlidingWindow::MessageHeader`，反序列化
`0x0184e390`）：

    0x0  1  flags
    0x1  1  stream id
    0x2  2  payload size, big-endian    refused at 0x589 and above
    0x4  2  sequence id, big-endian
    0x6  2  lowest sequence id pending ack, big-endian
    0x8  1  destination count           refused at 0x20 and above
    0x9  8 * count  station constant ids, big-endian

两个版本在 count 为 0 时一致，而双方发送的每条 0x7C 消息都是如此。

接收路径（`0x01859338`）会静默拒绝：超过 `0x57F - 8 * count` 的载荷、长度不是
`9 + 8 * count + size` 的消息、与该站点窗口不符的流 id、不含接收器的目标列表，以及缺少
FLAG_IS_INITIALIZED 的第一条消息。Flags 的第 5 位是 RESET，第 6 位是 RESET_ACK，第 0 位是
APPLICATION_DATA；其余情况都是确认。

一台主机在第一条消息上发 flags 0x0F，之后发 0x07。
`reliable4.build_data_message(bytes.fromhex("610000000a00"))` 复现一台主机序号 1 的消息：
`0f0000060001000100610000000a00`。

确认载荷正好是 0x260 字节，32 个 19 字节的条目：u8 流 id、u16be ack id、16 字节掩码（处理器
`0x01859a84`；其他大小都以 0x2c03 作答）。`reliable4.build_ack_payload` 用同一个条目填满每个
槽位。盾 会让未用的槽位留着陈旧字节：只读被确认流的那个条目，否则发送方会冲垮主机的窗口，它
就不再确认。

序号不断增长而 `lowest_pending` 固定，意味着积压不断增长。

一条太长而放不进单个载荷的消息会拆到连续的序号上，第一条带 flag 0x02，最后一条带 0x04，每个
单独压缩的分片带 0x10。盾 主机的一场对战回合日志（2074 到 2657 字节）分成两条：flags 0x03 加
1407 字节未压缩，然后 0x15 加其余部分作为 zlib 流；整条消息是第一个主体接上解压后的第二个。在
模拟回环上，11 条拆分消息中有 3 条里收尾分片比开头分片先到：要按序号顺序重组，绝不按到达顺序。

## 协议 0x80，广播可靠窗口

`nn::pia::transport::BroadcastReliableProtocol`。它的消息经过压缩（版本 4 的 flag 0x10）：可靠头
带目标数 1 与一个站点常量 id，压着 0x260 的确认载荷，解压后 625 字节。确认每个站点索引一个槽位：
一台主机填 0..7，把 8..31 留为零，8 即加入响应中的 `max_total`。

## 协议 0x81，流式广播可靠传输（Pia 6）

`StreamBroadcastReliableProtocol` 把一个固定大小的块，从一台站点分块搬到每个请求它的站点
（朱 4.0.0，更新 `0x6f5360`）。它与 0x7C 和 0x80 用同一个重传期限，且在任一目标都没有 RTT
样本时从不重传。

每条消息携带一个十一字节的 StreamData 头（`0x6f60e8`）：

    +0  1  kind: 0 a receive posted, 1 the first chunk, 2 a later chunk, 3 to 6 control
    +1  1  transfer id
    +2  1  percent of the block delivered after this chunk
    +3  4  big-endian u32: the receive capacity in a kind 0, zero in a chunk
    +7  4  big-endian u32: the length of the data that follows
    +11    the data

一次登记接收会发送一条携带其容量的 kind 0；已登记容量中最小的那个限定了发送 API 所接受的块大小。
超过该大小、id 为 0xff、或没有任何站点为该 id 登记接收时，发送会被拒绝。分块大小为
`[window+0x70] - 11` 字节。

| kind | 接收器做什么 |
|---|---|
| 0，登记接收 | 记下发送方的 id 与容量，或忙时以 kind 3 作答 |
| 1，第一个分块 | 重置已收计数，然后同 kind 2 |
| 2，分块 | 放得下就复制数据；收到 percent 100 时接收完成 |
| 3，忙碌的发送方拒绝接收 | 重置该传输 |
| 4，发送方取消 | 重置该传输 |
| 5，接收方取消 | 丢掉该接收方；发送方以 kind 6 作答 |
| 6，发送方确认取消 | 重置 |

控制用的 kind 携带 id 0xff。当每个目标的窗口都确认了最后一个分块时，一次发送完成。

## 协议 0x84，可靠广播传输

`nn::pia::transport::ReliableBroadcastProtocol` 承载 剑/盾 的交换快照：

| kind | 含义 |
|---|---|
| 0x11 / 0x12 | 一个数据分片；[4] 处一个计数器，[10] 处一个容量 |
| 0x19 | 传输完成 |
| 0x21 | 一份确认，携带一段连续基址与一个「哪些提前到达」的位掩码 |
| 0x28 | 对 0x19 的应答 |

从不作答的接收器永远见不到后三个，发送方会一直重传。`pokeldn/ldn/broadcast4.py`。一台主机在
端口 0 上发送自己的传输，在端口 1 上确认对端的传输。

## 未解决

- LAN 主机对会话第一个请求的应答在递增时，是把最后一个 key-parameter 字节的 0xFF 保持在 0xFF，
  还是进位到它前面的字节。

- 零售 剑 在 17 字节连接响应的 `[0x37]` 处读到的是什么，而那里是发送方没有写的字节。

- 是什么写入了版本 4 连接请求 [1] 处的 nat-flags 字节；它在不同连接之间会变。

- 一次实时拒绝把哪个错误码交给等待的上下文（`0x01769720`）。

## 致谢

头部版本表、会话密钥的派生方式与 nonce 布局来自
[NintendoClients wiki](https://github.com/kinnay/NintendoClients/wiki/Pia-Protocol)
（[逆向一款 Switch 作品](switch_re.md)讲了如何检索它）。哪种派生属于哪种网络类型、
`cryptoKeyDataSeed` 的值以及版本规则，都是从零售作品自身的代码里读出来的。
