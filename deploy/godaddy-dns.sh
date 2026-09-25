#!/usr/bin/env bash
# Point a GoDaddy-managed hostname at this server.
#
#   ./godaddy-dns.sh <zone> <host> [ip]
#     zone  registered domain in GoDaddy, e.g. example.com
#     host  "@" for the apex, or a subdomain label, e.g. drums
#     ip    server's public IPv4 (default: auto-detect)
#
# Uses the GoDaddy Domains API when GODADDY_KEY/GODADDY_SECRET are set and the
# account has API access (GoDaddy limits DNS API access to accounts with 10+
# domains or an active Discount Domain Club plan). Otherwise prints the record
# to add by hand in the GoDaddy DNS panel. Either way, it then checks resolution.
set -euo pipefail

ZONE="${1:-}"; HOST="${2:-}"; IP="${3:-}"
if [[ -z "$ZONE" || -z "$HOST" ]]; then
  sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
  exit 1
fi

HERE="$(cd "$(dirname "$0")" && pwd)"
[[ -f "$HERE/.env" ]] && set -a && . "$HERE/.env" && set +a

if [[ -z "$IP" ]]; then
  IP="$(curl -fsS4 https://api.ipify.org || true)"
  [[ -z "$IP" ]] && { echo "Could not detect public IP; pass it as the 3rd argument." >&2; exit 1; }
fi
FQDN=$([[ "$HOST" == "@" ]] && echo "$ZONE" || echo "$HOST.$ZONE")
TTL=600
API="https://api.godaddy.com/v1/domains"

manual() {
  cat <<EOF

--- Add this record manually ---
GoDaddy > My Products > $ZONE > DNS > Manage DNS > Add New Record
  Type:  A
  Name:  $HOST
  Value: $IP
  TTL:   $TTL seconds (or "1/2 Hour")
If an A or CNAME record with Name "$HOST" already exists, edit it instead of adding a second one.
EOF
}

updated=0
if [[ -n "${GODADDY_KEY:-}" && -n "${GODADDY_SECRET:-}" ]]; then
  AUTH="Authorization: sso-key ${GODADDY_KEY}:${GODADDY_SECRET}"
  code=$(curl -s -o /tmp/gd_check.json -w '%{http_code}' -H "$AUTH" "$API/$ZONE")
  case "$code" in
    200)
      echo "GoDaddy API access OK. Setting A $FQDN -> $IP"
      code=$(curl -s -o /tmp/gd_put.json -w '%{http_code}' -X PUT \
        -H "$AUTH" -H 'Content-Type: application/json' \
        -d "[{\"data\":\"$IP\",\"ttl\":$TTL}]" \
        "$API/$ZONE/records/A/$HOST")
      if [[ "$code" == 200 ]]; then updated=1; echo "Record updated."
      else echo "Update failed (HTTP $code): $(cat /tmp/gd_put.json)"; fi
      ;;
    401|403)
      echo "GoDaddy API refused access (HTTP $code): either the key/secret is wrong, or the"
      echo "account does not meet GoDaddy's API eligibility (10+ domains or Discount Domain Club)."
      ;;
    404) echo "Zone $ZONE not found in this GoDaddy account (HTTP 404)." ;;
    *)   echo "Unexpected GoDaddy API response (HTTP $code): $(cat /tmp/gd_check.json)" ;;
  esac
else
  echo "GODADDY_KEY/GODADDY_SECRET not set; skipping API."
fi

[[ $updated == 1 ]] || manual

echo
echo "Checking public DNS for $FQDN (may take a few minutes after a change)..."
for i in $(seq 1 30); do
  got=$(dig +short A "$FQDN" @1.1.1.1 2>/dev/null | tail -n1 || true)
  [[ -z "$got" ]] && got=$(getent hosts "$FQDN" | awk '{print $1}' || true)
  if [[ "$got" == "$IP" ]]; then echo "OK: $FQDN resolves to $IP"; exit 0; fi
  printf '  [%02d] %s -> %s\n' "$i" "$FQDN" "${got:-no answer}"
  sleep 20
done
echo "Not resolving to $IP yet. Re-run this script later to check again."
exit 2
