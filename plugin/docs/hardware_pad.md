---
title: 控制器板
parent: 硬件与设置
nav_order: 5
---

# 控制器板

控制器板是一块 ESP32-S3，Switch 会把它当作插在 USB-C 口上的有线控制器；或者是一块经典 ESP32，通过经典蓝牙配对成 Pro 控制器。主机通过它按下 Switch 主机的按键，并加载宏，由板子按自己的时钟播放。固件为 `firmware/pad`，主机侧为 `pokeldn.pad`，应用页面见[控制器](gui.md#the-controller)，命令行为 `tools/switch/pad.py`。

## 适用板子

| 芯片 | 控制器 | 原因 |
|---|---|---|
| ESP32-S3 | 有线，走 USB | 它的 USB-OTG 模块可以充当任意 USB 设备 |
| 经典 ESP32 | 无线 Pro 控制器，经典蓝牙；主机经其 USB 转串口连接 | 自身没有 USB 设备功能；它有经典蓝牙，也就是 Pro 控制器的传输方式 |
| ESP32-C3、ESP32-C6 | 无 | USB Serial/JTAG 是固定功能，且它们的蓝牙只有 LE |

## USB 一侧

板子会枚举成 HORI Pokken 控制器，`0f0d:0092`，一个 HID 接口，带一个中断 IN 端点和一个中断 OUT 端点。Switch 接受这个 ID 作为普通 HID 手柄，不需要 Pro 控制器握手；固件 23.0.1 的零售 Switch Lite 从 HOME 菜单直接识别，无需改动任何设置。

输入报告为 8 字节，只要主机准备好接收，就每毫秒发送一次：

| 偏移 | 大小 | 字段 |
|---|---|---|
| 0 | 2 | 按键，小端 |
| 2 | 1 | 十字键：0 为上，顺时针到 7 为左上；8 为居中 |
| 3 | 4 | LX、LY、RX、RY；128 为居中，0 为左或上 |
| 7 | 1 | 厂商字节；固件把它的蓝牙状态放在这里 |

| 位 | 按键 | 位 | 按键 |
|---|---|---|---|
| 0x0001 | Y | 0x0100 | 减号 |
| 0x0002 | B | 0x0200 | 加号 |
| 0x0004 | A | 0x0400 | 左摇杆按下 |
| 0x0008 | X | 0x0800 | 右摇杆按下 |
| 0x0010 | L | 0x1000 | HOME |
| 0x0020 | R | 0x2000 | 截图 |
| 0x0040 | ZL | | |
| 0x0080 | ZR | | |

厂商字节：1 已同步，2 广播中，3 已连接；该步骤失败时为 `0x80 | step`。

## 接线

用一根 USB-C 转 USB-C 线把板子接到主机上。主机既是电源也是 USB 主机；板子从它取电。主机配置好设备后，XIAO ESP32S3 的 LED（GPIO21）会亮。

把 Switch Lite 接在 Mac 的 USB-A 口上并打开「通过 USB 连接复制到电脑」时，它会枚举为 `057e:201d`：一个 MTP 接口、一个只读的「相册」存储、十个只读操作（`0x1001`-`0x100a`）。

## 蓝牙一侧

板子以 `POKELDN-PAD` 广播，带一个服务 `7a1e0001-5d2c-4c3e-9f4b-504f4b454c44`：

| 特征 | 访问 | 内容 |
|---|---|---|
| `...0002` | 写、无响应写 | 8 字节输入报告，原样发送；宏播放期间被忽略 |
| `...0003` | 读 | 状态，见下 |
| `...0004` | 写 | 命令，见下 |

状态字段，小端：mounted u8、report writes u32、playing u8、loops done u32、entry index u16、entry count u16、文本形式的固件版本，然后是 NUL、复位原因 u8（`esp_reset_reason`）、上一次启动达到的阶段 u8，以及上电以来的启动次数 u16。1.0.0 之前的固件只发送前五个字节。

| 命令 | 内容 | 效果 |
|---|---|---|
| `0x10` load | count u16、loop start u16、loops u32 | 停止当前宏并设定程序大小；loops 为 0 时一直播放到被停止 |
| `0x11` data | first entry u16，然后各条目 | 每个条目是一份报告加一个以毫秒计的保持时间 u16，共 10 字节 |
| `0x12` play | | 开始播放程序 |
| `0x13` stop | | 停止并松开所有按键 |
| `0xB0` download | | 把芯片重启进 ROM 加载器 |

程序可容纳 8192 个条目。循环起点之前的条目播放一次，其余重复。播放器以 1 kHz 节拍用 `vTaskDelayUntil` 等待，因此保持时间累加不会漂移。

陷阱：在 macOS 上通过 bleak 做无响应写时，CoreBluetooth 队列一满就会丢，而 bleak 从不读 `canSendWriteWithoutResponse`（连续 300 份报告中只有 67 份到达）。`pokeldn.pad.link` 在每次写报告前等待该标志（每份报告 2.4 ms，无一丢失）；在该标志不存在、或持续一秒为 false 的地方，改用有响应写，每份 60 ms。

断开连接会把报告恢复到中立状态，因此主机消失时不会有按键被按住；正在播放的宏则继续。

## 串口一侧

经典 ESP32 一直留在电脑的 USB 上：921600 波特率的 UART0 双向承载帧（`firmware/pad/main/uart_link.c`、`pokeldn/pad/serial_link.py`），控制台输出关闭。控制台关闭后，没有任何东西把 UART0 路由到 GPIO1 和 GPIO3，所以固件自己设置引脚；没有这一步，板子什么也不应答。

    A5 5A | length u16 (type and payload) | type u8 | payload | sum of type and payload mod 256

| 类型 | 方向 | 内容 |
|---|---|---|
| `0x01` | 发给板子 | 8 字节报告；由 `0x81` 应答 |
| `0x02` | 发给板子 | 无；由 `0x82` 带状态记录应答 |
| `0x03` | 发给板子 | 命令，与控制特征上的相同；由 `0x81` 应答 |
| `0x81` | 发给主机 | 结果 i8：0，-1 长度错误，-2 被拒绝 |
| `0x82` | 发给主机 | 状态记录；mounted 表示 Switch 已设置玩家灯 |

主机以 DTR 和 RTS 为低电平打开端口。在 macOS 上，DevKit 的 CP2102 仍会在端口打开时重启板子，启动期间发出的请求会丢失；主机会把状态请求重复最多 3 秒。服务会先尝试每个不是 S3 原生 USB 的 USB 串口，然后才扫描蓝牙 LE。请用一个进程占住端口：每次重新打开都会重启板子并断开它的蓝牙链路。

## 经典蓝牙一侧

`firmware/pad/main/bt_esp32.c` 注册一个 Bluedroid HID 设备：170 字节的 Pro 控制器报告描述符，服务名「Wireless Gamepad」，厂商「Nintendo」，子类 0x08，设备类 0x002508，名称「Pro Controller」，SSP 无输入无输出，关闭 modem sleep。它按 ID 应答 0x01 子命令：0x02 设备信息（固件 4.00、类型 0x03、自身蓝牙地址）、0x10 SPI 读取、0x03 报告模式、0x04 触发时间、0x21 MCU 配置，其余回一个普通 ACK；0x30（玩家灯）表示控制器已被取用。任何 0x30 之前都会先发出一条回复。

从链路打开的那一刻起，按键或摇杆一变化就立刻发出 0x30 报告，否则每 100 ms 发一次；板子不发时 Switch 不会主动开始握手。板子在链路打开后等 1 秒，一次变化后等 250 ms 转入 sniff 模式，在被以拥塞（原因 8）拒绝发送后等 45 ms：这些是 friendmaker 的 Switch Lite 取值（`classic_bt_controller_transport.cpp`、`SWITCH_LITE`）。陷阱：每 15 ms 发一次 0x30 会拥塞链路，Switch 会在玩家灯亮起后 20 秒内断开（HCI 0x13）。

Switch 的握手顺序：0x02、0x08、0x10 读 0x6000 与 0x6050、0x03（0x30）、0x04、0x10 读 0x6080、0x6098、0x8010、0x603D、0x6020、0x40、0x30（0）、0x48、0x21、0x30（玩家 1）。

已配对的板子会在启动时自动连回它的 Switch。刷写合并镜像会覆盖 NVS 分区，连带清掉配对信息：请从「更改握法/顺序」重新配对。

`pro_report.c` 把共享报告映射到 Pro 控制器的字节布局上（dekuNukem 的 `bluetooth_hid_notes.md`）：摇杆静止为 0x800，两端各为 0x700，与它在 0x603D 返回的出厂校准一致；序列号和用户校准用空白 flash（0xFF）。`tests/test_pad_pro.py` 在主机上编译它，并检查每个按键位与校准。

## 宏

宏是一个扩展名为 `.pokemacro` 的 JSON 文件（`pokeldn.pad.macro`）：

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

| 字段 | 含义 |
|---|---|
| `press_ms`, `gap_ms` | 步骤未另行指定时，它按住输入多久，以及之后的停顿 |
| `setup` | 只运行一次的步骤 |
| `loop` | 重复 `loops` 次的步骤；为 0 时一直重复到被停止 |
| 按下步骤 | `press`：一个按键名，或一组同时按住的按键（`A B X Y L R ZL ZR PLUS MINUS LSTICK RSTICK HOME CAPTURE UP DOWN LEFT RIGHT UPLEFT UPRIGHT DOWNLEFT DOWNRIGHT`）；`left` 与 `right`：摇杆 `[x, y]`，取值 -1 到 1，向上为正；`ms` 保持时间；`after` 停顿；`note` 备注 |
| 等待步骤 | `wait`：毫秒数，期间松开所有按键 |
| 重复步骤 | `repeat`：对 `steps` 重复 1 到 10000 次，最多嵌套 8 层 |

编译器会展开重复、合并相邻且报告相同的条目，并把超过 65535 ms 的保持时间拆开。展开后超过 8192 个条目的宏会被拒绝。两次相同按压之间的 `after: 0` 会把它们并成一次按住。`version` 比读取器更新的文件会被拒绝。

## 主机侧

`pokeldn.pad.service` 持有蓝牙链路，在 `127.0.0.1:47800` 上每行接收一个 JSON 请求：`status`、`connect`、`send`、`tap`、`play`、`stop`、`download`、`scan`、`disconnect`。应用把它作为自己的子进程启动；没有服务在跑时，`tools/switch/pad.py` 会在独立进程中启动它。

在 macOS 上，链路打开时板子断电（从 Switch 上拔下），CoreBluetooth 可能让一次读或写无声地一直挂着。服务会在时限内应答每个请求（`status` 5 秒，`play` 120 秒，`scan` 20 秒，其余 40 秒，连接请求也算在内）。超过时限，服务会关闭链路让板子重新广播，并回复一个错误。应用的客户端在 150 秒后停止等待。

    ./.venv/bin/python tools/switch/pad.py A
    ./.venv/bin/python tools/switch/pad.py HOME wait:1 'RIGHT*3' A
    ./.venv/bin/python tools/switch/pad.py hold:B:2 stick:L:-1:0:0.5
    ./.venv/bin/python tools/switch/pad.py --play soft_reset.pokemacro
    ./.venv/bin/python tools/switch/pad.py --stop --status

在 macOS 上，如果进程的负责应用没有声明 `NSBluetoothAlwaysUsageDescription`，它一打开蓝牙就会被中止；这种情况会出现在嵌在另一个应用里的终端下。`pad.py --make-app PATH` 会写出一个运行该服务的小应用；`open` 它一次并允许蓝牙，此后 `pad.py` 调用和源码检出里的应用都会用它。

## 再次刷写

控制器板占着 USB 口，因此 esptool 无法把它复位进加载器。download 命令、设备页的安装操作和 `pad.py --download` 都通过蓝牙完成；插板子时按住 BOOT 则不需要固件就能进入。

| 陷阱 | 固件或主机的做法 |
|---|---|
| `RTC_CNTL_USB_CONF` 会跨复位保留；若留在 USB-OTG，加载器为 `303a:0009`，esptool 只有一半概率能连上 | 停止 NimBLE 与 TinyUSB，把 PHY 交还 USB Serial/JTAG 并设置 `RTC_CNTL_FORCE_DOWNLOAD_BOOT`；此时加载器为 `303a:1001` |
| 蓝牙与 USB 都开着时 `esp_restart()` 可能挂死 | 不以这种方式调用 |
| 在 macOS 上新加载器端口第一次打开读不到任何东西，且 esptool 会一直占着端口 | `gui/board.py` 等 8 秒，然后不复位直接连接 |
| 从强制加载器刷写之后，USB 复位仍停在加载器里 | `--after watchdog-reset` |

`python -m gui.board --kind pad|radio` 可以互相刷写两种固件；`--from-loader` 用于刷写 download 命令已经放进加载器的板子。

陷阱：在 FreeRTOS 默认的 100 Hz 下，USB 循环的延迟是零个 tick，会饿死 NimBLE；固件按 1000 Hz 构建。

## 构建

    . scratchpad/esp/env.sh
    cd firmware/pad && idf.py -B BUILD_DIR -D SDKCONFIG=SDKCONFIG_PATH build

TinyUSB 来自组件管理器（`espressif/esp_tinyusb` 2.4.0）。发布构建会在无线固件镜像旁生成 `pokeldn-pad-s3.bin`。

## 未解决

- Switch 2 是与经典 ESP32 固件配对，还是接受 HORI 的 ID，尚无实测；目前只测过 Switch Lite。
