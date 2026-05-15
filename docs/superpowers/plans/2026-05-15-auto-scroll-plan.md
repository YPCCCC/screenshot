# 截图后自动翻页 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 截图保存后自动向目标窗口发送 Page Down，跳过已截内容

**Architecture:** 单文件变更 (`screenshot_tool.py`)。新增 Checkbutton 控制开关，截图前记住前台窗口句柄，截图后比对并发送 Page Down

**Tech Stack:** Python tkinter + ctypes (user32.dll)，零新依赖

---

### Task 1: 修改 `_load_config()` 和 `_save_config()` 支持 auto_scroll

**Files:**
- Modify: `screenshot_tool.py:176-200`

- [ ] **Step 1: 修改 `_load_config()` 返回 auto_scroll**

```python
def _load_config(self):
    try:
        if os.path.exists(self._config_file):
            with open(self._config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return (
                data.get('save_path'),
                data.get('hotkey_vk', HOTKEY_DEFAULT_VK),
                data.get('auto_scroll', False),
            )
    except Exception:
        pass
    return None, HOTKEY_DEFAULT_VK, False
```

- [ ] **Step 2: 修改 `_save_config()` 写入 auto_scroll**

```python
def _save_config(self):
    try:
        hotkey_name = self._hotkey_label.cget('text').split(': ', 1)[1] if hasattr(self, '_hotkey_label') else '['
        with open(self._config_file, 'w', encoding='utf-8') as f:
            json.dump(
                {
                    'save_path': self.save_path,
                    'hotkey_vk': self._hotkey_vk,
                    'hotkey_name': hotkey_name,
                    'auto_scroll': self._auto_scroll_var.get(),
                },
                f,
                ensure_ascii=False, indent=2,
            )
    except Exception:
        pass
```

### Task 2: 修改 `__init__()` 解包新的返回值

**Files:**
- Modify: `screenshot_tool.py:136-163`

- [ ] **Step 1: 解包 auto_scroll 并初始化 BooleanVar**

```python
def __init__(self):
    self.save_path = None
    self._drag_x = 0
    self._drag_y = 0
    self._running = True
    self._capturing = False

    self._config_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'config.json'
    )

    self.root = tk.Tk()
    self.root.withdraw()

    saved_path, self._hotkey_vk, auto_scroll = self._load_config()
    self._auto_scroll_var = tk.BooleanVar(value=auto_scroll)

    if saved_path and os.path.isdir(saved_path):
        self.save_path = saved_path
    else:
        self._prompt_save_path()

    if not self.save_path:
        self.root.destroy()
        return

    self._build_float_win()
    self.root.mainloop()
```

### Task 3: 修改 `_build_float_win()` 新增 Checkbutton

**Files:**
- Modify: `screenshot_tool.py:221-338`

- [ ] **Step 1: 窗口高度 270 → 295**

```python
W, H = 250, 295
```

- [ ] **Step 2: 在状态栏上方新增 Checkbutton（在 `self.status_label` 的 pack 之前插入）**

```python
self._scroll_cb = tk.Checkbutton(
    win,
    text="截图后自动翻页 (Page Down)",
    variable=self._auto_scroll_var,
    command=self._on_auto_scroll_toggle,
    bg=BG, fg=SUBTEXT,
    selectcolor=SURFACE,
    activebackground=BG,
    activeforeground=GREEN,
    font=('微软雅黑', 8),
    cursor='hand2',
)
self._scroll_cb.pack(fill='x', padx=12, pady=(2, 0))
```

### Task 4: 修改 `_capture()` 加入窗口句柄比对和 Page Down 发送

**Files:**
- Modify: `screenshot_tool.py:418-439`

- [ ] **Step 1: 重写 `_capture()`**

```python
def _capture(self):
    if self._capturing:
        return
    self._capturing = True
    try:
        target_hwnd = ctypes.windll.user32.GetForegroundWindow()

        self.float_win.withdraw()
        self.root.update()
        time.sleep(0.45)

        self._screenshot = ImageGrab.grab()

        if self._auto_scroll_var.get():
            current_hwnd = ctypes.windll.user32.GetForegroundWindow()
            if current_hwnd == target_hwnd:
                self._send_page_down()
            else:
                self._set_status("⚠️  窗口已切换，跳过翻页", self.COLOR_SUBTEXT)

        self.float_win.deiconify()
        self.float_win.attributes('-topmost', True)
        self.float_win.lift()
        self._force_foreground(self.float_win)

        self.float_win.after(80, self._prompt_filename)
    except Exception:
        self._capturing = False
        self.float_win.deiconify()
        self.float_win.attributes('-topmost', True)
```

- [ ] **Step 2: 新增 `_send_page_down()` 方法**

在 `_capture` 方法之后，`_prompt_filename` 方法之前插入：

```python
def _send_page_down(self):
    VK_NEXT = 0x22
    ctypes.windll.user32.keybd_event(VK_NEXT, 0, 0, 0)
    ctypes.windll.user32.keybd_event(VK_NEXT, 0, 2, 0)
    time.sleep(0.1)
```

- [ ] **Step 3: 新增 `_on_auto_scroll_toggle()` 方法**

在 `_save_config` 方法之后，合适位置插入：

```python
def _on_auto_scroll_toggle(self):
    self._save_config()
```

### Task 5: 验证

- [ ] **Step 1: 手动运行验证**

```bash
python screenshot_tool.py
```

验证项:
1. 悬浮窗高度变为 295，底部出现 Checkbutton
2. 默认不勾选，截图行为与原流程一致
3. 勾选后，截一个可滚动的页面，截图后自动翻页
4. 勾选后，截图时快速 Alt+Tab 切窗，状态栏显示"跳过翻页"
5. 重启后勾选状态保持
6. 不勾选时行为与原流程完全一致
