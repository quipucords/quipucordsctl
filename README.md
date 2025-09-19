# Installing Quipucords using `quipucordsctl`

## What is this?

`quipucordsctl` is a management tool that you can use to install and configure Quipucords and all of its required components to run in Podman containers on your local system.

## Using the RPM

> [!IMPORTANT]
> Installing the `quipucordsctl` RPM itself requires `sudo` or elevated `root` privileges, but ***all other commands*** for installing and interacting with Quipucords through the `quipucordsctl` program should be executed as a *regular non-root* user. If you install and run Quipucords as `root`, expect no support from the maintainers.

To prepare `quipucordsctl`:

```sh
sudo dnf copr enable -y @quipucords/quipucordsctl
sudo dnf install -y quipucordsctl
```


To install, configure, and start Quipucords:

```sh
quipucordsctl install
podman login registry.redhat.io  # REQUIRED before starting quipucords-app
systemctl --user start quipucords-app
```

A few seconds later, you may access Quipucords on https://localhost:9443

If you want to access Quipucords from systems outside of localhost, you may need to add a rule to allow access through the firewall:

```sh
sudo firewall-cmd --permanent --add-port=9443/tcp  # optional if you want external access
sudo firewall-cmd --reload  # optional if you want external access
```

# quipucordsctl

## setup

```sh
git clone git@github.com:quipucords/quipucordsctl.git quipucordsctl
cd quipucordsctl
uv sync

uv run ruff check
uv run ruff format --check
uv run pytest
```

## l10n/i18n

```sh
# export strings to template
uv run bin/translations.py extract

# update each language-specific po file
uv run bin/translations.py update

# compile binary mo file(s) after filling out all po file(s)
uv run bin/translations.py compile
```

## running

```sh
uv run python -m quipucordsctl --help

# override the locale using LC_MESSAGES, LC_ALL, LANGUAGE, or LANG 
LANG=pt uv run python -m quipucordsctl --help
```
