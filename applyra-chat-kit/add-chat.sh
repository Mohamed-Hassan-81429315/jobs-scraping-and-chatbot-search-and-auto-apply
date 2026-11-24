#!/usr/bin/env bash
# Adds / updates the chat widget. Safe to re-run. Backs up every file it edits.
set -euo pipefail
KIT="$(cd "$(dirname "$0")" && pwd)"
DEST="${KIT_DEST:-/home/engineer-mohamed-hassan/Jobs and chatbot}"
BE="$DEST/jobs-backend"; FE="$DEST/jobs-frontend"
BK="$DEST/.chat-backup-$(date +%Y%m%d-%H%M%S)"; mkdir -p "$BK"
[ -d "$BE" ] && [ -d "$FE" ] || { echo "jobs-backend / jobs-frontend not found in: $DEST"; exit 1; }

# ---- backend: OpenAI chat (controller + services + config + tests) ----
mkdir -p "$BE/app/Services" "$BE/config" "$BE/tests/Feature"
for f in app/Http/Controllers/ChatController.php app/Services/JobFinder.php app/Services/OpenAIChat.php config/openai.php tests/Feature/ChatTest.php; do
  [ -f "$BE/$f" ] && mkdir -p "$BK/$(dirname "$f")" && cp -a "$BE/$f" "$BK/$f"
  cp "$KIT/backend/$f" "$BE/$f"; echo "  backend  $f"
done

# ---- .env: switch provider Mistral -> OpenAI (old MISTRAL_* lines are commented out, not deleted) ----
ENVF="$BE/.env"; touch "$ENVF"; cp -a "$ENVF" "$BK/.env"
sed -i -E 's/^(MISTRAL_[A-Z_]*=)/# replaced by OpenAI: \1/' "$ENVF"
grep -q '^OPENAI_API_KEY=' "$ENVF" || echo 'OPENAI_API_KEY=' >> "$ENVF"
grep -q '^OPENAI_MODEL='   "$ENVF" || echo 'OPENAI_MODEL=gpt-5.4-mini' >> "$ENVF"
grep -Eq '^OPENAI_API_KEY=.+' "$ENVF" || echo "  >>> Put your key in $ENVF  ->  OPENAI_API_KEY=sk-...   (chat uses the keyword fallback until you do)"
API="$BE/routes/api.php"; cp -a "$API" "$BK/api.php"
grep -Eq "['\"]/?chat['\"]" "$API" || {
  echo "Route::post('/chat', [\\App\\Http\\Controllers\\ChatController::class, 'message'])->middleware('throttle:30,1');" >> "$API"
  echo "  route + POST /api/chat"; }

# ---- frontend files (always refreshed so style updates apply) ----
mkdir -p "$FE/components/chat" "$FE/app/api/chat/user"
cp "$KIT"/frontend/components/chat/* "$FE/components/chat/"
cp "$KIT/frontend/app/api/chat/user/route.js" "$FE/app/api/chat/user/route.js"
[ -f "$FE/app/api/backend/[...path]/route.js" ] || echo "WARNING: app/api/backend/[...path]/route.js is missing (comes from the auth kit: run merge-kit.sh)."

# ---- Next.js can only use ONE layout and ONE page file; the .tsx boilerplate can win and hide everything ----
for f in layout page; do
  if [ -f "$FE/app/$f.tsx" ] && [ -f "$FE/app/$f.js" ]; then
    mv "$FE/app/$f.tsx" "$BK/$f.tsx" && echo "  moved duplicate app/$f.tsx out of the way (backup in $BK)"
  fi
done

# ---- mount the widget in whichever layout file exists ----
LAYOUT="$FE/app/layout.js"; [ -f "$LAYOUT" ] || LAYOUT="$FE/app/layout.tsx"
[ -f "$LAYOUT" ] || { echo "ERROR: no app/layout.js or layout.tsx found in $FE/app"; exit 1; }
cp -a "$LAYOUT" "$BK/$(basename "$LAYOUT").orig"
python3 - "$LAYOUT" <<'PY'
import re, sys
p = sys.argv[1]; s = open(p).read()
REL = "../components/chat/ChatWidget"          # relative: works even without the '@/' alias
s = s.replace("'@/components/chat/ChatWidget'", f"'{REL}'")   # repair earlier alias-based patch
if "ChatWidget" not in s:
    if "</body>" not in s:
        print("  Could not find </body>. Add manually:\n    import ChatWidget from '../components/chat/ChatWidget';\n    <ChatWidget />   (just before </body>)"); sys.exit(0)
    s = s.replace("</body>", "  <ChatWidget />\n      </body>", 1)
    imps = list(re.finditer(r"^import .*?;\s*$", s, re.M))
    line = f"import ChatWidget from '{REL}';"
    s = (s[:imps[-1].end()] + "\n" + line + s[imps[-1].end():]) if imps else (line + "\n" + s)
open(p, "w").write(s)
print("  layout ready:", p)
PY
grep -q "<ChatWidget" "$LAYOUT" && echo "  OK: <ChatWidget /> is mounted in $(basename "$LAYOUT")" || echo "  NOT mounted: add <ChatWidget /> manually"

rm -rf "$FE/.next"
echo; echo "Backups: $BK"
echo "1) cd \"$BE\" && php artisan config:clear && php artisan route:clear && php artisan test --filter=ChatTest"
echo "2) cd \"$FE\" && npm run dev"
echo "3) check:  curl -s http://localhost:3000 | grep -c 'Open job assistant chat'    (1 or more = the button is in the page)"
