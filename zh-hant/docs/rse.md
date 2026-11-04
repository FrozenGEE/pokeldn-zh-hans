---
title: 紅寶石、藍寶石與綠寶石
nav_order: 11
has_children: true
nav_exclude: true
search_exclude: true
---

# 紅寶石、藍寶石與綠寶石

紅寶石、藍寶石與綠寶石沒有 Switch 版；pokeldn 對它們的支援是從
[pret/pokeemerald](https://github.com/pret/pokeemerald) 和 [pret/pokeruby](https://github.com/pret/pokeruby)
準備出來的，計劃與火紅、葉綠放在同一個 GBA 應用裡釋出。所有地址都取自 GBA 英文版。只有從原始碼倉庫執行時，應用才會顯示這個標題（見[未釋出的遊戲](gui.md#unreleased-titles)）。

為那個應用編譯的綠寶石會代替火紅的卡帶執行，並與 pokeldn 的主機對接（見 [Switch 版構建](rse_switch_build.md)）。在正式釋出之前，這幾頁講的都以那個構建為實驗物件。

| 頁面 | 主題 |
|---|---|
| [交換與聯盟室](rse_link.md) | 加入主機、連線交換、聯盟室 |
| [神秘禮物](rse_gift.md) | 協議差異、禮物、選單入口 |
| [Switch 版構建](rse_switch_build.md) | 給火紅應用用的綠寶石：移植、構建、執行、測試存檔 |

GBA 應用裡已經為全部五個第三世代遊戲代號準備了通關報告表，其中包括 `AXV?`、`AXP?` 和 `BPE?`（見[在主機上執行程式碼](frlg_rom.md)），而十二個火紅與葉綠標題共用同一個本地通訊 id `0x01006fa0233f8000`（見 [ROM 對映表](frlg_rom_map.md)）。

## 各遊戲在鏈路上能做什麼

| | 紅寶石 / 藍寶石 | 綠寶石 |
|---|---|---|
| 無線介面卡（RFU）程式碼 | 無：只有 SIO 多人線纜 | 火紅的 `link_rfu_2.c` |
| 連線交換 | 線纜 | 直連角與聯盟室，同火紅 |
| 神秘禮物（神秘卡片、神秘新聞） | 無 | 火紅的協議與結構體 |
| 神秘事件 | 通過線纜的 e-Reader，由「MYSTERY EVENT IS EXCITING」開啟 | 標題選單裡沒有 |

兩個啟動器說的是無線介面卡協議，所以只能連到綠寶石。鏈路之上，RS 的線纜協議共用 `LinkPlayer` 記錄、200、200、100、220、40 的塊大小、鏈路命令字和交換塊 [pokeruby link.c, trade.c]。RS 會在火紅與綠寶石讀作進度標誌的那些位元組上寫入一個 11 位元組的名字，所以面對 RS 夥伴時兩者都會把這些標誌清零。

## 識別符號

| 欄位 | 紅寶石 | 藍寶石 | 綠寶石 |
|---|---|---|---|
| 遊戲代號 | `AXV` + 語言 | `AXP` + 語言 | `BPE` + 語言 |
| 頭部標題 | `POKEMON RUBY` | `POKEMON SAPP` | `POKEMON EMER` |
| `gGameVersion` | 2 | 1 | 3 |
| `LinkPlayer.version` | `0x4002` | `0x4001` | `0x4003` |

語言字母是 `E`、`F`、`D`、`I`、`S` 或 `J` [include/constants/global.h:8-12]。

## 存檔

快閃記憶體佈局、簽名 `0x08012025` 和校驗和都與火紅相同 [save.c]。SaveBlock1 為 `0x3D88` 位元組，SaveBlock2 為 `0xF2C` 位元組；扇區校驗和為 `0xF2C`、三次 `0xF80`、`0xF08`、八次 `0xF80`，按 id 分別是 `0x7D0` 位元組。隊伍數量 `0x234`，隊伍 `0x238`，金錢 `0x490`（與 SaveBlock2 的 `+0xAC` 異或），標誌 `0x1270`，變數 `0x139C`，遊戲統計 `0x159C`，神秘禮物 `0x322C`。SaveBlock2 沒有 `filler_B20`。

| 欄位 | 偏移 | |
|---|---|---|
| SaveBlock1 `continueGameWarp` | `0x0C` | `WarpData`：s8 組、s8 地圖、s8 傳送點 id、填充、s16 x、s16 y |
| SaveBlock2 `specialSaveWarpFlags` | `0x09` | 位 0 `CONTINUE_GAME_WARP`：CONTINUE 會傳送到 `continueGameWarp` [overworld.c:1739] |

沒有 `CONTINUE_GAME_WARP` 時，CONTINUE 會用 `pos` 和 `location` 恢復 SaveBlock1 的地圖視角與物件事件；只改 `pos` 和 `location` 的存檔編輯會載入舊地圖，並且玩家看不見。

## pokeldn 尚未實現的綠寶石鏈路功能

記錄混合、樹果攪拌機、華麗大賽、對戰塔的連線多人對戰、樹果粉碎、寶可夢跳繩與嘟嘟利採果（鏈路組 12 到 21，活動 14 與 23 到 29）。

## 尚未解決

- Switch 版是否存在，以及它的標題 id、遊戲代號和軟體版本。
- 它是否沿用火紅應用的通訊 id、場景 id 和廣播打包方式。
- Switch 版如何承載紅寶石與藍寶石的線纜鏈路。
- Switch 版綠寶石的所有 ROM 與 RAM 地址。
