# 0008 Fetch from Trade Republic on demand, with Portfolia's own login

Supersedes [0007](0007-trade-republic-sync.md).

**Context.** With 0007, new trades reached Portfolia only after someone pressed Refresh in Bachat. The owner wants to fetch from Portfolia whenever they like.

**Decision.** Portfolia logs in itself with pytr 0.4.10's v2 web login, the same client code as Bachat's connector (`modules/broker_sync/trade_republic.py`): phone and PIN start it, the person confirms in the Trade Republic app or types an authenticator code. The PIN is never stored. The session (device info, cookies) is kept in `broker_connections.secret`, Fernet-encrypted with a key derived from `SECRET_KEY` (rotating it means logging in again). "Fetch from Trade Republic" marks a run, the API downloads into the shared `trade-republic/output` folder after the response (new documents, `account_transactions.csv` replaced atomically, `portfolio.csv`), then imports into every linked portfolio of that user exactly as the worker's file sync does. Only `api` mounts the folder read-write; the worker keeps it read only and still imports when Bachat changes the file. Staging never mounts it.

**Consequences.** pytr (and `cryptography`, `curl_cffi`) are dependencies of the API image. Trade Republic may keep one web session per account, so a login in Portfolia can end Bachat's session and the other way round; either app then asks for a new login. Bachat sees Portfolia's downloads and vice versa, since both write the same files. A fetch runs in the API process: a restart mid-run leaves it "running" until it counts as stale after 30 minutes.
