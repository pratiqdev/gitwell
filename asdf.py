import os
import subprocess
import requests
import sys
from colorama import Fore, Style, Back
import time
import functools

MAX_HISTORY = 5
MAX_CHANGES = 3

def useCache(func=None, cache_time=5000):
    if func is None:  # Decorator was called with parentheses but no arguments.
        return lambda f: useCache(f, cache_time=cache_time)

    cache = {}

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        key = str(args) + str(kwargs)
        cached_result, cached_time = cache.get(key, (None, None))

        if cached_time is None or time.monotonic() - cached_time > cache_time / 1000:
            # Cache is empty or expired
            result = func(*args, **kwargs)
            cache[key] = (result, time.monotonic())
        else:
            # Cache hit
            result = cached_result

        return result

    return wrapper




def run_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, shell=True)
    output, _ = process.communicate()
    return output.decode().strip()


def msg_warn(msg):
    return Style.RESET_ALL + Style.BRIGHT + Fore.YELLOW + msg + Style.RESET_ALL

def msg_err(msg):
    return Style.RESET_ALL + Style.BRIGHT + Fore.RED + msg + Style.RESET_ALL

def msg_dim(msg):
    return Style.RESET_ALL + Style.DIM + Fore.WHITE +  msg + Style.RESET_ALL

def msg_blue(msg):
    return Style.RESET_ALL + Style.BRIGHT + Fore.BLUE + msg + Style.RESET_ALL

def msg_bright(msg):
    return Style.RESET_ALL + Style.BRIGHT + Fore.WHITE + msg + Style.RESET_ALL

def msg_select(msg):
    return Style.RESET_ALL + Style.BRIGHT + Fore.CYAN + msg + Style.RESET_ALL





# Function to clear console
def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')



# Function for checking and initialising git repo
def init_git():
    if not os.path.isdir(".git"):
        # print(msg_warn("!! dir is not a git repo."))
        init_git_response = input(msg_bright("Initialize a repository? ") + msg_dim("(N) ") + Fore.CYAN)
        if init_git_response.lower() == 'y':
            print("\033[A\033[2K", end="")
            print(msg_bright("Initialize a repository? ") + Fore.CYAN + Style.BRIGHT + "Y" + msg_dim( 19 * ' ' + "Initializing repo..."))
            # print(">> Initializing git repo...")
            run_command('git config --global init.defaultBranch main')
            run_command('git init')
            print("\033[A\033[2K", end="")
            print(msg_bright("Initialize a repository? ") + Fore.CYAN + Style.BRIGHT + "Y" + msg_dim(19 * ' ' + "Repo initialized."))
        else:
            print("\033[A\033[2K", end="")
            print(msg_bright("Initialize a repository? ") + Fore.CYAN + Style.BRIGHT + "N" + msg_dim(19 * ' ' + "Aborted."))
            print(Fore.RED + Style.BRIGHT + "\nThis command can only be run from within a git repository.")
            sys.exit()






def format_template_name(template_name, max_length=20):
    # Trim the template name and add ellipsis if it exceeds max length
    if len(template_name) > max_length:
        template_name = template_name[:max_length-3] + "..."

    # Left-justify the template name and fill the remaining spaces with '\t'
    template_name = template_name.ljust(max_length, ' ')
    # print("\n\n\nfinal template name: '"+template_name+"'\n\n\n")

    return template_name





# Function for checking and creating .gitignore
def create_gitignore():
    if not os.path.isfile('.gitignore'):
        # print(msg_warn("\n!! No '.gitignore' file found."))
        # use_template = input(msg_bright("Create from template?") + msg_dim(" Y ") + Fore.CYAN)
        # if use_template.lower() != 'n':
        # print("\033[A\033[2K", end="")
        # print(msg_bright("Copy .gitignore template? ") + Fore.CYAN + Style.BRIGHT + "Y")
        template_name = input(msg_bright("Use .gitignore template: ") + msg_dim("(Node) ") +  Fore.CYAN)
        if template_name.lower() == '':
            template_name = "Node"
        
        formatted_template_name = format_template_name(template_name)
        
        print("\033[A\033[2K", end="")
        print(msg_bright("Use .gitignore template? ") + Fore.CYAN + Style.BRIGHT + formatted_template_name + msg_dim("Copying template..."))

        response = requests.get(f'https://raw.githubusercontent.com/github/gitignore/master/{template_name}.gitignore')
        if response.status_code == 200:
            with open('.gitignore', 'w') as f:
                f.write(response.text)
            print("\033[A\033[2K", end="")
            print(msg_bright("Use .gitignore template? ") + Fore.CYAN + Style.BRIGHT + formatted_template_name + msg_dim("Template copied.\n"))

            # print(Fore.GREEN + f"Created '.gitignore' from template: '{template_name}'" + Style.RESET_ALL)
        else:
            print(Fore.RED + Style.BRIGHT + f"Error creating '.gitignore' from template: '{template_name}'. Verify the template exists or create the file manually.")
            sys.exit()
        # else:
        #     with open('.gitignore', 'w') as f:
        #         f.write("# TODO- Add .gitignore contents")
        #     print(Fore.GREEN + "Created default '.gitignore' file" + Style.RESET_ALL)




@useCache
def get_git_details():
    try:
        origin = run_command('git remote get-url origin')
    except Exception as e:
        origin = None
    
    username = run_command('git config user.name')
    email = run_command('git config user.email')
    branch = run_command('git symbolic-ref --short HEAD')

    if origin:
        fetch_url = run_command('git remote get-url origin')
        push_url = run_command('git remote get-url --push origin')
        fetch_user, fetch_repo = fetch_url.split('/')[-2:]
        fetch_repo = fetch_repo.replace('.git', '')
        push_user, push_repo = push_url.split('/')[-2:]
        push_repo = push_repo.replace('.git', '')
    else:
        fetch_url = push_url = 'local'
        fetch_user = push_user = 'local'
        fetch_repo = push_repo = run_command('git rev-parse --show-toplevel').split('/')[-1]

    run_command('git add .')
    # changed_files = run_command('git diff --cached --name-only').split('\n')
    # changed_files = list(filter(None, run_command('git diff --cached --name-status --numstat').split('\n')))

    name_status_lines = list(filter(None, run_command('git diff --cached --name-status').split('\n')))
    numstat_lines = list(filter(None, run_command('git diff --cached --numstat').split('\n')))

    combined_changes = {}

    for name_status_line, numstat_line in zip(name_status_lines, numstat_lines):
        status, filename = name_status_line.split(maxsplit=1)
        additions, deletions, _ = numstat_line.split()

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



def print_break():
    print('\n' + Fore.BLACK + '-' * 60, end="")



def print_heading():
    g = get_git_details()

    print(Fore.BLUE + Style.BRIGHT + f"{g['username']}" + msg_dim(f"  {g['email']}"))
    print(f" fetch << {Fore.BLUE}{g['fetch_user']}/{Fore.WHITE}{g['fetch_repo']}/{Fore.YELLOW}{g['branch']}" + Style.RESET_ALL)
    print(f" push  >> {Fore.BLUE}{g['push_user']}/{Fore.WHITE}{g['push_repo']}/{Fore.YELLOW}{g['branch']}" + Style.RESET_ALL)



def print_history(last = False):
    g = get_git_details()

    if last:
        commit_limit = 1 # Display only the most recent commit if `last` is True, otherwise display the last 10 commits
        
        history = run_command(f'git log -n 1 --pretty=format:"---{Fore.YELLOW + Back.BLACK}%h {Fore.BLUE}%ad{Style.RESET_ALL + Fore.BLACK} %ar {Fore.GREEN}%an{Style.RESET_ALL} \n{Style.BRIGHT + Fore.WHITE}%s" --date=format:"%m/%d %H:%M"')
        commits = history.split('---')
        commits = [entry for entry in commits if entry]

        
        for commit in commits[:commit_limit]:
            commit = commit.replace(g['username'], '')
            print(f"{commit}")
    
    else:
        commit_limit = MAX_HISTORY # Display only the most recent commit if `last` is True, otherwise display the last 10 commits
        
        history = run_command(f'git log --pretty=format:"---{Fore.YELLOW + Back.BLACK}%h {Fore.BLUE}%ad{Style.RESET_ALL + Fore.BLACK} %ar {Fore.GREEN}%an{Style.RESET_ALL} \n%s" --date=format:"%m/%d %H:%M" --reverse')
        commits = history.split('---')
        commits = [entry for entry in commits if entry]

        print_break()
        print(Fore.BLUE + Style.BRIGHT + "\nHistory:" + msg_dim(f" ({len(commits)} commits)"))
        
        for commit in commits[-commit_limit:]:
            commit = commit.replace(g['username'], '')
            print(f"{commit}")




def print_changed():
    g = get_git_details()
    files = g['changed_files']
    print_break()

    if not files:
        print(msg_err("\nNo changed files found... Exiting.\n"))
        sys.exit()

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
    added = ""
    deleted = ""
    if added_count > 0:
        added = f", {added_count} added"
    if deleted_count > 0:
        added = f", {deleted_count} deleted"
    
    print(Fore.BLUE + Style.BRIGHT + "\nChanges:" + msg_dim(f" ({changed_count} changed{added}{deleted})"))

    for filename, changes in list(files.items())[:MAX_CHANGES]: 
        # print(filename, changes)
        # added, removed, path = file.split('\t')
        name = format_template_name(filename, 30)
        print(f"{msg_warn('-')} {name} {Fore.BLACK + changes['status']} {Fore.GREEN}+{changes['additions']} {Fore.RED}-{changes['deletions']}{Style.RESET_ALL}")

    if len(files) > MAX_CHANGES:
        print(msg_dim(f"    ...{len(files) - MAX_CHANGES} more files"))


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



# Main function
def main():

    # load_config()

    clear_console()
    init_git()
    create_gitignore()

    print_heading()
    print_history()
    print_changed()
    

    # username, email, branch, fetch_user, fetch_repo, push_user, push_repo, changed_files = get_git_details()

    # print(Fore.BLUE + Style.BRIGHT + f"{username}" + Style.RESET_ALL + f"  {email}")
    # print(f"  fetch << {Fore.BLUE}{fetch_user}/{Fore.WHITE}{fetch_repo}/{Fore.YELLOW}{branch}" + Style.RESET_ALL)
    # print(f"  push  >> {Fore.BLUE}{push_user}/{Fore.WHITE}{push_repo}/{Fore.YELLOW}{branch}" + Style.RESET_ALL)


    print_break()
    message = input(Fore.BLUE + Style.BRIGHT + "\nCommit:\n" + Style.RESET_ALL).strip()
    if not message:
        print("\033[A\033[2K", end="")
        print(msg_err("No message. Cancelling commit and exiting.\n"))
        sys.exit()

    try:
        run_command('git commit -m "' + message + '"')
        clear_console()
        print_heading()
        print('')
        print_history(True)
        print('')
    except Exception as e:
        print(msg_err("Error creating commit:" + e))

# Execute main function
if __name__ == "__main__":
    main()
