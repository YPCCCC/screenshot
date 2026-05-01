import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import time
import os
import sys
import json
import ctypes
import threading

from PIL import ImageGrab

VK_OEM_4 = 0xDB


class ScreenshotApp:
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

        saved = self._load_config()
        if saved and os.path.isdir(saved):
            self.save_path = saved
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
                return data.get('save_path')
        except Exception:
            pass
        return None

    def _save_config(self):
        try:
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(
                    {'save_path': self.save_path}, f,
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

        W, H = 250, 270
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
        tk.Label(
            win, text="快捷键: [",
            bg=BG, fg=SUBTEXT,
            font=('微软雅黑', 8),
        ).pack(pady=(4, 0))

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

    def _hotkey_loop(self):
        was_pressed = False
        while self._running:
            time.sleep(0.05)
            is_pressed = ctypes.windll.user32.GetAsyncKeyState(VK_OEM_4) & 0x8000
            if is_pressed and not was_pressed:
                self.root.after(0, self._capture)
            was_pressed = is_pressed

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

            screenshot = ImageGrab.grab()

            self.float_win.deiconify()
            self.float_win.attributes('-topmost', True)
            self.float_win.lift()
            self.float_win.focus_force()

            filename = simpledialog.askstring(
                "保存截图",
                "请输入图片名称（无需填写扩展名）：",
                parent=self.float_win,
            )

            if not filename or not filename.strip():
                self._set_status("🗑️  已取消", self.COLOR_SUBTEXT)
                return

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

            screenshot.save(filepath, 'PNG')
            self._set_status(f"✅ 已保存: {display_name}", self.COLOR_GREEN)
        finally:
            self._capturing = False

    # ── Exit ──────────────────────────────────────────────────────────────────

    def _exit(self):
        self._running = False
        self.root.destroy()
        sys.exit(0)


if __name__ == '__main__':
    app = ScreenshotApp()
