"""Static analysis of a shell command line, for the guard hooks — stdlib only.

Nothing is executed. `commands(text)` returns every simple command the text
would run, as argv lists with quotes removed, including commands nested in:

  ;  &&  ||  |  &  newlines  ( … )  { …; }  $( … )  ` … `  <( … )
  bash|sh|zsh|dash|ksh -c '…'    eval …    cmd /c …    pwsh -c|-EncodedCommand …
  a heredoc or here-string fed to a shell (`bash <<EOF`, `sh <<< '…'`)
  echo|printf|cat output piped into a shell (`echo '…' | sh`)
  python|node|perl|ruby -c|-e code: its string literals
  wrappers: env, command, exec, builtin, nice, nohup, time, sudo, doas,
            timeout, stdbuf, xargs, watch, find -exec
  aliases defined in the same text (`alias gc='git commit -n'; gc`)
  variables assigned in the same text (`G=git; $G commit -n`)

What it cannot see (SECURITY.md lists the consequences): a script file run
by path, a variable set outside the text, an alias or function defined in a
shell profile, encoded payloads other than pwsh -EncodedCommand, and code
read from the network or from a file.
"""
from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

MAX_DEPTH = 6
SHELLS = {"bash", "sh", "zsh", "dash", "ksh", "ash", "mksh", "busybox"}
INTERPRETERS = {"python", "python3", "python2", "py", "node", "nodejs", "deno", "perl", "ruby", "php"}
KEYWORDS = {"if", "then", "else", "elif", "fi", "do", "done", "while", "until", "!", "{", "}",
            "function", "coproc"}
SKIP_SEGMENT = {"for", "select", "case", "esac", "in"}
SEPARATORS = {";", "&", "&&", "||", "|", "|&", "\n", "(", ")", ";;", ";&", ";;&"}
REDIRECT = re.compile(r"^(\d*|&)(>>?|<|<>|>&|<&|>\||&>>?)$")


@dataclass
class Word:
    value: str                       # quotes removed, escapes resolved
    raw: str                         # as written
    nested: List[str] = field(default_factory=list)  # $( … ), ` … `, <( … ) bodies


@dataclass
class Command:
    argv: List[str]                                  # effective argv, wrappers stripped
    env: Dict[str, str] = field(default_factory=dict)
    redirects: List[tuple] = field(default_factory=list)   # (operator, target)
    text: str = ""                                   # source words, joined
    expanded: bool = False                           # a variable or alias was substituted
    stdin_code: List[str] = field(default_factory=list)    # heredocs / here-strings / piped text

    @property
    def name(self) -> str:
        return basename(self.argv[0]) if self.argv else ""


def basename(word: str) -> str:
    name = re.split(r"[\\/]", word)[-1].lower()
    return name[:-4] if name.endswith(".exe") else name


# ------------------------------------------------------------------ lexer

def _ansi_c(body: str) -> str:
    def esc(m):
        s = m.group(1)
        if s[0] == "x":
            return chr(int(s[1:], 16))
        if s[0] in "01234567":
            return chr(int(s, 8))
        return {"n": "\n", "t": "\t", "r": "\r", "e": "\x1b", "a": "\a", "b": "\b",
                "f": "\f", "v": "\v"}.get(s, s)
    return re.sub(r"\\(x[0-9a-fA-F]{1,2}|[0-7]{1,3}|.)", esc, body)


def _matching(text: str, i: int, open_: str, close: str) -> int:
    """Index of the `close` matching an `open_` just before i, aware of quotes."""
    depth = 1
    while i < len(text):
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if c == "'":
            j = text.find("'", i + 1)
            i = len(text) if j < 0 else j + 1
            continue
        if c == '"':
            i += 1
            while i < len(text) and text[i] != '"':
                i += 2 if text[i] == "\\" else 1
            i += 1
            continue
        if text.startswith(open_, i):
            depth += 1
            i += len(open_)
            continue
        if c == close:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return len(text)


def _heredocs(text: str):
    """Text without heredoc bodies, and the bodies in order of their operators."""
    lines, out, bodies, pending = text.split("\n"), [], [], []
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        quoted = [m.span() for m in re.finditer(r"'[^']*'|\"(?:\\.|[^\"\\])*\"", line)]
        for m in re.finditer(r"(?<![<\d])<<(-?)\s*(['\"]?)([A-Za-z0-9_.-]+)\2", line):
            if not any(a <= m.start() < b for a, b in quoted):
                pending.append((m.group(1) == "-", m.group(3)))
        i += 1
        for dash, end in pending:
            body = []
            while i < len(lines):
                candidate = lines[i].lstrip("\t") if dash else lines[i]
                if candidate.strip() == end:
                    i += 1
                    break
                body.append(lines[i])
                i += 1
            bodies.append("\n".join(body))
        pending = []
    return "\n".join(out), bodies


def tokens(text: str):
    """Words and operators of one shell text (heredoc bodies already removed)."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c in " \t\r":
            i += 1
            continue
        if c == "\\" and i + 1 < n and text[i + 1] == "\n":
            i += 2
            continue
        if c == "#":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if c == "\n":
            out.append("\n")
            i += 1
            continue
        fd = re.match(r"\d+(>>|>&|<&|<>|>\||>|<)", text[i:])
        if fd:
            out.append(fd.group(0))
            i += len(fd.group(0))
            continue
        if text.startswith("<(", i) or text.startswith(">(", i):
            word, i = _word(text, i)
            out.append(word)
            continue
        for op in (";;&", "<<<", "&>>", ";;", ";&", "&&", "||", "|&", ">>", "<<", "<>", ">&", "<&", ">|", "&>"):
            if text.startswith(op, i):
                out.append(op)
                i += len(op)
                break
        else:
            if c in ";&|()<>":
                out.append(c)
                i += 1
                continue
            word, i = _word(text, i)
            out.append(word)
    return out


def _word(text: str, i: int):
    value, nested, start, n = [], [], i, len(text)
    while i < n:
        c = text[i]
        if c in " \t\r\n;&|()<>" and not (c in "<>" and text.startswith("(", i + 1)):
            break
        if c == "\\":
            if i + 1 < n and text[i + 1] != "\n":
                value.append(text[i + 1])
            i += 2
        elif c == "'":
            j = text.find("'", i + 1)
            j = n if j < 0 else j
            value.append(text[i + 1:j])
            i = j + 1
        elif c == "$" and text.startswith("$'", i):
            j = i + 2
            while j < n and text[j] != "'":
                j += 2 if text[j] == "\\" else 1
            value.append(_ansi_c(text[i + 2:j]))
            i = j + 1
        elif c == '"':
            i += 1
            while i < n and text[i] != '"':
                if text[i] == "\\" and i + 1 < n and text[i + 1] in '$`"\\\n':
                    if text[i + 1] != "\n":
                        value.append(text[i + 1])
                    i += 2
                elif text.startswith("$((", i):
                    j = _matching(text, i + 3, "((", ")")
                    value.append(text[i:j + 2])
                    i = j + 2
                elif text.startswith("$(", i):
                    j = _matching(text, i + 2, "(", ")")
                    nested.append(text[i + 2:j])
                    value.append(text[i:j + 1])
                    i = j + 1
                elif text[i] == "`":
                    j = text.find("`", i + 1)
                    j = n if j < 0 else j
                    nested.append(text[i + 1:j])
                    value.append(text[i:j + 1])
                    i = j + 1
                else:
                    value.append(text[i])
                    i += 1
            i += 1
        elif text.startswith("$((", i):
            j = _matching(text, i + 3, "((", ")")
            value.append(text[i:j + 2])
            i = j + 2
        elif text.startswith("$(", i) or (c in "<>" and text.startswith("(", i + 1)):
            j = _matching(text, i + 2, "(", ")")
            nested.append(text[i + 2:j])
            value.append(text[i:j + 1])
            i = j + 1
        elif c == "`":
            j = text.find("`", i + 1)
            j = n if j < 0 else j
            nested.append(text[i + 1:j])
            value.append(text[i:j + 1])
            i = j + 1
        else:
            value.append(c)
            i += 1
    return Word("".join(value), text[start:i], nested), i


# ------------------------------------------------------------------ parser

class _Scope:
    def __init__(self):
        self.vars: Dict[str, str] = {}
        self.aliases: Dict[str, str] = {}


VAR_REF = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))")


def _expand(word: str, scope: _Scope):
    hit = False

    def sub(m):
        nonlocal hit
        name = m.group(1) or m.group(2)
        if name in scope.vars:
            hit = True
            return scope.vars[name]
        return m.group(0)
    return VAR_REF.sub(sub, word), hit


def commands(text: str, depth: int = 0, scope: Optional[_Scope] = None) -> List[Command]:
    """Every simple command `text` would run, nested ones included (see module doc)."""
    if depth > MAX_DEPTH or not text:
        return []
    scope = scope or _Scope()
    body, heredocs = _heredocs(text.replace("\\\n", " "))
    found: List[Command] = []
    pipeline: List[Command] = []
    words: List = []
    heredoc_iter = iter(heredocs)

    def flush(op):
        nonlocal words
        cmd = _simple(words, scope, heredoc_iter, depth, found)
        words = []
        if cmd is not None:
            if pipeline and cmd.name in SHELLS and _reads_stdin(cmd):
                for prev in pipeline:
                    cmd.stdin_code.extend(_piped_text(prev))
                found.extend(_shell_code(cmd, depth, scope))
            pipeline.append(cmd)
        if op not in ("|", "|&"):
            pipeline.clear()

    for tok in tokens(body):
        if isinstance(tok, str) and tok in SEPARATORS:
            flush(tok)
        else:
            words.append(tok)
    flush(";")
    return found


def _reads_stdin(cmd: Command) -> bool:
    args = cmd.argv[1:]
    if cmd.name == "busybox":
        args = args[1:]
    return not any(a == "-c" or (a.startswith("-") and not a.startswith("--") and "c" in a[1:]) for a in args) \
        and not any(not a.startswith("-") for a in args)


def _piped_text(cmd: Command) -> List[str]:
    if cmd.name in ("echo", "printf"):
        args = [a for a in cmd.argv[1:] if not re.fullmatch(r"-[neE]+", a)]
        return [" ".join(args).replace("\\n", "\n")]
    if cmd.name == "cat":
        return list(cmd.stdin_code)
    return []


def _simple(words, scope, heredoc_iter, depth, found) -> Optional[Command]:
    if not words:
        return None
    env, argv, redirects, expanded, stdin_code = {}, [], [], False, []
    i = 0
    while i < len(words):
        w = words[i]
        if isinstance(w, str) and (REDIRECT.match(w) or w in ("<<", "<<<")):
            target = words[i + 1] if i + 1 < len(words) else None
            tval = target.value if isinstance(target, Word) else ""
            if w == "<<":
                stdin_code.append(next(heredoc_iter, ""))
            elif w == "<<<":
                stdin_code.append(tval)
            else:
                redirects.append((w, tval))
            if isinstance(target, Word):
                for inner in target.nested:
                    found.extend(commands(inner, depth + 1, scope))
            i += 2
            continue
        if isinstance(w, str):
            i += 1
            continue
        for inner in w.nested:
            found.extend(commands(inner, depth + 1, scope))
        value, hit = _expand(w.value, scope)
        expanded |= hit
        if not argv and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*\+?=.*", value, re.S) and "=" in w.raw:
            name, _, val = value.partition("=")
            env[name.rstrip("+")] = val
        elif not argv and value in KEYWORDS:
            pass
        elif not argv and value in SKIP_SEGMENT:
            return None
        elif not argv and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*\(\)", value):
            pass                                     # function definition header
        else:
            argv.append(value)
        i += 1
    if not argv:
        scope.vars.update(env)                       # NAME=value alone: a shell variable
        return None
    if argv[0] in ("export", "declare", "typeset", "local", "readonly"):
        for a in argv[1:]:
            if "=" in a and not a.startswith("-"):
                k, _, v = a.partition("=")
                scope.vars[k] = v
        return None
    if argv[0] == "alias":
        for a in argv[1:]:
            if "=" in a:
                k, _, v = a.partition("=")
                scope.aliases[k] = v
                found.extend(commands(v, depth + 1, scope))
        return None
    if argv[0] in scope.aliases and depth <= MAX_DEPTH:
        alias_text = scope.aliases[argv[0]] + " " + " ".join(_quote(a) for a in argv[1:])
        for cmd in commands(alias_text, depth + 1, scope):
            cmd.expanded = True
            found.append(cmd)
        return None
    cmd = Command(argv, env, redirects, " ".join(argv), expanded, stdin_code)
    chain = _unwrap(cmd, depth, scope, found)
    _emit(chain, depth, scope, found)
    return chain[-1]


def _emit(chain, depth, scope, found):
    for c in chain:
        found.append(c)
        found.extend(_shell_code(c, depth, scope))


def _quote(word: str) -> str:
    return "'" + word.replace("'", "'\\''") + "'"


# ------------------------------------------------------------------ wrappers

def _skip_opts(args, with_arg=(), stop_at_first=True):
    """Index of the first non-option argument."""
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            return i + 1
        if not a.startswith("-") or a == "-":
            return i
        if a in with_arg:
            i += 2
            continue
        i += 1
    return i


def _unwrap(cmd: Command, depth, scope, found):
    """The command, then whatever command it runs through a wrapper."""
    chain = [cmd]
    for _ in range(8):
        cur = chain[-1]
        name, args = cur.name, cur.argv[1:]
        nxt = None
        if name == "env":
            i = _skip_opts(args, ("-u", "--unset", "-C", "--chdir", "-S", "--split-string"))
            if "-S" in args or "--split-string" in args:
                k = args.index("-S") if "-S" in args else args.index("--split-string")
                if k + 1 < len(args):
                    found.extend(commands(args[k + 1], depth + 1, scope))
            env = dict(cur.env)
            while i < len(args) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", args[i], re.S):
                k, _, v = args[i].partition("=")
                env[k] = v
                i += 1
            nxt = Command(args[i:], env, cur.redirects, " ".join(args[i:]), cur.expanded, cur.stdin_code)
        elif name in ("command", "builtin"):
            if any(a in ("-v", "-V") for a in args[:2]):
                return chain                     # a lookup, not a run
            i = _skip_opts(args)
            nxt = Command(args[i:], cur.env, cur.redirects, "", cur.expanded, cur.stdin_code)
        elif name == "exec":
            i = _skip_opts(args, ("-a",))
            nxt = Command(args[i:], cur.env, cur.redirects, "", cur.expanded, cur.stdin_code)
        elif name in ("nohup", "time", "doas", "chronic", "unbuffer", "caffeinate"):
            i = _skip_opts(args, ("-u", "-C"))
            nxt = Command(args[i:], cur.env, cur.redirects, "", cur.expanded, cur.stdin_code)
        elif name == "nice":
            i = _skip_opts(args, ("-n", "--adjustment"))
            nxt = Command(args[i:], cur.env, cur.redirects, "", cur.expanded, cur.stdin_code)
        elif name == "sudo":
            i = _skip_opts(args, ("-u", "-g", "-C", "-D", "-h", "-p", "-r", "-t", "-U", "-T", "-R"))
            env = dict(cur.env)
            while i < len(args) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", args[i], re.S):
                k, _, v = args[i].partition("=")
                env[k] = v
                i += 1
            nxt = Command(args[i:], env, cur.redirects, "", cur.expanded, cur.stdin_code)
        elif name in ("timeout", "gtimeout"):
            i = _skip_opts(args, ("-s", "--signal", "-k", "--kill-after"))
            nxt = Command(args[i + 1:], cur.env, cur.redirects, "", cur.expanded, cur.stdin_code)
        elif name == "stdbuf":
            i = _skip_opts(args, ("-i", "-o", "-e"))
            nxt = Command(args[i:], cur.env, cur.redirects, "", cur.expanded, cur.stdin_code)
        elif name == "xargs":
            i = _skip_opts(args, ("-I", "-n", "-L", "-P", "-d", "-E", "-s", "-a", "--arg-file",
                                  "--delimiter", "--max-args", "--max-procs", "--replace"))
            nxt = Command(args[i:], cur.env, cur.redirects, "", cur.expanded, cur.stdin_code)
        elif name == "watch":
            i = _skip_opts(args, ("-n", "--interval", "-d"))
            found.extend(commands(" ".join(args[i:]), depth + 1, scope))
            return chain
        elif name == "find":
            for k, a in enumerate(args):
                if a in ("-exec", "-execdir", "-ok", "-okdir"):
                    end = next((j for j in range(k + 1, len(args)) if args[j] in (";", "+")), len(args))
                    sub = args[k + 1:end]
                    if sub:
                        inner = Command(sub, cur.env, [], " ".join(sub), cur.expanded)
                        _emit(_unwrap(inner, depth, scope, found), depth, scope, found)
            return chain
        if nxt is None or not nxt.argv:
            return chain
        nxt.text = " ".join(nxt.argv)
        chain.append(nxt)
    return chain


# ------------------------------------------------------------------ code run by a shell or interpreter

def _windows(code: str) -> str:
    """cmd and PowerShell code: a backslash separates a path, it escapes nothing."""
    return code.replace("\\", "/")


STRING_LITERAL = re.compile(r"'''(.*?)'''|\"\"\"(.*?)\"\"\"|'((?:\\.|[^'\\])*)'|\"((?:\\.|[^\"\\])*)\"", re.S)


def _literals(code: str) -> List[str]:
    out = []
    for m in STRING_LITERAL.finditer(code):
        s = next(g for g in m.groups() if g is not None)
        out.append(s.encode("utf-8").decode("unicode_escape", "ignore") if "\\" in s else s)
    return out


def _shell_code(cmd: Command, depth, scope) -> List[Command]:
    """Commands in code that `cmd` hands to a shell or an interpreter."""
    name, args = cmd.name, cmd.argv[1:]
    codes: List[str] = []
    if name == "busybox" and args and basename(args[0]) in SHELLS:
        name, args = basename(args[0]), args[1:]
    if name in SHELLS:
        for k, a in enumerate(args):
            if a == "-c" or (a.startswith("-") and not a.startswith("--") and "c" in a[1:]):
                rest = [x for x in args[k + 1:] if not x.startswith("-")]
                if rest:
                    codes.append(rest[0])
                break
        else:
            if _reads_stdin(cmd):
                codes.extend(cmd.stdin_code)
    elif name == "eval":
        codes.append(" ".join(args))
    elif name in ("cmd", "cmd.exe") and args:
        for k, a in enumerate(args):
            if a.lower() in ("/c", "/k", "/r"):
                codes.append(_windows(" ".join(args[k + 1:])))
                break
    elif name in ("pwsh", "powershell"):
        for k, a in enumerate(args):
            low = a.lower()
            if low in ("-c", "-command") and k + 1 < len(args):
                codes.append(_windows(" ".join(args[k + 1:])))
                break
            if low in ("-e", "-ec", "-encodedcommand") and k + 1 < len(args):
                try:
                    codes.append(_windows(base64.b64decode(args[k + 1]).decode("utf-16-le")))
                except (ValueError, UnicodeDecodeError):
                    pass
                break
    elif name in INTERPRETERS or re.fullmatch(r"python[0-9.]*", name):
        for k, a in enumerate(args):
            if a in ("-c", "-e", "--eval", "-E") and k + 1 < len(args):
                code = args[k + 1]
                lits = _literals(code)
                codes.extend(lits)
                for group in re.findall(r"\[([^\]]*)\]", code):
                    joined = " ".join(_literals(group))
                    if joined:
                        codes.append(joined)
                break
        codes.extend(cmd.stdin_code)
    out: List[Command] = []
    for code in codes:
        out.extend(commands(code, depth + 1, scope))
    return out
