---
title: 插件
---
# 插件

插件为 pokeldn 添加工具、游戏、无线电和战斗服务器，并且可以加入或自行承载一个 LDN 网络。它是一个装着 Python 文件并带 `plugin.toml` 的文件夹，打包成单个 `.pokeplugin` 文件发行。第三方插件不由 pokeldn 分发、审核或提供支持。

代码：`pokeldn/plugins.py`（加载器与 API）、`pokeldn/app/plugin_store.py`（软件包）、`pokeldn/ldn/radios.py`（无线电查找）、`gui/views/plugins.py`（页面）。示例：`examples/plugins/hello`（一个工具）和 `examples/plugins/test_kit`（API 的每一部分）。

## 安装插件

在 **插件**（侧边菜单底部）中，按 **浏览** 下的 **安装**，或者把 `.pokeplugin` 拖到 **已安装** 上，或按 **添加插件**；然后接受风险提示页。它的工具会出现在游戏页上，并标有「Plugin: ...」。每个插件对应一张卡片，可用来开启和关闭、从文件更新、显示其文件夹和页面，以及移除它（可选连同其保存的数据一起删除）。每次安装和更新都会显示风险提示页；手动复制进来的插件会在首次开启时询问。启动时导致应用关闭或卡死的插件会在下次启动时被关闭。

插件以 Python 形式在 pokeldn 内运行，可完全访问文件、密钥、网络和板子。软件包里的任何内容在被安装并开启之前都不会运行。

### 来源

来源是一份公开发布的插件 JSON 列表。**来源** 会关注这些列表；**浏览** 会列出其中的插件。`Decryptu/pokeldn-decrypt-plugins` 始终会被关注。移除一个来源会保留它的插件。

| 在来源下输入 | 读取的列表 |
|---|---|
| `OWNER/REPO` 或 `https://github.com/OWNER/REPO` | `https://raw.githubusercontent.com/OWNER/REPO/HEAD/pokeldn-source.json` |
| 以 `.json` 结尾的 HTTPS 地址 | 该文件 |
| 任何其他 HTTPS 地址 | 该文件夹中的 `pokeldn-source.json` |

```json
{"schema": 1, "name": "My plugins", "homepage": "https://github.com/me/my-plugins",
 "plugins": [{"id": "my-plugin", "name": "My plugin", "version": "1.0.0", "api": "1.6",
   "description": "...", "author": "me", "download": "https://.../my-plugin-1.0.0.pokeplugin",
   "sha256": "64 hex digits", "size": 46302, "icon": "https://.../icon.png", "homepage": "https://..."}]}
```

缺少 `id`、`version`、HTTPS 的 `download` 或 `sha256` 的条目，或者 id 重复的条目，会被略过；`schema` 不是 1 的会被拒绝；SHA-256 不符的下载会在读取之前被拒绝；id 与条目不符的软件包会被拒绝。风险提示页和签名检查仍会执行。来源会在启动时（设置中的更新开启）和刷新时读取；最后一次列表缓存于 `plugins/.source-cache/`，关注列表为 `plugins/.sources.json`。插件从它来自的来源更新；从文件安装的插件，则从第一个列出它的来源更新，否则使用它的 `updates`。

```bash
python scripts/plugin_source.py my-plugin-1.0.0.pokeplugin -o pokeldn-source.json --name "My plugins" \
    --download "https://github.com/me/my-plugins/releases/download/{id}-{version}/{file}"
```

已经以更高版本列出的条目会保留。

### 防护栏

有两项检查可以阻止明显的危害；两者都不是沙箱。安装界面会列出这些 Python 文件会做什么：网络、其他程序、删除文件、原生代码（`ctypes`、`cffi`）、运行时执行的代码（`exec`、`eval`、`compile`、`marshal`）、提到 `prod.keys`，或者它无法读取的编译文件。当插件的代码位于调用栈上时，一个审计钩子（`pokeldn/plugin_guard.py`）会在以下情况抛出 `PermissionError`：

| 拒绝 | 允许 |
|---|---|
| 删除、清空、移动或覆盖插件文件夹之外的文件 | 在它的文件夹、数据文件夹、库、会话、日志和临时文件夹中进行同样的操作 |
| 启动 `rm`、`del`、`rd`、`Remove-Item`、`shred`、`dd`、`format`、`mkfs`、`diskutil`、`diskpart`、`sudo`、`su` 及类似命令，无论直接启动还是在 shell 中启动，或任何带 `-delete` 或 `--no-preserve-root` 的命令 | 任何其他程序；在任何位置创建文件 |

插件调用的 pokeldn 代码会被检查；调用栈上没有插件的代码永远不会被检查。

## 制作插件

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

嵌套超过 64 层数组或表的 `plugin.toml` 或语言包文件会被拒绝且不解析（`pokeldn.plugins.toml_loads`）；字符串和注释中的括号不计入。

当插件开启时，在应用中以及它启动的每次运行中，都会执行 `register(api)`：

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

游戏的列表为每个活动显示一行（[游戏页](gui.md#the-games-page)）。没有 `activity` 的工具自成一行。设置了 `activity` 的工具会加入该行，并由它的 `variant` 按钮来展示：

```python
Tool("my-lan-trade", "Trade over my LAN", "lan.py", "Trades over this computer's network.", (),
     activity="trade", variant=(("role", "host"), ("link", "lan")))
```

| `activity` | 该行 |
|---|---|
| `trade`、`gift`、`max-raid`、`lair`、`tera-raid`、`circle` | 交换、神秘礼物、极巨团体战、极巨大冒险、太晶团体战、联盟集友圈 |

| 轴 | 选项 | 按钮 |
|---|---|---|
| `role` | `host`、`join` | pokeldn：Hosts（你的主机加入）、Joins（你的主机主持） |
| `link` | `board`、`lan`、`online` | 连接方式：Board、不用板子的 Wi-Fi、在线 |
| `mode` | `quests`、`encounters` | 模式 |

`pokeldn.app.catalog.AXES` 和 `ACTIVITIES` 就是这些列表。`add_tool` 会拒绝未知的活动或选项，以及该游戏那一行中另一个工具已经占用的变体：应用永远无法显示它。

### 工具的脚本

应用会导入脚本以调用 `build_parser()`（高级选项卡），然后把它作为子进程在会话文件夹中运行。工作应放在 `if __name__ == "__main__"` 之下；顶层的工作会破坏游戏页。

| 脚本 | 应用 |
|---|---|
| 打印一行 | 在输出中显示它 |
| 打印 `[done] trade N complete`（`pokeldn.ldn.show_done()`） | 勾掉一个排队的交换 |
| 以 0 / 非 0 退出或抛出异常 | 完成 / 失败并显示回溯 |
| 收到 `KeyboardInterrupt` | 按下了停止；15 秒内退出，否则进程会被结束 |
| `pokeldn.popup`（1.2）、`popup.choose`（1.7） | 任意页面上的弹出窗口；答案会返回 |
| `pokeldn.progress.show(done, total, title, unit)`（1.7） | 带有速率和剩余时间的进度条（[进度](gui.md#progress)） |
| `pokeldn.panel`（1.8） | 状态卡片和库注释（[状态卡片](#status-cards-18)） |

弹出窗口会立即返回它的 id；答案稍后以回调形式到达，可能在任意线程上：

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

### 插件可以导入什么

发布的应用带有 Python 3.13，且没有 `pip`：

| 内容 | 来源 |
|---|---|
| 标准库 | 随附，除了 `multiprocessing`、`tkinter`、`curses`、`venv`、`ensurepip`、`profile`、`cProfile`、`pstats`、`trace`、`compileall`、`modulefinder`、`pyclbr`、`tabnanny` 以及其他平台的模块（`scripts/pack_app.py`、`PLUGIN_STDLIB`） |
| `trio`、`pycryptodome`（`Crypto`）、`zstandard`、`pyserial`（`serial`）、`websockets`、`certifi`、`bleak`、`unicorn`、`flet` | pokeldn 自身的依赖，版本见 `requirements.txt` |
| `ldn`、`pokeldn` | 只有下表中的部分是稳定的 |
| 纯 Python 模块 | 插件的文件夹 |

编译型软件包（`numpy`、`Pillow`）只在装有它们的源码运行中可用。

### 字段

| `kind` | 输入 | 传参形式 |
|---|---|---|
| `text`（默认） | 文本框 | `--flag VALUE` |
| `number` | 数字框 | `--flag VALUE` |
| `choice` | 由 `choices=((value, label), ...)` 构成的下拉菜单 | `--flag VALUE` |
| `switch` | 开关 | 开启时 `--flag` |
| `file` | 文件选择器，`exts=("bin",)` | `--flag PATH` |

`help=`、`default=` 和 `hidden=True`（高级选项卡）适用于任何字段；其余内容在 `pokeldn/app/catalog.py` 中。`Field.identity`（1.5）是为经过翻译的位置参数字段提供的稳定设置键。`fixed` 可以携带 `{ot}`、`{tid}`、`{sid}`、`{language}`、`{gender}`、`{received}`、`{stamp}` 和 `{keys}`（1.7，设置中的 `prod.keys`；接受 `--keys` 的解析器无论如何都会得到它）。

### 插件保留什么

更新会替换文件夹。需要长期保留的文件放在 `api.data` 中，或者在脚本中通过 `pokeldn.plugins.data_folder("my-plugin")` 获取：`plugin-data/<id>`，只有在被要求时才会在移除时删除。

### 库（1.7）

`library = "My files"` 对应 `Documents/pokeldn/My files`（设置了 `POKELDN_DATA` 时位于其下），由 `api.library` 或 `pokeldn.plugins.library_folder("my-plugin")` 返回，首次使用时创建。防护栏允许在其中进行任何写入，安装界面会列出它，移除插件时会保留它。游戏页会在插件的工具下列出它的文件，玩家可以在那里添加、重命名和删除它们；以 `.` 开头或以 `.part` 结尾的名字会被隐藏（先写在一个这样的文件里，然后重命名）。顺序由玩家选择，否则使用 `library_sort`（`name`、`name-desc`、`date`、`date-desc`、`size`、`size-desc`），再否则为 `date-desc`；名字按自然顺序排序。名字最多 40 个字母、数字、空格、`.`、`-`、`_`；pokeldn 自己的文件夹（`Bank`、`Saves`、`Received`……）、Windows 设备名和另一个插件的库都会被拒绝。

### 状态卡片（1.8）

`pokeldn.panel` 打印 `[panel]` 行；应用会在工具的页面上绘制卡片，在库文件上绘制注释，把它们保存在 `plugin-panels/<id>.json` 中，并随插件一起删除。

```python
panel.show("console", "Pokémon: Let's Go, Pikachu!", ["System version\t23.0.1"],
           image=icon, chips=[("Version", "1.0.2")], tone="ok")
panel.annotate("Game 1.0.2.nsp", state="ok", text="Every signature checks", image=icon)
```

| 调用 | 显示 |
|---|---|
| `panel.show(id, title, lines=(), *, image=None, chips=(), tone="info")` | 卡片 `id`，替换最后一张；一行是文本或 `label<TAB>value`；`tone` 为 `info`、`ok`、`warning`、`error` |
| `panel.clear(id)` | 移除它 |
| `panel.annotate(name, *, state="ok", text="", image=None)` | 把库文件标记为 `ok`、`bad` 或 `checking` |
| `panel.unannotate(name)` | 移除注释 |

限制：id 为 1 到 32 个 `[a-z0-9_-]` 字符；每个插件 8 张卡片；标题 80 个字符，12 行、每行 200 个字符，6 个标签、每个 40 个字符；图像为数据文件夹或库中不超过 2 MB 的 PNG 或 JPEG。注释跟随文件名。超出限制会抛出 `ValueError`；无法读取的 `[panel]` 行会显示在输出中。

### 自己的游戏

```python
api.add_game(Game("my-game", "My game", "Mine", "", (tool_one, tool_two)), icon="icon.png")
```

`Game(key, name, short, doc, tools)`；`api.add_tool("my-game", tool)` 可以添加更多工具。

### 无线电

`api.add_radio(scheme, install, label)` 会在插件下的 **无线电** 中列出一个无线电；一次运行会在其第一次无线调用之前调用 `install(argument, log)`。`install` 用异步上下文管理器调用 `ldn.wlan.set_factory(factory)`，产出一个 `ldn.wlan.Factory`；`pokeldn/ldn/esp32_wlan.py` 是参考实现。应用以 `POKELDN_RADIO=myradio:` 的形式运行它；在命令行上，参数跟在冒号之后。

### LDN 网络（1.7）

`pokeldn.ldn.network` 使用无线电的 IPv4 协议栈（ESP32 板子或 ldnrs）加入或承载网络。

```python
with network.join(COMM_ID, keys=args.keys, password=PASSPHRASE, name="My game") as net:
    net.add_protocol(6, lambda src, dst, segment: segments.put((src, segment)))
    while not net.send_ip(6, net.host_ip, first_segment):    # False until ARP resolves
        time.sleep(0.1)
```

| 名称 | 说明 |
|---|---|
| `join(comm_id, *, keys, password, nickname, app_version, name, log, timeout)` | 加入广播 `comm_id` 的网络；无人应答时抛出 `RuntimeError` |
| `host(comm_id, *, keys, password, nickname, application_data, scene_id, app_version, max_participants, channel, protocol, log, timeout)` | 开启一个可供主机加入的网络 |
| `Network.ip`、`.mac`、`.host_ip`、`.broadcast`、`.ssid`、`.comm_id`、`.application_data` | 地址与广播 |
| `Network.participants` | 就座的站点：`.index`、`.ip`、`.mac`、`.name` |
| `Network.add_protocol(number, handler)`、`.remove_protocol(number)` | 每个重组后的 IPv4 包调用 `handler(src_ip, dst_ip, payload)`，在无线电循环上执行；UDP（17）仍由协议栈处理；异常会丢弃该包 |
| `Network.send_ip(protocol, dst_ip, payload)` | 一个包，按 1500 分片；ARP 未决期间返回 `False` |
| `Network.udp_socket(port)` | `sendto`、`recvfrom`、`setblocking`、`settimeout`、`fileno`、`close` |
| `Network.set_application_data(data)` | 一条新的广播 |
| `Network.error`、`.close()` | 结束的原因；离开。是一个上下文管理器 |
| `pokeldn.ldn.radio_lost()` | 无线电离开的原因，可据此与「停止」区分 |

通过板子的吞吐量约为 0.5 MB/s。

### 战斗服务器

战斗服务器为 `bin/sv_host.py --raid-serve [NAME]` 运行朱 / 紫的团体战战斗（[承载战斗](sv_raid.md#serving-the-battle)）。`api.add_battle_server("sv", name, factory, label)` 注册它；`factory(bootstrap, partners)` 会带着引导字节和两个伙伴的 0x158 字节记录，在网络循环之外被调用。

| 成员 | 作用 |
|---|---|
| `start(now)` | 第一帧；返回推动了战斗的帧 |
| `run(until)` | 以 30 帧/秒推进到 `until`（至少一帧）；返回值相同 |
| `t` | 服务器时钟，单位为秒 |
| `receive(slot, message)` | 来自 `slot` 的 32 字节头加正文 |
| `sent(slot)` | 自上次调用以来为 `slot` 排队的消息 |

槽位：0 为程序方的宝可梦，1 为 Boss，2 为主机，3 和 4 为伙伴。出现异常会停止承载，主机将自行进行战斗。

### 提供的宝可梦编辑（1.10）

`api.add_offer_edit(game, edit, label="")` 会对 `game`（`frlg`、`lgpe`、`swsh`、`bdsp`、`pla`、`sv`、`za`）的内置启动器从文件准备的每一只宝可梦运行 `edit(record) -> record`：交换提供的宝可梦、排队中的提供、团体战伙伴、为接收方重制的神秘礼物宝可梦。记录就是 PKHeX 读取的文件字节（`pokeldn.pokemon.RECORD_SIZES`，无论是否加密）；`SERVICE.check(game, path)` 可读取一条。编辑返回要提供的记录。

```python
def rename(record):              # FireRed: the nickname at +0x08 is outside the checksum
    out = bytearray(record)
    out[8:18] = bytes((0xC6, 0xBE, 0xC8)) + b"\xff" * 7      # "LDN"
    return bytes(out)

def register(api):
    api.add_offer_edit("frlg", rename, "Renamer")
```

| 步骤 | |
|---|---|
| 1 | 启动器自身的编辑（提供选项、新的 PID、游戏的格式） |
| 2 | 每个插件的提供编辑，按加载顺序；运行日志会记录 `the plugin LABEL edited the offer` |
| 3 | PKHeX 的合法性检查 |

PKHeX 的合法性检查是每次提供的最后一步，没有插件能关闭它：如果编辑的结果被 PKHeX 拒绝，运行会以 PKHeX 给出的原因停止。抛出异常或没有返回字节的编辑会以插件的标签停止运行。启动器读取文件时会运行编辑，交换过程中重制神秘礼物宝可梦时会再次运行。

### 打包、测试、签名与更新

```bash
python scripts/pack_plugin.py my-plugin --key ~/my-plugin-signing.pem
POKELDN_PLUGINS=~/my-plugin python -m pokeldn --plugins            # lists plugins and load errors
POKELDN_PLUGINS=~/my-plugin python -m pokeldn my-hello -- --name Blue
POKELDN_PLUGINS=~/my-plugin python gui/main.py
```

`pack_plugin.py` 会写出 `my-plugin-1.0.0.pokeplugin`，并像应用那样检查它；隐藏文件和 `exclude` 中的内容不会被打包。任何 zip 都可以，只要 `plugin.toml` 位于其顶层或某个顶层文件夹中，且没有越界路径和符号链接。`POKELDN_PLUGINS` 会为该进程及其运行开启一个文件夹。在 `register` 中抛出异常、需要另一个 API 或重复使用某个键的插件不会添加任何东西，它的卡片会显示原因。Python 软件包也可以通过 `pokeldn.plugins` 入口点组注册。

`--key` 会用 Ed25519 密钥签名（首次使用时创建），并打印其指纹（`ABCD-EFGH-IJKL-MNOP`）。`plugin.sig` 保存公钥，以及针对 id、版本和每个文件的 SHA-256 的签名。请保管好密钥并做好备份，同时公开指纹。

| 应用看到 | 它会 |
|---|---|
| 签名不匹配 | 拒绝该文件 |
| 新签名插件 | 显示指纹，并按 id 记住该密钥 |
| 使用已记住密钥的更新 | 显示「Signed by the same author」 |
| 另一个密钥，或签名后变为未签名 | 以红色警告并要求二次确认 |
| 未签名且从未签名过 | 显示「Not signed」 |

| `updates` | 应用读取 |
|---|---|
| `https://github.com/OWNER/REPO` | 最新发布的标签（`v1.3.0` 或 `1.3.0`）和第一个 `.pokeplugin` |
| 任何其他 HTTPS 地址 | `{"version": "1.3.0", "url": "https://.../my-plugin-1.3.0.pokeplugin", "page": "..."}` |

在设置中开启更新后，这些会在启动和刷新时检查；有更新的版本时会显示 **Update to 1.3.0**，点击后会下载并打开安装界面。HTTP 仅对 `127.0.0.1` 和 `localhost` 接受。

## 语言包（1.5）

语言包是一种纯数据插件；`name` 显示在设置的应用语言中，`locale` 是它的标签。

```toml
id = "community-zh-hans"
name = "简体中文"
version = "1.0.0"
api = "1.5"
locale = "zh-Hans"
strings = "strings.toml"
```

`strings.toml` 在带引号的键下保存文本值（`"bank.bank_676c47" = "宝可梦银行"`）。错误的 TOML、非文本值和错误的格式语法会在安装时被拒绝；损坏的语言包会回退到英文。选择语言包会开启它，并需要重启。缺失的键使用其内联的英文默认值。像 `{value0}` 这样的占位符可以移动位置，但必须保留名称和规格；`{{` 和 `}}` 是字面量花括号；格式化失败的翻译会使用英文。

```bash
python scripts/extract_strings.py [--check]     # writes pokeldn/app/data/strings.en.toml
python scripts/pack_plugin.py examples/plugins/pseudo -o pseudo.pokeplugin
python scripts/check_language_pack.py PACK_FOLDER   # what the pack lacks against this release
```

`check_language_pack.py` 会列出未翻译的字符串和工具帮助、该版本已不再有的键，以及占位符与英文不同的翻译；占位符不一致时它会以 1 退出。

测试会检查模板与源匹配，并拒绝带有两个默认值的键。语言包从模板的翻译副本开始；`examples/plugins/pseudo` 是一个局部的伪语言环境。

### 额外资源（1.9）

```toml
api = "1.9"
messages = "messages.toml"
templates = "templates.toml"
terms = "terms.toml"
help = "help.toml"
documents = "docs"
font_family = "Noto Sans CJK SC"
```

| 条目 | 键 | 值 |
|---|---|---|
| `messages` | 模块的英文原文，逐字 | 它的翻译 |
| `templates` | `"Could not open {path}: {reason}"` | 字段相同的翻译 |
| `terms` | 游戏术语（1 到 200 个字符，最多 10000 条） | 它的翻译 |
| `help` | `"TOOL-KEY:--option"` | 该标志在高级选项卡中的说明 |
| `documents` | 由 `guide.md` 和 `docs/` 页面按名称组成的文件夹 | |
| `font_family` | 字体，最多 100 个字符 | 文本字体；CJK 回退仍然保留 |

路径必须留在插件文件夹内。这些用来翻译来自游戏模块、PKHeX 和插件的文本：一条消息会先在 `messages` 中整体尝试，然后是 `templates`，然后按句子，最后在词边界处替换 `terms`。一个模板有 1 到 8 个由字面文本分隔的普通命名字段，最多 2048 个字符，按字面匹配，最长者优先，作用于最长 4096 个字符的消息；名为 `term...` 或 `message...` 的字段本身也会被翻译，深度为 4。如果某个值整体上是一个物种、招式、特性、性格、属性或球的名字，且没有术语覆盖它，则采用 PKHeX 的名称。PKHeX 的名称和合法性报告对 `ja`、`fr`、`it`、`de`、`es`、`ko`、`zh-Hans`、`zh-Hant` 跟随区域设置（`zh` 带 `TW`、`HK`、`MO` 时为 `zh-Hant`）。
当标题数量匹配时，翻译后的页面保留英文锚点，否则用 `<a id="NAME"></a>` 设置一个；front matter 中的 `title` 会重命名侧边栏中的页面。

文件名、银行和队列摘要、GTS 列表、设置、会话日志、无线电输出和 `[done]` 行保持英文。设置中的训练家语言决定生成的宝可梦的语言。

## 插件测试套件

`examples/plugins/test_kit` 会添加自检（检查 API 的每一部分，打印 PASS 或 FAIL，留下一张「上次自检」卡片）、模拟会话（交换步骤和 `[done]` 行）、故意失败、火红 & 叶绿下的「Hello from a plugin」，以及测试套件无线电，它不承载任何东西。

## 版本

API 采用 `major.level` 形式；插件的 `api` 是它需要的最低版本。新增功能会提升 level（插件需求更高时会以「Update pokeldn」拒绝）；移除功能或改变含义会提升 major。仍在服务的旧 major 会连同其最后一个版本列在 `DEPRECATED` 中；已不再服务的会低于 `API_OLDEST` 并被拒绝。插件自己的 `version` 只决定是更新、重装还是降级。

| API | 新增 |
|---|---|
| 1.0 | `add_tool`、`add_game`、`add_radio`、`folder`、`version` |
| 1.1 | `api.data`、`api.level`、`pokeldn.plugins.data_folder(plugin_id)` |
| 1.2 | `pokeldn.popup` |
| 1.3 | 程序接口面：构建器、礼物文件、PKHeX 和板子 |
| 1.4 | 银行导入、记录、目标、提供和交换完成 |
| 1.5 | 语言包插件和字符串查找 |
| 1.6 | `add_battle_server` |
| 1.7 | `pokeldn.ldn.network`、`pokeldn.ldn.radio_lost`、`library` 和 `api.library`、`pokeldn.popup.choose`、`pokeldn.progress`、`{keys}` 记号 |
| 1.8 | `pokeldn.panel`、`library_sort` |
| 1.9 | 语言包的消息、模板、术语、工具帮助、文档和字体偏好 |
| 1.10 | `add_offer_edit` |
| 1.11 | 火红/叶绿 RNG：`lcg`、`rng_countdown.mon_from`、`scan`、`buffer_script.read_rng_trace` |
| 1.12 | `Tool` 的 `activity` 和 `variant`（[工具行](#a-tools-row-112)） |

## API 版本 1

| 名称 | 说明 |
|---|---|
| `api.add_tool(game, tool)` | 位于 `frlg`、`lgpe`、`swsh`、`bdsp`、`pla`、`sv`、`za` 或插件自己的游戏下的 `Tool` |
| `api.add_game(game, icon="")` | 一个游戏分区 |
| `api.add_radio(scheme, install, label="")` | 一个无线电 |
| `api.add_battle_server(game, name, factory, label="")` | 一个团体战战斗服务器（1.6） |
| `api.add_offer_edit(game, edit, label="")` | 对内置启动器的每次提供进行编辑，在 PKHeX 检查之前（1.10，[提供的宝可梦编辑](#offer-edits-110)） |
| `api.folder` | 插件的文件夹；对于软件包为 None |
| `api.version`、`api.level` | 应用的 API，`1` 和 `12` |
| `api.data` | 保留的数据文件夹（1.1） |
| `pokeldn.plugins.data_folder(plugin_id)` | 在脚本中获取同样的文件夹（1.1） |
| `api.library`、`pokeldn.plugins.library_folder(plugin_id)` | 库文件夹（1.7，[库](#a-library-17)） |
| `Tool`、`Field`、`Game` | 来自 `pokeldn.plugins` 的目录类型 |
| `pokeldn.ldn.show_done()` | 打印交换完成的行 |
| `pokeldn.popup.acknowledge(title, text="", *, id, label="OK", on_ack, tone)` | 单按钮弹出窗口；返回 id（1.2，[弹出窗口](gui.md#pop-ups)） |
| `pokeldn.popup.confirm(title, text, agree, disagree, *, id, on_agree, on_disagree, on_dismiss, tone)` | 两个按钮；按 Esc 或点击外部会关闭；返回 id（1.2） |
| `pokeldn.popup.choose(title, text, options, *, id, on_choice, on_dismiss, tone)` | 2 到 8 个选项，`on_choice(index)`；返回 id（1.7） |
| `pokeldn.progress.show(done, total, title, unit="bytes")` | 进度条；`unit` 为 `bytes` 或 `items`（1.7） |
| `pokeldn.panel.show(id, title, lines=(), *, image, chips, tone)`、`clear(id)`、`annotate(name, *, state, text, image)`、`unannotate(name)` | 状态卡片（1.8，[状态卡片](#status-cards-18)） |
| `pokeldn.ldn.network` | LDN 网络（1.7，[LDN 网络](#ldn-networks-17)） |
| `pokeldn.ldn.radio_lost()` | 无线电离开的原因，或为空（1.7） |
| `pokeldn.popup.cancel(id)`、`available()`、`set_dispatcher(dispatch)` | 关闭弹出窗口；弹出窗口是否显示；回调在哪里运行（1.2） |

这张表和下一张表就是受支持的接口面；其他任何导入都可能在任何版本中变化。

## 程序接口（1.3，1.4 加入银行，1.5 加入语言包，1.11 加入 RNG）

插件，或者在 pokeldn 源码检出上运行的独立程序，都可以使用这些；`tests/test_plugin_surface.py` 会逐一解析。

| 名称 | 说明 |
|---|---|
| `python -m pokeldn --list`、`python -m pokeldn TOOL -- ARGS` | 工具键；使用设置中的训练家运行 |
| `pokeldn.app.i18n.t(key, default, **fmt)`、`select(plugin_id)` | 字符串查找；选择一个语言包，或用 `""` 选择英文（1.5） |
| `pokeldn.app.catalog.GAMES` | 内置游戏及其 `Tool`；应用传入的标志保持其名称 |
| `pokeldn.pokemon.SERVICE.species(game)`、`.names(game, kind)` | 物种、`moves`、`items`、`bag`、`held`、`balls`，均为 `{"id", "name"}` 列表 |
| `pokeldn.pokemon.SERVICE.options(game, species, trainer)` | 一次提供可用的形态、性格、特性、道具和球 |
| `pokeldn.pokemon.SERVICE.make(game, species, trainer, level, shiny, nickname, version, options)` | 一只合法的宝可梦；返回值与 `"file"` |
| `pokeldn.pokemon.SERVICE.paste(game, text, trainer)` | 作为 `make` 值的 Showdown 配置，附带 `errors` |
| `pokeldn.pokemon.BuilderError` | PKHeX 拒绝或缺失，附带一句给玩家的话 |
| `pokeldn.pokemon.NATURES` | 按索引排列的 25 个性格名称 |
| `pokeldn.gifts.load(path, game=)`、`pokeldn.gifts.save(path, gift)` | `.pokegift`、`.wc3`、`.wc8`（[神秘礼物文件](gifts.md)） |
| `pokeldn.swsh.gift_builder.KINDS`、`PRESETS`、`PRESET`、`OUTFITS` | 剑/盾的礼物种类、预设和服装 |
| `pokeldn.swsh.gift_builder.blank(**changes)`、`record(state)`、`compile(state)`、`describe(state, name)` | 表单状态、720 字节记录、礼物、玩家文本；`ValueError` 会指出错误的字段 |
| `pokeldn.swsh.events.load()`、`by_key()`、`gift(key)` | 官方的剑/盾活动卡片 |
| `pokeldn.frlg.gift.builder.KINDS`、`PRESETS`、`PRESET`、`GIVERS`、`CARTRIDGES` | 火红/叶绿的种类、预设、赠予者和卡带 |
| `pokeldn.frlg.gift.builder.blank()`、`compile(state)`、`describe(state, name)` | 用于神秘卡片、新闻或主机代码的同类功能；`name` 根据卡带 id 得到物种 |
| `gui.board.ports()`、`identify(port, blink=)`、`detect_chip(port)` | 串口以及板子的 `.firmware`、`.firmware_version`、`.protocol`、`.current` |
| `gui.board.download_firmware(say=)`、`image_for(kind, chip)`、`image_version(path)`、`flash(port, kind=)` | 校验过的发布镜像和刷写 |
| `pokeldn.app.bank.library()` | 默认的银行文件夹；列出内容从不会创建它（1.4） |
| `pokeldn.app.bank.Entry`、`Imported`、`ImportedPokemon` | 银行结果类型（1.4） |
| `pokeldn.app.bank.Imported.count(state)` | 某个状态下的结果数（1.4） |
| `pokeldn.app.bank.entries(folder=)`、`find(entry_id, folder=)`、`data(entry)` | 记录按最新在前，返回一条或 `None`，以及它的字节（1.4） |
| `pokeldn.app.bank.import_file(path, trainers, folder=)` | 导入宝可梦文件或存档；返回 `Imported`（1.4） |
| `pokeldn.app.bank.deposit(game, source, info, folder=)` | 把收到的文件存入银行；返回 `Entry`，若已存入则为 `None`（1.4） |
| `pokeldn.pokemon.SERVICE.check(game, path)` | PKHeX 检查，即 `deposit` 所需的 `info`（1.4） |
| `pokeldn.app.bank.destinations(entry, trainer)`、`offer(entry, game, trainer)` | 按游戏转换；一个转换后的提供（1.4） |
| `pokeldn.app.bank.edit(entry, fields)`、`remove(entry_id, folder=)` | 编辑昵称、升级、招式、持有道具；删除一条记录（1.4） |
| `pokeldn.app.bank.TradeSession(offers, folder=)` | 本次运行按顺序的提供（1.4） |
| `pokeldn.app.bank.TradeSession.advance(count)` | 应用累计交换数；`.completed` 是已见的最大值（1.4） |
| `pokeldn.app.received.trades_done(line)` | `[done] trade N complete` 行中的数量，或 `None`（1.4） |
| `pokeldn.frlg.rom.lcg.step(value)`、`.advance(value, n)`、`.distance(start, target)`、`.draws(value, count)` | 火红/叶绿的 `gRngValue` 生成器：下一个状态、向前 n 步、两个状态之间的步数、接下来的 `count` 个 `Random()` 结果及剩余状态（1.11，[RNG](frlg_rng.md)） |
| `pokeldn.frlg.rom.lcg.recover_wild_state(personality, ivs, max_gap=)` | 能生成某只宝可梦的状态，个体值按存储顺序（1.11） |
| `pokeldn.frlg.rom.rng_countdown.mon_from(state, tid, sid)`、`.scan(state, tid, sid, frames=, want=)` | 某个状态构建的脚本化 `CreateMon`：`personality`、`ivs`、`nature`、`shiny`；`frames` 内的闪光按键（1.11） |
| `pokeldn.frlg.rom.buffer_script.read_rng_trace(dump)` | `--buffer-script rng-trace` 会话的 `--dump-file` 中的样本（1.11） |

要停止一次启动器运行，向它的 PID 发送 SIGINT，15 秒后再发送 SIGTERM；绝不要用 `pkill -f`。

## 银行集成（1.4）

外部前端使用 `pokeldn.app.bank`，并自行管理其队列和进程；转换需要 PKHeX 辅助程序（在源码中运行 `dotnet build -c Release services/pkhex`）。

| 类型 | 字段 |
|---|---|
| `Entry` | `id`、`path`（原生记录）、`game`、`species_id`、`shiny`、`summary`、`legal`、`tracker`、`created`（Unix 秒）、`origin`、`home_tracker`（`empty`、`made` 或 `""`，[HOME 追踪号设置](gui.md#the-home-tracker-setting)） |
| `Imported` | `name`、`save`、`pokemon` |
| `ImportedPokemon` | `where`、`species`、`species_id`、`shiny`、`state`（`banked`、`already`、`refused`）、`game`、`detail` |
| `destinations` 值 | 按游戏：`ok`、`reason`、`home_tracker` |
| `offer` 值 | `file`、`summary`、`species`、`shiny`、`legal`、`encounter`、`moves`、`report`、`home_tracker`、`bank`（来源 id） |

`trainers` 把游戏键映射到 `{ot, tid, sid, language, gender}`。导入会记住曾经导入过的每条记录。一次提供会把银行记录留在原处；把它的 `file` 作为启动器的 `--offer-file` 传入，且不要加 `--fresh-pid`，并在运行结束前保留它。直接运行目录工具的脚本，因为 `python -m pokeldn TOOL` 不接受提供。

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

每次运行一个 `TradeSession`，严格按提供顺序，包含已构建的提供。只向它喂入已确认的数量；未完成的记录会保留。`advance` 在数量错误时抛出 `ValueError`，在 `OSError` 之后可以重试。文件错误抛出 `OSError`；PKHeX 失败抛出 `BuilderError`。`deposit` 信任 `SERVICE.check`；玩家文件通过 `import_file` 进入。`folder` 默认为 `library()`。在导入前设置 `POKELDN_DATA` 以隔离所有文件。调用是同步的：让 PKHeX 远离 UI 线程。每个银行文件夹只有一个写入者；桌面应用旁边的前端使用自己的文件夹。`TradeSession` 只改动银行。
