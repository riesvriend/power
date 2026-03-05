#!/bin/zsh

# Configuration
REMOTE_USER="ec2-user"
REMOTE_HOST="aws-ping-robot"
MAIN_SCRIPT="powerrates.py"

echo "Disabling cron job on ${REMOTE_HOST}..."

# Remove cron jobs that reference the main script
ssh "${REMOTE_USER}@${REMOTE_HOST}" "
(crontab -l 2>/dev/null | grep -v -F \"${MAIN_SCRIPT}\") | crontab -
"

if [ $? -eq 0 ]; then
    echo "Cron job disabled successfully."
    echo "All cron jobs referencing '${MAIN_SCRIPT}' have been removed."
else
    echo "Failed to disable cron job."
    exit 1
fi

# Display remaining cron jobs (if any)
echo ""
echo "Remaining cron jobs on remote server:"
ssh "${REMOTE_USER}@${REMOTE_HOST}" "crontab -l 2>/dev/null || echo 'No cron jobs configured.'"
