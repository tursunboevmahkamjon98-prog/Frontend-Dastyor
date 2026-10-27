#!/usr/bin/env bash
# Repairs the SMS/SMTP half of an existing .env without touching anything
# else — the database password, SECRET_KEY and ADMIN_PASSWORD in there were
# generated on this machine by scripts/init-env.sh and cannot be recreated
# from anywhere else, so they must survive untouched.
set -euo pipefail
cd "$(dirname "$0")"

[ -f .env ] || { echo "No .env here. cd to the directory holding docker-compose.yml first."; exit 1; }

cp .env ".env.backup.$(date +%Y%m%d-%H%M%S)"

# Rewrites key=value in place if the key exists, appends it otherwise.
# awk rather than sed -i: sed's -i flag differs between BSD and GNU, and
# the values below contain characters sed would treat as delimiters.
set_var() {
    if grep -qE "^$1=" .env; then
        awk -v k="$1" -v v="$2" 'BEGIN{FS=OFS="="} $1==k {print k "=" v; next} {print}' .env > .env.tmp
        mv .env.tmp .env
    else
        printf '%s=%s\n' "$1" "$2" >> .env
    fi
}

# SMTP is e-mail only. The Robita portal credentials had been pasted in
# here, which broke outgoing mail and did nothing for SMS: send_sms_code()
# never reads these.
set_var SMTP_HOST      "smtp.gmail.com"
set_var SMTP_PORT      "587"
set_var SMTP_USER      "tursunboevmahkamjon98@gmail.com"
set_var SMTP_PASSWORD  "ajswzhgjpconnhzw"
set_var SMTP_FROM_NAME "TeachAIweb"

# The SMS provider the OTP codes actually go through.
set_var ROBITA_LOGIN     "Dast"
set_var ROBITA_PASSWORD  "Dastyor@7575"
set_var ROBITA_SENDER    "0176"
set_var SMS_DRY_RUN      "false"
set_var OTP_BYPASS_PHONE ""

chmod 600 .env
echo "Done. Variables now present (names only):"
grep -oE "^(SMTP|ROBITA|SMS_DRY_RUN|OTP_BYPASS_PHONE)[A-Z_]*" .env | sort | tr '\n' ' '
echo
