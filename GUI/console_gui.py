import random
import sys
import threading
import subprocess
import os
import time
from rich import print as rprint
from rich.table import Table
from rich.progress import track
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt, Confirm
from rich.panel import Panel, Style
from rich.tree import Tree
from rich.layout import Layout
import psutil

from Core.Core import Core
from Command_System.CommandTree import CommandTree

if sys.platform == "linux":
    # required for proper pyautogui and audio workflow
    subprocess.Popen("jack_control start", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    subprocess.Popen("xhost +local:$USER", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)


class GUI:
    def __init__(self):
        self.std = Console()
        self.input = Prompt.ask
        self.print = rprint
        self.plugin_nums = {}
        self.back = """
Press [strong]Enter[/] to go back [red]<--[/]
"""
        self.core = Core()
        self.start_up()

    @staticmethod
    def clear():
        print("\033c", end="")
        print("\x1bc", end="")

    def bprint(self, text: str, title: str = "Stewart"):
        self.print(
            Panel(text, border_style=Style(color="white", frame=True, dim=True), title=title, title_align="left",
                  highlight=True, width=90))

    def update_markdown(self):
        self.main_page = f"""[purple]
███████╗████████╗███████╗██╗    ██╗ █████╗ ██████╗ ████████╗
██╔════╝╚══██╔══╝██╔════╝██║    ██║██╔══██╗██╔══██╗╚══██╔══╝
███████╗   ██║   █████╗  ██║ █╗ ██║███████║██████╔╝   ██║
╚════██║   ██║   ██╔══╝  ██║███╗██║██╔══██║██╔══██╗   ██║
███████║   ██║   ███████╗╚███╔███╔╝██║  ██║██║  ██║   ██║
╚══════╝   ╚═╝   ╚══════╝ ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝
[/purple]
[strong]VERSION: [/strong][purple]0.0.1[/]  [strong]AUTHOR: [/strong][i]ilyamiro[/i] [strong]GitHub: [/][underline white][link=https://github.com/ilyamiro/Stewart]https://github.com/ilyamiro/Stewart[/link][/]

[u]RAM USAGE[/]: {float(str(psutil.virtual_memory().available / (1024 ** 3))[:4])}/{float(str(psutil.virtual_memory().total / (1024 ** 3))[:5])} Gb 
:computer_disk: [u]DISK USAGE[/]: {float(str(psutil.disk_usage("/").free / (1024 ** 3))[:5])}/{float(str(psutil.disk_usage("/").total / (1024 ** 3))[:5])} Gb
:computer: [u]PLATFORM[/]: [bold yellow]{sys.platform.capitalize()}[/]
[u]STEWART[/]: [strong]{"[green]ONLINE[/]" if self.core.power else "[red]OFFLINE[/]"}[/]

1. {"[red]Turn off[/]" if self.core.power else "[green]Turn on[/]"}
2. Settings (Not available now)
3. About a project (Not available now)
4. Plugins and extensions
5. Exit"""

    def update_plugins(self):
        self.plugin_print = """
        _             _           
       | |           (_)          
  _ __ | |_   _  __ _ _ _ __  ___ 
 | '_ \\| | | | |/ _` | | '_ \\/ __|
 | |_) | | |_| | (_| | | | | \\__ \\
 | .__/|_|\\__,_|\\__, |_|_| |_|___/
 | |             __/ |            
 |_|            |___/         

        """
        self.number_of_plugins = 0
        for plugin in self.core.plugins:
            self.number_of_plugins += 1
            self.plugin_print += f"""
------------------------------------------------------------------------------
{self.number_of_plugins} [strong]{plugin["name"]} Plugin[/]
[u]Author[/]: [i]{plugin["author"]}[/]
[strong]Type:[/] [i]{plugin["type"].capitalize()}[/] p
Available on [red]{plugin["platform"]}[/] platform :computer:
Description: [i][grey]{plugin["about"]}[/][/]

Status: {"[green]Enabled[/]" if self.core.plugin_enable[plugin["name"]] else "[red]Disabled[/]"}
------------------------------------------------------------------------------"""
            self.plugin_nums[self.number_of_plugins] = plugin["name"]
        self.plugin_print += self.back

    def plagin_handling(self, name: str):

        while True:
            self.clear()
            args_print = self.create_plugin_stats(name)
            self.print(*args_print)

            choice = self.input("Disable?" if self.core.plugin_enable[name] else "Enable?", choices=["y", "n"], default="", show_default=False)
            match choice:
                case "y":
                    if self.core.plugin_enable[name]:

                        self.core.disable_plagin(name)

                    else:
                        self.core.enable_plugin(name)
                case "n":
                    break
                case _:
                    break
    def create_plugin_stats(self, name):
        plugin = None
        func_table = Table(title="Functionality", title_style=Style(bold=True, color="purple"), show_lines=True)
        func_table.add_column("Command", header_style="bold")
        func_table.add_column("Handler", header_style="red")
        func_table.add_column("Synthesis", header_style="yellow")
        func_table.add_column("Parameters", header_style="bold black")
        for pl in self.core.plugins:
            if pl["name"].lower() == name.lower():
                plugin = pl
                break
        to_print1 = f"""
[bold red]Plugin settings[/]        
        
[strong]Name: [/][yellow]{name.capitalize()}[/]
[strong]Author: [/][u]{plugin["author"]}[/]
[strong]Type: [/][i]{plugin["type"]}[/]"""
        commands = self.core.plugin_ref[name]
        for command in commands.keys():
            parameters = commands[command]["parameters"]
            result = ""
            for key, value in parameters.items():
                result += f"{key}: {value}\n"
            if commands[command]["synthesize"]:
                synthesize = ";\n".join(commands[command]["synthesize"])
            else:
                synthesize = "-----"
            func_table.add_row(" ".join(command), commands[command]["handler"], synthesize, result)

        tree = Tree(name, guide_style=Style(bold=True, underline2=True, color="yellow"), expanded=True)
        for command in commands.keys():
            self.__add_command_to_tree(tree, command)

        ender = f"""
[bold]Plugin status:[/] {"[green]Enabled[/]" if self.core.plugin_enable[name] else "[red]Uninstalled[/]"}
"""
        ender += self.back


        return [to_print1, func_table, """
[red][bold]COMMAND TREE[/][/]
        """, tree, ender]

    def start_up(self) -> None:
        self.update_markdown()
        self.core.start()
        thread = threading.Thread(target=self.main_console)
        thread.start()

    def change_status(self) -> None:
        """
        Function to turn on/off stewart
        """
        self.core.power = True if not self.core.power else False

    @staticmethod
    def __add_command_to_tree(tree, command):
        current_node = tree
        for action in command:
            child_node = None
            for node in current_node.children:
                if node.label == action:
                    child_node = node
                    break
            if child_node is None:
                child_node = current_node.add(action)
            current_node = child_node

    def plugins(self):
        while True:
            self.update_plugins()
            self.clear()
            self.print(self.plugin_print)
            choice = self.input(prompt="Choose plagin (number) to interact", choices=[str(number) for number in range(1, self.number_of_plugins + 1)], default="", show_default=False)
            if choice:
                self.plagin_handling(self.plugin_nums[int(choice)])
            elif not choice:
                break

    def main_console(self):
        while True:
            self.update_markdown()
            self.clear()
            self.bprint(self.main_page)
            choice = self.input(prompt="Your choice", choices=["1", "2", "3", "4", "5"], default="", show_default=False)
            match choice:
                case "1":
                    self.change_status()
                case "4":
                    self.plugins()
                case "5":
                    choice = self.input("Are you sure you want to exit?", choices=["y", "n"], default="", show_default=False)
                    if choice == "y":
                        self.clear()
                        self.print("[red]Exiting...[/]")
                        os._exit(1)

                case _:
                    pass



if __name__ == "__main__":
    stewart = GUI()
