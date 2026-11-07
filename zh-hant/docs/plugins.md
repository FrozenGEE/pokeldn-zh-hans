---
title: 外掛
---
# 外掛

外掛為 pokeldn 新增工具、遊戲、無線電和戰鬥伺服器，並且可以加入或自行承載一個 LDN 網路。它是一個裝著 Python 檔案並帶 `plugin.toml` 的資料夾，打包成單個 `.pokeplugin` 檔案發行。第三方外掛不由 pokeldn 分發、稽核或提供支援。

程式碼：`pokeldn/plugins.py`（載入器與 API）、`pokeldn/app/plugin_store.py`（軟體包）、`pokeldn/ldn/radios.py`（無線電查詢）、`gui/views/plugins.py`（頁面）。示例：`examples/plugins/hello`（一個工具）和 `examples/plugins/test_kit`（API 的每一部分）。

## 安裝外掛

在 **外掛**（側邊選單底部）中，按 **瀏覽** 下的 **安裝**，或者把 `.pokeplugin` 拖到 **已安裝** 上，或按 **新增外掛**；然後接受風險提示頁。它的工具會出現在遊戲頁上，並標有「Plugin: ...」。每個外掛對應一張卡片，可用來開啟和關閉、從檔案更新、顯示其資料夾和頁面，以及移除它（可選連同其儲存的資料一起刪除）。每次安裝和更新都會顯示風險提示頁；手動複製進來的外掛會在首次開啟時詢問。啟動時導致應用關閉或卡死的外掛會在下次啟動時被關閉。

外掛以 Python 形式在 pokeldn 內執行，可完全訪問檔案、金鑰、網路和板子。軟體包裡的任何內容在被安裝並開啟之前都不會執行。

### 來源

來源是一份公開發布的外掛 JSON 列表。**來源** 會關注這些列表；**瀏覽** 會列出其中的外掛。`Decryptu/pokeldn-decrypt-plugins` 始終會被關注。移除一個來源會保留它的外掛。

| 在來源下輸入 | 讀取的列表 |
|---|---|
| `OWNER/REPO` 或 `https://github.com/OWNER/REPO` | `https://raw.githubusercontent.com/OWNER/REPO/HEAD/pokeldn-source.json` |
| 以 `.json` 結尾的 HTTPS 地址 | 該檔案 |
| 任何其他 HTTPS 地址 | 該資料夾中的 `pokeldn-source.json` |

```json
{"schema": 1, "name": "My plugins", "homepage": "https://github.com/me/my-plugins",
 "plugins": [{"id": "my-plugin", "name": "My plugin", "version": "1.0.0", "api": "1.6",
   "description": "...", "author": "me", "download": "https://.../my-plugin-1.0.0.pokeplugin",
   "sha256": "64 hex digits", "size": 46302, "icon": "https://.../icon.png", "homepage": "https://..."}]}
```

缺少 `id`、`version`、HTTPS 的 `download` 或 `sha256` 的條目，或者 id 重複的條目，會被略過；`schema` 不是 1 的會被拒絕；SHA-256 不符的下載會在讀取之前被拒絕；id 與條目不符的軟體包會被拒絕。風險提示頁和簽名檢查仍會執行。來源會在啟動時（設定中的更新開啟）和重新整理時讀取；最後一次列表緩存於 `plugins/.source-cache/`，關注列表為 `plugins/.sources.json`。外掛從它來自的來源更新；從檔案安裝的外掛，則從第一個列出它的來源更新，否則使用它的 `updates`。

```bash
python scripts/plugin_source.py my-plugin-1.0.0.pokeplugin -o pokeldn-source.json --name "My plugins" \
    --download "https://github.com/me/my-plugins/releases/download/{id}-{version}/{file}"
```

已經以更高版本列出的條目會保留。

### 防護欄

有兩項檢查可以阻止明顯的危害；兩者都不是沙箱。安裝介面會列出這些 Python 檔案會做什麼：網路、其他程式、刪除檔案、原生程式碼（`ctypes`、`cffi`）、執行時執行的程式碼（`exec`、`eval`、`compile`、`marshal`）、提到 `prod.keys`，或者它無法讀取的編譯檔案。當外掛的程式碼位於呼叫棧上時，一個審計鉤子（`pokeldn/plugin_guard.py`）會在以下情況丟擲 `PermissionError`：

| 拒絕 | 允許 |
|---|---|
| 刪除、清空、移動或覆蓋外掛資料夾之外的檔案 | 在它的資料夾、資料資料夾、庫、會話、日誌和臨時資料夾中進行同樣的操作 |
| 啟動 `rm`、`del`、`rd`、`Remove-Item`、`shred`、`dd`、`format`、`mkfs`、`diskutil`、`diskpart`、`sudo`、`su` 及類似命令，無論直接啟動還是在 shell 中啟動，或任何帶 `-delete` 或 `--no-preserve-root` 的命令 | 任何其他程式；在任何位置建立檔案 |

外掛呼叫的 pokeldn 程式碼會被檢查；呼叫棧上沒有外掛的程式碼永遠不會被檢查。

## 製作外掛

    my-plugin/
        plugin.toml        what the plugin is
        plugin.py          register(api): what it adds
        hello.py           a tool's script
        icon.png           optional, square, 96 x 96
        mylib_common.py    optional shared module (the folder is on sys.path: use a unique name)

```toml
id = "my-plugin"            # required: lowercase letters, digits, dots, dashes, underscores
name = "My plugin"
version = "1.0.0"           # compared on update
author = "Your name"
description = "Shown on the install screen and the card."
homepage = "https://example.org/my-plugin"   # optional
updates = "https://github.com/you/my-plugin" # optional, see Updates
api = "1.1"                 # required: lowest API needed; 1 means 1.0
icon = "icon.png"           # optional
library = "My files"        # optional (1.7), see A library
library_sort = "name"       # optional (1.8)
module = "plugin"           # optional; the module holding register()
exclude = ["tests"]         # optional; left out by pack_plugin.py
```

巢狀超過 64 層陣列或表的 `plugin.toml` 或語言包檔案會被拒絕且不解析（`pokeldn.plugins.toml_loads`）；字串和註釋中的括號不計入。

當外掛開啟時，在應用中以及它啟動的每次執行中，都會執行 `register(api)`：

```python
from pokeldn.plugins import Field, Game, Tool

def register(api):
    api.add_tool("frlg", Tool(
        "my-hello", "Hello", "hello.py", "Says hello.",       # key, name, script, summary
        ("Nothing to do on the console.", "Press Start."),    # console steps
        fields=(Field("--name", "Your name", default="Red"),),
        fixed=("--trainer", "{ot}"),                          # always passed
    ))
```

### 工具行（1.12）

遊戲的列表為每個活動顯示一行（[遊戲頁](gui.md#the-games-page)）。沒有 `activity` 的工具自成一行。設定了 `activity` 的工具會加入該行，並由它的 `variant` 按鈕來展示：

```python
Tool("my-lan-trade", "Trade over my LAN", "lan.py", "Trades over this computer's network.", (),
     activity="trade", variant=(("role", "host"), ("link", "lan")))
```

| `activity` | 該行 |
|---|---|
| `trade`、`gift`、`max-raid`、`lair`、`tera-raid`、`circle` | 交換、神秘禮物、極巨團體戰、極巨大冒險、太晶團體戰、聯盟集友圈 |

| 軸 | 選項 | 按鈕 |
|---|---|---|
| `role` | `host`、`join` | pokeldn：Hosts（你的主機加入）、Joins（你的主機主持） |
| `link` | `board`、`lan`、`online` | 連線方式：Board、不用板子的 Wi-Fi、線上 |
| `mode` | `quests`、`encounters` | 模式 |

`pokeldn.app.catalog.AXES` 和 `ACTIVITIES` 就是這些列表。`add_tool` 會拒絕未知的活動或選項，以及該遊戲那一行中另一個工具已經佔用的變體：應用永遠無法顯示它。

### 工具的指令碼

應用會匯入指令碼以呼叫 `build_parser()`（進階選項卡），然後把它作為子程序在會話資料夾中執行。工作應放在 `if __name__ == "__main__"` 之下；頂層的工作會破壞遊戲頁。

| 指令碼 | 應用 |
|---|---|
| 列印一行 | 在輸出中顯示它 |
| 列印 `[done] trade N complete`（`pokeldn.ldn.show_done()`） | 勾掉一個排隊的交換 |
| 以 0 / 非 0 退出或丟擲異常 | 完成 / 失敗並顯示回溯 |
| 收到 `KeyboardInterrupt` | 按下了停止；15 秒內退出，否則程序會被結束 |
| `pokeldn.popup`（1.2）、`popup.choose`（1.7） | 任意頁面上的彈出視窗；答案會返回 |
| `pokeldn.progress.show(done, total, title, unit)`（1.7） | 帶有速率和剩餘時間的進度條（[進度](gui.md#progress)） |
| `pokeldn.panel`（1.8） | 狀態卡片和庫註釋（[狀態卡片](#status-cards-18)） |

彈出視窗會立即返回它的 id；答案稍後以回撥形式到達，可能在任意執行緒上：

```python
answers = queue.Queue()
popup.set_dispatcher(answers.put)       # run callbacks from the loop below
asked = popup.confirm("Trade the shiny?", "Your partner offers a shiny Gholdengo.", "Trade", "Skip",
                      on_agree=lambda: print("trading"), on_disagree=lambda: print("skipping"),
                      tone="warning")
while not finished():
    try:
        answers.get(timeout=0.5)()
    except queue.Empty:
        pass
popup.cancel(asked)                     # closes it; no callback fires
```

### 執行啟動器（1.13）

工具的腳本可以先準備好自己的檔案，然後在同一次執行中執行內建啟動器，無線電和停止都由
啟動器管理。給它的解析器加上 `--keys`，應用就會傳入設定中的 `prod.keys`。

```python
from pokeldn.plugins import run_launcher

status = run_launcher("bin/frlg_mg_host.py", ["--live", "--keys", args.keys, "--save-backup", path])
```

`run_launcher` 傳回啟動器的退出狀態；130 表示停止。腳本會在它之後繼續執行，因此一個工具
可以依次執行多次會話。`bin/frlg_mg_host.py` 的穩定選項：

| 選項 | 會話 |
|---|---|
| `--save-backup FILE`、`--save-resume-dir DIR` | 把主機的存檔寫入 `FILE` |
| `--save-restore-emerald FILE` | 在主機最新存檔旁放入一份綠寶石存檔，供同一次啟動中隨後的 ROM 傳輸使用 |
| `--rom-transfer ROM`、`--rom-base ROM` 或 `none`、`--block-repeat N`、`--inter-block-gap-frames N` | 把 ROM 傳進正在執行的遊戲（[The ROM transfer](rse_switch_build.md#the-rom-transfer)） |

### 外掛可以匯入什麼

釋出的應用帶有 Python 3.13，且沒有 `pip`：

| 內容 | 來源 |
|---|---|
| 標準庫 | 隨附，除了 `multiprocessing`、`tkinter`、`curses`、`venv`、`ensurepip`、`profile`、`cProfile`、`pstats`、`trace`、`compileall`、`modulefinder`、`pyclbr`、`tabnanny` 以及其他平臺的模組（`scripts/pack_app.py`、`PLUGIN_STDLIB`） |
| `trio`、`pycryptodome`（`Crypto`）、`zstandard`、`pyserial`（`serial`）、`websockets`、`certifi`、`bleak`、`unicorn`、`flet` | pokeldn 自身的依賴，版本見 `requirements.txt` |
| `ldn`、`pokeldn` | 只有下表中的部分是穩定的 |
| 純 Python 模組 | 外掛的資料夾 |

編譯型軟體包（`numpy`、`Pillow`）只在裝有它們的原始碼執行中可用。

### 欄位

| `kind` | 輸入 | 傳參形式 |
|---|---|---|
| `text`（預設） | 文本框 | `--flag VALUE` |
| `number` | 數字框 | `--flag VALUE` |
| `choice` | 由 `choices=((value, label), ...)` 構成的下拉選單 | `--flag VALUE` |
| `switch` | 開關 | 開啟時 `--flag` |
| `file` | 檔案選擇器，`exts=("bin",)` | `--flag PATH` |

`help=`、`default=` 和 `hidden=True`（進階選項卡）適用於任何欄位；其餘內容在 `pokeldn/app/catalog.py` 中。`Field.identity`（1.5）是為經過翻譯的位置引數欄位提供的穩定設定鍵。`fixed` 可以攜帶 `{ot}`、`{tid}`、`{sid}`、`{language}`、`{gender}`、`{received}`、`{stamp}` 和 `{keys}`（1.7，設定中的 `prod.keys`；接受 `--keys` 的解析器無論如何都會得到它）。

### 外掛保留什麼

更新會替換資料夾。需要長期保留的檔案放在 `api.data` 中，或者在指令碼中通過 `pokeldn.plugins.data_folder("my-plugin")` 獲取：`plugin-data/<id>`，只有在被要求時才會在移除時刪除。

### 庫（1.7）

`library = "My files"` 對應 `Documents/pokeldn/My files`（設定了 `POKELDN_DATA` 時位於其下），由 `api.library` 或 `pokeldn.plugins.library_folder("my-plugin")` 返回，首次使用時建立。防護欄允許在其中進行任何寫入，安裝介面會列出它，移除外掛時會保留它。遊戲頁會在外掛的工具下列出它的檔案，玩家可以在那裡新增、重新命名和刪除它們；以 `.` 開頭或以 `.part` 結尾的名字會被隱藏（先寫在一個這樣的檔案裡，然後重新命名）。順序由玩家選擇，否則使用 `library_sort`（`name`、`name-desc`、`date`、`date-desc`、`size`、`size-desc`），再否則為 `date-desc`；名字按自然順序排序。名字最多 40 個字母、數字、空格、`.`、`-`、`_`；pokeldn 自己的資料夾（`Bank`、`Saves`、`Received`……）、Windows 裝置名和另一個外掛的庫都會被拒絕。

### 狀態卡片（1.8）

`pokeldn.panel` 列印 `[panel]` 行；應用會在工具的頁面上繪製卡片，在庫檔案上繪製註釋，把它們儲存在 `plugin-panels/<id>.json` 中，並隨外掛一起刪除。

```python
panel.show("console", "Pokémon: Let's Go, Pikachu!", ["System version\t23.0.1"],
           image=icon, chips=[("Version", "1.0.2")], tone="ok")
panel.annotate("Game 1.0.2.nsp", state="ok", text="Every signature checks", image=icon)
```

| 呼叫 | 顯示 |
|---|---|
| `panel.show(id, title, lines=(), *, image=None, chips=(), tone="info")` | 卡片 `id`，替換最後一張；一行是文本或 `label<TAB>value`；`tone` 為 `info`、`ok`、`warning`、`error` |
| `panel.clear(id)` | 移除它 |
| `panel.annotate(name, *, state="ok", text="", image=None)` | 把庫檔案標記為 `ok`、`bad` 或 `checking` |
| `panel.unannotate(name)` | 移除註釋 |

限制：id 為 1 到 32 個 `[a-z0-9_-]` 字元；每個外掛 8 張卡片；標題 80 個字元，12 行、每行 200 個字元，6 個標籤、每個 40 個字元；影像為資料資料夾或庫中不超過 2 MB 的 PNG 或 JPEG。註釋跟隨檔名。超出限制會丟擲 `ValueError`；無法讀取的 `[panel]` 行會顯示在輸出中。

### 自己的遊戲

```python
api.add_game(Game("my-game", "My game", "Mine", "", (tool_one, tool_two)), icon="icon.png")
```

`Game(key, name, short, doc, tools)`；`api.add_tool("my-game", tool)` 可以新增更多工具。

### 無線電

`api.add_radio(scheme, install, label)` 會在外掛下的 **無線電** 中列出一個無線電；一次執行會在其第一次無線呼叫之前呼叫 `install(argument, log)`。`install` 用非同步上下文管理器呼叫 `ldn.wlan.set_factory(factory)`，產出一個 `ldn.wlan.Factory`；`pokeldn/ldn/esp32_wlan.py` 是參考實現。應用以 `POKELDN_RADIO=myradio:` 的形式執行它；在命令列上，引數跟在冒號之後。

### LDN 網路（1.7）

`pokeldn.ldn.network` 使用無線電的 IPv4 協議棧（ESP32 板子或 ldnrs）加入或承載網路。

```python
with network.join(COMM_ID, keys=args.keys, password=PASSPHRASE, name="My game") as net:
    net.add_protocol(6, lambda src, dst, segment: segments.put((src, segment)))
    while not net.send_ip(6, net.host_ip, first_segment):    # False until ARP resolves
        time.sleep(0.1)
```

| 名稱 | 說明 |
|---|---|
| `join(comm_id, *, keys, password, nickname, app_version, name, log, timeout)` | 加入廣播 `comm_id` 的網路；無人應答時丟擲 `RuntimeError` |
| `host(comm_id, *, keys, password, nickname, application_data, scene_id, app_version, max_participants, channel, protocol, log, timeout)` | 開啟一個可供主機加入的網路 |
| `Network.ip`、`.mac`、`.host_ip`、`.broadcast`、`.ssid`、`.comm_id`、`.application_data` | 地址與廣播 |
| `Network.participants` | 就座的站點：`.index`、`.ip`、`.mac`、`.name` |
| `Network.add_protocol(number, handler)`、`.remove_protocol(number)` | 每個重組後的 IPv4 包呼叫 `handler(src_ip, dst_ip, payload)`，在無線電迴圈上執行；UDP（17）仍由協議棧處理；異常會丟棄該包 |
| `Network.send_ip(protocol, dst_ip, payload)` | 一個包，按 1500 分片；ARP 未決期間返回 `False` |
| `Network.udp_socket(port)` | `sendto`、`recvfrom`、`setblocking`、`settimeout`、`fileno`、`close` |
| `Network.set_application_data(data)` | 一條新的廣播 |
| `Network.error`、`.close()` | 結束的原因；離開。是一個上下文管理器 |
| `pokeldn.ldn.radio_lost()` | 無線電離開的原因，可據此與「停止」區分 |

通過板子的吞吐量約為 0.5 MB/s。

### 戰鬥伺服器

戰鬥伺服器為 `bin/sv_host.py --raid-serve [NAME]` 執行朱 / 紫的團體戰戰鬥（[承載戰鬥](sv_raid.md#serving-the-battle)）。`api.add_battle_server("sv", name, factory, label)` 註冊它；`factory(bootstrap, partners)` 會帶著引導位元組和兩個夥伴的 0x158 位元組記錄，在網路迴圈之外被呼叫。

| 成員 | 作用 |
|---|---|
| `start(now)` | 第一幀；返回推動了戰鬥的幀 |
| `run(until)` | 以 30 幀/秒推進到 `until`（至少一幀）；返回值相同 |
| `t` | 伺服器時鐘，單位為秒 |
| `receive(slot, message)` | 來自 `slot` 的 32 位元組頭加正文 |
| `sent(slot)` | 自上次呼叫以來為 `slot` 排隊的訊息 |

槽位：0 為程式方的寶可夢，1 為 Boss，2 為主機，3 和 4 為夥伴。出現異常會停止承載，主機將自行進行戰鬥。

### 提供的寶可夢編輯（1.10）

`api.add_offer_edit(game, edit, label="")` 會對 `game`（`frlg`、`lgpe`、`swsh`、`bdsp`、`pla`、`sv`、`za`）的內建啟動器從檔案準備的每一隻寶可夢執行 `edit(record) -> record`：交換提供的寶可夢、排隊中的提供、團體戰夥伴、為接收方重製的神秘禮物寶可夢。記錄就是 PKHeX 讀取的檔案位元組（`pokeldn.pokemon.RECORD_SIZES`，無論是否加密）；`SERVICE.check(game, path)` 可讀取一條。編輯返回要提供的記錄。

```python
def rename(record):              # FireRed: the nickname at +0x08 is outside the checksum
    out = bytearray(record)
    out[8:18] = bytes((0xC6, 0xBE, 0xC8)) + b"\xff" * 7      # "LDN"
    return bytes(out)

def register(api):
    api.add_offer_edit("frlg", rename, "Renamer")
```

| 步驟 | |
|---|---|
| 1 | 啟動器自身的編輯（提供選項、新的 PID、遊戲的格式） |
| 2 | 每個外掛的提供編輯，按載入順序；執行日誌會記錄 `the plugin LABEL edited the offer` |
| 3 | PKHeX 的合法性檢查 |

PKHeX 的合法性檢查是每次提供的最後一步，沒有外掛能關閉它：如果編輯的結果被 PKHeX 拒絕，執行會以 PKHeX 給出的原因停止。丟擲異常或沒有返回位元組的編輯會以外掛的標籤停止執行。啟動器讀取檔案時會執行編輯，交換過程中重製神秘禮物寶可夢時會再次執行。

### 打包、測試、簽名與更新

```bash
python scripts/pack_plugin.py my-plugin --key ~/my-plugin-signing.pem
POKELDN_PLUGINS=~/my-plugin python -m pokeldn --plugins            # lists plugins and load errors
POKELDN_PLUGINS=~/my-plugin python -m pokeldn my-hello -- --name Blue
POKELDN_PLUGINS=~/my-plugin python gui/main.py
```

`pack_plugin.py` 會寫出 `my-plugin-1.0.0.pokeplugin`，並像應用那樣檢查它；隱藏檔案和 `exclude` 中的內容不會被打包。任何 zip 都可以，只要 `plugin.toml` 位於其頂層或某個頂層資料夾中，且沒有越界路徑和符號連結。`POKELDN_PLUGINS` 會為該程序及其執行開啟一個資料夾。在 `register` 中丟擲異常、需要另一個 API 或重複使用某個鍵的外掛不會新增任何東西，它的卡片會顯示原因。Python 軟體包也可以通過 `pokeldn.plugins` 入口點組註冊。

`--key` 會用 Ed25519 金鑰簽名（首次使用時建立），並列印其指紋（`ABCD-EFGH-IJKL-MNOP`）。`plugin.sig` 儲存公鑰，以及針對 id、版本和每個檔案的 SHA-256 的簽名。請保管好金鑰並做好備份，同時公開指紋。

| 應用看到 | 它會 |
|---|---|
| 簽名不匹配 | 拒絕該檔案 |
| 新簽名外掛 | 顯示指紋，並按 id 記住該金鑰 |
| 使用已記住金鑰的更新 | 顯示「Signed by the same author」 |
| 另一個金鑰，或簽名後變為未簽名 | 以紅色警告並要求二次確認 |
| 未簽名且從未簽名過 | 顯示「Not signed」 |

| `updates` | 應用讀取 |
|---|---|
| `https://github.com/OWNER/REPO` | 最新發布的標籤（`v1.3.0` 或 `1.3.0`）和第一個 `.pokeplugin` |
| 任何其他 HTTPS 地址 | `{"version": "1.3.0", "url": "https://.../my-plugin-1.3.0.pokeplugin", "page": "..."}` |

在設定中開啟更新後，這些會在啟動和重新整理時檢查；有更新的版本時會顯示 **Update to 1.3.0**，點選後會下載並開啟安裝介面。HTTP 僅對 `127.0.0.1` 和 `localhost` 接受。

## 語言包（1.5）

語言包是一種純資料外掛；`name` 顯示在設定的應用語言中，`locale` 是它的標籤。

```toml
id = "community-zh-hans"
name = "簡體中文"
version = "1.0.0"
api = "1.5"
locale = "zh-Hans"
strings = "strings.toml"
```

`strings.toml` 在帶引號的鍵下儲存文本值（`"bank.bank_676c47" = "寶可夢銀行"`）。錯誤的 TOML、非文本值和錯誤的格式語法會在安裝時被拒絕；損壞的語言包會回退到英文。選擇語言包會開啟它，並需要重啟。缺失的鍵使用其內聯的英文預設值。像 `{value0}` 這樣的佔位符可以移動位置，但必須保留名稱和規格；`{{` 和 `}}` 是字面量花括號；格式化失敗的翻譯會使用英文。

```bash
python scripts/extract_strings.py [--check]     # writes pokeldn/app/data/strings.en.toml
python scripts/pack_plugin.py examples/plugins/pseudo -o pseudo.pokeplugin
python scripts/check_language_pack.py PACK_FOLDER   # what the pack lacks against this release
```

`check_language_pack.py` 會列出未翻譯的字串和工具幫助、該版本已不再有的鍵，以及佔位符與英文不同的翻譯；佔位符不一致時它會以 1 退出。

測試會檢查模板與源匹配，並拒絕帶有兩個預設值的鍵。語言包從模板的翻譯副本開始；`examples/plugins/pseudo` 是一個區域性的偽語言環境。

### 額外資源（1.9）

```toml
api = "1.9"
messages = "messages.toml"
templates = "templates.toml"
terms = "terms.toml"
help = "help.toml"
documents = "docs"
font_family = "Noto Sans CJK SC"
```

| 條目 | 鍵 | 值 |
|---|---|---|
| `messages` | 模組的英文原文，逐字 | 它的翻譯 |
| `templates` | `"Could not open {path}: {reason}"` | 欄位相同的翻譯 |
| `terms` | 遊戲術語（1 到 200 個字元，最多 10000 條） | 它的翻譯 |
| `help` | `"TOOL-KEY:--option"` | 該標誌在進階選項卡中的說明 |
| `documents` | 由 `guide.md` 和 `docs/` 頁面按名稱組成的資料夾 | |
| `font_family` | 字型，最多 100 個字元 | 文本字型；CJK 回退仍然保留 |

路徑必須留在外掛資料夾內。這些用來翻譯來自遊戲模組、PKHeX 和外掛的文本：一條訊息會先在 `messages` 中整體嘗試，然後是 `templates`，然後按句子，最後在詞邊界處替換 `terms`。一個模板有 1 到 8 個由字面文本分隔的普通命名欄位，最多 2048 個字元，按字面匹配，最長者優先，作用於最長 4096 個字元的訊息；名為 `term...` 或 `message...` 的欄位本身也會被翻譯，深度為 4。如果某個值整體上是一個物種、招式、特性、性格、屬性或球的名字，且沒有術語覆蓋它，則採用 PKHeX 的名稱。PKHeX 的名稱和合法性報告對 `ja`、`fr`、`it`、`de`、`es`、`ko`、`zh-Hans`、`zh-Hant` 跟隨區域設定（`zh` 帶 `TW`、`HK`、`MO` 時為 `zh-Hant`）。
當標題數量匹配時，翻譯後的頁面保留英文錨點，否則用 `<a id="NAME"></a>` 設定一個；front matter 中的 `title` 會重新命名側邊欄中的頁面。

檔名、銀行和佇列摘要、GTS 列表、設定、會話日誌、無線電輸出和 `[done]` 行保持英文。設定中的訓練家語言決定生成的寶可夢的語言。

## 外掛測試套件

`examples/plugins/test_kit` 會新增自檢（檢查 API 的每一部分，列印 PASS 或 FAIL，留下一張「上次自檢」卡片）、模擬會話（交換步驟和 `[done]` 行）、故意失敗、火紅 & 葉綠下的「Hello from a plugin」，以及測試套件無線電，它不承載任何東西。

## 版本

API 採用 `major.level` 形式；外掛的 `api` 是它需要的最低版本。新增功能會提升 level（外掛需求更高時會以「Update pokeldn」拒絕）；移除功能或改變含義會提升 major。仍在服務的舊 major 會連同其最後一個版本列在 `DEPRECATED` 中；已不再服務的會低於 `API_OLDEST` 並被拒絕。外掛自己的 `version` 只決定是更新、重灌還是降級。

| API | 新增 |
|---|---|
| 1.0 | `add_tool`、`add_game`、`add_radio`、`folder`、`version` |
| 1.1 | `api.data`、`api.level`、`pokeldn.plugins.data_folder(plugin_id)` |
| 1.2 | `pokeldn.popup` |
| 1.3 | 程式介面面：構建器、禮物檔案、PKHeX 和板子 |
| 1.4 | 銀行匯入、記錄、目標、提供和交換完成 |
| 1.5 | 語言包外掛和字串查詢 |
| 1.6 | `add_battle_server` |
| 1.7 | `pokeldn.ldn.network`、`pokeldn.ldn.radio_lost`、`library` 和 `api.library`、`pokeldn.popup.choose`、`pokeldn.progress`、`{keys}` 記號 |
| 1.8 | `pokeldn.panel`、`library_sort` |
| 1.9 | 語言包的訊息、模板、術語、工具幫助、文件和字型偏好 |
| 1.10 | `add_offer_edit` |
| 1.11 | 火紅/葉綠 RNG：`lcg`、`rng_countdown.mon_from`、`scan`、`buffer_script.read_rng_trace` |
| 1.12 | `Tool` 的 `activity` 和 `variant`（[工具行](#a-tools-row-112)） |
| 1.13 | `run_launcher`、`pokeldn.switch.cartridge.read`，以及 `bin/frlg_mg_host.py` 的 ROM 選項（[執行啟動器](#running-a-launcher-113)） |

## API 版本 1

| 名稱 | 說明 |
|---|---|
| `api.add_tool(game, tool)` | 位於 `frlg`、`lgpe`、`swsh`、`bdsp`、`pla`、`sv`、`za` 或外掛自己的遊戲下的 `Tool` |
| `api.add_game(game, icon="")` | 一個遊戲分割槽 |
| `api.add_radio(scheme, install, label="")` | 一個無線電 |
| `api.add_battle_server(game, name, factory, label="")` | 一個團體戰戰鬥伺服器（1.6） |
| `api.add_offer_edit(game, edit, label="")` | 對內建啟動器的每次提供進行編輯，在 PKHeX 檢查之前（1.10，[提供的寶可夢編輯](#offer-edits-110)） |
| `api.folder` | 外掛的資料夾；對於軟體包為 None |
| `api.version`、`api.level` | 應用的 API，`1` 和 `13` |
| `api.data` | 保留的資料資料夾（1.1） |
| `pokeldn.plugins.data_folder(plugin_id)` | 在指令碼中獲取同樣的資料夾（1.1） |
| `api.library`、`pokeldn.plugins.library_folder(plugin_id)` | 庫資料夾（1.7，[庫](#a-library-17)） |
| `Tool`、`Field`、`Game` | 來自 `pokeldn.plugins` 的目錄型別 |
| `pokeldn.plugins.run_launcher(script, argv)` | 在本次執行中執行內建啟動器；傳回其退出狀態（1.13） |
| `pokeldn.ldn.show_done()` | 列印交換完成的行 |
| `pokeldn.popup.acknowledge(title, text="", *, id, label="OK", on_ack, tone)` | 單按鈕彈出視窗；返回 id（1.2，[彈出視窗](gui.md#pop-ups)） |
| `pokeldn.popup.confirm(title, text, agree, disagree, *, id, on_agree, on_disagree, on_dismiss, tone)` | 兩個按鈕；按 Esc 或點選外部會關閉；返回 id（1.2） |
| `pokeldn.popup.choose(title, text, options, *, id, on_choice, on_dismiss, tone)` | 2 到 8 個選項，`on_choice(index)`；返回 id（1.7） |
| `pokeldn.progress.show(done, total, title, unit="bytes")` | 進度條；`unit` 為 `bytes` 或 `items`（1.7） |
| `pokeldn.panel.show(id, title, lines=(), *, image, chips, tone)`、`clear(id)`、`annotate(name, *, state, text, image)`、`unannotate(name)` | 狀態卡片（1.8，[狀態卡片](#status-cards-18)） |
| `pokeldn.ldn.network` | LDN 網路（1.7，[LDN 網路](#ldn-networks-17)） |
| `pokeldn.ldn.radio_lost()` | 無線電離開的原因，或為空（1.7） |
| `pokeldn.popup.cancel(id)`、`available()`、`set_dispatcher(dispatch)` | 關閉彈出視窗；彈出視窗是否顯示；回撥在哪裡執行（1.2） |

這張表和下一張表就是受支援的介面面；其他任何匯入都可能在任何版本中變化。

## 程式介面（1.3，1.4 加入銀行，1.5 加入語言包，1.11 加入 RNG，1.13 加入卡帶）

外掛，或者在 pokeldn 原始碼檢出上執行的獨立程式，都可以使用這些；`tests/test_plugin_surface.py` 會逐一解析。

| 名稱 | 說明 |
|---|---|
| `python -m pokeldn --list`、`python -m pokeldn TOOL -- ARGS` | 工具鍵；使用設定中的訓練家執行 |
| `pokeldn.app.i18n.t(key, default, **fmt)`、`select(plugin_id)` | 字串查詢；選擇一個語言包，或用 `""` 選擇英文（1.5） |
| `pokeldn.app.catalog.GAMES` | 內建遊戲及其 `Tool`；應用傳入的標誌保持其名稱 |
| `pokeldn.pokemon.SERVICE.species(game)`、`.names(game, kind)` | 物種、`moves`、`items`、`bag`、`held`、`balls`，均為 `{"id", "name"}` 列表 |
| `pokeldn.pokemon.SERVICE.options(game, species, trainer)` | 一次提供可用的形態、性格、特性、道具和球 |
| `pokeldn.pokemon.SERVICE.make(game, species, trainer, level, shiny, nickname, version, options)` | 一隻合法的寶可夢；返回值與 `"file"` |
| `pokeldn.pokemon.SERVICE.paste(game, text, trainer)` | 作為 `make` 值的 Showdown 配置，附帶 `errors` |
| `pokeldn.pokemon.BuilderError` | PKHeX 拒絕或缺失，附帶一句給玩家的話 |
| `pokeldn.pokemon.NATURES` | 按索引排列的 25 個性格名稱 |
| `pokeldn.gifts.load(path, game=)`、`pokeldn.gifts.save(path, gift)` | `.pokegift`、`.wc3`、`.wc8`（[神秘禮物檔案](gifts.md)） |
| `pokeldn.swsh.gift_builder.KINDS`、`PRESETS`、`PRESET`、`OUTFITS` | 劍/盾的禮物種類、預設和服裝 |
| `pokeldn.swsh.gift_builder.blank(**changes)`、`record(state)`、`compile(state)`、`describe(state, name)` | 表單狀態、720 位元組記錄、禮物、玩家文本；`ValueError` 會指出錯誤的欄位 |
| `pokeldn.swsh.events.load()`、`by_key()`、`gift(key)` | 官方的劍/盾活動卡片 |
| `pokeldn.frlg.gift.builder.KINDS`、`PRESETS`、`PRESET`、`GIVERS`、`CARTRIDGES` | 火紅/葉綠的種類、預設、贈予者和卡帶 |
| `pokeldn.frlg.gift.builder.blank()`、`compile(state)`、`describe(state, name)` | 用於神秘卡片、新聞或主機程式碼的同類功能；`name` 根據卡帶 id 得到物種 |
| `gui.board.ports()`、`identify(port, blink=)`、`detect_chip(port)` | 序列埠以及板子的 `.firmware`、`.firmware_version`、`.protocol`、`.current` |
| `gui.board.download_firmware(say=)`、`image_for(kind, chip)`、`image_version(path)`、`flash(port, kind=)` | 校驗過的釋出映象和刷寫 |
| `pokeldn.app.bank.library()` | 預設的銀行資料夾；列出內容從不會建立它（1.4） |
| `pokeldn.app.bank.Entry`、`Imported`、`ImportedPokemon` | 銀行結果型別（1.4） |
| `pokeldn.app.bank.Imported.count(state)` | 某個狀態下的結果數（1.4） |
| `pokeldn.app.bank.entries(folder=)`、`find(entry_id, folder=)`、`data(entry)` | 記錄按最新在前，返回一條或 `None`，以及它的位元組（1.4） |
| `pokeldn.app.bank.import_file(path, trainers, folder=)` | 匯入寶可夢檔案或存檔；返回 `Imported`（1.4） |
| `pokeldn.app.bank.deposit(game, source, info, folder=)` | 把收到的檔案存入銀行；返回 `Entry`，若已存入則為 `None`（1.4） |
| `pokeldn.pokemon.SERVICE.check(game, path)` | PKHeX 檢查，即 `deposit` 所需的 `info`（1.4） |
| `pokeldn.app.bank.destinations(entry, trainer)`、`offer(entry, game, trainer)` | 按遊戲轉換；一個轉換後的提供（1.4） |
| `pokeldn.app.bank.edit(entry, fields)`、`remove(entry_id, folder=)` | 編輯暱稱、升級、招式、持有道具；刪除一條記錄（1.4） |
| `pokeldn.app.bank.TradeSession(offers, folder=)` | 本次執行按順序的提供（1.4） |
| `pokeldn.app.bank.TradeSession.advance(count)` | 應用累計交換數；`.completed` 是已見的最大值（1.4） |
| `pokeldn.app.received.trades_done(line)` | `[done] trade N complete` 行中的數量，或 `None`（1.4） |
| `pokeldn.frlg.rom.lcg.step(value)`、`.advance(value, n)`、`.distance(start, target)`、`.draws(value, count)` | 火紅/葉綠的 `gRngValue` 生成器：下一個狀態、向前 n 步、兩個狀態之間的步數、接下來的 `count` 個 `Random()` 結果及剩餘狀態（1.11，[RNG](frlg_rng.md)） |
| `pokeldn.frlg.rom.lcg.recover_wild_state(personality, ivs, max_gap=)` | 能生成某隻寶可夢的狀態，個體值按儲存順序（1.11） |
| `pokeldn.frlg.rom.rng_countdown.mon_from(state, tid, sid)`、`.scan(state, tid, sid, frames=, want=)` | 某個狀態構建的指令碼化 `CreateMon`：`personality`、`ivs`、`nature`、`shiny`；`frames` 內的閃光按鍵（1.11） |
| `pokeldn.switch.cartridge.read(path, keys=)` | `.gba` 或火紅/葉綠遊戲包中的 GBA 映像；`ValueError` 會指出問題所在（1.13） |
| `pokeldn.frlg.rom.buffer_script.read_rng_trace(dump)` | `--buffer-script rng-trace` 會話的 `--dump-file` 中的樣本（1.11） |

要停止一次啟動器執行，向它的 PID 傳送 SIGINT，15 秒後再發送 SIGTERM；絕不要用 `pkill -f`。

## 銀行整合（1.4）

外部前端使用 `pokeldn.app.bank`，並自行管理其佇列和程序；轉換需要 PKHeX 輔助程式（在原始碼中執行 `dotnet build -c Release services/pkhex`）。

| 型別 | 欄位 |
|---|---|
| `Entry` | `id`、`path`（原生記錄）、`game`、`species_id`、`shiny`、`summary`、`legal`、`tracker`、`created`（Unix 秒）、`origin`、`home_tracker`（`empty`、`made` 或 `""`，[HOME 追蹤號設定](gui.md#the-home-tracker-setting)） |
| `Imported` | `name`、`save`、`pokemon` |
| `ImportedPokemon` | `where`、`species`、`species_id`、`shiny`、`state`（`banked`、`already`、`refused`）、`game`、`detail` |
| `destinations` 值 | 按遊戲：`ok`、`reason`、`home_tracker` |
| `offer` 值 | `file`、`summary`、`species`、`shiny`、`legal`、`encounter`、`moves`、`report`、`home_tracker`、`bank`（來源 id） |

`trainers` 把遊戲鍵對映到 `{ot, tid, sid, language, gender}`。匯入會記住曾經匯入過的每條記錄。一次提供會把銀行記錄留在原處；把它的 `file` 作為啟動器的 `--offer-file` 傳入，且不要加 `--fresh-pid`，並在執行結束前保留它。直接執行目錄工具的指令碼，因為 `python -m pokeldn TOOL` 不接受提供。

```python
from pokeldn.app import bank, received

trainer = {"ot": "ASH", "tid": 1111, "sid": 2222, "language": 2, "gender": 0}
bank.import_file("main", {g: trainer for g in ("frlg", "lgpe", "swsh", "bdsp", "pla", "sv", "za")},
                 folder="tradebox-bank")
entry = next(iter(bank.entries(folder="tradebox-bank")), None)
if entry is None:
    raise ValueError("No Pokemon available in the Bank.")
if not bank.destinations(entry, trainer)["swsh"]["ok"]:
    raise ValueError("cannot go to Sword/Shield")
session = bank.TradeSession([bank.offer(entry, "swsh", trainer)], folder="tradebox-bank")

def on_launcher_line(line):
    if (count := received.trades_done(line)) is not None:
        session.advance(count)
```

每次執行一個 `TradeSession`，嚴格按提供順序，包含已構建的提供。只向它喂入已確認的數量；未完成的記錄會保留。`advance` 在數量錯誤時丟擲 `ValueError`，在 `OSError` 之後可以重試。檔案錯誤丟擲 `OSError`；PKHeX 失敗丟擲 `BuilderError`。`deposit` 信任 `SERVICE.check`；玩家檔案通過 `import_file` 進入。`folder` 預設為 `library()`。在匯入前設定 `POKELDN_DATA` 以隔離所有檔案。呼叫是同步的：讓 PKHeX 遠離 UI 執行緒。每個銀行資料夾只有一個寫入者；桌面應用旁邊的前端使用自己的資料夾。`TradeSession` 只改動銀行。
