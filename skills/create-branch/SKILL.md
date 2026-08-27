---
name: create-branch
description: Push a new, named branch to origin without triggering CI. Used as a building block by other skills.
---

# Purpose

Create a new branch with a given name and push it to `origin` **without
triggering CI**.

There is no way to create a remote branch through a pull request — a branch
must be pushed to `origin` to exist at all. So this skill pushes directly to
`origin`. It only ever creates a **new feature branch**; it must never push to
a protected branch (`main`, `master`, `mainline`, `beta-braveheart`).

# Pre-requisites

- Ensure `git` exists and you are inside (or can clone) the target repo.
- Ensure `gh` exists and the user is logged in (`gh auth status`).
- The working tree is clean (`git status`).
- The branch name MUST be provided explicitly — either by the user or by the
  calling skill (e.g. `create-prerelease-branches` passes `rc` / `dev`).
  **Never invent a branch name.** If no name is given, ask the user for one
  before doing anything.

# Why an empty commit is required

conda-forge feedstock workflows trigger on **push to any branch**. Pushing a
branch that points at an existing commit still fires a `push` event, and that
commit's message carries no skip token — so CI runs. To make the push
CI-inert, the branch tip must be an **empty commit carrying a skip token**.

Skip tokens (exact spelling matters — do not paraphrase):

- GitHub Actions: `[ci skip]` (also honors `[skip ci]`, `[no ci]`, `[skip actions]`, `[actions skip]`).
- Azure Pipelines: `***NO_CI***` (underscore — `***NO CI***` with a space is NOT recognized).

Include **both** tokens so the branch is CI-inert regardless of which provider
the feedstock uses.

# Steps

## Step 1: Enter the repo

`cd` into a local clone of the target repo. If you only have the repo name,
clone it first:

```bash
gh repo clone <owner>/<repo>
cd <repo>
```

## Step 2: Resolve the base branch

Fetch and determine the base branch to fork from. Default to origin's default
branch unless the user specified `$base`:

```bash
git fetch origin
base="${base:-$(git remote show origin | sed -n 's/.*HEAD branch: //p')}"
```

## Step 3: Create the branch

Use the branch name provided by the user or calling skill as `$branch` — never
make one up. **Refuse** if `$branch` is `main`, `master`, `mainline`, or
`beta-braveheart`.

```bash
git switch -c "$branch" "origin/$base"
```

## Step 4: Add a CI-skipped empty tip commit

```bash
git commit --allow-empty -m "Create $branch branch [ci skip] ***NO_CI***"
```

## Step 5: Push to origin

`git push` MUST be its own standalone command — never chain it with `&&`,
`;`, or `|` (the sandbox policy blocks compound commands containing
`git push`).

```bash
git push -u origin "$branch"
```

## Step 6: Verify no CI was triggered

Confirm the branch exists on origin and that the push did not start a run:

```bash
gh run list --branch "$branch" --limit 5
```

There should be no new run for this branch.
