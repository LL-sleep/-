"""
完整流程：登录 -> 填写设备 -> 点击远程控制 -> 弹窗处理 -> 重新登录 -> 再次发送
"""
import time
from playwright.sync_api import sync_playwright

def run():
    p = sync_playwright().start()
    browser = p.chromium.launch(
        headless=False,
        executable_path=r'C:\Users\Administrator\AppData\Local\Google\Chrome\Application\chrome.exe'
    )
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    
    print("步骤1: 访问登录页面")
    # 直接访问登录页面
    page.goto('http://118.190.209.224:50044/#/login')
    page.wait_for_load_state('networkidle', timeout=30000)
    time.sleep(2)
    
    print("步骤2: 输入账号密码登录")
    # 登录页面通常只有一个用户名输入框和密码输入框
    # 使用更精确的选择器
    inputs = page.query_selector_all('input')
    print(f"找到 {len(inputs)} 个输入框")
    
    # 找到登录表单的输入框（通常第一个是用户名，第二个是密码）
    text_inputs = [i for i in inputs if i.get_attribute('type') in ['text', '']]
    password_inputs = page.query_selector_all('input[type="password"]')
    
    if len(text_inputs) >= 1:
        text_inputs[0].fill('tbit')
        print("已填写用户名")
    
    if len(password_inputs) >= 1:
        password_inputs[0].fill('369852')
        print("已填写密码")
    
    # 点击登录按钮
    login_btn = page.query_selector('button[type="submit"], .login-btn, button:has-text("登录")')
    if login_btn:
        login_btn.click()
        print("已点击登录")
    else:
        # 尝试按回车
        page.keyboard.press('Enter')
        print("已按回车登录")
    
    time.sleep(4)
    
    print("步骤3: 填写设备编号并发送业务开锁")
    # 现在在adminDebug页面
    # 填写设备编号 - 找到第一个textarea
    textarea = page.query_selector('textarea')
    if textarea:
        textarea.fill('868373060149100')
        print("已填写设备编号")
    
    time.sleep(1)
    
    # 选择控制类型 - 找到控制类型旁边的select
    # 先找到包含"控制类型"文本的form-item
    form_items = page.query_selector_all('.el-form-item')
    control_item = None
    for item in form_items:
        label = item.query_selector('.el-form-item__label')
        if label and '控制类型' in label.inner_text():
            control_item = item
            break
    
    if control_item:
        select = control_item.query_selector('.el-select')
        if select:
            select.click()
            time.sleep(0.5)
            # 选择业务开锁
            options = page.query_selector_all('.el-select-dropdown__item')
            for opt in options:
                if '业务开锁' in opt.inner_text():
                    opt.click()
                    print("已选择业务开锁")
                    break
    
    time.sleep(0.5)
    
    # 点击远程控制按钮
    if control_item:
        btn = control_item.query_selector('button')
        if btn:
            btn.click()
            print("已点击远程控制")
    
    time.sleep(2)
    
    # 检查是否有登录过期弹窗
    popup = page.query_selector('.el-message-box')
    if popup:
        popup_text = popup.inner_text()
        print(f"检测到弹窗: {popup_text[:50]}")
        
        # 点击确定
        page.click('.el-message-box__btns button')
        print("已点击确定")
        
        time.sleep(3)
        
        # 重新登录
        print("步骤4: 重新登录")
        inputs = page.query_selector_all('input')
        text_inputs = [i for i in inputs if i.get_attribute('type') in ['text', '']]
        password_inputs = page.query_selector_all('input[type="password"]')
        
        if len(text_inputs) >= 1:
            text_inputs[0].fill('tbit')
        if len(password_inputs) >= 1:
            password_inputs[0].fill('369852')
        
        login_btn = page.query_selector('button[type="submit"], .login-btn, button:has-text("登录")')
        if login_btn:
            login_btn.click()
        else:
            page.keyboard.press('Enter')
        
        print("已重新登录")
        time.sleep(4)
        
        # 再次填写并发送
        print("步骤5: 再次发送业务开锁")
        textarea = page.query_selector('textarea')
        if textarea:
            textarea.fill('868373060149100')
        
        # 重新选择控制类型
        form_items = page.query_selector_all('.el-form-item')
        control_item = None
        for item in form_items:
            label = item.query_selector('.el-form-item__label')
            if label and '控制类型' in label.inner_text():
                control_item = item
                break
        
        if control_item:
            select = control_item.query_selector('.el-select')
            if select:
                select.click()
                time.sleep(0.5)
                options = page.query_selector_all('.el-select-dropdown__item')
                for opt in options:
                    if '业务开锁' in opt.inner_text():
                        opt.click()
                        break
        
        time.sleep(0.5)
        
        if control_item:
            btn = control_item.query_selector('button')
            if btn:
                btn.click()
                print("已再次点击远程控制")
        
        time.sleep(2)
    
    page.screenshot(path='D:/110/final.png')
    print("完成!")
    
    input("按回车关闭浏览器...")
    browser.close()
    p.stop()

if __name__ == '__main__':
    run()
