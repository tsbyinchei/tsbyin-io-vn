import ipaddress
import json
import os
import re
import subprocess
import sys

ALLOWED_TYPES = {"A", "AAAA", "CNAME", "TXT"}
RESERVED_NAMES = {
    # Hạ tầng mạng & DNS
    "ns", "ns0", "ns1", "ns2", "ns3", "ns4", "ns5", "ns6", "ns7", "ns8", "ns9",
    "dns", "mx", "cname", "acme", "ssl", "tls", "cert", "certs", "whois", "rdap",
    "zone", "zones", "proxy", "proxied", "sys", "system", "server", "servers",

    # Mail & Giao thức truyền thông
    "mail", "email", "webmail", "mailbox", "smtp", "imap", "pop", "pop3",
    "autoconfig", "autodiscover", "ftp", "sftp", "ssh", "rsync", "vpn",
    "mqtt", "ota", "ws", "wss", "websocket",

    # Xác thực, Tài khoản & Bảo mật (Chống Phishing)
    "auth", "login", "signin", "signup", "sso", "oauth", "account", "accounts",
    "security", "secure", "verify", "verification", "privacy", "legal", "abuse",
    "terms", "password", "recovery", "mfa", "2fa",

    # Quản trị & Điều hướng hệ thống
    "admin", "administrator", "root", "panel", "dash", "dashboard", "portal",
    "internal", "private", "public", "support", "help", "billing", "pay",
    "payment", "payments", "checkout", "bank", "gov", "edu", "mil",

    # Dịch vụ ứng dụng & Tên miền
    "api", "app", "apps", "www", "blog", "docs", "doc", "status", "cdn",
    "static", "assets", "dev", "devops", "git", "github", "gitlab",
    "domain", "domains", "subdomain", "subdomains", "register", "registrar", "registry",
    "staging", "prod", "production", "test", "testing", "preview", "bot",

    # Brand, Project & TLDs
    "tsbyin", "tsbyinchei", "cloudflare", "vn", "io", "com", "net", "org"
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
