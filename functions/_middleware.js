export async function onRequest(context) {
  const url = new URL(context.request.url);
  const hostname = url.hostname.toLowerCase();

  // 1. Nếu người dùng truy cập vào doc.sub.tsbyin.io.vn
  if (hostname === "doc.sub.tsbyin.io.vn") {
    // Nếu truy cập trang chủ / hoặc /index.html -> rewrite nội bộ sang doc.html
    if (url.pathname === "/" || url.pathname === "" || url.pathname === "/index.html") {
      url.pathname = "/doc.html";
      return context.env.ASSETS.fetch(url);
    }
  }

  // 2. Mặc định (sub.tsbyin.io.vn hoặc các request file tĩnh như assets/*)
  return context.next();
}
