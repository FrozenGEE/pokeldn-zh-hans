---
title: 連線協議
parent: 火紅與葉綠
nav_order: 1
---

# GBA 連線，以及其上執行的東西

本頁講火紅／葉綠在 Pia 之上的鏈路層：RFU 幀、席位屏障、聯盟室、對戰與競技場。引用均指向 [pret/pokefirered](https://github.com/pret/pokefirered)。

# RFU 鏈路層

## 每次父輪詢只有一個子槽位

`RfuMain2_Parent` 每次輪詢只保留一個子槽位，並檢查其滾動的 `childSendCmdId` 標籤是上一個 `+1 mod 8` [link_rfu_2.c:876-892]。標籤不符會遞增 `numChildRecvErrors[i]`；連續四次以上則呼叫 `RfuSetErrorParams` 並終止鏈路。一次輪詢裡出現第二個槽位就算丟了一個標籤。子端若自由傳送、或每次輪詢發兩個槽位，會在房間走位開始後 0.3 s 內被丟棄；每次輪詢一個槽位時，每個標籤都按序。這條規則在每個階段都成立，席位走位也不例外。

## 父端表格的第一行是遊戲主機自己的命令，被映象回送

遊戲主機發送期間的每一次卡頓都受這條規則支配。

`MGL_Send` 按 252 位元組分塊，在每個分塊之前以及結束時都等待 `MGL_HasReceived(link->sendPlayerId)`（即自己的 id 1）[mystery_gift_link.c:176,205; mystery_gift_client.c:33]：它要等到自己的塊經父端 `gRecvCmds` 的第一行完整回送，而這一行由主機映象 [link_rfu_2.c:970,1125]。`HandleBlockSend` 一直扣住 INIT 直到被映象，`SendLastBlock` 重複最後一個分片直到被映象，隨後把映象點陣圖中缺失的每個分片重新排隊 [link_rfu_2.c:1366-1416]。

`rfu_leader.ChildEcho`：

- 從不丟棄一條不同的命令；丟掉一個分片就要重發整塊，再丟一次就終止鏈路；
- 合併仍在等待中的重複（`SendLastBlock` 每幀重發）；映象已經發出之後的重複才會被應答。

子端每收到一個父幀就發一條命令 [link_rfu_2.c:600]，因此映象佇列不會自行增長。

## 一步地格恰好是 16 次鏈路更新

`FacingHandler_DpadMovement` 置 `directionSequenceIndex = 16`，每次鏈路更新遞減一次 [overworld.c:3432-3470]。按下 N 個方向鍵之後，指令碼化行走的間隔還需要 `16 - (N mod 16)` 次更新。

## 玩家的輸入並不總是被髮送

當 `GetLinkSendQueueLength() > 1` 時，`UpdateHeldKeyCode` 把 EMPTY、方向鍵碼、START 與 A 改寫成 `LINK_KEY_CODE_NULL` [overworld.c:2786-2810]。`LINK_KEY_CODE_READY`（0x16）不受影響：要以 0x16 為準，絕不要以方向鍵碼缺席為準。

## 席位是一道相互屏障

`Task_EnterCableClubSeat` 呼叫 `SetInCableClubSeat()`（下一次按鍵發出的是 READY），並在 `GetCableClubPartnersReady()` 上自旋 [cable_club.c:827-869]，只有每個玩家都為 READY 時才為真 [overworld.c:2988-2999]。隨後 `Task_StartWirelessTrade` 執行 `SetLinkStandbyCallback()` [cable_club.c:910-943]。只在雙方都為 READY 之後才驅動待機輪次；對處於 `CABLE_SEAT_WAITING` 的遊戲主機驅動它們，會讓其席位狀態機出錯。

## 真實的子端發出什麼，端到端

一臺法版零售火紅子端；IDLE 計數取自一次交換：

```
IDLE x8
SEND_BLOCK_INIT w1=0x0011 x4   + 17 fragments      (LinkPlayer)
IDLE x31
SEND_BLOCK_INIT w1=0x0009 x4   + 9 fragments       (trainer card)
IDLE x262   READY_EXIT_STANDBY w1=0x0000 x1
IDLE x72    READY_EXIT_STANDBY w1=0x0001 x1
IDLE x45    <room: SEND_HELD_KEYS 0x1b x24, EMPTY, 0x1a once, the walk, READY, then EMPTY x13>
IDLE x22    READY_EXIT_STANDBY w1=0x0002 x1
IDLE x28    READY_EXIT_STANDBY w1=0x0003 x1
IDLE x75    -> the host pulls the party
```

- 每個待機輪次是一幀，由 Pia Reliable 重傳直到落地。
- 輪次之間子端全零 IDLE。隊伍交換之前，主端的靜默幀計數器只在恰好空閒的槽位上推進；發一個 EMPTY 保活會讓它死鎖。
- `LINK_KEY_CODE_IDLE`（0x1a）把對端的鏈路狀態置為 IDLE [overworld.c:2755]；只有處於該狀態的玩家才會執行地格指令碼。

## 雙方只有在聽到對方之後才前進

只有當某個 `gRecvCmds` 條目非零時，`CB1_UpdateLinkState` 才執行 `UpdateAllLinkPlayers` [link_rfu_2.c:787-800]；迴圈最終穩定為每個往返一次交換。主機 `SEND_HELD_KEYS` 的高位元組是 `heldKeyCount`，每條準備好的命令計一個。

## 席位之後的待機閘門與走出

雙方坐下之後，遊戲主機先把主機的計數反射回去，再在 mpId 0 上廣播自己的 `READY_EXIT_STANDBY` count=2。它只在子端計數等於自己的計數時才接受 [link_rfu_2.c:1577-1591]。count=3 要以主機自己的 mp0 count=2 為閘門再發一次，間隔大於 `HostTradeTiming.entry_final_standby_quiet_frames`（75 個槽位，比子端 60 幀的重發更長 [link_rfu_2.c:1529]）。

走出：主機發出 `LINK_KEY_CODE_EXIT_ROOM`（0x17）並阻塞，直到每個玩家都為 EXITING_ROOM [overworld.c:2962-2981]；子端在按住鍵流上以自己的 0x17 應答。

## 離開房間

遊戲主機走出交換中心時——無論坐下之前還是對戰之後——都會發出按住鍵 0x17，並在 "Please wait" 上等待每個玩家 [overworld.c:2977]。主機在 `H_ENTRY_SEAT`、`H_RETURN_FIELD` 與各對戰狀態下以自己的 0x17 應答（`host_trade._child_send_held_keys`）。

### 靜默閘門

當遊戲主機已有 `QUIET_GATE_SECONDS`（0.25 s）什麼都沒發時，主機丟掉自己的重傳，只保留每 `QUIET_RETRANSMIT_SECONDS`（1 s）一次（`tests/test_host_quiet_gate.py`）。

## 交換之後的取消

`BufferTradeParties` 在禮物緞帶交換之後、選單命令被讀取之前清除已接收塊標誌 [trade.c:1549]，[1593-1633]，因此在其中完成的取消可能丟失。`bin/frlg_trade_join.py` 在選擇「取消」之後，等主端的 `REQUEST_CANCEL` 到達時再補發一次 `REQUEST_CANCEL`（`0xEEAA`）（`trade.py`，`_on_linkcmd`）。跟隨方在 YES 之後發出 `REQUEST_CANCEL`，隨後空轉直到 `BOTH_CANCEL_TRADE` [trade.c:2049, 1643]；主機對遊戲主機的 `REQUEST_CANCEL` 立即應答。

## 單方取消會把雙方送回選單

`PLAYER_CANCEL_TRADE` / `PARTNER_CANCEL_TRADE` 回到 `CB_MAIN_MENU` [trade.c:2094-2113]；只有 `BOTH_CANCEL_TRADE` 結束會話 [1715-1722]。用 `PARTNER_CANCEL_TRADE` 應答 `REQUEST_CANCEL` 會讓遊戲主機在 "votre ami veut échanger des Pokémon" 上迴圈；`bin/frlg_trade_host.py` 改用 `BOTH_CANCEL_TRADE` 應答。主端自己的選擇不傳送任何內容 [trade.c:1811-1828]。先發出過 `READY_TO_TRADE` 的加入方，會在主端第一次取消時收到 `PLAYER_CANCEL_TRADE`；`bin/frlg_trade_join.py` 隨後在選單處取消。

## 鏈路上的版本與語言

`IsTryingToTradeAcrossVersionTooSoon` [union_room.c:1499] 只對既非火紅也非葉綠的夥伴觸發。`ConvertInternationalString` 對日文名字做特例；法版火紅接受英文神秘卡片。聯盟室搜尋會跳過日文候選 [union_room.c:3726]；神秘禮物的 `Task_ListenForCompatiblePartners` 則不會。日文卡帶使用另一套神秘卡片與神秘新聞的 activity 編號（[日文版式](frlg_rom_map.md#japanese-layout)），並把廣播國際編號的主機排除在好友列表之外。要服務所有卡帶的主機，只在 `--language japanese` 下才廣播日文編號；應用會傳入神秘禮物工具的語言，預設取設定中的訓練家語言。在神秘禮物好友列表裡，遊戲主機在 GameData 中發出其 ROM 的遊戲程式碼，主機據此在配送前選取該卡帶的地址。

## 模擬器可以自行關閉鏈路

`HandleLinkConnection` 在 Switch 構建上呼叫 `svc_51` [link.c:1654]；返回非零即執行 `CloseLink()`，隨後在神秘禮物下軟復位或呼叫 `RfuReloadSave()` [link.c:1674]：Switch 錯誤 2318-0006。若崩潰而主機在 RFU 層面一切正常，問題就指向 LDN/Pia。

| SVC | 呼叫位置 | 作用 |
|---|---|---|
| `swi 0x45` | librfu_rfu.c:667,749 | 把 `gRfuLinkStatus` 交給模擬器 |
| `swi 0x49` | AgbRfu_LinkManager.c:657 | 非零期間，在 SEARCH_CHILD 中保持 `connect_period` 開啟 |
| `swi 0x4a` | AgbRfu_LinkManager.c:720 | 同上，在 SEARCH_PARENT 中 |
| `swi 0x4b` | link_rfu_2.c:2114, union_room_player_avatar.c:518 | `SVC4B_EXIT_EARLY` 提前退出 SpawnGroupLeader；`SVC4B_RESEED_RNG` 用主機的訓練家 id 重新播種 |
| `swi 0x51` | link.c:1654 | 立刻關閉鏈路（神秘禮物下軟復位） |
| `swi 0x53` | wireless_communication_status_screen.c:328 | 由模擬器驅動退出狀態畫面 |

# 無線層，以及這款遊戲如何用到它

## 廣播的速率集

不含 6、9、12 Mbit/s 的關聯響應，會讓遊戲主機在關聯後 2.9 到 3.9 s、Pia 會話一完成就離開 LDN：76 次這類關聯中有 42 次離開，而帶這些速率的 284 次中 0 次。信標的請求速率集與遊戲主機的請求速率集都無關緊要。遊戲主機究竟需要其中哪幾個速率尚不清楚。ESP32 softAP 攜帶全部十二個（[hardware_esp32.md](hardware_esp32.md)）。

主機廣播 Switch 的速率集（1B 2B 5.5B 11B 6 9 12 18，擴充套件 24 36 48 54）。信標頭部攜帶元素 0、1 與 3（41 位元組）；Switch 的其它元素可選。帶 WMM 的信標會讓遊戲主機發送 QoS 資料幀，其 TID 會進入 CCMP 的 nonce 與 AAD。在 privacy 能力下不含 RSN 的探測響應，會讓遊戲主機的關聯請求得不到應答。`host_pia` 以單播發送型別 5 的 Update Session。

## 遊戲主機作為 Pia 子端

- 遊戲主機子端需要型別 2 的 Join Response：只有型別 5 時，它每 0.5 s 重發一次加入請求，並在加入後 3.05-3.20 s 離開。
- 主持神秘禮物的遊戲主機在 50-66 ms 內以型別 5 應答遊戲主機子端；它對 `bin/frlg_mg_client.py` 的應答沒有型別 2，型別 5 要等到 2.0 s 之後，原因不明。主持交換的遊戲主機在 34 ms 內發出型別 5 與型別 2。

一臺主持神秘禮物的遊戲主機對接收客戶端，從其 Net 0x11 開始：

    0.000  Net 0x11 (once)
    0.006  client: Net 0x12 + Session join
    0.252  RTT request, then every 316ms
    2.038  Session type 5, no type 2
    2.040  client: type 6 (finalize); 2.159 reliable open
    4.63   host's own NI (the player's YES)
    6.82   SEND_PLAYER_IDS, 6.87 BLOCK_REQ
    8.15   Net 0x50 property update every ~0.5s, acked 0x51

## 離開 Pia 會話

遊戲主機子端在發出 RFU 的 `D` 幀之後離開：先暫停，再發會話型別 3 的離開請求，然後是其 LDN 解除認證（原因碼 3）。在沒有型別 4 應答的情況下：

| 間隔 | 實測 |
|---|---|
| `D` 到第一個型別 3 | 1.97-2.02 s |
| 型別 3 到型別 3，共發四次 | 0.48-0.54 s |
| 第一個型別 3 到 LDN 離開 | 2.03-2.08 s |

    type 3, 22 bytes:  03 | random u32 | constant id (8) | variable id (2) | kind 0 | IPv4 | port
    type 4, 15 bytes:  04 | random u32 | the request's constant id and variable id

偏移在 GBA 應用的 `main` 中：`LeaveMeshJob` 在 `0xcacf4` 處發出該請求，期限 500 ms；`WaitLeaveResponse`（`0xcaf38`）在響應標誌 `+0x99` 出現時結束，否則最多重發四次（`0xcb06c`..`0xcb08c`）。型別 4 的分支（`0xba028`，表 `0x180fc9`）為攜帶該站點自身 id 的 15 位元組訊息置起該標誌。主機的型別 3 處理函式（`0xbf2d4`）接受 22 或 34 位元組，並以請求的第 5 到 14 位元組作為型別 4 應答（`0xbf454`..`0xbf4e4`）。`HostPeerProtocol` 對每個型別 3 都這樣應答，單播，首部為 `(console variable, 0x00C6)`，按發往該遊戲主機的單播計數器編號；編號低於該計數器的型別 4 會被忽略。遊戲主機為每個目的地各保留一個計數器。

該暫停是一個固定的 120 tick 倒計時（每秒 60 tick，`0x4ff64`）。`TryDisconnectRfu` 與 `LinkRfu_Shutdown` 發出 `swi 0x44` [link_rfu_2.c:1446-1455, 625]；處理函式 `0x58b0c` 投遞斷開請求 1（`0x53d98` -> `0x4f0ec`，`+0x730`），tick `0x4ee34` 置 `+0x734 = 0x78`（`0x4ef00`），歸零時呼叫槽位 `0x78`（`0x4ef60`），由 `Session::LeaveAsync`（`0xb1060`，來自 `0x537e0`）發出型別 3（[pia.md](pia.md)，離開會話）。收到任何東西都不會縮短它；只有請求 2 或 3（`swi 0x42`，或在 PID 0 下的 `swi 0x43`）或置起 `+0x277c` 的 Pia 錯誤才會。

## 802.11 行為

- 遊戲主機作為站點：不省電，每個資料幀前發 RTS，離開時解除認證一次。
- Switch 作為主機時以 11M 發信標，以 48-54M 發資料。

## Pia 首部 nonce 是遊戲主機會強制執行的計數器

遊戲主機會丟棄 8 位元組首部 nonce 不嚴格大於該通道上最後一次已接受值的任何資料包。`Sim._next_nonce` 與主機都會計數。

## 前向攜帶

每個可靠幀都會在隨後的 4 個數據報中重複。空口丟包率為 1-2% 且成簇；一個空洞會扣住其後每個槽位直到它重傳，而這次重傳會把遊戲主機 8 層深的 RFU 接收佇列灌過其深度。沒有前向攜帶時，丟一個槽位就會讓遊戲主機斷開。主機按序號去重。

## 遊戲主機的確認延遲是 512 ms 的節拍器

遊戲主機的累積 ACK 在 CTRL 幀載荷中（`parse_bulk_ack`）；可靠首部的 `ack` 是傳送方最低的待確認序號。每 16 或 17 個 512 ms 的槽位（與 LDN 加入相位鎖定），遊戲主機會停 50-70 ms，重傳其最後幾幀，隨後其 ACK 一次跳過好幾幀。負載之下，這次停頓會落在已經填滿的傳送視窗上。是哪個模擬器或 Pia/LDN 定時器驅動它，尚不清楚。

## ident-25 卡死：一個空洞加上無界積壓

當空洞在一個無界積壓之後閉合時，遊戲主機一次性交付所有積壓幀，其 8 層深的 RFU 佇列丟掉 ident-25（`MG_LINKID_RAM_SCRIPT`）分片，鏈路仍在卻停在 "Transmission..." 上。父塊從未被反射，因此這次丟失在抓包裡看不出來。`HostSession` 在有 `HOST_OUTSTANDING_MAX`（6）個未確認幀時扣住新幀，`--ram-script-block-repeat 3` 則把 ident 25 發三次。究竟是空口丟包還是遊戲主機側交接丟了分片，尚不清楚。

## 卡片之後的傳輸階段崩潰

在確認停頓之後每 tick 重發每個未確認幀，會殺死會話。以下檢查預設開啟：

- `HOST_RTX_LIMIT` 限制每個 VBlank 的 Reliable 重傳次數。
- `FRLG_ECHO_MAX` 限定子端塊槽位的 FIFO 回顯。
- 傳送套接字是非阻塞的，`FRLG_QUIET_GATE_MS` 在遊戲主機靜默期間扣住重傳（接受卡片之後約 0.5 s，是其快閃記憶體存檔）。

## 扣在套接字與空口之間的資料包

主機的資料包在上空口之前被扣住 0.1-1.1 s，會讓遊戲顯示 "erreur de connexion, rapprochez-vous" [link_rfu_2.c:2312, link.c:1521]。在 ESP32 板子上，測得的最長等待是 265 ms（[ESP32 無線](hardware_esp32.md)，TX_DONE）。

# 聯盟室

## 進入列表：廣播的 activity 位元組

搜尋中的遊戲主機只在候選的 activity 位於其 link group 的接受列表裡時才留下它 [`IsPartnerActivityAcceptable`，union_room.c:1590；src/data/union_room.h:398-456]。在聯盟室中，遊戲主機先搜尋 `{ACTIVITY_SEARCH, 0xFF}`，再搜尋 `IN_UNION_ROOM | activity`（`IN_UNION_ROOM = 1 << 6`）[union_room.c:2664]。記錄的第 16 位元組是 activity：21 會在神秘卡片畫面上列出這臺主機，22 則在神秘新聞上。

## 連線：必須恰好且僅為 IN_UNION_ROOM

`IsPartnerActivityIncompatible` 要求 `partner->activity == IN_UNION_ROOM` 嚴格相等 [link_rfu_2.c:2933]。0x44 會生成頭像，但連線被拒（"le DRESSEUR est occupé"）；0x40 能連上，交換意圖在鏈路建立之後再協商。

## 沒有父端 NI，以及五幀規則

聯盟室子端設定的是 TYPE_UNI 接收緩衝，從不設 TYPE_NI [link_rfu_2.c:2526, 533]。父端的 NI 體是致命的：它會以 ERR_RECV_BUFF_OVER 失敗 [librfu_rfu.c:2300]，並以 "erreur de connexion" 結束 [link_rfu_2.c:2585]。`RFULeader(skip_parent_ni=True)`（`--union-room`）會跳過它。

遊戲主機會在它第 5 個未應答的父幀上斷開（`maxMFrame = 4` [link_rfu_2.c:128]）。`--union-room-keepalive N`（120 可用）會在 UNI 之前把第一個 NI_START 重現 N 個 VBlank。遊戲主機隨後還要等約八秒：只要 NI_START 仍待處理，`rfu_UNI_setSendData` 就以 ERR_SUBFRAME_SIZE 失敗 [librfu_rfu.c:2262, 1449]，直到 `NI_failCounter_limit`，即最後一個 NI_START 之後 480 幀 [link_rfu_2.c:139, AgbRfu_LinkManager.c:1328]。

## 連上之後遊戲主機做什麼

鏈路建立後，遊戲主機交換訓練家卡片 [union_room.c:2858-2879]，並顯示 Salut / Combat / Tchat / Retour。每個選擇都發一個 `SEND_PACKET` 並等待 [union_room.c:3151]：

| 遊戲主機發出 | activity | 主機的應答 |
|---|---|---|
| 0x48 | CARD（Salut） | 0x51 ACCEPT |
| 0x44 | TRADE（交易板） | 0x51 ACCEPT |
| 0x41 | BATTLE（Combat） | 0x51 ACCEPT |
| 0x45 | CHAT（Tchat） | 0x51 ACCEPT |
| 0x40 | EXIT（Retour） | 視為遊戲主機主動關閉 |

每項活動之後雙方都 `SetLinkStandbyCallback` [union_room.c:2995, :3012]。接受方以 `svc_CommsAllowedByParentalControls()` 為閘門 [union_room.c:3159, :3037]。Retour 先發 0x40，再發 READY_CLOSE_LINK，然後正常斷開。

## 交易板

交易板讀取記錄的第 18 位元組（`type << 2`）、第 19 位元組（`gameClear | level << 1`，[廣播記錄](frlg_rom.md#the-advertisement-record)）以及 22:24 處的（`tradeSpecies:10`）[union_room.c:3400；include/link_rfu.h:107]。

一次交易板交換就是每條鏈路一場：`Task_StartUnionRoomTrade` 儲存 `CB2_ReturnToField` [union_room.c:1744]，而 `CB2_SaveAndEndTrade` 只為交易中心的回撥保留鏈路 [trade_scene.c:2722-2725]。時序：遊戲主機的寶可夢塊（count 9）、主機的、它的郵件塊（count 19）、主機的、動畫、READY_FINISH、CONFIRM_FINISH、各存檔屏障、雙向 READY_CLOSE_LINK、斷開。沒有隊伍交換，沒有選單，也沒有房間流程。

## 聊天

聊天走 `SendBlock(0, buf, 0x28)`（count 4），未經請求，也沒有 `BLOCK_REQ` [union_room_chat.c:429, :823]：

    [0]      command: 0 NULL, 1 CHAT, 2 JOIN, 3 LEAVE, 4 DROP, 5 DISBAND
    [1..8]   player name, EOS-terminated
    [9]      multiplayer id            (JOIN / LEAVE / DROP / DISBAND)
    [9..39]  message text, EOS-terminated (CHAT)

[union_room_chat.c:1256-1283]。0x45 的 ACCEPT 會保留鏈路 [union_room.c:1938]；兩個成員進入時都發 JOIN。一行是 15 個條目 [union_room_chat.c:21]；接收方會畫到螢幕外，而主機會在啟動時拒絕過長的行（`uroom_chat.entry_count`）。收到 LEAVE 時主端必須斷開鏈路 [union_room_chat.c:596-660]：主機在 0.1 s 後發 DROP 並關閉。追加到 `--chat-file` 的行會在寫入後約 1.7 s 抵達遊戲主機。

## 連線對戰（UR_BATTLE 0x41）

`HasAtLeastTwoMonsOfLevel30OrLower` [union_room.c:4565] 要求每方隊伍裡至少有兩隻是 30 級或以下的非蛋寶可夢，在提供與接受時各檢查一次 [union_room.c:2923, 3176]。

雙方各選兩隻之後，每方發一個 0x20 位元組的塊，首位元組 0x51（取消時為 0x52），其餘為零（`CB2_UnionRoomBattle`）；發任何別的內容都會關閉鏈路。Switch 路徑額外加兩次鏈路任務等待，中間夾一段待機（分支 50-52）。`StartUnionRoomBattle(BATTLE_TYPE_LINK | BATTLE_TYPE_TRAINER)` [union_room.c:1811] 置 `linkType = 0x2211` [link.h:92；battle_controllers.c:520]。隨後 [battle_main.c:934]：

    state 1  SendBlock struct LinkBattlerHeader {versionSignatureLo, versionSignatureHi,
             vsScreenHealthFlagsLo, vsScreenHealthFlagsHi, struct BattleEnigmaBerry}
    state 3  SendBlock gPlayerParty[0..1]   200 bytes      state 4  recv -> gEnemyParty
    state 7  SendBlock gPlayerParty[2..3]   200 bytes      state 8  recv
    state 11 SendBlock gPlayerParty[4..5]   200 bytes      state 12 recv
    state 15 InitBattleControllers

### 主站選舉

只有 `BATTLE_TYPE_IS_MASTER` 一方執行回合結算、傷害與 RNG [battle_controllers.c:141, :45]；作為非主站的主機只是一個對戰控制器。`LinkBattleComputeBattleTypeFlags` [battle_main.c:886]：若 `gBlockRecvBuffer[0][0] == 0x100` 或雙方簽名相等，玩家 0 為主站，否則版本高者為主站。主機發送 0x200，從而讓遊戲主機成為主站。

### 鏈路緩衝協議

每條控制器命令都是一個帶 8 位元組首部的 SendBlock [battle_controllers.c:401-435]：`BUFFER_ID, ACTIVE_BATTLER, ATTACKER, TARGET, SIZE_LO, SIZE_HI, ABSENT_BATTLER_FLAGS, EFFECT_BATTLER`，載荷按 `size - size % 4 + 4` 存放。`bufferId` 0 = BUFFER_A（命令），1 = BUFFER_B（應答），2 = 清除執行標誌並攜帶傳送方的多人 id [:566-594]。戰鬥位 0 屬於主站。

`MarkBattlerForControllerExec` 置位 `28+battler`；命令的回送塊置起每個玩家的半位元組，各玩家再用 bufferId 2 清除自己那一位 [battle_util.c:185-201]。主站只在 `gBattleControllerExecFlags == 0` 時前進。

需要超過一次 ACK 的命令 [battle_controller_player.c]：

    CONTROLLER_GETMONDATA    -> EmitDataTransfer(BUFFER_B, size, data)   [player.c:1515]
    CONTROLLER_CHOOSEACTION  -> EmitTwoReturnValues(1, B_ACTION_*, 0)    [player.c:232-241]
    CONTROLLER_CHOOSEMOVE    -> EmitTwoReturnValues(1, 10, move | target << 8) [player.c:342]
    CONTROLLER_CHOOSEPOKEMON -> EmitChosenMonReturnValue(1, partyId, order)    [player.c:1316]
    CONTROLLER_OPENBAG       -> EmitOneReturnValue(1, itemId)            [player.c:1340]
    CONTROLLER_EXPUPDATE     -> EmitTwoReturnValues(1, RET_VALUE_LEVELED_UP, exp) [player.c:1051]
    CONTROLLER_ENDLINKBATTLE -> gBattleOutcome = payload[1], then ack     [player.c:2876]

`B_ACTION_USE_MOVE` 為 0、`USE_ITEM` 為 1、`SWITCH` 為 2、`RUN` 為 3 [battle.h:34]。第一個 `GETMONDATA` 用一個 0x58 位元組的 `struct BattlePokemon` 應答 [pokemon.h:170]；重算得來的欄位可能為零。戰鬥位 0 的 BUFFER_B 應答可以省略 [link_opponent.c:444]。連線對戰中的戰鬥位可以享有最高行動順序 [battle_main.c:3239, 3548-3560]。

### 反編譯中看不到的兩條規則

- 對戰中狀態機按塊路由，從不按大小路由：每個 ACK 與短命令都是 16 位元組、兩個分片的記錄。
- ACK 絕不能越過它所確認的塊的回顯。遲到的回顯會再次置起執行位 [battle_util.c:193]，遊戲主機就會永遠等在 `gBattleControllerExecFlags == 0` 上 [battle_script_commands.c:2041]。`HostTradeEngine._echo_owed` 在子端命令等待映象期間扣住新塊，`rfu_leader.echo_blocks` 則讓 ACK 等到回顯的 0..count-1 每個分片都到齊。

### 節奏由 RFU 的 VBlank 預算決定

一個對戰步驟約需一秒：按 `HOST_VBLANK_SECONDS = 1/59.727` 每個 VBlank 一個 RFU 槽位，一個命令塊橫跨約二十幀，再加上回程。相鄰的 `bufferA` 命令中位間隔為 800 ms。

## 兩臺真實遊戲主機放到空口上的內容

一臺通過 Direct Corner 主持的火紅，向葉綠髮 25.5 幀/秒，向主機發 161.8 幀/秒。它在 `application_data` 的 0x11 偏移處以 ASCII 攜帶 Switch 的檔案名，而不是訓練家名字。

## 主機 tick 率與遊戲主機的輸出速率

`--tick-hz` 設定主機每秒的 RFU 槽位數；預設每個 VBlank 一個。在 20 Hz 下，一次交換耗時約為兩倍，遊戲主機發出的資料包多 80%。

# 電纜俱樂部競技場

`frlg_trade_host.py --colosseum` 主持寶可夢中心 2 樓、第三個 NPC、競技場、單打對戰、JOIN。只有 `CB2_ReturnFromCableClubBattle` 會遞增神秘卡片的 `battlesWon` [cable_club.c:792]。

`Task_StartActivity` 把 `ACTIVITY_BATTLE_SINGLE` 當作 `ACTIVITY_TRADE` 處理 [union_room.c:1903]，只是地圖（`MAP_BATTLE_COLOSSEUM_2P`，位於 (6, 8)）與 `HealPlayerParty()` 不同。與交換路徑的差別：

1. `LINK_GROUP_SINGLE_BATTLE` 接受 `{ACTIVITY_BATTLE_SINGLE, 0xFF}` [src/data/union_room.h:398]；`build_colosseum_app_data` 只改這一個位元組。
2. 2 人席位指令碼沒有隊伍檢查 [data/scripts/cable_club.inc:576]。
3. `Task_StartWirelessCableClubBattle` 的分支 2 由雙方主動發出裸的 28 位元組 `struct LinkPlayer` [cable_club.c:701]，隨後分支 4-6 在 `CB2_InitBattle` 之前加一段待機。
4. 整支隊伍參戰 [union_room_battle.c:47]。

從 `CB2_InitBattle` 起，它就是沒有 0x51 選擇塊的聯盟室對戰。席位只需要 READY 鍵，且席位之後沒有待機輪次；停在分支 3 的遊戲主機發出 count 3 的 `SEND_BLOCK_INIT` 與 `04 40 00 80 65 df | bb c8 ff 00 11 00 | 01 00 03 00 00 00`，該塊的到達即完成進入。對戰之後主機欠一個退出鍵 [overworld.c:2977]。

## 什麼決定一次競技場之行是否算數

認輸對另一方就是勝利：`HandleAction_Run` 在帶 `B_OUTCOME_LINK_BATTLE_RAN` 時置 `B_OUTCOME_WON` [battle_main.c:4300]，該標誌在返回前被清除 [:3734]。被計數的 id 是對方 28 位元組記錄中的訓練家 id [cable_club.c:794]，每個各計一次，每項統計五次 [mystery_gift.c:630]。對三個不同的 `--id` 值各認輸一次，即可拿到對戰計數卡的傷藥：

    save 0x3434:  0100 0000 0000 2300    battlesWon 1, lost 0, trades 0, icon 35 CARD_TYPE_LINK_STAT

# 兩條主機側約束

- 關閉定時器跑在 `activity.tick()` 裡，而 `HostSession.tick` 在空洞守衛生效期間會跳過它，因此停止確認的遊戲主機會把它卡住；在確認退出之後遊戲主機一離開 LDN，執行時即停止。
- 全零的 `easyChatProfile` 會在訓練家卡片上打出 "??? ???" [easy_chat.c:166-171]。一個詞是 `(group & 0x7F) << 9 | (index & 0x1FF)` [easy_chat.h:1089]，每張卡四個；用 `EC_WORD_UNDEFINED`（0xFFFF）填充。
