#!/usr/bin/env python3
"""Release-specific, compound-aware command syntax oracle.

The oracle checks structure, not shell execution.  Its tokenizer retains whether
operator text was quoted/escaped, splits only real shell control operators, and
returns every simple invocation.  Each invocation is checked against the grammar
for the selected RHEL release.  No option table is unioned across releases.
"""
import json
import os

VERSIONS = ("7", "8", "9", "10")
CONTROL_OPS = ("&&", "||", ";", "|")
REDIRECT_OPS = ("2>&1", "2>>", "2>", ">>", ">", "<")
ALL_OPS = tuple(sorted(CONTROL_OPS + REDIRECT_OPS, key=len, reverse=True))


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _validate_form(where, form):
    if not isinstance(form, dict):
        raise ValueError("%s is not an object" % where)
    unknown = set(form) - {"options", "operands", "children"}
    if unknown:
        raise ValueError("%s has unknown keys: %s" % (where, ", ".join(sorted(unknown))))
    for name, takes in (form.get("options") or {}).items():
        if not isinstance(name, str) or not name.startswith("-") or type(takes) is not bool:
            raise ValueError("%s has invalid option %r" % (where, name))
    operands = form.get("operands") or {}
    minimum, maximum = operands.get("min", 0), operands.get("max")
    if set(operands) - {"min", "max"} or type(minimum) is not int or minimum < 0:
        raise ValueError("%s has an invalid operands rule" % where)
    if maximum is not None and (type(maximum) is not int or maximum < minimum):
        raise ValueError("%s has an invalid operand maximum" % where)
    children = form.get("children")
    if children is not None:
        if not isinstance(children, dict) or not children:
            raise ValueError("%s children must be a non-empty object" % where)
        for name, child in children.items():
            if not isinstance(name, str) or not name:
                raise ValueError("%s has invalid child name" % where)
            _validate_form("%s child %s" % (where, name), child)


def load_grammars(repo):
    """Return {release: {binary: grammar}} without cross-release merging."""
    policy = _load(os.path.join(repo, "content", "command-syntax.json"))
    out = {version: {} for version in VERSIONS}
    dictionaries = {}
    for version in VERSIONS:
        dictionaries[version] = (_load(os.path.join(
            repo, "content", "flags_rhel%s.json" % version)).get("clis") or {})
    for binary, releases in (policy.get("tools") or {}).items():
        if not isinstance(binary, str) or not binary or any(ch.isspace() for ch in binary):
            raise ValueError("invalid grammar binary %r" % binary)
        if not isinstance(releases, dict) or not releases or set(releases) - set(VERSIONS):
            raise ValueError("%s must declare only the RHEL releases where it is invoked" % binary)
        for version in sorted(releases):
            row = releases[version]
            if not isinstance(row, dict):
                raise ValueError("%s/RHEL %s is not an object" % (binary, version))
            unknown = set(row) - {"authority", "root", "commands", "captured_options"}
            if unknown:
                raise ValueError("%s/RHEL %s has unknown keys: %s" %
                                 (binary, version, ", ".join(sorted(unknown))))
            authority = row.get("authority") or {}
            if not authority.get("source") or not authority.get("anchor"):
                raise ValueError("%s/RHEL %s lacks concrete authority source/anchor" %
                                 (binary, version))
            source_path = authority.get("source")
            if source_path.startswith("content-src/") and not os.path.isfile(os.path.join(repo, source_path)):
                raise ValueError("%s/RHEL %s authority source does not exist: %s" %
                                 (binary, version, source_path))
            root = json.loads(json.dumps(row.get("root") or {"options": {}, "operands": {"min": 0, "max": None}}))
            _validate_form("%s/RHEL %s root" % (binary, version), root)
            commands = row.get("commands") or {}
            if not isinstance(commands, dict):
                raise ValueError("%s/RHEL %s commands is not an object" % (binary, version))
            # Explicit policy facts must be named by the authority anchor. A
            # generic tool citation is not evidence for a particular arity or
            # subcommand rule.
            explicit_names = list((root.get("options") or {}).keys())
            def collect_form_names(prefix, form):
                names = [prefix]
                names.extend((form.get("options") or {}).keys())
                for child, child_form in (form.get("children") or {}).items():
                    names.extend(collect_form_names(child, child_form))
                return names
            for command, form in commands.items():
                explicit_names.extend(collect_form_names(command, form))
            absent = [name for name in explicit_names if name not in authority["anchor"]]
            if absent:
                raise ValueError("%s/RHEL %s authority anchor omits policy fact(s): %s" %
                                 (binary, version, ", ".join(sorted(set(absent)))))
            option_sources = {name: dict(authority) for name in root.get("options") or {}}
            if row.get("captured_options", True):
                for flag in (dictionaries[version].get(binary) or {}).get("flags") or []:
                    for name in flag.get("names") or []:
                        if name.startswith("-") and name not in root.setdefault("options", {}):
                            root["options"][name] = bool(flag.get("takes_arg"))
                            option_sources[name] = {
                                "source": flag.get("raw_ref"),
                                "anchor": "definition term %s" % "/".join(flag.get("names") or []),
                            }
            for command, form in commands.items():
                if not isinstance(command, str) or not command:
                    raise ValueError("%s/RHEL %s has invalid command name" % (binary, version))
                _validate_form("%s/RHEL %s command %s" % (binary, version, command), form)
            out[version][binary] = {
                "authority": authority, "root": root, "commands": commands,
                "option_sources": option_sources,
            }
    return out


def tokenize_shell(command):
    """Tokenize the supported shell subset, preserving real operator identity."""
    tokens, buf, quoted = [], [], False
    quote = None
    i = 0
    def flush():
        nonlocal buf, quoted
        if buf:
            tokens.append({"kind": "word", "text": "".join(buf), "quoted": quoted})
            buf, quoted = [], False
    while i < len(command):
        ch = command[i]
        if quote:
            if quote == '"' and (ch == "`" or command.startswith("$(", i)):
                return None, ["unmodeled command substitution is not accepted"]
            if ch == quote:
                quote = None
            elif ch == "\\" and quote == '"' and i + 1 < len(command):
                i += 1; buf.append(command[i]); quoted = True
            else:
                buf.append(ch); quoted = True
            i += 1; continue
        if ch in ("'", '"'):
            quote = ch; quoted = True; i += 1; continue
        if ch == "\\":
            if i + 1 >= len(command):
                return None, ["trailing shell escape"]
            i += 1; buf.append(command[i]); quoted = True; i += 1; continue
        if ch == "#" and not buf and (i == 0 or command[i - 1].isspace()):
            flush(); break
        if ch == "`" or command.startswith("$(", i):
            return None, ["unmodeled command substitution is not accepted"]
        if ch in "()" or (ch == "&" and not command.startswith("&&", i)):
            return None, ["unmodeled shell structure %r is not accepted" % ch]
        if ch in "\r\n":
            return None, ["unmodeled shell line break is not accepted"]
        if ch.isspace():
            flush(); i += 1; continue
        matched = next((op for op in ALL_OPS if command.startswith(op, i)), None)
        if matched:
            flush(); tokens.append({"kind": "op", "text": matched, "quoted": False})
            i += len(matched); continue
        buf.append(ch); i += 1
    if quote:
        return None, ["unbalanced shell quote"]
    flush()
    return tokens, []


def split_invocations(command):
    tokens, errors = tokenize_shell(command)
    if errors:
        return [], errors
    invocations, current = [], []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token["kind"] == "op" and token["text"] in REDIRECT_OPS:
            if token["text"] != "2>&1":
                if i + 1 >= len(tokens) or tokens[i + 1]["kind"] != "word":
                    errors.append("redirection %s has no target" % token["text"])
                    return [], errors
                i += 2
            else:
                i += 1
            continue
        if token["kind"] == "op" and token["text"] in CONTROL_OPS:
            if not current:
                errors.append("operator %s has no command on its left" % token["text"])
                return [], errors
            invocations.append(current); current = []; i += 1; continue
        current.append(token); i += 1
    if current:
        invocations.append(current)
    elif tokens and tokens[-1]["kind"] == "op" and tokens[-1]["text"] in CONTROL_OPS:
        errors.append("operator %s has no command on its right" % tokens[-1]["text"])
    return invocations, errors


def _option(word, options):
    if word.startswith("--"):
        name, mark, value = word.partition("=")
        if name not in options:
            return None, None, "unknown option %s" % word
        if mark and not options[name]:
            return None, None, "argument supplied to argument-free option %s" % name
        return name, value if mark else None, None
    if word in options:
        return word, None, None
    for name in sorted((x for x in options if x.startswith("-") and not x.startswith("--")),
                       key=len, reverse=True):
        if options[name] and word.startswith(name + "="):
            return None, None, "short option %s must not join its argument with '='" % name
        if options[name] and word.startswith(name) and len(word) > len(name):
            return name, word[len(name):], None
    if len(word) > 2 and word.startswith("-"):
        chars = word[1:]
        for index, char in enumerate(chars):
            name = "-" + char
            if name not in options:
                break
            if options[name]:
                return name, chars[index + 1:] or None, None
        else:
            return word, "", None
    return None, None, "unknown option %s" % word


def _parse_form(words, form, where):
    options = form.get("options") or {}
    children = form.get("children") or {}
    if children:
        i, prefix_errors = 0, []
        while i < len(words) and not words[i]["quoted"] and words[i]["text"].startswith("-"):
            name, inline, err = _option(words[i]["text"], options)
            if err:
                prefix_errors.append("%s: %s" % (where, err)); i += 1; continue
            if options.get(name, False) and inline is None:
                if i + 1 >= len(words):
                    prefix_errors.append("%s: option %s requires an argument" % (where, name))
                else:
                    i += 1
            i += 1
        if i == len(words):
            rule = form.get("operands") or {}
            if rule.get("min", 0) > 0:
                prefix_errors.append("%s: missing nested command" % where)
            return prefix_errors
        child = words[i]["text"]
        if child not in children:
            prefix_errors.append("%s: first operand is not an allowed nested command (%s)" %
                                 (where, ", ".join(sorted(children))))
            return prefix_errors
        prefix_errors.extend(_parse_form(words[i + 1:], children[child], where + " " + child))
        return prefix_errors
    operands, errors, stop = [], [], False
    i = 0
    while i < len(words):
        word = words[i]["text"]
        if not stop and not words[i]["quoted"] and word == "--":
            stop = True; i += 1; continue
        if not stop and not words[i]["quoted"] and word.startswith("-") and word != "-":
            name, inline, err = _option(word, options)
            if err:
                errors.append("%s: %s" % (where, err)); i += 1; continue
            if options.get(name, False) and inline is None:
                if i + 1 >= len(words) or (not words[i + 1]["quoted"] and words[i + 1]["text"].startswith("-")):
                    errors.append("%s: option %s requires an argument" % (where, name))
                else:
                    i += 1
            i += 1; continue
        operands.append(words[i]); i += 1
    rule = form.get("operands") or {}
    minimum, maximum = rule.get("min", 0), rule.get("max")
    if len(operands) < minimum:
        errors.append("%s: has %d operand(s); requires at least %d" % (where, len(operands), minimum))
    if maximum is not None and len(operands) > maximum:
        errors.append("%s: has %d operand(s); allows at most %d" % (where, len(operands), maximum))
    return errors


def invocation_errors(words, grammar, expected_binary=None):
    if not words:
        return ["empty invocation"]
    binary = words[0]["text"]
    if words[0]["quoted"]:
        return ["command binary may not be quoted"]
    if expected_binary and binary != expected_binary:
        return ["invokes %s; declared grammar is %s" % (binary, expected_binary)]
    rest, root, errors = words[1:], grammar.get("root") or {}, []
    commands = grammar.get("commands") or {}
    # Root options precede a subcommand.  The shipped command families that use
    # subcommands declare every accepted subcommand explicitly.
    if commands:
        i = 0
        root_opts = root.get("options") or {}
        while i < len(rest) and not rest[i]["quoted"] and rest[i]["text"].startswith("-"):
            name, inline, err = _option(rest[i]["text"], root_opts)
            if err:
                break
            if root_opts.get(name, False) and inline is None:
                if i + 1 >= len(rest):
                    return ["%s root: option %s requires an argument" % (binary, name)]
                i += 1
            i += 1
        if i >= len(rest) or rest[i]["text"] not in commands:
            got = rest[i]["text"] if i < len(rest) else "<missing>"
            return ["%s: %s is not an allowed subcommand (%s)" %
                    (binary, got, ", ".join(sorted(commands)))]
        command = rest[i]["text"]
        # Root options remain legal after the subcommand only when copied into
        # that subcommand's explicit option set.  This prevents global options
        # from silently becoming legal everywhere.
        errors.extend(_parse_form(rest[i + 1:], commands[command], binary + " " + command))
        return errors
    return _parse_form(rest, root, binary)


def syntax_errors(command, version, grammars, expected_binary=None):
    """Validate every simple invocation in command under one RHEL release."""
    invocations, errors = split_invocations(command)
    if errors:
        return errors
    if not invocations:
        return ["command contains no invocation"]
    for index, words in enumerate(invocations):
        binary = words[0]["text"] if words else ""
        grammar = (grammars.get(version) or {}).get(binary)
        if grammar is None:
            errors.append("invocation %d uses %s, which has no RHEL %s grammar" %
                          (index + 1, binary or "nothing", version))
            continue
        errors.extend(invocation_errors(words, grammar,
                                        expected_binary if index == 0 else None))
    return errors
