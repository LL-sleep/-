"""
完整流程：关闭弹窗 -> 登录 -> 发送业务开锁
"""
from playwright.sync_api import sync_playwright
import time

p = sync_playwright().start()
browser = p.chromium.launch(
    headless=False,
    executable_path=r'C:\Users\Administrator\AppData\Local\Google\Chrome\Application\chrome.exe'
)
page = browser.new_page(viewport={'width': 1920, 'height': 1080})

# 拦截所有请求和响应
requests = []
responses = []

def on_request(req):
    requests.append({'url': req.url, 'method': req.method, 'time': time.time()})

def on_response(resp):
    try:
        body = resp.body()
        responses.append({
            'url': resp.url,
            'status': resp.status,
            'body': body.decode('utf-8', errors='ignore')[:500]
        })
    except:
        pass

page.on('request', on_request)
page.on('response', on_response)

print("=" * 60)
print("步骤1: 访问远程指令页面")
print("=" * 60)

page.goto('http://118.190.209.224:50044/#/adminDebug')
page.wait_for_load_state('networkidle', timeout=30000)

page.screenshot(path='D:/110/step1_page_loaded.png')
print("[OK] 页面加载完成")

# 检查弹窗
popup = page.query_selector('.el-message-box')
if popup:
    popup_text = popup.inner_text()
    print(f"检测到弹窗: {popup_text[:50]}")
    
    # 点击确定按钮
    page.evaluate('() => { document.querySelector(".el-message-box__btns button")?.click() }')
    print("[OK] 点击确定按钮")
    page.wait_for_timeout(2000)
else:
    print("没有检测到弹窗")

page.screenshot(path='D:/110/step2_after_popup.png')

print("\n" + "=" * 60)
print("步骤2: 登录")
print("=" * 60)

# 检查是否在登录页面
if '/login' in page.url or page.query_selector('input[type="password"]') or page.query_selector('.login-form'):
    print("检测到登录页面")
    
    # 填写用户名
    username_input = page.query_selector('input[placeholder*="用户名"], input[name="username"]')
    if username_input:
        username_input.fill('tbit')
        print("[OK] 填写用户名: tbit")
    
    # 填写密码
    password_input = page.query_selector('input[type="password"], input[placeholder*="密码"]')
    if password_input:
        password_input.fill('369852')
        print("[OK] 填写密码")
    
    page.screenshot(path='D:/110/step3_login_filled.png')
    
    # 点击登录按钮
    login_btn = page.query_selector('button[type="submit"], button:has-text("登录")')
    if login_btn:
        login_btn.click()
        print("[OK] 点击登录按钮")
        page.wait_for_timeout(3000)
    
    try:
        page.wait_for_url('**/adminDebug', timeout=10000)
        print("[OK] 登录成功，已跳转到adminDebug页面")
    except:
        print(f"当前URL: {page.url}")
else:
    print(f"当前URL: {page.url}")
    print("可能已经在adminDebug页面")

page.screenshot(path='D:/110/step4_after_login.png')

print("\n" + "=" * 60)
print("步骤3: 发送业务开锁指令")
print("=" * 60)

if '/adminDebug' not in page.url:
    page.goto('http://118.190.209.224:50044/#/adminDebug')
    page.wait_for_load_state('networkidle', timeout=30000)
    page.wait_for_timeout(2000)

# 填写设备编号
device_id = '868373060149100'
try:
    textarea = page.locator('textarea').first
    textarea.fill(device_id)
    print(f"[OK] 填写设备编号: {device_id}")
except Exception as e:
    print(f"填写设备编号失败: {e}")

page.screenshot(path='D:/110/step5_device_filled.png')

# 选择控制类型为"业务开锁"
try:
    control_select = page.locator('.el-form-item:has-text("控制类型") .el-select').first
    control_select.click()
    page.wait_for_timeout(1000)
    page.click('text=业务开锁')
    print("[OK] 选择控制类型: 业务开锁")
    page.wait_for_timeout(1000)
except Exception as e:
    print(f"选择控制类型失败: {e}")

page.screenshot(path='D:/110/step6_control_selected.png')

# 点击远程控制按钮
try:
    page.evaluate('''() => {
        const buttons = document.querySelectorAll("button");
        for (const btn of buttons) {
            if (btn.textContent.includes("远程控制")) {
                btn.click();
                break;
            }
        }
    }''')
    print("[OK] 点击远程控制按钮")
    page.wait_for_timeout(3000)
except Exception as e:
    print(f"点击远程控制按钮失败: {e}")

page.screenshot(path='D:/110/step7_after_send.png')

print("\n" + "=" * 60)
print("步骤4: 检查结果")
print("=" * 60)

# 打印相关请求
print("\n相关请求:")
for r in requests:
    if any(k in r['url'].lower() for k in ['login', 'control', 'send', 'debug']):
        print(f"{r['method']} {r['url']}")

print("\n相关响应:")
for r in responses:
    if any(k in r['url'].lower() for k in ['login', 'control', 'send', 'debug']):
        print(f"{r['status']} {r['url']}")
        print(f"响应: {r['body'][:200]}")
        print("-" * 40)

print("\n[OK] 完成！")

input("按回车关闭浏览器...")

browser.close()
p.stop()