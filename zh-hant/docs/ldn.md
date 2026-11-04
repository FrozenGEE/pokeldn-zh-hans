---
title: 無線層
nav_order: 2
has_children: true
---

# 無線層

**LDN** 是 Switch 的本地無線；任天堂的點對點中介軟體 [Pia](pia.md) 執行在其上。

## 兩個秘密

LDN 口令（16-64 位元組，原樣使用）用於認證 802.11 關聯。16 位元組的 Pia 遊戲金鑰為每個資料包派生會話金鑰。

| 遊戲 | LDN 口令 | Pia 遊戲金鑰 |
|---|---|---|
| 晶燦鑽石與明亮珍珠 | `WirelessStrongCryptoKey2021`（27 位元組） | 來自 `cryptoKeyDataSeed`（[BDSP](bdsp_session.md)） |
| 劍與盾、朱與紫、傳說 阿爾宙斯 | `W3GoSMEn7RIIUQ89rzqBHGhGferRNb7K18ZBq2aNuj8Us9RO9Q9JYyGOZlLy8MYL`（64 位元組） | `p1frXqxmeCZWFv0X` |

## 發現

`tools/ldn/ldn_scan.py` 僅憑 `prod.keys` 就能讀取任何廣播。一款遊戲只能看到與自身 LDN 協議相同的廣播，因此主機要把它一併複製（`HostTransport(protocol=...)`）。

| 遊戲 | 協議 | 廣播格式 |
|---|---|---|
| GBA 應用，comm id `0x01006fa0233f8000` | 3（AES-GCM，`master_key_12`） | 3 |
| 劍的神秘禮物介面，`0x0100abf008968000` | 1（AES-CTR，`master_key_00`） | 2 |
| 傳說 阿爾宙斯本地交換，`0x01001f5010dfa000` | 1 | 4 |

信標以 11 Mbit/s DSSS 發出，廣播動作幀以 HT MCS 3（OFDM）發出；只支援 DSSS 的接收器會漏掉這些廣播。

## 廣播的應用資料

Pia 5（明亮珍珠）：

    +0x00  4  network id                     每次會話隨機
    +0x04  4  CRC32 of the user password     無密碼時為 0
    +0x08  1  system communication version
    +0x09  1  header size                    16
    +0x0c  4  session parameter              作為 Pia 會話金鑰的種子
    +0x10     application data

一份抓包只能用其自身會話的廣播解密。

Pia 6.16 到 6.41 從 SSID 派生會話金鑰和 network id：

    +0x00  2  system property data size      0x5C
    +0x02  1  system communication version   6.16-6.30 為 21，6.39-6.41 為 22
    +0x03  2  application communication version
    +0x05  16 user password                  以 0xFE 填充，在遊戲金鑰下用 AES-128-GCM 加密，tag 丟棄
    +0x15  1  is player limit enabled
    +0x16  1  number of players
    +0x17  4  player name size
    +0x1b  1  player name encoding           1 = UTF-8，2 = UTF-16
    +0x1c  64 player name
    +0x5c     application data

密碼的 IV 是 `key[1] key[8] key[7] key[2]`（阿爾宙斯 1.1.1 `0x6fac70`，[設定函式](pla.md#the-link-code-in-the-advertisement)）；只憑遊戲金鑰即可讀取。

## 為模擬器託管

處於 ldn_mitm 模式的模擬器通過埠 11452 關聯，並在 LAN 上執行 Pia，不使用無線模組，也不需要 `prod.keys`。`pokeldn/ldn/ldn_mitm.py` 負責加入；`ldn_mitm_host.py` 通過 `IpHostTransport` 託管（`NEEDS_RADIO = False`）。

    UDP  console -> host:11452   Scan          header only
    UDP  host    -> console      ScanResp      NetworkInfo, 0x480
    TCP  console -> host:11452   Connect       NodeInfo, 0x40
    TCP  host    -> console      SyncNetwork   NetworkInfo with the console seated, held open

`nn::ldn::NetworkInfo`，0x480 位元組：

    +0x000  NetworkId          IntentId 0x10 (u64 localCommunicationId, u16, u16 sceneId, u32) then SessionId 0x10
    +0x020  CommonNetworkInfo  MAC 6, Ssid 0x22 (length byte then 0x21), s16 channel, u8 linkLevel, u8 networkType, u32
    +0x050  LdnNetworkInfo     SecurityParameter 0x10, u16 securityMode, u8 acceptPolicy, ...
    +0x066                     u8 nodeCountMax, u8 nodeCount
    +0x068                     NodeInfo[8], 0x40 each: u32 IPv4 LE, MAC 6, u8 nodeId,
                               u8 isConnected, 0x20 name at 0x0C, u16 localCommunicationVersion at 0x2E
    +0x26A                     u16 advertiseDataSize, then 0x180 bytes of advertise data
    +0x478                     u64 authenticationId

節點 0 的地址必須是可達的 LAN 地址：遊戲主機會把 Pia 傳送到那裡。節點的 MAC 由其地址派生（172.16.86.1 對應 `02:00:ac:10:56:01`）。遊戲的節點在 +0x2E 處帶有 88。火紅的掃描過濾器只比較 `localCommunicationId` 和 `networkType`。

16 位元組的會話 id 是 `NetworkId.SessionId`、十六進位制的 `Ssid` 文本，以及 Pia 會話金鑰 `AES(game_key).encrypt(ssid)` 的明文；network id 是 `crc32(ssid[1:16])` [`pokeldn/ldn/crypto.py`:114]。陷阱：不匹配時仍能關聯，隨後遊戲主機靜默丟棄每一個數據報。

## 站點的廣播

已加入的遊戲主機發送不帶 DS 位的廣播與組播（CCMP 組金鑰，key id 1），以及發往 DS 的單播（成對金鑰，key id 0）。火紅以一個針對主機的 ARP 開場；不應答該 ARP 的主機會被以原因碼 3 解除認證。標準接入點會丟棄這些幀；[ESP32](hardware_esp32.md) 會把它們完整轉發。

## 通道

LDN 還允許 5 GHz 的 36-48 通道，ESP32 無法到達；火紅／葉綠只使用 2.4 GHz。板子也能聽到相鄰通道上的主機；在那裡加入會在主機的下一次廣播時被丟棄，因此掃描會報告最繁忙的通道：

    POKELDN_RADIO=esp32:auto ./.venv/bin/python tools/ldn/ldn_scan.py --keys PROD_KEYS --dwell 2.5
