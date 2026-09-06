"""NASA loader: tai ban moi nhat tu GitHub raw roi chay NASA.py.

Cach dung:
    python loader.py --threads 2
    python loader.py --threads 2 --view
    python loader.py --skip-update --threads 2   (bo qua update, chay ban local)

Chi update file CODE (NASA.py + scripts/*.js). File DATA local
(settings.json, proxies.txt, moneytask_cookie.txt, blacklist, campaign_domains)
KHONG bao gio bi dong den.
"""
import os
import sys
import urllib.request

# !!! SUA 2 DONG NAY theo repo cua may (vd: GITHUB_USER = "ratman4080") !!!
GITHUB_USER = "nenasa2013-stack"
REPO = "nasa-tool"
BRANCH = "main"

HERE = os.path.dirname(os.path.abspath(__file__))
CODE_FILES = [
    "NASA.py",
    "scripts/engine.js",
    "scripts/giai_cap.js",
    "scripts/hook.js",
    "scripts/solver_check.js",
    "scripts/stealth.js",
]


def fetch(rel):
    url = "https://raw.githubusercontent.com/%s/%s/%s/%s" % (
        GITHUB_USER, REPO, BRANCH, rel.replace("\\", "/"))
    dst = os.path.join(HERE, rel)
    d = os.path.dirname(dst)
    if d:
        os.makedirs(d, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "NASA-loader"})
    with urllib.request.urlopen(req, timeout=60) as r, open(dst, "wb") as f:
        f.write(r.read())
    print("  updated: %s (%s)" % (rel, url))


def main():
    args = sys.argv[1:]
    if "--skip-update" not in args:
        if GITHUB_USER == "TEN_GITHUB_CUA_MAY":
            print("SUA GITHUB_USER/REPO trong loader.py truoc!")
            return 1
        print("Dang tai ban moi tu GitHub...")
        try:
            for rel in CODE_FILES:
                fetch(rel)
        except Exception as e:
            print("Update loi (dung ban local): %s" % e)
    else:
        args = [a for a in args if a != "--skip-update"]
    import subprocess
    target = os.path.join(HERE, "NASA.py")
    return subprocess.run([sys.executable, target] + args).returncode


if __name__ == "__main__":
    sys.exit(main())
