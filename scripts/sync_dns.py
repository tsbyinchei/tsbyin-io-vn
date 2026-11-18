import glob
import json
import os
import sys
import urllib.request
import urllib.error

ZONE_ID = os.environ["CF_ZONE_ID"]
API_TOKEN = os.environ["CF_API_TOKEN"]
ROOT_DOMAIN = "tsbyin.io.vn"
MANAGED_COMMENT = "managed-by-gitops"


def cf_request(method, endpoint, payload=None):
    url = f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/{endpoint}"
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json",
    }
    data = json.dumps(payload).encode("utf-8") if payload else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"Cloudflare API Error [{method} {endpoint}]: {e.read().decode('utf-8')}")
        sys.exit(1)


def load_desired_records():
    desired = {}  # key: (type, fqdn, content) -> dict
    for filepath in sorted(glob.glob("domains/*.json")):
        subdomain = os.path.basename(filepath)[:-5]
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        for rec in data.get("records", []):
            rtype = rec["type"].upper()
            rname = rec["name"]
            fqdn = f"{subdomain}.{ROOT_DOMAIN}" if rname == "@" else f"{rname}.{subdomain}.{ROOT_DOMAIN}"
            content = rec["value"].strip()
            proxied = rec.get("proxied", False) if rtype in {"A", "AAAA", "CNAME"} else False

            key = (rtype, fqdn, content)
            desired[key] = {
                "type": rtype,
                "name": fqdn,
                "content": content,
                "proxied": proxied,
                "ttl": 1,  # Auto TTL
                "comment": MANAGED_COMMENT,
            }
    return desired


def get_existing_managed_records():
    existing = {}
    page = 1
    while True:
        res = cf_request("GET", f"dns_records?per_page=100&page={page}")
        for rec in res.get("result", []):
            if rec.get("comment") == MANAGED_COMMENT:
                key = (rec["type"], rec["name"], rec["content"])
                existing[key] = rec
        info = res.get("result_info", {})
        if page >= info.get("total_pages", 1):
            break
        page += 1
    return existing


def export_domains_index():
    domains_list = []
    for filepath in sorted(glob.glob("domains/*.json")):
        subdomain = os.path.basename(filepath)[:-5]
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            domains_list.append({
                "subdomain": subdomain,
                "owner": data.get("owner", {}).get("github", "anonymous"),
                "records": data.get("records", [])
            })
        except Exception as e:
            print(f"Warning: Không đọc được {filepath}: {e}")
    with open("domains.json", "w", encoding="utf-8") as f:
        json.dump(domains_list, f, indent=2, ensure_ascii=False)
    print("Exported domains.json successfully.")


def main():
    export_domains_index()
    desired = load_desired_records()
    existing = get_existing_managed_records()

    # 1. Tạo mới hoặc cập nhật proxy status
    for key, target in desired.items():
        if key not in existing:
            print(f"[CREATE] {target['type']} {target['name']} -> {target['content']} (proxied={target['proxied']})")
            cf_request("POST", "dns_records", target)
        else:
            cur = existing[key]
            if cur.get("proxied") != target["proxied"]:
                print(f"[UPDATE] {target['type']} {target['name']} -> proxied={target['proxied']}")
                cf_request("PATCH", f"dns_records/{cur['id']}", {"proxied": target["proxied"], "comment": MANAGED_COMMENT})

    # 2. Xóa các bản ghi đã bị gỡ khỏi repo
    for key, cur in existing.items():
        if key not in desired:
            print(f"[DELETE] {cur['type']} {cur['name']} -> {cur['content']}")
            cf_request("DELETE", f"dns_records/{cur['id']}")

    print("🎉 Đồng bộ DNS hoàn tất!")


if __name__ == "__main__":
    main()
