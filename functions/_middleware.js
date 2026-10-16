// Cloudflare Pages 鉴权中间件（HTTP Basic Auth）
//
// 作用：在任何人访问网站内容之前先检查用户名/密码，未通过一律返回 401。
// 账号密码从 Cloudflare Pages 项目的「环境变量」读取：
//     BASIC_USER  用户名
//     BASIC_PASS  密码
// 建议使用「英文字母 + 数字」的账号密码（本文件用 atob 解码，非 ASCII 可能异常）。
//
// 未配置账号密码时，出于安全会直接拒绝访问（避免网站被误公开）。

export async function onRequest(context) {
  const { request, next, env } = context;

  const unauthorized = () =>
    new Response("Authentication required", {
      status: 401,
      headers: {
        "WWW-Authenticate": 'Basic realm="AI Daily Brief", charset="UTF-8"',
        "Cache-Control": "no-store",
      },
    });

  const expectedUser = env.BASIC_USER;
  const expectedPass = env.BASIC_PASS;

  if (!expectedUser || !expectedPass) {
    return new Response(
      "Server not configured: missing BASIC_USER / BASIC_PASS environment variables.",
      { status: 500 }
    );
  }

  const auth = request.headers.get("Authorization") || "";
  if (!auth.startsWith("Basic ")) return unauthorized();

  let decoded = "";
  try {
    decoded = atob(auth.slice(6).trim());
  } catch (e) {
    return unauthorized();
  }

  const sep = decoded.indexOf(":");
  if (sep < 0) return unauthorized();
  const user = decoded.slice(0, sep);
  const pass = decoded.slice(sep + 1);

  if (user === expectedUser && pass === expectedPass) {
    return next();
  }
  return unauthorized();
}
