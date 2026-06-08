# Contributing to OMEIA

## Git identity

Use the lab platform identity for commits in this repository:

```bash
git config user.name "OMEIA Lab Platform"
git config user.email "omeia-platform@noreply.local"
```

Historical commits may display under this identity via `.mailmap`; we do not rewrite git history.

## Branch naming

- `feature/<short-description>` — new capability
- `fix/<short-description>` — bug fix or regression
- `docs/<short-description>` — documentation only

## Secrets and configuration

- Never commit `configs/.env`, credentials, API keys, or tokens.
- Copy environment from `configs/.env.example` or `configs/linux-workstation.env.template`.
- Merge local overrides after each pull; templates are the source of truth.

## Linux workstation workflow

After `git pull` on the primary Linux host:

```bash
./infra/scripts/ops/linux_post_pull.sh   # or ./scripts/ops/linux_post_pull.sh
make install   # when dependencies changed
make start
```

## Tests

Run targeted suites before opening a PR:

```bash
make test
# or: python -m pytest tests/ -q
```
