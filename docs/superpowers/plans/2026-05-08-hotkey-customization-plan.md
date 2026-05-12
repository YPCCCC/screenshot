# 自定义快捷键功能 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让用户点击快捷键标签后弹出对话框自定义截图快捷键，持久化到 config.json

**Architecture:** 所有改动在 `screenshot_tool.py` 单文件中完成。新增 `VK_TO_NAME` 映射表、`HotkeyDialog` 对话框类，改造 config 读写和热键轮询逻辑。

**Tech Stack:** Python 3, tkinter, ctypes (无新依赖)

---

### Task 1: 新增 VK_TO_NAME 映射表 & 删除 VK_OEM_4 常量

**Files:**
- Modify: `screenshot_tool.py:17`

- [ ] **Step 1: 替换模块顶层常量**

删除 `VK_OEM_4 = 0xDB`，新增 `VK_TO_NAME` 字典和默认热键常量。

```python
HOTKEY_DEFAULT_VK = 0xDB  # [

VK_TO_NAME = {
    8: 'Backspace', 9: 'Tab', 13: 'Enter',
    32: 'Space',
    **{i: chr(i) for i in range(48, 58)},   # 0-9
    **{i: chr(i) for i in range(65, 91)},   # A-Z
    **{i: f'NumPad {i - 96}' for i in range(96, 106)},  # NumPad 0-9
    106: 'NumPad *', 107: 'NumPad +', 109: 'NumPad -',
    110: 'NumPad .', 111: 'NumPad /',
    **{i: f'F{i - 111}' for i in range(112, 124)},  # F1-F12
    186: ';', 187: '=', 188: ',', 189: '-', 190: '.',
    191: '/', 192: '`',
    219: '[', 220: '\\', 221: ']', 222: "'",
}

MODIFIER_VKS = {16, 17, 18, 91, 92, 20}
```

### Task 2: 新增 HotkeyDialog 类

**Files:**
- Modify: `screenshot_tool.py`（在 ScreenshotApp 类之前插入）

- [ ] **Step 1: 添加 HotkeyDialog 类**

```python
class HotkeyDialog:
    def __init__(self, parent):
        self.result_vk = None
        self.result_name = None

        self.win = tk.Toplevel(parent)
        self.win.title("设置快捷键")
        self.win.resizable(False, False)
        self.win.configure(bg='#1e1e2e')
        self.win.transient(parent)
        self.win.grab_set()

        W, H = 300, 200
        px = parent.winfo_rootx() + (parent.winfo_width() - W) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - H) // 2
        self.win.geometry(f"{W}x{H}+{px}+{py}")

        tk.Label(
            self.win,
            text="请按下你想使用的快捷键...",
            bg='#1e1e2e', fg='#cdd6f4',
            font=('微软雅黑', 11),
        ).pack(pady=(16, 8))

        self.key_display = tk.Label(
            self.win,
            text="等待按键...",
            bg='#313244', fg='#89b4fa',
            font=('微软雅黑', 24, 'bold'),
            width=10, height=2,
        )
        self.key_display.pack(pady=(0, 8))

        tk.Label(
            self.win,
            text="提示：建议选择不常用的键，避免与其他操作冲突",
            bg='#1e1e2e', fg='#a6adc8',
            font=('微软雅黑', 8),
        ).pack()

        btn_frame = tk.Frame(self.win, bg='#1e1e2e')
        btn_frame.pack(pady=(12, 12))

        self.confirm_btn = tk.Button(
            btn_frame, text="✅ 确认",
            command=self._confirm,
            bg='#a6e3a1', fg='#1e1e2e',
            font=('微软雅黑', 10),
            relief='flat', cursor='hand2',
            padx=20, pady=6, bd=0,
            state='disabled',
        )
        self.confirm_btn.pack(side='left', padx=(0, 8))

        tk.Button(
            btn_frame, text="取消",
            command=self._cancel,
            bg='#f38ba8', fg='#1e1e2e',
            font=('微软雅黑', 10),
            relief='flat', cursor='hand2',
            padx=20, pady=6, bd=0,
        ).pack(side='right')

        self.win.bind('<KeyPress>', self._on_key)
        self.win.bind('<Escape>', lambda e: self._cancel())
        self.win.protocol('WM_DELETE_WINDOW', self._cancel)
        self.win.focus_force()

    def _on_key(self, event):
        vk = event.keycode
        if vk in MODIFIER_VKS:
            return
        self.result_vk = vk
        self.result_name = VK_TO_NAME.get(vk, event.keysym)
        self.key_display.config(text=self.result_name)
        self.confirm_btn.config(state='normal')

    def _confirm(self):
        self.win.destroy()

    def _cancel(self):
        self.result_vk = None
        self.result_name = None
        self.win.destroy()

    def show(self):
        self.win.wait_window()
        return self.result_vk, self.result_name
```

### Task 3: 改造 _load_config 和 _save_config

**Files:**
- Modify: `screenshot_tool.py:_load_config()`
- Modify: `screenshot_tool.py:_save_config()`

- [ ] **Step 1: 修改 _load_config 返回 tuple**

```python
def _load_config(self):
    try:
        if os.path.exists(self._config_file):
            with open(self._config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('save_path'), data.get('hotkey_vk', HOTKEY_DEFAULT_VK)
    except Exception:
        pass
    return None, HOTKEY_DEFAULT_VK
```

- [ ] **Step 2: 修改 _save_config 包含 hotkey 字段**

```python
def _save_config(self):
    try:
        with open(self._config_file, 'w', encoding='utf-8') as f:
            json.dump(
                {
                    'save_path': self.save_path,
                    'hotkey_vk': self._hotkey_vk,
                    'hotkey_name': self._hotkey_label.cget('text').split(': ')[1] if hasattr(self, '_hotkey_label') else '[',
                },
                f,
                ensure_ascii=False, indent=2,
            )
    except Exception:
        pass
```

### Task 4: 改造 __init__ 加载热键

**Files:**
- Modify: `screenshot_tool.py:__init__()`

- [ ] **Step 1: 修改 __init__ 中的配置加载逻辑**

将：
```python
saved = self._load_config()
if saved and os.path.isdir(saved):
    self.save_path = saved
```

改为：
```python
saved_path, self._hotkey_vk = self._load_config()
if saved_path and os.path.isdir(saved_path):
    self.save_path = saved_path
```

### Task 5: 改造 _build_float_win — 可点击快捷键标签

**Files:**
- Modify: `screenshot_tool.py:_build_float_win()` 快捷键标签部分

- [ ] **Step 1: 替换快捷键 Label 为可点击版本**

将原有的：
```python
tk.Label(
    win, text="快捷键: [",
    bg=BG, fg=SUBTEXT,
    font=('微软雅黑', 8),
).pack(pady=(4, 0))
```

改为：
```python
hotkey_name = VK_TO_NAME.get(self._hotkey_vk, '[')
self._hotkey_label = tk.Label(
    win,
    text=f"快捷键: {hotkey_name}",
    bg=BG, fg=BLUE,
    font=('微软雅黑', 8),
    cursor='hand2',
)
self._hotkey_label.pack(pady=(4, 0))
self._hotkey_label.bind('<Button-1>', lambda _e: self._change_hotkey())
```

### Task 6: 新增 _change_hotkey 方法 & 改造 _hotkey_loop

**Files:**
- Modify: `screenshot_tool.py`（新增方法 + 改造热键轮询）

- [ ] **Step 1: 新增 _change_hotkey 方法**

```python
def _change_hotkey(self):
    dlg = HotkeyDialog(self.float_win)
    vk, name = dlg.show()
    if vk is not None and name is not None:
        self._hotkey_vk = vk
        self._hotkey_label.config(text=f"快捷键: {name}")
        self._save_config()
        self._set_status(f"✅ 快捷键已更新: {name}", self.COLOR_GREEN)
```

- [ ] **Step 2: 改造 _hotkey_loop 使用实例变量**

将：
```python
is_pressed = ctypes.windll.user32.GetAsyncKeyState(VK_OEM_4) & 0x8000
```

改为：
```python
is_pressed = ctypes.windll.user32.GetAsyncKeyState(self._hotkey_vk) & 0x8000
```

### Task 7: 验证 & 测试

- [ ] **Step 1: 启动工具验证 UI 显示正确**

```bash
python screenshot_tool.py
```

- 检查：悬浮窗显示"快捷键: ["
- 点击快捷键标签 → 弹出对话框
- 按一个键 → 对话框显示键名，确认按钮变为可用
- 点取消 → 快捷键不变
- 重新打开对话框，按新键并确认 → 快捷键更新，状态栏显示提示
- 重启工具 → 快捷键保持修改后的值

- [ ] **Step 2: 确认热键截图功能正常**
- 按下自定义的快捷键 → 触发截图
