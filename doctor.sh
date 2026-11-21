#!/usr/bin/env bash
# Usage: ./doctor.sh   (run from the repo root). Tells you exactly what is missing.
R="$(cd "$(dirname "$0")" && pwd)"; FE="$R/jobs-frontend"; BE="$R/jobs-backend"; bad=0
ok(){ echo "  OK   $1"; }; no(){ echo "  FAIL $1"; bad=1; }
chk(){ [ -e "$1" ] && ok "$2" || no "$2  ->  missing $1"; }

echo "Frontend files"
for f in app/login/page.js app/register/page.js app/forgot-password/page.js app/reset-password/page.js \
         app/account/password/page.js "app/api/auth/[action]/route.js" "app/api/backend/[...path]/route.js" \
         components/AuthForm.js components/SiteHeader.js lib/session.js lib/brand.js app/brand.css; do chk "$FE/$f" "$f"; done
grep -q "brand.css" "$FE/app/layout.js" 2>/dev/null && ok "layout.js imports brand.css + SiteHeader (new layout active)" || no "app/layout.js is NOT the new layout (header with Sign in / Create account will not show)"
for f in layout page; do [ -f "$FE/app/$f.tsx" ] && no "app/$f.tsx still exists next to $f.js. Delete or rename it"; done
grep -q '"@/\*"' "$FE/tsconfig.json" 2>/dev/null && ok "'@/' import alias configured" || no "tsconfig.json needs: \"paths\": { \"@/*\": [\"./*\"] }"
[ -f "$FE/.env.local" ] && grep -q "API_URL" "$FE/.env.local" && ok ".env.local has API_URL" || no ".env.local needs API_URL=http://127.0.0.1:8000/api"

echo "Backend"
chk "$BE/app/Http/Controllers/AuthController.php" "AuthController.php"
grep -q "AuthController" "$BE/routes/api.php" 2>/dev/null && ok "routes/api.php has auth routes" || no "routes/api.php has no auth routes"
grep -q "HasApiTokens" "$BE/app/Models/User.php" 2>/dev/null && ok "User model uses HasApiTokens" || no "User model needs: use Laravel\\Sanctum\\HasApiTokens; + use HasApiTokens in the class"
if command -v php >/dev/null; then
  (cd "$BE" && php artisan route:list --path=api 2>/dev/null | grep -Eq "login|register") && ok "Laravel lists /api/login and /api/register" || no "php artisan route:list does not show login/register (run: php artisan route:clear)"
fi

echo "Live check"
API=$(grep -E '^API_URL=' "$FE/.env.local" 2>/dev/null | cut -d= -f2); API=${API:-http://127.0.0.1:8000/api}
code=$(curl -s -o /dev/null -w '%{http_code}' -H 'Accept: application/json' "$API/me" 2>/dev/null)
[ "$code" = "401" ] && ok "Laravel API reachable at $API (401 = auth working)" || no "Laravel API at $API returned '$code' (expected 401). Is 'php artisan serve' running?"

echo; [ $bad = 0 ] && echo "All good. Open http://localhost:3000 and click Sign in." || echo "Fix the FAIL lines above, then restart 'npm run dev'."
