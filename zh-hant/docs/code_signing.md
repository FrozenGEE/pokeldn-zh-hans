---
title: 程式碼簽名政策
nav_order: 12
---

# 程式碼簽名政策

免費程式碼簽名由 [SignPath.io](https://about.signpath.io) 提供，證書由 [SignPath Foundation](https://signpath.org) 提供

桌面應用的 Windows 發行版，即 [Releases](https://github.com/Decryptu/pokeldn/releases) 頁面上的 `pokeldn-windows-x64.zip`，會對其由本倉庫原始碼構建的二進位制檔案附帶 Authenticode 簽名：`pokeldn.exe`、PKHeX 輔助程式 `pokeldn-pkhex.exe` 以及 Unicorn 庫 `unicorn.dll`。GitHub Actions 從本倉庫的 `v*` 標籤構建它們（[release.yml](https://github.com/Decryptu/pokeldn/blob/main/.github/workflows/release.yml)）；SignPath 只為該構建產出的檔案簽名，不為在其他任何地方構建的檔案簽名。構件配置見 [.github/signpath/artifact-configuration.xml](https://github.com/Decryptu/pokeldn/blob/main/.github/signpath/artifact-configuration.xml)。原樣打包的第三方檔案保留其各自發布者的簽名，或者本就沒有簽名。

## 團隊角色

| 角色 | 成員 |
|---|---|
| 提交者與稽核者 | [Decryptu](https://github.com/Decryptu) |
| 批准者 | [Decryptu](https://github.com/Decryptu) |

每次針對某個發行版的簽名請求都由人工批准。其他人的貢獻只能以拉取請求的形式進入倉庫，並由提交者稽核。

## 隱私政策

除使用者或安裝、操作本程式的人明確要求外，本程式不會向其他聯網系統傳輸任何資訊。它會發出以下請求：

| 時機 | 接收方 | 傳送內容 |
|---|---|---|
| 啟動時，且設定中的「更新」處於開啟狀態（預設開啟） | GitHub API，以及每個已安裝外掛的更新地址 | 查詢最新發行版的請求；不含任何關於玩家或其遊戲的資訊 |
| 玩家下載無線模組韌體或活動團體戰資料 | GitHub | 一個下載請求 |
| 玩家使用「交換（線上）」或 GTS | 公共 Nostr 中繼（[線上交換](online.md)） | 加密的交換事件，其中包括所提供的那隻寶可夢 |
| 玩家安裝或更新外掛，或瀏覽外掛源 | 該外掛或該源的地址 | 一個下載請求 |

發往 GitHub 的請求適用 GitHub 的隱私宣告。發往某個中繼的請求適用該中繼運營者自己的政策。本應用不傳送任何分析資料，也不傳送崩潰報告。
