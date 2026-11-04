---
title: 桌面版構建
---
# 桌面版構建

桌面應用是 pokeldn 在 macOS、Windows 和 Linux 上的介面。發行版會打包 PKHeX 以及面向
ESP32、ESP32-S3、ESP32-C3 和 ESP32-C6 的無線韌體；`prod.keys` 由使用者自備。

1. 設定：選擇 `prod.keys`。
2. 裝置頁：選擇 USB 裝置並安裝無線韌體。執行安裝時會選中晶片自帶的映象；來自檔案的映象
   會對照晶片進行校驗。S3、C3 和 C6 通過原生 USB Serial/JTAG 連線；S2 晶片會被拒絕。
3. 選擇一款遊戲和一個工具，準備一隻寶可夢或一個檔案，按主機上的步驟操作，然後按開始。
   收到的寶可夢會進入設定中指定的資料夾，可由「輸出」旁的按鈕開啟。

每個交換工具中要提供的寶可夢都可以留空：按開始時，由 PKHeX 為該遊戲中你的訓練家生成一隻
隨機的合法寶可夢（`command.prepare`），每次執行都會重新生成。

神秘禮物工具共用一個構建器（預設、自行構建、`.pokegift`、劍/盾上的 `.wc8`）。
「儲存禮物檔案」在沒有裝置時也能匯出為 `.pokegift`、`.wc3` 或 `.wc8`
（[神秘禮物檔案](gifts.md#desktop-app)）。

## 首次啟動

macOS 保留系統原生的視窗按鈕；Windows 和 Linux 在應用標題欄中繪製它們，標題欄可拖動視窗，
雙擊則最大化。

| 系統 | 步驟 |
|---|---|
| macOS | 未簽名：開啟一次，關閉警告，然後進入系統設定、隱私與安全性、仍要開啟 |
| Windows | 解壓 zip 並執行 `pokeldn.exe`，`_internal` 放在它旁邊；SmartScreen：更多資訊、仍要執行。沒有 COM 埠：[Windows USB 驅動](#windows-usb-drivers) |
| Linux | GTK 3 與 libsecret；`sudo usermod -aG dialout $USER`（Arch 上是 `uucp`），然後重新登入。見 [Linux 序列埠](#linux-serial-ports) |

沒有可用的 `prod.keys` 時，應用會開啟一個要求提供金鑰的歡迎頁；按 Esc 或「稍後」可關閉它。
在電腦上選好金鑰後，第二步會監視 USB 埠並說明裝置需要什麼：已插入、需要裝置頁的韌體，
或者什麼都不需要。手機應用在各自頁面上完成裝置設定。

當金鑰檔案包含無線模組的金鑰派生所需的每個條目（`ldn.KEYS_NEEDED`）時，它才可用：
`aes_kek_generation_source`、`aes_key_generation_source`、`master_key_00`（LDN 協議 1）和
`master_key_12`（協議 3）。設定、遊戲頁檢查清單和開始都會指出缺少哪些條目。
`ldn.load_keys` 會跳過不是 16 或 32 位元組金鑰的行，例如註釋。

### 設定損壞

`settings.json` 在啟動時讀取（`pokeldn.app.settings.load`）。不是 JSON 的檔案，或某個值型別
錯誤的欄位，會在替換任何內容之前被複制到旁邊的 `settings.json.bad`；只有無法讀取的欄位會
恢復為預設值。隨後應用會顯示哪些欄位被重置，以及舊檔案所在的位置。

## Android 安裝要求

[Android 應用](../examples/android/README.md) 是這套介面在手機上的版本。裝置頁會在插入、
拔出、USB 提示關閉以及從設定返回時重新讀取 USB 狀態。原生 USB 裝置（`303a:1001`）插入
時會開啟應用。

| 檢測到的狀態 | 處理建議 |
|---|---|
| 沒有相容的 USB 裝置 | 檢查資料線；顯示手機的 USB 主機或 OTG 設定（一加有 OTG 開關） |
| USB 許可權缺失或被拒絕 | 解釋 Android 的提示；提供重試 |
| 裝置握手失敗 | 檢查裝置和韌體；顯示錯誤 |
| 裝置有應答 | 顯示裝置和韌體；繼續 |
| 裝置斷開，或從設定返回 | 重新整理並在就緒後繼續 |

經典 ESP32 只能通過 CP210x 橋接工作（`10c4:ea60`、`UsbStream.java`）；CH34x 和 FTDI 會被
指明為不受支援。PKHeX 在手機上執行。儲存和「開啟資料夾」（一個 zip）都使用 Android 的
檔案選擇器。

## iOS 安裝

[iOS 應用](../examples/ios/README.md) 是這套介面在 iPhone 或 iPad 上的版本（AltStore 或
SideStore）。它通過藍牙連線裝置：從桌面裝置頁安裝藍牙無線韌體（ESP32-C6 用
`pokeldn-radio-ble-c6.bin`，經典 ESP32 用 `pokeldn-radio-ble.bin`）；USB 只負責供電。
手機佔用裝置期間，裝置會忽略 USB：在別處使用之前請先關閉 iOS 應用。應用檔案位於
「檔案」、我的 iPhone、pokeldn 下。

## 視窗尺寸

頁面的各個面板按它們實際擁有的寬度佈局，寬度隨視窗變化而測量（`gui/theme.py` 的 `Panes`）。
與他列並排時，選項列不會窄於 440 點。

| 留給面板的寬度 | 佈局 |
|---|---|
| 側面板全寬加 440 | 並排 |
| 側面板 88% 加 440 | 並排，側面板收窄 |
| 最後一個面板 88% 加 440（三面板頁面） | 前兩個放到切換器上，最後一個在它們旁邊 |
| 更少 | 切換器上一次一個面板 |

從並排收窄視窗時，選項列會前移。寬視窗中選項列保持在 720 點並居中，欄位按能放下的數量
排成一行；設定和外掛保持在 760。調整尺寸後開啟的頁面會以寬度允許的佈局開始。

桌面視窗最窄可到 380 點。低於 760 時會即時切換到下方的手機佈局，加寬後切回；桌面視窗
始終在內容上方保留自己的標題欄行。

## 手機

寬度低於 760 點時，頁面位於底部標籤欄，面板在切換器上一次顯示一個（遊戲、選項、會話）。
Android 和 iOS 沒有控制頁或更新頁。

## 遊戲頁

每款遊戲的列表按活動各顯示一行：交換、神秘禮物，然後各類團體戰和聯盟集友圈。該行的執行
方式是選項上方的按鈕，每個選擇佔一行：

| 選擇 | 按鈕 | 顯示於 |
|---|---|---|
| pokeldn | 主持（你的主機加入）、加入（你的主機主持） | 通過裝置或 LAN 的交換、團體戰、極巨大冒險 |
| 連線 | 裝置、無裝置的 Wi-Fi、線上 | 交換；Wi-Fi 僅限劍/盾 |
| 模式 | 任務、遭遇 | 聯盟集友圈 |

每種組合都是一個目錄工具（`pokeldn/app/catalog.py` 中 `Tool` 的 `activity` 和 `variant`），
因此一次執行、它儲存的欄位以及 `python -m pokeldn TOOL` 都保留該工具的鍵。只有一個選項的
選擇不會顯示：線上交換沒有主機選擇。更改一個選擇會保留該行其他選擇上次的取值。外掛工具
也以同樣的方式加入一行（[工具的所在行](plugins.md#a-tools-row-112)）。

## 應用語言

設定中的「應用語言」會列出英語和已安裝的語言包（[語言包](plugins.md#language-packs-15)）；
更改在重啟後生效，缺失的字串會回退到英語。訓練家語言是獨立的。隨附的 Noto Sans CJK SC
字型覆蓋中文、日文和韓文（`gui/assets/fonts/LICENSE`）。它自帶的 ‘ ’ “ ” · … 是全形形式，
因此 Noto Sans Punctuation（同一字型中這六個符號的拉丁寬度形式，
`scripts/gen_punctuation_font.py`）排在它前面；語言包的 `font_family` 仍排在最前。

## 你的訓練家

設定中的「你的訓練家」是應用構建的每隻寶可夢的初訓家：名字、性別、語言，以及按遊戲顯示
方式給出的兩對 ID。記錄中儲存 16 位 TID 和 16 位 SID，它們是一個 32 位 id 的兩半。

| 遊戲 | 顯示的 ID | 裡ID | 儲存的 id |
|---|---|---|---|
| 火紅、葉綠 | TID，0 到 65535 | SID，0 到 65535 | `SID << 16 \| TID` |
| Let's Go、劍/盾、BDSP、傳說 阿爾宙斯、朱/紫、傳說 Z-A | id mod 10^6 | id div 10^6，0 到 4294 | `secret * 10^6 + ID` |

`Settings.ids` 會按遊戲進行換算。每個與主機連線的工具都會把這個訓練家作為其玩家呈現
（`tests/test_gui_catalog.py`）。火紅/葉綠的名字會被截到七個第三世代字元；無法編碼的名字
會變成 `POKELDN`（`Settings.name`）。傳說 Z-A 只有在性別、ID 和名字都匹配時才把收到的
寶可夢視為玩家自己的（[收到的記錄](za.md#what-the-trade-writes-into-a-received-record)）；
傳說 阿爾宙斯的記錄會帶上性別（[記錄](pla.md#the-games-reader-and-the-pre-handler-phase)）。

寶可夢檔案會保留自己的初訓家，除非提供卡片上的「讓我成為它的初訓家」開關開啟：帶
`trainer` 欄位的 PKHeX `check` 會寫入這個訓練家的名字、ID 和性別（`Retrain`）。閃光與否
由 PID 對照這些 ID 決定。從第七世代起，PID 的高半部分會移動，以保持方形、星形或普通閃光；
遭遇固定的 PID（第三世代的性格、特性和性別，劍的野外或團體戰種子）保持不變，卡片會說明
閃光發生了變化。只能搭配自身初訓家才合法的寶可夢（例如固定初訓家的活動寶可夢）會被拒絕，
並給出 PKHeX 的理由。

### 查詢你的訓練家

「查詢我的」會用一次執行從主機讀到的最近一個訓練家，填入某一行的 ID 和裡ID，以及名字、
性別和語言。Switch 遊戲從不顯示裡ID；它由連線攜帶。

| 行 | 什麼標明瞭訓練家 |
|---|---|
| 火紅、葉綠 | 主機的 LinkPlayer，`trainerId` = `SID << 16 \| TID`，在每次交換、神秘禮物和聯盟房間會話中，兩種角色都是 |
| Switch | 主機在一次 Let's Go、BDSP、傳說 阿爾宙斯、朱/紫 或 傳說 Z-A 交換中的會話資料，兩種角色都是（[這是誰的存檔](gift_simulated.md#whose-save-it-is)）；在劍/盾以及任何作品中，主機交換過的、由其存檔捕獲的寶可夢（handler 0，遊戲自己的版本，不是蛋） |

啟動器會為每個訓練家列印一次 `[trainer] {json}`（`pokeldn.console_trainer`）；應用按行、
按遊戲在 `settings.json` 的 `found_trainers` 中保留最新的一個，並在隱私日誌掩碼下記錄它。
Switch 行服務於所有 Switch 作品，因此取最後一次與之交換的那個。什麼都沒找到時，
「查詢我的」會提示進行交換。

### 每款遊戲一個訓練家

「每款遊戲使用不同訓練家」讓每個作品擁有自己的名字、性別、語言、ID 和裡ID，一次編輯一款
遊戲；ID 按該遊戲的顯示方式給出。從未編輯過的遊戲會沿用共享訓練家。以兩個版本發售的遊戲
會分別列出每個版本（火紅和葉綠、劍和盾，其餘同理），因此同一遊戲的兩份存檔各自保留訓練家；
從未編輯過的版本沿用該遊戲的訓練家。兩個版本不同時，該遊戲的工具會在主持和加入旁顯示
「你的遊戲」，執行會使用所選版本的訓練家。`settings.json` 以 `per_game_trainer` 儲存該開關，
以 `game_trainers` 儲存各值（遊戲或版本鍵對映到有差異的欄位），以 `played` 儲存每款遊戲
選中的版本。`Settings.own(game)` 是一款遊戲看到的訓練家；`Settings.ids`、`Settings.name`、
`Settings.trainer` 以及啟動令牌 `{ot}`、`{tid}`、`{sid}`、`{language}`、`{gender}` 都通過
它讀取（`tests/test_gui_catalog.py`）。遊戲上的「查詢我的」會取從該遊戲讀到的最新訓練家。
設定會開啟在最後編輯的那款遊戲上。

`settings.json` 位於資料資料夾中，與應用分開，因此更新會把它留在原處：Windows 上是
`%APPDATA%\pokeldn`，macOS 上是 `~/Library/Application Support/pokeldn`，Linux 上是
`~/.local/share/pokeldn`。手機應用把它儲存在各自的私有儲存中，解除安裝會將其清除。

## Windows USB 驅動

經典 ESP32 的 USB 轉序列埠橋需要驅動，Windows 才會給出 COM 埠（裝置管理器問題程式碼 28）。
使用原生 USB 的 S3、C3 和 C6 不需要。

| 橋接晶片 | USB id | 驅動 |
|---|---|---|
| CP210x | `10c4:ea60` | [CP210x VCP 驅動](https://www.silabs.com/developer-tools/usb-to-uart-bridge-vcp-drivers)：右鍵點選 `silabser.inf`，安裝，重新拔插 |
| CH340 | `1a86:7523` | [CH341SER.EXE](https://www.wch-ic.com/downloads/CH341SER_EXE.html)：安裝，重新拔插 |

沒有 COM 埠時，裝置頁每 2 秒輪詢一次 `Win32_PnPEntity`（`ConfigManagerErrorCode <> 0`），
並指出已知的橋接晶片（`gui/board.py` 的 `bridges_without_driver`）。

## Linux 序列埠

埠需要 `dialout` 組（Arch 上是 `uucp`）；遇到 `EACCES` 時裝置頁會指出該組。

| 服務 | 裝置 | 影響 |
|---|---|---|
| brltty 6.4（Ubuntu 22.04） | CH340 | 搶佔它，沒有 `/dev/ttyUSB*`（[LP 1990357](https://bugs.launchpad.net/bugs/1990357)）；修復：`sudo apt remove brltty` |
| brltty 6.6（Ubuntu 24.04） | CH340 | 僅在 `1a40:0101` 集線器後面搶佔（[LP 1958224](https://bugs.launchpad.net/bugs/1958224)） |
| ModemManager 1.23 | 全部 | 沒有針對 `10c4`、`1a86`、`303a` 的忽略規則 |

沒有埠時，裝置頁會讀取 `/sys/bus/usb/devices`，並指出沒有 tty 的橋接晶片
（`gui/board.py` 的 `bridges_without_port`）。

## 本地儲存

設定中的「儲存」會顯示可回收的空間；「清除本地檔案」在確認後於後臺刪除這些內容，期間會
暫緩會話和刷寫。請先儲存錯誤報告所需的內容。

| 刪除 | 保留 |
|---|---|
| `session/`（抓包、跟蹤、臨時提供）、`logs/`、`pokemon/` 中未使用的生成或匯入的提供、空資料夾 | 不到一分鐘或仍被已儲存的設定和佇列引用的提供；收到的檔案、寶可夢銀行、存檔、金鑰、韌體、設定；符號連結；檢查之後發生更改的檔案 |

## 你的存檔

火紅/葉綠神秘禮物工具的「你的存檔」標籤頁會備份或恢復主機的存檔
（[存檔備份與恢復](frlg_gift.md#save-backup-and-restore)）。存檔位於
`Documents/pokeldn/Saves`（`pokeldn.app.saves`；設定 `POKELDN_DATA` 時位於其中），每份各有一個
`.sav` 和一個 `.json`。

| 操作 | 發生什麼 |
|---|---|
| 從 Switch 備份 | 寫入 `backup-<run>.sav`；被中斷的備份留在 `Saves/.partial`，下次會繼續 |
| 將存檔放到 Switch 上 | 傳入 `--save-restore`；選定存檔之前「開始」被阻止 |
| `+` 或拖入的 `.sav` | 複製進來；16 位元組的模擬器尾部會被丟棄，128 KB 以外的尺寸會被拒絕 |
| 重新命名、匯出、刪除 | 刪除會在本地移除兩個檔案 |
| 檢視和編輯 | PKHeX 讀取訓練家、隊伍和盒子 |

沒有完整的存檔副本，或隊伍中有不合法的寶可夢時，恢復會被阻止，直到開啟「仍然恢復」。
編輯器可更改訓練家名字、性別、金錢、硬幣和隊伍；「保留為新存檔」會通過 PKHeX 寫入，
重新計算扇區校驗和，作為新條目儲存。

## 寶可夢銀行

寶可夢銀行頁儲存每隻收到的寶可夢，並能把其中一隻交換到 HOME 會把它轉移到的任何遊戲。
記錄以各自遊戲的格式連同 `.json` 儲存在 `Documents/pokeldn/Bank`（`pokeldn.app.bank`；
設定 `POKELDN_DATA` 時位於其中）。

| 步驟 | 發生什麼 |
|---|---|
| 一次交換完成 | 每個收到的檔案按位元組入庫一次 |
| 一隻寶可夢入庫 | `.json` 儲存物種、摘要、判定、來源、SHA-256、隨機的 63 位追蹤號、`home_tracker` |
| 目的地 | 助手的 `destinations` 會嘗試全部七款遊戲 |
| 選定一個目的地 | `move` 把它轉換進該工具的佇列，並帶上 `"bank": id` |
| 第 N 次交換完成 | `[done] trade N complete` 把它從庫中移除 |
| 執行失敗 | 它留在庫和佇列中 |

移動使用 PKHeX 的 HOME 轉換（通過 `PKH` 呼叫 `EntityConverter.ConvertToType`）以及目的地的
合法性檢查。應用的訓練家會成為處理者（`IHandlerUpdate`、`PB8.UpdateHandler`）；不合法的移動
會採用 PKHeX 建議的招式組合；PID、加密常量、OT 和 ID 保持不變，執行會省略 `--fresh-pid`。

| 拒絕 | 來源 |
|---|---|
| 無法回到火紅/葉綠 | `EntityConverter.IsConvertibleToFormat` |
| 無法進入 Let's Go | HOME 只從它取出 |
| 蛋；帶道具或秘傳招式的火紅/葉綠寶可夢 | HOME 的火紅/葉綠篩查 |
| 物種或形態不存在 | 目的地的個人表 |
| 傳說 Z-A 記錄出庫 | PKHeX.Core 26.10.18 沒有可用路徑 |

盒子會列出每隻已入庫的寶可夢，並支援按其摘要（按顯示文本和英文：物種、暱稱、性格、特性、
球）及其遊戲名搜尋，支援排序（最新、最舊、圖鑑編號、名稱）和篩選（閃光、等待交換、不合法）；
排序、篩選和圖鑑篩選儲存在 `settings.json`（`bank_view`）中。「選擇」可以挑選多隻寶可夢
（長按也會啟動），用於一次匯出到資料夾、移出交換或移除。選中多隻時，側邊窗格會列出每款遊戲
能接收其中多少隻，並按盒子的順序把它們排入所選交換工具的空位（佇列最多六個）。精靈圖的
裁剪會連同其 SHA-256 儲存在精靈圖快取的 `index.json` 中，因此盒子開啟時無需解碼此前顯示過
的 PNG。

寶可夢的窗格顯示來自助手 `check` 的對戰配置（`battle`）：按 Showdown 順序的個體值、努力值
和能力值，以及供「複製為 Showdown 配置」使用的英文 Showdown 配置。努力值列在 Let's Go 中
是 AV（`IAwakened`），在傳說 阿爾宙斯中按遊戲顯示方式給出 GV（儲存值加上個體值的
`GanbaruExtensions.GetBias`），其他地方為 EV。

圖鑑盒子會列出銀行七款遊戲中任一款持有的每個物種（助手 `species` 的並集），併為每個持有
的物種顯示銀行中的數量、精靈圖和閃游標記；篩選可顯示已持有、缺失或尚無閃光的物種。點選
已持有的物種會開啟盒子並以其為搜尋條件。

編輯只允許遊戲允許的內容：暱稱、向上調等級、招式、攜帶道具。助手 `check` 會拒絕使合法
寶可夢變得不合法的編輯。已排入佇列的寶可夢不可編輯。`tests/test_bank.py` 通過真實助手覆蓋
移動、拒絕、編輯和匯入。

### HOME 追蹤號設定

PKHeX 會對移入另一款遊戲的寶可夢以及經由 HOME 而來的禮物標出缺失的追蹤號
（`TransferTrackerMissing`）。HOME 3.1.0+ 會拒絕非它簽發的追蹤號（錯誤 10015）。
設定、高階、HOME 追蹤號（`Settings.home_tracker`）會隨每個助手請求傳送，並以
`POKELDN_HOME_TRACKER` 傳給執行。

| 設定 | 寫入的追蹤號 | 合法性 | 警告 |
|---|---|---|---|
| `empty`（預設） | 無 | 帶追蹤號合法時被接受 | PKHeX 標出缺失的 HOME 追蹤號 |
| `made` | 隨機 63 位（銀行的） | 不變 | 無法存入 HOME |

在 `empty` 下，助手會基於帶 HOME 更改的追蹤副本判定記錄（`ValidWithTracker`），因為 PKHeX
以追蹤號作為跨 HOME 遊戲進化的門檻，Z-A 也以它重新對齊特性。禮物遵循該設定
（`MendGift`）；生成的追蹤號會帶上 HOME 的更改（`HomeSeen`：朱/紫上以尺寸作為身高，Z-A 中
身高、體重和頭目標記）。劍/盾的神秘禮物卡片從不攜帶追蹤號
（[Pokemon HOME](swsh_gift.md#pokemon-home)）。

### 匯入

加號按鈕或拖入的檔案可匯入 PKSM 銀行、存檔（`SaveUtil.TryGetSaveFile`；3DS 存檔是名為
`main` 的檔案）或任意 PKHeX 格式的一條記錄（`FileUtil.TryGetPKM`）。存檔會先產出隊伍再產出
盒子槽位；PKSM 銀行按順序產出其盒子槽位。

| PKSM 銀行（`.bnk`） | 佈局（PKSM `common/source/BankFile.cpp`） |
|---|---|
| 頭部 | `PKSMBANK`、u32 版本、u32 盒子數量（版本 1 中沒有，從長度讀取） |
| 條目 | u32 世代標籤，然後是用 `0xFF` 填充的解密記錄；版本 1 和 2 中為 264 位元組，版本 3 中為 0x150 |
| 槽位 | 每盒 30 個，最多 500 個盒子 |
| 標籤（PKSM-Core `Generation.hpp`） | 0 第四世代、1 第五世代、2 第六世代、3 第七世代、4 Let's Go、5 第八世代（PK8）、6 第三世代、7 第一世代、8 第二世代；`0xFFFFFFFF` 為空 |

第一或第二世代的條目是帶兩個名字的單隻寶可夢列表：第一世代 59 或 69 位元組，第二世代 63 或
73 位元組，當其最後一個位元組為 `0x50` 或 0 時取日文長度（PKSM `3ds/source/Bank.cpp` 的
`Bank::pkm`）。版本高於 3 會被拒絕。盒子名稱位於銀行旁邊 PKSM 的 `.json` 中，不會被讀取。

| 記錄 | 儲存為 |
|---|---|
| 銀行某款遊戲的格式 | 合法時原樣儲存 |
| 其他任何格式 | 移除攜帶道具、遺忘第三/四世代秘傳招式；若合法，則移動到第一個接收它的遊戲：火紅/葉綠、朱/紫、劍/盾、BDSP、傳說 阿爾宙斯、傳說 Z-A |

不合法記錄、校驗和錯誤、其他遊戲的蛋以及無法抵達的物種會被拒絕。`Bank/.imported` 儲存每條
匯入記錄的 SHA-256，因此重新匯入存檔只會帶入發生變化的記錄。

### 未解決

- HOME 是否接受生成的追蹤號，或對跨遊戲移動的寶可夢接受空追蹤號。
- HOME 的火紅/葉綠規則是否超出蛋、攜帶道具和秘傳招式。
- 哪個欄位攜帶 HOME 的 Switch 火紅/葉綠來源圖示；PKHeX 按寶可夢公園血統轉換 `.pk3`。

## GTS

GTS 頁列出公開的掛單，可按物種篩選，玩家自己的掛單在「你的」下。「僅閃光」只保留提供閃光
的掛單；「我的銀行能應答」只保留可由合法且未排隊入庫寶可夢應答的掛單。掛單排序可按最新
優先、按結束日期、按圖鑑編號或按等級。閃光的寶可夢——無論是提供、求取還是選來存入——都
帶有閃光特效。「存入」會取一隻合法且未排隊的入庫寶可夢，掛單期間儲存在
`Documents/pokeldn/GTS`，並求取最多三個物種（每個可選擇閃光），限定在一個等級範圍內。
應用在執行時隨時應答報價（[GTS](online.md#the-gts)）。

## 裝置與韌體

裝置頁列出每個已插入的裝置，以及其韌體、版本和「已是最新」或「有可用更新」。韌體卡片
（`gui.board.FIRMWARES`）在確認後安裝無線或控制器韌體；「從檔案安裝」接收 pokeldn 的 `.bin`。

| 裝置 | 發現方式 | 版本來源 |
|---|---|---|
| 無線 | 序列埠 | HELLO 應答 |
| 控制器，經典 ESP32 | 序列埠 | 狀態幀 |
| 控制器，ESP32-S3 | USB id `0f0d:0092` | 藍牙狀態 |
| 無 | 序列埠，無應答 | 無 |

隨附的版本是 ESP-IDF 應用描述符中的 `version`（magic `0xABCD5432`，在合併映象中位於
`0x10020`）。執行控制器韌體的 S3 會通過藍牙收到下載命令；應用等待載入器埠 20 秒，並用
`--from-loader` 刷寫。

作為[便攜信標](hardware_esp32.md#portable-beacon)保留的裝置會顯示「已保留禮物」和「移除」。

### 裝置詳情

裝置頁上的「複製裝置詳情」（無論是否選中裝置）會以純文本複製詳情，並儲存為資料資料夾中的
`logs/board-report-DATE.txt`（`gui/board_report.py`）。複製時會開啟選中的埠，因此裝置
可能重啟；執行期間它只列出埠。

| 部分 | 內容 |
|---|---|
| 這臺電腦 | 應用版本、打包版或原始碼版、系統、Python、pyserial 和 esptool 版本 |
| USB 序列埠 | pyserial 列出的每個埠，及其 USB id、序列號、位置和 `hwid` |
| 驅動 | Windows 上無驅動的橋接晶片、Linux 上無 tty 的橋接晶片、USB 上的控制器裝置 |
| 開啟埠 | 開啟時的錯誤及 `errno`/`winerror`，或前 2 秒讀到的位元組 |
| pokeldn 韌體 | HELLO 和 STATUS，或為何無應答 |
| ESP32 載入程式 | esptool 的晶片、描述、特性、晶振、MAC 和 USB-Serial/JTAG 模式 |
| 活動 | 頁面最近 80 行 |

## 控制器

控制頁通過控制器韌體按下 Switch 的按鍵（[控制器裝置](hardware_pad.md)）並播放宏。
ESP32-S3 插入 Switch，通過藍牙 LE 連線；經典 ESP32 留在電腦的 USB 上，從「更改握法/順序」
配對。重新安裝會清除配對。連線斷開時，頁面會持續搜尋，直到裝置應答或選擇「停止查詢」。

| 部分 | 作用 |
|---|---|
| 螢幕控制器 | 按住按鍵；搖桿八個方向，L3/R3 在中心 |
| 鍵盤 | 方向鍵 D-pad，X 對應 A，Z 對應 B，S 對應 X，A 對應 Y，Q 對應 L，W 對應 R，1 對應 ZL，2 對應 ZR，Enter 對應 +，Backspace 對應 -，H 對應 HOME，C 對應 Capture |
| 錄製到宏 | 每次按下都會成為一個步驟，帶按住時長和停頓 |
| 宏編輯器 | 按鍵、搖桿、等待、巢狀重複；「執行一次」和「迴圈」部分 |
| 在裝置上播放 | 裝置按自己的時鐘播放宏 |

宏是 `Documents/pokeldn/Macros` 中的 `.pokemacro` 檔案
（[控制器裝置，宏](hardware_pad.md#macros)）。該頁面通過 `127.0.0.1:47800` 與
`pokeldn.pad.service` 通訊。在 macOS 26 上，以 bundle 主執行檔簽名的程序無法發現藍牙
裝置，因此打包版應用從 `Contents/Helpers/pokeldn-bluetooth` 執行該服務——一個裸簽名的副本，
其 `_internal` 連結到 `../Frameworks`。

## 裝置的螢幕

設定中的「顯示板子的螢幕」會在會話面板頂部繪製裝置的 128x64 畫素螢幕，無論裝置是否接了
螢幕（[螢幕](hardware_esp32.md#the-screen)）。應用會為執行設定 `POKELDN_SCREEN_MIRROR=1`；
隨後執行會列印它傳送的每條 DISPLAY 命令，並每秒列印來自 STATUS 的裝置模式、就座站點、
資料幀和 BOOT 按下次數：

    [screen] reset
    [screen] cmd HEX
    [screen] radio MODE STATIONS RX TX PRESSES

`pokeldn.app.screen_render` 通過韌體 `scene.c` 和 `screen.c` 的 Python 副本重放它們；
`tests/test_screen_render.py` 用編譯後的 C 校驗每一幀。面板按韌體的 50 毫秒幀繪製，隨裝置
變暗，並在空閒十分鐘後關閉。

## 寶可夢精靈圖

影像按需來自 [PokeAPI](https://github.com/PokeAPI/sprites)，快取在 `sprites/`。設定中的
「寶可夢精靈圖」可停用下載並清除快取。缺失的影像顯示佔位圖；缺失的閃光圖會回退到普通圖。

## 團體戰活動

朱/紫 太晶團體戰（主持）的「團體戰活動」卡片會主持來自
[EventsGallery](https://github.com/projectpokemon/EventsGallery) 的團體戰
（[活動團體戰](sv_raid.md#event-raids)），複製到 `EventsGallery/`
（`pokeldn.app.events_gallery`）。「下載」會從 `codeload.github.com` 獲取觸及
`Released/Gen 9/SV/Raid Events` 的最新提交，並保留每個活動最新的表；「檢查更新」會比較該
提交。副本只有在完整後才會替換舊的；Windows 以 `\\?\` 開啟長路徑。

選擇活動會把團體戰卡片限制為其版本、進度和水晶（`raid_event.constrain`），並把「查詢團體戰」
限制為其水晶、首領和獎勵表（[尋找種子](sv_raid.md#finding-a-seed)、
[尺寸標記](sv_raid.md#size-marks)）。只能捕捉一次的首領會提供「讓它再次可捕捉」
（`--raid-catch-normal`）。摺疊卡片會恢復為標準團體戰（「關閉：活動」）；副本中缺失的活動
顯示為「缺失：活動」，執行會拒絕它。

## 主持團體戰的獎勵

「獎勵」卡片提供模板（培養道具、薄荷、對戰道具、樹果、進化道具、太晶碎塊、秘傳調味料、
寶物、球），共用 1 到 999 的數量；編輯會切換到「自定義獎勵」，最多 45 行。「團體戰自身
獎勵」會清除這些覆蓋（[主持](sv_raid.md#hosting)；`gui/views/rewards.py`）。

## 團體戰 NPC 夥伴

「團體戰 NPC 夥伴」卡片會填補主機留空的槽位（[夥伴](sv_raid.md#partners)；
`gui/views/raid_partners.py`）；未做選擇時，主機會像主機遊戲那樣抽取它們。夥伴的進度通過
`--raid-partner-progress` 傳入；每張卡片顯示訓練家、寶可夢（等級為我方寶可夢的五分之四）、
太晶屬性、特性和招式，受青睞的夥伴帶有藍色或銀色條帶
（[受青睞的夥伴](sv_raid.md#favoured-partners)）。每次點選都會按槽位順序傳入
`--raid-partner`；該階段沒有的選擇會被丟棄。

## 聯盟集友圈

朱/紫 的聯盟集友圈工具會在四位連線密碼下加入主機的集友圈
（[聯盟集友圈](sv_union_circle.md)）；該欄位初始為空。

- 任務：解鎖剩餘的 Snacksworth 傳說的寶可夢，或給予 BP（1 到 9,999,999）；一次 Snacksworth
  執行會繪製通關數的[進度](#progress)條。
- 遭遇：生成卡片（`gui/views/encounter.py`）設定物種、閃光、形態、等級、太晶屬性、性格、
  性別、特性、道具、標記、尺寸和個體值；「僅合法遭遇」（預設）會把它們限制在 PKHeX 接受的
  範圍內，並列出有效地點。它會傳入 `--spawn` 和 `--spawn-*`。

`[panel]` 卡片（[狀態卡片](plugins.md#status-cards-18)）會在執行期間顯示在工具選項上方。
`--verbose-circle` 會記錄每條集友圈訊息。

## 神秘禮物 - 模擬

該工具在 Let's Go、BDSP、傳說 阿爾宙斯、朱/紫 和 傳說 Z-A 上的卡片會列出 PKHeX 活動表中的
禮物寶可夢（[模擬神秘禮物](gift_simulated.md#the-gifts)；`gui/views/event_gifts.py`），最新
在前，可搜尋。點選會把一份全新的副本排入佇列，使用設定中的訓練家；一次主持會話最多交換
六個禮物。副本會保留製作它時使用的訓練家。

如果禮物指定的接收者語言沒有任何存檔觸達，該禮物會顯示為不合法圖塊
（[卡片觸達的存檔](gift_simulated.md#saves-a-card-reached)）。「為接收玩家制作」（預設開啟）
會為主機的存檔重製這類禮物
（[為接收玩家制作](gift_simulated.md#made-for-the-receiving-player)）；當沒有符合條件的排隊
禮物時，該開關被停用，也不會傳入 `--for-receiver`。HOME 禮物以琥珀色描邊，並遵循
[HOME 追蹤號設定](#the-home-tracker-setting)
（[交換提供的副本](gift_simulated.md#the-copy-a-trade-offers)）。

## 隱私日誌

設定中的「在日誌中隱藏個人資訊」（預設開啟）會遮蔽顯示和複製的日誌
（`pokeldn/app/redact.py`）：

| 遮蔽內容 | 顯示為 |
|---|---|
| 路徑中的主目錄 | `~` |
| iOS 應用容器 | `<app>` |
| MAC 的裝置部分 | `**:**:**` |
| `ot_name`、`ht_name`、`OT`、`nickname`、`trainer`、`player`、`name` 後的引用值（`POKELDN`、`PKLDN` 除外） | `***` |
| `TID`、`SID`、`trainer_id` 後的值 | `***` |
| 作為完整單詞出現的已見訓練家名字，以及設定中的名字 | `***` |

會話記錄（`captures/`）不會被遮蔽。鏈路本地地址會保留。

## 彈出視窗

執行、子程序和應用可以在任何頁面上開啟彈出視窗（`pokeldn.popup`，外掛 API 1.2）。

| 型別 | 回撥 |
|---|---|
| `acknowledge(title, text)` | `on_ack` |
| `confirm(title, text, agree, disagree)` | `on_agree`、`on_disagree`、`on_dismiss` |
| `choose(title, text, options)`（1.7，2 到 8 個選項） | `on_choice(index)`、`on_dismiss` |

選項：`id`（重新開啟已開啟的 id 會替換它並丟棄其回撥）和 `tone`（`info`、`warning`、
`error`）。開啟會返回 id；回撥在應答執行緒上執行，除非設定了 `set_dispatcher(dispatch)`。
`cancel(id)` 會關閉一個。32 個未應答的彈出視窗會引發 `RuntimeError`。沒有應用時
（`available()` 為 false），彈出視窗是一行 `[pop-up]` 輸出。

`runner.Process(..., popups=app.popups)` 會設定 `POKELDN_POPUPS=1`；子程序在 stdout 寫入
`[popup]` 和 JSON，並從 stdin 讀取 `[popup] {"id", "n", "answer"}`
（`pokeldn.app.runner.child`）；`n` 使對已被替換的彈出視窗的遲到應答不觸發任何動作。
`pokeldn.app.popups.Manager` 儲存它們，`gui.popups.Dialogs` 繪製它們。應用自身的彈出視窗會
報告更新失敗、外掛被停用，以及用設定中的訓練家傳送的接收者禮物
（[交換](gift_simulated.md#the-trade)）。

## 執行狀態

執行等待期間，會話面板會顯示帶時間的 `正在等待主機`；60 秒無主機後，它會詢問主機是否停在
步驟所說的畫面上。加入後會顯示 `主機已連線`。裝置的後端會在無線模組首次主持或掃描時列印
一次 `[link] waiting`，之後在每次站點或鏈路變化時列印 `[link] joined` 和 `[link] left`
（`pokeldn.ldn.show_link`，僅在應用啟動的執行中；無線外掛不會列印這些）。

### 執行失敗時

`pokeldn.app.failure` 會讀取執行輸出的行，指出一個原因以及修復它的頁面：

| 原因 | 匹配內容 | 按鈕 |
|---|---|---|
| 裝置斷開 | `[esp32] The board's USB connection failed`、`the board left USB` | 裝置 |
| 埠被佔用 | `Resource busy`、`Access is denied`、errno 13 | 裝置 |
| 韌體不匹配 | `board speaks protocol N, host speaks M` | 裝置 |
| 裝置無響應 | HELLO 無應答，埠的裝置消失 | 裝置 |
| 缺少金鑰 | `prod.keys has no NAME`（`ldn.MissingKey`） | 設定 |
| 加入失敗 | `the board could not join` | |
| 無主機 | 出現 `[link] waiting` 且從未出現 `[link] joined`，沒有完成交換 | |
| 其他任何情況 | 回溯和非零退出 | 複製日誌 |

第一條匹配的行決定原因。玩家停止的執行，或已完成一次交換的執行，不會報告任何內容。
神秘禮物信標（`Tool.joins` 為 false）永遠不會被歸咎於主機。

### 重試失敗的交換

開啟設定中的「重試失敗的交換」後，以可重試原因（裝置斷開、加入失敗、無主機）結束的交換
執行會在 15 秒後用尚未交換的排隊寶可夢重新開始，最多連續三次；完成過一次交換的執行會重置
計數。「不重試」會取消等待；按開始或選擇另一個工具也會。

## 鍵盤快捷鍵

macOS 上是 Cmd，其他地方是 Ctrl：

| 按鍵 | 操作 |
|---|---|
| 1 到 6 | 遊戲、裝置、寶可夢銀行、GTS、控制、文件 |
| , | 設定 |
| Enter | 會話面板的「開始」，或「停止並開始」（當它可以按下時） |
| . | 停止 |

## 更大字號

設定中的「更大字號」會把所有文字放大 15%（`gui/theme.py`、`text_scale`），在啟動時讀取。
最淺的文字顏色 `#98989D` 在它所處的最亮表面上仍保持 4.8:1 的對比度。

## 進度

執行會列印 `[progress] DONE TOTAL UNIT TITLE`（`pokeldn.progress.show`，API 1.7；`UNIT` 為
`bytes` 或 `items`）來繪製帶數量、30 秒速率和剩餘時間的進度條，每個標題每秒最多四行。
`[save]` 行會繪製同樣的進度條。

## 更新

啟動時應用會查詢 `api.github.com/repos/Decryptu/pokeldn/releases/latest`（5 秒超時）。高於
`pokeldn.__version__` 的 `vX.Y.Z` 標籤會新增一條更新條目，帶「立即更新」或「下載」。

「立即更新」（`pokeldn.app.update`）會把平臺壓縮包和 `SHA256SUMS` 下載到 `update/`，
校驗和不匹配則拒絕，解包（`ditto -x -k`、`tarfile` 的 `data` 過濾器、`zipfile`），然後啟動
`pokeldn --apply-update NEW TARGET PID VERSION`（`gui/updating.py`）。助手會等待舊應用退出
（Windows 上還等待其程序），把它重新命名為 `.<name>.old`，複製新的進來並開啟；任何失敗都會
恢復舊應用。新應用會讀取一次 `update/outcome.json`。校驗和只能檢測損壞，不能驗證釋出版的
身份。

| 情況 | 行為 |
|---|---|
| 預釋出、草稿、異常標籤 | 不提供 |
| 無網路 | 「立即檢查」會提示 GitHub 沒有應答 |
| 設定中關閉更新 | 啟動時不發請求 |
| 沒有壓縮包或 `SHA256SUMS`、原始碼檢出、App Translocation、不可寫的資料夾（macOS、Linux） | 僅下載 |
| Windows，`C:\Program Files` | 「立即更新」需經 UAC（`ShellExecuteExW` `runas`） |
| Windows，另一個盤的根目錄（`D:\pokeldn`） | 「立即更新」無需 UAC：交換隻會在應用旁新增資料夾，而卷根目錄允許使用者這樣做。0.34.0 之前的釋出版會用檔案探測根目錄，在那裡請求 UAC，標準使用者的更新會停在「Windows 未授予 pokeldn 更改 D:\ 的許可權」；從這樣的版本開始，下一個版本需要手動下載一次 |
| Windows，對映或 `subst` 驅動器 | 保留驅動器磁碟機代號；助手在兩種拼寫下都能找到舊應用的程序；在 UAC 之後，助手拿到該磁碟機代號所代表的資料夾，因為提權程序看不到使用者會話對映的磁碟機代號 |
| 會話、刷寫或清理正在執行 | 會先請求結束它 |

`scripts/check_update.py ARCHIVE FOLDER` 會用 127.0.0.1 測試打包應用的更新；
`POKELDN_UPDATE_URL` 會替換端點（`tests/test_app_update.py`）。macOS 在 `/Applications` 中
是否會請求 App 管理許可權，尚未測量。

## 檔案拖放

| 目標 | 接受 |
|---|---|
| 交換的寶可夢 | 寶可夢檔案或 Showdown `.txt`；多出的會填進後續交換 |
| 新增交換 | 每個檔案一次交換 |
| 禮物卡片 | `.pokegift`、`.wc8`、`.wc3` |
| 裝置韌體卡片 | pokeldn 的 `.bin` |
| 任何路徑欄位 | 該檔案，或它所在的資料夾 |

Flet 1.0.2 的客戶端不接受拖放；`scripts/build_client.py` 會用 `gui/flet_drop`
（[desktop_drop](https://pub.dev/packages/desktop_drop)）把 Flet 的客戶端構建到
`gui/client/<platform>`，使用 `python -m flet_cli.cli --version --json` 指定的 Flutter 版本，
macOS 部署目標為 12.0。沒有它時，`gui/main.py` 會執行 Flet 自帶的客戶端，不支援拖放。

## 文件頁

文件頁會顯示應用指南和本站所有可導航的頁面；搜尋匹配小節，要求包含每個詞，標題匹配優先
（`gui/views/docs.py`）。

## 未釋出作品

早於 Switch 發售的作品只有在原始碼檢出中才會出現在遊戲、寶可夢銀行和文件裡
（`pokeldn/app/preview.py`）。`POKELDN_PREVIEW=1` 在任何地方都會顯示它，`0` 則隱藏。它的
文件頁會設定 `nav_exclude` 和 `search_exclude`。

## 從原始碼執行

安裝 Python 3.13 和 .NET 10 SDK：

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r gui/requirements.txt
dotnet build -c Release services/pkhex -warnaserror
python scripts/build_client.py    # optional: file drops; needs Flutter
python gui/main.py
```

Raspberry Pi OS 會把 piwheels 新增為包索引，而 piwheels 的
`flet_web-1.0.2-py3-none-any.whl`（25 KB）缺少 PyPI 的 wheel（27 MB）所攜帶的 `flet_web/web`
客戶端；應用隨後會報 `RuntimeError: Web root path not found`。僅從 PyPI 安裝該包：
`python -m pip install --force-reinstall --no-cache-dir --index-url https://pypi.org/simple flet-web==1.0.2`。
沒有 Linux arm64 釋出版；樹莓派需要從原始碼執行應用。

原始碼檢出中沒有韌體映象。裝置頁上的「下載韌體」會從最新發布版獲取所有映象和 `SHA256SUMS`，
只有全部匹配時才寫入。

## 構建桌面應用

啟用 ESP-IDF 6.1 後，把每個映象構建到 `gui/firmware`，然後打包：

```sh
mkdir -p gui/firmware
OUT="$PWD/gui/firmware"
cd firmware/esp32
for t in esp32:radio esp32s3:radio-s3 esp32c3:radio-c3 esp32c6:radio-c6; do
  chip=${t%%:*}; name=${t#*:}
  idf.py -B build/$chip -D SDKCONFIG="$PWD/build/$chip/sdkconfig" set-target $chip
  idf.py -B build/$chip -D SDKCONFIG="$PWD/build/$chip/sdkconfig" build
  idf.py -B build/$chip merge-bin -o "$OUT/pokeldn-$name.bin"
done
export POKELDN_BLE=1   # Bluetooth images for the iOS app (hardware_esp32.md, Bluetooth)
DEF="sdkconfig.defaults;sdkconfig.defaults.ble"
for t in esp32:ble esp32c6:ble-c6; do
  chip=${t%%:*}; name=${t#*:}
  idf.py -B build/$name -D SDKCONFIG="$PWD/build/$name/sdkconfig" -D SDKCONFIG_DEFAULTS="$DEF" set-target $chip
  idf.py -B build/$name -D SDKCONFIG="$PWD/build/$name/sdkconfig" -D SDKCONFIG_DEFAULTS="$DEF" build
  idf.py -B build/$name merge-bin -o "$OUT/pokeldn-radio-$name.bin"
done
unset POKELDN_BLE
cd ../pad
idf.py -B build -D SDKCONFIG="$PWD/build/sdkconfig" set-target esp32s3
idf.py -B build -D SDKCONFIG="$PWD/build/sdkconfig" build
idf.py -B build merge-bin -o "$OUT/pokeldn-pad-s3.bin"
cd ../..
python scripts/build_client.py
python scripts/build_unicorn.py   # needs CMake
python scripts/pack_app.py
```

凍結應用檢查會驗證每個映象、`flet_drop` 客戶端和 Unicorn 都已打包。版本是
`pokeldn.__version__`，隨 `.github/release-notes.md` 提升，其第一行必須是
`# pokeldn X.Y.Z`（`tests/test_release.py`）。`v*` 標籤會發布九個檔案和 `SHA256SUMS`；只有
帶連字元的標籤是預釋出。

應用是單資料夾的 PyInstaller 構建（`pokeldn.app`；在其他平臺上是一個含 `_internal` 的
`pokeldn` 資料夾）：在 M4 上，遊戲頁在 0.7 秒內開啟，執行在 0.08 秒內啟動。
`scripts/pack_app.py` 在 Flet 的 `--onefile` 之後傳入 `--onedir`，並設定 `LSBackgroundOnly`，
使只有檢視器擁有 Dock 圖示。

| 部分 | 大小 | 精簡方式 |
|---|---|---|
| Flet 檢視器 | 31 MB（macOS 上 xz 後 9.4 MB） | 不含可選擴充套件、單一架構、`--split-debug-info` |
| Unicorn | 3 MB | 僅 ARM 和 ARM64 引擎 |
| PKHeX 助手 | 16 MB | 完全裁剪 |
| Python | 8 MB | 排除 web、影像、測試和語法模組；macOS 上 `strip -x` |

打包陷阱：

- 裁剪會停用反射 JSON；`JsonSerializerIsReflectionEnabledByDefault` 可恢復它。
  `DynamicDependency` 保留 PKHeX.Core 的第三世代活動表。
- macOS 檢視器壓縮包是 xz，名字為 `flet-macos.tar.gz`；`gui/flet_client.py` 會以壓縮檢測
  開啟它，並刪除標記為 `pokeldn-drop` 的過期 `~/.flet/client` 資料夾。
- 絕不要 strip 執行檔或 PKHeX 助手：兩者的 Mach-O 映象之後都帶有一個歸檔。
- `scripts/pack_flet.py` 保留檢視器的授權；沒有
  `com.apple.security.files.user-selected.read-write` 時，選擇 `prod.keys` 會引發
  `ENTITLEMENT_NOT_FOUND`。
- 在 Linux 上，`pokeldn/app/paths.py` 會恢復使用者的 `LD_LIBRARY_PATH`（隨附的 `libstdc++`
  會讓 Fedora 的 EGL 出錯）並設定 `FLET_LINUX_DISTRO`。
- Unicorn 在控制流保護下會以 `0xC0000409` 中止
  （[unicorn#2281](https://github.com/unicorn-engine/unicorn/issues/2281)）；打包器會清除
  `pokeldn.exe` 中的 `GUARD_CF`（`0xC160` 改為 `0x8160`）。絕不要在凍結檢查中啟用
  `faulthandler`。

### 應用圖示

`gui/AppIcon.icon` 是一個 Icon Composer 文稿，是 macOS 和 iOS 圖示的唯一來源。`actool`
（Xcode 26）把它編譯成 `Assets.car` 和 `AppIcon.icns`；`scripts/pack_app.py` 會把兩者放進
`pokeldn.app` 和 Flet 檢視器，並設定 `CFBundleIconName`。macOS 26 會從目錄中繪製分層圖示；
macOS 12 到 15 繪製它的平面版本，這些版本位於 Apple 的圖示網格上（圖塊佔據 128 畫素中的
102 畫素）。Windows 使用 `gui/assets/icon.ico`，Linux 使用 `gui/assets/icon.png`，兩者都是
滿幅：兩個平臺都不會給圖示留邊。
