---
name: create-prerelease-branches
description: Stand up CFEP-05 rc and dev pre-release branches on a conda-forge feedstock, wiring channel sources/targets and rerendering, without triggering CI.
---

# Purpose

Set up [CFEP-05](https://github.com/conda-forge/cfep/blob/main/cfep-05.md)
pre-release branches (`rc` and `dev`) on a conda-forge feedstock:

1. Create the `rc` and `dev` branches on the feedstock.
2. Open a setup PR for each branch that wires `channel_sources` /
   `channel_targets` and triggers a rerender.

All steps are CI-inert — no build or upload fires until a real version-bump PR
is merged later.

# Pre-requisites

- Ensure `git`, `gh` (logged in — `gh auth status`), and `micromamba` (or
  `conda` / `pip`) exist.
- **ALWAYS update `conda-smithy` to the latest release before rerendering.** An
  out-of-date `conda-smithy` makes `conda smithy rerender` fail. Do this every
  run — do not assume the installed version is current:

  ```bash
  micromamba install -y -c conda-forge conda-smithy
  # or: pip install -U conda-smithy
  ```

- Follow the [`create-branch`](../create-branch) skill for the branch-creation
  step below.
- Ensure a **fork** of the feedstock exists and is available as the git remote
  `fork` (tracking the current user's GitHub account). Create it if missing:

  ```bash
  gh repo fork conda-forge/<feedstock> --remote --remote-name fork
  ```

> ⚠️ **CRITICAL — never push a channel-configured branch to `origin`.**
> A push (not a PR) to any branch of a conda-forge feedstock that carries
> `channel_targets` triggers a build **and an upload** to those labels on the
> push event. The `setup-<kind>` working branch carries the channel config, so
> it MUST be pushed to your **fork**, and the PR opened from the fork. Only the
> empty, CI-skipped `<kind>` base branch (from `create-branch`) may be pushed to
> `origin` — it has the skip tokens, so it never builds or uploads.

# Label logic

Determine the labels from the feedstock's **upstream** repo, read from the
recipe's `about.repository` / `about.homepage` / `source.url` — NOT from the
feedstock name (feedstocks always live under `conda-forge/`).

`<kind>` is `rc` or `dev` depending on which branch is being set up.

1. **Upstream repo under `jupyter-ai-contrib/`** — both source from and target
   the shared family label:

   ```yaml
   channel_sources:
     - conda-forge/label/jupyter-ai_<kind>,conda-forge
   channel_targets:
     - conda-forge jupyter-ai_<kind>
   ```

2. **`jupyterlab-chat`** (upstream repo `jupyterlab/jupyter-chat`) — it is the
   root of the pre-release stack, so it has no pre-release sources but is
   published to BOTH the family label and its own conventional label:

   ```yaml
   channel_targets:
     - conda-forge jupyter-ai_<kind>
     - conda-forge jupyterlab-chat_<kind>
   ```

   (no `channel_sources` — default `conda-forge` only.)

3. **Everything else** — do NOT assume a default. ASK the user for the
   label(s) and whether any `channel_sources` are needed.

Always echo the resolved `channel_sources` / `channel_targets` and confirm with
the user before committing.

# Steps

## Step 0: Determine the feedstock(s)

The agent MUST know which feedstock(s) to operate on before doing anything.
**Never guess or infer the feedstock from context** — ask the user for the
explicit feedstock name(s) (e.g. `jupyter-ai-persona-manager-feedstock`,
`jupyter-chat-feedstock`) if they were not given.

This skill can set up several feedstocks in one go — for example, the whole
Jupyter AI family. When multiple feedstocks are named, run every step below
(Steps 1–8, for both `rc` and `dev`) independently for each feedstock.

Then, **for each feedstock**, do the following **for each `<kind>` in `rc` then
`dev`**.

## Step 1: Enter the feedstock

`cd` into a local clone of the feedstock (clone from `origin` if needed). As a
recipe maintainer you have push access to the feedstock under `conda-forge/`.

## Step 2: Create the pre-release branch

Follow the [`create-branch`](../create-branch) skill with `branch=<kind>` to
push a CI-inert `<kind>` branch to origin.

## Step 3: Create a working branch

Branch off the new `<kind>` branch for the setup change:

```bash
git switch -c "setup-<kind>" "origin/<kind>"
```

## Step 4: Wire the channels

Edit `recipe/conda_build_config.yaml`, adding the `channel_sources` /
`channel_targets` for this `<kind>` per the Label logic above.

## Step 5: Rerender

A rerender is **mandatory** after editing `channel_targets` — otherwise the
labels never reach the generated CI config. It also requires the up-to-date
`conda-smithy` installed in the pre-requisites.

```bash
conda smithy rerender -c auto
```

Stage the recipe change and all rerender output.

## Step 6: Commit and push the working branch to your FORK

```bash
git commit -m "Set up <kind> pre-release channels"
```

Push the working branch to your **fork** — NOT `origin`. Pushing it to
`origin` would trigger a build+upload to the labels on the push event (see the
warning in Pre-requisites). `git push` MUST be a standalone command (sandbox
policy blocks compound commands containing `git push`):

```bash
git push -u fork "setup-<kind>"
```

## Step 7: Open the setup PR (from the fork)

Open a PR whose **head is the fork branch** and whose **base is the `<kind>`
branch on `origin`**. A PR from a fork runs CI via the `pull_request` event,
which builds but does **not** upload — so no label upload happens until a real
version-bump PR is merged into the `<kind>` branch.

The PR **title MUST contain the skip tokens**. These feedstock PRs are
squash-merged, and the squash commit message is the PR title — without the
tokens, merging would rebuild the CURRENT stable version and upload it as a
pre-release. Exact spelling matters:

```bash
gh pr create \
  --repo conda-forge/<feedstock> \
  --base "<kind>" \
  --head "<your-github-username>:setup-<kind>" \
  --title "Set up <kind> pre-release channels [ci skip] ***NO_CI***"
```

In the PR body:

- List the resolved `channel_sources` / `channel_targets`.
- Note that the first real pre-release build happens on the next version-bump
  PR merged into this branch — this PR only wires the channels.

## Step 8: Report

Reply with both PR URLs and the consumer install command, e.g.:

```bash
conda install -c conda-forge/label/jupyter-ai_<kind> -c conda-forge <package>
```

## Step 9: Merge (squash — the merge commit message MUST carry the skip tokens)

When you merge a setup PR, the merge lands a commit **on the `<kind>` branch**,
which is a push to a branch that now carries `channel_targets`. If that commit
message does **not** contain the skip tokens, CI runs on the push and
**builds + uploads the current stable version to the label prematurely**. So the
tokens must be in the **squash commit message**, not merely the PR title.

The PR title already contains `[ci skip] ***NO_CI***`, and a squash merge uses
the PR title as the default commit subject — but do **not** rely on that
default (a repo's squash-message setting, or a maintainer editing the subject,
can drop it). Pass the commit message **explicitly** so it is guaranteed:

```bash
gh pr merge <n> \
  --repo conda-forge/<feedstock> \
  --squash --delete-branch \
  -t "Set up <kind> pre-release channels [ci skip] ***NO_CI***" \
  -b ""
```

Notes:
- GitHub may append ` (#<n>)` to the subject — harmless; the skip tokens still
  take effect because CI matches them **anywhere** in the commit message.
- After merging, confirm no build was triggered on the `<kind>` branch:
  `gh run list --repo conda-forge/<feedstock> --branch <kind> --limit 3`
  should show no new run for the merge commit.
- The first real build/upload happens later, on the version-bump PR
  (`open-feedstock-pr`), which deliberately has **no** skip tokens.

# Notes and gotchas

- Skip tokens must be exact: `[ci skip]` (GitHub Actions) and `***NO_CI***`
  (Azure). `***NO CI***` with a space is not recognized.
- `dev` must sort below `rc` in conda version ordering:
  `X.Y.ZdevN` < `X.Y.ZrcN` < `X.Y.Z`.
- Labels are arbitrary strings and need NOT match the package name. Listing
  multiple `channel_targets` uploads the artifact to EACH label (the uploader
  loops over every `channel_targets` entry).
- Do not set repo-local git identity; inherit the global config.
- NEVER push the `setup-<kind>` (or any channel-configured) branch to a
  feedstock `origin` — a branch push with `channel_targets` uploads to those
  labels on the push event. Always push PR head branches to your fork and open
  the PR from the fork. Only the empty, skip-token `<kind>` base branch goes to
  `origin`.
