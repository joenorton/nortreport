# NORT REPORT — zero-js, static, drudge-style front page

Single page. Three columns. No JavaScript. Built from `links.yml` via `build.py`.  
Deployed to GitHub Pages by an Action on push and every 15 minutes.

## Quickstart
```bash
pip install pyyaml
python build.py
python -m http.server -d public 8080
```

Open [http://localhost:8080](http://localhost:8080)

## Edit Content

* Add/edit links in `links.yml`. Fields:

  * `title`, `url`, `lane` (`top|geo|mkts`), `priority` (int), `added_at` (ISO8601)
  * `id` optional; if omitted, a stable hash is used.
* Update `site.title`, `site.site_url`.

## Archives & RSS

* Each build writes `public/archive/YYYY-MM-DD.html` (snapshot of the current page).
* RSS at `/rss.xml` includes the top `site.rss_count` items across lanes.

## Deploy (GitHub Pages)

1. Create repo and push.
2. Enable **Pages**: Settings → Pages → Build from GitHub Actions.
3. Configure custom domain in Settings → Pages, add `CNAME` file or rely on the action.
4. Set DNS:

   * `CNAME` `www.nortreport.com` → `<username>.github.io`
   * For apex, either GitHub A records (185.199.108.153/154/155/156) or put Cloudflare in front with CNAME flattening.

## Operational Notes

* Scheduled builds are best-effort; don't expect exact 15-minute cadence.
* Front page stays under ~20kb inline CSS; no external fonts or JS.
* Click tracking: use Cloudflare (proxy) access logs or Netlify if you later want `/r/:id` redirects. Not supported on GH Pages without a worker.

## License

MIT (or whatever you prefer).
