import tkinter as tk
from tkinter import filedialog, messagebox
import time
import os
import sys
import json
import ctypes
import threading
import re

try:
    from PIL import ImageGrab
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import ImageGrab

HOTKEY_DEFAULT_VK = 0xDB  # [

VK_TO_NAME = {
    8: 'Backspace', 9: 'Tab', 13: 'Enter',
    32: 'Space',
    48: '0', 49: '1', 50: '2', 51: '3', 52: '4',
    53: '5', 54: '6', 55: '7', 56: '8', 57: '9',
    65: 'A', 66: 'B', 67: 'C', 68: 'D', 69: 'E', 70: 'F',
    71: 'G', 72: 'H', 73: 'I', 74: 'J', 75: 'K', 76: 'L',
    77: 'M', 78: 'N', 79: 'O', 80: 'P', 81: 'Q', 82: 'R',
    83: 'S', 84: 'T', 85: 'U', 86: 'V', 87: 'W', 88: 'X',
    89: 'Y', 90: 'Z',
    96: 'NumPad 0', 97: 'NumPad 1', 98: 'NumPad 2',
    99: 'NumPad 3', 100: 'NumPad 4', 101: 'NumPad 5',
    102: 'NumPad 6', 103: 'NumPad 7', 104: 'NumPad 8',
    105: 'NumPad 9',
    106: 'NumPad *', 107: 'NumPad +', 109: 'NumPad -',
    110: 'NumPad .', 111: 'NumPad /',
    112: 'F1', 113: 'F2', 114: 'F3', 115: 'F4',
    116: 'F5', 117: 'F6', 118: 'F7', 119: 'F8',
    120: 'F9', 121: 'F10', 122: 'F11', 123: 'F12',
    186: ';', 187: '=', 188: ',', 189: '-', 190: '.',
    191: '/', 192: '`',
    219: '[', 220: '\\', 221: ']', 222: "'",
}

MODIFIER_VKS = {16, 17, 18, 91, 92, 20}

NAMING_RULES = [
    ("Overview", "概述",       ["概", "ov"]),
    ("SYS",      "系统",       ["s", "sy", "系"]),
    ("BMC",      "BMC管理",    ["bm", "bmc"]),
    ("BIOS",     "BIOS管理",   ["bi", "bio", "bios"]),
    ("CHASSIS",  "机箱",       ["ch", "机"]),
    ("DIMM",     "DIMM插槽",   ["di", "dimm"]),
    ("PSU",      "电源",       ["ps", "psu", "电"]),
    ("CPU",      "处理器",     ["cp", "cpu", "处"]),
    ("PCIE",     "PCIe",       ["pc", "pci", "pcie"]),
    ("NIC",      "网卡",       ["ni", "nic", "网"]),
    ("BP",       "背板",       ["bp", "背"]),
    ("NVME",     "NVMe硬盘",   ["nv", "nvm", "nvme"]),
    ("HDD",      "HDD硬盘",    ["h", "hd", "hdd"]),
    ("FW",       "固件",       ["f", "fw", "固"]),
]


def _auto_complete(text):
    parts = text.split('&')
    result = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        matched = None
        for alias, _, triggers in NAMING_RULES:
            if part.lower() in triggers or part.lower() == alias.lower():
                matched = alias
                break
        if not matched:
            for alias, _, triggers in NAMING_RULES:
                if alias.lower().startswith(part.lower()):
                    matched = alias
                    break
        result.append(matched if matched else part)
    return '&'.join(result)


def _is_full_alias(text):
    t = text.strip()
    if not t:
        return False
    for alias, _, triggers in NAMING_RULES:
        if t.lower() == alias.lower() or t.lower() in triggers:
            return True
    return False


def _count_prefix_matches(text):
    t = text.strip().lower()
    if not t:
        return 0, []
    matches = set()
    for alias, _, triggers in NAMING_RULES:
        if alias.lower().startswith(t):
            matches.add(alias)
        for trig in triggers:
            if trig.startswith(t):
                matches.add(alias)
                break
    return len(matches), list(matches)


def _smart_complete(prev_text, new_text):
    if not new_text:
        return new_text

    parts = new_text.split('&')
    last_part = parts[-1].strip() if parts else ''

    if last_part:
        exact = False
        for alias, _, triggers in NAMING_RULES:
            if last_part.lower() in triggers or last_part.lower() == alias.lower():
                exact = True
                break

        if not exact:
            count, _ = _count_prefix_matches(last_part)
            if count > 1:
                return new_text

    if prev_text and new_text.startswith(prev_text) and len(new_text) > len(prev_text):
        appended = new_text[len(prev_text):]
        last_seg = prev_text.rsplit('&', 1)[-1].strip()

        if _is_full_alias(last_seg) and appended.strip():
            candidate = prev_text + '&' + appended.strip()
            new_seg = appended.strip()
            c, _ = _count_prefix_matches(new_seg)
            if c > 1:
                return candidate
            return _auto_complete(candidate)

    return _auto_complete(new_text)


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

        W, H = 340, 220
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
            btn_frame, text="确认",
            command=self._confirm,
            bg='#a6e3a1', fg='#1e1e2e',
            font=('微软雅黑', 12, 'bold'),
            relief='flat', cursor='hand2',
            padx=28, pady=10, bd=0,
            state='disabled',
        )
        self.confirm_btn.pack(side='left', padx=(0, 12))

        tk.Button(
            btn_frame, text="取消",
            command=self._cancel,
            bg='#f38ba8', fg='#1e1e2e',
            font=('微软雅黑', 12, 'bold'),
            relief='flat', cursor='hand2',
            padx=28, pady=10, bd=0,
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


class ScreenshotApp:
    def __init__(self):
        self.save_path = None
        self._drag_x = 0
        self._drag_y = 0
        self._running = True
        self._capturing = False

        self._config_file = os.path.join(
            os.path.dirname(sys.executable) if getattr(sys, 'frozen', False)
            else os.path.dirname(os.path.abspath(__file__)),
            'config.json',
        )

        self.root = tk.Tk()
        self.root.withdraw()

        saved_path, self._hotkey_vk, auto_scroll, show_quick_ref, show_tag_panel, auto_name = self._load_config()
        self._auto_scroll_var = tk.BooleanVar(value=auto_scroll)
        self._show_quick_ref_var = tk.BooleanVar(value=show_quick_ref)
        self._show_tag_panel_var = tk.BooleanVar(value=show_tag_panel)
        self._auto_name_var = tk.BooleanVar(value=auto_name)
        self._init_tag_labels()
        if saved_path and os.path.isdir(saved_path):
            self.save_path = saved_path
        else:
            self._prompt_save_path()

        if not self.save_path:
            self.root.destroy()
            return

        self._build_float_win()
        self.root.mainloop()

    # ── Path helpers ──────────────────────────────────────────────────────────

    def _prompt_save_path(self):
        path = filedialog.askdirectory(title="请选择截图保存位置")
        if path:
            self.save_path = path
        else:
            messagebox.showwarning("提示", "未选择保存位置，程序将退出。")

    def _short_path(self, path, max_len=30):
        return ("..." + path[-(max_len - 3):]) if len(path) > max_len else path

    def _load_config(self):
        try:
            if os.path.exists(self._config_file):
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return (
                    data.get('save_path'),
                    data.get('hotkey_vk', HOTKEY_DEFAULT_VK),
                    data.get('auto_scroll', False),
                    data.get('show_quick_ref', False),
                    data.get('show_tag_panel', False),
                    data.get('auto_name', False),
                )
        except Exception:
            pass
        return None, HOTKEY_DEFAULT_VK, False, False, False, False

    def _init_tag_labels(self):
        try:
            if os.path.exists(self._config_file):
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                cfg_labels = data.get('tag_labels')
                if cfg_labels:
                    self._tag_labels = list(cfg_labels)
                    return
        except Exception:
            pass
        self._tag_labels = [r[0] for r in NAMING_RULES]

    def _get_tag_labels(self):
        return list(self._tag_labels)

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
                        'show_quick_ref': self._show_quick_ref_var.get(),
                        'show_tag_panel': self._show_tag_panel_var.get(),
                        'auto_name': self._auto_name_var.get(),
                        'tag_labels': self._tag_labels,
                    },
                    f,
                    ensure_ascii=False, indent=2,
                )
        except Exception:
            pass

    def _change_path(self):
        new_path = filedialog.askdirectory(
            title="选择新的截图保存位置",
            mustexist=True,
            initialdir=self.save_path,
        )
        if new_path:
            self.save_path = new_path
            self.path_label.config(text=self._short_path(new_path))
            self._save_config()
            messagebox.showinfo(
                "路径已更新",
                f"新保存路径：\n{new_path}",
                parent=self.float_win,
            )

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_float_win(self):
        BG      = '#1e1e2e'
        SURFACE = '#313244'
        BLUE    = '#89b4fa'
        GREEN   = '#a6e3a1'
        RED     = '#f38ba8'
        TEXT    = '#cdd6f4'
        SUBTEXT = '#a6adc8'

        self.COLOR_GREEN   = GREEN
        self.COLOR_SUBTEXT = SUBTEXT
        self.COLOR_RED     = RED

        win = tk.Toplevel(self.root)
        self.float_win = win
        win.title("截图工具")
        win.attributes('-topmost', True)
        win.resizable(False, False)
        win.configure(bg=BG)
        win.protocol("WM_DELETE_WINDOW", self._exit)

        W, H = 250, 370
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"{W}x{H}+{sw - W - 20}+{(sh - H) // 2}")

        # ── Title bar ─────────────────────────────────────────────────────────
        title_bar = tk.Frame(win, bg=SURFACE, height=40)
        title_bar.pack(fill='x')
        title_bar.pack_propagate(False)

        tk.Label(
            title_bar, text="📷  截图工具",
            bg=SURFACE, fg=TEXT,
            font=('微软雅黑', 11, 'bold'),
        ).pack(side='left', padx=12)

        title_bar.bind('<ButtonPress-1>', self._drag_start)
        title_bar.bind('<B1-Motion>',     self._drag_move)

        # ── Save-path display ─────────────────────────────────────────────────
        path_frame = tk.Frame(win, bg=BG)
        path_frame.pack(fill='x', padx=12, pady=(10, 0))

        tk.Label(
            path_frame, text="保存位置",
            bg=BG, fg=SUBTEXT,
            font=('微软雅黑', 8),
        ).pack(anchor='w')

        self.path_label = tk.Label(
            path_frame,
            text=self._short_path(self.save_path),
            bg=BG, fg=BLUE,
            font=('微软雅黑', 8),
            cursor='hand2',
        )
        self.path_label.pack(anchor='w')
        self.path_label.bind('<Button-1>', lambda _e: self._change_path())

        # ── Shortcut hint ─────────────────────────────────────────────────────
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

        # ── Screenshot button ─────────────────────────────────────────────────
        tk.Button(
            win, text="📷   截  图",
            command=self._capture,
            bg=BLUE, fg='#1e1e2e',
            font=('微软雅黑', 13, 'bold'),
            relief='flat', cursor='hand2',
            padx=20, pady=10, bd=0,
            activebackground='#74c7ec',
            activeforeground='#1e1e2e',
        ).pack(fill='x', padx=12, pady=(8, 6))

        # ── Bottom buttons ────────────────────────────────────────────────────
        bottom = tk.Frame(win, bg=BG)
        bottom.pack(fill='x', padx=12, pady=(0, 6))

        tk.Button(
            bottom, text="更改路径",
            command=self._change_path,
            bg=GREEN, fg='#1e1e2e',
            font=('微软雅黑', 9),
            relief='flat', cursor='hand2',
            padx=8, pady=5, bd=0,
            activebackground='#94e2d5',
            activeforeground='#1e1e2e',
        ).pack(side='left', expand=True, fill='x', padx=(0, 4))

        tk.Button(
            bottom, text="退  出",
            command=self._exit,
            bg=RED, fg='#1e1e2e',
            font=('微软雅黑', 9),
            relief='flat', cursor='hand2',
            padx=8, pady=5, bd=0,
            activebackground='#eba0ac',
            activeforeground='#1e1e2e',
        ).pack(side='right', expand=True, fill='x', padx=(4, 0))

        # ── Status bar ────────────────────────────────────────────────────────
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

        self._ref_cb = tk.Checkbutton(
            win,
            text="显示命名快捷参考",
            variable=self._show_quick_ref_var,
            command=self._on_quick_ref_toggle,
            bg=BG, fg=SUBTEXT,
            selectcolor=SURFACE,
            activebackground=BG,
            activeforeground=GREEN,
            font=('微软雅黑', 8),
            cursor='hand2',
        )
        self._ref_cb.pack(fill='x', padx=12, pady=(2, 0))

        self._tag_panel_cb = tk.Checkbutton(
            win,
            text="截后弹标签面板",
            variable=self._show_tag_panel_var,
            command=self._on_tag_panel_toggle,
            bg=BG, fg=SUBTEXT,
            selectcolor=SURFACE,
            activebackground=BG,
            activeforeground=GREEN,
            font=('微软雅黑', 8),
            cursor='hand2',
        )
        self._tag_panel_cb.pack(fill='x', padx=12, pady=(2, 0))

        self._auto_name_cb = tk.Checkbutton(
            win,
            text="键盘输入自动补全",
            variable=self._auto_name_var,
            command=self._on_auto_name_toggle,
            bg=BG, fg=SUBTEXT,
            selectcolor=SURFACE,
            activebackground=BG,
            activeforeground=GREEN,
            font=('微软雅黑', 8),
            cursor='hand2',
        )
        self._auto_name_cb.pack(fill='x', padx=12, pady=(2, 0))

        tk.Button(
            win, text="✏️ 编辑标签",
            command=self._edit_tag_labels,
            bg=SURFACE, fg=SUBTEXT,
            font=('微软雅黑', 9),
            relief='flat', cursor='hand2',
            padx=8, pady=3, bd=0,
            activebackground='#45475a',
            activeforeground=TEXT,
        ).pack(fill='x', padx=12, pady=(4, 0))

        self.status_label = tk.Label(
            win, text="📌 就绪",
            bg=BG, fg=SUBTEXT,
            font=('微软雅黑', 8),
            anchor='w',
        )
        self.status_label.pack(fill='x', padx=12, pady=(0, 8))

        self._setup_hotkey()

    def _drag_start(self, event):
        self._drag_x = event.x_root - self.float_win.winfo_x()
        self._drag_y = event.y_root - self.float_win.winfo_y()

    def _drag_move(self, event):
        self.float_win.geometry(
            f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}"
        )

    # ── Hotkey ────────────────────────────────────────────────────────────────

    def _setup_hotkey(self):
        self._hotkey_thread = threading.Thread(
            target=self._hotkey_loop, daemon=True,
        )
        self._hotkey_thread.start()

    def _change_hotkey(self):
        dlg = HotkeyDialog(self.float_win)
        vk, name = dlg.show()
        if vk is not None and name is not None:
            self._hotkey_vk = vk
            self._hotkey_label.config(text=f"快捷键: {name}")
            self._save_config()
            self._set_status(f"快捷键已更新: {name}", self.COLOR_GREEN)

    def _hotkey_loop(self):
        was_pressed = False
        while self._running:
            time.sleep(0.05)
            is_pressed = ctypes.windll.user32.GetAsyncKeyState(self._hotkey_vk) & 0x8000
            if is_pressed and not was_pressed:
                self.root.after(0, self._capture)
            was_pressed = is_pressed

    def _force_foreground(self, window):
        try:
            hwnd = window.winfo_id()
            fg_hwnd = ctypes.windll.user32.GetForegroundWindow()
            fg_thread_id = ctypes.windll.user32.GetWindowThreadProcessId(fg_hwnd, None)
            our_thread_id = ctypes.windll.kernel32.GetCurrentThreadId()

            if fg_thread_id and fg_thread_id != our_thread_id:
                ctypes.windll.user32.AttachThreadInput(our_thread_id, fg_thread_id, True)
                ctypes.windll.user32.SetForegroundWindow(hwnd)
                ctypes.windll.user32.BringWindowToTop(hwnd)
                ctypes.windll.user32.AttachThreadInput(our_thread_id, fg_thread_id, False)
            else:
                ctypes.windll.user32.SetForegroundWindow(hwnd)
                ctypes.windll.user32.BringWindowToTop(hwnd)
        except Exception:
            pass

    def _refocus_entry(self, entry):
        try:
            if entry.winfo_exists():
                entry.focus_force()
        except Exception:
            pass

    def _set_status(self, text, color=None):
        if color is None:
            color = self.COLOR_SUBTEXT
        self.status_label.config(text=text, fg=color)

    # ── Screenshot logic ──────────────────────────────────────────────────────

    def _find_available_filename(self, base_path):
        name, ext = os.path.splitext(base_path)
        if not os.path.exists(base_path):
            return base_path, os.path.basename(base_path)
        n = 1
        while True:
            new_path = f"{name}_{n}{ext}"
            if not os.path.exists(new_path):
                return new_path, os.path.basename(new_path)
            n += 1

    def _capture(self):
        if self._capturing:
            return
        self._capturing = True
        try:
            self.float_win.withdraw()
            self.root.update()
            time.sleep(0.45)

            self._screenshot = ImageGrab.grab()

            if self._auto_scroll_var.get():
                self._send_page_down()

            self.float_win.deiconify()
            self.float_win.attributes('-topmost', True)
            self.float_win.lift()
            self._force_foreground(self.float_win)

            if self._show_tag_panel_var.get():
                self.float_win.after(80, self._show_tag_panel)
            else:
                self.float_win.after(80, self._prompt_filename)
        except Exception:
            self._capturing = False
            self.float_win.deiconify()
            self.float_win.attributes('-topmost', True)

    def _send_page_down(self):
        VK_NEXT = 0x22
        ctypes.windll.user32.keybd_event(VK_NEXT, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_NEXT, 0, 2, 0)
        time.sleep(0.1)

    def _on_auto_scroll_toggle(self):
        self._save_config()

    def _on_quick_ref_toggle(self):
        self._save_config()

    def _on_tag_panel_toggle(self):
        self._save_config()

    def _on_auto_name_toggle(self):
        self._save_config()

    def _edit_tag_labels(self):
        dialog = tk.Toplevel(self.float_win)
        dialog.title("编辑标签")
        dialog.resizable(False, False)
        dialog.configure(bg='#1e1e2e')
        dialog.transient(self.float_win)
        dialog.grab_set()

        W, H = 300, 350
        px = self.float_win.winfo_rootx() + (self.float_win.winfo_width() - W) // 2
        py = self.float_win.winfo_rooty() + (self.float_win.winfo_height() - H) // 2
        dialog.geometry(f"{W}x{H}+{px}+{py}")

        tk.Label(
            dialog, text="一行一个标签名",
            bg='#1e1e2e', fg='#cdd6f4',
            font=('微软雅黑', 10),
        ).pack(pady=(12, 6))

        text = tk.Text(
            dialog, bg='#313244', fg='#cdd6f4',
            insertbackground='#cdd6f4',
            font=('微软雅黑', 10),
            relief='flat', bd=4,
            width=30, height=14,
        )
        text.pack(fill='both', expand=True, padx=16, pady=(0, 10))
        text.insert('1.0', '\n'.join(self._tag_labels))

        btn_frame = tk.Frame(dialog, bg='#1e1e2e')
        btn_frame.pack(pady=(0, 12))

        def _do_save():
            lines = text.get('1.0', 'end-1c').split('\n')
            labels = [l.strip() for l in lines if l.strip()]
            unique = []
            seen = set()
            for l in labels:
                if l not in seen:
                    unique.append(l)
                    seen.add(l)
            if unique:
                self._tag_labels = unique
                self._save_config()
            dialog.destroy()

        tk.Button(
            btn_frame, text="保存", command=_do_save,
            bg='#a6e3a1', fg='#1e1e2e',
            font=('微软雅黑', 10, 'bold'),
            relief='flat', cursor='hand2',
            padx=20, pady=6, bd=0,
        ).pack(side='left', padx=(0, 8))

        tk.Button(
            btn_frame, text="取消", command=dialog.destroy,
            bg='#f38ba8', fg='#1e1e2e',
            font=('微软雅黑', 10, 'bold'),
            relief='flat', cursor='hand2',
            padx=20, pady=6, bd=0,
        ).pack(side='left')

        dialog.attributes('-topmost', True)
        dialog.focus_force()
        text.focus_force()

    def _show_tag_panel(self):
        labels = self._get_tag_labels()
        BG = '#313244'
        TEXT = '#cdd6f4'
        GREEN_BG = '#a6e3a1'
        GREEN_FG = '#1e1e2e'
        RED = '#f38ba8'
        BLUE = '#89b4fa'
        GRAY = '#6C7086'

        panel = tk.Toplevel(self.float_win)
        panel.overrideredirect(True)
        panel.configure(bg=BG)

        PW, PH = 280, 210
        mx = panel.winfo_pointerx()
        my = panel.winfo_pointery()
        px = mx - PW // 2
        py = my + 20
        sw, sh = panel.winfo_screenwidth(), panel.winfo_screenheight()
        if px < 0:
            px = 5
        if px + PW > sw:
            px = sw - PW - 5
        if py + PH > sh:
            py = my - PH - 10
        panel.geometry(f"{PW}x{PH}+{px}+{py}")

        panel.attributes('-topmost', True)

        _selected = set()

        def _dismiss():
            panel.destroy()
            self._capturing = False

        def _select_tag(alias):
            if alias in _selected:
                _selected.discard(alias)
            else:
                _selected.add(alias)
            _refresh_buttons()
            _refresh_selected_label()

        def _refresh_buttons():
            for btn in _tag_buttons:
                alias = btn['text']
                if alias in _selected:
                    btn.configure(bg=GREEN_BG, fg=GREEN_FG, activebackground=GREEN_BG, activeforeground=GREEN_FG)
                else:
                    btn.configure(bg='#45475a', fg='#a6adc8', activebackground='#585b70', activeforeground=TEXT)

        def _label_index(alias):
            try:
                return labels.index(alias)
            except ValueError:
                return 999

        def _refresh_selected_label():
            names = sorted(_selected, key=_label_index)
            if names:
                selected_str.set(' & '.join(names))
            else:
                selected_str.set('（未选择）')

        def _do_save():
            names = sorted(_selected, key=_label_index)
            if not names:
                return
            filename = '&'.join(names)
            panel.destroy()
            self._do_save_image(filename)

        def _do_skip():
            _dismiss()
            self._prompt_filename()

        title_bar = tk.Frame(panel, bg='#1e1e2e', height=20)
        title_bar.pack(fill='x')
        tk.Label(
            title_bar,
            text="点击标签命名",
            bg='#1e1e2e', fg=TEXT,
            font=('微软雅黑', 8),
        ).pack(side='left', padx=8, pady=2)
        tk.Label(
            title_bar,
            text="×", bg='#1e1e2e', fg=GRAY,
            font=('微软雅黑', 10),
            cursor='hand2',
        ).pack(side='right', padx=6, pady=1)
        title_bar.children[title_bar.winfo_children()[-1]._name].bind('<Button-1>', lambda e: _dismiss())

        tag_frame = tk.Frame(panel, bg=BG)
        tag_frame.pack(fill='x', padx=8, pady=(6, 0))

        _tag_buttons = []
        for i, alias in enumerate(labels):
            btn = tk.Button(
                tag_frame,
                text=alias,
                command=lambda a=alias: _select_tag(a),
                bg='#45475a', fg='#a6adc8',
                font=('微软雅黑', 8),
                relief='flat', cursor='hand2',
                padx=4, pady=2, bd=0,
                activebackground='#585b70', activeforeground=TEXT,
                width=6,
            )
            _tag_buttons.append(btn)
            row = i // 4
            col = i % 4
            btn.grid(row=row, column=col, padx=1, pady=1, sticky='ew')
            if row > 0:
                btn.grid_configure(pady=(0, 2))

        selected_str = tk.StringVar(value='（未选择）')
        sel_label = tk.Label(
            panel,
            textvariable=selected_str,
            bg=BG, fg=BLUE,
            font=('微软雅黑', 8),
            anchor='center',
        )
        sel_label.pack(fill='x', padx=8, pady=(6, 2))

        btn_frame = tk.Frame(panel, bg=BG)
        btn_frame.pack(fill='x', padx=8, pady=(0, 6))

        tk.Button(
            btn_frame, text="✅ 保存",
            command=_do_save,
            bg=GREEN_BG, fg=GREEN_FG,
            font=('微软雅黑', 9, 'bold'),
            relief='flat', cursor='hand2',
            padx=16, pady=4, bd=0,
        ).pack(side='left', expand=True, fill='x', padx=(0, 4))

        tk.Button(
            btn_frame, text="⏭ 跳过/自定义",
            command=_do_skip,
            bg='#45475a', fg=TEXT,
            font=('微软雅黑', 9),
            relief='flat', cursor='hand2',
            padx=16, pady=4, bd=0,
            activebackground='#585b70',
        ).pack(side='right', expand=True, fill='x', padx=(4, 0))

        panel.update_idletasks()
        self._force_foreground(panel)

    def _do_save_image(self, filename):
        filename = filename.strip()
        for ch in r'\/:*?"<>|':
            filename = filename.replace(ch, '_')

        filepath = os.path.join(self.save_path, f"{filename}.png")
        filepath, display_name = self._find_available_filename(filepath)

        if filepath != os.path.join(self.save_path, f"{filename}.png"):
            messagebox.showinfo(
                "文件已存在",
                f'"{filename}.png" 已存在，\n自动保存为 "{display_name}"',
                parent=self.float_win,
            )

        self._screenshot.save(filepath, 'PNG')
        self._screenshot = None
        self._set_status(f"✅ 已保存: {display_name}", self.COLOR_GREEN)
        self._capturing = False

    def _prompt_filename(self):
        try:
            result = [None]

            dialog = tk.Toplevel(self.float_win)
            dialog.title("保存截图")
            dialog.resizable(False, False)
            dialog.configure(bg='#1e1e2e')
            dialog.transient(self.float_win)

            W, H = 340, 210
            px = self.float_win.winfo_rootx() + (self.float_win.winfo_width() - W) // 2
            py = self.float_win.winfo_rooty() + (self.float_win.winfo_height() - H) // 2
            dialog.geometry(f"{W}x{H}+{px}+{py}")

            tk.Label(
                dialog,
                text="请输入图片名称（无需填写扩展名）：",
                bg='#1e1e2e', fg='#cdd6f4',
                font=('微软雅黑', 10),
            ).pack(pady=(16, 6))

            entry_var = tk.StringVar()
            entry = tk.Entry(
                dialog,
                textvariable=entry_var,
                bg='#313244', fg='#cdd6f4',
                insertbackground='#cdd6f4',
                font=('微软雅黑', 11),
                relief='flat', bd=4,
            )
            entry.pack(fill='x', padx=20, ipady=4)

            labels = self._get_tag_labels()
            half = (len(labels) + 1) // 2
            ref_parts_1 = "  ".join(f"{i+1}.{labels[i]}" for i in range(min(half, len(labels))))
            ref_parts_2 = "  ".join(f"{i+half+1}.{labels[i]}" for i in range(half, len(labels)))

            ref_frame = tk.Frame(dialog, bg='#1e1e2e')
            ref_frame.pack(fill='x', padx=20, pady=(4, 0))

            ref_label_1 = tk.Label(
                ref_frame,
                text=ref_parts_1,
                bg='#1e1e2e', fg='#6C7086',
                font=('微软雅黑', 8),
                anchor='w',
            )
            ref_label_1.pack(anchor='w')

            ref_label_2 = tk.Label(
                ref_frame,
                text=ref_parts_2,
                bg='#1e1e2e', fg='#6C7086',
                font=('微软雅黑', 8),
                anchor='w',
            )
            ref_label_2.pack(anchor='w')

            hint_label = tk.Label(
                ref_frame,
                text="💡 输入缩写自动补全，多标题用 & 连接，如: SYS&CPU",
                bg='#1e1e2e', fg='#89B4FA',
                font=('微软雅黑', 8),
                anchor='w',
            )
            hint_label.pack(anchor='w', pady=(2, 0))

            if not self._show_quick_ref_var.get():
                ref_label_1.pack_forget()
                ref_label_2.pack_forget()
                hint_label.pack_forget()

            if self._auto_name_var.get():
                _prev_text = [None]

                def _on_key_release(event):
                    if event.keysym in ('Control_L', 'Control_R', 'Shift_L', 'Shift_R',
                                        'Alt_L', 'Alt_R', 'Return', 'Escape', 'Tab',
                                        'BackSpace', 'Delete', 'Left', 'Right', 'Home', 'End'):
                        _prev_text[0] = entry_var.get()
                        return
                    if event.state & 0x4:
                        _prev_text[0] = entry_var.get()
                        return

                    text = entry_var.get()
                    completed = _smart_complete(_prev_text[0], text)
                    if completed != text:
                        entry_var.set(completed)
                        entry.icursor(tk.END)
                    _prev_text[0] = entry_var.get()

                entry.bind('<KeyRelease>', _on_key_release)

            btn_frame = tk.Frame(dialog, bg='#1e1e2e')
            btn_frame.pack(pady=(8, 12))

            def _ok():
                result[0] = entry_var.get()
                dialog.destroy()

            def _cancel():
                dialog.destroy()

            tk.Label(btn_frame, bg='#1e1e2e', width=4).pack(side='left')

            tk.Button(
                btn_frame, text="确定",
                command=_ok,
                bg='#a6e3a1', fg='#1e1e2e',
                font=('微软雅黑', 10, 'bold'),
                relief='flat', cursor='hand2',
                padx=20, pady=6, bd=0,
            ).pack(side='left', padx=(0, 8))

            tk.Button(
                btn_frame, text="取消",
                command=_cancel,
                bg='#f38ba8', fg='#1e1e2e',
                font=('微软雅黑', 10, 'bold'),
                relief='flat', cursor='hand2',
                padx=20, pady=6, bd=0,
            ).pack(side='left')

            dialog.bind('<Return>', lambda e: _ok())
            dialog.bind('<Escape>', lambda e: _cancel())
            dialog.protocol('WM_DELETE_WINDOW', _cancel)

            dialog.attributes('-topmost', True)
            dialog.update_idletasks()
            self._force_foreground(dialog)
            dialog.focus_force()
            dialog.grab_set()
            dialog.after(50, entry.focus_force)
            dialog.after(200, self._refocus_entry, entry)

            dialog.wait_window()

            filename = result[0]
            if not filename or not filename.strip():
                self._set_status("🗑️  已取消", self.COLOR_SUBTEXT)
                self._capturing = False
                return

            self._do_save_image(filename.strip())
        except Exception:
            self._capturing = False

    # ── Exit ──────────────────────────────────────────────────────────────────

    def _exit(self):
        self._running = False
        self.root.destroy()
        sys.exit(0)


if __name__ == '__main__':
    app = ScreenshotApp()
