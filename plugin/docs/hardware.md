---
title: 硬件与设置
nav_order: 9
has_children: true
---

# 硬件与设置

无线模块是一块通过 USB 串口运行 `firmware/esp32` 的 ESP32 板子；LDN、Pia 和游戏在主机上以 Python 运行，不需要 root 权限，也不需要 Wi-Fi 驱动。每个作品都通过它进行交换。Linux 主机也可以改为直接驱动一块支持 AP 模式的无线网卡；该方式属于旧版路径。

## 页面

- [ESP32 无线模块](hardware_esp32.md)：板子本身、其固件、串口协议与实测数据。
- [Switch 密钥](hardware_switch_keys.md)：安全地安装 `prod.keys`。
- [网卡](hardware_adapters.md)：Linux 无线网卡、其配置与故障模式。
- [控制器板](hardware_pad.md)：主机将其识别为有线控制器的 ESP32-S3，经蓝牙低功耗驱动；或者主机将其配对为 Pro 控制器的经典 ESP32，经 USB 串口驱动。
- [树莓派主机](hardware_raspberry_pi.md)：Linux 部署，以及受监管的神秘礼物运行器。
