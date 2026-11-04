---
title: 控制器板
parent: 硬體與設定
nav_order: 5
---

# 控制器板

控制器板是一塊 ESP32-S3，Switch 會把它當作插在 USB-C 口上的有線控制器；或者是一塊經典 ESP32，通過經典藍牙配對成 Pro 控制器。主機通過它按下 Switch 主機的按鍵，並載入宏，由板子按自己的時鐘播放。韌體為 `firmware/pad`，主機側為 `pokeldn.pad`，應用頁面見[控制器](gui.md#the-controller)，命令列為 `tools/switch/pad.py`。

## 適用板子

| 晶片 | 控制器 | 原因 |
|---|---|---|
| ESP32-S3 | 有線，走 USB | 它的 USB-OTG 模組可以充當任意 USB 裝置 |
| 經典 ESP32 | 無線 Pro 控制器，經典藍牙；主機經其 USB 轉序列埠連線 | 自身沒有 USB 裝置功能；它有經典藍牙，也就是 Pro 控制器的傳輸方式 |
| ESP32-C3、ESP32-C6 | 無 | USB Serial/JTAG 是固定功能，且它們的藍牙只有 LE |

## USB 一側

板子會列舉成 HORI Pokken 控制器，`0f0d:0092`，一個 HID 介面，帶一箇中斷 IN 端點和一箇中斷 OUT 端點。Switch 接受這個 ID 作為普通 HID 手柄，不需要 Pro 控制器握手；韌體 23.0.1 的零售 Switch Lite 從 HOME 選單直接識別，無需改動任何設定。

輸入報告為 8 位元組，只要主機準備好接收，就每毫秒傳送一次：

| 偏移 | 大小 | 欄位 |
|---|---|---|
| 0 | 2 | 按鍵，小端 |
| 2 | 1 | 十字鍵：0 為上，順時針到 7 為左上；8 為居中 |
| 3 | 4 | LX、LY、RX、RY；128 為居中，0 為左或上 |
| 7 | 1 | 廠商位元組；韌體把它的藍牙狀態放在這裡 |

| 位 | 按鍵 | 位 | 按鍵 |
|---|---|---|---|
| 0x0001 | Y | 0x0100 | 減號 |
| 0x0002 | B | 0x0200 | 加號 |
| 0x0004 | A | 0x0400 | 左搖桿按下 |
| 0x0008 | X | 0x0800 | 右搖桿按下 |
| 0x0010 | L | 0x1000 | HOME |
| 0x0020 | R | 0x2000 | 截圖 |
| 0x0040 | ZL | | |
| 0x0080 | ZR | | |

廠商位元組：1 已同步，2 廣播中，3 已連線；該步驟失敗時為 `0x80 | step`。

## 接線

用一根 USB-C 轉 USB-C 線把板子接到主機上。主機既是電源也是 USB 主機；板子從它取電。主機配置好裝置後，XIAO ESP32S3 的 LED（GPIO21）會亮。

把 Switch Lite 接在 Mac 的 USB-A 口上並開啟「通過 USB 連線複製到電腦」時，它會列舉為 `057e:201d`：一個 MTP 介面、一個只讀的「相簿」儲存、十個只讀操作（`0x1001`-`0x100a`）。

## 藍牙一側

板子以 `POKELDN-PAD` 廣播，帶一個服務 `7a1e0001-5d2c-4c3e-9f4b-504f4b454c44`：

| 特徵 | 訪問 | 內容 |
|---|---|---|
| `...0002` | 寫、無響應寫 | 8 位元組輸入報告，原樣傳送；宏播放期間被忽略 |
| `...0003` | 讀 | 狀態，見下 |
| `...0004` | 寫 | 命令，見下 |

狀態欄位，小端：mounted u8、report writes u32、playing u8、loops done u32、entry index u16、entry count u16、文本形式的韌體版本，然後是 NUL、復位原因 u8（`esp_reset_reason`）、上一次啟動達到的階段 u8，以及上電以來的啟動次數 u16。1.0.0 之前的韌體只發送前五個位元組。

| 命令 | 內容 | 效果 |
|---|---|---|
| `0x10` load | count u16、loop start u16、loops u32 | 停止當前宏並設定程式大小；loops 為 0 時一直播放到被停止 |
| `0x11` data | first entry u16，然後各條目 | 每個條目是一份報告加一個以毫秒計的保持時間 u16，共 10 位元組 |
| `0x12` play | | 開始播放程式 |
| `0x13` stop | | 停止並鬆開所有按鍵 |
| `0xB0` download | | 把晶片重啟進 ROM 載入器 |

程式可容納 8192 個條目。迴圈起點之前的條目播放一次，其餘重複。播放器以 1 kHz 節拍用 `vTaskDelayUntil` 等待，因此保持時間累加不會漂移。

陷阱：在 macOS 上通過 bleak 做無響應寫時，CoreBluetooth 佇列一滿就會丟，而 bleak 從不讀 `canSendWriteWithoutResponse`（連續 300 份報告中只有 67 份到達）。`pokeldn.pad.link` 在每次寫報告前等待該標誌（每份報告 2.4 ms，無一丟失）；在該標誌不存在、或持續一秒為 false 的地方，改用有響應寫，每份 60 ms。

斷開連線會把報告恢復到中立狀態，因此主機消失時不會有按鍵被按住；正在播放的宏則繼續。

## 序列埠一側

經典 ESP32 一直留在電腦的 USB 上：921600 波特率的 UART0 雙向承載幀（`firmware/pad/main/uart_link.c`、`pokeldn/pad/serial_link.py`），控制台輸出關閉。控制台關閉後，沒有任何東西把 UART0 路由到 GPIO1 和 GPIO3，所以韌體自己設定引腳；沒有這一步，板子什麼也不應答。

    A5 5A | length u16 (type and payload) | type u8 | payload | sum of type and payload mod 256

| 型別 | 方向 | 內容 |
|---|---|---|
| `0x01` | 發給板子 | 8 位元組報告；由 `0x81` 應答 |
| `0x02` | 發給板子 | 無；由 `0x82` 帶狀態記錄應答 |
| `0x03` | 發給板子 | 命令，與控制特徵上的相同；由 `0x81` 應答 |
| `0x81` | 發給主機 | 結果 i8：0，-1 長度錯誤，-2 被拒絕 |
| `0x82` | 發給主機 | 狀態記錄；mounted 表示 Switch 已設定玩家燈 |

主機以 DTR 和 RTS 為低電平開啟埠。在 macOS 上，DevKit 的 CP2102 仍會在埠開啟時重啟板子，啟動期間發出的請求會丟失；主機會把狀態請求重複最多 3 秒。服務會先嚐試每個不是 S3 原生 USB 的 USB 序列埠，然後才掃描藍牙 LE。請用一個程序佔住埠：每次重新開啟都會重啟板子並斷開它的藍牙鏈路。

## 經典藍牙一側

`firmware/pad/main/bt_esp32.c` 註冊一個 Bluedroid HID 裝置：170 位元組的 Pro 控制器報告描述符，服務名「Wireless Gamepad」，廠商「Nintendo」，子類 0x08，裝置類 0x002508，名稱「Pro Controller」，SSP 無輸入無輸出，關閉 modem sleep。它按 ID 應答 0x01 子命令：0x02 裝置資訊（韌體 4.00、型別 0x03、自身藍牙地址）、0x10 SPI 讀取、0x03 報告模式、0x04 觸發時間、0x21 MCU 配置，其餘回一個普通 ACK；0x30（玩家燈）表示控制器已被取用。任何 0x30 之前都會先發出一條回覆。

從鏈路開啟的那一刻起，按鍵或搖桿一變化就立刻發出 0x30 報告，否則每 100 ms 發一次；板子不發時 Switch 不會主動開始握手。板子在鏈路開啟後等 1 秒，一次變化後等 250 ms 轉入 sniff 模式，在被以擁塞（原因 8）拒絕傳送後等 45 ms：這些是 friendmaker 的 Switch Lite 取值（`classic_bt_controller_transport.cpp`、`SWITCH_LITE`）。陷阱：每 15 ms 發一次 0x30 會擁塞鏈路，Switch 會在玩家燈亮起後 20 秒內斷開（HCI 0x13）。

Switch 的握手順序：0x02、0x08、0x10 讀 0x6000 與 0x6050、0x03（0x30）、0x04、0x10 讀 0x6080、0x6098、0x8010、0x603D、0x6020、0x40、0x30（0）、0x48、0x21、0x30（玩家 1）。

已配對的板子會在啟動時自動連回它的 Switch。刷寫合併映象會覆蓋 NVS 分割槽，連帶清掉配對資訊：請從「更改握法/順序」重新配對。

`pro_report.c` 把共享報告對映到 Pro 控制器的位元組佈局上（dekuNukem 的 `bluetooth_hid_notes.md`）：搖桿靜止為 0x800，兩端各為 0x700，與它在 0x603D 返回的出廠校準一致；序列號和使用者校準用空白 flash（0xFF）。`tests/test_pad_pro.py` 在主機上編譯它，並檢查每個按鍵位與校準。

## 宏

宏是一個副檔名為 `.pokemacro` 的 JSON 檔案（`pokeldn.pad.macro`）：

```json
{
  "format": "pokeldn-macro", "version": 1,
  "name": "Soft reset", "description": "", "author": "", "game": "",
  "press_ms": 100, "gap_ms": 150,
  "setup": [{"press": "HOME"}, {"wait": 1000}],
  "loop": [
    {"press": ["A", "B"], "ms": 500, "after": 2000, "note": "skip the intro"},
    {"repeat": 3, "steps": [{"press": "A"}]},
    {"press": [], "left": [0, 1], "ms": 300},
    {"wait": 5000}
  ],
  "loops": 0
}
```

| 欄位 | 含義 |
|---|---|
| `press_ms`, `gap_ms` | 步驟未另行指定時，它按住輸入多久，以及之後的停頓 |
| `setup` | 只執行一次的步驟 |
| `loop` | 重複 `loops` 次的步驟；為 0 時一直重複到被停止 |
| 按下步驟 | `press`：一個按鍵名，或一組同時按住的按鍵（`A B X Y L R ZL ZR PLUS MINUS LSTICK RSTICK HOME CAPTURE UP DOWN LEFT RIGHT UPLEFT UPRIGHT DOWNLEFT DOWNRIGHT`）；`left` 與 `right`：搖桿 `[x, y]`，取值 -1 到 1，向上為正；`ms` 保持時間；`after` 停頓；`note` 備註 |
| 等待步驟 | `wait`：毫秒數，期間鬆開所有按鍵 |
| 重複步驟 | `repeat`：對 `steps` 重複 1 到 10000 次，最多巢狀 8 層 |

編譯器會展開重複、合併相鄰且報告相同的條目，並把超過 65535 ms 的保持時間拆開。展開後超過 8192 個條目的宏會被拒絕。兩次相同按壓之間的 `after: 0` 會把它們併成一次按住。`version` 比讀取器更新的檔案會被拒絕。

## 主機側

`pokeldn.pad.service` 持有藍牙鏈路，在 `127.0.0.1:47800` 上每行接收一個 JSON 請求：`status`、`connect`、`send`、`tap`、`play`、`stop`、`download`、`scan`、`disconnect`。應用把它作為自己的子程序啟動；沒有服務在跑時，`tools/switch/pad.py` 會在獨立程序中啟動它。

在 macOS 上，鏈路開啟時板子斷電（從 Switch 上拔下），CoreBluetooth 可能讓一次讀或寫無聲地一直掛著。服務會在時限內應答每個請求（`status` 5 秒，`play` 120 秒，`scan` 20 秒，其餘 40 秒，連線請求也算在內）。超過時限，服務會關閉鏈路讓板子重新廣播，並回復一個錯誤。應用的客戶端在 150 秒後停止等待。

    ./.venv/bin/python tools/switch/pad.py A
    ./.venv/bin/python tools/switch/pad.py HOME wait:1 'RIGHT*3' A
    ./.venv/bin/python tools/switch/pad.py hold:B:2 stick:L:-1:0:0.5
    ./.venv/bin/python tools/switch/pad.py --play soft_reset.pokemacro
    ./.venv/bin/python tools/switch/pad.py --stop --status

在 macOS 上，如果程序的負責應用沒有宣告 `NSBluetoothAlwaysUsageDescription`，它一開啟藍牙就會被中止；這種情況會出現在嵌在另一個應用裡的終端下。`pad.py --make-app PATH` 會寫出一個執行該服務的小應用；`open` 它一次並允許藍牙，此後 `pad.py` 呼叫和原始碼檢出裡的應用都會用它。

## 再次刷寫

控制器板佔著 USB 口，因此 esptool 無法把它復位進載入器。download 命令、裝置頁的安裝操作和 `pad.py --download` 都通過藍牙完成；插板子時按住 BOOT 則不需要韌體就能進入。

| 陷阱 | 韌體或主機的做法 |
|---|---|
| `RTC_CNTL_USB_CONF` 會跨復位保留；若留在 USB-OTG，載入器為 `303a:0009`，esptool 只有一半機率能連上 | 停止 NimBLE 與 TinyUSB，把 PHY 交還 USB Serial/JTAG 並設定 `RTC_CNTL_FORCE_DOWNLOAD_BOOT`；此時載入器為 `303a:1001` |
| 藍牙與 USB 都開著時 `esp_restart()` 可能掛死 | 不以這種方式呼叫 |
| 在 macOS 上新載入器埠第一次開啟讀不到任何東西，且 esptool 會一直佔著埠 | `gui/board.py` 等 8 秒，然後不復位直接連線 |
| 從強制載入器刷寫之後，USB 復位仍停在載入器裡 | `--after watchdog-reset` |

`python -m gui.board --kind pad|radio` 可以互相刷寫兩種韌體；`--from-loader` 用於刷寫 download 命令已經放進載入器的板子。

陷阱：在 FreeRTOS 預設的 100 Hz 下，USB 迴圈的延遲是零個 tick，會餓死 NimBLE；韌體按 1000 Hz 構建。

## 構建

    . scratchpad/esp/env.sh
    cd firmware/pad && idf.py -B BUILD_DIR -D SDKCONFIG=SDKCONFIG_PATH build

TinyUSB 來自元件管理器（`espressif/esp_tinyusb` 2.4.0）。釋出構建會在無線韌體映象旁生成 `pokeldn-pad-s3.bin`。

## 未解決

- Switch 2 是與經典 ESP32 韌體配對，還是接受 HORI 的 ID，尚無實測；目前只測過 Switch Lite。
