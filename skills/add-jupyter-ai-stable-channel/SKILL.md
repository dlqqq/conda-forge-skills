---
name: add-jupyter-ai-stable-channel
description: Wire a Jupyter AI family feedstock's main branch to source and target the additive conda-forge/label/jupyter-ai_stable label in addition to conda-forge main, without triggering a rebuild.
---

# Purpose

Add the `jupyter-ai_stable` label to the **`main` branch** of a Jupyter AI family
conda-forge feedstock, so that stable (GA) builds:

- **source** from `conda-forge/label/jupyter-ai_stable,conda-forge`, and
- **target** BOTH `conda-forge main` AND `conda-forge jupyter-ai_stable`.

This is the stable-branch counterpart to the
[`create-prerelease-branches`](../create-prerelease-branches) skill (which wires
the `rc` and `dev` branches). It is grounded in the
[Feedstock channel strategy](../../docs/channel-strategy.md) doc — read that
first for the full rationale.

## Why (and what the stable label is / is NOT)

- **`main` branch ONLY.** This change belongs exclusively on the feedstock's
  `main` branch. The `rc`/`dev` branches are handled by
  `create-prerelease-branches`; do NOT touch them here.
- **The `jupyter-ai_stable` label is ADDITIVE.** The main branch keeps targeting
  `conda-forge main` exactly as before; we merely ALSO push each stable artifact
  to `conda-forge/label/jupyter-ai_stable`. Nothing is removed and nothing on the
  stable label is ever absent from `main` — the label is a strict, fast-mirror
  of the family's `main` packages, never a divergent source of truth.
- **What it buys you.** A custom-label repodata index is tiny and served with
  `Cache-Control: max-age=60` (~1 min to resolve) versus `main`'s ~180 MB index
  at `max-age=1200` (~30–60 min end-to-end). So when you cut a **chain of
  inter-dependent stable releases** (e.g. `jupyter-ai-router` →
  `jupyter-ai-persona-manager` → `jupyter-ai-acp-client` → `jupyter-ai`), each
  downstream build resolves its just-published upstream from the fast label in
  ~1 min instead of waiting on `main` propagation between every step. It speeds
  up the maintainer's serial *build* chain; it does NOT change anything for end
  users (`conda install -c conda-forge <pkg>` reads only `main`).

## Pre-requisites

- `git`, `gh` (logged in — `gh auth status`), and `micromamba` (or `conda`).
- **ALWAYS update `conda-smithy` to the latest release before rerendering.** An
  out-of-date `conda-smithy` makes `conda smithy rerender` fail. Do this every
  run — do not assume the installed version is current:

  ```bash
  micromamba install -y -c conda-forge conda-smithy
  # or: pip install -U conda-smithy
  ```

- A **fork** of the feedstock must exist as the git remote `fork` (tracking the
  current user's GitHub account). Create it if missing:

  ```bash
  gh repo fork conda-forge/<feedstock> --remote --remote-name fork
  ```

> ⚠️ **CRITICAL — never push a channel-configured branch to `origin`.**
> A push (not a PR) to any branch of a conda-forge feedstock that carries
> `channel_targets` triggers a build **and an upload** to those labels on the
> push event. The working branch carries the channel config, so it MUST be
> pushed to your **fork**, and the PR opened from the fork.

## Label logic

Determine the label(s) from the feedstock's **upstream** repo, read from the
recipe's `about.repository` / `about.homepage` / `source.url` — NOT from the
feedstock name (feedstocks always live under `conda-forge/`).

1. **Upstream repo under `jupyter-ai-contrib/`** (or `jupyterlab/jupyter-ai`
   itself) — source from the stable label and target both `main` and the shared
   family stable label:

   ```yaml
   channel_sources:
     - conda-forge/label/jupyter-ai_stable,conda-forge
   channel_targets:
     - conda-forge main
     - conda-forge jupyter-ai_stable
   ```

2. **`jupyterlab-chat`** (upstream repo `jupyterlab/jupyter-chat`) — it sits at
   the root of the stack, so it has no family `channel_sources`, but it is
   published to `main`, the family stable label, AND its own conventional label:

   ```yaml
   channel_targets:
     - conda-forge main
     - conda-forge jupyter-ai_stable
     - conda-forge jupyterlab-chat_stable
   ```

   (no `channel_sources` beyond the implicit `conda-forge` — it depends on no
   family package.)

3. **Everything else** — do NOT assume a default. ASK the user for the label(s)
   and whether any `channel_sources` are needed.

Rules that make this correct (see the channel-strategy doc):

- **`channel_sources` ALWAYS appends `,conda-forge`.** The family label holds
  only family packages; every other dependency (`python`, `jupyter_server`, …)
  must still resolve from `main`. Listing the label first (strict priority)
  means family packages come from the fast label and everything else from
  `main`.
- **`channel_targets` is a list** — conda-smithy renders **one build variant per
  entry** (a matrix dimension), so each listed label gets its own `.ci_support`
  variant that builds and uploads to that label. Keeping `conda-forge main` in
  the list is what makes the stable label additive rather than a replacement.

Always echo the resolved `channel_sources` / `channel_targets` and confirm with
the user before committing.

## Steps

## Step 0: Determine the feedstock(s)

The agent MUST know which feedstock(s) to operate on before doing anything.
**Never guess or infer the feedstock from context** — ask the user for the
explicit feedstock name(s) (e.g. `jupyter-ai-router-feedstock`,
`jupyter-ai-persona-manager-feedstock`) if they were not given. This skill can
run over several feedstocks in one pass; run Steps 1–8 independently for each.

## Step 1: Enter the feedstock

`cd` into a local clone of the feedstock (clone from `origin` if needed). As a
recipe maintainer you have push access to the feedstock under `conda-forge/`.

## Step 2: Create a working branch off `main`

The stable channel config goes on `main`, so branch off `origin/main`:

```bash
git fetch origin
git switch -c "add-stable-channel" "origin/main"
```

## Step 3: Wire the channels

Edit `recipe/conda_build_config.yaml`, adding the `channel_sources` /
`channel_targets` per the Label logic above. If the file already declares
`channel_sources` / `channel_targets`, MERGE the stable entries in additively —
keep `conda-forge main` in `channel_targets`.

## Step 4: Install the README template override, then rerender

**Install the template override BEFORE rerendering**, so the first rerender
already produces a correct README. Otherwise conda-smithy regenerates
`README.md`'s "add channels …" instructions from `channel_targets[0]` — which
`render_readme` builds by reading the first entry of **each `.ci_support/*.yaml`
in `os.listdir` order** — and with two targets the label file
(`…conda-forge_jupyter-ai_stable.yaml`) sorts before the main file
(`…_main.yaml`) (`j` < `m`), so the README would tell **end users** to add
`conda-forge/label/jupyter-ai_stable`. That label is a **dev-only accelerator**
and must never appear in the user-facing README, and there is **no conda-smithy
config knob** for it.

The durable, automatic fix is a feedstock-local template override: conda-smithy's
jinja loader searches `<feedstock>/templates` **before** its bundled templates,
so the override is applied on **every** rerender (local, conda-forge admin, or
autotick-bot) with no manual step:

```bash
mkdir -p templates
cp assets/README.md.tmpl templates/README.md.tmpl   # from this skill's assets/
git add -f templates/README.md.tmpl
```

The asset is conda-smithy's own `README.md.tmpl` with **only** the
channel-selection header patched to prefer the `conda-forge main` channel_target
(making the advertised channel plain `conda-forge`); the rest is verbatim
upstream and it is label-agnostic. The **`-f` is required and correct**: the
conda-smithy-managed `.gitignore` ignores every root path outside its allowlist
(`recipe/`, `.ci_support/`, `conda-forge.yml`) AND rerender **rewrites**
`.gitignore` (it is a managed support file), so you cannot durably un-ignore
`templates/` by editing `.gitignore` — but a **tracked** file survives rerender
regardless of the ignore rule.

**Then rerender** (mandatory after editing `channel_targets`, or the labels never
reach the generated CI config; needs the up-to-date `conda-smithy`):

```bash
conda smithy rerender -c auto
```

Stage the recipe change and all rerender output (`rerender -c auto` auto-commits
CI support changes but does NOT commit an untracked `conda_build_config.yaml` —
`git add` it explicitly). Verify the README auto-rendered to plain `conda-forge`:

```bash
grep -iE 'add channels' README.md          # -> conda config --add channels conda-forge
grep -c '<label>' README.md                # want 0  (<label> = e.g. jupyter-ai_stable)
git diff --stat origin/main -- README.md   # empty = matches upstream, no label leaked
```

A `python_min` bump in the `.ci_support` files is **expected and unrelated** — it
is whatever the current global conda-forge-pinning sets, pulled in by any
rerender. Sanity-check the final diff: the two `.ci_support` channel-target
variants, the `conda-build.yml` matrix, `recipe/conda_build_config.yaml`, and
`templates/README.md.tmpl` (new) — and **NO `README.md` or `.gitignore` change**.

## Step 5: Commit and push the working branch to your FORK

Commit the channel config and rerender output. **The branch commit message MUST
be EXACTLY the PR title (Step 6), including the skip tokens.** This is the
crucial part: when this **single-commit** PR is squash-merged **from the GitHub
UI**, GitHub pre-fills the squash commit subject from the **commit message**, not
the PR title. So if the tokens are only in the title and not in the commit, a
UI squash merge drops them and rebuilds + re-uploads the current stable version.
There is **no build-number bump** — a channel-config-only change; the next real
version-bump PR handles the build number:

```bash
git commit -m '[ci skip] ***NO_CI*** Add jupyter-ai_stable channel'
```

Because the commit carries the skip tokens, the fork PR's GitHub Actions build
is **skipped** — which is intended: this is a config-only edit we do NOT want to
rebuild or upload. (The recipe's continued validity under the new
`channel_sources` is not in question for a pure channel edit; if you want a
one-off build sanity check, push a throwaway token-free commit to a scratch
branch, never to the PR head.)

Push the working branch to your **fork** — NOT `origin`. Pushing a
channel-configured branch to `origin` would trigger a build+upload on the push
event. `git push` MUST be a standalone command (sandbox policy blocks compound
commands containing `git push`):

```bash
git push -u fork "add-stable-channel"
```

## Step 6: Open the PR (from the fork, base `conda-forge:main`)

Open a PR whose **head is the fork branch** and whose **base is `main` on
`origin`** (`conda-forge/<feedstock>`).

The PR **title MUST contain the skip tokens `[ci skip] ***NO_CI***`** AND **be
byte-for-byte identical to the Step 5 commit message.** These feedstock PRs are
squash-merged and the squash commit lands **on `main`** — a push to a branch
that now carries `channel_targets`. Without the tokens in that commit, the merge
would **rebuild the current stable version and re-upload it** to both `main` and
the stable label, which we do not want for a pure channel-config change. Because
a single-commit PR squashed from the GitHub UI takes its subject from the
commit message (not the title), keeping the two identical means the merge is
safe no matter how it is triggered. Exact spelling matters (`***NO CI***` with a
space is not recognized). Use this exact title:

```
[ci skip] ***NO_CI*** Add jupyter-ai_stable channel
```

```bash
gh pr create \
  --repo conda-forge/<feedstock> \
  --base main \
  --head "<your-github-username>:add-stable-channel" \
  --title '[ci skip] ***NO_CI*** Add jupyter-ai_stable channel'
```

In the PR body:

- List the resolved `channel_sources` / `channel_targets`.
- State that the `jupyter-ai_stable` label is **additive** (main is still
  targeted) and exists to speed up serial dependent releases, not end users.
- Note that no rebuild/upload fires on merge (skip tokens), and the label starts
  mirroring on the next real version-bump PR merged into `main`.

## Step 7: Merge (squash — the merge commit message MUST carry the skip tokens)

Merging lands a commit **on `main`**, which now carries `channel_targets`. If
that commit message does **not** contain the skip tokens, CI runs on the push
and rebuilds + re-uploads the current stable version to `main` and the stable
label. Because the branch commit message (Step 5) already carries the tokens AND
matches the PR title, **both merge paths are safe**: a GitHub-UI squash of this
single-commit PR pre-fills the subject from the commit message, and a CLI merge
can pass the title explicitly. Prefer passing it explicitly so it is guaranteed
regardless of repo squash-message settings:

```bash
gh pr merge <n> \
  --repo conda-forge/<feedstock> \
  --squash --delete-branch \
  -t '[ci skip] ***NO_CI*** Add jupyter-ai_stable channel' \
  -b ""
```

- GitHub may append ` (#<n>)` to the subject — harmless; the skip tokens still
  take effect because CI matches them **anywhere** in the commit message.
- After merging, confirm no build was triggered on `main`:
  `gh run list --repo conda-forge/<feedstock> --branch main --limit 3`
  should show no new run for the merge commit.
- The stable label begins mirroring on the next real version-bump PR merged into
  `main` (via `open-feedstock-pr`), which deliberately has **no** skip tokens.

## Step 8: Report

Reply with the PR URL. The stable label is now wired; once the next stable
version-bump PR merges, that artifact lands on both `conda-forge main` and
`conda-forge/label/jupyter-ai_stable`, and downstream feedstocks can source it
in ~1 min via:

```bash
conda install -c conda-forge/label/jupyter-ai_stable -c conda-forge <package>
```

# Notes and gotchas

- **`main` branch only** — the stable label belongs on `main`; `rc`/`dev` are
  the `create-prerelease-branches` skill's job.
- **Additive, never a replacement** — `conda-forge main` MUST stay in
  `channel_targets`. Dropping it would silently remove the package from the main
  channel that all end users read.
- Skip tokens must be exact: `[ci skip]` (GitHub Actions) and `***NO_CI***`
  (Azure). The title/commit is `[ci skip] ***NO_CI*** Add jupyter-ai_stable
  channel` (no backticks).
- **The branch commit message MUST match the PR title exactly.** A single-commit
  PR squash-merged from the GitHub UI takes its subject from the **commit
  message**, not the PR title — so the tokens must live in the commit itself, and
  keeping commit == title makes every merge path safe. A side effect is that the
  fork PR's Actions build is skipped (the head commit carries `[ci skip]`), which
  is intended for a config-only change.
- **The rerender in Step 4 is mandatory** after editing `channel_targets` — the
  labels only reach the generated `.ci_support/*` CI config via
  `conda smithy rerender -c auto`. Skipping it means the build matrix never
  learns about the new target and the stable label is never populated.
- **Install the README template override** (Step 4, `assets/README.md.tmpl` →
  `<feedstock>/templates/README.md.tmpl`, `git add -f`). Without it, conda-smithy
  renders the README's install channel from `channel_targets[0]` (the label file
  sorts before the `_main` file) and advertises `conda-forge/label/jupyter-ai_stable`
  to end users. The override is applied automatically on every rerender
  (conda-smithy searches `<feedstock>/templates` first); it only patches the
  channel-selection header to prefer `conda-forge main`. Force-add is required —
  the managed `.gitignore` ignores `templates/` and rerender rewrites
  `.gitignore`, so only a tracked file survives. Final diff must show no
  `README.md` change.
- The stable label is a **non-standard** extension of CFEP-05 (which scopes
  labels to pre-releases). It is permitted by conda-forge tooling
  (`conda-forge/label/\S+` is an allowed `channel_sources` pattern) and does not
  affect default users, but it is a channel the family maintainers own.
- `conda smithy rerender -c auto` auto-commits CI support changes but does NOT
  commit an untracked `conda_build_config.yaml` — `git add` it explicitly.
- Do not set repo-local git identity; inherit the global config.
- NEVER push the working (channel-configured) branch to a feedstock `origin` —
  a branch push with `channel_targets` uploads to those labels on the push
  event. Always push PR head branches to your fork and open the PR from the
  fork.
