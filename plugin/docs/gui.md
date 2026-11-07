---
title: 桌面版构建
---
# 桌面版构建

桌面应用是 pokeldn 在 macOS、Windows 和 Linux 上的界面。发行版会打包 PKHeX 以及面向
ESP32、ESP32-S3、ESP32-C3 和 ESP32-C6 的无线固件；`prod.keys` 由用户自备。

1. 设置：选择 `prod.keys`。
2. 设备页：选择 USB 设备并安装无线固件。执行安装时会选中芯片自带的镜像；来自文件的镜像
   会对照芯片进行校验。S3、C3 和 C6 通过原生 USB Serial/JTAG 连接；S2 芯片会被拒绝。
3. 选择一款游戏和一个工具，准备一只宝可梦或一个文件，按主机上的步骤操作，然后按开始。
   收到的宝可梦会进入设置中指定的文件夹，可由「输出」旁的按钮打开。

每个交换工具中要提供的宝可梦都可以留空：按开始时，由 PKHeX 为该游戏中你的训练家生成一只
随机的合法宝可梦（`command.prepare`），每次运行都会重新生成。

神秘礼物工具共用一个构建器（预设、自行构建、`.pokegift`、剑/盾上的 `.wc8`）。
「保存礼物文件」在没有设备时也能导出为 `.pokegift`、`.wc3` 或 `.wc8`
（[神秘礼物文件](gifts.md#desktop-app)）。

## 首次启动

macOS 保留系统原生的窗口按钮；Windows 和 Linux 在应用标题栏中绘制它们，标题栏可拖动窗口，
双击则最大化。

| 系统 | 步骤 |
|---|---|
| macOS | 未签名：打开一次，关闭警告，然后进入系统设置、隐私与安全性、仍要打开 |
| Windows | 解压 zip 并运行 `pokeldn.exe`，`_internal` 放在它旁边；SmartScreen：更多信息、仍要运行。没有 COM 端口：[Windows USB 驱动](#windows-usb-drivers) |
| Linux | GTK 3 与 libsecret；`sudo usermod -aG dialout $USER`（Arch 上是 `uucp`），然后重新登录。见 [Linux 串口](#linux-serial-ports) |

没有可用的 `prod.keys` 时，应用会打开一个要求提供密钥的欢迎页；按 Esc 或「稍后」可关闭它。
在电脑上选好密钥后，第二步会监视 USB 端口并说明设备需要什么：已插入、需要设备页的固件，
或者什么都不需要。手机应用在各自页面上完成设备设置。

当密钥文件包含无线模块的密钥派生所需的每个条目（`ldn.KEYS_NEEDED`）时，它才可用：
`aes_kek_generation_source`、`aes_key_generation_source`、`master_key_00`（LDN 协议 1）和
`master_key_12`（协议 3）。设置、游戏页检查清单和开始都会指出缺少哪些条目。
`ldn.load_keys` 会跳过不是 16 或 32 字节密钥的行，例如注释。

### 设置损坏

`settings.json` 在启动时读取（`pokeldn.app.settings.load`）。不是 JSON 的文件，或某个值类型
错误的字段，会在替换任何内容之前被复制到旁边的 `settings.json.bad`；只有无法读取的字段会
恢复为默认值。随后应用会显示哪些字段被重置，以及旧文件所在的位置。

## Android 安装要求

[Android 应用](../examples/android/README.md) 是这套界面在手机上的版本。设备页会在插入、
拔出、USB 提示关闭以及从设置返回时重新读取 USB 状态。原生 USB 设备（`303a:1001`）插入
时会打开应用。

| 检测到的状态 | 处理建议 |
|---|---|
| 没有兼容的 USB 设备 | 检查数据线；显示手机的 USB 主机或 OTG 设置（一加有 OTG 开关） |
| USB 权限缺失或被拒绝 | 解释 Android 的提示；提供重试 |
| 设备握手失败 | 检查设备和固件；显示错误 |
| 设备有应答 | 显示设备和固件；继续 |
| 设备断开，或从设置返回 | 刷新并在就绪后继续 |

经典 ESP32 只能通过 CP210x 桥接工作（`10c4:ea60`、`UsbStream.java`）；CH34x 和 FTDI 会被
指明为不受支持。PKHeX 在手机上运行。保存和「打开文件夹」（一个 zip）都使用 Android 的
文件选择器。

## iOS 安装

[iOS 应用](../examples/ios/README.md) 是这套界面在 iPhone 或 iPad 上的版本（AltStore 或
SideStore）。它通过蓝牙连接设备：从桌面设备页安装蓝牙无线固件（ESP32-C6 用
`pokeldn-radio-ble-c6.bin`，经典 ESP32 用 `pokeldn-radio-ble.bin`）；USB 只负责供电。
手机占用设备期间，设备会忽略 USB：在别处使用之前请先关闭 iOS 应用。应用文件位于
「文件」、我的 iPhone、pokeldn 下。

## 窗口尺寸

页面的各个面板按它们实际拥有的宽度布局，宽度随窗口变化而测量（`gui/theme.py` 的 `Panes`）。
与他列并排时，选项列不会窄于 440 点。

| 留给面板的宽度 | 布局 |
|---|---|
| 侧面板全宽加 440 | 并排 |
| 侧面板 88% 加 440 | 并排，侧面板收窄 |
| 最后一个面板 88% 加 440（三面板页面） | 前两个放到切换器上，最后一个在它们旁边 |
| 更少 | 切换器上一次一个面板 |

从并排收窄窗口时，选项列会前移。宽窗口中选项列保持在 720 点并居中，字段按能放下的数量
排成一行；设置和插件保持在 760。调整尺寸后打开的页面会以宽度允许的布局开始。

桌面窗口最窄可到 380 点。低于 760 时会实时切换到下方的手机布局，加宽后切回；桌面窗口
始终在内容上方保留自己的标题栏行。

## 手机

宽度低于 760 点时，页面位于底部标签栏，面板在切换器上一次显示一个（游戏、选项、会话）。
Android 和 iOS 没有控制页或更新页。

## 游戏页

每款游戏的列表按活动各显示一行：交换、神秘礼物，然后各类团体战和联盟集友圈。该行的运行
方式是选项上方的按钮，每个选择占一行：

| 选择 | 按钮 | 显示于 |
|---|---|---|
| pokeldn | 主持（你的主机加入）、加入（你的主机主持） | 通过设备或 LAN 的交换、团体战、极巨大冒险 |
| 连接 | 设备、无设备的 Wi-Fi、在线 | 交换；Wi-Fi 仅限剑/盾 |
| 模式 | 任务、遭遇 | 联盟集友圈 |

每种组合都是一个目录工具（`pokeldn/app/catalog.py` 中 `Tool` 的 `activity` 和 `variant`），
因此一次运行、它保存的字段以及 `python -m pokeldn TOOL` 都保留该工具的键。只有一个选项的
选择不会显示：在线交换没有主机选择。更改一个选择会保留该行其他选择上次的取值。插件工具
也以同样的方式加入一行（[工具的所在行](plugins.md#a-tools-row-112)）。

## 应用语言

设置中的「应用语言」会列出英语和已安装的语言包（[语言包](plugins.md#language-packs-15)）；
更改在重启后生效，缺失的字符串会回退到英语。训练家语言是独立的。随附的 Noto Sans CJK SC
字体覆盖中文、日文和韩文（`gui/assets/fonts/LICENSE`）。它自带的 ‘ ’ “ ” · … 是全角形式，
因此 Noto Sans Punctuation（同一字体中这六个符号的拉丁宽度形式，
`scripts/gen_punctuation_font.py`）排在它前面；语言包的 `font_family` 仍排在最前。

## 你的训练家

设置中的「你的训练家」是应用构建的每只宝可梦的初训家：名字、性别、语言，以及按游戏显示
方式给出的两对 ID。记录中保存 16 位 TID 和 16 位 SID，它们是一个 32 位 id 的两半。

| 游戏 | 显示的 ID | 里ID | 存储的 id |
|---|---|---|---|
| 火红、叶绿 | TID，0 到 65535 | SID，0 到 65535 | `SID << 16 \| TID` |
| Let's Go、剑/盾、BDSP、传说 阿尔宙斯、朱/紫、传说 Z-A | id mod 10^6 | id div 10^6，0 到 4294 | `secret * 10^6 + ID` |

`Settings.ids` 会按游戏进行换算。每个与主机连接的工具都会把这个训练家作为其玩家呈现
（`tests/test_gui_catalog.py`）。火红/叶绿的名字会被截到七个第三世代字符；无法编码的名字
会变成 `POKELDN`（`Settings.name`）。传说 Z-A 只有在性别、ID 和名字都匹配时才把收到的
宝可梦视为玩家自己的（[收到的记录](za.md#what-the-trade-writes-into-a-received-record)）；
传说 阿尔宙斯的记录会带上性别（[记录](pla.md#the-games-reader-and-the-pre-handler-phase)）。

宝可梦文件会保留自己的初训家，除非提供卡片上的「让我成为它的初训家」开关打开：带
`trainer` 字段的 PKHeX `check` 会写入这个训练家的名字、ID 和性别（`Retrain`）。闪光与否
由 PID 对照这些 ID 决定。从第七世代起，PID 的高半部分会移动，以保持方形、星形或普通闪光；
遭遇固定的 PID（第三世代的性格、特性和性别，剑的野外或团体战种子）保持不变，卡片会说明
闪光发生了变化。只能搭配自身初训家才合法的宝可梦（例如固定初训家的活动宝可梦）会被拒绝，
并给出 PKHeX 的理由。

### 查找你的训练家

「查找我的」会用一次运行从主机读到的最近一个训练家，填入某一行的 ID 和里ID，以及名字、
性别和语言。Switch 游戏从不显示里ID；它由连接携带。

| 行 | 什么标明了训练家 |
|---|---|
| 火红、叶绿 | 主机的 LinkPlayer，`trainerId` = `SID << 16 \| TID`，在每次交换、神秘礼物和联盟房间会话中，两种角色都是 |
| Switch | 主机在一次 Let's Go、BDSP、传说 阿尔宙斯、朱/紫 或 传说 Z-A 交换中的会话数据，两种角色都是（[这是谁的存档](gift_simulated.md#whose-save-it-is)）；在剑/盾以及任何作品中，主机交换过的、由其存档捕获的宝可梦（handler 0，游戏自己的版本，不是蛋） |

启动器会为每个训练家打印一次 `[trainer] {json}`（`pokeldn.console_trainer`）；应用按行、
按游戏在 `settings.json` 的 `found_trainers` 中保留最新的一个，并在隐私日志掩码下记录它。
Switch 行服务于所有 Switch 作品，因此取最后一次与之交换的那个。什么都没找到时，
「查找我的」会提示进行交换。

### 每款游戏一个训练家

「每款游戏使用不同训练家」让每个作品拥有自己的名字、性别、语言、ID 和里ID，一次编辑一款
游戏；ID 按该游戏的显示方式给出。从未编辑过的游戏会沿用共享训练家。以两个版本发售的游戏
会分别列出每个版本（火红和叶绿、剑和盾，其余同理），因此同一游戏的两份存档各自保留训练家；
从未编辑过的版本沿用该游戏的训练家。两个版本不同时，该游戏的工具会在主持和加入旁显示
「你的游戏」，运行会使用所选版本的训练家。`settings.json` 以 `per_game_trainer` 保存该开关，
以 `game_trainers` 保存各值（游戏或版本键映射到有差异的字段），以 `played` 保存每款游戏
选中的版本。`Settings.own(game)` 是一款游戏看到的训练家；`Settings.ids`、`Settings.name`、
`Settings.trainer` 以及启动令牌 `{ot}`、`{tid}`、`{sid}`、`{language}`、`{gender}` 都通过
它读取（`tests/test_gui_catalog.py`）。游戏上的「查找我的」会取从该游戏读到的最新训练家。
设置会打开在最后编辑的那款游戏上。

`settings.json` 位于数据文件夹中，与应用分开，因此更新会把它留在原处：Windows 上是
`%APPDATA%\pokeldn`，macOS 上是 `~/Library/Application Support/pokeldn`，Linux 上是
`~/.local/share/pokeldn`。手机应用把它保存在各自的私有存储中，卸载会将其清除。

## Windows USB 驱动

经典 ESP32 的 USB 转串口桥需要驱动，Windows 才会给出 COM 端口（设备管理器问题代码 28）。
使用原生 USB 的 S3、C3 和 C6 不需要。

| 桥接芯片 | USB id | 驱动 |
|---|---|---|
| CP210x | `10c4:ea60` | [CP210x VCP 驱动](https://www.silabs.com/developer-tools/usb-to-uart-bridge-vcp-drivers)：右键点击 `silabser.inf`，安装，重新拔插 |
| CH340 | `1a86:7523` | [CH341SER.EXE](https://www.wch-ic.com/downloads/CH341SER_EXE.html)：安装，重新拔插 |

没有 COM 端口时，设备页每 2 秒轮询一次 `Win32_PnPEntity`（`ConfigManagerErrorCode <> 0`），
并指出已知的桥接芯片（`gui/board.py` 的 `bridges_without_driver`）。

## Linux 串口

端口需要 `dialout` 组（Arch 上是 `uucp`）；遇到 `EACCES` 时设备页会指出该组。

| 服务 | 设备 | 影响 |
|---|---|---|
| brltty 6.4（Ubuntu 22.04） | CH340 | 抢占它，没有 `/dev/ttyUSB*`（[LP 1990357](https://bugs.launchpad.net/bugs/1990357)）；修复：`sudo apt remove brltty` |
| brltty 6.6（Ubuntu 24.04） | CH340 | 仅在 `1a40:0101` 集线器后面抢占（[LP 1958224](https://bugs.launchpad.net/bugs/1958224)） |
| ModemManager 1.23 | 全部 | 没有针对 `10c4`、`1a86`、`303a` 的忽略规则 |

没有端口时，设备页会读取 `/sys/bus/usb/devices`，并指出没有 tty 的桥接芯片
（`gui/board.py` 的 `bridges_without_port`）。

## 本地存储

设置中的「存储」会显示可回收的空间；「清除本地文件」在确认后于后台删除这些内容，期间会
暂缓会话和刷写。请先保存错误报告所需的内容。

| 删除 | 保留 |
|---|---|
| `session/`（抓包、跟踪、临时提供）、`logs/`、`pokemon/` 中未使用的生成或导入的提供、空文件夹 | 不到一分钟或仍被已保存的设置和队列引用的提供；收到的文件、宝可梦银行、存档、密钥、固件、设置；符号链接；检查之后发生更改的文件 |

## 你的存档

火红/叶绿神秘礼物工具的「你的存档」标签页会备份或恢复主机的存档
（[存档备份与恢复](frlg_gift.md#save-backup-and-restore)）。存档位于
`Documents/pokeldn/Saves`（`pokeldn.app.saves`；设置 `POKELDN_DATA` 时位于其中），每份各有一个
`.sav` 和一个 `.json`。

| 操作 | 发生什么 |
|---|---|
| 从 Switch 备份 | 写入 `backup-<run>.sav`；被中断的备份留在 `Saves/.partial`，下次会继续 |
| 将存档放到 Switch 上 | 传入 `--save-restore`；选定存档之前「开始」被阻止 |
| `+` 或拖入的 `.sav` | 复制进来；16 字节的模拟器尾部会被丢弃，128 KB 以外的尺寸会被拒绝 |
| 重命名、导出、删除 | 删除会在本地移除两个文件 |
| 查看和编辑 | PKHeX 读取训练家、队伍和盒子 |

没有完整的存档副本，或队伍中有不合法的宝可梦时，恢复会被阻止，直到打开「仍然恢复」。
编辑器可更改训练家名字、性别、金钱、硬币和队伍；「保留为新存档」会通过 PKHeX 写入，
重新计算扇区校验和，作为新条目保存。

## 宝可梦银行

宝可梦银行页保存每只收到的宝可梦，并能把其中一只交换到 HOME 会把它转移到的任何游戏。
记录以各自游戏的格式连同 `.json` 保存在 `Documents/pokeldn/Bank`（`pokeldn.app.bank`；
设置 `POKELDN_DATA` 时位于其中）。

| 步骤 | 发生什么 |
|---|---|
| 一次交换完成 | 每个收到的文件按字节入库一次 |
| 一只宝可梦入库 | `.json` 保存物种、摘要、判定、来源、SHA-256、随机的 63 位追踪号、`home_tracker` |
| 目的地 | 助手的 `destinations` 会尝试全部七款游戏 |
| 选定一个目的地 | `move` 把它转换进该工具的队列，并带上 `"bank": id` |
| 第 N 次交换完成 | `[done] trade N complete` 把它从库中移除 |
| 运行失败 | 它留在库和队列中 |

移动使用 PKHeX 的 HOME 转换（通过 `PKH` 调用 `EntityConverter.ConvertToType`）以及目的地的
合法性检查。应用的训练家会成为处理者（`IHandlerUpdate`、`PB8.UpdateHandler`）；不合法的移动
会采用 PKHeX 建议的招式组合；PID、加密常量、OT 和 ID 保持不变，运行会省略 `--fresh-pid`。

| 拒绝 | 来源 |
|---|---|
| 无法回到火红/叶绿 | `EntityConverter.IsConvertibleToFormat` |
| 无法进入 Let's Go | HOME 只从它取出 |
| 蛋；带道具或秘传招式的火红/叶绿宝可梦 | HOME 的火红/叶绿筛查 |
| 物种或形态不存在 | 目的地的个人表 |
| 传说 Z-A 记录出库 | PKHeX.Core 26.10.18 没有可用路径 |

盒子会列出每只已入库的宝可梦，并支持按其摘要（按显示文本和英文：物种、昵称、性格、特性、
球）及其游戏名搜索，支持排序（最新、最旧、图鉴编号、名称）和筛选（闪光、等待交换、不合法）；
排序、筛选和图鉴筛选保存在 `settings.json`（`bank_view`）中。「选择」可以挑选多只宝可梦
（长按也会启动），用于一次导出到文件夹、移出交换或移除。选中多只时，侧边窗格会列出每款游戏
能接收其中多少只，并按盒子的顺序把它们排入所选交换工具的空位（队列最多六个）。精灵图的
裁剪会连同其 SHA-256 保存在精灵图缓存的 `index.json` 中，因此盒子打开时无需解码此前显示过
的 PNG。

宝可梦的窗格显示来自助手 `check` 的对战配置（`battle`）：按 Showdown 顺序的个体值、努力值
和能力值，以及供「复制为 Showdown 配置」使用的英文 Showdown 配置。努力值列在 Let's Go 中
是 AV（`IAwakened`），在传说 阿尔宙斯中按游戏显示方式给出 GV（存储值加上个体值的
`GanbaruExtensions.GetBias`），其他地方为 EV。

图鉴盒子会列出银行七款游戏中任一款持有的每个物种（助手 `species` 的并集），并为每个持有
的物种显示银行中的数量、精灵图和闪光标记；筛选可显示已持有、缺失或尚无闪光的物种。点击
已持有的物种会打开盒子并以其为搜索条件。

编辑只允许游戏允许的内容：昵称、向上调等级、招式、携带道具。助手 `check` 会拒绝使合法
宝可梦变得不合法的编辑。已排入队列的宝可梦不可编辑。`tests/test_bank.py` 通过真实助手覆盖
移动、拒绝、编辑和导入。

### 非合法宝可梦

设置、高级、允许非合法宝可梦（`Settings.allow_illegal`，默认关闭）会在每个助手请求中发送
`allow_illegal`；运行会以 `POKELDN_ALLOW_ILLEGAL` 继承该设置。构建器仍会先尝试所有遭遇。
若没有得到合法结果，助手的 `Forged` 会取一次遭遇的记录，并按请求写入种类、形态、等级、
是否异色、昵称、性格、性别、特性、个体值、招式、道具和精灵球；该记录会被标记为不合法。
特性与精灵球列表随后会提供游戏中的全部取值。第 3 世代的记录把性格和性别存在 PID 里，
因此会不断重掷 PID 直到两者匹配，并且只采用该种类拥有的特性。

该设置还会解除对非法文件、银行编辑、游戏间移动和交换的拒绝。游戏没有的种类或形态仍会被
拒绝。GTS 只保留合法宝可梦，因为挂牌会到达其他玩家，而绘制非法宝可梦可能导致游戏崩溃。

### HOME 追踪号设置

PKHeX 会对移入另一款游戏的宝可梦以及经由 HOME 而来的礼物标出缺失的追踪号
（`TransferTrackerMissing`）。HOME 3.1.0+ 会拒绝非它签发的追踪号（错误 10015）。
设置、高级、HOME 追踪号（`Settings.home_tracker`）会随每个助手请求发送，并以
`POKELDN_HOME_TRACKER` 传给运行。

| 设置 | 写入的追踪号 | 合法性 | 警告 |
|---|---|---|---|
| `empty`（默认） | 无 | 带追踪号合法时被接受 | PKHeX 标出缺失的 HOME 追踪号 |
| `made` | 随机 63 位（银行的） | 不变 | 无法存入 HOME |

在 `empty` 下，助手会基于带 HOME 更改的追踪副本判定记录（`ValidWithTracker`），因为 PKHeX
以追踪号作为跨 HOME 游戏进化的门槛，Z-A 也以它重新对齐特性。礼物遵循该设置
（`MendGift`）；生成的追踪号会带上 HOME 的更改（`HomeSeen`：朱/紫上以尺寸作为身高，Z-A 中
身高、体重和头目标记）。剑/盾的神秘礼物卡片从不携带追踪号
（[Pokemon HOME](swsh_gift.md#pokemon-home)）。

### 导入

加号按钮或拖入的文件可导入 PKSM 银行、存档（`SaveUtil.TryGetSaveFile`；3DS 存档是名为
`main` 的文件）或任意 PKHeX 格式的一条记录（`FileUtil.TryGetPKM`）。存档会先产出队伍再产出
盒子槽位；PKSM 银行按顺序产出其盒子槽位。

| PKSM 银行（`.bnk`） | 布局（PKSM `common/source/BankFile.cpp`） |
|---|---|
| 头部 | `PKSMBANK`、u32 版本、u32 盒子数量（版本 1 中没有，从长度读取） |
| 条目 | u32 世代标签，然后是用 `0xFF` 填充的解密记录；版本 1 和 2 中为 264 字节，版本 3 中为 0x150 |
| 槽位 | 每盒 30 个，最多 500 个盒子 |
| 标签（PKSM-Core `Generation.hpp`） | 0 第四世代、1 第五世代、2 第六世代、3 第七世代、4 Let's Go、5 第八世代（PK8）、6 第三世代、7 第一世代、8 第二世代；`0xFFFFFFFF` 为空 |

第一或第二世代的条目是带两个名字的单只宝可梦列表：第一世代 59 或 69 字节，第二世代 63 或
73 字节，当其最后一个字节为 `0x50` 或 0 时取日文长度（PKSM `3ds/source/Bank.cpp` 的
`Bank::pkm`）。版本高于 3 会被拒绝。盒子名称位于银行旁边 PKSM 的 `.json` 中，不会被读取。

| 记录 | 保存为 |
|---|---|
| 银行某款游戏的格式 | 合法时原样保存 |
| 其他任何格式 | 移除携带道具、遗忘第三/四世代秘传招式；若合法，则移动到第一个接收它的游戏：火红/叶绿、朱/紫、剑/盾、BDSP、传说 阿尔宙斯、传说 Z-A |

不合法记录、校验和错误、其他游戏的蛋以及无法抵达的物种会被拒绝。`Bank/.imported` 保存每条
导入记录的 SHA-256，因此重新导入存档只会带入发生变化的记录。

### 未解决

- HOME 是否接受生成的追踪号，或对跨游戏移动的宝可梦接受空追踪号。
- HOME 的火红/叶绿规则是否超出蛋、携带道具和秘传招式。
- 哪个字段携带 HOME 的 Switch 火红/叶绿来源图标；PKHeX 按宝可梦公园血统转换 `.pk3`。

## GTS

GTS 页列出公开的挂单，可按物种筛选，玩家自己的挂单在「你的」下。「仅闪光」只保留提供闪光
的挂单；「我的银行能应答」只保留可由合法且未排队入库宝可梦应答的挂单。挂单排序可按最新
优先、按结束日期、按图鉴编号或按等级。闪光的宝可梦——无论是提供、求取还是选来存入——都
带有闪光特效。「存入」会取一只合法且未排队的入库宝可梦，挂单期间保存在
`Documents/pokeldn/GTS`，并求取最多三个物种（每个可选择闪光），限定在一个等级范围内。
应用在运行时随时应答报价（[GTS](online.md#the-gts)）。

## 设备与固件

设备页列出每个已插入的设备，以及其固件、版本和「已是最新」或「有可用更新」。固件卡片
（`gui.board.FIRMWARES`）在确认后安装无线或控制器固件；「从文件安装」接收 pokeldn 的 `.bin`。

| 设备 | 发现方式 | 版本来源 |
|---|---|---|
| 无线 | 串口 | HELLO 应答 |
| 控制器，经典 ESP32 | 串口 | 状态帧 |
| 控制器，ESP32-S3 | USB id `0f0d:0092` | 蓝牙状态 |
| 无 | 串口，无应答 | 无 |

随附的版本是 ESP-IDF 应用描述符中的 `version`（magic `0xABCD5432`，在合并镜像中位于
`0x10020`）。运行控制器固件的 S3 会通过蓝牙收到下载命令；应用等待加载器端口 20 秒，并用
`--from-loader` 刷写。

作为[便携信标](hardware_esp32.md#portable-beacon)保留的设备会显示「已保留礼物」和「移除」。

### 设备详情

设备页上的「复制设备详情」（无论是否选中设备）会以纯文本复制详情，并保存为数据文件夹中的
`logs/board-report-DATE.txt`（`gui/board_report.py`）。复制时会打开选中的端口，因此设备
可能重启；运行期间它只列出端口。

| 部分 | 内容 |
|---|---|
| 这台电脑 | 应用版本、打包版或源码版、系统、Python、pyserial 和 esptool 版本 |
| USB 串口 | pyserial 列出的每个端口，及其 USB id、序列号、位置和 `hwid` |
| 驱动 | Windows 上无驱动的桥接芯片、Linux 上无 tty 的桥接芯片、USB 上的控制器设备 |
| 打开端口 | 打开时的错误及 `errno`/`winerror`，或前 2 秒读到的字节 |
| pokeldn 固件 | HELLO 和 STATUS，或为何无应答 |
| ESP32 引导程序 | esptool 的芯片、描述、特性、晶振、MAC 和 USB-Serial/JTAG 模式 |
| 活动 | 页面最近 80 行 |

## 控制器

控制页通过控制器固件按下 Switch 的按键（[控制器设备](hardware_pad.md)）并播放宏。
ESP32-S3 插入 Switch，通过蓝牙 LE 连接；经典 ESP32 留在电脑的 USB 上，从「更改握法/顺序」
配对。重新安装会清除配对。连接断开时，页面会持续搜索，直到设备应答或选择「停止查找」。

| 部分 | 作用 |
|---|---|
| 屏幕控制器 | 按住按键；摇杆八个方向，L3/R3 在中心 |
| 键盘 | 方向键 D-pad，X 对应 A，Z 对应 B，S 对应 X，A 对应 Y，Q 对应 L，W 对应 R，1 对应 ZL，2 对应 ZR，Enter 对应 +，Backspace 对应 -，H 对应 HOME，C 对应 Capture |
| 录制到宏 | 每次按下都会成为一个步骤，带按住时长和停顿 |
| 宏编辑器 | 按键、摇杆、等待、嵌套重复；「运行一次」和「循环」部分 |
| 在设备上播放 | 设备按自己的时钟播放宏 |

宏是 `Documents/pokeldn/Macros` 中的 `.pokemacro` 文件
（[控制器设备，宏](hardware_pad.md#macros)）。该页面通过 `127.0.0.1:47800` 与
`pokeldn.pad.service` 通信。在 macOS 26 上，以 bundle 主可执行文件签名的进程无法发现蓝牙
设备，因此打包版应用从 `Contents/Helpers/pokeldn-bluetooth` 运行该服务——一个裸签名的副本，
其 `_internal` 链接到 `../Frameworks`。

## 设备的屏幕

设置中的「显示板子的屏幕」会在会话面板顶部绘制设备的 128x64 像素屏幕，无论设备是否接了
屏幕（[屏幕](hardware_esp32.md#the-screen)）。应用会为运行设置 `POKELDN_SCREEN_MIRROR=1`；
随后运行会打印它发送的每条 DISPLAY 命令，并每秒打印来自 STATUS 的设备模式、就座站点、
数据帧和 BOOT 按下次数：

    [screen] reset
    [screen] cmd HEX
    [screen] radio MODE STATIONS RX TX PRESSES

`pokeldn.app.screen_render` 通过固件 `scene.c` 和 `screen.c` 的 Python 副本重放它们；
`tests/test_screen_render.py` 用编译后的 C 校验每一帧。面板按固件的 50 毫秒帧绘制，随设备
变暗，并在空闲十分钟后关闭。

## 宝可梦精灵图

图像按需来自 [PokeAPI](https://github.com/PokeAPI/sprites)，缓存在 `sprites/`。设置中的
「宝可梦精灵图」可禁用下载并清除缓存。缺失的图像显示占位图；缺失的闪光图会回退到普通图。

## 团体战活动

朱/紫 太晶团体战（主持）的「团体战活动」卡片会主持来自
[EventsGallery](https://github.com/projectpokemon/EventsGallery) 的团体战
（[活动团体战](sv_raid.md#event-raids)），复制到 `EventsGallery/`
（`pokeldn.app.events_gallery`）。「下载」会从 `codeload.github.com` 获取触及
`Released/Gen 9/SV/Raid Events` 的最新提交，并保留每个活动最新的表；「检查更新」会比较该
提交。副本只有在完整后才会替换旧的；Windows 以 `\\?\` 打开长路径。

选择活动会把团体战卡片限制为其版本、进度和水晶（`raid_event.constrain`），并把「查找团体战」
限制为其水晶、首领和奖励表（[寻找种子](sv_raid.md#finding-a-seed)、
[尺寸标记](sv_raid.md#size-marks)）。只能捕捉一次的首领会提供「让它再次可捕捉」
（`--raid-catch-normal`）。折叠卡片会恢复为标准团体战（「关闭：活动」）；副本中缺失的活动
显示为「缺失：活动」，运行会拒绝它。

## 主持团体战的奖励

「奖励」卡片提供模板（培养道具、薄荷、对战道具、树果、进化道具、太晶碎块、秘传调味料、
宝物、球），共用 1 到 999 的数量；编辑会切换到「自定义奖励」，最多 45 行。「团体战自身
奖励」会清除这些覆盖（[主持](sv_raid.md#hosting)；`gui/views/rewards.py`）。

## 团体战 NPC 伙伴

「团体战 NPC 伙伴」卡片会填补主机留空的槽位（[伙伴](sv_raid.md#partners)；
`gui/views/raid_partners.py`）；未做选择时，主机会像主机游戏那样抽取它们。伙伴的进度通过
`--raid-partner-progress` 传入；每张卡片显示训练家、宝可梦（等级为我方宝可梦的五分之四）、
太晶属性、特性和招式，受青睐的伙伴带有蓝色或银色条带
（[受青睐的伙伴](sv_raid.md#favoured-partners)）。每次点击都会按槽位顺序传入
`--raid-partner`；该阶段没有的选择会被丢弃。

## 联盟集友圈

朱/紫 的联盟集友圈工具会在四位连接密码下加入主机的集友圈
（[联盟集友圈](sv_union_circle.md)）；该字段初始为空。

- 任务：解锁剩余的 Snacksworth 传说的宝可梦，或给予 BP（1 到 9,999,999）；一次 Snacksworth
  运行会绘制通关数的[进度](#progress)条。
- 遭遇：生成卡片（`gui/views/encounter.py`）设置物种、闪光、形态、等级、太晶属性、性格、
  性别、特性、道具、标记、尺寸和个体值；「仅合法遭遇」（默认）会把它们限制在 PKHeX 接受的
  范围内，并列出有效地点。它会传入 `--spawn` 和 `--spawn-*`。

`[panel]` 卡片（[状态卡片](plugins.md#status-cards-18)）会在运行期间显示在工具选项上方。
`--verbose-circle` 会记录每条集友圈消息。

## 神秘礼物 - 模拟

该工具在 Let's Go、BDSP、传说 阿尔宙斯、朱/紫 和 传说 Z-A 上的卡片会列出 PKHeX 活动表中的
礼物宝可梦（[模拟神秘礼物](gift_simulated.md#the-gifts)；`gui/views/event_gifts.py`），最新
在前，可搜索。点击会把一份全新的副本排入队列，使用设置中的训练家；一次主持会话最多交换
六个礼物。副本会保留制作它时使用的训练家。

如果礼物指定的接收者语言没有任何存档触达，该礼物会显示为不合法图块
（[卡片触达的存档](gift_simulated.md#saves-a-card-reached)）。「为接收玩家制作」（默认开启）
会为主机的存档重制这类礼物
（[为接收玩家制作](gift_simulated.md#made-for-the-receiving-player)）；当没有符合条件的排队
礼物时，该开关被禁用，也不会传入 `--for-receiver`。HOME 礼物以琥珀色描边，并遵循
[HOME 追踪号设置](#the-home-tracker-setting)
（[交换提供的副本](gift_simulated.md#the-copy-a-trade-offers)）。

## 隐私日志

设置中的「在日志中隐藏个人信息」（默认开启）会遮蔽显示和复制的日志
（`pokeldn/app/redact.py`）：

| 遮蔽内容 | 显示为 |
|---|---|
| 路径中的主目录 | `~` |
| iOS 应用容器 | `<app>` |
| MAC 的设备部分 | `**:**:**` |
| `ot_name`、`ht_name`、`OT`、`nickname`、`trainer`、`player`、`name` 后的引用值（`POKELDN`、`PKLDN` 除外） | `***` |
| `TID`、`SID`、`trainer_id` 后的值 | `***` |
| 作为完整单词出现的已见训练家名字，以及设置中的名字 | `***` |

会话记录（`captures/`）不会被遮蔽。链路本地地址会保留。

## 弹出窗口

运行、子进程和应用可以在任何页面上打开弹出窗口（`pokeldn.popup`，插件 API 1.2）。

| 类型 | 回调 |
|---|---|
| `acknowledge(title, text)` | `on_ack` |
| `confirm(title, text, agree, disagree)` | `on_agree`、`on_disagree`、`on_dismiss` |
| `choose(title, text, options)`（1.7，2 到 8 个选项） | `on_choice(index)`、`on_dismiss` |

选项：`id`（重新打开已打开的 id 会替换它并丢弃其回调）和 `tone`（`info`、`warning`、
`error`）。打开会返回 id；回调在应答线程上运行，除非设置了 `set_dispatcher(dispatch)`。
`cancel(id)` 会关闭一个。32 个未应答的弹出窗口会引发 `RuntimeError`。没有应用时
（`available()` 为 false），弹出窗口是一行 `[pop-up]` 输出。

`runner.Process(..., popups=app.popups)` 会设置 `POKELDN_POPUPS=1`；子进程在 stdout 写入
`[popup]` 和 JSON，并从 stdin 读取 `[popup] {"id", "n", "answer"}`
（`pokeldn.app.runner.child`）；`n` 使对已被替换的弹出窗口的迟到应答不触发任何动作。
`pokeldn.app.popups.Manager` 保存它们，`gui.popups.Dialogs` 绘制它们。应用自身的弹出窗口会
报告更新失败、插件被禁用，以及用设置中的训练家发送的接收者礼物
（[交换](gift_simulated.md#the-trade)）。

## 运行状态

运行等待期间，会话面板会显示带时间的 `正在等待主机`；60 秒无主机后，它会询问主机是否停在
步骤所说的画面上。加入后会显示 `主机已连接`。设备的后端会在无线模块首次主持或扫描时打印
一次 `[link] waiting`，之后在每次站点或链路变化时打印 `[link] joined` 和 `[link] left`
（`pokeldn.ldn.show_link`，仅在应用启动的运行中；无线插件不会打印这些）。

### 运行失败时

`pokeldn.app.failure` 会读取运行输出的行，指出一个原因以及修复它的页面：

| 原因 | 匹配内容 | 按钮 |
|---|---|---|
| 设备断开 | `[esp32] The board's USB connection failed`、`the board left USB` | 设备 |
| 端口被占用 | `Resource busy`、`Access is denied`、errno 13 | 设备 |
| 固件不匹配 | `board speaks protocol N, host speaks M` | 设备 |
| 设备无响应 | HELLO 无应答，端口的设备消失 | 设备 |
| 缺少密钥 | `prod.keys has no NAME`（`ldn.MissingKey`） | 设置 |
| 加入失败 | `the board could not join` | |
| 无主机 | 出现 `[link] waiting` 且从未出现 `[link] joined`，没有完成交换 | |
| 其他任何情况 | 回溯和非零退出 | 复制日志 |

第一条匹配的行决定原因。玩家停止的运行，或已完成一次交换的运行，不会报告任何内容。
神秘礼物信标（`Tool.joins` 为 false）永远不会被归咎于主机。

### 重试失败的交换

开启设置中的「重试失败的交换」后，以可重试原因（设备断开、加入失败、无主机）结束的交换
运行会在 15 秒后用尚未交换的排队宝可梦重新开始，最多连续三次；完成过一次交换的运行会重置
计数。「不重试」会取消等待；按开始或选择另一个工具也会。

## 键盘快捷键

macOS 上是 Cmd，其他地方是 Ctrl：

| 按键 | 操作 |
|---|---|
| 1 到 6 | 游戏、设备、宝可梦银行、GTS、控制、文档 |
| , | 设置 |
| Enter | 会话面板的「开始」，或「停止并开始」（当它可以按下时） |
| . | 停止 |

## 更大字号

设置中的「更大字号」会把所有文字放大 15%（`gui/theme.py`、`text_scale`），在启动时读取。
最浅的文字颜色 `#98989D` 在它所处的最亮表面上仍保持 4.8:1 的对比度。

## 进度

运行会打印 `[progress] DONE TOTAL UNIT TITLE`（`pokeldn.progress.show`，API 1.7；`UNIT` 为
`bytes` 或 `items`）来绘制带数量、30 秒速率和剩余时间的进度条，每个标题每秒最多四行。
`[save]` 行会绘制同样的进度条。

## 更新

启动时应用会查询 `api.github.com/repos/Decryptu/pokeldn/releases/latest`（5 秒超时）。高于
`pokeldn.__version__` 的 `vX.Y.Z` 标签会添加一条更新条目，带「立即更新」或「下载」。

「立即更新」（`pokeldn.app.update`）会把平台压缩包和 `SHA256SUMS` 下载到 `update/`，
校验和不匹配则拒绝，解包（`ditto -x -k`、`tarfile` 的 `data` 过滤器、`zipfile`），然后启动
`pokeldn --apply-update NEW TARGET PID VERSION`（`gui/updating.py`）。助手会等待旧应用退出
（Windows 上还等待其进程），把它重命名为 `.<name>.old`，复制新的进来并打开；任何失败都会
恢复旧应用。新应用会读取一次 `update/outcome.json`。校验和只能检测损坏，不能验证发布版的
身份。

| 情况 | 行为 |
|---|---|
| 预发布、草稿、异常标签 | 不提供 |
| 无网络 | 「立即检查」会提示 GitHub 没有应答 |
| 设置中关闭更新 | 启动时不发请求 |
| 没有压缩包或 `SHA256SUMS`、源码检出、App Translocation、不可写的文件夹（macOS、Linux） | 仅下载 |
| Windows，`C:\Program Files` | 「立即更新」需经 UAC（`ShellExecuteExW` `runas`） |
| Windows，另一个盘的根目录（`D:\pokeldn`） | 「立即更新」无需 UAC：交换只会在应用旁添加文件夹，而卷根目录允许用户这样做。0.34.0 之前的发布版会用文件探测根目录，在那里请求 UAC，标准用户的更新会停在「Windows 未授予 pokeldn 更改 D:\ 的权限」；从这样的版本开始，下一个版本需要手动下载一次 |
| Windows，映射或 `subst` 驱动器 | 保留驱动器盘符；助手在两种拼写下都能找到旧应用的进程；在 UAC 之后，助手拿到该盘符所代表的文件夹，因为提权进程看不到用户会话映射的盘符 |
| 会话、刷写或清理正在运行 | 会先请求结束它 |

`scripts/check_update.py ARCHIVE FOLDER` 会用 127.0.0.1 测试打包应用的更新；
`POKELDN_UPDATE_URL` 会替换端点（`tests/test_app_update.py`）。macOS 在 `/Applications` 中
是否会请求 App 管理权限，尚未测量。

## 文件拖放

| 目标 | 接受 |
|---|---|
| 交换的宝可梦 | 宝可梦文件或 Showdown `.txt`；多出的会填进后续交换 |
| 添加交换 | 每个文件一次交换 |
| 礼物卡片 | `.pokegift`、`.wc8`、`.wc3` |
| 设备固件卡片 | pokeldn 的 `.bin` |
| 任何路径字段 | 该文件，或它所在的文件夹 |

Flet 1.0.2 的客户端不接受拖放；`scripts/build_client.py` 会用 `gui/flet_drop`
（[desktop_drop](https://pub.dev/packages/desktop_drop)）把 Flet 的客户端构建到
`gui/client/<platform>`，使用 `python -m flet_cli.cli --version --json` 指定的 Flutter 版本，
macOS 部署目标为 12.0。没有它时，`gui/main.py` 会运行 Flet 自带的客户端，不支持拖放。

## 文档页

文档页会显示应用指南和本站所有可导航的页面；搜索匹配小节，要求包含每个词，标题匹配优先
（`gui/views/docs.py`）。

## 未发布作品

早于 Switch 发售的作品只有在源码检出中才会出现在游戏、宝可梦银行和文档里
（`pokeldn/app/preview.py`）。`POKELDN_PREVIEW=1` 在任何地方都会显示它，`0` 则隐藏。它的
文档页会设置 `nav_exclude` 和 `search_exclude`。

## 从源码运行

安装 Python 3.13 和 .NET 10 SDK：

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r gui/requirements.txt
dotnet build -c Release services/pkhex -warnaserror
python scripts/build_client.py    # optional: file drops; needs Flutter
python gui/main.py
```

Raspberry Pi OS 会把 piwheels 添加为包索引，而 piwheels 的
`flet_web-1.0.2-py3-none-any.whl`（25 KB）缺少 PyPI 的 wheel（27 MB）所携带的 `flet_web/web`
客户端；应用随后会报 `RuntimeError: Web root path not found`。仅从 PyPI 安装该包：
`python -m pip install --force-reinstall --no-cache-dir --index-url https://pypi.org/simple flet-web==1.0.2`。
没有 Linux arm64 发布版；树莓派需要从源码运行应用。

源码检出中没有固件镜像。设备页上的「下载固件」会从最新发布版获取所有镜像和 `SHA256SUMS`，
只有全部匹配时才写入。

## 构建桌面应用

激活 ESP-IDF 6.1 后，把每个镜像构建到 `gui/firmware`，然后打包：

```sh
mkdir -p gui/firmware
OUT="$PWD/gui/firmware"
cd firmware/esp32
for t in esp32:radio esp32s3:radio-s3 esp32c3:radio-c3 esp32c6:radio-c6; do
  chip=${t%%:*}; name=${t#*:}
  idf.py -B build/$chip -D SDKCONFIG="$PWD/build/$chip/sdkconfig" set-target $chip
  idf.py -B build/$chip -D SDKCONFIG="$PWD/build/$chip/sdkconfig" build
  idf.py -B build/$chip merge-bin -o "$OUT/pokeldn-$name.bin"
done
export POKELDN_BLE=1   # Bluetooth images for the iOS app (hardware_esp32.md, Bluetooth)
DEF="sdkconfig.defaults;sdkconfig.defaults.ble"
for t in esp32:ble esp32c6:ble-c6; do
  chip=${t%%:*}; name=${t#*:}
  idf.py -B build/$name -D SDKCONFIG="$PWD/build/$name/sdkconfig" -D SDKCONFIG_DEFAULTS="$DEF" set-target $chip
  idf.py -B build/$name -D SDKCONFIG="$PWD/build/$name/sdkconfig" -D SDKCONFIG_DEFAULTS="$DEF" build
  idf.py -B build/$name merge-bin -o "$OUT/pokeldn-radio-$name.bin"
done
unset POKELDN_BLE
cd ../pad
idf.py -B build -D SDKCONFIG="$PWD/build/sdkconfig" set-target esp32s3
idf.py -B build -D SDKCONFIG="$PWD/build/sdkconfig" build
idf.py -B build merge-bin -o "$OUT/pokeldn-pad-s3.bin"
cd ../..
python scripts/build_client.py
python scripts/build_unicorn.py   # needs CMake
python scripts/pack_app.py
```

冻结应用检查会验证每个镜像、`flet_drop` 客户端和 Unicorn 都已打包。版本是
`pokeldn.__version__`，随 `.github/release-notes.md` 提升，其第一行必须是
`# pokeldn X.Y.Z`（`tests/test_release.py`）。`v*` 标签会发布九个文件和 `SHA256SUMS`；只有
带连字符的标签是预发布。

应用是单文件夹的 PyInstaller 构建（`pokeldn.app`；在其他平台上是一个含 `_internal` 的
`pokeldn` 文件夹）：在 M4 上，游戏页在 0.7 秒内打开，运行在 0.08 秒内启动。
`scripts/pack_app.py` 在 Flet 的 `--onefile` 之后传入 `--onedir`，并设置 `LSBackgroundOnly`，
使只有查看器拥有 Dock 图标。

| 部分 | 大小 | 精简方式 |
|---|---|---|
| Flet 查看器 | 31 MB（macOS 上 xz 后 9.4 MB） | 不含可选扩展、单一架构、`--split-debug-info` |
| Unicorn | 3 MB | 仅 ARM 和 ARM64 引擎 |
| PKHeX 助手 | 16 MB | 完全裁剪 |
| Python | 8 MB | 排除 web、图像、测试和语法模块；macOS 上 `strip -x` |

打包陷阱：

- 裁剪会禁用反射 JSON；`JsonSerializerIsReflectionEnabledByDefault` 可恢复它。
  `DynamicDependency` 保留 PKHeX.Core 的第三世代活动表。
- macOS 查看器压缩包是 xz，名字为 `flet-macos.tar.gz`；`gui/flet_client.py` 会以压缩检测
  打开它，并删除标记为 `pokeldn-drop` 的过期 `~/.flet/client` 文件夹。
- 绝不要 strip 可执行文件或 PKHeX 助手：两者的 Mach-O 镜像之后都带有一个归档。
- `scripts/pack_flet.py` 保留查看器的授权；没有
  `com.apple.security.files.user-selected.read-write` 时，选择 `prod.keys` 会引发
  `ENTITLEMENT_NOT_FOUND`。
- 在 Linux 上，`pokeldn/app/paths.py` 会恢复用户的 `LD_LIBRARY_PATH`（随附的 `libstdc++`
  会让 Fedora 的 EGL 出错）并设置 `FLET_LINUX_DISTRO`。
- Unicorn 在控制流保护下会以 `0xC0000409` 中止
  （[unicorn#2281](https://github.com/unicorn-engine/unicorn/issues/2281)）；打包器会清除
  `pokeldn.exe` 中的 `GUARD_CF`（`0xC160` 改为 `0x8160`）。绝不要在冻结检查中启用
  `faulthandler`。

### 应用图标

`gui/AppIcon.icon` 是一个 Icon Composer 文稿，是 macOS 和 iOS 图标的唯一来源。`actool`
（Xcode 26）把它编译成 `Assets.car` 和 `AppIcon.icns`；`scripts/pack_app.py` 会把两者放进
`pokeldn.app` 和 Flet 查看器，并设置 `CFBundleIconName`。macOS 26 会从目录中绘制分层图标；
macOS 12 到 15 绘制它的平面版本，这些版本位于 Apple 的图标网格上（图块占据 128 像素中的
102 像素）。Windows 使用 `gui/assets/icon.ico`，Linux 使用 `gui/assets/icon.png`，两者都是
满幅：两个平台都不会给图标留边。
