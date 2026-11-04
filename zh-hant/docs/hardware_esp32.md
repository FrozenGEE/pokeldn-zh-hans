---
title: ESP32 無線模組
parent: 硬體與設定
nav_order: 1
---

# ESP32 無線模組

接在 USB 序列埠上的 ESP32 板子就是無線模組。它執行 `firmware/esp32/`，承載 LDN 的廠商動作幀與乙太網路幀；廣播加密、LDN 認證、IP 與 Pia 都留在主機上，[便攜信標](#portable-beacon) 除外。`pokeldn.ldn.esp32_wlan` 為 LDN 庫提供一個由板子支撐的工廠，因此 `ldn.scan`、`ldn.connect` 與 `ldn.create_network` 無需改動即可執行，主機也不需要 Wi-Fi 驅動。

## 支援的板子

| 晶片 | 主機連線 | 合併映象 |
|---|---|---|
| 經典 ESP32（ESP32-D0WD、WROOM-32E） | UART0，經 USB 序列埠橋 | `pokeldn-radio.bin` |
| ESP32-S3 | 原生 USB Serial/JTAG | `pokeldn-radio-s3.bin` |
| ESP32-C3 | 原生 USB Serial/JTAG | `pokeldn-radio-c3.bin` |
| ESP32-C6 | 原生 USB Serial/JTAG | `pokeldn-radio-c6.bin` |
| 經典 ESP32、ESP32-C6 | 藍牙 LE（iOS 應用），以及上面的 USB | `pokeldn-radio-ble.bin`、`pokeldn-radio-ble-c6.bin` |

所有目標都使用 2.4 GHz；不支援 ESP32-S2。S3、C3 或 C6 若同時有獨立的 UART 口與原生 USB 口，必須使用原生口（S3 為 GPIO19/20，C3 為 GPIO18/19）；走 UART 口時韌體永不應答。當某個 USB 序列埠橋上沒有韌體應答時，桌面應用會從 ROM 引導載入器讀取晶片（esptool `detect_chip`），並指出 S3、C3 或 C6 插錯了口。`303a:1001` 由多款晶片共用；刷寫時用 esptool 檢測晶片。

| 板子 | 天線 | BOOT | 使用者 LED | CPU、任務核心 | 空閒可用堆 | 原生 USB 上的 BENCH，macOS |
|---|---|---|---|---|---|---|
| XIAO ESP32C3 rev 0.4 | 隨附外接天線，必須裝上 | GPIO9 | 無（只有充電指示） | 160 MHz，核心 0 | 152656 | 880.1 KB/s |
| XIAO ESP32C6 rev 0.2（C6FH4，4 MB） | 陶瓷天線，由韌體選擇 | GPIO9 | 黃色，GPIO15，低電平點亮 | 160 MHz，核心 0 | 255196 | 824.6 KB/s |
| XIAO ESP32S3 rev 0.2（8 MB flash、8 MB PSRAM） | 隨附外接天線，必須裝上 | GPIO0 | 黃色，GPIO21，低電平點亮 | 240 MHz，核心 1 | 212416 | 883 KB/s |

BENCH 不丟資料；主機的波特率設定不改變 USB 速度。更大的 S3 板子（N8R2、N16R8）帶板載天線。板子指南：[XIAO ESP32C3](https://wiki.seeedstudio.com/XIAO_ESP32C3_Getting_Started/)、[XIAO ESP32C6](https://wiki.seeedstudio.com/xiao_esp32c6_getting_started/)。

XIAO ESP32C6 在 GPIO3 為低時給射頻開關供電；GPIO14 為低則選擇陶瓷天線。C6 韌體在 Wi-Fi 啟動前把兩者都拉低；在 ESP32-C6-DevKitC-1 上這兩個引腳只引到排針，因此一個映象通用於所有 C6 板子。C6 的 station 被限制在 11b/g/n。它的接收頭部沒有 `sig_mode`、`mcs` 或 `cwb`：韌體從 `cur_bb_format` 推導 `sig_mode`，從 `he_siga1` 推導 HT MCS，其速率位元組對 OFDM 幀來說是 L-SIG 速率碼。

各板子完成的交換見[按板子統計的交換](#trades-by-board)。

### 復位後的 USB 鏈路（C6、S3）

開啟埠會復位 C6 或 S3。在 ESP-IDF 預設的 `CONFIG_ESP_SYSTEM_BBPLL_RECALIB=y` 下，啟動過程會停掉為 USB Serial/JTAG 提供時鐘的 BBPLL（`recalib_bbpll()`，`esp_system/port/soc/esp32c6/clk.c`），鏈路可能一直錯亂到板子被拔下（SOF 幀號凍結，`USB_SERIAL_JTAG_INT_RAW` 為 `0000b5b2`，健康時為 `0000b50a`）。C6 與 S3 的構建把它設為 `n`（v5.2 及以上的引導載入器允許，每個合併映象都自帶引導載入器）：900 次 C6 開啟和 300 次 S3 開啟全部有應答。C3 沒有這個選項，也沒有此故障。

C6 與 S3 的構建帶一個 USB 看門狗（`usbwatch.c`）：SOF 幀號停頓 2 秒就重啟晶片，下一次 HELLO 會以 LOG 行帶上 USB 與時鐘暫存器。它在收到第一個 SOF 幀、或從線纜讀到第一個主機位元組時武裝，並且在藍牙主機已連線時從不重啟：接在充電器上的板子收不到 SOF 幀，而在 1.7.0 之前的韌體裡，藍牙主機的位元組會武裝它，所以接在充電器上的 C6 在 iPhone 應用下每 2 到 3 秒重啟一次。以 `POKELDN_USB_BEACON=1` 構建時，兩個映象還會把那些暫存器每秒一次作為廠商動作幀廣播到 `03:55:53:42:57:00`（佈局見 `usbwatch.c`），USB 死掉期間 `esp32_sniff.py --mac 03:55:53:42:57:00` 會一直收著。

## 角色

| 角色 | 板子做什麼 |
|---|---|
| 空閒 | 在一個通道上混雜接收；每個帶任天堂 LDN 字首 `7f 00 22 aa` 的動作幀都送給主機 |
| station | 用主機派生出的 CCMP 金鑰按 BSSID 加入主機端的網路 |
| 接入點 | 在主機 BSSID 上的隱藏 SSID WPA2 網路，金鑰方式相同 |

主機端的網路沒有四次握手：兩端從廣播裡的 server random 派生 CCMP 金鑰。韌體替換 ESP-IDF 私有 `struct wpa_funcs` 表中的四個條目（`esp_wifi_driver.h`）。該佈局是 v6.1 blob 的 ABI；韌體拒絕針對其他版本構建。

| 條目 | 替換為 |
|---|---|
| `wpa_sta_connect` | 在原有回撥外面裝上 Switch station 的 RSN 元素（CCMP、PSK、capabilities `0x000c`） |
| `wpa_sta_rx_eapol` | 丟棄 EAPOL；看到關聯響應後用 `esp_wifi_set_sta_key_internal` 裝入金鑰，再由 `esp_wifi_auth_done_internal` 開啟埠 |
| `wpa_ap_join` | 新增 station 併發送關聯響應（`esp_send_assoc_resp`），不發 EAPOL-Key 訊息 1（`AP_START` 標誌位 0 保留原有加入流程）；主迴圈裝入成對金鑰（`esp_wifi_set_ap_key_internal(CCMP, mac, 0, key)`）並開啟埠（`esp_wifi_wpa_ptk_init_done_internal(mac)`），即 hostapd 的 `PTKINITDONE` 順序（`wpa_auth.c:2290-2332`）；組金鑰在 `WIFI_EVENT_AP_START` 時以索引 1 裝入 |

陷阱：絕不要等 `WIFI_EVENT_AP_STACONNECTED` 來裝金鑰。只有 `esp_wifi_wpa_ptk_init_done_internal` 會發出它，因此沒有四次握手時它永不出現，主機端的第一個加密幀會被丟棄。

## 接入點的幀

softAP 的信標、探測響應與關聯響應在閉源的 `libnet80211.a` 中構建（v6.1 `ieee80211_output.o` 的偏移），與 `vendor/LDN` 的接入點所發的幀對比：

| 欄位 | Switch 的形式 | ESP32 softAP | 可設定 |
|---|---|---|---|
| 隱藏 SSID 元素 | 32 個零位元組 | 長度 0（`ieee80211_beacon_construct` 0xc4） | 否 |
| 支援速率 | `82 84 8B 96 0C 12 18 24` | `8B 96 82 84 0C 18 30 60` | 否；同樣是十二個速率與基本位，9 和 18 在擴充套件速率裡 |
| 擴充套件速率 | `30 48 60 6C` | `6C 12 24 48` | 否 |
| 能力位，信標 | `0x0511` | `0x0431`（短前導常量，`ieee80211_getcapinfo` 0x7b） | 否 |
| HT 元素 | 無 | 11b/g/n 下存在 | 已移除：韌體設為 11b/g |
| RSN 能力位 | `0x000c` | hostapd 自己的 | 已設定：`wpa_ap_get_wpa_ie` 返回 Switch 的元素 |
| WMM | 無 | 11g 下存在 | 只有僅 11b 才能去掉 |

隱藏的 softAP 只應答定向探測。不帶配置 SSID 的關聯請求會被丟棄（0x9c6）。`esp_wifi_80211_tx` 拒絕傳送關聯響應（`ieee80211_raw_frame_sanity_check` 0xf9），而 blob 自己的信標無法停止。

## 序列埠協議

一幀是 `COBS(type | payload | crc32-le(type | payload))` 後接 `0x00`；CRC 為 CRC-32/ISO-HDLC（`zlib.crc32`）。經典 ESP32 以 115200 波特率啟動；`BAUD` 會切換兩端，板子保持該速率直到復位。在 S3 上，`BAUD` 會被確認，但不改變 USB 傳輸速率。`0x00` 之前的任何內容，包括 ROM 的啟動文本，都通不過校驗並被丟棄。

| 型別 | 方向 | 載荷 |
|---|---|---|
| `0x01` HELLO | 主機 | 無；先由 CREDIT 0 應答，然後 INFO。主機先發一個 `0x00` 結束任何殘缺幀 |
| `0x02` BAUD | 主機 | u32 波特率；以舊速率回 RESULT，UART 排空後切換（最多 3 秒）；`open_serial` 以新速率重試第一個 HELLO |
| `0x03` CHANNEL | 主機 | u8 通道；僅空閒時 |
| `0x04` STA_JOIN | 主機 | u8 通道、6 BSSID、32 SSID（LDN SSID 的十六進位制文本）、16 金鑰、6 station MAC（全零為隨機）；可選：u8 固定資料速率（AP_START 位 3..5 的速率表）、u8 以 0.25 dBm 計的最大發射功率（`esp_wifi_set_max_tx_power`，8 到 84，驅動把它封頂在 61）、u8 標誌：1 每幀前發 RTS，2 重試前不發 RTS（`esp_wifi_internal_set_rts`） |
| `0x05` STOP | 主機 | 無；回到空閒，清除金鑰 |
| `0x06` AP_START | 主機 | u8 通道、6 BSSID、32 SSID、16 金鑰、u8 最大 station 數、u8 標誌：1 走原有關聯與四次握手，2 對該 station 不用 QoS，4 不復制每個 station 資料幀的 40 位元組，位 3..5 為固定資料速率，`0x40` 每 1000 TU 一個信標，`0x80` 不混雜接收；可選的第二個標誌位元組：1 關閉驅動的噪聲底檢查，2 其間隔為 250，4 在每份 40 位元組副本頭部帶上接收時間，8 重試上限 7 和 4，`0x10` 除本網路 station 的正常資料幀外每幀都發 RX_CENSUS；之後是可選的以 0.25 dBm 計的最大發射功率 |
| `0x07` AP_KICK | 主機 | 6 MAC、u16 原因；解除認證 |
| `0x08` ETH_TX | 主機 | 一個乙太網路幀，由驅動用該 station 的金鑰或組金鑰加密。驅動佇列滿時每 1 ms 重試一次，最多 100 ms；發往已離開 station 的幀以 `0x3015` 失敗。station 的乙太網路源地址必須是 LINK 中的 MAC，否則該幀永遠不會被確認 |
| `0x09` RAW_TX | 主機 | 一個不帶 FCS 的 802.11 幀（`esp_wifi_80211_tx`）；用於廣播 |
| `0x0A` SNIFF | 主機 | u8 通道、6 MAC；發往或來自它的每個管理與資料幀，以及該通道上的每個動作幀（LDN 廣播會給主機端要遷去的網路提供金鑰）都完整地以 RX_SNIFF 送出；MAC 為 ff:ff:ff:ff:ff:ff 時，該通道上的每一幀都以 RX_CENSUS 送出 |
| `0x0B` STATUS | 主機 | 無；由 STATUS 應答 |
| `0x0C` BENCH | 主機 | u32 位元組數、u16 訊息大小（8 到 1600）；先 RESULT，然後以 UART 能承受的最快速度發 BENCH 訊息 |
| `0x0D` LED | 主機 | u8 圖案、u8 峰值亮度、u16 週期毫秒（0 為圖案預設值）、u16 持續時間毫秒（0 為到下一次 LED 為止）；RESULT |
| `0x0E` DISPLAY | 主機 | 一條螢幕命令（[螢幕](#the-screen)）；沒有螢幕時 RESULT 為 `0x105` |
| `0x0F` ALIVE | 主機 | 無，不回覆；武裝[主機看門狗](#the-host-watchdog)；只發給 1.4.0 及以後的韌體 |
| `0x10` BEACON | 主機 | u8 操作：0 WRITE，把 u32 偏移與位元組寫入暫存緩衝區；1 COMMIT，u16 長度（校驗並儲存暫存的映象）；2 ERASE；3 START；4 QUERY（由 BEACON 應答）；其餘操作回 RESULT。韌體 1.8.0 及以後（[便攜信標](#portable-beacon)） |
| `0x81` INFO | 板子 | u8 協議版本（1）、6 station MAC、6 AP MAC、u8 晶片版本、文本 |
| `0x82` RESULT | 板子 | u8 命令、i32 `esp_err_t` |
| `0x83` LOG | 板子 | 文本 |
| `0x84` RX_MGMT | 板子 | u8 通道、i8 RSSI、一個不帶 FCS 的幀：LDN 動作幀；主持期間還包括髮往板子 BSSID 的管理幀、發往它的資料幀的前 40 位元組，以及某個 station 完整的無 DS 位廣播 |
| `0x85` RX_ETH | 板子 | 驅動解密後的一個乙太網路幀 |
| `0x86` LINK | 板子 | u8 是否建立、u16 原因、6 MAC；原因 `0xFFFF` 為 15 秒內未關聯，`0xFFFE` 為金鑰被拒 |
| `0x87` STA_JOINED | 板子 | 6 MAC、u8 AID、i8 金鑰安裝結果、u8 埠是否開啟 |
| `0x88` STA_LEFT | 板子 | 6 MAC、u16 原因 |
| `0x89` STATUS | 板子 | 文本形式的計數器（見下）；主持期間每 2 秒主動傳送一次，寫跟蹤記錄的主機則每 5 秒輪詢一次 |
| `0x8A` BENCH | 板子 | u32 序號與載荷位元組；最後一個攜帶序號 `0xFFFFFFFF` 以及板子花掉的微秒數 u32 |
| `0x8B` CREDIT | 板子 | u32 自上次 HELLO 以來讀取並處理的主機位元組數，從其分隔符之後的位元組算起；在 HELLO 時、每 1024 位元組、線路轉為空閒時，以及空閒期間每 100 ms 傳送，優先於任何排隊的訊息 |
| `0x8C` RX_SNIFF | 板子 | u8 通道、i8 RSSI、u8 `sig_mode`（0 為 legacy，1 為 HT）、u8 legacy 速率碼（`wifi_phy_rate_t`）、u8 HT MCS（位 7 表示 40 MHz）、一個不帶 FCS 的幀；該通道上的每個 10 位元組 ACK 也會送出 |
| `0x8D` TX_DONE | 板子 | 驅動對某一幀（station 或接入點）的 TX-done：u32 板子時間 µs、u32 距它所完成的 ETH_TX 的 µs（沒有則為全 1）、u8 是否被對端射頻確認、u8 介面、u16 長度、該幀的前 24 位元組（即其 802.11 頭） |
| `0x8E` BUTTON | 板子 | 一次 BOOT 按下，30 ms 去抖：u32 板子時間 µs、u16 自啟動以來的按下次數；主機會列印 `BOOT button, mark N`，跟蹤記錄也會保留 |
| `0x8F` RX_CENSUS | 板子 | 收到的每一幀，包括 FCS 失敗的幀與控制幀：u32 接收時間 µs、i8 RSSI、i8 噪聲底、u8 `rx_state`（0 為正常）、u8 資料包型別（0 管理、1 控制、2 資料、3 其他）、u8 `sig_mode`、u8 速率碼、u8 MCS（位 7 表示 40 MHz）、含 FCS 的 u16 `sig_len`、該幀的前 16 位元組 |
| `0x90` BEACON | 板子 | u8 是否存有映象、u8 是否正在執行、u8 分片數、u16 映象長度、u32 映象 CRC-32（整個映象的 `zlib.crc32`） |

`rx_state` 為 98 表示雙流 HT（MCS 8 到 15），單流 ESP32 從不解出這種幀；65 表示其他調變方式下的損壞幀。

| STATUS 計數器 | 統計內容 |
|---|---|
| `tx_acked`、`tx_unacked` | 驅動的 TX-done 結果 |
| `tx_eth`、`tx_eth_failed`、`tx_eth_retried` | 已發出的 ETH_TX、失敗的，以及發現驅動佇列已滿的呼叫 |
| `tx_queued_max_us`、`_total_us`、`_n`、`_pending` | 從 ETH_TX 到 TX-done 的耗時，基於匹配上的 TX_DONE |
| `wire_dropped`、`wire_rx_bad` | 被丟棄的板子到主機訊息；COBS 或 CRC 失敗的主機命令 |
| `uart_fifo_ovf`、`uart_buffer_full`、`uart_overflow` | 128 位元組硬體 FIFO 與 16 KB 環形緩衝的溢位，以及兩者之和 |
| `uart_frame_err`、`uart_events_full` | 幀、奇偶與 break 事件；UART 事件佇列滿的 tick（計數器可能少計） |
| `read_max_us`、`write_max_us`、`handler_max_us`、`handler_max_type` | 最長的主機鏈路讀取回合（含 20 ms 超時）、寫者等待，以及最長的命令及其型別 |
| `heap_min`、`queue_max`、`refused_heap`、`refused_queue` | 最小空閒堆、最深的傳送佇列、因堆下限和佇列滿而被拒絕的訊息數 |
| `tx_eth_max_us`、`tx_eth_total_us`、`tx_eth_slow` | `esp_wifi_internal_tx` 中的 ETH_TX（含重試）的最長值、總和，以及超過 5 ms 的次數 |

EtherType 為 `0x88B7` 的幀是 LDN 認證；`esp32_wlan` 把它們轉成 LDN 庫的 `CustomFrameEvent`。其餘乙太網路幀都進入某個 L2 埠，由 `POKELDN_L2=tap|userspace` 選擇：

| 埠 | 位置 | 啟動器的套接字 |
|---|---|---|
| `userspace_ip` 棧 | 預設，所有平臺 | `userspace_ip.udp_socket` 與 `packet_socket` |
| 以介面命名的核心 TAP | 僅 Linux，`POKELDN_L2=tap` | 核心套接字，`SO_BINDTODEVICE` 與 `AF_PACKET` 保持不變 |
| `MemoryPort` | 測試 | 無 |

建立 TAP 需要 `CAP_NET_ADMIN`。

### 主機看門狗

主機每秒向 1.4.0 及以後的韌體傳送一次 ALIVE（`esp32.ALIVE_EVERY`）。HELLO 之後的第一個 ALIVE 會武裝看門狗；HELLO 會解除武裝，因此從不發 ALIVE 的主機永遠不會被監視。武裝後，不在空閒狀態的板子若 5 秒（`HOST_SILENT_US`）沒讀到主機命令，就執行 STOP 的拆除流程：接入點停止發信標、其 station 掉線，station 斷開。隨後它會丟棄所有發給主機的訊息且不計數，直到主機再次發來命令；否則每條排隊訊息都要付出一次 500 ms 寫入、一次 `wire_dropped`，以及 LED 上常亮的 `flash3`。在火紅交換房間裡殺掉主機程序時，主機端會顯示 2318-0006，之後搜尋 JOIN 也列不出任何主機。

## 便攜信標

從韌體 1.8.0 起，板子把一輪 LDN 廣播存放在 NVS 中，並可在沒有主機的情況下發送。儲存了映象且上電後 3 秒內沒有主機命令時，它會啟動映象裡的接入點、回放最多四條螢幕命令，並每隔 `interval_ms`（100）傳送一條廣播，每隔 `dwell_ms`（500）切換到下一個分片。HELLO、CHANNEL、SNIFF、STA_JOIN、STOP 與 AP_START 都會終止它；若主機被看門狗判定為消失，它則繼續執行。`pokeldn.ldn.portable` 根據 `ldn.create_network` 會建立的網路構建映象；`bin/swsh_gift_host.py --save-to-board` 會存下一份劍與盾的神秘禮物（[劍與盾神秘禮物](swsh_gift.md)）。

板子按主機的方式構建每一幀（`firmware/esp32/main/advert.c`，PSA SHA-256、AES-CTR 與 AES-GCM）：存下的頭部、該分片的載荷，以及一個每次啟動都從隨機值開始、每個分片加一的 nonce，與 `set_application_data` 在主機上遞增它的方式一致。`tests/test_esp32_beacon.py` 編譯 `advert.c`，並針對協議 1 和 3 把它的幀與 LDN 庫的幀逐位元組比對。

| 偏移 | 大小 | 欄位（小端） |
|---|---|---|
| 0 | 4 | `PKSA` |
| 4 | 1 | 佈局，1 |
| 5 | 1 | 種類，1（一輪廣播） |
| 6 | 2 | 映象長度，含 CRC |
| 8 | 1 | 通道 |
| 9 | 6 | BSSID |
| 15 | 32 | SSID，與 AP_START 接受的形式相同 |
| 47 | 16 | 資料金鑰 |
| 63 | 1 | 最大 station 數 |
| 64 | 16 | 廣播金鑰 |
| 80 | 40 | 廣播頭：network id、版本、格式、u16 大端長度、u32 大端 nonce |
| 120 | 2 | `interval_ms`，20 到 1000 |
| 122 | 2 | `dwell_ms`，不小於 `interval_ms` |
| 124 | 1 | 分片數，1 到 8 |
| 125 | 1 | 螢幕命令數，0 到 4 |
| 126 | 2 | 零 |
| 128 | | 每個分片：u16 長度與該廣播的明文；每條螢幕命令：u16 長度與一個 DISPLAY 載荷 |
| end | 4 | 此前所有內容的 `zlib.crc32` |

映象裡只有為它那一個網路派生出的廣播金鑰與資料金鑰，絕不含 `prod.keys`。一個映象最多 12288 位元組。一塊韌體 1.9.1 的 XIAO ESP32S3 在上電後獨立工作，向一臺零售劍送出了一隻劍的神秘禮物寶可夢。從韌體 1.9.1 起，板子應答第一條命令之前就會從 NVS 讀取存下的映象；1.9.0 會對埠剛開啟時發來的 BEACON QUERY 回答「未儲存」。板子留在電腦 USB 上但沒開應用時，會和接在充電器上一樣啟動信標。

### 主機映象

從韌體 1.9.0 起，種類 2 的映象讓板子自己應答每臺主機端的加入，並播放 `bin/frlg_mg_host.py` 所播放的會話，因此火紅或葉綠只憑板子就能收到神秘禮物。`bin/frlg_mg_host.py --save-to-board`（應用裡的「儲存在板子上」）會存下一份；`pokeldn.frlg.gift.portable` 通過構造啟動器本會執行的主機應用、並保留該主機在主機端加入前算出的內容來構建它。神秘卡片、神秘新聞、印章收集的印章、來訪訓練家和神秘事件指令碼佔 2 到 4 KB；緩衝指令碼與存檔備份/恢復要在電腦上讀取答案，會被拒絕。

種類 2 沒有分片（第 124 位元組為 0），只有 AES-GCM 頭。螢幕命令之後直到 CRC 是若干記錄，每條為 u8 標籤、u16 長度與位元組（`firmware/esp32/main/gift.h`）：

| 標籤 | 記錄 | 寫入者 |
|---|---|---|
| 1 | LDN：廣播明文，直到並包含主機的 48 位元組 station 條目；認證頭的 network id（小端）；用於解出認證金鑰的 16 位元組金鑰；32 位元組 challenge key；u64 challenge；u64 device id；版本；平臺 | `pokeldn.ldn.portable.ldn_record` |
| 2 | Pia：會話金鑰 `AES(game key, SSID)`、u32 network id、主機的 IPv4 地址、玩家 id 與名字 | `portable.pia_record` |
| 16、17 | 主機 LinkPlayer 塊之前與之後的應用資料 | `pokeldn.frlg.gift.portable` |
| 18 | 主機 200 位元組的 LinkPlayer 塊與 RFU parent id | |
| 19 | `MysteryGiftTiming` 的八個欄位、標誌（1 原生 nonce，2 先發加入響應，4 信任 Pia）、u32 協議 tick µs | |
| 20 | 遊戲家族（0 火紅/葉綠，1 綠寶石）、期望的主機端（0 任意） | |
| 21 | 編譯成位元組碼的伺服器指令碼：每個 `SVR_LOAD_*` 變成一個槽位 | |
| 22 | 一個載荷：u8 標識、u16 大小（0 表示 1024 位元組緩衝區）、位元組；每個不同訊息一條 | |
| 23 | 一份提供的卡帶：遊戲程式碼（四個零表示任意）、卡片標誌 id、圖示、印章欄位、每個槽位一個載荷 | |

認證金鑰是 `AES-ECB-decrypt(K, SHA-256(client random)[:16])`，其中 `K` 是 `KeyDerivation._derive_key` 針對源 `f1e7018419a84f711da714c2cf919c9c` 的第三步，一個為 LDN 協議 3 派生出的金鑰。除最後一條外，每條螢幕命令都在啟動時播放；最後一條是遞送場景，在一次成功遞送的會話之後播放，隨後再放啟動的那幾條。

引擎是純 C，逐層逐行移植了對應的 Python 模組：

| 檔案 | 移植自 |
|---|---|
| `gift_ldn.c` | `ldn.APNetwork` 的認證與 challenge 應答、station 加入時的廣播、`userspace_ip` 的 ARP 與 IPv4/UDP、`host_app.py` 的執行迴圈 |
| `gift_pia.c` | `crypto.PiaCrypto`、`reliable.parse_messages`、`pia_connect` 的 Net、Session 與 RTT 編解碼、`host_pia.HostPeerProtocol` |
| `gift_link.c` | `reliable.HostReliableSession`、`ni.py`、`rfu_leader.RFULeader`、`host_session.HostSession` |
| `gift_mg.c` | `host_mystery_gift.HostMysteryGiftEngine`、`block.BlockSender` 與 `RecvBlock`、`mg_link`、伺服器指令碼 |
| `gift_zstd.c` | zstd 1.5.7 的解碼器（`vendor/zstd`） |

信標任務執行它：驅動的幀與關聯通過一個佇列到達它，它按自己返回的截止時間執行定時器，並每隔 `interval_ms` 重建廣播，每次變化把 nonce 加一。station 的廣播（首先是它對主機的 ARP）不帶 DS 位、用組金鑰發出，接入點會丟棄它們：引擎從混雜回撥中整幀取走並自行解密，用 LDN 庫的 nonce 與 AAD 做 AES-CCM、8 位元組 MIC，無論是否帶 QoS（[station 的廣播](ldn.md#a-stations-broadcasts)）。零售 ESP32-S3 會把它們以已用當前組金鑰解密的形式交上來，Protected 位、CCMP 頭與 MIC 都還在（一個火紅 ARP 是 76 位元組）；從韌體 1.9.1 起，CCMP 頭之後以 SNAP 頭開頭的幀體被視為明文，與主機的 `accept_decrypted_ccmp` 一樣。韌體 1.9.0 會丟棄它們，主機端在認證之後以通訊錯誤退出。主機端會壓縮它的大部分資料包（一次神秘卡片會話中 1363 個裡有 1056 個）；解碼器上下文為 38,464 位元組，外加 1 KB 字面量緩衝。主機壓縮過的資料包以單原始塊的 zstd 幀發出。引擎狀態約 41 KB，啟動時連同解碼器一起從堆上取。

板子一次只接納一臺主機端，對另一臺的認證以狀態 1 拒絕。若某臺主機端的遊戲程式碼沒有任何卡帶記錄指名，或指令碼拒絕了它的遊戲資料，它會在遊戲資料請求之後被斷開，不再發送任何內容。已接納的主機端靜默 60 秒，或在 RFU 關閉後仍被接納 30 秒，都會被斷開。主機端離開時，在它確認關閉後等 2 秒穩定，板子便在同一網路與金鑰上服務下一臺。

`tests/test_esp32_gift.py` 編譯引擎與 zstd，讓它在模擬板子上對位扮演主機端的 `bin/frlg_mg_client.py` 執行；後者像零售火紅那樣用 ARP 解析主機，並以自己的 Session 型別 6 開啟 Reliable 流，其廣播由 LDN 庫加密、不帶 DS 位到達板子。神秘卡片、已持有的卡片、被拒絕的替換、一枚印章和神秘新聞，各自都以 `MysteryGiftServer` 對該主機端傳送的訊息收尾，逐位元組一致；第一臺之後會服務第二臺；映象不提供的卡帶會被拒絕。一塊韌體 1.9.1 的 XIAO ESP32S3 在無主機供電的情況下，向一臺零售法文火紅遞送了一張神秘卡片，並向已持有該卡的主機端又服務了一次。

## 序列埠上限

經典 ESP32 的 UART 在 921600 波特率下從板子到主機承載 92.16 KB/s；Pia 載荷是密文，無法壓縮。除非設定 AP 標誌 4（`POKELDN_ESP32_AP_FLAGS=4`），主持中的板子還會為每個 station 資料幀傳送一份 48 位元組的 RX_MGMT 副本；附近每個 LDN 網路每秒大約增加十條廣播。

傳送佇列可容納 384 條訊息，並在空閒堆低於 64 KB 時拒絕新訊息；當主機端以線路速率灌入時，堆下限會先於佇列滿而拒絕 RX_ETH。

### 波特率

`POKELDN_ESP32_BAUD` 設定 `open_serial` 切換到的速率，預設 921600；上限由 USB 橋決定。在 macOS 上，ELEGOO 板子的 CP2102 以 1500000 承載 149.1 KB/s 且無丟失，而 2000000 和 3000000 從不應答 HELLO。`tools/ldn/esp32_bench.py --port PORT --bauds LIST` 會按每個速率流式跑 BENCH。

### 主機到板子的命令丟失與 CREDIT

在主機端的洪流下，板子可能在處理函式之前就丟掉主機命令。韌體的對策如下，每一條都與其缺失時做過對比測量：

| 原因 | 韌體的做法 |
|---|---|
| UART 中斷在核心 0，與 Wi-Fi 任務同核 | 從讀取任務安裝驅動，核心 1 |
| 一次阻塞的 ETH_TX 會讓 16 KB 環形緩衝和 128 位元組 FIFO 溢位 | CREDIT 流控 |
| FIFO 在 120 位元組時就讀取，1500000 下距滿只有 53 µs | 閾值 32（`uart_set_rx_full_threshold`），640 µs |
| `uart_read_bytes`（IDF 6.1 `uart.c:1738`）對每個環形緩衝項都要等滿超時 | 先等一個位元組，再取 `uart_get_buffered_data_len` |
| `uart_write_bytes` 在 TX 環滿時忙等，餓死讀取者 | 寫者睡到該幀能放下為止（`uart_get_tx_buffer_free_size`） |
| `UART_DATA` 事件塞滿承載溢位事件的 64 項佇列 | 一個優先順序高於讀取者的任務每個 tick 排空它；`uart_events_full` |

板子發出一次 CREDIT 之後，主機的寫執行緒會把「已寫但未上報」的位元組控制在 8 KB 以內（`esp32.FLOW_WINDOW`）；啟動器的 trio 迴圈只做排隊，超過 512 個排隊幀後的 ETH_TX 與 RAW_TX 會被丟棄（`Radio.tx_dropped`）。視窗關閉期間計數連續 0.3 秒不變，說明有位元組丟失，主機會重新開啟視窗（`Radio.flow_resyncs`）。絕不要僅憑沉默就重同步：繁忙的讀取者可能壓住 0.7 秒，此時重同步會在 16 KB 環形緩衝上塞進 16 KB 在途資料。板子每 1024 位元組給一次 credit（`wire.c` 的 `CREDIT_STEP`），因此主機把 CREDIT 對應到已寫位元組加上線上的那一幀。沒有 CREDIT 的板子會被無節流地寫。板子會記錄超過 50 ms 的命令（`slow command`）和超過 100 ms 的讀取回合（`reader held`）。

HELLO 會重置兩邊的計數，因此主機會等到沒有在途資料才發它，並讓視窗保持關閉，直到板子發來 CREDIT 0（`tests/test_esp32.py::test_a_hello_mid_session_does_not_open_the_window`）。`tools/ldn/esp32_cmd_loss.py TRACE` 會對賬一份跟蹤記錄：已寫的 ETH_TX 對 `tx_eth + tx_eth_failed`，自 HELLO 以來已寫的位元組對最後一次 CREDIT。

### 傳送時序

ETH_TX 在驅動裡花約 0.1 ms，等待 TX-done 的中位數約 1 ms。在洪流下，TX_DONE 到達主機最多晚 0.6 秒。陷阱：嗅探板子自己的線路會成串積壓，因此要用對端的確認來計時遞送；接入點的洪流以 1 Mbit/s 廣播，超過約每秒 90 幀就會佔滿空口。

## 停頓與接收遺漏

在火紅交換中讓板子充當接入點時，一幀通常約 1 ms 完成；偶爾會有一幀未被主機端確認，卡住 100 到 260 ms，而它後面的幀成串完成，板子既聽不到主機端的資料，也聽不到它的 ACK。是否卡住由通道決定：在與繁忙接入點共用的通道上，大多數交換都會卡；在通道 11 上一次也沒有。`config/host.local.toml` 可以設 `[host] channel`；主機端只在 1、6 或 11 上加入主機。240 MHz 的 CPU 與固定速率（AP 標誌位 3..5：1 到 7 對應 1、11、6、12、24、36、54 Mbit/s）都不能消除卡頓。`tools/ldn/esp32_hold.py CAPTURE TRACE` 把每次等待拆成階段，`tools/ldn/esp32_hold_air.py` 列出嗅探器看到的內容，`tools/ldn/esp32_rx_copies.py` 把主機端的重試與板子的接收遺漏對應起來。

### 兩塊板子上的接收遺漏

作為接入點時，板子會漏掉 station 的 OFDM 首份複製的 1% 到 22%；1 Mbit/s 的 DSSS 幾乎從不漏。`tools/ldn/esp32_pair_bench.py AP STA --flood 0 --burst N --send R` 會統計這些。遺漏集中在緊跟板子自身傳送之後的幀上，例如它發出 6 Mbit/s 的 CTS 後 60 µs 的資料幀。在安靜通道上（3 到 9 上為 0.8% 到 2.3%）、每個 station 幀前都發 RTS（STA_JOIN 標誌 1）、以及 station 滿功率時，遺漏更少。

信標間隔、混雜接收、噪聲底檢查、接收緩衝、CPU 頻率、IRAM 最佳化、接入點功率，以及 ESP-IDF v5.5.5 對 v6.1，都沒有帶來變化。大多數遺漏在接入點側不留任何痕跡，甚至連 FCS 失敗都沒有。

station 的每次重試都在 RTS 之後發出（`lmacConfMib` +42，閾值在 +22；`esp_wifi_internal_get_rts`/`_set_rts`）。`lmacRetryTxFrame` 按 `lmacConfMib` 的上限重發（短重試 +21、長重試 +20，預設 32；`esp_wifi_internal_set_retry_counter`）。ACK 與 CTS 的速率表位於 `0x3ff73400`..`0x3ff7341c`。

## 使用者態協議棧

`pokeldn.ldn.userspace_ip` 在主機程序內實現 IPv4、UDP 與 ARP。協議棧按介面名註冊（加入方為 `ldnclient`，接入點為 `ldn-tap`）；對核心介面，`userspace_ip.lookup(name)` 返回 None，啟動器正是據此選擇路徑。地址與鄰居來自 LDN 庫的 `add_address`、`add_neighbor` 以及收到的幀；沒有鄰居的單播目的地會先發 ARP 請求並丟棄該資料包；`.255` 走廣播。超過 1472 位元組的資料包會被分片，分片重組超時 5 秒。`udp_socket(port)` 與 `packet_socket()` 分別頂替繫結的 UDP 套接字與 `AF_PACKET` 套接字，各自背後是一個套接字對、每個排隊資料包一位元組，因此 `select` 與 `trio.lowlevel.wait_readable` 在所有平臺上都能用。

陷阱：板子的幀通過啟動器自身 trio 迴圈裡的 trio 任務到達協議棧。絕不要在該迴圈裡阻塞於 `select`；要在 `trio.move_on_after` 下用 `trio.lowlevel.wait_readable` 等待。

## 板子的 LED 與按鍵

經典 ESP32 上 LED 是 GPIO2，S3 上是反相的 GPIO21，C6 上是反相的 GPIO15；C3 韌體不碰 LED 引腳。經典 ESP32 和 S3 上 BOOT 是 GPIO0，C3 和 C6 上是 GPIO9；每次按下都會發送 BUTTON（`0x8E`）、閃一下 LED 並喚醒螢幕。在 ELEGOO ESP-32 Type-C 板（CP2102、ESP32-D0WD-V3、無標的 PCB 天線模組）上，紅色 LED 是電源軌，藍色的是 GPIO2。GPIO2 和 GPIO0 是 strapping 引腳；韌體只在啟動之後才驅動 GPIO2。

LED 以 LEDC PWM（13 位、5 kHz）每 10 ms 更新，gamma 2.2，150 ms 交叉漸變。

| 圖案 | id | 預設週期 | 形狀 |
|---|---|---|---|
| auto | 0 | | 當前模式的外觀，見下 |
| off、on | 1、2 | | |
| breathe | 3 | 3000 ms | 升餘弦 |
| blink | 4 | 1000 ms | 半個週期內亮 |
| flash3 | 5 | 1000 ms | 週期的前 60 % 內閃三下 |
| ramp-up、ramp-down、pulse | 6、7、8 | 1000、1000、1200 ms | 只執行一次 |

自動外觀：啟動時一次脈衝，空閒時 4 秒的暗呼吸，加入中 250 ms 閃爍，主持且無 station 時更亮的 1.5 秒呼吸，已連線時保持暗亮，嗅探時熄滅。

在此之上，每一幀都會讓 LED 閃一下。加入失敗、金鑰被拒、板子到主機的訊息被丟棄，或主機命令丟失，都會播放 1.5 秒的 flash3。完成一次交換或神秘禮物會漸亮到最亮（`pokeldn.ldn.show_done`）。`tools/ldn/esp32_led.py --port PORT PATTERN` 可設定外觀；`--demo` 逐個演示。

## 螢幕

I2C 上的 SSD1306 128x64 OLED 是可選的（SSD1315 與 SSD1309 模組也可用）。韌體先探測 0x3C，再探測 0x3D；有螢幕時以 400 kHz 每 50 ms 畫一幀。

| 目標 | SDA | SCL | 板子引腳 |
|---|---|---|---|
| ESP32 | GPIO21 | GPIO22 | DevKit V1 D21、D22 |
| ESP32-S3 | GPIO8 | GPIO9 | |
| ESP32-C3 | GPIO6 | GPIO7 | XIAO D4、D5 |
| ESP32-C3 | GPIO5 | GPIO6 | 0.42 英寸 OLED 板自帶的 72x40 螢幕，第二個探測 |
| ESP32-C6 | GPIO22 | GPIO23 | XIAO D4、D5 |

常見的四針模組自帶穩壓與上拉；它的地址電阻選擇 0x3C（絲印 0x78）或 0x3D（0x7A）。韌體設定段重對映（`A1`）、反向 COM 掃描（`C8`）與備用 COM 引腳（`DA 12`）。ESP32-C3 的 0.42 英寸 OLED 板上 72x40 面板顯示幀的第 30..101 列與第 24..63 行；這些引腳上的螢幕會得到緊湊場景（一行 12 個字元、半尺寸精靈），可由 `tools/ldn/screen_preview.py --panel 72x40` 離線渲染。

沒有主機命令時，螢幕顯示無線模組的狀態：空閒、加入中或主持中，以及是否已連線，並統計各方向的幀數。無線模組活動或有動畫播放時，它保持最亮；最後一次 DISPLAY、HELLO 或 BOOT 按下後也保持 60 秒；然後它變暗到對比度 1、預充電 `22`（`81 01 D9 22`），600 秒後關閉（`AE`）。預充電更低會閃爍。空閒畫面每 60 秒平移 2 畫素以防燒屏。`tests/test_esp32_screen.py` 固化了這些時序。

DISPLAY（`0x0E`）攜帶一個操作：

| 操作 | 佈局 |
|---|---|
| `0` SHOW | u8 顯示編號、u16 保持秒數（0 為直到下一次顯示）、標題、NUL、一行文字、NUL；每段文字最多 21 個 ASCII 字元 |
| `1` SPRITE | u8 槽位（0 我方，1 對方，2 禮物）、u8 寬 ≤ 64、u8 高 ≤ 64、每行 `(width + 7) / 8` 位元組，MSB 在前；寬為 0 清空該槽 |
| `2` LOBBY | u8 星數（0..7，0 為無）、u8 已加入人數、u8 座位數（1..3，至少等於已加入人數）、標題、NUL、名字、NUL、連線密碼、NUL；啟動聯盟室畫面 |
| `3` JOINED | u8 已加入人數，最多為聯盟室的座位數；沒有聯盟室畫面時被拒 |

| 畫面 | id | 內容 |
|---|---|---|
| auto | 0 | 無線模組的狀態 |
| trade | 1 | 槽位 0 帶「offering」與那行文字 |
| traded | 2 | 槽位 0 乘球離開（2.1 秒），資料包來回直到保持時間，一個球到達並開啟（1.6 秒），然後槽位 1 顯示「received」10 秒 |
| gift | 3 | 一張持著槽位 2 的神秘卡片 |
| gifted | 4 | 卡片離開，然後「delivered!」 |
| arrived | 5 | 仍在等待的 traded 畫面現在把球帶進來 |
| lobby | LOBBY | 槽位 0、標題、名字、星數、「joined/seats」與密碼 |

一個畫面會等待正在播放的 traded 或 gifted 畫面；無線模組回到空閒時畫面結束。

`pokeldn.app.screen` 是啟動器一側：`offer`、`received`、`arrived`、`gift`、`delivered`、`lobby` 和 `joined` 立即返回，並在單個執行緒上按順序執行。主持團體戰時會亮出聯盟室。每個啟動器都在交換的最後一步呼叫 `received`，保持時間取下表時間減去 2.5 秒，好讓球與主機端的球同時開啟：

| 作品 | 起點 | 主機端收到寶可夢 | 動畫後的第一條訊息 |
|---|---|---|---|
| 火紅/葉綠 | START_TRADE | 22.7 秒 | READY_FINISH_TRADE（[火紅的連線](frlg_link.md)） |
| Let's Go | 步驟 `0e` | 15.3 秒 | 型別 4 載荷（[Let's Go 會話](lgpe_session.md#the-trade-animation)） |
| 劍/盾 | 最後一個 syncCommand 40 | 15.0 秒 | 無（[劍的交換](swsh_trade.md#the-trade-animation)） |
| 晶燦鑽石/明亮珍珠 | `tradeState` 5 | 18.6 秒 | 無（[BDSP 交換](bdsp_trade.md#the-completed-trade)） |
| 傳說 阿爾宙斯 | `01 0e` | 28.5 秒 | 盒子訊息 `00 02`（[傳說 阿爾宙斯](pla.md#the-completed-trade)） |
| 朱/紫 | `8001010e` | 19.8 秒 | 無（[朱與紫](sv.md#the-trade)） |
| 傳說 Z-A | 第四步 | 26.2 秒 | 下一條 `01 01` 預覽（[傳說 Z-A](za.md#a-trade-with-a-retail-console)） |

這些時間點是手工標記的（最多晚 2 秒）。啟動器在動畫之後的那條訊息處呼叫 `arrived`。精靈圖取自 PokeAPI 的火紅/葉綠版本，種族值 386 以內用這些，之後用預設圖；裁切、縮放到最多 64（卡片上為 40），並二值化到一位，內部線條保持深色。`tools/ldn/esp32_screen.py --port PORT` 在板子上播放一次交換和一次禮物；`tools/ldn/screen_preview.py OUT.gif` 離線渲染一段指令碼化會話。

### E32R40T 板

E32R40T（以 4.0 英寸 ESP32-32E 顯示屏的名義出售）是一塊經典 ESP32，帶 SPI 上的 480x320 ST7796S 面板。它的韌體是單獨的構建，在 `idf.py` 的環境裡設 `POKELDN_DISPLAY=E32R40T`（預設為 `OLED`）；釋出映象是 OLED 構建。

| 訊號 | GPIO |
|---|---|
| CS、DC、SCK、MOSI | 15、2、14、13 |
| 背光，高電平點亮 | 27 |
| RGB LED，低電平點亮：紅、綠、藍 | 22、16、17 |

面板以 3 倍（384x192）顯示 128x64 的幀，白底黑字，SPI 40 MHz。GPIO2 是面板的 DC，因此板子的 LED 是 GPIO17 上的藍色那顆。OLED 該熄滅時背光也關掉。

## 構建與刷寫

韌體版本（`firmware/esp32/version.txt`，`major.minor.patch`，所有目標共用）在 INFO 中以 `version=...` 報告；沒有版本號的構建顯示 `version unknown`，只要序列埠協議匹配就能工作。協議號是另一回事，只在線上協議變化時才變。

ESP-IDF v6.1（標籤 `v6.1`，提交 `fff9895c82d744c7237be8847347bdd1b07c6643`）可構建全部四個目標。用 `install.sh esp32,esp32s3,esp32c3,esp32c6` 安裝其工具，然後啟用 IDF 環境。

    cd firmware/esp32
    idf.py set-target esp32   # esp32s3, esp32c3 or esp32c6 for those chips
    idf.py build
    idf.py -p <port> flash

控制台輸出關閉；在經典 ESP32 上，韌體自己指定 UART0 的 GPIO1 與 GPIO3（`uart_set_pin`）。桌面應用用 esptool 檢測晶片，並在寫入前按晶片的 flash 偏移（ESP32 為 `0x1000`，其他為 `0x0`）校驗合併映象的引導載入器：esptool 5.4.0 的 `write_flash` 在映象以填充開頭時可能跳過晶片檢查。絕不要根據 USB 橋的 ID 來選擇韌體。esptool 根據埠的 USB id 決定復位方式，而 esp-pylib 1.1.5 拒絕對 Android 的 `android://board` 這類 URL 埠做該查詢；拿不到 id 時，它給 ESP32-S3、C3 或 C6 用經典的 DTR/RTS 復位，晶片永遠進不了 ROM 載入器，日誌顯示 `Failed to get VID/PID`。Android 應用用板子自身的 USB id 回答該查詢（`pokeldn/app/android.py`）。id 已知時，Linux 或 Android 上的 CP210x 板子會得到同時寫 DTR 與 RTS 的復位，通過埠 `fileno()` 上的 `ioctl` 完成；Android 端沒有檔案描述符，改為在一次 CDC `SET_CONTROL_LINE_STATE` 裡同時送出兩條線。[桌面構建](gui.md) 介紹四個映象的打包。

### 藍牙

以 `POKELDN_BLE=1` 構建時，還會通過藍牙 LE 承載主機鏈路，供打不開 USB 序列埠裝置的 iOS 應用使用；此時板子的 USB 只用來供電。

    POKELDN_BLE=1 idf.py -B ../../scratchpad/esp/build-ble \
        -D SDKCONFIG=../../scratchpad/esp/build-ble/sdkconfig \
        -D SDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.defaults.ble" build

板子只廣播自己的名字 `POKELDN-RADIO`；iOS 應用掃描時不帶服務過濾。服務為 `7a1e0101-5d2c-4c3e-9f4b-504f4b454c44`：主機把 COBS 流寫到 `...0102`（無響應寫），板子在 `...0103` 上通知。當某個中心裝置訂閱了 `...0103`，線路就走那裡，線纜隨之靜默。分幀、CRC 與 CREDIT 不變。HELLO 文本以 `link=ble` 結尾，裝置頁會把它顯示為藍牙無線韌體。`POKELDN_RADIO=esp32:ble`（或 `esp32:ble:NAME`）可從任意啟動器開啟它（`pokeldn/ldn/esp32_ble.py`，bleak）。

BLE 構建使用僅 BLE 的控制器、10 個靜態 Wi-Fi 接收緩衝和 10 KB 接收緩衝，並釋放經典藍牙的記憶體：雙模控制器會讓空閒堆低於線上協議的 64 KB 下限。走 BLE 時板子不發 TX_DONE，並把排隊幀合併成一次通知。它請求 15 ms 間隔（中心裝置訂閱後再請求一次；STATUS 中的 `ble_itvl_us`）、2M PHY、247 位元組 MTU 與資料長度擴充套件；間隔為 30 ms 時火紅的房間會慢得像爬。

經典 ESP32（藍牙 4.2，無 2M PHY）實測 28.1 KB/s，能完成火紅的主持方交換，但作為火紅加入方太慢（2318-0013）。XIAO ESP32C6 實測 33.6 KB/s，能完成火紅的加入方交換。每個無線韌體構建都採用 ESP-IDF 的 single-app-large 分割槽表（0x10000 處 1500 KB 的 factory 應用；nvs 仍在 0x9000，phy_init 仍在 0xf000）；C6 的 BLE 映象（0xfd000 位元組）在其中還剩 488 KB。

在 macOS 上，若程序的負責應用沒有藍牙授權，bleak 會中止（SIGABRT）；用 `open -n -a Terminal FILE.command` 啟動的指令碼則執行在 Terminal 的授權之下。

### USB 主機鏈路

S3、C3 與 C6 在 USB Serial/JTAG 上使用同一套 COBS、CRC 與 CREDIT 協議，環形緩衝為 16 KB。被拒絕的 `usb_serial_jtag_write_bytes` 會每 20 ms 重試，500 ms 後計為一條丟棄訊息。接收中斷在 RX 環滿時丟棄一個 64 位元組包且不計數（`usb_serial_jtag.c:144`）；CREDIT 使環不被打滿。這條路徑上 UART 計數器保持為零，`POKELDN_ESP32_BAUD` 只改變經典 ESP32 的速率。在 USB 目標上，讀取者以優先順序 21 執行，高於寫者（20）：低於它時，寫者會在滿速流下餓死讀取者。

主機設定 1 秒寫超時；寫失敗或寫入不足會把會話按板子丟失結束。HELLO 之後，1 秒沒有有效幀會排入一次 STATUS 探測，3 秒靜默則以 USB 錯誤結束會話，並請使用者重新插拔板子。

沒有主機端參與、持續兩小時的主機到板子浸泡測試（只用一個波特率值；原生 USB 會忽略它）：

```sh
./.venv/bin/python tools/ldn/esp32_bench.py --port COM5 --bauds 921600 \
    --soak 7200 --size 1400 --rate 460000
```

它每 5 秒列印幀數、位元組數、credit 與 STATUS，並在 USB 失敗或幀數不匹配時以非零碼退出。它既不重現主機端的確認，也不重現其 Wi-Fi 負載。

## 執行

`POKELDN_RADIO=esp32:<port>` 讓每個啟動器的 `ldn` 呼叫都走板子。`esp32:auto` 取唯一存在的 USB 序列埠，有多個時拒絕選擇，因為開啟埠可能復位對應板子。埠每個程序只打開一次，且釋放 DTR 與 RTS；macOS 上的 CP2102 板子無論如何都會在開啟時復位。沒有復位的板子會保留上一次的 `BAUD`，因此主機會依次在 115200、`POKELDN_ESP32_BAUD`、921600 和 1500000 下嘗試 HELLO，然後再切到請求的速率。在 Windows 上 COM 口是獨佔開啟的（`PermissionError(13, 'Access is denied.')`），因此啟動器會在重試前先關閉靜默板子的埠；執行中拔掉板子會以 `[esp32] The board disconnected from USB` 結束。對 CP2102 來說，只拉低 RTS 就會把 EN 拉低，板子保持靜默。處於 ROM 下載模式的板子從不應答 HELLO。

走板子時，啟動器跳過所有 nl80211 步驟（`--phy auto` 解析為 `esp32`），不需要 root，也不注入信標；加入方的 `--mac` 會成為板子 station 的地址。在 5 GHz 上主持的 Switch 主機無法觸及。

`POKELDN_ESP32_TRACE=FILE` 會把每條序列埠訊息追加一行：Unix 時間、`>`（主機）或 `<`（板子）、型別與十六進位制載荷。

`tools/ldn/esp32_first_contact.py` 檢查一塊新板子（`--flash` 會寫入構建，然後依次做 HELLO、STATUS、統計各通道 LDN 動作幀的空閒掃描，帶 `--keys` 時再做一次解密掃描）；`tools/ldn/esp32_sniff.py` 把第二塊板子當嗅探器；`tests/test_esp32.py` 在兩塊模擬板子上執行 LDN 主機與 station（`pokeldn.ldn.esp32_sim`）。CH9102 或 CH343 橋會列舉為 CDC ACM（`/dev/ttyACM0`、`/dev/cu.usbmodem*`）。

### 解不出 OFDM 的板子

Switch 主機端的廣播是 HT MCS 3（[發現](ldn.md#discovery)），因此解不出 OFDM 的板子聽不到任何廣播：`esp32_first_contact.py` 在每個通道上統計到 0 個 LDN 動作幀，而關聯與 ping 在 DSSS 下仍然正常。把 `tools/ldn/esp32_census.py` 放在繁忙接入點旁邊就能區分：正常的板子會列出 `OFDM` 與 `HT` 的正常幀，聾的板子只有 `DSSS`，OFDM 幀在 `rx_state` 65 處失敗。一塊普通的 ESP32-WROOM-32 DevKit（ESP32-D0WD-V3 rev 3.1，CP2102）就是聾的；同款晶片的 WROOM-32E 板子則正常（[issue 1](https://github.com/Decryptu/pokeldn/issues/1)）。

## 按板子統計的交換

ELEGOO 板（ESP32-D0WD-V3 rev 3.1，CP2102，921600 波特率）在所有作品裡都能與零售 Switch 2 主機交換，station 與接入點兩種角色都行，並能遞送火紅和劍的神秘禮物。XIAO ESP32C3、ESP32C6（陶瓷天線）和 ESP32S3 在兩種角色下都能完成火紅交換，也能完成劍的主持方交換，C6 還能完成朱的主持方交換；Windows 上的 ESP32-S3 能完成火紅的加入方交換（[PR 2](https://github.com/Decryptu/pokeldn/pull/2)）。[Android 應用](../examples/android/README.md) 通過 XIAO ESP32C6 主持火紅，在其 Python 執行緒繫結到單個性能核心後達到每秒 51.1 個父級槽位。

加入板子接入點的火紅主機端會接受它長度為 0 的隱藏 SSID、速率順序、能力位 `0x0431` 與 WMM 元素，併發出一條關聯請求：listen interval 10、32 個十六進位制字元的 SSID、速率 `02 04 0b 16 0c 12 18 24` 與 `30 48 60 6c`、功率能力 `00 14`、RSN 能力 `0x0000`、一個 WMM 資訊元素、廠商元素 `00 22 aa 10 01 02`。它最初的廣播需要韌體轉發（[station 的廣播](ldn.md#a-stations-broadcasts)）。

### 加入

`STA_JOIN` 做一次關聯嘗試：在該通道與 BSSID 上快速掃描，然後開放認證並關聯；`LINK` 在 0.23 到 0.34 秒後建立。零售劍的網路可能在廣播仍能聽到的情況下讓一次嘗試失敗（`LINK` 斷開，原因 `0xc9` 或 `0x2`），再試一次就能關聯，因此主機會最多傳送三次 `STA_JOIN`（`pokeldn.ldn.esp32_wlan.JOIN_ATTEMPTS`）。一次嘗試為何落空尚不清楚。最後一次被拒之後主機會發 `STOP`：隨後掃描的 `CHANNEL` 在板子回到空閒前都會被拒絕。

### 發射功率

`POKELDN_ESP32_TX_POWER` 以 dBm 給板子的發射功率封頂（2 到 20）；主機以 0.25 dBm 為單位，把它作為 `STA_JOIN` 與 `AP_START` 的功率位元組傳送，桌面應用的設定裡「發射功率」也可設定。從韌體 1.9.3 起，station 的上限在關聯之前就設好；更早的映象則在 `LINK` 建立後才設。愛好者論壇反映 ESP32-C3 Super Mini 板子只有 8.5 dBm 時才能與接入點關聯，這是這些板子的天線缺陷；在 ESP32-C3 的 0.42 英寸 OLED 板上，該效應尚未實測。

沒有選功率時（設定為「自動」），由主機決定（`pokeldn.ldn.esp32_wlan.board_tx_power`）：

| 板子 | 功率 |
|---|---|
| HELLO 回覆中的晶片名為 `esp32c3` | 兩種角色都用 8.5 dBm；Super Mini 與 XIAO ESP32C3 報告相同的晶片與 USB id，因此所有 C3 都用它 |
| 其他 | 驅動的最大值；在 `JOIN_ATTEMPTS` 次加入被拒之後，再以 8.5 dBm 試一次 `STA_JOIN`，若成功關聯則本次執行餘下時間都用它 |

設定裡的「滿功率」（20 dBm）可在 C3 上恢復最大值。

### 無線模組測試

桌面應用的裝置頁「測試無線模組」（`pokeldn.ldn.esp32_radio_test`）無需執行主機端、也不需要第二塊板子，就能檢查板子的兩個方向：

| 階段 | 板子做什麼 | 玩家看到什麼 |
|---|---|---|
| 聽，約 20 秒 | 在通道 1、6 和 11 上：3 秒空閒，LDN 廣播以 `RX_MGMT` 到達主機，然後 3 秒普查（`SNIFF` 到 `ff:ff:ff:ff:ff:ff`） | 每個通道上 Switch 發射端與 Wi-Fi 信標的最佳 RSSI、幀數與損壞數、噪聲底中位數 |
| 被聽到，60 秒 | 以交換時所用的功率開一個隱藏接入點（`AP_START`），並從它用 `RAW_TX` 每 100 ms 發一個開放的 `POKELDN-TEST` 信標 | 手機的 Wi-Fi 列表裡，板子附近是否出現 `POKELDN-TEST` |

在本地遊玩選單裡等待主持的 Switch 會在其通道上顯示為一臺 Switch。聽得到 Wi-Fi 卻沒有 Switch，問題在主機端；什麼都聽不到，問題在板子的接收端。手機在板子旁邊始終列不出 `POKELDN-TEST`，問題在板子的發射端。Mac 的掃描只有在信標帶執行時間戳與 TIM 元素時才列出它，而且有些掃描會漏掉；只帶 SSID、速率與通道的信標從未被列出。結果會進入裝置頁的日誌，「複製裝置詳情」會包含它。

## 未解決

- XIAO ESP32C3 是否在自動的 8.5 dBm 下完成交換尚未實測；它是在驅動的最大值下完成交換的（[發射功率](#transmit-power)）。
- softAP 會協商 WMM，而 Switch 主機不協商；帶與不帶 WMM 交換都能完成（`POKELDN_ESP32_AP_FLAGS=2`，`AP_FLAG_NO_QOS`，清除該 station 的 QoS 標誌）。
- 接入點的接收路徑中是什麼導致漏掉 station 的 OFDM 首份複製，尚不清楚（[兩塊板子上的接收遺漏](#receive-misses-on-two-boards)）。
- ESP32-WROOM-32E 模組是否比 ELEGOO 板上的無標模組漏得更少，尚未實測。有使用者報告說較老的 ESP32-WROOM-32 交換不可靠；一塊 WROOM-32 DevKit 解不出任何 OFDM（[解不出 OFDM 的板子](#a-board-that-decodes-no-ofdm)）。
- 朱的 Switch 主機加入板子的接入點後，可能確認了通告卻不發端口 2 的加入（[朱與紫](sv.md#unresolved)）。
