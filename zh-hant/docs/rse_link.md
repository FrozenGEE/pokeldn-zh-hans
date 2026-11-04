---
title: 交換與聯盟室
parent: 紅寶石、藍寶石與綠寶石
nav_order: 1
nav_exclude: true
search_exclude: true
---

# 綠寶石的交換與聯盟室

綠寶石的無線鏈路就是火紅那一套（見[連線協議](frlg_link.md)）；本頁只列綠寶石的不同之處。啟動器是 `bin/frlg_trade_host.py` 與 `bin/frlg_trade_join.py`，加上 `--version emerald`。測量都是在模擬主機上跑 [Switch 版構建](rse_switch_build.md) 得到的。

## 加入主機

廣播記錄與 `RfuGameData` 沿用火紅的 [include/link_rfu.h:80-113]。對於版本不是 3 的主機，綠寶石會把它列為「未就緒」，除非玩家已是冠軍且該主機廣播了 `canLinkNationally` [union_room.c:1266-1283; trade.c:2514-2521]。`--version emerald`（或 `ruby`、`sapphire`）會廣播該版本，並按存檔裡的資料設定 `canLinkNationally`、`hasNationalDex` 和 `gameClear`（分別對應 `[16:20]` 那個字的第 16、17、24 位；`RfuGameData` 的第 7、8、9 位）。火紅與葉綠保持這些位為 0。

在 `FLAG_SYS_POKEDEX_GET`（`0x861`）被設定之前，寶可夢中心 2 樓的每位店員都會回答「正在調整中」[cable_club.inc:803, 885, 901, 1152]。

## 交換

鏈路同火紅（訓練家卡上的神秘卡片 id 在 `0x60`），有兩處差異：

- 沒有全國圖鑑時，綠寶石會拒絕夥伴送來的蛋或非豐緣地區的寶可夢 [trade.c:1584-1589]：交換介面顯示「對方 TRAINER 的 POKéMON 現在不能交換」，主機在按下 A 之後傳送 `READY_CANCEL_TRADE`。`LinkPlayer.progressFlags & 0xF` 報告圖鑑狀態。`pokeldn.rse.constants.HOENN_DEX` 儲存著這 202 個條目，主持端會記錄被拒的報價。
- 綠寶石在交換後跑五輪待機 [trade.c:4686-4797]；Switch 版火紅跑六輪，最後一輪之後跟 `svc_FinishSave`。Switch 版構建保持五輪：主機發出 5 到 9 的 `READY_EXIT_STANDBY`，然後在「通訊等待」上等一個期待第六輪的主機。`--version emerald` 讓主持端跑五輪；`--save-rounds N` 可以覆蓋。

版本為 3 時，綠寶石在 `0x3A` 畫出帶開拓區符號的主持端訓練家卡，對戰點數在 `0x3C`。它的接收佇列有 32 個槽位（火紅是 20），除 `0x0002` 和 `0x7F7D` 之外也接受序列值 `0x0000`。

在模擬主機上，Switch 版構建能與主持端完成一次直連角交換：LinkPlayer、訓練家卡、座位路由、隊伍、郵件與緞帶塊、互換、五輪待機、`READY_CLOSE_LINK`、RFU 斷開幀和 Pia 離開，最後把存檔寫進模擬器的儲存。

## 聯盟室

房間、活動選單和交換板的行為與火紅相同（見[聯盟室](frlg_link.md#the-union-room)）。`--union-room --union-room-keepalive 120` 會生成 POKELDN 的頭像，主機裡的玩家與它對話後建立連線。與 POKELDN 對話會顯示 GREETINGS、BATTLE、CHAT 和 EXIT；綠寶石在這個選單裡不提供交換。

| 活動 | 引數 | 在模擬主機上的實測 |
|---|---|---|
| GREETINGS | `--union-room` | 雙方訓練家卡、待機屏障、返回房間 |
| EXIT | `--union-room` | `READY_CLOSE_LINK` 與正常斷開 |
| 交換板 | `--union-room --board-type TYPE` | 主機選中 POKELDN 的掛單，寶可夢與郵件塊交叉，交換與存檔完成，鏈路關閉 |
| CHAT | `--union-room-chat` | 未測 |
| BATTLE | `--union-room-battle` | 未測 |

主持端只為從 POKELDN 的掛單發起的交換板交易提供服務；它不會反過來向主機自己的掛單發起請求。`--board-type` 指定主持端回禮時所要求的屬性，主機只會拿出該屬性的寶可夢。

用 `--union-room-keepalive 600` 時，雙方訓練家卡塊交換完成後主機停在「正在與 POKELDN 通訊…」上，始終不顯示選單；120 就能正常進入。

## 尚未解決

- Switch 版綠寶石在交換後的待機輪數。
- 與綠寶石的聯盟室聊天與對戰。
