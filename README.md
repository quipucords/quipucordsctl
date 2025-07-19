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
DOMAIN=messages
SOURCE_CODE_DIR=quipucordsctl
LOCALES_DIR="${SOURCE_CODE_DIR}"/locale

# export strings to template
uv run pybabel extract -o "${LOCALES_DIR}"/"${DOMAIN}".pot "${SOURCE_CODE_DIR}"

# create each language-specific po file (first time only)
# replace "XX" with desired ISO 639-1 (two-letter) language code (e.g. "es")
# https://www.gnu.org/software/gettext/manual/html_node/Usual-Language-Codes.html
# https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes
uv run pybabel init -i "${LOCALES_DIR}"/"${DOMAIN}".pot -d "${LOCALES_DIR}" -D "${DOMAIN}" -l XX

# update each language-specific po file
# replace "XX" with desired ISO 639-1 (two-letter) language code (e.g. "es")
uv run pybabel update -i "${LOCALES_DIR}"/"${DOMAIN}".pot -d "${LOCALES_DIR}" -D "${DOMAIN}" -l XX

# compile binary mo file(s) after filling out all po file(s)
uv run pybabel compile -d "${LOCALES_DIR}" -D "${DOMAIN}"
```

## running

```sh
uv run python -m quipucordsctl --help

# override the locale using LC_MESSAGES, LC_ALL, LANGUAGE, or LANG 
LANG=pt uv run python -m quipucordsctl --help
```
