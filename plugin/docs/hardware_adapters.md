---
title: 适配器
parent: 硬件与设置
nav_order: 3
---

# Wi-Fi 网卡

Linux 主机可以 root 身份直接驱动一块支持 AP 模式的 Wi-Fi 网卡，替代 [ESP32 无线模块](hardware_esp32.md)。这条路径属于旧版。

| 症状 | 原因 |
|---|---|
| 启动 AP 时出现类似虚拟机环境的 USB 断开 | USB 模式切换（见下） |
| 主机毫无输出 | 未设置 `accept_decrypted_ccmp` |
| `dmesg` 中出现 `failed to get tx report from firmware` | 主机自身的拆除流程 |

## 通过 ldnrs 使用 Windows USB Wi-Fi

Windows 可以借助 [ldnrs 0.0.3](https://github.com/unlimitedcoder2/ldnrs/releases/tag/0.0.3) 使用外置 USB Wi-Fi 网卡。单独安装 ldnrs，完成它的网卡向导，并让它的守护进程保持运行。在 pokeldn 中打开**插件**，然后在**无线**下选择 **USB Wi-Fi（Windows，ldnrs）**。Switch 密钥仍来自 pokeldn 的设置。

ldnrs 向导会把网卡绑定到 WinUSB，并下载它所需的 Linux 驱动固件；此后在设备管理器中恢复原驱动之前，这块网卡不再提供 Windows Wi-Fi。兼容性取决于 ldnrs；下面 Linux 网卡的结果不能说明 Windows 的情况。

在 PowerShell 中，先选好后端，再运行任意游戏惯用的启动器：

```powershell
$env:POKELDN_RADIO = 'ldnrs:'
python bin/swsh_gift_host.py --keys C:\Switch\prod.keys --species 25 --level 25
```

空参数会选择本地管道 `\\.\pipe\ldnd`；冒号后也可以跟另一个管道名。守护进程通过该管道接收密钥。它掌管无线电、LDN 关联与加密；pokeldn 则通过现有的用户态 IPv4 栈承载以太网帧。扫描、加入、主持与广播更新使用[守护进程协议 7](https://github.com/unlimitedcoder2/ldnrs/blob/0.0.3/docs/daemon-protocol.md)。守护进程缺失、网卡未就绪或协议版本不同都会报错。

守护进程允许关联用 70 秒，启动器则至少给 90 秒：上游的 [RTL8822BU 测量](https://github.com/unlimitedcoder2/ldnrs/blob/0.0.3/clients/python/ldnd/compat.py)把两次驱动重配置各算约 14.5 秒。游戏的握手在关联之后才开始。一个守护进程一次只承载一个会话。会话结束时 pokeldn 关闭自己的原始信道与网络，但让外部守护进程继续运行。抓包会保留游戏的 UDP 流量；ESP32 的计数器与随附库的 Wi-Fi 管理钩子在此不适用。

离线测试把扫描、加入与主持请求同 ldnrs 0.0.3 Python 客户端的向量比对，并与脚本化的守护进程交换 UDP。本后端上 Windows 网卡配零售主机的组合尚未测试。

## 实测网卡

| 型号 | 类型 | 驱动 | 在实测主机上的结果 |
|---|---|---|---|
| TP-Link Archer T3U（`2357:012d`） | 外置 USB | `rtw88_8822bu` | 可靠；参考网卡 |
| ALFA AWUS036ACHM | 外置 USB | `mt76x0u` | 可靠 |
| Realtek RTL8821CE | 内置 PCIe | `rtw88_8821ce` | 可靠 |
| AMD RZ616 | 内置 M.2 | `mt7921e` | 速度约为一半，有时在退出前死锁 |
| MT7601U | 外置 USB | `mt7601u` | 自带驱动没有 AP 模式；需要固定版本的 `mt7601u-ap` DKMS 模块（[树莓派主机](hardware_raspberry_pi.md)） |
| Intel AX200 | 内置 M.2 | `iwlwifi` | 失败：无法分配 IP |
| Atheros AR9271 | 外置 USB | `ath9k_htc` | 失败：通常无法分配 IP |

## 主机模式

`--skip-encryption` 跳过 LDN 的 Python CCMP 步骤，让 mac80211 或硬件只做一次 CCMP；流量在空中仍然加密。Archer T3U（`config/host.toml` 中的 `skip_encryption = true`）和 ALFA AWUS036ACHM 需要它。

`--accept-decrypted-ccmp` 针对的是这类监听驱动：硬件解密后的明文外面仍留着 CCMP 头与 MIC，Archer T3U 的 `rtw88_8822bu` 就是这样；它在把明文转交给 `ldn-tap` 之前剥掉 MIC。ALFA 交付的是标准帧，对它保持关闭。

| 网卡 | 主机配置 |
|---|---|
| TP-Link Archer T3U | 受版本跟踪的 `config/host.toml` 配置；不加任何 Wi-Fi 参数 |
| ALFA AWUS036ACHM | `--phy phyN --skip-encryption --no-accept-decrypted-ccmp` |

`phy = "auto"` 只解析唯一一个 `rtw88_8822bu` 的 USB `2357:012d` 设备，没有或多个都会失败。显式的 `--phy phyN` 总是优先；把它留作一次性调试用，因为每次重新枚举该编号都会变。启动时会打印检测到的配置、发送与接收模式，以及参数与已验证配置不同时的警告。

## TP-Link Archer T3U

`rtw88_8822bu` 自内核 6.11 起进入主线，并列出这个 USB id。确认内核已绑定它：

```bash
modinfo rtw88_8822bu | grep -i 2357
lsusb | grep -i 2357
iw dev
```

### 让 NetworkManager 别碰网卡本身

NetworkManager 会抢占网卡热插的接口（`wlx...`）并启动后台扫描；切换信道会在接口出现后不久把无线电拉下线（实测 11 秒）：

```text
rtw88_8822bu 3-1:1.0: write register 0x81c failed with -71
usb 3-1: USB disconnect, device number 2
```

把网卡和 LDN 接口排除在外：

```text
# /etc/NetworkManager/conf.d/zz-ldn-unmanaged.conf
[keyfile]
unmanaged-devices=interface-name:ldnclient;interface-name:ldn;interface-name:ldn-mon;interface-name:ldn-tap;interface-name:wlx*;interface-name:wlan*
```

该文件必须排在最后（`zz-`）：有些发行版会附带一个更靠后的文件，把 `unmanaged-devices` 设为 `none`。重新加载 NetworkManager；`nmcli device status` 必须把网卡显示为 `unmanaged`，`NetworkManager --print-config | grep unmanaged` 必须列出这份清单。清单里没有 `ldnclient` 时，NetworkManager 会抢走加入时创建的接口，把 wpa_supplicant 指向它，加入便以 `[Errno 114] Match already configured` 失败。

### 关掉驱动的 USB 3 模式切换

`rtw88_usb` 默认为 `switch_usb_mode=Y`，驱动加载后会把网卡重新枚举为 USB 3 模式。以直通方式传递设备的虚拟机环境会看到一次断开，LDN 接口消失，主机在主持早期就退出（实测约 1 秒），此前没有任何驱动报错：

```text
RuntimeError: 802.11 beacon injector stopped: [Errno 100] Network is down
```

该参数自身的说明指出，USB 3 模式可能干扰 2.4 GHz，也就是 LDN 所在的频段。

```text
# /etc/modprobe.d/rtw88-ldn.conf
options rtw88_usb switch_usb_mode=N
options rtw88_core disable_lps_deep=Y
```

之后重新插拔网卡：在断电之前它会一直停在 USB 3 模式。重新插拔后它只以高速挂载一次（开关打开时会枚举两次，先高速再 SuperSpeed）：

```bash
cat /sys/bus/usb/devices/*/speed     # 480, not 5000
cat /sys/bus/usb/devices/*/version   # 2.10, not 3.00
```

### 运行前先把网卡接口关掉

处于 up 状态的受管接口会占住无线电的信道。`transport.free_radio()` 会把它关掉；直接跑 `tools/ldn/ldn_scan.py` 则不会：

```text
OSError: [Errno 16] Device or resource busy
```

```bash
sudo ip link set wlxXXXXXXXXXXXX down
```

把基础接口重新 up 的清理脚本会让下一次启动以这个错误失败。任何为内核 `iw scan` 而把接口 up 起来的操作，都必须在交接前再把它关掉。

### 验证

`./scripts/preflight_pi.sh` 可在任何 Linux 主机上运行。
