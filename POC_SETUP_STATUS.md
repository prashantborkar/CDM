# ServiceNow Certificate Management POC - Local Setup Status

Generated: 2026-07-27 (local Windows setup run)
**Follow-up run:** 2026-07-27 — network profile, WinRM, mock API URL ACL

## Checklist Summary

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | Java 17 installed | **PASS** | Microsoft Build of OpenJDK 17.0.19; `JAVA_HOME` (Machine): `C:\Program Files\Microsoft\jdk-17.0.19.10-hotspot\`. Use a **new** terminal for `java` on PATH, or full path to `bin\java.exe`. |
| 2 | WinRM running | **PASS** | Service running; HTTP listener **5985** enabled; **AllowUnencrypted: true**; **Auth\Basic: true**; firewall exception enabled; remote management configured. |
| 3 | Windows username noted | **PASS** | See credentials section — password must be supplied manually |
| 4 | Folders exist | **PASS** | All three paths verified present |
| 5 | ServiceNow_MID folder ready | **PASS** | Folder empty; MID Server ZIP must be downloaded from your PDI instance manually |
| 6 | Mock Sectigo URL ACL | **PASS** | `http://+:8080/sectigo/` reserved for **Everyone** |
| 7 | ServiceNow PDI URL | **MANUAL** | Sign up at https://developer.servicenow.com/ and provision a Personal Developer Instance (PDI) |

---

## Follow-up fixes (this session)

### Network profile + WinRM

- **Before:** Wi-Fi network category was **Public**; `AllowUnencrypted` was **false**.
- **Fixed:** `Set-NetConnectionProfile -InterfaceAlias "Wi-Fi" -NetworkCategory Private` — profile is now **Private**.
- **Fixed:** `winrm quickconfig -q` (enabled firewall exception and LocalAccountTokenFilterPolicy for remote local admin).
- **Fixed:** `Set-Item WSMan:\localhost\Service\AllowUnencrypted $true -Force` — verified **true**.
- **Verified:** `Set-Item WSMan:\localhost\Service\Auth\Basic $true -Force` — **true**.
- **Verified listener:** HTTP on port **5985**, Enabled, ListeningOn includes localhost and LAN addresses.

### Mock API HttpListener

- **Before:** No URL reservation for port 8080.
- **Fixed:** `netsh http add urlacl url=http://+:8080/sectigo/ user=Everyone`

### Prerequisites verification

| Check | Result |
|-------|--------|
| Java 17 | **PASS** (17.0.19 via full path; PATH may need new shell) |
| `C:\temp\cert_stage` | **Exists** |
| `C:\mock_linux_server\etc\ssl\certs` | **Exists** |
| `C:\ServiceNow_MID` | **Exists** |
| `mock_sectigo.ps1` | **Exists** at `C:\Users\riyaa\Downloads\POC\mock_sectigo.ps1` |

---

## 1. Java 17 (MID Server)

- **Install:** `winget install Microsoft.OpenJDK.17` — **Succeeded**
- **Version:** OpenJDK **17.0.19**
- **JAVA_HOME (Machine):** `C:\Program Files\Microsoft\jdk-17.0.19.10-hotspot\`

---

## 2. PowerShell Execution Policy

- **CurrentUser:** **RemoteSigned**
- **Effective in automation session:** may use **Bypass** at Process scope

---

## 3. WinRM Configuration

- Service **Running**
- Listener HTTP **5985** **Enabled**
- **Auth\Basic:** **true**
- **AllowUnencrypted:** **true** (after Private network profile)
- Network: **Wi-Fi** → **Private** ("Airtel_PR's Home")

---

## 4. Directory Structure

- `C:\temp\cert_stage` — Yes
- `C:\mock_linux_server\etc\ssl\certs` — Yes
- `C:\ServiceNow_MID` — Yes (empty)

---

## 5. Windows Username

```
tnl21909537-b\riyaa
```

Password must be provided manually for ServiceNow credentials.

---

## 6. Mock Sectigo API

- **Script:** `C:\Users\riyaa\Downloads\POC\mock_sectigo.ps1`
- **URL ACL:** `http://+:8080/sectigo/`
- **Run:** `.\mock_sectigo.ps1` from POC folder when testing.

---

## Still requires manual user action

1. **ServiceNow PDI:** Sign up at https://developer.servicenow.com/ and create a Personal Developer Instance.
2. **MID Server:** Download MID Server ZIP from your PDI; extract to `C:\ServiceNow_MID`.
3. **Credentials:** Provide Windows password when configuring ServiceNow / MID credentials (`tnl21909537-b\riyaa`).
4. **Optional:** Open a **new** PowerShell window so `java -version` works without full path (if still not on PATH in old sessions).

No further admin steps required for WinRM or mock API URL reservation on this machine unless network profile reverts to Public (e.g. new Wi-Fi network).
