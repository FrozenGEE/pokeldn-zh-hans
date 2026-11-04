---
title: 葉綠
parent: 火紅與葉綠
nav_order: 6
---

# 葉綠，以及兩版卡帶的偏移對照

法版葉綠（BPGF，版本 0x0A，`POKEMON LEAF`）跑的是法版火紅的程式碼，只是 ROM 偏移呈分段常數。所有負載程式碼在它上面都能原樣工作；ROM 地址則不能。

## 實測地址

| 符號 | 葉綠 | 火紅 |
|---|---|---|
| `gDecompressionBuffer` | 0x0201C000 | 相同 |
| 神秘禮物呼叫點 | 0x08148C50 | 0x08148C74 |
| `Random` | 0x080486B0 | 相同 |
| `SeedRng` | 0x080486D0 | 相同 |
| `gRngValue` | 0x03004220 | 相同 |
| `gPlayerParty` | 0x02024280 | 相同 |
| `gPlayerPartyCount` | 0x02024025 | 相同 |
| `gEnemyParty` | 0x02024028 | 相同 |
| `gSpeciesInfo` | 0x0824CDD8 | 0x0824CDFC |
| `CreateMon` | 0x08041150 | 相同 |
| `sEasyChatGroups` | 0x083E353C | 0x083E3700 |
| `gSpecialVar_0x8000` | 0x020370B4 | 相同 |
| `gSpecialVars` | 0x08163984 | 0x081639A8 |
| `gSaveBlock1Ptr` | 0x03004228 | 相同 |
| `gSaveBlock2Ptr` | 0x0300422C | 相同 |

`rom_map.LEAFGREEN` 連同證據一起儲存這些條目；對不在表裡的符號，`rom_map.leafgreen(symbol)` 會丟擲異常。所有 IWRAM 和 EWRAM 地址完全一致；0x080486C8 以上的 ROM 地址則都有差異。新符號要實測，絕不要預測。

## 按區域看偏移增量

火紅到葉綠的偏移是分段常數，而且不單調：

    +0x0   -0x2C   -0x28   -0x24   -0x20   -0x1C4   -0x124C   -0x1240   -0x12D8

`rom_map.leafgreen_guess(firered_address)` 只在已實測的分段內作答，落在空隙裡就拒絕。`pokeldn/frlg/rom/leafgreen_twins.py` 儲存著 738 對實測地址（約 200 個具名函式）；`leafgreen_twins.leafgreen(address)` 在有配對時精確作答，否則退回猜測。

### 分叉的區段

    步進           區間                          內容
    0     -> -0x2c   644 B, 0x0807CF68..0x0807D1EC  title_screen.o
    -0x2c -> -0x28    62 B, 0x080DE2E4..0x080DE322  mystery_event_script.o
    -0x28 -> -0x24    90 B, 0x081480CE..0x08148128  mystery_gift.o
    -0x24 -> -0x20    31 B, 0x08251D8E..0x08251DAD  pokemon.o rodata
    -0x20 -> -0x1c4 1209 B, 0x083B7B47..0x083B8000  title_screen.o rodata
    -0x1c4 -> -0x124c  30 KB, 0x0843AFFF..0x08442800  graphics
    -0x124c -> -0x1240 17 KB, 0x08442BFF..0x08447000  graphics
    -0x1240 -> -0x12d8 63 KB, 0x0844F3FF..0x0845F000  graphics

每個區段都是版本分叉段，段內不存在統一的增量。`rom_map.LEAFGREEN_DELTA_BOUNDARIES` 儲存這些邊界，有測試會用分段表核對它們。0x0843C800 以上兩版卡帶裝的是不同的圖形資料。`gMPlayTable` 在火紅上是 0x0849758C，在葉綠上是 0x084962B4，`gSongTable` 在兩者上都在它之後 0x30 處。

## 配對兩版卡帶

`tools/frlg/cartridge_pair.py` 從兩版卡帶共有的每個窗口裡讀取字面量池和 `bl` 目標並配對（1592 個點，每個位置都配上了）。`memory-dump-scatter` 把同樣的地址同時發給兩臺主機；對兩個塊做互相關就能讀出增量，再逐個視窗比較哪個增量吻合，從而把步進定位到位元組。拿一臺主機匯出裡唯一的四位元組互異字去另一臺掃描，就能得到 ROM 裡任意位置的對應點。

坑：

- 按程式碼偏移配對字面量池，絕不要按序號配：序號配對在第一次錯位之後就會憑空造出增量。
- 增量 0 也是掃錯主機時的答案；務必在某個步進邊界上方放一個控制點，它必須返回位移後的地址。
- 圖形資料自己像自己：把每個候選增量互相打分，得分接近的一律記為「無結論」。

## 用火紅的表讀葉綠的匯出

`tools/frlg/rom_functions.py --console leafgreen` 會把條目、函式體和名稱都經 twins 換算過去，並丟棄落在分叉段裡的條目。指令碼層在 0x0807AF04 以下完全相同（`rom_map.SHARED_WITH_LEAFGREEN_THROUGH`）：`gScriptCmdTable` 的處理函式塊（0x0806D7C0..0x080700B8）、指令碼引擎、`GetVarPointer`、`VarGet`、`FlagSet`、`FlagClear`、`FlagGet` 和 `_call_via_r0`。

## 地上世界，以及一隻異色超夢

[定址樁](frlg_rng.md) 未移植也能跑。`initramscript` 把一段 RAM 指令碼繫結到地圖物件上，之後 `GetRamScript` 會執行它而不跑物件自帶的指令碼 [field_control_avatar.c:458]。華藍洞窟 B1F 是第 1 組第 74 張地圖；超夢是 3 號物件 [data/maps/CeruleanCave_B1F/map.json]。用 `setwildbattle` 把 150 號物種以 70 級綁到那裡，就會觸發一場指向超夢的對戰（在正版葉綠上就是一隻異色超夢）。

- 該繫結能跨掉電保留。
- 神秘禮物會話會通過 `InitRamScript_NoObjectEvent` 重新繫結這個槽位，超夢自己的指令碼隨之恢復；而緩衝區指令碼不會動它。
- 繫結期內主機報告沒有神秘卡片（見[那一個 RAM 指令碼槽位](frlg_gift.md#the-one-ram-script-slot)）。

## 會變的區域不能做匯出

對逐幀變化的區域（例如 `gRngValue`）做 `memory-dump`，會因為 CRC 與傳送發生在不同的幀而校驗失敗，最後停在*erreur de connexion*（見[重新指向主機的出站訊息](frlg_rom.md#repointing-the-consoles-outgoing-message)）。上方兩個存檔塊指標會一起移動 0..124 內的一個 4 位元組對齊偏移 [load_save.c:75]。

## 英文版

`pret/pokefirered` 用 binutils 和 `pret/agbcc` 在 REVISION 10 上編譯兩版卡帶：

    make firered_switch     -> pokefirered_switch.gba    baa452d0b24629dd7782cfc07a8984085dde1311
    make leafgreen_switch   -> pokeleafgreen_switch.gba  62b9fc77549dbc67032eb6cbd0ea6ad3b825690f

與這兩個 sha1 對不上的構建一律不可用；ROM 永遠不提交進倉庫。它也是英文版，是第二對已知全部符號的卡帶。

### 偏移：法版地址到英文地址

法版到英文的偏移也是分段常數，在某個物件因語言而改變大小的地方跳變。`gSpecials`、`gScriptCmdTable` 和 `gMysteryEventScriptCmdTable` 的條目（675 個點）以及唯一的 16 位元組視窗，在兩者都適用的地方處處吻合。

    ./.venv/bin/python tools/frlg/english_build.py --offsets

### 對照驗證

經該偏移換算後，英文 ELF 與 `worker_names` 裡的全部 232 個名字一致，沒有一個不符。

    ./.venv/bin/python tools/frlg/english_build.py --check

`pokeldn/frlg/rom/english_names.py`（由 `scripts/gen_english_names.py` 生成）用這種方式命名了 7573 個法版函式地址，由 `rom_functions` 最後讀取並標為 `[english]`，因此從英文版推斷出的名字永遠不會覆蓋主機實際命名的函式體（`gen_worker_names` 傳 `with_english=False`）。落在兩段偏移之間的目標，只有在恰好一個相鄰偏移落到某個函式起點時，才會進 `english_names.BRACKETED`（`[english?]`）。`__divsi3`、`__modsi3` 和 `__umodsi3` 是 agbcc 的除法輔助函式。

### 英文版這一對自己的增量圖

兩個英文 ROM 給出同樣的六個增量、同樣的順序，每個步進都落在一個版本分叉物件內部：

    +0x0   -0x2c   -0x28   -0x24   -0x20   -0x1c4

五個預測出的法版步進位置全部落在硬體上實測到的括號區間內。

    ./.venv/bin/python tools/frlg/english_build.py --boundaries

### 坑

- `.gcc2_compiled.` 符號會遮蔽它所在檔案的第一個函式；跳過以 `.` 或 `$` 開頭的名字。
- 填充資料與任何增量都吻合。窗口裡必須有 16 個互不相同的位元組值，匹配才算數。
- 偏移（法版到英文，在同一版卡帶內）不是增量（火紅到葉綠）：`法版增量 = offsetFR - offsetLG + 英文增量`。
- 每次新匯出之後都要重新生成 `english_names.py`。

## 不能用的參照

`gSongTable` 把 122 個歌曲頭壓進 9 KB，所以它只能固定一個位置。火紅的 ROM 資料在 0x086ABE68 到 0x08800000 之間結束；0x08800000 讀出來全是 `0xFF`，0x08E00000 全是 `0x00`。
