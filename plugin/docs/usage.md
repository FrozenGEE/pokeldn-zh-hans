---
title: 命令行用法
---

# 命令行用法

本页列出各作品的命令行入口。请在仓库根目录下运行它们。
源码工具需要 Python 3.11+、Switch 的 `prod.keys`
（默认为 `~/.switch/prod.keys`，或用 `--keys PATH` 指定），以及一块已刷好固件的 ESP32 板子。
参见[支持的板子](hardware_esp32.md#supported-boards)和
[构建与刷写](hardware_esp32.md#building-and-flashing)。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
dotnet build -c Release services/pkhex
export POKELDN_RADIO=esp32:auto
python -m pokeldn --list
python -m pokeldn --radio esp32:auto swsh-host --offer-file offer.pk8
```

交换工具需要 .NET 10 SDK。PyPI 上的 `ldn` 包是另一个库。在 Windows 上请使用
`.venv\Scripts\Activate.ps1` 和 `$env:POKELDN_RADIO = "esp32:auto"`。`esp32:auto` 会挑选唯一的
USB 串口；`esp32:PORT` 则指定某一个（[无线设置](hardware_esp32.md#running)）。每个入口
都接受 `--help`。

## 火红与叶绿

在主机上解锁 Direct Corner，并准备至少两只 `.pk3` 队伍成员。

```bash
./.venv/bin/python bin/frlg_trade_join.py --live -o output.pk3 PARTY1.pk3 PARTY2.pk3   # join the Switch's trade
./.venv/bin/python bin/frlg_trade_host.py -o output.pk3 PARTY1.pk3 PARTY2.pk3          # host a Direct Corner trade
```

主机提供 `PARTY2.pk3`，并把收到的内容写入 `output.pk3`。默认值来自
`config/host.toml`，其次是 `config/host.local.toml`；命令行标志会覆盖这两者
（`--print-effective-config`）。在 `Hosting Direct Corner` 之后：Direct Corner、Join Group、pokeldn 的
训练家，然后选择并确认。`--trades N`（1 到 6）提供槽位 0 到 N-1，每次交换一个；最后一个之后，
CANCEL、YES。

| 标志 | 用途 |
|---|---|
| `--keys PATH` | `prod.keys` 的位置 |
| `--slot N` | 提供的队伍成员，从 0 开始计数 |
| `--capture FILE` | JSONL 诊断抓包 |
| `--config` / `--local-config` / `--no-local-config` | 替换或禁用某一层配置 |
| `--ot NAME`, `--version firered\|leafgreen`, `--id TID[:SID]` | 每次运行时覆盖训练家信息（各为 0..65535；LinkPlayer ID 为 `(SID << 16) \| TID`） |
| `--verbose` | 逐数据包输出；仅在配合 `--replay` 时，会让实时链路卡住 |

[`pokeldn/config.py`](../pokeldn/config.py) 中的 `DEFAULT_TRAINER` 保存其余默认值。协议：
[链路协议](frlg_link.md)。

### 联盟室

`--union-room` 会扮演中间的那个 NPC；主机会在约 10 秒后连接。一条链路只承载一次
交换（`union_room.c:1744`）。`--board-type normal` 在交换板上登记，`--union-room-chat`
配合 `--chat-message` / `--chat-file` 聊天，`--union-room-battle --battle-fight` 对战（两只
30 级或以下的非蛋宝可梦）。

```bash
./.venv/bin/python bin/frlg_trade_host.py --union-room --union-room-keepalive 120 PARTY1.pk3 PARTY2.pk3
```

### 神秘礼物

`bin/frlg_mg_host.py` 沿神秘礼物、神秘卡片、好友的路径发送一张神秘卡片和投递脚本。
`--make-artifact` 会把发送的字节写成 `.ram.lst`。目录：[神秘礼物](frlg_gift.md)。

```bash
./.venv/bin/python -u bin/frlg_mg_host.py --gift beast-cutscene --flag-id 1005 --capture mystery-gift.jsonl
```

这只野兽会跟随御三家（妙蛙种子配水君，杰尼龟配炎帝，小火龙配雷公）。

### 不可思议的新闻

`--news` 沿神秘礼物、不可思议的新闻、好友的路径提供服务。只有当新闻与主机上已有的内容
不同时，主机才会保留它；`--news-id N` 会强制使用一条新新闻。

```bash
./.venv/bin/python -u bin/frlg_mg_host.py --news berry --news-id 7
```

### 存档备份与恢复

好友路径会把 128 KB 的存档复制到 `.sav`（约四分钟），或把存档写回；未完成的恢复会让
存档保持原样（[详情](frlg_gift.md#save-backup-and-restore)）。

```bash
./.venv/bin/python -u bin/frlg_mg_host.py --live --save-backup backup.sav --save-resume-dir partial
./.venv/bin/python -u bin/frlg_mg_host.py --live --save-restore backup.sav
```

### 主机存档

`save-dump` 读取正在运行的存档；`flash-patch` 重写某个扇区中指定的字节，并同时更新其
校验和与计数器。写入之前请先阅读[构造扇区](frlg_rom.md#composing-a-sector-from-a-ram-snapshot)。
载荷：[主机上的代码](frlg_rom.md)。

```bash
./.venv/bin/python -u bin/frlg_mg_host.py --buffer-script save-dump --dump-block sav2 --dump-size 64 --dump-file dump.bin
./.venv/bin/python tools/frlg/dump_read.py dump.bin --block sav2
./.venv/bin/python -u bin/frlg_mg_host.py --buffer-script flash-patch --flash-id 0 \
  --flash-patch-offset 0x00 --flash-patch-hex cac9c5bfc6bec8ff --write-unsafe
```

## Let's Go 皮卡丘与伊布

pokeldn 可以主持，也可以加入。两者都会提供 232 字节的 PB7（`pokeldn.lgpe.pb7`；`--offer echo`
会返回主机的）；主持方的 `--first echo` 会回显主机的身份消息。主持方的 `--next-offer`
和加入方重复的 `--offer` 会排入后续交换；`--leave-after S` 会让加入方离开。

```bash
./.venv/bin/python bin/lgpe_host.py --seconds 600 --player-name POKELDN \
  --first echo --our-trainer 41234:12345 --offer offer.pb7
./.venv/bin/python bin/lgpe_join.py --connect --connect-seconds 300 \
  --ack-peer-clock --ack-re-announce \
  --our-trainer 41234:12345 --offer offer.pb7
```

主机：Communiquer、Communication locale、Échange，连接密码为皮卡丘 ×3，然后在搜索
界面等待。模拟主机：`lgpe_host.py --ip-host --our-ip IP`。参见 [Let's Go](lgpe.md)。

## 剑与盾

主机：Y-Comm、连接交换、本地通信，两条消息都按 A，然后在搜索界面等待。

```bash
# join the console's session and trade: the console's own party snapshot is sent back, rewritten
POKELDN_RADIO=esp32:auto ./.venv/bin/python bin/swsh_connect.py --keys PROD_KEYS \
  --preset trade --offer-slot 1 [--offer-file your.pk8 --offer-file next.pk8 --fresh-pid] \
  --save-offered received.pk8

# or host, and let the console join: its snapshot is taken from this trade
POKELDN_RADIO=esp32:auto ./.venv/bin/python bin/swsh_host.py --keys PROD_KEYS \
  --offer-file your.pk8 --fresh-pid --received received.pk8 --channel 6 --seconds 900
```

`--code 12345678` 会针对连接密码搜索来主持。重复的 `--offer-file` 每次交换排入一个；第 N 次
交换写入时带后缀 `-N`。详情：[交换](swsh_trade.md)。

神秘礼物：神秘礼物、领取礼物、通过本地无线。

```bash
./.venv/bin/python bin/swsh_gift_host.py --species 25 --level 25 \
  --move1 84 --move2 45 --move3 86 --move4 98 --nickname POKELDN --ot POKELDN --seconds 300
./.venv/bin/python bin/swsh_gift_host.py --record card.wc8 --seconds 300
```

`--set FIELD=VALUE` 设置记录中的字段（`shiny_type=3`、`held_item=236`），`--ribbon N` 添加一条
缎带，`--dump FILE` 无需无线模块即可写出记录。如果某个道具 ID 在表中没有对应行，当它的背包行
显示时游戏会中止。参见[神秘礼物](swsh_gift.md)。

## 晶灿钻石与明亮珍珠

pokeldn 以一个角色的身份加入主机的联盟室。主机：任意宝可梦中心 2F，左侧柜台，选普通的
「是」（第一个选项），然后在联盟室里远离墙壁处等待。

```bash
./.venv/bin/python tools/ldn/ldn_scan.py --channels 1,6,11 --dwell 0.8      # see the session
./.venv/bin/python bin/bdsp_connect.py --channels 1,6,11 --count 9 --connect 5 --join 6 \
  --hold 420 --reliable-ack --reliable-sweep 3 --room-walk 15 --room-pattern fixed \
  --room-walk-steps 0 --join-avatar 0 --answer-requests --state 0 --recruiting 0 \
  --answer-talk --can-talk 0 --initiate-talk --initiate-delay 3 \
  --after-approach 0x06:0001000000 --trade-reply --complete-trade \
  --trade-template offer.pb8 --trade-nickname POKELDN --src-var 0x2B7F4C12
```

遇到 `Connect failed with status code 1` 时重试（[会话](bdsp_session.md)）。重复的
`--trade-template` 会排入多次交换，最后一项会再次提供。每次运行都要使用新的 `--src-var`。
`--complete-trade` 允许主机存档；没有它，交换会在最后一次确认处停下。角色走进房间后：
Y、通信菜单、交换宝可梦。

要主持，先启动主机；玩家以同样的方式进入房间，并选择 Y、通信菜单、交换宝可梦：

```bash
./.venv/bin/python bin/bdsp_host.py --offer offer.pb8 --complete-trade --capture host.jsonl
```

`--offer` 是一个合法的 PB8，其 PID 在存档中不存在；重复给出会排入多次交换。`--password 00000000`
会主持一个密码房间。参见[晶灿钻石与明亮珍珠](bdsp.md)。

## 传说 阿尔宙斯

`bin/pla_host.py` 针对主机的连接密码主持；`bin/pla_join.py` 加入它的搜索，每次交换用一次重复的
`--offer`，并在被移交时承担主机角色（[传说 阿尔宙斯](pla.md)）。

```bash
./.venv/bin/python bin/pla_host.py --code 00000000 --channel 6 --seconds 1800 \
  --session-update --sustain --clock --data-exchange --data-exchange-name POKELDN \
  --data-exchange-id 11223344 --game-channel --trade-box --trade-box-record offer.pa8 \
  --offer-out received.pa8
./.venv/bin/python bin/pla_host.py --ip-host --our-ip 172.16.86.128 --code 00000000 ...   # emulated console, no radio
```

主机：祝庆村的 Simona，交换、附近的人，输入相同的八位密码，提供一只宝可梦并确认。
`--offer-out` 会接收每条收到的记录（`-2` 及之后），`--trade-box-collect DIR` 收集主机显示的
所有记录；重复的 `--trade-box-record` 会排入多次交换。`pokeldn.pla.pokemon`
可以构建一条记录。

## 朱与紫

pokeldn 可以主持（`bin/sv_host.py`）或加入（`bin/sv_join.py`）。

```bash
./.venv/bin/python bin/sv_host.py --seconds 240 --player-name POKELDN \
  --rtt-probe --net-property --clock --net-stations 4 --scarlet-response \
  --record-delay 0.17 --announce --announce-delay 5.25 \
  --send-at 6.00:0x7c:1:b90101b902b90280800001 \
  --trade-offer offer.hex --offer-after-open 8
```

主机：X、宝可梦入口、连接交换、离线、不设密码、搜索。重复的 `--trade-offer`
会排入多次交换。参见[朱与紫](sv.md)。

太晶团体战：`--raid-seed` 主持一场（宝可梦入口、太晶团体战、连接密码 4970），`--raid-reward
ITEM:QUANTITY` 替换奖励，`--raid-pokemon` 是 pokeldn 的宝可梦，`--raid-event FOLDER` 使用
Project Pokemon 的
[EventsGallery](https://github.com/projectpokemon/EventsGallery) 中的宝可梦入口新闻事件，
`--raid-players N`（最多 3）等待 N 台主机，`--raid-partner TRAINER` 为空位挑选 NPC 伙伴。
`bin/sv_join.py --raid-pokemon FILE` 加入主机的团体战。参见[太晶团体战](sv_raid.md)。

## 传说 Z-A

主机：连接交换、本地通信，用密码 00000000 搜索。

```bash
# host: start it first, then search on the console
POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/za_host.py --keys prod.keys --trade-offer offer.bin --capture zh.jsonl
# join
./.venv/bin/python bin/za_join.py --channels 1,6,11 --dwell 0.35 --seconds 900 \
  --hold 450 --quiet-seat 25 --connect-timeout 6 --game --trade-offer offer.bin --offer-delay 4
```

重复的 `--trade-offer` 会排入多次交换；在主机上按 B 结束会话。`--offer-out FILE` 保存主机
提供的宝可梦。模拟主机：`--ip-host --our-ip IP --comm-id ffffffffffffffff`
（主持）或 `--ip-join --host-ip IP --our-ip IP --comm-id ffffffffffffffff`（加入）。提供文件为
354 字节（9 字节头、344 字节记录、1 个尾字节）；`pokeldn.gen9.build` 负责构建该记录。
参见[传说 Z-A](za.md)。

## 诊断

- `tools/ldn/ldn_scan.py` 列出可发现的 LDN 网络；`esp32_sniff.py` 让第二块板子成为针对
  某个信道、某个 MAC 的空口嗅探器。
- `POKELDN_ESP32_TRACE=FILE` 记录板子的串口流量和计数器；每个入口上的 `--capture FILE`
  会把协议跟踪写成 JSONL。
- [主机实现](frlg_host.md)：组件布局、协议流程、时序、关闭。
