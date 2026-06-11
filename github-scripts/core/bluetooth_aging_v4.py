# -*- coding: utf-8 -*-
"""
蓝牙/网络老化测试工具 v4.0
支持手动登录模式（复制浏览器Cookie）
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import requests
import random
import json
from datetime import datetime

class BluetoothAgingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("蓝牙/网络老化测试工具 v4.0")
        self.root.geometry("700x750")
        
        # 设备信息
        self.device_id = tk.StringVar(value="867334078538316")
        self.ble_tid = tk.StringVar(value="sdfs")
        self.device_key = tk.StringVar(value="sdfs")
        self.plain_text = tk.StringVar(value="sdfs")
        
        # Cookie登录（网络老化用）
        self.cookie_str = tk.StringVar(value="")
        self.platform_ip = tk.StringVar(value="118.190.82.240")  # 用户浏览器看到的IP
        
        # 测试参数
        self.test_type = tk.StringVar(value="蓝牙老化")
        self.interval = tk.IntVar(value=10)
        self.max_cycles = tk.IntVar(value=1000)
        self.max_fail = tk.IntVar(value=1000)
        self.success_rate_req = tk.IntVar(value=95)
        self.enable_unlock = tk.BooleanVar(value=True)
        self.enable_lock = tk.BooleanVar(value=True)
        
        # 状态变量
        self.running = False
        self.paused = False
        self.current_count = 0
        self.success_count = 0
        self.fail_count = 0
        self.session = None
        self.logged_in = False
        
        self.create_widgets()
        
        # 日志平台地址
        self.platform_url = "http://ter.uqbike.cn:6800"
        
    def create_widgets(self):
        # 设备信息框
        device_frame = ttk.LabelFrame(self.root, text="设备信息", padding=10)
        device_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(device_frame, text="设备编号:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(device_frame, textvariable=self.device_id, width=20).grid(row=0, column=1, padx=5)
        ttk.Label(device_frame, text="calBleTid:").grid(row=0, column=2, padx=10)
        ttk.Entry(device_frame, textvariable=self.ble_tid, width=10).grid(row=0, column=3, padx=5)
        
        ttk.Label(device_frame, text="密钥:").grid(row=1, column=0, sticky=tk.W)
        ttk.Entry(device_frame, textvariable=self.device_key, width=10).grid(row=1, column=1, padx=5)
        ttk.Label(device_frame, text="明文:").grid(row=1, column=2, padx=10)
        ttk.Entry(device_frame, textvariable=self.plain_text, width=10).grid(row=1, column=3, padx=5)
        
        # 网络老化登录框
        login_frame = ttk.LabelFrame(self.root, text="网络老化 - Cookie登录", padding=10)
        login_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(login_frame, text="平台地址:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(login_frame, textvariable=self.platform_ip, width=20).grid(row=0, column=1, padx=5)
        ttk.Label(login_frame, text="(填浏览器看到的Remote Address IP)").grid(row=0, column=2, columnspan=2, sticky=tk.W)
        
        ttk.Label(login_frame, text="使用说明: 在浏览器登录后，按F12打开开发者工具，").grid(row=1, column=0, columnspan=4, sticky=tk.W)
        ttk.Label(login_frame, text="           找到 Network → 任意请求 → Headers → Cookie，复制整个Cookie值").grid(row=2, column=0, columnspan=4, sticky=tk.W)
        
        ttk.Label(login_frame, text="Cookie:").grid(row=3, column=0, sticky=tk.W)
        cookie_entry = ttk.Entry(login_frame, textvariable=self.cookie_str, width=50)
        cookie_entry.grid(row=3, column=1, columnspan=2, padx=5, pady=5)
        
        ttk.Button(login_frame, text="验证Cookie", command=self.verify_cookie).grid(row=3, column=3, padx=5)
        
        self.login_status_label = ttk.Label(login_frame, text="状态: 未登录", foreground="red")
        self.login_status_label.grid(row=4, column=0, columnspan=4, sticky=tk.W)
        
        # 测试参数框
        param_frame = ttk.LabelFrame(self.root, text="测试参数", padding=10)
        param_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(param_frame, text="测试类型:").grid(row=0, column=0, sticky=tk.W)
        ttk.Radiobutton(param_frame, text="蓝牙老化", variable=self.test_type, value="蓝牙老化").grid(row=0, column=1)
        ttk.Radiobutton(param_frame, text="网络老化", variable=self.test_type, value="网络老化").grid(row=0, column=2)
        
        ttk.Label(param_frame, text="间隔时间(秒):").grid(row=1, column=0, sticky=tk.W)
        ttk.Spinbox(param_frame, from_=1, to=60, textvariable=self.interval, width=8).grid(row=1, column=1, padx=5)
        
        ttk.Label(param_frame, text="循环次数:").grid(row=1, column=2, padx=10)
        ttk.Spinbox(param_frame, from_=1, to=10000, textvariable=self.max_cycles, width=8).grid(row=1, column=3, padx=5)
        
        ttk.Label(param_frame, text="最多失败次数:").grid(row=2, column=0, sticky=tk.W)
        ttk.Spinbox(param_frame, from_=1, to=10000, textvariable=self.max_fail, width=8).grid(row=2, column=1, padx=5)
        
        ttk.Label(param_frame, text="成功率要求(%):").grid(row=2, column=2, padx=10)
        ttk.Spinbox(param_frame, from_=0, to=100, textvariable=self.success_rate_req, width=8).grid(row=2, column=3, padx=5)
        
        ttk.Label(param_frame, text="测试项目:").grid(row=3, column=0, sticky=tk.W)
        ttk.Checkbutton(param_frame, text="解锁测试", variable=self.enable_unlock).grid(row=3, column=1)
        ttk.Checkbutton(param_frame, text="上锁测试", variable=self.enable_lock).grid(row=3, column=2)
        
        # 控制按钮
        btn_frame = ttk.Frame(self.root, padding=10)
        btn_frame.pack(fill=tk.X, padx=10)
        
        self.start_btn = ttk.Button(btn_frame, text="开始测试", command=self.start_test)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.pause_btn = ttk.Button(btn_frame, text="暂停", command=self.pause_test, state=tk.DISABLED)
        self.pause_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="停止", command=self.stop_test, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="保存日志", command=self.save_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="清空日志", command=self.clear_log).pack(side=tk.LEFT, padx=5)
        
        # 状态显示
        status_frame = ttk.LabelFrame(self.root, text="测试状态", padding=10)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="当前: 0  成功: 0  失败: 0  成功率: 0%", font=("Arial", 12, "bold"))
        self.status_label.pack()
        
        self.progress = ttk.Progressbar(status_frame, mode='determinate', maximum=100)
        self.progress.pack(fill=tk.X, pady=5)
        
        # 日志框
        log_frame = ttk.LabelFrame(self.root, text="日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
    def log(self, message):
        """添加日志"""
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{timestamp} {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
    def verify_cookie(self):
        """验证Cookie是否有效"""
        cookie_str = self.cookie_str.get().strip()
        if not cookie_str:
            messagebox.showwarning("警告", "请先输入Cookie")
            return
            
        # 获取用户输入的IP地址
        platform_ip = self.platform_ip.get().strip()
        if not platform_ip:
            messagebox.showwarning("警告", "请先输入平台IP地址")
            return
            
        self.log(f"正在验证Cookie... (连接 {platform_ip}:6800)")
        
        try:
            # 创建session并设置cookie
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Cookie': cookie_str,
                'Host': 'ter.uqbike.cn:6800'  # 关键：设置Host头
            })
            
            # 使用用户输入的IP地址
            self.platform_url = f"http://{platform_ip}:6800"
            
            # 尝试访问一个需要登录的页面
            test_url = f"{self.platform_url}/index.do"
            resp = self.session.get(test_url, timeout=10)
            
            if resp.status_code == 200 and ('登录' not in resp.text or '欢迎' in resp.text or '设备' in resp.text):
                self.logged_in = True
                self.login_status_label.config(text="状态: Cookie有效 ✓", foreground="green")
                self.log("Cookie验证成功！可以开始网络老化测试")
            else:
                self.logged_in = False
                self.login_status_label.config(text="状态: Cookie无效或已过期", foreground="red")
                self.log("Cookie验证失败，请重新获取Cookie")
                
        except Exception as e:
            self.logged_in = False
            self.login_status_label.config(text=f"状态: 验证失败 - {str(e)[:30]}", foreground="red")
            self.log(f"Cookie验证失败: {e}")
            
    def start_test(self):
        """开始测试"""
        if self.test_type.get() == "网络老化" and not self.logged_in:
            messagebox.showwarning("警告", "网络老化需要先验证Cookie")
            return
            
        self.running = True
        self.paused = False
        self.current_count = 0
        self.success_count = 0
        self.fail_count = 0
        
        self.start_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.NORMAL)
        
        test_type = self.test_type.get()
        self.log(f"开始{test_type}...")
        
        # 启动测试线程
        thread = threading.Thread(target=self.run_test)
        thread.daemon = True
        thread.start()
        
    def run_test(self):
        """运行测试"""
        test_type = self.test_type.get()
        
        while self.running and self.current_count < self.max_cycles.get():
            if self.paused:
                time.sleep(0.1)
                continue
                
            self.current_count += 1
            
            # 执行解锁测试
            if self.enable_unlock.get():
                success, msg = self.execute_command("unlock", test_type)
                if success:
                    self.success_count += 1
                else:
                    self.fail_count += 1
                self.log(f"[{self.current_count}] 解锁: {msg}")
                self.update_status()
                
                if self.fail_count >= self.max_fail.get():
                    self.log(f"失败次数达到阈值 {self.max_fail.get()}，测试停止")
                    break
                    
                time.sleep(self.interval.get())
                
            if not self.running:
                break
                
            # 执行上锁测试
            if self.enable_lock.get():
                success, msg = self.execute_command("lock", test_type)
                if success:
                    self.success_count += 1
                else:
                    self.fail_count += 1
                self.log(f"[{self.current_count}] 上锁: {msg}")
                self.update_status()
                
                if self.fail_count >= self.max_fail.get():
                    self.log(f"失败次数达到阈值 {self.max_fail.get()}，测试停止")
                    break
                    
                time.sleep(self.interval.get())
                
        self.stop_test()
        self.log("测试完成")
        
    def execute_command(self, cmd_type, test_type):
        """执行指令"""
        if test_type == "蓝牙老化":
            # 蓝牙老化 - 模拟模式
            time.sleep(random.uniform(0.5, 1.5))
            success = random.random() < 0.95
            if success:
                return True, "成功 (模拟)"
            else:
                return False, "失败 (模拟)"
        else:
            # 网络老化 - 真实HTTP请求
            return self.network_control(cmd_type)
            
    def network_control(self, cmd_type):
        """网络控制 - 通过日志平台API"""
        try:
            # 确定参数
            param_name = "11" if cmd_type == "unlock" else "1"  # 11=开锁, 1=关锁
            
            # 发送控制指令
            control_url = f"{self.platform_url}/terControl/sendControl.do"
            params = {
                'userCode': self.device_id.get(),
                'controlType': 'control',
                'paramName': param_name
            }
            
            resp = self.session.get(control_url, params=params, timeout=10)
            data = resp.json()
            
            if data.get('ret') != 1:
                return False, f"发送失败: {data}"
                
            serial_no = data.get('data')
            self.log(f"  指令已发送，流水号: {serial_no}")
            
            # 等待设备响应
            time.sleep(2)
            
            # 查询结果
            result_url = f"{self.platform_url}/terControl/getControlRet.do"
            max_retry = 10
            for i in range(max_retry):
                resp = self.session.get(result_url, params={'serNO': serial_no}, timeout=10)
                result = resp.json()
                
                rsp = result.get('rsp')
                if rsp == 1:
                    return True, "成功"
                elif rsp == 0:
                    return False, "设备返回失败"
                elif rsp == 2:
                    return False, "设备运动中"
                elif rsp == 3:
                    return False, "外接电源不在位"
                elif rsp == -1:
                    # 初始状态，继续等待
                    time.sleep(1)
                else:
                    return False, f"未知状态: {rsp}"
                    
            return False, "等待超时"
            
        except Exception as e:
            return False, f"异常: {str(e)}"
            
    def update_status(self):
        """更新状态显示"""
        total = self.success_count + self.fail_count
        rate = (self.success_count / total * 100) if total > 0 else 0
        self.status_label.config(text=f"当前: {self.current_count}  成功: {self.success_count}  失败: {self.fail_count}  成功率: {rate:.1f}%")
        self.progress['value'] = (self.current_count / self.max_cycles.get()) * 100
        
    def pause_test(self):
        """暂停/继续测试"""
        self.paused = not self.paused
        self.pause_btn.config(text="继续" if self.paused else "暂停")
        self.log("测试已暂停" if self.paused else "测试已继续")
        
    def stop_test(self):
        """停止测试"""
        self.running = False
        self.paused = False
        self.start_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED, text="暂停")
        self.stop_btn.config(state=tk.DISABLED)
        
    def save_log(self):
        """保存日志"""
        from datetime import datetime
        filename = f"D:/110/aging_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        self.log_text.config(state=tk.NORMAL)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(self.log_text.get('1.0', tk.END))
        self.log_text.config(state=tk.DISABLED)
        self.log(f"日志已保存到: {filename}")
        
    def clear_log(self):
        """清空日志"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete('1.0', tk.END)
        self.log_text.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = BluetoothAgingApp(root)
    root.mainloop()