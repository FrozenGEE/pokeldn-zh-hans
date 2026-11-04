---
title: 逆向分析一款 Switch 游戏
nav_order: 3
---

# 逆向分析一款 Switch 游戏

本页讲的是就地读取一款零售 Switch 游戏的代码，适用于 Unity/IL2CPP（晶灿钻石与明亮珍珠）和原生 C++（剑与盾）游戏。

## 工作顺序

1. 先在已公开的来源中查找某个常量，包括 NintendoClients wiki 的逐游戏页面：

       gh search code "<a constant, a field name, a class name>" --limit 20
       gh api repos/kinnay/NintendoClientsWiki/contents/<Page>.md --jq .content | base64 -d

2. 查找已有的反编译项目（BDSP 的 `TeamLumi/opendpr`）以及共用游戏密钥的客户端。
3. 在同一个构建的可执行文件和元数据中为所有东西命名。
4. 在二进制中验证。
5. 最后才搜索密钥空间：一个错误的输入就会给出看似确定的否定结果。

## 取出可执行文件

### 从 NSP

NSP 是由 NCA 组成的 PFS0。title key 位于 `<rights id>.tik` 中：加密密钥在 `+0x180`，rights id 在 `+0x2A0`；其最后一个字节 *n* 选择 `titlekek_{n-1}`。稀疏文件（用 `dd` 把所需区间写入一个经 `truncate` 创建的文件）能通过 hactool 的边界检查。

### 从 XCI

`tools/switch/xci_read.py` 遍历 HFS0/PFS0，解密 NCA 头并打印每一节的偏移、计数器和密钥；卡带 NCA 的正文密钥是 `key_area_key_application_<max(crypto_type, crypto_type2) - 1>` 下的 key area 槽位 2。

    ./.venv/bin/python tools/switch/xci_read.py <the.xci> --keys prod.keys --type Program
    ./.venv/bin/python tools/switch/xci_read.py <the.xci> --nca <id> --exefs 0 --extract main

陷阱：`fs_type` 在 +0x2，哈希类型在 +0x3（hactool 把两者的名称弄反了）；节计数器是反向使用的。

### 从 RomFS

各节使用 AES-128-CTR（计数器：节的 CTR 与大端序的 `offset >> 4`），因此任意区间都可单独解密。`tools/switch/romfs_read.py` 负责遍历和提取，遇到 size 字段不是 `0x50` 的头会拒绝。陷阱：hactool 遇到含 34 位十六进制数字的 `prod.keys` 行会中止，对稀疏文件执行 `--listromfs` 会段错误。

## 先命名一切

- IL2CPP：`global-metadata.dat` 加上同一构建的可执行文件，可让 Il2CppDumper 得到每个 C# 方法。
- C++ RTTI：`tools/switch/rtti_names.py` 从重定位中为 `nn::pia` 类命名（BDSP 中 279 个，剑与盾中 252 个）。`LocalProtocol` 与 `LanProtocol` 之分把 LDN 与 LAN 的密钥派生区分开来。

## 只存在于元数据中的常量

`[Serializable]` C# 类的 `byte[]` 默认值只存在于 `global-metadata.dat` 中，形式为 `Field$<PrivateImplementationDetails>.<SHA-1>`，通过构造函数中的 `InitializeArray` 访问。BDSP 的游戏密钥种子就是这样存储的。

## 确认导出的是哪个版本

BDSP 的基础版定义了 24 条网络消息，1.3.0 定义了 65 条：

| 结构 | 基础版 | 1.3.0（[协议页面](bdsp_protocol.md#framing)） |
|---|---|---|
| `PosData` | `Vector3 pos, short rotY`，16 字节 | `ushort posX, ushort posZ, short rotY`，6 字节 |
| `JoinData` | 少两个字段，已对齐 | `byte, byte, byte, short, Vector3`，17 字节未对齐 |

用基础版导出的布局去解码 1.3.0 的抓包，会得到看似合理却毫无意义的结果。`strings global-metadata.dat | grep NetPlayerNameData` 只能在 1.3.0 中找到。常量能跨越更新存活；结构不能。

## 读取游戏更新的 RomFS

更新的 RomFS 是叠加在基础版之上的 BKTR 节；`tools/switch/bktr_read.py` 会组合其重定位表和子节表：

    ./.venv/bin/python tools/switch/bktr_read.py UPDATE.nsp --base BASE.nsp \
        --extract /Data/Managed/Metadata/global-metadata.dat

陷阱：XCI 的更新分区中存放的是系统标题的 Program NCA；应根据更新所属的 title 来选择基础版。

## 查找调用方

扫描 `bl` 和尾调用 `b`：BDSP 的 `ANetData<SelectData>$$SendReliableData` 只有 `b` 调用方。没有任何分支指向的方法，可能是通过 ADRP/ADD 注册的委托（`arm64_xref.py`）。

陷阱：`arm64_xref.function_start` 可能越过 `udf` 填充进入前一个函数；用「入口之后 N 字节」来界定函数可能越过其 `ret`；`mov w0, #0x80` 是一条 ORR 立即数指令，字节扫描看不到它。

## 调用 nnSdk

对 nnSdk 的调用会经过一个由 JUMP_SLOT 重定位命名的 GOT 槽位（`tools/switch/nso_imports.py`）。

## 训练家名字

每款 Switch 游戏的训练家记录都在玩家名字旁带一个语言 id（PKHeX 的 LanguageID：1 日语、2 英语、3 法语、4 意大利语、5 德语、7 西班牙语、8 韩语、9 和 10 中文），游戏会用该语言对应的字体绘制名字。一台零售日版朱在记录标注为英语（2）的情况下，把假名名字 キリコ 用窄的半角字形绘制出来，而同一名字从日文存档读取时呈全角。`pokeldn.trainer_language.for_name` 会选出写入的名字所需的 id：假名用日语，谚文用韩语，汉字用日语（除非记录已经是中文）；拉丁字母名字保留记录的 id。每款游戏的身份写入器都会应用它：

| 游戏 | 语言所在位置 |
|---|---|
| 朱与紫 | 记录 1 的 `+0x11` |
| 传说 Z-A | 1400 身份值的第三个整数，名字前一个字节 |
| 剑与盾 | MyStatus `+0xA7`、TrainerCard `+0x1B`、档案的语言位 |
| 晶灿钻石与明亮珍珠 | PlayerInfo 和 `TradeTranerData` 的语言字节 |
| Let's Go | 首条消息的 MyStatus `+0x35` |
| 传说 阿尔宙斯 | 数据交换记录的 `+0x22` |

## 工具

全部离线，基于 `pokeldn.switch`：

    tools/switch/nso_read.py     把 NSO 的各段按其内存偏移解压
    tools/switch/nso_relocs.py   RELA 与 RELR 重定位（现代游戏使用 RELR）
    tools/switch/arm64_xref.py   ADRP 交叉引用、BL 调用图、函数起始
    tools/switch/arm64_dis.py    capstone 反汇编
