# 自定义快捷键功能 — 设计文档

**日期**: 2026-05-08
**项目**: 截图工具 (screenshot_tool.py)
**状态**: 已确认

---

## 1. 功能概述

允许用户在 GUI 上点击当前显示的快捷键标签（如 `快捷键: [`），弹出一个对话框，用户按下想要的新键，点击确认后即可修改截图快捷键。快捷键设置持久化到 `config.json`，重启后依然生效。

## 2. 确认的需求决策

| 决策项 | 选择 |
|---|---|
| 快捷键持久化 | 保存到 config.json，重启生效 |
| 交互方式 | 点击标签 → 弹出 Toplevel 对话框 → 按键 → 确认 |
| 快捷键范围 | 仅支持单个键（字母、数字、符号、F1-F12），不支持组合键 |
| 冲突提示 | 不做限制，对话框中显示提示文字"建议选择不常用的键" |
| 技术方案 | 方案 A：Toplevel + `<Key>` 绑定 |

## 3. 架构变更

### 3.1 config.json 格式变更

```json
{
  "save_path": "C:/Users/xxx/screenshots",
  "hotkey_vk": 219,
  "hotkey_name": "["
}
```

- 旧 config.json 无 hotkey 字段时，默认使用 `VK_OEM_4` (219 = `[`)
- 向后完全兼容

### 3.2 新增模块

| 模块 | 说明 |
|---|---|
| `VK_TO_NAME` 字典 | 虚拟键码 → 可读名称的映射表 |
| `HotkeyDialog` 类 | 自定义 Toplevel 对话框，捕获按键并返回键码 |
| `self._hotkey_vk` 属性 | 实例变量，存储当前快捷键的虚拟键码 |
| `self._hotkey_label` 控件 | 改造后的可点击快捷键提示 Label |

### 3.3 改动模块

| 模块 | 改动 |
|---|---|
| 模块顶层常量 | 删 `VK_OEM_4`，增 `VK_TO_NAME` 字典 |
| `__init__` | 增 `self._hotkey_vk` 初始化逻辑 |
| `_load_config()` | 返回值改为 tuple `(save_path, hotkey_vk)` |
| `_save_config()` | 增加 `hotkey_vk` 和 `hotkey_name` 写入 |
| `_build_float_win()` | "快捷键: [" → 可点击 Label，绑定点击事件 |
| `_hotkey_loop()` | `VK_OEM_4` 硬编码 → `self._hotkey_vk` |

## 4. HotkeyDialog 设计

### 4.1 结构

- 继承 `tk.Toplevel`
- 属性：`parent`（父窗口）、`result_vk`（返回的键码）、`result_name`（返回的键名）
- UI 布局：
  - 提示文字："请按下你想使用的快捷键..."
  - 大号显示区域（显示捕获到的键名，如 "F5"）
  - 辅助提示："提示：建议选择不常用的键，避免与其他操作冲突"
  - 确认按钮（仅在用户按过键后启用）
  - 取消按钮

### 4.2 按键捕获策略

1. 绑定 `<KeyPress>` 到 Toplevel 窗口级
2. 从 `event.keycode` 获取虚拟键码
3. 过滤单独修饰键：`VK_SHIFT`(16)、`VK_CONTROL`(17)、`VK_MENU`(18)、`VK_LWIN`(91)、`VK_RWIN`(92)、`VK_CAPITAL`(20)
4. 查 `VK_TO_NAME` 获取可读名称；若无匹配，使用 `event.keysym` 降级
5. 更新显示区域并启用确认按钮

### 4.3 返回值

- 点确认：返回 `(vk_code, key_name)`
- 点取消/关闭：返回 `(None, None)`

## 5. VK_TO_NAME 映射表

覆盖常用键的虚拟键码到名称的映射：

- 字母: A-Z (65-90)
- 数字: 0-9 (48-57)
- 数字键盘: NumPad 0-9 (96-105), NumPad 运算符 (106-111)
- 功能键: F1-F12 (112-123)
- 符号: `;=,-./` 等 (186-192), `[\]'` (219-222)
- 特殊: Space(32), Backspace(8), Tab(9), Enter(13)
- 其他键名使用 `event.keysym` 降级获取

## 6. 数据流

```
启动 → _load_config() → 读取 hotkey_vk (默认 219)
  ↓
显示 → VK_TO_NAME[hotkey_vk] → 显示快捷键名
  ↓
点击标签 → HotkeyDialog(parent=self.float_win)
  ↓
用户按键 → 捕获 VK → 过滤修饰键 → 显示键名
  ↓
用户确认 → 更新 self._hotkey_vk → _save_config() → 更新 Label
  ↓
热键轮询 → _hotkey_loop() 读取 self._hotkey_vk 实时生效
```

## 7. 边缘情况

| 场景 | 处理 |
|---|---|
| 旧 config.json 无 hotkey 字段 | 默认 VK_OEM_4 (219)，向后兼容 |
| config.json 读取失败 | 使用默认值，静默降级 |
| 用户按下修饰键(Ctrl/Alt/Shift) | 对话框中忽略，不更新显示 |
| 用户未按键直接想确认 | 确认按钮初始禁用，按键后才启用 |
| 用户点击取消/关闭对话框 | 快捷键不变，不写 config.json |
| 热键轮询线程读取 VK 变更 | 读取 int 是原子操作，无需加锁 |

## 8. 预估改动量

约 80-100 行代码变更，零新依赖（仅使用 tkinter + ctypes，均已有）。
