---
title: 神秘禮物檔案
---
# 神秘禮物檔案

`.pokegift` 檔案儲存一份完整的、面向火紅/葉綠或劍/盾的神秘禮物分發內容，或一段 FRLG ARM 主機載荷，並附帶其目標遊戲與原生記錄。

## 桌面應用

同一個構建器服務於兩款遊戲（`pokeldn/app/gift_builder.py`；表單位於
`pokeldn/frlg/gift/builder.py`、`pokeldn/swsh/gift_builder.py`）。

| 模式 | 傳送的內容 |
|---|---|
| Use a preset | 內建禮物；FRLG 的神秘卡片、神秘新聞和主機程式碼以標誌形式傳給啟動器 |
| Official events | 真實的劍/盾活動卡片（[官方活動卡片](swsh_gift.md#official-event-cards)），像構建好的禮物一樣編譯 |
| Build your own | 表單，在 Start 時編譯為 `session/gifts/<tool>.pokegift` 並以 `--gift-file` 傳入 |
| Open a file | 分享的 `.pokegift`，或劍/盾上的 `.wc8` |

FRLG 的 Game boosts 是常駐鉤子（[`install-resident`](frlg_rom.md#install-resident)），作為一條鏈
（[同時使用多個鉤子](frlg_rom.md#several-hooks-at-once)）在 1024 位元組內執行；各項設定會變成
`--resident-param` 標誌。

| 強化 | 設定 | 引數 |
|---|---|---|
| 加速遊戲（`turbo-lite`） | 速度 x1 到 x4；大地圖、對戰或兩者；始終開啟，或按住 R、B 或 Select 時開啟；更快的文本 | `field` 和 `battle` = speed - 1，x3 起 `budget=228`，`hold`，`extra=4` |
| 穿牆 | R、B 或 Select | `hold` |
| 閃光倒計時 | 減速按鈕；慢 x2、x4 或 x8 | `slow`，`slow_frames` 1、3 或 7 |
| 閃光傳說寶可夢（`shiny-press`） | 超夢；急凍鳥、閃電鳥或火焰鳥 | `offset` 1 或 2 |
| 無野生遭遇、螢幕上顯示隊首的個體值、寶可夢跟隨者 | 無 | |

不提供 L：只有 R 的幫助系統開關帶有一個鉤子能壓住的標誌。Save boosts for later 會把這組強化寫入
`filler_B20`（`save-write --resident`）並安裝它；超過 876 位元組的強化組以及跟隨者，始終走存檔。
Mom restores your boosts 會讓與媽媽對話在任何一次啟動後安裝已儲存的強化組。再次傳送強化會替換正在
執行的那一組。

Read the save 提供訓練家 ID（TID）與裡 ID（SID）、訓練家詳情與遊戲時間，以及上次儲存的隊伍的性格、
個體值與努力值，並保持存檔不變（[讀取存檔](frlg_rom.md#reading-the-save)）。

`.wc3` 和 `.wc8` 檔案按二進位制讀取，即使它們以 `{` 開頭。當表單能夠表達某個預設時，Customize 會把它
複製進表單：所有劍/盾預設，以及僅由無條件表單步驟構成的 FRLG 卡片。

FRLG 表單構建神秘卡片、神秘新聞或主機程式碼。

| 部分 | 內容 |
|---|---|
| 卡片 | 標題、副標題、四行文本、圖示種類、卡片 id 1000 到 1019、可再次接收、可分享 |
| 交付者 | 任意寶可夢中心裡的配送員、玩家家中的媽媽，或真新鎮南邊的那個人 |
| 步驟 | 寶可夢（種類、等級、攜帶道具、四個招式）、道具與數量、蛋、野生對戰、訊息 |
| 新聞 | 標題、最多十行、新聞 id |
| 主機程式碼 | ARM 原始碼或預編譯的 `.bin`、它為其構建的卡帶、期望的應答、回傳的位元組 |

每個步驟是一個獨立的交付階段：隊伍或背包滿時就此停止，重試會給出剩下的部分。另一個人通過
`initramscript` 繫結持有這些步驟，這會隱藏卡片，並在被替換之前每次都給出這些步驟。種類使用內部編號
（`pokeldn/frlg/save/species_names.py`）。

主機程式碼需要 `arm-none-eabi-as`（PATH、Homebrew 或 Arm 的 Windows 資料夾），或預編譯的 `.bin`：

| 系統 | 命令 |
|---|---|
| macOS | `brew install arm-none-eabi-binutils` |
| Fedora | `sudo dnf install arm-none-eabi-binutils-cs` |
| Debian、Ubuntu 及其衍生版 | `sudo apt install binutils-arm-none-eabi` |
| Windows | `winget install Arm.ArmGnuToolchain` |

Check 會離線在模擬主機上執行這段程式碼（`pokeldn/frlg/rom/custom_code.py`），Start 和儲存時也是如此；
出錯或永不返回 1 的程式碼會被拒絕。

劍/盾表單構建一隻寶可夢（可選超極巨化）、一顆蛋、最多六件道具、服裝
（[服裝](swsh_gift.md#clothing)，每個性別六件）、對戰點數或金錢，佈局與
[零售版劍兌換的記錄](swsh_gift.md#a-card-delivered-to-a-retail-console)一致。

Save gift file 會寫入一個包含所有卡帶變體的 `.pokegift`，無需板子或金鑰。主機的遊戲程式碼會選擇變體；
檔案中沒有的卡帶會在傳送前被拒絕。

## 命令列

兩個禮物啟動器都接受 `--gift-file FILE`；在劍/盾上 `--record` 是它的別名。
`--export-gift FILE` 會儲存所選禮物並在使用無線之前退出。

```bash
./.venv/bin/python bin/frlg_mg_host.py --gift celebi --export-gift celebi.pokegift
./.venv/bin/python bin/frlg_mg_host.py --news berry --export-gift news.pokegift
./.venv/bin/python bin/swsh_gift_host.py --species 25 --level 25 --export-gift pikachu.pokegift
./.venv/bin/python -m pokeldn.gifts inspect celebi.pokegift
```

FRLG 禮物檔案會一併定義卡片標誌 ID、指令碼、問卷和拒絕訊息。諸如 `--flag-id`、`--questionnaire` 和
`--hunt-*` 之類的載荷覆蓋項會被它拒絕；無線、訓練家和卡帶選擇選項仍然生效。

### 主機程式碼

內建載荷會連同其應答設定一起匯出：

```bash
./.venv/bin/python bin/frlg_mg_host.py --buffer-script save-dump --dump-size 64 \
  --export-gift save-dump.pokegift
```

原始 ARM 程式碼會帶明確的卡帶目標打包：

```bash
arm-none-eabi-as -march=armv4t -mcpu=arm7tdmi -o payload.o payload.s
arm-none-eabi-objcopy -O binary -j .text payload.o payload.bin
./.venv/bin/python -m pokeldn.gifts import --game frlg --code payload.bin \
  --build BPRF --name "Custom payload" --expect 66 -o custom.pokegift
```

一個最小的 `payload.s` 會把 66 寫入應答引數，並在一次呼叫中完成：

```asm
.syntax unified
.arm
.text
.global _start
_start:
    mov r3, #66
    str r3, [r0]
    mov r0, #1
    bx lr
```

程式碼是與位置無關的 ARMv4T，字對齊，最多 1024 位元組，每幀呼叫一次，呼叫時 `r0 = &param`、
`r1 = gSaveBlock2Ptr`、`r2 = gSaveBlock1Ptr`，直到它返回 1（[主機程式碼](frlg_rom.md)）。沒有
`--expect` 時接受任何應答；位元組緩衝區應答需要 `--dump-size N`。

接收方在 FRLG 神秘禮物工具中開啟該檔案，或傳入 `--gift-file`；`--dump-file PATH` 選擇返回的轉儲寫到
哪裡。打包只檢查結構和大小：在實機執行之前，用 `buffer_script.emulate_repeating` 離線執行新的載荷。

### 原生格式

轉換器可匯入 WC8、FRLG `.wc3` 以及 `pokemon-gen3-mysterygift-tool` 的卡片/指令碼對；`.wc3` 和 `.wc8`
也可以直接開啟。

不含絕對地址的 FRLG 指令碼（只有相對 `setvaddress` 的 `vgoto`/`vmessage` [scrcmd.c:171]，道具通過
`callstd`）可服務於其佈局下的每一張卡帶。含有 `goto`、`call`、`message`、`callnative` 或其他絕對指標的
指令碼需要 `--build`，直接開啟時會被拒絕。

```bash
./.venv/bin/python -m pokeldn.gifts import --game swsh --record event.wc8 -o event.pokegift
./.venv/bin/python -m pokeldn.gifts import --game frlg --wc3 "FL - Item AuroraTicket (FRE).wc3" -o aurora.pokegift
./.venv/bin/python -m pokeldn.gifts import --game frlg --card WonderCard.bin \
  --script Script.bin --name "Event gift" -o event.pokegift
./.venv/bin/python -m pokeldn.gifts export celebi.pokegift --build BPRF --out-dir native-gift
./.venv/bin/python -m pokeldn.gifts export celebi.pokegift --wc3 --build BPRJ --out-dir native-gift
./.venv/bin/python bin/frlg_mg_host.py --gift celebi --console-build BPRJ --export-gift celebi.wc3
```

儲存到 `.wc3` 或 `.wc8` 路徑會寫入原生檔案。一個 `.wc3` 只包含一張卡帶；不同變體需要 `--build`。
除圖示（重複卡片的圖示）外，其後設資料全為零。每個被接受的國際版圖鑑檔案都能往返轉換，卡片、指令碼和圖示
位元組完全一致。

國際版 `.wc3` 為 1420 位元組（`0x58C`）：

| 偏移 | 大小 | 內容 |
| --- | --- | --- |
| `0x000` | 336 | 卡片的 CRC16、2 個填充位元組、332 位元組的 `struct WonderCard` |
| `0x150` | 80 | 存檔側的卡片後設資料；不讀取 |
| `0x1A0` | 1004 | CRC16、2 個填充位元組、`struct RamScriptData`（magic 51、地圖組、地圖編號、物件 id、995 位元組指令碼）、1 個填充位元組 |

圖鑑檔案的指令碼 CRC 覆蓋 1000 位元組；遊戲自身的覆蓋 999 位元組 [script.c:488]；匯入接受兩者。
`--icon N`（應用中的 Card icon）設定 `iconSpecies`（卡片偏移 2），取值 0 到 411；0 表示不繪製
[mystery_gift_show_card.c:466]。

日文 `.wc3` 檔案為 1252 位元組（`0x4E4`）：卡片結構為 164 位元組，其 CRC 包裝為 168 位元組，後設資料從
`0x0A8` 開始，1004 位元組的 RAM 指令碼結構從 `0x0F8` 開始。日文檔案服務於 `BPRJ` 和 `BPGJ`，國際版檔案
服務於十種拉丁字母卡帶。超出 1000 到 1019 的標誌 id 會被拒絕 [mystery_gift.c:241]。

原生對（卡片加 1004 位元組指令碼）無法攜帶印章、來訪訓練家、神秘事件指令碼、問卷門檻或神秘新聞；匯出會拒絕
這些內容。匯入會檢查兩個 CRC。

## 版本 2

該檔案是帶五個必填欄位的 UTF-8 JSON：

| 欄位 | 值 |
| --- | --- |
| `format` | `pokeldn.gift` |
| `version` | 整數 `2` |
| `game` | `frlg` 或 `swsh` |
| `name` | 非空顯示名稱，最多 180 個字元 |
| `variants` | 將目的碼對映到原生資料與選項的物件 |

每個變體有 `data` 和 `options` 物件。`data` 中的元件有 `hex`（以十六進位制編碼的原生位元組）和 `sha256`
（其小寫 SHA-256 摘要）。匯出會對欄位排序。

| 遊戲 | 變體鍵 | 資料元件 | 選項 |
| --- | --- | --- | --- |
| FRLG 禮物 | 支援的卡帶程式碼 | `card`、`ram_script`、`stamp`、`activation_script`、`install_activation_script`、`trainer`、`news`、`mevent` | `questionnaire`、`denied_message` |
| FRLG 主機程式碼 | 支援的卡帶程式碼 | `buffer_code`、`buffer_lead_1`.. | 下方的應答設定 |
| 劍/盾 | `swsh` | `wc8` | 無 |

FRLG 卡片變體共享標誌 ID 和禮物型別；新聞和主機程式碼單獨傳輸。主機程式碼變體有一個 `buffer_code`，以及
最多八個在它之前執行的 `buffer_lead_N`，編號連續無空缺。應答設定：`buffer_expect`（u32 或
`trainer-id`）、`buffer_dump_size`（1 到 1024）、`buffer_dump_blocks`（最多 32）、
`buffer_dump_address`、`buffer_dump_addresses`（每個塊一個）、`buffer_decode`。

讀取器接受版本 1 檔案（卡片、新聞、WC8）；匯出為版本 2，它增加了主機程式碼。版本 1 的讀取器會拒絕
版本 2 檔案。

讀取器會拒絕未知的版本、欄位和程式碼、重複欄位、錯誤的雜湊、超過 256 KiB 的檔案、錯誤的原生大小以及
錯誤的組合；FRLG 還會檢查卡片欄位、訓練家校驗和與神秘事件終止。雜湊只用於檢測損壞；它們不認證任何
身份。

## 實現

`pokeldn.gifts` 負責外層封裝、校驗分發、讀取器、寫入器和轉換器。各遊戲專用的編解碼器位於
`pokeldn.frlg.gift.file` 和 `pokeldn.swsh.gift_file`。FRLG 介面卡構建 `MysteryGiftDistribution`，
包含其卡帶選擇與拒絕路徑；劍/盾介面卡則餵給 WC8 通告構建器。
