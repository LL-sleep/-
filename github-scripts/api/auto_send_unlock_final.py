from playwright.sync_api import sync_playwright
import json
import time

p = sync_playwright().start()
browser = p.chromium.launch(
    headless=False,
    executable_path=r'C:\Users\Administrator\AppData\Local\Google\Chrome\Application\chrome.exe'
)
page = browser.new_page()

# 拦截所有请求
requests_data = []
def handle_request(request):
    requests_data.append({
        'url': request.url,
        'method': request.method,
        'post_data': request.post_data
    })
page.on('request', handle_request)

# 直接访问远程指令页面
page.goto('http://118.190.209.224:50044/#/adminDebug')
page.wait_for_load_state('networkidle', timeout=30000)
time.sleep(3)

# ===== 第一步：处理登录过期弹窗 =====
print("=== 检查登录过期弹窗 ===")
popup = page.query_selector('.el-message-box')
if popup:
    popup_text = popup.inner_text()
    print(f"发现弹窗: {popup_text[:100]}")
    
    # 点击"确定"或"重新登录"按钮关闭弹窗
    confirm_btn = page.locator('.el-message-box__btns button').first
    if confirm_btn.is_visible():
        print("点击确定按钮关闭弹窗")
        confirm_btn.click()
        time.sleep(2)
else:
    print("没有弹窗")

# 截图确认
page.screenshot(path='D:/110/57_after_close_popup.png')
print("已关闭弹窗，截图保存")

# ===== 第二步：重新登录 =====
# 检查是否跳转到登录页
if '#/login' in page.url:
    print("跳转到登录页面，重新登录")
    page.fill('input[placeholder="请输入账号"]', 'tbit')
    page.fill('input[placeholder="请输入密码"]', '369852')
    page.click('button:has-text("登录")')
    page.wait_for_load_state('networkidle', timeout=30000)
    time.sleep(3)
    
    # 重新进入远程指令页面
    page.goto('http://118.190.209.224:50044/#/adminDebug')
    page.wait_for_load_state('networkidle', timeout=30000)
    time.sleep(2)

# ===== 第三步：填写表单并发送 =====
# 填写设备编号 - 在textarea中
textarea = page.locator('textarea').first
textarea.fill('863499087237947')
time.sleep(1)

# 点击"控制类型"下拉框，选择"业务开锁"
control_type_row = page.locator('.el-form-item:has-text("控制类型")')
print(f"控制类型行 found: {control_type_row.count()}")

# 点击下拉框
dropdown = control_type_row.locator('.el-select').first
dropdown.click()
time.sleep(1)

# 选择"业务开锁"
page.click('.el-select-dropdown__item:has-text("业务开锁")')
time.sleep(1)

# 截图确认
page.screenshot(path='D:/110/58_before_send.png')
print("已填写设备编号和控制类型")

# 检查控制类型行中的所有按钮
control_buttons = control_type_row.locator('button').all()
print(f"控制类型行中的按钮 ({len(control_buttons)}个)")
for i, btn in enumerate(control_buttons):
    print(f"  {i}: {btn.inner_text()}")

# 点击"远程控制"按钮发送
if len(control_buttons) >= 3:
    control_buttons[2].click()
    print("已点击远程控制按钮")
else:
    page.click('button:has-text("远程控制")')

time.sleep(3)

# 检查捕获的请求
print(f"\n=== 捕获的请求 (共{len(requests_data)}个) ===")
for req in requests_data:
    if 'send' in req['url'].lower() or 'control' in req['url'].lower() or 'command' in req['url'].lower():
        print(f"URL: {req['url']}")
        print(f"Method: {req['method']}")
        print("---")

page.screenshot(path='D:/110/59_after_send.png')
print("已发送，截图保存")

browser.close()
p.stop()
print("\n完成！")