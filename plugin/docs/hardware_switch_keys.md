---
title: 在树莓派上放 Switch 密钥
parent: 硬件与设置
nav_order: 2
---

# 在树莓派上安装 Switch 密钥

`prod.keys` 保存的是用户自己 Switch 的密钥，实时 LDN 主机需要它。绝不要提交它、把它粘进配置、放进抓包，也不要把桌面的虚拟环境复制到树莓派；部署过程从不传输它。它放在 `/home/PI_USER/.switch/prod.keys`，树莓派上被忽略的 `config/host.local.toml` 指向这个绝对路径，因为主机以 `sudo` 运行，`~` 不会解析到登录账户：

```toml
[ldn]
keys_path = "/home/PI_USER/.switch/prod.keys"
```

## 在树莓派本地安装

以树莓派登录用户的身份运行安装脚本（在 `sudo` 下它会以 `$SUDO_USER` 重新启动）。它创建权限 `0700` 的 `~/.switch`，以 `0600` 安装文件，从不显示内容；再次运行时，若文件内容相同就保留，并修复其权限。源必须是绝对路径下的常规文件，且登录用户可读：

```bash
cd ~/pokeldn
./scripts/install_switch_keys.sh --source /absolute/path/to/prod.keys
```

`--stdin` 通过 SSH 流式传入密钥，不产生暂存副本：

```bash
# On the desktop; pi-ldn is your SSH alias.
ssh pi-ldn 'cd ~/pokeldn && ./scripts/install_switch_keys.sh --stdin' < "$HOME/.switch/prod.keys"
```

## 通过 SSH 别名使用 SCP

在私有目录里暂存，绝不要用 `/tmp` 之类的共享目录，事后删除副本（`scp -p` 会保留本地权限）：

```bash
# On the desktop.
ssh pi-ldn 'install -d -m 700 "$HOME/.frlg-ldn-provision"'
scp -p "$HOME/.switch/prod.keys" pi-ldn:.frlg-ldn-provision/prod.keys
ssh pi-ldn 'cd ~/pokeldn && \
  ./scripts/install_switch_keys.sh --source "$HOME/.frlg-ldn-provision/prod.keys" && \
  rm -f "$HOME/.frlg-ldn-provision/prod.keys" && \
  rmdir "$HOME/.frlg-ldn-provision"'
```

两种方法都用下面的命令验证：

```bash
ssh pi-ldn 'stat -c "%a %U %n" "$HOME/.switch" "$HOME/.switch/prod.keys"'
# Expected: 700 PI_USER /home/PI_USER/.switch
#           600 PI_USER /home/PI_USER/.switch/prod.keys
```
