---
title: 卡帶與會話
parent: 劍與盾
nav_order: 1
---

# 卡帶、金鑰，以及坐下入座

`main` 靜態連結了整套 Pia（252 個 `nn::pia` 類、2036 個虛方法）並匯入 `nn::ldn`。Pia 之上游戲用 protocol buffers：`main` 為 78 組 P2P 訊息各帶一個 `FileDescriptorProto`（`gflnet.p2p.framework.pb`、`.block.pb`、`.sync.pb`，每個內容一個包：交換、對戰、露營、團體戰）。

## LDN 通行短語

    W3GoSMEn7RIIUQ89rzqBHGhGferRNb7K18ZBq2aNuj8Us9RO9Q9JYyGOZlLy8MYL

64 位元組，原始形式（兩份，在 `0x203ff04` 與 `0x203ff45`）；與 NintendoClients wiki 上朱/紫那一行相同，與傳說 阿爾宙斯只差一個字元（這裡是 `HGhG`，那裡是 `HGHG`）。設定呼叫在 `0x006c3ec8`，長度為 `0x40`。`nn::pia::local::LdnCreateNetworkJob` 把通行短語存在 +0xC4，長度存在 +0x104，本地通訊 id 存在 +0xB8；它在呼叫 `nn::ldn::CreateNetwork`（`0x017972bc`）之前把通行短語複製到 `SecurityConfig+4`。`LdnBackgroundProcessJob` 要求長度在 16..64 之間。

## Pia 遊戲金鑰

    p1frXqxmeCZWFv0X

十六個 ASCII 位元組在 `0x01c3dc87`，被三處呼叫原樣使用（就是 wiki 上劍/盾那一行）；建立/加入的呼叫是 `0x183fd10`，來自 `0x006ca914..0x006ca93c`。

## 讀取卡帶

    ./.venv/bin/python tools/switch/xci_read.py <the.xci> --keys prod.keys --type Program
    ./.venv/bin/python tools/switch/xci_read.py <the.xci> --nca 87e41bc8 --exefs 0 --extract main
    ./.venv/bin/python tools/switch/nso_read.py main
    ./.venv/bin/python tools/switch/rtti_names.py main.bin 0x1900fc0 --rodata 0x1901000:0x24da168

`main` 的 text 是 0..0x1900fc0，rodata 到 0x24da168，data 到 0x2635f38。方法見[逆向分析一款 Switch 遊戲](switch_re.md)。

`/bin/message/<Language>/common/*.dat` 用的是第六/七/八世代的訊息容器：第 *n* 行的鍵從 `0x7C89 + n * 0x2983` 開始，每個字元左旋 3 位（每行都以 `0x0000` 結尾）。`.tbl` 是一個 `AHTB` 索引，第 *i* 條就是第 *i* 行。

## Pia 4

Pia 頭裡寫的是版本 4，形狀與[Pia 層](pia.md)上那兩個帶都不同；它下面是 5.27 的 LDN 家族（同樣的金鑰、IV、封幀，只多一個欄位）。`pokeldn/ldn/pia4.py` 實現了它。`pokeldn.swsh.session_keys` 是 BDSP 的推導，但不做版本替換：

    會話金鑰 = ldn_session_key(GAME_KEY, application_data[12:16] 小端)
    IV       = crc32(application_data[0:4] || 傳送方 MAC)[0:3] || 源 id || nonce
    tag      = 十六位元組，完整校驗

484 個正版包全部通過認證，每個的源 id 都是 0。還有一條路徑 `0x0179bff0` -> `0x01774f40`，用會話的兩個 64 位值給 AES-GCM 播種；本地交換隻需要那條廣播就夠了。

## 入座

    POKELDN_RADIO=esp32:auto ./.venv/bin/python bin/swsh_join.py --keys PROD_KEYS --scan-only

會掃描一個主持中的介面，並把每條廣播寫進 `scratchpad/swsh_net_facts.json`。

| 介面 | 本地通訊 id | 版本 | 場景 | 應用版本 |
|---|---|---|---|---|
| 連線交換 | `0x0100ABF008968000`（劍的） | 4 | 60001 | 7 |
| 神秘禮物本地無線 | 同上 | 4 | 65535 | |

盾用的是劍的 id；它的 `control.nacp` 列出 `LocalCommunicationId[0] = 0x0100ABF008968000`、`[1..7] = 0x01008DB008C2C000`。

那 384 位元組應用資料：

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

`Connect failed with status code 1` 表示關聯被拒；在同一次搜尋中再試一次通常就能關聯上。一臺正在搜尋的劍會在同一個 comm id 下廣播兩個網路：一個是 Y-Comm 信標，場景 65535；過了第二條訊息之後，再加一個匹配網路，場景 60001。停在信標上的主機 16 次加入裡 0 次進到交換盒；`bin/swsh_connect.py` 只加入場景 60001，並一直重掃到它出現為止。關聯之後，主機會向 `169.254.x.255:12345` 廣播 Pia（每秒大約十個包）。加入的站點離開後是什麼讓一臺主機的廣播停下來，目前還沒讀出來。

## 一臺搜尋中的劍如何找到夥伴

在 Y-Comm 畫面上，每臺主機都在場景 65535 主持一個信標網路，並且大約每秒瀏覽一次（`0x006c3630`：主持走 `0x006c3840`，瀏覽走 `0x006c3770`，條件是來自 `0x006c4550`、`0x0183fac0` 的，只看 comm id 和網路型別）。通過 CRC 與版本閘門（`0x006c1be0`）的記錄會進入附近玩家登錄檔（`0x0110f270`），這個登錄檔會丟掉自己的記錄（廣播 0x1F 處的裝置 id 與 0x2F 處的賬號 uid，`0x0111b160`），也會丟掉任何缺網路 id 與場景對的記錄（`0x0110f2d4`）。這裡什麼都不加入。

走到連線交換、再走到普通交換，會顯示兩條訊息，每條都等按 A。第二條之後，`0x00fba940` 呼叫 `SetMode(comm, 2)`（`0x01096d10`）；`0x01095f10` 依次走狀態 0、5、3、4、6，狀態 6 用場景 60001 呼叫 `StartRandomMatching`（`0x010fcff0`）（`0x01096730`）。一臺上機後停在第一條訊息上的主機永遠不會呼叫 `SetMode(comm, 2)`，也就永遠不會匹配。

匹配層按下面的條件加入網路（`0x006c9e70`、`0x006cb8e0`，加入是 `0x006ca1c0`）：

    場景 60001，與自己的相同
    節點數 1，低於它自己的上限 2；網路型別 2；節點數上限 8 或更少
    廣播 0x04 為零：不帶連線密碼的搜尋會拒絕帶密碼的
    廣播 0x00 處的 u32 大於搜尋方自己的
    advertise 0x00 不在本次搜尋中曾加入失敗的 id 之列（0x80 條）

連線密碼只改變 0x04。`bin/swsh_connect.py`（不帶密碼）能加入帶密碼的主機並完成交換；`bin/swsh_host.py --code 12345678` 會被帶密碼的搜尋加入，不帶密碼則永遠不會。id 大的主持，所以兩臺都在搜尋的主機只會單向配對；主持端廣播的 id 接近 0xFFFFFFFF。

## 主機先說什麼

Pia 本地協議 0x24，與 BDSP 相同（`pokeldn.ldn.local_protocol`）：版本 1、型別 0x11、0x30 個固定位元組、八個九位元組的座位、一個主機遷移位元組。`allow_participating` 為真，所以主機在對方開口說 Pia 之前就把它登記進表：0 號站點是 `169.254.14.1:12345` 處的主機，1 號站點是 `169.254.14.2:12345` 處的座位。

主持端會反覆發更新會話直到每個站點都確認（0x21）。只有帶著對應序列號的確認才會讓重播停下（在 13 毫秒內）。頭位元組 0x05 和 IV 的源 id 都是 0。

## Pia 會話物件

`[[0x02616a30]]`（也就是 `[0x02630f40]`），交換程式碼從中讀站點 id 的地方，就是 Pia 的會話物件：0x270 位元組，沒有 vtable，由 `0x0183ddb0` 從 `0x006a8644` 一次性分配。在 LDN 上網路工廠是 `LdnNetworkFactory`，它的第 73 個槽（`0x01791080`）構造一個 0x7220 位元組的 `LdnMatchmakeSession`。

| 欄位 | 誰寫 | 值 |
|---|---|---|
| `+0xf0` | `0x018418a0`（`0x01841918`） | 本機自己的站點 id |
| `+0xf8` | `0x018418a0`（`0x01841990`） | mesh 主機索引處的站點 id（`[[0x0262f7b0]]+0xab`）；`[obj+0xd4] == 4` 時跳過 |
| `+0xf8` | `MeshEventListener` 槽 2（`0x01843580`），事件 1 | 後端第 30 槽，在主機離開時 |
| `+0xf8` | 事件 2 | 來自 `0x017d6080` 的 id（模式 2），或後端第 30 槽（僅模式 4） |
| `+0xf8`、`+0x100` | 事件 3 | 零，當 `[obj+0xd4] != 3` |

`0x018418a0` 在建立（`0x018394d8`）與加入（`0x0183d9b0`）時執行。`+0xd4` 的模式在普通 LDN 建立與加入時是 2；只有 `LanMatchJointSessionJob` 與 `NexMatchJointSessionJob`（`0x01839cc0`、`0x0183a040`）裡才是 3 或 4，`w8 - 6 < 3` 時是 4（`0x0183a2b8`）。

事件 1 寫第 30 槽要求離開的 id 等於 `+0xf8` 且不等於 `+0x100`、`0x01840b90(obj)` 為真（本地 mesh 控制器的 `+0x281` 與 `+0x234`，建立時都會置上）、`+0xd8 == 1`、`[mesh+0x64] == 0`，並且 `0x0184a4b0` 給出一個非零、且與 `obj+0x180+4*[obj+0x162]` 處的字不同的字。事件 2 只有在 `[obj+0xd8] - 2` 至少為 6 且 `0x01841350`、`0x01769ec0([obj+0x38])` 都為假時，才會寫到主機 id 的存處。

`LdnMatchmakeSession` 第 30 槽（`0x017a23d0`）在 `[this+0x18]` 為空時返回 `0xff`，否則返回 `0x017672d0` 處理 `[[this+0x18]+0x18]+0x2c0+8` 處那 16 位元組地址的結果：全零時為 0，後十二位元組為零時取前四位元組，其餘情況報錯 `0x10c07`。第 28 槽（`0x017a23b0`）是 `0x018407f0` 所呼叫的那個。

`0x018407f0` 在 `+0xf0` 非零、等於 `+0xf8`、且後端第 28 槽也同意時為真：也就是在這臺主機正在主持 Pia 的 mesh 時。主持一場交換的主機靠命令逐級爬確認階梯；而加入了 pokeldn 主持端的那臺，跟隨的是共享值（見[泵](swsh_trade.md#the-pump)）。

## 夠到遊戲層

遊戲層之下的每一層都是雙向的（見[Pia 層](pia.md)）：本地協議 0x24、站點握手 0x14、mesh 加入 0x18、RTT 0x58、可靠視窗 0x7C 與 0x80。

加入方對 0x14 連線的回應必須是劍所發的那種 840 位元組形式（`host4.build_host_response`：賬號 id 在 0x11、玩家名在 0x88、尾巴在 0xB1、token 在 0xBC）；`bin/swsh_connect.py --respond` 會發它。一臺模擬的盾 1.3.2 主持端在 56 位元組回應之後就不再發任何遊戲訊息。正版劍在 17 位元組回應之後就能完成交換（見[Pia 層](pia.md#what-a-connection-response-must-satisfy-to-be-read)）。

不管它的話，主機會反覆發 `61 00 00 00 0a 00`，也就是 ping（每秒約四次）；0x80 每秒要一次 ack id 1，0x7C 則保持沉默。`bin/swsh_connect.py --send-data HEX --send-protocol 0x7c` 用來發應用資料（`reliable4.build_data_message`；有五道靜默接收檢查，見[版本 4](pia.md#version-4)）。通過的訊號是：0x80 的 ack id 不再是 1，或者 0x7C 有了任何回應。

## ping 握手

一段負載是四位元組小端訊息 id 加 protobuf 訊息體。一次握手會帶上這五條訊息（`gflnet.p2p.sync.ping.pb`、`gflnet.p2p.block.pb`）：

    0x7C  61000000 0a00      97 SyncPingDataHolder, field 1 ping {}
    0x7C  61000000 1200      97, field 2 pingReply {}
    0x7C  61000000 1a00      97, field 3 pingSynced {}
    0x7C  60ea0000 0a00      60000 BlockDataHolder, field 1 result {}  (Result { bool isBlocking })
    0x80  60ea0000 12020801  60000, field 2 imReady { isReady: true }

應答要走過遊戲的五步：

    1  answer the ping continuously   --send-data 610000000a00 --send-mirror --send-count N
    2  ack every reliable window      0x7C, 0x18 port 1, 0x80; one unacked window kills the mesh
    3  answer `result{}` on 0x7C      the mirror is per protocol
    4  answer imReady on 0x80         --send2-data 60ea000012020801
    5  the console sends its party on 0x84

- 一次 ping 應答只換來一條 `pingReply`，之後遊戲就回去繼續 ping。
- 在主機索要之前就發 `pingReply`，會讓它的心跳停下來。
- 在 0x7C 上發 `imReady` 換不來 0x84；它要走 0x80。
- 遲到確認的訊息會被重發，並可能出現在它的後繼之後。只有比當前最新的序列號更大的才會替換當前訊息。

`bin/swsh_connect.py --sync-answers` 對 `trade.SYNC_ANSWERS` 裡有規則的按規則回，其餘按協議回顯，並列印每一條無規則的負載。

## 離開

一臺劍離開交換會話時會發盒子命令 3，約 0.77 秒後為它的角色發起 Pia 離開。每一步都等待回應，等不到就按超時落到下一步。

一臺作為加入方的劍離開主持端：

| 步驟 | 劍發什麼 | 主持端該回什麼 | 無人應答時 |
|---|---|---|---|
| mesh 離開 | LEAVE_REQUEST `04 <自己索引>`，0x18 埠 1，可靠，發一次 | LEAVE_RESPONSE `08 <主機索引>` | 5.0 秒 |
| 站點斷開 | 0x14 上的 `03`，每 0.5 秒一次 | `04` | 8 次請求，3.6 秒 |
| LDN | 離開網路 | | |

兩者都無人應答時，劍在 LEAVE_REQUEST 之後 9.0 到 9.1 秒離開 LDN 網路；都被應答時是 0.14 秒。版本 4 的主機處理函式 `0x017c19a0` 會通過 `0x017c2450` 發出 `08` 和自己的索引（不可靠地發兩遍）並丟掉該站點；0x14 的處理函式 `0x017c6110` 向傳送者回 `04`。`pokeldn/ldn/host4.py` 兩者都回。

一臺作為主持方的劍離開它的客戶端（它是 LDN 接入點）：

| 步驟 | 劍發什麼 | 客戶端該回什麼 | 無人應答時 |
|---|---|---|---|
| mesh 遷移 | MIGRATION_START `44 00 01`（見[主機遷移](swsh_trade.md#host-migration)） | MIGRATION_FINISH，以及一條把客戶端自己指為主機的 UPDATE_MESH | 5.0 秒 |
| 本地會話 | 它的更新會話（0x24 型別 0x11，主機遷移位元組 1，新的序列號），約每 0.11 秒一次 | 針對該序列號的 0x21 確認 | 10.0 秒 |
| 銷燬網路 | START_HOST_MIGRATION `01 13 00..`（16 位元組），每 0.33 秒一次 | 離開 LDN 網路 | 10.0 秒 |

給了 MIGRATION_FINISH、以客戶端為主機的 UPDATE_MESH、確認和離開之後，正版劍的最後一個包在 MIGRATION_START 之後 0.17 秒到達；什麼都不回，它就會發滿 25.0 秒。

- `LocalDestroyNetworkJob::WaitUntilAllClientsDisconnection`（`0x017acd70`）在只剩主持端一個或過了 `0x2710` 毫秒時銷燬網路，期間每 `0x12d` 毫秒重發一次 START_HOST_MIGRATION（`0x017acbd0`、`0x017a8bb0`）。
- 一次確認（處理函式 `0x017a9250`，本地型別 0x21）只有在序列號與該訊息相同時才清掉髮送者的位（`0x017aed10`）。是什麼把 10.0 秒的本地會話這一步限住的，還沒讀出來。
- START_HOST_MIGRATION 不帶序列號（`0x017abc60` 在 0xC 處寫 0），也沒有任何東西確認它。

`bin/swsh_connect.py --answer-migration --update-mesh --leave-with-host`（在 `--preset trade` 裡）會做這三項應答。

`bin/swsh_connect.py` 在 `--hold` 結束且不在交換裡時，按加入方劍的方式離開：盒子命令 3、一直髮 LEAVE_REQUEST 到被應答、然後是斷開請求。`bin/swsh_host.py` 在 `--seconds` 結束時按主持方劍的方式關閉：閒置交換上先發盒子命令 3，0.75 秒後 MIGRATION_START，等加入方離開或再過 10 秒後關掉網路。用 `--hold-after-trade SECONDS` 時，兩者都在最後一筆排隊交換之後等這麼久再做同樣的事。

## 區域網模式

在選項裡把 L、R 和左搖桿一起按下，就能開啟劍的區域網模式；遊戲會顯示「Mode réseau local activé」，並提示只有極巨團體戰是有保證的。之後 Pia 就跑在主機的 IP 網路上（見[區域網模式](pia.md#lan-mode)），Y-Comm 的連線交換搜尋也走它。

傳輸層選擇器 `0x6a8550`（盾 1.3.2）會為模式 0 建 Ldn 工廠（`0x6a90b0`）、為 2 建 Nex 工廠（`0x6a8f80`）、為 3 建 Lan 工廠（`0x6a9210`）。

| 在一臺模擬盾 1.3.2 上實測 | 值 |
|---|---|
| 連線交換搜尋所主持的會話 | 遊戲模式 60001、上限 2、版本 7 和 7、無應用資料、無屬性 |
| 搜尋開始時它的瀏覽 | 五次請求，遊戲模式 0，flags 0x2，參與者上限 4..4，結果大小 1 |
| 一臺主持中的劍離開它的加入方 | mesh 埠 1 上的 MULTI_MIGRATION_START（0x49），5.2 秒後歸於沉默 |

連線交換搜尋自己主持的會話與它開始時發出的瀏覽並不匹配。`bin/swsh_connect.py --lan auto`（也就是應用裡的 Trade (LAN Join)）會用 `--preset trade` 的 flags 瀏覽每個本地 /24，並已在 Wi-Fi 上對著 Switch 2 上的正版劍以及模擬主機完成過交換；它把主機的沉默當作對方離開（`--lan-quiet`，預設 3 秒），正版那次在玩家退出後 3.1 秒結束。`bin/swsh_host.py --lan`（應用裡的 Trade (LAN Host)）主持一個會話，正版劍從它的連線交換搜尋里加入並完成交換，同樣是在 Wi-Fi 上的 Switch 2。

在沒有 `--our-ip` 的多地址電腦上（VPN 會搶走預設路由），它會等主機發來第一次瀏覽，然後在那個子網的地址上主持。

區域網模式下的連線交換搜尋會發兩種瀏覽：

| 瀏覽 | 在哪構建 | 條件 |
|---|---|---|
| Y-Comm 附近玩家登錄檔 | `0x006c46a0` | 參與者上限 4..4、只找開放且空位的、結果大小 1 |
| 交換搜尋的隨機匹配（`Session::JoinRandomSession`，`0x0183f860`） | `0x006bb120` | 遊戲模式 60001、參與者上限 2..2、只找開放且空位的、結果大小 8 |

第二種會加入它聽到的第一個匹配會話，若沒有就自己主持一個兩人的會話（見[區域網模式](pia.md#lan-mode)）。兩人會話只會匹配第二種。

一個大廳的應用資料在區域網上與在 LDN 上是同樣的 0x168 遊戲位元組：LDN 廣播就是 Pia 的 0x18 位元組頭後面跟著這些位元組。區域網匹配物件把它們放在 +0x284，最多 0x168 位元組（`0x006b98c0`，經 `0x006b5bcc` 從巢穴大廳設定），而瀏覽結果由 LDN 掃描所用的同一個解析器讀回 0x168 位元組進 Y-Comm 列表（`0x006c2360`，區域網從 `0x006bb9c0` 呼叫，LDN 從 `0x006ca0b0` 呼叫）。所以巢穴團體戰在廣播偏移 `0xB0` 處的記錄，落在應用資料的 `0x98` 處。

| 在區域網模式下的模擬盾 1.3.2 上實測 | 值 |
|---|---|
| 一個巢穴主持的會話（「Combat à plusieurs」） | 遊戲模式 60006、上限 4 |
| Y-Comm 的瀏覽 | 遊戲模式 0、flags 0x2、參與者上限 4..4、只找開放且空位的、結果大小 1；它會按應用資料列出一個巢穴會話 |
| 一次不帶連線密碼的極巨大冒險「Invite Others」（正版劍） | 開始時一次瀏覽：遊戲模式 50000、上限 4..4、flags 0x712、屬性 2 = `0xfffffffe`、3 = `0x33d39298`、4 = `0x253cad29`；沒有回應時它就主持遊戲模式 50000、上限 4 的會話 |
| 加入一個列出的團體戰（「Participer」然後「Commencer le combat」） | 一次範圍開放的瀏覽、一條明文保活，然後是把會話請求（型別 5）發到子網廣播的 49152 到 49155 埠，之前沒有任何主機請求 |

`bin/swsh_host.py --lan` 搭配 `--raid-boss`、`--raid-event` 或 `--lair-legendary` 會主持一個攜帶大廳位元組的四座會話，並在自己的站點埠上監聽子網廣播；模擬盾和 Wi-Fi 上 Switch 2 裡的正版劍都列出了它、加入並打了這場團體戰，由主機提供服務（見[哪個站點在服務](swsh_raid.md#which-station-serves)）。`bin/swsh_connect.py --lan` 搭配 `--preset raid` 或 `--preset lair` 會瀏覽場景 60006 或 50000 的四座會話；它加入過模擬盾和正版劍的巢穴大廳並讓戰鬥開始，也加入過正版劍的冒險，租用的寶可夢被選中、第一場戰鬥成功載入。

瀏覽的屬性條件是六張最多 20 個 u32 的列表，位於 `0x1A + 0x50 k`，計數以 u8 存在 `0x1FA + k`，搜尋標誌 `0x40 << k` 開啟第 k 個屬性。極巨大冒險搜尋會跳過屬性值不符的會話。那三個值編碼的是什麼還不清楚；同一臺主機的兩次搜尋帶著相同的值。區域網主持端會把針對自己遊戲模式的那次搜尋的值抄進它自己的會話資訊（`pia_lan.criteria_attributes`）；之後一臺正版劍就能加入 `bin/swsh_host.py --lan --lair-legendary` 並開始它的冒險。

### 區域網上的連線密碼

`SetMode(comm, mode, code)`（`0x01096d10`）把場景放在 comm+0x70、連線密碼放在 comm+0x74，後者是個 optional u32（一個存在位元組，再是值）。`StartRandomMatching` 的引數把它帶到 +0x88，進到匹配物件的 +0x278（區域網走 `0x006b83ec`）。LDN 加入（`0x006ca1c0`）和 NEX 隨機加入（`0x006c6b7c`）用 `%u` 格式化它並當作會話密碼傳下去。而區域網匹配類（`0x006b6000`..`0x006bc000`，在 `0x006ba480` 構造）裡沒有任何程式碼讀 +0x278，它的建立、瀏覽、隨機加入設定也都不帶密碼。區域網模式下一次帶密碼的連線交換搜尋發出的瀏覽與不帶密碼時完全相同（在正版機上實測），並且會加入任何與之匹配的會話，不管對方的密碼是什麼：區域網主持端與加入方對帶密碼和不帶密碼的搜尋一視同仁。

## 操作備註

- 絕不要在實機上加 `--verbose`；用 `--capture FILE`。
- 主機的通道會在會話之間變化（見過 1 和 6）；掃描會保留最忙的那個（見[通道](ldn.md#channels)）。
- `0x2D0`（在 `0x006a970c`、`0x006a9740` 分配）是會話單例的大小（`0x006b4410`，全域性 `main+0x02616758`），一個 720 位元組的結構體，與神秘卡片無關。
