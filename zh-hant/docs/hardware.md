---
title: 硬體與設定
nav_order: 9
has_children: true
---

# 硬體與設定

無線模組是一塊通過 USB 序列埠執行 `firmware/esp32` 的 ESP32 板子；LDN、Pia 和遊戲在主機上以 Python 執行，不需要 root 許可權，也不需要 Wi-Fi 驅動。每個作品都通過它進行交換。Linux 主機也可以改為直接驅動一塊支援 AP 模式的無線網絡卡；該方式屬於舊版路徑。

## 頁面

- [ESP32 無線模組](hardware_esp32.md)：板子本身、其韌體、序列埠協議與實測資料。
- [Switch 金鑰](hardware_switch_keys.md)：安全地安裝 `prod.keys`。
- [網絡卡](hardware_adapters.md)：Linux 無線網絡卡、其配置與故障模式。
- [控制器板](hardware_pad.md)：主機將其識別為有線控制器的 ESP32-S3，經藍牙低功耗驅動；或者主機將其配對為 Pro 控制器的經典 ESP32，經 USB 序列埠驅動。
- [樹莓派主機](hardware_raspberry_pi.md)：Linux 部署，以及受監管的神秘禮物執行器。
