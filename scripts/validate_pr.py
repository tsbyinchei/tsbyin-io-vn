import ipaddress
import json
import os
import re
import subprocess
import sys

ALLOWED_TYPES = {"A", "AAAA", "CNAME", "TXT"}
RESERVED_NAMES = {
    # 1. Hạ tầng mạng, DNS & RFC
    "ns", "ns0", "ns1", "ns2", "ns3", "ns4", "ns5", "ns6", "ns7", "ns8", "ns9",
    "dns", "mx", "cname", "txt", "srv", "ptr", "soa", "caa", "dnssec",
    "acme", "ssl", "tls", "cert", "certs", "whois", "rdap",
    "zone", "zones", "proxy", "proxied", "edge", "tunnel", "tun", "cf",
    "sys", "system", "server", "servers", "node", "nodes", "host", "hosts",
    "localhost", "local", "default", "wildcard", "router", "gateway",

    # 2. Mail, Giao thức truyền thông & IoT/IoMT
    "mail", "email", "webmail", "mailbox", "smtp", "imap", "pop", "pop3",
    "autoconfig", "autodiscover", "postmaster", "hostmaster", "webmaster",
    "noreply", "no-reply", "mailer-daemon", "bounce", "bounces",
    "ftp", "sftp", "ssh", "rsync", "vpn", "wireguard", "wg",
    "mqtt", "ota", "ws", "wss", "websocket", "webhook", "webhooks", "hook", "hooks",
    "iot", "iomt", "telemetry", "sensor", "sensors", "device", "devices",

    # 3. Xác thực, Tài khoản & Bảo mật
    "auth", "login", "signin", "signup", "sso", "oauth", "oidc", "jwt", "token",
    "account", "accounts", "user", "users", "profile", "id", "verify", "verification",
    "security", "secure", "privacy", "legal", "abuse", "dmca", "tos", "terms",
    "password", "passwd", "recovery", "reset", "mfa", "2fa", "otp",

    # 4. Quản trị, Tài chính & Tổ chức nhạy cảm
    "admin", "administrator", "root", "panel", "cpanel", "1panel",
    "dash", "dashboard", "portal", "console", "manage", "management",
    "internal", "private", "public", "support", "help", "contact", "info",
    "billing", "pay", "payment", "payments", "checkout", "invoice", "wallet",
    "bank", "gov", "edu", "mil", "vnnic", "nic",

    # 5. Hệ sinh thái Dịch vụ, Homelab & Tiện ích của TsByin
    "api", "apis", "app", "apps", "www", "web", "site", "sites",
    "blog", "docs", "doc", "wiki", "guide", "status", "uptime", "monitor", "metrics",
    "cdn", "static", "assets", "media", "film", "stream", "video", "audio",
    "s3", "minio", "storage", "bucket", "dl", "download", "downloads",
    "drop", "share", "bin", "paste", "file", "files", "upload", "uploads", "iso",
    "dev", "devops", "git", "github", "gitlab", "ci", "cd", "actions",
    "domain", "domains", "subdomain", "subdomains", "register", "registrar", "registry",
    "staging", "prod", "production", "test", "testing", "preview", "sandbox", "lab", "labs",
    "bot", "bots", "ai", "agent", "agents", "mcp",
    "free", "sub", "qr", "eat", "exam", "quiz", "task", "tasks",
    "emqx", "grafana", "influx", "influxdb", "n8n", "ag", "docker",

    # 6. Thương hiệu cá nhân & TLDs
    "tsbyin", "tsbyinchei", "chei", "tuansy", "phenikaa",
    "cloudflare", "google", "firebase", "vercel", "netlify",
    "vn", "io", "com", "net", "org", "co", "me", "xyz", "site", "online",

    # 7. Cloud Storage, Office & Email Providers (Chống giả mạo dịch vụ & typosquatting)
    "drive", "onedrive", "icloud", "dropbox", "box", "mega", "terabox", "nextcloud", "owncloud",
    "gmail", "googlemail", "outlook", "hotmail", "yahoo", "proton", "protonmail", "zoho",
    "stmp", "smpt", "impa", "web-mail", "e-mail", "mailserver", "mx1", "mx2", "mx3",
    "relay", "spf", "dkim", "dmarc", "resend", "sendgrid", "mailgun", "ses",
    "docs", "sheets", "slides", "forms", "meet", "zoom", "teams", "discord", "telegram", "zalo",
    "momo", "zalopay", "vnpay", "vietqr", "napas", "payos", "stripe", "paypal",
    "store", "shop", "market", "update", "updates", "upgrade", "patch", "firmware",
}

DISALLOWED_CNAMES = (
    ".trycloudflare.com",
    ".cfargotunnel.com",
    ".workers.dev",
    ".r2.dev",
    ".pages.dev",
    ".blob.core.windows.net",
    ".tk",
    ".ml",
    ".ga",
    ".cf",
    ".gq",
    ".adult",
    ".porn",
    ".sex",
    ".sexy",
    ".xxx",
    ".ts.net",
)

BLOCKED_KEYWORDS = (
    # Quản trị & Xác thực
    "admin", "login", "signin", "signup", "auth", "verify", "secure", "password", "passwd",
    # Tài chính & Ngân hàng
    "bank", "pay", "paypal", "momo", "zalopay", "vnpay", "vietqr", "billing", "invoice", "wallet",
    # Cơ quan & Hệ thống
    "gov", "support", "tsbyin", "tsbyinchei", "tuansy", "cloudflare"
)

SUBDOMAIN_REGEX = re.compile(r"^[a-z0-9]([a-z0-9-]{1,30}[a-z0-9])?$")


def get_changed_files():
    base_ref = os.environ.get("GITHUB_BASE_REF", "main")
    subprocess.run(["git", "fetch", "origin", base_ref], check=True)
    result = subprocess.run(
        ["git", "diff", "--name-status", f"origin/{base_ref}...HEAD"],
        capture_output=True, text=True, check=True
    )
    changes = []
    for line in result.stdout.strip().splitlines():
        if line:
            parts = line.split("\t")
            changes.append((parts[0], parts[-1]))
    return changes


def validate_record(rec, idx, subdomain):
    if not isinstance(rec, dict):
        return f"Record #{idx} phải là object JSON."
    rtype = rec.get("type", "").upper()
    if rtype not in ALLOWED_TYPES:
        return f"Record #{idx}: Loại bản ghi '{rtype}' không được phép (chỉ hỗ trợ {ALLOWED_TYPES})."
    name = rec.get("name", "")
    if name != "@" and not re.match(r"^[a-z0-9-]+$", name):
        return f"Record #{idx}: Tên bản ghi con '{name}' không hợp lệ."
    value = rec.get("value", "")
    if not isinstance(value, str) or not value.strip():
        return f"Record #{idx}: Giá trị 'value' không được để trống."
    value = value.strip()
    proxied = rec.get("proxied", False)
    if not isinstance(proxied, bool):
        return f"Record #{idx}: 'proxied' phải là true hoặc false."
    if rtype == "TXT" and proxied:
        return f"Record #{idx}: Bản ghi TXT không thể bật proxied."

    # 1. Kiểm tra IPv4 cho bản ghi A
    if rtype == "A":
        try:
            ip = ipaddress.IPv4Address(value)
            # Ngoại lệ: 192.0.2.1 là dummy IP thông dụng của Cloudflare khi bật proxied
            if str(ip) == "192.0.2.1" and proxied:
                pass
            elif ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local or ip.is_multicast:
                return f"Record #{idx}: Địa chỉ IPv4 '{value}' thuộc dải mạng nội bộ/bảo lưu, không được phép sử dụng."
        except ipaddress.AddressValueError:
            return f"Record #{idx}: '{value}' không phải là địa chỉ IPv4 hợp lệ."

    # 2. Kiểm tra IPv6 cho bản ghi AAAA
    elif rtype == "AAAA":
        try:
            ip = ipaddress.IPv6Address(value)
            if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local or ip.is_multicast:
                return f"Record #{idx}: Địa chỉ IPv6 '{value}' thuộc dải mạng nội bộ/bảo lưu, không được phép sử dụng."
        except ipaddress.AddressValueError:
            return f"Record #{idx}: '{value}' không phải là địa chỉ IPv6 hợp lệ."

    # 3. Kiểm tra CNAME
    elif rtype == "CNAME":
        cname_lower = value.lower().rstrip(".")
        for disallowed in DISALLOWED_CNAMES:
            if cname_lower.endswith(disallowed.lstrip(".")):
                return f"Record #{idx}: CNAME không được trỏ đến dịch vụ '{disallowed}' vì lý do an toàn & bảo mật."
        if cname_lower == f"{subdomain}.tsbyin.io.vn" or cname_lower == "tsbyin.io.vn":
            return f"Record #{idx}: CNAME không được trỏ vào chính nó hoặc domain gốc (gây loop DNS)."

    return None


def main():
    actor = os.environ.get("GITHUB_ACTOR", "").lower()
    repo_owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "").lower()
    is_maintainer = (actor == repo_owner)

    changes = get_changed_files()
    if not changes:
        print("Không có file nào thay đổi.")
        return

    errors = []
    for status, filepath in changes:
        if not filepath.startswith("domains/") or not filepath.endswith(".json"):
            if not is_maintainer:
                errors.append(f"Bạn chỉ được phép thêm/sửa file trong thư mục 'domains/*.json' (vi phạm: {filepath}).")
            continue

        filename = os.path.basename(filepath)
        subdomain = filename[:-5]  # Bỏ đuôi .json

        if not SUBDOMAIN_REGEX.match(subdomain):
            errors.append(f"Tên subdomain '{subdomain}' không hợp lệ (chỉ dùng a-z, 0-9, dấu '-', dài 3-32 ký tự).")
        if subdomain in RESERVED_NAMES and not is_maintainer:
            errors.append(f"Subdomain '{subdomain}' nằm trong danh sách bảo lưu của hệ thống.")

        # Kiểm tra từ khóa nhạy cảm / Chống lừa đảo dạng substring
        if not is_maintainer:
            for kw in BLOCKED_KEYWORDS:
                if kw in subdomain:
                    if kw == "pay" and "display" in subdomain:
                        continue
                    if kw == "auth" and "author" in subdomain:
                        continue
                    errors.append(f"Subdomain '{subdomain}' chứa từ khóa nhạy cảm bị hạn chế ('{kw}').")
                    break

        # Chống sửa/xóa file của người khác
        if status.startswith("M") or status.startswith("D"):
            base_ref = os.environ.get("GITHUB_BASE_REF", "main")
            old_content = subprocess.run(
                ["git", "show", f"origin/{base_ref}:{filepath}"],
                capture_output=True, text=True
            ).stdout
            try:
                old_data = json.loads(old_content)
                old_owner = old_data.get("owner", {}).get("github", "").lower()
                if old_owner != actor and not is_maintainer:
                    errors.append(f"Từ chối quyền: '{filepath}' thuộc sở hữu của @{old_owner}, bạn (@{actor}) không thể sửa/xóa.")
            except json.JSONDecodeError:
                pass

        if status.startswith("D"):
            continue

        # Kiểm tra nội dung file JSON mới
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            errors.append(f"Lỗi cú pháp JSON ở '{filepath}': {e}")
            continue

        owner_gh = data.get("owner", {}).get("github", "").lower()
        if not owner_gh:
            errors.append(f"'{filepath}': Thiếu trường 'owner.github'.")
        elif owner_gh != actor and not is_maintainer:
            errors.append(f"'{filepath}': 'owner.github' ({owner_gh}) phải trùng với tài khoản GitHub tạo PR ({actor}).")

        records = data.get("records")
        if not isinstance(records, list) or len(records) == 0 or len(records) > 10:
            errors.append(f"'{filepath}': 'records' phải là mảng chứa từ 1 đến 10 bản ghi.")
        else:
            for idx, rec in enumerate(records, start=1):
                err = validate_record(rec, idx, subdomain)
                if err:
                    errors.append(f"'{filepath}' -> {err}")

    if errors:
        print("❌ KIỂM TRA PR THẤT BẠI:")
        for e in errors:
            print(f" - {e}")
        sys.exit(1)

    print("✅ Kiểm tra PR hợp lệ! Sẵn sàng để merge.")


if __name__ == "__main__":
    main()
