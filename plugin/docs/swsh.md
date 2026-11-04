---
title: 剑与盾
nav_order: 6
has_children: true
---

# 剑与盾

《宝可梦 剑／盾》在直接运行于 Pia 之上的发布/订阅框架中交换协议缓冲区消息。

静态分析对象是盾 1.3.2 欧版镜像（`01008db008c2c000`，更新 NCA，SDK 7.7.0.0）；实测针对一台法版剑 1.3.2。两者共用网络代码。

| 页面 | 内容 |
|---|---|
| [卡带与会话](swsh_session.md) | 密钥、镜像、Pia 4、到首条应用数据的关联 |
| [同步框架](swsh_protocol.md) | 消息 id、内容、持有者、路由、队伍载荷 |
| [交换](swsh_trade.md) | 交换界面、盒状态机、确认阶梯 |
| [神秘礼物](swsh_gift.md) | 神秘礼物菜单的本地无线分支 |
| [极巨团体战](swsh_raid.md) | 巢穴大厅、其广播、托管一场由一台或多台游戏主机加入的团体战、访客所打的战斗、极巨大冒险、离开 |

## 出处

除非某一节指明了具体客户端，否则 id、偏移和地址都来自盾的 `main` 或空口抓包。`pokeldn/swsh/trade.py` 中的 `SYNC_ANSWERS` 是 `andyjusa/nxldn-lab` 对一次游戏主机之间抓包的解读（消息 97 和 60000 与 pokeldn 的逐字节一致）。`kwsch/PokePiaSWSH`、`lincoln-lm/swsh-lan-client`、`andyjusa/nxldn-lab` 和 `Slashcash/PSD` 都从 Pia 站点握手开始实现 LAN 模式；没有一个覆盖 LDN 或主机迁移。

## 场地脚本

`bin/script/amx/*.amx`（1.3.2 中有 953 个）是采用 64 位单元的 Pawn 3.x：magic 为 `0xF1E1`，版本 10，flags 为 `0x1C`（紧凑代码、sleep、无检查）。紧凑编码：每字节 7 位，高位组在前，符号位于第一字节的第 6 位。非分支的单参数操作码也按 `(param << 32) | op` 打包，按 3.x 顺序从 162 开始编号（`LOAD.pri` 162、`LOAD.S.pri` 164、`PUSH.C` 188、`PUSH.S` 190、`STACK` 191、`ADD.C` 197、`ZERO.S` 200、`EQ.C.pri` 201、`INC.S` 204、`HALT` 210、`PUSH.ADR` 212）；偏移 0 处的 `halt 0` 可据此确认。

一个 native 为十二字节：`u64 0` 加一个 `u32` 名称哈希，由 `amx_Register`（`0x0066d970`）解析：

    h = 0; for each byte c: h = (h * 0x83) ^ c        (32-bit)

绑定表是 `.data` 中的 `(name, function)` 对，每个模块一张（取值函数如 `0x014aea00`）：777 个名称，513 个哈希中用到了 512 个。物品：`ItemAdd`（`0x014acea0`）、`ItemSub`（`0x014acf40`）、`ItemGetNum`、`ItemAddCheck`、`ItemGetCategory`、`GetPocketNumberFromItemNumber_`。变量：`WorkGet`/`WorkSet`（哈希的 64 位键）、`TempWorkGet`/`TempWorkSet`（界面在脚本恢复前填入的索引）。一次调用是对每个参数自右向左 `PUSH`，然后 `SYSREQ.N native, bytes`。

## 未解决

- [玩家档案](swsh_protocol.md#the-player-profile)：在宝可梦露营会话中，样本状态 3 和 4 分别代表哪个角色（`StateCreateSession`、`StateConnect`）。把 `a_wr0301` 判为王冠雪原旷野地带，只是从编号推断出来的。
- [对战竞技场](swsh_protocol.md#the-battle-stadium-block)：`0x01430670` 读取哪个存档块来取得已保存的队伍记录；以及在 `v1/validate` 签名替换 `+0x36` 之前，存档队伍的描述符在 `+0x30..+0x135` 处保存什么（即 `0x015039f0` 之后 `[sp+0x28]` 处的条目）。
- 剑与盾对照：二进制分析对象是盾，游戏主机是剑；[会话常量](swsh_session.md#taking-a-seat)在两者之间通用。剑是否测试卡带版本掩码的第 0 位这一结论，是从盾的代码——其中该测试为 `1 << (v == 0x2D)`，且 `0x007d4270` 的 31 处调用点中有 11 处同时与 `0x2C` 和 `0x2D` 比较——以及从 PKHeX 的 `RestrictVersion`（1 剑，2 盾，3 两者）推断出来的；两份零售剑快照在 MyStatus `+0xA4` 处带有 `0x2C`。剑自身的 `0x007d4270` 及其通信 id 字面量尚未读取。
- [神秘礼物](swsh_gift.md#what-the-menu-refuses)：零售游戏主机是否会和模拟的盾一样，把物种不存在于游戏中的 kind-1 礼物当作名为 "Egg" 的坏蛋接受；以及这样的蛋在孵化时或交换中会怎样。
