---
title: 在主機上執行程式碼
parent: 火紅與葉綠
nav_order: 3
---

# 在主機上執行程式碼

神秘禮物客戶端通過兩個直譯器執行傳送給它的程式碼：`CLI_RUN_MEVENT_SCRIPT`（操作碼 15）把位元組交給神秘事件 VM，`CLI_RUN_BUFFER_SCRIPT`（操作碼 21）則交給 CPU。兩者都不需要故障注入、預先準備的存檔或任何設定；主機始終停在神秘禮物選單上。

本頁的地址針對法語火紅、卡帶 BPRF、軟體版本 0x0A。葉綠的地址見[葉綠](frlg_leafgreen.md)，各張表見[ROM 對映](frlg_rom_map.md)。

# 神秘事件 VM

這是一個獨立的直譯器 [src/mystery_event_script.c]，帶有自己的 17 條命令表 [data/mystery_event_script_cmd_table.s]，與神秘卡片的配送指令碼所編譯到的場地指令碼 VM 不同。`pokeldn/frlg/rom/mystery_event.py` 負責彙編每一條命令（`MysteryEventScript.blob()` 儲存資料，組譯器解析指標）。每個操作碼都在零售硬體上驗證過。

## 命令表

| # | 命令 | 操作碼位元組之後的運算元 | 返回 | 效果 |
|---|---|---|---|---|
| 0 | `nop` |  | FALSE | 無 |
| 1 | `checkcompat` | u32 base, u16, u32, u16, u32 | TRUE | 相容性門閘 |
| 2 | `end` |  | TRUE | `StopScript` |
| 3 | `setmsg` | u8 selector, ptr | FALSE | 當選擇子為 `0xFF` 或等於狀態值時，呼叫 `StringExpandPlaceholders(gStringVar4, str)` |
| 4 | `setstatus` | u8 | FALSE | `ctx->data[2] = value` |
| 5 | `runscript` | ptr | FALSE | 對場地指令碼呼叫 `RunScriptImmediately` |
| 6 | `initramscript` | u8 group, u8 map, u8 object, ptr, ptr | FALSE | 繫結到任意地圖與物件的 `InitRamScript` |
| 7 | `setenigmaberry` | ptr | FALSE | 寫入 `gSaveBlock1Ptr->enigmaBerry` |
| 8 | `giveribbon` | u8 index, u8 ribbonId | FALSE | 給隊伍中每隻非蛋寶可夢一枚禮物緞帶 |
| 9 | `givenationaldex` |  | FALSE | `EnableNationalPokedex()` |
| 10 | `addrareword` | u8 | FALSE | `EnableRareWord`（一句 Easy Chat 流行語） |
| 11 | `setrecordmixinggift` |  | TRUE | 已廢棄：`SetIncompatible` |
| 12 | `givepokemon` | ptr | FALSE | 把完整的 `struct Pokemon` 連同附帶的郵件放入隊伍 |
| 13 | `addtrainer` | ptr | FALSE | 一個 188 位元組的 `BattleTowerEReaderTrainer` |
| 14 | `enableresetrtc` |  | TRUE | 已廢棄：`SetIncompatible` |
| 15 | `checksum` | u32, ptr, ptr | TRUE | 若該範圍內的 `CalcByteArraySum` 不匹配則返回狀態 1 |
| 16 | `crc` | u32, ptr, ptr | TRUE | 同上，改用 `CalcCRC16` |

## `checkcompat` 是可選的

`checkcompat` 出現在每個官方指令碼的開頭，用於校驗語言與版本掩碼（反編譯產物裡的 `LANGUAGE_MASK` 為英語）。指令碼可以跳過它：

```c
bool32 RunMysteryEventScriptCommand(struct ScriptContext *ctx)
{
    if (RunScriptCommand(ctx) && ctx->data[3])   // data[3] is set only by checkcompat
        return TRUE;
    return FALSE;
}
...
while (MEventScript_Run(&ret));
```

`RunScriptCommand` [script.c:107] 在一次呼叫內部迴圈，直到某條命令返回 TRUE。沒有 `checkcompat` 時，`data[3]` 保持為 0：指令碼一直跑到第一條返回 TRUE 的命令（通常是 `end`），外層的 `while` 隨即停止。掩碼從不生效，指標按 `operand - ctx->data[1] + ctx->data[0]` 重定位，其中 `data[1]` 為 0（只有 `checkcompat` 會設定它），`data[0]` 是主機的 1024 位元組 `client->recvBuffer`：運算元 N 表示所傳送內容中的第 N 個位元組。`checkcompat` 是組譯器唯一允許在其後繼續寫程式碼的命令。

## 返回通道

`MEventScript_Run` 把狀態寫入 `client->param` [mystery_event_script.c:75]；`CLI_LOAD_TOSS_RESPONSE` 再把它裝載進 `MG_LINKID_RESPONSE` [mystery_gift_client.c:204]。以下四條客戶端命令會返回一個由指令碼決定的 u32：

    CLI_RECV MG_LINKID_RAM_SCRIPT
    CLI_RUN_MEVENT_SCRIPT
    CLI_LOAD_TOSS_RESPONSE
    CLI_SEND_LOADED

`setstatus` 可以設定任意值。內建的幾種狀態：

| 狀態 | 含義 |
|---|---|
| 0 | 沒有命令設定過 |
| 1 | `setenigmaberry` 無法校驗該樹果，或 `checksum`/`crc` 不匹配 |
| 2 | 成功；每個完成本職工作的操作碼都會設定它 |
| 3 | `SetIncompatible`，或 `givepokemon` 發現隊伍已滿 |

`CLI_COPY_RECV_IF` 與 `CLI_COPY_RECV_IF_N` 可以據此讓客戶端指令碼分支 [mystery_gift_client.c:170]（未使用）。

選單從 `CLI_RETURN` [`GetClientResultMessage`，mystery_gift_menu.c:884] 列印結果，所以 `setmsg` 在這裡不可見。只有成功訊息才會到達 `MG_STATE_SAVE_LOAD_GIFT` [:1379]，否則事件寫入的內容會在重置時丟失；因此 `CLIENT_SCRIPT_MEVENT_DONE` 即使沒有卡片也返回 `CLI_MSG_CARD_RECEIVED`。另一個成功出口 `CLI_MSG_BUFFER_SUCCESS`（13）會列印 `CLI_COPY_MSG` 壓入的 64 位元組。

### 自檢指令碼

`--gift mystery-event-probe` 是無害的：全國圖鑑開啟後 `givenationaldex` 就是空操作，而 `checksum` 只讀取。

    givenationaldex; setstatus 42; checksum 1026, 16, 31

| 狀態 | 含義 |
|---|---|
| 42 | 命令鏈跑到了末尾，且指標運算元是已傳送緩衝區內的偏移 |
| 1 | 命令鏈跑完了，但重定位後的指標沒有落在測試位元組上 |
| 2 | `givenationaldex` 執行了，其後的命令都沒有執行 |
| 0 | 進入了 VM，但沒有命令被執行 |
| 無 | 客戶端指令碼的形態不對，而不是 VM 的問題 |

`checksum` 是終結性的，匹配時保留之前的狀態。零售版火紅會返回 42。

## `givepokemon`

`pokeldn/frlg/save/mevent_pokemon.py` 構建載荷：先是一個 100 位元組的加密隊伍個體，然後是 34 位元組的 `struct Mail`，主機在 `pointer + sizeof(struct Pokemon)` 處讀取它。`--gift mystery-event-celebi` 會送出這樣一隻。與場地指令碼的 `givemon` 不同，它會：

- 附帶郵件。`ItemIsMail` 會做校驗，所以攜帶道具必須是十二種郵件之一 [mail_data.c:167]；`GiveMailToMon2` 把整個結構體（文字、寄件人名字、訓練家 id、物種、道具）複製進 `gSaveBlock1Ptr->mail` [:100]；
- 按全國編號設定 `FLAG_SET_SEEN` 與 `FLAG_SET_CAUGHT`；
- 落在神秘禮物選單：選單關閉時該寶可夢已在隊伍中。

狀態 2 表示成功，3 表示隊伍已滿且什麼都沒寫入。絕不要在它之後放 `setstatus`。

構建器強制規避的陷阱：

- 該個體的 `mail` 位元組必須是 `MAIL_NONE`（0xFF）；0 表示郵件槽 0，會被當作真實郵件讀取；
- `personality == otId` 會使加密金鑰為 0，於是無論打亂與否都能通過校驗，可能發出一個未打亂的個體；
- 隊伍尾部是推匯出來的；全零的尾部讀回來等級為 0；
- 攜帶道具與郵件的 `itemId` 必須一致：`GiveMailToMon2` 會用郵件來設定攜帶道具。

## `initramscript`

`initramscript 3, 0, 2` 把一個場地指令碼繫結到組 3、地圖 0、物件 2，即真新鎮南部的那位胖男士。重啟後他會說出腳本里的臺詞，其中 `{PLAYER}` 會被展開。

`CLI_SAVE_RAM_SCRIPT` 使用 `InitRamScript_NoObjectEvent`（MAP_UNDEFINED，物件 0xFF）[script.c:578]，只有配送員的 `GetSavedRamScriptIfValid` [:554] 會讀取它，而且必須持有一張有效的神秘卡片。真實座標會走 `GetRamScript(gSpecialVar_LastTalked, script)` [:514, field_control_avatar.c:458]，它用該指令碼替代物件自帶的指令碼，並且無視卡片。`gSpecialVar_LastTalked` 是物件的本地 id，按 `map.json` 順序從 1 起。

它會消耗掉那張神秘卡片（[唯一的 RAM 指令碼槽位](frlg_gift.md#the-one-ram-script-slot)）；會話會記錄 "holding no Wonder Card"，直到下一張普通卡片奪回該槽位。繫結期內物件會失去自帶的指令碼：若繫結到某個固定遭遇的物件上，指令碼會取代那個遭遇。

## 陷阱

- `setenigmaberry` 無法設定道具效果。`struct ReceivedEnigmaBerry` [berry.c:944] 有 1322 位元組：`Berry2`（28 位元組）、`u8 unk_001C[0x4FA]`，然後是 `itemEffect[18]`、位於 0x516 的 `holdEffect` 與 `holdEffectParam`，都超出了 1024 位元組的緩衝區；尾部內容是堆上 `recvBuffer` 之後的資料（`build_enigma_berry_blob`；模擬器會報告 `read_past_buffer`）。
- `struct Berry2` 裡的兩個 ROM 描述指標必須從卡帶讀出並原樣送回：樹果袋會永遠從存檔中解引用它們。
- `giveribbon` 的 index 7..10：`GiveGiftRibbonToParty` [pokemon_size_record.c:193] 接受 `index < 11`，但 `sGiftRibbonsMonDataIds` 只有七項被複制進 `u8[8]`，因此 7..10 會用未初始化棧上的欄位 id 去 `SetMonData`。組譯器拒絕 6 以上的值。FRLG 沒有緞帶介面；緞帶只有在傳送之後才可見。
- 沒有終結命令的指令碼會把緩衝區剩餘的全零內容當作操作碼解碼。`assemble()` 與服務端都會拒絕這種指令碼。
- `setrecordmixinggift` 與 `enableresetrtc` 各自只做一次呼叫 `SetIncompatible`，然後中止命令鏈 [mystery_event_script.c:227, :291]。禮物編排器會拒絕它們。
- `addrareword` 與 `setenigmaberry` 在遊戲內不可見；要從存檔讀回來：`additionalPhrases`（SaveBlock1 + 0x2F10，多出一個 Easy Chat 詞）與 `enigmaBerry`（+0x30EC）。它設定的 `VAR_ENIGMA_BERRY_AVAILABLE` 在 FRLG 中沒有別處讀取。

## 接線方式

- `pokeldn/frlg/rom/mystery_event.py`：操作碼、組譯器、反組譯器（`describe`），以及離線客戶端所用的模擬器 `run()`。
- `pokeldn/frlg/gift/mg_script.py`：`CLIENT_SCRIPT_SAVE_CARD_AND_MEVENT`（未持卡：卡片、配送指令碼、事件）、`CLIENT_SCRIPT_RUN_MEVENT`（已持卡：只跑事件，不丟棄任何東西）、`CLIENT_SCRIPT_MEVENT_DONE`（共用的成功尾部）。
- `pokeldn/frlg/gift/mg_server.py`：`SCRIPT_SEND_MYSTERY_EVENT` 配合 `SVR_LOAD_MEVENT` 與 `SVR_READ_MEVENT_STATUS`；狀態落在 `server.mevent_status` 與主機日誌裡。
- `pokeldn/frlg/gift/gift_composer.py`：`WonderGift.mevent` 校驗彙編後的位元組。

# 原生 ARM 程式碼

```c
case CLI_RUN_BUFFER_SCRIPT:
    memcpy(gDecompressionBuffer, client->recvBuffer, MG_LINK_BUFFER_SIZE);
    client->funcId = FUNC_RUN_BUFFER;
    ...
static u32 Client_RunBufferScript(struct MysteryGiftClient * client)
{
    u32 (*func)(u32 *, struct SaveBlock2 *, struct SaveBlock1 *) = (void *)gDecompressionBuffer;
    if (func(&client->param, gSaveBlock2Ptr, gSaveBlock1Ptr) == 1)
```

[mystery_gift_client.c:237,276]。每個載荷都建立在五個事實之上：

- 無論傳送了什麼，都會複製 1024 位元組（`MG_LINK_BUFFER_SIZE`），所以載荷執行時身後是上一次接收的尾部，必須自包含。
- `r0 = &client->param`，`r1 = gSaveBlock2Ptr`，`r2 = gSaveBlock1Ptr`：兩個存檔塊都可讀可寫。
- `client->param` 就是 `CLI_LOAD_TOSS_RESPONSE` 作為 `MG_LINKID_RESPONSE` 送回的東西 [:204]。
- 它每幀被呼叫一次，直到返回 1；永不返回 1 的載荷會卡死神秘禮物選單且無法退出。`memcpy` 只在 `CLI_RUN_BUFFER_SCRIPT` [:239] 處執行一次，因此載荷可以跨幀保持狀態。
- ARM 狀態：呼叫方通過 `bx` 跳到一個字對齊的地址進入。

`gDecompressionBuffer` 位於 0x0201C000（由 `anchors` 實測）。載荷是位置無關的。

## 構建

應用的神秘禮物構建器用同一套工具鏈彙編 ARM 原始碼（`pokeldn/frlg/rom/custom_code.py`），也可以直接接收原始 `.bin`，並在傳送前先讓它在模擬主機上跑一遍。`.pokegift` 檔案攜帶編譯後的 ARM 位元組、卡帶目標與響應設定。[神秘禮物檔案](gifts.md#console-code) 記載了打包與分享方式。

- `asm/*.s`，每個載荷一份 ARM 原始碼，由 `scripts/gen_buffer_scripts.py` 彙編進已提交的 `pokeldn/frlg/rom/buffer_payloads.py`；裝了 `arm-none-eabi-as` 時，`tests/test_buffer_script.py` 會重新彙編並比對。
- `pokeldn/frlg/rom/buffer_script.py`：登錄檔、校驗，以及 `emulate()` / `emulate_repeating`，它們在 unicorn 裡按 GBA 記憶體對映、帶著主機的三個引數執行載荷；出錯或永不返回 1 的載荷上不了天。
- `pokeldn/frlg/gift/mg_script.py`：`CLIENT_SCRIPT_RUN_BUFFER`（接收、執行、裝載返回通道、傳送、接收下一個指令碼）與 `CLIENT_SCRIPT_BUFFER_SUCCESS`。
- `pokeldn/frlg/gift/mg_server.py`：`SCRIPT_RUN_BUFFER_SCRIPT`。沒有卡片，也沒有丟棄提示；已持有的神秘卡片會保留。
- 兩個模擬主機都獨立依據反編譯產物寫成，都以逐幀重入的方式執行載荷：`pokeldn/frlg/gift/mg_client.py` 與 `tests/test_mystery_gift_flow.py` 裡的 `ConsoleClientModel`。

每次都先離線驗證：

    ./.venv/bin/python -m pytest tests/test_buffer_script.py -q
    ./.venv/bin/python scratchpad/mg_client_harness.py --buffer-script -v

在真實硬體上，主機停在神秘禮物 -> 神秘卡片 -> 好友，然後加入主持端。下面的執行命令裡，`HOST` 代指
`POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live --keys PROD_KEYS --dump-file DUMP.bin`，
`IP_HOST` 代指 `./.venv/bin/python -u bin/frlg_mg_host.py --over-ip --dump-file DUMP.bin`，後者通過區域網服務一個模擬主機，不需要無線電也不需要金鑰。在 `DUMP.bin` 出現之前絕不要 SIGTERM 主持端；它是在 `Buffer script dump: N bytes` 之後幾秒才寫出的：

    until ls DUMP.bin >/dev/null 2>&1; do sleep 2; done

## 載荷可以放在哪裡

緩衝區指令碼每幀都會被重新複製，所以它寫進自身映象的任何東西都留不下來。要比選單活得更久的程式碼，得放在遊戲從不寫入的地方：

    0x0203FC00 .. 0x02040000    1024 bytes, above every symbol the game links

最高的有尺寸 EWRAM 符號結束於 0x0203FBAC（[EWRAM 在兩個構建中位於相同地址](frlg_rom_map.md)）。按反編譯產物命名（`gHeap` 的 114688 位元組在符號表裡沒有尺寸），這是唯一未被佔用的 EWRAM 區段；其餘都只是三位元組和八位元組的對齊空洞。

    0x0203F768 .. 0x0203FBAC    1092 bytes, newlib's malloc state

`__malloc_av_` 及其後的 malloc 計數器只被 newlib 的 stdio 訪問，而 stdio 只有 `AGBPrintf` 會呼叫，後者在釋出構建裡並不使用（pokefirered_switch.elf：指向 `_malloc_r`、`_calloc_r` 與 `_free_r` 的 `bl` 全在 libc 內部）。在 mGBA 下跑法語火紅時，在那裡填入 0xA5 後經歷了選單、行走和一整場野生戰鬥仍然存在。GB-Link Team 卡片就把重定位後的指令碼放在那裡（[frlg_gift.md](frlg_gift.md#gb-link-team-cards)）。`scratchpad/ewram_symbol.py ADDR LEN` 可以檢查某個地址。

絕不要因為某個地址讀出來是零就選它。0x0202B280、0x020185C4 與 0x0203B0E9 會讀出數十 KB 的零，它們分別是戰鬥與箱子緩衝區、`gDecompressionBuffer` 之前的一段，以及分配器的記賬區；0x02012304 位於 `gHeap` 內。0x0202B280 落在 `gPokemonStorage` 之中：寫那裡可能落到某隻箱中寶可夢的校驗和上，存檔隨後就會留下一個壞蛋。

軟復位會清空 EWRAM 兩次：`DoSoftReset` 呼叫 `SoftReset(RESET_ALL & ~RESET_SIO_REGS)` [main.c:488]（先 `svc 0x1` 再 `svc 0` [libagbsyscall.s:69]），隨後 `AgbMain` 呼叫 `RegisterRamReset(RESET_ALL)` [main.c:134]；0xFF 的 bit 0 就是 `RESET_EWRAM` [include/gba/syscall.h:4,12]。Switch 封裝層還會重啟模擬主機，所以 `AgbMain` 會跑兩次：每次啟動 `gIntrTable` 與 `INTR_VECTOR`（0x03007FFC）都被清空並重建兩次，其間條目 1、2、7 取無線相關的值（以每秒 328000 次取樣：33.3 ms，再 133.6 ms 到第二次清空，33.6 ms 到其重建）。啟動過程不會重建 0x0203B0E8 以上的任何東西。兩次啟動之間沒有任何東西寫 0x0203FC00..0x02040000：放在那裡的標記能挺過標題畫面、過載、選單、存檔、地圖切換、戰鬥和 PC 箱子，而軟復位（A+B+START+SELECT）會清掉它。

## 逐幀鉤子

`gIntrTable` 在法語卡帶上位於 0x03002720；條目 4 即 V-blank 處理函式，存放 `VBlankIntr`（0x0800071D）。它是十四個函式指標，由 `InitIntrHandlers` 依據 `gIntrTableTemplate` [main.c:339] 一次性寫入，BIOS 通過 `IntrMain` 抵達它，而 0x03007FFC 處的向量儲存著 `IntrMain` 的地址。替換條目 4 就能讓程式碼在每種遊戲狀態下每幀獲得一次呼叫；`gMain.vblankCallback` 與 `gMain.callback2` 則每當選單或戰鬥開始時被重寫。

在某臺主機的 IWRAM 中實測：`IntrMain_Buffer` 為 0x03002760（英文版 0x03002810），`gSaveBlock1Ptr` 為 0x03004228（英文版 0x030042D8），因此在這些地址上卡帶的 IWRAM 比英文構建低 0xB0。IWRAM 不像 EWRAM 那樣能在構建之間平移。

| 條目 | 卡帶 | 英文 | |
|---|---|---|---|
| 0 VCount | 0x08000805 | 0x0800081C | `VCountIntr` |
| 1 Serial | 0x03004B34 | | 鏈路建立期間的一個 IWRAM 處理函式 |
| 2 Timer3 | 0x08005AE1 | | `Timer3Intr`，位於另一個 ROM 段，偏移也不同 |
| 3 HBlank | 0x080007D5 | 0x080007EC | `HBlankIntr` |
| 4 VBlank | 0x0800071D | 0x08000734 | `VBlankIntr` |
| 5, 6, 8-13 | 0x08000885 | 0x0800089C | `IntrDummy`，共八次 |
| 7 | 0x081E0D35 | | RFU 定時器處理函式，`sTimerIntrFunc = gIntrTable + 0x7` [main.c:85] |

無線執行期間，條目 1 與 7 與反編譯產物預測的模板不同；一次會話之後，條目 1 與 2 會保留其無線相關的值，直到復位。遊戲只在 `InitIntrHandlers` 中寫條目 4，而它只在軟復位時重跑。

### 比會話活得更久的程式碼

放在暫存區的一段二十位元組樁程式碼被裝進條目 4，會話關閉之後它在每種遊戲狀態下每幀執行。`asm/resident/vblank-hook.s`：

```arm
    ldr     r0, .Lcounter
    ldr     r1, [r0]
    add     r1, #1
    str     r1, [r0]
    ldr     r0, .Loriginal
    bx      r0                      @ tail branch: lr still points at intr_return
```

`IntrMain` 以 SYS 模式進入處理函式，此時 `lr` 指向 `intr_return`，並允許它覆寫 r0-r3 [crt0.s, `jump_intr`]，所以被替換的處理函式通過自己的 `bx lr` 返回。兩個字面量在傳送前都會被打上補丁。

一個 `call-chain` 會安裝它：先寫那五個字，最後寫條目 4，每次寫入都讀回校驗。

    read32  [0x03002730]                gIntrTable[4], 0x0800071D
    write32 [0x0203FC00] = 0x68014802   the stub
    write32 [0x0203FC04] = 0x60013101
    write32 [0x0203FC08] = 0x47004801
    write32 [0x0203FC0C] = 0x0203FC40   the counter's address
    write32 [0x0203FC10] = 0x0800071D   the handler being replaced
    write32 [0x03002730] = 0x0203FC01   the hook, THUMB bit set
    read32  [0x0203FC40]                the counter

鉤子在每種遊戲狀態下每幀執行一次：在 19995 幀裡，它在選單、標題畫面、大地圖、隊伍選單、一場野生戰鬥以及一次遊戲內重啟之間測得每秒 59.0 到 63.3 次呼叫。軟復位會終止它：`InitIntrHandlers` 重寫條目 4 [main.c:339]（`gIntrTable[4]` 先讀出零，隨後為 0x0800071D）。只有在一次啟動之後才能進入神秘禮物，而啟動會清空 EWRAM，因此一個必須在不開啟新會話的前提下就存在的載荷，需要把安裝器放進存檔。

### 復位之後重新安裝

`--gift resident-hook` 送出一張神秘卡片，其神秘事件指令碼用 `initramscript` 把一個場地指令碼繫結到玩家的母親身上。該繫結存在存檔裡，能挺過斷電（[唯一的 RAM 指令碼槽位](frlg_gift.md#the-one-ram-script-slot)）；在任何一次啟動之後與她對話即可安裝鉤子，不需要鏈路，也不需要主持端。

`asm/field/install-vblank-hook.s`，68 位元組，用 `setptr` 每次六個指令碼位元組暫存，再用 `callnative` 執行：佔 RAM 指令碼體 995 位元組中的 418 位元組。

    read  gIntrTable[4]
    if it already names the stub: return, writing nothing
    write the five words of the V-blank stub to the staging area
    write the handler just read into the stub's fifth word
    zero the counter
    write the staging area, Thumb bit set, into gIntrTable[4], last

尾部目標取自該表，因此鉤子會接上當時在場的任何處理函式。開頭那次檢查是必需的：裝兩次會讓樁程式碼尾跳到自己，從而在中斷處理函式內部空轉，凍結大地圖。

位於 `SaveBlock1 + 0x32E0` 的指令碼塊在軟復位後仍留在重算後的指標處（已在模擬器上驗證）。

指令碼每次安裝都會重建程式碼，所以程式碼受指令碼體大小限制：暫存 162 位元組，或者在最後一條命令之後追加約 755 位元組並用一段跳板抵達。

### 大於指令碼體的載荷

`asm/field/save-loader.s`，64 位元組，無論載荷多重，RAM 指令碼暫存的都是它：它重新讀取 `gSaveBlock2Ptr`，加 0xB20，把 N 個字複製到暫存區，用魔數校驗第一個字（從未寫過的存檔，或後續卡片抵達過的區域），然後跳入。它只用 r0-r3，從不壓棧，因此載荷直接返回 `ScrCmd_callnative` 的呼叫方。

blob 為 936 位元組，一次 `save-write`（`MAX_SAVE_WRITE_BYTES`，即 1024 位元組接收緩衝區減去寫入器）：

    +0x000  magic 0x444C4B50
    +0x004  installer
    +0x054  the V-blank hook
    +0x068  filler
    +0x3A4  checksum over the filler

除非填充區之和正確，否則安裝器什麼都不裝（[證明尺寸](frlg_rng.md#proving-the-size-rather-than-the-jump)）。

存檔副本里鉤子的尾部目標必須是實測的 `VBlankIntr`，絕不能是零：載入器會在一個可能仍活著的鉤子上覆蓋，而第二次到訪時安裝器會發現鉤子已裝好、什麼都不補。那裡若是零，主機在第二次對話之後就會崩潰成黑屏。

無論載荷多大，RAM 指令碼都佔 995 位元組中的 394 位元組。`filler_B20` 有 1024 位元組，存檔裡其他未用區域約 700 位元組。更大的 blob 按每塊 936 位元組分次寫入，一次會話寫一個載荷（[`save-write`](#save-write)）。到滿 1024 時，blob 抵達 EWRAM 頂端，計數器則移入暫存區下方的 84 位元組。除鉤子的第五個字外，暫存的副本與存檔一致；每次安裝暫存的都是同樣的位元組（已在模擬器上驗證，計數器以每秒 60.0 次執行）。

### 呼叫封裝層

GBA 程式碼經由 Sloop 系統呼叫抵達 Switch 模擬器：`swi 0x40` 到 `swi 0x62` 之間有 23 個，缺口在 0x46、0x4E、0x52 以及 0x58 到 0x60 [src/sloopsvc.c]。常駐載荷可以發出其中任意一個：構建器會把一段 `swi N ; bx lr` 的 thunk 連同補進去的編號彙編進 blob。標記在呼叫之前寫下，因為不返回的系統呼叫不會留下任何可讀的東西：

    +0x00  0xB0B00001   the call was reached
    +0x04  the syscall number
    +0x08  0xB0B00002   it returned, and zero until it does
    +0x0C  r0, r1, r2, r3 as the syscall left them

編號較小的那些會執行內嵌的 BIOS：`main` 在檔案偏移 `0x177BAC` 處攜帶 16,384 位元組的 GBA BIOS 映像，其向量表在 `+0`，字串 `Coded by Kawasedo` 在 `+0x2D34`。`swi 0x00..0x2A` 在模擬 CPU 中作為客戶 ARM 程式碼執行。位於 `main+0x57014` 的分派器接管 `0x40..0x62`，把 0x2B 以下的編號留給那份映像。

`swi 0x54`，即 `svc_CommsAllowedByParentalControls` [sloopsvc.c:182]，在沒有家長控制的主機上返回非零。

#### 分派器及其跳轉表

分派器位於 `main + 0x057014`，其跳轉表位於 `main + 0x17D7F6`。它接受 0x40..0x62 範圍內的 `N`：

    cmp   w2, #0x2b ; b.lo default       below 0x2B, the BIOS syscalls
    sub   w9, w19, #0x40 ; cmp w9, #0x22 ; b.hi default
    ldrh  w12, [table, w9, lsl #1]       a u16 word-offset from 0x05706C
    br    base + offset * 4

三十五條表項，二十三個不同的處理函式。`sloopsvc.c` 點名的每個編號都有自己的處理函式。0x46、0x4E 與 0x58 到 0x60 共用預設項，正好是反編譯產物的缺口。0x48 與 0x56 共用一個處理函式（`WriteSector`、`ReplaceSector`）；0x40 與 0x41 共用一個，按編號分支。分派器的 `x0` 是 CPU 物件，`w2` 是編號，`x3` 是其處理函式要讀的暫存器上下文：客戶機的 `r0` 在 `+0x48`，`r1` 在 `+0x4C`（`0x52` 的處理函式在 `mov x20, x3` 之後執行 `ldp w1, w22, [x20, #0x48]`）。

預設項是 `cmp w19, #0x2a ; cset w0, hi ; ret`。那個 `w0` 是封裝層自己的「已處理」布林值，不是客戶機的 r0，所以未實現的編號是無害的（不會卡住），且不動客戶的任何暫存器。傳零進去、讀零出來，等於什麼都沒測。

絕不要在 r0 未選定的情況下單步 0x40..0x62：0x48 與 0x56 要一個扇區號和一個指標，0x4C 結束一次存檔，0x55 交出 SaveBlock2 指標，0x43、0x57、0x61 與 0x62 都要引數。r0 裡的標記會變成垃圾的 flash 來源。

載荷在每次呼叫前重寫自己的 `swi`（沒有指令快取），先寫編號，這樣卡住時能自報家門，並在七個頭部字之後按編號記錄 `r0`（35 個結果，140 位元組）。`p_probe_num_step` 逐步改變編號；`p_probe_a0_step` 在編號步進為零的情況下改變 `r0`。

| 編號 | 輸入 r0 | 輸出 r0 |
| --- | --- | --- |
| `swi 0x52` | `0xA5A00052` | `0` |
| `swi 0x53` | `0xA5C00052` | `1` |
| `swi 0x54` | `0xA5E00052` | `1` |
| `swi 0x55` | `0xA6000052` | `0xA6000052`，未變 |
| `swi 0x56` | `0xA6200052` | 封裝層觸發了故障 |

`swi 0x56`（`ReplaceSector`）若目標被區域表拒絕（r0 裡放標記），模擬器會在 `0xFF8`（`main+0x573F8`）處故障，存檔毫髮無損：

    Invalid memory access at virtual address 0x0000000000000FF8
    PC  = main+0x573F8     LR = main+0x573EC
    x19 = 0x56                  the syscall number
    x22 = 0xA6200052            the guest's r0
    x13 = 0x0203FFC2            the guest's PC, the halfword after the thunk's `swi`
    x03 = 0x655DB09BE8          0x2D0 above the object 0x52's index 45 resolves to

日誌把 `0x0855D3F8` 標為 `gba-app:0x573f8`，據此可定出 `main` 的基址為 0x08506000。

#### `swi 0x52` 與 `swi 0x55`：記憶體匯流排

0x52 有一個反編譯產物裡沒有的處理函式，位於 `main + 0x05728C`：

    ldp   w1, w22, [x20, #0x48]     guest r0 into w1, guest r1 into w22
    lsr   x9, x1, #0x15             r0 >> 21
    ldr   x8, [x21, #0xe0]!         the region table
    and   x9, x9, #0x7f8            bits 3..10, so x9 is a BYTE OFFSET, not an index
    add   x8, x8, x9
    ldr   x0, [x8, #0x50]           the object for this selector
    ldr   x8, [x0]                  its vtable
    ldr   x8, [x8, #0x48]           slot 9
    blr   x8
    mov   x0, x20 ; mov w1, wzr ; mov w2, wzr ; b 0x0855D584

返回值被丟棄：`main + 0x057584` 處的回寫拿到的是 `w1 = wzr`，所以客戶機讀到的永遠是 r0 = 0，r1 到 r3 不變。從大地圖出發、在 45 到 54 號選擇子上（`r0` 以 `1 << 21` 步進），`swi 0x52` 返回 r0 = 0，r1 到 r3 與存檔都不變。`swi 0x55` 位於 `main + 0x057304`，用同樣的移位索引同一張表，呼叫 slot 9，並從 `main + 0x057588` 退出，那裡跳過了回寫；這就是它原樣返回 r0 的原因。

要讀出物件與目標，停在 `blr x8`，即 `main + 0x0572AC`（虛擬地址 `0x0855D2AC`）：`x0` 是物件，`x8` 是 slot 9 的目標，`w1` 是客戶機的 r0。再執行一條指令，返回值仍在 `x0` 中。要普查全部 256 個表項，停在 `ldr x8, [x0]`，即 `main + 0x0572A4`，此時尚未解引用任何東西：空物件或未對映的物件會在那裡故障。

`0x7f8` 用一條指令同時完成掩碼與縮放：

    entry = (r0 >> 24) & 0xFF        and the byte offset is entry * 8

若按 `(r0 >> 21) & 0xFF` 去讀，每個表項都會大八倍。`r0` 是 GBA 地址，而這張表就是記憶體匯流排：最高位元組選擇區域，slot 9 負責該區域的地址摺疊。

| 表項 | 區域 | 物件 | slot 9 |
| --- | --- | --- | --- |
| 0x00 | BIOS | 自有 | `and w0, w1, #0xffffff` |
| 0x01 | 未對映 | 預設物件 | `and w0, w1, #0xffffff` |
| 0x02 | EWRAM，256 KB | 自有 | `and w0, w1, #0x3ffff` |
| 0x03 | IWRAM，32 KB | 自有 | `and w0, w1, #0x7fff` |
| 0x04 | I/O | 自有 | |
| 0x05 | 調色盤，1 KB | 自有 | `and w0, w1, #0x3ff` |
| 0x06 | VRAM，96 KB | 自有 | `and w8, w1, #0x1ffff`，隨後把 `0x18000..0x1FFFF` 向下折 `0x8000` |
| 0x07 | OAM，1 KB | 自有 | `and w0, w1, #0x3ff` |
| 0x08, 0x09 | ROM 等待狀態 0 | 兩者共用一個物件 | `ldr w8, [x0, #0x34] ; and w0, w8, w1`，即卡帶的尺寸掩碼 |
| 0x0A, 0x0B | ROM 等待狀態 1 | 兩者共用一個物件 | 同一張 vtable |
| 0x0C | ROM 等待狀態 2 | 自有 | 同一張 vtable |
| 0x0D | 等待狀態 2 的頂部，EEPROM 所在處 | 自有 | 預設 vtable |
| 0x0E | SRAM | 與其他所有區域物件分開分配 | |
| 0x0F | SRAM 映象 | 自有 | |
| 0x10 到 0xFF | 未對映 | 預設物件 | `and w0, w1, #0xffffff` |

表項 0 到 15 給出 14 個物件和 11 張 vtable。VRAM 的摺疊就是硬體映象（`0x18000` 讀到 `0x10000`，`0x1FFFF` 讀到 `0x17FFF`）。預設物件是 `0x655DB09918`，vtable 為 `main + 0x1C1FB0`，slot 9 為 `main + 0x01F7D8`；它的 slot 10 是 `mov x0, xzr ; ret`，11 是一條裸 `ret`，2 是一個兩次寫入的 setter。每張 vtable 在 `-0x08` 處都有一個空的 typeinfo 指標：沒有 RTTI，也沒有類名。

EWRAM 的 vtable 在 `main + 0x1C21A0`（`x0` 是區域物件，`x1` 是週期計數器，`x2` 是地址，`x3` 是值）：

| slot | 內容 |
| --- | --- |
| 2 | 把兩個字寫進物件 `+0x24` 與 `+0x2C` |
| 3, 4, 5 | 讀 16、32、8 位 |
| 6, 7, 8 | 寫 16、32、8 位 |
| 9 | 把地址摺疊進該區域 |
| 10, 11 | 返回空，以及一個空操作 |

訪問器先計入週期計數器（半字或位元組三次，字六次），然後以 `+0x10` 處的主機後備指標為索引。尺寸在 `+0x20`，ROM 尺寸掩碼在 `+0x34`。

有七個系統呼叫抵達這張表（0x45、0x47、0x48 與 0x56、0x4D、0x52、0x55、0x62），且每個只調用 slot 9；讀寫訪問器屬於模擬器的 CPU 核心。`swi 0x62` 是四條遞增計數器的指令。

要按處理函式自身的控制流來界定它：有幾個在最後一條表項之後還帶著一段行外延續程式碼，若以下一個處理函式的起點為界，就會把它歸錯。

### flash 扇區路徑

`swi 0x48` 與 `swi 0x56` 共用位於 `main + 0x057084` 的處理函式，延續程式碼在 `main + 0x057364`。客戶機的 `r0` 是 4 KB 扇區號，`r1` 是源：

    source      = r1, resolved through the region table and folded
    destination = 0x0E000000 + r0 * 0x1000, resolved the same way

目標地址用 32 位算術生成 [main + 0x05737C]：`0x0E000000 + ((r0 & 0xFFFFF) << 12)`，而區域表項是該地址的最高位元組 [main + 0x057384]：`0x0E + ((r0 & 0xFFFFF) >> 12)` 再對 256 取模，所以實際上是 `r0` 在選擇區域。目標落在 EWRAM、IWRAM 或卡帶緩衝區時能通過兩道邊界檢查（`fold < size`、`size - fold >= 0x1000`）；令 `r0 = 0xFA000 + n`，目標就從任意源區域折進 ROM 副本中 `n * 0x1000` 處的 4 KB（`n` 為 0..0xFFF）。

ROM 目的地址就是對卡帶緩衝區的即時寫入，這一點在 IP 主機下的模擬主機上實測過（未接觸零售主機）：令 `r0 = 0xFA3FF`（`dest` 0x083FF000，`n` = 0x3FF，區域表項 0x08）、源為 EWRAM（`r1` 0x0201C400，fold 0x1C400，掩碼 0x3ffff），兩道門都通過，複製確實落地：卡帶緩衝區 0x3FF000 處的位元組與源自身的 0x1000 位元組完全一致（0x3FF000..0x3FF31F 是選定圖案的 200 個字，隨後 0x3FF320+ 處帶過去的是源自身的尾部位元組，例如第 200 個字在兩處都是 0x11111000）。客戶機隨後在 0x083FF000 處載入，便通過摺疊後的 ROM 視窗讀到該圖案。主機會話保持完好：載荷返回 1，`client->param` 帶著圖案自己的第一個字，主機列印成功訊息並乾淨地關閉鏈路。

以同樣方式複製過來的程式碼可以執行。把源的第 0 個字換成一個兩條指令的 THUMB 例程（`0x47706001`：`str r1,[r0]; bx lr`），第 1..199 個字是圖案；複製完成後載荷讀回摺疊處（`0x47706001`，即那個例程），並帶著 `r1` 裡的 nonce 和 `r0` 裡自己結果字的地址跳到 `0x083FF001`：主機的應答帶回了該 nonce，說明封裝層的取指讀到的正是系統呼叫寫過的同一份即時後備記憶體，複製過來的位元組經由正常取指路徑當作程式碼執行。會話以成功訊息結束，遊戲完成了存檔。

該寫入能挺過軟復位。按 A+B+START+SELECT 之後，摺疊處 0x3FF000 的同一段 4 KB 經偵錯程式讀回逐位元組一致（4096 位元組中 0 位元組變化），而 EWRAM 源暫存區已被清空。復位後開啟的第二次會話讀到 0x083FF000（`0x47706001`）並帶著新的 nonce 跳到 0x083FF001；常駐例程返回了那個 nonce。完整重啟應用則會從模擬器的 ROM 檔案恢復這些位元組：新程序在摺疊處持有的是檔案的原始位元組。寫入的生命週期就是模擬器程序的生命週期。

若區域在 `+0x10` 處的後備指標為空、摺疊偏移等於或超過 `+0x20` 處的尺寸，或剩餘不足 `0x1000` 位元組，則該側被拒絕（指標置空）。兩側都在複製 `0x1000` 位元組之前解析完畢。隨後 `swi 0x56` 會在目標 `+0xFF8` 處寫入 `0xFF`，且沒有空指標檢查：

    cmp   w19, #0x56
    b.ne  exit
    mov   w8, #0xff
    strb  w8, [x21, #0xff8]

`+0xFF8` 是扇區簽名 [pokeldn/frlg/save/save_inject.py]：`0x08012025` 變成 `0x080120FF`，該扇區即作廢。`ReplaceSector` 寫入並作廢，`WriteSector` 只寫入。被拒絕的目標會讓 `x21` 為空，於是 `swi 0x56` 在 `0xFF8` 處故障，即上面那次中止。

在模擬主機上用 `swi 0x48` 實測：

| 呼叫 | 結果 |
| --- | --- |
| `r0` 為超出 flash 尺寸的扇區，`r1` 為未對映區域 | 什麼都沒寫，flash 逐位元組不變，無故障，無凍結 |
| `r0 = 30`，`r1 = 0x08000000`（ROM 頭） | 30 號扇區變成卡帶的前 4 KB，4096/4096 位元組，相鄰扇區未動 |
| `r0 = 30`，`r1` 為載荷填滿的 EWRAM 緩衝區 | 30 號扇區變成那些位元組；緩衝區讀回不變 |
| `r0 = 0xFA3FF`（dest 0x083FF000），`r1` 為 EWRAM 緩衝區 | 複製落在卡帶緩衝區：其摺疊處 0x3FF000 的位元組逐位元組變成源的 4 KB；客戶機在 0x083FF000 讀取返回該圖案；會話乾淨結束 |
| 同樣的複製，但源的第 0 個字是 THUMB 例程，然後帶著 `r1` 裡的 nonce 跳到 `0x083FF001` | 複製過去的例程返回了該 nonce；主機顯示成功、存檔並乾淨關閉 |
| 軟復位之後，用偵錯程式讀同一摺疊處 | 那 4 KB 逐位元組一致（4096 位元組中 0 位元組不同），而 EWRAM 源暫存區已被清空 |
| 復位之後，第二次會話先讀該例程再跳到 `0x083FF001` | 常駐例程返回了一個新的 nonce，並在同一程序內跨復位仍可呼叫 |
| 完整重啟應用之後，用偵錯程式讀同一摺疊處 | 摺疊處恢復為 ROM 檔案的原始位元組；寫入的生命週期即程序的生命週期 |

它不改動任何客戶暫存器，也不返回狀態：只有讀一次 flash 才能分辨呼叫是被接受還是被拒絕。

模擬器只在遊戲存檔時才提交它 128 KiB 的 flash 映像，順手把外來扇區一起帶上。系統呼叫寫入之後強殺程序，主機上的檔案不會變。在神秘禮物會話內部寫入，只要會話以成功訊息結束（該路徑會存檔 [mystery_gift_menu.c:1379]）就是持久的；若是其他結果，或者來自常駐鉤子，則要等下一次存檔。

### 斷點鉤子

封裝層的 GBA CPU 物件在 `cpu + 0x170` 處有 256 個鉤子槽，每個對應一個 `bkpt` 立即數。ARM 解碼測試 `(insn & 0xFFF000FF) == 0xE1200070`，THUMB 解碼在 `main + 0x01FCE4` 處測試 `(insn & 0xFF00) == 0xBE00`；`main + 0x01EFC0` 處的 THUMB 處理函式通過 `main + 0x01F820` 呼叫 `imm8` 槽中鉤子的 vtable slot 2（引數為 hook、`&insn`、`bkpt` 的地址、CPU）。返回 1 的鉤子會讓核心執行它存進 `insn` 的指令；返回 0 或空槽則讓該 `bkpt` 成為空操作。`main + 0x022A2C` 註冊鉤子，並拒絕已佔用的槽。有兩個槽被佔用：

| slot | 歸屬 | 鉤子 | 作用 |
| --- | --- | --- | --- |
| `bkpt #0x52` | Sloop 元件，vtable `main + 0x1C3878` | `main + 0x05499C` -> `main + 0x056368` -> `main + 0x03E850` | 下面那些 librfu 補丁 |
| `bkpt #0xFF` | 應用物件，vtable `main + 0x1B4078` | `main + 0x001140` | 以引數 1 投遞事件 `0x82EF0054`，該事件會退出應用 |

載入時封裝層會往客戶機的 ROM 副本里寫入三處補丁，這是 `0x08000000..0x09000000` 範圍內僅有的十個與卡帶不同的位元組，v0 與 1.0.1 上都是如此（塊校驗和，加上經神秘禮物客戶端的一次讀取，零售與模擬兩邊都驗過）：

| 地址 | 卡帶 | 客戶機 |
| --- | --- | --- |
| `0x081E1696` | THUMB `mov ip, r1`（`468c`） | `bkpt #0x52`（`be52`） |
| `0x081E187C` | ARM `ldr r3, [pc, #0x50]`（`e59f3050`） | `bkpt #0x52`（`e1200572`） |
| `0x081E1F90` | ARM `mov lr, r0, lsr #14`（`e1a0e720`） | `b 0x081E1FB8`（`ea000008`） |

第三處補丁去掉了一個等待迴圈。`0x081E1F74` 處的函式把 `REG_SIOCNT`（`0x04000128`）的 bit 2 與呼叫者的 `r0` 比較（`r0` 先掩到 u16，`lr = r0 >> 14`），當 `[*(0x03000030) + 0x10]` 處的位元組為 1 時提前返回，清掉它並應答 1。在模擬環境裡這個輪詢永遠不匹配，於是封裝層用 `mov r0, #0; return` 替換了函式體：等待立刻應答 0。

`bkpt #0x52` 按地址索引：它的鉤子在 `+0x120` 與 `+0x148` 處各持一條記錄 `{u32 pc, u32 original insn, ..., u32 hits at +0x0C}`，由 `main + 0x0546C0` 匹配地址並返回原始指令。在 `Sio32IDMain` 補丁處（`0x081E1696`）它會解析客戶機的 `r0`（`&gRfuSIO32Id`），並在 `+0x0A` 處寫入 `0x8001`，即 `AgbRFU_checkID` 所等待的介面卡 id [librfu_sio32id.c]。在其他任何地址上執行 `bkpt #0x52`，都會把第二條記錄（`0x081E187C` 補丁）指向自己，並在本次會話餘下的時間裡一直如此。

#### 記錄解析器（`main + 0x03E850`）

鉤子 `main + 0x05499C` 先把 `bkpt` 本身寫進 `insn`，然後以 `x0 - 0x60` 為 `this` 呼叫 `[[x0 - 0x60] + 0x98]` 處的虛擬函式（反彙編，`main + 0x549c4`-`0x549cc`）；對 Sloop 元件而言這解析到 `main + 0x056368`，它推匯出記錄持有者 `[component + 0x40] -> [+0xA8] + 0x68`，並帶著它、`&insn`、`bkpt` 的地址和 CPU 尾調解析器 `main + 0x03E850`（整個映像裡 `0x3e850` 只有一個呼叫者，`0x56378`）。客戶機 `r0` 的最高位元組要到後面、在解析器的 Sio32ID 模擬內部才用於選擇區域。解析器：

- 通過 `main + 0x0546C0` 匹配記錄 1（持有者 `+0x120`）：匹配則把 `+0x0C` 處的命中計數加一，並把 `+0x4` 處的原始指令複製進 `insn`，隨後核心執行它；
- 記錄 1 匹配後繼續進入 Sio32ID 模擬：客戶機的 `r0` 經區域表摺疊，摺疊偏移只按 `offset < region size`（`+0x20`）做邊界檢查，且當持有者 `+0x108` 處的標誌位元組置位時，`strh` 把 `0x8001` 存到 `backing + offset + 0xA`，`main + 0x2209C` 把 `backing + offset + 1` 處的位元組寫進客戶機的 `r1`（`str w2, [regfile + 4 + 0x48]`）。`+0xA` 不在邊界檢查覆蓋範圍內，因此區域最後 `0xA` 位元組內的偏移會寫到該區域後備分配之外，最多超出其末尾 11 位元組；標誌置位而偏移越界時後備指標為空，封裝層會在讀取地址 `0x1` 時故障。標誌清零時解析器直接返回，不做寫入。持有者 `+0x108` 是 `[+0xA8] + 0x170`（持有者為 `[+0xA8] + 0x68`），與下面介面卡的電源開關是同一個位元組：在主機自身的神秘禮物搜尋期間經 `main + 0x03E850` 做了三次即時讀取，每次都發現它是 `0x1`，所以單是 `swi 0x40` 就能開啟寫入路徑。
- 記錄 1 不匹配時重指記錄 2（持有者 `+0x148`）：`record2.pc := the bkpt address`，隨後匹配它，於是核心執行記錄 2 的原始指令，而那條永遠不會被更新：陳舊的 `0x081E187C` 原始指令 `e59f3050`（`ldr r3, [pc, #0x50]`），無論在客戶機從哪個地址、以哪種 CPU 模式執行 `bkpt #0x52`。在主機自身的神秘禮物搜尋中，每次分派都經由這條路徑重指：三次即時讀取期間，記錄 2 的命中計數（持有者 `+0x154`）每 0.33 s 前進約 20，記錄 1 的則不動，說明搜尋畫面每幀跑的是 STWI 驅動自己在 `0x081E187C` 的執行時 IWRAM 副本上的 `bkpt #0x52`，而不是 `Sio32IDMain` 的 ROM 位置。
- 記錄 2 匹配且 `+0x108` 標誌置位時，落入 `main + 0x03E954`：它摺疊持有者 `+0x170` 處存放的地址，在摺疊後的地址讀一個字，用該字的最高位元組作為區域選擇子、用該字本身作為再次摺疊的地址，做邊界檢查，並把持有者 `+0x42B8 + 0x7C` 處的計數器減一。
- 記錄 2 匹配且 `+0x108` 標誌清零時，落入 `main + 0x03E960`：它摺疊持有者 `+0x170` 處存放的地址，在那裡讀一個字，並把其 bit 15 到 26 與 `0x600` 比較。匹配時經同一張區域表摺疊該字的低 24 位，做邊界檢查，並把持有者 `+0x42B8 + 0x7C` 處的計數器減一；不匹配則什麼都不做。

整個觸發器都由客戶機掌控：一個帶著選定 `r0` 跳到 `0x081E1696`（被打補丁的位置，THUMB）的載荷，會讓封裝層在 `fold(r0) + 0xA` 寫入 `0x8001`，並把 `r1` 設為 `fold(r0) + 1` 處的位元組；在其他任何地方執行 `bkpt #0x52` 的載荷，則會在那裡執行陳舊的 `e59f3050`。兩者都是相對客戶機的；`+0xA` 那次寫入是唯一離開客戶機各區域的路徑：它能把 `0x8001` 這兩個常量位元組寫到任何區域後備分配之外，最多超出 11 位元組，包括 16 MB ROM 副本的。

#### ROM 緩衝區之後是什麼：Sloop 元件

ROM 物件的掩碼（`+0x34`）是 `0x1ffffff`，而卡帶只佔 `0x1000000` 位元組，因此 `0xFFFFF6..0xFFFFFF` 這些摺疊能通過邊界檢查，把寫入放到 ROM 緩衝區緊後面的十個位元組上。那裡的物件就是 Sloop 元件（[斷點鉤子](#the-breakpoint-hooks)）：它的第一個字是 vtable 指標 `main + 0x1C3878`，`+8` 是 `0x000004bf`，`+0xC` 是 `0x0A828400`，`+0x18` 與 `+0x20` 是 `main + 0x16EB83`，`+0x28` 是一個 `0x655db` 堆指標，`+0x60` 與 `+0x88` 是更多 vtable（`main + 0x1C3948`、`main + 0x1C3978`），`+0xE0` 是 CPU 匯流排物件。

鄰居在每次啟動之間會變：某次啟動時 ROM 的鄰居是一個首字為 vtable `main + 0x1C36D8`、`+0x60` 為 vtable `main + 0x1C3790` 的物件。建構函式 `main + 0x547CC` 寫的正是這一對，它讀取 `main + 0x86D67E8` 處的靜態指標（加數 `main + 0x1C36C8` [main_relocs.json]）。該類的欄位由它自己的建構函式和它自己的程式碼寫入；客戶會話的任何儲存都到不了那裡。

在被打補丁的位置上，卡帶自身的程式碼會停放它自己的 `r0`（`ldr r0, [pc, #0x10]` 裝載 `0x0300744A`，即它自己的 `&gRfuSIO32Id`，位於 IWRAM），所以遊戲自身的分派總是折到遊戲自己的結構體上：封裝層寫入的 `0x8001` 就是抵達 `gRfuSIO32Id.lastId` 的介面卡 id（`RFU_ID = 0x8001` [librfu.h]），也就是 `AgbRFU_checkID` 等待的那個值。若載荷直接跳到 `0x081E1696`，就跳過了那次裝載並停放自己的 `r0`，這正是讓寫入挪位的原因。

在 strh 本身（`main + 0x3E928`）及其延續程式碼上插樁：直接跳轉並令 `r0 = 0x08FFFFF6` 時，這次儲存的 `x8` 為 `backing + 0xFFFFF6`（`0x66209f9ff6`，其後是尾部的 `ff` 填充），前後轉儲顯示 `0x66209fa000` 在儲存前是 `78 98 6c 08 ...`，儲存後是 `01 80 6c 08 ...`：兩次寫入相隔約 90 ms（先是載荷的觸發，隨後是帶著停放的 `r0` 經同一位置的一次分派）。

寫完元件前兩個位元組後，vtable 指標變成 `0x086C8001`，隨後分派器 `main + 0x1F820` 從它讀取鉤子槽 19（偏移 `+0x98`）：`main + 0x1C2099` 處的八個位元組是 `f7 01 00 00 00 00 00 00`，於是封裝層的下一次虛呼叫會在客戶 PC `0x1F7` 處執行，那是一個沒有其他客戶路徑能抵達的未對映地址。在模擬器上這會中止程序（`Unhandled guest exception InstructionAbortLowerEl`）；同樣的觸發若摺疊落在某區域內，會話只以該區域內的那次寫入收場，不會出現這樣的分派。該位置卡帶自身的程式碼排除了另一個候選：`mov ip, r1` 是把 `ip` 當值存（`mov r0, ip; strh r0, [r4]`），從不經它跳轉。

鉤子只在 `[component + 0x40] -> [+0xA8] + 0x170` 處的位元組置位時起作用：那是虛擬介面卡的電源開關。`swi 0x40` 置位，`swi 0x41` 清零（處理函式 `main + 0x05706C` 存入 `number == 0x40`；[sloopsvc.c:23] 裡的「未被引用的標誌設定器」）。從神秘禮物選單發出 `swi 0x41` 會停掉 RFU 幀：遊戲丟擲鏈路錯誤並離開 LDN。介面卡在軟復位後仍保持關閉，所以下一次進無線選單會報 "L'adaptateur sans fil GBA n'est pas connecté"。該位元組能挺過軟復位；重啟應用或 `swi 0x40` 會恢復它。它每幀被讀取：在一個載荷裡先 `swi 0x41` 再 `swi 0x40` 是無害的。

#### 從 bkpt 到解析器的鏈條

NSO 的 vtable 槽在檔案裡存的是未重定位的加數；載入器再加上映像基址（`main` 在 `0x8506000`）。加上基址之後，客戶機的一條 `bkpt #0x52` 會跑這樣一條鏈：

- 兩條解碼路徑（THUMB `main + 0x1EFE0`，ARM `main + 0x1B7B8`）都以 `(CPU, bkpt address, immediate, &insn)` 呼叫分派器 `main + 0x1F820`；
- 分派器取 hook = `[CPU + (imm & 0xff) * 8 + 0x170]`；對 `bkpt #0x52` 而言那是 `component + 0x60`，即元件的一個子物件（元件就是 GBA CPU 物件：`+0x84` 當前 pc，`+0x170` 鉤子表，`+0x960` 第二張匯流排表，`+0xE0` 匯流排物件）。它讀鉤子自己的 vtable（`main + 0x1C3948`）的槽 `+0x10`，並以 `f(hook, &insn, bkpt address, CPU)` 呼叫它。槽 `+0x10` 直接就是 `main + 0x5499C`；
- `main + 0x5499C` 把 `0xE1200572` 寫進 `insn`，然後裝載 `[component]`，並以 `(component, &insn, bkpt address, CPU)` 尾調 `[that pointer + 0x98]` 處的虛擬函式：`main + 0x1C3878` 的槽 `+0x98` 是 `main + 0x56368`，它推匯出記錄持有者並抵達解析器 `main + 0x03E850`。

因此對元件前十個位元組的一次儲存會在槽 `+0x98` 處被消費；`+0x10` 的讀取發生在鉤子子物件上，在那十個位元組之外。解析器的寫入目標是 `buffer_data + fold + 0xA`，其中的摺疊就是所選區域的 slot 9（[`swi 0x52` 與 `swi 0x55`：記憶體匯流排](#swi-0x52-and-swi-0x55-the-memory-bus)）。

#### 跨區域邊緣的寫入會怎樣

當 `fold = size - 0xB`（在範圍內）時，寫入的一對位元組是 `(size-1, size)`：區域最後一個位元組得到 `0x01`，相鄰分配的第一個位元組得到 `0x80`。當 `fold = size - 0xA` 時，一對是 `(size, size+1)`：`0x01 0x80` 落在鄰居的前兩個位元組上。一次神秘禮物會話每次訪問只允許一次選定的摺疊。

該位置後面的函式體通過一個五字幀返回：它在 `0x081E177C` 的尾聲是 `movs r0,#0 ; pop {r4,r5,r6,r7} ; pop {r1} ; bx r1`。跳到該位置的載荷跳過了函式的序言，必須自己壓入那個幀，並把 `lr` 設在一段延續程式碼上；函式體隨後返回載荷，載荷可以繼續跑程式碼並正常結束會話。壓入其他任何幀的載荷會經由其呼叫者的棧展開，實測執行裡它們會帶著同一個停放的 `r0` 再次進入該位置。

視窗 4 即 GBA IO 暫存器，對映到一個 0x400 位元組的區域物件，它緊挨在自己後備分配之後：後備在匯流排 `+0x14C0`，物件在 `+0x18C0`，按鍵中斷子物件嵌在物件 `+0x88` 處。因此寫入落在匯流排每次 IO 訪問都要經過的那個物件上。映像的 CPU 核心裡有 210 個訪問器形態的呼叫點（[`swi 0x52` 與 `swi 0x55`：記憶體匯流排](#swi-0x52-and-swi-0x55-the-memory-bus)）。

在模擬主機上：

| 寫入 | 讀取處 | 結果 |
| --- | --- | --- |
| 元件位元組對 `01 80`（`0x086C8001`） | 在 `main + 0x1C2099` 讀取槽 `+0x98`，未重定位，為 `0x1f7`（[上文](#what-follows-the-rom-buffer-the-sloop-component)） | |
| 元件位元組 0 為 `0x80`（`0x086C9880`） | `main + 0x5492C`，同一個方法，但沒有 `-0x60` | 它會在已被改寫的元件上重讀 `[x0] + 0x98` 並遞迴進自己；執行緒棧耗盡，程序因資料中止（`InvalidMemoryRegionException`）而死 |
| IO 物件位元組 0 為 `0x80`（`0x086C8480`） | 匯流排的儲存槽 `+0x38`/`+0x40`，它們被替換的目標是裸值 `0xffffffffffffe5e0` 與 `0` | 寫入之後的第一次 IO 儲存會在約 30 ms 內中止程序；那三個載入目標（`main + 0x30EAC`、`main + 0x31114`、`main + 0x36D54`）從不執行 |
| 名稱雜湊塊位元組 0（`0x80`） | 該塊是 SDK 的 binder/surface 描述符物件（`android.gui.IGraphicBufferProducer` 之流是 SDK 映像裡的靜態字串），不是可被分派的物件 | 沒有反應；遊戲跑到自己乾淨的退出 |

寫入 `0x086C8080`（位元組 `80 80`：此後每條 `bkpt #0x52` 都跑純計數器 getter `main + 0x1F7F0`，於是每次 bkpt 都成了空操作）需要兩次寫入且中間不得有分派；一次會話只允許一次寫入，而途中的兩個單寫狀態都會殺死程序。若改用偵錯程式寫入，該指標能在遊戲執行、程序存活的情況下保持五分鐘。映像裡沒有任何程式碼位置會在初始化之後寫封裝層物件的頭部。

#### 一次寫入能造成的全部落點

一次寫入會在鄰居上留下兩種位元組形態之一：首位元組 `80`（區域自己的最後一個位元組拿到 `01`），或在位元組 `k` 與 `k+1` 上寫 `01 80`，`k` 取 0..9。鄰居的前八個位元組是它的 vtable 指標，所以消費者隨後讀到的指標是在檔案映像及其重定位之上解析的。有四種落點會讀到主存的即時內容：

| 物件 | 寫入的位元組 | 改寫後的指標 | 消費者 |
| --- | --- | --- | --- |
| 元件（vtable `main + 0x1C3878`） | `+0` 處為 `80` | `0x086C9880` | `bkpt #0x52` 鏈的 `[P + 0x98]` = `main + 0x1C3918` = `main + 0x5492C` |
| 元件 | `+0..1` 處為 `01 80` | `0x086C8001` | `[P + 0x98]` = `main + 0x1C2099` = 裸值 `0x1F7` |
| IO 物件（vtable `main + 0x1C2408`） | `+0` 處為 `80` | `0x086C8480` | 匯流排訪問器槽，見下文 |
| IO 物件 | `+0..1` 處為 `01 80` | `0x086C8001` | 匯流排訪問器槽：`0x1F7`、零、裸加數 |

其餘落點解析到映像之外。`+1` 處的 `01 80` 給出 `0x08800178`（元件）與 `0x08800108`（IO 物件），都在 main 的 bss 裡。一個按零填充建模的 bss 會預測那裡是空呼叫；僅憑檔案映像無法確定即時會話期間的內容。`+2` 到 `+7` 的 `01 80` 會移動位元組 2 或位元組 3，於是消費者自己的讀取就會故障。在 `+8` 與 `+9` 上，這一對落在 `+8` 處的欄位上（元件的 `0x000004BF` 在 `+8` 變成 `0x00008001`，在 `+9` 變成 `0x008001BF`），vtable 指標原地不動，因此分派的是物件自己的方法。

兩次到訪同一位置時，若其間沒有 `0x04` 訪問發生，就能在 IO 物件上把兩對位元組疊加起來；載荷從 ROM 或 EWRAM 取指本身不訪問該物件。重複同一落點是冪等的，而在 `+8` 或 `+9` 寫入不會改動 vtable 指標。僅限位元組 0 與 1 的不同落點仍可能留下上面某個映像內的指標；改到指標更高位元組的組合需要單獨分析。在元件上，下一次 `bkpt #0x52` 會消費掉當前的寫入。鏈路建立期間 STWI 驅動每秒產生約 60 次這樣的呼叫，但僅憑這個速率並不能斷定每兩次載荷訪問之間一定有一次呼叫介入。

IO 物件被改寫的塊，按匯流排槽列出。訪問類別來自呼叫者的結果掩碼（16 位載入為 `main + 0x18378` 處的 `and #0xffff`，32 位載入為 `main + 0xBDB8` 處的按字迴圈移位，8 位載入為 `main + 0xD914` 處的 `and #0xff`）。

| 匯流排槽 | 訪問 | 改寫後的目標 | 以 IO 物件為 `this` 時 |
| --- | --- | --- | --- |
| `+0x18` | 16 位載入 | `main + 0x30EAC` | 按鍵處理函式的預設分支：`w2` 是完整的 `0x04xxxxxx` 地址，高於該處理函式所 switch 的任何暫存器 id，於是它把 `w3 & 0xffff` 存到 `[x1]`；`main + 0x18330` 處的呼叫點傳入 `x1 = CPU + 0x20` 與 `w3 = 1`，客戶機這次載入返回該處理函式殘留的 `w0` |
| `+0x20` | 32 位載入 | `main + 0x31114` | 以 `(x1 from the site, IO + 0x20)` 呼叫 `main + 0x3580C`，隨後以 `x0 = [[IO + 8] + 0x90]` 尾調 `main + 0x22404` |
| `+0x28` | 8 位載入 | `main + 0x36D54` | 一個 0x76000 位元組物件的一組清理函式：`[x0 + 0x76C70]`、`+0x76C30`、`+0x76C00`、`[x0 + 0x4E68]` |
| `+0x30` | 儲存 | `main + 0x36E40` | `x0 -= 0x1A10`，然後 `main + 0x3664C`，即在重定基後的指標上跑同一組清理函式 |
| `+0x38` | 儲存 | 裸值 `0xFFFFFFFFFFFFE5E0` | 呼叫故障 |
| `+0x40` | 儲存 | `0` | 空呼叫 |
| `+0x48` | | `main + 0x36E4C` | 清理那一組：`+0x76C60`、`+0x76C20`、`+0x76BF0`、`[x0 + 0x4E58]` |
| `+0x68` | | `main + 0x310A8` | `x0 -= 0x10`，然後 `main + 0x30EAC` |

上面這些落點都沒有抵達由客戶記憶體提供的分派目標：四個映像內的落點讀的是 main 自己的資料，IO 物件的那塊則以匯流排的引數呼叫 main 自己的處理函式。

在零售機上（一臺 Switch Lite、英文火紅，載荷由 XIAO ESP32S3 無線電經 LDN 送達），元件寫入與範圍內寫入是靠鏈路拆除來區分的，而不是靠螢幕。每次執行都在指令碼之後約兩秒帶著「發生錯誤，軟體已關閉」回到 HOME，所以這條訊息是通用的；而優雅的 Pia 離開（`Session type 3`）不是：

- 摺疊越過卡帶緩衝區一個位置時（元件，`r0 = 0x08FFFFF6`），主機離開 LDN 時沒有 `Session type 3`，正是模擬器分派裡顯示的那種突然中止，如今出現在硬體上；
- 摺疊在範圍內時（`r0 = 0x08FFFFF0`，寫在緩衝區 `+0xFFFFFA`），以及讓 EWRAM 越尾落到 VRAM 上時（`r0 = 0x0203FFF6`），主機都發出了 `Session type 3` 並優雅離開；普通卡片會話同樣如此。

可見在零售機上，當摺疊越過 ROM 緩衝區末尾時，記錄解析器的這次寫入會觸到一個活的封裝層物件，應用隨即在那裡中止；同樣的寫入留在客戶可見記憶體裡則不會。壓入函式體那個幀的載荷在零售機上也能從該位置返回。

僅憑廣播本身也能結束標題畫面。若主持端信標那個 8 位元組顯示名欄位裡沒有任何 `0xFF`（第三代字串的終止符），標題畫面會在好友列表開啟的同時以同樣的訊息關閉，此時主機還沒發出任何資料包，也還沒加入；主持端的掃描抓包裡沒有 `udp_in`。只要這八個位元組裡任意位置有 `0xFF` 就不會發生，放在欄位外幾個位元組處則不起作用，可見搜尋只在欄位內部進行。正常編碼的名字總以 `0xFF` 結尾，所以這需要一條構造過的廣播；它屬於封裝層一側的中止，與元件寫入無關。

寫入之後的那次分派就是應用的下一條 `bkpt #0x52`。遊戲從兩個地方產生它們：STWI 驅動的 IWRAM 副本，鏈路建立期間每秒約 60 次（對其命中計數的即時讀取）；以及它自己在那個位置對 `Sio32IDMain` 的呼叫（對記錄 1 的一次即時讀取裡 12 次命中）。當 vtable 的低位元組為 `0x80` 時，那次分派抵達 `main + 0x5492C`，它在被改寫的指標上重讀 `[component] + 0x98` 並遞迴，直到執行緒棧越出所在區域；主機回到 HOME 且沒有 `Session type 3`。若載荷把卡帶自己的指令蓋回 IWRAM 副本的 `bkpt #0x52`，並回退卡帶副本的兩處載入期補丁（含兩處位置的那個 4 KB 塊，經 `swi 0x48`），就同時去掉了兩個來源：主機隨後顯示遊戲自己的通訊錯誤，帶著 `Session type 3` 離開 LDN，提交網路報告並繼續執行。那種狀態下被改寫的指標是惰性的，而不是被修復：沒有任何程式碼位置會恢復 vtable。回退後的卡帶副本同樣是程序生命週期的狀態：無線選單此後會報告介面卡未連線，而完整重啟會重新應用封裝層的載入期補丁。

#### 把候選者副本當作 vtable 寫入

`swi 0x45` 是通過候選者列表而不是單個落點來組織它的儲存的。列表裡只有一個候選者（`owner + 0x2770 == 0xB`，計數 1）且 `r0 = 0x08FFFFD7` 時，候選者那 8 位元組顯示名落在 `component + 0` 上，而 `+0x60` 處的 `bkpt #0x52` 鉤子物件仍在這筆寫入範圍之外。那個名字是 slot 位元組 `+0x10..+0x17`（[封裝層自己的掃描流水線](#the-wrappers-own-scan-pipeline)），所以元件的 vtable 指標來自對端的廣播記錄。

下一條 `bkpt #0x52` 會讀 `[component]` 並呼叫 `[component + 0x98]`，因此那種狀態下廣播來的名字就是呼叫目標。這種狀態需要客戶機自己選定的摺疊：遊戲自己的 `swi 0x45` 交出的是 IWRAM 裡的 `gRfuLinkStatus`（[`swi 0x45` 的引數](#the-remaining-syscalls)），這會讓寫入留在 RFU API 緩衝區內，所以僅憑一條廣播到不了任何 vtable。在模擬的法語火紅上實測：廣播名為 `08 01 df 1f 66 00 00 00`（`0x661FDF0108`，落在 ROM 副本內），經 `swi 0x48` 把一整塊 4 KB 的 `0xDEADBEEF` 寫到摺疊 `0xFA3F6`（`ROM + 0x3F6000`），列表裡一個候選者，然後載荷執行 `bkpt #0x52`：

```
Unhandled guest exception PcAlignmentFault at ELR 0xDEADBEEFDEADBEEF (ESR 0x8A000000)
```

`ESR 0x8A000000` 的異常類別為 `0x22`，即 PC 對齊故障，而 `ELR` 持有的是 `[P + 0x98]` 處的八個位元組，此處 `P` 等於廣播來的名字。分支目標是客戶資料。

### 覆蓋範圍

本頁梳理出的客戶路徑包括一次越過區域後備的寫入：解析器在 `fold + 0xA` 處的 `0x8001` strh；被改寫指標的讀取者，其目標取自靜態地址上 `main` 自己的資料（[一次寫入能造成的全部落點](#every-placement-a-single-write-can-make)）。讀到即時記憶體的那四種落點，以及其餘落點會留下什麼，都在那裡列出；低位元組 `80` 寫入之後、會話期間的元件消費者是 `main + 0x5492C`，來自 `bkpt #0x52` 鉤子鏈。單次寫入的普查沒有發現由客戶位元組提供的呼叫目標；它並不覆蓋所有寫入序列。去掉這條鏈的兩個客戶來源後，觀測到的分派就消失了。系統呼叫對元件的儲存及其讀取者見[其餘系統呼叫](#the-remaining-syscalls)；`main + 0x1C36C8` 那個類的欄位由其自身建構函式與自身程式碼寫入（[ROM 緩衝區之後是什麼](#what-follows-the-rom-buffer-the-sloop-component)）。第三處載入期補丁替換了一個等待迴圈。壞詞過濾器的兩個緩衝區在分派器自己的幀內都有長度限制（[壞詞過濾器](#the-bad-word-filter)）；flash 扇區路徑的邊界見 [flash 扇區路徑](#the-flash-sector-path)。

Pia 一側兩端都已解析：客戶機的 `RfuGameData` 與使用者名稱會被重新打包進廣播記錄並做 base85 編碼（[廣播記錄](#the-advertisement-record)）；對端的 `NetworkInfo` 位元組原樣進入候選者列表（[封裝層自己的掃描流水線](#the-wrappers-own-scan-pipeline)）；對端的會話訊息在某個處理函式讀取它們之前先通過按型別的邊界檢查（[Pia 會話訊息分派器](#the-pia-session-message-dispatcher)）。下面的[線路解析一節](#the-pia-librarys-own-wire-parsing)追蹤靜態連結的 `PiaCommon-6_42_1` 從 UDP 套接字到會話佇列的路徑；那條追蹤只描繪路徑，並不覆蓋其中每一次長度檢查和每一個訊息處理函式。

#### 其餘系統呼叫

處理函式地址由 `main + 0x17D7F6` 處的跳轉表給出，即 `main + 0x05706C + entry * 4`。最後一列是一次從神秘禮物客戶端經 `sloop-svc` 發出該呼叫時觀察到的結果。

| swi | 處理函式、被呼叫者 | 作用 | 單次發出時觀察到的結果 |
| --- | --- | --- | --- |
| 0x40, 0x41 | `main + 0x05706C` | 介面卡的電源開關：把 `r0 == 0x40` 存到 `[component + 0x40] -> [+0xA8] + 0x170` | 從神秘禮物選單發出 swi 0x41 會觸發鏈路錯誤並離開 LDN（[上文](#what-follows-the-rom-buffer-the-sloop-component)） |
| 0x42 | 模式切換 `main + 0x0588A0` | `rfu_REQ_startSearchChild` [sloopsvc.c:49]；把網路管理器設為模式 2 | 以鏈路錯誤結束會話；沒有接入點開啟 |
| 0x43 | `main + 0x0570EC` -> `main + 0x058AD0` | `rfu_REQ_startConnectParent`，`r0` 中是 16 位 PID [sloopsvc.c:91]；同一個模式切換 | 緩衝區指令碼作出了回應，隨後在關閉時報 Erreur de connexion |
| 0x44 | `main + 0x057100` -> `main + 0x058B0C` | `rfu_REQ_stopMode`，無引數 [sloopsvc.c:102] | 在 0x43 之後，沒有可見變化 |
| 0x45 | `main + 0x057110` -> `main + 0x058900` | `rfu_REQ_startSearchParent`，用 `gRfuLinkStatus` 呼叫 `rfu_STC_readParentCandidateList` [sloopsvc.c:67-75]；遊戲裝載 IWRAM `0x03003110` 處的指標變數（`0x0800C6EA`，Switch ROM 裡是三條指令），`rfu_initializeAPI` 把它設為 `0x03004710` 的 `sRfuAPIBuffer`；經區域表把封裝層的掃描結果複製進 `struct RfuLinkStatus`，偏移 8 處先是 `findParentCount` [include/librfu.h] | 220 個清零位元組保持為零（禮物會話裡沒有父端搜尋） |
| 0x46 | 跳轉表項 `0x147` | 落到分派器的出口：該呼叫什麼也不做 | |
| 0x47 | `main + 0x05715C` -> `main + 0x058680` | `rfu_REQ_configGameData`，`r0` 指向 `struct RfuGameData`（16 位元組）與使用者名稱（8 位元組，`RFU_USER_NAME_LENGTH`）[sloopsvc.c:34-46; include/link_rfu.h:103-115,232]；若 `activity`（第二個 64 位字的 16-22 位）有變化，就把全部 24 位元組複製到 `component + 0x6050D8`，並把 `activity` 複製到 `component + 0x605360` | `activity` 0x30 在兩處都逐位元組落地 |
| 0x48, 0x56 | `main + 0x057084` | flash 扇區複製：目標扇區是客戶 `r0`，源是經同一區域表摺疊、並針對區域大小做邊界檢查的 `fold(guest r1)`，最多 4 KB | [flash 扇區路徑](#the-flash-sector-path) |
| 0x49 | `main + 0x0571A8` -> `main + 0x0588D0` | 在 `component + 0xD0` 物件上呼叫 `main + 0x0588D0`；不接受客戶引數 | 返回 0 |
| 0x4A | `main + 0x0571B8` -> `main + 0x058AB8` | 在 `component + 0xD0` 上同樣形態 | 返回 0 |
| 0x4B | `main + 0x0572C4` | 無引數；bit 1 令 `RfuMain1` 從 `gHostRfuGameData->compatibility.playerTrainerId` 重播種 RNG，bit 0 清零令 `SpawnGroupLeaderAndMembers` 對組長提前退出 [sloopsvc.c:132-145] | 0 |
| 0x4C | `main + 0x0571CC` | 在 `[component + 0xE8] + 0xA0` 上呼叫 `main + 0x05D930`，它回 0 時再對某個全域性指標呼叫 `main + 0x049D28`；沒有客戶資料抵達兩者 | 返回 0 |
| 0x4D | `main + 0x0571FC` | 壞詞過濾器：解析 `r0` 並最多讀取 `fold(r0)` 處的 256 位元組，[見下文](#the-bad-word-filter) | |
| 0x4E | 跳轉表項 `0x147` | 落到分派器的出口：該呼叫什麼也不做 | |
| 0x4F | `main + 0x057248` -> `main + 0x058B54` | 在棧上構造 `{u16 tag 0x4757; u32 value = r0}`；帶標籤屬性的分派器 `main + 0x4EBD0` 與設定器 `main + 0x058BB4` 把該值未經校驗地存到 `component + 0x6052A0` | 寫入 3 與 `0x7FFFFFFF`，各自後跟 0x49 與 0x4A，沒有觀察到任何變化 |
| 0x50 | getter `main + 0x058BA4` | 讀回同一個 4 位元組計數 | |
| 0x51 | `main + 0x057270` -> `main + 0x0511BC` | 把 `component + 0x3404` 讀進一個出參並清零；該出參總是分派器自己的棧槽 | |
| 0x52 | `main + 0x05728C` | 把客戶 `r0` 經匯流排物件的區域表（`[component + 0xE0] + 0x50`）摺疊，並呼叫該區域的 `+0x48` 摺疊。客戶 `r1` 非零時還會跑指標解析器 `main + 0x562CC`：它以 0..255 的不設界索引讀 `[[bus] + 0x50 + (r1 >> 24) * 8]`，把該值的 `+0x48` 當作虛擬函式呼叫，然後在 `offset < size` 時返回 `backing + offset`。該處理函式是解析器唯一的呼叫者，丟棄其結果並返回 `r0 = 0`，所以客戶 `r1` 讀回 0。即時讀到的 256 項都是 main 自己的方法指標、負值與零，沒有一個物件帶 `+0x48` 方法 | |
| 0x53 | `main + 0x0572D4` | 回答 `component + 0x2770 == 0`（經 `[component + 0xD0]`） | |
| 0x54 | `main + 0x0572EC` | `svc_CommsAllowedByParentalControls` [sloopsvc.c:182] | 返回 1 |
| 0x55 | `main + 0x057304` | 把 `r0` 存到 `component + 0xE1BC`，把存入的字經區域表摺疊並讀回一個位元組（[遊戲報告的素材](#what-the-play-reports-are-built-from)） | |
| 0x57 | `main + 0x057330` | 把 `MonsSelect` 寫入 `component + 0x140` 處的報告副本 | |
| 0x58 到 0x60 | 跳轉表項 `0x147` | 落到分派器的出口：該呼叫什麼也不做 | |
| 0x61 | `main + 0x057340` -> `main + 0x058B2C` | `svc_SetActivity`；只在 0x41 到 0x48（Union Room 的活動碼）時把 `r0` 寫到 `component + 0x605360` | 0x45：在被呼叫者的 `ret`（`main + 0x058B50`）上下斷點，讀到 `w1` 與該欄位都是 0x45；正常關閉 |
| 0x62 | `main + 0x057354` | 把 `component + 0xE1B0` 加 1，即下一份報告的 `CommsError` | |

應答經 `main + 0x2209C` 返回：編號高於 0x2A 時客戶 `r0` = 1，客戶 `r1` = 處理函式的應答字。沒有任何處理函式的應答攜帶封裝層地址。

`component + 0x6052A0` 是 16 位元組：4 位元組計數，4 位元組未使用，一個指向 main 內的 8 位元組指標。剛啟動時：計數 1，指標 `main + 0x1E8D20`，那是一個指標陣列，在唯一有值的槽之後跟著兩個空值。

帶標籤屬性的分派器 `main + 0x4EBD0` 遍歷元件上的監聽者列表：表項 `0xd0` 位元組，在 `component + 0x10`，計數在 `+0x688`，啟用位元組在 `+0x690`；對每個首字為 2 的表項，它以 `entry - 8` 處的 8 位元組與那條帶標籤表項呼叫元件 vtable 的槽 `+0x50`。設定器 `main + 0x058BB4` 就是 `0x4757` 監聽者。`main + 0x50618` 處的 `0x59` 監聽者把 `[tagged entry + 4]` 處的值寫到 `component + 0x3324 + index * 4`，索引取自 `[x2]` 並由 `main + 0x4DB0C` 限制在 0..7。沒有哪個系統呼叫會構造 `0x59` 表項或提供那個第三引數，分派器的十二次呼叫都從封裝層內部欄位構造表項。`0x4757` 監聽者存到 `component + 0x6052A0` 的計數除 getter `main + 0x058BA4`（`swi 0x50`）之外沒有讀者：映像裡其餘構成 `0x6052A0` 或 `0x6052A8` 偏移的程式碼位置，都在初始化時寫入它或它旁邊的指標。`0x4F` 呼叫者提供的值是惰性的。

主機自己的神秘禮物搜尋會在任何緩衝區指令碼之前發出 `swi 0x47`，廣播 `activity` 0x15（`ACTIVITY_WONDER_CARD` [include/constants/union_room.h:46]）；載荷的呼叫會覆蓋它。在 `main + 0x0586B4` 下斷點，經 `x8 + 0x280` 讀到 `component + 0x605360`。遊戲資料物件（vtable `main + 0x1C3B30`）與 CPU/匯流排物件是兄弟：`bkpt #0x52` 的鉤子表解析在後者上（vtable `main + 0x1C3878`、區域表、系統呼叫 0x45、0x48、0x52、0x55、0x62）；兩者的即時地址相差 `0x100000000`。

`swi 0x45` 為每個候選者寫一條定長記錄，而不是複製 `sizeof(struct RfuTgtData)`：在 `dest + 0x14 + n*0x20` 處寫 id、slot、序列號、`+6` 處 15 位元組遊戲名與 `+0x15` 處 8 位元組使用者名稱，`+3` 處是 `mbootFlag`，該 slot 的最後三個位元組保持原樣。剩餘候選者數量寫到 `dest + 8`。一次呼叫最多寫四條記錄然後推進游標，所以更長的列表需要第二次呼叫。因此 `0x18` 這道門在只有一個候選者時越界 `0x19` 位元組，四個候選者時越界 `0x79`；計數從不會讓單次呼叫寫得更寬。

`component + 0x6050D8`，即 `swi 0x47` 複製的那 24 位元組（[main + 0x058694]，一次源自客戶 `r0` 緩衝區的預索引儲存），會被同一個處理函式讀回並重新打包進廣播記錄。`component + 0x605360` 的讀者是 activity 差分 `main + 0x058698`（經 `component + 0x6050E0`）與 `svc_SetActivity` 的設定器 `main + 0x058B40`；兩者都只比較或儲存活動碼。

#### 廣播記錄

`swi 0x47` 處理函式用客戶自己的 `RfuGameData`（16 位元組）與 `gHostRfuUsername`（8 位元組）拼出廣播所攜帶的 24 位元組 RFU 記錄 [include/link_rfu.h:103-115, src/sloopsvc.c:34-46]：

| 記錄 | 來源 |
| --- | --- |
| `[0:2]` | `RfuGameData[2:4]`，訓練家 id（`compatibility.playerTrainerId`） |
| `[2:10]` | 使用者名稱 |
| `[10:12]` | 封裝層的 RFU 會話 id，`main + 0x3F2E0([component + 0x6050D0])` |
| `[12:16]` | `RfuGameData[4:8]`，`partnerInfo` |
| `[16:20]` | 搜尋字，由 `RfuGameData[0:2]` 與 `[8:12]` 打包而成 |
| `[22:24]` | `RfuGameData[8:10]`，`tradeSpecies` |

搜尋字的位，來自兩個源字：0-6 是 activity（`RfuGameData` 第 16-22 位），7 是性別（第 24 位），8-10 是版本（`RfuGameData[0:2]` 第 10-12 位），11-14 是語言（第 0-3 位），15 是 `startedActivity`（第 23 位），16 是 `canLinkNationally`（第 7 位），17 是 `hasNationalDex`（第 8 位），18-23 是 `tradeType`（第 10-15 位），24 是 `gameClear`（第 9 位），25-31 是 `tradeLevel`（第 25-31 位）。`hasNews` 與 `hasCard`（第 4、5 位）不被複制。`[20:22]` 這兩個位元組保持該幀當時的內容。

編碼器 `main + 0x2A90` 每 4 位元組組寫五個字元，低位數字在前，字母表從 `0x23` 起並跳過 `0x5C`，當輸出會超出給定容量時拒絕。處理函式按 24 位元組以容量 `0x20` 呼叫它，於是 30 個字元放得下；文本存到 `component + 0x6C0`，其 `strlen` 存到 `component + 0x700`（`main + 0x15FAE0` 與 `main + 0x15FB20`，即 `strlen`/`memcpy` 的 PLT 樁）。

主機信標克隆的、被捕獲的應用資料（`pokeldn/frlg/link/host_beacon.py`）是 122 位元組：`0x5C` 的 Pia 系統頭，加上 30 個字元，讀回為訓練家 id `0x1050`、名字 `GREEN`、RFU 會話 id `0xac65` 與搜尋字 `0x1584`（activity 4、版本 5、語言 2、第 7 位置位）。

記錄文本進入一個專為這次投遞而建的 advertise-data 建構子（類 vtable `main + 0x1CB8C8`，建構函式 `main + 0x87514`）：`+0x1C` 處是 `0x180` 位元組的 Pia 廣播區，已用大小在 `+0x18`，從 `0x5C` 的頭部起算，應用資料指標 `main + 0xA2C70` = `+0x78`，應用資料大小 `main + 0xA2C90` = 已用大小減 `0x5C`，上限鉗到 `0x124`（槽 `+0x28`，`main + 0x875AC`；頭部偏移 `0x5C` 是槽 `+0x30`，`main + 0x875A4`）。`main + 0xA3480` 經它 `+8` 處持有的緩衝區物件把 30 個字元追加到應用資料偏移處（其容量是緩衝區的 vtable 槽 `+0x28`，已用大小在緩衝區的 `+0x18`，追加會置位緩衝區 `+8` 的第 1 位）；它唯一的呼叫者就是該處理函式（`main + 0x58838`）。處理函式隨後在 `main + 0x58854` 投遞該建構子：`x0 = [component + 0x3528]`，`main + 0xB1304`。那個方法對 `[session + 0xD0]` 調一個方法，把它作為引數傳下去，把 `+0xD8` 處的 u32 清零，並呼叫 `main + 0xD4DD0(x0 = [session + 0x70], x1 = [session + 0xD0], x2 = [session + 0x30], x3 = the builder)`。投遞取 `X = [session + 0x30]`，先過 `X` 的槽 `+0xD8`（須返回 true）與 `+0xE8`（須返回 false）兩道門，再以 `(X, [session + 0x70] + 0x90, builder)` 呼叫 `X` 的 vtable 槽 `+0xA8`。會話的 `+0x30` 由 `main + 0xAF760` 從 `[[session + 8] + 0xB8]` 設定，那是會話所有者的 `+0xB8`。

`X` 具有門面類的形態：`nn::pia::local::LocalFacade`（vtable `main + 0x1CB548`）與 `nn::pia::net::NetFacade`（`main + 0x1CBE60`）共用同一實現，其槽為 `+0xA8` = `main + 0x8D4AC`、`+0xD8` = `main + 0x8D84C`（門面的 `+0x28` 已置位且其 `+0x30` 非空時為 true）、`+0xE8` = `main + 0x8D920`（`[[facade + 0x30] + 0x12D8]` 非零時為 true）。門面的 `main + 0x8D4AC` 經 `main + 0x8C6FC` 校驗，鎖定管理器（從 `[facade + 0x30] + 0x2B8` 經 `main + 0x94B78`，可見門面把管理器放在 `+0x30`），取建構子 `+8` 處的值（`main + 0xA3710`）交給管理器的 `main + 0x99C3C`，然後把傳輸層記到 `[facade + 0x48]`、狀態 8 記到 `[facade + 0x40]`。管理器把緩衝區交給該任務的接收半（見下文），任務的釋出半則經管理器的 blob 建構子抵達 `nn::ldn::SetAdvertiseData`。

元件在 `[component + 0x3528]` 處持有的物件是一個 `nn::pia::session::Session`：填充 `main + 0xAF4E0` 到 `0xB23xx` 的那批方法所屬的類（主 vtable `main + 0x1CE300`，第二個在 `main + 0x1CE330`，建構函式 `main + 0xAF4E0`，它從 `+0x10` 起初始化欄位，並把 `+0xD8` 當 u32 處理）。它的方法設定 `+0x30`（`main + 0xAF760`）、`+0x70`（由 `main + 0xAF9F0` 設定；即時它是一個 `UpdateSessionPropertyJob` 單例，其 `+0x10` 處的 u16 由該設定器維護）與 `+0xD0`（`main + 0xAFA94`），並在 `main + 0xAFB44` 清除它們；投遞呼叫方讀取 `+0x150`、`+0x528`、`+0x70`、`+0x30`、`+0xD0` 與 `+0xD8`，全是 Session 的欄位。元件在 `main + 0x528F8` 處挑選它：從它嵌在 `+0x34A0` 的物件（取其首字）或從重定位槽 `main + 0x1D1AB0` 的全域性（它指向映像之外的 `0x41FB1C8`），並用 `main + 0xB14E0` 開啟，後者把回撥 `main + 0x52BB4` 存到 `+0x88`、把元件存到 `+0x90`。Session 的建構函式在映像裡沒有呼叫者，其 vtable 指標槽只被該建構函式與解構函式裝載，所以這個例項來自本模組之外。即時的形態（模擬的法語火紅、神秘禮物會話；同一個 `main` 映像）：該層是一組 bss 單例：`Session` 在 `main + 0x1029950`，`SessionProtocol` 在 `main + 0x1032000`，所有者在 `main + 0x9E1798`，`LocalFacade` 在 `main + 0x9E15B8`，以及三個會話任務單例在 `main + 0x103FBB0`、`+0x103FCE8` 與 `+0x1040180`（`LeaveMeshWithHostMigrationJob`、`ProcessHostMigrationJob`、`KickoutManageJob`）。會話進行中，`[component + 0x3528]` 正是那個 `Session`，其中 component = `[session + 0x90]`，即系統呼叫分派器收到的物件（它在 `+0x6050D8` 的 RFU 影子持有最後一條記錄：activity `0x15`、使用者名稱各位元組）。`[session + 8]`（所有者；對每個協議也是 `[protocol + 8]`，以及 `[reader + 0x60]`）沒有 vtable：`+0xB8` 是門面，`+0xC8` 是協議管理器。`[session + 0x30]` = `LocalFacade`（已用 typeinfo 核實）。會話任務的 `+0x80` 是 `[SessionProtocol + 0x130]`，即該 Session，它們的 `+0x88` 是 SessionProtocol（其建構函式 `main + 0xCB0D0`：`stp x9, x19, [x20, #0x80]`，`x9 = [x19 + 0x130]`）。

廣播機制屬於另一個物件，`nn::pia::local::LdnBackgroundProcessJob`（類 vtable `main + 0x1CAC48`，`0xA60` 位元組，工廠 `main + 0x7EED8` = 管理器的 vtable 槽 `+0x278`，建構函式 `main + 0x83A88`），它派生自 `nn::pia::net::NetBackgroundProcessJob`（vtable `main + 0x1CB928`），並在 `+0xD8` 嵌入一個 `nn::pia::common::StepSequenceJob::Step`（vtable `main + 0x1C9770`）、在 `+0x320` 嵌入一個 `nn::pia::local::LocalConnectNetworkSetting`（vtable `main + 0x1CA2D0`）。其基類建構函式 `main + 0x875BC` 把網路管理器存到 `+0xA8` 並構建各子物件；它自己的建構函式在 `+0x8C0` 構建 advertise-data 建構子（`main + 0x87514`）。該任務的方法 `main + 0x84260`（vtable 槽 `+0x60`）是接收半：它鎖定管理器（`+0x2B8`），觸碰持有者（對 `[manager + 0x200] + 0xA8` 與 `[manager + 0x2D8]` 調 `main + 0x87374`），經 `main + 0x8885C` 校驗入站緩衝區（緩衝區大小 `main + 0xA2C90` 需在管理器槽 `+0x100` 的限制內，緩衝區 `+0x8` 的第 1 位須置位，`[manager + 0x12D8]` 須為零，`w2 = 8` 的 `main + 0x879C0` 檢查，以及 `[job + 0xA0]` 處的時間戳），把緩衝區 `+0x1C` 處的 `0x180` 位元組廣播區複製進任務 `+0x8C0` 的建構子（`main + 0x87578`），並把任務的下一個步驟設為槽 `0x130`。這條路徑是經任務的 vtable 抵達的：管理器的 `main + 0x99C3C` 把緩衝區交給它存在 `+0x250` 的物件（一個派生自 `StepSequenceJob::Step` 的委託，建構函式 `main + 0xA2824`，`0x98` 位元組，`+0x88` 處有一個 `0x38` 位元組的輔助物件，管理器在 `+0x90`），後者的 `main + 0xA28E4` 以 `(job, helper, buffer)` 呼叫任務的槽 `+0x60`。釋出半是任務的 `+0x130`（`main + 0x84360`），它把任務 `+0x8C0` 的建構子交給管理器的槽 `+0xD0`，在 `main + 0x8445C`。Pia 自己會話任務的步驟裡有八個位置（`main + 0xCB0CC`-`0xCC738`；`nn::pia::session::LeaveMeshWithHostMigrationJob`（vtable `main + 0x1CEB70`）、`nn::pia::session::ProcessHostMigrationJob`（`main + 0x1CEBA0`）、`nn::pia::session::KickoutManageJob`，以及構造槽 `main + 0x1D26F8`-`0x1D2728` 處的那些類）各自以任務 `+0x90` 處的狀態位元組為門，讀取 `+0x80` 處的持有者（即 `[SessionProtocol + 0x130]`，那個 `Session`；已即時核實），並呼叫 `[holder + 0x30]` 的 vtable 槽 `+0x130`；`[holder + 0x30]` 就是 `LocalFacade`（即時 typeinfo），其 `+0x130` 項是 `main + 0x8E0B4`。

這條鏈以封裝層的網路狀態為門，而且是組長一側的路徑。`swi 0x47` 的函式體只在會話非空、`component + 0x690` 的位元組已置位、`component + 0x2770` 至少為 10、且會話謂詞 `main + 0xB06BC` 回答 false 時才投遞（`main + 0x5879C`-`0x587DC`）。`+0x690` 處的位元組就是監聽者列表的啟用標誌：它只在 `[component + 0x6A0] == [component + 0x6A4]`（封裝層那一對掃描與加入）時於 `main + 0x53A58` 置位，並由帶標籤屬性分派器的遍歷（`main + 0x4EBB0`，模式 `-2`）以及向兩者都寫入 `-1` 的拆除流程清除。投遞自身的各道門隨後比較管理器裡的兩個 Pia 地址結構：`X` 的槽 `+0xD8` 尾調到 `main + 0x95C90`，它要求 `[manager + 0x1268]` 與 `[manager + 0x1288]` 都通過 `main + 0x74BE0`（有效地址），並在 `main + 0x74C18` 中比較相等（先比 `+0x18` 的 u16，再比 `+8` 處的 0x10 位元組）；槽 `+0xE8` 要求 `[manager + 0x12D8]` 為零。這兩個結構分別持有封裝層的本地地址（模擬器上是 `127.0.0.1`）與對端地址（主機的 IP），所以這條鏈只在主機是所在網路組長時才跑通。加入方主機的記錄留在影子裡；它的遊戲資料仍經會話抵達父端。

在模擬器上於同一幀內即時確認了全部八跳：`swi 0x47` 攜帶版本 5、語言 2、訓練家 id `0x1234`、activity `0x45` 與使用者名稱 `PKLDNTST`：處理函式的影子接下了那 24 位元組；把門位元組與地址對 poke 成相等後，會話的 `main + 0xB1304` 執行，門面的 `main + 0x8D4AC` 接下棧上的建構子（其應用資料攜帶 30 字元的記錄文本 ``Z8J4;Vk.+>`.uN;#####<P?>######``），管理器的 `main + 0x99C3C` 與其 `+0x250` 委託的 `main + 0xA28E4` 把它傳下去，任務的 `+0x60` 校驗它並把 `0x180` 位元組區域複製進任務 `+0x8C0` 的建構子（`main + 0x87578`），任務的 `+0x130` 由狀態機執行到，管理器的 blob 建構子 `main + 0x80C3C` 帶著同一段記錄文本收到任務的建構子。任務本身作為狀態機執行：它的 `+0x38`/`+0x40` 持有當前步驟（一個帶單位元虛標誌的 vtable 槽，或一個直接函式），基類方法 `main + 0x6EAA0`（“ExecuteCore”，任務的槽 `+0x20`）分派它；觀察到的步驟是 vtable 槽 `0xB8`、`0xC8`、`0xD8`、`0xE8`、`0xF8`、`0x108`、`0x118`、`0x138`、`0x148` 以及 `main + 0x891F0` 之類的直接函式。

管理器類（`nn::pia::local::LdnProtocol`；vtable `main + 0x1CA5B0`，指標在 `main + 0x7E244` 處由重定位槽 `main + 0x1D1E98` 構成）把自己的 `NetworkInfo` 放在 `[manager + 0x2D8] + 0xB8`：廣播大小是 `NetworkInfo + 0x26A`（`+0x322`），blob 是 `NetworkInfo + 0x26C`（`+0x324`），`NetworkInfo + 0x282` 在 `+0x33A`。它的方法 `main + 0x80C3C`（建構子應用資料的唯一消費者；`main + 0xA2C70` 只有這一個呼叫者）清零 `+0x380`（`NetworkInfo + 0x2C8`），把應用資料複製過去，把大小設為應用資料加 `0x5C` 並寫到 `+0x322`，用持有者自己的方法（其 vtable 槽 `+0x68`）把 `0x5C` 位元組的 Pia 系統頭寫到 `+0x324`，然後呼叫 `nn::ldn::SetAdvertiseData(holder + 0x324, size)`（PLT `main + 0x160A90`，GOT `0x1d3800`）。另外兩個管理器方法廣播第二個物件的資料（`main + 0x7F990`、`0x81140`：`[object + 0x18]`，大小為其 vtable 槽 `+0x38` 加 `main + 0x8AC20`），而 `main + 0x80EBC` 在廣播前由 `[manager + 0x128]` 重建持有者。

`component + 0x2770`（經 `[component + 0xD0]`）的讀者是 `swi 0x53`（布林）與 `main + 0x0511CC`、`main + 0x0511F4`，後者沒有系統呼叫能抵達。`main + 0x0511F4` 把它與 10 比較，達到或超過時原子裝載 `component + 0x2790` 處的一個標誌；標誌置位則進入 `main + 0x057250` 的延續程式碼，那裡檢測第三個引數是否為空。其呼叫者尚未確認。

`bkpt #0x52` 的元件還擁有分派器（其 vtable 的槽 21）與 2324 個物種名，各六種語言，用 djb2 雜湊（`main + 0x056540`，字串在 `main + 0x1C4470`）。分派器的幀由所有處理函式共用，是 `0x40` 位元組的儲存暫存器加 `0x310`。

載荷發出 `bkpt #0xFF` 會關閉遊戲：封裝層提交本次會話的遊戲報告、終結 LDN、停止音訊、提交一份由存檔構造的報告、提交存檔並退出。沒有任何應答抵達主機。報告在模擬主機上由 `prepo` 服務打印出來，形如：

| 房間 | 欄位 |
| --- | --- |
| `network`，每個鏈路會話一條 | `Flavor` 66、`Trainer`（32 位訓練家 id）、`Zone`（鏈路活動，神秘禮物為 21 `ACTIVITY_WONDER_CARD`）、`Duration`、`Players`、`Slot`、`Rtt` |
| `game`，退出時 | `Flavor`、`TimeStamp`、`Trainer`、`Gender`、`Duration`、`Badges`（一個位掩碼）、`TotalBadges`、`HallOfFame`、`TotalHallOfFame`、`CompleteRegionalPokedex`、`RegionalPokedexCnt`、`RegionalPokedexCap`、`CompleteNationalPokedex`、`NationalPokedexCnt`、`NationalPokedexCap`、`Distributed`、`LinkExchange`、`LinkBattle`、`MonsNo1..5` 與 `MonsNoNLevel`、`Money`、`CommsError` |

### 遊戲報告的素材

遊戲報告是從 flash 映像解析出來的。`main + 0x05A280` 按扇區頁尾（簽名 `0x08012025`）找最新的槽，把它的 14 個扇區（0xE000 位元組）複製到 `component + 0x140 + 0x70`，`main + 0x05A370` 再用一張按遊戲而定的描述表遍歷它：徽章標誌位、名人堂與圖鑑標誌、與存檔金鑰異或的錢。每個偏移與位索引都來自那張靜態表；複製來的存檔提供的唯一計數 `playerPartyCount`（一個位元組）限制 `main + 0x05AAE0` 處的隊伍遍歷，255 條 0x64 位元組的記錄仍在 0xE000 的副本內。`swi 0x57` 填充 `MonsSelect`（初始寶可夢，經 `main + 0x17DA8C` 的內部編號到全國編號表）；打印出的 JSON 只帶該表的一個固定子集，省略 `MonsSelect`。`swi 0x62` 自增 `component + 0xE1B0`，它會成為 `CommsError`：每次呼叫都讓模擬主機 `prepo` 服務（`ProcessPlayReport`）寫到主機日誌裡的下一份報告中 `CommsError` 加一。`swi 0x55` 存到 `component + 0xE1BC` 的 SaveBlock2 指標，其唯一讀者是 `main + 0x0577D8`，它檢測 `optionsButtonMode == 2`（L=A）。儲存位置就是處理函式本身 `main + 0x057308`：分派器在 `main + 0x057058` 設 `x8 = component + 0xE1B0`，處理函式把客戶的原始 `r0` 存到 `[x8 + 0xC]`。讀者把存入的字經區域表摺疊、做邊界檢查並讀一個位元組，即摺疊區域內的 `+0x13`：兩者都是客戶相對且做過邊界檢查的。

`main + 0x059CE4` 從遊戲程式碼挑選表；應用攜帶全部五張：

| 遊戲程式碼 | 表 | `Flavor` 基值 |
| --- | --- | --- |
| `AXV?` | Ruby | 0x10 |
| `AXP?` | Sapphire | 0x20 |
| `BPE?` | Emerald | 0x30 |
| `BPR?` | FireRed | 0x40 |
| `BPG?` | LeafGreen | 0x50 |

`Flavor` 再加上該語言在 `JEFIDS` 中的索引，所以法語火紅報 `0x42`（66）。

表按 id 順序定址那 14 個扇區，每個 0x1000：位元組偏移 `o` 對應 SaveBlock1 偏移 `((o >> 12) - 1) * 0xF80 + (o & 0xFFF)`。一個標誌是 `(bit, byte)` 對；位號高於 7 表示不存在。對照三個反編譯專案解碼如下：

| 欄位 | 紅寶石 / 藍寶石 | 綠寶石 | 火紅 / 葉綠 |
| --- | --- | --- | --- |
| 徽章，8 個標誌起於 | 位元組 `0x23A0` 第 7 位，`FLAG_BADGE01_GET` 0x807 | `0x23FC` 第 7 位，0x867 | `0x2064` 第 0 位，0x820 |
| `HallOfFame` | `0x23A0` 第 4 位，`FLAG_SYS_GAME_CLEAR` 0x804 | `0x23FC` 第 4 位，0x864 | `0x2065` 第 4 位，0x82C |
| `Money` | `0x1490`（SaveBlock1 + 0x490），無金鑰 | `0x1490`，異或 `0x00AC`（SaveBlock2 `encryptionKey`） | `0x1290`（+0x290），異或 `0x0F20` |
| 隊伍計數、隊伍 | `0x1234`、`0x1238` | `0x1234`、`0x1238` | `0x1034`、`0x1038` |
| `TotalHallOfFame` | `0x25E8`，`GAME_STAT_ENTERED_HOF` | `0x2644` | `0x22A8` |
| `LinkExchange` | `0x2614`，`GAME_STAT_POKEMON_TRADES` | `0x2670` | `0x22D4` |
| `LinkBattle`，取和 | `0x261C..0x2624`，連結勝、負、平 | `0x2678..0x2680` | `0x22DC..0x22E4` |
| 地區圖鑑規模 | 202 | 202 | 151 |

在有金鑰的遊戲裡，遊戲統計量與錢用的金鑰異或。

`Distributed` 是四個位，每一位都是開通前往憑票島嶼的渡船的那個標誌：

| 位 | 標誌 | 紅寶石 / 藍寶石 | 綠寶石 | 火紅 / 葉綠 |
| --- | --- | --- | --- | --- |
| 0 | 肚臍巖（神秘票） | 不存在 | `0x240C` 第 0 位，`FLAG_ENABLE_SHIP_NAVEL_ROCK` 0x8E0 | `0x2069` 第 2 位，0x84A |
| 1 | 誕生島（極光票） | 不存在 | 不存在 | `0x2069` 第 3 位，0x84B |
| 2 | 南方孤島（無限票） | `0x23AA` 第 3 位，`FLAG_SYS_HAS_EON_TICKET` 0x853 | `0x2406` 第 3 位，`FLAG_ENABLE_SHIP_SOUTHERN_ISLAND` 0x8B3 | 不存在 |
| 3 | 遙遠島嶼（古老海圖） | 不存在 | `0x240A` 第 6 位，`FLAG_ENABLE_SHIP_FARAWAY_ISLAND` 0x8D6 | 不存在 |

在火紅與葉綠裡，兩個標誌都由票的神秘事件指令碼置位 [mystery_event_msg.s:222,281]，也由 Switch 版的名人堂授予置位 [post_battle_event_funcs.c:58]；一份已經進過名人堂的存檔被帶過來時報 0。

### 壞詞過濾器

`swi 0x4D`，處理函式 `main + 0x0571FC`，把 `r0` 解析為 GBA 地址，要求其後面有 256 位元組，把 ASCII 字串轉成 UTF-16 並跑平臺的髒詞檢查，就地改寫字串。`r1` 非零會選第二種模式，遊戲從不用（`r1` = 1 以同樣方式掩碼）。遊戲經 `svc_BadWordCheck` 呼叫它，先把名字轉成 ASCII 再轉回 [sloopsvc.c:211]。命名畫面只在它回答 0 時才儲存輸入的名字 [naming_screen.c:686]。

| 送出的字串 | `r0` | 之後的字串 |
| --- | --- | --- |
| `hello world` | 0 | `hello world` |
| `hello fuck` | 1 | `hello ` 然後四個 `0xA1` 位元組 |
| `POKELDN` | 0 | 不變 |
| `ASSASSIN` | 0 | 不變 |
| `NINTENDO` | 0 | 不變 |

路徑 [main + 0x0571FC -> main + 0x057458]：處理函式摺疊 `r0`，要求摺疊處後面有 `0x100` 位元組，並把字串複製進幀 `-0x100` 處的 `0x100` 位元組棧緩衝區（`main + 0x85645F0` 處的複製以其 `w1 = 0x100` 引數為界）。到 UTF-16 的轉換從該緩衝區進行到 `sp + 0x10` 處的 `0x200` 位元組緩衝區（[main + 0x855F100]，`w2 = 0x200`），髒詞檢查經一個全域性指標進行 [main + 0x574AC，被呼叫者 `main + 0x86664C0`]，被掩碼的字串再複製回客戶的摺疊處。兩個緩衝區的末端都在分派器自己 `0x310` 位元組的幀內（`sp + 0x210` 與 `sp + 0x310`）；複製既碰不到儲存暫存器，也越不出幀。替換位元組是常量 `0xA1`。

### 封裝層自己的掃描流水線

封裝層經自己的 PLT 用 `nn::ldn::Scan` 掃描網路（`main + 0x160B70`；`ScanPrivate` 在 `main + 0x160B60`），呼叫點 `main + 0x80944`/`0x8095C` 上的管理器物件是 `x23`，`w2 = 0x18` 個網路，結果進入 `manager + 0x14C0` 處的內聯陣列，24 條 x `0x480`（初始化時清零一次，`main + 0x7E290`）。模擬器自己的 ldn 服務把線路上的 `ScanResponse` 主體直接轉型為 `NetworkInfo` 而不做長度檢查，所以另一席的欄位值原樣抵達封裝層。

一個消費迴圈（`main + 0x80A20..0x80B9C`）遍歷該陣列：它把 `sp + 0x128` 處的 `0x480` 位元組記錄清零（`main + 0x874A0`），把表項轉換進去（`main + 0x87374`：先整塊 `0x480` memcpy 到 `record + 0xB8`，再按位精確讀取欄位：源 `+0xA`、`+0x11`（一次 15 位元組整數解析，`main + 0xA9830`，十/十六/八/二進位制，帶 `b`/`x` 字首，每次推進都做邊界檢查）、`+0x26A`（廣播資料大小）、`+0x281`/`+0x282`、`+0x11A..0x11F`；寫入 record 的 `+0x90`、`+0xA0`、`+0xA2`、`+0xA4`、`+0xA6`、`+0xB0`），然後讓記錄通過一個過濾虛擬函式（`main + 0x80A70`，`LocalSearchNetworkSetting::vfunc2` 在 `main + 0xA0F48`；該設定是 `LdnBackgroundProcessJob` 在 `+0x300` 的子物件，vtable `0x1CB408`）與一個接受虛擬函式（`main + 0x80A94`，站點列表的 `LocalSessionProperty::vfunc11` 在 `main + 0x87420`，它複製記錄並呼叫 `main + 0xA1BAC` 處的 `vfunc17`）。過濾器把設定 `+0x14` 的標誌位元組與屬性的會話 id（`+0x98`）比對，把 u16 `+0xa2` 與 `[setting + 0x12, setting + 0x10]` 比對，把 `+0xa6` 的布林值比對；接受函式複製記錄，把 record `+0x11` 處的 15 位元組雜湊進 `+0x90`，並把標誌存到 `+0xa7`。兩者都不讀顯示名。

被接受的網路進入父端候選者列表：16 個槽 x `0x1A` 位元組在 `owner + 0x6050F2`，寫索引在 `owner + 0x605294`，上限 15（`cmp w8, #0xf; b.le` [main + 0x58C3C]）；陣列止於 `+0x605292`，緊貼索引。填充是所有者類（vtable `main + 0x1C3B30`）的槽 `+0xA0`，即 `main + 0x58BF8`，由 `main + 0x536A4` 對每個掃描結果站點呼叫；站點的名字長度來自站點自己的虛擬函式 [槽 `+0x50`]，而 `sub w8, w0, #1; cmp w8, #0x3f; b.hi` [main + 0x5364C] 在呼叫前丟開 `x6 > 0x40` 的情況。填充內部，`sp + 7` 處的 `0x41` 位元組棧緩衝區接收 `memcpy(sp + 7, x5, x6)`，`x6 > 0x40` 時跳過尾部補零的 memset [main + 0x58C68]：於是 `x6 > 0x40` 時複製會觸及該幀儲存的 `x29`/`x30`（緩衝區偏移 `0x59`/`0x61`）。已解碼的那個呼叫者先做了限幅，所以經它進來的長度最多 `0x40`；映像裡裝載某類槽 `+0xA0` 的八個位置中，`main + 0x536A4` 是唯一確認在該類上分派的。

在模擬主機上實測，一個主機在做廣播：計數 1，slot 0 = 該主機的廣播逐位元組相同：16 位元組遊戲資料（activity `0x15`）、8 位元組顯示名、父端 id u16（`0x59f1`）。

在 `main` 裡，該列表只經填充那一族函式寫入（`main + 0x58BB4`、`0x58BE4`、`0x58BF8`），全是虛擬函式；映像裡其餘以元件為錨的訪問都是讀。所有者類的 vtable 指標 `main + 0x1C3B30` 在 `main` 裡由裝載重定位槽 `main + 0x1D1B38`（值為 `main + 0x1C3B20`）再加 `0x10` 構成：`main + 0x58558` 在清零 `component + 0x6050F0` 候選者列表時存入它，兩個元件初始化函數里的 `main + 0x58FD8`/`0x59054` 同樣如此。同樣的寫法構成管理器類的指標（槽 `main + 0x1D1E98`；`main + 0x7E244`、`0x7E4D0`）與會話類的指標（槽 `main + 0x1D2770`；`main + 0xB7D24`、`0xB7E78`）。

### Pia 會話訊息分派器

封裝層原生的 Pia 會話接收是 `main + 0xB9FC0` 處的一個型別 switch。它遍歷一條節點鏈：`[node + 0x10]` 是訊息體，其首位元組是型別，而節點自己的前三個位元組是用作佇列鍵的協議地址。當管理器物件的 `[x0 + 0xA0]` 非零且型別不超過 `0x11` 時，節點被分派；switch 是 `adr x8, main + 0xB9FD0`（`main + 0xB9FCC`）、`ldrb w9, [main + 0x180FC9 + type]`（`main + 0xB9FC4`；`main + 0xB9EFC` 處是 `adr x27, main + 0x180FC9`）、`add x8, x8, w9, lsl #2`、`br x8`。`main + 0x180FC9` 處的位元組表每個型別一項；十八個 case 塊位於 `main + 0xB9FD0 + index * 4`，每塊以無條件的 `b main + 0xB9F80` 結束，並各自呼叫其處理函式（`main + 0xBCB60`、`main + 0xBE438`、`main + 0xBE8BC` 等）。

每個處理函式都在觸碰訊息前按訊息長度做邊界檢查：型別 1 的處理函式 `main + 0xBE438` 以 `cmp w2, #0x15; b.ne` 開頭（只有 `0x15` 位元組的訊息才走到複製），審計解碼出的各型別測試為：型別 2 `>= 4`，型別 3 `== 0x16 or 0x22`，型別 4 `== 0xf`，型別 6 `>= 0xf`，型別 9 `== 0x1e or 0x2a`，型別 10 與 12 `== 0x15`，型別 11 `>= 0xe`，型別 13 `== 0xa`，型別 14 `>= 0x4d`，型別 17 `>= 0xd`。變長讀取函式 `main + 0xC0D90` 由位計數推位元組數，與宣告長度比較，不足即拒絕。這一組裡沒有發現哪個處理函式會把訊息控制的長度複製進定長緩衝區。

這些型別就是 Pia 會話協議自己的訊息型別；主機的會話層（`pokeldn/ldn/pia_connect.py`）把它們編號為 0 加入請求、1 加入確認、2 加入響應、3 離開請求、4 離開響應、5 更新、6 更新確認、7 開始主機遷移、8 遷移確認。型別 1 的處理函式 `main + 0xBE438` 把 21 位元組的訊息讀作 `[0]` 型別、`[1:9]` 與 `[9:0xB]` 源站點的常量 id 與變數 id、`[0xB:0x13]` 與 `[0x13:0x15]` 目的站點的對應值，除非目的這一對與傳輸層自己的（`[transport + 0x1B8]`、`+0x1C0`）相符，否則拒絕，然後查出源站點並在其上呼叫 `main + 0xC9B4C`。型別 2 的處理函式 `main + 0xBE8BC` 接受 4 位元組及以上，以管理器的狀態位元組（`+0x30 == 0xFD`）為門，並按訊息第 3 位元組在 3 到 0x10 之間 switch。

接收路徑的所有者是會話類（`nn::pia::session::SessionProtocol`；vtable 基址 `main + 0x1CE8E0`；其 vtable 指標在 `main + 0xB7D24`/`0xB7E78` 處由重定位槽 `main + 0x1D2770` 構成，建構函式是 `main + 0xB7E70`）。泵是該類 vtable 的槽 `+0x50`，即 `main + 0xB9CA0`，它呼叫遍歷器 `main + 0xB9DB0`；這條鏈掛在 `[protocol + 0xF8]` 處的物件（會話包讀取器，由協議管理器掛上）的 `+0x70` 表上（`main + 0xD6D68` 返回該地址）。訊息物件由 `main + 0xD4430` 構造（其 vtable 指標來自重定位槽 `main + 0x1D27B0`）。Pia 庫本身靜態連結在 `main` 裡（映像帶有 `SDK MW+Nintendo+PiaCommon-6_42_1-Release` 與會話任務名）。

### Pia 庫自己的線路解析

`main` 連結了整套 Pia 6.42.1 棧（映像帶有 `PiaCommon`、`PiaLocal`、`PiaNet`、`PiaSession`、`PiaTransport` 與 `Pia_ZStandard` 的 `SDK MW+Nintendo+...` 發行字串，以及改寫後的類名）。上文只按 vtable 指稱的類對應如下：

| 上文說法 | 類（vtable typeinfo 裡的改寫名） | vtable |
| --- | --- | --- |
| 網路管理器 | `nn::pia::local::LdnProtocol` | `main + 0x1CA5B0` |
| 會話物件（建構子在 `+0x8C0`） | `nn::pia::local::LdnBackgroundProcessJob` | `main + 0x1CAC48` |
| 會話類（接收路徑） | `nn::pia::session::SessionProtocol` | `main + 0x1CE8E0` |
| 包物件 | `nn::pia::common::Packet::Header` | `main + 0x1CA100` |
| 本地接收流 | `nn::pia::local::LocalInputStream` | `main + 0x1CA540` |
| 網路接收流 | `nn::pia::net::NetInputStream` | `main + 0x1CC1D0` |

傳輸類的 vtable 是 `PacketReader` `main + 0x1CF1A8`（第二個在 `main + 0x1CE7E8`）、`PacketWriter` `main + 0x1CF258`、`ProtocolManager` `main + 0x1CF3A0`、`ProtocolMessageReader` `main + 0x1CF458`、`ProtocolMessageWriter` `main + 0x1CF490`、`ReliableProtocol` `main + 0x1CF4C8`、`Station` `main + 0x1CF8C8`、`StationManager` `main + 0x1CF938`、`ReceiveThreadStream` `main + 0x1CFB20`、`SendThreadStream` `main + 0x1CFB68`；會話類的是 `Session` `main + 0x1CE300`、`SessionPacketReader` `main + 0x1CE748`、`SessionPacketWriter` `main + 0x1CE7F8`、`SessionStation` `main + 0x1CED20`；本地類的是 `LocalProtocol` `main + 0x1CA9B0`、`LocalService` `main + 0x1CB460`、`LocalFacade` `main + 0x1CB548`。

**包。** 包物件是 `0x1D18` 位元組：解析後的頭部在 `+8` 到 `+0x24`，資料包緩衝區在 `+0x30`（容量 `0x1C5C`，即追加輔助函式 `main + 0x75664` 與 `main + 0x75694` 中的界，後者在 `+0x14` 記錄頁尾大小），收到的大小在 `+0x1C90`（本地接收路徑在 `main + 0x7DE40` 處、一次 `0x5AC` 位元組接收並針對該上限檢查之後寫入）。它的解析（`main + 0x752D4`，vtable 槽 `+0x18`；入口 `main + 0x752C8` 提供物件自己的緩衝區與常量 `0x1C5C`）要求多於 `0x1C` 位元組，並讀取 `0x1D` 位元組的頭部：

| 位置 | 大小 | 含義 | 落到 |
| --- | --- | --- | --- |
| 0x00 | 4 | 魔數 `0x32AB9864`，大端 | `+0x08` |
| 0x04 | 1 | 版本在第 0-6 位，加密標誌 `0x80` | `+0x0C` |
| 0x05 | 1 | 一個位元組，原樣保留 | `+0x0D` |
| 0x06 | 2 | 目的變數 id，大端 | `+0x0E` |
| 0x08 | 2 | 源變數 id，大端 | `+0x10` |
| 0x0A | 2 | 包 id，大端 | `+0x12` |
| 0x0C | 1 | 頁尾大小 | `+0x14` |
| 0x0D | 8 | nonce，原樣保留 | `+0x15` |
| 0x15 | 8 | GCM 標籤，原樣保留 | `+0x1D` |

本應用使用的版本是 `0x10`（16）：有效性檢查 `main + 0x75610` 要求魔數、`([+0xC] & 0x7F) == 0x10` 且 `size - 0x1D < 0x1C40`。載荷指標是 `+0x4D`（緩衝區越過頭部之處，`main + 0x75474`）；`main + 0x75458` 返回 `buffer + t`，其中 `t = (n + 0x1D)` 按 32 位算術計算，當 `(t >> 2) > 0x716` 時返回空。該容量檢查允許 `t` 到 `0x1C5B`；訊息遍歷器則另行按收到的大小減去頭尾頁尾來檢查（`main + 0xDE278`）。

**套接字與接收流。** 套接字是一個小的持有者（建構函式 `main + 0x6D93C`：`+0` 處 fd `-1`，`+4` 處一個計數，`+8` 協議族，`+0xC` 協議）；`main + 0x6D95C` 開啟它（`nn::socket::Socket`，PLT `main + 0x160940`），`main + 0x6DBF4` 關閉（`main + 0x160950`），`main + 0x6DCD0` 繫結（`main + 0x160960`），`main + 0x6DE6C`、`0x6DF44`、`0x6E00C`、`0x6E0F0` 設定選項（`main + 0x160970`）。資料包呼叫是 `main + 0x6E1D0`（`nn::socket::RecvFrom`，PLT `main + 0x160980`，標誌 `0x80`，源地址由 `main + 0x6E9D0` 轉回）與 `main + 0x6E538`（`nn::socket::SendTo`，`main + 0x160990`）。本地接收流（變數 id 在 `+0x88`，鎖在 `+0x68`，套接字持有者指標在 `+0x18`）跑泵 `main + 0x7DD10`（vtable 槽 `+0x10`）：它接進一個包的緩衝區並把頭部解析進去（`main + 0x7DDEC`；`main + 0x6E1C8` 是 thunk）；包過濾器 `main + 0x91280`（槽 `+0x20`）首先要求包有效。當版本至少為 7、頁尾非空、目的變數 id 至多為 1 時，頁尾必須至少含兩個位元組，且流自己的 id（`+0x88`）必須非零並出現在它的那些大端 u16 收件 id 中（`footer_size >> 1` 項）。另外，當 `([+0xC] & 0x7E) >= 6` 且目的為 2 或更大時，它必須等於流自己的 `+0x88`。

過濾器把收件指標算作 `packet + (size - footer) + 0x30`，那是 `main + 0x912EC` 處 `sub w8, w8, w9` 之後；訊息遍歷器 `main + 0xD6460` 與解析器 `main + 0xDE278` 把遍歷上界算作 `size - footer - 0x1d`（`main + 0xD651C`、`main + 0xDE298`）。這兩個減法都不以頁尾大小是否裝得進資料包為條件。頁尾大小位元組是資料包偏移 12，在明文頭部裡，所以對端可以隨意設定它。頁尾大小超過資料包大小不會讓過濾器故障：六個 31 位元組、頁尾 `0x40` 的資料包都到達了套接字，會話繼續跑下去（在模擬器上實測）。

**執行緒。** 傳輸層的接收與傳送迴圈是名為 "Pia ReceiveThreadStream"（在 `main + 0xE9020` 啟動，名字經 `main + 0xE9034` 的 `adr`）與 "Pia SendThreadStream"（`main + 0xEA758`）的 `nn::os` 執行緒，經 `main + 0xF6010` 建立（`nn::os::CreateThread`，PLT `main + 0x15FDF0`，以及 `StartThread`，`main + 0x15FE00`）。

**從線路到會話處理函式。** 收到的會話訊息由會話包讀取器解析，並留在按地址索引的表裡，會話協議每次更新都遍歷該表。

`nn::pia::session::SessionPacketReader`（vtable `main + 0x1CE748`）繼承 `nn::pia::transport::PacketReader`（vtable `main + 0x1CF1A8`）。讀取器的 `+0x30` 方法（`main + 0xD5DE0`）處理收到的包，並呼叫 `main + 0xD6460(reader, packet)` 遍歷其中的訊息。遍歷器從資料包偏移 `0x1D` 開始，在 `packet_size - footer_size` 之前停下（`main + 0xDE278`、`0xD6510`-`0xD6538`）；頁尾跟在載荷之後。它用 `main + 0x74EA8` 解析每條訊息，並經讀取器的 `+0x78` 虛擬函式取用作佇列鍵的協議地址（`main + 0xD6D0C`：訊息 `+0x2C` 處的 u16，外加 `+0x2E` 處的位元組作為其高位），然後呼叫 `main + 0xD6944(table, address, message)`。

該表內嵌在 `reader + 0x70`：`+0` 處是 u32 桶數，`+8` 處是指向桶陣列的指標（每桶 0x18 位元組，鏈頭在 `+0`，鏈尾在 `+8`），`+0x40` 處是可選的雜湊回撥。`main + 0xD6944` 先裝載陣列指標，再加 `index * 0x18`；桶並不內聯在表裡。桶索引是 `callback(address) % count`，沒有設定回撥時是 `(address[0] + address[1] + address[2]) % count`。`main + 0xD71F0(bucket, address, message)` 取一個節點，把訊息複製進去（三個地址位元組在 `+0`，訊息體指標在 `+0x10`，id 在 `+0x18`，更多欄位在 `+0x20` 到 `+0x30`，其餘經 `main + 0x74C54`），並把它追加到該桶的雙向連結串列（next 在 `+0x78`，prev 在 `+0x80`）。

協議一側：`nn::pia::session::SessionProtocol` 的 `+0x50` 虛擬函式（`main + 0xB9CA0`）每次更新都跑 `main + 0xB9DB0`。它讀取 `[protocol + 0xF8]`（即讀取器，掛接方式見下），取讀取器 `+0x70` 處的表，為協議自己的三位元組地址算出桶（`+0x120` 處的 u16 加 `+0x122` 處的位元組，由 `+0x18` 虛擬函式 `main + 0x828E4` 讀取；這一對是 `nn::pia::transport::Protocol` 的欄位，由 `main + 0xDA614` 設定），遍歷鏈，並按 `[node + 0x10]` 處訊息體的首位元組經跳轉表把每個節點分派給各處理函式（`main + 0xBCB60`、`main + 0xBE438`、`main + 0xBE8BC`、`main + 0xBF2D4` 等），引數是 `(protocol, node, id)`。

掛接：協議管理器（內嵌在所有者 `+0xC8`，其協議表在 `+0x18`）遍歷自己的表，用所有者的 `+0xF8` 與 `+0x100` 設定每個協議的 `+0xF0` 與 `+0xF8`（設定器 `main + 0xDA8C8` 與 `main + 0xDA8D0`，廣播 `main + 0xDB740`，在 `main + 0xEC0E4` 以那一對呼叫；任一引數為零即拒絕）。`+0xF8` 那個物件就是讀取器，這就是遍歷器用的表是讀取器 `+0x70` 的原因。

即時情形：管理器位於 `[session + 8] + 0xC8`（即上面的所有者），它在 `[manager + 0x18]` 的表裡 `+0` 是 u32 桶數、`+8` 是桶陣列指標。每個桶 `0x18` 位元組：`+0` 是一個節點，節點的 `+8` 是協議，節點的 `+0x30` 鏈向下一個節點。在模擬的會話裡，該表計數為 `19`，正好六個協議，每種一個，以協議地址為鍵（u16；`+0x122` 處的位元組為零，每個協議的 `+0x108` 持有網路的 Pia var，`0x8fa2`/`0x0766`）：`0xfd01` `nn::pia::local::LdnProtocol`、`0xfd03` `nn::pia::transport::RttProtocol`、`0xfd05` `nn::pia::transport::UnreliableProtocol`、`0xfd0a` `nn::pia::transport::ReliableProtocol`、`0xfd0d` `nn::pia::session::SessionProtocol`、`0xfd0f` `nn::pia::transport::MonitoringDataProtocol`。這些協議每種一個，不是每站點一個：`SessionProtocol` 的泵在 8 次裡 8 次都追蹤到同一個例項，讀取器表的節點也歸在協議地址下（`0xfd0a`，訊息 id `0x60`）。例項由 `main + 0xB1F60` 建立並註冊（經 `main + 0xDB114` 分配 `0xD8E8` 位元組，建構函式 `main + 0xB7D0C`，以地址對為鍵插入管理器的對映）；Session 的建構函式呼叫它一次，並把返回的地址存到 `+0x12`/`+0x14`。

`nn::pia::transport::Protocol` 基類（vtable `main + 0x1CF308`，建構函式 `main + 0xDA548`，vtable 指標來自重定位槽 `main + 0x1D2808`）攜帶三位元組地址在 `+0x120`/`+0x122`，鎖在 `+0xC8`，掛接的那一對在 `+0xF0`/`+0xF8`，兩個 8 位元組加 u16 的配置值在 `+0x100`/`+0x108` 與 `+0x110`/`+0x118`，狀態位元組在 `+0x123`，標誌在 `+0xD8`。

## 改指主機的出站訊息

`r0` 就是 `&client->param`，所以 `struct MysteryGiftClient` [include/mystery_gift_client.h:71] 相對它有固定偏移：

| 欄位 | 相對 `r0` |
| --- | --- |
| `client->sendBuffer` | 0x10 |
| `client->link.sendSize` | 0x34 |
| `client->link.sendBuffer` | 0x3C |

`MysteryGiftLink_InitSend` 會存下傳給它的指標 [mystery_gift_link.c:59]；CRC 在傳送時對 `link->sendBuffer` 的 `link->sendSize` 位元組計算 [:166]。在 InitSend 與傳送之間執行的載荷，可以把主機的出站訊息指向任意地址：

    CLI_RECV -> CLI_LOAD_TOSS_RESPONSE -> CLI_RUN_BUFFER_SCRIPT -> CLI_SEND_LOADED

順序反過來時，InitSend 會覆蓋載荷的改動。

絕不要匯出在 CRC 幀與傳送幀之間會變的區域：

```c
case 0:  header.crc = CalcCRC16WithTable(link->sendBuffer, link->sendSize);   // one frame
case 1:  SendBlock(0, link->sendBuffer + blocksize, ...);                     // the next
case 2:  if (CalcCRC16WithTable(...) != link->sendCRC) LinkRfu_FatalError();  // the one after
```

[mystery_gift_link.c:155]。`gRngValue`（0x03004220）每幀推進兩步；對它的匯出會讓訊息體 CRC 失敗，主機報「erreur de connexion」。`buffer_script.build_memory_dump` 會拒絕任何與它重疊的範圍；繞開它匯出，或改用 `rng-trace`，後者經 4 位元組通道把它返回。其他任何易變區域也得用同樣辦法找。

## 各載荷

### `trainer-id-probe`

24 位元組，只讀。主機幾秒前就已在 `MysteryGiftLinkGameData` 裡送出了自己的 `playerTrainerId` [mystery_gift.c:337]，所以答案是已知的。

```arm
    ldrh    r3, [r1, #0x0A]         @ SaveBlock2.playerTrainerId[0..1]
    ldrh    ip, [r1, #0x0C]         @ SaveBlock2.playerTrainerId[2..3]
    orr     r3, r3, ip, lsl #16
    str     r3, [r0]                @ *param
    mov     r0, #1
    bx      lr
```

若相符，說明它確實以 ARM 狀態執行、用的是反編譯裡的引數、指向真的 `gSaveBlock2Ptr`，並返回 1；值不同說明引數或偏移不對；沒有 `Buffer script status:` 行，說明客戶端指令碼的形態不對，或呼叫根本沒到。7 個字元的玩家名，其終止符會覆蓋遊戲資料裡的 `playerTrainerId[0]` [mystery_gift.c:364]；主機於是比較高三個位元組。

### `save-dump` 與 `memory-dump`

`memory-dump` 取絕對地址。`save-dump` 經 r1 與 r2 在任意構建上按任意偏移讀任一存檔塊。每次執行最多 1024 位元組；再多 `MGL_Receive` 會拒絕 [mystery_gift_link.c:102]。

    HOST --buffer-script save-dump --dump-block sav2 --dump-size 256 --version firered
    HOST --buffer-script memory-dump --dump-address 0x0201C000 --version firered

它們能到達 0x0038 處的 `SaveBlock1.playerParty`、0x0290 處與 0xF20 的 `SaveBlock2.encryptionKey` 異或的 `money`、背包、flags 與 vars，以及 IWRAM（`gRngValue`）。

### `memory-dump-multi` 與 `memory-dump-scatter`

`MG_LINK_BUFFER_SIZE` 限的是一條訊息，不是一次會話。客戶端從其 1024 位元組接收緩衝區裡跑一串命令 [mystery_gift_client.c:140]，而匯出那三步

    CLI_LOAD_TOSS_RESPONSE -> CLI_RUN_BUFFER_SCRIPT -> CLI_SEND_LOADED

會盡可能多地重複：每條命令 8 位元組、迴圈外還有三條固定命令時，能跑 41 輪。`mg_script.MAX_DUMP_BLOCKS` 把它壓在 32，因為中途死掉的會話會丟掉所有塊。16 KB 的匯出在 ESP32 無線電上花了約 57 秒，塊間隔約 2.5 秒。

`CLI_RUN_BUFFER_SCRIPT` 每一輪都會重新複製映像 [:238]，所以游標放在 `client->param` 裡：每輪發送 `base + index * 1024` 並傳出下一個索引。高半字裡沒有 `0x5A5A0000` 的 `param` 視為第零輪。

`memory-dump-scatter` 改為索引一張基址表：

    adr     r3, .Ltable
    ldr     r3, [r3, r1, lsl #2]    @ this block's own base
    str     r3, [r0, #0x3C]         @ client->link.sendBuffer

`adr` 是 PC 相對的。32 個槽全部填寫，未用的填成最後一個地址，於是多跑一輪只會重發一個已持有的塊，而不是把訊息指向 0。分散的塊每次加入能抓到的短函式體約為連續塊的四倍；對某一組超過一兆位元組、166 個從未讀到的函式體：

| 一次加入、從線路上取 16 KB | 抓到的函式體 |
|---|---|
| `memory-dump-multi`，在最佳基址處取十六個連續塊 | 22 |
| `memory-dump-scatter`，最密的十六個 KB | 83 |
| `memory-dump-scatter`，32 塊 | 119 / 166 |

可讀性檢查覆蓋每個分散塊。各塊端到端落到一個檔案裡；`--dump-scatter A,B,C` 讓 `script_read.dumps` 把每塊放到它自己的基址，標記為 `<run>[0]`、`<run>[1]`……`--dump-blocks 1` 會逐位元組返回 `CLIENT_SCRIPT_DUMP_MEMORY`。

### `anchors`

把十一個字寫進 `client->sendBuffer`，並把 `link->sendSize` 加寬到 44；不需要改指，因為 `CLI_LOAD_TOSS_RESPONSE` 已經把 `link->sendBuffer` 指向那裡 [MysteryGiftClient_InitSendWord, mystery_gift_client.c:91]。

| 字 | 內容 | 某次啟動 |
| --- | --- | --- |
| 0 | `sub ip, pc, #8`：主機把程式碼放在哪 | 0x0201C000 |
| 1 | `lr`：呼叫之後的 ROM 地址 [mystery_gift_client.c:276]，第 0 位置位，因為呼叫者是 THUMB | 0x08148C75 |
| 2 | `sp` | 0x03007DB8 |
| 3 | `r0` = `&client->param`，即 `AllocZeroed` 把客戶端放進 `gHeap` 的位置 | 0x020020D4 |
| 4-5 | gSaveBlock2Ptr、gSaveBlock1Ptr | 0x02024598、0x0202553C |
| 6-9 | 四個 AllocZeroed 緩衝區：send、recv、script、msg | 0x02006510 .. 0x02007140 |
| 10 | InitSend 留下的 `link->sendBuffer`；必須等於字 6 | 0x02006510 |

字 4-5 在每場戰鬥與每次讀取後都會變 [load_save.c:75]；字 3 與 6-9 取決於堆狀態。字 1 錨定一個反編譯呼叫點；字 10 等於字 6 證實結構體偏移。各緩衝區相隔 0x410（1024 位元組加 16 位元組塊頭），與 `malloc.c` 的描述一致。`buffer_script.describe_anchors` 會連同它的一致性檢查列印全部十一個字。

### `save-write`

把載荷尾部複製進塊，然後把 `link->sendBuffer` 指向目標，於是應答就是存檔現在持有的內容。會話以 `CLI_MSG_BUFFER_SUCCESS` 結束，它抵達 `MG_STATE_SAVE_LOAD_GIFT` 並把寫入提交到 flash；從標題畫面重新讀取後它依然存在。

    HOST --buffer-script save-write --dump-block sav2 --dump-offset 0xB20 \
        --write-text "some text" --version firered

一條載荷攜帶 936 位元組。更長的資料按 936 分片，每片一條載荷，全都在同一次會話裡依次執行；客戶端按其命令表接收並執行它們 [mystery_gift_client.c:145, 236]。應答就是最後一片之下存檔持有的內容。

`build_save_write` 拒絕 `struct SaveBlock2` 中 0x090 的 `filler_90[8]` 與 0xB20 的 `filler_B20[0x400]` 之外的任何區間 [global.h:345,357]，而 `src/` 裡沒有任何東西引用它們。`filler_B20` 之後四個位元組就是 `encryptionKey`，錢會與它異或。`--write-unsafe` 可以強制覆蓋。塊落到 flash 的哪裡是輪換的（[id 住在哪裡](#where-an-id-lives-and-which-sector-carries-the-slots-counter)）。

一次 `save-write` 只改動它點名的區間：一次 256 位元組寫入改動了 SaveBlock2 的 196 位元組，全在區間內，SaveBlock1 一個位元組沒動。遊戲裡沒有任何東西寫 `filler_B20`：寫在那裡能跨存檔留存（實測十代），跨神秘事件、神秘卡片、軟復位與遊玩留存（一分鐘遊玩中 SaveBlock1 有 1456 位元組變動，而那 256 位元組未變）。

### `memory-scan`

取一個 32 位搜尋值和一段範圍。每次呼叫掃完它那批 32 位元組塊，把游標寫回自己的映像並返回 0；走到盡頭的那次呼叫把 `link->sendBuffer` 改指結果並返回 1。映像開頭是一條跳過其引數的分支：

| 偏移 | |
|---|---|
| 0x000 | `b .Lcode` |
| 0x004 | 游標：起始地址，由載荷推進 |
| 0x008 | 結束 |
| 0x00C | 搜尋值 |
| 0x010 | 每次呼叫的塊數 |
| 0x014 | max_calls，看門狗 |
| 0x018 | 結果：命中數、最終游標、用掉的呼叫數、已存命中 |
| 0x028 | 結果：64 × (地址, 值) |
| 0x228 | 程式碼 |

這個預算保護需要幀的 RFU 鏈路。內層迴圈是一次八字的 `ldmia` 與八條鏈式 `cmpne`，每八字約 14 條指令；預設的 512 塊在 unicorn 上每次呼叫是 7703 條指令，從 EWRAM 取指（16 位匯流排，一次 ARM 取指約 6 週期）約佔一幀 280896 週期裡的 60000。16 MB 卡帶是 1024 次呼叫，約 17 秒。`--scan-blocks` 可以改它；全程主機每秒讀約 60 個子幀。

`max_calls` 預設是範圍所需次數加二；看門狗叫停時會以一個短游標作答，說明從哪裡繼續。應答總是 528 位元組，所以 `len(dump) == buffer_dump_size` 就證明改指成功。`found` 統計所有命中，`hits` 保留前 64 個。`ldmia` 只看字對齊的命中：若搜尋值相對於真實步長從不對齊，就只會返回零。

### `table-scan`

按形狀找表：每一段最長的 `runlen` 字連續段，其中每個字恰好比前一個高 `delta`，以該段起點與首值作答。`gSpecialVars` [data/event_scripts.s:51] 列出 `gSpecialVar_0x8000` 到 `0x800B`，十二個連續的 `u16` [event_data.c:16]，所以它的前十二個字步長為 2，首值是 `&gSpecialVar_0x8000`。

    HOST --buffer-script table-scan --table-delta 2 --table-runlen 12 \
        --table-start 0x08140000 --table-end 0x08400000 --version firered

第 12 項是 `gSpecialVar_Facing`，宣告在 `Result` 與 `LastTalked` 之後，比第 11 項高 6，所以該段恰好是十二個，13 就找不到任何東西。

形狀測試每個字約 7 條指令，按值找約 1.75 條，所以 `TABLE_SCAN_DEFAULT_BLOCKS` 是 192 個 16 位元組塊，負載與 `memory-scan` 的 512 個 32 位元組塊相同。`run`、`runstart` 與 `expect` 放在 0x22C..0x234，緊挨游標，每次讓出都會儲存，因為一段可能橫跨 `ldmia` 與幀邊界。`expect` 從 0 起，所以首字為零會被記給一段未寫 `runstart` 的段；`read_table_scan` 會丟棄範圍外的命中。

同一形狀能找到活動的 `struct ScriptContext`：`InitScriptContext` 把命令表及其末尾存在 +0x5C 與 +0x60 [include/script.h]，17 項的表相差 68，所以對 EWRAM 用 `--table-delta 0x44 --table-runlen 2` 會以該 context 的地址與該表的地址作答。context 在指令碼跑過之前全是零，所以掃描必須在同一次啟動裡跟在神秘事件禮物之後。`--table-delta 0x358`（214 項）能找到野外指令碼的 context，其 `cmdTable` 就是已知的 `gScriptCmdTable`。

### `rom-checksum`

按最多 128 塊對一段求範圍，每塊一個和，於是主機就能點名卡帶上與它的 ROM 映像不同的塊；對某一塊再用更小的塊跑第二次，就能縮小範圍。幀迴圈、預算、看門狗與改指傳送都沿用 `memory-scan` 的。每塊從 0 起按升序把字相加：

    acc = w + ror(acc, 31)          one `add r0, rN, r0, ror #31` per word, mod 2^32

`rom_checksum_reference` 從 ROM 檔案算出同樣的和。XOR 會互相抵消（重複的字和為 0；相隔 32 字的等量變化會抵消）。超出參照映像的塊按它的和命名：全零、全 0xFF、開匯流排（每個半字各自取地址的一半）、映象，或 CONTENT。

| 偏移 | |
|---|---|
| 0x000 | `b .Lcode` |
| 0x004 | 游標：起始地址，由載荷推進 |
| 0x008 | 結束 |
| 0x00C | 起始 |
| 0x010 | 每次呼叫的 32 位元組塊數 |
| 0x014 | max_calls，看門狗 |
| 0x018 | shift：塊大小的 log2，5 到 25 |
| 0x01C | 進行中那塊的累計和，跨呼叫攜帶 |
| 0x020 | 結果：最終游標、用掉的呼叫數、已存的和、回顯的 shift |
| 0x030 | 結果：128 × u32 塊和 |
| 0x230 | 程式碼 |

應答是從 0x020 起的 528 位元組。建構子拒絕起點不對齊到塊、範圍不是整數塊、超過 128 塊、以及不是 32 位元組到 2 的冪的塊大小。每八字 13 條指令；512 個塊每次呼叫 6688 條指令。預設的 0x08000000..0x09000000 按 128 KiB 分塊是 1024 次呼叫，約 17 秒。

    HOST --buffer-script rom-checksum --version firered
    HOST --buffer-script rom-checksum --sum-start 0x08120000 --sum-end 0x08140000 \
        --sum-block 0x400 --version firered

主機會記錄每塊的範圍、兩個和，以及 `SAME` 或 `DIFF`，最後是 `rom-checksum: N of M blocks differ from <image>`。映像是 `config.REFERENCE_ROMS[game code]`，或用 `--sum-reference` 指定任意構建。超出映像的塊會列出但不計數。

### `rng-trace`

每幀採一個字，並在每次取樣的兩次讀取之間呼叫一個 ROM 函式（`--trace-call 0` 就是單純取樣）。

    HOST --buffer-script rng-trace --trace-address 0x03004220 --trace-call 0x080486B1 \
        --trace-samples 96 --version firered

呼叫形如 `mov lr, pc; bx r2`：pc 讀作 `bx` 之後那條指令，第 0 位清零，於是被調者返回到 ARM 狀態。零售版火紅上，`Random` 跟蹤的每個取樣都遵循 LCG（實測的 96 個裡有 96 個）。結果見 [RNG](frlg_rng.md)。

### `string-gather`

給定第一個指標的地址、一個步長與一個計數，把每個被指向的字串（含 0xFF 終止符）複製進同一份應答，並報告下一輪從哪裡繼續。

    HOST --buffer-script string-gather --gather-address 0x083E0D54 --gather-count 69 \
        --gather-stride 12 --version firered

`--gather-stride` 對 `struct EasyChatWordInfo`（`text` 在 0）是 12，對 `const u8 *` 陣列是 4。應答是 776 位元組：四個頭部字，最多 760 位元組字串。它從不截斷：裝不下的字串會結束本輪，`next` 點名它。`--gather-maxlen`（預設 64）限制不是字串的指標。

### `create-mon`

```c
void CreateMon(struct Pokemon *mon, u16 species, u8 level, u8 fixedIV,
               u8 hasFixedPersonality, u32 fixedPersonality, u8 otIdType, u32 fixedOtId)
```

四個引數在 `r0..r3`，四個在棧上。`asm/create-mon.s` 沿用主機自己的序言：

    08041150  push {r4,r5,r6,r7,lr}    ; sp -= 20
    08041152  mov  r7, r8
    08041154  push {r7}                ; sp -= 4
    08041156  sub  sp, #28             ; sp -= 28, so entry sp is now sp + 52
    0804115c  ldr  r4, [sp, #52]       -> entry sp +  0   hasFixedPersonality  (masked to u8)
    0804115e  ldr  r7, [sp, #56]       -> entry sp +  4   fixedPersonality     (NOT masked: u32)
    08041160  ldr  r5, [sp, #60]       -> entry sp +  8   otIdType             (masked to u8)
    08041184  ldr  r0, [sp, #64]       -> entry sp + 12   fixedOtId            (u32)

這四個按整字放在 `sp+0..sp+12`，載荷自己彈出。寶可夢建在載荷的映像裡，程式碼之前有 32 位元組填充；`--create-mon-destination ADDR` 把它複製出去，需要 `--write-unsafe`。

    HOST --buffer-script create-mon \
        --create-mon-species 151 --create-mon-level 30 --create-mon-iv 31 \
        --create-mon-personality 0x3ADE0000 --version firered

`--create-mon-call` 預設是 `rom_map.py` 裡的 `CreateMon | 1`；`0` 表示不呼叫，答以清零的緩衝區。應答是 116 位元組（四個頭部字加 100 位元組的 `struct Pokemon`），`*param` 是個性值。

各子結構用 `personality ^ otId` 加密並帶校驗和，所以校驗和有效就證明這兩個字。`check_create_mon` 檢查物種、等級與個體值；`scratchpad/verify_create_mon.py` 預測十三個派生欄位：經驗值來自 `gExperienceTables[growthRate][level]`，親密度與特性槽來自 `gSpeciesInfo`，招式與 PP 來自學習表，六項能力來自 `CalculateMonStats`。暱稱來自 `gSpeciesNames` [pokemon.c:1810]，即卡帶上的法語表，是讀出來的，從不預測。三個欄位度量主機：

| 欄位 | 值 | 說明 |
| --- | --- | --- |
| `language` | 3 | `gGameLanguage` 是 LANGUAGE_FRENCH [global.h:22] |
| `metGame` | 4 | `gGameVersion` 是 VERSION_FIRE_RED [global.h:11] |
| `metLocation` | 91 | `GetCurrentRegionMapSectionId()` [overworld.c:1265]，即玩家當時所在處 |

`buffer_script.shiny_personality(tid, sid)` 給出閃光的 `fixedPersonality`。`CreateMon` 的離線樁：`CREATE_MON_ARG_MODEL` 把八個引數寫進目標，`create_mon_copy_model(source)` 複製 100 個預備位元組。

#### `--create-mon-append`

它寫 `gPlayerParty`，不是存檔塊裡的隊伍：

```c
void SavePlayerParty(void)
{
    gSaveBlock1Ptr->playerPartyCount = gPlayerPartyCount;
    for (i = 0; i < PARTY_SIZE; i++)
        gSaveBlock1Ptr->playerParty[i] = gPlayerParty[i];
}
```

往存檔塊裡追加會報成功，並在下次儲存時丟失 [load_save.c:160,196]。它在 `slot == playerPartyCount` 處寫入並提高計數，與捕獲一樣；已佔用的槽絕不碰，隊伍滿時什麼都不寫。應答的第五個字報告 `countBefore | slot << 8 | status << 16`（0 未詢問、1 已追加、2 隊伍滿、3 試執行）。帶絕對 `--create-mon-destination` 的追加，或帶 `--create-mon-call 0` 的追加，會被拒絕。

    # dry run first: the same code with the two stores left out
    HOST --buffer-script create-mon --create-mon-append-dry-run \
        --create-mon-species 59 --create-mon-level 30 --version firered
    HOST --buffer-script create-mon --create-mon-append \
        --write-unsafe --create-mon-species 59 --create-mon-level 30 --version firered

試執行報告計數、目標地址與該槽當前那 100 位元組，能抓出與隊伍不符的 `playerPartyCount`。空槽不是全零：`ZeroMonData` 以 `SetMonData(mon, MON_DATA_MAIL, &MAIL_NONE)` 結尾 [pokemon.c:1737]，所以偏移 0x55 是 `0xFF`（`buffer_script.EMPTY_PARTY_SLOT`、`is_empty_party_slot`）。

| | 會移動嗎？ | 所以 |
| --- | --- | --- |
| `gSaveBlock1Ptr` | 會，一個隨機 4 對齊偏移，每場戰鬥與每次讀取都重擲 [`SetSaveBlocksPointers`, load_save.c:75] | 每次呼叫都從 `r1`/`r2` 取 |
| `gPlayerParty` | 不會，是連結期 EWRAM 全域性量 | 地址是合法的 |

`gPlayerParty` 是 0x02024280，`gPlayerPartyCount` 是 0x02024025：EWRAM 轉儲裡唯一一個 4 對齊視窗，能解碼成帶校驗和的 `struct Pokemon`。

### `call`

一個地址、最多八個引數字、返回的 `r0`，以及呼叫前後各讀一個地址。

    HOST --buffer-script call \
        --call-address 0x080486D1 --call-arg 0xC0DE --call-watch 0x03004220 --version firered

    0x000  b .Lcode
    0x004  function    THUMB pointer (bit 0 set), or 0 to call nothing
    0x008  argc        how many of the eight words below are meant
    0x00C  args[0..7]  r0, r1, r2, r3, then [sp+0], [sp+4], [sp+8], [sp+12]
    0x02C  watch       a word to read before and after the call, or 0
    0x030  result      calls used, function, argc, r0, *watch before, *watch after

`asm/call.s` 總是壓入那十六個棧位元組；被調者從不彈出。`SeedRng` 不返回東西（`gRngValue = seed` [random.c:15]），所以 watch 字就是證據。只調用已經讀作程式碼的地址。`tests/test_buffer_script.py` 在 unicorn 下把主機自己的 `SeedRng` 位元組跑過載荷，並用 2 的冪測八引數路徑。

### `flash-write`

在 EWRAM 裡拼出一個 4 KB 扇區，用 [`swi 0x48`](#the-flash-sector-path) 寫進 flash，而不走遊戲的存檔程式碼。臨時區是 `gDecompressionBuffer + 0x400`，比載荷自己的映像高 0x400。

    --flash-sector N            the sector, 0..31; 0..27 are the save bands and need --write-unsafe
    --flash-fill-base WORD      word[i] = base + i * step, the data pattern
    --flash-footer              compose a well-formed sector instead of a raw pattern
    --flash-id N                the sector id at +0xFF4
    --flash-derive              read the save globals and place it where that id actually lives
    --flash-position N          aim at band position N and derive the id from it instead
    --flash-counter-bias N      added to gSaveCounter for the footer

`--flash-footer` 像遊戲那樣從圖案末尾清零到 `+0xFF4`，算出遊戲的校驗和，並鋪下 id、校驗和、簽名與計數器。狀態字是物理扇區（高半）與校驗和（低半）。`--flash-derive` 在寫入時讀 `gLastWrittenSector` 與 `gSaveCounter`：兩者每次儲存都前進，而以成功訊息結束的禮物會話會儲存 [mystery_gift_menu.c:1379]。

### `sloop-svc`

一次會話最多八個 Sloop 系統呼叫，運算元由主機選擇，經結果塊作答。

    IP_HOST --buffer-script sloop-svc --svc-number 0x4d --svc-text "hello fuck" \
        --svc-data-in r0 --version firered

    0x000  b .Lcode
    0x004  flags       bit 0: r0 = &copy, bit 1: r1 = &copy
    0x008  r0..r3
    0x018  scratch     gDecompressionBuffer + 0x400
    0x01C  length      of the data, at most 256
    0x020  thunk       swi N ; bx lr (THUMB), or bkpt N ; bx lr with --svc-bkpt
    0x024  count       1..8
    0x028  numbers     eight bytes, one per call
    0x030  data

每次呼叫前，載荷重新複製資料，並把編號寫進 thunk 的低位元組。結果塊：標記 `0x53565331`、計數、標記 `0x53565332`、長度、八個 20 位元組記錄（thunk 字、之後的 `r0..r3`），以及最後一次呼叫留下時的資料。只讀值的編號（0x46、0x49..0x4B、0x4D、0x4E、0x50..0x54、0x58..0x60）原樣放行；0x48、0x56、0x4C 與 0x55 被拒絕；其餘的以及 `--svc-bkpt` 需要 `--write-unsafe`；`--svc-bkpt` 拒絕 `#0x52`。

### `install-resident`

把常駐 THUMB 鉤子複製到 `0x0203FC00`，並在一次會話裡裝進 `gIntrTable[4]`。它每幀執行，穿過 CONTINUER 與野外，直到軟復位。

    IP_HOST --buffer-script install-resident --resident turbo \
        --resident-param extra=4 --resident-param field=1 --resident-param battle=1 \
        --resident-param overlay=0x03004220 --resident-param hold=0x100 \
        --resident-param budget=228 --write-unsafe --version firered

    0x000  b .Lcode
    0x004  dest          0x0203FC00
    0x008  length        of the hook, whole words
    0x00C  table         &gIntrTable[4], 0x03002730
    0x010  entry_off     the hook's entry inside it
    0x014  original_off  its p_original word
    0x018  blob_off      where the hook starts in this image, after the installer's code

THUMB 安裝器是 148 位元組，給鉤子留 876 位元組，鉤子的資料（`p_frames`、`p_ring`、`p_state`）不得與程式碼重疊，也不得越過 `0x02040000`。複製與寫表期間會清 `REG_IME`。第一次安裝把被替換的處理函式留在 `0x0203FBFC`；之後的安裝鏈到那個字，它為空時以 `0xBAD0BAD0` 拒絕。應答是找到的處理函式：乾淨安裝上是 `0x0800071D`。同一時間只有一個鉤子常駐；它們共用 `0x0203FC00` 處的 1 KB。

#### `turbo`

`asm/resident/turbo.s` 先跑 `VBlankIntr`，然後在空閒幀裡把野外回撥多跑 `field` 次、戰鬥的多跑 `battle` 次，並把 `RunTextPrinters`（`0x08002D51`）多跑 `extra` 次。只有 `callback1`/`callback2` 恰好是 `CB1_Overworld`（`0x08059E49`）/`CB2_Overworld`（`0x08059EC9`）或 `BattleMainCB1`（`0x08015B6D`，由戰鬥初始化在 `0x08013FDE` 存下）/`BattleMainCB2`（`0x08014889`）時才跑一輪，兩次呼叫之間會重新檢查。先清 `newKeys` 與 `newAndRepeatedKeys`，使一次按鍵只被處理一次。

`gPaletteFade.active`（`0x02037AB4`）置位時不跑任何一輪：硬體淡出在 `UpdatePaletteFade` 置上一位的 `hardwareFadeFinishing`、下一個 V-blank 看到它時結束 [palette.c:701, 743]；一幀內第二次更新會把該位翻回 0，於是 `CompleteWhenChoseItem` 在戰鬥裡合上背包後永遠等下去。另有兩道門：

- `gMain.intrCheck`（`0x030022EC`）第 0 位清零，在 `VBlankIntr` 之前讀：主迴圈停在 `WaitForVBlank` [main.c:462]。置位說明是掉幀，放過。
- `sTextPrinters`（`0x02020034`，32 個 0x24 位元組）裡沒有在其原位的活動列印器（`currentX == x`、`currentY == y`）：野外訊息在框畫出來之前就加進列印器 [field_message_box.c:44]，在框畫出之前跑一輪會把字打進框隨後清掉的視窗。

實測（模擬器上）：每秒 60 幀、97% 空閒、文本每幀五個字形；`field=1` 讓野外快一倍，`battle=1` 讓戰鬥及其選單快一倍。

`hold=MASK` 只在 `gMain.heldKeys`（`gMain + 0x2C`）按住掩碼裡的每個鍵時才跑回調那幾輪；文本的額外次數照跑。用 `hold=0x100`（R）時，鉤子每幀往 `gHelpSystemToggleWithRButtonDisabled`（`0x0203F171`，字面量在 `RunHelpSystemCallback` 的 `0x0813F6FC`，函式在 `0x0813F65C`）寫 1，於是 R 不再開啟幫助系統 [help_system_util.c:50]；L 仍然可以。

`budget=LINES` 按時間限制輪數。Switch 模擬器在一幀的程式碼執行時推進 `REG_VCOUNT`（0 到 227，V-blank 從 160 起）；只有自 V-blank 以來的行數加上上一輪開銷的兩倍能塞進 `LINES` 時才開一輪。上一輪開銷在計數器 `+0x0C`，被攔下的輪次計在 `+0x10`；每攔一次就把保留的開銷縮小八分之一。

實測（模擬器上）：

| 設定，按住 R | 每幀額外輪數 | 備註 |
|---|---|---|
| `field=2 battle=2` | 2 裡 1.70 到 1.90 | 約 2.9 倍，無可見掉幀 |
| `field=3 battle=3` | 3 裡最多 2.38 | 約四分之一的幀掉幀；可見卡頓 |
| `field=3 battle=3 budget=228` | 最多 2.48 | 流暢；走路一輪 36 到 42 行，戰鬥 100 到 108 行 |

`overlay=ADDRESS` 把 `ADDRESS` 處的字以八個十六進位制位畫在野外的右上角（`0x03004220` 是 `gRngValue`）。這些項寫進 `gMain.oamBuffer[120..127]`（`0x030026C8`），兩種顏色寫進 `gPlttBufferFaded`（`0x020375F4`）與 `gPlttBufferUnfaded`（`0x020371F4`）的 OBJ 調色盤 15，都在 `VBlankIntr` 的 `LoadOam` 與 `TransferPlttBuffer` 之前（之後的話，最上面幾行會晚一幀）。一套 128 位元組的 1bpp 字型（十六個 3x5 數字，畫素在第 1 到 5 行的第 2 到 4 列，`asm/resident/overlay.inc`）在兩個哨兵字不同時展開到 OBJ 圖塊 1008 到 1023。覆蓋層會蓋掉遊戲在調色盤 15 與那些圖塊裡放的東西。

`ring=ADDRESS`（140 位元組；`0x0203FF74` 到 EWRAM 頂端結束）按 `VBlankIntr` 看到的樣子儲存 `gRngValue`，每幀一個字、共 32 幀，`watch`（`gEnemyParty[0]` 的個性值，`0x02024028`）變化時凍結。草叢遇敵的個性值由保留的每個種子推出。實測（模擬器上在草叢裡走動）：每幀兩次 `Random` 呼叫，從前一幀的種子數起，性格抽取是第五次呼叫（`VBlankIntr` 的 [main.c:412]、本幀自己的、slot、等級、性格）。

#### `shiny`、`shiny-press`、`ivs`、`noencounter`

`shiny`（`asm/resident/shiny.s`）倒計數到下一次閃光野生個體的抽取。`VBlankIntr` 每幀呼叫一次 `Random` [main.c:412]；野生寶可夢先以 `Random() % 25` 抽性格，再反覆抽 `Random() | Random() << 16` 直到性格相符 [wild_encounter.c:233, pokemon.c:1864]；`method=1` 取第一對（指令碼化的 `CreateMon`）。閃光的判據是 `TID ^ SID ^ high ^ low < 8`，TID 與 SID 取自 `gSaveBlock2Ptr`（`0x0300422C`）的 `+0x0A`。鉤子逐幀跟隨 `gRngValue`（最多 64 步，否則重啟），每個空閒幀搜尋 `search` 個候選，並以十進位制顯示目標的性格與 `target - current - offset`（`offset=4`，草叢的情形），或顯示 `FF` 與搜尋距離。按住 `slow`（R）時它每幀多等 `slow_frames` 個 V-blank：`IntrMain` 在處理函數里讓 VCount 保持使能 [crt0.s]，所以 `m4aSoundVSync` 會跑，鉤子每等一個 V-blank 就呼叫 `m4aSoundMain`（`0x081DF53D`，`gPcmDmaCounter` `0x03002F68` 來自 `gSoundInfo` `0x03005F80`），並在 `REG_IF` 裡清掉它。狀態是 `0x0203FF80` 處的 36 位元組。

`shiny-press`（`asm/resident/shiny-press.s`，872 位元組）是同一份原始碼加上 `SHINY_PRESS` 彙編出來的：沒有慢動作、`method=1`，A 由鉤子按下。在倒計數為 0 的空閒幀上，若 `callback1`/`callback2` 是 `CB1_Overworld`/`CB2_Overworld`，且 `sGlobalScriptContext`（十二張卡帶上都是 `0x03000FB0`，`ScriptContext_SetupScript` 的第一個字面量）處於模式 2、`nativePtr` 是 `WaitForAorBPress`（`ScrCmd_waitbuttonpress` 的字面量，`gScriptCmdTable[0x6D]`；法語是 `0x0806F159`），或在按住 B 時沒跑指令碼（模式 0），它就把一個墊片（用 `adr` 找到）寫進 `callback1`。下一輪主迴圈先跑 `ReadKeys` [main.c:81]；墊片把 `CB1_Overworld` 放回去，把 A 或進 `gMain.newKeys` 並呼叫它。等待中的指令碼會立刻返回 [scrcmd.c:1313]；沒有指令碼時，A 對玩家面前的東西說話。等待時按住 B 不算新按鍵，站著不動什麼也不做。

| 寶可夢 | 造出它的那次按鍵 | `offset` mGBA | `offset` 零售版 Switch |
|---|---|---|---|
| 超夢 | 它的 `waitbuttonpress`；`setwildbattle` 緊隨其後 [CeruleanCave_B1F/scripts.inc:37] | 1 | 3 |
| 急凍鳥、閃電鳥、火焰鳥 | 那次對話：`lock`、`faceplayer`、`setwildbattle`，然後是等待 | 2 | 5 |

在 Switch 2 上的零售版英文火紅裡，超夢叫聲處 `offset=1` 按一次，得到的個性值是 `0x9C9D9DC5`，比目標閃光值晚兩次呼叫抽出；`offset=2` 得到非閃光的超夢，`offset=3` 得到閃光的。面對閃電鳥，對話那次按鍵用 `offset=4` 得到 `0xC2C9758B`，比目標閃光值晚一次呼叫，`offset=5` 得到閃光的閃電鳥（`tests/test_shiny.py`）。應用傳送的是 3 與 5。

Switch 的模擬器每個 V-blank 呼叫兩次 `Random`，而 mGBA 只調用一次：在模擬主機上站在華藍洞窟 B1F，法語火紅，600 個 V-blank 裡 1200 次呼叫，每個 V-blank 的 `intrCheck` 第 0 位都清零。每幀兩次呼叫時，奇數倒計數會從 1 跳到 -1，永遠按不下；在零售主機上，這讓閃電鳥的對話按鍵在三次倒計數里丟了兩次。鉤子在狀態 `+32` 處保留上一幀的 `64 - calls`。當它是 62 且被追蹤目標的倒計數為奇數時，鉤子自己花掉一次 `Random` 呼叫（`gRngValue` 與所跟隨的種子都前進一步），於是它顯示的每個倒計數都能走到 0。用這個鉤子加 `offset=3`，模擬主機在超夢叫聲處的第一個倒計數上就給出了閃光超夢（`0xA893924D`）。

有野生寶可夢的地圖每 1200 到 3600 幀播放一次環境叫聲；叫聲花 2 次呼叫，除非叫聲來自水屬性寶可夢而玩家不在水上，下一幀再花 1 次決定下一個間隔 [overworld.c:1131-1172]。在 mGBA 裡用法語火紅站在雙子島急凍鳥面前，3599 幀裡只有一幀是 2 次呼叫，其餘都是 1 次。多出來的那次奇偶呼叫會讓每幀兩次呼叫下的倒計數變成奇數；花掉的那次呼叫把它抵消回來，mGBA 於是就在倒計數期間的一次叫聲裡按出了閃光急凍鳥（`0xFF0AFD1B`，offset 2）。

在 mGBA 裡，CONTINUE 之後的回顧畫面會讓玩家物件朝南（`gObjectEvents[0]` 的 `+0x18` = `0x11`，法語與英文火紅上都是 `0x02036E34`），回顧期間按的方向不會被接受；鉤子發出的 A 於是只進了 `gMain.newKeys`，對著空氣說話。回顧之後按一幀上，就把方向設為 `0x22`（北），下一次按鍵就說得上話。應用讓玩家去和超夢對話；在叫聲處不需要按任何鍵。野生戰鬥之後，鉤子保留倒計數，但在叫聲處不按任何東西，直到它被重新下發。

`offset` 數的是從按鍵那一幀鉤子的種子到個性值之前那次呼叫的呼叫數，在 mGBA 上用法語火紅測得（A 按一幀，每種三次，`tests/test_shiny.py`），並在玩家按住 B 時用應用的載荷端到端跑過：在閃電鳥處 offset 從 0 到 8，只有一個取 2 時是閃光。用表裡的偏移，應用的載荷在七張卡帶上都給出了四個閃光：法語、英語、西班牙語、德語火紅，法語、英語、義大利語葉綠。日語未試。

`ivs`（`asm/resident/ivs.s`）分兩行顯示隊首的個體值（`OVERLAY_TWO_ROWS`，第二行在 `gMain.oamBuffer[112..117]`，y 為 10）：HP、攻擊、防禦、速度，然後是特攻、特防與 `personality % 25`。`GetMonData(mon, MON_DATA_IVS)`（66，`0x080432E5`）返回六個五位個體值，HP 最低 [pokemon.c:3250]；`GetBoxMonData` 就地解密再加密 [pokemon.c:2992, 3327]，所以只在野外空閒幀呼叫它。

`noencounter`（`asm/resident/noencounter.s`）每幀往 `sWildEncountersDisabled`（`0x020386D8`）寫 1，`StandardWildEncounter`（`0x08086528`）最先檢查它 [wild_encounter.c:360]；`DisableWildEncounters`（`0x08085FAC`）是它唯一的另一個寫入者。草叢、水面與遊蕩寶可夢的遇敵都會停；釣魚與甜香走各自的路徑。

#### `noclip`

`noclip`（`asm/resident/noclip.s`，304 位元組）在按住 `hold`（預設 `0x100`，R）裡的每個鍵時讓玩家穿牆。在每個野外空閒幀（`gMain.intrCheck` 第 0 位清零、`callback2` 為 `CB2_Overworld`），它把地圖網格 `VMap.map`（`gBackupMapData`，`0x02031DF8`）裡玩家 `currentCoords` 周圍的四個塊改寫為碰撞 0、海拔 15，並保留 metatile id。`VMap` 是 `0x03004260`（法語）或 `0x03004310`（英語）處的 `{s32 Xsize, s32 Ysize, u16 *map}`，也就是 `MapGridGetCollisionAt` 裡的那個字面量。一個塊是 `metatile | collision << 10 | elevation << 12` [global.fieldmap.h:7]；`GetCollisionAtCoords` 先按碰撞位攔，再按 `IsElevationMismatchAt` 攔，而海拔 15 能過，`ObjectEventUpdateElevation` 在 15 的圖塊上不改變玩家自己的海拔 [event_object_movement.c:4830, 8346, 8400]。

下一個空閒幀會把每個塊放回去，但只在 `gMapHeader.mapLayout`（`0x02036DF8`）仍是它改過的那個佈局、且該塊仍是它的 metatile id 加海拔 15、碰撞 0 時才放：傳送或遊戲自己改寫過的 metatile 會保留新塊。等於 `MAPGRID_UNDEFINED`（`0x3FF`）的塊保持不動，否則玩家會走出地圖。物件事件仍然會擋（`DoesObjectCollideWithObjectAt`），臺階仍然會跳，玩家旁邊的遊蕩物件事件也可能踏上被開啟的塊。按住 R 會開啟幫助系統，所以鉤子每幀往 `0x0203F171` 寫 1（見 `turbo`）。狀態是 `0x0203FF80` 處的 24 位元組：佈局、一個計數與四個 `{u16 index, u16 block}`。

`tests/test_noclip.py` 用每張卡帶自己的客戶端安裝它，並用卡帶自己的 `MapGridGetCollisionAt` 與 `MapGridGetElevationAt` 讀結果。在 mGBA 上用法語卡帶在真新鎮實測：向南走，不按 R 玩家會停在柵欄前，按住 R 能穿過六個圖塊；物件事件仍然會擋住它。

#### `follower`

`asm/resident/follower.s` 把隊首寶可夢作為一個真正的物件事件跟在玩家身後一格，用遊戲自己的移動動作驅動，於是步、跑、跳臺階（弧線、影子、落地塵土）、門淡出與精靈優先順序都由遊戲畫出。設計沿用 GB-Link 的 `cards/follow.s`（GPL-3.0）。它有 984 位元組，超過一次 `install-resident` 會話，所以從存檔裡安裝（[常駐鉤子留在存檔裡](#a-resident-hook-kept-in-the-save)）。

在每個野外空閒幀（`gMain.intrCheck` 第 0 位清零、`callback2` 為 `CB2_Overworld`），在 `VBlankIntr` 之後：

| 步驟 | 鉤子做什麼 |
| --- | --- |
| 找到它 | 區域性 id `0xF0` 的活動物件事件，沒有地圖用這個區域性 id；地圖載入後不存在 |
| 生成 | 在玩家腳下調 `SpawnSpecialObjectEventParameterized(gfx, MOVEMENT_TYPE_NONE, 0xF0, x, y, elevation)`，隱藏到玩家走出第一步 |
| 每幀 | 把它的當前海拔設為 14，沒有任何圖塊是這個海拔：玩家能走回去，也沒有東西和它對話 [event_object_movement.c:4899]；野外被鎖時置 `fixedPriority`，讓存檔保留那個海拔 |
| 玩家走一步 | 玩家離開的那格成為它的目標；隔一格時它拿到玩家自己的動作族（跑會變成 `WALK_FAST`），不在一條線上就用 `MoveObjectEventToMapCoords` 直接移過去 |
| 臺階 | 玩家的 `JUMP_2` 會把它的座標移兩次：第一次把跟隨者帶到邊緣，第二次把它留在那裡；玩家下一步時它自己做 `JUMP_2`，兩格；一條線上兩格且沒有待處理的臺階時，它用 `WALK_FASTER`（0x35）每次一格地跟上 |
| 選單 | `sGlobalScriptContextStatus`（`0x03000FA8`）為 `CONTEXT_SHUTDOWN` 時置 `sLockFieldControls`（`0x0300109C`）：`RemoveObjectEvent`，於是存檔絕不會帶著它；之後會重新生成 |
| 腳踏車、衝浪、潛水 | 隱藏在玩家腳下 |
| 換隊首 | 移除並重新生成 |
| 撞上 | 玩家在海拔 0 的圖塊上撞到它時，它被放到玩家腳下 |

| 隊首 | 物件 |
| --- | --- |
| 42 個有野外精靈的物種之一（`OBJ_EVENT_GFX_SNORLAX` 109 到 `DEOXYS_N`；代歐奇希斯用它所在版本的形態，建構子的 `deoxys=`） | 它自己的圖形 id |
| 其他任何物種、蛋、按字母區分的未知圖騰 | 卡比獸的 32x32 幀（109，`sAnimTable_Standard`）；它精靈的 `images` 指向 `0x0203FBB4` 處的九個 `SpriteFrameImage`（站立 0..2：圖示幀 0，走路 3..8：幀 1，每個 0x200 位元組，來自 `GetMonIconPtr`），用 OBJ 調色盤 15 |

圖示的調色盤每空閒幀寫進 `gPlttBufferUnfaded` 的 OBJ 調色盤 15（`0x020375D4`），只在混合的 `y`（`gPaletteFade + 4`，第 6..10 位）為 0 時才寫進 `gPlttBufferFaded`（`0x020379D4`）。門的淡出會把 `BeginNormalPaletteFade` 跑到 `y` 16，然後在螢幕仍黑時清掉 `active` [field_weather.c:740, palette.c]；在 mGBA 上走進門實測，`active` 保持 21 幀，然後 `y` 為 16、`active` 清零持續四幀，之後 `callback2` 離開野外。

在野外按 A，且玩家面前的圖塊是跟隨者、野外又沒被鎖時（遊戲自己的 A、指令碼或選單會先佔這一幀）：把 `gSelectedObjectEvent` 設成它，跑 `ScriptContext_SetupScript`，並把物種寫進去（`SPECIES_EGG` 即 412 不寫，它沒有叫聲）：

    6A                lock
    A1 SPEC 0000      playmoncry SPECIES, CRY_MODE_NORMAL
    5A                faceplayer
    4F F000 PTR       applymovement 0xF0: 66 FE (MOVEMENT_ACTION_EMOTE_SMILE, step_end)
    51 0000           waitmovement 0
    C5                waitmoncry
    7F 00 0000        bufferpartymonnick STR_VAR_1, 0
    67 PTR            message: "{STR_VAR_1} saute\nde joie !" (French), "{STR_VAR_1} jumps\nfor joy!" (English)
    66 6D 6C 02       waitmessage, waitbuttonpress, release, end

狀態是 `0x0203FFDC` 處的 17 位元組（`state=`）：`+0` 它的物件事件或 `0xFF`，`+1` 有待走的步，`+2` 正在顯示圖示，`+3` 動作族，`+4` 上次看到的玩家座標，`+8` 它的目標，`+12` 隊首的物種，`+14` 它被生成時對應的物種，`+16` 有待處理的臺階。圖示的幀表是 `0x0203FBB4` 處的 72 位元組（`images=`），在安裝器保留於 `0x0203FBFC` 的處理函式之下。

| 卡帶 | `SpawnSpecialObjectEventParameterized` | `ObjectEventSetHeldMovement` | `ObjectEventClearHeldMovement` | `MoveObjectEventToMapCoords` | `RemoveObjectEvent` | `ScriptContext_SetupScript` | `gSelectedObjectEvent` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BPRF, BPGF | `0x08062130` | `0x080675A4` | `0x08067634` | `0x08063024` | `0x08061DB4` | `0x0806D3D4` | `0x03004294` |
| BPRE, BPGE | `0x08061FD4` | `0x08067448` | `0x080674D8` | `0x08062EC8` | `0x08061C58` | `0x0806D270` | `0x03004344` |

| 卡帶 | `gMonIconPaletteIndices` | `gMonIconPalettes` | `GetMonIconPtr` |
| --- | --- | --- | --- |
| BPRF | `0x083CBEE8` | `0x083CB7A8` | `0x0809AA74` |
| BPGF | `0x083CBD24` | `0x083CB5E4` | `0x0809AA48` |
| BPRE | `0x083D197C` | `0x083D123C` | `0x0809A7B8` |
| BPGE | `0x083D17B8` | `0x083D1078` | `0x0809A78C` |

英語的值來自 `pokefirered_switch.elf`；法語的值是在各個映像裡找到的同樣位元組。`tests/test_follower.py` 按 `install-kept` 安裝的方式在各個映像上跑這個鉤子，物件函式用樁替代：生成、走路、圖示幀與調色盤、臺階等待與單次跳、對話指令碼、選單下的移除。

`AddSpritesToOamBuffer` 只用 `gDummyOamData` 填到 `gOamLimit` 為止的未用 OAM 項 [sprite.c:487]，`ResetSpriteData` 把它設為 64 [sprite.c:297]，野外讀出來也是 64（`0x02021B44`）：鉤子寫進 64 以上的項會一直留在螢幕上，直到某個畫面重置自己的精靈。

#### 已驗證

| 鉤子 | 零售版法語火紅，ESP32 無線電（每次安裝都答 `0x0800071D`） | 模擬器 |
| --- | --- | --- |
| `turbo` `extra=4 field=3 battle=3 hold=0x100 budget=228` | 按住 R 能快進 | |
| `overlay` | 畫出八個數字，每幀變化 | 在 CONTINUE 之後的回顧畫面裡也畫 |
| `shiny` | 在草叢裡倒計數；R 讓它變慢 | 跟隨的種子與 `gRngValue` 相符；Python 模型對閃光的判斷一致 |
| `ivs` | 隊首的個體值字與 `personality % 25` 與 `SaveBlock1 + 0x34` 的 `save-dump` 相符 | 與 `gPlayerParty`（`0x02024280`）相符 |
| `noencounter` | 在草叢裡走時沒有野生遇敵 | 無；軟復位後遇敵恢復 |
| `turbo-lite+noclip+noencounter`，`turbo-lite.field=2 battle=2 hold=0x2`，`noclip.hold=0x100` | 一次會話答 `0x0800071D`；按住 B 快進、按住 R 穿牆、草叢無遇敵，兩個鍵一起按則快速穿牆 | |
| `follower` | 跟在一格之後，在臺階邊緣等待，玩家離開落點那一格後跳上去，帶遊戲的影子與塵土；跑動與跑著越過臺階都不閃；面對它按 A：叫聲、微笑、臺詞；開始選單與門；一次會話把它寫進存檔並安裝 | 在 mGBA 上相同，用吉利蛋的精靈與水箭龜的圖示 |

未解決：在模擬器上，覆蓋層在 CONTINUE 之後的回顧畫面裡畫出來了，但在可操作遊玩中沒畫，而 `field` 仍能讓遊戲加速。

每個鉤子在葉綠上只需改一個地址就能跑：`m4aSoundMain` 是 `0x081DF518`（它在 `VBlankIntr` 裡的 `bl` 在 `0x08000772`）；其餘常量都通過火紅自己的引用同樣對映。`follower` 還讀 ROM 表與會移動的函式，都在它那一節裡列出。建構子接受 `version=`，主機用 `--version leafgreen`。在模擬的葉綠上驗證過：turbo 與 `shiny`，音樂完好。

### 同時裝多個鉤子

每個鉤子都把它替換掉的處理函式當作函式呼叫（`bl` 到 `p_original` 上的 `bx r3`），並通過自己壓入的 `lr` 返回，所以一個鉤子的 `p_original` 可以指向另一個鉤子。`--resident turbo-lite+noclip+noencounter` 把這些鉤子從 `0x0203FC00` 起首尾相接排好，把每個鉤子的 `p_original` 寫成下一個的入口（Thumb 位置位），並交給安裝器一個 blob，其入口是第一個鉤子的、`p_original` 是最後一個的。`install-resident`、`install-kept` 與 MOM 的載入器都不變。某個設定用名字指定它的鉤子：`--resident-param turbo-lite.hold=2`。

| 規則 | 原因 |
|---|---|
| 順序為 turbo、noclip、shiny、ivs、noencounter | turbo 的回撥輪次在其他鉤子用完這一幀之後才跑 |
| 每個鉤子的資料先放在 `0x0203FBB4..0x0203FBFC`，再放到程式碼之上 | 預設值會重疊：`shiny`、`ivs` 與 `noclip` 都把狀態放在 `0x0203FF80` |
| `shiny`、`ivs` 與 turbo 的 `overlay` 最多隻能有一個 | 它們都畫在 `gMain.oamBuffer[120..127]` 與 OBJ 調色盤 15 |
| `follower` 單獨執行 | 984 位元組：配上任何其他鉤子就超過存檔能放的 1004 |
| 程式碼要裝進 `0x0203FC00..0x02040000` | 1024 位元組；超過 876 就得走存檔，超過 1004 無處可放 |

`turbo-lite`（`asm/resident/turbo-lite.s`）是設了 `TURBO_LITE` 的 `turbo.s`：同樣的輪次、門、hold 與 budget，沒有覆蓋層也沒有 RNG 歷史，356 位元組對 696 位元組。每個 turbo 幀測試都在它上面跑（`tests/test_turbo_lite.py`）；穿過一條鏈的一幀會把每個鉤子與 `VBlankIntr` 各跑一次（`tests/test_resident_chain.py`）。

### `install-kept`

`asm/install-kept.s`，192 位元組，把存在 `filler_B20` 裡的鉤子按 `install-resident` 裝自己那一套的方式裝起來：它讀 `gSaveBlock2Ptr`（塊每次讀取都會移動），檢查魔數、長度（要保證校驗和仍在 `filler_B20` 內）與和，然後清 `REG_IME`，把遊戲的處理函式留在 `0x0203FBFC`，複製鉤子，寫它的 `p_original`，並把 `gIntrTable[4]` 指向它。應答是表裡找到的處理函式，什麼都沒裝時是 `0xBAD0BAD0`。`+0` 處的 ARM 入口是緩衝區指令碼的；MOM 的 RAM 指令碼跑 `+8` 處的 THUMB 入口，把應答指向映像裡的一個字。最後兩個字按卡帶打補丁：`&gSaveBlock2Ptr` 與 `&gIntrTable[4]`。

    IP_HOST --buffer-script install-kept --version firered

### 常駐鉤子留在存檔裡

任何常駐鉤子都能住在 `filler_B20` 裡，並在啟動後通過與 MOM 對話重新安裝，不需要鏈路，也不需要主機。兩次禮物會話就能建好：

    IP_HOST --buffer-script save-write --resident follower --version firered
    IP_HOST --gift resident-save --version firered

第一次把這段 blob 寫到 `SaveBlock2 + 0xB20`，並在同一次會話裡從它安裝鉤子：

    +0x00  magic     0x32524B50, "PKR2"
    +0x04  length    the hook's bytes, whole words
    +0x08  dest      0x0203FC00
    +0x0C  entry     u16 offset of the hook's entry
    +0x0E  original  u16 offset of its p_original word
    +0x10  the hook
    +len   checksum  the sum of every word before it

超過一次 `save-write`（936 位元組）的 blob 由兩次寫入完成。會話依次跑每次寫入，然後是 [`install-kept`](#install-kept)，各自是一條載荷：客戶端按命令表依次接收並執行緩衝區指令碼 [mystery_gift_client.c:145, 236]，只有最後的應答回傳。

    client  RECV RUN  RECV RUN  RECV RUN LOAD_TOSS_RESPONSE SEND_LOADED  RECV COPY_RECV
    host    script    write 1   write 2  install-kept   <- the handler found

會話以 `CLI_MSG_BUFFER_SUCCESS` 結束，它會儲存，於是 `filler_B20` 落到 flash。

第二次把一個 RAM 指令碼綁到 MOM 上，該指令碼佈置 36 位元組的 [RAM 跳板](#a-payload-larger-than-a-script-body) 並跳進 `install-kept` 的 THUMB 入口，後者逐位元組帶著（995 位元組裡的 428 位元組）。和 MOM 對話就安裝鉤子；第二次拜訪會鏈到已保留的處理函式，軟復位會移除鉤子，直到再和 MOM 對話。

| 鉤子 | blob | `save-write` 載荷數 |
| --- | --- | --- |
| `noencounter` | 48 | 1 |
| `ivs` | 520 | 1 |
| `turbo-lite` | 376 | 1 |
| `turbo` | 716 | 1 |
| `shiny` | 888 | 1 |
| `follower` | 1004 | 2 |

`tests/test_resident_save.py` 在主機與模擬客戶端之間跑完整個會話，並在啟動過的主機上跑 MOM 的 body 指令碼：翻一個位元組、少一次寫入、長度超過 `filler_B20`，都裝不上任何東西。一臺零售版火紅從它的 `PKR2` blob 裝上了跟隨者。

新的神秘卡片會撤銷繫結：`SaveWonderCard` 呼叫 `ClearSavedWonderCardAndRelated`，後者呼叫 `ClearRamScript` [mystery_gift.c:172, 160]。`filler_B20` 仍保持寫入時的樣子。

### `call-chain`

一幀內按順序最多十六步，每步一個應答字。

    HOST --buffer-script call-chain \
        --chain-step call:FlagGet,0x828 \
        --chain-step call:FlagSet,0x828 \
        --chain-step call:FlagGet,0x828 --version firered

一步是 24 位元組（op、target、四個引數），寫作 `OP:TARGET[,ARG]...`，op 為 `call`、`read32/16/8`、`write32/16/8`。呼叫目標可以是 `rom_map.CALLABLE` 裡的名字（絕不是反編譯地址）。

一步可以從上一個結果 `prev` 取它的目標或第一個引數：

    --chain-step call:GetVarPointer,0x4024      prev = the address the GAME computed
    --chain-step read16+keep:prev               the value before, prev untouched
    --chain-step write16:prev,7                 the store, read back by the payload itself
    --chain-step read16:prev                    the value after

`ScrCmd_setvar` 通過 `GetVarPointer` 的返回值寫入 [scrcmd.c:472]；沒有哪個 ScrCmd 工作者是 `VarSet`（見 [ROM 對映表](frlg_rom_map.md)）。寫入永遠不會成為 `prev`；讀取會，除非帶上 `+keep`。每次寫入都會把自己讀回應答裡。

    0x000  b .Lcode
    0x004  count       how many steps are meant, 0..16
    0x010  steps[16]   {op, target, a0, a1, a2, a3}, 24 bytes each
    0x190  result      calls, count, steps executed, the op word that stopped it
    0x1A0  values[16]  one word per step, in order

未知 opcode 會中止執行，並在應答裡點名；ARM 側也會限制步數。建構子拒絕空鏈、超過十六步、呼叫 ARM 指標或卡帶之外的地址、從 `prev` 取呼叫目標（取錯會讓選單卡死）、不對齊或不可達的讀取、超過四個引數，以及任何不帶 `--write-unsafe` 的寫入（之後主機會提交它的存檔）。

    call GetVarPointer(0x4024)   -> 0x020265B4
    read16 [prev] keep           -> 0
    write16 [prev] = 3           -> 3        the store, read back by the payload
    read16 [prev]                -> 3
    call VarGet(0x4024)          -> 3        the game's own reader, same frame

`gSaveBlock1Ptr` 換基址之後，該變數讀出來仍是 3。錢是 `*moneyPtr ^ gSaveBlock2Ptr->encryptionKey` [money.c:14]：

    read32 [0x03004228]              -> 0x02025554     gSaveBlock1Ptr
    read32 [prev + 0x290] keep       -> 0x5A5A198C     the ciphertext, before
    call GetMoney(prev + 0x290) keep -> 0x00000BB8     3000, the plaintext
    call AddMoney(prev + 0x290, 1234) keep
    call GetMoney(prev + 0x290) keep -> 0x0000108A     4234, exactly +1234
    read32 [prev + 0x290]            -> 0x5A5A02BE     the ciphertext, after

（示例值。）兩組 XOR 都給出金鑰，這裡是 0x5A5A1234，即 SaveBlock2 + 0xF20 處的那個字（`rom_map.SAV1_MONEY`、`SAV2_ENCRYPTION_KEY`）。特殊函式從特殊變數裡取運算元：把 `gSpecialVar_Result` 設為 `GET_CARD_BATTLES_WON` 後，特殊函式 390 答以卡片的 `battlesWon`，即同一幀裡 `SaveBlock1 + 0x3434` 持有的值。

絕不要在緩衝區腳本里呼叫傳送或訊息工作者：神秘禮物選單沒有野外。它們屬於 [野外樁](frlg_rng.md#the-payload-in-the-script-body)。

## 寫一個遊戲會讀入的扇區

以下內容全部在模擬器上實測。

### 校驗和覆蓋 id 自己的那塊

`CalculateChecksum(data, size)` 把 `size` 位元組按小端 u32 相加，並把 `(sum >> 16) + sum` 摺疊成 u16 [decomp:src/save.c]。`size` 是 `sSaveSlotLayout` 裡 id 自己那一塊的大小，14 個 {u16 offset, u16 size} 項在法語卡帶的 `0x083F58C4` 處：

| id | 大小 | id | 大小 |
| --- | --- | --- | --- |
| 0 | 3876 | 4 | 3816 |
| 1-3 | 3968 | 5-12 | 3968 |
| 13 | 2000 | | |

`HandleWriteSector` 在複製該塊之前把整個扇區緩衝區清零 [save.c:181-183]，所以遊戲寫的扇區在其塊之後是零，對全部 3968 位元組求和得到同一個校驗和；而在塊之後帶資料的自拼扇區會被拒絕。只填那一塊。id 在主機上決定時，最多填 2000 位元組，即最小的塊：這樣一個校驗和對任何 id 都有效。

### id 住在哪裡，哪個扇區攜帶該 slot 的計數器

一個 slot 是 14 個扇區；遊戲在兩個 slot 之間交替並輪換 id [decomp:src/save.c:174]：

    physical = ((gLastWrittenSector + id) % 14) + 14 * (gSaveCounter % 2)

`gLastWrittenSector` 每次完整儲存前進一，在 14 處迴繞 [:147]。普通遊玩中它與計數器一致，但在一次寫入被標為損壞時會分開：遊戲從 `gLastKnownGoodSector` 恢復它 [save.c:159]，而 `Save_ResetSaveCounters` [:104] 會獨立重置它。`gLastKnownGoodSector` 與 `gLastSaveCounter` 在它前進之前取走當前這一對，所以它們精確地描述上一代。要找一個扇區，解析頁尾，絕不要靠固定的檔案偏移。

`GetSaveValidStatus` 在扇區的簽名為 `0x08012025` 且按 `locations[id].size` 算出的校驗和相符時計入該扇區，id 取自它自己的頁尾：

- 只有 14 個 id 都在且有效時，一個 slot 才算 OK；同一 slot 內的計數器不必一致；
- `slotNsaveCounter` 按物理順序在每個有效扇區上賦值，所以它持有最後一個有效扇區的計數器。

所以一個完整 band 若其最後一個扇區攜帶更高的計數器，就會贏過所有扇區都攜帶更低計數器的 band（十三個 129 加一個 131 勝過十四個 130）。

| 地址 | 符號 | 寬度 |
| --- | --- | --- |
| `0x030045A0` | `gLastWrittenSector` | u16 |
| `0x030045A4` | `gLastSaveCounter` | u32 |
| `0x030045A8` | `gLastKnownGoodSector` | u16 |
| `0x030045AC` | `gDamagedSaveSectors` | u32 |
| `0x030045B0` | `gSaveCounter` | u32 |

法語構建的 IWRAM。讀取之後，`gLastWrittenSector` 描述被採納的 slot。

### 本次會話自己的儲存不會寫的那個 band

一次完整儲存先分配上一對，前進 `gLastWrittenSector` 與 `gSaveCounter`，然後寫入遞增後的計數器所選的那個 band [save.c:144-153]。以成功訊息結束的禮物會話會儲存 [mystery_gift_menu.c:1379]；以其他任何結果結束的會話回到選單，不儲存。當會話將以成功結束時，現在就寫 `gSaveCounter % 2` 選中的那個 band：會話的儲存會寫另一個。要被採納，一個扇區要落在 band 位置 13，計數器為 `gSaveCounter + 2`，比會話的 `gSaveCounter + 1` 高一個。位置 13 處的 id 是 `(13 - gLastWrittenSector) % 14`，在主機上推導。

### 從 RAM 快照拼一個扇區

存檔例程在儲存時才序列化，所以 SaveBlock2 的即時內容與它會寫出的內容不同。下面兩種情況下每個校驗和都通過、`gDamagedSaveSectors` 都保持 0：

- 加密金鑰在讀取時重擲。`LoadGameSave` 恢復各塊，造一個新金鑰，把它作用到 RAM 裡每個加密欄位，並把它存進 SaveBlock2 [decomp:src/load_save.c:126-128]。用 RAM 拼出的 SaveBlock2 配一個未動過的 SaveBlock1 時，錢會讀成 `raw ^ flash_key ^ ram_key`。加密的欄位集 [ApplyNewEncryptionKeyToAllEncryptedData] 包括：SaveBlock2 裡的訓練家塔時間、遊戲統計、背包數量與樹果粉，以及錢與遊戲幣。
- 儲存的地圖檢視是 SaveBlock2 `+0x898` 處的 420 位元組（210 個 u16 metatile id，`0x03FF` 為空白），只在儲存時填充，在 RAM 裡是零；拼出的扇區會把野外畫成空白網格。

正常儲存一次寫全部十四個扇區，所以金鑰與密文一起動；部分寫入必須保住這一點。

### 讀 flash：128 KiB 晶片上的 64 KiB 視窗

`swi 0x48` 線性定址晶片。guest 讀取看到 `0x0E000000` 處一個 64 KiB 的視窗，而 1 Mbit 的器件以兩個 bank 到達它：

    sector N is bank N / 16 at 0x0E000000 + (N % 16) * 0x1000

視窗以上的地址會別名：`0x0E01E000`（扇區 30）讀到 `0x0E00E000`，即所選 bank 的扇區 14，通常是零。從扇區算出 bank 與視窗位置。選擇 bank 用遊戲自己的四條儲存 [decomp:src/agb_flash.c SwitchFlashBank, `0x081E0C74`，七條指令，無迴圈，不碰 `REG_WAITCNT`]，內聯進來，於是載荷不發起 ROM 呼叫：

    strb 0xAA -> 0x0E005555 ; strb 0x55 -> 0x0E002AAA ; strb 0xB0 -> 0x0E005555 ; strb bank -> 0x0E000000

讀取按位元組進行；flash 匯流排是 8 位。

`ReadFlash` 唯一持久的效果，是把 `REG_WAITCNT` 的 SRAM 欄位設為 3（`WAITCNT_SRAM_8` [decomp:src/agb_flash.c:149]），在啟動後已經就位：`AgbMain` 清掉它 [main.c:143]，啟動時的存檔讀取呼叫 `ReadFlash` [intro.c:1006]，而每個 flash 例程都寫 3（`gFlash->wait[0]` [agb_flash_mx.c:28, agb_flash_le.c:28]）。

絕不要把出站訊息指向 flash。頭部與訊息體以不同寬度讀那個視窗：

| 步驟 | 程式碼 | 讀法 | 它讀到了什麼 |
|---|---|---|---|
| 頭部 CRC | `CalcCRC16WithTable` [mystery_gift_link.c:166] | `ldrb` | flash：`0xDEC2` 是物理 `0x1BC00..0x1BFFF` 的 CRC，`0x5907` 是 `0x1E000..0x1E0FB` 的（已選 bank 1） |
| 訊息體 | `Rfu_InitBlockSend` 把每段不超過 252 位元組的資料用 `memcpy` `0x081E44F4` 複製進 `gBlockSendBuffer` [link_rfu_2.c:1357] | 源與目標都字對齊且還剩 16 位元組以上時用 `ldm`，一次一字 | 其他位元組：成串的位元組對 `01 cb`、`10 3a` 與 `04 3a`，對 `0x0E01BC00` 與 `0x0E01E000` 都一樣 |

訊息體 CRC 失敗，主機丟棄它，禮物選單在 RFU 鏈路仍連著的情況下卡住。訊息體位元組從哪裡來不明。`build_memory_dump` 及其兩個同族函式拒絕任何觸及 `0x0E000000..0x0FFFFFFF` 的範圍。`flash-read` 用 `ldrb` 把扇區複製進 EWRAM 併發送副本，能原樣取回該扇區。

### 改動真實存檔的一個欄位

`flash-patch` 讀一個真實儲存寫下的扇區，改一個欄位再寫回去，於是金鑰與地圖檢視保持一致。一次編輯涉及兩個扇區：

    A   the target id's sector: patch the field, recompute the checksum over the id's own chunk,
        set the counter to gSaveCounter + 2
    B   the sector at band position 13: set its counter to gSaveCounter + 2 and nothing else, not
        even the checksum, because +0xFFC is outside the summed data area

載入器會取這個 band（十二個扇區是舊計數器，兩個是新的），因為 14 個 id 都有效，且最後一個有效扇區攜帶更高的計數器。對玩家名做一次 `flash-patch`，只改扇區 A 的欄位與校驗和、扇區 B 的計數器；讀取採納該 band，沒有壞校驗和，錢與野外不變，金鑰副本與地圖檢視正是遊戲寫下的那些。

### 整條鏈，端到端

在模擬主機上實測：緩衝區指令碼從即時全域性量拼出一個扇區，`swi 0x48` 寫入它，遊戲下一次儲存提交該映像，下一次讀取採納該 band，`gDamagedSaveSectors` 乾淨。交付的圖案（與載入器的預檢圖案不同，後者哪裡都沒出現）在兩個位置的各 500 個連續字上從 EWRAM 讀回。

### 存檔容器

Switch 版的存檔資料只有一個檔案 `save:/FireRed_f.sav`（英文為 `FireRed_e.sav`，其他語言同理），即原始 128 KiB 的 GBA flash 映像。封裝層不在那個儲存裡建立任何指令碼、配置或狀態檔案；模擬主機的存檔目錄裡只有這個映像。存檔路徑與 `.sav` 字尾出現在封裝層的 `main` 裡，而它不帶任何 Lua 或指令碼直譯器。因此存檔的匯入或匯出只帶走 guest 的 flash 映像，不帶任何會被封裝層當作程式碼或配置讀取的東西。

# 讀取存檔

神秘禮物會話讀取即時存檔：裡 ID，以及每隻隊伍寶可夢的 PID、個體值與性格。不寫任何東西，也沒有卡片易手。主機的日誌用 `pokeldn.frlg.save.readout` 解碼從偏移 0 起的 SaveBlock2 `save-dump`（名字、性別、TID、SID、遊玩時間），或覆蓋 0x38 起的 SaveBlock1 `save-dump`（每隻隊伍寶可夢的性格、個體值與努力值），並把 `trainer-id-probe` 的應答解成 TID 與 SID。

## 訓練家 ID 與裡 ID

SaveBlock2 偏移 0 處存著玩家名、性別、32 位訓練家 id 與遊玩時間 [global.h:327]。低半是訓練家卡上的 TID；高半是裡 ID，哪裡都不顯示，也不在任何鏈路訊息裡傳送。

    POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live --keys PROD_KEYS \
        --buffer-script save-dump --dump-block sav2 --dump-size 64 --dump-file dump.bin

    ./.venv/bin/python tools/frlg/dump_read.py dump.bin --block sav2

    dump.bin: 64 bytes from sav2 + 0x0
      playerName    'PLAYER'
      gender        boy
      trainerId     0x12345678  TID 22136  SID 4660
      playTime      12h 34m 56s

TID 與訓練家卡不符說明讀取有問題。

## 隊伍

SaveBlock1 0x34 是 `playerPartyCount`，然後 0x38 起是 `playerParty[6]`，每隻 100 位元組 [global.h:772]：六隻共 604 位元組。

    POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live --keys PROD_KEYS \
        --buffer-script save-dump --dump-block sav1 --dump-offset 0x34 \
        --dump-size 608 --dump-file party.bin

    ./.venv/bin/python tools/frlg/dump_read.py party.bin --block sav1 --offset 0x34

    party.bin: 608 bytes from sav1 + 0x34
      playerPartyCount 5
      slot 1: PIKACHU   Lv25 nick='PIKACHU' OT='PLAYER' PID=0x00000019 Hardy   IVs=[10,20,30,15,5,25] checksum ok
      slot 2: ...

（示例值。）

個體值按 HP、攻擊、防禦、速度、特攻、特防的順序讀。閃光那一列把每隻的 PID 與它自己的 OTID 比較。每個槽都 `checksum ok` 說明是真實的隊伍。隊伍寶可夢按 `.pk3`/`.ek3` 的存法存（`pokeldn.frlg.save.mon`）：0x20 處的 48 位元組與 `PID ^ OTID` 異或，四個子結構按 `PID % 24` 排序。

SaveBlock1 持有的是上次儲存時的隊伍（`SavePlayerParty` [load_save.c:160]，見 `--create-mon-append`）。要匯出即時隊伍，用 `gPlayerParty`，兩張實測卡帶上都是 0x02024280：

    --buffer-script memory-dump --dump-address 0x02024280 --dump-size 600

絕不要在兩次執行之間沿用絕對的存檔塊地址；`save-dump` 每次都重新取指標。IWRAM 與 `gRngValue` 見 [隨機數生成器](frlg_rng.md)。
