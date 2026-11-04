---
title: 火紅與葉綠
nav_order: 4
has_children: true
---

# 火紅與葉綠

火紅與葉綠在 Switch 上的發行版是運行於模擬器中的原版 GBA ROM，其上疊加了兩層連線：

| 層 | 歸屬 | 記載於 |
|---|---|---|
| LDN 與 Pia | 模擬器的，與所有 Switch 遊戲共用 | [無線層](ldn.md) |
| GBA 連線：RFU 幀、席位、塊傳送 | ROM 的 | 本組頁面 |

`REVISION >= 0xA` 的 [pret/pokefirered](https://github.com/pret/pokefirered) 是遊戲層協議的權威依據。法版卡帶報告的軟體版本為 `0x0A`，遊戲程式碼為 `BPRF`（火紅）和 `BPGF`（葉綠）。主機還攜帶了英語、德語、義大利語、西班牙語和日語各語言對的 ROM 與 RAM 地址，合計十二張卡帶；玩家在好友列表中選擇 pokeldn 後，神秘禮物會依據遊戲程式碼從中挑選一張。覆蓋情況見[零售驗證](frlg_rom_map.md#retail-verification)與[卡帶對映](frlg_rom_map.md#the-international-revision-0x0a-cartridges)。

一臺在關聯後約三秒（此時 Pia 會話已完成）就離開的遊戲主機，收到的是不含 6、9、12 Mbit/s 的關聯響應（[frlg_link.md](frlg_link.md)，廣播的速率集）。缺少 Pia 型別 2 的 Join Response 會出現相同症狀。

## 可用功能

在零售硬體上、兩張卡帶上，主機都能提供雙向的神秘禮物、作為主機方與加入方的交換、帶完整連線對戰的聯盟室、神奇新聞、電纜俱樂部競技場，以及一位來訪的對戰塔訓練家。

遊戲主機通過禮物鏈路的兩個直譯器執行傳送給它的程式碼：讀寫記憶體、把 ROM 按構建對映為具名函式、以八個引數呼叫其函式，以及讓主機選定的寶可夢經其自身的 `CreateMon` 生成並放入隊伍。隨機數生成器可被端到端預測；一次瞄準的閃光遭遇每次嘗試只需按一次 A。

訪客與封裝層之間的介面見[遊戲主機上的程式碼](frlg_rom.md#coverage)，封裝層的掃描流水線到其第一階段為止的部分見[封裝層自己的掃描流水線](frlg_rom.md#the-wrappers-own-scan-pipeline)。

## 頁面

| 頁面 | 內容 |
|---|---|
| [連線協議](frlg_link.md) | RFU 鏈路層、席位屏障、聯盟室、聊天、連線對戰、電纜俱樂部競技場 |
| [神秘禮物](frlg_gift.md) | 禮物會話、創作禮物、神奇新聞、來訪訓練家、被封鎖的無線通訊路徑 |
| [遊戲主機上的程式碼](frlg_rom.md) | 神秘事件 VM、原生 ARM 載荷、即時存檔 |
| [ROM 對映](frlg_rom_map.md) | 地址來源、四張函式表、物種表、法語 Easy Chat 詞表 |
| [隨機數生成器](frlg_rng.md) | 讀取與預測 `gRngValue`、用於瞄準遭遇的場地樁函式 |
| [葉綠](frlg_leafgreen.md) | 到火紅的偏移對映、作為測量工具的英文構建 |
| [主機實現](frlg_host.md) | 交換與神秘禮物主機的各個元件 |

## 規則

- 葉綠以分段常量偏移運行同一份程式碼（[葉綠](frlg_leafgreen.md)）。絕不要跨未加括號的區段預測地址。
- 反編譯產物的連結順序是證據；其地址仍需在卡帶上實測。`pokeldn/frlg/rom/rom_map.py` 記錄了每個地址的獲取方式。
- 載荷在傳送前先在 unicorn 下離線執行（`buffer_script.emulate`、`emulate_repeating`，兩者都是模擬的遊戲主機）。出錯或永不返回 1 的載荷會卡住神秘禮物選單；無限迴圈的場地樁函式會凍結大地圖。
