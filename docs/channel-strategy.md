# Feedstock channel strategy (Jupyter AI family)

A convention for the Jupyter AI family of conda-forge feedstocks that lets a
chain of **inter-dependent serial releases** (e.g.
`jupyter-ai-router` → `jupyter-ai-persona-manager` → `jupyter-ai-acp-client` →
`jupyter-ai`) publish back-to-back without waiting on the `main` channel's
propagation delay between each step.

## The problem

conda-forge's `main` channel index (`conda-forge/noarch/repodata.json`) is
enormous (~180+ MB) and served through a CDN. Its cache directive is
`Cache-Control: public, max-age=1200` (20 min), and with origin regeneration,
conda-forge's repodata-patching pipeline, and per-PoP caching on top, a freshly
uploaded package realistically takes **~30–60 min** to become resolvable from
`main`.

A **custom label** index (`conda-forge/label/<label>/noarch/repodata.json`) is
tiny (a few KB — just the packages pushed to that label) and served with
`Cache-Control: public, max-age=60` (60 s). So a package uploaded to a custom
label is resolvable in **~1 minute**.

> Verify anytime with `curl -sI <repodata-url>` and read `cache-control`,
> `age`, and `cf-cache-status`.

When a downstream feedstock **sources from** a fast label, its build resolves
the just-published upstream in ~1 min instead of ~30–60 min. That is the entire
win: serial dependent releases proceed at build speed, not TTL speed.

## The convention

Each feedstock configures `recipe/conda_build_config.yaml` **per branch**.
`<pkg>` is the family label (`jupyter-ai`) unless the package also warrants its
own conventional label (see jupyterlab-chat note).

| branch | `channel_sources` | `channel_targets` |
|---|---|---|
| `main` | `conda-forge/label/jupyter-ai_stable,conda-forge` | `conda-forge main`<br>`conda-forge jupyter-ai_stable` |
| `rc` | `conda-forge/label/jupyter-ai_rc,conda-forge` | `conda-forge jupyter-ai_rc` |
| `dev` | `conda-forge/label/jupyter-ai_dev,conda-forge` | `conda-forge jupyter-ai_dev` |

Rules that make this correct:

1. **`channel_sources` ALWAYS appends `,conda-forge`.** The family label only
   holds the family packages; every other dependency (`python`,
   `jupyter_server`, `pydantic`, …) must still resolve from `main`. Listing the
   label first (with strict channel priority) means family packages come from
   the fast label and everything else from `main`.
2. **`channel_targets` is a list** — the uploader loops over every entry, so a
   single build uploads the artifact to each listed label
   (verified in `conda_forge_ci_setup.build_utils.upload_package`).
3. **The `main` branch targets BOTH `main` and `jupyter-ai_stable`.** This is
   what keeps the strategy safe: every stable artifact lands on `main` too, so
   `jupyter-ai_stable` is always a strict, fast-propagating **mirror** of the
   family's `main` packages — never a divergent source of truth. Nothing on the
   stable label is absent from `main`.
4. **CFEP-05 branch routing for versions:** stable `X.Y.Z` → `main`; alpha
   (`aN`) / dev (`.devN`) → `dev`; beta (`bN`) / rc (`rcN`) → `rc`.

### jupyterlab-chat exception

`jupyterlab-chat` also publishes under its own conventional label in addition
to the family label, e.g. on the `rc` branch:

```yaml
channel_targets:
  - conda-forge jupyter-ai_rc
  - conda-forge jupyterlab-chat_rc
```

(and analogously `jupyter-ai_dev` + `jupyterlab-chat_dev` on `dev`,
`jupyter-ai_stable` + `jupyterlab-chat_stable` on `main`). It has no
`channel_sources` beyond `conda-forge` because it sits at the root of the stack.

## What this does and does NOT speed up

- **DOES** speed up your own serial *build* chain across all three branches —
  each downstream build finds its just-released upstream on the fast label.
- **Does NOT** speed up end users. `conda install -c conda-forge <pkg>` reads
  only the `main` label repodata; it never consults `jupyter-ai_stable` unless
  the user explicitly adds `-c conda-forge/label/jupyter-ai_stable`. GA packages
  still propagate to users on the normal `main` timeline. The stable label is an
  **internal release-velocity accelerator**, not a user-facing channel.

## Tradeoffs (read before adopting the stable label)

- **Non-standard.** CFEP-05 defines labels for pre-releases (`_rc`/`_dev`).
  A `jupyter-ai_stable` label for GA packages is an intentional extension of
  that mechanism; expect it to be unfamiliar to reviewers. conda-forge tooling
  permits it (`conda-forge/label/\S+` is an allowed `channel_sources` pattern),
  and it does not affect default users, but it is a channel the family
  maintainers own and maintain.
- **Extra channel.** `jupyter-ai_stable` accumulates the family's stable history
  in parallel with `main`. Harmless, but it exists.
- **Alternative if you don't want the stable label:** cut the GA releases in
  dependency order and accept one `main`-propagation wait per dependency level,
  or let the autotick-bot migrator sequence and retry. The stable label exists
  specifically to avoid that per-level wait when publishing many dependent
  releases back-to-back.

## Rationale for adopting it here

The family is released as a tightly-coupled cohort with strict lower bounds
between packages (e.g. `jupyter-ai 3.2.0rc0` requires the rc0 of every sibling).
Publishing 7+ dependent feedstocks in serial while waiting ~30–60 min for `main`
between each is a multi-hour-to-full-day operation. Sourcing from the family
label collapses that to build speed, which is the deciding factor for
maintainer throughput.
