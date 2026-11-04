---
title: 在樹莓派上放 Switch 金鑰
parent: 硬體與設定
nav_order: 2
---

# 在樹莓派上安裝 Switch 金鑰

`prod.keys` 儲存的是使用者自己 Switch 的金鑰，即時 LDN 主機需要它。絕不要提交它、把它粘進配置、放進抓包，也不要把桌面的虛擬環境複製到樹莓派；部署過程從不傳輸它。它放在 `/home/PI_USER/.switch/prod.keys`，樹莓派上被忽略的 `config/host.local.toml` 指向這個絕對路徑，因為主機以 `sudo` 執行，`~` 不會解析到登入賬戶：

```toml
[ldn]
keys_path = "/home/PI_USER/.switch/prod.keys"
```

## 在樹莓派本地安裝

以樹莓派登入使用者的身份執行安裝指令碼（在 `sudo` 下它會以 `$SUDO_USER` 重新啟動）。它建立許可權 `0700` 的 `~/.switch`，以 `0600` 安裝檔案，從不顯示內容；再次執行時，若檔案內容相同就保留，並修復其許可權。源必須是絕對路徑下的常規檔案，且登入使用者可讀：

```bash
cd ~/pokeldn
./scripts/install_switch_keys.sh --source /absolute/path/to/prod.keys
```

`--stdin` 通過 SSH 流式傳入金鑰，不產生暫存副本：

```bash
# On the desktop; pi-ldn is your SSH alias.
ssh pi-ldn 'cd ~/pokeldn && ./scripts/install_switch_keys.sh --stdin' < "$HOME/.switch/prod.keys"
```

## 通過 SSH 別名使用 SCP

在私有目錄裡暫存，絕不要用 `/tmp` 之類的共享目錄，事後刪除副本（`scp -p` 會保留本地許可權）：

```bash
# On the desktop.
ssh pi-ldn 'install -d -m 700 "$HOME/.frlg-ldn-provision"'
scp -p "$HOME/.switch/prod.keys" pi-ldn:.frlg-ldn-provision/prod.keys
ssh pi-ldn 'cd ~/pokeldn && \
  ./scripts/install_switch_keys.sh --source "$HOME/.frlg-ldn-provision/prod.keys" && \
  rm -f "$HOME/.frlg-ldn-provision/prod.keys" && \
  rmdir "$HOME/.frlg-ldn-provision"'
```

兩種方法都用下面的命令驗證：

```bash
ssh pi-ldn 'stat -c "%a %U %n" "$HOME/.switch" "$HOME/.switch/prod.keys"'
# Expected: 700 PI_USER /home/PI_USER/.switch
#           600 PI_USER /home/PI_USER/.switch/prod.keys
```
