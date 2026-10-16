// Cloudflare Worker：鉴权（HTTP Basic Auth）+ 提供 docs/ 静态网站
//
// 账号密码来自 Worker 的「环境变量 / 密钥」：
//     BASIC_USER  用户名
//     BASIC_PASS  密码
// 建议使用「英文字母 + 数字」（本文件用 atob 解码，非 ASCII 可能异常）。
// 未配置账号密码时，出于安全直接拒绝访问（避免网站被误公开）。

export default {
  async fetch(request, env) {
    const expectedUser = env.BASIC_USER;
    const expectedPass = env.BASIC_PASS;

    if (!expectedUser || !expectedPass) {
      return new Response(
        "Server not configured: missing BASIC_USER / BASIC_PASS.",
        { status: 500 }
      );
    }

    const auth = request.headers.get("Authorization") || "";
    if (auth.startsWith("Basic ")) {
      let decoded = "";
      try {
        decoded = atob(auth.slice(6).trim());
      } catch (e) {
        decoded = "";
      }
      const sep = decoded.indexOf(":");
      if (sep >= 0) {
        const user = decoded.slice(0, sep);
        const pass = decoded.slice(sep + 1);
        if (user === expectedUser && pass === expectedPass) {
          return env.ASSETS.fetch(request);
        }
      }
    }

    return new Response("Authentication required", {
      status: 401,
      headers: {
        "WWW-Authenticate": 'Basic realm="AI Daily Brief", charset="UTF-8"',
        "Cache-Control": "no-store",
      },
    });
  },
};
