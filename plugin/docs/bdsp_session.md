---
title: 加入与 Pia 层
parent: 晶灿钻石与明亮珍珠
nav_order: 1
---

# 加入 BDSP 会话，以及加密层下面是什么

本页讲述一场晶灿钻石或明亮珍珠的联盟室会话，从 LDN 广播一直到 Pia mesh：密钥、Local Protocol、加入、
开设房间与离开。地址均为 1.3.0 的 `main`。

## 广播

    local_communication_id  0100000011d90000
    scene_id                4352 (0x1100) Union Room; 5120 (0x1400) Union Room with a password;
                            12608 (0x3140) Grand Underground
    version                 4
    accept_policy           ALL, 1/8
    application_data        17 bytes: Pia's 16-byte LDN header (ldn.md), then one byte

通信 id 是晶灿钻石的 title id，明亮珍珠共用（`010018e011d92000`）。该广播仅凭 `prod.keys` 就能解密
（`tools/ldn/ldn_scan.py`）。

普通房间中头部 +0x04 处的 CRC32 字段为 0。带密码的房间在该处放的是密码 ASCII 数字的 CRC32，小端
（00000000 -> `0xC0088D03`），场景 id 为 5120。主机在扫描时按场景 id 过滤，跳过保护方式与自己不匹配的
房间，并在调用 `nn::ldn::Connect` 之前把输入的密码的 CRC 与 +0x04 比较（检查点 `0x16b8890`，错误
0x6c51）。没有任何消息把加入方的 CRC 送到主持端：密码错误时主持端什么也收不到。超过八个字符的密码，
前八个留给 Pia，其余移入 `INL1` 之后的应用程序数据。`bin/bdsp_host.py --password 00000000` 开设带密码
的房间；`bin/bdsp_connect.py` 原样加入这样的房间。

## 口令

    WirelessStrongCryptoKey2021

原样使用，27 字节，既不补齐也不哈希（LDN 接受 16 到 64 字节并带显式长度），作为
`nn::ldn::SecurityConfig` 的口令；它从不参与 Pia 的加密。

## 入座

`bin/bdsp_join.py` 扫描、关联并打印参与者表；IP 由主机分配。联盟室的八个席位就是 LDN 的
`max_participants`。LDN 的席位在屏幕上什么也不显示。

- `Connect failed with status code 1` 表示关联失败；用 ESP32 板子时大约每两次尝试就有一次失败。
  先重试，再谈诊断。
- 重新进入房间会开一个新网络（新的信道、SSID 与会话参数）。
- LDN 接口上的接收端必须过滤掉自己的源 IP：广播会回环。
- 未经认证的 Pia 会被静默丢弃，席位不受影响。

### 随机匹配

独占自己联盟室会话的主机会把它关掉并重新匹配，屏幕上毫无变化，直到它独自待够足够长的时间。
`INL1.IlcaNetSession$$GameState_GameFrontBefore_LocalRandom` [0x02740640] 在每次会话更新时运行，
30 帧每秒下每渲染帧一次。只有一个站点时，它在 `25 + (0x7F & r)` 次更新之后关闭会话（0.83 到 5.07 s，
`r` 每次尝试随机），直到累计独处 270 次更新（9.0 s），此后就保留自己的网络。这些常数来自
`IlcaNetSessionSetting` 的构造函数 [0x01f46fc0]。更新链：`Sequencer$$SubscribeUpdate` 调用
[0x0202da38] -> `_orderableList` [0x01a8fed0] -> `Sequencer$$Update` [0x01a906d8..0x01a9071c] ->
`NetworkManager$$OnUpdate` [0x02253190] -> `IlcaNetSession$$Update` [0x02030a38]；`targetFrameRate`
为 30 [0x01a8ed68]，唯一的画质档（`Ultra`）`vSyncCount` 为 2（60 Hz 下 30 fps）。

## 空口上有什么

在有站点确认之前，主持中的主机会每 100 ms 把它的更新会话广播到 `169.254.x.255:12345`，
`dst_var = 0`，176 字节：

    32ab9864 89 00000000 11bac90d 0000 00 f5a83bd383ce712d 59baa5cbc320cb56 <144 bytes>
    magic    v  dst=0    src      pid  f  nonce (a counter) tag              ciphertext

版本 9，已加密：Pia 5.31-5.43。头部与传输协议见 [Pia 层](pia.md)；`pokeldn/ldn/pia5.py` 能对抓到的
数据包做逐字节一致的往返。

## 密钥层级

    cryptoKeyDataSeed  9918bd0fdcfa65779918bd0fdcfa6577    from global-metadata.dat
    game key           9900bd0cdcfa65639918bd0fc7fa6577    = seed derived with version 199
    session param      0x36dee059                          advertisement +0x0c, little-endian
    session key        7b182cb087eeabd228a2efd91a8be147    = AES-ECB(game key) over 16 SEAD bytes
    network id         b4c85cf8                            advertisement +0x00, little-endian
    source MAC         48:f1:eb:20:9b:22
    crc32(netid||MAC)  0xda291352
    IV (first packet)  da29130df5a83bd383ce712d

### 种子的位置

`INL1.IlcaNetSessionSetting` 的构造函数从 `global-metadata.dat` 里的一段字段默认值二进制块填充
`cryptoKeyDataSeed`（`<PrivateImplementationDetails>.33F804682DF9E210AABDC4D939CBCD380EC7517F`）；
该方法见[逆向分析一款 Switch 游戏](switch_re.md)。

### 公开的密钥是派生后的种子

游戏用本地通信版本覆盖种子的第 1、3、7、12 字节，1.3.0 为 199（即广播的 `app_version`）；
`ldn_game_key(seed, 199)` 给出游戏密钥。

### 会话密钥

    seed  = the session parameter (LocalProtocol+0x5b0)
    state = for i in 1..4:  prev = ((prev ^ (prev >> 30)) * 0x6C078965 + i)
    rnd   = four xorshift128 draws (shifts 11, 8, 19) -> 16 bytes, little-endian
    key   = AES-128-ECB(game key).encrypt(rnd)

`pokeldn/ldn/sead.py` 实现了 SEAD 的 RNG。

### GCM 的 nonce

由 `nn::pia::local::LdnOutputStream::vfunc3` `0x16b39c4` 构造：

    IV[0..3]  = u32be( crc32(network id LE || source MAC) )
    IV[3]     = overwritten with (packet.source_variable_id & 0xFF)
    IV[4..11] = the eight-byte header nonce

CRC 就是普通 CRC32。源 MAC 来自站点记录；数据包本身并不携带它。

## 解码后的 Local Protocol

更新会话（Local Protocol 0x24，类型 0x11）每 100 ms 重播一次，直到每个站点都确认它：

    local message header  version 1, type 0x11, size 73
    sequence id           4
    network id            8b4a3b22        random, unrelated to the advertisement's
    host variable id      11bac90d        the packet header's source variable id
    host constant id      0000 48f1 2022 9beb
    allow participating   1
    node 0..7             nine bytes each (ip, port, ranking); empty slots 0xff
    host migration state  0

主持常数 id 按小端读出后，按 LDN 的规则解包成主持端的 MAC：
`mac[2] << 56 | mac[4] << 48 | mac[5] << 40 | mac[3] << 32 | mac[1] << 24 | mac[0] << 16`。
Pia 消息头是大端，Local Protocol 的字段是小端，其中的地址又是大端。

### 确认

20 字节的确认包见 [Pia 层](pia.md#the-local-protocol-0x24)，以广播发出，`dst_var` 为 0，目的地址为 0。
第一个确认就止住更新。

## 加入 mesh

握手见 [Pia 层](pia.md#joining-a-mesh)。BDSP 的地址：

| 内容 | 位置 |
|---|---|
| 站点协议的接收分发器 | `0x0154e848`，表 `0x3e6b38f` |
| 连接请求的反序列化 | `0x0154ebd0` |
| 内部错误到结果的映射 | `0x0154f5e8` |
| 按 id 查协议版本 | `0x0159b850`，未注册的 id 返回 0 |
| 读取 mesh 消息的 ack id | `0x01542db8`（`size - 4`，大端） |
| 发送确认（8 字节，走 0x14） | `0x01550324`，MeshStationProtocol 位于 `session + 0xa0` |
| 加入 REQUEST 处理函数，主持端一侧 | `0x0154b790`、`0x0154b868` |
| 加入 RESPONSE 处理函数 | `0x0154b984`、`0x0154b9a4`；指针存于 `MeshProtocol + 0x128`（`0x0154e5c4`） |

主机注册九个协议（[实测](#measurement-methods)）：

    0x14 Station v2   0x18 Mesh v3      0x1c SyncClock v0
    0x24 Local v0     0x58 RTT v3       0x68 Unreliable v1
    0x7c Reliable v3  0x94 Session v1   0xa4 MonitoringData v0

加入响应列出两个站点，主持索引 0，加入方索引 1，`max_active` 为 8。结果 7 表示该可变 id 已经是它的
某个站点。会话协议（0x94）在 LDN 上不起作用：它的处理函数（分发器 `0x15820b8`，跳转表 `0x3e6b986`）
因为 session+0x70 为空而直接返回：`LdnNetworkFactory` 的 61 号槽位 [`0x16b30ac`] 不创建联合会话作业。
该作业在 `0x157c66c` 处创建（当 GOT `0x4c4b850` 之后的 +0x38 被置位时跳过），存于 session+0xC8，
每个站点一个 `ReliableSlidingWindow` [`0x1581938`；构造函数 `0x159dab4`；
`0x159de54(window, 2, 2, 0x94000001)`；接收槽位 10 `0x1581c98`]。合法的可靠 0x94 会被确认，然后丢弃。

## 开设房间

进入联盟室的主机会先加入任何有空位的房间，然后才开设自己的房间。`bin/bdsp_host.py`
（`pokeldn/bdsp/host.py`）以场景 id 0x1100、`app_version` 199 以及全新的 network id 和会话参数开设一个
房间。它发送的内容，每一项都按零售主持端逐字节重建（`tests/test_bdsp_host.py`）：

| 步骤 | 消息 | 分帧 |
|---|---|---|
| 有站点关联 | 每 100 ms 一次更新会话直到被确认，加入方作为节点 1 | 广播，`dst_var` 0 |
| 它的连接请求 | 一个已接受的连接响应，949 字节 | `dst_var` 0，flags 0x01 |
| 它的 mesh 加入请求 | 站点确认，然后加入响应 | `dst_var` 0 |
| 加入响应被确认 | `NetJoinData`，可靠序列 1 | `dst_var` 为加入方的 |
| 此后 | 每秒一次更新 mesh、RTT 请求、0x68 上的 `NetCharacterStateData{0, 0}` | `dst_var` 1 |

主持端必须用请求里的 tick 和以毫秒计的 mesh 时钟来回应加入方的 Sync Clock（0x1C）请求。没人应答的
加入方会在约十秒后掉认证并重新关联，屏幕上显示「communication en cours」。一旦应答，房间就是对称的，
[交换](bdsp_trade.md)照原样跑。

## 离开

两种离开都从 mesh 的可靠窗口开始（0x18 端口 1，序列 1），并等待一个在端口 0 上不可靠发出的应答，
零售 Pia 会把它发两次。mesh 分发器 `0x0154ac94`。

| 主机 | 发送 | 应收 |
|---|---|---|
| 加入方 | `04 <own index>`，然后在 0x14 上发送站点断开 `03` | `08 <host index>`，然后 `04` |
| 主持端 | 向每个站点发 `44 <host index> <new host index>` | 从每个站点收 `48 <station index>` |

应答之后，加入方在 0.2 s 内掉认证，主持端在 0.5 s 内关闭它的网络。没人应答时，加入方重试约 5 s 后
在约 9 s 离开；主持端会跑约 25 s 的迁移，尾声是每 0.3 s 一次 Local Protocol 0x13，最长 10 s
（`LocalDestroyNetworkJob::WaitUntilAllClientsDisconnection` `0x016b95b8`），只要有站点离开就立刻结束。
它的步骤：301 ms 后重发（`job+0x68`）；取消字节送到 `WaitForCancel` `0x016b9330`；只剩一个站点
（计数 `0x016b014c`，判断 `0x016b9614`）或距
`WaitUntilAllClientsReceiveUpdateSessionMessage` `0x016b936c`（`job+0x70`，判断 `0x016b9644`）已满
10000 ms，就走到 `StartDestroyNetwork` `0x016b950c`；上一个状态在 `[[protocol+0x4f0]+0x5c]`
（`0x016b0888`）或 10001 ms 后结束。离开相关的处理函数：主持端的离开请求 `0x0154b9e0`（经
`0x0154c860` 应答）、加入方的响应 `0x0154baf8`、迁移响应 `0x0154b068`；`WaitLeaveResponse`
`0x0155fd2c`、`WaitMigrationResponse` `0x015607bc`。

`pokeldn.bdsp.session.answer_departure` 构造这两个应答；`bin/bdsp_host.py` 应答离开的加入方，
`bin/bdsp_connect.py` 应答迁移的开始并在 0x13 上离开网络（`--no-leave-on-host-migration` 则不然）。
两个启动器也像主机那样离开：`--hold` 结束或收到信号时，`bin/bdsp_connect.py` 发送离开请求和站点断开；
`--seconds` 结束或按下 Ctrl-C 时，`bin/bdsp_host.py` 发送 `44 00 01`（`HostSession.close`），然后在收到
`48` 或 5 s 之后停止。`--hold-after-trade N` 在最后一次排队的交换之后 N 秒走同一条路径，且不早于其后
的 30 s——那时玩家重新获得操作权（[完成的交换](bdsp_trade.md#the-completed-trade)）。离开交换盒不发
离开消息，只在一个包里发 `NetDataCurrentFlowCancelData{0}`（0x25）和 `NetCharacterStateData{0}`。

## LAN 模式

BDSP 1.3.0 从不启用 LAN 模式。它的 Pia 来自任天堂的 Unity 插件，该插件的框架初始化（约在
`0x16886d0`）会为 LAN 模式构建 Lan 工厂（构造函数 `0x169fdcc`），而这需要一个已注册的 LAN 设置。
`INL1.IlcaNetBase.PlatformInitialize` 注册互联网设置（`0x1e13800`），`PlatformInitialize2` 注册本地设置
（`0x1e139dc`）；没有任何东西调用 `PiaPlugin.RegisterInitializeLanSetting`（`0x227caf0`）或它的 native
版本 `0x227cac0`。`global-metadata.dat` 里没有任何 C# 名字提到 LAN。

## 测量方法

- 只有当协议数量与自己的相符时，主机才会回应连接请求；扫一遍这个数量就得到 9。未注册的协议期望
  版本 0，所以二分版本号就能读到任意协议的版本。
- 判据必须是一个回复；沉默同样可能只是丢包。可靠窗口会确认它接受的数据，所以先发数据，只扫序列 id。
