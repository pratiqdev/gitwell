HISTORY_STYLE = 1
MAX_HISTORY = 3
MAX_CHANGES = 3

"""
Interactive commit workflow: inspect repo metadata, staged diff stats, recent
history, then collect a multiline message and run ``git commit``.

Rendering helpers and subprocess wrappers live in ``gitwell.utils``.
"""


import argparse
import os
import requests
import sys
from colorama import Fore, Style, Back
from InquirerPy import inquirer, get_style
from rich.console import Console
from rich.markdown import Markdown
from rich.theme import Theme

from gitwell.config import (
    apply_config_cli,
    build_config_argument_parser,
    loadConfig,
    config as gw_config,
)

from gitwell.utils import (
    clearConsole,
    formatTemplateName,
    git_index_has_staged_vs_head,
    msgBright,
    msgDim,
    msgErr,
    msgWarn,
    printBreak,
    runCommand,
    splitAndFormat,
    truncateText,
    useCache,
)



# Define a custom theme
custom_theme = Theme({
    "heading": "bold magenta",
    "code": "on black",
    "link": "underline cyan",
    # "bullet": "grey",
    # "enumerate.number": "grey",

    "markdown.bullet": "#ff0000",
    "markdown.bullet_lead": "#00ff00",
    "markdown.enumerate.number": "#0000ff",
    "markdown.enumerate_lead": "#222222",

    "bullet": "#ff0000",
    "bullet_lead": "#00ff00",
    "enumerate.number": "#0000ff",
    "enumerate_lead": "#222222",
})

# Create a console object with the custom theme
console = Console(theme=custom_theme)

# console = Console()

# Function to clear console
os.system('cls' if os.name == 'nt' else 'clear')



common_style = get_style({
    "questionmark": "#05a bold",
    "answermark": "bold",
    "answer": "#61afef",
    "input": "#98c379",
    "question": "#05a bold",
    "answered_question": "bold",
    "instruction": "#225",
    "long_instruction": "#abb2bf",
    "pointer": "",
    "checkbox": "#98c379",
    "separator": "",
    "skipped": "#5c6370",
    "validator": "",
    "marker": "#e5c07b",
    "fuzzy_prompt": "#05a",
    "fuzzy_info": "#abb2bf",
    "fuzzy_border": "#4b5263",
    "fuzzy_match": "#c678dd",
    "spinner_pattern": "#e5c07b",
    "spinner_text": "#f00",
}, style_override=False)
    
gitignore_choices = ['AL', 'Actionscript', 'Ada', 'Agda', 'Android', 'AppEngine', 'AppceleratorTitanium', 'ArchLinuxPackages', 'Autotools', 'C', 'C++', 'CFWheels', 'CMake', 'CUDA', 'CakePHP', 'ChefCookbook', 'Clojure', 'CodeIgniter', 'CommonLisp', 'Composer', 'Concrete5', 'Coq', 'CraftCMS', 'D', 'DM', 'Dart', 'Delphi', 'Drupal', 'EPiServer', 'Eagle', 'Elisp', 'Elixir', 'Elm', 'Erlang', 'ExpressionEngine', 'ExtJs', 'Fancy', 'Finale', 'FlaxEngine', 'ForceDotCom', 'Fortran', 'FuelPHP', 'GWT', 'Gcov', 'GitBook', 'Go', 'Godot', 'Gradle', 'Grails', 'Haskell', 'IGORPro', 'Idris', 'JBoss', 'JENKINS_HOME', 'Java', 'Jekyll', 'Joomla', 'Julia', 'KiCad', 'Kohana', 'Kotlin', 'LabVIEW', 'Laravel', 'Leiningen', 'LemonStand', 'Lilypond', 'Lithium', 'Lua', 'Magento', 'Maven', 'Mercury', 'MetaProgrammingSystem', 'Nanoc', 'Nim', 'Node', 'OCaml', 'Objective-C', 'Opa', 'OpenCart', 'OracleForms', 'Packer', 'Perl', 'Phalcon', 'PlayFramework', 'Plone', 'Prestashop', 'Processing', 'PureScript', 'Python', 'Qooxdoo', 'Qt', 'R', 'ROS', 'Racket', 'Rails', 'Raku', 'RhodesRhomobile', 'Ruby', 'Rust', 'SCons', 'Sass', 'Scala', 'Scheme', 'Scrivener', 'Sdcc', 'SeamGen', 'SketchUp', 'Smalltalk', 'Stella', 'SugarCRM', 'Swift', 'Symfony', 'SymphonyCMS', 'TeX', 'Terraform', 'Textpattern', 'TurboGears2', 'TwinCAT3', 'Typo3', 'Unity', 'UnrealEngine', 'VVVV', 'VisualStudio', 'Waf', 'WordPress', 'Xojo', 'Yeoman', 'Yii', 'ZendFramework', 'Zephir']

inq_commit = inquirer.text(
    multiline=True,
    message="\nCommit:",  
    qmark="",
    amark="",
    instruction="(ESC + ENTER to confirm, supports markdown)",
    style=common_style,
    mandatory=False,
    raise_keyboard_interrupt=False
    # default=""
)

inq_init = inquirer.confirm(
    message="Initialize a repository?",
    default=False,
    confirm_letter="y",
    reject_letter="n",
    transformer=lambda result: "Y          Initializing..." if result else "N          Aborting.",
    style=common_style,
)

inq_gitignore = inquirer.fuzzy(
    message="Use .gitignore template?",
    choices= gitignore_choices,
    # multiselect=True,
    # validate=lambda result: len(result) > 1,
    # default='Node',
    # invalid_message="minimum 2 selections",
    transformer=lambda result: f"Y          Copying template '{result}'..." if result else "N          Skipping template.",
    max_height="30%",
    style=common_style
)


# inq_init.execute()
# inq_gitignore.execute()
# sys.exit()



# Function for checking and initialising git repo
def initGit() -> None:
    """
    Ensure the current directory is a git repository, optionally creating one.

    **Intention:** Make the tool usable from a non-repo folder by offering
    ``git init`` (with ``main`` as default branch) while preserving the
    historical behavior of exiting if the user declines.

    **Usage:** Call once near the start of ``main()`` before any git queries.

    **Arguments:** None.

    **Returns:** ``None``.

    **Raises:** Calls ``sys.exit()`` if ``.git`` is missing and the user rejects
    initialization, or if initialization path is not taken but repo is still
    invalid (same message path as the “Aborted” branch).
    """
    if not os.path.isdir(".git"):
        # print(msgWarn("!! dir is not a git repo."))
        willInit = inq_init.execute()
        # init_git_response = input(msgBright("Initialize a repository? ") + msgDim("(N) ") + Fore.CYAN)
        if willInit:
            print("\033[A\033[2K", end="")
            print(msgBright("? Initialize a repository? ") + Fore.CYAN + Style.BRIGHT + "Y" + msgDim( 19 * ' ' + "Initializing repo..."))
            # print(">> Initializing git repo...")
            runCommand('git config --global init.defaultBranch main')
            runCommand('git init')
            print("\033[A\033[2K", end="")
            print(msgBright("Initialize a repository? ") + Fore.CYAN + Style.BRIGHT + "Y" + msgDim(19 * ' ' + "Repo initialized."))
        else:
            print("\033[A\033[2K", end="")
            print(msgBright("Initialize a repository? ") + Fore.CYAN + Style.BRIGHT + "N" + msgDim(19 * ' ' + "Aborted."))
            print(Fore.RED + Style.BRIGHT + "\nThis command can only be run from within a git repository.")
            sys.exit()


# Function for checking and creating .gitignore
def createGitignore() -> None:
    """
    If no ``.gitignore`` exists, prompt for a GitHub template and download it.

    **Intention:** Bootstrap ignore rules for new projects using the official
    ``github/gitignore`` repository, with a fuzzy-finder over known template names.

    **Usage:** Run after ``initGit()`` so the working tree is a repo; uses the
    network via ``requests`` when a template is chosen.

    **Arguments:** None.

    **Returns:** ``None``.

    **Raises:** Calls ``sys.exit()`` if the HTTP response is not ``200`` (template
    name likely invalid).
    """
    if not os.path.isfile('.gitignore'):
        # print(msgWarn("\n!! No '.gitignore' file found."))
        # use_template = input(msgBright("Create from template?") + msgDim(" Y ") + Fore.CYAN)
        # if use_template.lower() != 'n':
        # print("\033[A\033[2K", end="")
        # print(msgBright("Copy .gitignore template? ") + Fore.CYAN + Style.BRIGHT + "Y")
        # template_name = input(msgBright("Use .gitignore template: ") + msgDim("(Node) ") +  Fore.CYAN)
        template_name = inq_gitignore.execute()
        if template_name.lower() == '':
            template_name = "Node"
        
        formatted_template_name = formatTemplateName(template_name)
        
        print("\033[A\033[2K", end="")
        print(msgBright("Use .gitignore template? ") + Fore.CYAN + Style.BRIGHT + formatted_template_name + msgDim("Copying template..."))

        response = requests.get(f'https://raw.githubusercontent.com/github/gitignore/master/{template_name}.gitignore')
        if response.status_code == 200:
            with open('.gitignore', 'w') as f:
                f.write(response.text)
            print("\033[A\033[2K", end="")
            print(msgBright("Use .gitignore template? ") + Fore.CYAN + Style.BRIGHT + formatted_template_name + msgDim("Template copied.\n"))

            # print(Fore.GREEN + f"Created '.gitignore' from template: '{template_name}'" + Style.RESET_ALL)
        else:
            print(Fore.RED + Style.BRIGHT + f"Error creating '.gitignore' from template: '{template_name}'. Verify the template exists or create the file manually.")
            sys.exit()
        # else:
        #     with open('.gitignore', 'w') as f:
        #         f.write("# TODO- Add .gitignore contents")
        #     print(Fore.GREEN + "Created default '.gitignore' file" + Style.RESET_ALL)




def sync_runtime_from_config() -> None:
    """Copy ``gw_config`` display keys into module-level style caps."""
    global HISTORY_STYLE, MAX_HISTORY, MAX_CHANGES
    HISTORY_STYLE = int(gw_config.get("history_type", 1))
    MAX_HISTORY = int(gw_config.get("history_length", 10))
    MAX_CHANGES = int(gw_config.get("diff_length", 3))


def _should_run_stage_command(run_stage: bool) -> bool:
    if not run_stage:
        return False
    cmd = (gw_config.get("stage_command") or "").strip()
    if not cmd or cmd.lower() in ("none", "null"):
        return False
    if bool(gw_config.get("auto_stage", True)):
        return True
    return not git_index_has_staged_vs_head()


@useCache(3000)
def fetchGitDetails(run_stage: bool = True) -> dict:
    """
    Collect identity, remote, branch, and staged per-file addition/deletion stats.

    When ``run_stage`` is True and policy allows, runs ``stage_command`` (default
    ``git add -A``) before reading ``git diff --cached``.
    """
    try:
        origin = runCommand('git remote get-url origin')
    except Exception:
        origin = None

    username = runCommand('git config user.name')
    email = runCommand('git config user.email')
    branch = runCommand('git symbolic-ref --short HEAD')

    if origin:
        fetch_url = runCommand('git remote get-url origin')
        push_url = runCommand('git remote get-url --push origin')
        fetch_user, fetch_repo = fetch_url.split('/')[-2:]
        fetch_repo = fetch_repo.replace('.git', '')
        push_user, push_repo = push_url.split('/')[-2:]
        push_repo = push_repo.replace('.git', '')
    else:
        fetch_url = push_url = 'local'
        fetch_user = push_user = 'local'
        fetch_repo = push_repo = runCommand('git rev-parse --show-toplevel').split('/')[-1]

    if _should_run_stage_command(run_stage):
        runCommand((gw_config.get("stage_command") or "").strip())

    name_status_lines = list(filter(None, runCommand('git diff --cached --name-status').split('\n')))
    numstat_lines = list(filter(None, runCommand('git diff --cached --numstat').split('\n')))

    combined_changes = {}

    for name_status_line, numstat_line in zip(name_status_lines, numstat_lines):
        status, filename = name_status_line.split(maxsplit=1)
        additions, deletions, _ = numstat_line.split(maxsplit=2)

        additions = '0' if additions == '-' else additions
        deletions = '0' if deletions == '-' else deletions

        if filename in combined_changes:
            combined_changes[filename]['additions'] += int(additions)
            combined_changes[filename]['deletions'] += int(deletions)
        else:
            combined_changes[filename] = {
                'status': status,
                'additions': int(additions),
                'deletions': int(deletions)
            }

    return {
        "username": username,
        "email": email,
        "branch": branch,
        "fetch_user": fetch_user,
        "fetch_url": fetch_url,
        "fetch_repo": fetch_repo,
        "push_user": push_user,
        "push_url": push_url,
        "push_repo": push_repo,
        "changed_files": combined_changes,
    }



def printHeading(run_stage: bool = True) -> None:
    """
    Print the user line (name + email) and fetch/push remote summary.

    **Returns:** ``None`` (prints to stdout). Skips output when ``heading_type`` is 0.
    """
    if int(gw_config.get("heading_type", 1)) == 0:
        return
    g = fetchGitDetails(run_stage=run_stage)

    print(Fore.BLUE + Style.BRIGHT + f"{g['username']}" + msgDim(f"  {g['email']}"))
    print(f" fetch << {Fore.BLUE}{g['fetch_user']}/{Fore.WHITE}{g['fetch_repo']}/{Fore.YELLOW}{g['branch']}" + Style.RESET_ALL)
    print(f" push  >> {Fore.BLUE}{g['push_user']}/{Fore.WHITE}{g['push_repo']}/{Fore.YELLOW}{g['branch']}" + Style.RESET_ALL)

 

def printHistory(last: bool = False, run_stage: bool = True) -> None:
    """
    Render recent commits or only the latest commit when finalizing a success view.

    **Intention:** Surface repository rhythm via ``git log`` with embeded ANSI
    color codes in the format string; richer layouts use ``rich`` Markdown when
    ``HISTORY_STYLE > 2``.

    **Usage:**
        - ``last=False`` during the pre-commit review (up to ``MAX_HISTORY`` entries,
          newest-first, subject to ``HISTORY_STYLE``).
        - ``last=True`` after a commit to echo the fresh HEAD message with a
          single-entry layout.

    **Arguments:**
        ``last`` (bool, optional): When ``True``, restrict to one commit and use a
        format that includes the body (``%B``). Default ``False``.

    **Returns:** ``None``. No output when ``HISTORY_STYLE == 0`` or when there
    are no commits in the non-``last`` branch.
    """
    if HISTORY_STYLE == 0:
        return
    
    g = fetchGitDetails(run_stage=run_stage)

    if last:
        commit_limit = 1 # Display only the most recent commit if `last` is True, otherwise display the last 10 commits
        
        history = runCommand(f'git log -n 1 --pretty=format:"---{Fore.YELLOW + Back.BLACK}%h {Fore.BLUE}%ad{Style.RESET_ALL + Fore.BLACK} %ar {Fore.GREEN}%an{Style.RESET_ALL} {Style.BRIGHT + Fore.WHITE}\n\n%B" --date=format:"%m/%d %H:%M"')
        commits = history.split('---')
        commits = [entry for entry in commits if entry]

        printBreak()
        print('')
        for commit in commits[:commit_limit]:
            commit = commit.replace(g['username'], '')
            # console.print(Markdown(commit))
            print(commit)
    
    else:
        commit_limit = MAX_HISTORY # Display only the most recent commit if `last` is True, otherwise display the last 10 commits
        
        history = "---"
        if HISTORY_STYLE == 1:
            history = runCommand(
                f'git log -n {commit_limit} --pretty=format:"---{Fore.YELLOW + Back.BLACK}%h {Fore.BLUE}%ad{Style.RESET_ALL + Fore.BLACK} %ar {Fore.GREEN}%an{Style.RESET_ALL} %s" --date=format:"%m/%d %H:%M"'
            )
        elif HISTORY_STYLE == 2:
            history = runCommand(
                f'git log -n {commit_limit} --pretty=format:"---{Fore.YELLOW + Back.BLACK}%h {Fore.BLUE}%ad{Style.RESET_ALL + Fore.BLACK} %ar {Fore.GREEN}%an{Style.RESET_ALL} \n%s" --date=format:"%m/%d %H:%M"'
            )
        elif HISTORY_STYLE == 3:
            history = runCommand(
                f'git log -n {commit_limit} --pretty=format:"---{Fore.YELLOW + Back.BLACK}%h {Fore.BLUE}%ad{Style.RESET_ALL + Fore.BLACK} %ar {Fore.GREEN}%an{Style.RESET_ALL} ===%B" --date=format:"%m/%d %H:%M"'
            )

        commits = history.split('---')
        commits = [entry for entry in commits if entry]

        if len(commits) == 0:
            return

        printBreak()
        print(Fore.BLUE + Style.BRIGHT + "\nHistory:" + msgDim(f" ({len(commits)} commits)"))

        for commit in commits[:commit_limit]:
            commit = commit.replace(g['username'], '')

            if HISTORY_STYLE == 1:
                commit = commit.replace("\n", "")
                commit = formatTemplateName(commit, 113)


            if HISTORY_STYLE > 2:
                commit = commit.replace("===", " " * 100)
                # print(msgDim('-' * 40))
                res = truncateText(commit)
                if not "text" in res:
                    return
                
                # print(res["text"])
                console.print(Markdown("\n" + res["text"]))
                print(msgDim(res['remaining']), end="")
            else:
                print(commit)


oldG = {}


def printChanged(useOld: bool = False) -> None:
    """
    List staged files with status/addition/deletion counts and optional rename layout.

    **Intention:** Summarize what will be included in the commit, cap rows at
    ``MAX_CHANGES``, and reuse the prior ``fetchGitDetails`` snapshot when
    ``useOld`` is ``True`` (post-commit refresh without re-running ``git add``-heavy
    paths that would clear the just-committed index view—see module ``oldG`` cache).

    **Usage:** Pair ``useOld=False`` before composing the message and ``True`` after
    a successful commit when the UI redraws a celebratory summary.

    **Arguments:**
        ``useOld`` (bool, optional): Read from the module-level ``oldG`` copy if
        ``True``; otherwise refresh via ``fetchGitDetails()``. Default ``False``.

    **Returns:** ``None``.

    **Raises:** ``sys.exit()`` when there are zero changed files in the snapshot.
    """
    global oldG  # Add this line to indicate you want to use the global variable
    g = oldG if useOld else fetchGitDetails()
    oldG = g.copy()
    files = g['changed_files']
    printBreak()

    if not files:
        print(msgErr("\nNo changed files found... Exiting.\n"))
        sys.exit(1)

    changed_count = 0
    added_count = 0
    deleted_count = 0

    for filename, changes in list(files.items()):
        if changes['status'] == 'M':
            changed_count += 1
        elif changes['status'] == 'A':
            added_count += 1
        elif changes['status'] == 'D':
            deleted_count += 1
        elif 'R' in changes['status']:
            changed_count += 1
    added = ""
    deleted = ""
    if added_count > 0:
        added = f", {added_count} added"
    if deleted_count > 0:
        added = f", {deleted_count} deleted"
    
    print(Fore.BLUE + Style.BRIGHT + "\nChanges:" + msgDim(f" ({changed_count} changed{added}{deleted})"))

    for filename, changes in list(files.items())[:MAX_CHANGES]: 
        # print(filename, changes)
        # added, removed, path = file.split('\t')
        shortStat = formatTemplateName(f'{changes["status"]}', 4)
        shortAdd = formatTemplateName(f'{changes["additions"]}', 4)
        shortDel = formatTemplateName(f'{changes["deletions"]}', 4)
        diff = f"{Fore.BLACK + shortStat} {Fore.GREEN}+{shortAdd} {Fore.RED}-{shortDel}{Style.RESET_ALL}"
        # shortDiff = formatTemplateName(diff, 14)
        # name = formatTemplateName(filename, 30)
        splitFiles = splitAndFormat(filename)
        print(f"{msgWarn('-')} {diff} {Style.RESET_ALL + splitFiles}")

    if len(files) > MAX_CHANGES:
        print(msgDim(f" ...{len(files) - MAX_CHANGES} more files"))


# def load_config():
#     import json

#     data = {"my_var": 123}  # initial data

#     # Save data to a file
#     with open("data.json", "w") as f:
#         json.dump(data, f)

#     # Later, load data from the file
#     with open("data.json", "r") as f:
#         data = json.load(f)

#     if len(sys.argv) > 1:
#         print(f"Received the following arguments: {sys.argv[1:]}")


GITWELL_MANPAGE = """\
NAME
    gitwell - interactive git commit helper

SYNOPSIS
    gitwell [--help]
    gitwell help
    gitwell config [ -g | --global ] [OPTION]...
    gitwell info | gitwell i
    gitwell history | gitwell h

DESCRIPTION
    With no subcommand, gitwell runs the full-screen flow: optional repository
    initialization and .gitignore template, repository summary panels, staged
    file stats, a multiline commit prompt, then git commit -F using a temp file.

COMMANDS
    help        Full manual (this text).
    config      View merged configuration or write .gitwell / .gitwell_globals.
                Value flags accept both equals and space forms, for example:
                  gitwell config --heading=2
                  gitwell config -h 2
                  gitwell config --auto-stage true
                  gitwell config -a=true
                Booleans must be the literal words true or false (case-insensitive).
                Inverse names such as --no-* are not used. On this subcommand,
                -h means --heading; use --help for help.
    info, i     Print repository heading only. Does not run stage_command.
                Requires an existing .git directory.
    history, h  Print recent commit history using history_type and history_length
                from config. Does not run stage_command.

STAGING (default flow only)
    stage_command   Shell snippet executed before reading the index (default:
                    git add -A). Empty or none disables.
    auto_stage      When true, always runs stage_command when it is non-empty,
                    even if the index already has staged changes (full staging).
                    When false, skips stage_command when the index already has
                    staged content versus HEAD, so you can git add manually first.

FILES
    .gitwell             Per-repository overrides
    .gitwell_globals     User-wide defaults

EXAMPLES
    gitwell
    gitwell config --history-length 5
    gitwell config -g --auto-stage false
    gitwell config -s "git add -A"
    gitwell i
    gitwell h
"""


def _run_root_help_short() -> None:
    print(
        "usage: gitwell [--help] [COMMAND]\n\n"
        "Commands: help, config, info|i, history|h\n"
        "With no COMMAND: interactive commit flow.\n\n"
        "Run `gitwell help` for the full manual."
    )


def _require_git_repo() -> None:
    if not os.path.isdir(".git"):
        print(
            msgErr(
                "Not a git repository (.git missing). "
                "Use `gitwell` (no subcommand) to initialize, or run from a repo root.\n"
            )
        )
        sys.exit(1)


def _run_help_manpage() -> None:
    print(GITWELL_MANPAGE)


def _run_config_argv(config_argv: list[str]) -> None:
    parser = build_config_argument_parser()
    ns = parser.parse_args(config_argv)
    clearConsole()
    apply_config_cli(ns)


def _run_info() -> None:
    _require_git_repo()
    loadConfig(quiet=True)
    sync_runtime_from_config()
    if int(gw_config.get("heading_type", 1)) != 0:
        printHeading(run_stage=False)


def _run_history() -> None:
    _require_git_repo()
    loadConfig(quiet=True)
    sync_runtime_from_config()
    printHistory(last=False, run_stage=False)


def _run_default_commit_flow() -> None:
    try:
        loadConfig(quiet=True)
        sync_runtime_from_config()
        clearConsole()
        initGit()
        createGitignore()

        printHeading()
        printHistory()
        printChanged()

        printBreak()
        message = inq_commit.execute()

        if not message:
            print("\033[A\033[2K", end="")
            print(msgErr("No message. Cancelling commit and exiting.\n"))
            sys.exit(1)

        try:
            temp_file = "temp_commit_message_file.txt"
            with open(temp_file, "w", encoding="utf-8") as file:
                file.write(message)

            runCommand(f"git commit -F {temp_file}")
            if os.path.exists(temp_file):
                os.remove(temp_file)

            clearConsole()
            printHeading(run_stage=False)
            printChanged(True)
            printHistory(last=True, run_stage=False)
            print("")
        except Exception as e:
            print(msgErr("Error creating commit:" + str(e)))

    except Exception as e:
        print(msgErr("Error:" + str(e)))


def main() -> None:
    """Entry point for ``gitwell`` and ``python -m gitwell``."""
    argv = sys.argv[1:]
    if not argv:
        _run_default_commit_flow()
        return

    cmd = argv[0]
    if cmd in ("--help", "-h"):
        _run_root_help_short()
        return
    if cmd == "help":
        _run_help_manpage()
        return
    if cmd == "config":
        _run_config_argv(argv[1:])
        return
    if cmd in ("info", "i"):
        _run_info()
        return
    if cmd in ("history", "h"):
        _run_history()
        return

    _run_default_commit_flow()


if __name__ == "__main__":
    main()

# TODO: inherit console width from terminal more accurately
# TODO: shorten history dates - '2 years, 9 months ago' -> '2y 9mo ago'
# '2 minutes ago' -> '2m ago'