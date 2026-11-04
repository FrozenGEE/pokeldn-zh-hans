---
title: 隨機數生成器
parent: 火紅與葉綠
nav_order: 5
---

# gRngValue：讀出它、預測它、並對準它

火紅的 `gRngValue` 可以被讀出、可以從一隻寶可夢反推出來，還可以用一段地圖樁對準，讓下一次指令碼觸發的遭遇變成異色，且性格與個體值都任你挑。地址取法版火紅（BPRF，0x0A）。

## 生成器

```c
u16 Random(void) { gRngValue = 1103515245 * gRngValue + 24691; return gRngValue >> 16; }
void SeedRng(u16 seed) { gRngValue = seed; }
```

[src/random.c, include/random.h:18]

| 符號 | 地址 |
|---|---|
| `gRngValue` | `0x03004220` |
| `Random` | `0x080486B0` |
| `SeedRng` | `0x080486D0` |
| `gSpecialVar_0x8000` | `0x020370B4` |

`pokeldn/frlg/rom/lcg.py` 負責算術部分；`distance(a, b)` 用大小步演算法精確求解。這個對映在全部 2<sup>32</sup> 個狀態上是一個置換，所以只有當距離很小時它才算證據（機率約 N / 2<sup>32</sup>）。`gRngValue` 與 `gSpecialVar_0x8000` 從不移動；存檔塊則在每次對戰與載入時移動 [load_save.c:75]。

## 速率：每幀正好 2 步

狀態每幀正好前進 2 步：`--gift rng-rate-probe`（讀、`delay` N 幀 [scrcmd.c:651]、再讀）測得 `2N + 2` 步，多出的 2 步是 `delay` 前後各一幀。讀完之後再過 n 幀的狀態是 `advance(S, 2n)`。一步約 8 毫秒。

## 種子從哪來，以及為什麼帶不過去

`SeedRngAndSetTrainerId` [main.c:264] 從定時器 1（`REG_TM1CNT_L`）取種子，取樣點是標題畫面按下 START 的那一刻 [title_screen.c:735]，共 65536 個取值；讀取有亞幀抖動，所以靠掐時間按 START 是選不出種子的。從神秘禮物退出會回到標題畫面 [mystery_gift_menu.c:463]，因此在鏈路上設下的種子永遠到不了地上世界。

| `SeedRng` 呼叫點 | 時機 |
|---|---|
| `SeedRngAndSetTrainerId` [title_screen.c:735] | 標題畫面 |
| `LinkTestScreen` [link.c:318] | 未使用的除錯畫面 |
| `Debug_RfuIdle` [link_rfu_2.c:2670] | 未使用的除錯畫面 |
| `RfuMain1` [link_rfu_2.c:2116] | 僅 Switch 版，條件為 `svc_4b() & SVC4B_RESEED_RNG`，種子取自主機廣播的 `playerTrainerId` |

沒有任何實測狀態來自 `RfuMain1` 的重新播種；這一位何時被置上目前不明。

## 從一隻寶可夢反推產生它的狀態

野生寶可夢是四次取值：性格低半、性格高半、HP/攻擊/防禦、速度/特攻/特防 [wild_encounter.c:233]。個體值再提供 30 位校驗，所以 `lcg.recover_wild_state` 能唯一定出一個狀態。個體值那兩次取值之前或之間可能還夾著一次雜散取值；其來源不明，因此兩個間隙都要搜：

| 方式 | 個體值之前的間隙 | 個體值之間的間隙 |
|---|---|---|
| 1 | 0 | 0 |
| 2 | 1 | 0 |
| 4 | 0 | 1 |

在提出任何 RNG 結論之前，先用一隻寶可夢的 PID、個體值與其六項能力值互相對照。

## 指令碼觸發的對戰

```
setptr b0..b3 -> 0x03004220      gRngValue = seed          (opcode 0x11)
setwildbattle <species> <level>  CreateMon rolls PID, PID, IV, IV   (0xB6)
dowildbattle                     the battle starts          (0xB7)
```

`setwildbattle` 呼叫 `CreateMon(..., 32, 0, 0, OT_ID_PLAYER_ID, 0)` [script_pokemon_util.c:128]：就是乾淨的四次取值方式 1，沒有草叢或遭遇抽取。兩條命令都返回 FALSE，所以寫入與生成在同一幀內完成；兩者之間不能有任何會讓出執行的命令（有測試斷言這一點）。這段 RAM 指令碼由 `initramscript` 繫結，並以 `end`（0x02）結尾而不是 `endram`，所以會重複觸發。一隻預測出來的異色 50 級百變怪，其 PID、性格與個體值完全吻合。

若先讀出即時狀態再生成寶可夢，四次取值從讀到的那個狀態開始；這隻寶可夢花掉 4 步（`Random32()` 2 步，個體值 2 步 [pokemon.c:1796,1836,1845]），再加上地上世界的一幀 2 步。

## 讀種子的 NPC

`--gift rng-seed-reader`，標誌位 id 1015，一段繫結的 RAM 指令碼：

```
copybyte gSpecialVar_0x8000+0, 0x03004220      (opcode 0x15)
copybyte gSpecialVar_0x8000+1, 0x03004221
copybyte gSpecialVar_0x8001+0, 0x03004222
copybyte gSpecialVar_0x8001+1, 0x03004223
buffernumberstring 0, VAR_0x8000               (0x83)
msgbox                                          the NPC prints the value
```

`rng_script.seed_from_printed(low, high)` 把兩個字重新拼回來，`rng_script.check_two_readings` 給兩次讀數打分。

- 六條命令都返回 FALSE 並在同一幀內跑完，所以讀取不會被撕開。
- 文本指標是相對的：`setvaddress`（0xB8）與 `vmessage`（0xBD）[scrcmd.c:171] 會把運算元當成指令碼體內的偏移，而指令碼體隨存檔塊一起移動。
- `buffernumberstring` 列印一個 `u16` [scrcmd.c:1678]：兩個變數就是兩行。

綁到玩家的媽媽身上（第 4 組、第 0 張地圖、1 號物件，`MOVEMENT_TYPE_FACE_LEFT`，永不隱藏）。真新鎮的物件事件會到處走動。

## 人手按 A 能有多準

提前 30 秒瞄準的玩家，落點相對某個固定偏移的標準差是 4.5 幀，所以一次按鍵大約只有 9% 的機率命中選定幀；而異色幀每約 8192 幀才出現一次。`pokeldn/frlg/rom/rng_countdown.py` 是那個倒計時；`--aimed-at STATE` 以幀為單位測出偏差。當 RAM 指令碼槽被神秘卡片佔著時，走的就是這條路線。

在指令碼的按鍵等待處，鉤子可以代你按下，正好落在那一幀，而且不寫 `gRngValue`：[`shiny-press`](frlg_rom.md#shiny-shiny-press-ivs-noencounter)，也就是應用裡的「異色傳說寶可夢」。

## 做搜尋的那段樁

`--gift rng-shiny-hunt`、`pokeldn/frlg/rom/native_script.py`、`asm/field/`。四段樁在正版卡帶上都能用：

| 樁 | 禮物 |
|---|---|
| `shiny-seek.s` | `rng-shiny-hunt` |
| `mon-seek.s` | `rng-mon-hunt` |
| `mon-seek-far.s` | `rng-mon-hunt-far` |
| `mon-seek-both.s` | `rng-mon-hunt-both` |

```c
bool8 ScrCmd_setptr(struct ScriptContext * ctx)          // 0x11
{ u8 value = ScriptReadByte(ctx); *(u8 *)ScriptReadWord(ctx) = value; }
bool8 ScrCmd_callnative(struct ScriptContext * ctx)      // 0x23
{ void (*func)(void) = ((void (*)(void))ScriptReadWord(ctx)); func(); return FALSE; }
```

[scrcmd.c:300, :120]。`setptr` 把程式碼暫存進 EWRAM，`callnative` 在地上世界裡執行它，這是 `CLI_RUN_BUFFER_SCRIPT` 到不了的地方（`notblisy/RUBYSAPPHIREDLC` 在紅寶石/藍寶石上做的是同一件事）。`CreateScriptedWildMon` 沒有固定性格，`OT_ID_PLAYER_ID` 也不消耗取值，所以是否異色只取決於樁留下的那個狀態之後的頭兩次取值。

樁在 `gSaveBlock2Ptr + 0x0A` 處讀 `playerTrainerId`，並且只寫 `gRngValue`。搜尋是有界的；耗盡之後遭遇就是普通遭遇。每段樁在暫存之前都會在 unicorn 下跑一遍（`tests/test_native_script.py`）。

### RAM 指令碼未必能從對戰中回來

`CB2_InitBattle` 與 `InitOverworldBgs` 會呼叫 `MoveSaveBlocks_ResetHeap` [battle_main.c:614, overworld.c:1337]，把 `gSaveBlock1` 在 0..124 內按 4 的倍數移動 [load_save.c:75]，而指令碼引擎仍握著自己的指標指向 `ramScript.data.script` [script.c:514]。`dowildbattle` 之後的東西全都不可達：恢復執行會落到一場莫名其妙的戰鬥、一段零填充，或一條讓地上世界卡死的命令上。

所以對戰從存檔塊之外啟動 [`rng_script.battle_and_exit`]：

    setvar 0x8000, 0x02B7      ->  0x020370B4: B7 02  =  dowildbattle ; end
    goto   0x020370B4

對戰中沒有任何東西會寫 `gSpecialVar_0x8000`，而 `end` 會把控制權交還 [script.c:335]。任何 RAM 指令碼都不能指望跨過一場對戰或一次地圖載入後存檔塊地址還不變。

## 挑選性格與個體值

`--gift rng-mon-hunt`、`asm/field/mon-seek.s`、標誌位 id 1019，檢查是否異色、性格（`personality % 25` [pokemon.c:5020]）以及個體值下限（第 3、4 次取值 [pokemon.c:1836]）：

    --hunt-nature adamant,jolly   --hunt-iv speed=31 --hunt-iv attack=20   --hunt-cap N

| 要求 | 命中率 | 典型卡頓 | 達到上限時最壞 |
|---|---|---|---|
| 異色 | 1 / 8,192 | 0.02 秒 | 0.10 秒 |
| 異色 + 指定性格 | 1 / 204,800 | 0.55 秒 | 2.5 秒 |
| 異色 + 性格 + 一項個體值 >= 20 | 1 / 546,133 | 1.5 秒 | 6.7 秒 |
| 異色 + 兩項個體值 = 31 | 1 / 8,388,608 | 22 秒 | 拒絕執行 |

`native_script.search_cost` 會算出這些數；最壞情況超過 `--hunt-freeze-frames`（預設 900）時主持端直接拒絕。玩家看到的是一幀靜止畫面和音樂。`mon-seek.s` 佔 163 位元組暫存預算裡的 160 位元組。

## 指令碼體裡的負載

`setptr` 每寫入一個程式碼位元組就要花掉六個指令碼位元組。指令碼引擎在原地執行那 995 位元組的 RAM 指令碼體，並且從不讀最後一條命令之後的內容 [script.c:514]，所以它之後的位元組可以按一位元組一個當儲存用。`&gSaveBlock1Ptr`（0x03004228）給出該幀指令碼體的地址；只有 `asm/field/ram-jump.s`（36 位元組）需要暫存：

    setptr x36    the trampoline, into gDecompressionBuffer        216 bytes
    callnative    -> trampoline -> payload -> back                   5
    setwildbattle / setvar / goto                                   16
    pad to a multiple of four                                        3
    payload                                                        755

跳板的尾部用 `bx r0` 跳轉，所以負載的 `pop {r4-r7, pc}` 會直接返回到 `ScrCmd_callnative` 的呼叫者。除非 `ramScript.data.magic` 等於 51，否則它會提前返回 [script.c:12]。

### 四位元組對齊

THUMB 的 `ldr rN, [pc, #imm]` 使用 `Align(PC, 4)`。指令碼體是按字對齊的：存檔塊偏移是 `& 0x7C` [load_save.c:75]，而 `RAMSCRIPT_BODY_OFFSET` 是 0x3624。`native_script.emulate_body_script` 會走一遍真實的指令碼位元組，以便抓出未對齊。

### 用大小來證明，而不是靠跳轉

`asm/field/mon-seek-far.s` 之後填滿非零資料直到第 995 位元組；只有填充校驗和正確時樁才會搜尋。`InitRamScript` 會零填充剩下的部分 [script.c:495]，所以交付的位元組短了就等於完全不碰 `gRngValue`。`--gift rng-mon-hunt-far` 帶 196 位元組的樁和 559 位元組填充。

## 讓搜尋不受雜散取值影響

`asm/field/mon-seek-both.s`（232 位元組，`--gift rng-mon-hunt-both`，標誌位 id 1001）在兩個落點上檢查下限。設性格之後的取值為 d3、d4、d5：

| 方式 | 第一組（HP/攻擊/防禦） | 第二組（速度/特攻/特防） |
|---|---|---|
| 1（乾淨） | d3 | d4 |
| 2 | d4 | d5 |
| 4 | d3 | d5 |

同時要求 `d3 | d4<<15` 與 `d4 | d5<<15` 兩個詞，就覆蓋了全部三種方式。異色 + 開朗 + 速度 >= 20 變成 1 / 1,456,000，典型耗時約 4 秒；上限是 95%。

## 搜尋把報告寫在哪

`asm/field/mon-seek-log.s`（288 位元組，`--gift rng-mon-hunt-log`，標誌位 id 1002）把 `{marker, start, found, iterations, cap}` 寫到 `gSaveBlock1Ptr + 0x348C`，也就是 `u8 unused_348C[400]` [include/global.h]，沒有任何程式碼寫那裡。它能熬過對戰，並在存檔時進到快閃記憶體；搜尋耗盡時會寫 `found` 為 0。

    --buffer-script save-dump --dump-block sav1 --dump-offset 0x348C --dump-size 32

`native_script.decode_hunt_log` 負責解讀它。一次記錄在案的 603,745 次迭代搜尋與 `lcg.distance(start, found)` 完全吻合，耗時 2–3 秒，每條指令 3.7–5.6 個週期，而模型的 `CYCLES_PER_INSTRUCTION_FROM_EWRAM` 取的是 3。

## 葉綠

這些樁不用移植就能跑：每個字面量要麼是連結期的 IWRAM 字，要麼是常量，而 `TID ^ SID` 是執行時讀的。見[葉綠](frlg_leafgreen.md)。
