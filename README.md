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
