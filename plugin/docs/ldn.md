---
title: 无线层
nav_order: 2
has_children: true
---

# 无线层

**LDN** 是 Switch 的本地无线；任天堂的点对点中间件 [Pia](pia.md) 运行在其上。

## 两个秘密

LDN 口令（16-64 字节，原样使用）用于认证 802.11 关联。16 字节的 Pia 游戏密钥为每个数据报派生会话密钥。

| 游戏 | LDN 口令 | Pia 游戏密钥 |
|---|---|---|
| 晶灿钻石与明亮珍珠 | `WirelessStrongCryptoKey2021`（27 字节） | 来自 `cryptoKeyDataSeed`（[BDSP](bdsp_session.md)） |
| 剑与盾、朱与紫、传说 阿尔宙斯 | `W3GoSMEn7RIIUQ89rzqBHGhGferRNb7K18ZBq2aNuj8Us9RO9Q9JYyGOZlLy8MYL`（64 字节） | `p1frXqxmeCZWFv0X` |

## 发现

`tools/ldn/ldn_scan.py` 仅凭 `prod.keys` 就能读取任何广播。一款游戏只能看到与自身 LDN 协议相同的广播，因此主机要把它一并复制（`HostTransport(protocol=...)`）。

| 游戏 | 协议 | 广播格式 |
|---|---|---|
| GBA 应用，comm id `0x01006fa0233f8000` | 3（AES-GCM，`master_key_12`） | 3 |
| 剑的神秘礼物界面，`0x0100abf008968000` | 1（AES-CTR，`master_key_00`） | 2 |
| 传说 阿尔宙斯本地交换，`0x01001f5010dfa000` | 1 | 4 |

信标以 11 Mbit/s DSSS 发出，广播动作帧以 HT MCS 3（OFDM）发出；只支持 DSSS 的接收器会漏掉这些广播。

## 广播的应用数据

Pia 5（明亮珍珠）：

    +0x00  4  network id                     每次会话随机
    +0x04  4  CRC32 of the user password     无密码时为 0
    +0x08  1  system communication version
    +0x09  1  header size                    16
    +0x0c  4  session parameter              作为 Pia 会话密钥的种子
    +0x10     application data

一份抓包只能用其自身会话的广播解密。

Pia 6.16 到 6.41 从 SSID 派生会话密钥和 network id：

    +0x00  2  system property data size      0x5C
    +0x02  1  system communication version   6.16-6.30 为 21，6.39-6.41 为 22
    +0x03  2  application communication version
    +0x05  16 user password                  以 0xFE 填充，在游戏密钥下用 AES-128-GCM 加密，tag 丢弃
    +0x15  1  is player limit enabled
    +0x16  1  number of players
    +0x17  4  player name size
    +0x1b  1  player name encoding           1 = UTF-8，2 = UTF-16
    +0x1c  64 player name
    +0x5c     application data

密码的 IV 是 `key[1] key[8] key[7] key[2]`（阿尔宙斯 1.1.1 `0x6fac70`，[设置函数](pla.md#the-link-code-in-the-advertisement)）；只凭游戏密钥即可读取。

## 为模拟器托管

处于 ldn_mitm 模式的模拟器通过端口 11452 关联，并在 LAN 上运行 Pia，不使用无线模块，也不需要 `prod.keys`。`pokeldn/ldn/ldn_mitm.py` 负责加入；`ldn_mitm_host.py` 通过 `IpHostTransport` 托管（`NEEDS_RADIO = False`）。

    UDP  console -> host:11452   Scan          header only
    UDP  host    -> console      ScanResp      NetworkInfo, 0x480
    TCP  console -> host:11452   Connect       NodeInfo, 0x40
    TCP  host    -> console      SyncNetwork   NetworkInfo with the console seated, held open

`nn::ldn::NetworkInfo`，0x480 字节：

    +0x000  NetworkId          IntentId 0x10 (u64 localCommunicationId, u16, u16 sceneId, u32) then SessionId 0x10
    +0x020  CommonNetworkInfo  MAC 6, Ssid 0x22 (length byte then 0x21), s16 channel, u8 linkLevel, u8 networkType, u32
    +0x050  LdnNetworkInfo     SecurityParameter 0x10, u16 securityMode, u8 acceptPolicy, ...
    +0x066                     u8 nodeCountMax, u8 nodeCount
    +0x068                     NodeInfo[8], 0x40 each: u32 IPv4 LE, MAC 6, u8 nodeId,
                               u8 isConnected, 0x20 name at 0x0C, u16 localCommunicationVersion at 0x2E
    +0x26A                     u16 advertiseDataSize, then 0x180 bytes of advertise data
    +0x478                     u64 authenticationId

节点 0 的地址必须是可达的 LAN 地址：游戏主机会把 Pia 发送到那里。节点的 MAC 由其地址派生（172.16.86.1 对应 `02:00:ac:10:56:01`）。游戏的节点在 +0x2E 处带有 88。火红的扫描过滤器只比较 `localCommunicationId` 和 `networkType`。

16 字节的会话 id 是 `NetworkId.SessionId`、十六进制的 `Ssid` 文本，以及 Pia 会话密钥 `AES(game_key).encrypt(ssid)` 的明文；network id 是 `crc32(ssid[1:16])` [`pokeldn/ldn/crypto.py`:114]。陷阱：不匹配时仍能关联，随后游戏主机静默丢弃每一个数据报。

## 站点的广播

已加入的游戏主机发送不带 DS 位的广播与组播（CCMP 组密钥，key id 1），以及发往 DS 的单播（成对密钥，key id 0）。火红以一个针对主机的 ARP 开场；不应答该 ARP 的主机会被以原因码 3 解除认证。标准接入点会丢弃这些帧；[ESP32](hardware_esp32.md) 会把它们完整转发。

## 信道

LDN 还允许 5 GHz 的 36-48 信道，ESP32 无法到达；火红／叶绿只使用 2.4 GHz。板子也能听到相邻信道上的主机；在那里加入会在主机的下一次广播时被丢弃，因此扫描会报告最繁忙的信道：

    POKELDN_RADIO=esp32:auto ./.venv/bin/python tools/ldn/ldn_scan.py --keys PROD_KEYS --dwell 2.5
