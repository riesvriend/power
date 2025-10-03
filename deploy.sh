#!/bin/zsh

# Configuration
REMOTE_USER="ec2-user"
REMOTE_HOST="aws-ping-robot"
REMOTE_DIR="/home/ec2-user/power"
LOCAL_DIR="/Users/ries/oteny/power/"
MAIN_SCRIPT="powerrates.py"
PYTHON_PATH="/usr/bin/python3"
LOG_FILE="${REMOTE_DIR}/power.log"

# How to view the log file on the remote server:
# ssh ec2-user@aws-ping-robot "tail -f /home/ec2-user/power/power.log"
#
# How to manually run the script as the cron job would:
# ssh ec2-user@aws-ping-robot "cd /home/ec2-user/power && /usr/bin/python3 powerrates.py"

# Files to exclude from deployment
EXCLUDE_FILES=(
    "__pycache__"
    ".idea"
    ".git"
    "deploy.sh"
    "power.log"
)

echo "Starting deployment to ${REMOTE_HOST}..."

# Create remote directory if it doesn't exist
ssh "${REMOTE_USER}@${REMOTE_HOST}" "mkdir -p ${REMOTE_DIR}"

# Build exclude options for rsync
EXCLUDE_OPTS=""
for item in "${EXCLUDE_FILES[@]}"; do
    EXCLUDE_OPTS+="--exclude '${item}' "
done

# Sync files to the remote server
echo "Syncing files..."
eval "rsync -avz --delete ${EXCLUDE_OPTS} '${LOCAL_DIR}' '${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/'"

# Setup cron job on the remote server
echo "Setting up cron job..."
CRON_COMMAND="cd ${REMOTE_DIR} && ${PYTHON_PATH} ${MAIN_SCRIPT} >> ${LOG_FILE} 2>&1"
CRON_JOB="0 */4 * * * ${CRON_COMMAND}"

ssh "${REMOTE_USER}@${REMOTE_HOST}" "
(crontab -l 2>/dev/null | grep -v -F \"${MAIN_SCRIPT}\" ; echo \"${CRON_JOB}\") | crontab -
"

echo "Deployment and cron job setup complete."
