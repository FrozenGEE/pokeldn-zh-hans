---
title: 主持端實現
parent: 火紅與葉綠
nav_order: 7
---

# 主持端實現

`bin/frlg_trade_host.py` 是火紅/葉綠的直連角主持人：一臺 Switch 加入主持端開的 LDN 網路，Pia 建立對等會話，再由 Reliable 承載一條模擬的父端 RFU 鏈路，終點是主持人一側的交換狀態機。`bin/frlg_mg_host.py` 複用了活動層以下的全部內容。

## 元件與職責

| 元件 | 負責 |
|---|---|
| `TradeRunConfig` | 不可變的執行配置：`TrainerProfile`、`TradePlan`、`LdnConfig`、`HostOptions` 或 `JoinerOptions` |
| `HostApplication` | 資源順序：校驗、啟動傳輸、廣播信標、事件迴圈、中斷、清理；活動鉤子只提供訊息與持久化，所以交換與神秘禮物共用同一個迴圈 |
| `HostTransport` | LDN 熱點、虛擬網絡卡、參與者事件、UDP :12345；不解析 Pia |
| `HostPeerProtocol` | 單個對端的 Pia 狀態：Net、Session 接受、RTT、包 id、nonce 選擇、加密、封幀、Reliable 分批；產出 `OutboundDatagram` |
| `HostSession` | Reliable + `RFULeader` + 活動引擎（`engine=` 選交換或神秘禮物）；不碰套接字，離線端到端測試用的就是這一層 |
| `HostTradeEngine` | 主持人進房、隊伍與卡片交換、選擇、確認、動畫與存檔屏障、取消、退房、關閉寬限；`HostTradeTiming` 給出各處的幀數 |
| `BeaconInjector` | 它的原始監聽套接字與工作執行緒 |

資料包的流向是 Switch → `HostTransport` → `HostPeerProtocol` → `HostSession` → `RFULeader` → `HostTradeEngine`（子程序命令列進、父程序命令列出），然後再反向回到 Switch。定時截止時間由對端協議給出，所以 Net/Session 重試、RTT 探測、重傳和約 59.727 Hz 的節拍都不依賴輪詢延時。

## 啟動與建立會話

1. CLI 把 `TradeRunConfig` 交給 `HostApplication`，後者啟動一個未啟用的直連角網路和週期性信標。
2. Switch 加入；`on_participant_joined()` 傳送 Pia Net 連線請求，未收到 ACK 就一直重試。
3. Switch 回覆 Net ACK 併發起 Session 加入請求；主持端發出一個 Session 更新和一條單播加入響應（有個診斷開關能把這兩條的先後反過來），Switch 再確認。
4. RTT 與 Reliable/RFU 流量開始跑，應用資料屬性被置為有效。

畸形的 Pia 包、填充錯誤、認證失敗、Reliable 拼接不完整、Session 身份不符，都只記日誌並丟棄。只有當常量 id、Pia 變數、來源 IP 和加密頭都與當前 LDN 對端吻合時，Session 請求才會被接受。

## 交換與退房過程

```mermaid
stateDiagram-v2
    [*] --> PlayerExchange
    PlayerExchange --> RoomEntry: LinkPlayer and trainer card
    RoomEntry --> PartyExchange: seat route and entry barriers
    PartyExchange --> Selection: party, mail, ribbons
    Selection --> Confirmation: Switch selects; leader offers configured slot
    Confirmation --> Animation: both confirm
    Animation --> Save: trade committed
    Save --> PartyExchange: another configured trade
    Save --> MenuExit: final party refresh
    MenuExit --> RoomExit: both cancel; five-second field wait
    RoomExit --> CloseGrace: Switch confirms room exit
    CloseGrace --> Disconnect: fifteen seconds of peer traffic
    Disconnect --> [*]
```

最後一筆交換完成後，主持端等 Switch 開啟交換選單；玩家選 CANCEL 再確認 YES，主持端立刻回 `BOTH_CANCEL_TRADE`。主持端走完待機屏障，等五秒再離開房間（Switch 先走的話就不用等），並在 Switch 確認關閉（`READY_CLOSE_LINK`）之後繼續維持正常對端流量十五秒，然後排入 RFU 斷開。對主機發來的 Session 離開請求，它用型別 4 回應（見 [frlg_link.md](frlg_link.md) 裡「離開 Pia 會話」一節）。收到 LDN 離開事件會立刻停止對端輸出。

只有雙方都選 CANCEL，房間才會結束 [trade.c:1716]，所以主持端發什麼都無法把主機踢出房間。用 `--hold-after-trade N` 時，`bin/frlg_trade_host.py` 和 `bin/frlg_trade_join.py` 會在最後一筆排隊的交換之後再等 N 秒，如果那時主機的玩家還沒取消，就走與 Ctrl-C 相同的拆解流程強行關閉鏈路；主機隨後顯示無線鏈路錯誤，按 A 會帶著重新載入的存檔回到櫃檯 [link.c:1540-1560]。那些交換已經在存檔裡了。

## 關閉與清理

斷開之後，如果收到過寶可夢，主持端會先儲存它，然後等信標執行緒結束、關閉套接字與網路、移除 LDN 虛擬網絡卡。正常完成、`KeyboardInterrupt`、啟動中途失敗、信標執行緒崩潰，走的都是同一套清理。

所有主持端——交換、對戰、神秘禮物都一樣——在主機離開 LDN 時停止（`HostApplication.run`）：沒有確認過關閉就立刻停，確認過則等 2 秒穩定期（`HOST_CLOSE_SETTLE_SECONDS`）。`--end-on-success` 讓神秘禮物主持端在一次成功投遞的斷開發出後立刻停止，不等主機離開；它的 `--idle-timeout` 則在連續若干秒沒有 Switch 流量後停止。

## 訓練家資料的傳遞

`pokeldn.config.DEFAULT_TRAINER` 是預設身份。每個 CLI 都從 `--ot`、`--version`、十進位制的 `--id TID[:SID]` 推出本次執行專屬的不可變 `TrainerProfile`，校驗第三世代的名字與取值範圍，然後從它派生出每一處展示：

| 展示位置 | 攜帶內容 |
|---|---|
| LDN 發現 | 名字與公開的 TID |
| Pia Session | UTF-8 參與者名 |
| LinkPlayer | `SID << 16 \| TID`、版本、語言、性別與進度標誌；第三世代名字 |
| 訓練家卡 | 第三世代名字；主持端用 `0xFF` 填充，加入方保留原生 `0x00` |

## 失敗處理

- 預檢會拒絕不支援熱點模式的無線網絡卡。
- 在 Linux 無線網絡卡上，LDN 認證之後熱點必須把該站點標記為 `NL80211_STA_FLAG_AUTHORIZED`。驅動配置與標誌見[介面卡](hardware_adapters.md)。
- 傳輸層或信標執行緒出錯會中止本次執行，並把已建立的東西全部回收。
- 參與者意外離開會立刻停止輸出。那十五秒寬限只有在參與者仍線上時才會走完。
- 寬限（`HostTradeTiming.post_client_close_grace_frames`）只在 RFU 主持人處於 UNI 狀態時計時；主機發來的 `D` 會把它切到 DISCONNECTED（`pokeldn/gba/rfu_leader.py`），引擎隨即停止走幀。在 13 次正版火紅主持交換中，主機都在發出第一個 `READY_CLOSE_LINK` 之後 0.1 秒發 `D`，並在其後 0.5 到 4.0 秒離開 LDN，所以正常關閉時寬限根本不會生效。
- 只有完整收到的寶可夢才會被寫出；輸入的 `.pk3`/`.ek3` 檔案永遠不被修改。

## 擴充套件主持端

把新行為加在最懂它的那一層：設定放進執行配置，作業系統與網路的事放進應用或傳輸層，Pia 的事放進 `HostPeerProtocol`，RFU 的事放進 `RFULeader`，直連角的判定放進 `HostTradeEngine`。每一層都用它自己產出的資料包、負載、幀或命令列來測。

主持端只服務一臺 Switch。要多接幾個對端，就得給每個對端配一個 `HostPeerProtocol`（各自的 Pia 變數、nonce、包 id），再加一套遊戲層的 RFU 策略；只提高 LDN 的參與者上限是不夠的。

## 原始碼地圖

| 原始碼 | 職責 |
|---|---|
| `bin/frlg_trade_host.py` | CLI、配置、入口 |
| `pokeldn/frlg/host_cli.py` | 共用的主持端 CLI 選項 |
| `pokeldn/frlg/link/host_app.py` | `HostApplication` |
| `pokeldn/frlg/config.py` | 訓練家、交換計劃、神秘禮物負載、LDN、角色與執行配置 |
| `pokeldn/frlg/link/trade_runtime.py` | CLI 日誌、隊伍載入、槽位解析、輸出儲存 |
| `pokeldn/frlg/link/host_beacon.py` | 抓包得到的交換信標、發現資訊改寫、`BeaconInjector` |
| `pokeldn/host_support.py` | 面向作業系統的支援（能識別 sudo 的金鑰路徑解析） |
| `pokeldn/ldn/transport.py` | `HostTransport` |
| `pokeldn/ldn/host_pia.py` | Pia 封幀、`HostPeerProtocol` |
| `pokeldn/frlg/link/host_session.py` | `HostSession` |
| `pokeldn/ldn/reliable.py` | Reliable |
| `pokeldn/gba/rfu_leader.py` | `RFULeader`：父端封幀、NI/UNI 握手、回顯表 |
| `pokeldn/frlg/link/host_trade.py` | `HostTradeEngine`、`HostTradeTiming` |
| `pokeldn/frlg/link/linkplayer.py` | LinkPlayer 與訓練家卡編碼器 |
| `pokeldn/ldn/ldntrace.py` | 可選的 JSONL 診斷輸出 |
