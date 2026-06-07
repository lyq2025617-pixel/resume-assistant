"""使用 Playwright 自动化测试简历助手"""
import asyncio
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:8001"
PASSWORD = "resume2025"

async def test_app():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # 1. 访问主页（应重定向到登录）
        print("=== 1. 访问主页 ===")
        await page.goto(BASE_URL, wait_until="domcontentloaded")
        print(f"  URL: {page.url}")
        title = await page.title()
        print(f"  标题: {title}")

        # 2. 登录
        print("\n=== 2. 登录 ===")
        pwd_input = page.locator('input[type="password"]')
        await pwd_input.fill(PASSWORD)
        await page.keyboard.press("Enter")
        await page.wait_for_url("**/*", wait_until="domcontentloaded")
        print(f"  登录后 URL: {page.url}")
        title = await page.title()
        print(f"  登录后标题: {title}")

        # 3. 检查主页元素
        print("\n=== 3. 主页元素检查 ===")
        for selector in ["#name", "#phone", "#email", "#skills-list", "#internship-list", "#projects-list"]:
            el = page.locator(selector)
            visible = await el.is_visible()
            print(f"  {selector}: {'✓ 可见' if visible else '✗ 不可见'}")

        # 4. 保存数据
        print("\n=== 4. 保存数据 ===")
        save_btn = page.locator("text=保存修改")
        await save_btn.click()
        await asyncio.sleep(2)
        # 检查 toast
        toast = page.locator("text=保存成功")
        print(f"  保存成功提示: {'✓ 显示' if await toast.count() > 0 else '✗ 未显示'}")

        # 5. 切换到 JD 标签
        print("\n=== 5. JD 定制标签 ===")
        jd_tab = page.locator("#tab-jd")
        await jd_tab.click()
        await asyncio.sleep(0.5)
        jd_panel = page.locator("#panel-jd")
        hidden = await jd_panel.get_attribute("class")
        print(f"  JD 面板可见: {'✓' if 'hidden' not in (hidden or '') else '✗ 仍隐藏'}")

        jd_input = page.locator("#jd-input")
        await jd_input.fill("这是一个测试JD，要求有产品经验和数据分析能力")
        tailor_btn = page.locator("#tailor-btn")
        await tailor_btn.click()
        await asyncio.sleep(3)

        # 检查错误
        error_el = page.locator("text=未配置 API Key")
        if await error_el.count() > 0:
            print("  AI 定制: API Key 未配置提示正常显示 ✓")
        else:
            result = page.locator("#tailor-result")
            print(f"  AI 定制结果: {'✓ 有响应' if not await result.get_attribute('class') or 'hidden' not in (await result.get_attribute('class') or '') else '✗ 无响应'}")

        # 6. 切换到面试问题标签
        print("\n=== 6. 面试问题生成 ===")
        q_tab = page.locator("#tab-questions")
        await q_tab.click()
        await asyncio.sleep(0.5)
        q_panel = page.locator("#panel-questions")
        q_class = await q_panel.get_attribute("class")
        print(f"  问题面板可见: {'✓' if 'hidden' not in (q_class or '') else '✗ 仍隐藏'}")

        q_input = page.locator("#jd-input-q")
        await q_input.fill("测试JD")
        q_btn = page.locator("#questions-btn")
        await q_btn.click()
        await asyncio.sleep(3)
        q_error = page.locator("text=未配置 API Key")
        if await q_error.count() > 0:
            print("  面试问题: API Key 未配置提示正常显示 ✓")
        else:
            print("  面试问题: 已生成或有其他响应")

        # 7. 访问预览页
        print("\n=== 7. 预览页面 ===")
        await page.goto(f"{BASE_URL}/preview", wait_until="domcontentloaded")
        preview_title = await page.title()
        print(f"  预览标题: {preview_title}")
        # 检查简历元素
        name_el = page.locator(".name")
        print(f"  姓名显示: {'✓' if await name_el.count() > 0 else '✗ 未找到'}")

        # 8. 截图
        print("\n=== 8. 截图 ===")
        await page.goto(BASE_URL, wait_until="domcontentloaded")
        await page.screenshot(path="screenshot_main.png", full_page=True)
        print("  主页截图: screenshot_main.png")

        await page.goto(f"{BASE_URL}/preview", wait_until="domcontentloaded")
        await page.screenshot(path="screenshot_preview.png", full_page=True)
        print("  预览截图: screenshot_preview.png")

        # 9. 检查 console 错误
        print("\n=== 9. 页面控制台错误 ===")
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        await page.goto(BASE_URL, wait_until="domcontentloaded")
        await asyncio.sleep(1)
        print(f"  发现 {len(errors)} 个控制台错误")
        for e in errors:
            print(f"    - {e}")

        print("\n=== 测试完成 ===")
        await browser.close()

asyncio.run(test_app())
