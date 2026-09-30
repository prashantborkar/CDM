"""A real ACME client for CDM, built on the `acme`/`josepy` libraries -- the same engine certbot
itself is built on -- instead of shelling out to certbot. This removes the one real gap the local
test CA (mini_acme_ca.py) deliberately skipped: every request here is a properly signed JWS
(JSON Web Signature), tied to a persistent account key, exactly as real ACME servers require.

Why not just keep using certbot: certbot also insists on owning the install step (it wants to
edit Apache's config itself). CDM already has tested, careful installers for Windows/Linux/Java
with backup+verify+rollback -- this client's only job is to get a certificate and hand it back in
the same {cert_pem, key_pem, chain_pem} shape every other source in sources/ uses, so it slots
into the existing pipeline instead of fighting it.

Challenge fulfillment (HTTP-01) is done here over the same SSH path ssh_executor.py already uses
to talk to the EC2 target -- no certbot, no webroot plugin, just CDM placing the proof file itself.

Domain: real public ACME CAs can only issue for names that resolve on the public internet (see
module docstring history in mini_acme_ca.py / the vhost setup on the EC2 box for why). This
targets 16-16-120-70.nip.io, the free wildcard-DNS name already pointed at the EC2 box, until a
real product domain exists.
"""
import subprocess
import sys
from pathlib import Path

import josepy as jose
from acme import client as acme_client
from acme import errors as acme_errors
from acme import messages
from acme import challenges
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vault_stub.vault import get_credential  # noqa: E402

DIRECTORY_URL = "https://acme-staging-v02.api.letsencrypt.org/directory"  # staging: safe, no rate limits
ACCOUNT_KEY_PATH = Path(__file__).parent / "pki" / "acme_account_key.pem"
CONTACT_EMAIL = "contact@qubra.uk"

# Where the target's webroot is, and how to reach it -- reused from the deployment profile
# shape already established in config/deployment_profiles.json.
SSH_HOST = "16.16.120.70"
SSH_CRED_ALIAS = "lab/ec2_linux_deploy"
WEBROOT = "/var/www/html"


def _load_or_create_account_key() -> jose.JWKRSA:
    ACCOUNT_KEY_PATH.parent.mkdir(exist_ok=True)
    if ACCOUNT_KEY_PATH.exists():
        pem = ACCOUNT_KEY_PATH.read_bytes()
        key = serialization.load_pem_private_key(pem, password=None)
    else:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        ACCOUNT_KEY_PATH.write_bytes(key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    return jose.JWKRSA(key=jose.ComparableRSAKey(key))


def _ssh(cmd: str) -> str:
    cred = get_credential(SSH_CRED_ALIAS)
    key_path = cred["secret"]
    full = ["ssh", "-i", key_path, "-o", "StrictHostKeyChecking=accept-new",
            "-o", "ConnectTimeout=10", f"{cred['username']}@{SSH_HOST}", cmd]
    proc = subprocess.run(full, capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        raise RuntimeError(f"SSH command failed: {cmd}\n{proc.stderr}")
    return proc.stdout


def _place_http01_response(token: str, validation_content: str):
    """Writes the ACME HTTP-01 proof file directly onto the target over SSH -- this is the
    'prove you control the domain' step, done by CDM's own code instead of certbot's webroot
    plugin or Apache module."""
    remote_dir = f"{WEBROOT}/.well-known/acme-challenge"
    _ssh(f"sudo mkdir -p {remote_dir} && "
         f"echo '{validation_content}' | sudo tee {remote_dir}/{token} > /dev/null && "
         f"sudo chmod 0644 {remote_dir}/{token}")


def issue_certificate(domain: str) -> dict:
    account_key = _load_or_create_account_key()
    net = acme_client.ClientNetwork(account_key, user_agent="cdm-acme-client/1.0")
    directory = acme_client.ClientV2.get_directory(DIRECTORY_URL, net)
    client = acme_client.ClientV2(directory, net=net)

    try:
        regr = client.new_account(
            messages.NewRegistration.from_data(email=CONTACT_EMAIL, terms_of_service_agreed=True))
        print(f"  [real-acme] account registered: {regr.uri}")
    except acme_errors.ConflictError as exc:
        # This account key is already registered with the CA -- reuse it, same as a real client would.
        account_uri = exc.location
        regr = messages.RegistrationResource(
            body=messages.Registration(), uri=account_uri)
        client.net.account = regr
        print(f"  [real-acme] account already registered, reusing: {account_uri}")

    cert_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    csr = (x509.CertificateSigningRequestBuilder()
           .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, domain)]))
           .add_extension(x509.SubjectAlternativeName([x509.DNSName(domain)]), critical=False)
           .sign(cert_key, hashes.SHA256()))
    csr_pem = csr.public_bytes(serialization.Encoding.PEM)

    order = client.new_order(csr_pem)
    print(f"  [real-acme] order created, {len(order.authorizations)} authorization(s) pending")

    for authz in order.authorizations:
        http01 = next(c for c in authz.body.challenges if isinstance(c.chall, challenges.HTTP01))
        response, validation = http01.response_and_validation(client.net.key)
        token_str = http01.chall.encode("token")
        print(f"  [real-acme] placing HTTP-01 proof on {SSH_HOST} via SSH (token {token_str[:16]}...)")
        _place_http01_response(token_str, validation)
        client.answer_challenge(http01, response)

    print(f"  [real-acme] waiting for Let's Encrypt to validate + finalize...")
    finalized = client.poll_and_finalize(order)
    print(f"  [real-acme] issued: {finalized.fullchain_pem[:60].splitlines()[0]}...")

    leaf = x509.load_pem_x509_certificate(finalized.fullchain_pem.encode().split(b"-----END CERTIFICATE-----")[0]
                                           + b"-----END CERTIFICATE-----\n")
    key_pem = cert_key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()

    return {
        "domain": domain,
        "cert_pem": finalized.fullchain_pem,
        "key_pem": key_pem,
        "serial": format(leaf.serial_number, "x"),
        "thumbprint": leaf.fingerprint(hashes.SHA256()).hex().upper(),
        "issuer": leaf.issuer.rfc4514_string(),
        "not_before": leaf.not_valid_before_utc.isoformat(),
        "not_after": leaf.not_valid_after_utc.isoformat(),
    }


if __name__ == "__main__":
    domain = sys.argv[1] if len(sys.argv) > 1 else "16-16-120-70.nip.io"
    print(f"Requesting a REAL certificate for {domain} via CDM's own ACME client (no certbot)...\n")
    result = issue_certificate(domain)
    print(f"\nISSUED:")
    for k in ("domain", "issuer", "serial", "thumbprint", "not_before", "not_after"):
        print(f"  {k}: {result[k]}")
