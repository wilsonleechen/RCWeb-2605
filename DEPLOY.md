# Rexpand · 部署指南

> 当前官网 `rexpandcareer.com` / `www.rexpandcareer.com` 由阿里云 OSS 桶
> `rexpand-official-website` 提供页面文件，经 DCDN 分发。以下 Vercel、Netlify 等配置是
> 备选平台说明，不是当前官网的发布路径。

## 当前官网发布前检查

`index.html` 是网站内容的主版本。`production-index.html`、`production-offer.html`
是生成过的发布快照；发布时必须先与最新页面内容同步，不能直接使用旧快照。
OSS 中每个 `.html` 子页也包含完整页面代码，更新公共文案或样式时要同步这些子页，
并刷新两个域名对应的 DCDN 缓存。

**上传前必须运行：**

```bash
python3 scripts/check_site_release.py --live
```

检查失败时不要上传。它会阻止旧发布快照、已删除服务文案的回归，以及遗漏线上新增文章。
若套餐内容经过确认后再次调整，应与页面修改一起更新检查脚本中的对应规则。
如果本次准备上传一批独立的 `.html` 子页，还要对**本次生成的发布目录**运行
`python3 scripts/check_site_release.py --live --pages-dir /path/to/generated-pages`；
脚本会检查每个完整子页的页面主体是否与最新 `index.html` 一致。
这道检查只有在所有发布流程都执行它时才有效：官网应只保留一个拥有
`rexpand-official-website` 写入权限的发布身份，找出并停用旧发布任务，
再收回其他 RAM 用户或 AccessKey 的 `oss:PutObject` 权限。OSS 版本控制可用于恢复历史版本，
但不能阻止有写入权限的旧任务覆盖当前页面。

Git 远端 `main` 若仍是旧版，也不能作为发布源。每次发布后应把本次使用的
`index.html`、发布检查脚本和相关内容同步到真正的发布仓库；文章生成任务应基于
最新页面添加文章，不能从旧页面快照重新生成整个网站。

发布前至少核对首页与 `/offer` 的页面内容、套餐表和新文章；发布后再读取线上页面核对。
2026-10-12 曾有一次发布使用较早的页面快照，导致新版套餐和移动端修改被覆盖。

网站主体是一个 single-page app，`index.html` 包含页面结构和路由逻辑；浏览器通过 `history.pushState` 显示 `/about`、`/cases`、`/offer` 等页面。当前 OSS 还保存了带各自 SEO 元数据的完整 `.html` 子页副本。

部署的关键：**服务器要把所有未知路径都重写到 `/index.html`**。JS router 会读 `location.pathname` 并显示对应页面。

---

## 1. 静态文件清单

若迁移到支持 SPA fallback 的平台，基础文件包括：

```
index.html              ← 主入口（包含所有页面 + JS router + SEO meta）
sitemap.xml             ← Google / Baidu 用
robots.txt              ← 爬虫指南
/media/                 ← 团队照片、视频、食物照片等
```

加上一个 host 配置文件（按平台选一个）：
- `vercel.json`     → Vercel
- `netlify.toml`    → Netlify
- `_redirects`      → Cloudflare Pages / Netlify (备用)
- `.htaccess`       → Apache shared hosting

---

## 2. 按平台部署

### Vercel（推荐）

```bash
npm i -g vercel
vercel --prod
```

Vercel 会自动读取 `vercel.json`。完成后绑定域名 `rexpandcareer.com` 即可。

### Cloudflare Pages

1. 上传整个目录（不需要 build command，直接 deploy static）
2. `_redirects` 会自动生效
3. Custom domain → `rexpandcareer.com`

### Netlify

```bash
npm i -g netlify-cli
netlify deploy --prod --dir=.
```

`netlify.toml` 自动生效。

### nginx (VPS / 自建)

`/etc/nginx/sites-available/rexpand`:

```nginx
server {
    listen 443 ssl http2;
    server_name rexpandcareer.com;
    root /var/www/rexpand;
    index index.html;

    # SPA fallback — unknown routes → index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Long cache for static media
    location /media/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location = /sitemap.xml {
        add_header Content-Type "application/xml; charset=utf-8";
    }

    # Security
    add_header X-Frame-Options "SAMEORIGIN";
    add_header X-Content-Type-Options "nosniff";
    add_header Referrer-Policy "strict-origin-when-cross-origin";
}

server {
    listen 80;
    server_name rexpandcareer.com www.rexpandcareer.com;
    return 301 https://rexpandcareer.com$request_uri;
}
```

### Apache shared hosting

把 `.htaccess` 放在 `public_html/` 根目录即可。

---

## 3. 域名 DNS 设置

| Record | Name | Value |
|---|---|---|
| A     | @   | (主机 IP) |
| CNAME | www | rexpandcareer.com |

对于 Vercel / Netlify / Cloudflare Pages，按它们 dashboard 给的 CNAME 配置即可。

---

## 4. SEO 上线后必做

### 4.1 提交搜索引擎

- **Google Search Console**: 添加 `rexpandcareer.com`，验证后提交 `/sitemap.xml`
- **Baidu 站长平台**: 同上 (https://ziyuan.baidu.com/)
- **Bing Webmaster**: https://www.bing.com/webmasters

### 4.2 验证富媒体卡片

- Google Rich Results: https://search.google.com/test/rich-results?url=https%3A%2F%2Frexpandcareer.com
- Facebook OG Debugger: https://developers.facebook.com/tools/debug/?q=https%3A%2F%2Frexpandcareer.com
- Twitter Card Validator: https://cards-dev.twitter.com/validator
- LinkedIn Post Inspector: https://www.linkedin.com/post-inspector/

### 4.3 移动端友好测试

- https://search.google.com/test/mobile-friendly
- 用真实手机访问每一页，检查 hamburger 菜单 + 横向滚动

### 4.4 性能 & Core Web Vitals

- https://pagespeed.web.dev/?url=https%3A%2F%2Frexpandcareer.com

---

## 5. 可选优化

### 把大图压缩 / 转 WebP

```bash
# 安装 cwebp 后批量转
for f in media/team/*.{jpg,png}; do
  cwebp -q 82 "$f" -o "${f%.*}.webp"
done
```

然后用 `<picture>` 标签同时支持 WebP + 兼容回退。当前的 `<img>` 直接用 jpg/png 已经足够，浏览器 + Cloudflare/Vercel 的 image optimizer 会自动转 WebP。

### CDN 前置

如果国内访问慢，建议套一层 Cloudflare 或腾讯云 CDN。
