---
title: 劍與盾
nav_order: 6
has_children: true
---

# 劍與盾

《寶可夢 劍／盾》在直接運行於 Pia 之上的釋出/訂閱框架中交換協議緩衝區訊息。

靜態分析物件是盾 1.3.2 歐版映象（`01008db008c2c000`，更新 NCA，SDK 7.7.0.0）；實測針對一臺法版劍 1.3.2。兩者共用網路程式碼。

| 頁面 | 內容 |
|---|---|
| [卡帶與會話](swsh_session.md) | 金鑰、映象、Pia 4、到首條應用資料的關聯 |
| [同步框架](swsh_protocol.md) | 訊息 id、內容、持有者、路由、隊伍載荷 |
| [交換](swsh_trade.md) | 交換介面、盒狀態機、確認階梯 |
| [神秘禮物](swsh_gift.md) | 神秘禮物選單的本地無線分支 |
| [極巨團體戰](swsh_raid.md) | 巢穴大廳、其廣播、託管一場由一臺或多臺遊戲主機加入的團體戰、訪客所打的戰鬥、極巨大冒險、離開 |

## 出處

除非某一節指明瞭具體客戶端，否則 id、偏移和地址都來自盾的 `main` 或空口抓包。`pokeldn/swsh/trade.py` 中的 `SYNC_ANSWERS` 是 `andyjusa/nxldn-lab` 對一次遊戲主機之間抓包的解讀（訊息 97 和 60000 與 pokeldn 的逐位元組一致）。`kwsch/PokePiaSWSH`、`lincoln-lm/swsh-lan-client`、`andyjusa/nxldn-lab` 和 `Slashcash/PSD` 都從 Pia 站點握手開始實現 LAN 模式；沒有一個覆蓋 LDN 或主機遷移。

## 場地指令碼

`bin/script/amx/*.amx`（1.3.2 中有 953 個）是採用 64 位單元的 Pawn 3.x：magic 為 `0xF1E1`，版本 10，flags 為 `0x1C`（緊湊程式碼、sleep、無檢查）。緊湊編碼：每位元組 7 位，高位組在前，符號位於第一位元組的第 6 位。非分支的單引數操作碼也按 `(param << 32) | op` 打包，按 3.x 順序從 162 開始編號（`LOAD.pri` 162、`LOAD.S.pri` 164、`PUSH.C` 188、`PUSH.S` 190、`STACK` 191、`ADD.C` 197、`ZERO.S` 200、`EQ.C.pri` 201、`INC.S` 204、`HALT` 210、`PUSH.ADR` 212）；偏移 0 處的 `halt 0` 可據此確認。

一個 native 為十二位元組：`u64 0` 加一個 `u32` 名稱雜湊，由 `amx_Register`（`0x0066d970`）解析：

    h = 0; for each byte c: h = (h * 0x83) ^ c        (32-bit)

繫結表是 `.data` 中的 `(name, function)` 對，每個模組一張（取值函式如 `0x014aea00`）：777 個名稱，513 個雜湊中用到了 512 個。物品：`ItemAdd`（`0x014acea0`）、`ItemSub`（`0x014acf40`）、`ItemGetNum`、`ItemAddCheck`、`ItemGetCategory`、`GetPocketNumberFromItemNumber_`。變數：`WorkGet`/`WorkSet`（雜湊的 64 位鍵）、`TempWorkGet`/`TempWorkSet`（介面在指令碼恢復前填入的索引）。一次呼叫是對每個引數自右向左 `PUSH`，然後 `SYSREQ.N native, bytes`。

## 未解決

- [玩家檔案](swsh_protocol.md#the-player-profile)：在寶可夢露營會話中，樣本狀態 3 和 4 分別代表哪個角色（`StateCreateSession`、`StateConnect`）。把 `a_wr0301` 判為王冠雪原曠野地帶，只是從編號推斷出來的。
- [對戰競技場](swsh_protocol.md#the-battle-stadium-block)：`0x01430670` 讀取哪個存檔塊來取得已儲存的隊伍記錄；以及在 `v1/validate` 簽名替換 `+0x36` 之前，存檔隊伍的描述符在 `+0x30..+0x135` 處儲存什麼（即 `0x015039f0` 之後 `[sp+0x28]` 處的條目）。
- 劍與盾對照：二進位制分析物件是盾，遊戲主機是劍；[會話常量](swsh_session.md#taking-a-seat)在兩者之間通用。劍是否測試卡帶版本掩碼的第 0 位這一結論，是從盾的程式碼——其中該測試為 `1 << (v == 0x2D)`，且 `0x007d4270` 的 31 處呼叫點中有 11 處同時與 `0x2C` 和 `0x2D` 比較——以及從 PKHeX 的 `RestrictVersion`（1 劍，2 盾，3 兩者）推斷出來的；兩份零售劍快照在 MyStatus `+0xA4` 處帶有 `0x2C`。劍自身的 `0x007d4270` 及其通訊 id 字面量尚未讀取。
- [神秘禮物](swsh_gift.md#what-the-menu-refuses)：零售遊戲主機是否會和模擬的盾一樣，把物種不存在於遊戲中的 kind-1 禮物當作名為 "Egg" 的壞蛋接受；以及這樣的蛋在孵化時或交換中會怎樣。
