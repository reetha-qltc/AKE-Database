# AKE-Database – notes for Claude

- SAP Business One 10 (HANA) training database AKE_DEMO for AKE Infrastructure, built by Qltc. Read
  `docs/02_Handover_SAP_Server.md` for the current state of the SAP company and the scripts in `tools/`.
- **Daily tracker:** keep `DAILY_UPDATES.md` current. Add a section for each working day (newest on top) with
  Completed / In progress / Waiting on user / Next. Update it after every finished task, then commit and push it
  to GitHub (`origin main`) together with the day's work.
- Never commit `.env`, `sl_cert.crt`, `logs/`, `prints/` or screenshots containing licence data.
- Service Layer TLS: the server certificate is pinned via `SL_CA_FILE`; never disable certificate verification.
