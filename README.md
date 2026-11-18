# tsbyin.io.vn - Free Subdomains for Developers 🚀

Dự án cung cấp subdomain miễn phí dạng `*.tsbyin.io.vn` dành cho cộng đồng lập trình viên, học sinh và sinh viên, được quản lý theo mô hình **GitOps** tự động hóa hoàn toàn với GitHub Actions và Cloudflare DNS.

🌐 **Trang web chính thức & Công cụ kiểm tra Subdomain:** [tsbyin.io.vn](https://tsbyin.io.vn)

---

## ⚡ Tính năng nổi bật trên Web
- **Tra cứu Subdomain tức thì:** Kiểm tra tính khả dụng, tên bảo lưu và trạng thái DNS của subdomain trước khi gửi PR.
- **Trình tạo file JSON trực quan:** Điền biểu mẫu và tự động sinh mã JSON chuẩn hoặc tạo nhanh PR trên GitHub chỉ với 1 cú click.
- **Giao diện hiện đại:** Hỗ trợ Dark/Light theme, song ngữ Việt - Anh, kế thừa ngôn ngữ thiết kế từ hệ sinh thái [tsbyin-cv](https://tsbyin.dev).

---

## 📖 Hướng dẫn đăng ký Subdomain

Để đăng ký subdomain mới (ví dụ: `yourname.tsbyin.io.vn`), bạn chỉ cần làm theo các bước sau:

### 1. Fork repository
Fork repository này về tài khoản GitHub của bạn.

### 2. Tạo file cấu hình JSON
Tạo file mới trong thư mục `domains/` với tên file là subdomain bạn muốn đăng ký:
- Đường dẫn: `domains/<subdomain>.json` (ví dụ: `domains/yourname.json` sẽ cấp phát `yourname.tsbyin.io.vn`).

### 3. Cấu hình nội dung file
Nội dung file JSON mẫu:
```json
{
  "owner": {
    "github": "<your-github-username>",
    "email": "<your-email>"
  },
  "records": [
    {
      "type": "CNAME",
      "name": "@",
      "value": "<your-github-username>.github.io",
      "proxied": false
    }
  ]
}
```

#### Quy ước bản ghi (`records`):
- `name`: 
  - `"@"`: Trỏ trực tiếp cho `subdomain.tsbyin.io.vn`.
  - `"sub"` (ví dụ `"api"`): Trỏ cho `api.subdomain.tsbyin.io.vn`.
- `type`: Chỉ hỗ trợ các loại bản ghi: `A`, `AAAA`, `CNAME`, `TXT`.
- `proxied`: `true` hoặc `false` (bản ghi `TXT` không được bật proxied).
- `owner.github`: Bắt buộc phải trùng khớp với tài khoản GitHub tạo Pull Request.

### 4. Tạo Pull Request (PR)
- Tạo Pull Request từ branch của bạn vào branch `main` của repository này.
- Hệ thống GitHub Actions sẽ tự động kiểm tra định dạng và quyền hạn (`pr-check.yml`).
- Khi PR được merge, hệ thống sẽ tự động cập nhật bản ghi DNS lên Cloudflare (`deploy-dns.yml`).

---

## 🛡️ Quy định & Cơ chế bảo mật

- **Subdomain hợp lệ:** Dài từ 3 đến 32 ký tự, chỉ gồm chữ thường `a-z`, số `0-9` và dấu gạch ngang `-`. Không bắt đầu hoặc kết thúc bằng dấu `-`.
- **Subdomain bảo lưu (Reserved Names):** Các từ khóa hệ thống, giao thức DNS, mail tự động, tên thương hiệu và định danh nhạy cảm (`admin`, `auth`, `login`, `billing`, `tsbyin`, `dns`, `acme`,...) được bảo lưu.
- **Chặn dải IP riêng tư (SSRF Guard):** Không cho phép trỏ bản ghi A/AAAA về IP nội bộ (`127.0.0.1`, `10.0.0.0/8`, `192.168.0.0/16`, `172.16.0.0/12`,...). Ngoại trừ `192.0.2.1` khi bật Cloudflare Proxied.
- **Chặn CNAME nguy hiểm:** Cấm trỏ CNAME về các dịch vụ tunnel tạm thời hoặc dễ bị lạm dụng (`*.trycloudflare.com`, `*.cfargotunnel.com`, `*.workers.dev`, `*.r2.dev`, `*.ts.net`,...).
- **Bảo vệ quyền sở hữu:** Người khác không thể chỉnh sửa hoặc xóa file subdomain thuộc quyền sở hữu của bạn.
- **Số lượng bản ghi:** Tối đa 10 bản ghi cho mỗi subdomain.
- **Nghiêm cấm:** Sử dụng subdomain cho mục đích lừa đảo (phishing), phát tán mã độc (malware), spam hoặc các hành vi vi phạm pháp luật. Các subdomain vi phạm sẽ bị thu hồi ngay lập tức mà không cần báo trước.

---

## ⚙️ Cấu trúc thư mục

```plaintext
├── assets/                 # Logo, favicon và icon từ hệ sinh thái tsbyin-cv
├── domains/
│   └── demo.json           # File mẫu tham khảo
├── domains.json            # Danh mục subdomain đang hoạt động (dùng cho web)
├── scripts/
│   ├── validate_pr.py      # Kiểm tra bảo mật & định dạng khi có PR
│   └── sync_dns.py         # Đồng bộ trạng thái DNS lên Cloudflare
├── .github/
│   └── workflows/
│       ├── pr-check.yml    # Workflow chạy CI khi mở PR
│       └── deploy-dns.yml  # Workflow deploy DNS khi merge vào main
├── index.html              # Trang web tra cứu subdomain & tài liệu hướng dẫn
└── README.md
```
