# Chạy NASA trên Android (Termux, không cần root)

## 1. Cài Termux
1. Gỡ bản Termux trên CH Play (cũ, chết).
2. Tải bản mới trên F-Droid: `https://f-droid.org/packages/com.termux/`
3. Mở lên, cho phép truy cập bộ nhớ.

## 2. Cài môi trường
Dán từng dòng trong Termux:
```bash
pkg update && pkg upgrade -y
pkg install python git -y
pip install --upgrade pip
pip install requests playwright
playwright install chromium
```
Kiểm tra: `python --version` (phải 3.11+). Nếu `playwright install chromium` lỗi trên máy cũ (aarch64 thiếu wheel) thì dùng máy khác — Termux đời mới thường OK.

## 3. Tải tool
```bash
cd ~
git clone https://github.com/nenasa2013-stack/nasa-tool.git nasa-tool
cd nasa-tool
```

## 4. Cấu hình (lần đầu)
```bash
cp settings.example.json settings.json
```
Mở `settings.json` dán 2 key kiot vào `key_xoay_1` / `key_xoay_2` (dùng app MT Manager hoặc `nano settings.json`).
Cookie MoneyTask: chạy tool gõ `mt`, nó hỏi dán cookie 1 lần rồi tự lưu.

## 5. Chạy
```bash
cd ~/nasa-tool
python loader.py --threads 2
```
- `loader.py` tự tải bản mới nhất từ GitHub mỗi lần chạy, không đè `settings.json`/cookie.
- Prompt proxy: `1/2` chọn key, `3` = Direct không proxy.
- Lệnh trong tool: dán link octo, hoặc `mt` lấy link MoneyTask, `auto` bật/tắt tự chạy, `pkey` đổi key, `q` thoát.
- Muốn chạy offline không update: `python loader.py --skip-update --threads 2`

## 6. Lưu ý
- **Không dùng `--view`** (Android không có Chrome GUI, headless mặc định là đúng).
- **Giữ Termux sống nền:** vuốt notification Termux → `Acquire wakelock`, không là Android giết giữa chừng.
- **Port 8080:** userscript (`moneytask.user.js`) trên Kiwi Browser + Tampermonkey vẫn gọi `http://127.0.0.1:8080` như trên PC.
- Update tool: không cần làm gì — mỗi lần `loader.py` chạy là bản mới nhất.
