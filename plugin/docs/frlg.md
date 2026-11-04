---
title: 火红与叶绿
nav_order: 4
has_children: true
---

# 火红与叶绿

火红与叶绿在 Switch 上的发行版是运行于模拟器中的原版 GBA ROM，其上叠加了两层连接：

| 层 | 归属 | 记载于 |
|---|---|---|
| LDN 与 Pia | 模拟器的，与所有 Switch 游戏共用 | [无线层](ldn.md) |
| GBA 连接：RFU 帧、席位、块发送 | ROM 的 | 本组页面 |

`REVISION >= 0xA` 的 [pret/pokefirered](https://github.com/pret/pokefirered) 是游戏层协议的权威依据。法版卡带报告的软件版本为 `0x0A`，游戏代码为 `BPRF`（火红）和 `BPGF`（叶绿）。主机还携带了英语、德语、意大利语、西班牙语和日语各语言对的 ROM 与 RAM 地址，合计十二张卡带；玩家在好友列表中选择 pokeldn 后，神秘礼物会依据游戏代码从中挑选一张。覆盖情况见[零售验证](frlg_rom_map.md#retail-verification)与[卡带映射](frlg_rom_map.md#the-international-revision-0x0a-cartridges)。

一台在关联后约三秒（此时 Pia 会话已完成）就离开的游戏主机，收到的是不含 6、9、12 Mbit/s 的关联响应（[frlg_link.md](frlg_link.md)，广播的速率集）。缺少 Pia 类型 2 的 Join Response 会出现相同症状。

## 可用功能

在零售硬件上、两张卡带上，主机都能提供双向的神秘礼物、作为主机方与加入方的交换、带完整连接对战的联盟室、神奇新闻、电缆俱乐部竞技场，以及一位来访的对战塔训练家。

游戏主机通过礼物链路的两个解释器运行发送给它的代码：读写内存、把 ROM 按构建映射为具名函数、以八个参数调用其函数，以及让主机选定的宝可梦经其自身的 `CreateMon` 生成并放入队伍。随机数生成器可被端到端预测；一次瞄准的闪光遭遇每次尝试只需按一次 A。

访客与封装层之间的接口见[游戏主机上的代码](frlg_rom.md#coverage)，封装层的扫描流水线到其第一阶段为止的部分见[封装层自己的扫描流水线](frlg_rom.md#the-wrappers-own-scan-pipeline)。

## 页面

| 页面 | 内容 |
|---|---|
| [连接协议](frlg_link.md) | RFU 链路层、席位屏障、联盟室、聊天、连接对战、电缆俱乐部竞技场 |
| [神秘礼物](frlg_gift.md) | 礼物会话、创作礼物、神奇新闻、来访训练家、被封锁的无线通信路径 |
| [游戏主机上的代码](frlg_rom.md) | 神秘事件 VM、原生 ARM 载荷、实时存档 |
| [ROM 映射](frlg_rom_map.md) | 地址来源、四张函数表、物种表、法语 Easy Chat 词表 |
| [随机数生成器](frlg_rng.md) | 读取与预测 `gRngValue`、用于瞄准遭遇的场地桩函数 |
| [叶绿](frlg_leafgreen.md) | 到火红的偏移映射、作为测量工具的英文构建 |
| [主机实现](frlg_host.md) | 交换与神秘礼物主机的各个组件 |

## 规则

- 叶绿以分段常量偏移运行同一份代码（[叶绿](frlg_leafgreen.md)）。绝不要跨未加括号的区段预测地址。
- 反编译产物的链接顺序是证据；其地址仍需在卡带上实测。`pokeldn/frlg/rom/rom_map.py` 记录了每个地址的获取方式。
- 载荷在发送前先在 unicorn 下离线运行（`buffer_script.emulate`、`emulate_repeating`，两者都是模拟的游戏主机）。出错或永不返回 1 的载荷会卡住神秘礼物菜单；无限循环的场地桩函数会冻结大地图。
