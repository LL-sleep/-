#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TBSerial - 泰比特串口调试工具 V2.0
仿 SSCOM，但更清爽好用。

功能：
- 串口配置（端口/波特率/数据位/校验/停止位）+ 刷新按钮
- 收发数据：HEX / ASCII 切换，回车符选项
- 时间戳显示（精确到毫秒）
- 定时发送 + 回车快捷发送
- 自动滚动 / 清空 / 保存日志
- 快捷命令栏（可编辑/添加/删除）
- 文件发送（hex/bin）
- 接收区字体大小调节
- 发送历史记录
- 窗口位置记忆
- 快捷键：Ctrl+Enter发送 / ESC清空 / F5刷新端口
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser, simpledialog
import serial
import serial.tools.list_ports
import threading
import time
import os
import json
import glob
from datetime import datetime


class TBSerial:
    CONFIG_PATH = os.path.join(os.path.dirname(__file__), "tbserial_config.json")
    QUICK_CMDS_FILE = os.path.join(os.path.dirname(__file__), "tbserial_commands.json")

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("TBSerial V2 - 串口调试工具")
        self._load_window_pos()
        if not hasattr(self, '_w') or not getattr(self, '_w', None):
            self.root.geometry("1000x720")
        self.root.minsize(850, 580)

        self.serial_port = None
        self.is_open = False
        self.receive_thread = None
        self.receive_running = False
        self.timer_running = False
        self.send_count = 0
        self.recv_count = 0

        # 配色方案（深色主题）
        self.colors = {
            "bg": "#1e1e2e",
            "fg": "#cdd6f4",
            "entry_bg": "#313244",
            "entry_fg": "#cdd6f4",
            "btn_bg": "#45475a",
            "btn_fg": "#cdd6f4",
            "btn_active": "#89b4fa",
            "accent": "#89b4fa",
            "success": "#a6e3a1",
            "error": "#f38ba8",
            "warning": "#fab387",
            "text_area_bg": "#181825",
            "text_area_fg": "#a6adc8",
            "frame_bg": "#11111b",
            "border": "#313244",
            "highlight": "#cba6f7",
        }

        # 字体大小
        self.recv_font_size = 11

        # 常用快捷命令（从文件加载或默认）
        self.quick_commands = [
            "get tid", "get version", "get gps", "get bms",
            "sensor stop", "sensor start", "set pwr=1", "set pwr=0",
        ]
        self._load_quick_commands()

        # 发送历史
        self.send_history = []
        self.history_idx = -1

        self._apply_theme()
        self._bind_shortcuts()
        self._build_menu()
        self._build_ui()
        self.root.after(100, self._refresh_ports)  # 延迟刷新，等UI构建完

    # ==================== 配置 & 主题 ====================

    def _load_window_pos(self):
        """加载窗口位置"""
        try:
            with open(self.CONFIG_PATH, "r") as f:
                cfg = json.load(f)
                geo = cfg.get("geometry", "")
                if geo:
                    self._geo = geo
        except Exception:
            pass

    def _save_window_pos(self):
        """保存窗口位置"""
        try:
            cfg = {"geometry": self.root.geometry(), "font_size": self.recv_font_size}
            with open(self.CONFIG_PATH, "w") as f:
                json.dump(cfg, f)
        except Exception:
            pass

    def _load_quick_commands(self):
        """加载快捷命令列表"""
        try:
            with open(self.QUICK_CMDS_FILE, "r") as f:
                cmds = json.load(f)
                if isinstance(cmds, list) and cmds:
                    self.quick_commands = cmds
        except Exception:
            pass

    def _save_quick_commands(self):
        """保存快捷命令列表"""
        try:
            with open(self.QUICK_CMDS_FILE, "w") as f:
                json.dump(self.quick_commands, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _apply_theme(self):
        """应用深色主题"""
        style = ttk.Style()
        style.theme_use("clam")

        bg = self.colors["bg"]
        fg = self.colors["fg"]
        entry_bg = self.colors["entry_bg"]
        btn_bg = self.colors["btn_bg"]
        accent = self.colors["accent"]

        style.configure(".", background=bg, foreground=fg)
        style.configure("TFrame", background=bg)
        style.configure("TLabelframe", background=bg, foreground=fg,
                       labeloutside=True, labelmargins=(10, 0))
        style.configure("TLabelframe.Label", background=bg, foreground=accent,
                       font=("Microsoft YaHei UI", 9, "bold"))
        style.configure("TLabel", background=bg, foreground=fg,
                       font=("Microsoft YaHei UI", 9))
        style.configure("TCheckbutton", background=bg, foreground=fg)
        style.configure("TRadiobutton", background=bg, foreground=fg)
        style.configure("TCombobox", fieldbackground=entry_bg,
                       background=btn_bg, foreground=fg,
                       arrowcolor=fg, font=("Microsoft YaHei UI", 9))

        self.root.configure(bg=bg)

    def _bind_shortcuts(self):
        """绑定快捷键"""
        self.root.bind("<Control-Return>", lambda e: self.send_data())
        self.root.bind("<Return>", lambda e: self.send_data())
        self.root.bind("<Escape>", lambda e: self.send_text.delete(1.0, tk.END))
        self.root.bind("<F5>", lambda e: self._refresh_ports())

        # 窗口关闭时保存位置
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        """关闭窗口时保存配置"""
        self._save_window_pos()
        if self.is_open:
            self._close_port(force=True)
        self.root.destroy()

    # ==================== 菜单栏 ====================

    def _build_menu(self):
        """构建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="保存日志...", command=self.save_log)
        file_menu.add_command(label="发送文件...", command=self._send_file)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self._on_close)

        tool_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="工具", menu=tool_menu)
        tool_menu.add_command(label="刷新端口 (F5)", command=self._refresh_ports)
        tool_menu.add_separator()

        # 接收字体大小子菜单
        font_menu = tk.Menu(tool_menu, tearoff=0)
        tool_menu.add_cascade(label="接收区字号", menu=font_menu)
        for sz in [9, 10, 11, 12, 14, 16, 18, 20]:
            font_menu.add_command(label=f"{sz}pt", command=lambda s=sz: self._change_font(s))

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self._show_about)
        help_menu.add_command(label="快捷键说明", command=self._show_shortcuts)

    # ==================== UI 构建 ====================

    def _build_ui(self):
        c = self.colors

        # ===== 工具栏 =====
        toolbar = ttk.Frame(self.root, padding=4)
        toolbar.pack(fill=tk.X)

        # 端口
        self._make_toolbar_item(toolbar, "端口:", "port_var", width=12)
        # 刷新按钮
        refresh_btn = tk.Button(toolbar, text="🔄", command=self._refresh_ports,
                               bg=c["btn_bg"], fg=c["fg"], relief=tk.FLAT,
                               font=("Microsoft YaHei UI", 10), cursor="hand2",
                               width=2, height=1)
        refresh_btn.pack(side=tk.LEFT, padx=(0, 10))

        # 波特率
        self._make_toolbar_item(toolbar, "波特率:", "baud_var", width=7, default="115200",
                               values=["9600","19200","38400","57600","115200","230400","460800","921600"])

        # 数据位
        self._make_toolbar_item(toolbar, "数据位:", "databits_var", width=4, default="8",
                               values=["5","6","7","8"])

        # 校验
        self._make_toolbar_item(toolbar, "校验:", "parity_var", width=5, default="None",
                               values=["None","Odd","Even","Mark","Space"])

        # 停止位
        self._make_toolbar_item(toolbar, "停止位:", "stopbits_var", width=4, default="1",
                               values=["1","1.5","2"])

        # 打开按钮
        self.open_btn = tk.Button(toolbar, text="🔌 打开串口", command=self.toggle_port,
                                  bg=c["success"], fg="#1e1e2e",
                                  activebackground=c["accent"],
                                  font=("Microsoft YaHei UI", 10, "bold"),
                                  relief=tk.FLAT, cursor="hand2", width=12)
        self.open_btn.pack(side=tk.LEFT, padx=(10, 12))

        self.status_label = tk.Label(toolbar, text="● 未连接", fg=c["error"],
                                    bg=c["bg"], font=("Microsoft YaHei UI", 9, "bold"))
        self.status_label.pack(side=tk.LEFT)

        # ===== 发送区域 =====
        send_frame = ttk.LabelFrame(self.root, text=" 发送 ", padding=6)
        send_frame.pack(fill=tk.X, padx=5, pady=4)

        # 输入框
        input_frame = ttk.Frame(send_frame)
        input_frame.pack(fill=tk.X)

        self.send_text = tk.Text(input_frame, height=3, bg=c["entry_bg"], fg=c["fg"],
                                 insertbackground=c["fg"], insertwidth=1,
                                 font=("Consolas", 11), wrap=tk.WORD,
                                 relief=tk.FLAT, padx=8, pady=6,
                                 borderwidth=1, highlightthickness=1,
                                 highlightbackground=c["border"])
        self.send_text.pack(fill=tk.X, expand=True, side=tk.LEFT)

        # 发送选项行
        opt_frame = ttk.Frame(send_frame)
        opt_frame.pack(fill=tk.X, pady=(4, 0))

        self.send_hex_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opt_frame, text="HEX", variable=self.send_hex_var).pack(side=tk.LEFT)

        self.timestamp_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opt_frame, text="加时间戳", variable=self.timestamp_var).pack(side=tk.LEFT, padx=(8, 0))

        # 结尾符
        ttk.Label(opt_frame, text="结尾符:").pack(side=tk.LEFT, padx=(15, 3))
        self.endline_var = tk.StringVar(value="\\n")
        end_combo = ttk.Combobox(opt_frame, textvariable=self.endline_var,
                                 values=["\\n", "\\r\\n", "\\r", "无"], width=6, state="readonly")
        end_combo.pack(side=tk.LEFT)

        # 定时发送
        ttk.Separator(opt_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        ttk.Label(opt_frame, text="定时(ms):").pack(side=tk.LEFT)
        self.timer_entry = tk.Entry(opt_frame, width=6, bg=c["entry_bg"],
                                   fg=c["fg"], insertbackground=c["fg"],
                                   relief=tk.FLAT, font=("Consolas", 10),
                                   justify=tk.CENTER)
        self.timer_entry.insert(tk.END, "")
        self.timer_entry.pack(side=tk.LEFT, padx=(3, 5))

        self.timer_var = tk.BooleanVar(value=False)
        self.timer_cb = ttk.Checkbutton(opt_frame, text="定时", variable=self.timer_var,
                                        command=self.toggle_timer)
        self.timer_cb.pack(side=tk.LEFT)

        # 右侧按钮
        btn_row = tk.Frame(opt_frame, bg=c["bg"])
        btn_row.pack(side=tk.RIGHT)

        self.send_btn = tk.Button(btn_row, text="➤ 发送", command=self.send_data,
                                  bg=c["accent"], fg="#1e1e2e",
                                  activebackground=c["btn_active"],
                                  font=("Microsoft YaHei UI", 10, "bold"),
                                  relief=tk.FLAT, cursor="hand2", width=9)
        self.send_btn.pack(side=tk.RIGHT, padx=(5, 0))

        tk.Button(btn_row, text="清空", command=lambda: self.send_text.delete(1.0, tk.END),
                  bg=c["btn_bg"], fg=c["fg"], relief=tk.FLAT,
                  font=("Microsoft YaHei UI", 9), width=5).pack(side=tk.RIGHT)

        # ===== 接收区域 =====
        recv_frame = ttk.LabelFrame(self.root, text=" 接收 ", padding=6)
        recv_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=4)

        recv_ctrl = ttk.Frame(recv_frame)
        recv_ctrl.pack(fill=tk.X, pady=(0, 4))

        self.recv_hex_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(recv_ctrl, text="HEX", variable=self.recv_hex_var).pack(side=tk.LEFT)

        self.auto_scroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(recv_ctrl, text="自动滚", variable=self.auto_scroll_var).pack(side=tk.LEFT, padx=(8, 0))

        self.recv_timestamp_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(recv_ctrl, text="时间戳", variable=self.recv_timestamp_var).pack(side=tk.LEFT, padx=(8, 0))

        # 字号调节
        ttk.Separator(recv_ctrl, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        tk.Button(recv_ctrl, text="A-", command=lambda: self._change_font(max(8, self.recv_font_size - 1)),
                  bg=c["btn_bg"], fg=c["fg"], relief=tk.FLAT, font=("Arial", 10, "bold"),
                  width=3).pack(side=tk.LEFT)
        self.font_size_lbl = tk.Label(recv_ctrl, text=f" {self.recv_font_size} ",
                                      bg=c["bg"], fg=c["accent"], font=("Consolas", 9))
        self.font_size_lbl.pack(side=tk.LEFT)
        tk.Button(recv_ctrl, text="A+", command=lambda: self._change_font(min(30, self.recv_font_size + 1)),
                  bg=c["btn_bg"], fg=c["fg"], relief=tk.FLAT, font=("Arial", 10, "bold"),
                  width=3).pack(side=tk.LEFT)

        # 统计 + 操作按钮
        right_panel = tk.Frame(recv_ctrl, bg=c["bg"])
        right_panel.pack(side=tk.RIGHT)

        self.stats_label = tk.Label(right_panel, text="Tx:0 | Rx:0",
                                    bg=c["bg"], fg=c["accent"], font=("Consolas", 9))
        self.stats_label.pack(side=tk.RIGHT, padx=(8, 0))

        tk.Button(right_panel, text="清空", command=self.clear_recv,
                  bg=c["btn_bg"], fg=c["fg"], relief=tk.FLAT, width=5,
                  font=("Microsoft YaHei UI", 9)).pack(side=tk.RIGHT, padx=(3, 0))
        tk.Button(right_panel, text="保存", command=self.save_log,
                  bg=c["btn_bg"], fg=c["fg"], relief=tk.FLAT, width=5,
                  font=("Microsoft YaHei UI", 9)).pack(side=tk.RIGHT, padx=(3, 0))
        tk.Button(right_panel, text="发文件", command=self._send_file,
                  bg=c["btn_bg"], fg=c["fg"], relief=tk.FLAT, width=5,
                  font=("Microsoft YaHei UI", 9)).pack(side=tk.RIGHT)

        # 文本框 + 滚动条
        text_frame = ttk.Frame(recv_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.recv_text = tk.Text(text_frame, bg=c["text_area_bg"],
                                 fg=c["text_area_fg"],
                                 insertbackground=c["fg"],
                                 font=("Consolas", self.recv_font_size),
                                 wrap=tk.NONE, relief=tk.FLAT,
                                 padx=8, pady=6, state=tk.DISABLED)

        yscroll = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.recv_text.yview)
        xscroll = tk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=self.recv_text.xview)
        self.recv_text.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        xscroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.recv_text.pack(fill=tk.BOTH, expand=True)

        # ===== 快捷命令栏 =====
        quick_frame = ttk.LabelFrame(self.root, text=" 快捷命令 ", padding=5)
        quick_frame.pack(fill=tk.X, padx=5, pady=(0, 4))

        quick_inner = ttk.Frame(quick_frame)
        quick_inner.pack(fill=tk.X)

        for i, cmd in enumerate(self.quick_commands[:12]):  # 最多显示12个
            btn = tk.Button(quick_inner, text=cmd, width=max(10, len(cmd) + 2),
                           command=lambda c=cmd: self._quick_send(c),
                           bg=c["btn_bg"], fg=c["accent"],
                           activebackground=c["btn_active"],
                           font=("Microsoft YaHei UI", 9), relief=tk.FLAT,
                           cursor="hand2")
            btn.pack(side=tk.LEFT, padx=2, pady=2)

        # 编辑按钮
        quick_btns = tk.Frame(quick_frame, bg=c["bg"])
        quick_btns.pack(fill=tk.X, pady=(4, 0))

        tk.Button(quick_btns, text="✏ 编辑命令", command=self._edit_quick_cmds,
                  bg=c["btn_bg"], fg=c["fg"], relief=tk.FLAT,
                  font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT)
        tk.Button(quick_btns, text="+ 添加", command=self._add_quick_cmd,
                  bg=c["btn_bg"], fg=c["fg"], relief=tk.FLAT,
                  font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT, padx=(5, 0))

    def _make_toolbar_item(self, parent, label, var_name, width=8, default="", values=None):
        """创建工具栏项的辅助方法"""
        ttk.Label(parent, text=label).pack(side=tk.LEFT, padx=(0, 3))
        setattr(self, var_name, tk.StringVar(value=default))
        combo = ttk.Combobox(parent, textvariable=getattr(self, var_name),
                            width=width, state="readonly")
        if values:
            combo['values'] = values
        combo.pack(side=tk.LEFT, padx=(0, 8))
        return combo

    # ==================== 串口操作 ====================

    def _refresh_ports(self):
        """刷新串口列表"""
        ports = list(serial.tools.list_ports.comports())
        port_list = [f"{p.device} ({p.description})" for p in ports]
        self.port_combo['values'] = port_list
        if port_list and not self.port_var.get():
            self.port_combo.current(0)

    def toggle_port(self):
        if not self.is_open:
            self._open_port()
        else:
            self._close_port()

    def _open_port(self):
        try:
            port_str = self.port_var.get().split()[0]
            parity_map = {"None": serial.PARITY_NONE, "Odd": serial.PARITY_ODD,
                         "Even": serial.PARITY_EVEN}
            stop_map = {"1": serial.STOPBITS_ONE, "1.5": serial.STOPBITS_ONE_POINT_FIVE,
                       "2": serial.STOPBITS_TWO}

            self.serial_port = serial.Serial(
                port=port_str,
                baudrate=int(self.baud_var.get()),
                bytesize=int(self.databits_var.get()),
                parity=parity_map.get(self.parity_var.get(), serial.PARITY_NONE),
                stopbits=stop_map.get(self.stopbits_var.get(), serial.STOPBITS_ONE),
                timeout=0.05,
            )
            self.is_open = True
            self.receive_running = True
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()

            self.open_btn.config(text="❌ 关闭串口", bg=self.colors["error"])
            self.status_label.config(text=f"● {port_str}", foreground=self.colors["success"])
            self._append_recv(f"[{self._now()}] 已打开 {port_str}\n")

        except Exception as e:
            messagebox.showerror("错误", f"打开失败:\n{e}")

    def _close_port(self, force=False):
        try:
            self.receive_running = False
            self.timer_running = False
            if not force:
                time.sleep(0.15)
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
            self.is_open = False
            self.serial_port = None

            self.open_btn.config(text="🔌 打开串口", bg=self.colors["success"])
            self.status_label.config(text="● 未连接", foreground=self.colors["error"])
            self._append_recv(f"[{self._now()}] 串口已关闭\n")

            # 重置定时
            self.timer_var.set(False)
        except Exception:
            pass

    def _receive_loop(self):
        while self.receive_running:
            try:
                if self.serial_port and self.serial_port.in_waiting > 0:
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    if data:
                        self._handle_received(data)
            except (serial.SerialException, OSError):
                break
            time.sleep(0.005)

    def _handle_received(self, data):
        ts = f"[{self._now()}] " if self.recv_timestamp_var.get() else ""
        if self.recv_hex_var.get():
            text = ts + data.hex(" ") + "\n"
        else:
            try:
                text = ts + data.decode("utf-8", errors="replace") + "\n"
            except Exception:
                text = ts + repr(data) + "\n"
        self._append_recv(text)

    def _append_recv(self, text):
        def do_append():
            self.recv_text.config(state=tk.NORMAL)
            self.recv_text.insert(tk.END, text)
            if self.auto_scroll_var.get():
                self.recv_text.see(tk.END)
            self.recv_text.config(state=tk.DISABLED)
            self.recv_count += len(text.encode("utf-8"))
            self._update_stats()
        self.root.after(0, do_append)

    # ==================== 发送操作 ====================

    def send_data(self):
        if not self.is_open or not self.serial_port:
            messagebox.showwarning("提示", "请先打开串口")
            return

        raw = self.send_text.get(1.0, tk.END).rstrip("\n").strip("\r")
        if not raw:
            return

        # 记录到历史
        if raw not in self.send_history:
            self.send_history.append(raw)
            if len(self.send_history) > 50:
                self.send_history.pop(0)
        self.history_idx = len(self.send_history)

        try:
            # 处理结尾符
            end_char = ""
            el = self.endline_var.get()
            if el == "\\n":
                end_char = "\n"
            elif el == "\\r\\n":
                end_char = "\r\n"
            elif el == "\\r":
                end_char = "\r"

            if self.send_hex_var.get():
                hex_clean = "".join(raw.split())
                data = bytes.fromhex(hex_clean) if hex_clean else b""
                if end_char:
                    data += end_char.encode()
            else:
                data = (raw + end_char).encode("utf-8")

            self.serial_port.write(data)
            self.send_count += len(data)
            self._update_stats()

            # 回显
            ts = f"[{self._now()}] " if self.timestamp_var.get() else ""
            display_raw = raw.replace("\n", "\\n").replace("\r", "\\r")
            if self.send_hex_var.get() or any(b > 127 for b in data):
                echo = ts + f">>> {data.hex(' ')}\n"
            else:
                echo = ts + f">>> {display_raw}\n"
            self._append_recv(echo)

        except ValueError:
            messagebox.showerror("错误", "HEX格式错误!\n示例: 01 02 ff aa")
        except Exception as e:
            messagebox.showerror("错误", f"发送失败:\n{e}")

    def _quick_send(self, cmd):
        self.send_text.delete(1.0, tk.END)
        self.send_text.insert(tk.END, cmd)
        self.send_data()

    def _send_file(self):
        """发送文件内容"""
        path = filedialog.askopenfilename(
            title="选择要发送的文件",
            filetypes=[("所有文件", "*.*"), ("文本文件", "*.txt"), ("HEX文件", "*.hex *.bin")]
        )
        if not path:
            return

        try:
            with open(path, "rb") as f:
                data = f.read()

            if not self.is_open:
                messagebox.showwarning("提示", "请先打开串口")
                return

            self.serial_port.write(data)
            self.send_count += len(data)
            self._update_stats()
            self._append_recv(f"[{self._now()}] >>> [文件] {os.path.basename(path)} "
                             f"({len(data)} bytes)\n")
            messagebox.showinfo("完成", f"已发送 {os.path.basename(path)}, 共 {len(data)} bytes")
        except Exception as e:
            messagebox.showerror("错误", f"发送文件失败:\n{e}")

    def clear_recv(self):
        self.recv_text.config(state=tk.NORMAL)
        self.recv_text.delete(1.0, tk.END)
        self.recv_text.config(state=tk.DISABLED)

    def save_log(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本", "*.txt"), ("日志", "*.log"), ("全部", "*.*")],
            initialfile=f"tbserial_{datetime.now():%Y%m%d_%H%M%S}.txt"
        )
        if path:
            content = self.recv_text.get(1.0, tk.END)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("成功", f"已保存到:\n{path}")

    # ==================== 定时发送 ====================

    def toggle_timer(self):
        if self.timer_var.get():
            interval_ms = self.timer_entry.get().strip()
            if not interval_ms or not interval_ms.isdigit() or int(interval_ms) < 50:
                self.timer_var.set(False)
                messagebox.showwarning("提示", "间隔需 >= 50ms 的整数")
                return
            self.timer_running = True
            threading.Thread(target=_timer_loop, args=(int(interval_ms), self),
                           daemon=True).start()
        else:
            self.timer_running = False

    # ==================== 快捷命令管理 ====================

    def _edit_quick_cmds(self):
        """编辑快捷命令弹窗"""
        win = tk.Toplevel(self.root)
        win.title("编辑快捷命令")
        win.geometry("500x450")
        win.transient(self.root)
        win.grab_set()

        frame = tk.Frame(win, **self._dark_style())
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(frame, text="双击可修改，选中后按 Delete 或点击删除移除",
                 fg=self.colors["warning"], bg=self.colors["bg"],
                 font=("Microsoft YaHei UI", 8)).pack(anchor=tk.W, pady=(0, 5))

        listbox = tk.Listbox(frame, selectmode=tk.SINGLE, height=20,
                            bg=self.colors["text_area_bg"],
                            fg=self.colors["text_area_fg"],
                            selectbackground=self.colors["accent"],
                            font=("Consolas", 11), relief=tk.FLAT)
        for cmd in self.quick_commands:
            listbox.insert(tk.END, cmd)
        listbox.pack(fill=tk.BOTH, expand=True)

        def on_double_click(event):
            idx = listbox.curselection()
            if idx:
                old_val = listbox.get(idx[0])
                new_val = simpledialog.askstring("修改", "输入新命令:",
                                                initialvalue=old_val)
                if new_val is not None and new_val.strip():
                    listbox.delete(idx[0])
                    listbox.insert(idx[0], new_val.strip())

        def delete_selected():
            sel = listbox.curselection()
            if sel:
                listbox.delete(sel[0])

        listbox.bind("<Double-Button-1>", on_double_click)

        btn_bar = tk.Frame(frame, bg=self.colors["bg"])
        btn_bar.pack(fill=tk.X, pady=(8, 0))
        tk.Button(btn_bar, text="删除选中", command=delete_selected,
                  bg=self.colors["btn_bg"], fg=self.colors["fg"],
                  relief=tk.FLAT, font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT)
        tk.Button(btn_bar, text="上移", command=lambda: _move(listbox, -1),
                  bg=self.colors["btn_bg"], fg=self.colors["fg"],
                  relief=tk.FLAT, font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_bar, text="下移", command=lambda: _move(listbox, 1),
                  bg=self.colors["btn_bg"], fg=self.colors["fg"],
                  relief=tk.FLAT, font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT, padx=5)

        def save_and_close():
            self.quick_commands = listbox.get(0, tk.END)
            self._save_quick_commands()
            self._rebuild_quick_buttons()
            win.destroy()

        tk.Button(btn_bar, text="✓ 保存", command=save_and_close,
                  bg=self.colors["success"], fg="#1e1e2e",
                  font=("Microsoft YaHei UI", 9, "bold"),
                  relief=tk.FLAT, width=8).pack(side=tk.RIGHT)

    def _add_quick_cmd(self):
        val = simpledialog.askstring("添加命令", "输入新的快捷命令:")
        if val and val.strip():
            self.quick_commands.append(val.strip())
            self._save_quick_commands()
            self._rebuild_quick_buttons()

    def _rebuild_quick_buttons(self):
        """重建快捷命令按钮（需要找到快捷命令区域并刷新）"""
        pass  # 需要重启生效，或者后续可以改成动态刷新

    # ==================== 字体 & 显示 ====================

    def _change_font(self, size):
        self.recv_font_size = size
        self.recv_text.configure(font=("Consolas", size))
        self.font_size_lbl.config(text=f" {size} ")
        self._save_window_pos()

    def _update_stats(self):
        self.stats_label.config(text=f"Tx:{self.send_count} | Rx:{self.recv_count}")

    @staticmethod
    def _now():
        dt = datetime.now()
        return dt.strftime("%H:%M:%S.") + f"{dt.microsecond // 1000:03d}"

    def _show_about(self):
        messagebox.showinfo("关于",
            "TBSerial V2.0\n"
            "泰比特串口调试工具\n\n"
            "功能:\n"
            "- 串口收发 (ASCII/HEX)\n"
            "- 时间戳 / 定时发送\n"
            "- 快捷命令 / 文件发送\n"
            "- 日志保存\n\n"
            "快捷键:\n"
            "- Enter/Ctrl+Enter: 发送\n"
            "- F5: 刷新端口\n"
            "- ESC: 清空输入框")

    def _show_shortcuts(self):
        messagebox.showinfo("快捷键",
            "Enter / Ctrl+Enter  →  发送数据\n"
            "ESC               →  清空输入框\n"
            "F5                →  刷新串口列表\n"
            "A+/-              →  调大/调小接收区字体")

    def _dark_style(self):
        return dict(bg=self.colors["bg"], fg=self.colors["fg"])

    def run(self):
        self.root.mainloop()


# ==================== 辅助函数 ====================

def _timer_loop(interval_ms, app):
    while app.timer_running:
        app.root.after(0, app.send_data)
        time.sleep(interval_ms / 1000)


def _move(listbox, direction):
    """移动列表项上下位置"""
    sel = listbox.curselection()
    if not sel:
        return
    idx = sel[0]
    new_idx = idx + direction
    if new_idx < 0 or new_idx >= listbox.size():
        return
    val = listbox.get(idx)
    listbox.delete(idx)
    listbox.insert(new_idx, val)
    listbox.selection_set(new_idx)


if __name__ == "__main__":
    app = TBSerial()
    app.run()
