---
name: create-recipe
description: Create a new v1 recipe for a PyPI package and open it as a PR on conda-forge/staged-recipes
---

# Pre-requisites

Validate the shell environment before doing anything.

- Ensure `jq` exists in the shell environment
- Ensure `rattler-build` exists in the shell environment
- Ensure `python` exists in the shell environment
- Ensure `gh` exists in the shell environment, and that the user is logged in (`gh auth status`)
- Ensure `.kiro/skills/create-recipe/assets/recipe.yaml` exists
- Ensure `.kiro/skills/create-recipe/assets/get_build_deps.py` exists

This skill works for **any PyPI package**, not just Jupyter AI packages.

# Recipe creation process

## Step 0: Clone `conda-forge/staged-recipes`

The recipe must be created inside a local clone of `conda-forge/staged-recipes`.

If you are not already inside a clone of `conda-forge/staged-recipes`, clone it first:

```
gh repo clone conda-forge/staged-recipes
cd staged-recipes
```

## Step 1: Gather requirements and create branch

Get the Python package name from the user and remember it as `$name`. This could be `jupyter-ai-router` or any other PyPI package name, for example.

Verify the package exists on PyPI:

```
curl -s https://pypi.org/pypi/$name/json | jq -r '.info.name'
```

Create a new branch **OFF THE MAIN BRANCH**.

```
git switch main
git pull
git switch -c add-$name
```

## Step 2: Create new recipe

Create the new recipe dir:

```
mkdir -p recipes/$name
cd recipes/$name
```

Copy the `recipe.yaml` asset into this dir as `recipe.yaml`.

## Step 3: Update version and SHA hash

Get the latest version of the PyPI package.

```
curl -s https://pypi.org/pypi/PACKAGE_NAME/json | jq -r '.info.version'
```

With that, get the SHA hash:

```sh
pypi_name="<PYPI-NAME>"
version="<VERSION>"
curl https://pypi.org/pypi/$pypi_name/$version/json | jq '.urls[] | select(.url | contains("tar.gz")) | .digests.sha256'
```

Then set `context.version` and `source.sha256` accordingly.

**Do not set `context.python_min`** - it is provided globally by the build system per [CFEP-25](https://github.com/conda-forge/cfep/blob/main/cfep-25.md).

### Step 4: Update build requirements

Run `get_build_deps.py` to get the build requirements.

Add these to `requirements.build`. Follow the Conda Forge syntax. Assume the packages already exist.

### Step 5: Update run requirements

Get the run requirements of the package:

```
curl -s https://pypi.org/pypi/PACKAGE_NAME/json | jq '.info.requires_dist'
```

Ignore optional dependencies. Add all required dependencies to `requirements.run`. Follow the Conda Forge syntax. Assume the packages already exist.

### Step 6: Verify all requirements

Extract all package names from `requirements.host` and `requirements.run` sections (excluding `python` and `pip`).

Use `micromamba search -c conda-forge PACKAGE_NAME` to verify each package exists in conda-forge. If `micromamba` is not available, fall back to `conda search -c conda-forge PACKAGE_NAME`.

To search in parallel, invoke multiple `execute_bash` tool calls in a single function_calls block. For example, if you have packages A, B, and C, call `execute_bash` three times within one `<function_calls>` block.

If a package is not found, try replacing hyphens with underscores or vice versa (e.g., `jupyter-server` → `jupyter_server`). Conda-forge naming is inconsistent with hyphen/underscore usage. Update the recipe with the correct package name when found.

### Step 7: Create conda_build_config.yaml

Create `conda_build_config.yaml` in the recipe directory with the current `python_min` from conda-forge:

```yaml
python_min:
  - '3.10'
```

This file is only for local testing. It will be deleted before pushing to GitHub.

### Step 8: Final touches

Replace Jinja2 expressions containing `name` with the actual value. For example, if `name := 'jupyter-ai-router'`, replace `${{ name[0] }}` with 'j' and `${{ name.replace("-", "_") }}` with 'jupyter_ai_router'.

Delete `context.name`.

**Do not delete or modify `${{ python_min }}`** - it is a global variable provided by the build system.

Set the `about.homepage`, `about.repository`, and `about.summary` fields to match the upstream project. If the package is hosted on GitHub, you can fetch the description with:

```
curl -s https://api.github.com/repos/<org>/<repo> | jq -r '.description'
```

Otherwise, read the summary from the PyPI metadata:

```
curl -s https://pypi.org/pypi/PACKAGE_NAME/json | jq -r '.info.summary'
```

Set `about.license` to the package's SPDX license identifier (from the PyPI metadata) and set `extra.recipe-maintainers` to the correct GitHub usernames (default to the current user).

Check the license file name in the PyPI package metadata:

```
curl -s https://pypi.org/pypi/PACKAGE_NAME/json | jq -r '.info.license'
```

Common license files are `LICENSE`, `LICENSE.txt`, `COPYING`, or `LICENSE.md`. Update `about.license_file` if needed.

### Step 9: Test the build process

If the `output/` directory exists, delete it first because it occupies a higher channel priority than `conda-forge`:

```
rm -rf output/
```

Then build the recipe:

```
rattler-build build -r recipes/$name
```

Make sure the recipe builds successfully before continuing to the push process.

# Push process

Only continue once the recipe has built successfully above.

MAKE SURE you are on a Git branch like `add-<package-name>`, e.g. `add-jupyter-ai-router`.

## Step 10: Clean up local testing files

Delete `conda_build_config.yaml` from the recipe directory if it exists:

```bash
rm -f recipes/<package-name>/conda_build_config.yaml
```

This file is only for local testing and should not be committed.

## Step 11: Commit changes

If there are any changes under `recipes/`, commit them in a format like "Add <package-name>".

## Step 12: Create a fork and push the branch to it

The recipe must be pushed to a **branch on your own fork** of `conda-forge/staged-recipes` — never directly to the upstream repo.

Create a fork if one does not already exist (this is a no-op if you already have a fork). This also adds a git remote pointing at your fork:

```bash
gh repo fork conda-forge/staged-recipes --remote --remote-name fork
```

Then push the branch to your fork:

```bash
git push -u fork add-<package-name>
```

## Step 13: Open a PR

Use the `gh` CLI to open a **DRAFT** PR from your fork's branch to https://github.com/conda-forge/staged-recipes/

```bash
gh pr create --repo conda-forge/staged-recipes --draft --title "Add \`<package-name>\`"
```

Set the PR title to "Add `<package-name>`", e.g. "Add `jupyter-ai-router`".

READ the `.github/pull_request_template.md` file. Check every box EXCEPT "GitHub users listed in the maintainer section have posted a comment confirming they are willing to be listed there."

Add a brief description at the bottom. Include a link to the upstream repo. Read `recipes/<package-name>/recipe.yaml` to get this info.

## Step 14: Reply with the link

Send the user the link to the PR to click.
