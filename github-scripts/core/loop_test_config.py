# -*- coding: utf-8 -*-
"""
蓝牙综测自动化 - loop_test_config.py
按照流程图执行: 触发 → 等待40s → 滑动收集 → 解析 → 记录日志 → 循环
"""
import sys, os, time, subprocess, re, json
from datetime import datetime

# ============================================================
# 配置 (优先读 config.json, 否则用默认值)
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")

DEFAULTS = {
    "adb_path": "C:/platform-tools/adb.exe",
    "device_serial": "30e1ddc6",
    "tid": "863499087071635",
    "trigger_x": 417,
    "trigger_y": 2141,
    "confirm_x": 849,
    "confirm_y": 1388,
    "wait_seconds": 40,
    "slide_count": 8,
    "slide_pixels": 500,
    "slide_x_center": 540,
    "slide_start_y": 1700,
    "slide_duration_ms": 500,
    "cycle_interval": 60,
    "log_file": r"C:\Users\Administrator\Desktop\test_loop_log.txt",
    "log_dir": r"D:\110\logs"
}

def load_config():
    config = dict(DEFAULTS)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config.update(json.load(f))
        except Exception as e:
            print(f"[WARN] config.json 读取失败: {e}")
    return config

CFG = load_config()

ADB = CFG["adb_path"]
DEVICE = f"-s {CFG['device_serial']}"
LOG_FILE = CFG["log_file"]
os.makedirs(CFG["log_dir"], exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# ============================================================
# 日志
# ============================================================
def log(msg, to_file=True):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    if to_file:
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(line + '\n')
        except:
            pass

# ============================================================
# ADB 操作
# ============================================================
def adb_shell(cmd):
    r = subprocess.run(f"{ADB} {DEVICE} {cmd}", shell=True, capture_output=True)
    return (r.stdout + b'\n' + r.stderr).decode('utf-8', errors='replace').strip()

def adb_tap(x, y):
    adb_shell(f"input tap {x} {y}")

def adb_swipe(x1, y1, x2, y2, duration=500):
    adb_shell(f"input swipe {x1} {y1} {x2} {y2} {duration}")

def check_device():
    """检测设备是否连接"""
    r = adb_shell("get-state")
    return r.strip() == "device"

def dump_ui():
    """Dump UI XML"""
    dump_path = os.path.join(CFG["log_dir"], f"ui_dump.xml")
    adb_shell("uiautomator dump /sdcard/ui.xml")
    adb_shell(f"pull /sdcard/ui.xml {dump_path}")
    if os.path.exists(dump_path):
        with open(dump_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ''

def parse_results(xml):
    """从XML解析测试结果"""
    results = {}
    for m in re.finditer(r'text="([^"]*)"', xml):
        text = m.group(1)
        # 解析 "测试结果: XXX-成功/失败"
        match = re.match(r'测试结果:\s*(.+?)-(成功|失败)', text)
        if match:
            name, status = match.group(1), match.group(2)
            results[name] = status
        # 解析 "正在进行: XXX"
        match = re.match(r'正在进行:\s*(.*)', text)
        if match:
            name = match.group(1)
            if name not in results:
                results[name] = '进行中'
    return results

def collect_results():
    """滑动收集所有测试结果"""
    all_results = {}
    
    # 第1次: 当前屏幕
    xml = dump_ui()
    all_results.update(parse_results(xml))
    
    x = CFG["slide_x_center"]
    start_y = CFG["slide_start_y"]
    pixels = CFG["slide_pixels"]
    dur = CFG["slide_duration_ms"]
    
    # 向下滑动收集
    for i in range(CFG["slide_count"]):
        adb_swipe(x, start_y, x, start_y - pixels, dur)
        time.sleep(0.5)
        xml = dump_ui()
        new_items = parse_results(xml)
        added = {k: v for k, v in new_items.items() if k not in all_results}
        all_results.update(added)
    
    return all_results

def trigger_test():
    """触发测试: 点击输入编号 -> 确认"""
    log("  [Click] 输入编号 (%d, %d)" % (CFG["trigger_x"], CFG["trigger_y"]))
    adb_tap(CFG["trigger_x"], CFG["trigger_y"])
    time.sleep(2)
    log("  [Click] 确认 (%d, %d)" % (CFG["confirm_x"], CFG["confirm_y"]))
    adb_tap(CFG["confirm_x"], CFG["confirm_y"])
    time.sleep(1)

# ============================================================
# 主循环
# ============================================================
def main():
    log("=" * 60)
    log("  蓝牙综测自动化启动 (loop_test_config.py)")
    log(f"  设备: {CFG['tid']}  |  ADB: {CFG['device_serial']}")
    log(f"  等待: {CFG['wait_seconds']}s  |  滑动: {CFG['slide_count']}次  |  周期: {CFG['cycle_interval']}s")
    log("=" * 60)
    
    # 1. 启动ADB服务
    log("启动 ADB 服务...")
    subprocess.run(f"{ADB} start-server", shell=True, capture_output=True)
    
    # 2. 检测设备
    log("检测设备连接...")
    while not check_device():
        log("  设备未连接，5秒后重试...", to_file=False)
        time.sleep(5)
    log("  设备已连接")
    
    # 3. 主循环
    round_num = 0
    total_ok = 0
    total_ng = 0
    
    try:
        while True:
            round_num += 1
            round_start = time.time()
            
            log(f"\n{'#' * 50}")
            log(f"  第 {round_num} 轮 开始")
            log(f"{'#' * 50}")
            
            # Step 1: 触发综测
            trigger_test()
            
            # Step 2: 等待测试完成
            log(f"  [Wait] 等待 {CFG['wait_seconds']}s ...")
            time.sleep(CFG["wait_seconds"])
            
            # Step 3: 滑动收集结果
            log(f"  [Collect] 滑动 {CFG['slide_count']} 次收集结果...")
            results = collect_results()
            log(f"  [Collect] 收集到 {len(results)} 个测试项")
            
            # Step 4: 解析结果
            log(f"  [Parse] 解析结果...")
            success = []
            fail = []
            running = []
            info = []
            for name, status in sorted(results.items()):
                if status == '成功':
                    success.append(name)
                elif status == '失败':
                    fail.append(name)
                elif status == '进行中':
                    running.append(name)
                else:
                    info.append(f"{name}={status}")
            
            round_ok = len(success)
            round_ng = len(fail)
            total_ok += round_ok
            total_ng += round_ng
            
            # Step 5: 记录日志
            elapsed = time.time() - round_start
            log("-" * 40)
            log(f"  第 {round_num} 轮 完成 (耗时: {elapsed:.1f}s)")
            log(f"  [OK] 成功: {round_ok}  失败: {round_ng}  进行中: {len(running)}")
            log(f"  [Sum] 累计成功: {total_ok}  累计失败: {total_ng}")
            
            for name in success:
                log(f"    [PASS] {name}")
            for name in fail:
                log(f"    [FAIL] {name}")
            for name in running:
                log(f"    [RUNNING] {name}")
            for item in info:
                log(f"    [INFO] {item}")
            log("-" * 40)
            
            # 等待下一轮 (补齐到 cycle_interval)
            remaining = CFG["cycle_interval"] - elapsed
            if remaining > 0:
                log(f"  等待 {remaining:.0f}s 进入下一轮...", to_file=False)
                time.sleep(remaining)
            
    except KeyboardInterrupt:
        log("\n[STOP] 用户手动停止")
    except Exception as e:
        log(f"\n[ERROR] 异常: {e}")
    
    log(f"\n{'=' * 60}")
    log(f"  测试结束: {round_num} 轮")
    log(f"  累计: 成功 {total_ok}  失败 {total_ng}")
    log(f"{'=' * 60}")


if __name__ == "__main__":
    main()
