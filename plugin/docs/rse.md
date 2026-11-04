---
title: 红宝石、蓝宝石与绿宝石
nav_order: 11
has_children: true
nav_exclude: true
search_exclude: true
---

# 红宝石、蓝宝石与绿宝石

红宝石、蓝宝石与绿宝石没有 Switch 版；pokeldn 对它们的支持是从
[pret/pokeemerald](https://github.com/pret/pokeemerald) 和 [pret/pokeruby](https://github.com/pret/pokeruby)
准备出来的，计划与火红、叶绿放在同一个 GBA 应用里发布。所有地址都取自 GBA 英文版。只有从源码仓库运行时，应用才会显示这个标题（见[未发布的游戏](gui.md#unreleased-titles)）。

为那个应用编译的绿宝石会代替火红的卡带运行，并与 pokeldn 的主机对接（见 [Switch 版构建](rse_switch_build.md)）。在正式发布之前，这几页讲的都以那个构建为实验对象。

| 页面 | 主题 |
|---|---|
| [交换与联盟室](rse_link.md) | 加入主机、连接交换、联盟室 |
| [神秘礼物](rse_gift.md) | 协议差异、礼物、菜单入口 |
| [Switch 版构建](rse_switch_build.md) | 给火红应用用的绿宝石：移植、构建、运行、测试存档 |

GBA 应用里已经为全部五个第三世代游戏代号准备了通关报告表，其中包括 `AXV?`、`AXP?` 和 `BPE?`（见[在主机上运行代码](frlg_rom.md)），而十二个火红与叶绿标题共用同一个本地通信 id `0x01006fa0233f8000`（见 [ROM 映射表](frlg_rom_map.md)）。

## 各游戏在链路上能做什么

| | 红宝石 / 蓝宝石 | 绿宝石 |
|---|---|---|
| 无线适配器（RFU）代码 | 无：只有 SIO 多人线缆 | 火红的 `link_rfu_2.c` |
| 连接交换 | 线缆 | 直连角与联盟室，同火红 |
| 神秘礼物（神秘卡片、神秘新闻） | 无 | 火红的协议与结构体 |
| 神秘事件 | 通过线缆的 e-Reader，由「MYSTERY EVENT IS EXCITING」开启 | 标题菜单里没有 |

两个启动器说的是无线适配器协议，所以只能连到绿宝石。链路之上，RS 的线缆协议共用 `LinkPlayer` 记录、200、200、100、220、40 的块大小、链路命令字和交换块 [pokeruby link.c, trade.c]。RS 会在火红与绿宝石读作进度标志的那些字节上写入一个 11 字节的名字，所以面对 RS 伙伴时两者都会把这些标志清零。

## 标识符

| 字段 | 红宝石 | 蓝宝石 | 绿宝石 |
|---|---|---|---|
| 游戏代号 | `AXV` + 语言 | `AXP` + 语言 | `BPE` + 语言 |
| 头部标题 | `POKEMON RUBY` | `POKEMON SAPP` | `POKEMON EMER` |
| `gGameVersion` | 2 | 1 | 3 |
| `LinkPlayer.version` | `0x4002` | `0x4001` | `0x4003` |

语言字母是 `E`、`F`、`D`、`I`、`S` 或 `J` [include/constants/global.h:8-12]。

## 存档

闪存布局、签名 `0x08012025` 和校验和都与火红相同 [save.c]。SaveBlock1 为 `0x3D88` 字节，SaveBlock2 为 `0xF2C` 字节；扇区校验和为 `0xF2C`、三次 `0xF80`、`0xF08`、八次 `0xF80`，按 id 分别是 `0x7D0` 字节。队伍数量 `0x234`，队伍 `0x238`，金钱 `0x490`（与 SaveBlock2 的 `+0xAC` 异或），标志 `0x1270`，变量 `0x139C`，游戏统计 `0x159C`，神秘礼物 `0x322C`。SaveBlock2 没有 `filler_B20`。

| 字段 | 偏移 | |
|---|---|---|
| SaveBlock1 `continueGameWarp` | `0x0C` | `WarpData`：s8 组、s8 地图、s8 传送点 id、填充、s16 x、s16 y |
| SaveBlock2 `specialSaveWarpFlags` | `0x09` | 位 0 `CONTINUE_GAME_WARP`：CONTINUE 会传送到 `continueGameWarp` [overworld.c:1739] |

没有 `CONTINUE_GAME_WARP` 时，CONTINUE 会用 `pos` 和 `location` 恢复 SaveBlock1 的地图视角与对象事件；只改 `pos` 和 `location` 的存档编辑会载入旧地图，并且玩家看不见。

## pokeldn 尚未实现的绿宝石链路功能

记录混合、树果搅拌机、华丽大赛、对战塔的连接多人对战、树果粉碎、宝可梦跳绳与嘟嘟利采果（链路组 12 到 21，活动 14 与 23 到 29）。

## 尚未解决

- Switch 版是否存在，以及它的标题 id、游戏代号和软件版本。
- 它是否沿用火红应用的通信 id、场景 id 和广播打包方式。
- Switch 版如何承载红宝石与蓝宝石的线缆链路。
- Switch 版绿宝石的所有 ROM 与 RAM 地址。
