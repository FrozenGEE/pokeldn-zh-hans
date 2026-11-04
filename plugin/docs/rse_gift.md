---
title: 绿宝石 神秘礼物
parent: 红宝石、蓝宝石与绿宝石
nav_order: 2
nav_exclude: true
search_exclude: true
---

# 绿宝石的神秘礼物

绿宝石的神秘礼物就是火红那一套（见[神秘礼物](frlg_gift.md)），只是数字换成绿宝石的。启动器是 `bin/frlg_mg_host.py --version emerald`。

## 菜单入口

只要 `FLAG_SYS_MYSTERY_GIFT_ENABLE`（`0x8DB`）被设置，标题菜单就会列出 MYSTERY GIFT。玩家持有图鉴后，在友好商店柜台做那份问卷并选 LINK TOGETHER WITH ALL 就能设置它 [questionnaire.inc:30-37; easy_chat.c:693]。之后的路径是神秘礼物 → 神秘卡片 → 好友。

## 协议

传输方式、脚本、332 字节的 `WonderCard`、444 字节的 `WonderNews` 和 `MysteryGiftSave`（`0x36C`）都是火红的。神秘卡片时 GameData 的 `+0x0C` 与 `+0x10` 分别带 4 和 `0x200`，神秘新闻时带 5 和 `0x201`，而火红发的是 1 和它自己的版本码 [mystery_gift.c:346-363]；绿宝石的校验在卡片时要第 2 位和 `0x380` [mystery_gift.c:390]。主持端按主机游戏代号所指的那款游戏的规则来处理。绿宝石的字段操作码只在 `0xC7..0xCC`、`0xD0`、`0xD3..0xD5` 处不同，一直到 `0xE3`。

| | 火红 / 叶绿 | 绿宝石 |
|---|---|---|
| 卡片 flagId 1000（`sReceivedGiftFlags[0]`） | `0x2A7` | `0x13A` |
| `FLAG_MYSTERY_GIFT_DONE` | `0x3D8` | `0x1E4` |
| 礼物光标变量 | `0x40B6..0x40BC` | `0x40DE..0x40E4` |
| 最后一个道具 | 374 | 376（`ITEM_OLD_SEA_MAP`） |
| `StartLegendaryBattle` / `GetMysteryGiftCardStat` | 312 / 390 | 314 / 392 |
| `special` 索引检查 | 由 `gSpecialsEnd` 限定 [scrcmd.c:101] | 无：527 个 special [scrcmd.c:119] |
| SaveBlock1 里的 RamScript | `0x361C` | `0x3728` |

`gift_composer` 接受一张 `GameRules` 表；`pokeldn.rse.constants.EMERALD_RULES` 按绿宝石的数字编译。遇到别款游戏的主机，主持端会在发送前拒绝。绿宝石的神秘新闻没有奖励。

在模拟主机上，[Switch 版构建](rse_switch_build.md) 会出现在好友搜索里并显示为 POKELDN，表明自己是未持卡的绿宝石，随后接收古代海图卡片并正常关闭 LDN；之后宝可梦中心 2 楼的配送员会按存档里的脚本交出 OLD SEA MAP。

## 礼物

`pokeldn.rse.gifts` 用 pokeldn 的文案逐条重建 pokeemerald 的四个官方礼物脚本（`tests/test_rse.py` 比对字节码）。宝可梦中心 2 楼的神秘礼物员会运行存档里的脚本。

| 预设 | 卡片 flagId | 作用 |
|---|---|---|
| 极光船票 | 1000 | 船票与 `FLAG_ENABLE_SHIP_BIRTH_ISLAND` |
| 神秘船票 | 1001 | 船票与 `FLAG_ENABLE_SHIP_NAVEL_ROCK` |
| 古代海图 | 1002 | 海图与 `FLAG_ENABLE_SHIP_FARAWAY_ISLAND` |
| 变化洞窟传闻 | 1003 | 切换到洞窟九张野生表里的下一张 |
| 无限船票 | 1007 | 游戏自带的发放 [cable_club.inc:33]：船票与 `FLAG_ENABLE_SHIP_SOUTHERN_ISLAND` |
| 大师球、神奇糖果 ×5、会冲浪的皮丘蛋 | 1004..1006 | 在 `EMERALD_RULES` 下合成 |

    POKELDN_RADIO=esp32:auto ./.venv/bin/python -u bin/frlg_mg_host.py --live --version emerald \
        --gift-file old-sea-map.pokegift --keys "$HOME/Documents/Switch/23.0.0 keys/prod.keys"

预设可以用 `pokeldn.gifts.save(PATH, pokeldn.rse.gift_builder.compile(PRESET[key].state))` 存成文件。绿宝石的礼物文件只有一个变体 `emerald`（见[神秘礼物文件](gifts.md)）。原生代码、存档备份和火红的预设对绿宝石一律拒绝。

## 尚未解决

- 日版绿宝石的神秘礼物活动与卡片大小。
- Switch 版是否保留菜单入口。
