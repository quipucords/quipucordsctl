"""Global constants for quipucordsctl."""

# System commands commonly run
SYSTEMCTL_USER_RESET_FAILED_CMD = ["systemctl", "--user", "reset-failed"]
SYSTEMCTL_USER_DAEMON_RELOAD_CMD = ["systemctl", "--user", "daemon-reload"]
SYSTEMCTL_USER_STOP_QUIPUCORDS_APP = ["systemctl", "--user", "stop", "quipucords-app"]
SYSTEMCTL_USER_STOP_QUIPUCORDS_NETWORK = [
    "systemctl",
    "--user",
    "stop",
    "quipucords-network",
]

# podman secrets we use
QUIPUCORDS_SECRETS = {
    "db": "quipucords-db-password",
    "encryption": "quipucords-encryption-secret-key",
    "redis": "quipucords-redis-password",
    "server": "quipucords-server-password",
    "session": "quipucords-session-secret-key",
}

QUIPUCORDS_SECRET_KEYS = QUIPUCORDS_SECRETS.values()
