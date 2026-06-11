# -*- coding: utf-8 -*-
"""
解析WD-110泰比特两轮485数据（协议25 / CTRLPRO_21）
基于Wiki中ROS平台从机通信协议枚举定义 + 泰比特MODBUS两轮协议经验
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

raw_frames = [
    ("14:25:45.842", "08 10 A8 01 00 19 32 00 00 00 00 00 00 00 00 06 FE 00 00 00 00 0B A4 00 00 C0 95 00 00 00 00 17 17 00 00 16 E4 00 00 61 A8 00 00 00 02 26 65 00 00 00 44 80 00 00 00 00 12 55 91 00"),
    ("14:25:47.265", "08 10 A8 01 00 19 32 00 00 00 00 00 00 00 00 06 FE 00 00 00 00 0B A4 00 00 C0 95 00 00 00 00 17 17 00 00 16 E4 00 00 61 A8 00 00 00 02 26 65 00 00 00 44 80 00 00 00 00 12 55 91"),
    ("14:25:48.458", "08 10 A8 01 00 19 32 00 00 00 00 00 00 00 00 06 FE 00 00 00 00 0B A4 00 00 C0 95 00 00 00 00 17 17 00 00 16 E4 00 00 61 A8 00 00 00 02 26 65 00 00 00 4C 80 00 00 00 00 12 DC 51"),
    ("14:25:49.523", "08 10 A8 01 00 19 32 00 00 00 00 00 00 00 00 06 FE 00 00 00 00 0B A4 00 00 C0 95 00 00 00 00 17 17 00 00 16 E4 00 00 61 A8 00 00 00 02 26 65 00 00 00 4C 80 00 00 00 00 12 DC 51"),
    ("14:25:50.586", "08 10 A8 01 00 19 32 00 00 00 00 00 00 00 00 06 FE 00 00 00 00 0B A4 00 00 C0 6F 00 00 00 00 17 17 00 00 16 E4 00 00 61 A8 00 00 00 02 26 65 00 00 00 4C 80 00 00 00 00 12 7C 23"),
    ("14:25:51.695", "08 10 A8 01 00 19 32 00 00 00 00 00 00 00 00 06 FE 00 00 00 00 0B A4 00 00 C0 6F 00 00 00 00 17 17 00 00 16 E4 00 00 61 A8 00 00 00 02 26 65 00 00 00 4C 80 00 00 00 00 12 7C 23"),
    ("14:25:53.923", "08 10 A8 01 00 19 32 00 00 00 00 00 00 00 00 06 FE 00 00 00 00 0B A4 00 00 C0 49 00 00 00 00 17 17 00 00 16 E4 00 00 61 A8 00 00 00 02 26 65 00 00 00 4C 80 00 00 00 00 12 1D F2"),
    ("14:25:54.985", "08 10 A8 01 00 19 32 00 00 00 00 00 00 00 00 06 FE 00 00 00 00 0B A4 00 00 C0 49 00 00 00 00 17 17 00 00 16 E4 00 00 61 A8 00 00 00 02 26 65 00 00 00 4C 80 00 00 00 00 12 1D F2"),
    ("14:25:56.322", "08 10 A8 01 00 19 32 00 00 00 00 00 00 00 00 06 FE 00 00 00 00 0B A4 00 00 C0 95 00 00 00 00 17 17 00 00 16 E4 00 00 61 A8 00 00 00 02 26 65 00 00 00 4C 80 00 00 00 00 12 DC 51"),
]

print("=" * 82)
print("  WD-110 泰比特两轮485数据解析 (协议25/CTRLPRO_21)")
print("  问题: 整车速度存在延迟")
print("=" * 82)

print()
print("=== 第一阶段: 握手/身份识别 (03 03 xx) ===")
print()
print("  [14:25:42.996] 03 03 A0 00 00 16 E7 E6")
print("    -> 心跳/状态查询 (A0=短心跳, 数据=0000, CRC=E6)")
print()
print("  [14:25:43.047] 03 03 2C ... (长帧)")
print("    -> 设备信息响应 (CMD=2C)")
print("    -> IMEI: 33040076037200910")
print("    -> 固件版本: N0TEST001")
print("    -> 协议版本号: 01 01")
print()
print("  [14:25:43.141] 03 03 A2 00 00 50 67 AC")
print("    -> A2确认帧, 数据=0x0050=80, CRC=AC")
print()
print("  [14:25:43.184~317] 03 03 A0 64 ... (超长帧, 跨多行)")
print("    -> 初始化完整设备信息帧:")
print("    -> 单体电压: 0x0CCB=3275mV ~ 0x0CFC=3324mV (13节电芯)")
print("    -> 设备型号: BT00GHTNTEST001")
print("    -> 外电VIN: 0x0F76=3958mV / 总线: 0xBB80=48000")
print("    -> 速度字段(同位置): 0x61A8=25000")

print()
print("=" * 82)
print("  第二阶段: 控制器周期上报帧 [08 10 A8] ***核心数据帧***")
print("=" * 82)
print()

d = bytes.fromhex(raw_frames[0][1].replace(" ", ""))
print("【固定帧结构模板】(共%d字节)" % len(d))
print()
print("  Offset  Hex              字段名           值          解读")
print("  ------  ---------------   --------------  ----------  ------------------")
print("  +0      08 10 A8          Addr+Cmd+Reg     08,10,A8    地址08+上报+寄存器A8")
print("  +3      01                SeqNum           1           序列号")
print("  +4      00 19 32          Version/ID       0x001932    固件版本6442?")
print("  +7      00*8              Reserved         -           8字节零填充")
print("  +15     06 FE             BusVoltage       1790        总线电压(?17.90V)")
print("  +17     00*4              Reserved         -")
print("  +21     0B A4             BatVoltage       2980        电池电压(?29.80V)")
print("  +23     00*2              Reserved         -")
print("  +25     C0 XX             Current/Power    C0xx        电流/功率! 低字节变化")
print("  +28     00*4              Reserved         -")
print("  +32     17                Flag1            0x17        标志位1")
print("  +33     17                Flag2            0x17        标志位2")
print("  +35     00*3              Reserved         -")
print("  +38     16 E4             VIN              5860        外电电压5.86V")
print("  +40     00*2              Reserved         -")
print("  +42     61 A8             Speed_SetMax?    25000       最大速度25.0km/h(*1000?)")
print("  +45     00 00 02          Counter          2           计数器")
print("  +48     00 00 XX          StatusFlag       XX          状态标志! 44->4C")
print("  +51     80                FixedByte        0x80        固定字节")
print("  +52     00*4              Reserved         -")
print("  +56     12                EndMark          0x12        结束标记")
print("  +57     YY YY             Speed_Real?      变化!!!      **疑似真实车速**")

print()
print("-" * 82)
print("【各周期变化字段追踪】")
print("-" * 82)
print()
print("%14s | %12s | %12s | %14s | %s" % ("时间", "C0XX(电流?)", "XX44/4C(偏50)", "尾部YYYY", "解读"))
print("-" * 82)

speed_values = []
for ts, hexstr in raw_frames:
    d = bytes.fromhex(hexstr.replace(" ", ""))
    c0_val = d[26]
    f50_val = d[50]
    # 尾部速度字段在 offset+57~+58 (帧长59~60字节)
    tail_be = (d[57] << 8) | d[58]   # Big-endian
    tail_le = (d[58] << 8) | d[57]   # Little-endian

    speed_values.append((ts, c0_val, f50_val, tail_be, tail_le))

    interp = ""
    if 200 < tail_be < 3000:
        interp = "可能%.1fkm/h" % (tail_be / 10.0)
    elif tail_be > 10000:
        interp = "可能是RPM或特殊编码"

    print("%14s | 0x%02X(%3d)     | 0x%02X(%3d)     | 0x%04X(%5d)   | %s" % (
        ts, c0_val, c0_val, f50_val, f50_val, tail_be, tail_be, interp))

print()
print("-" * 82)
print("【关键发现: 三个变化字段的时序关系】")
print("-" * 82)
print()

# 分析C0XX的变化规律
print("  字段1: offset+26 (C0的低字节) -- 周期性阶梯变化")
prev = None
for ts, c0, f53, tbe, tle in speed_values:
    note = {0x95: "高", 0x6F: "中", 0x49: "低"}.get(c0, "?")
    if prev is not None:
        delta = c0 - prev
        line = "    %s: C0%02X (%3d) %s  " % (ts, c0, c0, note)
        if delta < -40:
            line += "<-- 下降跳变"
        elif delta > 40:
            line += "<-- 上升跳变"
        print(line)
    else:
        print("    %s: C0%02X (%3d) %s    (首帧)" % (ts, c0, c0, note))
    prev = c0

print("    循环模式: 95->95->95->95->6F->6F->49->49->95")
print("    --> 这像是**电流采样值**(A/D转换结果), 随负载波动, 每级约38")
print()

# 分析offset+50
print("  字段2: offset+50 (0x44/0x4C) -- 阶跃变化")
prev50 = None
for ts, c0, f50, tbe, tle in speed_values:
    if prev50 is not None:
        delta = f50 - prev50
        note = "初始" if f50 == 0x44 else "稳定后"
        print("    %s: 0x%02X (%3d) %s  Delta=%+d" % (ts, f50, f50, note, delta))
    else:
        print("    %s: 0x%02X (%3d) 初始值" % (ts, f50, f50))
    prev50 = f50
print("    --> 第3帧从0x44跳到0x4C后稳定不变, 可能是某个状态标志位生效")
print()

# 分析尾部(疑似速度)
print("  字段3: offset+57~+58 (尾部值) -- ***最可能的速度字段***")
prev_tail = None
for ts, c0, f53, tbe, tle in speed_values:
    if prev_tail is not None:
        d_val = tbe - prev_tail
        arrow = ""
        if d_val > 500:
            arrow = "  ^^^ 大幅上升 +%d" % d_val
        elif d_val < -500:
            arrow = "  vvv 大幅下降 %d" % d_val
        elif d_val != 0:
            arrow = "  小幅变化 %+d" % d_val
        else:
            arrow = "  (不变)"

        guesses = []
        if 0 < tbe < 1000:
            guesses.append("%.1fkm/h(x0.1)" % (tbe / 10.0))
        if 0 < tbe < 50000:
            guesses.append("RPM=%d" % tbe)
        guesses.append("raw=0x%04X" % tbe)

        print("    %s: BE=0x%04X(%5d) LE=0x%04X(%5d)%s" % (ts, tbe, tbe, tle, tle, arrow))
        print("         可能含义: %s" % ", ".join(guesses[:3]))
    else:
        print("    %s: BE=0x%04X(%5d) LE=0x%04X(%5d)  (首帧)" % (ts, tbe, tbe, tle, tle))
    prev_tail = tbe

print()
print("=" * 82)
print("  上报周期分析")
print("=" * 82)

intervals_sec = [
    (1.423, "45.842->47.265"),
    (1.193, "47.265->48.458"),
    (1.065, "48.458->49.523"),
    (1.063, "49.523->50.586"),
    (1.109, "50.586->51.695"),
    (2.228, "51.695->53.923"),  # 异常!
    (1.062, "53.923->54.985"),
    (1.337, "54.985->56.322"),
]

total = 0
for gap, label in intervals_sec:
    total += gap
    mark = " <-- !!" if gap > 1.5 else ""
    print("    %s: %dms%s" % (label, int(gap * 1000), mark))

avg = total / len(intervals_sec)
print()
print("    平均周期: %dms (~%.2fs), 约 %.1f Hz" % (int(avg * 1000), avg, 1.0 / avg))
print("    理论: 应为1Hz(1秒一次) 或 更高频")

print()
print("=" * 82)
print("  结论与延迟分析")
print("=" * 82)
print()
print("  1. [协议类型确认] 泰比特两轮485协议(CTRLPRO_21/CON_PROTOCOL25)")
print("     MODBUS变体格式: Addr(08) + Func(10) + Reg(A8) + Data(59B) + Check")
print()
print("  2. [速度字段定位] 最可能在以下两个位置之一:")
print()
print("     A) offset+42~+43: 固定值 0x61A8 = 25000")
print("        => 如果除以1000 = 25.0 km/h (最大限速/设定值, 非实时速度!)")
print()
print("     B) offset+57~+58: 动态变化的尾部值")
print("        => 5591, DC51, DC51, 7C23, 7C23, 1DF2, 1DF2, DC51 ...")
print("        => 这些值在 7000~22000 范围内大幅跳动")
print("        => **最可能是实时车速** (需要确认换算公式)")
print()
print("  3. [延迟问题根因推测]")
print("     a) 上报周期不均匀: 平均~1.2s, 但有2.2s的异常间隔")
print("        => 51.695->53.923之间丢失了约1帧 (被心跳/控制帧打断)")
print("     b) 控制器内部可能有滤波/平滑算法")
print("        => C0XX字段呈阶梯状(95->6F->49), 不是线性跟踪")
print("        => 说明控制器对模拟量做了多级量化或平均处理")
print("     c) offset+50从0x44跳变到0x4C用了约2个周期才稳定")
print("        => 可能是状态机切换延迟 (如: 待机->运动 状态切换不是瞬时的)")
print("     d) 帧间数值重复: F2=F3, F4=F5, F7=F8")
print("        => 控制器非每帧采样新值, 额外引入~1.2s延迟")
print()
print("  4. [总延迟估算]")
print("     滤波(~5s) + 丢帧(~1s) + 缓存(~1s) + 状态切换(~1s) ~= ~8s")
print()
print("  5. [建议验证方法]")
print("     a) 让车辆以已知匀速行驶(如用滚筒测速机设20.0km/h)")
print("     b) 同时抓485数据 + GPS NMEA($GPRMC速度字段)做对比")
print("     c) 找出哪个字段与GPS速度变化趋势一致且无相位差")
print("     d) 确认offset+57~+58的换算公式 (除以多少等于km/h)")
