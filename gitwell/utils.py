"""
Shared helpers for gitwell: subprocess wrappers, terminal styling, simple
numeric/string layout, and a small time-based memoization decorator.

This module is intentionally free of CLI prompts and git-specific orchestration
so both ``gitwell.cli`` and ``gitwell.config`` can reuse the same building blocks
without circular imports.
"""

from __future__ import annotations

import functools
import os
import subprocess
import time
from typing import Any, Callable, Dict, List

from colorama import Fore, Style

# -----------------------------------------------------------------------------
# Terminal and subprocess
# -----------------------------------------------------------------------------


def clearConsole() -> None:
    """
    Clear the terminal screen using the OS-native command.

    **Intention:** Give the interactive CLI a clean canvas (Windows ``cls`` or
    POSIX ``clear``) without depending on a third-party TUI library.

    **Usage:** Call once at the start of a flow or after a major action (e.g.
    post-commit refresh). Side effect: mutates the user's visible scrollback in
    most terminals.

    **Arguments:** None.

    **Returns:** ``None``.
    """
    os.system("cls" if os.name == "nt" else "clear")


def runCommand(command: str) -> str:
    """
    Run a shell command and return its stdout as a single trimmed string.

    **Intention:** Centralize how gitwell invokes ``git`` and other shell
    utilities: always capture stdout, discard stderr (see implementation), and
    decode text for display or parsing.

    **Usage:** Pass a full command string as you would type in a shell, e.g.
    ``runCommand("git symbolic-ref --short HEAD")``. Empty output becomes
    ``""``.

    **Arguments:**
        ``command`` (str): Shell command line. Passed to ``subprocess.Popen``
        with ``shell=True`` (caller must trust the string; avoid untrusted input).

    **Returns:**
        str: Standard output, decoded as UTF-8 (with default error handler),
        stripped of leading/trailing whitespace.

    **Note:** stderr is sent to ``DEVNULL``; failures may produce empty strings
    rather than exception messages from the child process—callers that need
    robust error handling may need to extend this helper.
    """
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        shell=True,
    )
    output, _ = process.communicate()
    return output.decode().strip()


def git_index_has_staged_vs_head() -> bool:
    """
    Return True if ``git diff --cached`` vs HEAD is non-empty (staged content).
    Uses exit codes from ``git diff --cached --quiet`` (1 = have diff).
    """
    result = subprocess.run(
        "git diff --cached --quiet",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode == 1:
        return True
    if result.returncode == 0:
        return False
    return bool(runCommand("git diff --cached --name-only").strip())


# -----------------------------------------------------------------------------
# Memoization decorator
# -----------------------------------------------------------------------------


def useCache(cache_time_ms: int = 5000) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Build a decorator that memoizes a function's return value for a few seconds.

    **Intention:** Reduce repeated expensive shell/git calls when the UI
    refreshes several times in quick succession (e.g. printing heading, history,
    and changes), while still allowing data to become stale after a short TTL.

    **Usage:**
        @useCache(3000)
        def fetchGitDetails():
            ...

    **Arguments:**
        ``cache_time_ms`` (int, optional): Time-to-live for each cache entry,
        in **milliseconds**. After this duration (converted via monotonic clock),
        the wrapped function runs again for the same arguments. Default ``5000``.

    **Returns:**
        A decorator that replaces ``func`` with a wrapper sharing an in-memory
        cache keyed by ``str(args) + str(kwargs)``.

    **Caveats:** Not thread-safe; cache grows unbounded with distinct argument
    shapes; keying on stringified args is coarse (different objects with same
    repr could collide, or vice versa).
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        cache: Dict[str, tuple[Any, float]] = {}

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = str(args) + str(kwargs)
            cached_result, cached_time = cache.get(key, (None, None))

            if cached_time is None or time.monotonic() - cached_time > cache_time_ms / 1000:
                result = func(*args, **kwargs)
                cache[key] = (result, time.monotonic())
            else:
                result = cached_result

            return result

        return wrapper

    return decorator


# -----------------------------------------------------------------------------
# Colorama-backed message styling (return ANSI-styled strings; do not print)
# -----------------------------------------------------------------------------


def msgWarn(msg: str) -> str:
    """
    Format ``msg`` as a bright yellow warning line fragment.

    **Intention:** Consistent “attention” styling (e.g. bullets in the changed-files list)
    without scattering color codes in call sites.

    **Arguments:**
        ``msg`` (str): Plain text to wrap with Colorama reset/bright/yellow sequences.

    **Returns:** str: Message with leading reset and trailing reset.
    """
    return Style.RESET_ALL + Style.BRIGHT + Fore.YELLOW + msg + Style.RESET_ALL


def msgErr(msg: str) -> str:
    """
    Format ``msg`` as a bright red error line fragment.

    **Intention:** User-visible error feedback before exit or after a failed step.

    **Arguments:**
        ``msg`` (str): Plain text to style as an error.

    **Returns:** str: Message with reset/bright/red styling applied.
    """
    return Style.RESET_ALL + Style.BRIGHT + Fore.RED + msg + Style.RESET_ALL


def msgDim(msg: str) -> str:
    """
    Format ``msg`` as dim white secondary text (metadata, counts, hints).

    **Intention:** De-emphasize auxiliary information next to bright headings.

    **Arguments:**
        ``msg`` (str): Secondary text to dim.

    **Returns:** str: Dim white styled string with resets.
    """
    return Style.RESET_ALL + Style.DIM + Fore.WHITE + msg + Style.RESET_ALL


def msgBlue(msg: str) -> str:
    """
    Format ``msg`` as bright blue highlighted text.

    **Intention:** Draw attention to identifiers (usernames, remotes) in summaries.

    **Arguments:**
        ``msg`` (str): Text to highlight in blue.

    **Returns:** str: Bright blue styled string with resets.
    """
    return Style.RESET_ALL + Style.BRIGHT + Fore.BLUE + msg + Style.RESET_ALL


def msgBright(msg: str) -> str:
    """
    Format ``msg`` as bright white primary prompt or label text.

    **Intention:** Prompt echoes and labels that should read as “main” copy.

    **Arguments:**
        ``msg`` (str): Content to emphasize.

    **Returns:** str: Bright white styled string with resets.
    """
    return Style.RESET_ALL + Style.BRIGHT + Fore.WHITE + msg + Style.RESET_ALL


def msgSelect(msg: str) -> str:
    """
    Format ``msg`` as bright cyan “selection” or interactive hint text.

    **Intention:** Reserved for choices / keyboard affordances (historically used
    alongside prompts).

    **Arguments:**
        ``msg`` (str): Text to show in cyan.

    **Returns:** str: Bright cyan styled string with resets.
    """
    return Style.RESET_ALL + Style.BRIGHT + Fore.CYAN + msg + Style.RESET_ALL


# -----------------------------------------------------------------------------
# Numeric and string layout
# -----------------------------------------------------------------------------


def clamp(value: float, min_value: float, max_value: float) -> float:
    """
    Clamp ``value`` to the inclusive range ``[min_value, max_value]``.

    **Intention:** Keep numeric config values (lengths, type indices) within
    allowed bounds when parsing CLI ``key=value`` overrides.

    **Arguments:**
        ``value`` (float): Input number (often ``int`` coercible from user input).
        ``min_value`` (float): Lower bound (inclusive).
        ``max_value`` (float): Upper bound (inclusive).

    **Returns:**
        float: ``max(min_value, min(value, max_value))``.

    **Raises:** Nothing; if ``min_value > max_value``, behavior follows Python's
    ``min``/``max`` composition (may still return a value outside intuitive bounds).
    """
    return max(min_value, min(value, max_value))


def pad(text: str, length: int, char: str = " ") -> str:
    """
    Pad or truncate ``text`` to exactly ``length`` characters using ``char``.

    **Intention:** Align columns when printing configuration key/value dumps in
    ``gitwell-config`` without pulling in a full tabular formatter.

    **Arguments:**
        ``text`` (str): Source string.
        ``length`` (int): Target character width. If greater than ``len(text)``,
        padding is appended; if smaller, ``text`` is cut on the right.
        ``char`` (str, optional): Single padding character; must be length 1.
        Default space.

    **Returns:**
        str: Padded or truncated string of width ``length`` (when padding applies).

    **Raises:**
        ValueError: If ``char`` is not exactly one character long.
    """
    if len(char) != 1:
        raise ValueError("Padding character must be a single character.")

    if length > len(text):
        return text + char * (length - len(text))
    return text[:length]


def truncateText(text: str, max_lines: int = 6) -> Dict[str, Any]:
    """
    Limit multi-line ``text`` to the first ``max_lines`` lines for compact display.

    **Intention:** Show a preview of long commit bodies in history style 3+ while
    signaling how much was omitted.

    **Arguments:**
        ``text`` (str): Input, split on ``\\n``.
        ``max_lines`` (int, optional): Maximum number of lines to keep at the
        start. Default ``6``.

    **Returns:**
        dict with keys:
            - ``"text"`` (str): Full ``text`` if within limit, else the truncated
              prefix joined with newlines.
            - ``"lines"``: Either the original split list when not truncating,
              **or** the total line count (int) when truncating (legacy behavior
              preserved for callers that branch on structure).
            - ``"remaining"`` (str): Empty when not truncating; otherwise a short
              suffix like ``"\\n ... N more lines\\n"``.
    """
    lines: List[str] = text.split("\n")
    num_total_lines = len(lines)

    if num_total_lines <= max_lines:
        return {
            "text": text,
            "lines": lines,
            "remaining": "",
        }

    truncated_lines = lines[:max_lines]
    num_more_lines = num_total_lines - max_lines
    truncated_text = "\n".join(truncated_lines)

    return {
        "text": truncated_text,
        "lines": num_total_lines,
        "remaining": f"\n ... {num_more_lines} more lines\n",
    }


def formatTemplateName(template_name: str, max_length: int = 20) -> str:
    """
    Fit ``template_name`` into a fixed display width with ellipsis and padding.

    **Intention:** Keep fuzzy-selected ``.gitignore`` template names aligned in
    the prompt echo line without overflowing narrow terminals.

    **Arguments:**
        ``template_name`` (str): Raw template key (e.g. ``"Node"``).
        ``max_length`` (int, optional): Column width. Names longer than this
        are truncated to ``max_length - 3`` characters plus ``"..."``. Default ``20``.

    **Returns:**
        str: Left-justified string of width ``max_length``, space-padded on the right,
        or truncated with ``...`` when needed.
    """
    if len(template_name) > max_length:
        template_name = template_name[: max_length - 3] + "..."
    return template_name.ljust(max_length, " ")


def printBreak() -> None:
    """
    Print a horizontal rule (80 dashes) with a leading newline.

    **Intention:** Visually separate sections (history, changes, commit) in the
    terminal UI. Uses black foreground for the dash run per existing aesthetic.

    **Arguments:** None.

    **Returns:** ``None`` (prints to stdout, no trailing newline after the rule).
    """
    print("\n" + Fore.BLACK + "-" * 80, end="")


def splitAndFormat(path_line: str, tabs: int = 2) -> str:
    """
    Pretty-print a path line that may contain a tab between two path segments.

    **Intention:** Git rename lines sometimes pair “old” and “new” paths; this
    splits on tab (or passes through unchanged) and adds stylized separators for
    the **changes** panel.

    **Arguments:**
        ``path_line`` (str): Single line, optionally containing ``\\t`` between two tokens.
        ``tabs`` (int, optional): Number of tab characters to indent the second line.
        Default ``2``.

    **Returns:**
        str: If ``\\t`` in ``path_line``, a two-line colored layout with ``|`` and ``>``
        markers; otherwise returns ``path_line`` unchanged.

    **Note:** If ``\\t`` is present, ``split()`` is used without ``maxsplit``;
    path tokens must not introduce extra whitespace fields beyond the two-token case.
    """
    if "\t" in path_line:
        word1, word2 = path_line.split()
        tab_str = "\t" * tabs + "   "
        return (
            f"{Fore.BLACK}|{Style.RESET_ALL} {word1}\n"
            f"{tab_str}{Fore.BLACK}>{Style.RESET_ALL} {word2}"
        )
    return path_line
