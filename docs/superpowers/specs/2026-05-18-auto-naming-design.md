# 自动补全命名 + 快捷参考 — 设计文档

**日期**: 2026-05-15
**项目**: 截图工具 (screenshot_tool.py)
**状态**: 已确认

---

## 1. 功能概述

命名对话框中输入首字母/缩写时自动补全为 BMC 页面区域别名（如 `s` → `SYS`）。对话框底部显示快捷参考行列出 14 类命名，用户一目了然。支持 `&` 连接多标题（如 `s&c` → `SYS&CPU`）。

---

## 2. 命名规则

```python
NAMING_RULES = [
    # (alias, 中文名, 英文名, 触发词列表)
    ("Overview", "概述", "Overview",   ["概", "ov"]),
    ("SYS",      "系统", "System",     ["s", "sy", "系"]),
    ("BMC",      "BMC管理", "BMC manager", ["b", "bm", "bmc"]),
    ("BIOS",     "BIOS管理", "BIOS manager", ["bi", "bio", "bios"]),
    ("CHASSIS",  "机箱", "Chassis",    ["c", "ch", "机"]),
    ("DIMM",     "DIMM插槽", "DIMM slot", ["d", "di", "dimm"]),
    ("PSU",      "电源", "Power supplies", ["p", "ps", "psu", "电"]),
    ("CPU",      "处理器", "Processors", ["cp", "cpu", "处"]),
    ("PCIE",     "PCIe", "PCIe",       ["pc", "pci", "pcie"]),
    ("NIC",      "网卡", "Network adapter", ["n", "ni", "nic", "网"]),
    ("BP",       "背板", "Back plane",  ["bp", "背"]),
    ("NVME",     "NVMe硬盘", "NVMe disk", ["nv", "nvm", "nvme"]),
    ("HDD",      "HDD硬盘", "HDD",      ["h", "hd", "hdd"]),
    ("FW",       "固件", "Firmware",    ["f", "fw", "固"]),
]
```

---

## 3. auto_complete 逻辑

- 用户每按键触发 `<KeyRelease>` 事件
- 按 `&` 分割输入文本，逐段匹配
- 匹配优先：触发词精确匹配 > alias 前缀匹配 > 不匹配（保留原样）
- 结果用 `&` 重新拼接，更新输入框内容

---

## 4. UI 变更

### 4.1 命名对话框改造

原对话框高度 140 → ~210，新增两个区域：

**快捷参考行**：两行小字灰字显示 14 个类名：
```
1.Overview  2.SYS  3.BMC  4.BIOS  5.CHASSIS  6.DIMM  7.PSU
8.CPU  9.PCIE  10.NIC  11.BP  12.NVME  13.HDD  14.FW
```

**提示行**：`💡 输入缩写自动补全，多标题用 & 连接，如: SYS&CPU`

### 4.2 悬浮窗新增开关

`☐ 显示命名快捷参考` — Checkbutton，持久化到 config.json（`show_quick_ref: true/false`）

关闭时不显示快捷参考行和提示行。

### 4.3 config.json

```json
{
  "save_path": "...",
  "hotkey_vk": 219,
  "hotkey_name": "[",
  "auto_scroll": true,
  "show_quick_ref": true
}
```

---

## 5. 边缘情况

| 场景 | 处理 |
|---|---|
| 输入不匹配任何规则 | 保留原样 |
| `&` 分割的多标题 | 逐段独立匹配 |
| 中文输入法组合输入中 | `<KeyRelease>` 可能不在合适的时机，需处理输入法状态 |
| 快捷参考关闭 | 仅隐藏参考行和提示行，输入框不变 |
| 用户手动编辑补全结果 | 不强制纠正，后续按键继续触发补全 |
