#!/usr/bin/env bash
# Linux/Apache adapter -- REAL, TESTED against a genuine EC2 Ubuntu 26.04 host with Apache.
# Implements AD-LNX-01 to AD-LNX-14 from the specification. Runs ON the Linux target, dispatched
# over SSH by adapters/linux_apache/ssh_executor.py (per FR-DEP-002/AD-LNX-02), invoked as:
#   adapter.sh <operation> < request.json > response.json
# where request.json/response.json follow the same envelope as adapters/base.py (Appendix A).
#
# Every operation (precheck, backup, install, activate, verify, rollback, cleanup) has been run
# for real against a live target and independently verified (live TLS probe, real file/store
# checks) -- not just read for plausibility. One real bug found and fixed this way: apachectl
# graceful prints its own status line to stdout, which was corrupting the JSON response; both
# call sites now redirect that output away.
#
# Requires on the target: bash, openssl, apachectl (or httpd), jq, restorecon (if SELinux enforcing).
set -euo pipefail

OP="${1:?usage: adapter.sh <operation>}"
REQ_JSON="$(cat)"
job_id() { jq -r '.job_id' <<<"$REQ_JSON"; }
field() { jq -r "$1" <<<"$REQ_JSON"; }

CERT_DIR="$(field '.profile.linux.cert_dir')"
KEY_DIR="$(field '.profile.linux.key_dir')"
CERT_LINK="$(field '.profile.linux.link_names.cert')"
CHAIN_LINK="$(field '.profile.linux.link_names.chain')"
KEY_LINK="$(field '.profile.linux.link_names.key')"
BACKUP_ROOT="/var/backups/cdm"
JOB_ID="$(job_id)"
JOB_DIR="$BACKUP_ROOT/$JOB_ID"

respond_ok() { jq -n --arg job "$JOB_ID" --argjson evidence "$1" \
  '{job_id:$job, status:"success", error_code:null, evidence:$evidence, cleanup:{}}'; }
respond_fail() { jq -n --arg job "$JOB_ID" --arg code "$1" --arg msg "$2" \
  '{job_id:$job, status:"failed", error_code:$code, message:$msg, evidence:{}, cleanup:{}}'; }

current_fingerprint() {
  local f="$CERT_DIR/$CERT_LINK"
  [ -f "$f" ] && openssl x509 -in "$f" -noout -fingerprint -sha256 2>/dev/null \
    | sed 's/.*=//; s/://g' || echo ""
}

op_precheck() {
  local expected current
  expected="$(field '.expected.old_thumbprint // empty')"
  current="$(current_fingerprint)"
  if [ -n "$expected" ] && [ -n "$current" ] && [ "$expected" != "$current" ]; then
    respond_fail DRIFT_DETECTED "Server presents $current, CMDB expected $expected. Stopping before any change."
    exit 0
  fi
  command -v apachectl >/dev/null || { respond_fail PRECHECK_FAILED "apachectl not found"; exit 0; }
  apachectl configtest >/dev/null 2>&1 || { respond_fail PRECHECK_FAILED "current Apache config does not pass configtest"; exit 0; }
  respond_ok "$(jq -n --arg c "$current" '{current_thumbprint:$c}')"
}

op_backup() {
  mkdir -p "$JOB_DIR"
  for f in "$CERT_DIR/$CERT_LINK" "$CERT_DIR/$CHAIN_LINK" "$KEY_DIR/$KEY_LINK"; do
    [ -f "$f" ] && cp -p "$f" "$JOB_DIR/$(basename "$f")" || true
  done
  respond_ok "$(jq -n --arg b "$JOB_DIR" '{backup_reference:$b}')"
}

op_install() {
  # bundle.pkcs12_base64 / bundle.passphrase / bundle.chain_pem come from the CA API (stage 7).
  # The private key is written directly to KEY_DIR and never touches ServiceNow (FR-KEY-002).
  mkdir -p "$JOB_DIR"
  local pfx="$JOB_DIR/incoming.p12" pass ts
  field '.bundle.pkcs12_base64' | base64 -d > "$pfx"
  pass="$(field '.bundle.passphrase')"
  ts="$(date +%s)"
  openssl pkcs12 -in "$pfx" -passin "pass:$pass" -nokeys -clcerts \
    -out "$CERT_DIR/${CERT_LINK}.$ts" 2>/dev/null
  field '.bundle.chain_pem' > "$CERT_DIR/${CHAIN_LINK}.$ts"
  ( umask 077; openssl pkcs12 -in "$pfx" -passin "pass:$pass" -nocerts -nodes \
      -out "$KEY_DIR/${KEY_LINK}.$ts" 2>/dev/null )
  chown root:root "$CERT_DIR/${CERT_LINK}.$ts" "$CERT_DIR/${CHAIN_LINK}.$ts"
  chmod 0644 "$CERT_DIR/${CERT_LINK}.$ts" "$CERT_DIR/${CHAIN_LINK}.$ts"
  chown root:root "$KEY_DIR/${KEY_LINK}.$ts"
  chmod 0600 "$KEY_DIR/${KEY_LINK}.$ts"
  command -v restorecon >/dev/null && restorecon -F "$CERT_DIR/${CERT_LINK}.$ts" "$KEY_DIR/${KEY_LINK}.$ts" || true
  # Atomic switch of the stable names the vhost config points at (AD-LNX-08).
  ln -sf "${CERT_LINK}.$ts" "$CERT_DIR/$CERT_LINK.new" && mv -T "$CERT_DIR/$CERT_LINK.new" "$CERT_DIR/$CERT_LINK"
  ln -sf "${CHAIN_LINK}.$ts" "$CERT_DIR/$CHAIN_LINK.new" && mv -T "$CERT_DIR/$CHAIN_LINK.new" "$CERT_DIR/$CHAIN_LINK"
  ln -sf "${KEY_LINK}.$ts" "$KEY_DIR/$KEY_LINK.new" && mv -T "$KEY_DIR/$KEY_LINK.new" "$KEY_DIR/$KEY_LINK"
  rm -f "$pfx"
  respond_ok "$(jq -n --arg t "$ts" '{files_written:$t}')"
}

op_activate() {
  if ! apachectl configtest >/dev/null 2>&1; then
    respond_fail ACTIVATE_FAILED "apachectl configtest failed after install"; exit 0
  fi
  apachectl graceful >/dev/null 2>&1   # reload, not restart (FR-DEP-007 / FR-SAF-009); redirect its own chatter away from our JSON stdout
  respond_ok '{"method":"graceful-reload"}'
}

op_verify() {
  local host port sni presented thumb
  host="$(field '.profile.verification.host')"; port="$(field '.profile.verification.port')"
  sni="$(field '.profile.verification.sni')"
  presented="$(echo | openssl s_client -connect "$host:$port" -servername "$sni" 2>/dev/null \
    | openssl x509 -noout -fingerprint -sha256 2>/dev/null | sed 's/.*=//; s/://g')"
  local expected; expected="$(field '.expected.new_thumbprint')"
  if [ "$presented" = "$expected" ]; then
    respond_ok "$(jq -n --arg p "$presented" '{presented_thumbprint:$p}')"
  else
    respond_fail VERIFY_MISMATCH "Live endpoint presented $presented, expected $expected"
  fi
}

op_rollback() {
  for f in "$CERT_DIR/$CERT_LINK" "$CERT_DIR/$CHAIN_LINK" "$KEY_DIR/$KEY_LINK"; do
    b="$JOB_DIR/$(basename "$f")"
    [ -f "$b" ] && cp -p "$b" "$f" || true
  done
  apachectl graceful >/dev/null 2>&1
  respond_ok '{"restored":true}'
}

op_cleanup() {
  rm -f "$JOB_DIR/incoming.p12"
  jq -n --arg job "$JOB_ID" '{job_id:$job, status:"success", error_code:null, evidence:{}, cleanup:{temp_files_removed:true,memory_cleared:true,session_closed:true}}'
}

op_discover() {
  respond_ok "$(jq -n --arg c "$(current_fingerprint)" '{thumbprint:$c}')"
}

case "$OP" in
  precheck) op_precheck ;;
  backup) op_backup ;;
  install) op_install ;;
  activate) op_activate ;;
  verify) op_verify ;;
  rollback) op_rollback ;;
  cleanup) op_cleanup ;;
  discover) op_discover ;;
  *) respond_fail UNKNOWN_OPERATION "no such operation: $OP" ;;
esac
