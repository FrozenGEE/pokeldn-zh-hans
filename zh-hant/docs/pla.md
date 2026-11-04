---
title: 傳說 阿爾宙斯
nav_order: 8
has_children: true
---

# 傳說 阿爾宙斯

Pokemon Legends: Arceus（標題 id `01001f5010dfa000`）是原生 Switch 遊戲，Pia 6.16-6.23 被靜態
連結進 `main`。地址是更新 1.1.1 解壓後 `main` 裡的偏移，按 `tools/switch/nso_read.py` 的排布方式
（text `0x0..0x32a5690`，rodata 從 `0x32a6000` 起，data 從 `0x401a000` 起）。

## 無線層

| | 值 |
|---|---|
| Pia 頭部版本號 | 11（劍 4，BDSP 9，GBA 應用 15/16） |
| 頭部大小 | 0x1C |
| 線上 GCM 標籤 | 8 位元組，從 16 位元組截斷 |
| LDN 口令 | 劍/盾的口令，即 `HGhG` 這種拼寫（wiki 的 `HGHG` 行是錯的）；rodata `0x3985319` |
| Pia 遊戲金鑰 | `p1frXqxmeCZWFv0X`，與劍/盾和朱/紫相同；rodata `0x3985308` |
| LDN 本地通訊 id | `0x01001f5010dfa000`，也就是標題 id |

LDN 初始化 `0x2c1e684` 從 `x3` 取本地通訊 id（在 `0x264082c` 構造），並在 `0x2c1e880` 裝入遊戲
金鑰。頭部初始化器 `0x6f0744` 把 magic 存到物件 `+8`、把 `0x0b` 存到 `+0xc`；校驗器 `0x6f07d0`
檢查 magic、`(byte & 0x7f) == 11` 以及長度減 0x1C 小於 0x5a5。資料包緩衝區在 `+0x30`（容量
0x5c0），長度在 `+0x5f8`；欄位大小來自複製賦值 `0x6f0878`：

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

加密路徑 `0x6f09f4` 減去 footer，用 0xFF 填充到塊大小，從緩衝區 `+0x4c` 開始加密，經 GCM 入口
`0x6e68d0` 以標籤長度 8 寫入標籤（`0x6f0b24`），然後把 `0x80` 按位或進版本。

斷點：套接字讀取 `0x6ff6d8`，校驗器 `0x6f07d0`，解密 `0x6f0b84`（在這裡失敗，原因不是金鑰、
IV 就是標籤），`LdnBackgroundProcessJob::WaitConnected` `0x7015b4`。

分派鍵是資料包的源變數 id：來自注冊表中不存在的站的訊息會被跳過，而變數 id 每個會話都會重新
生成。訊息標誌 `0x01` 跳過源變數 id 檢查；`bin/pla_host.py` 在兩個探測上都設定了它。

## 資料包加密

| | |
|---|---|
| 會話金鑰 | 對網路 SSID 的一個塊做 `AES-128-ECB(game key)` |
| 網路 id | `ssid[1:16]` 的 CRC-32 |
| GCM IV | `u32be(network id XOR source IP)`，然後是頭部的八個 nonce 位元組 |
| 頭部 nonce | 每包遞增的大端計數器 |
| 標籤 | GCM 標籤的前 8 位元組 |

`0x70d61c` 匯出會話金鑰；`LocalOutputStream::vfunc3`（`0x711710`）構造 IV。`pokeldn/ldn/crypto.py`
覆蓋 6.16 到 6.42。

## 資料包之上的協議

Pia 6.16 到 6.30 把 5.29 到 5.45 的 id 保留在會話層之下，並用一個會話協議取代站協議和網格
協議：

| 協議 | 5.29-5.45 | 6.16-6.30 | 6.32-6.40 |
|---|---|---|---|
| Net | 無 | 0x2C | 1 |
| RTT | 0x58 | 0x58 | 3 |
| 不可靠 | 0x68 | 0x68 | 5 |
| Clone，對時鐘原子 | 0x74-0x77 | 0x74-0x77 | 6-9 |
| 可靠 | 0x7C | 0x7C | 10 |
| 廣播可靠 | 0x80 | 0x80 | 11 |
| 會話 | 0x94 | 0x98 | 13 |
| 監控資料 | 0xA4 | 0xA4 | 15 |
| 站、網格、同步時鐘、本地 | 0x14, 0x18, 0x1C, 0x24 | 無 | 無 |

`pia_connect.py` 以重新編號的 id 適配這個區段。遊戲主機的加入請求列出：

    Net 0x2c v0   RTT 0x58 v3   Unreliable 0x68 v1   Clone 0x74 v0   Clock 0x77 v0
    Reliable 0x7c v2   BroadcastReliable 0x80 v3   0x81 v3   Session 0x98 v0   Monitoring 0xa4 v0

一條訊息在它的載荷結束處結束；這個區段不把訊息對齊到四位元組（5.27-5.45 會）。填充位元組在每一層
都是 0xFF：訊息遍歷讀到存在位元組 0x00 時，會把它當成一個繼承上一條訊息欄位的一位元組頭部，所以
零填充會讓資料包失敗（`0x74419c`）。遊戲主機在 `0x6f0af8` 處用 0xFF 預填它的加密緩衝區；
`0x6e6cb0` 把塊大小設為 16。`pokeldn/ldn/pia6.py` 講版本 11，`pia5.parse_messages` 讀取成幀。
`tests/test_pia6.py` 固定了佈局、金鑰匯出、兩個抓到的廣播，以及每一個從 `main` 讀出的常量。

| 協議 | 頭部目的地 | 尾部 |
|---|---|---|
| 會話、Clone Clock、可靠 | 對端的變數 id | 無 |
| RTT、可靠廣播流 | 網格目的地 0x0001 | 接收方的變數 id，明文 |

在頭部定址到對端變數 id 的 0x81 訊息永遠到不了遊戲。

### Net 協議

遊戲主機在託管自己的網路時，以 `NetUpdateNetworkConnectionStatusMessage`（0x2C 型別 0x11）開場，
即 wiki 的 6.16 到 6.39 佈局：

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

### 會話加入請求

一個 115 位元組的會話型別 0：型別位元組、一個協議計數、十個 `(id, version)` 對，然後是：

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

位置 id 是 12 位元組：大端 u64 常量 id、兩個零位元組、大端 u16 變數 id。訊息標誌是 `0x01`。
`pokeldn.ldn.pia6.build_session_join` 復現它（`tests/test_pla_session_v11.py`）。

遊戲主機的 `ClusterPacketReader` 門 `0x744644`（vfunc `0x98`，在 `0x743ec0` 呼叫）在它的站列表裡
查詢單播資料包的源變數 id（`0x744718`），沒有匹配時丟棄它（`0x7447a8`）；發往目的地 0 或 1 且
沒有尾部的資料包，或源變數 id 為 0 的資料包，跳過查詢。加入請求必須發往頭部目的地 0；定址到
遊戲主機的變數 id 時，它會在解密後被丟棄。

### 會話加入回覆

加入方在 `0x737534` 解析 ack、在 `0x7379c0` 解析加入響應，二者由 `0x7353a0` 經型別表 `0x3973f19`
分派。每個都會丟棄四個 id 不匹配的訊息：主機的 id 是請求的目的地 id，遊戲主機的則是它的源 id。

ack 是型別 1、25 位元組：型別、主機位置 id、遊戲主機位置 id。它設定 `JoinMeshJob+0x69` 並把截止
時間 `+0x80` 延長 8000 ms。加入響應是型別 2、43 位元組：

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

分配欄位不做校驗（第一個加入者得到路由 `00 01`、索引 1、次序 1）。狀態 1 會停止重複。當一條
型別 5 更新到達 `+0x29` 的序列並被應用時，加入完成；加入方用一個 13 位元組的型別 6 作答：型別、
自己的常量 id、兩個零位元組、序列。

### 型別 5 的站列表更新

`0x7404a8` 在 `0x73897c` 讀取它之前重組它。分片頭部是 7 位元組：型別、大端 u16 序列、計數、索引、
大端 u16 偏移（單分片時為 3）。正文：

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

IPv6 站用 18 個地址位元組代替六個。主機是路由 `00 00`、索引 0、次序 0。

`0x738bc0` 按常量 id 更新或建立每個站。已加入的遊戲主機隨後執行 RTT、Clone Clock 和可靠廣播流。

### 主機遷移

一臺託管交換的遊戲主機不會回應定址到它變數 id 的加入請求，而是要求已加入的站接管主機角色：

| 加入方 | 遊戲主機 |
|---|---|
| 用 0x12 回應 0x11 | 再次 0x11，`is migrating host` 置 1，然後約每秒兩次 `01 40 00 00`（`NetStartHostMigrationMessage`） |
| 傳送加入請求，從不回應 0x11 | 每 0.5 s 一次 0x11，然後遷移，然後 0x40，然後網路斷開 |
| 用 `NetUpdateNetworkHostMessage` 回應 | 持續重複 0x40 |

託管中的遊戲主機離開時總會遷移（`NetProtocol+0x248`，由其建構函式置 1）：`NetDestroyNetworkJob`
（`0x7069d0`）傳送一條遷移中的 0x11，最多等 4000 ms 等每個 0x12，隨後在 4000 ms 內每 300 ms
傳送 0x40（0x11 未被確認時為 2000 ms），然後銷燬網路。`LeaveMeshWithHostMigrationJob`
（`0x73eee4`）先最多輪詢 8000 ms 找下一個主機；路由位元組在 0xfd 的站永遠不合格。

點名繼任者的型別 7 出現於遊戲主機的 WaitMember 在加入被接受之前就結束的時候，朱的情況就是
如此（[docs/sv.md](sv.md#what-decides-a-seat)）；`bin/pla_join.py --join-delay 4.5` 能引出它。
遊戲主機每秒重發它，直到收到型別 8。型別 8 處理器 `0x739b08` 只接受第二個位置 id 是遊戲主機
自己的 25 位元組訊息；當第一個 id 等於 `+0x68` 處的目標時，`0x73f0a8` 置任務的完成標誌 `+0xb0`：

    08 | joiner location id (12) | host location id (12)

新主機在同一程式碼上建立網路來完成遷移；遊戲主機加入它並以加入方身份交換。`bin/pla_join.py` 在
收到第一個 0x40 時讓出席位，並在相同的程式碼和通道上執行 `bin/pla_host.py`，或用 `--ip-join` 走
IP（`--take-host`，預設開啟）。

## 靜默站檢查

每次會話更新（`0x73564c`）都會列出靜默時間超過 `SessionProtocol+0xd8`（10000 ms）的每個
站（來自啟動設定 `+0x28c`，沒有下限；Z-A 有 4000 ms 的下限）。再過 3000 ms 後主機把每個站踢出
（`KickoutManageJob`），而加入方會把被列出的主機視為已離開。盒子介面上的靜默主機會在約 13 s 時
引出夥伴離開的訊息。

## 遊戲的讀取器與前置處理器階段

遊戲在 `main+0x2ca4f30`（`0x741494`）輪詢它的讀取器：迴圈處理 0x7C 和 0x80，兩者共用一個處理器
表。訊息的前八個位元組是一個由兩個 u32 組成的處理器鍵；匹配到的處理器接收其餘部分，未匹配的鍵被
丟棄。0x81 上的主機資料永遠到不了這裡。遊戲裡的九個 Pia 呼叫點只解析 0x68、0x7C 和 0x80；0x77
的時鐘流量是 Pia 自己的。

在搜尋介面，表是空的，每條訊息都被讀取後丟棄；處理器在流程步驟 0x1e（`0x2ca5264`）註冊。

交換流程是 `0x13d5bfc`（步驟 `[flow+0xa4]`，表 `0x397c118`）。步驟 0x17 構造匹配序列
（`0x26bdcac`）；步驟 0x18 輪詢它和網路選單的頁面結果（`0x13de870`）。序列的步驟：

    LoginRelayServer     looked up before the sequence is built; missing returns false
    Matching             from TradeMatchmakingConfig (0x26be354)
    DataExchangeStart    the two-round data exchange, 10.0 s deadline (0x26be3f0)
    OnCancelDataExchange
    OnSuccess            the trade scene (0x26d5f64)
    OnFailure            event 8, flow step 0x23 (table 0x397c134), the leave
    OnCancel
    Cleanup

DataExchangeStart（`0x26c5288`）在會話建立後開始，一旦至少兩個站的記錄到達就完成；超過 10.0 s
（`0x26c6a94`）則以 `net_contents::p2p::ErrorLeaveAnyone` 失敗（vtable `0x416c628`，
`0x26c6d30`）。失敗路徑走 `0x13d654c -> 0x13d6384 -> 0x2c43d78 -> 0x2ca0a10 ->
Session::LeaveAsync (0x72a6dc)`，然後是錯誤 7 對話方塊；主機帶著遷移離開。

`Error::Timeout` 的唯一來源是監視器 `0x2bdb754`，它在匹配的兩個 WaitMember 步驟裡被武裝：
25000 ms（`0x2bda24c`）和 `3000 + rand % 1000` ms（`0x2c491b8`，目標是匹配記錄的 `+0x22` 半字，
在程式碼 00000000 下為 2）。當成員數（`[Session+0xe0]`，即 Pia 會話的成員列表）達到目標時
WaitMember 完成；沒有任何東西延長這個計時器。列表裡存本機站以及每次被接受的會話加入各一條
（對加入方來說，是每個型別 5 的站）；僅有 LDN 關聯或 Net 0x11 不計入。沒有成員時搜尋會在這個
計時器上重新託管，每 2.4 到 4.3 s 換一個新網路、新會話 id，所以加入方只有一個網路計時器剩餘的
時間被計入。

### 資料交換

DataExchangeStart 在可靠廣播流（0x81）的埠 0 和 1 上等待兩輪交換：每個站用
型別 0x0f 的訊息開啟流，在標誌 0xa0 下用 44 位元組的 `0000002c ffff` 訊息確認，併發送一條 74 位元組
的型別 0x1f 記錄，其中攜帶 64 位元組、以 `484b6264` 開頭的載荷。這一步在對端的第二輪記錄到達時
完成。加入的遊戲主機會主動開啟自己的流，並在主機之後傳送自己的記錄；託管中的遊戲主機會先發，
在加入方開啟時發。主機回應遊戲主機的開啟時，會把埠 0 上的記錄和埠 1 上自己的開啟捆在一個
資料包裡；`bin/pla_host.py` 每次加入傳送一次，若在空氣中丟失就以錯誤 7 結束。

這 64 位元組載荷是 139 位元組記錄（`pokeldn.pla.data_exchange`）的 zlib 壓縮（4 KB 視窗，級別 5），
位於 Pia 的 StreamData 頭部之下的一個塊裡（[協議 0x81](pia.md#protocol-0x81-the-stream-broadcast-reliable-transfer-pia-6)）：

    +0x00  1   StreamData kind, 1: first chunk
    +0x01  1   transfer id, 0
    +0x02  1   percent delivered, 0x64
    +0x03  4   zero
    +0x07  4   big-endian u32 0x80
    +0x0b  128 the MyStatus block (PKHeX MyStatus8a): trainer id pair +0x1b, version +0x1f (47),
               gender +0x20, language +0x22, UTF-16LE name +0x2b

遊戲只把這一個塊交給 Pia（`0x26bfd28` 處的 `0x753554`）。為接收方玩家生成的神秘禮物會讀取遊戲
主機的訓練家（`data_exchange.read_trainer`，[為接收方玩家生成](gift_simulated.md#made-for-the-receiving-player)）。

塊 +0x3c 是玩家外觀，取自開場 4x2 的 `grid_player` 的列 + 4 x 行（設定器 `0x1023f94`），列 2 和 3
為女性；它必須與 +0x15 的性別一致。`data_exchange.build_record` 由 `--gender` 決定傳送 5（男）
或 7（女）。塊 +0x50 是 1，由初始化器 `0x10230e4` 寫入。

## 維持網格

RTT（0x58）是 11 位元組：kind、八位元組時間戳、兩位元組目標；目標為 0 的 kind-1 回顯會被接受。

可靠廣播流（0x81）承載 `pokeldn/ldn/reliable5.py` 的視窗：9 或 13 位元組的頭部，
然後是資料，或在資料標誌清除時是 `2 + 21 * count` 位元組的批次確認（型別位元組，讀取位 0；條目為站
位元組、u16 ack id、u16、16 位元組掩碼）。消費者（vf13 `0x742730`）讀取自己站索引處的條目，並要求
其站位元組等於傳送者的索引：主機確認索引 1 的加入方時會發送兩個站位元組為 0 的條目。id 通過
`0x74f0ec` 生效。遊戲主機的 0x81 訊息攜帶序列 1，所以主機確認 `ack_id 2`。

遊戲主機用 INITIALIZED 訊息開啟它的流（標誌 `0x0f`，序列 1）；主機資料需要遊戲主機站索引對應的
目的地點陣圖位（位 1，計數 2）。

## 遊戲的可靠通道

交換之後流程到達 `0x13d5cac`，它檢查 `[net+0xb8] > 1`：狀態 0 經 `0x26d9170` 到 1，1 在
`[net+0x78]` 上到 2，該欄位由接收處理器 `0x26da310` 在選擇器 1 上設定（`0x26da3a4`）。

分派器 `0x2ca4a88` 把訊息的鍵與每個通道的 `+0x6c` 匹配。存在兩個通道：鍵
`00 00 00 00 00 00 00 00` 用於交換盒（`0x26d8c2c`），`01 00 00 00 00 00 00 00` 用於階段協議
（`0x26d7aa0`）。0x7c 的埠 0 和 1 是兩個可靠例項；埠 1 是通道表。

兩個埠都用 `reliable5` 流開啟（無點陣圖，發往對端的變數 id，序列 1，start、end 和 initialized
標誌）；每側都確認併發回同樣的東西：

    port 0    key eight zero bytes      body 0100        the host opens it
    port 1    b9 01 01 b9 02 b9 02 00 00 01              the joiner announces the zero key open

### 確認

`ReliableSlidingWindow`（vtable `0xc5b4d98`）在 vf12 `0x74ee1c` 中構造它的 ack：id 為接收視窗的
`+0x50`，其後每個持有的條目在 16 位元組掩碼中佔一位（`0x74ef18..0x74efb8`），當 `[window+0x54]`
置位時為空。vf13 `0x74efbc` 解析它（`0x742da0`），要求 `2 + 21 * count` 位元組且條目的流位元組等於
`+0x36`，並呼叫 `0x74f0ec(window, station, ack_id, mask)`。一個傳送條目是 0x5d0 位元組，序列在
`+0x24`，每站待決點陣圖在 `+0x2c`：

| 條目序列 | 待決位 |
|---|---|
| 低於 `ack_id` | 清除（`0x74f274`） |
| 等於 | 保留 |
| 高於 | 當掩碼位 `seq - ack_id - 1` 置位時清除，偏移最大到 0x7f（`0x74f280..0x74f2a8`） |

| `ack_id` | 效果 |
|---|---|
| 0 | 無（`0x74f0fc`） |
| 低於基址 | 設定 `[window+0x4b8]`（`0x74f17c`，`0x74f2d0`） |
| `base + count`（`[window+0x32]`） | 釋放全部 |
| 超出 | vf6 `0x74f2e8`，一個裸 `ret`：忽略 |
| `0xffff` | 應用整個視窗（`0x74f104`） |

id 是累積的；掩碼是 128 位小端整數的第 n 位（`pokeldn.ldn.reliable5.build_mask`）。

接收方根據每條訊息的最低待決欄位移動視窗基址，ack 也算在內（`0x74c250`）。絕不要把最低待決
宣告到一條未確認訊息之後：它的重傳會落在基址之下並被丟棄。

`bin/pla_host.py` 和 `pokeldn.pla.joiner` 使用 `reliable5`（`SendWindow`、`ReceiveWindow`）：
保留每條 0x7c 訊息直到被確認，0.4 s 後以相同序列和新 nonce 重傳，最多隻宣告自己的最低未確認
序列，確認連續段之後的一個，按序只交付一次。加入方的 0x81 訊息每 1 s 重傳一次。遊戲主機在某個
埠上的第一條 0x7c 訊息攜帶序列 1（66/66）。

遊戲主機對 0x7c 和 0x81 一視同仁地重傳（`0x74c9c8`），間隔為 33 ms + 1.4 x 最大往返時間
（`0x74d06c`），沒有重試上限，直到收到視窗內的 ack 或該站離開。

## 埠 1 上的通道表

0x7c 的埠 1 承載通道表：每個站宣告自己已開啟的處理器鍵，而一個站只有在對端宣告該鍵已開啟後
才在它上面傳送。

表物件（`0x2ca36f0`，vtable `0x41997d8`）儲存自己的通道（`+0xa0`）和對端宣告的通道（`+0xd8`），
每個條目是一個八位元組鍵和一個站掩碼；幀輪詢 `0x2ca82d0` 負責收發。

傳送方把已存在的通道宣告為開啟、把已銷燬的通道宣告為關閉。接收方（`0x2ca9800`）在開啟時把
傳送方的位或進對端條目、在關閉時清除它，遇到未知鍵則追加一個條目；回收器擦除零掩碼的條目，
離開的站的位在各處都被清除（`0x2ca90e0`）。建立通道（`0x2bcb8c8 -> 0x2ca5264 -> 0x2ca3024`）
時把表的介面儲存在 `+0xb8`。每個通道傳送方都詢問介面槽 3（`0x2ca92e0`，經 `0x2ca9360`）對端
是否宣告了它的鍵，只有答案為是才傳送：主機在埠 1 上沉默會讓交換介面一直等待。

一條訊息是遊戲的帶標籤序列化：小於 0x80 的整數就是它自己那一個位元組；0x80 到 0x83 字首一個小端
的 1、2、4、8 位元組值（寫入器 `0x2661ec4`、`0x26619cc`、`0x2661f78`）。尺寸表 `0x397dfcc` 給
0x84 到 0x87 同樣的寬度，0x88 四位元組，0x89 八位元組，0xb5 到 0xbf 一位元組。0xb9 開啟一個元組，
後面跟著欄位計數。

    b9 01  NN  { b9 02  b9 02 LO HI  01|00 }    list of NN (key as two u32, open 1 / closed 0)

| 訊息 | 含義 | 時機 |
|---|---|---|
| `b9 01 01 b9 02 b9 02 00 00 01` | 交換盒鍵開啟 | 隨埠 1 的開啟，在交換步驟 |
| `b9 01 01 b9 02 b9 02 01 00 01` | 階段鍵開啟 | 確認之後，`0x26d7aa0` 建立它時 |
| `b9 01 01 b9 02 b9 02 01 00 00` | 階段鍵關閉 | 交換寫入之後 |

`pokeldn.ldn.channel_table` 構造並解析這些。主機對每個鍵只回應一次開啟，並不回應關閉，所以它
常駐的條目服務於下一次交換。

## 交換盒

在埠 0 上零鍵之後，處理器 `0x26da310` 讀取一個選擇器和一個計數器，經 `0x397e388` 分派，丟棄
大於 7 的任何值，並且除非它的第四個引數等於 `[net+0x88]`（即夥伴）就中止。

    1   ready                0x26da3a4   sets [net+0x78]; the port-0 open body 01 00, once a session
    2   showing a Pokemon    0x26da3f0   stored at [net+0x98] by 0x26da1d8
    3   showing no record    0x26da430   -> 0x26d93c8
    4   offering a Pokemon   0x26da3b0   stored at [net+0xb0] by 0x26da23c, phase 0xbc := 3
    5   confirmed            0x26da43c   counter check, -> 0x26da2c0
    6   withdrawn            0x26da458   state 4|5 := 3, phase 0xbc := 2, counters moved
    7                        0x26da49c   counter check, phase 0xbc := 5

`0x26d9458` 傳送選擇器 2 並附帶游標下的記錄（從 `0x2b65514` 起的 0x178 位元組），或對空槽位傳送
無載荷的選擇器 3（`03 00`）。選擇器 2 和 4 攜帶相同的載荷；只有 4 會推進階段。主機必須用報價
回應報價：若用展示來回應，遊戲主機會顯示一個空的夥伴六邊形。

選擇器 6 撤回一次報價或一次確認（傳送方 `0x26d9898`，計數器 `[net+0xf8] + 1`）。接收分支把
狀態退回 3 且不傳送任何東西：回顯的 6 會取消遊戲主機的確認。

載荷（`0x26dac6c`，`0x26662fc`，`0x26dacbc`）：

    0x00  1   selector
    0x01  1   counter, 0 on both record-carrying selectors
    0x02  1   0xbc
    0x03  1   0x81
    0x04  2   record length, 0x178
    0x06  376 the record

九位元組頭部之下 390 位元組，標誌 0x07，序列 2。它只依賴存檔，所以抓包可以重放。

記錄是第八世代的實體（`pokeldn.gen8` 頭部、LCG、塊置換、16 位校驗和），塊大小為 0x58 位元組：
儲存時 0x168，在隊伍中 0x178。解密時 `gen8.BLOCK_ORDER[(ec >> 13) & 31]` 按原樣應用，加密時取反；
校驗和分辨不出這兩者，名字可以（暱稱在 0x60，訓練家名在 0x110）。0x0c 處的訓練家 id 和訓練家名
就是資料交換所攜帶的那些。

## 確認交換

交換時它傳送選擇器 5 和 `[net+0xf8]`。傳送方 `0x26d9770` 要求狀態 3 並置 4。消費者 `0x26da2c0`
置階段 4，當狀態已是 4 時分配 `[net+0xc8]`：第二個確認的站繼續。選擇器 5 和 7 會丟棄低於
`[net+0xfa]` 的計數器（`0x26da440`，`0x26da4a0`）。遊戲主機隨後在埠 1 上宣告階段鍵開啟，並在
階段 5 等待，直到主機也宣告它。

tick `0x26d9094` 推進 `[net+0xb8]`：

    0     if [net+0x90] is set, 0x26d9170 -> 1
    1     once [net+0x78] is set, one store of 0x200000002: state 2, phase [net+0xbc] 2
    3, 4  while [net+0xc0]: past 1.5 s on [net+0xc8] with phase 4 or 5, 0x26d9254 sends
          selector 7, state 5
    5     finished; the save is untouched until the job below

## 執行交換的任務

這個任務（`0x26d9a90`，vtable `0x416c8f8`，更新 `0x26dc71c`，執行器 `[job+0x130]`）攜帶被報價的
記錄 `[net+0xb0]`。

| 狀態 | 動作 |
|---|---|
| 1 | 傳送階段 3（`0x26d7d8c`）；只有傳送成功才到狀態 2 |
| 2 | 等待主機的 `02 03`（`0x26d7e5c`） |
| 3 | 交換限制已設定並儲存（vf `+0x50` `0x26dd910`） |
| 4, 5 | 傳送階段 6，等待 `02 06` |
| 6 | 交換已應用，限制已清除（vf `+0x58`） |
| 7 到 10 | 傳送 `0x0b`（狀態 9 中隨機 2 到 302 幀之後），等待 `02 0b` |
| 11, 12 | 提交存檔（`nn::fs::Commit`），傳送 `0x0e` |
| 13 | 等待 `02 0e` |
| 14 | 成功（`[net+0xb8] = 6`）或失敗（7） |

傳送門失敗會重試下一次更新；停在狀態 1 或 2 的任務沒有超時，並顯示 `msg_ui_box_p2ptrd_09`，
“正在通訊。請稍候……”。它只能通過取消請求 `0x26dc640` 結束，來源是場景監視器 `0x1109d00` 在會話
錯誤或夥伴離開（站計數低於 2）時，或來自模式 9。遊戲主機在等待期間沒有待辦：主機重發它十一個
回答中任何在空氣中丟失的（埠 0 開啟、兩次通道開啟、展示、報價、選擇器 5 和 7、四個階段）。

取消在狀態 `0x3ff7 >> state & 1` 中接受（0 到 2，4 到 13）。在階段 2 到 4 被取消時，執行器先
完成存檔；vf `+0x48` `0x26dd5f8` 只在 `[executor+0xb0]` 置位時寫入，該標誌在狀態 6 完成。在
狀態 1 或 2 被取消的任務什麼也不寫。

## 交換限制

限制是存檔塊 `0x96993D83` 中一個 u64 的分鐘計數，位於 `[game manager+0x2b8]` 物件的欄位 `+0x70`
（vtable `0x40f2048`）。塊 `0x24E0D195`（欄位 `+0x78`，0x2F2 位元組）儲存一個標誌位元組，然後是最近
換入的記錄。

`+0x78` 處的位元組標記一條已收到但尚未放置的記錄：在任務狀態 6 置位（`0x10251c8`，記錄在 `+0x79`，
進化形態在 `+0x1f1`），由 `0x26dcc74` 清除，後者放置記錄、把它登記進圖鑑並儲存。

| 位置 | 呼叫者 | 值 | 時機 |
|---|---|---|---|
| `0x26dd9a0` | vf `+0x50`，任務狀態 3 | 10 | 夥伴的 `02 03` 之後，在任一記錄移動之前 |
| `0x26ddaf0` | vf `+0x58`，任務狀態 6 | 0 | 交換已應用 |
| `0x26dd704` | vf `+0x48`，取消 | 10 | 僅在 `[executor+0xb0]` 置位時 |
| `0x26bd5d0` | 計時器 `0x26bd434` | 減 1 | 每 60 s |

狀態 3 在設定 10 之後儲存。在狀態 3 之前被停止的交換不會留下限制；在狀態 3 與狀態 6 之後的儲存
之間被停止的交換，會在存檔裡留下 10。

計時器（`0x26bd434`）每 60.0 s 的系統 tick（`0x26bd5b4`）減一次：遊戲執行十分鐘即可清零。時鐘
設定不起作用，遊戲關閉期間的時間不計入。

當計數非零時，連線交換的夥伴選單（`0x13d55fc`，`0x13d56ac`）會顯示 `common/net` 的
`matching_win_03`（上次連線被中斷），而不是警告 `matching_win_06`。

## 階段協議

任務在鍵 `01 00 00 00 00 00 00 00` 上宣告階段，該鍵在任務建立時註冊。宣告物件儲存三對
標誌/半字：

    [obj+0x94] / [obj+0x96]   own announced phase, written by 0x26d7d8c (selector 1)
    [obj+0x98] / [obj+0x9a]   the peer's, on receiving selector 1
    [obj+0x90] / [obj+0x92]   written by 0x26d7e84 (selector 2), and on receiving selector 2

接收處理器 `0x26d7f90` 映象傳送方；選擇器 0 中止。訊息就是選擇器和階段。`0x26d7e5c(obj, n)` 在
`+0x90` 置位時返回 `[obj+0x92] == n`。

選擇器 2 由主機發送：`0x26d7e84` 只在 `[obj+0x78]` 之後可達，該欄位在任務建立時由 `0x26d7aa0`
設定，條件是本站是會話的主機。加入方的任務只在主機的選擇器 2 上離開狀態 2；只映象選擇器 1 的
主機會讓交換介面一直等待。

一個站在某個埠上發起的每條訊息（包括映象）都取自己下一個序列 id；複用對端 id 的映象會被
確認，但一旦計數出現分歧就被丟棄。

## 完成的交換

遊戲主機宣告 3、6、0xb 和 0xe；主機用選擇器 2 和相同的階段逐個作答：

    <-  0x7c p0  01 03      ->  01 03   the mirror     ->  02 03   the host's
    <-  0x7c p0  01 06      ->  02 06
    <-  0x7c p0  01 0b      ->  02 0b
    <-  0x7c p0  01 0e      ->  02 0e

動畫之後，盒子把主機的玩家記為原始夥伴。八個存檔檔案發生變化：兩個槽位裡的 `main`、`main2`、
`backup`，以及兩個 ExtraData 檔案。遊戲主機隨後傳送一個新的選擇器 2（主機用一次展示回應），以及
階段鍵關閉（無人回應）。

## 同一會話中的第二次交換

一次交換完成後，場景重置交換物件（`0x26d8fd0`，在 `0x110aa04`）：任務的輸入和記錄被釋放，任務
被釋放，狀態和階段為 2，計數器 `[net+0xf8]` 歸零。`[net+0x78]` 和 `[net+0x88]` 保留：下一輪從
狀態 2 開始，沒有新的選擇器 1。場景（更新 `0x1109a68`，模式 `[scene+0xb0]`：0 盒子，5 交換，
6 夥伴離開，7 和 8 會話錯誤，9 離開）在會話保持的情況下回到模式 0。`0x10fb178` 清除盒子控制器
的有效標誌，所以盒子會發送一次新的展示；否則它只在游標移動時傳送一次。

下一個任務再次用鍵 1 建立它的階段通道，並使用相同的階段。第二次交換逐位元組重複 `05 00`、
`07 00`、各個階段和階段鍵開啟；只有序列 id 不同，所以按載荷去重的對端一個都不回應。回應了遊戲
主機關閉的主機，會讓第二個 `01 03` 卡在門裡：任務停在狀態 1，無超時，無限制。

## 一次交換改寫了什麼

一條收到的記錄在這些欄位上與發出的那條不同（對一條以 70 級隊伍尾部發送的 50 級記錄，共 23
位元組）：

    0x006  2   checksum
    0x092  1   current HP
    0x0b8  26  handling trainer's name, the receiver's own
    0x0d3  1   handling trainer's language (3 French, 2 English)
    0x0d4  1   current handler, 1
    0x0d8  1   handling trainer's friendship, the species' base friendship
    0x16a  12  the six party stats, recomputed

高於等級的相遇等級會被保留。塊起點是 `pokeldn.gen8` 的起點加上每個前置塊八位元組：暱稱 0x60，處理
訓練家名 0xb8，訓練家名 0x110，隊伍尾部 0x168。第一塊是第八世代的塊，但招式在 0x54（PP 0x5c），
第二塊加 8，第三塊加 0x10，第四塊加 0x18，球在相遇日期之後。`pokeldn/pla/trade_box.py` 和
`pokemon.py` 復現遊戲主機的位元組。

## 選擇要報價的內容

遊戲讀取 PKHeX 的 PA8：

| 偏移 | 欄位 | 偏移 | 欄位 |
|---|---|---|---|
| 0x08 | 物種 | 0x92 | 當前 HP |
| 0x0a | 持有物 | 0x94 | 打包的個體值 |
| 0x0c | 訓練家 id，32 位（顯示為對 1000000 取模） | 0xa4 | 成長值 |
| 0x10 | 經驗 | 0xac, 0xb0 | 絕對身高、體重（浮點） |
| 0x14 | 特性 | 0xb8 | 處理訓練家 |
| 0x16 | 頭目標誌位 | 0xee | 版本 |
| 0x1c | 性格值 | 0xf2 | 語言 |
| 0x20 | 性格（9 是 Lax） | 0x110 | 訓練家名 |
| 0x24 | 形態 | 0x134 | 相遇日期 |
| 0x26 | 努力值 | 0x137 | 球 |
| 0x3e | 頭目招式 | 0x138, 0x13a | 蛋與相遇地點 |
| 0x50, 0x51, 0x52 | 身高係數、體重係數、體型係數 | 0x13d | 相遇等級與訓練家性別 |
| 0x54, 0x5c | 招式、PP | 0x159 | 已購招式記錄 |
| 0x60 | 暱稱 | 0x15d | 已掌握招式點陣圖 |
| 0x8a | 重新學習招式 | 0x168, 0x16a | 等級、六項能力 |

在 47 條抓到的記錄中，頭目在 0x50 到 0x52 攜帶 0xff，體型係數等於身高係數，0x94 的蛋和暱稱位
為清除，每條記錄都攜帶版本 47、語言 2、sanity 0 和 affixed ribbon 0xff。`pokemon.build` 在 376
個零位元組和校驗和之上寫入給定欄位。合成的記錄（異色、頭目、有暱稱、存檔從未有過的物種）能換入
並按要求顯示。加密常量和 PID 已被存檔持有的記錄會被儲存（盒子塊 `0x47E1CEAB`）；`--fresh-pid`
會重擲兩者。

`bin/pla_host.py` 按順序對每個 `(port, sequence id)` 只處理一次，並重發未確認的回答；被取消的
報價會以 `04 01` 重新報價。它在兩次報價之間重讀它的報價檔案。

### 已掌握招式

0x15d 處的八個位元組是遊戲 61 個招式掌握列表上的點陣圖；一個物種只能掌握它的 personal 條目允許的
那些（0xa8 處的 u64）。更改招式介面允許使用掌握等級（`mastery_la`）等於或低於當前等級的招式，
或位已置位的招式。

### 遊戲計算的能力

`pokeldn/pla/stats.py` 復現它們。每項能力是一個成長項，取整的
`(sqrt(base) * multiplier + level) / 2.5`，加上一個基礎項：HP 是截斷的 `((level / 100 + 1) * base)`
再加等級，其餘是截斷的 `((level / 50 + 1) * base / 1.5)` 再乘性格的 110% 或 90%。倍率由成長值
加個體值偏置讀出（31 及以上為 3，26 為 2，20 為 1），上限截到 10。用十二個等級 68、性格 14、
耿鬼的主機數字驗證：273/210/199/322/345/220（IV 31，成長 10）和 239/136/121/322/304/133。

0xac 和 0xb0 處的身高與體重是物種平均值乘以每個係數各自的
`(scalar / 255) * 0.40000004 + 0.8`，體重用兩個係數，以 32 位浮點計算（係數 111、221，平均值
150、405 得到 146.11766052246094 和 452.38031005859375）。表來自 PKHeX：`personal_la`（每條目
0xB0 位元組；0x21 的位 6 標記遊戲中的 264 個物種）、`lvlmove_la.pkl`、`MoveInfo8a`、`Experience`。

## Clone Clock 與 Atomic 協議

Clone Clock（0x77）訊息是 18 位元組：kind、序列、大端 u64 起始 tick、大端 u64 響應方時鐘（毫秒）。
kind 0 是請求（非主控時忽略）；kind 1 是回覆，推進 ClockProtocol `+0x5c`（0 復位，1 請求中，
2 已同步，3 主控，4 停駐）。加入的遊戲主機停在 4 併發送請求；回顯序列和 tick 並帶上主機時鐘的
kind-1 回覆會讓它同步。

Clone Atomic（0x74）訊息是 14 位元組：kind（0 宣告，1 提交，2 確認）、generation、大端 u32 元素
索引（小於 33）、大端 u64 值。只有交換場景建立元素；主機的 kind-0 宣告會引來一個 kind-2 回顯，
它不填充任何槽位。

## LAN 模式

傳說 阿爾宙斯 1.1.1 有一條它的程式碼從不走的 LAN 路徑。網路啟動 `0x2bb9a10` 為模式 1 構造本地
服務、為 2 構造網際網路服務、為 3 構造 LAN 服務（`0x711ab4`）。模式從網路任務的 `+0x78`
（建構函式 `0x2bbe7f4`）傳到那裡，其唯一的建立鏈終結於 `0x2629258(.., mode)`；它的兩個呼叫者
傳 1（`0x2628b74`）和 2（`0x262a020`），而沒有任何指標指向那條鏈上的任何函式。

## 託管

`bin/pla_host.py` 廣播標題、口令、場景 id 和連線碼；`pokeldn.pla.build_advertise_data(code)` 逐
位元組復現一個零售廣播（`app_version` 0，`security_mode` 1）。

    POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/pla_host.py --keys PROD_KEYS \
        --code 00000000 --seconds 240

搜尋介面上的遊戲主機交替地作為站掃描和在新的 SSID 下託管，約五秒一個迴圈。已關聯的加入方保持
沉默，直到主機每 500 ms 傳送一次 Net 0x2C 連線請求（`--no-net-probe` 會阻止它）。

## 加入遊戲主機的網路

`pokeldn.pla.joiner` 回應一臺託管中的遊戲主機：

| 主機發送 | 加入方回應 |
|---|---|
| Net 0x11 | Net 0x12，回顯序列，標誌 `0x11`，頭部目的地 0；第一次時附帶會話加入請求，標誌 `0x01`，目的地 0 |
| Net 0x50 | Net 0x51，回顯序列，目的地 0 |
| 點名加入方的會話型別 7 | 型別 8 |
| 會話型別 5 | 型別 6 |
| 第一個型別 5 | 埠 0 上的 0x81 流開啟，`0f00000b 0001 0001 01 00000001 0000000000008000000000` |
| 它在埠 0 上的 0x81 記錄 | ack，埠 1 上自己的記錄（標誌 `0x1f`，序列 1，點陣圖 `0x01`），然後 0x7c 埠 1 上的零鍵開啟 |
| 0x7c 埠 0 的開啟 `0000000000000000 0100` | 同樣的發回，序列 1 |
| 一次展示或一次報價 | 自己的，相同的選擇器和計數器 |
| 選擇器 5 和 7 | 相同的；7 之後是階段鍵開啟 |
| 階段鍵開啟 | 階段 3、6、11、14（選擇器 1），每個都在主機的回答之後，然後是鍵關閉 |
| RTT kind 0 | kind 1，回顯時間戳，最後是請求方的變數 id |

零售的加入方把它的 0x12 發往目的地 0（108/108）；定址到主機的變數 id 時讀取器門會丟棄它。
託管中的零售遊戲主機會在加入方之後 0.02 到 0.04 s 用選擇器 2 回應每個階段。絕不要因遊戲主機
自己的 `01 0e` 就關閉階段鍵：`02 0e` 永遠不來，遊戲主機在離開時顯示 2-AW7KA-0007 並保持限制。
`bin/pla_join.py` 在 `02 0e` 時關閉它，保持席位直到玩家退出或 `--hold` 結束（`--hold-after-trade N`
在最後一次排隊的交換之後 N 秒離開），並在每次交換後忘記已回答的步驟。它大約每秒在埠 0 和 1
上重複它的 0x81 確認：

    0000002c ffff 0002 01 00000001       header: size 0x2c, lowest pending 2, bitmap 1
    00 02                                type 0 the first time, then 1; two entries
    00 0002 0001 00*16                   the host's stream
    00 0001 0001 00*16                   its own stream

`tests/test_pla_joiner.py` 扮演一個指令碼化的主機；`tests/test_esp32.py` 在兩塊模擬板子上執行它。

## 在遊戲主機上進入本地交換

    title screen, A -> Jubilife Village, the trading post -> talk to Simona (Trado in French), A
    -> "echanger des pokemon !" -> local -> the restriction warning -> an eight-digit code
    -> "Echange en reseau ! Recherche d'un partenaire en cours..."

`0x397e1b8` 處的分鐘表（`30 30 60 60 ... 2160 2160`）是丟失挎包用的（`0x2686a0c`，基於網路時鐘），
與交換無關。

## 廣播

| | |
|---|---|
| 本地通訊 id | `0x01001f5010dfa000` |
| LDN 協議 | 1：AES-CTR 廣播，與劍相同 |
| 場景 id | 1 |
| 廣播幀版本 | 4（GBA 應用 3，劍 2） |
| 接受策略 | 全部 |
| 參與者 | 1 / 2 |
| SSID | 16 位元組，會話金鑰的輸入 |
| 應用資料 | 112 位元組 |

應用資料是 0x5C 的系統屬性塊（`docs/ldn.md`，6.16 到 6.41：系統通訊版本 21、應用版本 0、一個
16 位元組的使用者口令、玩家上限開啟、一名玩家、名字為一個空格），然後是明文中的連線碼：16 位元組
ASCII、以 NUL 填充，然後它的長度作為小端 u32（`0000 0000` 得到 `3030303030303030`、八個 NUL、8）。

### 廣播中的連線碼

使用者口令是連線碼經 Pia 的設定器 `0x6fc454` 加密的結果：在模式 1（`+0x234`）下開啟加密（會話
`+0x230`）時，它用 0xFE 填滿 16 位元組，把 NUL 填充的連線碼拷到其上，並用 `0x6e68d0` 就地加密：
遊戲金鑰下的 AES-128-GCM（會話 `+0x238`，經 `0x6fc8a4` 設定），無附加資料，標籤丟棄，IV 為
`key[1] key[8] key[7] key[2]`（`0x6fc4e4..0x6fc4fc`），這裡是 `1emf`：

    password  = KEYSTREAM XOR (the code's ASCII, NUL-padded to 16)
    KEYSTREAM = AES-128-GCM(key = p1frXqxmeCZWFv0X, iv = 1emf).encrypt(16 zero bytes)
              = e5ab19ed742b6d40885998bf968aa166

金鑰流是固定的。`pokeldn.pla` 裡有 `link_code_keystream`、`user_password`、`link_code` 和
`parse_advertise_data`。設定器是 Pia 的，所以這個區段裡的每個標題都這樣加密
（[無線層](ldn.md)）。

其主機在其執行期間重啟的遊戲主機，會在下一次搜尋時顯示錯誤 2318-0006；離開交換選單並重新
搜尋即可清除。

## 離開

遊戲主機退出時執行 `nn::pia::session::LeaveMeshJob`：它傳送會話型別 3 的離開請求，最多
傳送四次、每次等 500 ms 等型別 4 響應，然後離開網路。步驟：SendLeaveRequest `0x73b898`（寫入器
`0x737ee8`，截止在 `0x73b9a8`），WaitLeaveResponse `0x73bab8`（計數器 `[job+0x6c]`，超過 3 就在
`0x73bbf0` 放棄），CompleteProcess `0x73ba54`。

    03 | u32 random | location id (12) | address kind | IPv4 (4) | port big-endian (2)
    04 | u32 random | location id (12)                          the response, 17 bytes

隨機字每次都不同。型別 3 處理器 `0x738000` 用 `04`、一個新的隨機字和請求的第 5 到 16 位元組作答，
然後移除該站；型別 4 處理器 `0x738280` 只接受離開者自己的 id。

無人回答時，遊戲主機在四次請求（約 2 s）後離開；有回答時，一次後離開。`bin/pla_host.py` 回應
每個型別 3（`tests/test_pla_host_loss.py`，該回答在 unicorn 下經過 `0x738280`）。

退出、夥伴離開訊息和會話錯誤都會進入場景模式 9（`0x110b72c`）：它放置一條待處理的接收記錄，
啟動離開（`0x26be890`），取消任務，並至少等 3.0 s（`0x110b7d8`）等離開和任務，所以無論主機是否
回答，退出後約 3.7 s 野外就回來了。`Session::LeaveAsync` 唯一的呼叫者是遊戲的離開請求
`0x2ca0a10`；第一個型別 3 之前沒有 Pia 計時器（[pia.md](pia.md)，離開會話）。

一條收到的離開不會改變螢幕上的任何東西。當遊戲主機在盒子介面時：

| 主機 | 遊戲主機 |
|---|---|
| 網路斷開 | 一秒內出現“錯誤程式碼 2318-0006” |
| 網路線上但沉默（`--leave-sends 0`） | 約 13 s 時出現“你的交換夥伴選擇不再繼續交換”，然後正在通訊，然後 `DisconnectedByUser`，無錯誤碼 |

`--leave-after SECONDS` 向每個已加入的站傳送離開並結束執行；`--stay-after-leave` 保持網路線上但
沉默。`bin/pla_host.py --hold-after-trade N` 向每個站傳送同樣的離開，並在最後一次排隊的交換之後
N 秒結束執行。

## 未解決

- 場景解構函式與螢幕上的野外之間那 0.4 s 由什麼填充。
- 盒子程式碼的哪些流程呼叫 `0x26dcc74`（`0xc17ce0`，`0xc17e8c`）。
