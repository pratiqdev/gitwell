import os
import subprocess
import requests
import json
from getpass import getpass
from colorama import Fore, Style, Back
from types import SimpleNamespace

# Create an instance

import time
import functools

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


# def useCache(cache_time=5000):
#     def decorator(func):
#         cache = {}

#         @functools.wraps(func)
#         def wrapper(*args, **kwargs):
#             key = str(args) + str(kwargs)
#             cached_result, cached_time = cache.get(key, (None, None))

#             if cached_time is None or time.monotonic() - cached_time > cache_time / 1000:
#                 # Cache is empty or expired
#                 result = func(*args, **kwargs)
#                 cache[key] = (result, time.monotonic())
#             else:
#                 # Cache hit
#                 result = cached_result

#             return result

#         return wrapper

#     return decorator



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
        init_git_response = input(msg_bright("?? Initialize a repository? ") + msg_dim("(N) ") + Fore.CYAN)
        if init_git_response.lower() == 'y':
            print("\033[A\033[2K", end="")
            print(msg_bright("?? Initialize a repository? ") + Fore.CYAN + Style.BRIGHT + "Y" + msg_dim( 19 * ' ' + "Initializing repo..."))
            # print(">> Initializing git repo...")
            run_command('git config --global init.defaultBranch main')
            run_command('git init')
            print("\033[A\033[2K", end="")
            print(msg_bright("?? Initialize a repository? ") + Fore.CYAN + Style.BRIGHT + "Y" + msg_dim(19 * ' ' + "Repo initialized."))
        else:
            print("\033[A\033[2K", end="")
            print(msg_bright("?? Initialize a repository? ") + Fore.CYAN + Style.BRIGHT + "N")
            print(Fore.RED + Style.BRIGHT + "\nThis command can only be run from within a git repository.")
            exit()






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
        # use_template = input(msg_bright("?? Create from template?") + msg_dim(" Y ") + Fore.CYAN)
        # if use_template.lower() != 'n':
        # print("\033[A\033[2K", end="")
        # print(msg_bright("?? Copy .gitignore template? ") + Fore.CYAN + Style.BRIGHT + "Y")
        template_name = input(msg_bright("?? Use .gitignore template: ") + msg_dim("(Node) ") +  Fore.CYAN)
        if template_name.lower() == '':
            template_name = "Node"
        
        formatted_template_name = format_template_name(template_name)
        
        print("\033[A\033[2K", end="")
        print(msg_bright("?? Use .gitignore template? ") + Fore.CYAN + Style.BRIGHT + formatted_template_name + msg_dim("Copying template..."))

        response = requests.get(f'https://raw.githubusercontent.com/github/gitignore/master/{template_name}.gitignore')
        if response.status_code == 200:
            with open('.gitignore', 'w') as f:
                f.write(response.text)
            print("\033[A\033[2K", end="")
            print(msg_bright("?? Use .gitignore template? ") + Fore.CYAN + Style.BRIGHT + formatted_template_name + msg_dim("Template copied.\n"))

            # print(Fore.GREEN + f"Created '.gitignore' from template: '{template_name}'" + Style.RESET_ALL)
        else:
            print(Fore.RED + Style.BRIGHT + f"Error creating '.gitignore' from template: '{template_name}'. Verify the template exists or create the file manually.")
            exit()
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
    changed_files = list(filter(None, run_command('git diff --cached --name-only').split('\n')))
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
        "changed_files": changed_files,
    }



def print_break():
    print('\n' + Fore.BLACK + '-' * 60, end="")



def print_heading():
    g = get_git_details()

    print(Fore.BLUE + Style.BRIGHT + f"{g['username']}" + msg_dim(f"  {g['email']}"))
    print(f" fetch << {Fore.BLUE}{g['fetch_user']}/{Fore.WHITE}{g['fetch_repo']}/{Fore.YELLOW}{g['branch']}" + Style.RESET_ALL)
    print(f" push  >> {Fore.BLUE}{g['push_user']}/{Fore.WHITE}{g['push_repo']}/{Fore.YELLOW}{g['branch']}" + Style.RESET_ALL)



def print_history():
    g = get_git_details()
    history = run_command(f'git log --pretty=format:"---{Fore.YELLOW + Back.BLACK}%h {Fore.BLUE}%ad{Style.RESET_ALL + Fore.BLACK} %ar {Fore.GREEN}%an{Style.RESET_ALL} \n %s" --date=format:"%m/%d %H:%M" --reverse')
    commits = history.split('---')
    commits = [entry for entry in commits if entry]

    print_break()
    print(Fore.BLUE + Style.BRIGHT + "\nHistory:" + msg_dim(f" ({len(commits)} commits)"))
    for commit in commits[:10]:
        commit = commit.replace(g['username'], '')
        print(f" {commit}")




def print_changed():
    g = get_git_details()
    files = g['changed_files']
    print_break()
    print(Fore.BLUE + Style.BRIGHT + "\nChanges:" + Style.RESET_ALL + f" ({len(files)} files)")

    if not files:
        print(msg_err("\nNo changed files found... Exiting.\n"))
        exit()

    

    for file in files[:3]:
        print(f" {msg_warn('-')} {file}")

    if len(files) > 3:
        print(f"    ...{len(files) - 3} more files")


 


# Main function
def main():
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
        exit()

    run_command('git commit -m "' + message + '"')

# Execute main function
if __name__ == "__main__":
    main()
