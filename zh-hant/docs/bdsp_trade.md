---
title: 聯盟室交換
parent: 晶燦鑽石與明亮珍珠
nav_order: 3
---

# BDSP 的交換

一場 BDSP 聯盟室交換用五條訊息在兩個站點之間換一隻寶可夢，然後跑一個寫入存檔的安全階段。靠近與問候見
[遊戲協議](bdsp_protocol.md)。地址均為 1.3.0 的 `main`。

## 訊息序列

    NetDataTransitionData{transitionType: 18}     entering the trade
    NetDataTradeTranerData        32 B            who they are
    NetTradePokeData             328 B            the Pokemon
    NetDataTradePokeCheckOkData    1 B, value 1   "yours is fine"
    NetDataTradeReadyOkData        2 B            the last message before the exchange

每一條都用一個客戶端自己的對應訊息作答。主機的 check-ok 永遠是 1；它從不通過這條訊息拒絕一隻寶可夢。

在本地無線下，主機只按存檔的非法標記檢查玩家自己選的那隻（[重複檢測](#duplicate-detection)）。
`SS_box_182`（「Un problème avec votre Pokémon rend tout échange impossible.」）會拒絕被標記的選擇。
只有在 `UnionFrontDeskStateController.isGlobal` 被置位時才跑伺服器校驗：
`NetworkManager$$RequestValidateTrade` [0x02251cb0] 把每個 `CoreParam` 放進一條 0x148 位元組的請求裡
發出（`IlcaNetServerValidate.CheckRequestAutoAsync` [0x027318c0]）；回覆的 `ValidateResultID` 為
None、InvalidData、SignatureError 或 ProcessError，後兩種會彈出錯誤對話方塊。`SS_box_181` 拒絕對方
被標記的寶可夢。

## 交換狀態機

`UnionTradeManager.currentState`（+0x80）是
`TradeFlowState {NONE 0, SELECT_WINDOW 1, SECURIY_TRADE 2, PLAY_DEMO 3, END 4}`。只有在
SELECT_WINDOW 才會取走一隻寶可夢。ready-ok（0x21）在 SELECT_WINDOW 進入
`TradeSelectPokeModel$$ReciveReadyOk` [0x1c27d40]，在 SECURIY_TRADE 進入
`TradeSecurityController$$ReciveState`，其他狀態下一律丟棄。

當自己與對方的 `tradeState`（0x21 的第二個位元組）都為 2（`WAIT`）時，主機離開 SELECT_WINDOW，然後
傳送自己 `tradeState` 為 0 的 0x21。只有對方的 0x21 才能把它推出去。

### 交換盒階段，以及會重置一輪的訊息

`BoxWindow.NetTradePhase`：

    None 0, WaitSave 1, PlayerSelecting 2, WaitSend 3, OtherPokeConfirm 4, WaitOtherDecide 5,
    LastConfirm 6, WaitTrading 7, Complete 8, WaitClose 9, CancelOther 10, Error 11

重置（`TradeSelectPokeModel$$ReciveReturnSelectPoke` [0x1c27f00]）清空雙方的寶可夢和雙方的交換狀態；
從階段 3 起，交換盒回到階段 2 並顯示 `SS_box_588`（「L'autre joueur a choisi d'annuler l'échange.」）。
收到 `NetDataReturnSelectData{1}` 就用 `{0}` 作答。

| 對方發來的訊息 | 交換盒階段 | 主機做什麼 |
|---|---|---|
| check-ok（0x46） | 低於 6 | 記下對方的檢查 |
| check-ok（0x46） | 6 `LastConfirm` 或更後 | 執行重置 |
| ready-ok（0x21），SELECT_WINDOW | 階段 5 或更低 | 執行重置 |
| ready-ok（0x21），SELECT_WINDOW | 階段 6 或更後 | 記下對方的狀態；之後的副本被丟棄 |
| return-select（0x45），任一值 | 任意階段，PLAY_DEMO 之外 | 執行重置 |

這個閂鎖（+0x71，`<isLoadingBox>k__BackingField`；在 [0x1c342e4] 處清除，在 [0x1c3435c] 處置位）由
`Init`、`WaitBoxWindowComplete`、`Cancel`、`RecivePokeData` 和 `ReciveCancelData` 清除；它的 setter
[0x1c33040] 沒有呼叫者。重置把 `UnionWork` +0x50（`boxState`）設為 6 `CANCEL_SELECT` [0x1c28030]，
由 `BoxWindow$$UpdateNetworkTrade` [0x2121628] 消費 [0x2121c64]。

當玩家退出（`onCancelSelect`，`b__54_5` 0x1c28620；傳送在 [0x1c286a4]），主機會發出 `{1}` 並等待
一條新的 `NetTradePokeData`；對方的 `{0}` 不能把它放行。

- 每條主機的 check-ok 只應答一次；在 `LastConfirm` 之後才應答的副本會重置這一輪。接收方會丟棄已經
  投遞過的可靠 id（`pokeldn.ldn.reliable5.Reassembler`）。
- 用 `45 0001 00` 應答 `45 0001 01`。替換的寶可夢發出之後、或主機重新挑選之後，絕不要再發 0x45：
  它會把這一輪抹掉。
- 在選擇窗口裡，主機最後一次確認之前的 0x21 等於取消。要在主機可能回到選擇視窗之前停掉安全狀態
  重發器。

## 安全階段

`TradeStateModel` 掌管存檔：

    NONE 0, INIT 1, WAIT 2, SEND_POKE 3, WAIT_POKE 4,
    SEND_READYOK 5, WAIT_READYOK 6, START_WRITE_SAVE 7, WRITEING_SAVE 8

在這個階段，對方的寶可夢訊息只觸發下一步：主機用的是玩家在全屏介面上確認過的那隻寶可夢，而
WAIT_POKE 絕不會在那次確認之前結束。

### 誰主導：更稀有的那隻寶可夢

角色 PARENT 或 CHILD 在對方的寶可夢到達時確定（`TradeSecurityController$$CheckPokeRarity`
[0x1c25060]），依據每個物種的稀有度：

| 稀有度 | 物種 |
|---|---|
| 3 | 151、251、385、386、489、490、491、492、493（幻之寶可夢） |
| 2 | 150、249、250、382、383、384、483、484、487（封面傳說寶可夢） |
| 1 | 144、145、146、243、244、245、377-381、480、481、482、485、486、488 |
| 0 | 其他 |

`Dpr.SubContents.Utils$$GetPokeRarityNum` [0x1cbe560] 遍歷三個 `MonsNo[]` 列表（稀有度 3 在
0x1cbe614，2 在 0x1cbe698，1 在 0x1cbe71c，都沒有時 0x1cbe730），由 `Utils$$.cctor` [0x1cbe9a0] 從
`global-metadata.dat` 的 `0x666aa6`、`0x666b06`、`0x667c39` 填充（靜態欄位 +0x78、+0x80、+0x88）。
更稀有的一方是 PARENT；平手時招募者是 PARENT。拿帝牙盧卡去換一臺主機的夢幻，主機仍是 PARENT。

`TradeParentStateModel$$StateProc` [0x1c23350]，表 0x3d80f2f，與
`TradeSecurityController$$ReciveState` [0x1c24f10]，表 0x3d80f39，共同驅動它：

    2 WAIT            peer at WAIT                           -> 3
    3 SEND_POKE       send the Pokemon                       -> 4
    4 WAIT_POKE       peer Pokemon confirmed                 -> 5
    5 SEND_READYOK    PARENT sends its state; CHILD waits for a peer 5 or 6   -> 6
    6 WAIT_READYOK    one more peer message                  -> 7
    7 START_WRITE_SAVE, 8 WRITEING_SAVE

處於 SEND_READYOK 的 CHILD 主機會靜默等待，所以把 WAIT_POKE 原樣回顯的客戶端會把它卡死。
`room.mirror_trade_state` 用 SEND_READYOK 應答 WAIT_POKE，兩種角色下都可行
（`tests/test_bdsp_trade_states.py` 在隨機時延下對這兩個函式都做了建模）。

每個可靠序列 id 只發一條訊息：同一個 id 下的後續訊息看起來像重傳，會被丟棄。

## 完成的交換

主機的狀態，然後是客戶端的應答：

    their READY-OK {tradeState 2}  ->  the client's READY-OK
    INIT          ->  WAIT
    WAIT          ->  WAIT
    SEND_POKE     ->  SEND_POKE, and its Pokemon
    WAIT_POKE     ->  WAIT_POKE
    SEND_READYOK  ->  SEND_READYOK
    WAIT_READYOK  ->  SEND_READYOK

隨後主機寫入存檔、播放動畫，並且只發 `NetCharacterStateData`。客戶端每秒重複一次自己的狀態，但只到
主機的 SEND_READYOK 為止（`room.repeats_trade_state`）；此後的一條 0x21 會落進下一個選擇視窗並重置
這一輪。站點不能在這個窗口裡離開：掉線會讓主機停在 `FirstSave` 與 `SecondSave` 之間
（[斷線懲罰](#the-disconnect-penalty)）。

動畫在 `tradeState` 6 之後約 2.7 s 開始，收到的寶可夢在約 18.6 s 出現，玩家在約 29 s 重新獲得操作權。
完成的交換不發任何訊息就結束；下一輪從主機的下一條 `NetTradePokeData` 開始。兩種角色下交換都能在
一次關聯中接續。

## 寶可夢

`NetTradePokeData` 攜帶 328 位元組，是一個加密的 PB8，格式見[劍與盾頁](swsh_protocol.md#the-pk8)
（`pokeldn/gen8.py`、`pokeldn/bdsp/pokemon.py`）。0x06 處的校驗和無法發現區塊順序錯誤。

`NetDataTradeTranerData`（[分幀](bdsp_protocol.md#framing)）：

    0x00  26  tranerName, UTF-16LE, NUL-terminated
    0x1a   4  tranerId, the full 32-bit id, secret id in its high half
    0x1e   1  cassetVersion, the save's version (49)
    0x1f   1  langId, the save's language (3)

主機在任何寶可夢之前先發它；為接收玩家生成的禮物會讀它（`room.traner_trainer`，
[為接收玩家而生成](gift_simulated.md#made-for-the-receiving-player)）。它不帶性別。交換介面用它來
稱呼對方；問候用的是 Pia 玩家名（[協議頁](bdsp_protocol.md#the-name-in-the-greeting)）。名字終止符
之後的十個位元組是堆殘渣；`room.build_trade_traner` 照抄主機自己的那十個位元組。

提供的寶可夢是一隻真寶可夢，只是改動了具名欄位（`pokemon.build_from`）。

## 主機對收到的寶可夢做什麼

`TradeStateModel$$ReplacePoke` [0x1c29120] 把這隻寶可夢的初訓家性別、32 位 id 和初訓家名字與接收方
存檔比較（`CoreParam$$UpdateOwnerInfo` [0x2495920]）：

| 比較結果 | 效果 |
|---|---|
| 三者都相同 | 處理者標誌被清除；名字與物種名不同時置位 `IsNicknamed`（0x08F 的第 7 位） |
| 否則 | 按存檔設定處理者：名字 0x0A8、性別 0xC2、語言 0x0C3、`CurrentHandler` 0x0C4 = 1、親密度 0x0C8 = 物種基礎值、記憶欄位清零 |

隨後更新校驗和。`ot_name` 和 0xC6 不動。GTS、遊戲內交換和神秘禮物也用同樣的方式寫處理者。遊戲裡沒有
寶可夢 HOME 的程式碼。

### 重複檢測

`PokeDupeChecker`（1.3.0）會給重複的寶可夢打標記：解密後 PB8 第 0x52 位元組的第 0 位，即 PKHeX 的
`PB8.IsDprIllegal`。被標記的寶可夢不能交換，標記也永遠不會被清除。

這項檢查（`UpdateIllegalFlagAll` [`0x01de5860`]）按順序走一遍隊伍、1 到 40 號盒子以及寄放屋，在存檔
載入時和交換盒裡每次挑選時執行；收到交換時什麼也不跑。它覆蓋非蛋的、且不是遊戲內交換所得的晶燦鑽石
與明亮珍珠寶可夢。當以下各項都與更早的一隻相符時，較晚的那隻被標記：

| 欄位 | 取值函式 | PB8 偏移 |
|---|---|---|
| 加密常數 | `GetPersonalRnd` | 0x00 |
| PID | `GetColorRnd` | 0x1C |
| 訓練家 id（TID16、SID16） | `GetID` | 0x0C |
| 性格 | `GetSeikaku` | 0x20 |
| 六項個體值 | `GetTalentHp` .. | 0x8C |

比較：`IsDuplicatedPokemonParam` [`0x01de62f0`]，對每隻寶可夢 `CheckDuplicate` [`0x01de59d0`]；遊戲內
交換判定 `IsLocalKoukanPokemonParam` [`0x01de66d0`]；極限特訓檢查
`UpdateIllegalSpecialTraining` [`0x01de6830`]；交換盒呼叫點 [`0x01c28310`]；置標函式
`CoreDataBlockA.set_dpr_illegal_flag` `0x027bb040`。

鐵面忍者（291）與脫殼忍者（292）這一對永遠不算重複。等級 99 或更低、且置了任何極限特訓位的 BDSP
寶可夢也會被標記。

永遠不要提供這樣一條 BDSP 記錄：它的加密常數、PID、訓練家 id、性格和個體值全都與接收方存檔裡的某隻
寶可夢相符。`bin/bdsp_host.py --fresh-pid` 會重新抽一個加密常數和 PID，異色狀態保留。

## 斷線懲罰

站點在 `FirstSave`（懲罰計數 30，並記錄時間）與 `SecondSave`（計數 0）之間掉線，會讓主機拒絕新的本地
交換，提示「vous ne pouvez pas faire d'echange en reseau pour le moment」
（`UnionFrontDeskStateController$$CheckPenarty` 0x1fcc400）。出現懲罰說明主機已經寫了存檔。

這個懲罰時鐘（`UnionWork$$CheckDateTime` [0x1dd3e30]、`SetPenartyTime` [0x1dd32d0]；`FirstSave`
0x1cd4fc0、`SecondSave` 0x1cd5030）是一個不加權的和，`Year + Month + Day + Hour + Minute + Second`，
一旦超過記錄的和 30 就解除。分鐘或小時進位時，這個和會下降 58，所以在某個小時末段觸發的懲罰可能持續
到第二天甚至更久。

不要為了解除它而改動主機的時鐘或系統設定：BDSP 能檢測到這種改動，並會鎖住基於時間的功能一天。把時鐘
往回調會讓懲罰回來；只有 `SecondSave` 才能把計數清零。
