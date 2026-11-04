---
title: 樹莓派主機
parent: 硬體與設定
nav_order: 4
---

# 樹莓派 4 神秘禮物主機

64 位樹莓派 4 搭配 TP-Link Archer T3U / AC1300（`2357:012d`，`rtw88_8822bu`）來主持神秘禮物。打過補丁的 LDN 實現是 `vendor/LDN`；絕不要在樹莓派上安裝未打補丁的 PyPI 包。網絡卡的核心配置見[介面卡](hardware_adapters.md)。

部署通過 SSH 別名把已提交的 Git 物件推送到樹莓派上的裸倉庫，不經過 GitHub，不用 `rsync`，也不傳被忽略的檔案（參考倉庫、`.venv`、抓包、寶可夢檔案、Switch 金鑰）。

## 首次部署

在桌面上，從乾淨的已提交檢出開始，帶上 SSH 別名和樹莓派登入使用者：

```bash
./scripts/deploy_pi.sh --host pi-ldn --user PI_USER
```

`deploy_pi.sh` 會拒絕有未提交改動的桌面檢出，執行配置與文件測試，按需建立 `/home/PI_USER/repos/pokeldn.git`，把當前提交推到它的 `deploy` 分支，並建立或快進 `/home/PI_USER/pokeldn`。它從不強制重置，也會拒絕含未提交檔案的樹莓派檢出。如果 SSH 別名已指明遠端使用者，就改為給出路徑：

```bash
./scripts/deploy_pi.sh --host pi-ldn \
  --path /home/PI_USER/pokeldn \
  --repo /home/PI_USER/repos/pokeldn.git
```

然後初始化樹莓派：

```bash
ssh pi-ldn
cd ~/pokeldn
./scripts/setup_pi.sh
```

`setup_pi.sh` 需要 64 位 Raspberry Pi OS（`aarch64`）和 Python 3.11 或更新版本（Bookworm 為 3.11，Trixie 為 3.13）。它從 `requirements.txt` 構建虛擬環境，安裝系統工具（`--no-apt` 跳過），並把 `ldnclient`、`ldn`、`ldn-mon` 和 `ldn-tap` 排除在 NetworkManager 之外（`--no-networkmanager` 跳過）。SSH 請走乙太網路或板載 Wi-Fi：主持會獨佔 TP-Link 網絡卡。

## 配置與 Switch 金鑰

受版本跟蹤的 `config/host.toml` 就是 TP-Link 的實機配置：

```toml
[host]
live = true
skip_encryption = true
accept_decrypted_ccmp = true

[ldn]
phy = "auto"
```

被忽略的 `config/host.local.toml` 儲存金鑰的絕對路徑（主機以 `sudo` 執行）；如何安裝 `prod.keys` 見[在樹莓派上放 Switch 金鑰](hardware_switch_keys.md)。

## 驗證並執行

插上 TP-Link 網絡卡後：

```bash
cd ~/pokeldn
./scripts/preflight_pi.sh
./scripts/run_mystery_gift.sh
```

預檢是隻讀的。它檢查 Python 與隨附的 LDN 包，載入 `config/host.toml` 和可選的 `config/host.local.toml`，檢查 TP-Link 的 USB id 與 `rtw88_8822bu`、AP 與監聽模式支援、NetworkManager 排除項，以及金鑰檔案許可權為 `0600`。對 TP-Link 的呼叫如果停用了 `skip_encryption` 或 `accept_decrypted_ccmp`，包括經 `run_mystery_gift.sh` 傳進去的引數，都會被拒絕。它會自行補上 Debian 的 `sbin` 路徑，因此在 shell 裡和通過單行 SSH 命令執行時表現一致。

`run_mystery_gift.sh` 先跑一次預檢，然後監管短命的 root 主機程序，每個程序用隨機的表ID/裡ID，在完成一次遞送、一次嘗試失敗，或五分鐘內既沒有 Switch 加入也沒有 Pia/RFU 流量之後重啟。按一次 Ctrl-C 即可停止。它總是傳入 `--end-on-success`（在遞送後的關閉流程結束時退出）和 `--idle-timeout 300`（在這麼多秒沒有 Switch 流量後退出），並自己掌管 `--id`，因此儲存的 `--id` 無法複用舊身份。`bin/frlg_mg_host.py` 的其他選項全部原樣轉發；`--help` 和 `--print-effective-config` 既不需要預檢也不需要 root。

每次加入的嘗試都會追加到被忽略的每日臺賬 `logs/mystery-gift-attempts-YYYY-MM-DD.csv`，列為 `attempt`、`received_result`（僅當發出了神秘卡片或印章時為 `true`）、`time`、`trainer_name`、`trainer_ot`（來自 Switch 的 LinkPlayer 塊的名字與五位訓練家 ID，若嘗試在此之前失敗則為空）。`bin/frlg_mg_host.py --attempt-log-dir logs` 會寫同一份臺賬。

活動控制：`--gift`、`--flag-id`、`--verbose`、`--capture`、`--ot`、`--version`、`--id`。`--client-ready-idle-frames N` 是供硬體測試用的時序診斷項，其他情況下不要設定。`--make-artifact` 會在 `artifacts/` 下寫出確定性的 `.ram.lst` 清單（`--artifact-dir DIR` 可改位置）：編譯後的 RAM 指令碼體、反彙編指令、校驗和、分支與訊息目標，以及遞送階段摘要；`--no-make-artifact` 可在儲存的命令裡關掉它。

```bash
./scripts/run_mystery_gift.sh --gift solrock-stamp --client-ready-idle-frames 45 \
  --capture solrock-45.jsonl
./scripts/run_mystery_gift.sh --gift worlds-xp --make-artifact
```

除診斷其他硬體外，`--phy`、`--adapter`、`--skip-encryption` 和 `--accept-decrypted-ccmp` 都保持 TP-Link 的預設值。使用 ALFA `mt76x0u` 時，傳入它當前的 PHY（`iw dev`；重新插拔後會變）和 `--no-accept-decrypted-ccmp`；預檢隨後會檢查該 PHY 的 AP 與監聽模式，以及 `mt76x0u` 的 CCMP 配置。

### 配自定義 AP 驅動的 MT7601U 網絡卡

自帶的 `mt7601u` 驅動沒有 AP 模式。主持需要固定版本的 `mt7601u-ap` DKMS 模組（`vendor/mt7601u-ap-1.0`），並針對樹莓派的 ARM64 核心在樹莓派上構建；絕不要複製桌面構建的 `.ko`。在桌面上：

```bash
./scripts/deploy_pi.sh --host pi-ldn --user PI_USER --install-mt7601u-ap
```

或者在樹莓派上：

```bash
cd ~/pokeldn
./scripts/setup_pi.sh --install-mt7601u-ap --no-networkmanager
```

這會安裝 `dkms` 和 `linux-headers-rpi-v8`，併為每個已安裝且標頭檔案匹配的核心註冊該模組（APT 可能在重啟前裝上更新的核心）；如果當前執行的核心沒有對應標頭檔案，它會停下。重新插拔網絡卡（或重啟），從 `iw dev` 讀出它的 PHY，然後用 `--phy phyN --no-accept-decrypted-ccmp` 執行。預檢會確認載入的 `mt7601u` 來自 `updates/dkms` 且具備 AP 與監聽模式。

## 部署改動

在桌面提交，然後再次執行 `./scripts/deploy_pi.sh --host pi-ldn --user PI_USER`。它只快進程式碼；當依賴檔案或 `vendor/LDN` 變化時，樹莓派會自行重新整理虛擬環境。手動推送之後，在樹莓派上執行 `./scripts/update_pi.sh` 更新。絕不要在樹莓派上編輯受跟蹤的檔案；`config/host.local.toml`、金鑰和抓包都留在樹莓派本地並保持被忽略。
