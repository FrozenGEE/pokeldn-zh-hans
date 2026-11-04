---
title: ESP32 无线模块
parent: 硬件与设置
nav_order: 1
---

# ESP32 无线模块

接在 USB 串口上的 ESP32 板子就是无线模块。它运行 `firmware/esp32/`，承载 LDN 的厂商动作帧与以太网帧；广播加密、LDN 认证、IP 与 Pia 都留在主机上，[便携信标](#portable-beacon) 除外。`pokeldn.ldn.esp32_wlan` 为 LDN 库提供一个由板子支撑的工厂，因此 `ldn.scan`、`ldn.connect` 与 `ldn.create_network` 无需改动即可运行，主机也不需要 Wi-Fi 驱动。

## 支持的板子

| 芯片 | 主机连接 | 合并镜像 |
|---|---|---|
| 经典 ESP32（ESP32-D0WD、WROOM-32E） | UART0，经 USB 串口桥 | `pokeldn-radio.bin` |
| ESP32-S3 | 原生 USB Serial/JTAG | `pokeldn-radio-s3.bin` |
| ESP32-C3 | 原生 USB Serial/JTAG | `pokeldn-radio-c3.bin` |
| ESP32-C6 | 原生 USB Serial/JTAG | `pokeldn-radio-c6.bin` |
| 经典 ESP32、ESP32-C6 | 蓝牙 LE（iOS 应用），以及上面的 USB | `pokeldn-radio-ble.bin`、`pokeldn-radio-ble-c6.bin` |

所有目标都使用 2.4 GHz；不支持 ESP32-S2。S3、C3 或 C6 若同时有独立的 UART 口与原生 USB 口，必须使用原生口（S3 为 GPIO19/20，C3 为 GPIO18/19）；走 UART 口时固件永不应答。当某个 USB 串口桥上没有固件应答时，桌面应用会从 ROM 引导加载器读取芯片（esptool `detect_chip`），并指出 S3、C3 或 C6 插错了口。`303a:1001` 由多款芯片共用；刷写时用 esptool 检测芯片。

| 板子 | 天线 | BOOT | 用户 LED | CPU、任务核心 | 空闲可用堆 | 原生 USB 上的 BENCH，macOS |
|---|---|---|---|---|---|---|
| XIAO ESP32C3 rev 0.4 | 随附外置天线，必须装上 | GPIO9 | 无（只有充电指示） | 160 MHz，核心 0 | 152656 | 880.1 KB/s |
| XIAO ESP32C6 rev 0.2（C6FH4，4 MB） | 陶瓷天线，由固件选择 | GPIO9 | 黄色，GPIO15，低电平点亮 | 160 MHz，核心 0 | 255196 | 824.6 KB/s |
| XIAO ESP32S3 rev 0.2（8 MB flash、8 MB PSRAM） | 随附外置天线，必须装上 | GPIO0 | 黄色，GPIO21，低电平点亮 | 240 MHz，核心 1 | 212416 | 883 KB/s |

BENCH 不丢数据；主机的波特率设置不改变 USB 速度。更大的 S3 板子（N8R2、N16R8）带板载天线。板子指南：[XIAO ESP32C3](https://wiki.seeedstudio.com/XIAO_ESP32C3_Getting_Started/)、[XIAO ESP32C6](https://wiki.seeedstudio.com/xiao_esp32c6_getting_started/)。

XIAO ESP32C6 在 GPIO3 为低时给射频开关供电；GPIO14 为低则选择陶瓷天线。C6 固件在 Wi-Fi 启动前把两者都拉低；在 ESP32-C6-DevKitC-1 上这两个引脚只引到排针，因此一个镜像通用于所有 C6 板子。C6 的 station 被限制在 11b/g/n。它的接收头部没有 `sig_mode`、`mcs` 或 `cwb`：固件从 `cur_bb_format` 推导 `sig_mode`，从 `he_siga1` 推导 HT MCS，其速率字节对 OFDM 帧来说是 L-SIG 速率码。

各板子完成的交换见[按板子统计的交换](#trades-by-board)。

### 复位后的 USB 链路（C6、S3）

打开端口会复位 C6 或 S3。在 ESP-IDF 默认的 `CONFIG_ESP_SYSTEM_BBPLL_RECALIB=y` 下，启动过程会停掉为 USB Serial/JTAG 提供时钟的 BBPLL（`recalib_bbpll()`，`esp_system/port/soc/esp32c6/clk.c`），链路可能一直错乱到板子被拔下（SOF 帧号冻结，`USB_SERIAL_JTAG_INT_RAW` 为 `0000b5b2`，健康时为 `0000b50a`）。C6 与 S3 的构建把它设为 `n`（v5.2 及以上的引导加载器允许，每个合并镜像都自带引导加载器）：900 次 C6 打开和 300 次 S3 打开全部有应答。C3 没有这个选项，也没有此故障。

C6 与 S3 的构建带一个 USB 看门狗（`usbwatch.c`）：SOF 帧号停顿 2 秒就重启芯片，下一次 HELLO 会以 LOG 行带上 USB 与时钟寄存器。它在收到第一个 SOF 帧、或从线缆读到第一个主机字节时武装，并且在蓝牙主机已连接时从不重启：接在充电器上的板子收不到 SOF 帧，而在 1.7.0 之前的固件里，蓝牙主机的字节会武装它，所以接在充电器上的 C6 在 iPhone 应用下每 2 到 3 秒重启一次。以 `POKELDN_USB_BEACON=1` 构建时，两个镜像还会把那些寄存器每秒一次作为厂商动作帧广播到 `03:55:53:42:57:00`（布局见 `usbwatch.c`），USB 死掉期间 `esp32_sniff.py --mac 03:55:53:42:57:00` 会一直收着。

## 角色

| 角色 | 板子做什么 |
|---|---|
| 空闲 | 在一个信道上混杂接收；每个带任天堂 LDN 前缀 `7f 00 22 aa` 的动作帧都送给主机 |
| station | 用主机派生出的 CCMP 密钥按 BSSID 加入主机端的网络 |
| 接入点 | 在主机 BSSID 上的隐藏 SSID WPA2 网络，密钥方式相同 |

主机端的网络没有四次握手：两端从广播里的 server random 派生 CCMP 密钥。固件替换 ESP-IDF 私有 `struct wpa_funcs` 表中的四个条目（`esp_wifi_driver.h`）。该布局是 v6.1 blob 的 ABI；固件拒绝针对其他版本构建。

| 条目 | 替换为 |
|---|---|
| `wpa_sta_connect` | 在原有回调外面装上 Switch station 的 RSN 元素（CCMP、PSK、capabilities `0x000c`） |
| `wpa_sta_rx_eapol` | 丢弃 EAPOL；看到关联响应后用 `esp_wifi_set_sta_key_internal` 装入密钥，再由 `esp_wifi_auth_done_internal` 打开端口 |
| `wpa_ap_join` | 添加 station 并发送关联响应（`esp_send_assoc_resp`），不发 EAPOL-Key 消息 1（`AP_START` 标志位 0 保留原有加入流程）；主循环装入成对密钥（`esp_wifi_set_ap_key_internal(CCMP, mac, 0, key)`）并打开端口（`esp_wifi_wpa_ptk_init_done_internal(mac)`），即 hostapd 的 `PTKINITDONE` 顺序（`wpa_auth.c:2290-2332`）；组密钥在 `WIFI_EVENT_AP_START` 时以索引 1 装入 |

陷阱：绝不要等 `WIFI_EVENT_AP_STACONNECTED` 来装密钥。只有 `esp_wifi_wpa_ptk_init_done_internal` 会发出它，因此没有四次握手时它永不出现，主机端的第一个加密帧会被丢弃。

## 接入点的帧

softAP 的信标、探测响应与关联响应在闭源的 `libnet80211.a` 中构建（v6.1 `ieee80211_output.o` 的偏移），与 `vendor/LDN` 的接入点所发的帧对比：

| 字段 | Switch 的形式 | ESP32 softAP | 可设置 |
|---|---|---|---|
| 隐藏 SSID 元素 | 32 个零字节 | 长度 0（`ieee80211_beacon_construct` 0xc4） | 否 |
| 支持速率 | `82 84 8B 96 0C 12 18 24` | `8B 96 82 84 0C 18 30 60` | 否；同样是十二个速率与基本位，9 和 18 在扩展速率里 |
| 扩展速率 | `30 48 60 6C` | `6C 12 24 48` | 否 |
| 能力位，信标 | `0x0511` | `0x0431`（短前导常量，`ieee80211_getcapinfo` 0x7b） | 否 |
| HT 元素 | 无 | 11b/g/n 下存在 | 已移除：固件设为 11b/g |
| RSN 能力位 | `0x000c` | hostapd 自己的 | 已设置：`wpa_ap_get_wpa_ie` 返回 Switch 的元素 |
| WMM | 无 | 11g 下存在 | 只有仅 11b 才能去掉 |

隐藏的 softAP 只应答定向探测。不带配置 SSID 的关联请求会被丢弃（0x9c6）。`esp_wifi_80211_tx` 拒绝发送关联响应（`ieee80211_raw_frame_sanity_check` 0xf9），而 blob 自己的信标无法停止。

## 串口协议

一帧是 `COBS(type | payload | crc32-le(type | payload))` 后接 `0x00`；CRC 为 CRC-32/ISO-HDLC（`zlib.crc32`）。经典 ESP32 以 115200 波特率启动；`BAUD` 会切换两端，板子保持该速率直到复位。在 S3 上，`BAUD` 会被确认，但不改变 USB 传输速率。`0x00` 之前的任何内容，包括 ROM 的启动文本，都通不过校验并被丢弃。

| 类型 | 方向 | 载荷 |
|---|---|---|
| `0x01` HELLO | 主机 | 无；先由 CREDIT 0 应答，然后 INFO。主机先发一个 `0x00` 结束任何残缺帧 |
| `0x02` BAUD | 主机 | u32 波特率；以旧速率回 RESULT，UART 排空后切换（最多 3 秒）；`open_serial` 以新速率重试第一个 HELLO |
| `0x03` CHANNEL | 主机 | u8 信道；仅空闲时 |
| `0x04` STA_JOIN | 主机 | u8 信道、6 BSSID、32 SSID（LDN SSID 的十六进制文本）、16 密钥、6 station MAC（全零为随机）；可选：u8 固定数据速率（AP_START 位 3..5 的速率表）、u8 以 0.25 dBm 计的最大发射功率（`esp_wifi_set_max_tx_power`，8 到 84，驱动把它封顶在 61）、u8 标志：1 每帧前发 RTS，2 重试前不发 RTS（`esp_wifi_internal_set_rts`） |
| `0x05` STOP | 主机 | 无；回到空闲，清除密钥 |
| `0x06` AP_START | 主机 | u8 信道、6 BSSID、32 SSID、16 密钥、u8 最大 station 数、u8 标志：1 走原有关联与四次握手，2 对该 station 不用 QoS，4 不复制每个 station 数据帧的 40 字节，位 3..5 为固定数据速率，`0x40` 每 1000 TU 一个信标，`0x80` 不混杂接收；可选的第二个标志字节：1 关闭驱动的噪声底检查，2 其间隔为 250，4 在每份 40 字节副本头部带上接收时间，8 重试上限 7 和 4，`0x10` 除本网络 station 的正常数据帧外每帧都发 RX_CENSUS；之后是可选的以 0.25 dBm 计的最大发射功率 |
| `0x07` AP_KICK | 主机 | 6 MAC、u16 原因；解除认证 |
| `0x08` ETH_TX | 主机 | 一个以太网帧，由驱动用该 station 的密钥或组密钥加密。驱动队列满时每 1 ms 重试一次，最多 100 ms；发往已离开 station 的帧以 `0x3015` 失败。station 的以太网源地址必须是 LINK 中的 MAC，否则该帧永远不会被确认 |
| `0x09` RAW_TX | 主机 | 一个不带 FCS 的 802.11 帧（`esp_wifi_80211_tx`）；用于广播 |
| `0x0A` SNIFF | 主机 | u8 信道、6 MAC；发往或来自它的每个管理与数据帧，以及该信道上的每个动作帧（LDN 广播会给主机端要迁去的网络提供密钥）都完整地以 RX_SNIFF 送出；MAC 为 ff:ff:ff:ff:ff:ff 时，该信道上的每一帧都以 RX_CENSUS 送出 |
| `0x0B` STATUS | 主机 | 无；由 STATUS 应答 |
| `0x0C` BENCH | 主机 | u32 字节数、u16 消息大小（8 到 1600）；先 RESULT，然后以 UART 能承受的最快速度发 BENCH 消息 |
| `0x0D` LED | 主机 | u8 图案、u8 峰值亮度、u16 周期毫秒（0 为图案默认值）、u16 持续时间毫秒（0 为到下一次 LED 为止）；RESULT |
| `0x0E` DISPLAY | 主机 | 一条屏幕命令（[屏幕](#the-screen)）；没有屏幕时 RESULT 为 `0x105` |
| `0x0F` ALIVE | 主机 | 无，不回复；武装[主机看门狗](#the-host-watchdog)；只发给 1.4.0 及以后的固件 |
| `0x10` BEACON | 主机 | u8 操作：0 WRITE，把 u32 偏移与字节写入暂存缓冲区；1 COMMIT，u16 长度（校验并保存暂存的镜像）；2 ERASE；3 START；4 QUERY（由 BEACON 应答）；其余操作回 RESULT。固件 1.8.0 及以后（[便携信标](#portable-beacon)） |
| `0x81` INFO | 板子 | u8 协议版本（1）、6 station MAC、6 AP MAC、u8 芯片版本、文本 |
| `0x82` RESULT | 板子 | u8 命令、i32 `esp_err_t` |
| `0x83` LOG | 板子 | 文本 |
| `0x84` RX_MGMT | 板子 | u8 信道、i8 RSSI、一个不带 FCS 的帧：LDN 动作帧；主持期间还包括发往板子 BSSID 的管理帧、发往它的数据帧的前 40 字节，以及某个 station 完整的无 DS 位广播 |
| `0x85` RX_ETH | 板子 | 驱动解密后的一个以太网帧 |
| `0x86` LINK | 板子 | u8 是否建立、u16 原因、6 MAC；原因 `0xFFFF` 为 15 秒内未关联，`0xFFFE` 为密钥被拒 |
| `0x87` STA_JOINED | 板子 | 6 MAC、u8 AID、i8 密钥安装结果、u8 端口是否打开 |
| `0x88` STA_LEFT | 板子 | 6 MAC、u16 原因 |
| `0x89` STATUS | 板子 | 文本形式的计数器（见下）；主持期间每 2 秒主动发送一次，写跟踪记录的主机则每 5 秒轮询一次 |
| `0x8A` BENCH | 板子 | u32 序号与载荷字节；最后一个携带序号 `0xFFFFFFFF` 以及板子花掉的微秒数 u32 |
| `0x8B` CREDIT | 板子 | u32 自上次 HELLO 以来读取并处理的主机字节数，从其分隔符之后的字节算起；在 HELLO 时、每 1024 字节、线路转为空闲时，以及空闲期间每 100 ms 发送，优先于任何排队的消息 |
| `0x8C` RX_SNIFF | 板子 | u8 信道、i8 RSSI、u8 `sig_mode`（0 为 legacy，1 为 HT）、u8 legacy 速率码（`wifi_phy_rate_t`）、u8 HT MCS（位 7 表示 40 MHz）、一个不带 FCS 的帧；该信道上的每个 10 字节 ACK 也会送出 |
| `0x8D` TX_DONE | 板子 | 驱动对某一帧（station 或接入点）的 TX-done：u32 板子时间 µs、u32 距它所完成的 ETH_TX 的 µs（没有则为全 1）、u8 是否被对端射频确认、u8 接口、u16 长度、该帧的前 24 字节（即其 802.11 头） |
| `0x8E` BUTTON | 板子 | 一次 BOOT 按下，30 ms 去抖：u32 板子时间 µs、u16 自启动以来的按下次数；主机会打印 `BOOT button, mark N`，跟踪记录也会保留 |
| `0x8F` RX_CENSUS | 板子 | 收到的每一帧，包括 FCS 失败的帧与控制帧：u32 接收时间 µs、i8 RSSI、i8 噪声底、u8 `rx_state`（0 为正常）、u8 数据包类型（0 管理、1 控制、2 数据、3 其他）、u8 `sig_mode`、u8 速率码、u8 MCS（位 7 表示 40 MHz）、含 FCS 的 u16 `sig_len`、该帧的前 16 字节 |
| `0x90` BEACON | 板子 | u8 是否存有镜像、u8 是否正在运行、u8 分片数、u16 镜像长度、u32 镜像 CRC-32（整个镜像的 `zlib.crc32`） |

`rx_state` 为 98 表示双流 HT（MCS 8 到 15），单流 ESP32 从不解出这种帧；65 表示其他调制方式下的损坏帧。

| STATUS 计数器 | 统计内容 |
|---|---|
| `tx_acked`、`tx_unacked` | 驱动的 TX-done 结果 |
| `tx_eth`、`tx_eth_failed`、`tx_eth_retried` | 已发出的 ETH_TX、失败的，以及发现驱动队列已满的调用 |
| `tx_queued_max_us`、`_total_us`、`_n`、`_pending` | 从 ETH_TX 到 TX-done 的耗时，基于匹配上的 TX_DONE |
| `wire_dropped`、`wire_rx_bad` | 被丢弃的板子到主机消息；COBS 或 CRC 失败的主机命令 |
| `uart_fifo_ovf`、`uart_buffer_full`、`uart_overflow` | 128 字节硬件 FIFO 与 16 KB 环形缓冲的溢出，以及两者之和 |
| `uart_frame_err`、`uart_events_full` | 帧、奇偶与 break 事件；UART 事件队列满的 tick（计数器可能少计） |
| `read_max_us`、`write_max_us`、`handler_max_us`、`handler_max_type` | 最长的主机链路读取回合（含 20 ms 超时）、写者等待，以及最长的命令及其类型 |
| `heap_min`、`queue_max`、`refused_heap`、`refused_queue` | 最小空闲堆、最深的发送队列、因堆下限和队列满而被拒绝的消息数 |
| `tx_eth_max_us`、`tx_eth_total_us`、`tx_eth_slow` | `esp_wifi_internal_tx` 中的 ETH_TX（含重试）的最长值、总和，以及超过 5 ms 的次数 |

EtherType 为 `0x88B7` 的帧是 LDN 认证；`esp32_wlan` 把它们转成 LDN 库的 `CustomFrameEvent`。其余以太网帧都进入某个 L2 端口，由 `POKELDN_L2=tap|userspace` 选择：

| 端口 | 位置 | 启动器的套接字 |
|---|---|---|
| `userspace_ip` 栈 | 默认，所有平台 | `userspace_ip.udp_socket` 与 `packet_socket` |
| 以接口命名的内核 TAP | 仅 Linux，`POKELDN_L2=tap` | 内核套接字，`SO_BINDTODEVICE` 与 `AF_PACKET` 保持不变 |
| `MemoryPort` | 测试 | 无 |

创建 TAP 需要 `CAP_NET_ADMIN`。

### 主机看门狗

主机每秒向 1.4.0 及以后的固件发送一次 ALIVE（`esp32.ALIVE_EVERY`）。HELLO 之后的第一个 ALIVE 会武装看门狗；HELLO 会解除武装，因此从不发 ALIVE 的主机永远不会被监视。武装后，不在空闲状态的板子若 5 秒（`HOST_SILENT_US`）没读到主机命令，就执行 STOP 的拆除流程：接入点停止发信标、其 station 掉线，station 断开。随后它会丢弃所有发给主机的消息且不计数，直到主机再次发来命令；否则每条排队消息都要付出一次 500 ms 写入、一次 `wire_dropped`，以及 LED 上常亮的 `flash3`。在火红交换房间里杀掉主机进程时，主机端会显示 2318-0006，之后搜索 JOIN 也列不出任何主机。

## 便携信标

从固件 1.8.0 起，板子把一轮 LDN 广播存放在 NVS 中，并可在没有主机的情况下发送。保存了镜像且上电后 3 秒内没有主机命令时，它会启动镜像里的接入点、回放最多四条屏幕命令，并每隔 `interval_ms`（100）发送一条广播，每隔 `dwell_ms`（500）切换到下一个分片。HELLO、CHANNEL、SNIFF、STA_JOIN、STOP 与 AP_START 都会终止它；若主机被看门狗判定为消失，它则继续运行。`pokeldn.ldn.portable` 根据 `ldn.create_network` 会创建的网络构建镜像；`bin/swsh_gift_host.py --save-to-board` 会存下一份剑与盾的神秘礼物（[剑与盾神秘礼物](swsh_gift.md)）。

板子按主机的方式构建每一帧（`firmware/esp32/main/advert.c`，PSA SHA-256、AES-CTR 与 AES-GCM）：存下的头部、该分片的载荷，以及一个每次启动都从随机值开始、每个分片加一的 nonce，与 `set_application_data` 在主机上递增它的方式一致。`tests/test_esp32_beacon.py` 编译 `advert.c`，并针对协议 1 和 3 把它的帧与 LDN 库的帧逐字节比对。

| 偏移 | 大小 | 字段（小端） |
|---|---|---|
| 0 | 4 | `PKSA` |
| 4 | 1 | 布局，1 |
| 5 | 1 | 种类，1（一轮广播） |
| 6 | 2 | 镜像长度，含 CRC |
| 8 | 1 | 信道 |
| 9 | 6 | BSSID |
| 15 | 32 | SSID，与 AP_START 接受的形式相同 |
| 47 | 16 | 数据密钥 |
| 63 | 1 | 最大 station 数 |
| 64 | 16 | 广播密钥 |
| 80 | 40 | 广播头：network id、版本、格式、u16 大端长度、u32 大端 nonce |
| 120 | 2 | `interval_ms`，20 到 1000 |
| 122 | 2 | `dwell_ms`，不小于 `interval_ms` |
| 124 | 1 | 分片数，1 到 8 |
| 125 | 1 | 屏幕命令数，0 到 4 |
| 126 | 2 | 零 |
| 128 | | 每个分片：u16 长度与该广播的明文；每条屏幕命令：u16 长度与一个 DISPLAY 载荷 |
| end | 4 | 此前所有内容的 `zlib.crc32` |

镜像里只有为它那一个网络派生出的广播密钥与数据密钥，绝不含 `prod.keys`。一个镜像最多 12288 字节。一块固件 1.9.1 的 XIAO ESP32S3 在上电后独立工作，向一台零售剑送出了一只剑的神秘礼物宝可梦。从固件 1.9.1 起，板子应答第一条命令之前就会从 NVS 读取存下的镜像；1.9.0 会对端口刚打开时发来的 BEACON QUERY 回答「未保存」。板子留在电脑 USB 上但没开应用时，会和接在充电器上一样启动信标。

### 主机镜像

从固件 1.9.0 起，种类 2 的镜像让板子自己应答每台主机端的加入，并播放 `bin/frlg_mg_host.py` 所播放的会话，因此火红或叶绿只凭板子就能收到神秘礼物。`bin/frlg_mg_host.py --save-to-board`（应用里的「保存在板子上」）会存下一份；`pokeldn.frlg.gift.portable` 通过构造启动器本会运行的主机应用、并保留该主机在主机端加入前算出的内容来构建它。神秘卡片、神秘新闻、印章收集的印章、来访训练家和神秘事件脚本占 2 到 4 KB；缓冲脚本与存档备份/恢复要在电脑上读取答案，会被拒绝。

种类 2 没有分片（第 124 字节为 0），只有 AES-GCM 头。屏幕命令之后直到 CRC 是若干记录，每条为 u8 标签、u16 长度与字节（`firmware/esp32/main/gift.h`）：

| 标签 | 记录 | 写入者 |
|---|---|---|
| 1 | LDN：广播明文，直到并包含主机的 48 字节 station 条目；认证头的 network id（小端）；用于解出认证密钥的 16 字节密钥；32 字节 challenge key；u64 challenge；u64 device id；版本；平台 | `pokeldn.ldn.portable.ldn_record` |
| 2 | Pia：会话密钥 `AES(game key, SSID)`、u32 network id、主机的 IPv4 地址、玩家 id 与名字 | `portable.pia_record` |
| 16、17 | 主机 LinkPlayer 块之前与之后的应用数据 | `pokeldn.frlg.gift.portable` |
| 18 | 主机 200 字节的 LinkPlayer 块与 RFU parent id | |
| 19 | `MysteryGiftTiming` 的八个字段、标志（1 原生 nonce，2 先发加入响应，4 信任 Pia）、u32 协议 tick µs | |
| 20 | 游戏家族（0 火红/叶绿，1 绿宝石）、期望的主机端（0 任意） | |
| 21 | 编译成字节码的服务器脚本：每个 `SVR_LOAD_*` 变成一个槽位 | |
| 22 | 一个载荷：u8 标识、u16 大小（0 表示 1024 字节缓冲区）、字节；每个不同消息一条 | |
| 23 | 一份提供的卡带：游戏代码（四个零表示任意）、卡片标志 id、图标、印章字段、每个槽位一个载荷 | |

认证密钥是 `AES-ECB-decrypt(K, SHA-256(client random)[:16])`，其中 `K` 是 `KeyDerivation._derive_key` 针对源 `f1e7018419a84f711da714c2cf919c9c` 的第三步，一个为 LDN 协议 3 派生出的密钥。除最后一条外，每条屏幕命令都在启动时播放；最后一条是递送场景，在一次成功递送的会话之后播放，随后再放启动的那几条。

引擎是纯 C，逐层逐行移植了对应的 Python 模块：

| 文件 | 移植自 |
|---|---|
| `gift_ldn.c` | `ldn.APNetwork` 的认证与 challenge 应答、station 加入时的广播、`userspace_ip` 的 ARP 与 IPv4/UDP、`host_app.py` 的运行循环 |
| `gift_pia.c` | `crypto.PiaCrypto`、`reliable.parse_messages`、`pia_connect` 的 Net、Session 与 RTT 编解码、`host_pia.HostPeerProtocol` |
| `gift_link.c` | `reliable.HostReliableSession`、`ni.py`、`rfu_leader.RFULeader`、`host_session.HostSession` |
| `gift_mg.c` | `host_mystery_gift.HostMysteryGiftEngine`、`block.BlockSender` 与 `RecvBlock`、`mg_link`、服务器脚本 |
| `gift_zstd.c` | zstd 1.5.7 的解码器（`vendor/zstd`） |

信标任务运行它：驱动的帧与关联通过一个队列到达它，它按自己返回的截止时间运行定时器，并每隔 `interval_ms` 重建广播，每次变化把 nonce 加一。station 的广播（首先是它对主机的 ARP）不带 DS 位、用组密钥发出，接入点会丢弃它们：引擎从混杂回调中整帧取走并自行解密，用 LDN 库的 nonce 与 AAD 做 AES-CCM、8 字节 MIC，无论是否带 QoS（[station 的广播](ldn.md#a-stations-broadcasts)）。零售 ESP32-S3 会把它们以已用当前组密钥解密的形式交上来，Protected 位、CCMP 头与 MIC 都还在（一个火红 ARP 是 76 字节）；从固件 1.9.1 起，CCMP 头之后以 SNAP 头开头的帧体被视为明文，与主机的 `accept_decrypted_ccmp` 一样。固件 1.9.0 会丢弃它们，主机端在认证之后以通信错误退出。主机端会压缩它的大部分数据报（一次神秘卡片会话中 1363 个里有 1056 个）；解码器上下文为 38,464 字节，外加 1 KB 字面量缓冲。主机压缩过的数据报以单原始块的 zstd 帧发出。引擎状态约 41 KB，启动时连同解码器一起从堆上取。

板子一次只接纳一台主机端，对另一台的认证以状态 1 拒绝。若某台主机端的游戏代码没有任何卡带记录指名，或脚本拒绝了它的游戏数据，它会在游戏数据请求之后被断开，不再发送任何内容。已接纳的主机端静默 60 秒，或在 RFU 关闭后仍被接纳 30 秒，都会被断开。主机端离开时，在它确认关闭后等 2 秒稳定，板子便在同一网络与密钥上服务下一台。

`tests/test_esp32_gift.py` 编译引擎与 zstd，让它在模拟板子上对位扮演主机端的 `bin/frlg_mg_client.py` 运行；后者像零售火红那样用 ARP 解析主机，并以自己的 Session 类型 6 打开 Reliable 流，其广播由 LDN 库加密、不带 DS 位到达板子。神秘卡片、已持有的卡片、被拒绝的替换、一枚印章和神秘新闻，各自都以 `MysteryGiftServer` 对该主机端发送的消息收尾，逐字节一致；第一台之后会服务第二台；镜像不提供的卡带会被拒绝。一块固件 1.9.1 的 XIAO ESP32S3 在无主机供电的情况下，向一台零售法文火红递送了一张神秘卡片，并向已持有该卡的主机端又服务了一次。

## 串口上限

经典 ESP32 的 UART 在 921600 波特率下从板子到主机承载 92.16 KB/s；Pia 载荷是密文，无法压缩。除非设置 AP 标志 4（`POKELDN_ESP32_AP_FLAGS=4`），主持中的板子还会为每个 station 数据帧发送一份 48 字节的 RX_MGMT 副本；附近每个 LDN 网络每秒大约增加十条广播。

发送队列可容纳 384 条消息，并在空闲堆低于 64 KB 时拒绝新消息；当主机端以线路速率灌入时，堆下限会先于队列满而拒绝 RX_ETH。

### 波特率

`POKELDN_ESP32_BAUD` 设定 `open_serial` 切换到的速率，默认 921600；上限由 USB 桥决定。在 macOS 上，ELEGOO 板子的 CP2102 以 1500000 承载 149.1 KB/s 且无丢失，而 2000000 和 3000000 从不应答 HELLO。`tools/ldn/esp32_bench.py --port PORT --bauds LIST` 会按每个速率流式跑 BENCH。

### 主机到板子的命令丢失与 CREDIT

在主机端的洪流下，板子可能在处理函数之前就丢掉主机命令。固件的对策如下，每一条都与其缺失时做过对比测量：

| 原因 | 固件的做法 |
|---|---|
| UART 中断在核心 0，与 Wi-Fi 任务同核 | 从读取任务安装驱动，核心 1 |
| 一次阻塞的 ETH_TX 会让 16 KB 环形缓冲和 128 字节 FIFO 溢出 | CREDIT 流控 |
| FIFO 在 120 字节时就读取，1500000 下距满只有 53 µs | 阈值 32（`uart_set_rx_full_threshold`），640 µs |
| `uart_read_bytes`（IDF 6.1 `uart.c:1738`）对每个环形缓冲项都要等满超时 | 先等一个字节，再取 `uart_get_buffered_data_len` |
| `uart_write_bytes` 在 TX 环满时忙等，饿死读取者 | 写者睡到该帧能放下为止（`uart_get_tx_buffer_free_size`） |
| `UART_DATA` 事件塞满承载溢出事件的 64 项队列 | 一个优先级高于读取者的任务每个 tick 排空它；`uart_events_full` |

板子发出一次 CREDIT 之后，主机的写线程会把「已写但未上报」的字节控制在 8 KB 以内（`esp32.FLOW_WINDOW`）；启动器的 trio 循环只做排队，超过 512 个排队帧后的 ETH_TX 与 RAW_TX 会被丢弃（`Radio.tx_dropped`）。窗口关闭期间计数连续 0.3 秒不变，说明有字节丢失，主机会重新打开窗口（`Radio.flow_resyncs`）。绝不要仅凭沉默就重同步：繁忙的读取者可能压住 0.7 秒，此时重同步会在 16 KB 环形缓冲上塞进 16 KB 在途数据。板子每 1024 字节给一次 credit（`wire.c` 的 `CREDIT_STEP`），因此主机把 CREDIT 对应到已写字节加上线上的那一帧。没有 CREDIT 的板子会被无节流地写。板子会记录超过 50 ms 的命令（`slow command`）和超过 100 ms 的读取回合（`reader held`）。

HELLO 会重置两边的计数，因此主机会等到没有在途数据才发它，并让窗口保持关闭，直到板子发来 CREDIT 0（`tests/test_esp32.py::test_a_hello_mid_session_does_not_open_the_window`）。`tools/ldn/esp32_cmd_loss.py TRACE` 会对账一份跟踪记录：已写的 ETH_TX 对 `tx_eth + tx_eth_failed`，自 HELLO 以来已写的字节对最后一次 CREDIT。

### 发送时序

ETH_TX 在驱动里花约 0.1 ms，等待 TX-done 的中位数约 1 ms。在洪流下，TX_DONE 到达主机最多晚 0.6 秒。陷阱：嗅探板子自己的线路会成串积压，因此要用对端的确认来计时递送；接入点的洪流以 1 Mbit/s 广播，超过约每秒 90 帧就会占满空口。

## 停顿与接收遗漏

在火红交换中让板子充当接入点时，一帧通常约 1 ms 完成；偶尔会有一帧未被主机端确认，卡住 100 到 260 ms，而它后面的帧成串完成，板子既听不到主机端的数据，也听不到它的 ACK。是否卡住由信道决定：在与繁忙接入点共用的信道上，大多数交换都会卡；在信道 11 上一次也没有。`config/host.local.toml` 可以设 `[host] channel`；主机端只在 1、6 或 11 上加入主机。240 MHz 的 CPU 与固定速率（AP 标志位 3..5：1 到 7 对应 1、11、6、12、24、36、54 Mbit/s）都不能消除卡顿。`tools/ldn/esp32_hold.py CAPTURE TRACE` 把每次等待拆成阶段，`tools/ldn/esp32_hold_air.py` 列出嗅探器看到的内容，`tools/ldn/esp32_rx_copies.py` 把主机端的重试与板子的接收遗漏对应起来。

### 两块板子上的接收遗漏

作为接入点时，板子会漏掉 station 的 OFDM 首份拷贝的 1% 到 22%；1 Mbit/s 的 DSSS 几乎从不漏。`tools/ldn/esp32_pair_bench.py AP STA --flood 0 --burst N --send R` 会统计这些。遗漏集中在紧跟板子自身发送之后的帧上，例如它发出 6 Mbit/s 的 CTS 后 60 µs 的数据帧。在安静信道上（3 到 9 上为 0.8% 到 2.3%）、每个 station 帧前都发 RTS（STA_JOIN 标志 1）、以及 station 满功率时，遗漏更少。

信标间隔、混杂接收、噪声底检查、接收缓冲、CPU 频率、IRAM 优化、接入点功率，以及 ESP-IDF v5.5.5 对 v6.1，都没有带来变化。大多数遗漏在接入点侧不留任何痕迹，甚至连 FCS 失败都没有。

station 的每次重试都在 RTS 之后发出（`lmacConfMib` +42，阈值在 +22；`esp_wifi_internal_get_rts`/`_set_rts`）。`lmacRetryTxFrame` 按 `lmacConfMib` 的上限重发（短重试 +21、长重试 +20，默认 32；`esp_wifi_internal_set_retry_counter`）。ACK 与 CTS 的速率表位于 `0x3ff73400`..`0x3ff7341c`。

## 用户态协议栈

`pokeldn.ldn.userspace_ip` 在主机进程内实现 IPv4、UDP 与 ARP。协议栈按接口名注册（加入方为 `ldnclient`，接入点为 `ldn-tap`）；对内核接口，`userspace_ip.lookup(name)` 返回 None，启动器正是据此选择路径。地址与邻居来自 LDN 库的 `add_address`、`add_neighbor` 以及收到的帧；没有邻居的单播目的地会先发 ARP 请求并丢弃该数据报；`.255` 走广播。超过 1472 字节的数据报会被分片，分片重组超时 5 秒。`udp_socket(port)` 与 `packet_socket()` 分别顶替绑定的 UDP 套接字与 `AF_PACKET` 套接字，各自背后是一个套接字对、每个排队数据报一字节，因此 `select` 与 `trio.lowlevel.wait_readable` 在所有平台上都能用。

陷阱：板子的帧通过启动器自身 trio 循环里的 trio 任务到达协议栈。绝不要在该循环里阻塞于 `select`；要在 `trio.move_on_after` 下用 `trio.lowlevel.wait_readable` 等待。

## 板子的 LED 与按键

经典 ESP32 上 LED 是 GPIO2，S3 上是反相的 GPIO21，C6 上是反相的 GPIO15；C3 固件不碰 LED 引脚。经典 ESP32 和 S3 上 BOOT 是 GPIO0，C3 和 C6 上是 GPIO9；每次按下都会发送 BUTTON（`0x8E`）、闪一下 LED 并唤醒屏幕。在 ELEGOO ESP-32 Type-C 板（CP2102、ESP32-D0WD-V3、无标的 PCB 天线模块）上，红色 LED 是电源轨，蓝色的是 GPIO2。GPIO2 和 GPIO0 是 strapping 引脚；固件只在启动之后才驱动 GPIO2。

LED 以 LEDC PWM（13 位、5 kHz）每 10 ms 更新，gamma 2.2，150 ms 交叉渐变。

| 图案 | id | 默认周期 | 形状 |
|---|---|---|---|
| auto | 0 | | 当前模式的外观，见下 |
| off、on | 1、2 | | |
| breathe | 3 | 3000 ms | 升余弦 |
| blink | 4 | 1000 ms | 半个周期内亮 |
| flash3 | 5 | 1000 ms | 周期的前 60 % 内闪三下 |
| ramp-up、ramp-down、pulse | 6、7、8 | 1000、1000、1200 ms | 只执行一次 |

自动外观：启动时一次脉冲，空闲时 4 秒的暗呼吸，加入中 250 ms 闪烁，主持且无 station 时更亮的 1.5 秒呼吸，已连接时保持暗亮，嗅探时熄灭。

在此之上，每一帧都会让 LED 闪一下。加入失败、密钥被拒、板子到主机的消息被丢弃，或主机命令丢失，都会播放 1.5 秒的 flash3。完成一次交换或神秘礼物会渐亮到最亮（`pokeldn.ldn.show_done`）。`tools/ldn/esp32_led.py --port PORT PATTERN` 可设定外观；`--demo` 逐个演示。

## 屏幕

I2C 上的 SSD1306 128x64 OLED 是可选的（SSD1315 与 SSD1309 模块也可用）。固件先探测 0x3C，再探测 0x3D；有屏幕时以 400 kHz 每 50 ms 画一帧。

| 目标 | SDA | SCL | 板子引脚 |
|---|---|---|---|
| ESP32 | GPIO21 | GPIO22 | DevKit V1 D21、D22 |
| ESP32-S3 | GPIO8 | GPIO9 | |
| ESP32-C3 | GPIO6 | GPIO7 | XIAO D4、D5 |
| ESP32-C3 | GPIO5 | GPIO6 | 0.42 英寸 OLED 板自带的 72x40 屏幕，第二个探测 |
| ESP32-C6 | GPIO22 | GPIO23 | XIAO D4、D5 |

常见的四针模块自带稳压与上拉；它的地址电阻选择 0x3C（丝印 0x78）或 0x3D（0x7A）。固件设置段重映射（`A1`）、反向 COM 扫描（`C8`）与备用 COM 引脚（`DA 12`）。ESP32-C3 的 0.42 英寸 OLED 板上 72x40 面板显示帧的第 30..101 列与第 24..63 行；这些引脚上的屏幕会得到紧凑场景（一行 12 个字符、半尺寸精灵），可由 `tools/ldn/screen_preview.py --panel 72x40` 离线渲染。

没有主机命令时，屏幕显示无线模块的状态：空闲、加入中或主持中，以及是否已连接，并统计各方向的帧数。无线模块活动或有动画播放时，它保持最亮；最后一次 DISPLAY、HELLO 或 BOOT 按下后也保持 60 秒；然后它变暗到对比度 1、预充电 `22`（`81 01 D9 22`），600 秒后关闭（`AE`）。预充电更低会闪烁。空闲画面每 60 秒平移 2 像素以防烧屏。`tests/test_esp32_screen.py` 固化了这些时序。

DISPLAY（`0x0E`）携带一个操作：

| 操作 | 布局 |
|---|---|
| `0` SHOW | u8 显示编号、u16 保持秒数（0 为直到下一次显示）、标题、NUL、一行文字、NUL；每段文字最多 21 个 ASCII 字符 |
| `1` SPRITE | u8 槽位（0 我方，1 对方，2 礼物）、u8 宽 ≤ 64、u8 高 ≤ 64、每行 `(width + 7) / 8` 字节，MSB 在前；宽为 0 清空该槽 |
| `2` LOBBY | u8 星数（0..7，0 为无）、u8 已加入人数、u8 座位数（1..3，至少等于已加入人数）、标题、NUL、名字、NUL、连接密码、NUL；启动联盟室画面 |
| `3` JOINED | u8 已加入人数，最多为联盟室的座位数；没有联盟室画面时被拒 |

| 画面 | id | 内容 |
|---|---|---|
| auto | 0 | 无线模块的状态 |
| trade | 1 | 槽位 0 带「offering」与那行文字 |
| traded | 2 | 槽位 0 乘球离开（2.1 秒），数据包来回直到保持时间，一个球到达并打开（1.6 秒），然后槽位 1 显示「received」10 秒 |
| gift | 3 | 一张持着槽位 2 的神秘卡片 |
| gifted | 4 | 卡片离开，然后「delivered!」 |
| arrived | 5 | 仍在等待的 traded 画面现在把球带进来 |
| lobby | LOBBY | 槽位 0、标题、名字、星数、「joined/seats」与密码 |

一个画面会等待正在播放的 traded 或 gifted 画面；无线模块回到空闲时画面结束。

`pokeldn.app.screen` 是启动器一侧：`offer`、`received`、`arrived`、`gift`、`delivered`、`lobby` 和 `joined` 立即返回，并在单个线程上按顺序执行。主持团体战时会亮出联盟室。每个启动器都在交换的最后一步调用 `received`，保持时间取下表时间减去 2.5 秒，好让球与主机端的球同时打开：

| 作品 | 起点 | 主机端收到宝可梦 | 动画后的第一条消息 |
|---|---|---|---|
| 火红/叶绿 | START_TRADE | 22.7 秒 | READY_FINISH_TRADE（[火红的连接](frlg_link.md)） |
| Let's Go | 步骤 `0e` | 15.3 秒 | 类型 4 载荷（[Let's Go 会话](lgpe_session.md#the-trade-animation)） |
| 剑/盾 | 最后一个 syncCommand 40 | 15.0 秒 | 无（[剑的交换](swsh_trade.md#the-trade-animation)） |
| 晶灿钻石/明亮珍珠 | `tradeState` 5 | 18.6 秒 | 无（[BDSP 交换](bdsp_trade.md#the-completed-trade)） |
| 传说 阿尔宙斯 | `01 0e` | 28.5 秒 | 盒子消息 `00 02`（[传说 阿尔宙斯](pla.md#the-completed-trade)） |
| 朱/紫 | `8001010e` | 19.8 秒 | 无（[朱与紫](sv.md#the-trade)） |
| 传说 Z-A | 第四步 | 26.2 秒 | 下一条 `01 01` 预览（[传说 Z-A](za.md#a-trade-with-a-retail-console)） |

这些时间点是手工标记的（最多晚 2 秒）。启动器在动画之后的那条消息处调用 `arrived`。精灵图取自 PokeAPI 的火红/叶绿版本，种族值 386 以内用这些，之后用默认图；裁切、缩放到最多 64（卡片上为 40），并二值化到一位，内部线条保持深色。`tools/ldn/esp32_screen.py --port PORT` 在板子上播放一次交换和一次礼物；`tools/ldn/screen_preview.py OUT.gif` 离线渲染一段脚本化会话。

### E32R40T 板

E32R40T（以 4.0 英寸 ESP32-32E 显示屏的名义出售）是一块经典 ESP32，带 SPI 上的 480x320 ST7796S 面板。它的固件是单独的构建，在 `idf.py` 的环境里设 `POKELDN_DISPLAY=E32R40T`（默认为 `OLED`）；发布镜像是 OLED 构建。

| 信号 | GPIO |
|---|---|
| CS、DC、SCK、MOSI | 15、2、14、13 |
| 背光，高电平点亮 | 27 |
| RGB LED，低电平点亮：红、绿、蓝 | 22、16、17 |

面板以 3 倍（384x192）显示 128x64 的帧，白底黑字，SPI 40 MHz。GPIO2 是面板的 DC，因此板子的 LED 是 GPIO17 上的蓝色那颗。OLED 该熄灭时背光也关掉。

## 构建与刷写

固件版本（`firmware/esp32/version.txt`，`major.minor.patch`，所有目标共用）在 INFO 中以 `version=...` 报告；没有版本号的构建显示 `version unknown`，只要串口协议匹配就能工作。协议号是另一回事，只在线上协议变化时才变。

ESP-IDF v6.1（标签 `v6.1`，提交 `fff9895c82d744c7237be8847347bdd1b07c6643`）可构建全部四个目标。用 `install.sh esp32,esp32s3,esp32c3,esp32c6` 安装其工具，然后激活 IDF 环境。

    cd firmware/esp32
    idf.py set-target esp32   # esp32s3, esp32c3 or esp32c6 for those chips
    idf.py build
    idf.py -p <port> flash

控制台输出关闭；在经典 ESP32 上，固件自己指定 UART0 的 GPIO1 与 GPIO3（`uart_set_pin`）。桌面应用用 esptool 检测芯片，并在写入前按芯片的 flash 偏移（ESP32 为 `0x1000`，其他为 `0x0`）校验合并镜像的引导加载器：esptool 5.4.0 的 `write_flash` 在镜像以填充开头时可能跳过芯片检查。绝不要根据 USB 桥的 ID 来选择固件。esptool 根据端口的 USB id 决定复位方式，而 esp-pylib 1.1.5 拒绝对 Android 的 `android://board` 这类 URL 端口做该查询；拿不到 id 时，它给 ESP32-S3、C3 或 C6 用经典的 DTR/RTS 复位，芯片永远进不了 ROM 加载器，日志显示 `Failed to get VID/PID`。Android 应用用板子自身的 USB id 回答该查询（`pokeldn/app/android.py`）。id 已知时，Linux 或 Android 上的 CP210x 板子会得到同时写 DTR 与 RTS 的复位，通过端口 `fileno()` 上的 `ioctl` 完成；Android 端没有文件描述符，改为在一次 CDC `SET_CONTROL_LINE_STATE` 里同时送出两条线。[桌面构建](gui.md) 介绍四个镜像的打包。

### 蓝牙

以 `POKELDN_BLE=1` 构建时，还会通过蓝牙 LE 承载主机链路，供打不开 USB 串口设备的 iOS 应用使用；此时板子的 USB 只用来供电。

    POKELDN_BLE=1 idf.py -B ../../scratchpad/esp/build-ble \
        -D SDKCONFIG=../../scratchpad/esp/build-ble/sdkconfig \
        -D SDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.defaults.ble" build

板子只广播自己的名字 `POKELDN-RADIO`；iOS 应用扫描时不带服务过滤。服务为 `7a1e0101-5d2c-4c3e-9f4b-504f4b454c44`：主机把 COBS 流写到 `...0102`（无响应写），板子在 `...0103` 上通知。当某个中心设备订阅了 `...0103`，线路就走那里，线缆随之静默。分帧、CRC 与 CREDIT 不变。HELLO 文本以 `link=ble` 结尾，设备页会把它显示为蓝牙无线固件。`POKELDN_RADIO=esp32:ble`（或 `esp32:ble:NAME`）可从任意启动器打开它（`pokeldn/ldn/esp32_ble.py`，bleak）。

BLE 构建使用仅 BLE 的控制器、10 个静态 Wi-Fi 接收缓冲和 10 KB 接收缓冲，并释放经典蓝牙的内存：双模控制器会让空闲堆低于线上协议的 64 KB 下限。走 BLE 时板子不发 TX_DONE，并把排队帧合并成一次通知。它请求 15 ms 间隔（中心设备订阅后再请求一次；STATUS 中的 `ble_itvl_us`）、2M PHY、247 字节 MTU 与数据长度扩展；间隔为 30 ms 时火红的房间会慢得像爬。

经典 ESP32（蓝牙 4.2，无 2M PHY）实测 28.1 KB/s，能完成火红的主持方交换，但作为火红加入方太慢（2318-0013）。XIAO ESP32C6 实测 33.6 KB/s，能完成火红的加入方交换。每个无线固件构建都采用 ESP-IDF 的 single-app-large 分区表（0x10000 处 1500 KB 的 factory 应用；nvs 仍在 0x9000，phy_init 仍在 0xf000）；C6 的 BLE 镜像（0xfd000 字节）在其中还剩 488 KB。

在 macOS 上，若进程的负责应用没有蓝牙授权，bleak 会中止（SIGABRT）；用 `open -n -a Terminal FILE.command` 启动的脚本则运行在 Terminal 的授权之下。

### USB 主机链路

S3、C3 与 C6 在 USB Serial/JTAG 上使用同一套 COBS、CRC 与 CREDIT 协议，环形缓冲为 16 KB。被拒绝的 `usb_serial_jtag_write_bytes` 会每 20 ms 重试，500 ms 后计为一条丢弃消息。接收中断在 RX 环满时丢弃一个 64 字节包且不计数（`usb_serial_jtag.c:144`）；CREDIT 使环不被打满。这条路径上 UART 计数器保持为零，`POKELDN_ESP32_BAUD` 只改变经典 ESP32 的速率。在 USB 目标上，读取者以优先级 21 运行，高于写者（20）：低于它时，写者会在满速流下饿死读取者。

主机设置 1 秒写超时；写失败或写入不足会把会话按板子丢失结束。HELLO 之后，1 秒没有有效帧会排入一次 STATUS 探测，3 秒静默则以 USB 错误结束会话，并请用户重新插拔板子。

没有主机端参与、持续两小时的主机到板子浸泡测试（只用一个波特率值；原生 USB 会忽略它）：

```sh
./.venv/bin/python tools/ldn/esp32_bench.py --port COM5 --bauds 921600 \
    --soak 7200 --size 1400 --rate 460000
```

它每 5 秒打印帧数、字节数、credit 与 STATUS，并在 USB 失败或帧数不匹配时以非零码退出。它既不重现主机端的确认，也不重现其 Wi-Fi 负载。

## 运行

`POKELDN_RADIO=esp32:<port>` 让每个启动器的 `ldn` 调用都走板子。`esp32:auto` 取唯一存在的 USB 串口，有多个时拒绝选择，因为打开端口可能复位对应板子。端口每个进程只打开一次，且释放 DTR 与 RTS；macOS 上的 CP2102 板子无论如何都会在打开时复位。没有复位的板子会保留上一次的 `BAUD`，因此主机会依次在 115200、`POKELDN_ESP32_BAUD`、921600 和 1500000 下尝试 HELLO，然后再切到请求的速率。在 Windows 上 COM 口是独占打开的（`PermissionError(13, 'Access is denied.')`），因此启动器会在重试前先关闭静默板子的端口；运行中拔掉板子会以 `[esp32] The board disconnected from USB` 结束。对 CP2102 来说，只拉低 RTS 就会把 EN 拉低，板子保持静默。处于 ROM 下载模式的板子从不应答 HELLO。

走板子时，启动器跳过所有 nl80211 步骤（`--phy auto` 解析为 `esp32`），不需要 root，也不注入信标；加入方的 `--mac` 会成为板子 station 的地址。在 5 GHz 上主持的 Switch 主机无法触及。

`POKELDN_ESP32_TRACE=FILE` 会把每条串口消息追加一行：Unix 时间、`>`（主机）或 `<`（板子）、类型与十六进制载荷。

`tools/ldn/esp32_first_contact.py` 检查一块新板子（`--flash` 会写入构建，然后依次做 HELLO、STATUS、统计各信道 LDN 动作帧的空闲扫描，带 `--keys` 时再做一次解密扫描）；`tools/ldn/esp32_sniff.py` 把第二块板子当嗅探器；`tests/test_esp32.py` 在两块模拟板子上运行 LDN 主机与 station（`pokeldn.ldn.esp32_sim`）。CH9102 或 CH343 桥会枚举为 CDC ACM（`/dev/ttyACM0`、`/dev/cu.usbmodem*`）。

### 解不出 OFDM 的板子

Switch 主机端的广播是 HT MCS 3（[发现](ldn.md#discovery)），因此解不出 OFDM 的板子听不到任何广播：`esp32_first_contact.py` 在每个信道上统计到 0 个 LDN 动作帧，而关联与 ping 在 DSSS 下仍然正常。把 `tools/ldn/esp32_census.py` 放在繁忙接入点旁边就能区分：正常的板子会列出 `OFDM` 与 `HT` 的正常帧，聋的板子只有 `DSSS`，OFDM 帧在 `rx_state` 65 处失败。一块普通的 ESP32-WROOM-32 DevKit（ESP32-D0WD-V3 rev 3.1，CP2102）就是聋的；同款芯片的 WROOM-32E 板子则正常（[issue 1](https://github.com/Decryptu/pokeldn/issues/1)）。

## 按板子统计的交换

ELEGOO 板（ESP32-D0WD-V3 rev 3.1，CP2102，921600 波特率）在所有作品里都能与零售 Switch 2 主机交换，station 与接入点两种角色都行，并能递送火红和剑的神秘礼物。XIAO ESP32C3、ESP32C6（陶瓷天线）和 ESP32S3 在两种角色下都能完成火红交换，也能完成剑的主持方交换，C6 还能完成朱的主持方交换；Windows 上的 ESP32-S3 能完成火红的加入方交换（[PR 2](https://github.com/Decryptu/pokeldn/pull/2)）。[Android 应用](../examples/android/README.md) 通过 XIAO ESP32C6 主持火红，在其 Python 线程绑定到单个性能核心后达到每秒 51.1 个父级槽位。

加入板子接入点的火红主机端会接受它长度为 0 的隐藏 SSID、速率顺序、能力位 `0x0431` 与 WMM 元素，并发出一条关联请求：listen interval 10、32 个十六进制字符的 SSID、速率 `02 04 0b 16 0c 12 18 24` 与 `30 48 60 6c`、功率能力 `00 14`、RSN 能力 `0x0000`、一个 WMM 信息元素、厂商元素 `00 22 aa 10 01 02`。它最初的广播需要固件转发（[station 的广播](ldn.md#a-stations-broadcasts)）。

### 加入

`STA_JOIN` 做一次关联尝试：在该信道与 BSSID 上快速扫描，然后开放认证并关联；`LINK` 在 0.23 到 0.34 秒后建立。零售剑的网络可能在广播仍能听到的情况下让一次尝试失败（`LINK` 断开，原因 `0xc9` 或 `0x2`），再试一次就能关联，因此主机会最多发送三次 `STA_JOIN`（`pokeldn.ldn.esp32_wlan.JOIN_ATTEMPTS`）。一次尝试为何落空尚不清楚。最后一次被拒之后主机会发 `STOP`：随后扫描的 `CHANNEL` 在板子回到空闲前都会被拒绝。

### 发射功率

`POKELDN_ESP32_TX_POWER` 以 dBm 给板子的发射功率封顶（2 到 20）；主机以 0.25 dBm 为单位，把它作为 `STA_JOIN` 与 `AP_START` 的功率字节发送，桌面应用的设置里「发射功率」也可设置。从固件 1.9.3 起，station 的上限在关联之前就设好；更早的镜像则在 `LINK` 建立后才设。爱好者论坛反映 ESP32-C3 Super Mini 板子只有 8.5 dBm 时才能与接入点关联，这是这些板子的天线缺陷；在 ESP32-C3 的 0.42 英寸 OLED 板上，该效应尚未实测。

没有选功率时（设置为「自动」），由主机决定（`pokeldn.ldn.esp32_wlan.board_tx_power`）：

| 板子 | 功率 |
|---|---|
| HELLO 回复中的芯片名为 `esp32c3` | 两种角色都用 8.5 dBm；Super Mini 与 XIAO ESP32C3 报告相同的芯片与 USB id，因此所有 C3 都用它 |
| 其他 | 驱动的最大值；在 `JOIN_ATTEMPTS` 次加入被拒之后，再以 8.5 dBm 试一次 `STA_JOIN`，若成功关联则本次运行余下时间都用它 |

设置里的「满功率」（20 dBm）可在 C3 上恢复最大值。

### 无线模块测试

桌面应用的设备页「测试无线模块」（`pokeldn.ldn.esp32_radio_test`）无需运行主机端、也不需要第二块板子，就能检查板子的两个方向：

| 阶段 | 板子做什么 | 玩家看到什么 |
|---|---|---|
| 听，约 20 秒 | 在信道 1、6 和 11 上：3 秒空闲，LDN 广播以 `RX_MGMT` 到达主机，然后 3 秒普查（`SNIFF` 到 `ff:ff:ff:ff:ff:ff`） | 每个信道上 Switch 发射端与 Wi-Fi 信标的最佳 RSSI、帧数与损坏数、噪声底中位数 |
| 被听到，60 秒 | 以交换时所用的功率开一个隐藏接入点（`AP_START`），并从它用 `RAW_TX` 每 100 ms 发一个开放的 `POKELDN-TEST` 信标 | 手机的 Wi-Fi 列表里，板子附近是否出现 `POKELDN-TEST` |

在本地游玩菜单里等待主持的 Switch 会在其信道上显示为一台 Switch。听得到 Wi-Fi 却没有 Switch，问题在主机端；什么都听不到，问题在板子的接收端。手机在板子旁边始终列不出 `POKELDN-TEST`，问题在板子的发射端。Mac 的扫描只有在信标带运行时间戳与 TIM 元素时才列出它，而且有些扫描会漏掉；只带 SSID、速率与信道的信标从未被列出。结果会进入设备页的日志，「复制设备详情」会包含它。

## 未解决

- XIAO ESP32C3 是否在自动的 8.5 dBm 下完成交换尚未实测；它是在驱动的最大值下完成交换的（[发射功率](#transmit-power)）。
- softAP 会协商 WMM，而 Switch 主机不协商；带与不带 WMM 交换都能完成（`POKELDN_ESP32_AP_FLAGS=2`，`AP_FLAG_NO_QOS`，清除该 station 的 QoS 标志）。
- 接入点的接收路径中是什么导致漏掉 station 的 OFDM 首份拷贝，尚不清楚（[两块板子上的接收遗漏](#receive-misses-on-two-boards)）。
- ESP32-WROOM-32E 模块是否比 ELEGOO 板上的无标模块漏得更少，尚未实测。有用户报告说较老的 ESP32-WROOM-32 交换不可靠；一块 WROOM-32 DevKit 解不出任何 OFDM（[解不出 OFDM 的板子](#a-board-that-decodes-no-ofdm)）。
- 朱的 Switch 主机加入板子的接入点后，可能确认了通告却不发端口 2 的加入（[朱与紫](sv.md#unresolved)）。
