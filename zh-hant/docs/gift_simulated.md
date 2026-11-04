---
title: 模擬神秘禮物
---
# 模擬神秘禮物

模擬神秘禮物會把一隻官方禮物寶可夢帶給一款無法通過本地無線接收神秘禮物卡片的遊戲：遊戲的交換 Host
以收到該禮物的訓練家的身份提供一份全新的合法副本，主機的玩家則交換一隻寶可夢迴去，這隻寶可夢會進入
Received。指定接收者的禮物會為主機自己的存檔生成（[為接收玩家而生成](#made-for-the-receiving-player)）。

| 遊戲 | 工具 | 對應的 Host | 提供標誌 |
|---|---|---|---|
| Let's Go | `lgpe-gift-host` | Trade (Host)，`bin/lgpe_host.py` | `--offer` |
| 晶燦鑽石/明亮珍珠 | `bdsp-gift-host` | Trade (Host)，`bin/bdsp_host.py` | `--offer` |
| 傳說 阿爾宙斯 | `pla-gift-host` | Trade (Host)，`bin/pla_host.py` | `--trade-box-record` |
| 朱/紫 | `sv-gift-host` | Trade (Host)，`bin/sv_host.py`（[為主機承載](sv.md#hosting-for-a-console)） | `--trade-offer` |
| 傳說 Z-A | `za-gift-host` | Trade (Host)，`bin/za_host.py` | `--trade-offer` |

每個工具都是其遊戲中的 Trade (Host)，按交換順序最多六隻活動寶可夢（`catalog.simulated_gift`）；
Host 在多次交換之間保持會話。

## 禮物

PKHeX.Core 內嵌了其合法性檢查所知的每一個分發內容，每款遊戲一張表；不會下載任何東西。PKHeX 服務的
`gift_events` 會列出某張表中的寶可夢卡片（不含蛋和道具卡），按
`EncounterServerDate.GetDistributionWindow` 從新到舊排列，無日期的卡片排在最後。PKHeX.Core 26.10.18
中有：

| 遊戲 | 表 | 禮物寶可夢 | 開放時間 | HOME 的 | Your OT |
|---|---|---:|---|---|---:|
| Let's Go | `MGDB_G7GG` | 15 | 無日期，但 HOME 的美錄坦除外（2025 年 2 月 11 日） | 美錄坦（9028） | 3 |
| 晶燦鑽石/明亮珍珠 | `MGDB_G8B` | 9 | 2022 年 5 月 18 日到 2025 年 1 月 27 日，5 張無日期 | 草苗龜、小火焰猴、波加曼（9015 到 9017）、瑪納霏（9026） | 3 |
| 傳說 阿爾宙斯 | `MGDB_G8A` | 11 | 2022 年 1 月 27 日到 2025 年 1 月 27 日 | 木木梟、火球鼠、水水獺（9018 到 9020）、眷戀雲（9027） | 3 |
| 朱/紫 | `MGDB_G9` | 106 | 2022 年 11 月 17 日到 2026 年 6 月 5 日 | 新葉喵、呆火鱷、潤水鴨（9021 到 9023）、美洛耶塔（9024）、烈咬陸鯊（9035） | 29 |
| 傳說 Z-A | `MGDB_G9A` | 9 | 2025 年 10 月 14 日到 2026 年 8 月 28 日 | 菊草葉、暖暖豬、小鋸鱷（9031 到 9033）、波爾凱尼恩（9034） | 5 |

禮物的鍵是 `card-species-form`，在朱/紫中還要加上太晶屬性（`0503-964-0-10` 是 Gavin 的海豚俠）。
朱/紫的卡片 1521 包含十八隻夢幻，每種太晶屬性一隻。

工具會按設定中的訓練家收到它時的樣子列出每個禮物（PKHeX 的 `ConvertToPKM`）：卡片固定了 OT 和語言時
用卡片的，否則用 Your OT，並帶上等級、太晶屬性、是否閃光、攜帶道具和開放日期
（[神秘禮物 - 模擬](gui.md#mystery-gift---simulated)）。如果一張 Your OT 卡片從未在設定中訓練家的
語言下發放過，則列為非法。

### 卡片發放到過的存檔

Your OT 副本把接收的存檔作為其 OT，因此它必須是卡片發放到過的存檔。`gift_event` 會以 `refused` 回覆
並給出原因，允許時原因為空（`services/pkhex/Program.cs`）：

- 語言：副本使用存檔的語言。如果卡片固定了另一種語言，則由 PKHeX 的 `CanHaveLanguage` 決定
  （`InTrainerLanguage`）。
- 版本：在 `"only_version"` 下，卡片會拒絕它從未發放到的版本（`ReachedVersion`）。HOME 的卡片
  （9000 起）發放到了任一版本；另一張固定了來源的卡片只發放到該版本；否則由 `RestrictVersion`
  （Let's Go 的 `IRestrictVersion`）決定。

自帶訓練家的卡片永遠不會被拒絕：它的副本是交換來的寶可夢。在 PKHeX.Core 26.10.18 中，唯一被拒絕的
Your OT 卡片是 Let's Go 的美錄坦和美錄梅塔（1501、1502），它們僅在簡體中文下合法
（`WB7.IsMainlandChinaGift`）。

### HOME 的禮物

PKHeX 的 HOME 卡片重建了 HOME 所發放的內容：

| OT | 圖鑑 | 卡片 | 為接收玩家而生成 |
|---|---|---|---|
| HOME | "Simulated HOME" | Let's Go 的美錄坦（9028）、瑪納霏（9026）、眷戀雲（9027）、美洛耶塔（9024）、波爾凱尼恩（9034） | 否：按生成的樣子發出 |
| 接收訓練家的 | "Simulated (Trainer)" | 草苗龜、小火焰猴、波加曼（9015 到 9017）；木木梟、火球鼠、水水獺（9018 到 9020） | 是 |
| 接收訓練家的，帶經手人 | "Simulated (Trainer)" | 新葉喵、呆火鱷、潤水鴨（9021 到 9023）；菊草葉、暖暖豬、小鋸鱷（9031 到 9033） | 否：隨設定中的訓練家發出 |
| PJCS26，日文 | "Simulated PJCS26" | 朱/紫的烈咬陸鯊（9035） | 否：按生成的樣子發出 |

在 Let's Go 之外，HOME 禮物帶有 HOME 追蹤碼，由 [HOME 追蹤碼設定](gui.md#the-home-tracker-setting)
設定：`empty` 下沒有（這是 PKHeX 唯一的抱怨，會被接受），`made` 下為生成的追蹤碼（Pokemon HOME
會拒絕它）。每個回覆都會指明它（`home_tracker`）；列表用琥珀色描出這類禮物，Host 會繼承該設定
（`POKELDN_HOME_TRACKER`）。

有兩個 HOME 禮物需要在 `services/pkhex/Program.cs` 中修正：

- Let's Go 的美錄坦（9028）保留 HOME 的身高和體重（`WB7.IsHeightWeightFixed`、`ResetSizes`）。
- 傳說 Z-A 的菊草葉、暖暖豬和小鋸鱷（9031 到 9033）獲得 HOME 的個體值，三項滿值，其餘為 20
  （`WA9.HomeBaseIV`、`SetHomeIVs`）。

## 交換所提供的副本

`gift_event` 會為設定中的訓練家在該遊戲的每個版本上生成一份全新副本，直到有一份合法。按原樣非法的
副本會得到經手人 POKELDN。招式從不重新適配，被拒絕的 PID 會在每個版本上最多重擲八次。Host 會以提供
的形式再次檢查副本；New PID each run 會在卡片會擲出 PID 的地方給出新的 PID 和加密常數。每個禮物在
兩種 HOME 追蹤碼設定下都能通過（`tests/test_pokemon_service.py`）。

主機收到：

- 卡片固定了訓練家和語言時，用卡片自己的訓練家和語言；
- 否則用主機自己的存檔作為訓練家（[為接收玩家而生成](#made-for-the-receiving-player)），若關閉該選項
  則用設定中的訓練家；
- 使用卡片的或設定中的訓練家時，以主機的玩家作為經手人。

## 為接收玩家而生成

`--for-receiver`（應用中預設開啟）會在交換期間為主機自己的存檔生成一份 Your OT 禮物。自帶訓練家的
禮物按生成的樣子發出。只有在帶經手人時才合法的禮物（`handled`：HOME 的新葉喵、呆火鱷、潤水鴨、
菊草葉、暖暖豬、小鋸鱷）隨設定中的訓練家發出，因為接收自己 OT 的存檔會清除經手人，PKHeX 隨後會拒絕它
（[交換會改寫什麼](sv.md#what-a-trade-rewrites)）。應用把每個提供以 `--gift-event KEY` 傳入
（`command._args`）。

啟動時，Host 以探測訓練家 `receiver_gift.PROBE` 向 `gift_event` 詢問該卡片，由此得知卡片是否指定
接收者（`your_ot`），並啟動服務。五個 Host 共享 `pokeldn.receiver_gift`，其中的 `ReceiverGift` 站在
線上夥伴的位置上（[在啟動器中](online.md#in-a-launcher)）。

### 這是誰的存檔

當存檔自己捕獲了這隻寶可夢時，所提供的寶可夢會指明該存檔：初訓家（經手人為 0）、屬於該遊戲的某個
版本、不是蛋。它給出 OT 名稱、16 位 TID 和 SID、性別、語言和版本（`receiver_gift.own_trainer`），在
工作執行緒上讀取（`Service.owner`；朱/紫用 Python，`receiver_gift.sv_owner`）。

| 遊戲 | Your OT 卡片 | 主機的提供 | 版本 |
|---|---|---|---|
| Let's Go | 美錄坦（1501）、美錄梅塔（1502），兩者僅限簡體中文存檔；夢幻（2001） | 交換 r 中的 kind 2 + 2r，一個加密的 232 位元組 PB7 | 42 皮卡丘、43 伊布 |
| 晶燦鑽石/明亮珍珠 | HOME 的草苗龜、小火焰猴、波加曼（9015 到 9017） | 0x13，一個加密的 328 位元組 PB8 | 48 晶燦鑽石、49 明亮珍珠 |
| 傳說 阿爾宙斯 | HOME 的木木梟、火球鼠、水水獺（9018 到 9020） | 選擇器 4，一個加密的 376 位元組 PA8 | 47 |
| 朱/紫 | 9 張卡片，其中包括夢幻（1521）和皮卡丘（1501） | `80 00 02 00` 的 348 位元組主體（[交換訊息攜帶的記錄](sv.md#the-record-a-trade-message-carries)） | 50 朱、51 紫 |
| 傳說 Z-A | 噴火龍（1607）、拉魯拉絲（1601） | 354 位元組的選擇 | 52 |

否則，主機的會話會在任何寶可夢之前指明存檔（`receiver_gift.hear`）：

| 遊戲 | 主機的訊息 | 指明的內容 |
|---|---|---|
| Let's Go | kind 1，存檔的 MyStatus 塊（[Kind 1](lgpe_session.md#the-games-messages-on-the-reliable-protocol)，`pb7.first_trainer`） | id 對、版本、性別、語言、名稱 |
| 晶燦鑽石/明亮珍珠 | 0x24 `TradeTranerData`，在交換開始時（[寶可夢](bdsp_trade.md#the-pokemon)，`room.traner_trainer`） | id 對、版本、語言、名稱 |
| 傳說 阿爾宙斯 | 其 0x81 資料交換記錄，即存檔的 MyStatus 塊（[遊戲的讀取器](pla.md#the-games-reader-and-the-pre-handler-phase)，`data_exchange.read_trainer`） | id 對、版本、性別、語言、名稱 |
| 朱/紫 | 其身份塊的第 1 條記錄，位於其站點索引的 0x81 埠（[記錄](sv.md#the-records)，`sv_host.identity_chunk`，`reference.identity_trainer`） | id 對、版本、性別、語言、名稱 |
| 傳說 Z-A | 1400 身份（[遊戲自身的交換](za.md#the-games-own-exchange)，`reference.identity_trainer`） | id 對、性別、語言、名稱 |

晶燦鑽石/明亮珍珠的會話從不指明性別（[模型](bdsp_protocol.md#the-model)）；所提供的寶可夢則會，作為
初訓家，或作為遊戲寫在每隻收到寶可夢上的經手人
（[主機對收到的寶可夢做了什麼](bdsp_trade.md#what-the-console-does-to-a-received-pokemon)）。會話缺少的
欄位，如果所提供的寶可夢的初訓家（經手人 0）或經手人（經手人 1）與會話的名稱和 id 對匹配，就取自該
寶可夢；否則取自設定。日誌會指明每個這樣的欄位
（`[gift] the console's Pokemon ... cannot name the save`）。傳說 阿爾宙斯和傳說 Z-A 只有一個版本。
後續交換中提供的已捕獲寶可夢優先於會話，副本會重新生成。

`gift_event` 只在存檔所屬的版本上生成卡片（`"only_version"`），並拒絕沒有此類存檔接收過的卡片
（[卡片發放到過的存檔](#saves-a-card-reached)）。HOME 的草苗龜、小火焰猴和波加曼是晶燦鑽石的。

### 交換

交換按線上交換的方式執行（[線上交換](online.md)）：

1. 主機先提供。
2. 如果寶可夢和會話都沒有指明存檔，禮物就隨設定中的訓練家發出；Host 會記錄原因，並按每種原因各彈一次
   彈窗（[彈窗](gui.md#pop-ups)）。
3. `gift_event` 為該存檔生成卡片，然後在工作執行緒上，副本通過 Host 的提供檢查（`pokemon.prepare_offer`，
   在 HOME 追蹤碼設定下）及其載入器。
4. 副本在主機的提供之後上傳，並保持到交換結束。
5. Host 在主機之後確認。

| 遊戲 | 載入器 | 檢查的內容 |
|---|---|---|
| Let's Go | `lgpe_host.boxed` | 一個加密的 232 位元組盒子結構，其校驗和與合理性字成立 |
| 晶燦鑽石/明亮珍珠 | `bdsp.pokemon.build_from` | 加密的 PB8 |
| 傳說 阿爾宙斯 | 交換盒子的 `box_offer` | 其編輯內容，然後 PKHeX 對加密記錄的檢查（`pokemon.validate`） |
| 朱/紫 | `trade.load_offer` | 交換訊息攜帶的 348 位元組主體 |
| 傳說 Z-A | `za_host.gift_offer` | 一個能解密的 354 位元組提供；禮物絕不會以壞蛋的形式傳送 |

PKHeX 無法生成或未通過檢查的副本，會按應用生成的樣子發出；日誌（`[gift] could not be made ...`）和
彈窗會指明存檔與階段（`receiver_gift.maker`）：

| 位置 | 原因文字 |
|---|---|
| 卡片 | 該存檔不可能收到這張卡片：卡片 1502 只在簡體中文下發放過，從未發放給英文存檔 |
| PKHeX | PKHeX 從卡片 ... 生成了非法的 ...：其檢查的發現 |
| 提供檢查 | 副本未通過 Host 的提供檢查：... |
| 載入器 | Host 無法傳送副本：... |

朱/紫、傳說 阿爾宙斯和傳說 Z-A 為每臺主機保留一個 `ReceiverGift`；Let's Go 和晶燦鑽石/明亮珍珠只
承載一臺主機。同一席位上的下一次交換會在前一次完成後立刻進行；最後一個禮物服務於之後的所有交換。

在這五款遊戲的零售版主機上，無論主機提供的是捕獲的還是交換來的寶可夢，禮物都會以存檔自己的訓練家
送達。交換回主機的禮物會以經手人 0 送達，就像存檔自己捕獲的一樣
（[交換會改寫什麼](sv.md#what-a-trade-rewrites)）。

## 其他遊戲

火紅和葉綠通過自己的神秘禮物接收活動寶可夢（[活動寶可夢](frlg_gift.md#event-pokemon)）。劍和盾通過
本地無線接收真實卡片（[官方活動卡片](swsh_gift.md#official-event-cards)）。
