---
title: 树莓派主机
parent: 硬件与设置
nav_order: 4
---

# 树莓派 4 神秘礼物主机

64 位树莓派 4 搭配 TP-Link Archer T3U / AC1300（`2357:012d`，`rtw88_8822bu`）来主持神秘礼物。打过补丁的 LDN 实现是 `vendor/LDN`；绝不要在树莓派上安装未打补丁的 PyPI 包。网卡的内核配置见[适配器](hardware_adapters.md)。

部署通过 SSH 别名把已提交的 Git 对象推送到树莓派上的裸仓库，不经过 GitHub，不用 `rsync`，也不传被忽略的文件（参考仓库、`.venv`、抓包、宝可梦文件、Switch 密钥）。

## 首次部署

在桌面上，从干净的已提交检出开始，带上 SSH 别名和树莓派登录用户：

```bash
./scripts/deploy_pi.sh --host pi-ldn --user PI_USER
```

`deploy_pi.sh` 会拒绝有未提交改动的桌面检出，运行配置与文档测试，按需创建 `/home/PI_USER/repos/pokeldn.git`，把当前提交推到它的 `deploy` 分支，并创建或快进 `/home/PI_USER/pokeldn`。它从不强制重置，也会拒绝含未提交文件的树莓派检出。如果 SSH 别名已指明远端用户，就改为给出路径：

```bash
./scripts/deploy_pi.sh --host pi-ldn \
  --path /home/PI_USER/pokeldn \
  --repo /home/PI_USER/repos/pokeldn.git
```

然后初始化树莓派：

```bash
ssh pi-ldn
cd ~/pokeldn
./scripts/setup_pi.sh
```

`setup_pi.sh` 需要 64 位 Raspberry Pi OS（`aarch64`）和 Python 3.11 或更新版本（Bookworm 为 3.11，Trixie 为 3.13）。它从 `requirements.txt` 构建虚拟环境，安装系统工具（`--no-apt` 跳过），并把 `ldnclient`、`ldn`、`ldn-mon` 和 `ldn-tap` 排除在 NetworkManager 之外（`--no-networkmanager` 跳过）。SSH 请走以太网或板载 Wi-Fi：主持会独占 TP-Link 网卡。

## 配置与 Switch 密钥

受版本跟踪的 `config/host.toml` 就是 TP-Link 的实机配置：

```toml
[host]
live = true
skip_encryption = true
accept_decrypted_ccmp = true

[ldn]
phy = "auto"
```

被忽略的 `config/host.local.toml` 保存密钥的绝对路径（主机以 `sudo` 运行）；如何安装 `prod.keys` 见[在树莓派上放 Switch 密钥](hardware_switch_keys.md)。

## 验证并运行

插上 TP-Link 网卡后：

```bash
cd ~/pokeldn
./scripts/preflight_pi.sh
./scripts/run_mystery_gift.sh
```

预检是只读的。它检查 Python 与随附的 LDN 包，加载 `config/host.toml` 和可选的 `config/host.local.toml`，检查 TP-Link 的 USB id 与 `rtw88_8822bu`、AP 与监听模式支持、NetworkManager 排除项，以及密钥文件权限为 `0600`。对 TP-Link 的调用如果禁用了 `skip_encryption` 或 `accept_decrypted_ccmp`，包括经 `run_mystery_gift.sh` 传进去的参数，都会被拒绝。它会自行补上 Debian 的 `sbin` 路径，因此在 shell 里和通过单行 SSH 命令运行时表现一致。

`run_mystery_gift.sh` 先跑一次预检，然后监管短命的 root 主机进程，每个进程用随机的表ID/里ID，在完成一次递送、一次尝试失败，或五分钟内既没有 Switch 加入也没有 Pia/RFU 流量之后重启。按一次 Ctrl-C 即可停止。它总是传入 `--end-on-success`（在递送后的关闭流程结束时退出）和 `--idle-timeout 300`（在这么多秒没有 Switch 流量后退出），并自己掌管 `--id`，因此保存的 `--id` 无法复用旧身份。`bin/frlg_mg_host.py` 的其他选项全部原样转发；`--help` 和 `--print-effective-config` 既不需要预检也不需要 root。

每次加入的尝试都会追加到被忽略的每日台账 `logs/mystery-gift-attempts-YYYY-MM-DD.csv`，列为 `attempt`、`received_result`（仅当发出了神秘卡片或印章时为 `true`）、`time`、`trainer_name`、`trainer_ot`（来自 Switch 的 LinkPlayer 块的名字与五位训练家 ID，若尝试在此之前失败则为空）。`bin/frlg_mg_host.py --attempt-log-dir logs` 会写同一份台账。

活动控制：`--gift`、`--flag-id`、`--verbose`、`--capture`、`--ot`、`--version`、`--id`。`--client-ready-idle-frames N` 是供硬件测试用的时序诊断项，其他情况下不要设置。`--make-artifact` 会在 `artifacts/` 下写出确定性的 `.ram.lst` 清单（`--artifact-dir DIR` 可改位置）：编译后的 RAM 脚本体、反汇编指令、校验和、分支与消息目标，以及递送阶段摘要；`--no-make-artifact` 可在保存的命令里关掉它。

```bash
./scripts/run_mystery_gift.sh --gift solrock-stamp --client-ready-idle-frames 45 \
  --capture solrock-45.jsonl
./scripts/run_mystery_gift.sh --gift worlds-xp --make-artifact
```

除诊断其他硬件外，`--phy`、`--adapter`、`--skip-encryption` 和 `--accept-decrypted-ccmp` 都保持 TP-Link 的默认值。使用 ALFA `mt76x0u` 时，传入它当前的 PHY（`iw dev`；重新插拔后会变）和 `--no-accept-decrypted-ccmp`；预检随后会检查该 PHY 的 AP 与监听模式，以及 `mt76x0u` 的 CCMP 配置。

### 配自定义 AP 驱动的 MT7601U 网卡

自带的 `mt7601u` 驱动没有 AP 模式。主持需要固定版本的 `mt7601u-ap` DKMS 模块（`vendor/mt7601u-ap-1.0`），并针对树莓派的 ARM64 内核在树莓派上构建；绝不要复制桌面构建的 `.ko`。在桌面上：

```bash
./scripts/deploy_pi.sh --host pi-ldn --user PI_USER --install-mt7601u-ap
```

或者在树莓派上：

```bash
cd ~/pokeldn
./scripts/setup_pi.sh --install-mt7601u-ap --no-networkmanager
```

这会安装 `dkms` 和 `linux-headers-rpi-v8`，并为每个已安装且头文件匹配的内核注册该模块（APT 可能在重启前装上更新的内核）；如果当前运行的内核没有对应头文件，它会停下。重新插拔网卡（或重启），从 `iw dev` 读出它的 PHY，然后用 `--phy phyN --no-accept-decrypted-ccmp` 运行。预检会确认加载的 `mt7601u` 来自 `updates/dkms` 且具备 AP 与监听模式。

## 部署改动

在桌面提交，然后再次运行 `./scripts/deploy_pi.sh --host pi-ldn --user PI_USER`。它只快进代码；当依赖文件或 `vendor/LDN` 变化时，树莓派会自行刷新虚拟环境。手动推送之后，在树莓派上运行 `./scripts/update_pi.sh` 更新。绝不要在树莓派上编辑受跟踪的文件；`config/host.local.toml`、密钥和抓包都留在树莓派本地并保持被忽略。
