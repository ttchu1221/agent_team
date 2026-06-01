const http = require("http");
const { parse } = require("url");
const next = require("next");

const dev = process.env.NODE_ENV !== "production";
const hostname = "0.0.0.0";
const port = parseInt(process.env.PORT || "3000", 10);

const app = next({ dev, hostname, port });
const handle = app.getRequestHandler();

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

app.prepare().then(() => {
  http
    .createServer((req, res) => {
      try {
        const parsedUrl = parse(req.url, true);

        if (parsedUrl.pathname.startsWith("/api/")) {
          const target = new URL(req.url, BACKEND_URL);
          const proxyReq = http.request(
            target,
            {
              method: req.method,
              headers: { ...req.headers, host: target.host },
              timeout: 300_000,
            },
            (proxyRes) => {
              const headers = { ...proxyRes.headers };
              // 禁止反向代理/CDN 缓冲 SSE
              headers["x-accel-buffering"] = "no";
              headers["cache-control"] = "no-cache";
              delete headers["content-length"]; // 流式响应不能有 content-length

              res.writeHead(proxyRes.statusCode, headers);
              proxyRes.pipe(res, { end: true });
            }
          );

          proxyReq.on("error", (err) => {
            console.error("Proxy error:", err.message);
            if (!res.headersSent) {
              res.writeHead(502, { "Content-Type": "application/json" });
            }
            res.end(JSON.stringify({ detail: `Backend error: ${err.message}` }));
          });

          if (req.method !== "GET" && req.method !== "HEAD") {
            req.pipe(proxyReq, { end: true });
          } else {
            proxyReq.end();
          }
          return;
        }

        handle(req, res, parsedUrl);
      } catch (err) {
        console.error("Error handling", req.url, err);
        res.statusCode = 500;
        res.end("internal server error");
      }
    })
    .once("error", (err) => {
      console.error(err);
      process.exit(1);
    })
    .listen(port, hostname, () => {
      console.log(`> Ready on http://${hostname}:${port}`);
    });
});
