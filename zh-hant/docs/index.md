---
title: 主頁
nav_order: 1
---

# pokeldn

pokeldn 是 Nintendo Switch 本地無線（LDN）的一種實現，它通過一塊 ESP32 板子作為無線模組，與零售 Switch 硬體上的寶可夢遊戲通訊：可以從電腦或安卓手機經 USB 序列埠連線，也可以從 iPhone 經藍牙連線。這些頁面記錄相關協議，並附有反編譯出處、反彙編地址和硬體實測資料。

請先閱讀[應用設定](gui.md)或[命令列用法](usage.md)。

## 目標遊戲

七個遊戲共用同一套 LDN 與 Pia 層：

| | FRLG | LGPE | SwSh | BDSP | PLA | SV | PLZA |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 交換 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 神秘禮物 | ✓ | ∅ | ✓ | ∅ | ∅ | ∅ | ∅ |
| 活動寶可夢 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 連線對戰 | ✓ | ✗ | ✗ | ✗ | ∅ | ✗ | ✗ |
| 在主機上執行程式碼、讀取與寫入存檔 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

✓ 在零售主機上可用 · ✗ 尚未實現 · ∅ 該遊戲在本地無線下沒有此功能
FRLG 火紅/葉綠 · LGPE Let's Go 皮卡丘/伊布 · SwSh 劍/盾 · BDSP 晶燦鑽石/明亮珍珠 · PLA 傳說 阿爾宙斯 · SV 朱/紫 · PLZA 傳說 Z-A

火紅與葉綠以 GBA ROM 的形式執行在 Switch 的模擬器中，因此該 ROM 的 GBA 連線協議架在 LDN 和 Pia 之上。其餘六個遊戲則把自己的程式碼直接放在 Pia 上：BDSP 是 Unity/IL2CPP，SwSh 與 LGPE 是藉助 `gflnet3` 傳輸 protocol buffers 的 C++，PLA、SV 和 PLZA 是靜態連結 Pia 的 C++。

## 章節

| 章節 | 內容 |
|---|---|
| [無線層](ldn.md) | LDN 與 Pia：廣播、關聯、各版本的資料包格式、會話金鑰推導。 |
| [逆向一款 Switch 遊戲](switch_re.md) | 閱讀零售遊戲自身的程式碼：原地提取 NCA/RomFS、IL2CPP 後設資料、C++ RTTI。 |
| [火紅與葉綠](frlg.md) | GBA 連線、神秘禮物、程式碼執行、RNG、卡帶。 |
| [晶燦鑽石與明亮珍珠](bdsp.md) | Pia 5.27-5.45、聯盟室，以及交換流程。 |
| [劍與盾](swsh.md) | Pia 4、同步框架、交換、極巨團體戰、極巨大冒險、神秘禮物。 |
| [Let's Go 皮卡丘與伊布](lgpe.md) | Pia 3、連線碼，以及交換流程。 |
| [傳說 阿爾宙斯](pla.md) | Pia 頭版本 11、交換流程、合成記錄。 |
| [朱與紫](sv.md) | Pia 頭版本 11、可靠流、交換、太晶團體戰、聯盟集友圈。 |
| [傳說 Z-A](za.md) | Pia 頭版本 16 與二十條交換訊息。 |
| [模擬的神秘禮物](gift_simulated.md) | 由主機向沒有本地神秘禮物的作品交換的官方禮物寶可夢。 |
| [命令列用法](usage.md) | 各遊戲的原始碼配置與命令。 |
| [桌面應用](gui.md) | 設定、寶可夢銀行、控制器、構建；安卓與 iOS。 |
| [程式碼組織](architecture.md) | 共享模組、寶可夢的準備與校驗。 |
| [硬體與設定](hardware.md) | ESP32 無線模組、Switch 金鑰，以及舊版 Linux 無線網絡卡。 |
| [程式碼簽名政策](code_signing.md) | Windows 發行版簽名的內容、團隊角色，以及隱私政策。 |

## 致謝

本專案基於 [kinnay 的 LDN 庫](https://github.com/kinnay/LDN) 和
[NintendoClients wiki](https://github.com/kinnay/NintendoClients/wiki) 構建，並對照
[pret/pokefirered](https://github.com/pret/pokefirered) 這一火紅/葉綠反編譯專案進行核對。
