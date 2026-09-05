#!/bin/bash
# Ryan-present install (needs sudo; the agent account only has NOPASSWD for systemctl ollama).
# Run ON ryan-spark:  sudo bash ~/models/flash-next/unit/install.sh
set -euo pipefail
U=/home/ryanneely1000/models/flash-next/unit
install -m 0644 $U/flash-next.service $U/flash-next-health.service $U/flash-next-health.timer /etc/systemd/system/
install -m 0755 $U/flash-next-health.sh /home/ryanneely1000/models/flash-next/flash-next-health.sh
chown ryanneely1000:ryanneely1000 /home/ryanneely1000/models/flash-next/flash-next-health.sh
systemctl daemon-reload
# Let the agent account manage the pilot without a password, same shape as the ollama grant:
cat > /etc/sudoers.d/flash-next <<'SUD'
ryanneely1000 ALL=(root) NOPASSWD: /usr/bin/systemctl start flash-next, /usr/bin/systemctl stop flash-next, /usr/bin/systemctl restart flash-next, /usr/bin/systemctl is-active flash-next, /usr/bin/systemctl start flash-next-health.timer, /usr/bin/systemctl stop flash-next-health.timer
SUD
chmod 0440 /etc/sudoers.d/flash-next; visudo -cf /etc/sudoers.d/flash-next
echo "installed. NOT enabled/started: the flip (t_37efebbb) evicts 120b+27b first, then: systemctl enable --now flash-next flash-next-health.timer"
