---
title: Pia 層
parent: 無線層
nav_order: 1
---

# Pia 層

Pia 是任天堂的點對點會話中介軟體，在檢查過的每款作品中都用 UDP 埠 12345。每個資料包都以魔數
`32 AB 98 64` 開頭。Pia 版本決定頭部佈局：

| | 火紅/葉綠（GBA 應用） | 晶燦鑽石/明亮珍珠 | 劍/盾 |
|---|---|---|---|
| Pia 版本位元組 | 15/16（6.32+） | 9（5.27-5.45） | 4 |
| 頭大小 | 0x1D | 0x20 | 0x20 |
| 可變 id | 各 2 位元組 | 各 4 位元組 | 1 位元組 + 一個半字 |
| 線上的 GCM 標籤 | | 8，從 16 截斷 | 全部 16 |
| 模組 | `pokeldn/ldn/pia_connect.py` | `pokeldn/ldn/pia5.py` | `pokeldn/ldn/pia4.py` |

除非某節指名別的構建，`0x01...` 地址是 盾 1.3.2 解壓後的 `main`（按 `tools/switch/nso_read.py`
的佈局），而 `main.bin 0x01...` 地址是 BDSP 1.3.0 的。

## 資料包頭

### 版本 9（Pia 5.27-5.45）

來自 `nn::pia::common::Packet::Header`：

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

來自反序列化器 `0x01774730`（要求超過 0x1f 位元組）：

    0x00  4  magic 0x32AB9864, big-endian
    0x04  1  0x80 (encrypted) | version (0x7F) = 4
    0x05  1  connection id
    0x06  2  packet id, big-endian
    0x08  8  AES-GCM nonce, a monotonic counter
    0x10  16 AES-GCM tag, not truncated
    0x20     ciphertext

這兩個小欄位都按目標站點取值，對不特定發給某個站點的資料包為 0；零售 劍 在兩者中都發 0，這能
通過每條接收路徑。

- 連線 id：接收器（`0x017bdbd0`）會丟棄大於等於 2 且與它所持值不同的 id；0 與 1 通過。
- 資料包 id：接收器（`0x0185dd20`）把 0 當作無序號放行，並丟棄不高於該站點上一個序號的非零 id。

在頭部之下，版本 4 與版本 9 共用會話金鑰、IV 與分幀。

### 版本 11：接收器丟棄什麼（朱 4.0.0）

`0x6e9744` 在任何協議讀取之前就接受或丟棄整個資料包。設 `st` 為源地址處的站點，`V` 為接收器的
可變 id，`D` 為頭部目標，`S` 為源：

| 檢查 | 丟棄條件 |
|---|---|
| 傳送方 | `st` 被標記（`+0x78`）或處於狀態 3 |
| 目標 | `D >= 2` 且 `D != V` |
| 源 id | `S != 0` 指名不了任何站點、`D == V`、或 `D` 為 0 或 1 且帶尾部 |
| 資料包 id，`D == 1` | 不比 `st` 在其目標 1 計數器（`st+0x60`）上的上一個更新 |
| 資料包 id，其他 `D` | 不比 `st` 在其另一個計數器（`st+0x48`）上的上一個更新 |

資料包 id 0 總是通過且不存任何東西；否則要求 `(int16)(id - last) >= 1`，所以同 id 的重發會被
丟棄。源地址處沒有站點時（一次加入），不檢查資料包 id。零售傳送方用同一個計數器給目標 1 的
資料包編號，單播則用按接收方的計數器；兩者都跳過 0。

## 訊息分幀

一個 Pia 載荷攜帶一條或多條訊息，每條以一個存在位元組開頭，說明後面跟著哪些頭欄位。省略的欄位從
資料包中的上一條訊息繼承（`0x01853050`）。遍歷只在 `0xFF` 處停止，別的都不停：`0x00` 是合法的
單位元組頭，繼承所有欄位。

| 頭版本 | 讀取的作品 | 讀取者 | 下一條訊息開始於 |
|---|---|---|---|
| 4 | 劍 | `0x01852da0` | 四的倍數處 |
| 9（5.27-5.45） | 明亮珍珠 1.3.0 | `0x159b980` | 四的倍數處 |
| 11（6.16-6.30） | 傳說 阿爾宙斯 1.1.1 | `0x7484cc` | 載荷結束處 |
| 11 | 朱 4.0.0 | `0x6ed2d0` | 載荷結束處 |
| 16（6.39-7.2） | 傳說 Z-A | `0x256e088`；無 `0xFF` 終止，資料包頭宣告其填充 | 載荷結束處 |

站點會把一串大小相同的訊息捆在存在位元組 0x00 之後（朱 的零填充記錄分塊、明亮珍珠 的可靠訊息、
阿爾宙斯 的第二份 24 位元組記錄）。絕不要在 0x00 處停止遍歷。`tests/test_pia_bundled.py` 固定了
每款作品的一個數據包。

版本 3（Let's Go 1.0.2）沒有存在位元組：固定的 0x16 位元組頭，其第二個位元組必須為 1（`0x5ae7d0`），
遍歷在 `0xFF` 處停止。

版本 4 的頭是一個位元組加五個條件欄位：

    bit 0x01  +1  message flags
    bit 0x02  +2  payload size, big-endian
    bit 0x04  +4  protocol id and a 3-byte port
    bit 0x08  +8  destination
    bit 0x10  +8  the sender's station constant id

存在位元組 0x7F 給出 24 位元組（版本 9 為 16）；位 0x20/0x40 不增加任何東西。常量 id 是對傳送方 MAC
計算的 `station_protocol.ldn_constant_id`，此處為大端，而在 Local Protocol 主體中為小端。

版本 16（Z-A）的 flags、protocol（0x04）、port（0x08）各佔一個位元組，位 0x10 另有自己的位元組，
size 佔兩個；位 0x10 的位元組位於 protocol 與 port 之間（`0x256df54`）。0x590 及以上的大小會被
拒絕。`pokeldn.ldn.reliable.parse_messages` 讀取它。

在版本 4 與 9 中，每條訊息都填充到四的倍數；資料包尾部是 `0xFF`。`pia4.parse_packet()` 解析繼承，
`pia4.parse_messages()` 按傳送時的樣子返回每個頭。當消耗的位元組加上 `0xFF` 填充正好等於整個明文
時，一次遍歷才是正確的。

### 壓縮

一個載荷可以是一條 zlib 流，在訊息 flags 中標記：5.27-5.45 為 0x20，版本 4 為 0x10。版本 5 的
可靠頭有自己的 zlib 標誌 0x10，BDSP 在某些遊戲訊息上會置它（[BDSP 的協議](bdsp_protocol.md)）。
BDSP 會在會話中途開啟壓縮。zlib 流的前兩個位元組按大端半字讀，是 31 的倍數。

### 尾部

發給多臺主機的資料包帶一個尾部：每個接收方一個兩位元組的大端半字，即其可變 id 的低半部分，長度在
頭部位元組 0x0f。GCM 標籤不覆蓋它：密文是 `data[0x20 : len(data) - footer_size]`
（`pia5.ciphertext()`）。把尾部留在裡面會導致認證失敗，且沒有其他症狀。

## 會話金鑰

| 網路型別 | 類 | 派生方式 |
|---|---|---|
| LDN（本地無線） | `nn::pia::local::LocalProtocol` | 在遊戲金鑰下的 AES-128-ECB，作用於由會話值播種的 xorshift128 產生的 16 位元組 |
| LAN | `nn::pia::lan::LanProtocol` | HMAC-SHA256(遊戲金鑰, 一個 32 位元組引數，其最後一個位元組遞增) 的前 16 位元組（[LAN 模式](#lan-mode)） |
| NEX（網際網路） | `nn::pia::nex::*` | 來自匹配伺服器的會話金鑰 |

### 遊戲金鑰

    key = cryptoKeyDataSeed                     the game's own 16-byte constant
    key[1]  = (version >> 8) & 0xFF
    key[3]  = (version >> 4) & 0xFF             version = the local communication version,
    key[7]  = (version >> 1) & 0xFF                       which the advertisement carries
    key[12] = (version >> 0) & 0xFF

`ldn_game_key()` 計算它。劍/盾 的金鑰是一個 16 位元組的 ASCII 字面量，原樣使用，沒有種子也沒有
版本替換。

### LDN 會話金鑰

對 Pia 5.9-5.45：

    rnd = four SEAD draws, seeded with the session parameter from the advertisement (+0x0c),
          packed little-endian into 16 bytes
    session key = AES-128-ECB(game key).encrypt(rnd)

SEAD 以 `s[i] = (prev ^ (prev >> 30)) * 0x6C078965 + i` 播種，並執行移位為 11、8 與 19 的
xorshift128（`pokeldn/ldn/sead.py`；`pia5.ldn_session_key()`）。對 Pia 6.16+，會話金鑰是在遊戲
金鑰下對 SSID 做 AES（[無線層](ldn.md#hosting-for-an-emulator)）。

### AES-GCM IV

對 Pia 5.27-5.45 與版本 4（`ldn_nonce_crc()`、`gcm_iv()`）：

    IV[0..2]  = first three bytes of crc32( network id (little-endian) || source MAC address )
    IV[3]     = source variable id & 0xFF        from the packet header
    IV[4..11] = the packet's 8-byte header nonce

明文的 `0xFF` 填充是已知明文，可以在一個 AES 分組內檢驗候選金鑰。

## LAN 模式

LAN 模式在普通 IP 網路上用 UDP 承載 Pia：站點通過廣播找到會話，不使用無線，也不用 LDN。
`pokeldn/ldn/pia_lan.py` 實現 Pia 5.45 及更早的版本；下面每一條事實都是對著模擬的 盾 1.3.2
測得的（`tests/test_swsh_lan.py` 把它們固定在其位元組上）。

| 埠 | 承載 |
|---|---|
| 30000 | 瀏覽請求（廣播）與瀏覽應答（單播給請求方），不包在 Pia 中 |
| 49152-49155 | 一個站點的 Pia 資料包；一臺主機佔用第一個空閒的 |
| 40000 | 站點發往子網廣播地址的廣播可靠（0x80）訊息 |

朱 4.0.0（Pia 6）在 UDP 35000 上瀏覽，請求 317 位元組、應答 620 位元組，其站點埠是 49152
（[LAN 模式](sv.md#lan-mode)）。

### 哪些作品能進入 LAN 模式

每款寶可夢作品都連結 `nn::pia::lan`，並某個模式值之後構建其 LAN 網路工廠；只有當某段程式碼傳入
該值時，作品才能進入 LAN 模式。以下讀自各作品的 `main`：

| 作品 | LAN 模式值 | 其程式碼傳入的值 | 頁面 |
|---|---|---|---|
| 劍/盾 1.3.2 | 3 | 0、2、3（在選項中按 L + R + 左搖桿） | [LAN 模式](swsh_session.md#lan-mode) |
| Let's Go 1.0.2 | 2 | 0、1 | [LAN 模式](lgpe_session.md#lan-mode) |
| BDSP 1.3.0 | Pia 外掛的 LAN 設定 | 無；該 LAN 設定從未被註冊 | [LAN 模式](bdsp_session.md#lan-mode) |
| 傳說 阿爾宙斯 1.1.1 | 3 | 1、2 | [LAN 模式](pla.md#lan-mode) |
| 朱 4.0.0 | 3 | 1、2、3（實測：在 Combats en réseau 上按住 ZL + ZR；從交換選單永遠到不了） | [LAN 模式](sv.md#lan-mode) |
| 傳說 Z-A 2.0.2 | 3 | 1、2 | [LAN 模式](za.md#lan-mode) |

### 瀏覽請求與應答

瀏覽請求是 `00`、一個 u32 大小 `0x23A`、0x23A 位元組的搜尋條件以及 0x12A 位元組的加密質詢。應答是
`01`、一個 u32 大小 `0x511`、會話資訊以及 0x3A 位元組的質詢應答。

| 條件偏移 | 欄位 |
|---|---|
| 0x00 | 最少參與者，一對 (maximum, minimum) u16 |
| 0x04 | 最多參與者，同一對 |
| 0x08 | 僅已開放、僅空缺 |
| 0x0A | 結果偏移、結果大小（各為 u32） |
| 0x12 | 遊戲模式（u32） |
| 0x16 | 會話型別（u32） |
| 0x236 | 搜尋標誌：0x1 最少、0x2 最多、0x4 已開放、0x8 空缺、0x10 遊戲模式、0x20 會話型別 |

| 會話資訊偏移 | 欄位 |
|---|---|
| 0x00 | 遊戲模式、network id（各為 u32） |
| 0x08 | 六個 u32 屬性 |
| 0x20 | 參與者、最少、最多（各為 u16） |
| 0x26 | 系統通訊版本、應用程式通訊版本（各為 u8；劍 中為 7 與 7） |
| 0x28 | 會話型別（u16） |
| 0x2A | 384 位元組的應用程式資料，然後是其 u32 大小，位於 0x1AA |
| 0x1AE | 已開放 |
| 0x1AF | 主機地址：IPv4、12 個零位元組、u16 埠 |
| 0x1C1 | 主機常量 id（u64）、可變 id（u32）、服務可變 id（u32） |
| 0x1D1 | 十六個 50 位元組站點：角色（1 主機，2 玩家）、名字編碼（1 UTF-8）、40 位元組名字、u64 常量 id |
| 0x4F1 | 32 位元組的會話金鑰引數 |

站點的 id 來自其地址：常量 id 是 IPv4 地址接上埠（192.168.1.31:49153 對應
`c0a8011f0000c001`），服務可變 id 是地址的低半部分接上埠，network id 等於主機的服務可變 id。

### 質詢

    challenge  = version 2, enabled 1, u64 counter, 16-byte challenge key, 16-byte tag,
                 256 random bytes under AES-GCM(AES-ECB(game key, challenge key),
                                                 nonce = receiver's broadcast address || counter)
    reply      = HMAC-SHA256(game key, the 256 bytes)[:16]
                 under AES-GCM(HMAC-SHA256(game key, reply key || request key)[:16], the same nonce)
    key param  = the first answered reply's challenge key || its request's challenge key
    session key = HMAC-SHA256(game key, key param with its last byte plus one)[:16]

nonce 以接收方子網的廣播地址（`local | ~mask`）開頭。主機為每次應答抽一個新的 16 位元組質詢金鑰，
並用它和它所應答請求的質詢金鑰加密響應；key param 存在會話資訊的 0x4F1 處，保留它所應答的第一個
請求的那一對（劍 1.3.2 `0x0178b464`）。搜尋中的站點用應答的質詢金鑰和自己最新請求的質詢金鑰來
校驗應答，從不用 key param（`0x0178ab2c`），並丟棄校驗失敗的應答。主機只應答其會話滿足條件的
請求（`0x0178e590`）：遊戲模式、會話型別、兩個參與者範圍（0xFFFF 的邊界表示不限）、僅已開放與
僅空缺。

站點從瀏覽的應答中挑一個會話（`0x01778c80`）：條件匹配、已開放、不是加入已經失敗的會話、系統與
應用程式通訊版本相同，且能容納加入的站點。一個都沒有時，它建立自己的會話。

### 主持請求與 AES-GCM IV

瀏覽之後，加入方傳送一條主持請求，協議 0x44 型別 3：`03`、11 個零位元組、u32 network id。主機以
型別 4 應答：`04`、11 個零位元組、network id、其站點位置。隨後的站點握手與 LDN 上相同；沒有
Local Protocol（0x24）。零售 劍 的主持請求攜帶源常量 id 0；它的常量 id 是其地址接上其站點埠，
而主機發給任何其他 id 的連線請求都不會得到應答。

進入網格後，零售 劍 傳送一條會話請求，型別 5：`05`、11 個零位元組、network id。主機用會話訊息中
的會話資訊作答，型別 6：`06`、11 個零位元組、由各分片共享的一個 u32 值、一個 u16 序號、分片索引
與分片數（各為 u8）、一個 u32 分片大小，然後是最多 800 位元組的會話資訊。沒收到它的 劍 會在 5 s
後沉默並離開網格。

站點每兩秒傳送一條 keep-alive，型別 7（`07` 與 11 個零位元組），在會話之外以明文傳送；接收器
忽略它。

    IV[0..3]  = the sender's IPv4 address
    IV[4]     = the connection id from the packet header
    IV[5..11] = the last seven bytes of the header nonce

## 協議

來自 `GetProtocolId`（每個 `nn::pia` 協議物件上的 vfunc4）：

| id | 類 | 備註 |
|---|---|---|
| 0x14 | MeshStationProtocol | 連線握手；網格的每一次確認 |
| 0x18 | MeshProtocol | 加入、更新網格、主機遷移 |
| 0x1c | SyncClockProtocol | |
| 0x24 | LocalProtocol | 主機重播的更新會話 |
| 0x54 | BandwidthCheckProtocol | |
| 0x58 | RttProtocol | 往返計時 |
| 0x68 | UnreliableProtocol | |
| 0x77 | ClockProtocol | |
| 0x7c | ReliableProtocol | 可靠滑動視窗 |
| 0x80 | BroadcastReliableProtocol | |
| 0x84 | ReliableBroadcastProtocol | 與 0x80 不同的類 |
| 0x94 | SessionProtocol | |
| 0xa4 | MonitoringDataProtocol | |

BDSP 註冊九個：0x14 v2、0x18 v3、0x1c v0、0x24 v0、0x58 v3、0x68 v1、0x7c v3、0x94 v1、0xa4
v0，這把它的庫限定在 Pia 5.31-5.43。

### 加入網格

站點依次通過更新會話（0x24）、連線請求（0x14）與加入請求（0x18）加入；每一者每 500 ms 重傳
一次，直到被確認。

網格訊息在 0x14 上用八位元組的型別 5 確認來應答，即 `05 00 00 00` 加上大端的 ack id；ack id 是
該訊息的最後四個位元組（`mesh_protocol.ack_for()`）。主機在傳送加入響應之前先確認加入請求；接收器
確認每一份副本。

### 離開會話（Pia 6）

`Session::LeaveAsync` 執行 `LeaveSessionJob`，其 LeaveMesh 步驟在非主機上啟動 `LeaveMeshJob`
（在主機上啟動 `LeaveMeshWithHostMigrationJob`）。它的 SendLeaveRequest 步驟傳送 Session 型別 3
的離開請求，並等待主機的型別 4 響應 500 ms，最多傳送四次。第一個型別 3 之前的任何延遲都屬於
遊戲。

| | 傳說 阿爾宙斯 1.1.1 | GBA 應用（Pia 6.39） |
|---|---|---|
| `Session::LeaveAsync` | `0x72a6dc` | `0xb1060` |
| SendLeaveRequest | `0x73b898` | `0xcacf4` |

## Local Protocol（0x24）

主機大約每 100 ms 廣播一次更新會話（型別 0x11），直到每個站點都確認它：

    local message header  version 1, type 0x11, size 73
    sequence id
    network id            random, not the advertisement's network id
    host variable id      the packet header's source variable id
    host constant id
    allow participating
    node 0..7             address:port and a ranking byte each
    host migration state

Pia 訊息頭為大端，這些欄位為小端，其中的本地地址為大端。`pokeldn/ldn/local_protocol.py` 解析它
以及版本 4 的。

### 確認

確認（型別 0x21）為 20 位元組（`LocalAckMessage::Serialize`，`main.bin 0x016bc0f4`）：0 處為 `1`，
1 處為型別，2 處為載荷大小半字，六個零位元組，0x0C 處為序號，四個零位元組。它的分幀與更新會話相同：
存在位元組 `0x7F`、flags `0x11`、協議 36、埠 0、目標 0。客戶端廣播它；重播停止就是通過訊號。

主機按傳送方的地址與埠歸屬確認（`0x016aec94`）。客戶端的可變 id 會影響 IV，因此它在一次執行
中必須穩定且非零。

## Mesh Station Protocol（0x14）

位元組 0 是型別：1 連線請求，2 響應，3 與 4 斷開請求與響應，5 確認，6 與 7 中繼連線請求與響應
（分發器：版本 4 `0x017c5f50`，BDSP `0x0154e848`）。

### 版本 9 的連線請求

按順序檢查：

| 偏移 | 欄位 | 失敗時 |
|---|---|---|
| | 大小 15..949 | 丟棄 |
| 0x0 | 訊息型別、連線結果、平臺 id | 丟棄 |
| 0x3 | 目標常量 id，大端 u64，即主機自己的 | 沉默 |
| 0xB | 目標可變 id，大端 u32，即主機自己的 | 沉默 |
| 0xF | 協議數量，即主機自己的數量 | 沉默 |
| 0x10 | 相應數量的 (id, version) 對 | 版本偏低 → 結果 2，偏高 → 結果 3 |
| | 站點位置大小，大端 u16，0x20..0x40 | 丟棄 |
| | 站點位置 | 丟棄 |

協議 id 從不檢查。站點位置的地址大小位元組必須是 2、6 或 18；格式錯誤的位置會被讀成可變 id 0。

結果碼（`0x0154f5e8`）：

| 結果 | 含義 |
|---|---|
| 2 | 請求方的版本太低 |
| 3 | 太高 |
| 7 | 所有版本都匹配而第二階段拒絕了它，或該可變 id 已是主機某個站點的（站點離開時清除，或用一個新的 id） |

大小：確認 8 位元組，拒絕 15，斷開響應 1。

### 版本 4 的連線請求

處理器 `0x017c62a0`：

    [0]     message type            1
    [1]     nat flags
    [2]     platform id             must be 9
    [3]     0 or 1; 1 means the request also names a target variable id
    [4]     target constant id      big-endian u64, the console's own
    [0xC]   target variable id      big-endian u32, checked only when [3] is 1
    [0x10]  nat location / protocol count
    [0x11]  the sender's station location (deserializer `0x0185ee20`)

沒有協議列表。[3] = 1 時主機不應答。平臺錯誤會以 `02 02 09 00` 加 13 個零位元組作答（結果 2）；
之後的檢查都是沉默。

握手，[3] 清零：

    ->   the console's connection request
    <-   the joiner's connection response, result 0, carrying the console's constant and variable ids
    ->   a type-5 ack
    ->   its own connection response, ~600 bytes, carrying the joiner's ids and the player's name,
         repeated until acknowledged

傳送主機請求的型別 5 確認會停止其重傳（`--ack-request`）；沒有它也能接受響應。

### 連線響應要被讀取必須滿足什麼

型別 2 與 7 到達 `0x017c6e70`。結果不為 2 的響應會被靜默丟棄，除非：

| 欄位 | 要求 |
|---|---|
| `[5]` 大端 u64 | 接收器自己的常量 id |
| `[0xD]` 大端 u32 | 接收器自己的可變 id |
| 站點位置 | 能解析到一個它認識的站點 |
| `[0x37]`，僅結果 0 | 小於 5 |
| 站點狀態 | 為 4，在發出確認之後檢查；接受時為 5 |

主機在 `[0x37]` 檢查之後才確認響應：從未被確認的響應是在 id、位置或 `[0x37]` 上失敗。17 位元組的
響應會讓 `[0x37]` 落在其末尾之後的陳舊緩衝位元組裡；
`station4.build_connection_response(..., min_size=ACCEPTED_RESPONSE_SIZE)` 會填充到 0x38，並在
那裡寫入 1。這一層的接受並不會啟動其上的遊戲
（[到達遊戲層](swsh_session.md#reaching-the-game-layer)）。

主機自己的連線響應就是接受；它每 500 ms 帶著相同尾部計數器重傳請求就是拒絕；只有沉默則兩者
都不是。

## Mesh Protocol（0x18）

位元組 0 減一用於索引一張 129 項的表格（版本 4：`0x017c0c80`）；版本 4 缺少 BDSP 的 0x22
DUMMY_MESSAGE 與 0x23 DUMMY_ACK。

加入請求是六位元組：型別 1、站點索引 253（「還不在網格中」）、一個 ack id。Pia 會重傳它約十秒。

加入響應的頭是十六位元組。拒絕是 `[1] == 0`、`[2] == [3] == 0xFF`，原因在 [4]；否則 [1] 是站點數，
0xC 處是大端的更新計數器。站點條目：

| 版本 | 條目 | 佈局 |
|---|---|---|
| 5.31-5.45 | 68 位元組 | 64 位元組站點位置、站點索引、大端加入順序 |
| 4 | 64 位元組 | 索引在 0x3E，沒有加入順序，最多 32 個站點 |

版本 4 在未分片時遍歷 `stations` 條目，分片時遍歷 [6] 個條目放進槽 [7]；5.31-5.45 在兩種情況下
都取 [6]。`parse_join_response(version4=True)` 走這兩條路徑。

UPDATE_MESH（0x20）大約每秒一次，列出網格中有誰；BDSP 總是傳送 556 位元組，未用的座位為零，所以
要按 `entries` 位元組遍歷（`mesh_protocol.parse_update_mesh()`）。

### 主機遷移

0x18 埠 1 上的網格訊息在可靠頭之下到達。被指名為下一任主機的站點必須應答。

| 訊息 | 位元組 | 處理器要求 |
|---|---|---|
| MIGRATION_START (0x44) | `[0x44, 主機索引, 新主機索引]` | 大小 3，[1] 為網格的主機索引，[2] <= 0x1F 且不是主機索引（`0x017c1f00`） |
| MIGRATION_RESPONSE (0x48) | `[0x48, 自己的站點索引]` | 大小 2（`0x017c10ac`） |
| MIGRATION_FINISH (0x41) | `[0x41, 主機索引, flag & 1]` | 大小 3，[1] 為主機索引（`0x017c0fb0`） |

應答發往新主機，由它廣播 MIGRATION_FINISH。`pokeldn/ldn/mesh_protocol.py` 構建並解析這三者。

## RTT 協議（0x58）

主機從每個站點進入網格時開始計時。版本 9 的訊息是十三位元組：

    u8   kind        0 = request, 1 = response
    u64  timestamp   big-endian, the sender's own clock
    u32  target      big-endian, whose reply this is; zero is accepted by everyone

版本 4 讀取平鋪的十六位元組，並忽略十三位元組的應答；`rtt_protocol.response_for_v4()` 回顯請求，只
設定 kind。

站點以回顯時間戳的方式應答 kind 1。主機為每個站點保留一個九樣本的環形緩衝，其中位數即 RTT；
BDSP 的時間戳約以 31.36 MHz 執行。沉默的站點不會被丟棄，只是不再取樣。BDSP 在未應答時每 410 ms
請求一次，每個環形緩衝填滿後每 508 ms 一次（`0x015ace54`）；可靠重傳間隔跟隨 RTT。

## 可靠滑動視窗（0x7c）

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

0x20 及以上的 N 與 0x5a1 及以上的載荷會被拒絕。

應用程式資料標誌未置位時，載荷是一份批次確認：

    0x0  1   a bitfield, 0 in every captured ack
    0x1  1   entry count, refused at 0x21 or more
    0x2  21 * n  entries: u8 stream id, u16be ack id, u16be `ack id - 1`, 16-byte ack mask

一臺零售主機對序號 0 與 1 的確認：

    00 00 0017 ffff 0003 00   00 01   00 0002 0001  00 * 16

控制訊息的序號是 0xFFFF。`ack id` 是收到的最高序號加一。`reliable5.build_ack_message()` 逐位元組
復現它。序號 0 的資料訊息不會引來確認；序號 1 的會。

### 接收器靜默丟棄什麼

接收路徑（朱 4.0.0 `0x006f0330`，BDSP 1.3.0 `0x159fb98`）在以下情況丟棄一條訊息卻仍返回成功：

| 訊息被丟棄的條件 | 朱 | 仍傳送確認 |
|---|---|---|
| 視窗未初始化且 flags 缺少 `is initialized` | `0x6f037c` | 否 |
| 序號低於視窗基址 | `0x6f03cc` | 是 |
| 目標數非零且點陣圖中沒有接收器的位 | `0x6f0430` | 否 |
| 流 id 與初始化時鎖定的不同 | `0x6f0454` | 否 |
| 環形槽位已被佔用 | `0x6f0540` | 是 |

那兩個仍確認的情況會讓傳送方讀到一條針對應用從未收到的訊息的確認。超出視窗末尾的序號返回
`0x4c0d`，重組超過 `0x5a1` 位元組返回 `0x10407`，無法解壓的 zlib 載荷返回 `0x2c03`。

一條流上的第一條訊息把基址設為自己的序號。接收器還會把基址推進到傳送方的 `lowest pending`
（朱 `0x6eff24`）。傳送方宣告的 `lowest pending` 高於其下一個序號時，在 朱 與 BDSP 上都會讓
對端帶確認地丟棄那些訊息。確認在頭部與條目的第二個半字中攜帶傳送方自己最低的未確認序號。BDSP
在定時器上以及隨資料一起，向每個仍線上的對端傳送欠下的確認。

### 視窗發給誰（Pia 6）

`ReliableSlidingWindow` 的目標是按站點索引的站點指標，由 Pia 在站點加入與離開事件時填充，無需
遊戲程式碼（朱 4.0.0：註冊 `0x6ef588`）。一個站點只在其加入事件之前、離開之後、協議持有站點索引
0xfd 時，或註冊拒絕它時（索引已被佔用，或該站點已註冊）才不在列表中。批次確認的組裝器
`0x6f2138` 讀取同一張列表：確認中的某一位只表明視窗註冊了該站點，與發給它的訊息無關。

### 版本 4

一個頭類同時服務 0x7C 與 0x80（`ReliableSlidingWindow::MessageHeader`，反序列化
`0x0184e390`）：

    0x0  1  flags
    0x1  1  stream id
    0x2  2  payload size, big-endian    refused at 0x589 and above
    0x4  2  sequence id, big-endian
    0x6  2  lowest sequence id pending ack, big-endian
    0x8  1  destination count           refused at 0x20 and above
    0x9  8 * count  station constant ids, big-endian

兩個版本在 count 為 0 時一致，而雙方傳送的每條 0x7C 訊息都是如此。

接收路徑（`0x01859338`）會靜默拒絕：超過 `0x57F - 8 * count` 的載荷、長度不是
`9 + 8 * count + size` 的訊息、與該站點視窗不符的流 id、不含接收器的目標列表，以及缺少
FLAG_IS_INITIALIZED 的第一條訊息。Flags 的第 5 位是 RESET，第 6 位是 RESET_ACK，第 0 位是
APPLICATION_DATA；其餘情況都是確認。

一臺主機在第一條訊息上發 flags 0x0F，之後發 0x07。
`reliable4.build_data_message(bytes.fromhex("610000000a00"))` 復現一臺主機序號 1 的訊息：
`0f0000060001000100610000000a00`。

確認載荷正好是 0x260 位元組，32 個 19 位元組的條目：u8 流 id、u16be ack id、16 位元組掩碼（處理器
`0x01859a84`；其他大小都以 0x2c03 作答）。`reliable4.build_ack_payload` 用同一個條目填滿每個
槽位。盾 會讓未用的槽位留著陳舊位元組：只讀被確認流的那個條目，否則傳送方會沖垮主機的視窗，它
就不再確認。

序號不斷增長而 `lowest_pending` 固定，意味著積壓不斷增長。

一條太長而放不進單個載荷的訊息會拆到連續的序號上，第一條帶 flag 0x02，最後一條帶 0x04，每個
單獨壓縮的分片帶 0x10。盾 主機的一場對戰回合日誌（2074 到 2657 位元組）分成兩條：flags 0x03 加
1407 位元組未壓縮，然後 0x15 加其餘部分作為 zlib 流；整條訊息是第一個主體接上解壓後的第二個。在
模擬迴環上，11 條拆分訊息中有 3 條裡收尾分片比開頭分片先到：要按序號順序重組，絕不按到達順序。

## 協議 0x80，廣播可靠視窗

`nn::pia::transport::BroadcastReliableProtocol`。它的訊息經過壓縮（版本 4 的 flag 0x10）：可靠頭
帶目標數 1 與一個站點常量 id，壓著 0x260 的確認載荷，解壓後 625 位元組。確認每個站點索引一個槽位：
一臺主機填 0..7，把 8..31 留為零，8 即加入響應中的 `max_total`。

## 協議 0x81，流式廣播可靠傳輸（Pia 6）

`StreamBroadcastReliableProtocol` 把一個固定大小的塊，從一臺站點分塊搬到每個請求它的站點
（朱 4.0.0，更新 `0x6f5360`）。它與 0x7C 和 0x80 用同一個重傳期限，且在任一目標都沒有 RTT
樣本時從不重傳。

每條訊息攜帶一個十一位元組的 StreamData 頭（`0x6f60e8`）：

    +0  1  kind: 0 a receive posted, 1 the first chunk, 2 a later chunk, 3 to 6 control
    +1  1  transfer id
    +2  1  percent of the block delivered after this chunk
    +3  4  big-endian u32: the receive capacity in a kind 0, zero in a chunk
    +7  4  big-endian u32: the length of the data that follows
    +11    the data

一次登記接收會發送一條攜帶其容量的 kind 0；已登記容量中最小的那個限定了傳送 API 所接受的塊大小。
超過該大小、id 為 0xff、或沒有任何站點為該 id 登記接收時，傳送會被拒絕。分塊大小為
`[window+0x70] - 11` 位元組。

| kind | 接收器做什麼 |
|---|---|
| 0，登記接收 | 記下發送方的 id 與容量，或忙時以 kind 3 作答 |
| 1，第一個分塊 | 重置已收計數，然後同 kind 2 |
| 2，分塊 | 放得下就複製資料；收到 percent 100 時接收完成 |
| 3，忙碌的傳送方拒絕接收 | 重置該傳輸 |
| 4，傳送方取消 | 重置該傳輸 |
| 5，接收方取消 | 丟掉該接收方；傳送方以 kind 6 作答 |
| 6，傳送方確認取消 | 重置 |

控制用的 kind 攜帶 id 0xff。當每個目標的視窗都確認了最後一個分塊時，一次傳送完成。

## 協議 0x84，可靠廣播傳輸

`nn::pia::transport::ReliableBroadcastProtocol` 承載 劍/盾 的交換快照：

| kind | 含義 |
|---|---|
| 0x11 / 0x12 | 一個數據分片；[4] 處一個計數器，[10] 處一個容量 |
| 0x19 | 傳輸完成 |
| 0x21 | 一份確認，攜帶一段連續基址與一個「哪些提前到達」的位掩碼 |
| 0x28 | 對 0x19 的應答 |

從不作答的接收器永遠見不到後三個，傳送方會一直重傳。`pokeldn/ldn/broadcast4.py`。一臺主機在
埠 0 上傳送自己的傳輸，在埠 1 上確認對端的傳輸。

## 未解決

- LAN 主機對會話第一個請求的應答在遞增時，是把最後一個 key-parameter 位元組的 0xFF 保持在 0xFF，
  還是進位到它前面的位元組。

- 零售 劍 在 17 位元組連線響應的 `[0x37]` 處讀到的是什麼，而那裡是傳送方沒有寫的位元組。

- 是什麼寫入了版本 4 連線請求 [1] 處的 nat-flags 位元組；它在不同連線之間會變。

- 一次即時拒絕把哪個錯誤碼交給等待的上下文（`0x01769720`）。

## 致謝

頭部版本表、會話金鑰的派生方式與 nonce 佈局來自
[NintendoClients wiki](https://github.com/kinnay/NintendoClients/wiki/Pia-Protocol)
（[逆向一款 Switch 作品](switch_re.md)講了如何檢索它）。哪種派生屬於哪種網路型別、
`cryptoKeyDataSeed` 的值以及版本規則，都是從零售作品自身的程式碼裡讀出來的。
