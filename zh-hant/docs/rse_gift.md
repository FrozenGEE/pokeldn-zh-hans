---
title: 綠寶石 神秘禮物
parent: 紅寶石、藍寶石與綠寶石
nav_order: 2
nav_exclude: true
search_exclude: true
---

# 綠寶石的神秘禮物

綠寶石的神秘禮物就是火紅那一套（見[神秘禮物](frlg_gift.md)），只是數字換成綠寶石的。啟動器是 `bin/frlg_mg_host.py --version emerald`。

## 選單入口

只要 `FLAG_SYS_MYSTERY_GIFT_ENABLE`（`0x8DB`）被設定，標題選單就會列出 MYSTERY GIFT。玩家持有圖鑑後，在友好商店櫃檯做那份問卷並選 LINK TOGETHER WITH ALL 就能設定它 [questionnaire.inc:30-37; easy_chat.c:693]。之後的路徑是神秘禮物 → 神秘卡片 → 好友。

## 協議

傳輸方式、指令碼、332 位元組的 `WonderCard`、444 位元組的 `WonderNews` 和 `MysteryGiftSave`（`0x36C`）都是火紅的。神秘卡片時 GameData 的 `+0x0C` 與 `+0x10` 分別帶 4 和 `0x200`，神秘新聞時帶 5 和 `0x201`，而火紅髮的是 1 和它自己的版本碼 [mystery_gift.c:346-363]；綠寶石的校驗在卡片時要第 2 位和 `0x380` [mystery_gift.c:390]。主持端按主機遊戲代號所指的那款遊戲的規則來處理。綠寶石的欄位操作碼只在 `0xC7..0xCC`、`0xD0`、`0xD3..0xD5` 處不同，一直到 `0xE3`。

| | 火紅 / 葉綠 | 綠寶石 |
|---|---|---|
| 卡片 flagId 1000（`sReceivedGiftFlags[0]`） | `0x2A7` | `0x13A` |
| `FLAG_MYSTERY_GIFT_DONE` | `0x3D8` | `0x1E4` |
| 禮物游標變數 | `0x40B6..0x40BC` | `0x40DE..0x40E4` |
| 最後一個道具 | 374 | 376（`ITEM_OLD_SEA_MAP`） |
| `StartLegendaryBattle` / `GetMysteryGiftCardStat` | 312 / 390 | 314 / 392 |
| `special` 索引檢查 | 由 `gSpecialsEnd` 限定 [scrcmd.c:101] | 無：527 個 special [scrcmd.c:119] |
| SaveBlock1 裡的 RamScript | `0x361C` | `0x3728` |

`gift_composer` 接受一張 `GameRules` 表；`pokeldn.rse.constants.EMERALD_RULES` 按綠寶石的數字編譯。遇到別款遊戲的主機，主持端會在傳送前拒絕。綠寶石的神秘新聞沒有獎勵。

在模擬主機上，[Switch 版構建](rse_switch_build.md) 會出現在好友搜尋裡並顯示為 POKELDN，表明自己是未持卡的綠寶石，隨後接收古代海圖卡片並正常關閉 LDN；之後寶可夢中心 2 樓的配送員會按存檔裡的指令碼交出 OLD SEA MAP。

## 禮物

`pokeldn.rse.gifts` 用 pokeldn 的文案逐條重建 pokeemerald 的四個官方禮物指令碼（`tests/test_rse.py` 比對位元組碼）。寶可夢中心 2 樓的神秘禮物員會執行存檔裡的指令碼。

| 預設 | 卡片 flagId | 作用 |
|---|---|---|
| 極光船票 | 1000 | 船票與 `FLAG_ENABLE_SHIP_BIRTH_ISLAND` |
| 神秘船票 | 1001 | 船票與 `FLAG_ENABLE_SHIP_NAVEL_ROCK` |
| 古代海圖 | 1002 | 海圖與 `FLAG_ENABLE_SHIP_FARAWAY_ISLAND` |
| 變化洞窟傳聞 | 1003 | 切換到洞窟九張野生表裡的下一張 |
| 無限船票 | 1007 | 遊戲自帶的發放 [cable_club.inc:33]：船票與 `FLAG_ENABLE_SHIP_SOUTHERN_ISLAND` |
| 大師球、神奇糖果 ×5、會衝浪的皮丘蛋 | 1004..1006 | 在 `EMERALD_RULES` 下合成 |

    POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live --version emerald \
        --gift-file old-sea-map.pokegift --keys "$HOME/Documents/Switch/23.0.0 keys/prod.keys"

預設可以用 `pokeldn.gifts.save(PATH, pokeldn.rse.gift_builder.compile(PRESET[key].state))` 存成檔案。綠寶石的禮物檔案只有一個變體 `emerald`（見[神秘禮物檔案](gifts.md)）。原生程式碼、存檔備份和火紅的預設對綠寶石一律拒絕。

## 尚未解決

- 日版綠寶石的神秘禮物活動與卡片大小。
- Switch 版是否保留選單入口。
