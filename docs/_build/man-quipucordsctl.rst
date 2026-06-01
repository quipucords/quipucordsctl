quipucordsctl
==============================

Synopsis
--------

.. code-block:: none

   quipucordsctl [--help] [-v | --verbose] [-q | --quiet]
       [-y | --yes] [-C {auto|always|never} | --color {auto|always|never}]
       [-c DIRECTORY | --override-conf-dir DIRECTORY]
       COMMAND [ARGS]

Description
-----------

**quipucordsctl** is a command-line management tool for Quipucords, an agentless inspection and reporting tool that collects relevant facts about Red Hat software usage. This tool simplifies the installation, configuration, and management of Quipucords and all of its required components to run in Podman containers on your local system.

The quipucordsctl tool manages the complete lifecycle of a Quipucords deployment, including container image management, systemd service configuration, database setup, and secret management. It provides commands for installation, health checking, secret rotation, log collection, and system maintenance.

By default, Quipucords configuration is stored under ``~/.config/quipucords/`` and application data under ``~/.local/share/quipucords/`` in your home directory. The Quipucords services run as systemd user services, which means no root privileges are required for normal operation after the initial package installation.

This manual page describes the commands and options for the ``quipucordsctl`` command and includes usage information and example commands.

Usage
-----

The ``quipucordsctl`` command manages the Quipucords deployment lifecycle. Within that workflow, ``quipucordsctl`` performs the following major tasks:

* Installing Quipucords:

  ``quipucordsctl install``

* Checking system health:

  ``quipucordsctl check``

* Resetting administrator credentials:

  ``quipucordsctl reset_admin_password``

  ``quipucordsctl reset_admin_username``

* Collecting diagnostic logs:

  ``quipucordsctl export_logs``

* Uninstalling Quipucords:

  ``quipucordsctl uninstall``

The following sections describe these commands and their options in more detail.

Installation
------------

Installing Quipucords
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To install Quipucords and configure all required components, use the ``install`` command. This command sets up container volumes, generates initial secrets, creates systemd service unit files, and prepares the environment for running Quipucords.

``quipucordsctl install``

After installation, start the Quipucords application service:

``systemctl --user restart quipucords-app``

After a few seconds, access Quipucords at https://localhost:9443

Uninstalling Quipucords
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To completely remove Quipucords and all its data, use the ``uninstall`` command. This command stops all running services, removes systemd unit files, removes secrets and configuration files, and deletes all data directories.

``quipucordsctl uninstall``

``--keep-data-dirs``
    Preserve data directories and secrets while still removing services, unit files, and configuration. Use this to retain your data when reinstalling.

Diagnostics
-----------

Checking System Health
~~~~~~~~~~~~~~~~~~~~~~

To verify the installation status and health of Quipucords services, use the ``check`` command. This command checks for the presence and correct permissions of data directories, certificate files, configuration files, and systemd unit files required by Quipucords.

``quipucordsctl check``

Exporting Logs
~~~~~~~~~~~~~~

To export Quipucords logs for troubleshooting, use the ``export_logs`` command. This command creates a compressed archive containing log files from all running containers and systemd services.

``quipucordsctl export_logs``

The command outputs the path to the generated log archive file.

Configuration
-------------

**quipucordsctl** provides commands for managing Quipucords configuration and secrets. These commands allow you to reset credentials and rotate secrets without reinstalling the system.

Resetting Administrator Password
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To reset the administrator password for the Quipucords web interface and CLI, use the ``reset_admin_password`` command. This command prompts for a new password and updates the stored credentials. Set the ``QUIPUCORDS_SERVER_PASSWORD`` environment variable to provide a value non-interactively.

``quipucordsctl reset_admin_password``

Resetting Administrator Username
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To reset the administrator username for the Quipucords web interface and CLI, use the ``reset_admin_username`` command. This command prompts for a new username and updates the stored credentials. Set the ``QUIPUCORDS_SERVER_USERNAME`` environment variable to provide a value non-interactively.

``quipucordsctl reset_admin_username``

Resetting Database Password
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To reset the database password used by Quipucords, use the ``reset_database_password`` command. By default, this command generates a cryptographically strong random password. Set the ``QUIPUCORDS_DBMS_PASSWORD`` environment variable to use a specific value without prompting. Resetting this password on a running system may break the installation or cause data loss.

``quipucordsctl reset_database_password``

``-p``, ``--prompt``
    Prompt for a custom password instead of generating a random value.

Resetting Redis Password
~~~~~~~~~~~~~~~~~~~~~~~~~

To reset the Redis password used by Quipucords for caching and session management, use the ``reset_redis_password`` command. By default, this command generates a cryptographically strong random password. Set the ``QUIPUCORDS_REDIS_PASSWORD`` environment variable to use a specific value without prompting. Resetting this password on a running system may cause disruption.

``quipucordsctl reset_redis_password``

``-p``, ``--prompt``
    Prompt for a custom password instead of generating a random value.

Resetting Encryption Secret
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To reset the encryption secret key used to protect sensitive data stored by Quipucords, use the ``reset_encryption_secret`` command. By default, this command generates a cryptographically strong random key. Set the ``QUIPUCORDS_ENCRYPTION_SECRET_KEY`` environment variable to use a specific value without prompting. Resetting this secret on a running system may break the installation or cause data loss.

``quipucordsctl reset_encryption_secret``

``-p``, ``--prompt``
    Prompt for a custom secret key instead of generating a random value.

Resetting Session Secret
~~~~~~~~~~~~~~~~~~~~~~~~~

To reset the session secret key used for web session management in Quipucords, use the ``reset_session_secret`` command. By default, this command generates a cryptographically strong random key. Set the ``QUIPUCORDS_SESSION_SECRET_KEY`` environment variable to use a specific value without prompting. Resetting this secret on a running system may cause active sessions to become invalid.

``quipucordsctl reset_session_secret``

``-p``, ``--prompt``
    Prompt for a custom secret key instead of generating a random value.

Options for All Commands
-------------------------

The following options are available for every quipucordsctl command.

``--help``
    Display help information for the command.

``-v``, ``--verbose``
    Increase verbose output. Can be specified multiple times for more detailed logging (e.g., ``-vv`` or ``-vvv``).

``-q``, ``--quiet``
    Quiet output. Suppresses all non-error messages (overrides ``-v``/``--verbose``).

``-y``, ``--yes``
    Automatically answer yes to all confirmation prompts.

``-C`` *{auto|always|never}*, ``--color`` *{auto|always|never}*
    Control color output. Default is ``auto``, which enables color when writing to a terminal.

``-c``, ``--override-conf-dir`` *DIRECTORY*
    Load override values from this custom configuration directory. Use this to define override values for built-in container runtime configuration defaults that are not exposed directly through quipucordsctl commands.

Examples
--------

* Installing Quipucords::

    $ quipucordsctl install
    $ systemctl --user restart quipucords-app

* Verifying services are running::

    $ systemctl --user status quipucords-app

* Installing with detailed progress information::

    $ quipucordsctl -vv install

* Installing with maximum verbosity::

    $ quipucordsctl -vvv install

* Checking installation status::

    $ quipucordsctl check

* Checking with verbose output::

    $ quipucordsctl -v check

* Resetting administrator password::

    $ quipucordsctl reset_admin_password

* Resetting administrator username::

    $ quipucordsctl reset_admin_username

* Resetting database password::

    $ quipucordsctl reset_database_password

* Resetting Redis password::

    $ quipucordsctl reset_redis_password

* Resetting encryption secret::

    $ quipucordsctl reset_encryption_secret

* Resetting session secret::

    $ quipucordsctl reset_session_secret

* Exporting logs for troubleshooting::

    $ quipucordsctl export_logs

* Exporting logs with verbose output::

    $ quipucordsctl -v export_logs

* Viewing service logs::

    $ journalctl --user -u quipucords-app

* Uninstalling Quipucords::

    $ quipucordsctl uninstall

* Uninstalling Quipucords while preserving data::

    $ quipucordsctl uninstall --keep-data-dirs

* Installing with custom config overrides::

    $ quipucordsctl --override-conf-dir ~/overrides install

* Installing without confirmation prompts::

    $ quipucordsctl --yes install

* Installing silently::

    $ quipucordsctl -q install

* Checking status silently (errors only)::

    $ quipucordsctl -q check

Files
-----

``~/.config/quipucords/env/``
    Environment files for Quipucords container services. Contains configuration values passed to each container at startup.

``~/.config/containers/systemd/quipucords-*``
    Podman Quadlet unit files (``.container`` and ``.network``) that define the Quipucords container services.

``~/.local/share/quipucords/``
    Quipucords application data directory. Contains the database, certificates, logs, and SSH keys.

``~/.local/share/containers/storage/``
    Podman container storage location. Quipucords container images are stored here.

Environment
-----------

``NO_COLOR``
    If set, disables color output regardless of ``--color`` setting.

Exit Status
-----------

``0``
    Success. The command completed without errors.

``1``
    General error. The command failed due to invalid arguments, missing prerequisites, user interruption, or runtime errors.

``N`` (any positive integer, ``check`` command only)
    The ``check`` command exits with the number of issues found. For example, if three problems are detected, the exit code is 3.

See Also
--------

``podman(1)``, ``systemctl(1)``, ``journalctl(1)``

Notes
-----

quipucordsctl requires Podman and systemd user sessions to function. All commands except the initial RPM installation should be run as a regular non-root user.

To enable the Quipucords service to start automatically at login:

``systemctl --user enable quipucords-app``

quipucordsctl upstream source code: https://github.com/quipucords/quipucordsctl

Security Considerations
-----------------------

The configuration and environment files in ``~/.config/quipucords/`` are stored with user-only permissions (mode 0600 for files, 0700 for directories). Ensure your home directory has appropriate permissions to protect these files.

Database passwords, Redis passwords, encryption secrets, and session secrets are stored as Podman secrets, managed by Podman's secret storage. They are not stored as plain text files in the configuration directory.

When using the ``--override-conf-dir`` option, ensure the custom configuration directory has appropriate permissions before storing sensitive data there.
