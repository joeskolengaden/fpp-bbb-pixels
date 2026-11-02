#!/bin/bash
# Create the two helper scripts every hwtest tool uses to reach the board (ssh and scp), with a PRIVATE known_hosts file.
#   bash board-wrappers.sh [host=192.168.6.2] [user=fpp]
# The board's host key is shown to you and only stored after you confirm the fingerprint (compare it with the one on the board's console:
# ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub). Nothing is trusted silently, and host-key checking stays ON for every later call.
set -e
HOST="${1:-192.168.6.2}"; USER_="${2:-fpp}"
DIR="${FBP_BOARD_DIR:-$(cd "$(dirname "$0")" && pwd)/.board}"
mkdir -p "$DIR"; chmod 700 "$DIR"
KEY=$(ssh-keyscan -T 5 -t ed25519 "$HOST" 2>/dev/null)
[ -n "$KEY" ] || { echo "could not read the host key of $HOST (is the board reachable?)" >&2; exit 1; }
echo "$KEY" | ssh-keygen -lf - | sed 's/^/board host key: /'
read -r -p "Does this fingerprint match the board? [y/N] " ok
[ "$ok" = y ] || [ "$ok" = Y ] || { echo "not trusted, nothing written"; exit 1; }
echo "$KEY" > "$DIR/known_hosts"
cat > "$DIR/bbg" <<W
#!/bin/bash
exec ssh -o UserKnownHostsFile="$DIR/known_hosts" -o StrictHostKeyChecking=yes -o ConnectTimeout=\${BBG_TIMEOUT:-20} $USER_@$HOST "\$@"
W
cat > "$DIR/bbgcp" <<W
#!/bin/bash
exec scp -o UserKnownHostsFile="$DIR/known_hosts" -o StrictHostKeyChecking=yes "\$@"
W
chmod +x "$DIR/bbg" "$DIR/bbgcp"
echo "ready: $DIR/bbg 'uname -a'   (set FBP_BOARD_DIR=$DIR if you keep it elsewhere)"
