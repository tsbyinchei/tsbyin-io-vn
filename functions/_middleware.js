export async function onRequest(context) {
  const url = new URL(context.request.url);
  const hostname = url.hostname.toLowerCase();

  // 1. Khi truy cập vào doc.sub.tsbyin.io.vn
  if (hostname === "doc.sub.tsbyin.io.vn") {
    // Nếu vô tình vào /index.html -> chuyển hướng về trang chủ tra cứu sub.tsbyin.io.vn
    if (url.pathname === "/index.html") {
      return Response.redirect("https://sub.tsbyin.io.vn/", 302);
    }
    // Nếu vào root / hoặc /doc hoặc /doc.html -> phục vụ nội dung doc.html
    if (url.pathname === "/" || url.pathname === "" || url.pathname === "/doc" || url.pathname === "/doc/" || url.pathname === "/doc.html") {
      url.pathname = "/doc.html";
      return context.env.ASSETS.fetch(url);
    }
  }

  // 2. Khi truy cập vào sub.tsbyin.io.vn (hoặc preview pages.dev) mà bấm vào /doc hoặc /doc.html
  // -> Chuyển hướng sang domain chính thức doc.sub.tsbyin.io.vn
  if (hostname === "sub.tsbyin.io.vn") {
    if (url.pathname === "/doc" || url.pathname === "/doc/" || url.pathname === "/doc.html") {
      return Response.redirect("https://doc.sub.tsbyin.io.vn/", 302);
    }
  }

  // 3. Mặc định (sub.tsbyin.io.vn vào / sẽ phục vụ index.html, các file assets/ giữ nguyên)
  return context.next();
}
