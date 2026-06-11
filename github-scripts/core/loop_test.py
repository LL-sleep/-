# -*- coding: utf-8 -*-
"""
===============================================================================
综测循环自动化脚本
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
流程: 触发测试 → 等待完成 → 滑动屏幕收集结果 → 写入日志 → 循环下一轮
依赖: ADB (Android Debug Bridge) + USB连接
适用: Android设备综测APP（蓝牙/GPS/GSM/网络等32+项检测）
===============================================================================
"""
import subprocess, re, time, json, os
from datetime import datetime

# ============================================================================
# 第一部分: 全局配置
# 修改这些变量即可适配不同设备/环境
# ============================================================================

# ADB工具路径 — Android调试桥，用于控制手机
ADB = r"C:\platform-tools\adb.exe"

# 设备串号 — 通过 `adb devices` 查看，-s 指定操作哪台设备
DEVICE = "-s 30e1ddc6"

# 终端TID — 设备的唯一标识，写入日志用于区分
TID = "863499087271599"

# 临时文件路径 — ADB从手机拉取的UI布局文件存在这里
DUMP = r"D:\110\ui_dump.xml"

# 日志文件 — 综测结果写入桌面（方便查看）
# 注意: Windows路径含 \U、\D 等会被误认为转义序列，必须用 r"..."
LOG_FILE = r"C:\Users\16280\Desktop\综测结果_863499087271599.txt"

# dump备份目录 — 每轮dump文件存档（当前未使用，预留）
DUMP_DIR = r"D:\110\dumps"

# ============================================================================
# 配置文件加载
# 如果存在 config.json 则读取，覆盖下面的默认值
# 配置文件格式: {"trigger_x":417, "trigger_y":2141, "wait_seconds":45, ...}
# ============================================================================

CONFIG_FILE = "D:/WD/110/config.json"
CFG = {
    # 触发按钮坐标 — 屏幕上的"开始测试"按钮位置 (x, y 像素)
    "trigger_x": 417, "trigger_y": 2141,
    # 确认按钮坐标 — 弹出确认框后的"确认"按钮位置
    "confirm_x": 849, "confirm_y": 1388,
    # 等待时长(秒) — 综测执行大约需要45秒完成所有32项检测
    "wait_seconds": 45,
    # 滑动次数(保留字段, 新版已改为动态退出)
    "slide_count": 8,
    # 循环周期(秒) — 每轮测试的总时间上限，到点自动开始下一轮
    "cycle_interval": 60
}

# 如果配置文件存在，加载并覆盖默认值
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        CFG.update(json.load(f))


# ============================================================================
# 第二部分: ADB 基础操作函数
# ============================================================================

def adb(cmd):
    """
    执行一条ADB命令并返回输出文本
    示例: adb("shell input tap 417 2141")  →  点击屏幕坐标(417,2141)
    """
    r = subprocess.run(f"{ADB} {DEVICE} {cmd}", shell=True, capture_output=True)
    return r.stdout.decode('utf-8', errors='replace')


def dump_and_read():
    """
    导出手机当前屏幕的UI布局 → 拉到电脑 → 读取内容
    步骤:
      1. adb shell uiautomator dump  →  手机生成 /sdcard/ui.xml
      2. adb pull                    →  拉到电脑 D:/110/ui_dump.xml
      3. 读取文件内容返回
    返回: XML字符串，里面每个元素都带有 text="..." 属性
    """
    adb("shell uiautomator dump /sdcard/ui.xml")
    adb(f"pull /sdcard/ui.xml {DUMP}")
    try:
        with open(DUMP, 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return ''  # 文件读取失败返回空字符串，避免脚本崩溃


# ============================================================================
# 第三部分: 核心逻辑 — 收集测试结果
# ============================================================================

def collect_all():
    """
    滚动屏幕逐屏收集所有测试结果
    ───────────────────────────────────────────────────────────────
    原理:
      - 综测结果列表很长（30+项），一屏看不完
      - 先滚到列表最顶部
      - 然后逐屏向下滑，每滑一次就dump一次
      - 从XML中提取所有 text="测试结果:xxx" 和 text="正在进行:xxx"
      - 连续3屏没有新内容就认为已经到底，自动停止
      - 最多50屏兜底，防止死循环
    ───────────────────────────────────────────────────────────────
    返回: 去重后的结果列表，保持首次出现的顺序
    """
    seen = {}       # 已收集的去重字典 {文本: True}
    all_items = []  # 收集到的所有结果（保持时间顺序）

    # ---- 第1步: 快速滚到最顶部 ----
    # 从下往上快速滑15次（每次只滑动很少距离+极短间隔），确保到达列表顶部
    for _ in range(15):
        adb("shell input swipe 540 700 540 1500 100")
        time.sleep(0.05)

    # ---- 第2步: 逐屏向下滑动收集 ----
    no_new_count = 0     # 连续无新增计数
    MAX_ROUNDS = 50      # 最多50屏兜底

    for round_num in range(MAX_ROUNDS):
        before = len(seen)  # 本屏收集前已有的数量

        # 导出当前屏幕布局并解析
        xml = dump_and_read()
        # 正则匹配所有 text="xxx" 的内容
        for m in re.finditer(r'text="([^"]+)"', xml):
            t = m.group(1)
            # 只收集"测试结果"和"正在进行"两类文本
            if ('测试结果' in t or '正在进行' in t) and t not in seen:
                seen[t] = True
                all_items.append(t)

        # 判断是否应该停止: 连续3屏都没有新内容 → 到底了
        if len(seen) == before:
            no_new_count += 1
            if no_new_count >= 3:
                break       # 3屏无新增，退出
        else:
            no_new_count = 0  # 有新内容，重置计数

        # 向下翻一屏（从屏幕下半部滑到上半部，模拟手指上推）
        adb("shell input swipe 540 1500 540 700 300")
        time.sleep(0.3)

    return all_items


# ============================================================================
# 第四部分: 日志写入
# ============================================================================

def write_log(round_num, items):
    """
    将本轮收集的结果写入日志文件
    ───────────────────────────────────────────────────────────────
    参数:
      round_num: 第几轮测试
      items:     collect_all() 返回的结果列表
    ───────────────────────────────────────────────────────────────
    日志格式:
      [第 X 次] - 2026-06-09 15:20
        设备: 863499087071635
      ----------------------------------------
      [PASS] 蓝牙连接测试结果: 成功
      [PASS] GPS测试结果: 成功
      [FAIL] 网络测试结果: 失败
      [RUN]  正在进行:锁电机测试
      ----------------------------------------
        统计: 成功 20 / 失败 1 / 进行中 3
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 按前缀分类: 区分"正在进行"和"测试结果"
    # 测试结果再细分: 成功 / 失败未找到 / 其他(INFO)
    running = [x for x in items if x.startswith("正在进行:")]
    passed  = [x for x in items if x.startswith("测试结果:") and "成功" in x]
    failed  = [x for x in items if x.startswith("测试结果:") and ("失败" in x or "未找到" in x)]
    info    = [x for x in items if x.startswith("测试结果:") and "成功" not in x and "失败" not in x and "未找到" not in x]

    # 拼接日志文本
    log = f"\n========================================\n"
    log += f"[第 {round_num} 次] - {ts}\n"
    log += "========================================\n"
    log += f" 设备: {TID}\n"
    log += "----------------------------------------\n"

    # 按收集的原始顺序逐条输出, 保证时间顺序不乱
    for item in items:
        if item in running:
            log += f"[RUN]  {item}\n"          # 还在跑
        elif item in passed:
            name = item.replace("测试结果: ", "")
            log += f"[PASS] {name}\n"          # 通过了
        elif item in failed:
            name = item.replace("测试结果: ", "")
            log += f"[FAIL] {name}\n"          # 失败了
        elif item in info:
            name = item.replace("测试结果: ", "")
            log += f"[INFO] {name}\n"          # 其他信息

    # 统计摘要
    log += "----------------------------------------\n"
    log += f"  统计: 成功 {len(passed)} / 失败 {len(failed)} / 进行中 {len(running)}\n"
    log += "========================================\n"

    # 同时输出到控制台 + 写入文件
    print(log)
    try:
        # 自动创建日志目录（如果不存在）
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        # 追加模式写入
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log)
    except:
        pass  # 写文件失败不中断脚本


# ============================================================================
# 第五部分: 主循环
# ============================================================================

def main():
    """
    主函数 — 无限循环执行综测
    ───────────────────────────────────────────────────────────────
    每轮流程:
      t0 = 当前时间
      ① 触发: 点击"开始测试" → 点"确认"
      ② 等待: 等45秒让综测跑完
      ③ 收集: 滑动屏幕把所有结果dump出来
      ④ 记录: 分类统计写入日志
      ⑤ 补齐: 如果本轮耗时不到60秒, 补等剩余时间
      → 回到 ①
    ───────────────────────────────────────────────────────────────
    停止: Ctrl+C 中断
    """
    print(f"\n综测循环启动 - {TID}")
    print(f"日志: {LOG_FILE}")

    # 启动时清空旧日志（避免和之前的测试结果混在一起）
    try:
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            f.write('')
        print("旧日志已清除\n")
    except:
        pass

    round_num = 0

    try:
        # 无限循环, 直到用户按 Ctrl+C
        while True:
            round_num += 1
            t0 = time.time()  # 记录本轮开始时间

            # ---- ① 触发测试 ----
            # 点击两个坐标: 先点"开始测试", 等2秒弹窗出来, 再点"确认"
            print(f"[第{round_num}轮] 触发测试...")
            adb(f"shell input tap {CFG['trigger_x']} {CFG['trigger_y']}")
            time.sleep(2)
            adb(f"shell input tap {CFG['confirm_x']} {CFG['confirm_y']}")

            # ---- ② 等待测试完成 ----
            # 综测APP需要约45秒跑完全部检测项
            wait = CFG["wait_seconds"]
            print(f"[第{round_num}轮] 等待 {wait}s...")
            time.sleep(wait)

            # ---- ③ 收集结果 ----
            # 滑动屏幕 + dump UI, 提取所有测试项的文本
            print(f"[第{round_num}轮] 收集结果...")
            items = collect_all()
            print(f"[第{round_num}轮] 收集 {len(items)} 项")

            # ---- ④ 写入日志 ----
            write_log(round_num, items)

            # ---- ⑤ 周期补齐 ----
            # 如果本轮还没到60秒, 补等剩余时间, 确保每轮间隔均匀
            elapsed = time.time() - t0
            remain = CFG["cycle_interval"] - elapsed
            if remain > 0:
                time.sleep(remain)

    except KeyboardInterrupt:
        # Ctrl+C 正常退出
        print(f"\n停止，共 {round_num} 轮")


# ============================================================================
# 入口
# ============================================================================
if __name__ == "__main__":
    main()
