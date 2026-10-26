# Environment files

Secrets are not committed. Copy the template and fill it in:

```bash
cp python/app/.env.example python/app/.env.docker
cp js/.env.example js/.env.docker
```

Compose loads those `.env.docker` files. `config.py` also reads a `.env` in `python/app` if you run the API outside Docker. Variable-by-variable notes: [docs/ENVIRONMENT_README.md](docs/ENVIRONMENT_README.md).

Never print `.env.docker` or commit it. When you add a key, add it to the matching `.env.example` (empty if it is a secret).
