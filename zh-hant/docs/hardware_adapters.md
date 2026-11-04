---
title: 介面卡
parent: 硬體與設定
nav_order: 3
---

# Wi-Fi 網絡卡

Linux 主機可以 root 身份直接驅動一塊支援 AP 模式的 Wi-Fi 網絡卡，替代 [ESP32 無線模組](hardware_esp32.md)。這條路徑屬於舊版。

| 症狀 | 原因 |
|---|---|
| 啟動 AP 時出現類似虛擬機器環境的 USB 斷開 | USB 模式切換（見下） |
| 主機毫無輸出 | 未設定 `accept_decrypted_ccmp` |
| `dmesg` 中出現 `failed to get tx report from firmware` | 主機自身的拆除流程 |

## 通過 ldnrs 使用 Windows USB Wi-Fi

Windows 可以藉助 [ldnrs 0.0.3](https://github.com/unlimitedcoder2/ldnrs/releases/tag/0.0.3) 使用外接 USB Wi-Fi 網絡卡。單獨安裝 ldnrs，完成它的網絡卡嚮導，並讓它的守護程序保持執行。在 pokeldn 中開啟**外掛**，然後在**無線**下選擇 **USB Wi-Fi（Windows，ldnrs）**。Switch 金鑰仍來自 pokeldn 的設定。

ldnrs 嚮導會把網絡卡繫結到 WinUSB，並下載它所需的 Linux 驅動韌體；此後在裝置管理器中恢復原驅動之前，這塊網絡卡不再提供 Windows Wi-Fi。相容性取決於 ldnrs；下面 Linux 網絡卡的結果不能說明 Windows 的情況。

在 PowerShell 中，先選好後端，再執行任意遊戲慣用的啟動器：

```powershell
$env:POKELDN_RADIO = 'ldnrs:'
python bin/swsh_gift_host.py --keys C:\Switch\prod.keys --species 25 --level 25
```

空引數會選擇本地管道 `\\.\pipe\ldnd`；冒號後也可以跟另一個管道名。守護程序通過該管道接收金鑰。它掌管無線電、LDN 關聯與加密；pokeldn 則通過現有的使用者態 IPv4 棧承載乙太網路幀。掃描、加入、主持與廣播更新使用[守護程序協議 7](https://github.com/unlimitedcoder2/ldnrs/blob/0.0.3/docs/daemon-protocol.md)。守護程序缺失、網絡卡未就緒或協議版本不同都會報錯。

守護程序允許關聯用 70 秒，啟動器則至少給 90 秒：上游的 [RTL8822BU 測量](https://github.com/unlimitedcoder2/ldnrs/blob/0.0.3/clients/python/ldnd/compat.py)把兩次驅動重配置各算約 14.5 秒。遊戲的握手在關聯之後才開始。一個守護程序一次只承載一個會話。會話結束時 pokeldn 關閉自己的原始通道與網路，但讓外部守護程序繼續執行。抓包會保留遊戲的 UDP 流量；ESP32 的計數器與隨附庫的 Wi-Fi 管理鉤子在此不適用。

離線測試把掃描、加入與主持請求同 ldnrs 0.0.3 Python 客戶端的向量比對，並與指令碼化的守護程序交換 UDP。本後端上 Windows 網絡卡配零售主機的組合尚未測試。

## 實測網絡卡

| 型號 | 型別 | 驅動 | 在實測主機上的結果 |
|---|---|---|---|
| TP-Link Archer T3U（`2357:012d`） | 外接 USB | `rtw88_8822bu` | 可靠；參考網絡卡 |
| ALFA AWUS036ACHM | 外接 USB | `mt76x0u` | 可靠 |
| Realtek RTL8821CE | 內建 PCIe | `rtw88_8821ce` | 可靠 |
| AMD RZ616 | 內建 M.2 | `mt7921e` | 速度約為一半，有時在退出前死鎖 |
| MT7601U | 外接 USB | `mt7601u` | 自帶驅動沒有 AP 模式；需要固定版本的 `mt7601u-ap` DKMS 模組（[樹莓派主機](hardware_raspberry_pi.md)） |
| Intel AX200 | 內建 M.2 | `iwlwifi` | 失敗：無法分配 IP |
| Atheros AR9271 | 外接 USB | `ath9k_htc` | 失敗：通常無法分配 IP |

## 主機模式

`--skip-encryption` 跳過 LDN 的 Python CCMP 步驟，讓 mac80211 或硬體只做一次 CCMP；流量在空中仍然加密。Archer T3U（`config/host.toml` 中的 `skip_encryption = true`）和 ALFA AWUS036ACHM 需要它。

`--accept-decrypted-ccmp` 針對的是這類監聽驅動：硬體解密後的明文外面仍留著 CCMP 頭與 MIC，Archer T3U 的 `rtw88_8822bu` 就是這樣；它在把明文轉交給 `ldn-tap` 之前剝掉 MIC。ALFA 交付的是標準幀，對它保持關閉。

| 網絡卡 | 主機配置 |
|---|---|
| TP-Link Archer T3U | 受版本跟蹤的 `config/host.toml` 配置；不加任何 Wi-Fi 引數 |
| ALFA AWUS036ACHM | `--phy phyN --skip-encryption --no-accept-decrypted-ccmp` |

`phy = "auto"` 只解析唯一一個 `rtw88_8822bu` 的 USB `2357:012d` 裝置，沒有或多個都會失敗。顯式的 `--phy phyN` 總是優先；把它留作一次性除錯用，因為每次重新列舉該編號都會變。啟動時會列印檢測到的配置、傳送與接收模式，以及引數與已驗證配置不同時的警告。

## TP-Link Archer T3U

`rtw88_8822bu` 自核心 6.11 起進入主線，並列出這個 USB id。確認核心已繫結它：

```bash
modinfo rtw88_8822bu | grep -i 2357
lsusb | grep -i 2357
iw dev
```

### 讓 NetworkManager 別碰網絡卡本身

NetworkManager 會搶佔網絡卡熱插的介面（`wlx...`）並啟動後臺掃描；切換通道會在接口出現後不久把無線電拉下線（實測 11 秒）：

```text
rtw88_8822bu 3-1:1.0: write register 0x81c failed with -71
usb 3-1: USB disconnect, device number 2
```

把網絡卡和 LDN 介面排除在外：

```text
# /etc/NetworkManager/conf.d/zz-ldn-unmanaged.conf
[keyfile]
unmanaged-devices=interface-name:ldnclient;interface-name:ldn;interface-name:ldn-mon;interface-name:ldn-tap;interface-name:wlx*;interface-name:wlan*
```

該檔案必須排在最後（`zz-`）：有些發行版會附帶一個更靠後的檔案，把 `unmanaged-devices` 設為 `none`。重新載入 NetworkManager；`nmcli device status` 必須把網絡卡顯示為 `unmanaged`，`NetworkManager --print-config | grep unmanaged` 必須列出這份清單。清單裡沒有 `ldnclient` 時，NetworkManager 會搶走加入時建立的介面，把 wpa_supplicant 指向它，加入便以 `[Errno 114] Match already configured` 失敗。

### 關掉驅動的 USB 3 模式切換

`rtw88_usb` 預設為 `switch_usb_mode=Y`，驅動載入後會把網絡卡重新列舉為 USB 3 模式。以直通方式傳遞裝置的虛擬機器環境會看到一次斷開，LDN 介面消失，主機在主持早期就退出（實測約 1 秒），此前沒有任何驅動報錯：

```text
RuntimeError: 802.11 beacon injector stopped: [Errno 100] Network is down
```

該引數自身的說明指出，USB 3 模式可能干擾 2.4 GHz，也就是 LDN 所在的頻段。

```text
# /etc/modprobe.d/rtw88-ldn.conf
options rtw88_usb switch_usb_mode=N
options rtw88_core disable_lps_deep=Y
```

之後重新插拔網絡卡：在斷電之前它會一直停在 USB 3 模式。重新插拔後它只以高速掛載一次（開關開啟時會列舉兩次，先高速再 SuperSpeed）：

```bash
cat /sys/bus/usb/devices/*/speed     # 480, not 5000
cat /sys/bus/usb/devices/*/version   # 2.10, not 3.00
```

### 執行前先把網絡卡介面關掉

處於 up 狀態的受管介面會佔住無線電的通道。`transport.free_radio()` 會把它關掉；直接跑 `tools/ldn/ldn_scan.py` 則不會：

```text
OSError: [Errno 16] Device or resource busy
```

```bash
sudo ip link set wlxXXXXXXXXXXXX down
```

把基礎介面重新 up 的清理指令碼會讓下一次啟動以這個錯誤失敗。任何為核心 `iw scan` 而把介面 up 起來的操作，都必須在交接前再把它關掉。

### 驗證

`./scripts/preflight_pi.sh` 可在任何 Linux 主機上執行。
