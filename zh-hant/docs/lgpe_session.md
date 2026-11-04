---
title: Let's Go 卡帶與會話
parent: Let's Go 皮卡丘與伊布
nav_order: 1
---

# 卡帶、它的金鑰與會話

本頁覆蓋 Let's Go 皮卡丘與伊布從卡帶金鑰到交換提交的全過程。地址都是 Let's Go 皮卡丘 1.0.2 解壓後 `main` 的偏移，按 `tools/switch/nso_read.py` 給出的佈局：text 為 `0..0xd32ba8`，rodata 從 `0xd33000` 起，data 從 `0x1527000` 起。

## 這個標題由什麼構建

更新 NSP 攜帶 Program NCA `2b7730a9e56498bbafac2002d4908c6b`（標題 ID `010003f003a34000`，rights id `010003f003a348000000000000000007`，金鑰世代 6）。所有 `nn::pia` 和 `gflnet3` 引用都在它的 exefs `main` 裡。

    ./.venv/bin/python tools/switch/xci_read.py "<the .nsp>" --keys prod.keys \
        --nca 2b7730a9e56498bbafac2002d4908c6b --exefs 0 --extract main
    ./.venv/bin/python tools/switch/nso_read.py main main.bin
    ./.venv/bin/python tools/switch/rtti_names.py main.bin 0xd32ba8

Pia 是靜態連結的：269 個 `nn::pia` 類、2112 個具名虛擬函式，`nn::pia::local` 裡含有 `LdnCreateNetworkJob`、`LdnCreateSessionSetting`、`LdnJoinSessionSetting` 和 `LocalProtocol`。`nn::ldn` 從 nnSdk 匯入，GOT 槽位 `0x15fa1e0..0x15fa2a8`。Pia 之上，`gflnet3` 打包了協議緩衝區。

## LDN 口令

    W3GoSMEn7RIIUQ89rzqBHGhGferRNb7K18ZBq2aNuj8Us9RO9Q9JYyGOZlLy8MYL

`0xf73a50` 處的 64 位元組，原樣使用，與劍與盾的相同。`0x004db6b4` 連同長度 `0x40` 把它傳給 `LdnCreateSessionSetting` 的 setter `0x5c0fb0`，`0x004dbba4` 傳給 `LdnJoinSessionSetting` 的 setter `0x5c1280`。`LdnCreateNetworkJob`（`0x5ce640`）把它儲存在 +0xC4，長度儲存在 +0x104，並在 `nn::ldn::CreateNetwork`（`0x5ce988`，PLT 樁 `0xd31c78`）之前構建 `nn::ldn::SecurityConfig`。

## Pia 遊戲金鑰

    p1frXqxmeCZWFv0X

`0xefd659` 處的十六個 ASCII 位元組，也就是劍與盾、傳說 阿爾宙斯和朱與紫所用的金鑰。當模式欄位 `[x19+0x98]` 為 0 或 2 時，`0x0011a364..0x0011a384` 把它寫入加密設定的 +0x24c。

## Pia 頭

版本 3（即 wiki 的 Pia 5.11-5.17）。初始化函式 `0xd122d4` 寫入 `0x00000003_32AB9864`；校驗函式 `0xd12400` 檢查魔數以及 `(byte & 0x7f) == 3`。佈局就是劍與盾的版本 4，只有版本位元組不同（`pokeldn/ldn/pia4.py`）：

    0x00  4  magic 0x32AB9864, big-endian
    0x04  1  0x80 (encrypted) | version = 3
    0x05  1  connection id
    0x06  2  packet id
    0x08  8  AES-GCM nonce
    0x10  16 AES-GCM tag
    0x20     ciphertext

## 訊息分幀

固定的 22 位元組訊息頭（Pia 5.11-5.12；反序列化函式 `0x5ae870`，寫入函式 `0x5aeb00`），見 `pokeldn/ldn/pia3.py`：

    0x00  1  flags: 1 destination is a bitmap, 2 relay needed, 4 relayed, 8 unbundled
    0x01  1  version, 1
    0x02  2  payload size, big-endian
    0x04  1  protocol type
    0x05  1  protocol port
    0x06  8  destination, big-endian: a constant id, or a station bitmap under flag 1
    0x0E  8  source constant id, big-endian
    0x16     payload, padded to a multiple of 4

## 會話金鑰

`LocalProtocol` 的派生函式 `0x5cd560` 與 BDSP、劍與盾的相同：以會話引數（`0x57cfc0`）為種子做 SEAD xorshift128，取四次，在 `LocalProtocol+0x49c` 的遊戲金鑰下做 AES-128-ECB。`pokeldn.ldn.pia5.ldn_session_key`。IV 沿用 pia4：`crc32(網路 id 小端 || 主機 MAC)` 的三個位元組、一個源 id 位元組 0、頭部的 nonce。

廣播的應用資料以一個 24 位元組頭開始：

    0x00  4  network id, random per session
    0x04  4  CRC32 of the user password, 0
    0x08  1  system communication version, 4
    0x09  1  header size, 0x18
    0x0C  4  session param, the key seed
    0x18     the game's application data

## LAN 模式

Let's Go 1.0.2 中有一條程式碼從不進入的 LAN 路徑。網路建立函式 `0x5dabb0` 為模式 0 構建本地工廠、為 1 構建 Nex、為 2 構建 Lan 工廠（`0x5ddaf0`，LanNetworkFactory 建構函式 `0xd14a20`），與之配套的啟動函式 `0x4da710` 接受 1 或 2。但所有寫入模式的程式碼都只傳 0 或 1：`0x115818` 傳 1，會話物件的建構函式在 `+0xa4` 處把模式清零，它唯一的 setter `0x348eb0` 也只存 0 或 1。英文的選項、匹配、選單和錯誤訊息裡沒有任何 LAN 文字。

## 連線碼

連線碼就是 NetworkInfo 的 scene id，`1000a + 100b + 10c + 1`，每一位取它在選擇器中的序號（皮卡丘 0、伊布 1、妙蛙種子 2、小火龍 3、傑尼龜 4、波波 5、綠毛蟲 6、小拉達 7、胖丁 8、地鼠 9）；SSID 始終是 `01000000000000000000000000000000`。`0x891580` 把三次選擇合併，`0x978080` 算出 `10 * number + mode`（模式 1 為交換），會話建構函式 `0x4db1e0` 把它寫進 `LdnCreateSessionSetting+0x60`（`0x4db6ac`），Pia 再把它複製到 `NetworkConfig.intentId.sceneId`。

同一個建構函式還決定正在搜尋的遊戲主機在哪個通道上託管：`{1, 6, 11}[scene % 3]`，表在 `0xf73a44`；`pokeldn.lgpe.search_channel(code)`。三隻皮卡丘是 scene 1、通道 6；妙蛙種子、小火龍、傑尼龜是 2341、通道 6；皮卡丘、皮卡丘、妙蛙種子是 21、通道 1。

正在搜尋的遊戲主機只有在某個網路於它自己的通道上廣播了它的 scene id 時才加入。`bin/lgpe_host.py --code NAMES` 就在該通道上託管（`--channel auto` 會掃描遊戲主機的網路）。`bin/lgpe_join.py` 不傳送連線碼。

## 本地協議

會話狀態走協議 0x24、埠 0：即 wiki 的 5.7-5.45 更新會話訊息（`pokeldn.ldn.local_protocol.parse_update_session`），本地頭版本 1、型別 0x11、八個節點：主機 `169.254.105.1` 排名 0，加入方 `169.254.105.2` 排名 1，其餘為 255。訊息體以小端攜帶主機的常量 id（MAC `48:f1:eb:20:9b:22` 對應 `000048f120229beb`）；訊息頭則以大端攜帶它。

## 站點協議（用於加入網格）

先走協議 0x14 的連線請求，再走 0x18 的網格加入。處理函式 `0x5b8800` 按 wiki 的 5.10-5.18 佈局讀取，站點協議版本 9：

    [0]     message type            1
    [1]     connection id
    [2]     version number          must be 9 (0x5b8848)
    [3]     is inverse connection request; rejected above 1
    [4]     target constant id      big-endian u64, the console's own (0x5b6830)
    [0xC]   target variable id      big-endian u32, checked only when [3] is 1
    [0x10]  inverse connection id
    [0x11]  station location        36 bytes for a joiner: no public address, zero NAT fields
    [...]   ack id                  u32, the message size minus four

零售遊戲主機會帶著反向請求跑完整套序列：

    ->  connection request (is_inverse 0)
    <-  ack; inverse connection request (is_inverse 1) with the host's location
    ->  ack; connection response (type 2, result 0, padded to 0x38)
    <-  connection response, 840 bytes, repeated until acknowledged
    ->  ack

### 站點發送的連線響應

0x348 位元組（解析函式 `0x5b9270` 接受 0x3C）：

    0x00  1  message type 2
    0x01  1  result
    0x02  1  version 9
    0x03  1  platform 4
    0x05  8  the receiver's constant id, big-endian
    0x0D  4  the receiver's variable id, big-endian
    0x31  4  the network id, big-endian
    0x35  2  01 01
    0x37  0xC3  a PlayerInfo (`station_protocol.player_info`); its first byte must be below 5
    0x344 4  the ack id

見 `station9.build_connection_response`；`bin/lgpe_join.py --player-name NAME`。遊戲主機若收到 0x3C 位元組的響應，就永遠不會發送自己的克隆資料，並離開克隆會話。

## 加入網格

0x18 上的網格加入請求（`mesh_protocol.build_join_request`，本機站點索引 253）換來一個 148 位元組的加入響應（主機索引 0、加入方索引 1、最大活躍 2、最大總數 8），在 0x14 上確認，然後是一個更新網格（型別 0x20）。隨後主機依次推送更新會話（0x24，用 0x21 確認）、RTT（0x58）、同步時鐘（0x1C）和克隆（0x73）。保活是協議 0x08，無訊息體，以同樣的方式應答。

## RTT 協議（0x58），版本 3

十六位元組：[0] 處是大端 u32 的 kind，[8] 處是傳送方 19.2 MHz 計時數的 u64；應答把 kind 置 1 並原樣帶回該計時數。`rtt_protocol.build_v3`；`--no-rtt` 關閉它。

## 同步時鐘協議（0x1C）

由主機控制的一個網格時鐘。請求：[0] 是 u64 計時數，[8] 為零。應答：[0] 原樣返回計時數，[8] 是以毫秒計的網格時鐘 u64。站點從收到加入響應起每兩秒請求一次，並加上往返時間的一半。克隆協議的時鐘就是這個時鐘；主機若在加入方自己的執行時長上收到克隆時鐘，就會釋放該克隆並離開。`pokeldn.ldn.sync_clock`。

## 可靠協議（0x7C），遊戲資料所在之處

Pia 5.11 的頭是 24 位元組；序列 id 從 0xFFFFF82F 開始。

    0x00  1  flags
    0x01  1  stream id, 3 for the game, 0 on an acknowledgement
    0x02  2  payload size, big-endian
    0x08  4  sequence id, big-endian
    0x0C  4  the next sequence id expected from the peer
    0x18     the payload

確認就是隻有頭部。`pokeldn.ldn.reliable3`。

## 克隆協議（0x73）

`nn::pia::clone::CloneProtocol`（`PiaCommon-5_11_4`）承載對端同步。每條訊息都以版本 3、一個型別位元組（高半位元組是結構，低半位元組是變體）和傳送方以大端 u16 表示的幀計數器開頭。

### 時鐘同步，最初兩秒

雙方每秒約發 5 個時鐘請求（型別 0x11，18 位元組，`0x51f9b0`），並以應答回覆（型別 0x21，22 位元組，`0x51fab0`）：

    clock request                              clock reply
    [4]   4  sender message count              [4]   4  sender message count
    [8]   2  destination bitmap                [8]   2  destination bitmap
    [0xA] 8  sender system tick                [0xA] 4  sender clone clock, ms
                                               [0xE] 8  the request's tick, echoed

訊息計數從 1 起，統計傳送方的請求、應答和參與訊息。點陣圖是 `1 << station index`。克隆時鐘為 0 的應答會讓零售遊戲主機一直請求下去。

### 參與

在十個請求被應答之後，加入方傳送一條參與訊息（型別 0x31，10 位元組，點陣圖 0x0003）；主機應答 0x33 併發來自己的一條，加入方再應答 0x33。之後時鐘應答變為 0x22，時鐘請求停止。

### 克隆元素

一個克隆由克隆型別（1 到 4）、所屬站點（0xFD 表示無）和一個 u32 克隆 id 共同標識。兩個站點各自發布自己的副本。

    every command message   [4] u8 clone type, [5] u8 owning station, [8] u32 clone id
    types 0x81 to 0xc4      [0xC] u32 message count, [0x10] u16 destination bitmap, then fields
    types 0xd1 to 0xf4      [0xC] the data

低半位元組是命令令牌加一：1 宣告、2 請求、3 結束、4 加鎖。`0x51c110` 通過表 `0xf769c4` 分派高半位元組：

| 型別 | 附加內容 | 長度 |
|---|---|---|
| 0x8N | 無 | 0x12 |
| 0x9N | [0x12] 處的 u32 毫秒時鐘 | 0x16 |
| 0xaN | 時鐘，[0x16] 處的 u8 計數 | 0x1a |
| 0xbN | 時鐘，[0x16] 處的 u32 參與者點陣圖 | 0x1a |
| 0xcN | 時鐘、計數、[0x1A] 處的點陣圖 | 0x1e |
| 0xeN | [0xD] 處的 zlib 流 | 確認狀態 |
| 0xfN | [0xD] 處的一個位元組、[0xE] 處的 zlib 流 | 帶資料的狀態 |

zlib 流解壓後是一條記錄，tag 為 0x20：

    0x20 0x06 u16 clone id  0x01  0x00                               empty copy
    0x20 len  u16 clone id  0x03  u8 station  u16 0  u16 participants  u32 clock  data
    0x20 0x0A u16 clone id  0x05  u8 the station acknowledged  u32 clock

`clone.pack_record` 能復現每一條抓到的流（一次壓縮、一次同步重新整理、一個末尾空塊）。

| 互動 | 訊息 |
|---|---|
| 擁有者宣告 | 0xa1 和 0xb1；對端在資料之前應答 0xa2 和 0xc1 |
| 接管 | 對端用 0x91 應答 0xa1 |
| 資料 | 擁有者的 0xf3；對端的 0xe3，攜帶同一時鐘 |
| 釋放 | 0x83；0x84 確認 |
| 離開克隆會話 | 0x32；0x41 應答 |

0xa2 攜帶網格時鐘和計數，克隆型別 4 上計數為 1、克隆型別 2 上為 0。0xaN 的 `0x17..0x19` 位元組是棧殘留，沒有接收方讀取（`01 2808ab`）。克隆型別 3 和 4 的 0xa1 處理函式（`0x522a60`）會以 0xa2、0x91 或什麼都不回；針對未知克隆的 0xa1 會引出 0x91。`0x51c110` 在遇到目標不符、訊息計數不高於傳送方上一條（`0x51c1e0`）、長度或型別越界時靜默丟棄。當協議的待處理掩碼 `+0xc0` 清空時，參與握手完成。

### 克隆 0 這一對

克隆型別 3 上克隆 0 的擁有者用 0xa1 和 0xb1 宣告它，並且只有在收到對端的 0xa2 和 0xc1 之後才釋出。應答丟失的主機會讓遊戲主機停在「vous allez bientôt être connecté」；`bin/lgpe_host.py` 每 110 ms 重發這一對，最多 20 次，直到收到 0xa2、0xc1 或 0x91。

### 宣告的目標欄位決定什麼

首次宣告某個克隆的 0x81 攜帶整個網格（0x0003）；它後面的 0xa1 只攜帶對端（0x0001）。若 0x81 上給的是對端點陣圖，對端既不會應答 0xa2，閘門 `0x11b080` 也就永遠不會放行。

### 可靠協議上的遊戲訊息

`0x7c` 上的每條訊息都是一個 16 位元組的頭加一個訊息體：

```
+0x00  4  kind: the channel id
+0x04  4  body length: 0x168 kind 1, 0xe8 kinds 2 and 4, 4 kind 3
+0x08  4  step, counting every message a station sends from 1
+0x0c  1  tag, 0 on every trade message
+0x0d  1  destination station index, 0xff for every station
+0x10     the body
```

`0x116f30` 構建頭部；交換的傳送方走 `0x4d94e0`。接收函式 `0x1171d0` 取佇列中第一條 step 等於本站下一個值的訊息，丟棄發往別處或型別未註冊的訊息，而把型別或 tag 不同的訊息留在佇列裡，擋住它後面的一切。

kind 是該會話的一個從 1 開始的 u32 計數器（`0x116e80`）給出的通道 id，同時最多註冊 16 個。一次交換註冊 1（交換會話）、2（提供）、3（提交）和 4（交換後存檔重建的提供物件）。每次註冊都會宣告一組克隆，所以克隆 id 與通道 id 並不相同。死通道每幀都會被壓實，因此一個席位大約只佔用四個，可以無限連續交換。

kind 1，訊息體 0x168，身份：存檔的 MyStatus 塊（PKHeX 的 `MyStatus7b`，名字為 UTF-16LE），由兩個站點在任意一方收到任何東西之前發出：

```
+0x00  4  trainer id, then secret id
+0x04  1  version: 42 Pikachu, 43 Eevee
+0x05  1  gender
+0x35  1  language
+0x38 26  trainer name; --trainer-name on both launchers
+0x52 16  Pokemon name
+0x90  4  the trade lock
```

為接收方玩家制作的禮物會從這裡讀訓練家（[為接收方玩家制作](gift_simulated.md#made-for-the-receiving-player)）。`pokeldn.lgpe.reference` 自帶一份訓練家為 `POKELDN` 的禮物；`--our-trainer` 替換它的 id 對。

kind 2，訊息體 0xe8，提供：當站點已釋出的狀態字到達 2 時發出，之後玩家每改變一次選擇，就在新的 step 下再發一次。新的 step 會被應答；重複的 step 是重傳。若用一個新的 step 而不是它自己的 step 去應答提供，就會開啟一輪沒有結束的新回合。傳送方是隊伍提供物件（`0x349bf0`，位於 `mgr+0x68`），`0x34a3d0` 在交換狀態允許時於每次選擇變化後重新填充它。

kind 3，訊息體 4，提交（[提交與交換鎖](#the-commit-and-the-trade-lock)）：每個站點發一個 1，其中一個在收到對端的 1 後發一個 2。收到 2 即提交；1 之後的任何其他訊息體都被忽略。

kind 4，訊息體 0xe8，搭載正常存檔在其存檔 3000 ms 之後、交換演示之後重建的提供物件：先是站點的第一個槽位，然後每選一次一個。它開啟下一次交換。

| step | kind | 訊息體 |
|---|---|---|
| 1 | 1 | 身份 |
| 2 | 2 | 提供，每次選擇再發一次 |
| 5 | 3 | 提交，1 |
| 6 | 3 | 提交，2 |
| 7 | 4 | 第一個槽位，每次選擇再發一次 |

從 0 開始計的第 r 次交換，在 kind 2 + 2r 上提供、在 3 + 2r 上提交、在 4 + 2r 上結束。它的隊伍克隆是 2 + 3r 和 3 + 3r，提交克隆是 4 + 3r。

| 啟動器 | 連續交換 |
|---|---|
| `bin/lgpe_host.py --next-offer` | 用下一條記錄應答之後每次交換的選擇 |
| `bin/lgpe_join.py --offer ...` | 用下一條記錄應答遊戲主機的 kind 4；最後一條之後再不應答 |
| `bin/lgpe_host.py --lead` | 為 `bin/lgpe_join.py` 扮演遊戲主機的角色；`tests/test_esp32.py` |

兩個啟動器都在 2 交換完成時寫出收到的記錄；撤回的提供不寫任何東西。

kind 2 和 4 的訊息體是 232 位元組的盒結構：第 7 世代的佈局套上第 6 世代的加密，從 +0x08 起的四個 56 位元組塊按 `((ec >> 13) & 0x1F) % 24` 置換，並與以加密常量為種子的 LCRNG 流異或。`pokeldn.lgpe.pb7`。遊戲主機不校驗就儲存它：一隻異色、100 級、隱藏特性的百變怪，各項 IV 均為 31、各項 AV 均為 200，在概要介面上顯示如常。

### 什麼閘住遊戲自己的第一條訊息

連線交換物件的狀態機是 `0x349200`（跳轉表 `0xf4e994`，基於 +0x68）。

| 狀態 | 做什麼 |
|---|---|
| 3 | 宣告克隆 1 的集合（`0x11aec0`），置 4 |
| 4 | 等待閘門 `0x11b080` |
| 6 | 在沒有網路輸入的情況下發送 kind 1 |
| 7 | 統計 kind 1 訊息，包含自己的迴環；到兩個時進入 8 |
| 8 | 終態；介面顯示已找到玩家 |

當 +0x90 的 SendClone 和 +0x1258 的 SharingClone 的已確認集合 `clone+0xA8` 包含每個參與站點、每個隊伍克隆的完成位元組 `+0x110` 都已置位、且 +0x1430 的站點索引不是 0xFD 時，閘門才放行。一個站點的位只有通過來自該站點的、克隆型別 2 上的 0xa2 才能進入 `clone+0xA8`。

`0x11aec0` 在一幀內宣告一個站點的克隆集合：克隆型別 2 上的 `0x81`、型別 4 上的 `0xa1` 和型別 1 上的 `0xa1`。克隆 id 2 和 3 在 id 1 之後約 3.2 s 由交換排程器 `0x886530` 發出，而它只在模式字 `+0x8C` 為 3 時釋出；那個 3 是誰寫的仍然不明。

### 把零售遊戲主機託管到它的交換介面

- 本地協議的訊息體以小端攜帶主機的常量 id；若用大端，遊戲主機無法解析傳送方，會停在狀態 7。
- 更新會話在會話變化時發出，之後再多發一次，從不按定時器傳送。
- 主機在釋出克隆 0 的那一幀宣告克隆 1；遊戲主機約 31 ms 後宣告自己的，等待的主機會輸掉這場競爭，角色隨之互換。
- 應答對端宣告主機所擁有的克隆的 0xa2，要攜帶對端 0xa1 的時鐘；若用主機自己的時鐘，遊戲主機會永遠重新宣告。
- 兩個站點都要用自己的一份副本應答每一次克隆型別 2 的釋出。
- 主機必須在克隆型別 4 和 1 上釋出克隆資料，否則加入的遊戲主機會一直停在搜尋介面。

### 一次接管必須攜帶的序列

`0x520c30` 在宣告時把一個序列分配到 `+0x10C`；完成函式 `0x520ce0`（一個 `0xa2`）只在值等於 `+0x10C` 時才置 `+0x110`，而 `0x520d30`（一個 `0x91`）只解除連結、不置位。該值是對方站點針對該克隆最近一次 `0xa1` 的時鐘。用加入方自己的時鐘構造的 `0xa2` 會錯過，狀態字永遠離不開 4。入站的 `0x82` 同樣會分配序列，所以用一串 `0x82` 去應答每次重新宣告，會無休止地製造序列。

### 加入方對每個克隆跑一次的接管互動

接管會取消對端的宣告，並在加入方自己的時鐘下宣告該克隆：

```
+0 ms   host    0x81 clone 2, 0x81 clone 3, dest 0x0003
        host    0xa1 x2 per clone                        clock 0x197e, the host's
+5 ms   joiner  0x82, 0x91 x2, 0x82, 0x91 x2, 0x84 x2    echoing 0x197e
+75 ms  joiner  0x81 clone 2, 0x81 clone 3, 0xa1 x2 each clock 0x19c1, the joiner's own
+102 ms host    0xa2 per clone                           clock 0x19c1
        host    0xa1 per clone                           clock 0x19e2, the host's own
+141 ms joiner  0xa2 per clone                           clock 0x19e2
```

加入方對每個克隆只接管一次。之後每次重新宣告都只得到一條攜帶該宣告時鐘的 `0xa2`，位於加入方站點下的克隆型別 2 上，載荷為 `<clock> 00 00 00 02`；第二次接管會讓對端無限制地重新宣告。

只針對對端的重新宣告會引出對端在克隆型別 1 上的 `0x82`，而它又引出主機的型別 4 副本，遊戲主機以 `1 1 1` 應答。若主機收不到針對提交克隆的 `0x82`，就會帶著已儲存的交換鎖停在確認介面；`pokeldn.ldn.clone` 每 100 ms 重發一次只針對對端的 `0x81`，最多 20 次，直到 `0x82` 到達。

### 一次交換走過的兩條克隆記錄

克隆型別 2 副本的 20 位元組資料：

```
+0x00  4  state: 1 a vote, 2 a vote withdrawn, 4 a forced leave
+0x04  4  argument, 1 on selection and 2 on confirmation
+0x08  4  a counter, incremented on each call
+0x0c  4  the station's own step
+0x10  4  the trailing word
```

克隆型別 4 副本的 32 位元組資料是會話主機（權威方）的檢視：

```
+0x00  4  A, the agreed argument
+0x04  4  B
+0x08 16  per station index: the counter of the vote it last saw withdrawn
+0x18  4  the station's step
+0x1c  4  the trailing word
```

權威方 `0x11b6c0` 只有在每個站點都針對當前尾字以引數 X 釋出狀態 1 時才把 A 移到 X，同時釋出 A 和加一的尾字；狀態 4 則立即移動 A。對處於狀態 2、且引數與 A 不同的站點，它記錄計數器並把尾字繼續推進。副本只會被時鐘嚴格更新的記錄替換；`pokeldn.ldn.clone.Participant.record_clock` 讓每條記錄的時鐘保持在上一份之上。主機在型別 4 上釋出 32 個零，會讓遊戲主機停在「communication en cours」。

交換介面的狀態（`0x34a300`）由 A 和本地狀態得出：

| A | 本地狀態 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| 0 | 0 | 1 | 1 | 0 | 0 |
| 1 | 2 | 3 | 3 | 0 | 2 |
| 2 | 4 | 4 | 4 | 4 | 4 |
| 3 | 5 | 5 | 5 | 5 | 5 |

狀態 4 開始同步存檔，狀態 2 回到選擇，5 表示對端離開。

被提供的隊伍克隆走過 `1 1 1`、尾字 1，然後 `x 2 2`、尾字 2。比它大一號的提交克隆先接下前兩個，然後是一個零：

```
+0 ms     type 4 data, 32 zeros, with the announcement
          the peer publishes 1 1 1 step 0 once its player has confirmed
          1 1 1 step 0                 the host's own confirmation
+30 ms    1 1 1 step 1                 type 4 data 1, zeros, step, 1
+8 ms     the peer answers 0 1 1 step 1
+27 ms    0 1 1 step+1 1               the offered clone goes 0 2 2 step+1 2,
                                       and the kind 3 carrying 1 goes under that step
+3 ms     the peer's kind 3 carrying 1
+63 ms    kind 3 carrying 2 under the next step, every copy republished under it
after the trade demo and the normal save:
          two more clones announced, 32 zeros on type 4; the peer publishes 0 0 0 on each
then      kind 4 under the next step
```

只有當型別 4 副本的第一個字是 1 時，對端才應答尾字 1。遊戲主機宣告每個克隆並先投票；加入方若接管每個克隆，並在自己的狀態字下重新發布主機的頭三個字和尾字，就能完成這次交換。

在確認介面再按一次 A 會撤回投票：在 `1 2 2` 之後是 `2 2 3`。以 A 2 應答它，會在未完成交換的情況下提交交換鎖（[未解決](lgpe.md#unresolved)）。應答 `1 0 0 3 0 0 step T+1` 會讓遊戲主機回到選擇；A 0 下撤回的選擇 `2 1 4` 得到 `0 0 0 4 0 0 step T+1`。`bin/lgpe_host.py` 就是這樣應答的；`tests/test_lgpe_host_withdraw.py` 讓這兩種情形都跑過遊戲的程式碼。

### 交換動畫

遊戲主機在自己的 step `0e` 之後播放交換動畫，其間不傳送任何交換載荷。從該 step 起：動畫約在 1.7 s 開始，收到的寶可夢約在 15.3 s 出現，遊戲主機的型別 4 載荷（248 位元組）在 27.0 s 到達，玩家約在 28.8 s 拿回控制權。

### 提交與交換鎖

交換鎖是 MyStatus `+0x90` 處一個以秒為單位的 u32 倒計時（`savedata.bin` 的 `0x1090`；setter `0x1c9d40`）。一次交換的同步存檔把它置為 600，並在提交互動之前提交一次；互動完成後再把它提交回 0。交換選單的檢查 `0x9765f4` 在它非零時拒絕交換（`0x976634`，訊息 `0x0248810f825b1fee`）。只有在遊戲處於前臺且計入遊戲時間時，鎖才會倒計時，每秒一秒，每次更新至多一秒。

`0x347190` 構建三種存檔序列之一：正常存檔、同步存檔、致命錯誤。一次交換使用同步存檔（更新函式 `0x838070`，跳轉表 `0xf867c4`）：

| 狀態 | 做什麼 |
|---|---|
| 0 | 等待 `SaveThread`（已提交 600），決定本機是否傳送那個 2（`0x838660`），應用收到的寶可夢並在記憶體中把鎖清零（`0x838800`），啟動 `FirstSaveThread` |
| 1 | 等待 `FirstSaveThread` 寫完，然後隨機延遲 `2000 + r % 6000` ms |
| 2 | 註冊提交通道 |
| 3 | 在提交克隆上投票 1，等待該通道的閘門 |
| 4 | 傳送一條攜帶 1 的 kind 3 |
| 5 | 接收對端的 kind 3；訊息體不是 1 就中止；傳送方站點發一個 2 |
| 6 | 收到 2 即表示提交；任何其他訊息體都被忽略 |
| 7 | 等待 `FirstSaveThread` 提交 |

沒有任何狀態帶超時。在狀態 0 結束到那個 2 之間記錄到的任何網路錯誤都會中止：`FirstSaveThread` 不提交，存檔保留 600，排程器丟擲致命錯誤 `error_fatal_save`（“An error occurred. You couldn't trade Pokémon. Press the HOME Button to end the game.”，標籤 id `0x191615296121e064`，位於 `common/message_error.dat`），遊戲從此不再返回。提交期間對端離開網格也會記錄這樣一個錯誤。

| 對端的行為 | 後果 |
|---|---|
| 權威方釋出 A 2 | 遊戲主機提交 600；權威方欠下整個提交互動 |
| 第一條攜帶 1 以外內容的 kind 3 | 中止，鎖已置位 |
| 在接收方註冊提交通道之前發出的 kind 3 | 被丟棄；狀態 3 的投票會把它壓住，直到雙方都註冊完畢 |

`0x838660` 決定由誰傳送那個 2：若一方交出急凍鳥、閃電鳥、火焰鳥、超夢、夢幻、美錄坦或美錄梅坦來換任何其他寶可夢，就由它傳送；反向則不由它傳送；其餘情況由會話開始時擔任主機的站點（`mgr+0x128c`）傳送。

`0x838800` 把收到的寶可夢寫到本方提供的盒槽位上，並施加交換的副作用：圖鑑登記、通訊進化（方式 5 總是成立，方式 6 需持有道具；方式 7 是蓋蓋蟲與小嘴蝸，永遠不會匹配，因為到達的副本被同時當作兩隻寶可夢傳入；方式 6、19、20 會清空持有道具），以及遊戲記錄 476（本地交換）或 477（聯網狀態下的交換）。

### 交換排程器

`0x886530` 從選單執行鏈路直到其退出，通過 `0xf87bc4` 對 `[obj+0x68]` 做分支：

| 狀態 | 做什麼 |
|---|---|
| 0 | 初始化；交換選單程序寫入模式字 `+0x8c` |
| 1 | 模式 1 或 2 開始連線對戰，隨後到 6；模式 3 等待隊伍提供物件就緒；網路錯誤轉到 8 |
| 2 | `[obj+0x100]` 為 5，即交換介面的繼續，開始同步存檔；其他值轉到 8 |
| 3 | 等待同步存檔；結果為 2 時丟擲致命錯誤；否則銷燬提供物件並開始交換演示 |
| 4 | 釋放演示，進入狀態 5 |
| 5 | 把收到的寶可夢寫入盒槽位，開始正常存檔，進入狀態 7 |
| 6 | 進入狀態 8 |
| 7 | 等待存檔；結果為 1 轉到 8，其他轉到 1 |
| 8 | 銷燬提供物件並離開 |

存檔程序在 `obj+0x178` 處得到一塊空間：

```
+0x00  save type: 0 sync save, 1 normal save, 2 or 3 fatal error
+0x04  result: 0 done, 2 aborted, 1 the link ends
+0x08  box index of the own offered Pokemon
+0x10  the received Pokemon
```

正常存檔在其 `SaveThread` 之後等待 3000 ms，然後在新通道上重建隊伍提供物件。排程器從狀態 7 回到狀態 1，因此一個席位可以一次接一次地交換。交換選單的選項 1（交換）存模式 3；選項 2 和 3 存 1 和 2，即單打和雙打連線對戰，它們各自注冊帶 tag 1 和 3 的通道，並計入 `local_btl_single_cnt` 和 `local_btl_double_cnt`。交換則計入 `local_trade_cnt`（`0x1dc`）或 `net_trade_cnt`（`0x1dd`）。

### 加入方離開

遊戲主機按 Retour 退出時，在被提供的克隆上釋出狀態 4，引數先是 0 後是 3；主機對每一次都以頭三個字為零、尾字加一、並把該引數作為型別 4 副本的第一個字來應答。雙方釋放各自的克隆（0x83，由 0x84 應答）。一旦它的克隆協議空閒（[離開前的等待](#the-wait-before-leaving)），遊戲主機就在網格協議的可靠埠上傳送網格離開請求 `04 01`。

它應當收到可靠確認，以及不可靠埠上的離開響應 `08 00`（網格主機的索引）。`LeaveMeshJob` 每 40 ms 重發該請求，最多 5000 ms。收到 `08 00` 後，遊戲主機發送自己的斷開請求，並在 0.1 s 內取消認證；若無人應答，它在 5.0 s 時取消認證。Retour 之後，主機會發送型別 3 的站點斷開請求；遊戲主機以型別 4 應答。

遊戲主機對加入方的離開請求連答兩次 `08 00`，然後每 0.3 s 重複一次本地協議的開始主機遷移（型別 0x13）。加入方的斷開請求會把主機的玩家送回選單。`bin/lgpe_join.py --leave-after SECONDS` 執行該退出（`pokeldn.lgpe.leave`）；`--stall-leave`（預設 5）在任何 kind 3 之前有投票未達成一致時執行它，`--hold-after-trade N` 在最後一條排隊的交換之後 N 秒執行它，而在交換之外的 `--connect-seconds` 或 `--hold` 結束時也會執行。若無人應答，我們的離開請求會在第一次之後 5.0 s 放棄，與 `LeaveMeshJob` 的放棄方式相同。該退出不會解除交換鎖。

### 主機離開

玩家按退出的遊戲主機會發布狀態 4、引數 3，釋放自己的克隆，並在空閒後傳送網格遷移開始 `44 00 01`（主機索引、下一任主機的索引），每 45 ms 重傳一次，最多 5000 ms，直到每個站點應答 `48 <index>`。隨後它廣播一條攜帶主機遷移狀態 1 的更新會話，並每 301 ms 重複一次開始主機遷移（型別 0x13），直到沒有其他站點連線或已過 10000 ms，然後銷燬網路（八個 LDN 斷開幀，原因 3）。`bin/lgpe_join.py` 應答該 ack 和 `48 01`，並在第一個 0x13 上離開（`pokeldn.lgpe.leave.host_departure`）。

`bin/lgpe_host.py` 在 `--seconds`、`--hold-after-trade N`（遊戲主機對最後一條排隊交換給出結果之後 N 秒）和 Ctrl-C 時以同樣的方式離開（`pokeldn.lgpe.leave.HostLeaver`）：狀態 4、在被提供的克隆上引數 3、每 100 ms 重發一次釋放，最多 2.5 s，直到每一個都被確認，然後是遷移開始，最後是更新會話和開始主機遷移。這兩條訊息與錄到的逐位元組相同。遊戲主機離開後，或 20 s 之後，它停止網路；再按一次 Ctrl-C 會立即停止。

### 離開前的等待

拆除步驟 `0x116bc0` 結束克隆會話，並在克隆協議空閒時立即離開；否則它等待 150 次呼叫，約 2.5 s。當沒有克隆存在未確認的資料、且每個站點都用 0x41 應答了它的 0x32 時，協議到達空閒。釋放克隆 0 之後，遊戲主機仍會約每 100 ms 釋出一次克隆型別 2 的副本；對端若在克隆型別 1、站點 0xFD 上以攜帶釋出方站點和時鐘的 0xe3 逐條應答，就能讓它進入空閒並在 0.3 s 內離開。若對端用自己的副本應答，則會讓它等滿整個等待時間。`pokeldn.ldn.clone.Participant` 在對端釋放克隆 0 之後應答。
