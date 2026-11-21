# Applyra auth + brand kit

Drop-in for **jobs-backend** (Laravel + Sanctum) and **jobs-frontend** (Next.js App Router).

## Install
```bash
./install.sh /path/to/jobs-scraping-and-chatbot-search-and-auto-apply
```

## Start both servers
```bash
cd jobs-backend  && php artisan serve          # http://127.0.0.1:8000
cd jobs-frontend && npm run dev                # http://localhost:3000
./doctor.sh                                    # from repo root: lists anything missing
```
Then open `http://localhost:3000/login` or `/register`. The header on every page has **Sign in / Create account**.

Want guests to land on the login screen first? Set `REQUIRE_AUTH=true` in `jobs-frontend/.env.local` (note: this hides job pages from search engines, so leave it off for SEO).

## Connecting your existing features to login
- **Server Components:** `import { apiFetch } from '@/lib/api'` then `await apiFetch('/jobs')`; the user's token is attached automatically.
- **Client components (chatbot, Apply button):** `fetch('/api/backend/jobs/12/apply', { method: 'POST' })`; the proxy adds the token. A 401 means "send to /login".
- **Laravel:** put action endpoints in `Route::middleware('auth:sanctum')` (see `backend/protect-existing-routes.php`).
- Put `<AuthCallout />` (from `components/AuthCallout.js`) at the top of `app/page.js` to show Sign in / Create account on the jobs home too.

## Backend (5 minutes)
1. `routes/api.php` gets the auth routes (the script appends them; verify the `use` lines).
2. In `app/Models/User.php` make sure you have `use Laravel\Sanctum\HasApiTokens;` and `use HasApiTokens, HasFactory, Notifiable;`.
3. Paste `backend/app-service-provider-snippet.php` into `AppServiceProvider::boot()` so reset emails link to the Next.js page.
4. Add `backend/env-additions.txt` to `jobs-backend/.env`.
5. `php artisan migrate` (the default users migration already creates `password_reset_tokens` and Sanctum's tokens table exists in your repo).
6. `php artisan test --filter=AuthTest`

## Frontend
```bash
cd jobs-frontend && npm run dev
```
Pages: `/login`, `/register`, `/forgot-password`, `/reset-password`, `/account`, `/account/password`.

## How auth works
Browser -> Next.js route handler (`/api/auth/*`) -> Laravel `/api/*`.
The Sanctum token is stored in an **httpOnly, SameSite=Lax cookie** set by Next.js, so JavaScript on the page can never read it (XSS-safe), and no CORS setup is needed.

## SEO checklist covered
Title template + meta description, canonical URLs, Open Graph + Twitter cards, dynamic OG image, `robots.txt`, `sitemap.xml`, web manifest, SVG favicon, JSON-LD (Organization + WebSite), `lang`, theme-color, skip link, landmarks, one `h1` per page, `noindex` on auth/account pages, keyboard focus styles, AA-contrast colors, dark mode, reduced-motion support.

Set `NEXT_PUBLIC_SITE_URL` to your production domain before deploying.
