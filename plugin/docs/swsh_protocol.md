---
title: 同步框架
parent: 剑与盾
nav_order: 2
---

# 消息、内容与路由

Pia 之上的发布/订阅框架。一条消息是一个 u16 小端 id、一个鉴别字节、一个零字节，以及一个 protobuf 体。

## 消息 id 从哪来

低位 id 来自 `0x01BBFFA0` 处一张 838 条 24 字节记录的表，`{u64 handler 槽, u32 0x402, u32 id, u64 0}`，id 为 1..880。高位 id 是基址加偏移。

## 内容与持有者

每个内容注册三个持有者（注册器 `0x010ccd90` 内容 30、`0x010da7d0` 40、`0x010d5150` 50），给它的偏移 `ldrh [content+0x372]` 加上一个基址，再把每一个传给 `0x006daeb0(manager, &holder, flag)`：

| id | 持有者 | flag |
|---|---|---|
| 10000 + 偏移 | `0x010dd910` | 1 |
| 20000 + 偏移 | `0x010d85f0` | 0 |
| 30000 + 偏移 | `0x010d0980` | 0 |

40000 那一族是在更低一层铸出来的（`ldrb w20,[x0,#0x28]`、`add w24,w20,#-0x63c0`、`strh w24,[x20,#0x160]`）：40030 / 40040 / 40050。

没有监听者的持有者会静默丢弃（`0x010d81d0`）。没有任何东西会到内容 40 或 50 的 20000 基持有者：20040 与 20050 是惰性的。

### 30000 持有者

30000+偏移那个持有者（`0x010d0980`，vtable GOT `0x02618620` = `0x02528100`，无 RTTI）携带的是 `gflnet.p2p.framework.pb.SequenceDataHolder`：

    SequenceDataHolder    oneof message {
                             1 CancelAccepted        cancelAccepted
                             2 RequestCancel         requestCancel
                             3 RequestCancelAll      requestCancelAll
                             4 RequestForcedProceed  requestForcedProceed }
    CancelAccepted        { 1 int32 currentSeqNo; 2 bool  isForced    }
    RequestCancel         { 1 int32 currentSeqNo }
    RequestCancelAll      { 1 int32 currentSeqNo }
    RequestForcedProceed  { 1 int32 currentSeqNo; 2 int32 targetSeqNo }

解析器 `0x006a7580`；接收（槽 8 `0x008b9590`）调用 `[holder+0x168]` 的监听者槽（case - 1）。盾 1.3.2 只构造 CancelAccepted（`0x006a3db0`，由发送包装 `0x008b7420` 和十个同步内容里各两个回复任务调用）。正版交换从不带 case 2 到 4；但主机收到仍会照做（见[内容 40](swsh_trade.md#the-cancel-and-proceed-messages)）。内容 40 的实例，30040，端口 0：

    RequestForcedProceed{c, c+1}   58750000 2204 08<c> 10<c+1>     c=0: 58750000 2204 0800 1001

### 三个交换内容

`0x010c9280` 建立会话：内容 30（盒子交换）在 `+0x120`，内容 40（SyncSaveDataHolder）在 `+0x148`，内容 50（PokemonTradeDataHolder）在 `+0x2b0`；自己的宝可梦 `+0x68`，对方的 `+0x70`；交换状态（1..10）`+0x140`，错误码 `+0x144`；`+0x418` 在第一帧发命令 3，而 `+0x419` 是抑制它的角色位。内容 50 以状态 1 初始化，内容 40 以状态 6 初始化。

## 路由路径

    0x006a9a20   同步泵，来自交换会话的更新
    0x006db3b0   轮询：对每条已注册条目，抽干它那种类型的两个流（字节 +8）
    0x006a8490   流 A：mesh 端口 [pia+0xd0+kind*4]，Pia 协议 0x7C
    0x006a84f0   流 B：mesh 端口 [pia+0xd8+kind*4]，Pia 协议 0x80
    0x006db9c0   抽干：槽 0x78 填入 (发送者*, 长度) 与 manager+0xf0 处的缓冲
    0x006db620   派发：匹配条目，调用持有者的槽 8
    0x010d81d0   内容 50 的 10000 基持有者：解析，调用监听者的槽 0
    0x010d5e40   监听者：发送者转站点索引，memcpy 0x158，调用

### 应用层头

一段负载是 `struct.pack("<HBB", id, discriminator, 0)` 后面接消息体，由 `0x006db840` 构建、`0x006db620` 解析。鉴别字节是个世代计数（`[content+0x370]`，+1 模 255，`0x008b6670`），被推进 `[manager+0x480f0]`；一次强制的 CancelAccepted 会在内容 40 上让它加一（`0x006db470`），而各注册器会把它清零（`0x010d53a0`）。没有强制 CancelAccepted 的交换全程都是零。

### 在线读取注册表

    manager = read_u64(read_u64(main + 0x02616750))     0x006a9a70，轮询的调用者
    count   = read_u64(manager + 0xD8)                  0x006db3dc
    array   = read_u64(manager + 0xD0)                  0x006db3e0
    entry i = array + i * 0x10                          0x006db3e4
    id      = holder's vtable slot 7, called at 0x006db740 (`ldr x8, [x8, #0x38]`)

槽 7 返回 `[holder+0x160]`。闲置画面上这张表是空的；坐下的连接交换会加两条；神秘礼物不加。

### 派发闸门、端口与发送者

一条条目是 16 字节：holder、+8 处的 kind、+9 处的 flag（只有 10000+偏移 才是 1）：

    id == holder->slot7()
    entry[8] == the drain's kind
    entry[9] ? header[2] == [manager+0x480f0] : no check

Kind 就是 mesh 端口：内容持有者为 0（20030、10050、ping），40000 族为 1（`0x006daf40(manager, &holder, 1, 0)`）。发送者是一个传输指针，由 `0x006b5850` 解析（`mesh->GetStationIndex`，失败为 0xfd）；回环传的是 `[[0x2616a30]]+0xf0`。`Data.ownerId` 在 10050 上不起作用。

## `Data` 信封

`gflnet.p2p.sync.pb`、`data.proto`：

    1  uint32  syncId        内容偏移        30 / 40 / 50
    2  uint32  elementId     基址            10000 / 20000
    3  uint64  ownerId       发送者
    4  uint64  clock
    5  bytes   body          一对里四个字节；40050 里是 344 字节的 PK8

40000 持有者的监听者是 `element+0x18`；它的槽 0，`0x006d59f0`，这样路由：

    [Data+0x14] == [listener+0x10]        syncId，元素的偏移
    walk [listener+0x28] .. [+0x30]       子元素，每个 0x90 字节
      [Data+0x18] == [sub+0x62]           elementId，u16
      [Data+0x20] == [sub+0x68]           ownerId，u64
    sub->vtable at 0x48 (sub, body, len, [Data+0x28])     body 与 clock
    otherwise: ret                        静默丢弃

### 子元素种类

| 种类 | 构造器 | vtable | 出生时 `+0x88` | 槽 9，接收：长度检查，存到 `+0x88` |
|---|---|---|---|---|
| 32 位 | `0x006d5c00` | `0x2512bc8` | 0 | `0x006d5f20`：4 字节 |
| 对（相位） | `0x006d6160` | `0x2512c90` | `0xfc18fc18` | `0x006d6490`：4 字节 |
| 16 位 | `0x006d66d0` | `0x2512d58` | 0 | `0x006d69f0`：2 字节 |

一次接收随后把 `[sub+0x78] = clock`，并 `strh 0x0100 -> [sub+0x60]`（就绪字节 `+0x61`）；槽 7，也就是哈希值，返回 clock。构造器接受元素 `x0`（`+0x80`）、elementId `w1`（`+0x62`）、ownerId `x2`（`+0x68`）、flag `w3`（`+0x70`）。

同步元素（`0x006d3f80`）每个同步内容构建一次（内容 30 在 `0x010ce604`，50 在 `0x010d6904`，40 在 `0x010dc264`）。vtable 来自 `0x2512b28`：

| 偏移 | vtable | 角色 |
|---|---|---|
| `+0x00` | `0x2512b38` | 主，6 个槽；2、3、4 是三个构造器，w3 = 1 |
| `+0x08` | `0x2512b78` | 接口 A：32 位那种 |
| `+0x10` | `0x2512b90` | 接口 B：对与 16 位那种 |
| `+0x18` | `0x2512bb0` | 路由监听者，槽 0 = `0x006d59f0` |

铸造 `0x006d44e0` 建四个通道：`+0xd0` 每个站点一个 32 位子元素，elementId 10000（法定人数哈希）；`+0xf0` 在 `+0x38` 处一个 16 位子元素，elementId 20000、owner 0（就是[共享值](swsh_trade.md#the-phase-is-the-elements-field)），并每站点一个对，elementId 20000；`+0x110` 是法定人数哈希所遍历的那张表。

### 法定人数哈希

elementId 10000 上的那四个字节，由 `0x006d7b40` 在 `element+0xa8` 构建：

    h = 0
    for sub in subs:
        if (!sub[+0x61]) { h = 0; break }        任一站点未就绪 -> 零
        h = crc32(le32(h + sub->slot7()))        槽 7 就是 clock

非零表示每个站点都就绪了。`0x0065de30` 是 `zlib.crc32`；`0x0065df04`（多项式 `0x8005`）是 CRC-16。被遍历的表 `element+0x110` 是 `0x006d48b0` 对 `+0x40` 的拷贝，保留 `+0x68` 为零的条目。

这条链覆盖发送者的 elementId 0 和 1（无 owner），然后是它自己的 elementId 20000。主持中的剑的非零哈希能对得上，例如内容 50：

    elementId 0, no owner      clock 2304   主机自己的宝可梦（344 字节）
    elementId 1, no owner      clock 2313   对方的宝可梦，被送回去
    elementId 20000, host      clock 2278   它那一对移动后变成 2338
    crc32 chain                8ffa0f2e     然后 b3615e90

把主机的哈希回显回去的加入方，就能对着主持中的剑完成一次交换。

## 协议 0x84 上的队伍负载

`ReliableBroadcastProtocol` 把 3456 字节的交换快照分三片发送直到被确认；第三片是 zlib（Pia flag 0x10）：原始 1404 + 1404 + 157，最后一片解压后为 648。`trade_payload.py` 拒绝任何别的总长。布局（同 `kwsch/PokePiaSWSH`、`lincoln-lm/swsh-lan-client`）：

    0x000  六条 PK8 记录，队伍形态，每条 0x158          -> 0x810
    0x810  u32   队伍数量
    0x814  MyStatus，272 字节      TID/SID 在 0xA0，训练家名在 0xB0
    0x924  TrainerCard，456 字节   训练家名在 0x00，存档开始日期在 0x170
    0xAEC  玩家档案，266 字节                             -> 0xBF6
    0xBF6  392 字节，对战竞技场块；连接交换时为零
    0xD7E  2 字节填充                                    -> 0xD80 = 3456

MyStatus 与 TrainerCard 是 PKHeX 的存档块（`Saves/Substructures/Gen8/SWSH/`）。构建者是 `0x0110c180`，接收者是 `0x0110cff0`。连接交换（`0x010967f0`）与密码匹配（`0x00bd80f4`）不传对战竞技场块；对战竞技场（`0x00b2d7d0`）会传一个。

### 对战竞技场块

0x180 字节数据，外加一个 u64 长度；读取者 `0x00b2d9fc` 要求长度为 0x118。生产者 `0x00b2eb60`。从 0xBF6 起：

    0x000  u32    0x22fc 字节规则核心（0x008ff9e0；regulation_preset_core_%d.bin）的 CRC-16（0x8005）
    0x004  0x100  队伍签名：match+0x98 处 0x136 字节队伍描述的 +0x36
    0x104  4      零
    0x108  u64    管理器的 optional（值 +0x1ab8，标志 +0x1ab0），除非比赛类型 3 否则为零
    0x110  u8     当 0x00adb920 产出对象且 0x00b1ce10(0) == 2 时，管理器的字节 +0x191c
    0x111  u32, u16, u8   队伍描述 +0、+4、+6
    0x118  0x68   零
    0x180  u64    长度，0x118

接收者 `0x00b2e590` 把对方的 CRC 与自己的（`0x00b2e760`）相比；两者都持有结果为 9，否则 10。

队伍描述在 match+0x70 处一个 optional 的 match+0x98，只由对战竞技场匹配更新 `0x00ad5750` 里的 `0x00ad9cf0` 写入。队伍下载任务（`0x014f7fd0`）填充它：`+0x00..+0x2f` 是结果持有者 `+0x38` 的六个 u64，`+0x30..+0x35` 是 `+0x68` 的六个字节，`+0x36..+0x135` 来自 `+0x6e`，然后被 `v1/validate` 的签名覆盖。持有者取队伍列表（`0x0150320c`）里键与选中键相符的那条 0x158 字节条目：

| 键 | 条目 |
|---|---|
| (1, team) | 一个存档对战队伍：六个 u64 `box \| slot << 32`，来自 `save+0x525 + team*12 + i*2`；名字在 `save+0x4a0 + team*0x16` |
| (2, i) | 一条存下的记录：0x87f 字节记录（`0x01430670`）的第 0x26..0x15b 字节 |

签名是 RSA-2048、PKCS#1 v1.5、SHA-256，由 `0x011aedf0(team, v, sig)` 校验，它是 `nn::crypto::detail::BigNum::ModExp`（PLT `0x018fff50`）唯一的调用者。被签的消息是队伍那 0x148 字节的已存 PK8、以大端 u16 表示的密钥版本 `v`，再是 `00 01`。主机只持有公钥；镜像里写着 `https://v3-lp1.vp.n.srv.nintendo.net/v1/public_key` 和 `.../v1/validate`，所以大概由任天堂的服务器签名。连接交换永远走不到这项校验。

`v1/validate`（`0x011a2a70`）发送一个 NUL 结尾的字符串（`v1/public_key` 的正文）、以大端 u16 表示的密钥版本、主机版本 `0x2D`（盾）以大端 u16、`00 01`、一个大端计数，以及那些 0x148 字节记录。回复解析器 `0x011a2870`：第 0 字节是状态（2：密钥过期，重新取），第 5-6 字节是大端计数 n（钳到 6），n 个大端 u32，状态为 0 时再跟一个 0x100 字节的签名。

比赛类型是 vtable `0x2538238`、`0x2538358`、`0x2538478` 的槽 8：1 休闲、2 排位、3 线上大赛。它们由 `0x00adcfb0(obj, mode)` 从 `StateBtlSpotTop`（`0x00b23080`）构建。块 `+0x108` 由 `0x00adc8b0` 从 `StateBtlSpotCompTop` 写入，取存档块 `0x88F6D6AE`（0x33D0 字节；前一个键 `0xEEE5A3F8` 是 PKHeX 的 `KOfficialCompetition`）0x33C0 处的 u64。

### 玩家档案

0xAEC 处的 266 字节，也是信标在 0x1F 处的记录（见[会话](swsh_session.md#taking-a-seat)）。`0x01111970` 从单例 `[0x2610958]`（+0x310 到 +0x564）拷贝它；`0x01125080` 要么打包所有组，要么一个都不打；按位打包的组是低位在前。`trade_payload.read_tail` 解码它。

    0x00  16  nn::oe::GetPseudoDeviceId
    0x10  16  nn::account::GetUserId，账号 Uid
    0x20   8  nn::account::GetNetworkServiceAccountId，或零
    0x28  24  训练家名，UTF-16，来自 MyStatus+0xB0；终止符之后是陈旧字节
    0x40  25  外观，按位打包：
                第 0 位      MyStatus+0xA5（性别）!= 0
                第 1 位      由 0x0111cfec 置位；每次抓包里都是 0
                第 2-5 位    MyStatus+0xA7，语言（3，法语）
                第 6-7 位    零
                 8 位        MyStatus+0xCC
                 17 x 10    模型 0x0111dd60 从 +0x00 处的 MyStatus 位域解出
                 2, 2, 10   那次解包的最后一组三个
    0x59  55  位置采样，按位打包：
                 2、2 位    `a` 与 `b`，见下
                 8 位       世代：环重置时随机（0x00eb98a8），每次重播种 +1
                 8 位       玩家对象字节 +0x136（每次抓包里都是 7）
                 3 x 17     在 0x5C、0x6D、0x7E，最新在前：5 位计数（每次推入 +1）；
                            3 位状态（+0x1c8，见下）；x、y、z 三个浮点；以弧度表示的偏航角。
                            0x00ebf590 从场地对象的 +0x60（位置）与 +0x50（旋转）每秒最多推一次
                 8 位       在 0x8F：玩家对象字节 +0x140（每次抓包里都是 1）
    0x90  37  活动，按位打包：一个 8 位种类（交换时为 13）、一个可选的 28 字节部分、
              一个 24 字节字段、一个 0xB2 处的 u16、一个布尔；只有种类与 u16 非零。那个 u16 是
              地点，即 `script/place_name.dat` 的某一行，也就是 PKHeX 的相遇地点 id
              （170 挑战海滩）
    0xB5  37  另外两组，每次抓包里都是零
    0xDA  32  十六条 u16 记录（`0x010f5060`）：Record8 的索引 6、32、0、33、17、27、34、24、
              12、3、10、35、38、7、36、37，每个钳到 0xFFFF（PKHeX `RecordList_8`）
    0xFA   8  一个可选的 u64，每次抓包里都是零
    0x102  8  零

接收方（0x00dd5e24）把位置存到 +0xB0，把偏航角以四元数形式存到 +0xA0。

采样状态（`[[0x261bd18]]` 的 `+0x1c8`，由 `0x00ebf570` 设置）在场地设置它之前是 0；为 0 时推入立即返回。状态 1 与 2 是场地动作，3 与 4 是宝可梦露营的拜访与会话画面，6 是极巨团体战匹配（`0x01466d30`）。`a` 对区域 `wr0101`、`wr0201`（铠之孤岛，抓包在 170 位置）与 `wr0301` 分别是 1、2、3，其余为 0，来自一个 FNV-1a 64 的区域键；`b` 来自 vtable `0x259add8` 的槽 8 与 11。

0x90 处的活动记录是 `0x49` 字节，由 `0x0111b660(rec, kind)` 设置；连接交换把通信模式设为 2（`SetMode` `0x01096d10`，见[会话](swsh_session.md#how-a-searching-sword-finds-a-partner)），经 `0x2066c40` 处的表映射为种类 13。

训练家名出现四次（MyStatus、训练家卡、队伍记录、档案）；`pokeldn/swsh/trade_payload.rewrite` 会移动全部四处，交换画面显示的就是这个训练家。空的队伍槽是一条全零记录，发送时要么是零字节，要么以加密常数 0 加密；两者解密后都是零，0x810 处的数量也自洽。仅靠加密常数 0 并不能标记槽为空：HOME 3.0.0 之前的 HOME 礼物给的就是卡上的零常数（时拉比礼物，WC8 9011）[PKHeX `WC8.cs`]。`pokeldn.gen8.is_empty` 检测的是解密后的记录。

## PK8

与 BDSP 共用 `pokeldn/gen8.py`（PKHeX 的 `PK8` 与 `PB8` 都是 `G8PKM`）。剑发送 0x158 的队伍形态（`pokeldn/swsh/pokemon.py`），BDSP 发送 0x148 的存储形态。

    0x00  u32  加密常数，明文。给密码与块序播种
    0x06  u16  校验和，明文，只覆盖解密后的主体
    0x08       四个 80 字节块，经 LCG 加密，按 (EC >> 13) & 31 置换
    0x148      队伍数值，LCG 加密且流重启，从不置换

坑：

- 队伍数值会重启 LCG（`PokeCrypto.Decrypt8` 用 EC 给 `CryptArray` 播两次种）；接着上一段流解下去会给出像等级 110 这样看似合理的垃圾。
- `BLOCK_ORDER[sv]` 说的是“成为第 *i* 块的是原第几块”：正着用，绝不要反过来。32 个 `sv` 值里有 16 个自逆，而校验和又忽略顺序。PKHeX 的 `BlockPosition` 第 24-31 项重复了 0-7。
- 解出队伍后可以查：昵称与种类相符；等级与经验相符；极限特训字节 0x126 与个体值字 0x8C 相符；MyStatus 的训练家 id 与每条 PK8 相符。

## 交换消息

`net_contents.trade.common.pokemon_trade.protocol_buffers`：

    Pokemon                  { 1 bytes   serializePokemonParam }
    PokemonTradeDataHolder   { 1 Pokemon pokemon }

一次报价在 10050 上携带 344 字节的 PK8（`trade.py` 的 `pokemon_offer`）。解析 `0x010d81d0` 建一条 0x28 字节消息，调用 `ParseFromArray`（`0x0070c180`）；`MergePartialFromCodedStream`（`0x010d9ee0`）只接受 tag 0x0a。监听者把 `[Pokemon+0x18]` 当作 libc++ 的 `std::string` 读取，拷出 0x158。

### 接收处理器的两处静默丢弃

`0x010d5e40`：

    w0 = 0x006b5850(senderPointer)                            失败为 0xfd
    if (w0 == 0xfd) { [content+0x1a4] = 1; return; }          静默
    memcpy(stack, body, 0x158)
    subscriber = [content + 0x30 + index*8]
    if (subscriber == null || its refcount is 0) return        静默
    ... 调用它，然后内容 50 的发送 0x010d6000

内容 50 的初始化只填 `+0x30` 与 `+0x38`，所以站点索引大于 1 就直接返回；内容 40 的 `0x010dbc90` 在 `+0x38`/`+0x40` 处做同样的闸门。主机收到 10050 会立刻用自己的回一条；没有回来的 10050 就意味着那次报价根本没到 `0x010d5e40`。内容 30 的槽（`0x010ce080`）只拒绝它自己的 id：一条无 owner 的报价能过盒子阶段，却在内容 50 上失败。

### 内容 40 的消息

`net_contents.trade.common.sync_save.protocol_buffers`：

    SyncSaveDataHolder { 1 SyncCommand syncCommand }
    SyncCommand        { 1 int32       data       }

解析 `0x010ddb20`；`0x010df6d0` 只接受 tag 0x0a，子消息解析器 `0x010debc0` 只接受 tag 0x08。`trade.sync_command` 构建它。
