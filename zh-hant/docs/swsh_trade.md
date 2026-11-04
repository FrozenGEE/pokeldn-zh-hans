---
title: 連線交換
parent: 劍與盾
nav_order: 3
---

# 與零售版劍與盾交換

劍與盾的連線交換，從快照交換一直到存檔。幀結構、內容註冊與 PK8 見[同步框架](swsh_protocol.md)。

## 時序

    1  the console broadcasts its 3456-byte snapshot on protocol 0x84, port 0
    2  the client acknowledges the fragments (0x21) and the transfer (0x19 / 0x28)
    3  the client sends its own snapshot on 0x84 port 1 and reports it complete
    4  the trade screen opens
    5  the console sends the 40030 RPC pair on 0x7C port 1, several times a second
    6  the client answers the pair and sends `imReady` on 20030
    7  the console offers a Pokemon on 20030; the client offers one on 10050
    8  the player accepts (box command 4)
    9  the confirmation ladder runs on content 40
    10 the console writes its save

主持中的遊戲主機不會確認加入方發在埠 0 上的快照；加入方的快照走埠 1。在它的 0x84 得到應答之前，遊戲主機不傳送任何其它內容，並無限重傳該快照。`pokeldn/ldn/broadcast4.py` 實現了全部四種。

## 交換 RPC

ping、塊訊息與提供使用埠 0，40030 對使用埠 1；發到錯誤埠上的應答不會被讀取。

    id 40030 = 40000 + 30
      1  offset      30
      2  base        10000, and 20000 in the other member
      3  station id  the sender's, equal to the host_constant of the seat record
      4  clock       a counter advancing between messages
      5  bytes(4)    00000000 for the 10000 member, 000018fc for the 20000 one

`000018fc` 是哨兵值 `0xfc18`（[步驟體](#the-step-body)）。`3e4e000012020801` 是 20030 上攜帶 `imReady{isReady:true}` 的訊息，由加入的客戶端發出。這些訊息可由解析出的欄位逐位元組重建（`pokeldn/swsh/trade.py`）。

- 每個應答只發一次（`--answer-once`）；按定時器重新推導應答會重發提供內容。
- 讀取器遇到非交換訊息時返回 `None`。可靠視窗上的 mesh 訊息（`44 00 01`，[主機遷移](#host-migration)）若丟擲異常，會終止接收任務與這場交換。

## 主機遷移

主持中的劍離開會話時，會在協議 0x18 埠 1 上請求主機遷移（`nn::pia::mesh::LeaveWithHostMigrationJob`）：先發可靠首部 `0f 00 00 03 00 01 00 01`，再發 mesh 訊息 `44 00 01`，即 MIGRATION_START `[0x44, host index 0, new host index 1]`。被指定的客戶端必須在 mesh 埠 1 的可靠視窗上廣播 `MIGRATION_FINISH`（[Pia 層](pia.md#host-migration)）。`--answer-migration --update-mesh` 會發出該完成訊息，並以新的主機索引發布 mesh 更新。交接之後能否保住會話尚未驗證。

主持中的零售版劍只在兩種情形下各發一次 MIGRATION_START：

| 時機 | 條件 |
|---|---|
| 盒命令 3 之後 0.8 s | 一場交換完成之後 |
| 玩家接受後數秒，遊戲主機以 `2-ALZAA-0016` 斷開之前 | 在確認階梯之前就失敗的交換，加入方未發出確認命令 |

`bin/swsh_host.py --migrate` 以盒命令 3 與 MIGRATION_START 結束其主持的交換。預設情況下主機保留會話。

## 主持一場交換

`bin/swsh_host.py` 負責主持，`pokeldn/swsh/host_trade.py` 按主持中的劍的方式主導流程。法版零售劍 1.3.2 與模擬的盾 1.3.2 都能加入並完成交換。

主機構造站點廣播，使用新的 network id、device id 與 account uid。在 0x84 上它確認加入方的三個快照分片，用自身的訓練家身份與 `--offer-file` 指定的 PK8 改寫這份線上快照，再把結果發到埠 0。遊戲主機提供的 PK8 寫入 `--received`。`--advert FILE` 與 `--snapshot FILE` 則改用已儲存的記錄。

站點握手雙向確認，主機的請求在 [0x10] 處攜帶加入方的隨機位元組；未獲確認時，加入方會重複其請求。主機應答加入方的 Sync Clock（0x1C，每兩秒一次）與 Clone Clock（0x77）。

應用層則在兩個方向的 [ping 握手](swsh_session.md)之後：

    0x84  each side's snapshot on the port of its station index (joiner 1, host 0), each acked on the
          same port; a retail host sends first, `host_trade.py` second
    110   the joiner pings first once its trade screen is up; the host answers with its own ping
          and the reply (a host ping before that screen is acked and dropped)
    30    the host opens content 30; each side offers on 20030 and sends box command 1; each
          acceptance is box command 4
    130   the joiner pings first
    50    the host publishes its Pokemon as element 0 and relays the joiner's 10050 as element 1
    120   the host pings first
    40    the ladder: host commands as element 0, the joiner's 10040 as element 1, phases 0 to 4

## 交換動畫

遊戲主機在最後一個 syncCommand 40（`3`）之後播放交換動畫，期間沒有任何交換訊息。一臺加入 `bin/swsh_host.py` 的零售版劍在發出該 syncCommand 後 1.2 s 開始播放，約 24 s 時把控制權交回玩家。

## 同一會話上的連續交換

一個會話可以一場接一場地交換：交換狀態 9 發出事件 7（成功）或 8（失敗），寫入狀態 0，玩家回到盒介面。內容 30 與 ping 110 在整個會話期間存活（初始化 `0x010c9280`）；內容 50 配 ping 130（交換狀態 1，`0x010d5440`）與內容 40 配 ping 120（狀態 6，`0x010dabc0`）每場交換都重建，每個元素都以新的 SyncPing 鑄出。已達 synced 的 SyncPing 從不在原地重置，因此在遊戲主機尚未持有內容 50 時發出的 ping 130 找不到任何持有者。

盒介面的步驟機（`0x00aa5160`，表 `0x2059218`）讀取由監聽者 `0x00c8d900` 設定的對方盒命令標誌。在步驟 3，收到對方的標誌 1（其提供）時，它一併清除標誌 1 與 4（`0x00aa5688..0x00aa569c`）；步驟 7 等待標誌 4（`0x00aa5628`），只有步驟 10 才發出動作 6，從而啟動交換狀態 1。與提供在同一突發裡發出的盒命令 4 會被抹掉，遊戲主機隨後停在步驟 7，顯示 "En attente d'une réponse"。對方的 4 必須在遊戲主機處理完其提供之後到達：`pokeldn.swsh.host_trade` 只在加入方的 4 之後才發出自己的 4，而加入方啟動器則以 4 應答主機的 4。

步驟 7 只在玩家按 B 時結束（沒有計時器）：按鍵會清除對方的標誌，發出盒命令 5（撤回接受）並離開該序列（`0x00aa57d0`）；在步驟 3 中則發出盒命令 2。在該盒命令 5 之前到達的對方提供與盒命令 1 會隨其標誌一起被清除，因此 `pokeldn.swsh.host_trade` 與 `bin/swsh_connect.py` 在盒命令 5 之後會再次發出自己的提供與盒命令 1。缺了這第二次傳送，遊戲主機就停在 "En attente d'une réponse"。

後續每一場交換都重複屬於交換本身的那部分：雙方的提供與盒命令 1、依序的兩個盒命令 4、ping 130（加入方先 ping）、相位 0 處的新內容 50、ping 120、從相位 0 到 4 的新內容 40。交換與交換之間不再出現 0x84 快照、ping 97 或 110、盒命令 3，也不再發布內容 30。`bin/swsh_host.py` 與 `bin/swsh_connect.py` 配合重複給出的 `--offer-file`，可在一個會話上每場交換用掉一條排隊記錄——前者面對作為加入方的零售版劍，後者面對作為主機的零售版劍；主機在遊戲主機離開時關閉。

`bin/swsh_connect.py` 在確認階梯走完（40040 上到相位 4）之後，把遊戲主機的提供當作下一場交換，並清除自己每場交換的狀態；40030 對與 ping 應答則繼續沿用。`bin/swsh_host.py --accept-first --lead SECONDS` 扮演主機端的玩家（先接受，交換後提供其下一條排隊記錄）；在模擬板子上，兩個啟動器在一個會話裡各換出兩條記錄（`tests/test_esp32.py`）。

零售版加入方的玩家在盒介面按 B 時，遊戲主機會發出盒命令 2 與 3、mesh `0401`，並無錯誤地解除認證；它下一次搜尋仍可加入同一個被主持的網路。搜尋中的遊戲主機會加入任何通過[匹配規則](swsh_session.md#how-a-searching-sword-finds-a-partner)的網路。

## 盒狀態機

內容 30 承載從交換介面到提供的全部過程。`onBoxSyncStateCommand` `0x010ce180` 丟棄線路命令 0 以及 7 及以上，並以事件 *N* 通知每個監聽者對應線路命令 *N*（跳轉表 `0x2067bec`）。監聽者 `0x00c8d900` 設定 `[owner + 0x218 + code] = 1`；1 表示提供，2 表示撤回提供；4 表示確認，5 表示撤回一個 4。傳送函式 `0x010cda70(content, command)` 由場景的跳轉表 `0x00a96d10` 按其動作 `+0x78` 驅動：

    action 1  ->  command 3
    action 2  ->  the Pokemon (0x010ca430), then command 1
    action 3  ->  command 2
    action 4  ->  command 5
    action 5  ->  command 4
    action 6  ->  0x010ca640, which stores its Pokemon and sets the trade state to 1

命令暫存在 `[content+0x48]` 中，直到通道就緒位元組 `[content+0x4c]` 被置位；其間若到達另一條不同的命令，會置起錯誤位元組 `[content+0x4d]`，什麼也不發。

命令 3 只由一方發出：初始化 `0x010c9280` 設定 `[session+0x419] = 0x00dceea0() & 1`（取自玩家列表），每幀更新 `0x010c9bb0` 在該位元組為 0 時發出它。`--box-open` 在收到 0x84 確認時發出盒命令。

## 交換狀態機

`[session+0x140]`，取值範圍 1..10，表 `0x2067b68`：1 啟動內容 50 併發出自己的寶可夢（`0x010ca0a0`），2 等待，3 是寶可夢交換（`0x010d54b0`），4 做決定（`0x01109320`），6 安裝四個委託並啟動內容 40（`0x010ca1ac`），8 釋放它（`0x010dac90`），9 是終態（`[+0x144]` 置位表示失敗；監聽者收到事件 8）。盒回撥 `0x010ca800` 在狀態不為 0 時丟棄事件。狀態 2 在委託 `0x010cc380` 中結束：對方的寶可夢寫入 `session+0x70`，即一條 0x60 位元組的記錄（`0x010f5cc0`）。內容 50 的初始化 `0x010d4d90` 失敗時，呼叫方置 `[session+0x144] = 1`，進入狀態 9：通訊中斷提示。

## 確認階梯

內容 40 是一道屏障，每條命令上一級。

### 相位到狀態的對映

狀態存於 `delegate+0x5c`。狀態機 `0x010dae70` 把 `state - 1` 分派進表 `0x2067ed0`；狀態 2、4、7、9 只能經由 `0x010dbf40` 離開，該函式忽略大於 4 的 u16，否則索引表 `0x2067f4c`：

    phase 0  -> state 1              -> send(0), announcing 1     0x010db308
    phase 1  -> state 3              -> send(1), announcing 2     0x010db0b0
    phase 2  -> state 5 -> 6 or 8    -> send(2), announcing 3     0x010db0dc / 0x010db104
    phase 3  -> state 10 or 11 -> 12 -> send(3), announcing 4     0x010db16c
    phase 4  -> state 13 -> 14       -> 0x010db970 tears down, content+0x84 = 0xfc18; no send

`[delegate+0x58]`（`0x110e620(...) & 1`）是角色：狀態 7 立刻發出 2，狀態 9 則在倒計時 `[delegate+0x60]` 之後發出，該值由 xorshift 在 2..302 中抽取。初始化把該委託安裝為 10040 持有者的監聽者（`0x010da6d0`），並在 `[content+0x2c0]` 處安裝其第二個介面（`0x010da6bc`）。

### 交換中的傳說寶可夢

狀態 1（`0x010daf3c`）根據 `[delegate+0x48]` 與 `[delegate+0x50]` 處的兩隻寶可夢，經兩個物種檢查 `0x008fc280(species, form)` 與 `0x008fc310(species)` 重算角色。`0x008fc280` 對物種 150、151 與 249 到 251 為真，對跳轉表 `0x02052aec`（382 到 494）與 `0x02052cb0`（643 及以上）中的條目也為真。角色為 0 時，狀態 6 轉到狀態 8，其倒計時會推遲遊戲主機的命令 2。

在一臺主持中的模擬盾 1.3.2 上，以 `bin/swsh_connect.py` 加入，測得：

| 提供的寶可夢 | 角色位元組 | 遊戲主機在 `02000200` 之後 |
|---|---|---|
| 水箭龜、皮卡丘 | 1 | 發出命令 2，0.6 s 後發出 `02000300` |
| 靈幽馬、蒼響，我方的一對只應答一次 | 0 | 53 s 內無命令，內容 40 停在狀態 9，泵停在狀態 3（`0x010db48c`，其傳送 `0x010de080` 未完成），隨後提示 "L'échange de Pokémon n'a pas pu être effectué" |
| 靈幽馬，我方的一對每秒重發 | 0 | `02000300` 出現在 `02000200` 之後 2.4 s；交換完成 |

重發的一對攜帶遊戲主機最後一次的時鐘值加上其後的流逝時間，按每秒 60 計（抓包中信封時鐘的速率）；`--ladder-refresh` 設定該週期。反方向（`bin/swsh_host.py` 主持、遊戲主機加入）在毫無改動的情況下完成了一次靈幽馬交換：其主機按自己的幀時鐘釋出。泵狀態 3 中究竟是哪個檢查讀取加入方的時鐘，尚未確定。

### 泵

`0x010db3e0` 由內容 40 的 tick 在狀態機之前執行，是一個作用於 `[content+0x80]` 的 17 狀態機，帶一段共享尾部。尾部通過 `0x010de310` 提交內容的相位 `[content+0x17c]`（該函式丟棄待處理的體並清空作業佇列 `content+0x310`），並在相位等於已宣告值時呼叫委託的狀態設定函式，隨後執行排隊的作業 `0x010ddf40` 與元素更新 `0x006d4b80(content+0xd0)`。

| 欄位 | 含義 |
|---|---|
| `+0x84` | 已提交的相位；建構函式置為 `0xfc18` |
| `+0x86` | 隨最後一條命令宣告的相位，在全部五個傳送點均為 `data + 1`（`0x010dbab0`） |
| `+0x17c` | 相位，即 `element+0xac` |

相位到達 `+0x86` 時，階梯上升一級。泵狀態（表 `0x2067f08`；`[+0x1c0]` 是元素的 `+0xf0` 通道）：

    1   element ready -> 2; delegate slot 0 with the phase (command 0, announcing 1)
    2   a pending body at +0x88 -> 3
    3   all ready, every pair's low half == phase: send the body -> 4
    4   0x006d3690 publishes the high half; the master goes to 8, others to 7
    8   every station has sent a command -> 9
    9   no resend byte set -> 10
    10  every high half == announced: the master writes shared value = announced -> 7
    11  clears every flag (a station left); [+0x374] ? 12 : 2
    14  the gated commit

狀態 8 到 10 只在主站上執行（`0x018407f0`）；其它站點跟隨共享值。內容 40 的註冊者在 `[+0x374]` 處存 1：有站點離開時進入 11、12 並終止階梯（`0x010dc720`）。

### 相位就是元素的欄位

相位就是 `element+0xac`（`0xd0 + 0xac = 0x17c`）：註冊者在 `content+0xd0` 處以 `0x006d44e0(element, 0)` 鑄出 40040 元素，而 `0x010c0000..0x010e0000` 區間內沒有任何程式碼向它寫入。

它只在 `0x006d4ca0` 中前進，即元素更新 `0x006d4b80` 的尾部：一旦共享值 `0x006d3260([element+0xf0])`（沒有時為 `0xfc18`）作為該站點自己的低半部分發布出去，相位就變為該值，並通知內容。

`0x018407f0` 在主持 Pia mesh 的遊戲主機上為真（[會話](swsh_session.md#the-pia-session-object)）。只有它會播種共享值，即 `+0xf0` 通道的 16 位子元素（[子元素種類](swsh_protocol.md#sub-element-kinds)）；每個站點都會採納它。內容還會發出另外幾種形態，見[下文](#shapes-the-confirmation-content-also-sends)：

    0x006d3260  read            ready [sub+0x61] ? [sub+0x88] : 0xfc18
    0x006d33b0  write(v)        0x006d3570 when not ready or body != v
    0x006d3570  publish         body [sub+0x88] = v and queue it per station
    0x006d3060  all high == v   every pair's [sub+0x8a] == v

寫入不會碰就緒位元組（只有接收路徑 `0x006d6a08` 會存入 `+0x60`），因此在收到訊息之前讀取返回 `0xfc18`；在主站上，那條訊息就是它自己發的。

### 步驟體

內容 40 的 elementId 20000 上的四位元組體，低半部分為相位，高半部分為最後宣告的值：

    0x006d3980(channel, v)   body = <u16 v><u16 [sub+0x8a]>    low; from the element update
    0x006d3690(channel, v)   body = <u16 [sub+0x88]><u16 v>    high; from pump state 4, [content+0x86]

一次觀測到的階梯：

    000018fc   phase 0, announced 0xfc18   the birth sentinel
    00000100   phase 0, announced 1        the cue; command 0 already sent
    01000100   phase 1, announced 1        caught up, committed
    01000200   phase 1, announced 2        state 3 sent command 1
    02000200   phase 2, announced 2        caught up
    02000300   phase 2, announced 3        committed, sent command 2
    04000400   phase 4                     the teardown rung

`trade.parse_sync_step`、`SYNC_LADDER` 與 `sync_announced_phase` 負責解析它。

### 命令

`SyncSaveDataHolder{syncCommand{data:N}}`，位於 10040、可靠埠 0。處理函式 `0x010dbc90` 會丟棄 `0x006b5850` 無法解析的傳送方（`0xfd`），把 `[arg1+0x14]` 處的 int32 轉交中轉函式 `0x010dbe20`，然後總是對 `[content+0x2a0]` 呼叫 `0x006a24a0(obj, sender, 1)`（`0x010dbdf8..0x010dbe08`）：階梯從不讀取該值，因此任何命令都能推進一級。狀態只經由 `0x010dbf40` 改變，由泵以其自己的相位呼叫。

`[content+0x2a0]` 是按站點記錄標誌的對映（`0x006a24a0` 置位，`0x006a2840` 在所列站點全部置位時返回 1，`0x006a2760` 清除）；狀態 8 等待它，提交與狀態 11 會清除它。該標誌在網路更新的排空函式 `0x006db3b0` 中置位，幀函式 `0x00f1df30` 圍繞遊戲更新執行它兩次。內容 40 的命令 tick `0x010dae70` 跑在兩次排空之間。

一級需要一條在上次提交之後到達主站的命令。在第 0 級，任何命令都算，包括落在提示體 `00000100` 上的那條；此後落在提示體（`01000200`、`02000300`、`03000400`）上的命令會在提交之前落地並被清除，只有落在追平體（`01000100`、`02000200`、`03000300`）上的那條才算數：

| 命令，每個新體一條 | 最後一個體 |
|---|---|
| 1 條，落在 `00000100` 上 | `01000200`：第 0 級 |
| 4 條，從 `000018fc` 到 `01000200` | `02000300`：第 0 與第 1 級 |
| 9 條，從 `000018fc` 到 `04000400` | `04000400`：完成交換 |

`--confirm-commands 0,1,2,3,0,1,2,3,0,1,2,3` 每出現一個新體彈出一條，`000018fc` 也算在內；佇列不能見底。`answer_rpc` 原樣回顯體，不動任何一半；`--confirm-phase N` 寫入低半部分。

### 取消與繼續訊息

30040，即 `SequenceDataHolder`（[協議頁](swsh_protocol.md#the-30000-holder)），存放在 `[content+0x2b8]`，監聽者為 `content+0x68`（虛表 `0x02580030`）：

| 分支 | 訊息 | 處理函式 |
|---|---|---|
| 1 | CancelAccepted | `0x010dce70` |
| 2 | RequestCancel | `0x010dc920` |
| 3 | RequestCancelAll | `0x010dcaa0` |
| 4 | RequestForcedProceed | `0x010dc7b0` |

三者都只在 `currentSeqNo` 等於已提交相位 `(s16)[content+0x84]` 時動作。RequestCancel 以 `CancelAccepted{[+0x84], isForced: 0}` 應答傳送方並清除其標誌；RequestCancelAll 以 `isForced: 1` 應答所列的每個站點並清除所有標誌。CancelAccepted 重跑狀態 2 到 4 並留在該相位。RequestForcedProceed（作業 `0x010dd040`）執行 `0x006d33b0([content+0x1c0], targetSeqNo)`，即狀態 10 的寫入，但不經狀態 8 與 9，也不做主站判定。

RequestForcedProceed 在沒有 `syncCommand` 的情況下推進共享相位（一臺模擬的盾）。若階梯後續的命令都是這類請求，流程會停在 "Communicating"，進不到存檔。

### 確認內容還會發出的其它形態

不帶 ownerId、且體不是四位元組的 40040 信封：

    elementId 20000, no owner, 2 bytes   0000   then   0100
    elementId 1,     no owner, 4 bytes   00000000        after a syncCommand{data:0}
    no elementId,    no owner, 4 bytes   00000000  then  01000000

該對的接收函式 `0x006d6490` 丟棄兩位元組的那些（`cmp x2,#4`）；它們就是共享值（[相位就是元素的欄位](#the-phase-is-the-elements-field)）。

## 聯盟卡

交換結束後，每臺遊戲主機都會詢問是否保留對方的聯盟卡，即其快照 0x924 處的 TrainerCard（[協議](swsh_protocol.md#the-party-payload-on-protocol-0x84)）；該回答不傳送任何內容。

回答 "Oui" 時會把它原樣存入存檔塊 `0x28e707f5`：自 `album+0x230` 起 300 個 0x1d0 大小的槽位，`+0x1c8` 非零即表示還有空位（`0x013fbab0` 填入第一個空位；`0x013fbc00` 在全部用滿時返回 1）。

`0x013fbc40(album, card)` 在某個已用槽位匹配卡上 0x1C 處的 u32 與 0x1A8 處的八個位元組時跳過提問。0x1C 是 PKHeX 的 `TrainerCard8.TrainerID`，即 `(SID << 16 | TID) mod 10**6`；0x1A8 是 `TimestampPrinted`，一個 Unix 時間。對一臺模擬的盾而言，訓練家 id 改變或 0x1A8 處某個位元組改變會再次提問並存進第二個槽位；圖鑑數量或名字改變則不會。`pokeldn.swsh.league_card` 負責對映一個 u32；`trade_payload.rewrite` 設定訓練家 id。

零售版劍會繪製收到日期、`game`（0x24）的 Logo、0x39 處的三個 ASCII 位元組、`dex_complete`（0x30）為真時的洛托姆圖鑑王冠，以及七個星格中的 `count + 1` 個，其中 `count = card[0x177] + (card[0x1b6] != 0) + (card[0x1b7] != 0)`。構建函式 `0x0158eef0` 從存檔填入 0x177（`DesignLevel`：帶 `FSYS_GAME_CLEAR` 時為 4，否則按徽章數 > 6、> 3、> 0、0 分別為 3、2、1、0）、0x1B1（`FSYS_SEED_CHALLENGE`）、0x1B3（`FSYS_INPUT_SHIRT_NUMBER`）以及 0x1B6、0x1B7 處的星（`FSYS_R1_GAME_CLEAR`、`FSYS_R2_GAME_CLEAR`）；標誌鍵是名稱的 FNV-1a 64（[協議](swsh_protocol.md#the-player-profile)）。

`0x0158f5e0` 會拒收某些卡（DesignLevel 5、language 6、GlossIndex 9），改以預設卡替代。`bin/swsh_host.py --card-set FIELD=VALUE` 可編輯送出的卡（`pokeldn.swsh.league_card` 的欄位）；換一個新的 `trainer_id` 會讓遊戲主機重新提問。

## 提供的記錄

20030 上的提供就是快照中的隊伍槽位 `--offer-slot`，就地編輯，因此顯示的隊伍與提供的內容一致；身份改寫先執行，`party_matches_trainer` 成立。`pokeldn.swsh.pokemon.build_from` 重寫校驗和，按新的加密常量重排，並保留每個未命名的位元組。構建出的皮卡丘換給零售版劍再換回來，等級、性格、特性、性別、球種、攜帶道具、個體值與努力值都不變，並通過 PKHeX 的合法性檢查。

法版劍 1.3.2 在四次交換中都接受了其存檔已持有的記錄（PID 與 EC 相同）。盾 1.3.2 在所讀路徑上沒有重複檢查：PID 與加密常量的取值函式不會走到盒遍歷，盒程式碼只讀物種與蛋標誌。晶燦鑽石在 PK8 位元組 0x52 處的非法標誌沒有任何訪問器讀取（[BDSP 交換頁](bdsp_trade.md#duplicate-detection)）。`bin/swsh_host.py` 與 `bin/swsh_connect.py` 的 `--fresh-pid` 會抽取新的加密常量與 PID。

    --offer-slot 1 --offer-nickname POKELDN --offer-ivs 31,31,31,31,31,31

| 標誌 | 作用 |
|---|---|
| `--offer-nickname`、`--offer-ot` | 26 位元組的 UTF-16 欄位，至多 12 個字元；設了暱稱就置上已起暱稱標誌，否則取物種名 |
| `--offer-species` | 只寫物種字；其餘保持模板的值 |
| `--offer-ability ID`、`--offer-moves A,B,C,D` | 這兩個欄位；PP 與再學習招式保持不變 |
| `--offer-level N` | 0x148 處的等級位元組 |
| `--offer-experience N` | 0x10 處的經驗字 |
| `--offer-ivs` | 六項個體值 |
| `--offer-file FILE` | 四種形態之一的 `.pk8`（儲存或隊伍、加密或 PKHeX 的解密匯出，按首部校驗和區分）；OT 名與 id 改為快照中的訓練家 |
| `--offer-file-as-is` | 保留檔案自帶的 OT |
| `--save-offer FILE` | 在觸碰無線之前先寫出構建好的記錄 |

法版劍 1.3.2 不校驗特性或招式與物種是否匹配，等級取自經驗字（0x10），能力值由個體值、努力值、性格與極限特訓（0x126）重算，初訓家 id 顯示為 `(SID << 16 | TID) mod 1000000`，不與 MyStatus 比對任何初訓家 id，並把 PID 高半部分滿足 `low ^ TID ^ SID` 的顯示為異色。無資料的物種（152）以皮卡丘的模型、黑色的精靈球圖示與全零的種族值存入。

未解決：其它不存在的物種會繪製成什麼，以及名字取的是名稱欄位還是查詢失敗的結果。

## 一次完整交換的命令列

`swsh_connect.py --preset trade` 攜帶一場交換所需的標誌；其後給出的標誌會覆蓋該預設。在遊戲主機上按本地連線交換的方式搜尋（Y-Comm → 連線交換 → 本地，兩條提示都按 A）：

    POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/swsh_connect.py --keys PROD_KEYS \
        --preset trade --save-offered offered.pk8 --capture trade.jsonl

回發的快照是同一會話中游戲主機自己的那份（`--send-snapshot live`，即預設的預設值）：三個 0x84 分片被重組，訓練家名字、TID 與 SID 被改寫為 `--snapshot-name/-tid/-sid`，並在遊戲主機的快照重組完成之後發出。`--send-snapshot FILE` 改為傳送一份儲存好的 3456 位元組載荷（先 `--preset capture`，再用 `tools/switch/swsh_snapshot.py` 寫出一份）。

`--offer-file FILE` 把一個 `.pk8` 放進提供的隊伍槽位。重複給出時，它在會話上為每場交換排隊一條記錄；最後一條用於之後每一場交換，配合 `--fresh-pid` 時換用新的 PID，第 N 場交換會以 `-N` 字尾寫出 `--save-offered`。遊戲主機已提供、但確認階梯尚未走完的交換，會把會話在 `--hold` 之後再多留至多 `--grace` 秒（300）。任一啟動器上的 `--hold-after-trade SECONDS` 會在最後一場排隊交換結束那麼久之後終止執行（[離開](swsh_session.md#leaving)）。儲存格式、不帶隊伍能力值的記錄也能用於交換；遊戲主機會由經驗算出等級。

## 懲罰，以及乾淨地結束一次執行

鏈路仍在而交換超時，會被記為一次失敗的交換，並禁止遊戲主機再交換（`msg_ui_live_comm_app_alert_00`，`/bin/message/French/common/live_comm.dat` 第 331 行）；該禁令持續多久尚未讀出。在 `04000400` 之後 15 s、存檔進行中切斷鏈路，會顯示通訊錯誤 `2-ALZAA-0016`，不觸發交換禁令，並立刻開始新的本地搜尋。

`bin/swsh_connect.py --abort-on-stall SECONDS` 在確認階梯開始後、連續 SECONDS 秒沒有新體時切斷鏈路。它在相位 4——靜默拆除的那一級——就停手（`stall_abort()`、`final_phase_seen`、`LADDER_FINAL_PHASE`），因此存檔期間絕不會切斷鏈路。

## 驗證一次完成的交換

收到的寶可夢在 0xC4 處帶 `CurrentHandler` 1，0xA8 處的 `HandlingTrainerName` 是接收方的名字，覆蓋傳送方的初訓家。`--offer-echo` 會把遊戲主機自己的記錄原樣送回，因此只有物種不同才能證明真的發生了轉移。
