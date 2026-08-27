# conda-forge-skills

A collection of agent skills for creating and updating Conda Forge feedstocks. Mainly focused on re-distributions of PyPI packages.

## Skills

- [`create-recipe`](skills/create-recipe) — Create a new v1 recipe for a PyPI package and open it as a PR on `conda-forge/staged-recipes`.
- [`create-branch`](skills/create-branch) — Push a new, named branch to `origin` without triggering CI. Used as a building block by other skills.
- [`create-prerelease-branches`](skills/create-prerelease-branches) — Stand up CFEP-05 `rc` and `dev` pre-release branches on a feedstock, wiring channel sources/targets and rerendering, without triggering CI.
- [`open-feedstock-pr`](skills/open-feedstock-pr) — Stage a new package version (stable or pre-release) for release by opening a version-bump PR from your fork onto the correct branch (`main`/`rc`/`dev`), rerendered with the latest `conda-smithy`.
