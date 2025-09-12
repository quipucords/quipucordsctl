"""
SystemdUnitParser is originally from https://github.com/sgallagher/systemdunitparser.

quipucords devs modified this code to fix lint issues identified by ruff and to better
adhere the quipucords project style conventions.
"""

import configparser
import sys

__author__ = "sgallagh"

"""
Sections of this parser are adapted from:

http://stackoverflow.com/questions/13921323/handling-duplicate-keys-with-configparser
LICENSE: https://creativecommons.org/licenses/by-sa/3.0/ (CC-BY-SA 3.0)
Original Author: Praetorian on StackExchange
"""


class SystemdUnitParser(configparser.RawConfigParser):
    """ConfigParser allowing duplicate keys. Values are stored in a list."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, empty_lines_in_values=False, strict=False, **kwargs)
        self.optionxform = lambda option: option

        self._inline_comment_prefixes = kwargs.get("inline_comment_prefixes", None)
        self._comment_prefixes = kwargs.get("comment_prefixes", ("#", ";"))

    def _get_inline_prefixes(self):
        # Fix for newer cython
        if hasattr(self, "_inline_comment_prefixes"):
            return self._inline_comment_prefixes or ()
        elif hasattr(self, "_prefixes"):
            return self._prefixes.inline or ()
        return ()

    def _get_comment_prefixes(self):
        if hasattr(self, "_comment_prefixes"):
            return self._comment_prefixes or ()
        elif hasattr(self, "_prefixes"):
            return self._prefixes.full or ()
        return ()

    def _read(self, fp, fpname):  # noqa: C901, PLR0912, PLR0915
        """Parse a sectioned configuration file.

        Each section in a configuration file contains a header, indicated by
        a name in square brackets (`[]'), plus key/value options, indicated by
        `name' and `value' delimited with a specific substring (`=' or `:' by
        default).

        Values can span multiple lines, as long as they are indented deeper
        than the first line of the value. Depending on the parser's mode, blank
        lines may be treated as parts of multiline values or ignored.

        Configuration files may include comments, prefixed by specific
        characters (`#' and `;' by default). Comments may appear on their own
        in an otherwise empty line or may be entered in lines holding values or
        section names.
        """
        elements_added = set()
        cursect = None  # None, or a dictionary
        sectname = None
        optname = None
        lineno = 0
        indent_level = 0
        e = None  # None, or an exception
        for lineno, line in enumerate(fp, start=1):
            comment_start = sys.maxsize
            # strip inline comments
            inline_prefixes = {p: -1 for p in self._get_inline_prefixes()}
            while comment_start == sys.maxsize and inline_prefixes:
                next_prefixes = {}
                for prefix, index in inline_prefixes.items():
                    next_index = line.find(prefix, index + 1)
                    if next_index == -1:
                        continue
                    next_prefixes[prefix] = next_index
                    if next_index == 0 or (
                        next_index > 0 and line[next_index - 1].isspace()
                    ):
                        comment_start = min(comment_start, next_index)
                inline_prefixes = next_prefixes
            # strip full line comments
            for prefix in self._get_comment_prefixes():
                if line.strip().startswith(prefix):
                    comment_start = 0
                    break
            if comment_start == sys.maxsize:
                comment_start = None
            value = line[:comment_start].strip()
            if not value:
                if self._empty_lines_in_values:
                    # add empty line to the value, but only if there was no
                    # comment on the line
                    if (
                        comment_start is None
                        and cursect is not None
                        and optname
                        and cursect[optname] is not None
                    ):
                        cursect[optname].append("")  # newlines added at join
                else:
                    # empty line marks end of value
                    indent_level = sys.maxsize
                continue
            # continuation line?
            first_nonspace = self.NONSPACECRE.search(line)
            cur_indent_level = first_nonspace.start() if first_nonspace else 0
            if cursect is not None and optname and cur_indent_level > indent_level:
                cursect[optname].append(value)
            # a section header or option header?
            else:
                indent_level = cur_indent_level
                # is it a section header?
                mo = self.SECTCRE.match(value)
                if mo:
                    sectname = mo.group("header")
                    if sectname in self._sections:
                        cursect = self._sections[sectname]
                        elements_added.add(sectname)
                    elif sectname == self.default_section:
                        cursect = self._defaults
                    else:
                        cursect = self._dict()
                        self._sections[sectname] = cursect
                        self._proxies[sectname] = configparser.SectionProxy(
                            self, sectname
                        )
                        elements_added.add(sectname)
                    # So sections can't start with a continuation line
                    optname = None
                # no section header in the file?
                elif cursect is None:
                    raise configparser.MissingSectionHeaderError(fpname, lineno, line)
                # an option line?
                else:
                    mo = self._optcre.match(value)
                    if mo:
                        optname, vi, optval = mo.group("option", "vi", "value")
                        if not optname:
                            e = self._handle_error(e, fpname, lineno, line)
                        optname = self.optionxform(optname.rstrip())
                        elements_added.add((sectname, optname))
                        # This check is fine because the OPTCRE cannot
                        # match if it would set optval to None
                        if optval is not None:
                            optval = optval.strip()
                            # Check if this optname already exists
                            if (optname in cursect) and (cursect[optname] is not None):
                                # If it does, convert it to a tuple if it isn't already
                                if not isinstance(cursect[optname], tuple):
                                    cursect[optname] = tuple(cursect[optname])
                                cursect[optname] = cursect[optname] + tuple([optval])
                            else:
                                cursect[optname] = [optval]
                        else:
                            # valueless option handling
                            cursect[optname] = None
                    else:
                        # a non-fatal parsing error occurred. set up the
                        # exception but keep going. the exception will be
                        # raised at the end of the file and will contain a
                        # list of all bogus lines
                        e = self._handle_error(e, fpname, lineno, line)
        # if any parsing errors occurred, raise an exception
        if e:
            raise e
        self._join_multiline_values()

    def _validate_value_types(self, *, section="", option="", value=""):
        """Raise a TypeError for non-string values.

        The only legal non-string value if we allow valueless
        options is None, so we need to check if the value is a
        string if:
        - we do not allow valueless options, or
        - we allow valueless options but the value is not None

        For compatibility reasons this method is not used in classic set()
        for RawConfigParsers. It is invoked in every case for mapping protocol
        access and in ConfigParser.set().
        """  # noqa: E501
        if not isinstance(section, str):
            raise TypeError("section names must be strings")
        if not isinstance(option, str):
            raise TypeError("option keys must be strings")
        if not self._allow_no_value or value:
            if not isinstance(value, str) and not isinstance(value, tuple):
                raise TypeError("option values must be strings or a tuple of strings")

    # Write out duplicate keys with their values
    def _write_section(self, fp, section_name, section_items, delimiter):
        """Write a single section to the specified `fp`."""
        fp.write("[{}]\n".format(section_name))
        for key, _vals in section_items:
            vals = self._interpolation.before_write(self, section_name, key, _vals)
            if not isinstance(vals, tuple):
                vals = tuple([vals])
            for value in vals:
                if value is not None or not self._allow_no_value:
                    new_value = delimiter + str(value).replace("\n", "\n\t")
                else:
                    new_value = ""
                fp.write("{}{}\n".format(key, new_value))
        fp.write("\n")

    # Default to not creating spaces around the delimiter
    def write(self, fp, space_around_delimiters=False):
        """Write a systemd-format representation of the configuration state."""
        configparser.RawConfigParser.write(self, fp, space_around_delimiters)
