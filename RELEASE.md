# gitwell — release process

Operational guide for maintainers publishing **frozen binaries** and GitHub Releases. End users installing from PyPI or source should follow [README.md](README.md).

---

## Naming and terminology

| Term | Meaning |
|------|---------|
| **gitwell** | CLI and project name; use consistently in headings, binaries, archives, and releases (lowercase logotype, not spaced title case). |
| **Release version** | Semantic version **`MAJOR.MINOR.PATCH`**, embedded in filenames and ideally in package metadata (see strategies below). |
| **Git tag** | Annotated tag **`vMAJOR.MINOR.PATCH`** (leading `v`); triggers the publish workflow when pushed. |

---

## What gets published

On a successful workflow run GitHub Releases receive:

| Asset pattern | Contents |
|---------------|----------|
| `gitwell-<version>-<os>-<arch>.zip` | Single frozen binary **`gitwell`** or **`gitwell.exe`** wrapped for download |
| **`SHA256SUMS`** | `sha256sum` lines over all downloadable archives |

Release body:

- **GitHub-generated notes** from the API (`POST /releases/generate-notes`) — “What’s Changed” since the previous tag (PR titles, commits, contributors).
- **Optional preamble** built from **`CHANGELOG.md`** (section `## [version]`) and/or **`release-notes/gitwell-<version>.md`** via [scripts/extract_changelog_fragment.py](scripts/extract_changelog_fragment.py) in [.github/workflows/release.yml](.github/workflows/release.yml).

Release title convention: **`gitwell <version>`** (no leading `v` in the GitHub Release title UI), matching the workflow [`softprops/action-gh-release`](https://github.com/softprops/action-gh-release).

---

## Source of truth for version vs tags

### Strategy A — Static `[project.version]` (default)

**Rule:** Immediately before tagging, **`[project].version`** in [pyproject.toml](pyproject.toml) must equal the version you are about to tag **without** the `v`.

| Step | Value |
|------|-------|
| `pyproject.toml` | `version = "1.4.2"` |
| Git tag pushed | **`v1.4.2`** |

**CI:** Sets `GITWELL_VERSION="${GITHUB_REF_NAME#v}"` and **fails** if it does not match `tomllib` parse of `[project]` version — prevents silent drift between wheel metadata and binaries.

### Strategy B — `setuptools-scm` (optional)

Tags alone drive version (`v*`); no manual `[project]` bump in pyproject. Requires extra tool config and verifying PyInstaller still sees consistent `gitwell` package metadata/`--version`. Prefer Strategy A unless you deliberately want fully tag-driven semver.

See [pyinstaller.org](https://pyinstaller.org) for quirks when injecting dynamic versions into frozen binaries.

---

## GitHub Actions: configuration reference

Implemented in [.github/workflows/release.yml](.github/workflows/release.yml).

### Triggers

| Trigger | Typical use |
|---------|--------------|
| `push` tags `v*.*.*` | Production freeze + GitHub Release |
| `workflow_dispatch` | Builds all matrix artifacts on the selected ref; **does not publish** — the release job requires `push` plus a tag ref starting with **`refs/tags/v`**. |

### Key contexts and environment

| Variable | Typical value | Used for |
|-----------|---------------|----------|
| `github.ref_name` | `v1.4.2` on tag workflows | Tag basename |
| `GITHUB_REF_NAME` | Same | Shell snippets stripping `v` |
| **`GITWELL_VERSION`** | `1.4.2` *(no `v`)* | Names for zips/archives, CHANGELOG/snippet filenames |
| **`steps.vers.outputs.version`** | Same as `GITWELL_VERSION` | Reliable artifact path interpolation in YAML |
| `GITHUB_TOKEN` | Default Actions token | `contents: write` for Releases + uploads |
| **`PYTHON_VERSION`** | `3.12` *(workflow env)* | Bump here when migrating Python baseline |

### Artifact naming checklist

Bundles must satisfy:

```
gitwell-${GITWELL_VERSION}-${OS_SLUG}-${ARCH_SLUG}.zip
```

Current matrix slugs: **`linux-amd64`**, **`windows-amd64`**, **`macos-arm64`**, **`macos-amd64`** (Intel via `macos-13`).

CI writes each archive with [scripts/package_frozen_zip.py](scripts/package_frozen_zip.py) (stdlib **`zipfile`**) so **`windows-latest`** jobs do not depend on the **`zip`** executable (Git Bash omits it on hosted runners).

### Permissions

```yaml
permissions:
  contents: write
```

Add only scopes you need later (`id-token`, `attestations`, etc.) if you introduce attestations/signing tools.

---

## Maintainer checklist (Strategy A — static version)

Follow in order:

1. **Merge** planned work onto the release branch (usually **`main`**).
2. **`CHANGELOG.md`** *(optional)*: section **`## [<version>] - YYYY-MM-DD`** for the prelude on the Release page — or add **`release-notes/gitwell-<version>.md`** under [release-notes/](release-notes/).
3. **Bump `[project].version`** in [pyproject.toml](pyproject.toml) to **`X.Y.Z`**.
4. **Commit** (example): `Prepare release gitwell X.Y.Z`.
5. **Tag** (annotated): `git tag -a vX.Y.Z -m "gitwell X.Y.Z"`.
6. **`git push origin vX.Y.Z`** — CI builds and publishes. Do not retag; use PATCH `vX.Y.(Z+1)` if binaries are wrong.

### After CI completes

| Check | Action |
|-------|--------|
| Release assets | Correct OS/arch zips attached |
| `SHA256SUMS` | Present and references every **`gitwell-<version>-*.zip`** basename |
| Release body | Starts with preamble *(if CHANGELOG/snippet existed)* followed by GitHub-generated section |
| Smoke test | Unzip one artifact and run `gitwell --help` on that OS |

### If CI fails mid-flight

Prefer a new PATCH tag after fixing `pyproject` or code. Avoid rewriting published tags collaborators may have fetched.

---

## Local reproduction (rough CI parity)

```shell
python3 -m venv .venv
source .venv/bin/activate        # Windows: activate equivalent
pip install --upgrade pip
pip install -e ".[build]"
pyinstaller --noconfirm --clean gitwell.spec
# Inspect dist/gitwell OR dist/gitwell.exe
```

Binary identity across hosts usually differs (libc, linker); reproducibility expectation is **same steps produce auditable parity**, not bit-identical blobs across Ubuntu vs macOS runners.

---

## Checksums verification (downloader sketch)

POSIX (GNU `grep`/`sha256sum`):

```shell
FN='gitwell-1.4.2-linux-amd64.zip'
grep " $FN\$" SHA256SUMS && sha256sum -c <<<"$(grep " $FN\$" SHA256SUMS)"
```

End-user recipes live in [README.md](README.md).

---

## Trust posture

Downloads come from GitHub Releases created by [.github/workflows/release.yml](.github/workflows/release.yml). Compare the tag SHA to the commit on GitHub, then reconcile hashes with **`SHA256SUMS`**. Frozen installers are **unsigned** unless/until signing/notarization is added later.

---

## Troubleshooting FAQ

**Q:** CI reports a **version mismatch** between tag and `pyproject.toml`.  
**A:** Align `[project.version]` with the semver after stripping `v` from the pushed tag (`v2.4.1` ⇒ `version = "2.4.1"`).

**Q:** Missing deps or **`ModuleNotFoundError`** inside the frozen bundle.  
**A:** Inspect PyInstaller **`hiddenimports`** in [gitwell.spec](gitwell.spec); reproduce locally with `pyinstaller` debug flags before shipping.

**Q:** AV tools flag **`UPX`**.  
**A:** Releases build with **`upx=False`** in [gitwell.spec](gitwell.spec); if regressions arise, revisit packaging flags.

---

## Future extensions

| Extension | Benefit |
|-----------|---------|
| **Sigstore / cosign / minisign** | Extra verification surface |
| **Apple notarization + codesign** | Smoother macOS Gatekeeper UX |
| **`actions/attest-build-provenance`** | Hosted provenance metadata |
