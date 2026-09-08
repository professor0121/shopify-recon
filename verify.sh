#!/usr/bin/env bash
#
# verify.sh - one-command self-test for Shopify Recon.
#
# Run this FIRST after cloning the repo. It proves the toolkit is wired up
# correctly without you needing to read every file or trust the README:
#
#   ./verify.sh              # phases 1-3: deps, syntax, dry-run smoke (offline)
#   ./verify.sh --golden     # also runs a real clone and diffs vs golden fixture
#   ./verify.sh --capture URL # run a real clone of URL and SAVE it as the golden
#
# Phases 1-3 make ZERO network calls and finish in seconds. Use them in CI or
# on a fresh machine. --golden does a real clone (needs network) and is the
# full regression check.
#
# Exit 0 = all phases passed. Exit 1 = something failed (details printed).

set -uo pipefail

cd "$(dirname "$0")"

# ---- colors (fall back to plain if not a tty) ----
if [ -t 1 ]; then
  GREEN=$'\033[0;32m'; RED=$'\033[0;31m'; YEL=$'\033[0;33m'; BOLD=$'\033[1m'; NC=$'\033[0m'
else
  GREEN=''; RED=''; YEL=''; BOLD=''; NC=''
fi

PASS_N=0; FAIL_N=0
GOLDEN="tests/golden/rothys.json"
TEST_URL="https://rothys.com"

pass() { echo "${GREEN}  PASS${NC} $1"; PASS_N=$((PASS_N+1)); }
fail() { echo "${RED}  FAIL${NC} $1"; FAIL_N=$((FAIL_N+1)); }
hdr()  { echo; echo "${BOLD}== $1 ==${NC}"; }

# ---- phase 1: dependencies ----
hdr "Phase 1/4  Dependencies"
if python3 -c "import requests, bs4, rich, lxml" 2>/dev/null; then
  pass "requests, beautifulsoup4, lxml, rich all importable"
else
  fail "missing dependency - run: pip install -r requirements.txt"
  python3 -c "import requests" 2>/dev/null || echo "       -> requests missing"
  python3 -c "import bs4"      2>/dev/null || echo "       -> beautifulsoup4 missing"
  python3 -c "import lxml"     2>/dev/null || echo "       -> lxml missing (BeautifulSoup tree builder)"
  python3 -c "import rich"     2>/dev/null || echo "       -> rich missing"
fi

# lxml is requested by name as a BeautifulSoup tree builder in many tools, so
# prove the parser actually works rather than just importing the module.
if python3 -c "from bs4 import BeautifulSoup; BeautifulSoup('<a/>', 'lxml')" 2>/dev/null; then
  pass "BeautifulSoup 'lxml' tree builder works"
else
  fail "BeautifulSoup cannot find the 'lxml' parser - run: pip install -r requirements.txt"
fi

# ---- phase 2: syntax of every python tool ----
hdr "Phase 2/4  Syntax check (all .py tools)"
SYNTAX_BAD=0
for f in *.py; do
  if ! python3 -c "import ast,sys; ast.parse(open('$f').read())" 2>/dev/null; then
    fail "syntax error in $f"
    SYNTAX_BAD=$((SYNTAX_BAD+1))
  fi
done
[ "$SYNTAX_BAD" -eq 0 ] && pass "all $(ls *.py | wc -l | tr -d ' ') python tools parse clean"

# ---- phase 3: dry-run smoke (offline, no network) ----
hdr "Phase 3/4  Dry-run smoke (offline)"
DRY_OUT="$(python3 shopify-recon.py "$TEST_URL" /tmp/recon-verify-dry --dry-run 2>&1)"
if echo "$DRY_OUT" | grep -q "steps would run"; then
  N_STEPS="$(echo "$DRY_OUT" | grep -oE '[0-9]+ steps would run' | grep -oE '^[0-9]+')"
  pass "pipeline planned $N_STEPS steps, no network calls"
else
  fail "dry-run did not produce a plan"
  echo "$DRY_OUT" | tail -5 | sed 's/^/       /'
fi
rm -rf /tmp/recon-verify-dry 2>/dev/null

# ---- phase 4: golden regression (real clone, needs network) ----
if [ "${1:-}" = "--capture" ]; then
  CAP_URL="${2:-$TEST_URL}"
  hdr "Capture golden  ($CAP_URL)"
  echo "  Running a real clone to capture the golden fixture..."
  python3 shopify-recon.py "$CAP_URL" /tmp/recon-golden-capture >/dev/null 2>&1
  python3 verify_manifest.py capture /tmp/recon-golden-capture "$GOLDEN"
  rm -rf /tmp/recon-golden-capture 2>/dev/null
  echo "${GREEN}Golden captured at $GOLDEN${NC}"
  exit 0
fi

if [ "${1:-}" = "--golden" ]; then
  hdr "Phase 4/4  Golden regression (real clone)"
  if [ ! -f "$GOLDEN" ]; then
    echo "${YEL}  SKIP${NC} no golden fixture yet - run ./verify.sh --capture first"
  else
    echo "  Running a real clone of $TEST_URL (needs network)..."
    python3 shopify-recon.py "$TEST_URL" /tmp/recon-verify-real >/dev/null 2>&1
    if python3 verify_manifest.py compare /tmp/recon-verify-real "$GOLDEN"; then
      pass "clone output matches golden fixture"
    else
      fail "clone output regressed vs golden"
    fi
    rm -rf /tmp/recon-verify-real 2>/dev/null
  fi
else
  hdr "Phase 4/4  Golden regression"
  echo "${YEL}  SKIP${NC} offline mode - run ./verify.sh --golden for the full check"
fi

# ---- summary ----
echo
echo "${BOLD}────────────────────────────────────────${NC}"
if [ "$FAIL_N" -eq 0 ]; then
  echo "${GREEN}${BOLD}  ALL CHECKS PASSED${NC}  ($PASS_N passed)"
  echo "${BOLD}────────────────────────────────────────${NC}"
  exit 0
else
  echo "${RED}${BOLD}  $FAIL_N CHECK(S) FAILED${NC}  ($PASS_N passed)"
  echo "${BOLD}────────────────────────────────────────${NC}"
  exit 1
fi
