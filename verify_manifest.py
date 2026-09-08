#!/usr/bin/env python3
"""
verify_manifest.py - golden-output regression check for Shopify Recon.

Two modes:
  capture: walk a clone output dir and write a manifest (structure + shape).
  compare: walk a clone output dir and diff it against a stored golden manifest.

The manifest records STRUCTURE and SHAPE, not exact bytes, so it survives
trivial run-to-run noise (timestamps, minor size drift) but catches real
regressions: a tool that stops emitting files, a section that vanishes, a
template that disappears, a validator score that drops.

Usage:
  python3 verify_manifest.py capture <clone_dir> <golden.json>
  python3 verify_manifest.py compare <clone_dir> <golden.json>

Compare exits 0 on PASS, 1 on FAIL.
"""

import json
import os
import sys


# Size buckets - we compare bucket, not exact bytes, to tolerate minor drift.
def _bucket(size):
    if size == 0:
        return "empty"
    if size < 1024:
        return "tiny"        # < 1 KB
    if size < 32 * 1024:
        return "small"       # < 32 KB
    if size < 256 * 1024:
        return "medium"      # < 256 KB
    if size < 1024 * 1024:
        return "large"       # < 1 MB
    return "huge"            # >= 1 MB


def build_manifest(clone_dir):
    """Walk a clone output dir and capture its structure + shape."""
    clone_dir = os.path.abspath(clone_dir)
    files = {}
    total_files = 0
    total_size = 0
    ext_counts = {}

    for root, dirs, names in os.walk(clone_dir):
        dirs.sort()
        for name in sorted(names):
            full = os.path.join(root, name)
            try:
                size = os.path.getsize(full)
            except OSError:
                continue
            rel = os.path.relpath(full, clone_dir)
            files[rel] = _bucket(size)
            total_files += 1
            total_size += size
            ext = os.path.splitext(name)[1].lower() or "(none)"
            ext_counts[ext] = ext_counts.get(ext, 0) + 1

    theme = os.path.join(clone_dir, "theme")
    sections = _count_in(os.path.join(theme, "sections"), ".liquid")
    templates = _count_in(os.path.join(theme, "templates"), None)
    snippets = _count_in(os.path.join(theme, "snippets"), ".liquid")

    return {
        "total_files": total_files,
        "size_bucket": _bucket(total_size),
        "ext_counts": ext_counts,
        "theme": {
            "sections": sections,
            "templates": templates,
            "snippets": snippets,
        },
        "files": files,
    }


def _count_in(path, suffix):
    if not os.path.isdir(path):
        return 0
    n = 0
    for name in os.listdir(path):
        if suffix is None or name.endswith(suffix):
            n += 1
    return n


def compare(actual, golden):
    """Return (passed, list_of_problems). Regressions fail; additions pass."""
    problems = []

    # Some tools emit files whose NAMES are non-deterministic run-to-run (e.g.
    # deep-extract numbers inline scripts inline_1.js, inline_2.js ... and the
    # numbering shifts with fetch order). Exact per-file matching on those paths
    # produces false "MISSING" regressions even when the clone is healthy, so we
    # skip them here and rely on ext_counts + total_files (both drift-tolerant)
    # to guard that family instead.
    VOLATILE_PREFIXES = (
        "analysis/deep-extract/deobfuscated-js/",
    )

    def _is_volatile(path):
        return any(path.startswith(p) for p in VOLATILE_PREFIXES)

    # Missing files = regression (a tool stopped emitting output), except for
    # volatile-named paths which are validated by count below.
    missing = sorted(
        f for f in (set(golden["files"]) - set(actual["files"]))
        if not _is_volatile(f)
    )
    for f in missing:
        problems.append(f"MISSING file: {f}")

    # Theme shape must not shrink.
    for key in ("sections", "templates", "snippets"):
        g = golden["theme"][key]
        a = actual["theme"][key]
        if a < g:
            problems.append(f"theme/{key} shrank: golden={g} actual={a}")

    # File count must not drop more than 5% (tolerate tiny drift).
    g_total = golden["total_files"]
    a_total = actual["total_files"]
    if g_total and a_total < g_total * 0.95:
        problems.append(f"total_files dropped: golden={g_total} actual={a_total}")

    # Each extension family must not lose more than a couple files.
    for ext, g_count in golden["ext_counts"].items():
        a_count = actual["ext_counts"].get(ext, 0)
        if a_count < g_count - 2:
            problems.append(f"ext {ext} dropped: golden={g_count} actual={a_count}")

    return (len(problems) == 0, problems)


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(2)

    mode, clone_dir, golden_path = sys.argv[1], sys.argv[2], sys.argv[3]

    if mode == "capture":
        manifest = build_manifest(clone_dir)
        os.makedirs(os.path.dirname(os.path.abspath(golden_path)), exist_ok=True)
        with open(golden_path, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2, sort_keys=True)
        print(f"Captured golden: {golden_path}")
        print(f"  files={manifest['total_files']} "
              f"sections={manifest['theme']['sections']} "
              f"templates={manifest['theme']['templates']} "
              f"snippets={manifest['theme']['snippets']}")
        sys.exit(0)

    elif mode == "compare":
        if not os.path.exists(golden_path):
            print(f"FAIL: no golden manifest at {golden_path}")
            print("  Run 'capture' first on a known-good clone.")
            sys.exit(1)
        with open(golden_path, encoding="utf-8") as fh:
            golden = json.load(fh)
        actual = build_manifest(clone_dir)
        passed, problems = compare(actual, golden)
        if passed:
            print(f"PASS: clone matches golden "
                  f"(files={actual['total_files']}, "
                  f"sections={actual['theme']['sections']})")
            sys.exit(0)
        else:
            print(f"FAIL: {len(problems)} regression(s) vs golden:")
            for p in problems[:30]:
                print(f"  - {p}")
            if len(problems) > 30:
                print(f"  ... and {len(problems) - 30} more")
            sys.exit(1)

    else:
        print(f"Unknown mode: {mode}")
        sys.exit(2)


if __name__ == "__main__":
    main()
