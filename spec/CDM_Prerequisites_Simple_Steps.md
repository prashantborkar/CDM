# CDM: Build Your Own Test Environment, Step by Step (one person)

This guide is for one person working alone. No other team is needed. You will create every account and machine yourself, install the MID Server, and set up the test websites. Follow the steps in order. In each step: do the tasks, fill in the blanks, run the check.

> **About passwords.** Do not write passwords or keys in this file. Use a password manager. Where a step asks for a password, write only **where it is stored** (for example "password manager, entry ServiceNow admin").

**What you will have at the end**

```text
 ServiceNow personal instance (cloud)          <- MID Server connects OUT to it
                                                        |
 AWS account
   Windows machine (cdm-win-01)  = MID Server + IIS test website (+ Sectigo test service)
   Linux machine   (cdm-lnx-01)  = Apache test website + Java (Tomcat) test app

 The MID Server (on the Windows machine) will later deploy new certificates to IIS, Apache and Java.
```

**Cost and time.** The two AWS machines cost a small amount per hour while running (Windows costs more than Linux). Check the current prices on the AWS pricing page and set a budget alert (Step 3). **Stop the machines when you are not using them.** Plan about one working day for everything.

**What you need before you start:** an email address, a mobile phone, a debit or credit card (for AWS), a computer with a browser and Git Bash, and a password manager.

---

## Step 1. ServiceNow personal instance

**Goal:** the ServiceNow instance where we build CDM.

**Do this**
1. Go to developer.servicenow.com and sign in (or create a free account).
2. Click **Request an Instance** and choose the newest release.
3. Open the instance URL and log in as admin.
4. Write down the URL, admin user name and release.
5. Log in every few days so the instance stays active.

| Item | Your value |
|---|---|
| Instance URL (for example https://dev12345.service-now.com) | |
| Admin user name | |
| Where the admin password is stored | |
| Release | |

**Check:** you can log in and see the home page.

---

## Step 2. Users in ServiceNow

**Goal:** users for building, and to test the roles later.

**Do this**
1. Open **User Administration > Users** and create: a developer user, a test owner, a test approver, a test auditor.
2. Give the developer user the admin role for now.
3. Put an email address on each user.

| User | User ID | Where the password is stored |
|---|---|---|
| Developer | | |
| Test owner | | |
| Test approver | | |
| Test auditor | | |

**Check:** each user can log in.

---

## Step 3. AWS account

**Goal:** an AWS account where you create the test machines.

**Do this**
1. Go to aws.amazon.com and click **Create an AWS account**. Enter email, account name, card and phone verification. Choose the basic (free) support plan.
2. Sign in as the root user. Open **Security credentials** and turn on **MFA** for the root user (use an authenticator app).
3. Open **IAM > Users > Create user**. Name it `admin-lab`, give it **AdministratorAccess**, and turn on MFA for it too. From now on sign in with this user, not root.
4. Open **Billing > Budgets** and create a monthly cost budget with an email alert (for example a small amount you are comfortable with).
5. Pick one **region** near you (top right corner of the console) and use only that region.

| Item | Your value |
|---|---|
| AWS account ID | |
| IAM user name | |
| Where the password and MFA are stored | |
| Region | |
| Budget amount | |

**Check:** you can sign in as `admin-lab` and see the EC2 page.

---

## Step 4. AWS network access and key

**Goal:** the two machines can talk to each other, and only you can reach them from outside.

**Do this**
1. Open **EC2 > Key Pairs > Create key pair**. Name it `cdm-lab-key`, type **RSA**, format **.pem**. Save the downloaded file safely (you cannot download it again).
2. Open **EC2 > Security Groups > Create security group**. Name it `cdm-lab-sg` and use the default network (VPC).
3. Add these **inbound** rules:

| Type | Port | Source |
|---|---|---|
| RDP | 3389 | **My IP** |
| SSH | 22 | **My IP** |
| All traffic | all | The same security group `cdm-lab-sg` (so the two machines can reach each other) |

4. Never open RDP or SSH to "anywhere" (0.0.0.0/0).
5. Leave outbound as it is (all allowed). The MID Server needs outbound HTTPS to ServiceNow.

| Item | Your value |
|---|---|
| Key pair name and where the .pem file is kept | |
| Security group name | |
| My public IP (shown in the rule) | |

**Check:** the security group shows the three inbound rules.

---

## Step 5. Windows machine (MID Server and IIS)

**Goal:** a Windows server that will run the MID Server and the IIS test website.

**Do this**
1. Open **EC2 > Launch instance**.
2. Name: `cdm-win-01`. Image: **Microsoft Windows Server 2022 Base**.
3. Instance type: `t3.medium` (2 CPU, 4 GB). Storage: 40 GB.
4. Key pair: `cdm-lab-key`. Security group: `cdm-lab-sg`.
5. Launch. Wait until the status checks pass.
6. Select the instance > **Connect > RDP client > Get password**. Upload the `.pem` file to decrypt the administrator password. Save that password in your password manager.
7. Connect with Remote Desktop using the public IP, user `Administrator`.
8. On the machine, open Windows Update and install updates when convenient.

| Item | Your value |
|---|---|
| Instance name | cdm-win-01 |
| Public IP (changes when stopped and started) | |
| Private IP (stays the same) | |
| Administrator password stored in | |

**Check:** you are logged in to the Windows machine by Remote Desktop.

---

## Step 6. Linux machine (Apache and Java)

**Goal:** a Linux server for the Apache website and the Java test app.

**Do this**
1. **EC2 > Launch instance**. Name: `cdm-lnx-01`. Image: **Amazon Linux 2023**.
2. Instance type: `t3.small`. Storage: 20 GB.
3. Key pair: `cdm-lab-key`. Security group: `cdm-lab-sg`.
4. Launch and wait for the status checks.
5. In Git Bash on your computer, connect:

```bash
chmod 400 /path/to/cdm-lab-key.pem
ssh -i /path/to/cdm-lab-key.pem ec2-user@<public-ip-of-cdm-lnx-01>
```

| Item | Your value |
|---|---|
| Instance name | cdm-lnx-01 |
| Public IP | |
| Private IP | |

**Check:** you get a shell prompt on the Linux machine.

---

## Step 7. MID Server on the Windows machine

**Goal:** the agent that will do the deployments. It only connects out to ServiceNow.

**Do this**
1. In ServiceNow open **User Administration > Users**, create a user for the MID Server (for example `mid.lab`) and give it the role **mid_server**. This is not a person.
2. On `cdm-win-01`, open a browser and log in to your ServiceNow instance. Go to **MID Server > Downloads** and download the Windows 64-bit zip.
3. Unzip it to `C:\ServiceNow_MID`.
4. The MID package usually contains the Java it needs. If the installer asks for Java, install Java 17.
5. Edit `C:\ServiceNow_MID\agent\config.xml`: set the instance URL, the MID user name and password, and the MID name (for example `mid-lab-01`). The password stays only in this file on this machine.
6. Start the MID Server (run the batch file or install and start the service, as the instructions in the download say).
7. In ServiceNow open **MID Server > Servers** and click **Validate** for your MID.

| Item | Your value |
|---|---|
| MID Server name | |
| MID user name in ServiceNow | |
| Where the MID user password is stored | |

**Check:** **MID Server > Servers** shows your MID as **Up** and **Validated**.

---

## Step 8. IIS test website with secure remote access

**Goal:** an IIS website with an old test certificate, and remote management over HTTPS (WinRM), which is how the MID Server will deploy.

**Do this** on `cdm-win-01`, in PowerShell as Administrator.

1. Install IIS:
```powershell
Install-WindowsFeature Web-Server -IncludeManagementTools
```
2. Create an old test certificate (valid 10 days) and bind it to the website:
```powershell
$cert = New-SelfSignedCertificate -DnsName "web01.lab.example.com" -CertStoreLocation Cert:\LocalMachine\My -NotAfter (Get-Date).AddDays(10)
Import-Module WebAdministration
New-WebBinding -Name "Default Web Site" -Protocol https -Port 443 -HostHeader "web01.lab.example.com" -SslFlags 1
(Get-WebBinding -Name "Default Web Site" -Protocol https).AddSslCertificate($cert.Thumbprint, "My")
$cert.Thumbprint
```
3. Turn on WinRM over HTTPS:
```powershell
$winrm = New-SelfSignedCertificate -DnsName $env:COMPUTERNAME -CertStoreLocation Cert:\LocalMachine\My
New-Item -Path WSMan:\LocalHost\Listener -Transport HTTPS -Address * -CertificateThumbPrint $winrm.Thumbprint -Force
New-NetFirewallRule -DisplayName "WinRM HTTPS" -Direction Inbound -Protocol TCP -LocalPort 5986 -Action Allow
```
4. Create the deployment user (lab only) and let it use remote management:
```powershell
net user cdmdeploy "<a-long-random-password>" /add
net localgroup Administrators cdmdeploy /add
New-ItemProperty -Path HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System -Name LocalAccountTokenFilterPolicy -Value 1 -PropertyType DWord -Force
```
Put that password in your password manager.

| Item | Your value |
|---|---|
| Website host name | web01.lab.example.com |
| Website name | Default Web Site |
| Old certificate thumbprint (printed above) | |
| Deployment user ID | cdmdeploy |
| Where its password is stored | |

**Check:** in PowerShell, `Test-WSMan -ComputerName localhost -UseSSL -Port 5986` succeeds, and `Get-WebBinding -Protocol https` shows the binding.

---

## Step 9. Apache test website on Linux

**Goal:** an Apache website with an old test certificate, and a deployment user.

**Do this** on `cdm-lnx-01` (SSH session).

1. Install Apache with HTTPS support:
```bash
sudo dnf install -y httpd mod_ssl
sudo systemctl enable --now httpd
```
2. Create an old test certificate (valid 10 days):
```bash
sudo openssl req -x509 -newkey rsa:3072 -nodes -days 10 \
  -keyout /etc/pki/tls/private/portal.key -out /etc/pki/tls/certs/portal.crt \
  -subj "/CN=portal.lab.example.com" -addext "subjectAltName=DNS:portal.lab.example.com"
sudo chmod 600 /etc/pki/tls/private/portal.key
```
3. Point Apache at it: open `/etc/httpd/conf.d/ssl.conf` and set `SSLCertificateFile /etc/pki/tls/certs/portal.crt` and `SSLCertificateKeyFile /etc/pki/tls/private/portal.key`. Then:
```bash
sudo apachectl configtest
sudo systemctl reload httpd
```
4. On **your own computer** (Git Bash) create a key pair for the deployment user:
```bash
ssh-keygen -t ed25519 -f ~/cdm_deploy_key -N ""
cat ~/cdm_deploy_key.pub
```
5. Back on the Linux machine, create the deployment user and add the public key you just printed:
```bash
sudo useradd -m cdmdeploy
sudo mkdir -p /home/cdmdeploy/.ssh
echo "<paste the public key line here>" | sudo tee /home/cdmdeploy/.ssh/authorized_keys
sudo chown -R cdmdeploy:cdmdeploy /home/cdmdeploy/.ssh
sudo chmod 700 /home/cdmdeploy/.ssh && sudo chmod 600 /home/cdmdeploy/.ssh/authorized_keys
```
6. Lab only: let the deployment user run commands as root (we will tighten this later with a wrapper script):
```bash
echo "cdmdeploy ALL=(root) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/cdm
```

| Item | Your value |
|---|---|
| Website host name | portal.lab.example.com |
| Certificate file | /etc/pki/tls/certs/portal.crt |
| Private key file | /etc/pki/tls/private/portal.key |
| Deployment user ID | cdmdeploy |
| Where the private key file `cdm_deploy_key` is kept | |

**Check:** `ssh -i ~/cdm_deploy_key cdmdeploy@<linux-private-or-public-ip> 'sudo apachectl configtest'` prints "Syntax OK".

---

## Step 10. Java test app on Linux

**Goal:** a Java app (Tomcat) using a keystore with an old test certificate.

**Do this** on `cdm-lnx-01`.

1. Install Java and Tomcat:
```bash
sudo dnf install -y java-17-amazon-corretto-devel
cd /tmp
# download the latest Tomcat 9 tar.gz from tomcat.apache.org (Binary Distributions, Core, tar.gz), then:
sudo mkdir -p /opt/tomcat && sudo tar xzf apache-tomcat-9.*.tar.gz -C /opt/tomcat --strip-components=1
```
2. Create the keystore with an old test certificate (valid 10 days). Choose a password and keep it in your password manager:
```bash
sudo /usr/lib/jvm/java-17-amazon-corretto/bin/keytool -genkeypair -alias api -keyalg RSA -keysize 3072 \
  -storetype PKCS12 -keystore /opt/tomcat/conf/keystore.p12 -validity 10 \
  -dname "CN=api.lab.example.com" -ext "san=dns:api.lab.example.com"
```
3. In `/opt/tomcat/conf/server.xml` add an HTTPS connector on port 8443:
```xml
<Connector port="8443" protocol="org.apache.coyote.http11.Http11NioProtocol" SSLEnabled="true">
  <SSLHostConfig>
    <Certificate certificateKeystoreFile="/opt/tomcat/conf/keystore.p12"
                 certificateKeystorePassword="<keystore-password>" type="RSA"/>
  </SSLHostConfig>
</Connector>
```
4. Start Tomcat: `sudo /opt/tomcat/bin/startup.sh`

| Item | Your value |
|---|---|
| Application name | api |
| Website host name | api.lab.example.com |
| Keystore file | /opt/tomcat/conf/keystore.p12 |
| Keystore type | PKCS12 |
| Alias | api |
| Where the keystore password is stored | |
| How to restart it | /opt/tomcat/bin/shutdown.sh then startup.sh |

**Check:** `openssl s_client -connect localhost:8443 -servername api.lab.example.com </dev/null | openssl x509 -noout -dates` shows the dates of your test certificate.

---

## Step 11. Let the machines find each other by name

**Goal:** the MID Server can reach the test sites using their names (no DNS needed).

**Do this:** on `cdm-win-01`, open Notepad **as Administrator**, open `C:\Windows\System32\drivers\etc\hosts`, and add these lines (use your private IPs from Steps 5 and 6):

```text
<private-ip-of-cdm-win-01>  web01.lab.example.com
<private-ip-of-cdm-lnx-01>  portal.lab.example.com
<private-ip-of-cdm-lnx-01>  api.lab.example.com
```

Also check that the clock is correct on both machines (Windows: Settings > Time; Linux: `timedatectl`).

**Check:** on `cdm-win-01`, in PowerShell: `Test-NetConnection portal.lab.example.com -Port 22` and `Test-NetConnection portal.lab.example.com -Port 443` succeed. (Port 443 on Linux is Apache; port 22 is SSH.)

---

## Step 12. Keep the passwords and keys in ServiceNow (temporary)

**Goal:** CDM reads every password from a vault. For your test, use ServiceNow's own encrypted credential store. In production this is replaced by CyberArk, which a single person cannot set up alone.

**Do this:** in ServiceNow open **Connections & Credentials > Credentials** and create:

| Credential | Type | Contents |
|---|---|---|
| Windows deployment | Windows | user `cdmdeploy` and its password |
| Linux deployment | SSH private key | user `cdmdeploy` and the private key `cdm_deploy_key` |
| Java keystore | Basic auth | any user name and the keystore password |
| Sectigo | Basic auth | API user and password (later, Step 14) |

| Credential name in ServiceNow | Your value |
|---|---|
| Windows deployment | |
| Linux deployment | |
| Java keystore | |
| Sectigo | |

**Check:** the four credentials are listed.

---

## Step 13. Certificate records in ServiceNow

**Goal:** confirm ServiceNow has the certificate data we match on (name, thumbprint, serial, SAN, server, dates).

**Do this**
1. In ServiceNow open the list of certificate records in the CMDB (the certificate table).
2. If records exist, open five and check the fields above. Tell me the exact field names.
3. If there are none (normal on a personal instance), that is fine. I will build a small **scan simulator** that reads the certificates from your test servers every day and creates or updates the records. You only need the test servers from Steps 8 to 10.

| Item | Your value |
|---|---|
| Certificate records exist (yes or no) | |
| Field names for thumbprint, serial, SAN, server, valid from, valid to, last scanned (if yes) | |

---

## Step 14. Sectigo

**Goal:** a source of new certificates for CDM. Choose one path.

**Path A: use my test service (start here; no account needed).**
I will build a small test service that behaves like the Sectigo landing area: it lists new certificates and delivers the certificate together with its private key. It runs on `cdm-win-01`. You do nothing now.

**Path B: a real Sectigo trial or sandbox.**
1. Go to sectigo.com and ask for a trial or sandbox of **Sectigo Certificate Manager** (use the contact or sales form).
2. Ask them, in writing:
   - can the private key be created together with the certificate and downloaded by API?
   - which API call, and in which format (usually PKCS#12)?
   - how many downloads, for how long, and does Sectigo keep a copy of the key?
   - can you get test certificates with a short validity?
3. Create an API account for CDM in Sectigo and keep its password in your password manager.

| Item | Your value |
|---|---|
| Path chosen (A or B) | |
| Sectigo API address (if B) | |
| Customer URI (if B) | |
| API user name (if B) | |
| Where the API password is stored (if B) | |

Paste Sectigo's answer about the private key here (if B):

> 

---

## Step 15. Decisions you make yourself

Since you are the only person, you decide. Suggested answers are filled in. Change them if you like.

| Decision | Suggested | Your choice |
|---|---|---|
| Start renewing when remaining life is at most | 30 days, or 33 percent of the lifetime if that is smaller (minimum 3 days) | |
| Deploy as soon as the new certificate lands | No, wait for the renewal window | |
| Approval needed before deploying (lab) | No | |
| Time window for deploying | Any time in the lab | |
| One certificate and key shared by servers of the same service | Yes | |
| Alert if the next-day scan has not confirmed within | 36 hours | |

---

## Step 16. Send me this

When the steps are done, send me:
1. All the filled tables (no passwords).
2. The sample of certificate records, or a note that there are none (Step 13).
3. Your answer for Step 14 (Path A or B).

Then I build, in this order: the ServiceNow application, the connection to the MID Server, the Sectigo (or test) connection, the matching, the three deployment methods (IIS, Apache, Java), and the check the next day.

---

## When you are finished for the day

- **Stop** both EC2 machines (EC2 > select > Instance state > Stop). The public IPs will change when you start them again; the private IPs stay the same.
- When the whole test is over, **terminate** the instances so you are not billed, and delete unused storage.

## Later, for the real (licensed) setup

The real setup adds things one person cannot create alone: the company's Sectigo account, CyberArk, real servers and firewall rules. Those are listed in `CDM_Prerequisites_and_Readiness.md`. Everything you build here carries over: the same application, the same settings and the same deployment methods.
