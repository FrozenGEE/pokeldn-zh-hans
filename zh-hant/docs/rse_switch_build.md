---
title: Switch 版構建
parent: 紅寶石、藍寶石與綠寶石
nav_order: 3
nav_exclude: true
search_exclude: true
app_exclude: true
---

# 給 Switch 火紅應用用的綠寶石

這個 Switch 版構建就是 pret/pokeemerald，加上從 pokefirered 移植過來的 `REVISION >= 0xA` 改動，連結時讓火紅/葉綠應用的載入期補丁正好落在綠寶石的無線驅動上。它代替火紅卡帶執行：在模擬主機上它能存檔、收神秘禮物、交換，也能對著 pokeldn 的主持端用聯盟室。`tools/rse/pokeemerald_switch.patch` 是針對 pret 提交 `731ad5bf` 的移植補丁；`tools/rse/emerald_switch_build.py` 負責應用並構建它。

## 應用對卡帶的要求

英文 Switch 火紅 ROM 就是 pret/pokefirered 的 `make compare_firered_switch`（見 [ROM 對映表](frlg_rom_map.md#the-cartridge-image)）；移植就是那個構建與 REVISION 1 之間的差異，施加到綠寶石裡同一批檔案上。

- **系統呼叫。** 應用提供 `swi 0x40..0x62`（Sloop 呼叫，見[在主機上執行程式碼](frlg_rom.md)）。`src/sloopsvc.c` 是 pokefirered 的原樣檔案：無線介面卡呼叫（`0x42..0x53`）、`WriteSector`（`0x48`）、`ReplaceSector`（`0x56`）、`FinishSave`（`0x4C`）、家長控制（`0x54`）、髒詞過濾（`0x4D`）、`SetSaveBlock2`（`0x55`）、`SetStarter`（`0x57`）、`SetActivity`（`0x61`）和 `IncrementLinkError`（`0x62`）。
- **存檔。** 應用只在 `svc_FinishSave` 時把快閃記憶體映象寫進儲存。這個構建通過 `svc_WriteSector`/`svc_ReplaceSector` 寫扇區，並在 pokefirered 呼叫 `svc_FinishSave` 的地方呼叫它：`HandleSavingData` 末尾、特殊的存檔扇區、最後一個鏈路存檔扇區。
- **固定地址上的驅動。** 載入時應用會在卡帶自己的 `Sio32IDMain + 0x12E`、`IntrSIO32 + 8` 和 `IntrSIO32 + 0x71C` 處打三個指令補丁（見[斷點鉤子](frlg_rom.md#the-breakpoint-hooks)）。`ld_script_switch.ld` 把 `librfu_sio32id.o` 與 `librfu_intr.o`（`+0x30C`）放進一個位於卡帶對應地址的 `sloop_rfu` 段；除字面量指標與 `bl` 偏移外，這些程式碼位元組就是火紅的。

| 卡帶 | `librfu_sio32id.o` | | 卡帶 | `librfu_sio32id.o` |
|---|---|---|---|---|
| BPRE | `0x081E2814` | | BPGE | `0x081E27F0` |
| BPRF | `0x081E1568` | | BPGF | `0x081E1544` |
| BPRD | `0x081E702C` | | BPGD | `0x081E7008` |
| BPRI | `0x081E0200` | | BPGI | `0x081E01DC` |
| BPRS | `0x081E28C8` | | BPGS | `0x081E28A4` |
| BPRJ | `0x081C66EC` | | BPGJ | `0x081C66C8` |

日版的這兩個地址落在綠寶石的 `.text` 裡面，所以那兩版卡帶不做構建。

## 補丁改了什麼

每處改動都包在 `#if REVISION >= 0xA` 裡，所以 `make compare` 仍然與 pret 的 ROM 一致。

| 區域 | 檔案 |
|---|---|
| 構建 | `Makefile`（`REVISION`、`SWITCH_CART`、地址表、`make emerald_switch`）、`ld_script_switch.ld`、`sym_common.txt` |
| 系統呼叫 | `include/sloopsvc.h`、`src/sloopsvc.c` |
| 介面卡庫與鏈路管理 | `librfu.h`（版本 1028）、`librfu_rfu.c`、`AgbRfu_LinkManager.{c,h}`：那批 svc 呼叫、更長的週期、關閉鏈路恢復 |
| 鏈路層 | `link_rfu_2.c`（rev10 的超時、重新播種、`svc_51` 上的過載與軟復位）、`link_rfu_3.c`（ASCII 表）、`link.c`（錯誤畫面、`HandleLinkConnection`） |
| 聯盟室 | `union_room.c`（主持與加入組的狀態機、活動上報、家長控制）、`union_room_chat.c` 與 `naming_screen.c`（髒詞過濾）、`union_room_player_avatar.c`、`union_room_battle.c` |
| 存檔 | `save.c`、`load_save.c`、`main.c`（`svc_SetSaveBlock2`、黑色背板、軟復位時不等待介面卡） |
| 保護性檢查 | `cable_club.c`、`trade.c`、`field_screen_effect.c`、`menu.c`、`task.c`、`wireless_communication_status_screen.c`、`mystery_gift_menu.c`、`battle_setup.c`（`svc_SetStarter`） |

沒有移植的部分：pokefirered 的片頭配色、狀態畫面的計數、鏈路測試的移除、名人堂票券、樹果修復、中毒閃屏速度、多選預設值和 `NDEBUG`。交換仍保留綠寶石的五輪交換後待機（見[交換](rse_link.md#trade)）。

## 構建

需要 pret/agbcc、arm-none-eabi binutils 和一個 C 前處理器。

    ./.venv/bin/python tools/rse/emerald_switch_build.py --tree ~/pokeemerald_switch --agbcc ~/agbcc \
        --cart BPRE --cpp /opt/homebrew/bin/cpp-16 --compare

`--tree` 指定的目錄不存在時會自動克隆，並檢出到基線提交。`--agbcc` 會把 agbcc 的 `install.sh` 跑進那個目錄。`--compare` 還會額外構建 REVISION 0 並跑 pret 的 sha1 校驗。如果連結指令碼把 `librfu_sio32id.o` 放到了卡帶地址以外，工具會拒絕這個 ROM。Homebrew 裡沒有 `arm-none-eabi-cpp`；用 `--cpp` 指定另一個。

從一個全新克隆出發，BPRE 構建的 sha1 是 `4e0a7e203e761cbb861ec65e98b31d6657083865`，REVISION 0 構建則通過 `pokeemerald.gba: OK`。

## 執行它

應用每次啟動都從自己的 RomFS 載入 ROM（見 [ROM 對映表](frlg_rom_map.md)），所以在那個路徑上放一個 LayeredFS 檔案就能替換卡帶，直到把它刪掉。`tools/rse/rom_mod.py` 可以把這樣一個檔案裝進模擬器的 mod 目錄或 Atmosphere 的 SD 卡：

    ./.venv/bin/python tools/rse/rom_mod.py install pokeemerald_switch_BPRE.gba --title 0100554023408000
    ./.venv/bin/python tools/rse/rom_mod.py install pokeemerald_switch_BPRE.gba --title 0100554023408000 --sd /Volumes/SWITCH
    ./.venv/bin/python tools/rse/rom_mod.py remove --title 0100554023408000

ROM 必須與該標題的卡帶相符：英文火紅用 BPRE（`0100554023408000`），法版火紅用 BPRF（`01004B3023412000`）。遊戲沿用該標題的存檔檔名（`FireRed_e.sav`）；綠寶石存檔與火紅存檔不能共用同一個檔案，所以先把火紅的存檔備份好。

在模擬主機上（英文火紅，BPRE 構建），綠寶石以 60 FPS 啟動，不顯示電池耗盡提示，能存檔，重啟後也能讀回存檔。把模擬器的 LDN 指向 Mac 時，主持端的 `--over-ip` 可以為它服務（見[交換與聯盟室](rse_link.md)、[神秘禮物](rse_gift.md)）。

## 測試存檔

這些鏈路功能都藏在劇情標誌位後面。`tools/rse/emerald_save.py` 會編輯遊戲實際載入的那個槽位並重算校驗和（見[存檔](rse.md#the-save)）：

    ./.venv/bin/python tools/rse/emerald_save.py FireRed_e.sav --link-ready --copy-party-mon 0

| 標誌位 | 開啟什麼 |
|---|---|
| `FLAG_SYS_POKEDEX_GET` `0x861` | 寶可夢中心 2 樓的店員 |
| `FLAG_SYS_MYSTERY_GIFT_ENABLE` `0x8DB` | 標題選單裡的 MYSTERY GIFT |

`--link-ready` 會把兩者都置上，並設一個到古辰鎮寶可夢中心 2 樓（地圖組 2、地圖 3、x 5、y 4）的繼續傳送點。`--copy-party-mon N` 會用新的 PID 複製一份第 N 號隊伍的寶可夢追加到隊尾，這樣只有一隻寶可夢的存檔也能交換。圖鑑標誌位只讓 POKéDEX 選單出現，裡面沒有任何見過或捕捉的記錄。

## 不用 Atmosphere 的投遞方式

裝了 Atmosphere 的主機可以直接吃 LayeredFS 檔案（見[執行它](#running-it)）。未破解的主機只讀該標題簽過名的 RomFS，所以只能在遊戲內部、每次啟動時，通過存檔傳輸所用的同一條神秘禮物原生程式碼通路，把 ROM 寫進正在執行的那份 ROM 副本（見[存檔備份與恢復](frlg_gift.md#save-backup-and-restore)）。

三個機制都已實測，支撐起整個設計：

- 帶 `r0 = 0xFA000 + n`（n 在 0..0xFFF）的 `swi 0x48` 會把 4 KB 從客戶機記憶體裡的源地址寫進 ROM 副本的 `0x08000000 + n * 0x1000`，覆蓋全部 16 MB（見[快閃記憶體扇區通路](frlg_rom.md#the-flash-sector-path)）。
- 這樣寫進去的程式碼能跑：一份複製到 `0x083FF000` 的例程在被跳轉過去時執行了（見 [frlg_rom.md](frlg_rom.md#the-flash-sector-path)）。
- 存檔傳輸把壓縮資料拆成許多條神秘禮物訊息，流進 EWRAM 裡一塊常駐區域，每次解壓 `0x800` 位元組並寫入一個扇區，每條訊息大約 1 KB 的 token（見[存檔備份與恢復](frlg_gift.md#save-backup-and-restore)）。

ROM 傳輸就是那條流水線，只是把寫入目標從快閃記憶體扇區（0..13）換成 ROM 摺疊區（`0xFA000 + n`），並且最後是啟動而不是存檔。每次啟動都要重來一遍，因為應用每次啟動都會從 RomFS 重新載入 ROM 副本。

### ROM 傳輸

`bin/frlg_mg_host.py --rom-transfer ROM` 會跑它（`pokeldn.frlg.gift.rom_transfer`、`asm/rom-transfer.s`；`--rom-no-boot` 在校驗後停下）。一次會話是：

1. 裝載負載，同時停掉 m4a 引擎（把 `gSoundInfo.ident` 和 `SOUNDCNT_X` 清零）：否則音樂會去讀正在被替換的那份 ROM 裡的歌曲與波形資料；
2. 對 ROM 副本的全部 4096 個塊做雜湊（`h = rotl(h, 1) ^ word`，每幀 32 個塊）；
3. 把雜湊與映象不同的每個塊寫下去，每 62 條訊息一個確認，每塊都經 ROM 視窗讀回校驗；連續的同位元組塊會合併成一條填充訊息，一次最多八塊；
4. 再對所有塊雜湊一遍並比對；
5. 傳送啟動操作：關掉 `IME` 與四個 DMA 通道，把暫存的塊移到正確位置，映象之後的塊變成 `0xFF`，然後 `swi 0x00`。

因為有雜湊這一遍，被打斷的會話能在同一次應用啟動內續傳：下一次會話只寫仍然不同的那些塊。

在模擬的英文火紅上經 IP 主持端實測：把火紅映象的三個標題畫面調色盤改色（塊 `0xEAB`、`0xEAD`、`0xEAE`），這三個塊被就地寫入，151 個活動塊被暫存到 `0xEB1`，校驗通過，啟動操作之後主機經過片頭重啟，進了改過色的標題畫面。

完整的 BPRE 綠寶石構建也曾在模擬英文火紅上流式傳輸並啟動成功：3073 個塊就地寫入，157 個活動塊暫存到 `0xE3D`，3,691,122 位元組的 LZMA 分成 4268 條訊息（`--block-repeat 1 --inter-block-gap-frames 8`，訊息按 10 幀解碼量切分），校驗一次通過，啟動操作在 3 小時 12 分時發出，隨後是綠寶石的片頭和它在火紅應用裡的標題畫面。過了標題，綠寶石列印了「內部電池已耗盡。遊戲仍可進行。」和「但基於時鐘的事件將不再發生。」，然後是一個主選單，在火紅的存檔檔案上提供 CONTINUE（玩家名與遊戲時間都讀了回來，0 枚徽章）。通過 LayeredFS 在啟動時載入的綠寶石不顯示電池提示；應用啟動流程裡哪一步設定了時鐘目前不明。

ROM 副本帶著應用打的三個 librfu 補丁（見[斷點鉤子](frlg_rom.md#the-breakpoint-hooks)），而卡帶檔案本身沒有這些補丁。寫映象時會在卡帶的 `librfu_sio32id.o` 對應位置（`builds.SIO32ID`，偏移 `+0x12E`、`+0x314`、`+0xA28`；十二版卡帶都核對過那裡的位元組）施加同樣的補丁。如果映象裡那幾處的位元組不是該卡帶的指令，就會被拒絕：補丁會落到別的程式碼上。

### LZMA 流

用 `--rom-base` 指定主機自己的卡帶 ROM 後，塊會以 LZMA（lc 0、lp 0、pb 2，`pokeldn.frlg.gift.rom_lzma`）編碼，而不是用遊程與字面量 token。字典就是主機上那份副本本身：16 MB 以下的虛擬位置指向副本的位元組，超出部分指向流的輸出。從 0 到仍需寫入的最高塊，每一塊都要產出，按主持端先寫 `0xFFD` 與 `0xFFE` 兩個 ROM 塊這樣的順序排列：先做一遍不限可用性的掃描，記下每個塊從哪些副本塊複製，然後讓一個塊排在它取用 8 位元組以上的任何副本塊之前（拓撲排序，塊號大的優先）。只有當某個副本塊仍保持著掃描時看到的內容時，匹配才允許指向它：還沒被流覆蓋、是活動塊，或者從未被觸碰。匹配會在它不得讀取的塊之前停下；匹配之後的一個字面量，按主機在那個位置的位元組編碼。

解碼器（`asm/rom-lzma.c`，用 clang 編譯出的 1768 位元組 Thumb）從 ROM 塊 `0xFFF` 執行，那一塊由主持端最先寫入，啟動時的填充會用順序表把它清掉。它的狀態連同 5.2 KB 機率表共 6.9 KB，放在 `gDecompressionBuffer + 0x2000`。它每幀解大約一千位元組（在 unicorn 下每次呼叫最多 98,000 條指令），在一條訊息被消費完之前返回 0，於是客戶端下一幀再調它。解完的塊用 `swi 0x48` 寫入並讀回校驗。主持端在工作程序裡編碼，同時用單塊掃描讓鏈路保持忙碌。

主機在還在跑上一條訊息時會丟掉新到的鏈路塊。編碼器記錄解碼器每位元組流的開銷（一個符號 6 單位，一個複製的位元組 1 單位，每幀 1000 單位）；一個符號要等解碼器攢夠 20 位元組的前瞻才開始解，也就是比編碼器的計數超前 25 位元組，所以它的工作量落在送來這些位元組的那條訊息上。每條資料訊息攜帶它引起的解碼幀數再加 6 幀；下一條訊息的頭塊可以在解碼期間到達，它的第二塊只能更晚。一小段流如果對應一長串 `0xFF`，可能解上一百多幀。

| 綠寶石（BPRE）的編碼方式 | 位元組 |
|---|---|
| 遊程與字面量 | 11,667,649 |
| 遊程與字面量，外加從任何仍有效的 ROM 位元組取用的複製 token（離線） | 9,081,120 |
| 對著主機副本的 LZMA，降序排列（57 段，編碼耗時 26 秒） | 3,691,122 |
| 同一種編碼，參照順序（離線） | 3,206,459 |
| 不限可用性的 LZMA，貪心（離線下界） | 3,027,095 |

### 活動塊

會話要執行火紅自己的鏈路與神秘禮物程式碼，而它正在覆蓋這份副本。這些塊最後寫：新位元組先寫進兩份映象之外的暫存塊（BPRE 上是 `0xEB1` 到 `0xFFF`，共 335 塊），再由啟動操作搬過去。

英文火紅（BPRE）的這套集合是 157 塊，見 `pokeldn/frlg/data/rom_live_blocks.json`：一次模擬會話會執行的函式（傳輸過程中對 GBA `pc` 採了 2.16 億次宿主側樣本，落在 327 個函式、53 個塊裡）、它們的直接被調者，以及它們字面量池指到的資料。把副本其餘所有塊都填成 `0xFF` 後，一次模擬英文火紅會話照樣完成了寫入和校驗，並列印了結束訊息。再順著資料指標往外收，幾乎能覆蓋整個 ROM（兩級就到 3380 塊）。其餘十一版卡帶沒有實測集合，會被拒絕。

### 速率

模擬英文火紅經 IP 主持端：完整雜湊一遍要 120 秒（每 32 塊的回答 0.6 秒）；一條 1 KB 的資料訊息要 6.3 秒（160 B/s）；2077 個塊作為填充訊息花了 400 秒。在預設節奏下，一個 252 位元組的鏈路塊約耗 80 幀：21 個分片各發兩遍（`block_repeat`），加一個 36 幀的間隔（`inter_block_gap_frames`），而鏈路上本來是每幀一個分片。

綠寶石（BPRE）在它的 `0xFF` 尾巴之前是 14,929,764 位元組，3645 個 4 KB 扇區，且每一個都與火紅 Switch 映象同偏移的扇區不同，所以沒有扇區可以跳過。一條訊息攜帶 1012 位元組 token（1 KiB 鏈路緩衝減去 12 位元組頭）：

| 編碼方式 | 流大小 | 訊息數 | 解碼器 |
|---|---|---|---|
| 存檔傳輸用的遊程與字面量 | 11,667,649 位元組 | 14,566 | GBA 側已有，已測試 |
| 不做過熵編碼的複製/字面量格式，對著整個火紅映象與綠寶石自身的輸出做匹配，位元組對齊 token | 8,470,154 位元組 | 8370 | 未實現 |
| LZMA2，64 KB 視窗 | 6,169,577 位元組 | 6097 | 未實現 |
| LZMA2，不限視窗 | 5,747,728 位元組 | 5680 | 未實現 |
| 以火紅映象為字典的 LZMA2 | 2,561,046 位元組 | 2531 | 未實現 |

DEFLATE 的 32 KiB 視窗看不穿兩個 ROM 之間 15 MB 共用的庫與引擎程式碼，所以在 `zlib` 下用火紅當字典幾乎沒用（6,991,630 位元組，完全不用字典是 6,975,681 位元組）：字典帶來的收益只對跟 ROM 一樣大的視窗成立。而解碼器的複雜度不必隨視窗增長：一個複製 token 可以不加額外成本地寫明任意 32 位源地址，所以不限視窗的匹配器所需的解碼器和存檔傳輸現有的那個一樣，都是分發加 memcpy，只多一種 token 型別。在火紅映象與綠寶石自身輸出上對著雜湊鏈匹配器（6 個候選，5 位元組鍵）實測，這種格式仍比 LZMA2 差約 3.3 MB：LZMA2 在視窗之外的大部分優勢來自它的區間編碼器把短匹配和字面量打包成幾分之一位元組，這是位元組對齊格式做不到的。要達到 LZMA2 的數字，GBA 側需要真正的熵編碼器，而不只是更大的視窗。`tools/rse/emerald_switch_build.py` 已經為這個目標帶著一套可用的 agbcc / arm-none-eabi 工具鏈，所以那個解碼器更適合從現成的小型 C 語言 LZMA 或 LZMA2 參考解碼器改造並交叉編譯，而不是從零手寫彙編；目前還沒有這樣的實現。

在板子上做一次正版機恢復，每秒約 150 位元組 token，再加每扇區約 3.5 秒：19 個扇區花了 107 秒、6182 位元組 token，27 個扇區花了 249 秒、27,421 位元組 token，兩點擬合，未經第三次執行確認。按這個速率，整條流在存檔傳輸編碼下約需 22 小時，在無熵編碼格式下 16 小時，LZMA2 下 11 小時，用火紅當字典則 5 小時；3645 個扇區按每扇區 3.5 秒再給上述任一數字加上 3.5 小時——前提是每個扇區仍沿用恢復流程裡每扇區一次往返的確認。恢復現在每條確認最多發 62 條資料訊息（見[恢復](frlg_gift.md#restore)），ROM 傳輸用的是同樣的批處理。目前測到的最長會話持續了 269 秒。

啟動會寫入 GBA 的 SoftReset 標誌並執行 `swi 0x00`：BIOS 清空 RAM 後跳到 `0x08000000` 的 ROM 復位向量，於是綠寶石自己的 `AgbMain` 從剛寫好的位元組開始初始化。BIOS 軟復位在核內完成，不算一次應用啟動，所以對 ROM 副本的寫入能活過它。rom-reset-probe 負載（`asm/rom-reset-probe.s`）往 ROM 副本塊 0xF00（0x08F00000，在火紅的 `0xFF` 尾巴里）寫了 `word[i] = 0x454D4552 + i`，執行 `swi 0x00`，重啟後第二次神秘禮物會話匯出了 0x08F00000：16 個字全部原樣讀回（英文火紅，模擬主機，經 IP 主持端）。RomFS 的過載發生在應用啟動時而不是軟復位時，所以寫進去的 ROM 能挺過這次啟動，進入新遊戲。

## 尚未解決

- 應用是否模擬綠寶石讀取的 GPIO 即時時鐘：在啟動時載入的綠寶石主選單不顯示電池提示，而流式傳輸進去的會顯示。
- 正版主機能否執行這個構建：目前只有模擬主機上的測量。
- 流式啟動之後的即時時鐘，以及綠寶石在繼續火紅存檔時會做什麼。
- 正版主機上經板子的傳輸流，以及那裡的節奏。
- 錯誤路徑所需的活動塊。在一次模擬流寫到第 2816 塊時出現鏈路錯誤，在錯誤畫面按 A 得到黑屏：回到標題的路徑位於已被覆蓋的塊上，所以被打斷的流只能從重啟應用開始。
- 為什麼模擬主機的鏈路在流式傳輸中途停了兩次（一次在 20 分鐘後，一次在 1 小時 49 分後），而幀率直到最後一秒都穩定。後一次停止時，主機自己的鏈路層在開啟一批的那條短訊息之後 0.27 秒發出了 RFU 斷開幀（`0x44`），在此之前兩個方向都是滿速；究竟是什麼讓它放棄仍不清楚。
- 其餘十一版卡帶的活動塊。
- 持續數小時的會話能否穩定維持。
- 綠寶石往火紅存檔檔案裡存過之後，火紅會怎麼處理它。
- 日版卡帶的構建。
