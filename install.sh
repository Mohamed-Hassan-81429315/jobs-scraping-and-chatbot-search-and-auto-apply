#!/usr/bin/env bash
# Usage: ./install.sh /path/to/jobs-scraping-and-chatbot-search-and-auto-apply
set -euo pipefail
REPO="${1:?Pass the repo root path}"
KIT="$(cd "$(dirname "$0")" && pwd)"
BE="$REPO/jobs-backend"; FE="$REPO/jobs-frontend"
[ -d "$BE" ] && [ -d "$FE" ] || { echo "jobs-backend / jobs-frontend not found in $REPO"; exit 1; }

# ---- backend ----
cp "$KIT/backend/app/Http/Controllers/AuthController.php" "$BE/app/Http/Controllers/"
mkdir -p "$BE/tests/Feature" && cp "$KIT/backend/tests/Feature/AuthTest.php" "$BE/tests/Feature/"
if ! grep -q "AuthController" "$BE/routes/api.php" 2>/dev/null; then
  { echo; echo "use App\\Http\\Controllers\\AuthController;"; tail -n +2 "$KIT/backend/routes/api-auth-block.php" | grep -v '^// ADD'; } >> "$BE/routes/api.php"
  echo "Appended auth routes to routes/api.php (check the 'use' lines sit at the top of the file)."
fi

# ---- frontend ----
cp -R "$KIT/frontend/app/." "$FE/app/"
mkdir -p "$FE/components" "$FE/lib" && cp -R "$KIT/frontend/components/." "$FE/components/" && cp "$KIT/frontend/lib/brand.js" "$KIT/frontend/lib/session.js" "$FE/lib/"
cp "$KIT/frontend/public/logo.svg" "$FE/public/"
[ -f "$FE/.env.local" ] || cp "$KIT/frontend/.env.example" "$FE/.env.local"

cp "$KIT/frontend/middleware.js" "$FE/middleware.js"
# Next.js 16 renamed middleware -> proxy
if grep -Eq '"next": *"[^0-9]*(1[6-9]|[2-9][0-9])\.' "$FE/package.json"; then
  mv "$FE/middleware.js" "$FE/proxy.js" && sed -i 's/export function middleware/export function proxy/' "$FE/proxy.js"
  echo "Next 16+ detected: installed proxy.js"
fi

# The repo has BOTH .js and .tsx versions of layout/page. Next.js can only use one, and the .tsx
# boilerplate may be the one that wins, which would hide the new pages/header. Keep the .js ones.
for f in layout page; do
  if [ -f "$FE/app/$f.tsx" ] && [ -f "$FE/app/$f.js" ]; then
    mv "$FE/app/$f.tsx" "$FE/app/$f.tsx.bak" && echo "Moved app/$f.tsx -> $f.tsx.bak"
  fi
done
rm -rf "$FE/.next"   # clear stale build cache so the new routes are picked up

echo
cp "$KIT/doctor.sh" "$REPO/doctor.sh"; chmod +x "$REPO/doctor.sh"
echo "Now run: $REPO/doctor.sh"
echo "Manual steps left (see README-INSTALL.md): 1) AppServiceProvider snippet  2) .env additions  3) User model HasApiTokens  4) php artisan migrate"
