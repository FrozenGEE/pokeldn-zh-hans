---
title: 神秘禮物
parent: 火紅與葉綠
nav_order: 2
---

# 神秘禮物

火紅與葉綠通過好友模式接收的神秘禮物可以是一張神秘卡片、一段配送指令碼、一份神秘新聞、一位來訪的對戰塔訓練家，或一隻直接放進隊伍的寶可夢，全程不需要寶可夢中心。神秘事件 VM 與原生 ARM 程式碼見[遊戲主機上的程式碼](frlg_rom.md)。

## 會話

遊戲主機的客戶端以 `{CLI_RECV, MG_LINKID_CLIENT_SCRIPT}, {CLI_COPY_RECV}` 啟動 [mystery_gift_scripts.c:15]，並執行它收到的任何 `MysteryGiftClientCmd` 陣列 [mystery_gift_client.c:87]。

    console joins  ->  SEND_PLAYER_IDS  ->  LinkPlayer block exchange  ->  one standby barrier
      server -> CLIENT_SCRIPT (sClientScript_SendGameData, 32 B)
      client -> GAME_DATA     (MysteryGiftLinkGameData, 96 B)   -- validated, card flag compared
      server -> CLIENT_SCRIPT (sClientScript_SaveCard, 48 B)
      server -> CARD          (struct WonderCard, 332 B)
      server -> RAM_SCRIPT    (1024 B: the delivery bytecode, zero-padded)
      client -> READY_END     (1024 B)
    close-link handshake  ->  disconnect

### 分幀規則

- 大小為 0 表示 1024 [mystery_gift_link.c:55]；`SVR_COPY_SAVED_RAM_SCRIPT` 從不設定 `ramScriptSize` [mystery_gift_server.c:275]，因此 RAM 指令碼和 READY_END 都是完整的 1024 位元組訊息。CRC 覆蓋填充後的緩衝區。
- 塊節奏沒有確認：除非接收方的槽位是 `RECV_STATE_READY`，`SEND_BLOCK_INIT` 會被忽略 [link_rfu_2.c:1146]。`MysteryGiftTiming.inter_block_gap_frames` 為 36；丟一個塊就會讓遊戲主機永遠等下去。客戶端要用若干幀才收完的載荷會佔用槽位那麼久：伺服器發這類訊息時要帶上 `after`，即最後一個塊發出後遊戲主機仍忙的幀數。下一條訊息的頭塊可能就落在這段時間裡；主機會壓住自己的第二個塊，直到遊戲主機空閒。
- 遊戲主機發送期間的停頓遵循[映象規則](frlg_link.md#row-one-of-the-parents-table-is-the-consoles-own-command-mirrored-back)。

### 模組

除非另有說明，均位於 `pokeldn/frlg/gift/` 下：

| 檔案 | 作用 |
|---|---|
| `mg_link.py` | 分幀：6 位元組 `{ident, crc, size}` 頭塊 + 每塊不超過 252 位元組 |
| `mg_script.py` | 客戶端指令碼組譯器、反編譯產物中的現成指令碼、`MysteryGiftLinkGameData` 讀取器 |
| `mg_server.py` | 伺服器指令碼直譯器（`SVR_*`） |
| `host_mystery_gift.py` | 主導端引擎：`tick()` → 父程序 gSendCmd，`feed_child_slot()` ← 子行 |
| `host_mg_app.py` | 掛在主機執行時之上的應用鉤子 |
| `wonder_card.py` | 逐位元組精確的時拉比與傳說三聖獸卡片／RAM 指令碼構建器 |
| `stamp_rally.py` | 印章拉力卡片、印章、啟用包裝、配送指令碼 |
| `gift_composer.py` | 動作定義、游標狀態校驗、RAM 指令碼編譯器 |
| `gift_registry.py` | 目錄 |
| `gift_to_bin.py` | 供外部第三世代神秘禮物工具使用的 `.bin` 匯出器 |
| `pokeldn/frlg/save/save_inject.py` | 帶卡片、RAM 指令碼和扇區校驗和的存檔禮物寫入 |
| `bin/frlg_mg_host.py` | 命令列入口 |

## 執行它

    (them) Mystery Gift -> Wonder Cards (Recevoir) -> Friend (Ami), wait on the search screen
    (you)  POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live --phy auto \
               --keys PROD_KEYS --gift beast-cutscene --flag-id 1005
    (them) join the host when it appears; YES on the replace-card prompt if one shows

無線電設定見 [ESP32 無線模組](hardware_esp32.md)。每次執行只服務一臺遊戲主機；主機在它離開 LDN 後停止（[主機實現](frlg_host.md)）。`tests/test_mystery_gift_flow.py` 和 `tests/test_mystery_gift_end_to_end.py` 模擬了遊戲主機的接收路徑。

`--save-to-board` 改為把禮物存到 ESP32 板子上然後退出；此後板子只要接上任意 USB 充電器供電，就會自己對每一臺加入的遊戲主機重放這個會話，一次一臺，使用每張卡帶自己的位元組（[主機映象](hardware_esp32.md#a-host-image)）。

    (you)  POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live \
               --keys PROD_KEYS --gift celebi --save-to-board

## 鏈路能承載什麼

22 條客戶端指令中有三條 [include/mystery_gift_client.h:18] 會真正執行東西：

| 指令 | 遊戲主機做什麼 |
|---|---|
| `CLI_SAVE_RAM_SCRIPT` (17) | 存下一段場地指令碼；它在下次與 NPC 互動時執行 |
| `CLI_RUN_MEVENT_SCRIPT` (15) | 執行一段神秘事件位元組碼指令碼（17 條操作碼的 VM） |
| `CLI_RUN_BUFFER_SCRIPT` (21) | `func = (void *)gDecompressionBuffer; func(&param, gSaveBlock2Ptr, gSaveBlock1Ptr)`；最多 1024 位元組 ARM |

## 唯一的 RAM 指令碼槽位

遊戲主機要麼持有一張神秘卡片，要麼持有一段繫結 RAM 指令碼，絕不會兩者兼有。`ValidateSavedWonderCard` 以 `ValidateRamScript` 收尾 [mystery_gift.c:186]，後者要求 `RAM_SCRIPT_MAGIC`、地圖為 `MAP_UNDEFINED` 且 `objectId == 0xFF` [script.c:538]；場地只會在與之對話的物件的座標上執行這樣一段指令碼 [field_control_avatar.c:458]。`CLI_SAVE_RAM_SCRIPT` 寫入的是 MAP_UNDEFINED/0xFF [script.c:578]；神秘事件 VM 的 `initramscript` 寫入真實座標。繫結指令碼存在時，卡片仍留在存檔裡，但選單會把它藏起來，GameData 報告的 `flagId` 為 0 [mystery_gift.c:349]。

下一張神秘卡片會重新繫結該槽位，卡片隨之恢復；緩衝區指令碼則不碰這個槽位。一張卡片會重寫 SaveBlock1 的 +0x32E0（卡片）和 +0x361C（RAM 指令碼），只涉及一個扇區，SaveBlock2 不動。

存檔本身也能帶上同樣的一對：`pokeldn/frlg/save/save_inject.py` 會把一張有效卡片和一個 RamScript 寫進原始存檔（`inject_gift`、`build_ram_script_struct`），因此通過神秘卡片匯入的存檔無需線上主機，就能在它的 NPC 處執行該指令碼。指令碼的 `callnative` 操作碼可以觸達客戶機 ARM，`resident-save` 禮物正是用它繫結媽媽的載入器。

`ramScript.checksum` 是對 1000 位元組做的 `CalcCRC16WithTable`，即宣告的 999 位元組加一個置零的填充位元組 [script.c:500]（`CalculateRamScriptChecksum`，BPRE 為 `0x0806D43C`，BPRF 為 `0x0806D5A0`）。若某個槽位的 CRC 只覆蓋 999 位元組，它會在物件第一次被對話時被清掉 [script.c:526]。

## 禮物目錄

`--gift NAME`；`--help` 會列出 flag id（1000..1019）。只有當前持有的卡片才有意義：相同的 id 就意味著「已有這張卡片」（`MysteryGift_CompareCardFlags`）。已經持有該卡片的遊戲主機只收下神秘事件禮物，不會出現提示。

| 禮物 | 做什麼 |
|---|---|
| `beast-cutscene-share` | 可重複的傳說三聖獸過場；預設演示卡片 |
| `celebi` | 由組合器生成的 50 級時拉比卡片 |
| `porygon-tm-gift` | 多邊獸卡片、皮皮場景，先給 TM29 精神強念再給 TM46 小偷 |
| `solrock-stamp` / `lunatone-stamp` | 同一張印章拉力卡片的兩半 |
| `altering-cave` | 移植來的官方變化洞窟活動 |
| `wish-egg`、`pokepark-egg`、`pc-japan-egg` | 官方配送的蛋 |
| `event-pokemon` | 一隻第三世代配送寶可夢，直接放進隊伍 |
| `starter-egg` | 九隻初始夥伴之一的蛋，由 `random` 抽取 |
| `rare-berries` | 謎之果、龍睛果和星桃果各一，每階段一個 |
| `national-dex` | 除非 `IsNationalPokedexEnabled`（403）返回 1，否則呼叫 `EnableNationalPokedex`（special 367） |
| `nature-mint`、`pc-anywhere` 以及另外 42 個 | GB-Link 團隊的卡片 |
| `battle-count-card` | 官方對戰計數卡片 |
| `visiting-trainer` | 以 ident 26 傳入的對戰塔訓練家（僅火紅） |
| `mystery-event-probe` | `givenationaldex; setstatus 42; checksum`，即 VM 的自檢 |
| `mystery-event-celebi` | `givepokemon`：一隻攜帶信件的 30 級時拉比，直接放進隊伍 |
| `mystery-event-npc` | `initramscript`：把一段場地指令碼繫結到真新鎮的胖男人身上 |
| `rng-seed-reader`、`rng-rate-probe`、`rng-shiny-hunt`、`rng-mon-hunt`、`rng-mon-hunt-both`、`rng-mon-hunt-log` | 見[隨機數生成器](frlg_rng.md) |

### 傳說三聖獸

一位配送員給出龍睛果、枝荔果和大師球，然後開啟一場可重複的 65 級對戰：存檔選了妙蛙種子就是水君，選了傑尼龜就是炎帝，選了小火龍就是雷公。

### 多邊獸招式學習器禮物

一張帶多邊獸圖示的卡片，加上玩家右側三格處的皮皮立繪，會在兩個不同的檢查點分別給出 TM29 和 TM46。預設 flag id 為 1007；檢視器顯示 `flag_id % 100`。

### 印章拉力

兩個活動共用一張 `SUN AND MOON RALLY` 卡片（念力土偶圖示、兩個印章槽位、flag id 1006），先後順序隨意。每個印章給一隻 30 級的太陽巖或月石；兩個都給則給一隻 50 級的時拉比。

| 狀態 | 含義 |
|---|---|
| `VAR_MYSTERY_GIFT_1` | 時拉比的完成游標 |
| `VAR_MYSTERY_GIFT_2 = 0/1/2` | 太陽巖 無／進行中／已收到 |
| `VAR_MYSTERY_GIFT_3 = 0/1/2` | 月石 無／進行中／已收到 |
| `FLAG_MYSTERY_GIFT_DONE` | 拉力完成 |

```text
matching = saved flag ID == distribution flag ID and max stamps == 2 and icon species == CLAYDOL
if no card:                install shared card + delivery script + selected stamp, run activation
else if not matching:      offer the toss prompt; on accept, install as above
else if stamp species or ID already exists:   HAS_STAMP
else if neither slot empty:                   NO_ROOM_STAMPS
else:                      save the stamp, run activation, STAMP_RECEIVED
```

啟用部分是一段神秘事件包裝。`IsStampInMetadata` [mystery_gift.c:272] 會拒絕衝突的印章；`CLI_SAVE_STAMP` 只寫入 `cardMetadata.stampData` [mystery_gift.c:307]。

### 變化洞窟

官方指令碼 [data/mystery_event_msg.s:325] 給 `VAR_ALTERING_CAVE_WILD_SET`（0x4024，SaveBlock1 + 0x1048）加 1，在 10 處迴繞；值為 9 及以上時讀表 0 [wild_encounter.c:192]。

| 變數 | 物種 | | 變數 | 物種 |
|---|---|---|---|---|
| 0 | 超音蝠 | | 5 | 長尾怪手 |
| 1 | 咩利羊 | | 6 | 壺壺 |
| 2 | 榛果球 | | 7 | 驚角鹿 |
| 3 | 戴魯比 | | 8 | 圖圖犬 |
| 4 | 熊寶寶 | | | |

### 配送的蛋

三個日本配送活動，來自 GB-Link-Switch-LDN 的 `web/js/gift/official.js`。卡片用 `random` 抽取一枚蛋 [scrcmd.c:455]；它會帶上該配送的招式、命運邂逅位和 0xFF 的相遇地點。隊伍已滿時會在抽取之前拒絕。

| 卡片 | 蛋 |
|---|---|
| `wish-egg`（Pokemon Center New York） | 吉利蛋、催眠貘、蛋蛋、大蔥鴨、袋獸、大舌頭；各自都會許願 |
| `pokepark-egg`（PokePark Market Fantasia） | 刺球仙人掌、龍蝦小兵、太陽珊瑚、寶寶丁、負電拍拍、皮丘、正電拍拍、可達鴨、向尾喵、晃晃斑、跳跳豬、溜溜糖球、傲骨燕、咕妞妞、小果然 |
| `pc-japan-egg`（Pokemon Center Japan） | 喇叭芽（搖晃舞）、喵喵（花瓣舞）、走路草（寄生種子）、蚊香蝌蚪（天使之吻） |

### 活動寶可夢

`--gift event-pokemon --event-pokemon NAME` 傳送一隻由 PKHeX.Core 依 `EncounterGift3`（非蛋、非日本）按其 PID/IV 方式生成、並通過合法性檢查的第三世代配送寶可夢；卡片儲存時經神秘事件的 `givepokemon` 給出。隊伍已滿時返回狀態 3，卡片可以再次接收。預設是 WISHMKR 的基拉祈。

`NAME` 由訓練家名和物種組成：`WISHMKR Jirachi`、`CHANNEL Jirachi`、`Aura Mew`、`MYSTRY Mew`、`DOEL Deoxys`、`SPACE C Deoxys`、`ROCKS Metang`、所有 `10 ANIV` 物種，以及歐版的 `10ANNIV`、`10JAHRE`、`10ANNI` 和 `10ANIV` 釋出；`--language` 用於在語言間選擇。

該卡片與構建無關；`tests/test_frlg_english_cartridges.py` 會讓它在每張卡帶的 `RunMysteryEventScript` 上跑一遍。

### GB-Link 團隊卡片

GB-Link 團隊的自定義卡片（GB-Link-Switch-LDN 的 `cards/`，GPL-3.0）由一張神秘卡片加一段通過 `callnative` 呼叫 THUMB 程式碼的 RAM 指令碼組成。原始碼在 `vendor/gblink-cards/`；`scripts/gen_team_cards.py` 生成 `pokeldn/frlg/data/team_cards.json`，逐位元組復現他們全部 44 個 `BPRE 1.10` 載荷，`team_cards.py` 則註冊每個去掉 `custom-` 字首的 id。`starter-egg`、`rare-berries`（道具 173-175）和 `national-dex`（`FLAG_SYS_NATIONAL_DEX` 0x840）是用組合器重建的。

| 分組 | 卡片 |
|---|---|
| 改變一隻寶可夢 | `nature-mint`、`ability-capsule`、`poke-ball-changer`、`pokemon-gender`、`nickname`、`stat-judge`、`hidden-power`、`hidden-power-type`、`ev-training`、`friendship`、`pp-max`、`max-conditions`、`pokerus`、`unown-letters`、`trade-evolution`、`espeon-umbreon`、`move-tutor` |
| 逐幀鉤子 | `speed-2`、`speed-3`、`speed-4`、`speed-0-75`、`speed-0-5`、`fast-text`、`travel-anywhere`、`pc-anywhere`、`hm-moves`、`reusable-tms`、`physical-special-split`、`exp-share`、`shiny-hunting`、`roamer` |
| 其他 | `no-encounters`、`legendary-respawn`、`instant-eggs`、`gift-box`、`pocket-casino`、`gift-ribbons`、`trainer-ids`、`gender-swap`、`rival-name` |
| 活動寶可夢 | `box-eggs`、`colosseum-pikachu`、`ageto-celebi`、`mattle-ho-oh` |

與他們構建版的差異：

- 全部十二張 `0x0A` 修訂版卡帶：`vendor/gblink-cards/symbols.json` 儲存每張 ROM 的 167 個地址，`tests/test_team_cards.py` 校驗它們，每段指令碼還會檢查頭部的遊戲、語言和修訂版（[卡帶對映](frlg_rom_map.md#the-international-revision-0x0a-cartridges)）。
- 搬遷後的指令碼（996 位元組）和選單列表（80 位元組）位於 `0x0203F768` 和 `0x0203FB50`，在 `0x0203FC00` 的常駐鉤子之下（[載荷能放在哪裡](frlg_rom.md#where-a-payload-can-live)）。
- 鉤子安裝器鏈到 `VBlankIntr`，存放於 `0x0203FBFC`，因此鉤子卡片和遊戲增益會互相替換。它們的狀態在 `0x0203FF60`。
- 大於 1019 的 id 沒有 `sReceivedGiftFlags` 位；登錄檔傳送 `1000 + id mod 20`。
- `hm-moves` 和 `physical-special-split` 的文本被縮短，以塞進 995 位元組。

十二張卡帶上，每張卡片都能在 mGBA 下以繫結媽媽的形式執行。在另一款遊戲的卡帶上，載荷會回應「This gift doesn't work with this version of the game.」（日文為「Wrong game.」）。`colosseum-pikachu` 和 `ageto-celebi` 攜帶日文訓練家名，在歐洲卡帶上會顯示為圓點。

### 對戰計數卡片

`MysteryEventScript_BattleCard` [data/mystery_event_msg.s:162] 在 `GET_CARD_BATTLES_WON`（special 390）恰好為三時給一個傷藥；移植版按自己的變數設閘，所以可以重複。只有當 96 位元組訓練家卡片之後的 u16 等於當前卡片的 flag id 時，計數器才會推進 [union_room.c:1777]（`frlg_trade_host.py --card-flag-id N`）。

| 什麼會推進 | 在哪裡 | 規則 |
|---|---|---|
| `numTrades` | 一次完成的交換 [trade_scene.c:2609] | 卡片尚未計過的訓練家 id |
| `battlesWon` / `battlesLost` | 一場電纜俱樂部對戰 [cable_club.c:792] | 同上，每項 5 個 id |

聯盟室的對戰不計入任何東西；只有[電纜俱樂部競技場](frlg_link.md#the-cable-club-colosseum)計入。計數器位於 SaveBlock1 + 0x3434，沒有 CRC [mystery_gift.c:490]：

    0x3434: 0000 0000 0100 2300     trades 1, icon 35 (CARD_TYPE_LINK_STAT)

`CARD_TYPE_GIFT` 型別的卡片即使 special 執行過也保持為零。

### 來訪訓練家

`CLI_RECV_EREADER_TRAINER`（18，ident 26）把緩衝區複製到 `gSaveBlock2Ptr->battleTower.ereaderTrainer` [mystery_gift_client.c:233]。該結構為 188 位元組 [global.h:286]：

    0x00 u8  unk0                  0x10 u16 greeting[6]            0x34 BattleTowerPokemon party[3]
    0x01 u8  trainerClass          0x1C u16 farewellPlayerLost[6]  0xB8 u32 checksum
    0x02 u16 winStreak             0x28 u16 farewellPlayerWon[6]
    0x04 u8  name[8]
    0x0C u8  trainerId[4]

當前 46 個字不全為零、且那個 u32 是它們的和時才有效 [battle_tower.c:1354, :1384]。隨後 `SevenIsland_House_Room1` 裡的老婦人會提供一場由 `CreateBattleTowerMon` 構建的可重複 3v3 對戰 [battle_tower.c:928]；不適用等級規則，也沒有停用名單。FRLG 只顯示名字的五個位元組 [battle_tower.c:1343]。`--gift visiting-trainer` 會一起傳送卡片、RAM 指令碼和訓練家；若已持有同一張卡片，則只發訓練家。

## 神秘新聞

`struct WonderNews` [global.h:646] 為 444 位元組：

| 偏移 | 大小 | 欄位 | 說明 |
|---|---|---|---|
| 0x000 | 2 | `id` | 不能為 0，這是唯一的檢查 [mystery_gift.c:113] |
| 0x002 | 1 | `sendType` | `SEND_TYPE_DISALLOWED` 會隱藏「Send」 [mystery_gift.c:120] |
| 0x003 | 1 | `bgType` | `>= NUM_WONDER_BGS` 時讀作 0 [mystery_gift_show_news.c:110] |
| 0x004 | 40 | `titleText` | 在 224 px 的視窗中居中 |
| 0x02C | 400 | `bodyText[10][40]` | 螢幕上顯示八行；索引超過 7 的行會點亮滾動指示符 [:346] |

`IsWonderNewsSameAsSaved` 會比較全部 444 位元組 [mystery_gift.c:140]（`--news-id N` 可讓新聞變新）。新聞和卡片從不互相頂替。

- `build_wonder_news_app_data` 廣播活動號 22 [src/data/union_room.h:406]。
- 遊戲主機以 `MG_LINKID_RESPONSE`（ident 19）應答：`FALSE` 表示已儲存，`TRUE` 表示已持有 [mystery_gift_client.c:210; mystery_gift_scripts.c:126]。
- 來自好友模式的新聞會在 `ITEM_RAZZ_BERRY` 與 `ITEM_NOMEL_BERRY` 之間抽一種樹果，由 `CeruleanCity_House4` 裡的男人給出，最多五個，然後走 500 步 [mystery_gift_menu.c:1367, wonder_news.c:21]。四個樹果的獎勵需要那條被封鎖的無線路徑。

`--news`（`--news berry`、`--news-id N`）。訊息順序（約 18 s）：

    ident 16  sClientScript_SendGameData
    ident 17  MysteryGiftLinkGameData
    ident 16  sClientScript_SaveNews
    ident 23  MG_LINKID_NEWS - 444 bytes in three blocks
    ident 19  MG_LINKID_RESPONSE - FALSE: the console saved it
    ident 16  sClientScript_NewsReceived
    ident 20  READY_END                              -> SVR_MSG_NEWS_SENT

## 問卷作為口令閘門

`SVR_CHECK_QUESTIONNAIRE` 會比較友好商店問卷的四個詞 [mystery_gift.c:422]；`mg_server.gate_on_questionnaire(script)` 把它接在遊戲資料字首之後：

    bin/frlg_mg_host.py --gift ... --questionnaire species:55,FEELINGS/60,move:177,why

一個詞可以是英文名、`species:N`、`move:N`、`GROUP/INDEX` 或原始 id。短語不對時，遊戲主機會收到主機發來的 64 位元組訊息（`CLIENT_SCRIPT_DYNAMIC_ERROR`），別的什麼都不發。每次會話都會從 GameData 記錄遊戲主機的四個詞 [mystery_gift.c:361]：

    questionnaire: POKEMON/55  done [FEELINGS/60]  MOVE_1/177  why [MISC/37]

`EC_GROUP_POKEMON` 按物種索引，`EC_GROUP_MOVE_1` 按招式 id 索引；見[法語 Easy Chat 詞表](frlg_rom_map.md#the-french-easy-chat-vocabulary)。

## 遊戲主機會主動交出什麼

GameData 攜帶 Easy Chat 檔案和卡片統計 [mystery_gift.c:361]。`--game-data-log PATH`（`game_data_log.py`）會把每次會話追加到一份 JSONL 臺賬，並列印該遊戲主機上一次以來的變化；`tools/frlg/game_data_read.py PATH` 可讀取它。計數器只有在同一卡片 flag id 上作為差值才構成證據。

## 存檔備份與恢復

一次「神秘卡片、好友」會話會把遊戲主機整個 128 KiB 的存檔晶片複製到主機，或者把一個 `.sav` 寫進去並讓遊戲載入再儲存它；期間不傳送卡片。`asm/save-backup.s` 和 `asm/save-restore.s` 移植自 GB-Link 團隊的 `cards/savebackup.s` 和 `cards/saverestore.s`（GPL-3.0）；主機側是 `pokeldn.frlg.gift.save_transfer`（`--save-backup FILE`、`--save-restore FILE`），以及應用裡的「你的存檔」標籤頁（[你的存檔](gui.md#your-saves)）。兩者都能在全部十二張卡帶上執行（[存檔備份與恢復](frlg_rom_map.md#save-backup-and-restore)）。

### 令牌編碼

位元組 `n < 0x80` 後面跟 `n + 1` 個原樣位元組；`n >= 0x80` 則把一個位元組重複 `n - 0x80 + 3` 次（遊程 3 到 130，原樣位元組最多 128 個）。

### 備份

客戶端指令碼會把 `CLI_LOAD_TOSS_RESPONSE, CLI_RUN_BUFFER_SCRIPT, CLI_SEND_LOADED` 每段最多重複 32 次。每一趟為晶片上至多 8 KiB 的內容傳送至多 1 KiB 的令牌，絕不跨越 64 KiB 的 bank 邊界；晶片偏移是 `client->param = 0x5A << 24 | offset` [mystery_gift_client.c:276]，不帶 `0x5A` 的 `param` 會從 `first` 開始。

| 載荷字 | 偏移 | 值 |
|---|---|---|
| `first` | `0x004` | 第一趟起始的晶片偏移 |
| `send_queue` | `0x008` | `&gRfu.sendQueue.count` |

一趟會每幀把 `0x800` 位元組搬進 `gDecompressionBuffer + 0x800`，壓縮到 `+ 0x400`，並設定 `link.sendBuffer`（`param + 0x3C`）和 `link.sendSize`（`param + 0x34`）。當 `gRfu.sendQueue.count` 不為零時它等待。會話以 `CLI_MSG_BUFFER_FAILURE` 加一條訊息結束，因此遊戲主機不會存檔 [mystery_gift_menu.c:1379]。被截斷的備份按遊戲程式碼和訓練家 id 續傳。

### 恢復

1. 第一條訊息是 620 位元組的映象；`install` 把它複製到 `gDecompressionBuffer + 0x400`，並以 28 個槽位扇區的 12 位元組尾部（id、校驗和、簽名、`+0xFF4` 處的計數器）作答。
2. 主機按 `GetSaveValidStatus` 的方式找出最新的完整槽位，把檔案裡的副本寫進另一個槽位、計數器為 `newest + 1`，然後照檔案所寫寫入扇區 28 到 31。
3. 它先擦除目標槽位的 id-0 扇區，最後才寫新的 id 0，這樣在新的那份完整之前，晶片自己的副本仍能載入。
4. 之後的訊息以 `b RESIDENT + 4`（`0xEA0000FF`）開頭，然後是一個 op。`OP_DATA`（1）把扇區、寫入標誌、u16 偏移、u16 令牌長度和令牌帶進一個 4 KiB 緩衝區；該扇區的最後一條訊息用 `swi 0x48` 寫入並校驗，不匹配時置一個失敗掩碼位。一段客戶端指令碼最多攜帶 62 條資料訊息、涉及若干扇區，遊戲主機在它結束時一次性報告累積的失敗掩碼。新的 id 0 會自開一批，因此只有在其槽位其餘部分讀回完整之後才會傳送。
5. `OP_FINISH`（2）在沒有失敗時呼叫 `LoadGameSave(SAVE_NORMAL)` [save.c:803]。結果為 `SAVE_STATUS_OK` 時會話以 `CLI_MSG_BUFFER_SUCCESS` 結束，遊戲主機儲存載入後的遊戲；否則以 `CLI_MSG_BUFFER_FAILURE` 結束，舊存檔保留。

| 載荷字 | 偏移 | 值 |
|---|---|---|
| `b install` | `0x000` | 第一條訊息的入口 |
| `b entry` | `0x004` | 之後每條訊息的入口，位於 `gDecompressionBuffer + 0x404` |
| `load_game_save` | `0x008` | `LoadGameSave \| 1` |

若載入到的副本不完整或屬於另一種佈局，主機會拒絕該存檔：日文 SaveBlock1 短 40 位元組，這一點從訓練家自己那隻寶可夢的語言位元組（`+0x12`）讀出。

`tests/test_save_transfer.py` 針對指令碼化的遊戲主機覆蓋備份、續傳、恢復和被中斷的恢復。在零售硬體上，備份在法版和英版火紅上可用，恢復在英版火紅上可用（包括法版存檔）。遊戲主機的下一次存檔會在扇區 1 到 7 與檔案不同，那些扇區承載 `LoadGameSave` 重新擲出的加密金鑰。

## 創作禮物

`pokeldn.frlg.gift.gift_composer` 從 `WonderGift` 定義構建卡片和配送指令碼：

```python
MEWTWO_GIFT = WonderGift(
    slug="mewtwo-encounter",
    card=WonderCardSpec(icon_species=150, title="MYSTERIOUS ENCOUNTER",
                        body=("Visit the deliveryman.",), default_flag_id=1008),
    intro_message="A powerful presence is waiting!",
    event=GiftSpec(shareable="once"),          # or StampRallySpec(...)
    delivery=DeliveryPlan(delivery=(
        DeliveryStage(Message("Take this."), GiveItem(1)),  # Master Ball
        DeliveryStage(ShowSprite(0, RelativeToPlayer(dx=1)), BattleLegendary(150, level=70)),
    )),
    completed_message="That mysterious encounter is over.",
)
```

`WonderGift.delivery` 使用 `delivery`；`StampSlot.delivery` 和 `StampRallySpec.completion` 使用 `pre_stages` 和 `post_stages`。編譯器從 `VAR_MYSTERY_GIFT_1` 恢復階段，成功時置 `FLAG_MYSTERY_GIFT_DONE` 和收據標誌；`GiftSpec(repeatable=True)` 會重置游標。

### 階段與條件

每個 `DeliveryStage` 就是一個檢查點；絕不要把兩個可能失敗的獎勵（`GiveItem`、`GivePokemon`、`GiveEgg`）放進同一個階段。攜帶招式的 `GiveEgg` 需要一個隊伍空位。`GiveRandomEgg(eggs)` 通過跳轉表抽取一個（十五枚四招式的蛋可以塞進 944 位元組）。`condition=`（`VarEquals`、`FlagSet`、`Not`、`AllOf`、`AnyOf`）會跳過某個階段但推進游標；`RequireSpecialResult(...)` 在失敗時停下且不推進。

```python
DeliveryStage(ShowSprite(142, RelativeToPlayer(dx=1)),
              condition=VarEquals(0x4031, 0))  # VAR_STARTER_MON == Bulbasaur
DeliveryStage(RequireSpecialResult(SPECIAL_HAS_ALL_KANTO_MONS, 1, "Finish the KANTO POKEDEX first."),
              GivePokemon(251, level=50))
```

`SetVar`（`setvar` 0x16）和 `AddVar`（`addvar` 0x17）接受存檔變數 0x4000..0x40FF 和特殊變數 0x8000..0x8011。

### 對戰

`BattleLegendary` 會發出 `setwildbattle`、`special StartLegendaryBattle`、`end`，且不帶 `waitstate`（[RAM 指令碼可能無法從對戰中返回](frlg_rng.md#a-ram-script-may-not-come-back-from-a-battle)）；`BattlePokemon` 發出 `dowildbattle`。兩者都會結束自己的階段。印章槽位路徑中拒絕放置對戰，除非作為帶條件的終結備選。

### 共享

`GiftSpec.shareable` 設定卡片的 `sendType`：`"never"`、`"once"`（接收方的那份變得不可共享）或 `"always"`。

### 命運邂逅標記

`GivePokemon(..., fateful_encounter=True)`（以及 `GiveEgg`）會發出 `setmonmodernfatefulencounter`（`0xCD`）和 `setmonmetlocation`（`0xD2`，0xFF）[data/mystery_event_msg.s:71]。第一條命令不檢查索引邊界 [scrcmd.c:2239]；索引是給出之前的隊伍數量，隊伍已滿時會跳到失敗標籤。概要介面那一行只來自相遇地點 [pokemon_summary_screen.c:2665, 2799]；`modernFatefulEncounter` 是 Misc+0x08 的第 31 位 [include/pokemon.h:40-82]。

### 組合器中的 `initramscript`

`gift_composer.build_bound_script(actions)` 和 `build_mevent_npc_script(actions=...)` 把動作編譯成 `initramscript` 所繫結的場地指令碼。它沒有階段游標，每次都會整個重跑，所以只應發生一次的效果需要自己的 `SetVar` 或條件。

### 註冊與校驗

```python
from pokeldn.frlg.gift.gift_registry import GIFT_REGISTRY
GIFT_REGISTRY.register_definition(MEWTWO_GIFT)
```

註冊時會校驗並編譯：卡片文本與標誌、計劃結構、動作範圍、游標邊界、印章唯一性、對戰放置、指標以及 995 位元組的 RAM 指令碼上限，出錯時會指出路徑（`example-rally.event.slots[1].delivery.post_stages[0].actions[1]: ...`）。

## 靜態工具

```bash
./.venv/bin/python -m pokeldn.frlg.gift.gift_to_bin --gift beast-cutscene --flag-id 1005 --out-dir exported-gift
./.venv/bin/python -m pokeldn.frlg.save.save_inject game.sav --gift beast-cutscene --flag-id 1005
```

`gift_to_bin` 會為 `pokemon-gen3-mysterygift-tool` 寫出 336 位元組的神秘卡片和 1004 位元組的 RAM 指令碼。`save_inject` 把兩者寫進活動槽位，修正卡片、RAM 指令碼和扇區的校驗和，並另存為 `<save>.gift.sav`（`--in-place` 會覆蓋原檔案；`--make-artifact` 會在 `artifacts/` 下寫出一個 `.ram.lst` 清單）。

## 被封鎖的路徑

### 無線通訊（JoySpot）

無線路徑在 RFU 序列號閘門上被擋住：

| | 好友 | 無線通訊 |
|---|---|---|
| 監聽函式 | `Task_ListenForCompatiblePartners` [union_room.c:3757] | `Task_ListenForWonderDistributor` [union_room.c:3799] |
| 接受的 RFU 序列號 | `{0x0002, 0x7F7D}` | 僅 `== 0x7F7D` [link_rfu_3.c:920] |
| 選擇 | 玩家從列表中選擇 | 自動連線 |
| 能否從 Switch 到達 | 可以 | 不行 |

`Task_CardOrNewsOverWireless` [union_room.c:2415] 只在候選 0 的 `serialNo` 為 `0x7F7D` 時保留它，然後檢查生成狀態、`hasCard` 位（失敗時為 SE_BOO）並重連。Switch 橋報告的是 `0x0002`，而廣播裡沒有序列號欄位；`svc_47` [sloopsvc.c:34] 接收 24 位元組且不含序列號。一條原生廣播：

```
50 10 | c1 cc bf bf c8 ff 00 00 | 65 ac | 00 00 00 00 | 84 15 | 00 00 00 00 00 00
TID   | uname                   | parent| unexplained | search| unexplained
```

`record[16:18]` 處的搜尋字是 `activity:7 | bit7 | version:3 | language:3 | hasCard?:1 | startedActivity:1`。

試過的每一種廣播變體（scene id、應用版本、在每個空閒偏移放 `0x7F7D`、活動號、`hasCard`、第 7 位）都沒能從無線路徑換來一次認證。未測試：`local_communication_id`、暴力列舉 scene、各種組合。

### e-Reader 本身

訓練家之塔的 e-Reader 套件走 GBA 序列鏈路（`ereader_screen.c`）上的 `LINKTYPE_EREADER_FRLG`，不走無線介面卡。

### 極光票與神秘票

Switch 版在首次進入名人堂時就會給出兩張票及它們的 `FLAG_RECEIVED_*` 標誌 [post_battle_event_funcs.c:52, `REVISION >= 0xA`]，所以此後的票據卡片不再給任何東西。卡片的 `iconSpecies` 若不是 `SPECIES_NONE` 就會畫一個圖示；超過 `SPECIES_UNOWN_B - 1` 則畫問號 [mystery_gift_show_card.c:466, pokemon_icon.c:1102]。古代海圖僅限綠寶石 [mystery_gift.c:30]。

## 陷阱

- `charmap.encode` 會丟棄未知字元，換行符也在內。換行是 0xFE；`mg_server` 拒絕第三行，或寬度超過 31 個字元的行 [strings.c:1291]（視窗 28 格寬 4 格高，[mystery_gift_menu.c:97,524]）。
- 新的載荷要同時加進 `buffer_script.py` 的 `DUMP_SCRIPTS` 和 `DECODED_SCRIPTS`，以及啟動器的 `--dump-file` 行。
