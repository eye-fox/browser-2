#!/usr/bin/env python3
"""
Selenium Browser Automation — fallback when CDP not available.
Gunakan Chrome in headless mode via Selenium + WebDriver Manager.
"""
import argparse, json, os, sys, base64, time, random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

try:
    from webdriver_manager.chrome import ChromeDriverManager
    HAS_WDM = True
except ImportError:
    HAS_WDM = False


def create_driver(headless=True, window_size=(1920, 1080), proxy=None, user_agent=None):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument(f"--window-size={window_size[0]},{window_size[1]}")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-sync")
    opts.add_argument("--no-first-run")
    opts.add_argument("--disable-features=ChromeWhatsNewUI,TranslateUI")
    opts.add_argument("--remote-allow-origins=*")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    if proxy:
        opts.add_argument(f"--proxy-server={proxy}")
    if user_agent:
        opts.add_argument(f"--user-agent={user_agent}")
    if HAS_WDM:
        service = Service(ChromeDriverManager().install())
    else:
        service = Service()
    driver = webdriver.Chrome(service=service, options=opts)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3]});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        """
    })
    return driver


def cmd_elements(driver):
    els = driver.find_elements(By.CSS_SELECTOR,
        "a,button,input,select,textarea,[tabindex],[contenteditable],"
        "[role=button],[role=link],[role=checkbox]")
    result = []
    for i, el in enumerate(els):
        try:
            if not el.is_displayed():
                continue
            rect = el.rect
            result.append({
                "index": i, "tag": el.tag_name,
                "type": el.get_attribute("type") or "",
                "id": el.get_attribute("id") or "",
                "text": (el.text or "").strip()[:50],
                "rect": {"x": int(rect["x"]), "y": int(rect["y"]),
                         "w": int(rect["width"]), "h": int(rect["height"])}
            })
        except:
            pass
    return json.dumps(result)


def cmd_state(driver):
    return json.dumps({
        "url": driver.current_url,
        "title": driver.title,
        "ready": driver.execute_script("return document.readyState")
    })


def cmd_screenshot(driver, path=None, full=False):
    if full:
        pw = driver.execute_script("return document.body.scrollWidth")
        ph = driver.execute_script("return document.body.scrollHeight")
        driver.set_window_size(pw, ph)
    png = driver.get_screenshot_as_png()
    if path:
        with open(path, "wb") as f:
            f.write(png)
        return json.dumps({"saved": path})
    return base64.b64encode(png).decode()


def main():
    p = argparse.ArgumentParser(prog="selenium-browser")
    p.add_argument("--cdp-url", help="Ignored (selenium CDP)")
    p.add_argument("--session", default="default")
    p.add_argument("--headed", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--proxy-server")
    sub = p.add_subparsers(dest="command")

    sub.add_parser("start").add_argument("--port", type=int, default=0)
    sp = sub.add_parser("open"); sp.add_argument("url")
    sub.add_parser("eval").add_argument("js")
    sp = sub.add_parser("screenshot"); sp.add_argument("path", nargs="?"); sp.add_argument("--full", action="store_true")
    sub.add_parser("state")
    sub.add_parser("elements")
    sp = sub.add_parser("click"); sp.add_argument("args", nargs="+")
    sub.add_parser("type").add_argument("text")
    sp = sub.add_parser("input"); sp.add_argument("index"); sp.add_argument("text")
    sp = sub.add_parser("scroll"); sp.add_argument("direction", nargs="?", default="down"); sp.add_argument("--amount", type=int, default=300)
    sub.add_parser("back")
    sub.add_parser("keys").add_argument("keys")
    sub.add_parser("close")

    args = p.parse_args()
    if not args.command:
        p.print_help(); sys.exit(1)

    driver = create_driver(headless=not args.headed, proxy=args.proxy_server)

    try:
        if args.command == "open":
            driver.get(args.url)
            time.sleep(1.5)
            print(cmd_state(driver))

        elif args.command == "state":
            print(cmd_state(driver))

        elif args.command == "elements":
            print(cmd_elements(driver))

        elif args.command == "eval":
            result = driver.execute_script(args.js)
            print(json.dumps(result) if not isinstance(result, str) else result)

        elif args.command == "screenshot":
            print(cmd_screenshot(driver, args.path, args.full))

        elif args.command == "click":
            if len(args.args) == 1:
                els = json.loads(cmd_elements(driver))
                idx = int(args.args[0])
                if idx < len(els):
                    el = driver.find_element(By.CSS_SELECTOR, f"*")
                    el = driver.find_elements(By.CSS_SELECTOR,
                        "a,button,input,select,textarea,[tabindex],[contenteditable],"
                        "[role=button],[role=link],[role=checkbox]")[idx]
                    el.click()
                    print(json.dumps({"clicked": idx}))
                else:
                    print(json.dumps({"error": f"index {idx} not found"}))
            elif len(args.args) == 2:
                from selenium.webdriver.common.action_chains import ActionChains
                x, y = int(args.args[0]), int(args.args[1])
                ActionChains(driver).move_by_offset(x, y).click().perform()
                print(json.dumps({"clicked": [x, y]}))

        elif args.command in ("type", "input"):
            text = args.text
            if args.command == "input":
                idx = int(args.index)
                els = driver.find_elements(By.CSS_SELECTOR,
                    "a,button,input,select,textarea,[tabindex],[contenteditable],"
                    "[role=button],[role=link],[role=checkbox]")
                if idx < len(els):
                    els[idx].click()
                    els[idx].clear()
                    els[idx].send_keys(text)
                else:
                    print(json.dumps({"error": f"index {idx} not found"})); return
            else:
                from selenium.webdriver.common.action_chains import ActionChains
                ActionChains(driver).send_keys(text).perform()
            print(json.dumps({"typed": text}))

        elif args.command == "scroll":
            d = 1 if args.direction == "down" else -1
            driver.execute_script(f"window.scrollBy(0, {d * args.amount})")
            print(json.dumps({"scrolled": args.direction, "amount": args.amount}))

        elif args.command == "back":
            driver.back()
            time.sleep(1)
            print(cmd_state(driver))

        elif args.command == "keys":
            k = getattr(Keys, args.keys.upper(), args.keys)
            from selenium.webdriver.common.action_chains import ActionChains
            ActionChains(driver).send_keys(k).perform()
            print(json.dumps({"key": args.keys}))

        elif args.command == "close":
            driver.quit()
            print("closed")

    finally:
        if args.command != "close":
            driver.quit()

if __name__ == "__main__":
    main()
