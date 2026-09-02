---
name: open-feedstock-pr
description: Stage a new package version (stable or pre-release) for release on conda-forge by opening a version-bump PR from your fork onto the correct branch (main / rc / dev), rerendered with the latest conda-smithy.
---

# Purpose

Stage a new version of a package for release on conda-forge by opening a
version-bump PR on its feedstock: update the version + sha256 + run
dependencies, rerender with the latest `conda-smithy`, and open the PR **from
your fork** onto the branch that corresponds to the release channel.

# Branch routing — which branch = which release channel

The target branch is determined by the **type** of the version being staged,
following [CFEP-05](https://github.com/conda-forge/cfep/blob/main/cfep-05.md)
label semantics:

| Version type | Example | Target branch | Publishes to label |
|---|---|---|---|
| Stable | `1.2.3` | `main` | main conda-forge channel |
| **alpha** (`aN`) or **dev** (`.devN`) | `1.2.3a1`, `1.2.3.dev0` | **`dev`** | the branch's `_dev` label |
| **beta** (`bN`) or **rc** (`rcN`) | `1.2.3b1`, `1.2.3rc0` | **`rc`** | the branch's `_rc` label |

This mirrors CFEP-05 exactly: the **`dev` label = pre-alpha/alpha**, and the
**`rc` label = beta/release-candidate**. So:

- **alpha and dev go into `dev`.**
- **beta and rc go into `rc`.**

The `rc` / `dev` branches (and their `channel_targets`) must already exist on
the feedstock — they are created by the
[`create-prerelease-branches`](../create-prerelease-branches) skill. If the
target pre-release branch is missing, run that skill first. This skill does NOT
modify `channel_targets`; the label a branch publishes to is already baked into
its `recipe/conda_build_config.yaml`.

# Pre-requisites

- Ensure `git`, `gh` (logged in — `gh auth status`), `jq`, and `micromamba`
  (or `conda`) exist.
- **ALWAYS update `conda-smithy` to the latest release before rerendering** —
  rerender must run on the latest version. Do this every run:

  ```bash
  micromamba install -y -c conda-forge conda-smithy
  # or: pip install -U conda-smithy
  ```

- A **fork** of the feedstock exists as the git remote `fork`:

  ```bash
  gh repo fork conda-forge/<feedstock> --remote --remote-name fork
  ```

> ⚠️ NEVER push a branch that carries recipe `channel_targets` to the feedstock
> `origin` — a push (not a PR) to such a branch uploads to those labels on the
> push event. Always push the version-bump branch to your **fork** and open the
> PR from the fork.

# Steps

## Step 0: Inputs

Get the package name and the target version. If either was not given, ASK —
never guess. Determine the target branch via **Branch routing** above.

## Step 1: Verify the version exists on PyPI

```bash
curl -s https://pypi.org/pypi/<pkg>/<version>/json | jq -r '.info.version // "NOT_FOUND"'
```

If `NOT_FOUND`, the version is not published yet — stop (or wait until it is).

## Step 2: Clone, ensure fork, branch off the target branch

```bash
gh repo clone conda-forge/<feedstock>
cd <feedstock>
gh repo fork conda-forge/<feedstock> --remote --remote-name fork
git fetch origin
git switch -c "update-<branch>-to-<version>" "origin/<branch>"
```

## Step 3: Update version and sha256

- Set `context.version` to `"<version>"`.
- Set the source `sha256` to the sdist hash:

  ```bash
  curl -s https://pypi.org/pypi/<pkg>/<version>/json \
    | jq -r '.urls[] | select(.url|endswith(".tar.gz")) | .digests.sha256'
  ```

- Build number: **reset to `0`** if the version changed; **bump by 1** if the
  version is unchanged (a rebuild).

## Step 4: Update run dependencies

```bash
curl -s https://pypi.org/pypi/<pkg>/<version>/json | jq -r '.info.requires_dist[]?'
```

Reconcile `requirements.run` against this:

- Keep `python >=${{ python_min }}` as the first run dependency.
- **Ignore** optional/extra dependencies (those with an `extra ==` marker) —
  including ones that moved from required to an extra between versions (drop
  them from `run`).
- **Add** any newly-required dependency.
- Use conda-forge package naming (e.g. `jupyter_server`, `jupyter_ydoc`,
  `jupyter_events` use underscores). Verify any NEW dependency exists with
  `conda search -c conda-forge <pkg>`; if not found, swap hyphens/underscores
  and search again.
- Format constraints like `package >=1.0,<2`.

## Step 5: Rerender with the LATEST conda-smithy (mandatory)

A rerender with the latest `conda-smithy` is **required** on every version bump
— it regenerates the CI config and keeps the feedstock current. Ensure the
latest `conda-smithy` is installed (see Pre-requisites), then:

```bash
conda smithy rerender -c auto
```

`-c auto` auto-commits a `MNT: Re-rendered with conda-smithy <version>` commit,
which **records the exact conda-smithy version used** in git history. If it
prints `No changes made. This feedstock is up-to-date.`, the feedstock is
already current with the latest conda-smithy — that still satisfies the
requirement (note it in the PR).

## Step 6: Commit the recipe change

```bash
git add recipe/recipe.yaml
git commit -m "<pkg> v<version>"
```

(The rerender's `MNT` commit, if any, is a separate commit — keep both.)

## Step 7: Push to your FORK and open the PR

Push the branch to the **fork** (standalone command — never chain `git push`
with `&&`/`;`/`|`):

```bash
git push -u fork "update-<branch>-to-<version>"
```

Open the PR **from the fork** onto the target branch:

```bash
gh pr create \
  --repo conda-forge/<feedstock> \
  --base "<branch>" \
  --head "<your-github-username>:update-<branch>-to-<version>" \
  --title "<pkg> v<version>"
```

**PR title convention:** `<package-name> v<version>` — and append
`-<build-number>` **only when the build number is not 0** (i.e. a rebuild of an
already-released version). So:

- New version (build number `0`): `jupyter-ai v3.2.0rc0`
- Rebuild of the same version (build number `1`): `jupyter-ai v3.2.0rc0-1`

(The `-<N>` suffix is omitted for the common `build: 0` case.)

Do **NOT** put `[ci skip]` / `***NO_CI***` in this PR — this is a real release
that must build. Merging it into `<branch>` publishes `<version>` to that
branch's channel/label (main channel for `main`; the `_rc` / `_dev` label for
the pre-release branches).

PR body — the conda-forge checklist, boxes reflecting reality:

```
- [x] Used a personal fork of the feedstock to propose changes
- [ ] Bumped the build number (if the version is unchanged)
- [x] Reset the build number to `0` (if the version changed)
- [x] Re-rendered with the latest `conda-smithy`
- [x] Ensured the license file is being packaged.
```

## Step 8: Watch CI and report

```bash
gh pr checks <n> --repo conda-forge/<feedstock> --watch --interval 30
```

Report the PR link, the CI result, and which label the version will land on
when the PR is merged.

# Notes and gotchas

- Pre-release version sorting: `dev` < `rc` < final —
  `X.Y.ZdevN` < `X.Y.ZrcN` < `X.Y.Z`. Ensure the upstream tag sorts correctly.
- `git push` is ALWAYS its own command (sandbox blocks compound `git push`).
- Never push a channel-configured branch to `origin`; PR from the fork.
- Do not set repo-local git identity; inherit the global config.
