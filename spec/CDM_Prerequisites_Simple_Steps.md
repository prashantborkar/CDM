# CDM: What You Need Ready, Step by Step

Do the steps in order. In every step: do the small tasks, fill in the blanks, and check it works. When a step is done, send me the filled blanks.

> **About passwords.** This file will be shared, so do not write passwords or keys in it. Where a step asks for a password, write only **where it is stored** (for example "my password manager" or the CyberArk object name). I will use that.

---

## Step 1. ServiceNow personal instance

**Goal:** an instance where we build and test CDM.

**Do this**
1. Go to developer.servicenow.com and sign in (or create a free account).
2. Click **Request an Instance** and choose the newest release.
3. Open the instance URL and log in as admin.
4. Write down the instance URL, the admin user name and the release.
5. Log in every few days so the instance stays active.

**Fill in**

| Item | Your value |
|---|---|
| Instance URL (for example https://dev12345.service-now.com) | |
| Admin user name | |
| Where the admin password is stored | |
| Release (for example Xanadu) | |

**Check it works:** you can log in and see the home page.

---

## Step 2. Users for building and testing

**Goal:** a few users to build CDM and to test the roles.

**Do this**
1. In ServiceNow open **User Administration > Users** and create these users:
   - a developer user (builds CDM),
   - a test **owner** (owns certificates),
   - a test **approver**,
   - a test **auditor** (read only).
2. Give the developer user the admin role for now.
3. Set a valid email on each user so notifications can be tested.

**Fill in**

| User | User ID | Email | Where the password is stored |
|---|---|---|---|
| Developer | | | |
| Test owner | | | |
| Test approver | | | |
| Test auditor | | | |

**Check it works:** each user can log in.

---

## Step 3. MID Server on your laptop

**Goal:** the agent that runs the deployment on the servers.

**Do this**
1. In ServiceNow create a user for the MID Server and give it the **mid_server** role. (This is not a person.)
2. In ServiceNow go to **MID Server > Downloads**, download the Windows 64-bit zip, and unzip it to a clean folder such as `C:\ServiceNow_MID`.
3. Java 17 is already installed on the laptop from the earlier setup.
4. Edit the MID `config.xml`: put in the instance URL, the MID user name and its password, and a MID name (for example `mid-lab-01`). The password stays only on the laptop, in that file.
5. Start the MID Server service.
6. In ServiceNow open **MID Server > Servers** and click **Validate**.

**Fill in**

| Item | Your value |
|---|---|
| MID Server name | |
| MID user name in ServiceNow | |
| Folder where the MID is installed | |
| Where the MID password is stored | |

**Check it works:** in **MID Server > Servers** the status is **Up** and **Validated**.

---

## Step 4. Certificate records in ServiceNow

**Goal:** confirm ServiceNow already holds the certificate data we match on.

**Do this**
1. Ask whoever runs Discovery which schedule scans certificates, and at what time each day.
2. In the CMDB open the list of certificate records and open five of them.
3. Check that each one shows: **name, thumbprint, serial, SAN, server, valid from, valid to, last scanned**.
4. Export about 20 records to a file (certificate data only, nothing secret) and send it to me.
5. If the personal instance has no Discovery data, say so. We will use a small scan simulator for the test.

**Fill in**

| Item | Your value |
|---|---|
| Name of the certificate list or table | |
| Field name for thumbprint | |
| Field name for serial | |
| Field name for SAN | |
| Field name for server | |
| Field name for valid from / valid to | |
| Field name for last scanned | |
| Discovery scan time each day | |
| Real Discovery or simulator (write one) | |

**Check it works:** the five records show all the fields.

---

## Step 5. Sectigo

**Goal:** CDM can read new certificates from Sectigo and get the certificate with its private key.

**Do this**
1. Ask your Sectigo administrator to create an **API account just for CDM** (not a personal account). It needs to: list certificates, download certificates, and download the certificate with its private key.
2. Ask Sectigo (support or your account contact) to confirm **in writing**:
   - the private key can be created together with the certificate and downloaded by API,
   - which API call to use and in which format (usually a PKCS#12 file),
   - how many times, and for how long, it can be downloaded,
   - whether Sectigo keeps a copy of the key.
3. Ask for a **test setup** (sandbox) or a few **test certificates** with a short validity.
4. Ask how renewals reach the landing area today, and how many days before expiry the new certificate appears.
5. Ask the administrator to store the API password in CyberArk (Step 6), not to send it to you.

**Fill in**

| Item | Your value |
|---|---|
| Sectigo API address | |
| Customer URI | |
| Organisation or department | |
| API account user name | |
| Where the API password is stored | |
| Certificate types or profiles we will use | |
| Test setup available (yes or no) | |
| Days before expiry the new certificate appears | |
| Sectigo contact name and email | |

Write here what Sectigo answered about the private key (paste their reply):

> 

**Check it works:** the API account can list certificates (your administrator runs a test call).

---

## Step 6. CyberArk

**Goal:** CDM gets every password from CyberArk, only when needed.

**Do this**
1. Ask the CyberArk administrator for:
   - an **application ID** for CDM (for example `CDM`), allowed only from the MID Server host,
   - a **safe** for CDM with read-only access for that application,
   - these **objects** in the safe: the Sectigo API account, the Windows deployment account, the Linux deployment account (SSH key), and the Java keystore passwords.
2. Ask which way the MID Server will read them (the Central Credential Provider web address).
3. Ask the administrator to run a **test read from the MID host** and show it in the CyberArk audit.
4. If no CyberArk is available for the test, say so. We use a clearly marked temporary stand-in, removed before production.

**Fill in**

| Item | Your value |
|---|---|
| CyberArk web address for reading credentials | |
| Application ID | |
| Safe name | |
| Object name: Sectigo API | |
| Object name: Windows deployment account | |
| Object name: Linux deployment account | |
| Object name: Java keystore (per application) | |
| CyberArk contact name and email | |

**Check it works:** the MID host can read one object and it appears in the audit.

---

## Step 7. Test servers

**Goal:** three small servers to test on: IIS, Apache and Java.

### 7a. Windows with IIS

**Do this**
1. Use a test Windows server (or the laptop). Turn on IIS.
2. Create a site and add an **HTTPS binding** with an old test certificate.
3. Turn on remote management over HTTPS (WinRM on port 5986).
4. Create a deployment user with only the rights it needs (certificates, IIS bindings, private key permission, remote PowerShell). Store its password in CyberArk.

| Item | Your value |
|---|---|
| Server name | |
| Site name | |
| Host name in the binding | |
| Application pool user | |
| Deployment user ID | |
| Where its password is stored | |

### 7b. Linux with Apache

**Do this**
1. Use a Linux test machine (a small virtual machine or WSL). Install Apache with an HTTPS site and an old test certificate.
2. Create a deployment user that logs in by SSH key, not by password.
3. Allow that user to run only the few commands the tool needs (I will give you the exact list).

| Item | Your value |
|---|---|
| Server name | |
| Linux version | |
| Website name | |
| Certificate file path | |
| Private key file path | |
| Chain file path | |
| Deployment user ID | |
| Where its SSH key is stored | |

### 7c. Java application

**Do this**
1. Use a small Java app that uses a keystore file with an old test certificate.
2. Put the keystore password in CyberArk.
3. Find out how the app reloads the keystore, or how it is restarted.

| Item | Your value |
|---|---|
| Application name | |
| Server name | |
| Keystore file path | |
| Keystore type (JKS or PKCS12) | |
| Alias | |
| Where the keystore password is stored | |
| How it reloads or restarts | |

**Check it works:** you can open each test site or app over HTTPS, and it shows the old certificate.

---

## Step 8. Network access

**Goal:** the MID Server can reach everything it needs. All connections start from the MID Server going out.

**Do this:** ask the network team to allow the MID Server host to reach:

| # | To | Port |
|---|---|---|
| 1 | The ServiceNow instance | 443 |
| 2 | Sectigo | 443 |
| 3 | CyberArk | 443 |
| 4 | The Windows test server | 5986 |
| 5 | The Linux test server | 22 |
| 6 | The test websites and app (to check the certificate) | 443 or the app port |

Also make sure the server names resolve from the MID host, and that the clocks on all machines are correct (time sync).

**Fill in**

| Item | Your value |
|---|---|
| Firewall request numbers | |
| Proxy address (if any) | |

**Check it works:** from the MID host, connection tests to each address and port succeed.

---

## Step 9. Approvals

**Goal:** the people who must agree have agreed, before we change any real server.

**Do this:** get a yes or no on each line.

| Question | Answer |
|---|---|
| Security agrees that Sectigo creates the private key and the MID Server briefly holds it while installing it | |
| Security agrees that one certificate and key may be shared by several servers of the same service | |
| Change management agrees how automatic certificate changes are approved, and the time window for production | |
| Someone is named to call if a deployment fails or a rollback fails | |

**Fill in**

| Item | Your value |
|---|---|
| Security approver | |
| Change approver | |
| Person to call when a deployment fails | |
| Production change window | |

---

## When everything is filled in

Send me the filled steps. With that I can start building in this order: the ServiceNow application, the MID connection, the Sectigo connection, the matching, the three deployment methods (IIS, Apache, Java), and the check the next day.

**Later, for the licensed ServiceNow instance:** repeat Steps 1 to 3 for the development, test and production instances, and Step 8 for the real servers. Steps 4 to 7 are repeated for the real (pilot) servers.
