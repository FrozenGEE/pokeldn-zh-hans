---
title: 代码签名政策
nav_order: 12
---

# 代码签名政策

免费代码签名由 [SignPath.io](https://about.signpath.io) 提供，证书由 [SignPath Foundation](https://signpath.org) 提供

桌面应用的 Windows 发行版，即 [Releases](https://github.com/Decryptu/pokeldn/releases) 页面上的 `pokeldn-windows-x64.zip`，会对其由本仓库源码构建的二进制文件附带 Authenticode 签名：`pokeldn.exe`、PKHeX 辅助程序 `pokeldn-pkhex.exe` 以及 Unicorn 库 `unicorn.dll`。GitHub Actions 从本仓库的 `v*` 标签构建它们（[release.yml](https://github.com/Decryptu/pokeldn/blob/main/.github/workflows/release.yml)）；SignPath 只为该构建产出的文件签名，不为在其他任何地方构建的文件签名。构件配置见 [.github/signpath/artifact-configuration.xml](https://github.com/Decryptu/pokeldn/blob/main/.github/signpath/artifact-configuration.xml)。原样打包的第三方文件保留其各自发布者的签名，或者本就没有签名。

## 团队角色

| 角色 | 成员 |
|---|---|
| 提交者与审核者 | [Decryptu](https://github.com/Decryptu) |
| 批准者 | [Decryptu](https://github.com/Decryptu) |

每次针对某个发行版的签名请求都由人工批准。其他人的贡献只能以拉取请求的形式进入仓库，并由提交者审核。

## 隐私政策

除用户或安装、操作本程序的人明确要求外，本程序不会向其他联网系统传输任何信息。它会发出以下请求：

| 时机 | 接收方 | 发送内容 |
|---|---|---|
| 启动时，且设置中的「更新」处于开启状态（默认开启） | GitHub API，以及每个已安装插件的更新地址 | 查询最新发行版的请求；不含任何关于玩家或其游戏的信息 |
| 玩家下载无线模块固件或活动团体战数据 | GitHub | 一个下载请求 |
| 玩家使用「交换（在线）」或 GTS | 公共 Nostr 中继（[在线交换](online.md)） | 加密的交换事件，其中包括所提供的那只宝可梦 |
| 玩家安装或更新插件，或浏览插件源 | 该插件或该源的地址 | 一个下载请求 |

发往 GitHub 的请求适用 GitHub 的隐私声明。发往某个中继的请求适用该中继运营者自己的政策。本应用不发送任何分析数据，也不发送崩溃报告。
