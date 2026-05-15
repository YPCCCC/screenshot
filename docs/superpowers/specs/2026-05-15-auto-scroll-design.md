# 截图后自动翻页 — 设计文档

**日期**: 2026-05-15
**项目**: 截图工具 (screenshot_tool.py)
**状态**: 已确认

---

## 1. 功能概述

悬浮窗新增复选框"截图后自动翻页 (Page Down)"。勾选后，截图完成时会自动向目标窗口发送 Page Down 按键，跳过当前已截屏的内容，方便连续截取长文档/网页。

---

## 2. 确认的需求决策

| 决策项 | 选择 |
|---|---|
| 翻页方式 | 发送 Page Down 按键（VK_NEXT, 0x22），应用原生处理缩放 |
| 触发时机 | 截图抓取后、命名对话框弹出前 |
| 开关方式 | 悬浮窗新增 Checkbutton，持久化到 config.json |
| 持久化 | 是，重启保持上次勾选状态 |
| 窗口比对 | 方案 A：截图前后比对前台窗口句柄，切换则跳过翻页 |

---

## 3. UI 变更

悬浮窗底部，状态栏上方新增：

```
☐ 截图后自动翻页 (Page Down)
```

- tk.Checkbutton，绿色主题
- 勾选/取消时实时保存到 config.json
- 窗口高度 270 → 295

---

## 4. config.json 格式变更

```json
{
  "save_path": "...",
  "hotkey_vk": 219,
  "hotkey_name": "[",
  "auto_scroll": true
}
```

- `auto_scroll` 字段：布尔值，缺失时默认 `false`
- `_load_config()` 和 `_save_config()` 同时更新

---

## 5. 核心流程变更

### 5.1 原流程

```
隐藏悬浮窗 → sleep 0.45s → 截图 → 显示悬浮窗 → 弹命名对话框 → 保存
```

### 5.2 新流程（auto_scroll = True）

```
记住前台窗口句柄 → 隐藏悬浮窗 → sleep 0.45s → 截图
  → 比对前台窗口句柄
     ├─ 相同 → 发送 Page Down → sleep 0.1s → 显示悬浮窗 → 弹命名对话框 → 保存
     └─ 不同 → 显示悬浮窗 → 弹命名对话框 → 保存（状态栏提示"窗口已切换，跳过翻页"）
```

### 5.3 新流程（auto_scroll = False）

与原流程完全一致，零影响。

---

## 6. Page Down 发送

使用 ctypes 调用 `keybd_event`：

```python
VK_NEXT = 0x22
ctypes.windll.user32.keybd_event(VK_NEXT, 0, 0, 0)
ctypes.windll.user32.keybd_event(VK_NEXT, 0, 2, 0)  # KEYEVENTF_KEYUP
time.sleep(0.1)
```

---

## 7. 窗口句柄比对

```python
# 截图前（隐藏悬浮窗之前）
target_hwnd = ctypes.windll.user32.GetForegroundWindow()

# 截图后（发送 Page Down 之前）
current_hwnd = ctypes.windll.user32.GetForegroundWindow()

if current_hwnd == target_hwnd:
    _send_page_down()
else:
    self._set_status("⚠️  窗口已切换，跳过翻页", self.COLOR_SUBTEXT)
```

---

## 8. 新增属性与方法

| 新增 | 类型 | 说明 |
|---|---|---|
| `self.auto_scroll_enabled` | `tk.BooleanVar` | Checkbutton 绑定的变量 |
| `_send_page_down()` | 方法 | 发送 Page Down 按键 |
| `_on_auto_scroll_toggle()` | 方法 | Checkbutton 切换回调，保存配置 |

---

## 9. 改动模块

| 模块 | 改动 |
|---|---|
| `_load_config()` | 返回值增加 `auto_scroll` 字段 |
| `_save_config()` | 写入 `auto_scroll` 字段 |
| `_build_float_win()` | 高度 270→295，新增 Checkbutton |
| `_capture()` | 截图前记窗口句柄，截图后根据开关翻页 |

---

## 10. 边缘情况

| 场景 | 处理 |
|---|---|
| auto_scroll 关闭 | 完全走原流程 |
| 0.45s 内前台窗口切换 | 比对失败，跳过翻页，状态栏提示 |
| config.json 无 auto_scroll 字段 | 默认 false |
| 文档已到底，Page Down 无效 | 无影响，静默 |
| Page Down 发送失败 | ctypes 不抛异常，静默 |
| Checkbutton 初始勾选 | 启动时从 config 加载 |
| 手动取消/关闭命名对话框 | 不影响，Page Down 在命名前已发送 |

---

## 11. 预估改动量

约 30-40 行代码变更，零新依赖。
