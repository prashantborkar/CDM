# CDM implementation (local, runs today on this Windows laptop)

This is the real implementation of `CDM_End_to_End_Specification.md`, built now so it can be tested
on this machine before ServiceNow, AWS, Sectigo and CyberArk exist. Every stand-in below is clearly
marked in its own file, with a `SWAP TO PRODUCTION` note saying exactly what replaces it and why
nothing else has to change when that happens.

## What is real and tested here today

| Piece | What it does | Tested locally? |
|---|---|---|
| `ca_simulator/` | Issues real X.509 certificates with real private keys, serves them over HTTP exactly like Sectigo's landing area (list / collect / bundle) | **Yes** |
| `lab_site/` | Two live HTTPS endpoints (stand in for the IIS site and the Tomcat app) that reload their certificate with no restart | **Yes** |
| `discovery/discover.py` | Scans the lab endpoints over TLS and writes certificate records shaped exactly like ServiceNow Discovery output (thumbprint, serial, SAN, server, dates) | **Yes** |
| `matcher/match.py` | Matches old-to-new by certificate identity (rules M1/M2/M3 from the spec); ambiguous matches never auto-deploy | **Yes** |
| `adapters/windows_cert_store/adapter.py` | Imports a real PFX into the real Windows certificate store (`Cert:\CurrentUser\My`) via PowerShell, then activates and verifies over live TLS | **Yes** |
| `adapters/java_keystore/adapter.py` | Imports into a real PKCS#12 keystore using the real `keytool` from the JDK already on this machine | **Yes** |
| `vault_stub/vault.py` | A local JSON credential store, called through the same `get_credential(alias)` interface a real vault client would use | **Yes (stand-in)** |
| `orchestrator/run.py` | Runs every stage of the daily loop end to end: sync, match, plan, deploy, verify, roll back on failure, confirm the next day | **Yes** |
| `adapters/linux_apache/adapter.sh` | Full production-shape adapter for a real Apache server | **No** -- no Linux machine exists yet. Run it over SSH once one does (`CDM_Prerequisites_Simple_Steps.md` step 9). |

## Why these stand-ins, specifically

- **CyberArk -> `vault_stub/`.** One person cannot stand up CyberArk. The stub exposes exactly the
  interface every other module needs (`get_credential(alias)`), so replacing it with a CyberArk CCP
  client is a one-file change (see the docstring in `vault_stub/vault.py`).
- **Sectigo -> `ca_simulator/`.** This is "Path A" from `CDM_Prerequisites_Simple_Steps.md` step 14:
  no Sectigo account needed to start. It issues real certificates and delivers a real certificate +
  private key bundle by API, matching your answer that Sectigo can create the key with the
  certificate and deliver it by API. Swap the `base_url` in `config/cdm_config.json` to the real
  Sectigo tenant when it is available; nothing else changes (`matcher/match.py` and the adapters only
  ever call the same three HTTP routes).
- **ServiceNow CMDB/Discovery -> `discovery/discover.py`.** Produces the exact record shape
  (`cmdb/certificates.json`) that a real ServiceNow CMDB export/API read would produce. Swapping this
  module for a real ServiceNow API call is the only change needed once the instance exists.
- **IIS / Tomcat -> `lab_site/`.** Neither is installed on this laptop (no admin rights, no IIS
  feature enabled). `lab_site/server.py` is a small HTTPS server that reloads its certificate live,
  so `verify()` in the adapters has something real to TLS-probe. Its existence is the one thing that
  does **not** carry over to production -- there, `verify()` probes the real IIS/Tomcat endpoint
  instead, unchanged.
- **`Cert:\LocalMachine\My` -> `Cert:\CurrentUser\My`.** This laptop is not running as admin, and
  `LocalMachine` requires it. `adapters/windows_cert_store/adapter.ps1` is the production-shape
  script that targets `LocalMachine` and a real IIS binding; it is not run here.

## Run the demo

Three terminals, from `implementation/`:

```powershell
# once, or any time you want to reset the lab back to "certificates about to expire"
python seed.py

# terminal 1 -- the two lab websites (stand in for IIS and Tomcat)
python lab_site/server.py

# terminal 2 -- the CA simulator (stands in for the Sectigo landing area)
python ca_simulator/server.py

# terminal 3 -- the whole daily loop, end to end
python orchestrator/run.py demo
```

`demo` runs, in order: **sync** (read the lab "CMDB" + the CA landing area) -> **plan** (match by
identity, create one job per unique match that has a deployment profile) -> **deploy** (precheck,
backup, fetch the certificate+key bundle from the CA, install, activate, verify; roll back
automatically on any failure) -> **confirm** (re-scan, as the next day's Discovery run would, and
mark the binding "Confirmed by discovery" once the new thumbprint is observed).

You can also run each stage on its own: `python orchestrator/run.py sync|plan|deploy|confirm|status`.

### What you should see

- `web01.lab.example.com` (Windows/IIS stand-in) and `api.lab.example.com` (Java stand-in) each start
  with a certificate valid for about 3 days -- already inside the renewal window.
- `plan` matches each one, uniquely, to a 365-day replacement waiting at the CA simulator.
- `deploy` fetches the certificate **and its private key** from the CA simulator, imports it into the
  real Windows certificate store / a real Java keystore, and a live TLS probe on
  `https://127.0.0.1:8443` / `:8445` shows the new certificate immediately.
- `confirm` re-scans and reports `Confirmed by discovery` for both bindings.
- `python orchestrator/run.py status` shows the final state of every binding.
- `logs/audit.jsonl` has one tamper-evident (hash-chained) line per action, with every private key
  and password redacted -- `grep -i "BEGIN PRIVATE"  logs/audit.jsonl` (or Select-String) should
  find nothing.

### Proving the failure and rollback path

Edit `config/deployment_profiles.json` and change `PRF-WIN-001`'s `verification.sni` to a name that
does not match the certificate's SAN (for example `wrong.lab.example.com`), then run
`python orchestrator/run.py demo` again after `python seed.py`. The `verify` step fails, the adapter
rolls back automatically, and the binding's `status` in `jobs/job_log.json` is `Rolled back`.

## Folder map

```
implementation/
  common/              shared helpers: JSON load/save, UTC timestamps, hash-chained audit log
  config/              cdm_config.json (chapter 7 of the spec) and deployment_profiles.json
  vault_stub/          STAND-IN for CyberArk
  ca_simulator/        STAND-IN for the Sectigo landing area (real certs, real keys)
  lab_site/            STAND-IN for the IIS site and the Tomcat app (two live HTTPS endpoints)
  discovery/           STAND-IN for ServiceNow Discovery / the CMDB certificate table
  matcher/             real: identity matching (M1-M8), landing queue, review queue
  adapters/
    base.py            shared request/response envelope (Appendix A) + live TLS probe
    windows_cert_store/  REAL, tested -- Windows certificate store adapter (CurrentUser, lab)
    windows_cert_store/adapter.ps1  production-shape reference (LocalMachine, real IIS) -- not run
    java_keystore/      REAL, tested -- PKCS#12 keystore adapter using the real JDK keytool
    linux_apache/       production-shape reference (adapter.sh) -- not run, no Linux host yet
  orchestrator/         real: the daily loop (sync, plan, deploy, confirm) -- ServiceNow stand-in
  cmdb/, jobs/, logs/   generated at run time (gitignored); seed.py resets them
```

## Wiring in the real prerequisites, once you have them

Nothing above needs to be rewritten. Each swap is exactly one file:

| When you have... | Change |
|---|---|
| A ServiceNow instance | Replace `discovery/discover.py`'s reads with the real CMDB API; replace `orchestrator/run.py`'s local JSON state with ServiceNow table writes |
| CyberArk | Replace `vault_stub/vault.py`'s `get_credential()` body with a CyberArk CCP call |
| A real Sectigo tenant/sandbox | Change `sources.sectigo.base_url` in `config/cdm_config.json`; confirm the real list/collect/bundle endpoints match `ca_simulator/server.py`'s shape (adjust the three call sites in `matcher/match.py` and `orchestrator/run.py` if they don't) |
| The AWS Windows machine, with WinRM/IIS | Use `adapters/windows_cert_store/adapter.ps1` (LocalMachine store, real IIS binding) instead of `adapter.py`, dispatched by the MID Server over WinRM |
| The AWS Linux machine, with SSH | Run `adapters/linux_apache/adapter.sh` over SSH from the MID Server -- it is already written and matches AD-LNX-* |
| A MID Server | The orchestrator's `_run_adapter()` call becomes a real MID Server job dispatch instead of an in-process function call; the JSON request/response shape does not change |
