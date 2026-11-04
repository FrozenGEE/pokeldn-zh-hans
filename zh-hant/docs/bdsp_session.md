---
title: 加入與 Pia 層
parent: 晶燦鑽石與明亮珍珠
nav_order: 1
---

# 加入 BDSP 會話，以及加密層下面是什麼

本頁講述一場晶燦鑽石或明亮珍珠的聯盟室會話，從 LDN 廣播一直到 Pia mesh：金鑰、Local Protocol、加入、
開設房間與離開。地址均為 1.3.0 的 `main`。

## 廣播

    local_communication_id  0100000011d90000
    scene_id                4352 (0x1100) Union Room; 5120 (0x1400) Union Room with a password;
                            12608 (0x3140) Grand Underground
    version                 4
    accept_policy           ALL, 1/8
    application_data        17 bytes: Pia's 16-byte LDN header (ldn.md), then one byte

通訊 id 是晶燦鑽石的 title id，明亮珍珠共用（`010018e011d92000`）。該廣播僅憑 `prod.keys` 就能解密
（`tools/ldn/ldn_scan.py`）。

普通房間中頭部 +0x04 處的 CRC32 欄位為 0。帶密碼的房間在該處放的是密碼 ASCII 數字的 CRC32，小端
（00000000 -> `0xC0088D03`），場景 id 為 5120。主機在掃描時按場景 id 過濾，跳過保護方式與自己不匹配的
房間，並在呼叫 `nn::ldn::Connect` 之前把輸入的密碼的 CRC 與 +0x04 比較（檢查點 `0x16b8890`，錯誤
0x6c51）。沒有任何訊息把加入方的 CRC 送到主持端：密碼錯誤時主持端什麼也收不到。超過八個字元的密碼，
前八個留給 Pia，其餘移入 `INL1` 之後的應用程式資料。`bin/bdsp_host.py --password 00000000` 開設帶密碼
的房間；`bin/bdsp_connect.py` 原樣加入這樣的房間。

## 口令

    WirelessStrongCryptoKey2021

原樣使用，27 位元組，既不補齊也不雜湊（LDN 接受 16 到 64 位元組並帶顯式長度），作為
`nn::ldn::SecurityConfig` 的口令；它從不參與 Pia 的加密。

## 入座

`bin/bdsp_join.py` 掃描、關聯並列印參與者表；IP 由主機分配。聯盟室的八個席位就是 LDN 的
`max_participants`。LDN 的席位在螢幕上什麼也不顯示。

- `Connect failed with status code 1` 表示關聯失敗；用 ESP32 板子時大約每兩次嘗試就有一次失敗。
  先重試，再談診斷。
- 重新進入房間會開一個新網路（新的通道、SSID 與會話引數）。
- LDN 介面上的接收端必須過濾掉自己的源 IP：廣播會迴環。
- 未經認證的 Pia 會被靜默丟棄，席位不受影響。

### 隨機匹配

獨佔自己聯盟室會話的主機會把它關掉並重新匹配，螢幕上毫無變化，直到它獨自待夠足夠長的時間。
`INL1.IlcaNetSession$$GameState_GameFrontBefore_LocalRandom` [0x02740640] 在每次會話更新時執行，
30 幀每秒下每渲染幀一次。只有一個站點時，它在 `25 + (0x7F & r)` 次更新之後關閉會話（0.83 到 5.07 s，
`r` 每次嘗試隨機），直到累計獨處 270 次更新（9.0 s），此後就保留自己的網路。這些常數來自
`IlcaNetSessionSetting` 的建構函式 [0x01f46fc0]。更新鏈：`Sequencer$$SubscribeUpdate` 呼叫
[0x0202da38] -> `_orderableList` [0x01a8fed0] -> `Sequencer$$Update` [0x01a906d8..0x01a9071c] ->
`NetworkManager$$OnUpdate` [0x02253190] -> `IlcaNetSession$$Update` [0x02030a38]；`targetFrameRate`
為 30 [0x01a8ed68]，唯一的畫質檔（`Ultra`）`vSyncCount` 為 2（60 Hz 下 30 fps）。

## 空口上有什麼

在有站點確認之前，主持中的主機會每 100 ms 把它的更新會話廣播到 `169.254.x.255:12345`，
`dst_var = 0`，176 位元組：

    32ab9864 89 00000000 11bac90d 0000 00 f5a83bd383ce712d 59baa5cbc320cb56 <144 bytes>
    magic    v  dst=0    src      pid  f  nonce (a counter) tag              ciphertext

版本 9，已加密：Pia 5.31-5.43。頭部與傳輸協議見 [Pia 層](pia.md)；`pokeldn/ldn/pia5.py` 能對抓到的
資料包做逐位元組一致的往返。

## 金鑰層級

    cryptoKeyDataSeed  9918bd0fdcfa65779918bd0fdcfa6577    from global-metadata.dat
    game key           9900bd0cdcfa65639918bd0fc7fa6577    = seed derived with version 199
    session param      0x36dee059                          advertisement +0x0c, little-endian
    session key        7b182cb087eeabd228a2efd91a8be147    = AES-ECB(game key) over 16 SEAD bytes
    network id         b4c85cf8                            advertisement +0x00, little-endian
    source MAC         48:f1:eb:20:9b:22
    crc32(netid||MAC)  0xda291352
    IV (first packet)  da29130df5a83bd383ce712d

### 種子的位置

`INL1.IlcaNetSessionSetting` 的建構函式從 `global-metadata.dat` 裡的一段欄位預設值二進位制塊填充
`cryptoKeyDataSeed`（`<PrivateImplementationDetails>.33F804682DF9E210AABDC4D939CBCD380EC7517F`）；
該方法見[逆向分析一款 Switch 遊戲](switch_re.md)。

### 公開的金鑰是派生後的種子

遊戲用本地通訊版本覆蓋種子的第 1、3、7、12 位元組，1.3.0 為 199（即廣播的 `app_version`）；
`ldn_game_key(seed, 199)` 給出遊戲金鑰。

### 會話金鑰

    seed  = the session parameter (LocalProtocol+0x5b0)
    state = for i in 1..4:  prev = ((prev ^ (prev >> 30)) * 0x6C078965 + i)
    rnd   = four xorshift128 draws (shifts 11, 8, 19) -> 16 bytes, little-endian
    key   = AES-128-ECB(game key).encrypt(rnd)

`pokeldn/ldn/sead.py` 實現了 SEAD 的 RNG。

### GCM 的 nonce

由 `nn::pia::local::LdnOutputStream::vfunc3` `0x16b39c4` 構造：

    IV[0..3]  = u32be( crc32(network id LE || source MAC) )
    IV[3]     = overwritten with (packet.source_variable_id & 0xFF)
    IV[4..11] = the eight-byte header nonce

CRC 就是普通 CRC32。源 MAC 來自站點記錄；資料包本身並不攜帶它。

## 解碼後的 Local Protocol

更新會話（Local Protocol 0x24，型別 0x11）每 100 ms 重播一次，直到每個站點都確認它：

    local message header  version 1, type 0x11, size 73
    sequence id           4
    network id            8b4a3b22        random, unrelated to the advertisement's
    host variable id      11bac90d        the packet header's source variable id
    host constant id      0000 48f1 2022 9beb
    allow participating   1
    node 0..7             nine bytes each (ip, port, ranking); empty slots 0xff
    host migration state  0

主持常數 id 按小端讀出後，按 LDN 的規則解包成主持端的 MAC：
`mac[2] << 56 | mac[4] << 48 | mac[5] << 40 | mac[3] << 32 | mac[1] << 24 | mac[0] << 16`。
Pia 訊息頭是大端，Local Protocol 的欄位是小端，其中的地址又是大端。

### 確認

20 位元組的確認包見 [Pia 層](pia.md#the-local-protocol-0x24)，以廣播發出，`dst_var` 為 0，目的地址為 0。
第一個確認就止住更新。

## 加入 mesh

握手見 [Pia 層](pia.md#joining-a-mesh)。BDSP 的地址：

| 內容 | 位置 |
|---|---|
| 站點協議的接收分發器 | `0x0154e848`，表 `0x3e6b38f` |
| 連線請求的反序列化 | `0x0154ebd0` |
| 內部錯誤到結果的對映 | `0x0154f5e8` |
| 按 id 查協議版本 | `0x0159b850`，未註冊的 id 返回 0 |
| 讀取 mesh 訊息的 ack id | `0x01542db8`（`size - 4`，大端） |
| 傳送確認（8 位元組，走 0x14） | `0x01550324`，MeshStationProtocol 位於 `session + 0xa0` |
| 加入 REQUEST 處理函式，主持端一側 | `0x0154b790`、`0x0154b868` |
| 加入 RESPONSE 處理函式 | `0x0154b984`、`0x0154b9a4`；指標存於 `MeshProtocol + 0x128`（`0x0154e5c4`） |

主機註冊九個協議（[實測](#measurement-methods)）：

    0x14 Station v2   0x18 Mesh v3      0x1c SyncClock v0
    0x24 Local v0     0x58 RTT v3       0x68 Unreliable v1
    0x7c Reliable v3  0x94 Session v1   0xa4 MonitoringData v0

加入響應列出兩個站點，主持索引 0，加入方索引 1，`max_active` 為 8。結果 7 表示該可變 id 已經是它的
某個站點。會話協議（0x94）在 LDN 上不起作用：它的處理函式（分發器 `0x15820b8`，跳轉表 `0x3e6b986`）
因為 session+0x70 為空而直接返回：`LdnNetworkFactory` 的 61 號槽位 [`0x16b30ac`] 不建立聯合會話作業。
該作業在 `0x157c66c` 處建立（當 GOT `0x4c4b850` 之後的 +0x38 被置位時跳過），存於 session+0xC8，
每個站點一個 `ReliableSlidingWindow` [`0x1581938`；建構函式 `0x159dab4`；
`0x159de54(window, 2, 2, 0x94000001)`；接收槽位 10 `0x1581c98`]。合法的可靠 0x94 會被確認，然後丟棄。

## 開設房間

進入聯盟室的主機會先加入任何有空位的房間，然後才開設自己的房間。`bin/bdsp_host.py`
（`pokeldn/bdsp/host.py`）以場景 id 0x1100、`app_version` 199 以及全新的 network id 和會話引數開設一個
房間。它傳送的內容，每一項都按零售主持端逐位元組重建（`tests/test_bdsp_host.py`）：

| 步驟 | 訊息 | 分幀 |
|---|---|---|
| 有站點關聯 | 每 100 ms 一次更新會話直到被確認，加入方作為節點 1 | 廣播，`dst_var` 0 |
| 它的連線請求 | 一個已接受的連線響應，949 位元組 | `dst_var` 0，flags 0x01 |
| 它的 mesh 加入請求 | 站點確認，然後加入響應 | `dst_var` 0 |
| 加入響應被確認 | `NetJoinData`，可靠序列 1 | `dst_var` 為加入方的 |
| 此後 | 每秒一次更新 mesh、RTT 請求、0x68 上的 `NetCharacterStateData{0, 0}` | `dst_var` 1 |

主持端必須用請求裡的 tick 和以毫秒計的 mesh 時鐘來回應加入方的 Sync Clock（0x1C）請求。沒人應答的
加入方會在約十秒後掉認證並重新關聯，螢幕上顯示「communication en cours」。一旦應答，房間就是對稱的，
[交換](bdsp_trade.md)照原樣跑。

## 離開

兩種離開都從 mesh 的可靠視窗開始（0x18 埠 1，序列 1），並等待一個在埠 0 上不可靠發出的應答，
零售 Pia 會把它發兩次。mesh 分發器 `0x0154ac94`。

| 主機 | 傳送 | 應收 |
|---|---|---|
| 加入方 | `04 <own index>`，然後在 0x14 上傳送站點斷開 `03` | `08 <host index>`，然後 `04` |
| 主持端 | 向每個站點發 `44 <host index> <new host index>` | 從每個站點收 `48 <station index>` |

應答之後，加入方在 0.2 s 內掉認證，主持端在 0.5 s 內關閉它的網路。沒人應答時，加入方重試約 5 s 後
在約 9 s 離開；主持端會跑約 25 s 的遷移，尾聲是每 0.3 s 一次 Local Protocol 0x13，最長 10 s
（`LocalDestroyNetworkJob::WaitUntilAllClientsDisconnection` `0x016b95b8`），只要有站點離開就立刻結束。
它的步驟：301 ms 後重發（`job+0x68`）；取消位元組送到 `WaitForCancel` `0x016b9330`；只剩一個站點
（計數 `0x016b014c`，判斷 `0x016b9614`）或距
`WaitUntilAllClientsReceiveUpdateSessionMessage` `0x016b936c`（`job+0x70`，判斷 `0x016b9644`）已滿
10000 ms，就走到 `StartDestroyNetwork` `0x016b950c`；上一個狀態在 `[[protocol+0x4f0]+0x5c]`
（`0x016b0888`）或 10001 ms 後結束。離開相關的處理函式：主持端的離開請求 `0x0154b9e0`（經
`0x0154c860` 應答）、加入方的響應 `0x0154baf8`、遷移響應 `0x0154b068`；`WaitLeaveResponse`
`0x0155fd2c`、`WaitMigrationResponse` `0x015607bc`。

`pokeldn.bdsp.session.answer_departure` 構造這兩個應答；`bin/bdsp_host.py` 應答離開的加入方，
`bin/bdsp_connect.py` 應答遷移的開始並在 0x13 上離開網路（`--no-leave-on-host-migration` 則不然）。
兩個啟動器也像主機那樣離開：`--hold` 結束或收到訊號時，`bin/bdsp_connect.py` 傳送離開請求和站點斷開；
`--seconds` 結束或按下 Ctrl-C 時，`bin/bdsp_host.py` 傳送 `44 00 01`（`HostSession.close`），然後在收到
`48` 或 5 s 之後停止。`--hold-after-trade N` 在最後一次排隊的交換之後 N 秒走同一條路徑，且不早於其後
的 30 s——那時玩家重新獲得操作權（[完成的交換](bdsp_trade.md#the-completed-trade)）。離開交換盒不發
離開訊息，只在一個包裡發 `NetDataCurrentFlowCancelData{0}`（0x25）和 `NetCharacterStateData{0}`。

## LAN 模式

BDSP 1.3.0 從不啟用 LAN 模式。它的 Pia 來自任天堂的 Unity 外掛，該外掛的框架初始化（約在
`0x16886d0`）會為 LAN 模式構建 Lan 工廠（建構函式 `0x169fdcc`），而這需要一個已註冊的 LAN 設定。
`INL1.IlcaNetBase.PlatformInitialize` 註冊網際網路設定（`0x1e13800`），`PlatformInitialize2` 註冊本地設定
（`0x1e139dc`）；沒有任何東西呼叫 `PiaPlugin.RegisterInitializeLanSetting`（`0x227caf0`）或它的 native
版本 `0x227cac0`。`global-metadata.dat` 裡沒有任何 C# 名字提到 LAN。

## 測量方法

- 只有當協議數量與自己的相符時，主機才會回應連線請求；掃一遍這個數量就得到 9。未註冊的協議期望
  版本 0，所以二分版本號就能讀到任意協議的版本。
- 判據必須是一個回覆；沉默同樣可能只是丟包。可靠視窗會確認它接受的資料，所以先發資料，只掃序列 id。
