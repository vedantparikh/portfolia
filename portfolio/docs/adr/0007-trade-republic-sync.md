# 0007 Read Bachat's Trade Republic export, no own login

**Context.** Bachat (`../bachat`) already logs in to Trade Republic with pytr's v2 web login (phone, PIN, app confirmation or code), keeps the encrypted session, and on Refresh writes `account_transactions.csv` atomically into the shared `trade-republic/output` folder. Trade Republic keeps one web session per device; a second app logging in would end the first one's session.

**Decision.** Portfolia only reads that file. The folder is mounted read only at `/pytr`; `PYTR_EXPORT_PATH` names the CSV and `PYTR_SYNC_USERS` the accounts allowed to link a portfolio to it (it is one person's brokerage account). A linked EUR portfolio is re-imported through the existing pytr parser and bulk-create when the file's hash changes, so source keys keep it idempotent. ISINs without a confident ticker are reported, not guessed.

**Consequences.** No pytr dependency, no PIN or session in Portfolia. New trades arrive only after someone refreshes in Bachat. If Bachat's export format changes, the pytr parser's column check fails loudly and the sync report shows it.
