---
title: 交换与联盟室
parent: 红宝石、蓝宝石与绿宝石
nav_order: 1
nav_exclude: true
search_exclude: true
---

# 绿宝石的交换与联盟室

绿宝石的无线链路就是火红那一套（见[连接协议](frlg_link.md)）；本页只列绿宝石的不同之处。启动器是 `bin/frlg_trade_host.py` 与 `bin/frlg_trade_join.py`，加上 `--version emerald`。测量都是在模拟主机上跑 [Switch 版构建](rse_switch_build.md) 得到的。

## 加入主机

广播记录与 `RfuGameData` 沿用火红的 [include/link_rfu.h:80-113]。对于版本不是 3 的主机，绿宝石会把它列为「未就绪」，除非玩家已是冠军且该主机广播了 `canLinkNationally` [union_room.c:1266-1283; trade.c:2514-2521]。`--version emerald`（或 `ruby`、`sapphire`）会广播该版本，并按存档里的资料设置 `canLinkNationally`、`hasNationalDex` 和 `gameClear`（分别对应 `[16:20]` 那个字的第 16、17、24 位；`RfuGameData` 的第 7、8、9 位）。火红与叶绿保持这些位为 0。

在 `FLAG_SYS_POKEDEX_GET`（`0x861`）被设置之前，宝可梦中心 2 楼的每位店员都会回答「正在调整中」[cable_club.inc:803, 885, 901, 1152]。

## 交换

链路同火红（训练家卡上的神秘卡片 id 在 `0x60`），有两处差异：

- 没有全国图鉴时，绿宝石会拒绝伙伴送来的蛋或非丰缘地区的宝可梦 [trade.c:1584-1589]：交换界面显示「对方 TRAINER 的 POKéMON 现在不能交换」，主机在按下 A 之后发送 `READY_CANCEL_TRADE`。`LinkPlayer.progressFlags & 0xF` 报告图鉴状态。`pokeldn.rse.constants.HOENN_DEX` 保存着这 202 个条目，主持端会记录被拒的报价。
- 绿宝石在交换后跑五轮待机 [trade.c:4686-4797]；Switch 版火红跑六轮，最后一轮之后跟 `svc_FinishSave`。Switch 版构建保持五轮：主机发出 5 到 9 的 `READY_EXIT_STANDBY`，然后在「通信等待」上等一个期待第六轮的主机。`--version emerald` 让主持端跑五轮；`--save-rounds N` 可以覆盖。

版本为 3 时，绿宝石在 `0x3A` 画出带开拓区符号的主持端训练家卡，对战点数在 `0x3C`。它的接收队列有 32 个槽位（火红是 20），除 `0x0002` 和 `0x7F7D` 之外也接受串行值 `0x0000`。

在模拟主机上，Switch 版构建能与主持端完成一次直连角交换：LinkPlayer、训练家卡、座位路由、队伍、邮件与缎带块、互换、五轮待机、`READY_CLOSE_LINK`、RFU 断开帧和 Pia 离开，最后把存档写进模拟器的存储。

## 联盟室

房间、活动菜单和交换板的行为与火红相同（见[联盟室](frlg_link.md#the-union-room)）。`--union-room --union-room-keepalive 120` 会生成 POKELDN 的头像，主机里的玩家与它对话后建立连接。与 POKELDN 对话会显示 GREETINGS、BATTLE、CHAT 和 EXIT；绿宝石在这个菜单里不提供交换。

| 活动 | 参数 | 在模拟主机上的实测 |
|---|---|---|
| GREETINGS | `--union-room` | 双方训练家卡、待机屏障、返回房间 |
| EXIT | `--union-room` | `READY_CLOSE_LINK` 与正常断开 |
| 交换板 | `--union-room --board-type TYPE` | 主机选中 POKELDN 的挂单，宝可梦与邮件块交叉，交换与存档完成，链路关闭 |
| CHAT | `--union-room-chat` | 未测 |
| BATTLE | `--union-room-battle` | 未测 |

主持端只为从 POKELDN 的挂单发起的交换板交易提供服务；它不会反过来向主机自己的挂单发起请求。`--board-type` 指定主持端回礼时所要求的属性，主机只会拿出该属性的宝可梦。

用 `--union-room-keepalive 600` 时，双方训练家卡块交换完成后主机停在「正在与 POKELDN 通信…」上，始终不显示菜单；120 就能正常进入。

## 尚未解决

- Switch 版绿宝石在交换后的待机轮数。
- 与绿宝石的联盟室聊天与对战。
