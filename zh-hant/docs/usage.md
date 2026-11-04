---
title: 命令列用法
---

# 命令列用法

本頁列出各作品的命令列入口。請在倉庫根目錄下執行它們。
原始碼工具需要 Python 3.11+、Switch 的 `prod.keys`
（預設為 `~/.switch/prod.keys`，或用 `--keys PATH` 指定），以及一塊已刷好韌體的 ESP32 板子。
參見[支援的板子](hardware_esp32.md#supported-boards)和
[構建與刷寫](hardware_esp32.md#building-and-flashing)。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
dotnet build -c Release services/pkhex
export POKELDN_RADIO=esp32:auto
python -m pokeldn --list
python -m pokeldn --radio esp32:auto swsh-host --offer-file offer.pk8
```

交換工具需要 .NET 10 SDK。PyPI 上的 `ldn` 包是另一個庫。在 Windows 上請使用
`.venv\Scripts\Activate.ps1` 和 `$env:POKELDN_RADIO = "esp32:auto"`。`esp32:auto` 會挑選唯一的
USB 序列埠；`esp32:PORT` 則指定某一個（[無線設定](hardware_esp32.md#running)）。每個入口
都接受 `--help`。

## 火紅與葉綠

在主機上解鎖 Direct Corner，並準備至少兩隻 `.pk3` 隊伍成員。

```bash
./.venv/bin/python bin/frlg_trade_join.py --live -o output.pk3 PARTY1.pk3 PARTY2.pk3   # join the Switch's trade
./.venv/bin/python bin/frlg_trade_host.py -o output.pk3 PARTY1.pk3 PARTY2.pk3          # host a Direct Corner trade
```

主機提供 `PARTY2.pk3`，並把收到的內容寫入 `output.pk3`。預設值來自
`config/host.toml`，其次是 `config/host.local.toml`；命令列標誌會覆蓋這兩者
（`--print-effective-config`）。在 `Hosting Direct Corner` 之後：Direct Corner、Join Group、pokeldn 的
訓練家，然後選擇並確認。`--trades N`（1 到 6）提供槽位 0 到 N-1，每次交換一個；最後一個之後，
CANCEL、YES。

| 標誌 | 用途 |
|---|---|
| `--keys PATH` | `prod.keys` 的位置 |
| `--slot N` | 提供的隊伍成員，從 0 開始計數 |
| `--capture FILE` | JSONL 診斷抓包 |
| `--config` / `--local-config` / `--no-local-config` | 替換或停用某一層配置 |
| `--ot NAME`, `--version firered\|leafgreen`, `--id TID[:SID]` | 每次執行時覆蓋訓練家資訊（各為 0..65535；LinkPlayer ID 為 `(SID << 16) \| TID`） |
| `--verbose` | 逐資料包輸出；僅在配合 `--replay` 時，會讓即時鏈路卡住 |

[`pokeldn/config.py`](../pokeldn/config.py) 中的 `DEFAULT_TRAINER` 儲存其餘預設值。協議：
[鏈路協議](frlg_link.md)。

### 聯盟室

`--union-room` 會扮演中間的那個 NPC；主機會在約 10 秒後連線。一條鏈路只承載一次
交換（`union_room.c:1744`）。`--board-type normal` 在交換板上登記，`--union-room-chat`
配合 `--chat-message` / `--chat-file` 聊天，`--union-room-battle --battle-fight` 對戰（兩隻
30 級或以下的非蛋寶可夢）。

```bash
./.venv/bin/python bin/frlg_trade_host.py --union-room --union-room-keepalive 120 PARTY1.pk3 PARTY2.pk3
```

### 神秘禮物

`bin/frlg_mg_host.py` 沿神秘禮物、神秘卡片、好友的路徑傳送一張神秘卡片和投遞指令碼。
`--make-artifact` 會把傳送的位元組寫成 `.ram.lst`。目錄：[神秘禮物](frlg_gift.md)。

```bash
./.venv/bin/python -u bin/frlg_mg_host.py --gift beast-cutscene --flag-id 1005 --capture mystery-gift.jsonl
```

這隻野獸會跟隨御三家（妙蛙種子配水君，傑尼龜配炎帝，小火龍配雷公）。

### 不可思議的新聞

`--news` 沿神秘禮物、不可思議的新聞、好友的路徑提供服務。只有當新聞與主機上已有的內容
不同時，主機才會保留它；`--news-id N` 會強制使用一條新新聞。

```bash
./.venv/bin/python -u bin/frlg_mg_host.py --news berry --news-id 7
```

### 存檔備份與恢復

好友路徑會把 128 KB 的存檔複製到 `.sav`（約四分鐘），或把存檔寫回；未完成的恢復會讓
存檔保持原樣（[詳情](frlg_gift.md#save-backup-and-restore)）。

```bash
./.venv/bin/python -u bin/frlg_mg_host.py --live --save-backup backup.sav --save-resume-dir partial
./.venv/bin/python -u bin/frlg_mg_host.py --live --save-restore backup.sav
```

### 主機存檔

`save-dump` 讀取正在執行的存檔；`flash-patch` 重寫某個扇區中指定的位元組，並同時更新其
校驗和與計數器。寫入之前請先閱讀[構造扇區](frlg_rom.md#composing-a-sector-from-a-ram-snapshot)。
載荷：[主機上的程式碼](frlg_rom.md)。

```bash
./.venv/bin/python -u bin/frlg_mg_host.py --buffer-script save-dump --dump-block sav2 --dump-size 64 --dump-file dump.bin
./.venv/bin/python tools/frlg/dump_read.py dump.bin --block sav2
./.venv/bin/python -u bin/frlg_mg_host.py --buffer-script flash-patch --flash-id 0 \
  --flash-patch-offset 0x00 --flash-patch-hex cac9c5bfc6bec8ff --write-unsafe
```

## Let's Go 皮卡丘與伊布

pokeldn 可以主持，也可以加入。兩者都會提供 232 位元組的 PB7（`pokeldn.lgpe.pb7`；`--offer echo`
會返回主機的）；主持方的 `--first echo` 會回顯主機的身份訊息。主持方的 `--next-offer`
和加入方重複的 `--offer` 會排入後續交換；`--leave-after S` 會讓加入方離開。

```bash
./.venv/bin/python bin/lgpe_host.py --seconds 600 --player-name POKELDN \
  --first echo --our-trainer 41234:12345 --offer offer.pb7
./.venv/bin/python bin/lgpe_join.py --connect --connect-seconds 300 \
  --ack-peer-clock --ack-re-announce \
  --our-trainer 41234:12345 --offer offer.pb7
```

主機：Communiquer、Communication locale、Échange，連線密碼為皮卡丘 ×3，然後在搜尋
介面等待。模擬主機：`lgpe_host.py --ip-host --our-ip IP`。參見 [Let's Go](lgpe.md)。

## 劍與盾

主機：Y-Comm、連線交換、本地通訊，兩條訊息都按 A，然後在搜尋介面等待。

```bash
# join the console's session and trade: the console's own party snapshot is sent back, rewritten
POKELDN_RADIO=esp32:auto ./.venv/bin/python bin/swsh_connect.py --keys PROD_KEYS \
  --preset trade --offer-slot 1 [--offer-file your.pk8 --offer-file next.pk8 --fresh-pid] \
  --save-offered received.pk8

# or host, and let the console join: its snapshot is taken from this trade
POKELDN_RADIO=esp32:auto ./.venv/bin/python bin/swsh_host.py --keys PROD_KEYS \
  --offer-file your.pk8 --fresh-pid --received received.pk8 --channel 6 --seconds 900
```

`--code 12345678` 會針對連線密碼搜尋來主持。重複的 `--offer-file` 每次交換排入一個；第 N 次
交換寫入時帶字尾 `-N`。詳情：[交換](swsh_trade.md)。

神秘禮物：神秘禮物、領取禮物、通過本地無線。

```bash
./.venv/bin/python bin/swsh_gift_host.py --species 25 --level 25 \
  --move1 84 --move2 45 --move3 86 --move4 98 --nickname POKELDN --ot POKELDN --seconds 300
./.venv/bin/python bin/swsh_gift_host.py --record card.wc8 --seconds 300
```

`--set FIELD=VALUE` 設定記錄中的欄位（`shiny_type=3`、`held_item=236`），`--ribbon N` 新增一條
緞帶，`--dump FILE` 無需無線模組即可寫出記錄。如果某個道具 ID 在表中沒有對應行，當它的背包行
顯示時遊戲會中止。參見[神秘禮物](swsh_gift.md)。

## 晶燦鑽石與明亮珍珠

pokeldn 以一個角色的身份加入主機的聯盟室。主機：任意寶可夢中心 2F，左側櫃檯，選普通的
「是」（第一個選項），然後在聯盟室裡遠離牆壁處等待。

```bash
./.venv/bin/python tools/ldn/ldn_scan.py --channels 1,6,11 --dwell 0.8      # see the session
./.venv/bin/python bin/bdsp_connect.py --channels 1,6,11 --count 9 --connect 5 --join 6 \
  --hold 420 --reliable-ack --reliable-sweep 3 --room-walk 15 --room-pattern fixed \
  --room-walk-steps 0 --join-avatar 0 --answer-requests --state 0 --recruiting 0 \
  --answer-talk --can-talk 0 --initiate-talk --initiate-delay 3 \
  --after-approach 0x06:0001000000 --trade-reply --complete-trade \
  --trade-template offer.pb8 --trade-nickname POKELDN --src-var 0x2B7F4C12
```

遇到 `Connect failed with status code 1` 時重試（[會話](bdsp_session.md)）。重複的
`--trade-template` 會排入多次交換，最後一項會再次提供。每次執行都要使用新的 `--src-var`。
`--complete-trade` 允許主機存檔；沒有它，交換會在最後一次確認處停下。角色走進房間後：
Y、通訊選單、交換寶可夢。

要主持，先啟動主機；玩家以同樣的方式進入房間，並選擇 Y、通訊選單、交換寶可夢：

```bash
./.venv/bin/python bin/bdsp_host.py --offer offer.pb8 --complete-trade --capture host.jsonl
```

`--offer` 是一個合法的 PB8，其 PID 在存檔中不存在；重複給出會排入多次交換。`--password 00000000`
會主持一個密碼房間。參見[晶燦鑽石與明亮珍珠](bdsp.md)。

## 傳說 阿爾宙斯

`bin/pla_host.py` 針對主機的連線密碼主持；`bin/pla_join.py` 加入它的搜尋，每次交換用一次重複的
`--offer`，並在被移交時承擔主機角色（[傳說 阿爾宙斯](pla.md)）。

```bash
./.venv/bin/python bin/pla_host.py --code 00000000 --channel 6 --seconds 1800 \
  --session-update --sustain --clock --data-exchange --data-exchange-name POKELDN \
  --data-exchange-id 11223344 --game-channel --trade-box --trade-box-record offer.pa8 \
  --offer-out received.pa8
./.venv/bin/python bin/pla_host.py --ip-host --our-ip 172.16.86.128 --code 00000000 ...   # emulated console, no radio
```

主機：祝慶村的 Simona，交換、附近的人，輸入相同的八位密碼，提供一隻寶可夢並確認。
`--offer-out` 會接收每條收到的記錄（`-2` 及之後），`--trade-box-collect DIR` 收集主機顯示的
所有記錄；重複的 `--trade-box-record` 會排入多次交換。`pokeldn.pla.pokemon`
可以構建一條記錄。

## 朱與紫

pokeldn 可以主持（`bin/sv_host.py`）或加入（`bin/sv_join.py`）。

```bash
./.venv/bin/python bin/sv_host.py --seconds 240 --player-name POKELDN \
  --rtt-probe --net-property --clock --net-stations 4 --scarlet-response \
  --record-delay 0.17 --announce --announce-delay 5.25 \
  --send-at 6.00:0x7c:1:b90101b902b90280800001 \
  --trade-offer offer.hex --offer-after-open 8
```

主機：X、寶可夢入口、連線交換、離線、不設密碼、搜尋。重複的 `--trade-offer`
會排入多次交換。參見[朱與紫](sv.md)。

太晶團體戰：`--raid-seed` 主持一場（寶可夢入口、太晶團體戰、連線密碼 4970），`--raid-reward
ITEM:QUANTITY` 替換獎勵，`--raid-pokemon` 是 pokeldn 的寶可夢，`--raid-event FOLDER` 使用
Project Pokemon 的
[EventsGallery](https://github.com/projectpokemon/EventsGallery) 中的寶可夢入口新聞事件，
`--raid-players N`（最多 3）等待 N 臺主機，`--raid-partner TRAINER` 為空位挑選 NPC 夥伴。
`bin/sv_join.py --raid-pokemon FILE` 加入主機的團體戰。參見[太晶團體戰](sv_raid.md)。

## 傳說 Z-A

主機：連線交換、本地通訊，用密碼 00000000 搜尋。

```bash
# host: start it first, then search on the console
POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/za_host.py --keys prod.keys --trade-offer offer.bin --capture zh.jsonl
# join
./.venv/bin/python bin/za_join.py --channels 1,6,11 --dwell 0.35 --seconds 900 \
  --hold 450 --quiet-seat 25 --connect-timeout 6 --game --trade-offer offer.bin --offer-delay 4
```

重複的 `--trade-offer` 會排入多次交換；在主機上按 B 結束會話。`--offer-out FILE` 儲存主機
提供的寶可夢。模擬主機：`--ip-host --our-ip IP --comm-id ffffffffffffffff`
（主持）或 `--ip-join --host-ip IP --our-ip IP --comm-id ffffffffffffffff`（加入）。提供檔案為
354 位元組（9 位元組頭、344 位元組記錄、1 個尾位元組）；`pokeldn.gen9.build` 負責構建該記錄。
參見[傳說 Z-A](za.md)。

## 診斷

- `tools/ldn/ldn_scan.py` 列出可發現的 LDN 網路；`esp32_sniff.py` 讓第二塊板子成為針對
  某個通道、某個 MAC 的空口嗅探器。
- `POKELDN_ESP32_TRACE=FILE` 記錄板子的序列埠流量和計數器；每個入口上的 `--capture FILE`
  會把協議跟蹤寫成 JSONL。
- [主機實現](frlg_host.md)：元件佈局、協議流程、時序、關閉。
