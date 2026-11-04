---
title: ROM 對映表
parent: 火紅與葉綠
nav_order: 4
---

# ROM 對映表

本頁把火紅/葉綠卡帶的 ROM 映射出來：映象、函式表、指令碼讀取器、物種表、法語的快捷聊天詞庫，以及十二個國際版構建。除表格另有說明外，地址一律是法版火紅（BPRF，版本 0x0A）；葉綠的地址見[葉綠](frlg_leafgreen.md)。`pokeldn/frlg/rom/rom_map.py` 記錄了每個地址是怎麼得到的，`tests/test_rom_map.py` 用主機匯出核對它。

## 卡帶映象

Switch 版把 GBA ROM 作為 RomFS 裡唯一的檔案帶著。

| 標題 id | RomFS 檔案 | 大小 | sha1 |
|---|---|---|---|
| 01004B3023412000 | `/FireRed_f.gba` | 16777216 | `07566b82dbd2a91321698f730f6400ae4c56ddf1` |
| 010087C02342E000 | `/LeafGreen_f.gba` | 16777216 | `9f774956dfbad7f69ddb91fb91d2c26e54408f75` |
| 0100554023408000 | `/FireRed_e.gba` | 16777216 | `baa452d0b24629dd7782cfc07a8984085dde1311` |
| 010034D02340E000 | `/LeafGreen_e.gba` | 16777216 | `62b9fc77549dbc67032eb6cbd0ea6ad3b825690f` |

0xA0 處的頭部讀出來是 `POKEMON FIRE` `BPRF` 和 `POKEMON LEAF` `BPGF`，版本 0x0A，校驗和有效。法版火紅 1.0.1 更新除了外殼的三處載入期補丁外不改動客戶 ROM（見 [frlg_rom.md](frlg_rom.md) 的「斷點鉤子」一節）；`0x09000000..0x0A000000` 讀出來是開放匯流排（每個半字都是它自己的地址減半）。英文這一對（`BPRE`、`BPGE`）與 `pret/pokefirered` 的 `pokefirered_switch.gba`、`pokeleafgreen_switch.gba` 逐位元組相同。

`scratchpad/base_romfs.py` 讀取 Program NCA 裡那個唯一的 CTR RomFS 段：

    ./.venv/bin/python scratchpad/base_romfs.py "$NSP" --list
    ./.venv/bin/python scratchpad/base_romfs.py "$NSP" --extract /FireRed_f.gba --out scratchpad/FireRed_f.gba

## 兩個構建的 EWRAM 地址相同

英文 ELF 裡的 EWRAM 符號就是法版卡帶的那一套（`gDecompressionBuffer` 0x0201C000、`gPlayerParty` 0x02024280、`gPlayerPartyCount` 0x02024025）。IWRAM 則不同。從 0x0203FBAC（最高符號結束處）到 0x02040000 之間沒有任何符號佔用（`scratchpad/ram_survey.py`）。

## 英文版卡帶

`pokeldn/frlg/rom/builds.py` 為每版卡帶儲存一張表（`BPRF`、`BPGF`、`BPRE`、`BPGE`、`BPRS`、`BPGS`、`BPRD`、`BPGD`、`BPRI`、`BPGI`、`BPRJ`、`BPGJ`）：IWRAM 全域性變數、ROM 函式負載、鉤子、樁，以及 `call-chain` 用到的和禮物攜帶的資料指標。主持端在傳送任何依賴地址的東西之前，先從 `MysteryGiftLinkGameData` 裡的遊戲代號選表 [mystery_gift.c:369]；沒有對應表，或被 `--console-build CODE` 或 `--version` 排除的主機，會被拒絕，什麼都不發。

英文地址來自 ELF，每一處都與正版映象核對過。

| 區域 | 法版到英文 |
|---|---|
| EWRAM | 不變 |
| IWRAM 0x03000000..0x03001B6F | 不變 |
| IWRAM 0x03002370..0x0300602F（英文），起點是 `gMain`（法版 0x030022D0，英文 0x03002380） | +0xB0 |
| IWRAM 0x03006090..0x03007583（英文），從 `gSoundInfo`（法版 0x03005F80）到 `gFlash` | +0x110 |
| IWRAM 0x03007590 以上：棧、中斷向量 | 不變 |
| ROM | 沒有統一偏移；每個函式單獨查表 |

英文版取值：`gRngValue` 0x030042D0、`gSaveBlock1Ptr` 0x030042D8、`gSaveBlock2Ptr` 0x030042DC、`gIntrTable[4]` 0x030027E0、`gLastWrittenSector` 0x03004650、`gSaveCounter` 0x03004660。英文版葉綠的 RAM 就是英文版火紅的；常駐鉤子的地址裡只有 `m4aSoundMain` 會移動（0x081E07C4 對 0x081E07E8）。`tests/test_frlg_english_cartridges.py` 會把各負載放進對應映象的 `Client_RunBufferScript` 裡跑（沒有 `scratchpad/frlg_en/` 時跳過）。

## BIOS 包裝函式

`libagbsyscall.s` 按反編譯原始碼的順序連結成 THUMB 的 `svc N ; bx lr` 對，葉綠上整體低 0x24：

| 包裝 | svc | 火紅 | 葉綠 |
|---|---|---|---|
| `ArcTan2` | 0x0A | 0x081E21D4 | 0x081E21B0 |
| `BgAffineSet` | 0x0E | 0x081E21D8 | 0x081E21B4 |
| `CpuFastSet` | 0x0C | 0x081E21DC | 0x081E21B8 |
| `CpuSet` | 0x0B | 0x081E21E0 | 0x081E21BC |
| `Div` | 0x06 | 0x081E21E4 | 0x081E21C0 |
| `LZ77UnCompVram` | 0x12 | 0x081E21E8 | 0x081E21C4 |
| `LZ77UnCompWram` | 0x11 | 0x081E21EC | 0x081E21C8 |

遊戲裡的 LZ77 資料流對 VRAM 安全，且與 `gbagfx` 的輸出一致。LZ77 不會讓負載程式碼變小，只有超過 1024 位元組的資料才值得用。

## 第一個錨點

`anchors` 返回 `0x08148C75`，即 `Client_RunBufferScript` 裡的返回地址 [mystery_gift_client.c:274]。它的字面量池是：

    0x08148C88 -> 0x0201C000   gDecompressionBuffer
    0x08148C8C -> 0x0300422C   &gSaveBlock2Ptr
    0x08148C90 -> 0x03004228   &gSaveBlock1Ptr

0x08148C94 處的 `MysteryGiftClient_CallFunc` 用 `client->funcId` 索引 `sClientFuncs`（0x0845DBD0，八個條目）。其餘所有地址都是從字面量池、`bl` 目標和指標表一路追下來的，每一處都落在已知的函式序言上（`scratchpad/rom_read.py`）。

## 四張函式表

    gScriptCmdTable              0x08163650   214 entries   the field script commands
    gSpecialVars                 0x081639A8    21 entries
    gSpecials                    0x081639FC   444 entries   gSpecialsEnd 0x081640EC
    gStdScripts                  0x081640EC    10 entries
    gMysteryEventScriptCmdTable  0x081DE144    17 entries

`script_data` 從 0x08163650 一直到 0x081DE188，那裡是 `lib_text`（`libgcnmultiboot`）的起點 [ld_script_rev10.ld:318-330]。

- `gSpecialVars`：十二個字，每個比前一個高 2（`gSpecialVar_0x8000` = 0x020370B4，一個 `EWRAM_DATA` 全域性變數）[event_data.c:16]。
- `gScriptCmdTable`：214 個 THUMB 指標；第 0 和第 213 條都是 `ScrCmd_nop`。`pokeldn/frlg/rom/scrcmd_names.py` 給每一條都起了名（`scrcmd_names.handler("additem")`）。

      0x23 callnative   0x0806D854      0x44 additem      0x0806DED0
      0x25 special      0x0806D7EC      0x79 givemon      0x0806F834
      0x29 setflag      0x0806E0EC      0x90 addmoney     0x0806F998

- `gSpecials`：444 個條目，來自 `ScrCmd_special` 的字面量池 [scrcmd.c:101]，經 0x081E2224 呼叫；其中 171 個是 `NullFieldSpecial`。`rom_map.SPECIAL_ADDRESSES` 儲存它們，`rom_map.special_function("HealPlayerParty")` 可以解析出單個函式。
- `gStdScripts`：十個字，指向 0x081A76xx..0x081AB5xx。
- `gMysteryEventScriptCmdTable`：通過 `sMysteryEventScriptContext`（0x0203AA38）找到，它的表對位於 +0x5C/+0x60 [mystery_event_script.c:27,52]（在同一次啟動裡先領一次神秘事件禮物，然後在 EWRAM 上跑 `table-scan --table-delta 0x44 --table-runlen 2`）。

| # | 命令 | 處理函式 | | # | 命令 | 處理函式 |
|---|---|---|---|---|---|---|
| 0 | `nop` | 0x080DE451 | | 9 | `givenationaldex` | 0x080DE61D |
| 1 | `checkcompat` | 0x080DE401 | | 10 | `addrareword` | 0x080DE641 |
| 2 | `end` | 0x080DE3F5 | | 11 | `setrecordmixinggift` | 0x080DE66D |
| 3 | `setmsg` | 0x080DE465 | | 12 | `givepokemon` | 0x080DE681 |
| 4 | `setstatus` | 0x080DE455 | | 13 | `addtrainer` | 0x080DE78D |
| 5 | `runscript` | 0x080DE49D | | 14 | `enableresetrtc` | 0x080DE7D5 |
| 6 | `initramscript` | 0x080DE5B5 | | 15 | `checksum` | 0x080DE7E9 |
| 7 | `setenigmaberry` | 0x080DE4B9 | | 16 | `crc` | 0x080DE831 |
| 8 | `giveribbon` | 0x080DE581 | | | | |

## 從表項到它背後的函式

按地址順序排一個處理函式的 `bl` 目標，得到的就是反編譯原始碼裡按原始碼順序的呼叫 [scrcmd.c:463-590]：

    ScriptReadHalfword   0x0806D1E8      AddBagItem           0x0809DA70
    VarGet               0x08071DDC      RemoveBagItem        0x0809DBC4
    GetVarPointer        0x08071CC8      CheckBagHasSpace     0x0809D9EC
    FlagSet              0x08071EF4      CheckBagHasItem      0x0809D92C
    FlagClear            0x08071F1C      AddPCItem            0x0809DDB4
    FlagGet              0x08071F44      IncrementGameStat    0x080587A4

`gSpecialVar_Result` 是 0x020370CC；`Random` 是 0x080486B0。`scratchpad/handler_workers.py` 會列印某個處理函式的 `bl` 目標；`tools/frlg/rom_functions.py --table specials|field|mystery-event|callable` 則跨整張表來做，並規劃下一批 `--dump-address` 視窗。

ROM 是 agbcc 編譯的，一個 THUMB 函式以 `pop {r4,r5,r6}; pop {r1}; bx r1`（BC70 BC02 4708）結尾，從不用 `pop {..., pc}`。`pokeldn/frlg/rom/thumb.py` 匹配 `bx Rn`，並且只有當後面跟著函式序言時才把一次返回當作塊的結束。

### 離線命名 300 個函式

`scripts/gen_worker_names.py` 把每份匯出的函式體與反編譯原始碼做拉鏈比對，寫出 `pokeldn/frlg/rom/worker_names.py`，並受四道檢查約束：

| 檢查 | 排除了什麼 |
|---|---|
| 長度 | 內聯、`__umodsi3`、把宏當成呼叫 |
| 錨點 | 未對齊的函式體：每個實測地址都必須落回它自己的名字 |
| 一致 | 同一個目標被兩個呼叫者起了不同的名字 |
| 連結順序 | 名字在 ROM 裡位置不對（保留最長的遞增鏈） |

如果兩個錨點之間只夾著一個未命名目標和一個原始碼呼叫，那就唯一確定了。讀原始碼時要注意：

- `firered_switch` 是 `GAME_REVISION=10 MODERN=0` [Makefile:227]：那些 `#if REVISION >= 0xA` 的塊是生效的。
- `VarGet(ScriptReadHalfword(ctx))` 是 `bl ScriptReadHalfword` 再 `bl VarGet`。
- `ScriptReadByte` 是宏，不產生 `bl` [include/script.h:24]。
- `NDEBUG` 處於定義狀態：沒有斷言呼叫。

| `rom_map` 裡的名字 | 反編譯原始碼 | 吻合的函式體數 |
|---|---|---|
| `GET_MON_DATA` | `GetMonData3` | 15 |
| `SCRIPT_CONTEXT_SET_NATIVE` | `SetupNativeScript` | 11 |
| `SET_RESPAWN` | `SetLastHealLocationWarp` | 1 |
| `SCRIPT_MOVEMENT_START` | `ScriptMovement_StartObjectMovementScript` | 2 |
| `CHANGE_AMOUNT_MONEY_BOX` | `ChangeAmountInMoneyBox` | 2 |
| `ME_CHECK_COMPATIBILITY` / `ME_SET_INCOMPATIBLE` | `CheckCompatibility` / `SetIncompatible` | 1 / 3 |

`GetMonData2` 是 `GetMonData3` 的別名 [pokemon.c:2970]。`0x0806D0EC` 是 `StopScript(ctx)` [script.c:76]；`ScriptContext_Stop(void)` [:360] 是 0x0806D418。

### 混用映象的兩個陷阱

- 絕不能把兩版卡帶的匯出當成一個映象來讀：葉綠這段程式碼整體低 0x2C，混在一起的映象會把呼叫錯認。`script_read.every_dump` 一次只認一版卡帶。
- 要一次讀入全部匯出：`scrcmd.Memory` 會合並互相重疊的匯出（`tools/frlg/script_read.py --with-every-dump`）。

### 實測了什麼

每張表背後的每個函式體都讀過了：213 條野外指令碼命令、17 個神秘事件操作碼、27 個可呼叫函式、272 個 special。`NullFieldSpecial` 是 0x080CE8DC 處的 `bx lr`；`GetLeadMonIndex` 是 0x080CE818；`DoDiveWarp` 是 0x08081CC8，`DoFallWarp` 是 0x08081DA0。

神秘事件虛擬機器的幹活的函式：

| 函式 | 地址 | 被誰呼叫 |
|---|---|---|
| `StringExpandPlaceholders` | 0x0800CADC | 每個會留下訊息的處理函式的最後一次呼叫 |
| `RunScriptImmediately` | 0x0806D438 | `runscript` |
| `InitRamScript` | 0x0806D5F0 | `initramscript` |
| `GiveGiftRibbonToParty` | 0x080A43B0 | `giveribbon` |
| `EnableRareWord` | 0x080C1658 | `addrareword` |
| `CheckCompatibility` | 0x080DE300 | `checkcompat` |
| `SetIncompatible` | 0x080DE330 | `checkcompat` 的 else 分支 |
| `memcpy` | 0x081E44F4 | `addtrainer` |
| `CalcCRC16` | 0x080489A0 | `crc` |
| `StringCopyN` | 0x0800C8CC | `setenigmaberry`、`givepokemon` |
| `StringCompare`、`SetEnigmaBerry` | 0x0800C938、0x080A01B0 | `setenigmaberry` |
| `VarSet` | 0x08071DF8 | `setenigmaberry`；沒有任何 ScrCmd 呼叫它 |
| `SpeciesToNationalPokedexNum` | 0x08046994 | `givepokemon` |
| `GetSetPokedexFlag` | 0x0808C860 | `givepokemon` |
| `ItemIsMail`、`GiveMailToMon2`、`CompactPartySlots` | 0x0809BB18、0x0809B964、0x080971FC | `givepokemon` |

呼叫跳板從 0x081E2224 的 `_call_via_r0` 起每個四位元組（r4 是 0x081E2234，r6 是 0x081E223C）。

## 存檔備份與恢復

每版卡帶上都要用的 `LoadGameSave` [save.c:803] 和 `gRfu.sendQueue.count` [link_rfu_2.c:3131]。`LoadGameSave` 以 `70 b5 00 06` 開頭並把 `gDecompressionBuffer` 放進字面量池；佇列計數由一個葉子函式讀出來：`ldr r0, =gRfu; ldr r1, =0x8D2; adds r0, r0, r1; ldrb r0, [r0]; bx lr`。

| 卡帶 | `LoadGameSave` | `gRfu` | `gRfu.sendQueue.count` |
|---|---|---|---|
| `BPRE` | `0x080DDBF4` | `0x03005590` | `0x03005E62` |
| `BPGE` | `0x080DDBC8` | `0x03005590` | `0x03005E62` |
| `BPRF` | `0x080DDFD4` | `0x030054E0` | `0x03005DB2` |
| `BPGF` | `0x080DDFA8` | `0x030054E0` | `0x03005DB2` |
| `BPRD`、`BPRI` | `0x080DDF14` | `0x030054E0` | `0x03005DB2` |
| `BPGD`、`BPGI` | `0x080DDEE8` | `0x030054E0` | `0x03005DB2` |
| `BPRS` | `0x080DDFFC` | `0x030054E0` | `0x03005DB2` |
| `BPGS` | `0x080DDFD0` | `0x030054E0` | `0x03005DB2` |
| `BPRJ` | `0x080DED68` | `0x03005520` | `0x03005DF2` |
| `BPGJ` | `0x080DED3C` | `0x03005520` | `0x03005DF2` |

十二版卡帶的 `sSaveSlotLayout` 都一致，只有扇區 id 4 例外：拉丁語系卡帶是 3816 位元組，日版是 3776 位元組。

# 讀主機的指令碼

`scripts/gen_scrcmd_args.py` 從反編譯原始碼的宏生成運算元寬度，寫進 `pokeldn/frlg/rom/scrcmd_args.py`；之後用 `memory-dump` 加 `scrcmd.disassemble` 就能讀任何指令碼：

    0x081A7624  6A  lock
    0x081A7625  5A  faceplayer
    0x081A7626  67  message 0x00000000
    0x081A762B  66  waitmessage
    0x081A762C  6D  waitbuttonpress
    0x081A762D  6C  release
    0x081A762E  03  return

這就是 `Std_MsgboxNPC`。從每個 `gStdScripts` 條目往下走，都會在下一個條目之前的那一位元組上遇到終止符。

## 條件宏

| 命令 | 寬度 | 結構 |
|---|---|---|
| `applymovement` | 7 位元組 | `.ifb \map` 分支 |
| `waitmovement`、`removeobject`、`addobject` | 3 位元組 | `.ifb \map` 分支 |
| `applymovementat`、`waitmovementat`、`removeobjectat`、`addobjectat` | 9、5、5、5 位元組 | 另一條分支 |
| `warp` 及其餘八個傳送命令 | 8 位元組 | `formatwarp` 子宏 |
| 十個 `buffer*` 命令 | 4 位元組 | `stringvar` 子宏 |
| `showobjectat`、`hideobjectat`、`resetobjectsubpriority` | 5 位元組 | `map` 子宏 |
| `trainerbattle` | 6 + 4..16 位元組 | 依型別分支 |

只有當每條分支都以自己的操作碼位元組開頭、且不落到別的命令宏時，一個宏才算命令宏（`giveitem` 是兩條指令）。`trainerbattle` 是 `scrcmd_args.VARIABLE`；遇到未知型別，`scrcmd.shape` 會返回 `None`。`goto` 與 `end`、`return` 一樣是終止符。0x081A7699..0x081A77A3 這段 266 位元組的訓練家對戰區域是 `tests/test_script_cmd_table.py` 裡的固定樣例。

## 給運算元命名

`tools/frlg/script_read.py DUMP.bin --base ADDR`：

    0x081A76A8  4F  applymovement 0x800F (VAR_LAST_TALKED), 0x081A77B0
    0x081A76B2  26  specialvar 0x800D (VAR_RESULT), 0x0036 (Script_HasTrainerBeenFought)
    0x081A76BC  06  goto_if 0x05 (!=), 0x081A76CD
    0x081A76C2  25  special 0x0038 (PlayTrainerEncounterMusic)

- 任何命令裡 0x4000 及以上的運算元都是變數引用 [event_data.c:214,235]。`pokeldn/frlg/rom/symbol_names.py` 裡有 274 個變數名和 1470 個標誌位名。
- `scrcmd_args.PARAMS` 給每個運算元命名，並據此選表（`special` 的 u16 查 `gSpecials`，`callstd` 的 u8 查 `gStdScripts`）。
- 條件有 <、=、>、<=、>=、!= 六種 [scrcmd.c:65]。

## 順著指令碼走到它夠得著的地方

`scrcmd.follow` 會追每一個 `goto`、`call`、`goto_if` 和 `call_if`，收集還沒匯出的地址；資料指標只報告，不追。`scrcmd.dump_plan` 把缺的部分變成 `--dump-address` 行。`charmap.decode` 用於名字，`charmap.decode_message` 用於對白。如果一條命令跑過了匯出的末尾，會報告為匯出過短。

# 物種表

`gSpeciesInfo` = 0x0824CDFC，步長 28（反編譯原始碼裡的 26 位元組加上兩個 `00 00` 填充位元組）。它的資料與英文反編譯一致。解析反編譯原始碼時的坑：`[SPECIES_NONE] = {0},` 寫在一行裡、`PERCENT_FEMALE(x)`、`noFlip` 位域，以及十六進位制的 `#define`。

## 由它找到 `CreateMon`

`pokemon.o` 裡第一個 `&gSpeciesInfo` 字面量池屬於 `CreateMon` [pokemon.c:1755]：

| 符號 | 地址 | 依據 |
|---|---|---|
| `CreateMon` | `0x08041150` | 反彙編（`f0b5 4746 80b4 87b0`） |
| `ZeroMonData` | `0x08041090` | 它的第一次呼叫 |
| `CreateBoxMon` | `0x080411C0` | ZeroMonData 與 SetMonData 之間的那次呼叫 |
| `SetMonData` | `0x08043A78` | 以 56（`MON_DATA_LEVEL`）呼叫，再以 64（`MON_DATA_MAIL`）和 255 呼叫 |
| `CalculateMonStats` | `0x08041B78` | 它的最後一次呼叫 |

## 西班牙語火紅卡帶

西語火紅基礎版 v0（`0100EB702342C000`）裡裝著 `FireRed_s.gba`，遊戲代號 `BPRS`，修訂號 0x0A。`builds.BPRS` 與 `vendor/gblink-cards/symbols.json`（語言 id 7）儲存它的地址。

| 符號 | 西語火紅 |
|---|---|
| `gRngValue`、`gSaveBlock1Ptr`、`gSaveBlock2Ptr` | 0x03004220、0x03004228、0x0300422C |
| `gMain`、`gIntrTable[4]`、`gSoundInfo` | 0x030022D0、0x03002730、0x03005F80 |
| `VBlankIntr`、`Client_RunBufferScript` | 0x0800071C、0x08148CD0 |
| `CreateMon`、`GetMonData3`、`Random` | 0x08041164、0x080432F8、0x080486C4 |
| `CB1_Overworld`、`CB2_Overworld`、`RunTextPrinters` | 0x08059E5C、0x08059EDC、0x08002D50 |
| `m4aSoundMain`、`ReadFlash` | 0x081E089C、0x081E224C |
| `MapGridGetElevationAt`、`MapGridGetCollisionAt` | 0x0805C658、0x0805C6D8 |
| 居合斬、碎巖、怪力的訊息返回指標 | 0x081C1909、0x081C19FD、0x081C1AE6 |
| `GetMoney`、`SpeciesToNationalPokedexNum`（表） | 0x080A376C、0x080469A8（0x0824B9DE） |

徽章檢查指向 0x081C1901、0x081C19F5 和 0x081C1ADE 處的訊息指令碼；`EventScript_CurrentTooFast` 從 `0x081AA346`（`lockall`）開始。翻譯過的文本會讓每個恢復指令碼的位置發生變化。`tests/test_frlg_english_cartridges.py`、`tests/test_noclip.py` 和 `tests/test_follower.py` 在有 `scratchpad/frlg_es/FireRed_s.gba` 時用它。

# 法語快捷聊天詞庫

全部 1006 個隨語言變化的快捷聊天詞都從主機 ROM 裡讀出來，寫進 `pokeldn/frlg/text/easychat_french_words.py`；`easychat_french.french(id)` 從那裡作答。

## 槽位問題

一個快捷聊天 id 是 `(group << 9) | index`。`pokeldn/frlg/text/easychat_words.py` 記錄英文 ROM 在每個槽位放了什麼；法版 ROM 放的是別的詞（`EC_WORD_ENJOY` 顯示為 STRESSE，`EC_WORD_DONE` 是 FURAX，`SPEECH/12` 是 LES）。郵件、訓練家卡上的簽名、來訪訓練家、`--denied-message` 以及問卷入口都依賴法語這張表。

## 找到這張表

`sEasyChatGroups[]` 是 22 個 `{ const void *wordData; u16 numWords; u16 numEnabledWords; }` [src/data/easy_chat/easy_chat_groups.h:26]，位於 0x083E3700。它的計數與英文版相同，所以同一個 id 在兩種語言裡都是同一個槽位。詞陣列與文本跨 0x083DE2C8..0x083E3700。`tests/test_easychat_french.py` 要求渲染結果與 ROM 證據一致。`TRAINER/11` 是 DRESSEUR；DRESSEURS 不在表裡。

## 這張表說了什麼

- `EC_GROUP_STATUS`（109 個特性）幾乎是直譯（`stench` PUANTEUR、`thick_fat` ISOGRAISSE、`air_lock` AIR LOCK）。
- `EC_GROUP_FEELINGS` 重新分箱：槽位 13（`disappoints`）是 RAVI，44（`eat`）是 HUMILIE，51（`drink`）是 HONTEUX。
- `EC_GROUP_SPEECH`：LES 和 L' 佔了英文用來放 `case` 和 `miss` 的槽位。

807 個槽位（`EC_GROUP_POKEMON`、`POKEMON_2`、`MOVE_1`、`MOVE_2`）由 `gSpeciesNames` / `gMoveNames` 列印 [easy_chat.c:155]，由主機本地化；`easychat.species_word(55)`、`easychat.move_word(177)` 和 `easychat.is_language_safe` 負責處理它們。

## 用法

```python
from pokeldn.frlg.text import easychat, easychat_french
easychat_french.french(easychat.WORDS["enjoy"])     # 'STRESSE'
easychat_french.render(ids)                          # the line as the console will print it
easychat_french.check(ids, strict=True)              # raises on anything unread or out of range
```

    POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live --keys PROD_KEYS \
        --buffer-script string-gather --gather-address 0x083DF5C0 --gather-count 42 \
        --gather-stride 12 --dump-file DUMP.bin --version firered    # one group per run
    ./.venv/bin/python scratchpad/ec_words.py --group 4 DUMP.bin

葉綠的快捷聊天區域就是火紅的減 0x1C4，詞庫完全相同。

## 國際版修訂 0x0A 卡帶

主持端為英文、法文、德文、義大利文、西班牙文和日文兩個版本都準備了地址表。函式通過與英文 ELF 的唯一指令視窗配對（相對呼叫和指標字面量都做掩碼）；RAM 全域性變數來自字面量池；野外移動指令碼按命令序列配對。`SpeciesToNationalPokedexNum` 是通過共享指令序列的鄰居配出來的。

| 卡帶 | ROM 檔案 | SHA-256 |
|---|---|---|
| `BPRD` | `FireRed_d.gba` | `04f43a43f7cf9109561cd1744d108f50202c931ce31b30abaa6f18950824d20d` |
| `BPRE` | `FireRed_e.gba` | `d32c8df8702293716ad8de68755fe5903161f4829a0a2e486bfa7e74a0b62e94` |
| `BPRF` | `FireRed_f.gba` | `9edf7a3137536b0ccf024a732025da9a0ea1330eb9fd13b2ffed19f5e008c147` |
| `BPRI` | `FireRed_i.gba` | `cf7fa25cf57fbf12f24709efdd1d1aa8056efb4e9b6520ac7d068d3de13ff135` |
| `BPRJ` | `FireRed_j.gba` | `e2cdfb0415ef09e887e9d27b925ff02a713a92f004843490cf6b88b68db6cd01` |
| `BPRS` | `FireRed_s.gba` | `d4dee5aeb5313e073d6067bee37278b0204886958467633978bb746bbe3d5b76` |
| `BPGD` | `LeafGreen_d.gba` | `eb0e340b5efb3ccb7bab104183d2050fa834261dd816c5ad8221e4e98c04342b` |
| `BPGE` | `LeafGreen_e.gba` | `993a8a5695a4f7e4dfe8ceec55beb43e020e82b492854d457d4aa3f864d20f08` |
| `BPGF` | `LeafGreen_f.gba` | `751346c16c0cf3a3ec601d6c2d3c482b54609c5d00ca74f2f668d75b31b8efde` |
| `BPGI` | `LeafGreen_i.gba` | `b99b9c58c83a61b5bd8a1a69b6f21ce0cfab8d1f6065b53b81a323801c9b2895` |
| `BPGJ` | `LeafGreen_j.gba` | `a2aa939a23a36610902be51169042efac78f2f6db6a433e06443a2ee09d4f19e` |
| `BPGS` | `LeafGreen_s.gba` | `a943ecfd6560115b184dc244daed71ba328a67334f343eb35b39932c3ce7c731` |

| 符號 | 德語火紅 | 德語葉綠 | 意語火紅 | 意語葉綠 | 西語葉綠 |
|---|---|---|---|---|---|
| `gmain` | `0x030022D0` | `0x030022D0` | `0x030022D0` | `0x030022D0` | `0x030022D0` |
| `sb1ptr` | `0x03004228` | `0x03004228` | `0x03004228` | `0x03004228` | `0x03004228` |
| `sb2ptr` | `0x0300422C` | `0x0300422C` | `0x0300422C` | `0x0300422C` | `0x0300422C` |
| `rng` | `0x03004220` | `0x03004220` | `0x03004220` | `0x03004220` | `0x03004220` |
| `vblank_intr` | `0x08000730` | `0x08000730` | `0x08000730` | `0x08000730` | `0x0800071C` |
| `create_mon` | `0x08041178` | `0x08041178` | `0x08041164` | `0x08041164` | `0x08041164` |
| `client_run_buffer_script` | `0x08148BA4` | `0x08148B80` | `0x08148BE4` | `0x08148BC0` | `0x08148CAC` |
| `save_slot_layout` | `0x083FCEC0` | `0x083FCCFC` | `0x083F464C` | `0x083F4488` | `0x083F7674` |

依賴 ROM 的測試會在 Unicorn 下跑每版卡帶的 `Client_RunBufferScript`、`CreateMon`、`GetVarPointer`、`VBlankIntr`、存檔鉤子載入器和碰撞函式，並在 mGBA 下跑每張卡。

### 日版佈局

日版火紅與葉綠用的是另一套 EWRAM 佈局：

| 符號 | 日版 |
|---|---|
| 隊伍、隊伍數量 | `0x020241E0`、`0x02023F85` |
| 玩家頭像、物件事件 | `0x02036FA8`、`0x02036D68` |
| 調色盤淡入淡出、停用野生遭遇的位元組 | `0x020379E8`、`0x02038624` |
| `gSpecialVar_0x8000` | `0x02036FE8` |
| `gMain`、`gIntrTable[4]` | `0x030022E0`、`0x03002740` |
| `gRngValue`、`gSaveBlock1Ptr`、`gSaveBlock2Ptr` | `0x03004230`、`0x03004238`、`0x0300423C` |

`RunTextPrinters`（`0x08002D38`）讀的是 `0x02020030` 處的陣列，步長 `0x20`（國際版是 `0x24`）。

SaveBlock1 是 `0x3D40` 位元組（國際版 `0x3D68`）；扇區 id 4 覆蓋 `0xEC0` 位元組（`0xEE8`）。`RamScript` 保持校驗和 `0x361C`、magic `0x3620`、指令碼體 `0x3624`。

神秘卡片是 164 位元組，神秘新聞是 224 位元組。`SaveWonderCard` 是 `0x081481F4`（`BPRJ`）/ `0x081481CC`（`BPGJ`），校驗是 `0x08148250` / `0x08148228`。卡片 CRC 在 SaveBlock1 的 `+0x3204`，資料在 `+0x3208`，新聞在 `+0x3124`。`BufferCardText`（`0x08149934`）讀取標題第 10..27 位元組、副標題 28..40、正文四行每行 20 位元組（41..120）、兩行頁尾每行 20 位元組（121..160）。原生 `.wc3` 佈局見[禮物檔案](gifts.md#native-formats)。

日版的神秘卡片與神秘新聞可接受列表儲存的是活動 6 和 7（`BPRJ` `0x08410EC4`、`0x08410EC8`；`BPGJ` `0x08410E4C`、`0x08410E50`），而其他每版卡帶儲存的是 21 和 22 [src/data/union_room.h:405-406]。可接受的 RFU 序列值是 `{0x0002, 0x7F7F}`（`BPRJ` `0x083FC378`）。十二個標題都把 `0x01006fa0233f8000` 列為它們的第一個本地通訊 id。

日版名字用假名錶，訓練家名字限五個字元；拉丁重音與假名共用位元組值，所以內建禮物文案會去掉重音，並在 26 個字元處折行，一頁兩行。`CreateMon` 把 25 號物種命名為 ピカチュウ。日版隊伍卡沿用其來源的日版結構體大小；有兩處提示被縮短了。

### 正版機驗證

| 卡帶 | 在正版硬體上驗證過 | 來源 |
|---|---|---|
| 意語葉綠（`BPGI`，修訂 `0x0A`） | 全部 41 個 `Build` 欄位與主機記憶體一致；隨行寶可夢安裝；大師球卡片與道具投遞 | [貢獻者驗證](https://github.com/Decryptu/pokeldn/issues/13) |
