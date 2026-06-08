# Environment configuration

Copy templates here and create `configs/.env` (symlink `configs` → `config/env` at repo root):

```bash
cp .env.example .env
# optional Linux workstation overrides:
# cat linux-workstation.env.template >> .env
```

Never commit `.env` — it is gitignored.
