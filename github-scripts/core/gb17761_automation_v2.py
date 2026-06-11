#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新国标检测APP自动化测试脚本 V2
使用Playwright实现浏览器自动化

流程：
1. 打开首页（已登录状态）
2. 点击"输入编号"按钮
3. 输入设备编号
4. 执行检测

截图命名规则：每个关键操作后截图，文件名=操作名称（按钮文字）
"""

from playwright.sync_api import sync_playwright
import time

class GB17761Automation:
    """新国标检测APP自动化测试"""

    def __init__(self, headless=False, slow_mo=100):
        self.headless = headless
        self.slow_mo = slow_mo

    def start(self):
        """启动浏览器"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo
        )
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        print("[OK] 浏览器启动成功")

    def stop(self):
        """关闭浏览器"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        print("[OK] 浏览器已关闭")

    def snap(self, name="debug"):
        """截图保存，name=按钮或操作名称"""
        # 清理文件名中的特殊字符
        safe_name = name.replace("/", "_").replace("\\", "_")
        path = f"D:/110/新国际检测/{safe_name}.png"
        self.page.screenshot(path=path)
        print(f"[截图] {path}")

    def open_homepage(self):
        """打开首页"""
        print(f"\n[步骤1] 打开首页...")
        self.page.goto("https://test.uqbike.cn/gb17761/index.html#/")
        time.sleep(1)
        self.snap("01_打开首页")
        print("[OK] 首页加载完成")

    def login(self, phone, code):
        """验证码登录"""
        print(f"\n[步骤2] 切换到验证码登录...")
        print(f"手机号: {phone}, 验证码: {code}")
        time.sleep(1)

        # 点击"验证码登录"选项卡
        try:
            code_tab = self.page.get_by_text("验证码登录", exact=True)
            if code_tab and code_tab.is_visible():
                code_tab.click(force=True)
                print("[OK] 已切换到验证码登录")
        except:
            print("[WARN] 可能已经是验证码登录界面")
        time.sleep(0.5)

        # 查找输入框并填写
        inputs = self.page.query_selector_all('input')
        if len(inputs) == 0:
            print("[ERROR] 找不到输入框")
            return False
        phone_input = inputs[0]
        phone_input.fill(phone)
        time.sleep(0.3)
        if len(inputs) > 1:
            code_input = inputs[1]
            code_input.fill(code)
            time.sleep(0.3)

        # 点击"登录"按钮
        print("\n[步骤3] 点击'登录'按钮...")
        js_code = """() => {
            var elements = document.querySelectorAll('button, view, div, span');
            for (var i = 0; i < elements.length; i++) {
                var text = elements[i].innerText || elements[i].textContent;
                var className = elements[i].className || '';
                if (text && text.trim() === '登录' && !className.includes('uni-page-head')) {
                    elements[i].click();
                    return '已点击: 登录';
                }
            }
            return '未找到登录按钮';
        }"""
        result = self.page.evaluate(js_code)
        print(f"[DEBUG] {result}")
        time.sleep(2)
        self.snap("02_点击登录按钮")
        print("[OK] 登录完成")
        return True

    def input_device_id(self, device_id):
        """输入设备编号"""
        print(f"\n[步骤4] 点击'输入编号'按钮...")
        input_btn = self.page.get_by_text("输入编号", exact=True)
        if not input_btn or not input_btn.is_visible():
            print("[ERROR] 找不到'输入编号'按钮")
            all_btns = self.page.query_selector_all('button, [role="button"], .button, .btn')
            for i, btn in enumerate(all_btns):
                t = btn.inner_text()
                if t: print(f"  [{i}] {t}")
            self.snap("ERROR_未找到输入编号按钮")
            return False
        try:
            input_btn.click(force=True, timeout=3000)
        except:
            input_btn.evaluate('el => el.click()')
        time.sleep(0.5)
        self.snap("03_点击输入编号")
        print("[OK] 已点击输入编号")

        # 输入设备号
        print(f"\n[步骤5] 输入设备编号...")
        device_input = self.page.query_selector('input[placeholder*="编号"]') \
                      or self.page.query_selector('input[type="text"]') \
                      or self.page.query_selector('input')
        if not device_input:
            print("[ERROR] 找不到设备编号输入框")
            self.snap("ERROR_未找到设备编号输入框")
            return False
        device_input.fill(device_id)
        time.sleep(0.5)
        self.snap("04_输入设备编号")
        print("[OK] 已输入设备编号")

        # 点击确认
        print(f"\n[步骤6] 点击'确认'(设备编号)...")
        confirm_btn = self.page.get_by_text("确认", exact=True)
        if not confirm_btn or not confirm_btn.is_visible():
            confirm_btn = self.page.get_by_text("确定", exact=True)
        if not confirm_btn or not confirm_btn.is_visible():
            print("[ERROR] 找不到确认按钮")
            self.snap("ERROR_未找到确认按钮")
            return False
        try:
            confirm_btn.click(force=True, timeout=3000)
        except:
            confirm_btn.evaluate('el => el.click()')
        time.sleep(1)
        self.snap("05_点击确认_设备编号")
        print("[OK] 已进入设备检测页面")

        # 选择电池类型：锂电
        print("\n[步骤7] 选择电池类型：锂电")
        time.sleep(1)

        # 点击电池类型下拉框
        js_dropdown = """() => {
            var elements = document.querySelectorAll('view, div, text, input');
            for (var i = 0; i < elements.length; i++) {
                var text = elements[i].innerText || elements[i].textContent;
                if (text && (text.includes('铅酸电池') || text.includes('锂电池'))) {
                    elements[i].click();
                    return '已点击下拉框';
                }
            }
            return '未找到下拉框';
        }"""
        result = self.page.evaluate(js_dropdown)
        print(f"[DEBUG] {result}")
        time.sleep(0.5)

        # 点击锂电池选项
        js_lithium = """() => {
            var elements = document.querySelectorAll('view, div, span, text');
            for (var i = 0; i < elements.length; i++) {
                var text = elements[i].innerText || elements[i].textContent;
                if (text && text.trim() === '锂电池') {
                    elements[i].click();
                    return '已选择锂电池';
                }
            }
            return '未找到锂电池';
        }"""
        result = self.page.evaluate(js_lithium)
        print(f"[DEBUG] {result}")
        time.sleep(0.5)
        self.snap("06_选择锂电池")

        # 点击确认（电池类型）
        print("\n[步骤8] 点击'确认'(电池类型)...")
        js_confirm = """() => {
            var allElements = document.querySelectorAll('*');
            for (var i = 0; i < allElements.length; i++) {
                var text = allElements[i].innerText || allElements[i].textContent;
                if (text && text.trim() === '确认') {
                    allElements[i].click();
                    return '已点击确认';
                }
            }
            return '未找到确认按钮';
        }"""
        result = self.page.evaluate(js_confirm)
        print(f"[DEBUG] {result}")
        time.sleep(2)

        # 关闭可能残留的弹窗
        js_close_modal = """() => {
            var overlay = document.querySelector('.uv-overlay, .uni-mask');
            if (overlay) { overlay.click(); return '关闭弹窗'; }
            return '';
        }"""
        self.page.evaluate(js_close_modal)
        time.sleep(1)
        self.snap("07_点击确认_电池类型")
        print("[OK] 电池选择完成")

        # 等待检测页面加载
        print("\n[步骤9] 等待检测页面加载...")
        time.sleep(2)
        self.snap("08_检测页面加载完成")
        return True

    def run_detection_tests(self):
        """运行各项检测"""
        print(f"\n[步骤10] 开始运行检测项目...")
        time.sleep(1)

        test_items = [
            "数据存储功能检测",
            "信号接收及处理检测",
            "定位及异常状态检测",
            "动态安全监测功能检测",
            "信息发送频次检测",
            "启动状态",
            "非启动状态",
            "异常状态",
        ]

        for idx, item in enumerate(test_items):
            print(f"\n--- 检测项: {item} ---")
            clicked = False
            try:
                test_btn = self.page.get_by_text(item, exact=False).first
                if test_btn and test_btn.is_visible():
                    test_btn.click(force=True)
                    print(f"[OK] 已点击: {item}")
                    clicked = True
                else:
                    print(f"[WARN] 未找到: {item}")
            except Exception as e:
                print(f"[ERROR] 点击失败: {e}")

            if not clicked:
                self.snap(f"ERROR_未找到_{item}")
                continue

            # === 数据存储功能检测：停留30秒 ===
            if idx == 0:
                print(f"[步骤11] 数据存储功能检测 - 停留30秒...")
                self.snap("09_点击数据存储功能检测")
                time.sleep(30)
                self.snap("10_数据存储功能检测完成")

            # === 信号接收及处理检测：完整设置流程 ===
            elif item == "信号接收及处理检测":
                time.sleep(1.5)

                # 弹窗 → 点击"去设置"
                goto_setting_btn = self.page.get_by_text("去设置", exact=True)
                if goto_setting_btn and goto_setting_btn.is_visible():
                    goto_setting_btn.click(force=True)
                    print("[OK] 点击'去设置'")
                    time.sleep(2)
                    self.snap("11_点击去设置")
                else:
                    print("[WARN] 未找到'去设置'弹窗")

                # 定位设置
                loc_btn = self.page.get_by_text("定位设置", exact=True)
                if loc_btn and loc_btn.is_visible():
                    loc_btn.click(force=True)
                    print("[OK] 点击'定位设置'")
                    time.sleep(2)
                    self.snap("12_点击定位设置")
                else:
                    print("[WARN] 未找到'定位设置'")

                # 选择定位方式
                select_btn = self.page.get_by_text("选择定位方式", exact=True)
                if select_btn and select_btn.is_visible():
                    select_btn.click(force=True)
                    print("[OK] 点击'选择定位方式'")
                    time.sleep(1.5)
                    self.snap("13_点击选择定位方式")
                else:
                    print("[WARN] 未找到'选择定位方式'")

                # 使用设备定位
                device_loc_btn = self.page.get_by_text("使用设备定位", exact=True)
                if device_loc_btn and device_loc_btn.is_visible():
                    device_loc_btn.click(force=True)
                    print("[OK] 点击'使用设备定位'，等待5秒...")
                    time.sleep(5)
                    self.snap("14_点击使用设备定位")
                else:
                    print("[WARN] 未找到'使用设备定位'")

                # 确认选择
                confirmed = False
                for txt in ["确认选择", "确认", "确定"]:
                    try:
                        btn = self.page.get_by_text(txt, exact=True)
                        if btn and btn.is_visible():
                            btn.click(force=True)
                            print(f"[OK] 点击'{txt}'")
                            confirmed = True
                            time.sleep(2)
                            self.snap("15_点击确认选择")
                            break
                    except Exception:
                        continue
                if not confirmed:
                    print("[WARN] 未找到确认按钮")

                # 开始检测
                time.sleep(1.5)
                start_btn = self.page.get_by_text("开始检测", exact=True)
                if start_btn and start_btn.is_visible():
                    start_btn.click(force=True)
                    print("[OK] 点击'开始检测'，等待60秒...")
                    self.snap("16_点击开始检测_信号接收及处理")
                    time.sleep(60)
                    self.snap("17_信号接收及处理检测完成")
                else:
                    print("[WARN] 未找到'开始检测'")

            # === 定位及异常状态检测：两个模拟按钮 ===
            elif item == "定位及异常状态检测":
                time.sleep(2)
                self.snap("18_进入定位及异常状态检测页面")

                # 模拟北斗模块通讯异常
                beidou_btn = self.page.get_by_text("模拟北斗模块通讯异常", exact=True)
                if beidou_btn and beidou_btn.is_visible():
                    beidou_btn.click(force=True)
                    print("[OK] 点击'模拟北斗模块通讯异常'，等待60秒...")
                    self.snap("19_点击模拟北斗模块通讯异常")
                    time.sleep(60)
                    self.snap("20_北斗模块通讯异常检测完成")
                else:
                    print("[WARN] 未找到'模拟北斗模块通讯异常'")

                # 模拟无法采集卫星信号
                satellite_btn = self.page.get_by_text("模拟无法采集卫星信号", exact=True)
                if satellite_btn:
                    satellite_btn.scroll_into_view_if_needed()
                    time.sleep(0.5)
                    satellite_btn.click(force=True)
                    print("[OK] 点击'模拟无法采集卫星信号'，等待60秒...")
                    self.snap("21_点击模拟无法采集卫星信号")
                    time.sleep(60)
                    self.snap("22_卫星信号异常检测完成")
                else:
                    print("[WARN] 未找到'模拟无法采集卫星信号'")

            # === 动态安全监测功能检测：4个模拟异常，每个等60秒 ===
            elif item == "动态安全监测功能检测":
                time.sleep(2)
                self.snap("23_进入动态安全监测页面")

                anomalies = [
                    ("电池电压", 0),
                    ("电池温度", 1),
                    ("北斗定位", 2),
                    ("车速速度", 3),
                ]

                for name, nth_idx in anomalies:
                    print(f"[步骤] 点击第{nth_idx+1}个'模拟异常'({name})...")
                    try:
                        # 用 nth 精确匹配第N个"模拟异常"
                        btn = self.page.get_by_text("模拟异常", exact=True).nth(nth_idx)
                        btn.scroll_into_view_if_needed()
                        time.sleep(0.5)
                        if btn.is_visible():
                            btn.click(force=True)
                            print(f"[OK] 已点击'{name}模拟异常'，等待60秒...")
                            self.snap(f"24_点击{name}模拟异常")
                            time.sleep(60)
                            self.snap(f"25_{name}模拟异常完成")
                        else:
                            print(f"[WARN] 第{nth_idx+1}个'模拟异常'不可见")
                    except Exception as e:
                        print(f"[ERROR] 点击'{name}模拟异常'失败: {e}")

            # === 启动状态：点击重新检测，停留3分30秒(210秒) ===
            elif item == "启动状态":
                time.sleep(2)
                self.snap("26_进入启动状态页面")

                # 点击"重新检测"
                print("[步骤] 点击'重新检测'...")
                try:
                    retry_btn = self.page.get_by_text("重新检测", exact=True)
                    # 滚动到底部确保可见
                    retry_btn.scroll_into_view_if_needed()
                    time.sleep(0.5)
                    retry_btn.click(force=True)
                    print("[OK] 已点击'重新检测'")
                    self.snap("27_点击重新检测")
                    time.sleep(1)
                except Exception as e:
                    print(f"[ERROR] 点击'重新检测'失败: {e}")

                # 等待3分30秒
                print("[步骤] 等待3分30秒(210秒)...")
                time.sleep(210)
                self.snap("28_启动状态检测完成")

            # === 非启动状态：点击重新检测，停留1小时30秒(3630秒) ===
            elif item == "非启动状态":
                time.sleep(2)
                self.snap("29_进入非启动状态页面")

                print("[步骤] 点击'重新检测'...")
                try:
                    retry_btn = self.page.get_by_text("重新检测", exact=True)
                    retry_btn.scroll_into_view_if_needed()
                    time.sleep(0.5)
                    retry_btn.click(force=True)
                    print("[OK] 已点击'重新检测'")
                    self.snap("30_点击重新检测")
                    time.sleep(1)
                except Exception as e:
                    print(f"[ERROR] 点击'重新检测'失败: {e}")

                print("[步骤] 等待1小时30秒(3630秒)...")
                time.sleep(3630)
                self.snap("31_非启动状态检测完成")

            # === 异常状态：电池电压异常 → 系统模拟异常检测(210s) → 环境已准备好开始检测(210s) ===
            elif item == "异常状态":
                time.sleep(2)
                self.snap("32_进入异常状态页面")

                # 1. 点击"电池电压异常"
                print("[步骤] 点击'电池电压异常'...")
                try:
                    voltage_btn = self.page.get_by_text("电池电压异常", exact=True)
                    voltage_btn.click(force=True)
                    print("[OK] 已点击'电池电压异常'")
                    self.snap("33_点击电池电压异常")
                    time.sleep(2)
                except Exception as e:
                    print(f"[ERROR] 点击'电池电压异常'失败: {e}")

                # 2. 点击"系统模拟异常检测"，等待3分30秒
                print("[步骤] 点击'系统模拟异常检测'...")
                try:
                    sys_btn = self.page.get_by_text("系统模拟异常检测", exact=True)
                    sys_btn.scroll_into_view_if_needed()
                    time.sleep(0.5)
                    sys_btn.click(force=True)
                    print("[OK] 已点击'系统模拟异常检测'，等待3分30秒...")
                    self.snap("34_点击系统模拟异常检测")
                    time.sleep(210)
                    self.snap("35_系统模拟异常检测完成")
                except Exception as e:
                    print(f"[ERROR] 失败: {e}")

                # 3. 点击"环境已准备好，开始检测"，等待3分30秒
                print("[步骤] 点击'环境已准备好，开始检测'...")
                try:
                    env_btn = self.page.get_by_text("环境已准备好，开始检测", exact=True)
                    env_btn.scroll_into_view_if_needed()
                    time.sleep(0.5)
                    env_btn.click(force=True)
                    print("[OK] 已点击'环境已准备好，开始检测'，等待3分30秒...")
                    self.snap("36_点击环境已准备好开始检测")
                    time.sleep(210)
                    self.snap("37_异常状态检测完成")
                except Exception as e:
                    print(f"[ERROR] 失败: {e}")

            # === 其他检测项：默认等待3秒 ===
            else:
                self.snap(f"{idx + 9}_点击{item}")
                time.sleep(3)
                self.snap(f"{idx + 10}_{item}完成")

            # 返回（除信息发送频次外都要返回）
            if item != "信息发送频次检测":
                print(f"[返回] 点击返回按钮...")
                try:
                    js_back = """() => {
                        var backBtn = document.querySelector('.uni-page-head__left, .uni-nav-btn, [class*="back"]');
                        if (backBtn) { backBtn.click(); return '返回(class)'; }
                        var elements = document.querySelectorAll('view, div, text, i');
                        for (var i = 0; i < elements.length; i++) {
                            var cls = elements[i].className || '';
                            if (cls.includes('left') || cls.includes('back')) {
                                elements[i].click();
                                return '返回(icon)';
                            }
                        }
                        window.history.back();
                        return '浏览器后退';
                    }"""
                    result = self.page.evaluate(js_back)
                    print(f"[DEBUG] {result}")
                    time.sleep(1)
                    self.snap(f"返回_从{item}返回")
                except Exception as e:
                    print(f"[WARN] 返回失败（可能页面已关闭）: {e}")

        print("\n[OK] 所有检测项目执行完成")


def main():
    PHONE = "17376460623"
    CODE = "5566"
    DEVICE_ID = "863499087071635"

    print("=" * 50)
    print("新国标检测APP自动化测试 V2")
    print("=" * 50)

    auto = GB17761Automation(headless=False, slow_mo=100)

    try:
        auto.start()
        auto.open_homepage()
        auto.login(PHONE, CODE)

        if auto.input_device_id(DEVICE_ID):
            auto.run_detection_tests()
            print("\n" + "=" * 50)
            print("[OK] 自动化测试完成！")
            print("=" * 50)
        else:
            print("\n[ERROR] 输入设备编号失败")

    except Exception as e:
        print(f"\n[ERROR] 异常: {e}")
        import traceback
        traceback.print_exc()

    finally:
        input("\n按回车键关闭浏览器...")
        auto.stop()


if __name__ == "__main__":
    main()
