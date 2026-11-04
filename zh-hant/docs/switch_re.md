---
title: 逆向分析一款 Switch 遊戲
nav_order: 3
---

# 逆向分析一款 Switch 遊戲

本頁講的是就地讀取一款零售 Switch 遊戲的程式碼，適用於 Unity/IL2CPP（晶燦鑽石與明亮珍珠）和原生 C++（劍與盾）遊戲。

## 工作順序

1. 先在已公開的來源中查詢某個常量，包括 NintendoClients wiki 的逐遊戲頁面：

       gh search code "<a constant, a field name, a class name>" --limit 20
       gh api repos/kinnay/NintendoClientsWiki/contents/<Page>.md --jq .content | base64 -d

2. 查詢已有的反編譯專案（BDSP 的 `TeamLumi/opendpr`）以及共用遊戲金鑰的客戶端。
3. 在同一個構建的執行檔和後設資料中為所有東西命名。
4. 在二進位制中驗證。
5. 最後才搜尋金鑰空間：一個錯誤的輸入就會給出看似確定的否定結果。

## 取出執行檔

### 從 NSP

NSP 是由 NCA 組成的 PFS0。title key 位於 `<rights id>.tik` 中：加密金鑰在 `+0x180`，rights id 在 `+0x2A0`；其最後一個位元組 *n* 選擇 `titlekek_{n-1}`。稀疏檔案（用 `dd` 把所需區間寫入一個經 `truncate` 建立的檔案）能通過 hactool 的邊界檢查。

### 從 XCI

`tools/switch/xci_read.py` 遍歷 HFS0/PFS0，解密 NCA 頭並列印每一節的偏移、計數器和金鑰；卡帶 NCA 的正文金鑰是 `key_area_key_application_<max(crypto_type, crypto_type2) - 1>` 下的 key area 槽位 2。

    ./.venv/bin/python tools/switch/xci_read.py <the.xci> --keys prod.keys --type Program
    ./.venv/bin/python tools/switch/xci_read.py <the.xci> --nca <id> --exefs 0 --extract main

陷阱：`fs_type` 在 +0x2，雜湊型別在 +0x3（hactool 把兩者的名稱弄反了）；節計數器是反向使用的。

### 從 RomFS

各節使用 AES-128-CTR（計數器：節的 CTR 與大端序的 `offset >> 4`），因此任意區間都可單獨解密。`tools/switch/romfs_read.py` 負責遍歷和提取，遇到 size 欄位不是 `0x50` 的頭會拒絕。陷阱：hactool 遇到含 34 位十六進位制數字的 `prod.keys` 行會中止，對稀疏檔案執行 `--listromfs` 會段錯誤。

## 先命名一切

- IL2CPP：`global-metadata.dat` 加上同一構建的執行檔，可讓 Il2CppDumper 得到每個 C# 方法。
- C++ RTTI：`tools/switch/rtti_names.py` 從重定位中為 `nn::pia` 類命名（BDSP 中 279 個，劍與盾中 252 個）。`LocalProtocol` 與 `LanProtocol` 之分把 LDN 與 LAN 的金鑰派生區分開來。

## 只存在於後設資料中的常量

`[Serializable]` C# 類的 `byte[]` 預設值只存在於 `global-metadata.dat` 中，形式為 `Field$<PrivateImplementationDetails>.<SHA-1>`，通過建構函式中的 `InitializeArray` 訪問。BDSP 的遊戲金鑰種子就是這樣儲存的。

## 確認匯出的是哪個版本

BDSP 的基礎版定義了 24 條網路訊息，1.3.0 定義了 65 條：

| 結構 | 基礎版 | 1.3.0（[協議頁面](bdsp_protocol.md#framing)） |
|---|---|---|
| `PosData` | `Vector3 pos, short rotY`，16 位元組 | `ushort posX, ushort posZ, short rotY`，6 位元組 |
| `JoinData` | 少兩個欄位，已對齊 | `byte, byte, byte, short, Vector3`，17 位元組未對齊 |

用基礎版匯出的佈局去解碼 1.3.0 的抓包，會得到看似合理卻毫無意義的結果。`strings global-metadata.dat | grep NetPlayerNameData` 只能在 1.3.0 中找到。常量能跨越更新存活；結構不能。

## 讀取遊戲更新的 RomFS

更新的 RomFS 是疊加在基礎版之上的 BKTR 節；`tools/switch/bktr_read.py` 會組合其重定位表和子節表：

    ./.venv/bin/python tools/switch/bktr_read.py UPDATE.nsp --base BASE.nsp \
        --extract /Data/Managed/Metadata/global-metadata.dat

陷阱：XCI 的更新分割槽中存放的是系統標題的 Program NCA；應根據更新所屬的 title 來選擇基礎版。

## 查詢呼叫方

掃描 `bl` 和尾呼叫 `b`：BDSP 的 `ANetData<SelectData>$$SendReliableData` 只有 `b` 呼叫方。沒有任何分支指向的方法，可能是通過 ADRP/ADD 註冊的委託（`arm64_xref.py`）。

陷阱：`arm64_xref.function_start` 可能越過 `udf` 填充進入前一個函式；用「入口之後 N 位元組」來界定函式可能越過其 `ret`；`mov w0, #0x80` 是一條 ORR 立即數指令，位元組掃描看不到它。

## 呼叫 nnSdk

對 nnSdk 的呼叫會經過一個由 JUMP_SLOT 重定位命名的 GOT 槽位（`tools/switch/nso_imports.py`）。

## 訓練家名字

每款 Switch 遊戲的訓練家記錄都在玩家名字旁帶一個語言 id（PKHeX 的 LanguageID：1 日語、2 英語、3 法語、4 義大利語、5 德語、7 西班牙語、8 韓語、9 和 10 中文），遊戲會用該語言對應的字型繪製名字。一臺零售日版朱在記錄標註為英語（2）的情況下，把假名名字 キリコ 用窄的半形字形繪製出來，而同一名字從日文存檔讀取時呈全形。`pokeldn.trainer_language.for_name` 會選出寫入的名字所需的 id：假名用日語，諺文用韓語，漢字用日語（除非記錄已經是中文）；拉丁字母名字保留記錄的 id。每款遊戲的身份寫入器都會應用它：

| 遊戲 | 語言所在位置 |
|---|---|
| 朱與紫 | 記錄 1 的 `+0x11` |
| 傳說 Z-A | 1400 身份值的第三個整數，名字前一個位元組 |
| 劍與盾 | MyStatus `+0xA7`、TrainerCard `+0x1B`、檔案的語言位 |
| 晶燦鑽石與明亮珍珠 | PlayerInfo 和 `TradeTranerData` 的語言位元組 |
| Let's Go | 首條訊息的 MyStatus `+0x35` |
| 傳說 阿爾宙斯 | 資料交換記錄的 `+0x22` |

## 工具

全部離線，基於 `pokeldn.switch`：

    tools/switch/nso_read.py     把 NSO 的各段按其記憶體偏移解壓
    tools/switch/nso_relocs.py   RELA 與 RELR 重定位（現代遊戲使用 RELR）
    tools/switch/arm64_xref.py   ADRP 交叉引用、BL 呼叫圖、函式起始
    tools/switch/arm64_dis.py    capstone 反彙編
