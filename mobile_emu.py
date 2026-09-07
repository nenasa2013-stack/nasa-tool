"""Fake thiet bi mobile nhu DevTools F12 (Playwright device emulation).

No lam: mo Chromium that voi viewport + UA + scale + is_mobile + has_touch
cua thiet bi di dong (y nhu bat device toolbar trong F12).

Cach dung:
  python mobile_emu.py
      Mo iPhone 14, vao trang check fingerprint.

  python mobile_emu.py "Pixel 5" https://moneytask.top
      Mo Pixel 5 tai URL chi dinh.

  python mobile_emu.py --list
      Liet ke thiet bi co san (iPhone / Pixel / Galaxy / iPad...).

Luu y: script chay doc lap de test tay. Luong mt/claim cua NASA.py
van ghim UA desktop Chrome/152 de nhat quan fingerprint - dung tron lan.
"""
import sys

from playwright.sync_api import sync_playwright

DEFAULT_DEVICE = "iPhone 14"
DEFAULT_URL = "https://www.whatismybrowser.com/detect/what-is-my-user-agent"


def main():
    args = sys.argv[1:]
    with sync_playwright() as pw:
        if "--list" in args:
            for name in sorted(pw.devices.keys()):
                print(" - " + name)
            return 0
        device_name = args[0] if len(args) > 0 else DEFAULT_DEVICE
        url = args[1] if len(args) > 1 else DEFAULT_URL
        if device_name not in pw.devices:
            print(f"Khong co thiet bi '{device_name}'. Chay voi --list de xem.")
            return 1
        device = pw.devices[device_name]
        print(f"Emulate: {device_name}")
        print(f"  viewport : {device['viewport']}")
        print(f"  UA       : {device['user_agent'][:80]}...")
        print(f"  mobile   : {device.get('is_mobile')} | touch: {device.get('has_touch')}")
        browser = pw.chromium.launch(headless=False, args=["--no-sandbox"])
        ctx = browser.new_context(**device)
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        print(f"Da mo: {url}")
        input("Enter de dong...")
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
