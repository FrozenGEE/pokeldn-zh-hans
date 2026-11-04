---
title: 卡带与会话
parent: 剑与盾
nav_order: 1
---

# 卡带、密钥，以及坐下入座

`main` 静态链接了整套 Pia（252 个 `nn::pia` 类、2036 个虚方法）并导入 `nn::ldn`。Pia 之上游戏用 protocol buffers：`main` 为 78 组 P2P 消息各带一个 `FileDescriptorProto`（`gflnet.p2p.framework.pb`、`.block.pb`、`.sync.pb`，每个内容一个包：交换、对战、露营、团体战）。

## LDN 通行短语

    W3GoSMEn7RIIUQ89rzqBHGhGferRNb7K18ZBq2aNuj8Us9RO9Q9JYyGOZlLy8MYL

64 字节，原始形式（两份，在 `0x203ff04` 与 `0x203ff45`）；与 NintendoClients wiki 上朱/紫那一行相同，与传说 阿尔宙斯只差一个字符（这里是 `HGhG`，那里是 `HGHG`）。设置调用在 `0x006c3ec8`，长度为 `0x40`。`nn::pia::local::LdnCreateNetworkJob` 把通行短语存在 +0xC4，长度存在 +0x104，本地通信 id 存在 +0xB8；它在调用 `nn::ldn::CreateNetwork`（`0x017972bc`）之前把通行短语复制到 `SecurityConfig+4`。`LdnBackgroundProcessJob` 要求长度在 16..64 之间。

## Pia 游戏密钥

    p1frXqxmeCZWFv0X

十六个 ASCII 字节在 `0x01c3dc87`，被三处调用原样使用（就是 wiki 上剑/盾那一行）；创建/加入的调用是 `0x183fd10`，来自 `0x006ca914..0x006ca93c`。

## 读取卡带

    ./.venv/bin/python tools/switch/xci_read.py <the.xci> --keys prod.keys --type Program
    ./.venv/bin/python tools/switch/xci_read.py <the.xci> --nca 87e41bc8 --exefs 0 --extract main
    ./.venv/bin/python tools/switch/nso_read.py main
    ./.venv/bin/python tools/switch/rtti_names.py main.bin 0x1900fc0 --rodata 0x1901000:0x24da168

`main` 的 text 是 0..0x1900fc0，rodata 到 0x24da168，data 到 0x2635f38。方法见[逆向分析一款 Switch 游戏](switch_re.md)。

`/bin/message/<Language>/common/*.dat` 用的是第六/七/八世代的消息容器：第 *n* 行的键从 `0x7C89 + n * 0x2983` 开始，每个字符左旋 3 位（每行都以 `0x0000` 结尾）。`.tbl` 是一个 `AHTB` 索引，第 *i* 条就是第 *i* 行。

## Pia 4

Pia 头里写的是版本 4，形状与[Pia 层](pia.md)上那两个带都不同；它下面是 5.27 的 LDN 家族（同样的密钥、IV、封帧，只多一个字段）。`pokeldn/ldn/pia4.py` 实现了它。`pokeldn.swsh.session_keys` 是 BDSP 的推导，但不做版本替换：

    会话密钥 = ldn_session_key(GAME_KEY, application_data[12:16] 小端)
    IV       = crc32(application_data[0:4] || 发送方 MAC)[0:3] || 源 id || nonce
    tag      = 十六字节，完整校验

484 个正版包全部通过认证，每个的源 id 都是 0。还有一条路径 `0x0179bff0` -> `0x01774f40`，用会话的两个 64 位值给 AES-GCM 播种；本地交换只需要那条广播就够了。

## 入座

    POKELDN_RADIO=esp32:auto ./.venv/bin/python bin/swsh_join.py --keys PROD_KEYS --scan-only

会扫描一个主持中的界面，并把每条广播写进 `scratchpad/swsh_net_facts.json`。

| 界面 | 本地通信 id | 版本 | 场景 | 应用版本 |
|---|---|---|---|---|
| 连接交换 | `0x0100ABF008968000`（剑的） | 4 | 60001 | 7 |
| 神秘礼物本地无线 | 同上 | 4 | 65535 | |

盾用的是剑的 id；它的 `control.nacp` 列出 `LocalCommunicationId[0] = 0x0100ABF008968000`、`[1..7] = 0x01008DB008C2C000`。

那 384 字节应用数据：

    0x00  4  network id, random per session
    0x04  4  CRC32 of the Link Code's ASCII digits, LE; 0 with no code (12345678 -> 0x9AE0DAAF)
    0x08  1  system communication version, 5
    0x09  1  header size, 0x18
    0x0A  2  padding
    0x0C  4  session param, random per session
    0x10  8  zero
    0x18  2  CRC16 over 0x1A..0x180 (`0x0065dcb0`, `pokeldn.swsh.beacon.crc16`)
    0x1A  2  network version word, 12 bits, 0x0D70 (`0x006c17c0` from `0x02068848`)
    0x1C  1  bit 0 from `0x006b5c10`; set is refused
    0x1D  1  payload type, 0 for station info
    0x1E  1  page byte, 1 and 2 in turn every third publish (`0x0111aac0`)
    0x1F 266 the player profile, as in the trade snapshot at 0xAEC
              ([the protocol page](swsh_protocol.md#the-player-profile)); zero to the end

`Connect failed with status code 1` 表示关联被拒；在同一次搜索中再试一次通常就能关联上。一台正在搜索的剑会在同一个 comm id 下广播两个网络：一个是 Y-Comm 信标，场景 65535；过了第二条消息之后，再加一个匹配网络，场景 60001。停在信标上的主机 16 次加入里 0 次进到交换盒；`bin/swsh_connect.py` 只加入场景 60001，并一直重扫到它出现为止。关联之后，主机会向 `169.254.x.255:12345` 广播 Pia（每秒大约十个包）。加入的站点离开后是什么让一台主机的广播停下来，目前还没读出来。

## 一台搜索中的剑如何找到伙伴

在 Y-Comm 画面上，每台主机都在场景 65535 主持一个信标网络，并且大约每秒浏览一次（`0x006c3630`：主持走 `0x006c3840`，浏览走 `0x006c3770`，条件是来自 `0x006c4550`、`0x0183fac0` 的，只看 comm id 和网络类型）。通过 CRC 与版本闸门（`0x006c1be0`）的记录会进入附近玩家注册表（`0x0110f270`），这个注册表会丢掉自己的记录（广播 0x1F 处的设备 id 与 0x2F 处的账号 uid，`0x0111b160`），也会丢掉任何缺网络 id 与场景对的记录（`0x0110f2d4`）。这里什么都不加入。

走到连接交换、再走到普通交换，会显示两条消息，每条都等按 A。第二条之后，`0x00fba940` 调用 `SetMode(comm, 2)`（`0x01096d10`）；`0x01095f10` 依次走状态 0、5、3、4、6，状态 6 用场景 60001 调用 `StartRandomMatching`（`0x010fcff0`）（`0x01096730`）。一台上机后停在第一条消息上的主机永远不会调用 `SetMode(comm, 2)`，也就永远不会匹配。

匹配层按下面的条件加入网络（`0x006c9e70`、`0x006cb8e0`，加入是 `0x006ca1c0`）：

    场景 60001，与自己的相同
    节点数 1，低于它自己的上限 2；网络类型 2；节点数上限 8 或更少
    广播 0x04 为零：不带连接密码的搜索会拒绝带密码的
    广播 0x00 处的 u32 大于搜索方自己的
    advertise 0x00 不在本次搜索中曾加入失败的 id 之列（0x80 条）

连接密码只改变 0x04。`bin/swsh_connect.py`（不带密码）能加入带密码的主机并完成交换；`bin/swsh_host.py --code 12345678` 会被带密码的搜索加入，不带密码则永远不会。id 大的主持，所以两台都在搜索的主机只会单向配对；主持端广播的 id 接近 0xFFFFFFFF。

## 主机先说什么

Pia 本地协议 0x24，与 BDSP 相同（`pokeldn.ldn.local_protocol`）：版本 1、类型 0x11、0x30 个固定字节、八个九字节的座位、一个主机迁移字节。`allow_participating` 为真，所以主机在对方开口说 Pia 之前就把它登记进表：0 号站点是 `169.254.14.1:12345` 处的主机，1 号站点是 `169.254.14.2:12345` 处的座位。

主持端会反复发更新会话直到每个站点都确认（0x21）。只有带着对应序列号的确认才会让重播停下（在 13 毫秒内）。头字节 0x05 和 IV 的源 id 都是 0。

## Pia 会话对象

`[[0x02616a30]]`（也就是 `[0x02630f40]`），交换代码从中读站点 id 的地方，就是 Pia 的会话对象：0x270 字节，没有 vtable，由 `0x0183ddb0` 从 `0x006a8644` 一次性分配。在 LDN 上网络工厂是 `LdnNetworkFactory`，它的第 73 个槽（`0x01791080`）构造一个 0x7220 字节的 `LdnMatchmakeSession`。

| 字段 | 谁写 | 值 |
|---|---|---|
| `+0xf0` | `0x018418a0`（`0x01841918`） | 本机自己的站点 id |
| `+0xf8` | `0x018418a0`（`0x01841990`） | mesh 主机索引处的站点 id（`[[0x0262f7b0]]+0xab`）；`[obj+0xd4] == 4` 时跳过 |
| `+0xf8` | `MeshEventListener` 槽 2（`0x01843580`），事件 1 | 后端第 30 槽，在主机离开时 |
| `+0xf8` | 事件 2 | 来自 `0x017d6080` 的 id（模式 2），或后端第 30 槽（仅模式 4） |
| `+0xf8`、`+0x100` | 事件 3 | 零，当 `[obj+0xd4] != 3` |

`0x018418a0` 在创建（`0x018394d8`）与加入（`0x0183d9b0`）时运行。`+0xd4` 的模式在普通 LDN 创建与加入时是 2；只有 `LanMatchJointSessionJob` 与 `NexMatchJointSessionJob`（`0x01839cc0`、`0x0183a040`）里才是 3 或 4，`w8 - 6 < 3` 时是 4（`0x0183a2b8`）。

事件 1 写第 30 槽要求离开的 id 等于 `+0xf8` 且不等于 `+0x100`、`0x01840b90(obj)` 为真（本地 mesh 控制器的 `+0x281` 与 `+0x234`，创建时都会置上）、`+0xd8 == 1`、`[mesh+0x64] == 0`，并且 `0x0184a4b0` 给出一个非零、且与 `obj+0x180+4*[obj+0x162]` 处的字不同的字。事件 2 只有在 `[obj+0xd8] - 2` 至少为 6 且 `0x01841350`、`0x01769ec0([obj+0x38])` 都为假时，才会写到主机 id 的存处。

`LdnMatchmakeSession` 第 30 槽（`0x017a23d0`）在 `[this+0x18]` 为空时返回 `0xff`，否则返回 `0x017672d0` 处理 `[[this+0x18]+0x18]+0x2c0+8` 处那 16 字节地址的结果：全零时为 0，后十二字节为零时取前四字节，其余情况报错 `0x10c07`。第 28 槽（`0x017a23b0`）是 `0x018407f0` 所调用的那个。

`0x018407f0` 在 `+0xf0` 非零、等于 `+0xf8`、且后端第 28 槽也同意时为真：也就是在这台主机正在主持 Pia 的 mesh 时。主持一场交换的主机靠命令逐级爬确认阶梯；而加入了 pokeldn 主持端的那台，跟随的是共享值（见[泵](swsh_trade.md#the-pump)）。

## 够到游戏层

游戏层之下的每一层都是双向的（见[Pia 层](pia.md)）：本地协议 0x24、站点握手 0x14、mesh 加入 0x18、RTT 0x58、可靠窗口 0x7C 与 0x80。

加入方对 0x14 连接的回应必须是剑所发的那种 840 字节形式（`host4.build_host_response`：账号 id 在 0x11、玩家名在 0x88、尾巴在 0xB1、token 在 0xBC）；`bin/swsh_connect.py --respond` 会发它。一台模拟的盾 1.3.2 主持端在 56 字节回应之后就不再发任何游戏消息。正版剑在 17 字节回应之后就能完成交换（见[Pia 层](pia.md#what-a-connection-response-must-satisfy-to-be-read)）。

不管它的话，主机会反复发 `61 00 00 00 0a 00`，也就是 ping（每秒约四次）；0x80 每秒要一次 ack id 1，0x7C 则保持沉默。`bin/swsh_connect.py --send-data HEX --send-protocol 0x7c` 用来发应用数据（`reliable4.build_data_message`；有五道静默接收检查，见[版本 4](pia.md#version-4)）。通过的信号是：0x80 的 ack id 不再是 1，或者 0x7C 有了任何回应。

## ping 握手

一段负载是四字节小端消息 id 加 protobuf 消息体。一次握手会带上这五条消息（`gflnet.p2p.sync.ping.pb`、`gflnet.p2p.block.pb`）：

    0x7C  61000000 0a00      97 SyncPingDataHolder, field 1 ping {}
    0x7C  61000000 1200      97, field 2 pingReply {}
    0x7C  61000000 1a00      97, field 3 pingSynced {}
    0x7C  60ea0000 0a00      60000 BlockDataHolder, field 1 result {}  (Result { bool isBlocking })
    0x80  60ea0000 12020801  60000, field 2 imReady { isReady: true }

应答要走过游戏的五步：

    1  answer the ping continuously   --send-data 610000000a00 --send-mirror --send-count N
    2  ack every reliable window      0x7C, 0x18 port 1, 0x80; one unacked window kills the mesh
    3  answer `result{}` on 0x7C      the mirror is per protocol
    4  answer imReady on 0x80         --send2-data 60ea000012020801
    5  the console sends its party on 0x84

- 一次 ping 应答只换来一条 `pingReply`，之后游戏就回去继续 ping。
- 在主机索要之前就发 `pingReply`，会让它的心跳停下来。
- 在 0x7C 上发 `imReady` 换不来 0x84；它要走 0x80。
- 迟到确认的消息会被重发，并可能出现在它的后继之后。只有比当前最新的序列号更大的才会替换当前消息。

`bin/swsh_connect.py --sync-answers` 对 `trade.SYNC_ANSWERS` 里有规则的按规则回，其余按协议回显，并打印每一条无规则的负载。

## 离开

一台剑离开交换会话时会发盒子命令 3，约 0.77 秒后为它的角色发起 Pia 离开。每一步都等待回应，等不到就按超时落到下一步。

一台作为加入方的剑离开主持端：

| 步骤 | 剑发什么 | 主持端该回什么 | 无人应答时 |
|---|---|---|---|
| mesh 离开 | LEAVE_REQUEST `04 <自己索引>`，0x18 端口 1，可靠，发一次 | LEAVE_RESPONSE `08 <主机索引>` | 5.0 秒 |
| 站点断开 | 0x14 上的 `03`，每 0.5 秒一次 | `04` | 8 次请求，3.6 秒 |
| LDN | 离开网络 | | |

两者都无人应答时，剑在 LEAVE_REQUEST 之后 9.0 到 9.1 秒离开 LDN 网络；都被应答时是 0.14 秒。版本 4 的主机处理函数 `0x017c19a0` 会通过 `0x017c2450` 发出 `08` 和自己的索引（不可靠地发两遍）并丢掉该站点；0x14 的处理函数 `0x017c6110` 向发送者回 `04`。`pokeldn/ldn/host4.py` 两者都回。

一台作为主持方的剑离开它的客户端（它是 LDN 接入点）：

| 步骤 | 剑发什么 | 客户端该回什么 | 无人应答时 |
|---|---|---|---|
| mesh 迁移 | MIGRATION_START `44 00 01`（见[主机迁移](swsh_trade.md#host-migration)） | MIGRATION_FINISH，以及一条把客户端自己指为主机的 UPDATE_MESH | 5.0 秒 |
| 本地会话 | 它的更新会话（0x24 类型 0x11，主机迁移字节 1，新的序列号），约每 0.11 秒一次 | 针对该序列号的 0x21 确认 | 10.0 秒 |
| 销毁网络 | START_HOST_MIGRATION `01 13 00..`（16 字节），每 0.33 秒一次 | 离开 LDN 网络 | 10.0 秒 |

给了 MIGRATION_FINISH、以客户端为主机的 UPDATE_MESH、确认和离开之后，正版剑的最后一个包在 MIGRATION_START 之后 0.17 秒到达；什么都不回，它就会发满 25.0 秒。

- `LocalDestroyNetworkJob::WaitUntilAllClientsDisconnection`（`0x017acd70`）在只剩主持端一个或过了 `0x2710` 毫秒时销毁网络，期间每 `0x12d` 毫秒重发一次 START_HOST_MIGRATION（`0x017acbd0`、`0x017a8bb0`）。
- 一次确认（处理函数 `0x017a9250`，本地类型 0x21）只有在序列号与该消息相同时才清掉发送者的位（`0x017aed10`）。是什么把 10.0 秒的本地会话这一步限住的，还没读出来。
- START_HOST_MIGRATION 不带序列号（`0x017abc60` 在 0xC 处写 0），也没有任何东西确认它。

`bin/swsh_connect.py --answer-migration --update-mesh --leave-with-host`（在 `--preset trade` 里）会做这三项应答。

`bin/swsh_connect.py` 在 `--hold` 结束且不在交换里时，按加入方剑的方式离开：盒子命令 3、一直发 LEAVE_REQUEST 到被应答、然后是断开请求。`bin/swsh_host.py` 在 `--seconds` 结束时按主持方剑的方式关闭：闲置交换上先发盒子命令 3，0.75 秒后 MIGRATION_START，等加入方离开或再过 10 秒后关掉网络。用 `--hold-after-trade SECONDS` 时，两者都在最后一笔排队交换之后等这么久再做同样的事。

## 局域网模式

在选项里把 L、R 和左摇杆一起按下，就能打开剑的局域网模式；游戏会显示「Mode réseau local activé」，并提示只有极巨团体战是有保证的。之后 Pia 就跑在主机的 IP 网络上（见[局域网模式](pia.md#lan-mode)），Y-Comm 的连接交换搜索也走它。

传输层选择器 `0x6a8550`（盾 1.3.2）会为模式 0 建 Ldn 工厂（`0x6a90b0`）、为 2 建 Nex 工厂（`0x6a8f80`）、为 3 建 Lan 工厂（`0x6a9210`）。

| 在一台模拟盾 1.3.2 上实测 | 值 |
|---|---|
| 连接交换搜索所主持的会话 | 游戏模式 60001、上限 2、版本 7 和 7、无应用数据、无属性 |
| 搜索开始时它的浏览 | 五次请求，游戏模式 0，flags 0x2，参与者上限 4..4，结果大小 1 |
| 一台主持中的剑离开它的加入方 | mesh 端口 1 上的 MULTI_MIGRATION_START（0x49），5.2 秒后归于沉默 |

连接交换搜索自己主持的会话与它开始时发出的浏览并不匹配。`bin/swsh_connect.py --lan auto`（也就是应用里的 Trade (LAN Join)）会用 `--preset trade` 的 flags 浏览每个本地 /24，并已在 Wi-Fi 上对着 Switch 2 上的正版剑以及模拟主机完成过交换；它把主机的沉默当作对方离开（`--lan-quiet`，默认 3 秒），正版那次在玩家退出后 3.1 秒结束。`bin/swsh_host.py --lan`（应用里的 Trade (LAN Host)）主持一个会话，正版剑从它的连接交换搜索里加入并完成交换，同样是在 Wi-Fi 上的 Switch 2。

在没有 `--our-ip` 的多地址电脑上（VPN 会抢走默认路由），它会等主机发来第一次浏览，然后在那个子网的地址上主持。

局域网模式下的连接交换搜索会发两种浏览：

| 浏览 | 在哪构建 | 条件 |
|---|---|---|
| Y-Comm 附近玩家注册表 | `0x006c46a0` | 参与者上限 4..4、只找开放且空位的、结果大小 1 |
| 交换搜索的随机匹配（`Session::JoinRandomSession`，`0x0183f860`） | `0x006bb120` | 游戏模式 60001、参与者上限 2..2、只找开放且空位的、结果大小 8 |

第二种会加入它听到的第一个匹配会话，若没有就自己主持一个两人的会话（见[局域网模式](pia.md#lan-mode)）。两人会话只会匹配第二种。

一个大厅的应用数据在局域网上与在 LDN 上是同样的 0x168 游戏字节：LDN 广播就是 Pia 的 0x18 字节头后面跟着这些字节。局域网匹配对象把它们放在 +0x284，最多 0x168 字节（`0x006b98c0`，经 `0x006b5bcc` 从巢穴大厅设置），而浏览结果由 LDN 扫描所用的同一个解析器读回 0x168 字节进 Y-Comm 列表（`0x006c2360`，局域网从 `0x006bb9c0` 调用，LDN 从 `0x006ca0b0` 调用）。所以巢穴团体战在广播偏移 `0xB0` 处的记录，落在应用数据的 `0x98` 处。

| 在局域网模式下的模拟盾 1.3.2 上实测 | 值 |
|---|---|
| 一个巢穴主持的会话（「Combat à plusieurs」） | 游戏模式 60006、上限 4 |
| Y-Comm 的浏览 | 游戏模式 0、flags 0x2、参与者上限 4..4、只找开放且空位的、结果大小 1；它会按应用数据列出一个巢穴会话 |
| 一次不带连接密码的极巨大冒险「Invite Others」（正版剑） | 开始时一次浏览：游戏模式 50000、上限 4..4、flags 0x712、属性 2 = `0xfffffffe`、3 = `0x33d39298`、4 = `0x253cad29`；没有回应时它就主持游戏模式 50000、上限 4 的会话 |
| 加入一个列出的团体战（「Participer」然后「Commencer le combat」） | 一次范围开放的浏览、一条明文保活，然后是把会话请求（类型 5）发到子网广播的 49152 到 49155 端口，之前没有任何主机请求 |

`bin/swsh_host.py --lan` 搭配 `--raid-boss`、`--raid-event` 或 `--lair-legendary` 会主持一个携带大厅字节的四座会话，并在自己的站点端口上监听子网广播；模拟盾和 Wi-Fi 上 Switch 2 里的正版剑都列出了它、加入并打了这场团体战，由主机提供服务（见[哪个站点在服务](swsh_raid.md#which-station-serves)）。`bin/swsh_connect.py --lan` 搭配 `--preset raid` 或 `--preset lair` 会浏览场景 60006 或 50000 的四座会话；它加入过模拟盾和正版剑的巢穴大厅并让战斗开始，也加入过正版剑的冒险，租用的宝可梦被选中、第一场战斗成功载入。

浏览的属性条件是六张最多 20 个 u32 的列表，位于 `0x1A + 0x50 k`，计数以 u8 存在 `0x1FA + k`，搜索标志 `0x40 << k` 打开第 k 个属性。极巨大冒险搜索会跳过属性值不符的会话。那三个值编码的是什么还不清楚；同一台主机的两次搜索带着相同的值。局域网主持端会把针对自己游戏模式的那次搜索的值抄进它自己的会话信息（`pia_lan.criteria_attributes`）；之后一台正版剑就能加入 `bin/swsh_host.py --lan --lair-legendary` 并开始它的冒险。

### 局域网上的连接密码

`SetMode(comm, mode, code)`（`0x01096d10`）把场景放在 comm+0x70、连接密码放在 comm+0x74，后者是个 optional u32（一个存在字节，再是值）。`StartRandomMatching` 的参数把它带到 +0x88，进到匹配对象的 +0x278（局域网走 `0x006b83ec`）。LDN 加入（`0x006ca1c0`）和 NEX 随机加入（`0x006c6b7c`）用 `%u` 格式化它并当作会话密码传下去。而局域网匹配类（`0x006b6000`..`0x006bc000`，在 `0x006ba480` 构造）里没有任何代码读 +0x278，它的创建、浏览、随机加入设置也都不带密码。局域网模式下一次带密码的连接交换搜索发出的浏览与不带密码时完全相同（在正版机上实测），并且会加入任何与之匹配的会话，不管对方的密码是什么：局域网主持端与加入方对带密码和不带密码的搜索一视同仁。

## 操作备注

- 绝不要在实机上加 `--verbose`；用 `--capture FILE`。
- 主机的信道会在会话之间变化（见过 1 和 6）；扫描会保留最忙的那个（见[信道](ldn.md#channels)）。
- `0x2D0`（在 `0x006a970c`、`0x006a9740` 分配）是会话单例的大小（`0x006b4410`，全局 `main+0x02616758`），一个 720 字节的结构体，与神秘卡片无关。
