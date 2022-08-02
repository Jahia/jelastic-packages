#!/usr/bin/env python3

import argparse
import os
import re
import sys
import yaml
import pygraphviz as pgv
import cmd2
from rich.console import Console
from rich.table import Table
from rich.progress import track


console = Console()


parser = argparse.ArgumentParser()
subparser_toplevel = parser.add_subparsers(help='command', dest='command')


subparser_shell = subparser_toplevel.add_parser("shell", help="shell access")
subparser_graph = subparser_toplevel.add_parser('graph', help='create dot file')
subparser_check = subparser_toplevel.add_parser('check', help='check manifest dependencies')
subparser_mixins_duplicates = subparser_toplevel.add_parser('mixins_duplicates', help='check for duplicated actions in mixins files')
subparser_search = subparser_toplevel.add_parser('search', help="searching for something")


subparser_graph.add_argument("-o", "--output", help="dot file to write to", default="output.dot")
subparser_graph.add_argument("-c", "--console", help="output generated dot to console", default=False, action="store_true")
subparser_graph.add_argument("-q", "--quiet", help="be quiet", default=False, action='store_true')
subparser_graph.add_argument("file", nargs='*', type=argparse.FileType('r'), help="manifest to graph", default=None)


subparser_check.add_argument("file", nargs='*', type=argparse.FileType('r'), help="manifest to check", default=None)
subparser_check.add_argument("-q", "--quiet", help="be quiet", default=False, action='store_true')


subparser_search.add_argument('-i', '--id', help="id number")
subparser_search.add_argument('-n', '--name', help="which name")
subparser_search.add_argument('-k', '--kind', help="which kind", choices=['manifest', 'action'])
subparser_search.add_argument('-s', '--section', help="which section", choices=['onInstall', 'actions'])
subparser_search.add_argument('-p', '--parent', help="from this manifests id", type=int)
subparser_search.add_argument('-c', '--childs', help="having theses actions list id as child", type=str)
subparser_search.add_argument('--call', help="calling these actions list id", type=str)
subparser_search.add_argument('--called_by', help="called by these actions list id", type=str)
subparser_search.add_argument('--not_legit', help="action is not legit", default=False, action="store_true")


args = parser.parse_args()


graph_manifest_parser = cmd2.Cmd2ArgumentParser()
graph_manifest_parser.add_argument('file', type=str, help='the manifest to check')
graph_manifest_parser.add_argument('-o', '--output', type=str, help='where to output dot', default="output.dot")
graph_manifest_parser.add_argument("-q", "--quiet", help="be quiet", default=False, action='store_true')
graph_manifest_parser.add_argument("-c", "--console", help="output generated dot to console", default=False, action="store_true")


check_manifest_parser = cmd2.Cmd2ArgumentParser()
check_manifest_parser.add_argument('file', type=str, help='the manifest to check')


folder_list = []
manifest_list = []
actions_list = []
nodes_list = []

regex_dict = {
        "is_event": r"^on(After|Before)(ChangeTopology|Scale(In|Out)|DetachExtIp|RemoveNode|Set(CloudletCount|EnvVars|EntryPoint|RunCmd)|Add(Node|Volume)|(un)?[lL]inkNodes|RestartContainer|ServiceScaleOut|StartService|CloneNodes)",
        "is_mixins": r"/mixins/",
        "is_events_file": r"events.ya?ml",
        }

jelastic_simple_keywords = (
        "assert",
        "createDirectory",
        "createFile",
        "deploy",
        "elif",
        "else",
        "forEach",
        "foreach",
        "if",
        "install",
        "installAddon",
        "log",
        "message",
        "type",
        "unpack",
        )

jelastic_script_keyword = (
        "script",
        "cmd",
        )

jelastic_keywords_with_args = (
        "api",
        "appendFile",
        "cmd",
        "env",
        "environment",
        "replaceInFile",
        "return",
        "script",
        "set",
        "setGlobals",
        "setNodeDisplayName",
        "sleep",
        "upload",
        "writeFile",
        "writefile",
        )

jelastic_keywords_args = (
        "data",
        "nodeGroup",
        "nodegroup",
        "user",
        "vars"
        )
jelastic_keywords = tuple(
        set(
            jelastic_simple_keywords
            + jelastic_script_keyword
            + jelastic_keywords_with_args
            + jelastic_keywords_args
            )
        )

graph_attributes = {
        "root": {
            "concentrate": "true",
            "directed": True,
            "rankdir": "LR",
            "constraint": "false",
            },
        "manifest": {
            "concentrate": "true",
            "bgcolor": "lemonchiffon",
            "constraint": "false",
            },
        "section_onInstall": {
            "concentrate": "true",
            "bgcolor": "lavender",
            "constraint": "false",
            },
        "section_actions": {
            "concentrate": "true",
            "bgcolor": "lightcyan",
            "constraint": "false",
            },
        "section_events": {
            "concentrate": "true",
            "bgcolor": "lightgray",
            "constraint": "false",
            },
        "action_legit": {
            "concentrate": "true",
            "constraint": "false",
            },
        "action_not_legit": {
            "concentrate": "true",
            "style": "filled,dashed",
            "color": "red",
            "fillcolor": "lightpink",
            "constraint": "false",
            },
        }

graph = pgv.AGraph(**graph_attributes["root"])


class Action():
    def __init__(self, name: str, **kwargs):
        self.__name = name
        self.__content = kwargs["content"]
        self.__from_file = kwargs["from_file"]
        try:
            self.__params = kwargs["params"]
        except:
            pass

    def name(self) -> str:
        return self.__name

    def content(self):
        return self.__content

    def parameters(self):
        return self.__params

    def from_file(self) -> str:
        return self.__from_file


class Manifest():
    def __init__(self, name: str, **kwargs):
        self.__name = name
        self.__kind = re.split('/', name)[1:-1]
        self.__full_content = kwargs["full_content"]

        if "mixins" in self.__full_content:
            # update path to be relatif to the root folder if need
            # so object's mixins and object's name() can match
            self.__mixins = [ re.sub(r'(\.\./)+', "./", mixin)
                    for mixin in self.__full_content["mixins"] ]
        else:
            self.__mixins = []

        if "onInstall" in self.__full_content:
            # it's a list but items can be string or dict
            self.__on_install = self.__full_content["onInstall"]
        else:
            self.__on_install = []

        if "actions" in self.__full_content:
            # transform self.__full_content["actions"] dict
            # to a list where each dict's item is a dict item in a list
            self.__embeded_actions = [{k:self.__full_content["actions"][k]}
                    for k in self.__full_content["actions"]]
        else:
            self.__embeded_actions = []

        # transform self.__full_content's events dict
        # to a list where each dict's item is a dict item in a list
        self.__events = [{k:self.__full_content[k]}
                for k in self.__full_content.keys() if re.search(regex_dict["is_event"], k)]

    def name(self) -> str:
        return self.__name

    def kind(self) -> list:
        return self.__kind

    def full_content(self):
        return self.__full_content

    def mixins(self) -> list:
        return self.__mixins

    def on_install(self) -> list:
        return self.__on_install

    def embeded_actions(self) -> list:
        return self.__embeded_actions

    def events(self) -> list:
        return self.__events


class Node():
    def __init__(self, name, **kwargs):
        self.__name = name
        self.__parent = kwargs.get('parent', None)
        self.__childs = kwargs.get('childs', [])
        self.__call = kwargs.get('call', [])
        self.__called_by = kwargs.get('called_by', [])
        self.__kind = kwargs.get('kind', None)
        self.__section = kwargs.get('section', None)
        self.__legit = kwargs.get('legit', True)

    def get_all_attributes(self) -> dict:
        methods = [
                x for x in dir(self) if x.startswith('_') is False
                and x.startswith('set_') is False
                and x.startswith('add_') is False
                and x != "get_all_attributes"
                ]
        attributes = {}
        for method in methods:
            method_to_call = getattr(self, method)
            attributes[method] = method_to_call()
        return attributes

    def name(self):
        return self.__name

    def kind(self):
        return self.__kind

    def section(self):
        return self.__section

    def legit(self):
        return self.__legit

    def parent(self):
        return self.__parent

    def childs(self):
        return self.__childs

    def call(self):
        return self.__call

    def called_by(self):
        return self.__called_by

    def set_parent(self, node_id: int):
        self.__parent = node_id

    def add_childs(self, childs: list):
        self.__childs = list(set([*self.__childs, *childs]))  # also remove duplicates

    def add_call(self, call: list):
        self.__call = list(set([*self.__call, *call]))  # also remove duplicates

    def add_called_by(self, called_by: list):
        self.__called_by = list(set([*self.__called_by, *called_by]))  # also remove duplicates

    def set_kind(self, kind: str):
        self.__kind = kind

    def set_section(self, section: str):
        self.__section = section

    def set_legit(self, legit: bool):
        self.__legit = legit


def update_node(node_id: int, **kwargs):
    parent = kwargs.get('parent', None)
    add_childs = kwargs.get('add_childs', [])
    add_call = kwargs.get('add_call', [])
    add_called_by = kwargs.get('add_called_by', [])
    kind = kwargs.get('kind', None)
    section = kwargs.get('section', None)
    legit = kwargs.get('legit', None)

    if parent:
        nodes_list[node_id].set_parent(parent)
    if add_childs:
        nodes_list[node_id].add_childs(add_childs)
    if add_call:
        nodes_list[node_id].add_call(add_call)
    if add_called_by:
        nodes_list[node_id].add_called_by(add_called_by)
    if kind:
        nodes_list[node_id].set_kind(kind)
    if section:
        nodes_list[node_id].set_section(section)
    if legit:
        nodes_list[node_id].set_legit(legit)


def get_node_parents_id_by_name(name: str) -> list:
    return [ nodes_list.index(x) for x in nodes_list if x.name() == name ]


def search_node(get="object", **criteria) -> list:
    name = criteria.get('name', None)
    kind = criteria.get('kind', None)
    section = criteria.get('section', None)
    legit = criteria.get('legit', None)
    parent = criteria.get('parent', None)
    childs = criteria.get('childs', [])
    call = criteria.get('call', [])
    called_by = criteria.get('called_by', [])
    matching_list = nodes_list.copy()

    if name:
        matching_list = [ item for item in matching_list if item.name() == name ]
    if kind:
        matching_list = [ item for item in matching_list if item.kind() == kind ]
    if section:
        matching_list = [ item for item in matching_list if item.section() == section ]
    if parent or parent==0:
        matching_list = [ item for item in matching_list if item.parent() == parent ]
    if childs:
        matching_list = [ item for item in matching_list if item.childs() == childs ]
    if call:
        matching_list = [ item for item in matching_list if item.call() == call ]
    if called_by:
        matching_list = [ item for item in matching_list if item.called_by() == called_by ]
    if isinstance(legit, bool):
        matching_list = [ item for item in matching_list if item.legit() == legit ]

    if get == "id":
        return [nodes_list.index(x) for x in matching_list]

    return matching_list


def log(string, **kwargs):
    options = {}
    prefix_with = ""
    quiet = kwargs.get("quiet", SILENT_MODE)
    not_legit = kwargs.get("not_legit", False)
    if quiet:
        return
    kind = kwargs.get('kind', None)

    if kind == "work_in_progress":
        pass
    elif not_legit:
        prefix_with = ":x:"
    elif not string:
        console.rule("")
        return
    console.print(f"{prefix_with}{string}", **options)


def is_keyword(word: str) -> bool:
    return word in jelastic_keywords


def generate_lists():
    for root, _, files in os.walk(os.path.relpath(os.getcwd())):
        for file in files:
            if re.search(r"\.ya?ml$", file) and not re.search(r"(v\d+_)?assets", root):
                with open(f"{root}/{file}", "r", encoding="utf-8") as stream:
                    data_loaded = yaml.safe_load(stream)
                try:
                    manifest_list.append(Manifest(f"{root}/{file}",
                        full_content=data_loaded))
                except Exception as error:
                    print(f"error on {root}/{file}: {error}")
                nodes_list.append(Node(f"{root}/{file}", kind="manifest"))
                parent_id = len(nodes_list) - 1
                if "actions" in data_loaded:
                    for action in data_loaded["actions"]:
                        actions_list.append(
                                Action(
                                    action,
                                    content=data_loaded["actions"][action],
                                    from_file=f"{root}/{file}",
                                    )
                                )
                        nodes_list.append(
                                Node(action,
                                    kind="action",
                                    section="actions",
                                    parent=parent_id,
                                )
                        )
                        child_id = len(nodes_list) - 1
                        update_node(parent_id, add_childs=[child_id])


def get_manifest_id_by_name(name: str) -> int:
    try:
        return [manifest_list.index(x) for x in manifest_list if x.name() == name][0]
    except:
        return ""


def get_node_id_by_name(name: str) -> list:
    try:
        return [nodes_list.index(x) for x in nodes_list if x.name() == name]
    except:
        return ""


def crawl(item, degree=1, section="", manifest_name="", previous_was_legit=True,
        previous_degree=1, previous_item_id=0, called_by=None):
    padding = ' '
    width = degree * 4
    manifest = manifest_list[get_manifest_id_by_name(manifest_name)]

    # get all related actions nodes
    manifest_id = get_manifest_id_by_name(manifest_name)
    mixins_list = manifest_list[manifest_id].mixins()
    for mixin in mixins_list:
        if mixin.startswith("/"):   # yes, one manifest has a '/../../mixins/blabla.yml' mixin
            mixin = re.sub(r"^/\W*", "./", mixin)

    if isinstance(item, dict):
        legit = False
        to_break = False
        i = 0
        for k in item:
            i += 1
            first_word = re.split(r"[\W]", k)[0]
            if is_keyword(first_word):
                if first_word in jelastic_script_keyword:
                    kind = "script_keyword"
                elif first_word in jelastic_keywords_with_args:
                    kind = "jelastic keyword with args"
                    to_break = True
                elif first_word in jelastic_keywords_args:
                    kind = "jelastic keyword args"
                else:
                    kind = "keyword"
                log(rf"{padding :>{width}}\[{first_word}] is a {kind}")
                if kind == "jelastic keyword with args":
                    break
            elif first_word in jelastic_keywords_args:
                continue
            elif re.search(regex_dict["is_event"], k):
                legit = True
                kind = "event"
                log(rf"{padding :>{width}}\[{k}] is an event")
                # isn't in the nodes objects list yet, so append to it:
                parent_id = search_node(get="id", name=manifest_name, kind="manifest")
                nodes_list.append(Node(k, parent=parent_id, kind=kind, legit=legit, section=section))
            elif first_word in [ x.name() for x in actions_list ]:
                matching_actions = [ x for x in actions_list if x.name() == first_word ]
                # select the actions used in case of actions with the same name
                for matching_action in matching_actions:
                    if matching_action.from_file() == manifest_name or \
                       matching_action.from_file() in manifest.mixins():
                        matching_actions = [matching_action]
                legit = True
                kind = "action"
                log(rf"{padding :>{width}}\[{first_word}] is an action from {[x.from_file() for x in matching_actions]}")

                if section != "actions" :
                    parent_id = search_node(get="id", name=manifest_name)[0]
                else:
                    parent_id = get_node_parents_id_by_name(matching_actions[0].from_file())[0]
                try:
                    node_id = search_node(get="id", name=first_word, kind=kind,
                            parent=parent_id, section=section)[0]
                except:
                    nodes_list.append(Node(first_word, parent=parent_id, kind=kind, legit=legit, section=section))
                    node_id = search_node(get="id", name=first_word, kind=kind,
                            parent=parent_id, section=section)[0]
                    update_node(parent_id, add_childs=[node_id])
                update_node(node_id, legit=legit, section=section)

                if called_by:
                    node_id = search_node(get="id", name=first_word, kind=kind,
                            parent=parent_id, section=section)[0]
                    if node_id != called_by:
                        update_node(node_id, add_called_by=[called_by])
                        update_node(called_by, add_call=[node_id])

                if section != "actions":
                    calls_total = search_node(get="id", section="actions", name=first_word)
                    legit_calls_parent_name = [manifest_name] + manifest_list[manifest_id].mixins()
                    calls = []
                    for call in calls_total:
                        call_parent_id = nodes_list[call].parent()
                        if nodes_list[call_parent_id].name() in legit_calls_parent_name:
                            calls.extend(search_node(get="id", sections="actions", name=first_word, parent=call_parent_id))

                    if node_id not in calls:
                        update_node(node_id, add_call=calls)
                    for target in calls:
                        update_node(target, add_called_by=[node_id])

                if isinstance(item[k], list) and len(item[k]) == 1:
                    next_item = str(item[k])
                else:
                    next_item = item[k]

                if not isinstance(item[k], dict):
                    crawl(next_item, degree = degree + 1, section=section, manifest_name=manifest_name,
                            previous_degree=degree, previous_item_id=i, called_by=node_id)

            elif degree > 1 and previous_item_id != 0:
                legit = True
                log(rf"{padding :>{width}}\[{k}] is a parameter")

            elif not legit and previous_was_legit:
                legit = False
                to_break = True
                kind = "action"
                parent_id = search_node(get="id", name=manifest_name, kind="manifest")[0]
                nodes_list.append(Node(k, parent=parent_id, kind=kind, legit=legit, section=section))
                log(rf"{padding :>{width}}\[{k}] is an action not defined anywhere !")

                if section == "actions" and \
                        not search_node(name=first_word, parent=parent_id, section=section):
                    nodes_list.append(Node(k, parent=parent_id, kind=kind, legit=legit, section=section))

                if called_by:
                    node_id = search_node(get="id", name=first_word, kind=kind,
                            parent=parent_id, section=section)[0]
                    if node_id != called_by:
                        update_node(node_id, add_called_by=[called_by])
                        update_node(called_by, add_call=[node_id])

            else:
                legit = False
                log(rf"{padding :>{width}}\[{k}] is an unknown kind, this should never be showned")

        if not isinstance(item[k], str) and not to_break:
            crawl(item[k], degree + 1, section=section, manifest_name=manifest_name,
                    previous_degree=degree, previous_item_id=i)

        return legit, to_break

    elif isinstance(item, str):
        legit = False
        to_break = False
        first_word = re.split(r"[\W]", item)[0]
        if is_keyword(first_word):
            if first_word in jelastic_script_keyword:
                kind = "script_keyword"
            else:
                kind = "keyword"
            log(rf"{padding :>{width}}\[{first_word}] is a {kind}")
        elif first_word in [ x.name() for x in actions_list ]:
            matching_actions = [ x for x in actions_list if x.name() == first_word ]
            # select the actions used in case of actions with the same name
            for matching_action in matching_actions:
                if matching_action.from_file() == manifest_name or \
                   matching_action.from_file() in manifest.mixins():
                    matching_actions = [matching_action]

            legit = True
            kind = "action"
            log(rf"{padding :>{width}}\[{first_word}] is an action from {[x.from_file() for x in matching_actions]}")

            if section == "onInstall":
                parent_id = search_node(get="id", name=manifest_name)[0]
            else:
                parent_id = get_node_parents_id_by_name(matching_actions[0].from_file())[0]

            try:
                node_id = search_node(get="id", name=first_word, kind=kind,
                        parent=parent_id, section=section)[0]
            except:
                nodes_list.append(Node(first_word, parent=parent_id, kind=kind, legit=legit, section=section))
                node_id = search_node(get="id", name=first_word, kind=kind,
                        parent=parent_id, section=section)[0]
                update_node(parent_id, add_childs=[node_id])
            update_node(node_id, legit=legit, section=section)

            if called_by and node_id != called_by:
                update_node(node_id, add_called_by=[called_by])
                update_node(called_by, add_call=[node_id])
            else:
                mixin_node_id = search_node(get="id", name=[x.from_file() for x in matching_actions][0])[0]
                target_node_id = search_node(get="id", name=first_word, parent=mixin_node_id)[0]
                if node_id != target_node_id:
                    update_node(node_id, add_call=[target_node_id])
                    update_node(target_node_id, add_called_by=[node_id])

        elif re.search(regex_dict["is_event"], item):
            legit = True
            kind = "event"
            log(rf"{padding :>{width}}\[{first_word}] is an event")
            parent_id = search_node(get="id", name=manifest_name, kind="manifest")[0]
            nodes_list.append(Node(first_word, parent=parent_id, kind=kind, legit=legit, section=section))
        elif degree > previous_degree and previous_item_id != 0:
            legit = True
            kind = "parameter"
            if first_word:
                log(rf"{padding :>{width}}\[{first_word}] is a parameter")
        else:
            legit = False
            to_break = True
            kind = "action"
            log(rf"{padding :>{width}}\[{first_word}] is an action not defined anywhere !")
            parent_id = search_node(get="id", name=manifest_name, kind="manifest")[0]
            if not search_node(name=first_word, kind=kind, parent=parent_id, section=section):
                nodes_list.append(Node(first_word, parent=parent_id, kind=kind, legit=legit, section=section))

            if called_by:
                node_id = search_node(get="id", name=first_word, kind=kind,
                        parent=parent_id, section=section)[0]

                if node_id != called_by:
                    update_node(node_id, add_called_by=[called_by])
                    update_node(called_by, add_call=[node_id])

        return legit, to_break

    elif isinstance(item, list):
        for _, to_crawl in enumerate(item):
            crawl(to_crawl, degree + 1, section=section, manifest_name=manifest_name,
                    previous_degree=degree, called_by=called_by)

    elif isinstance(item, (type(None), bool, int)):
        pass

    else:
        log(f"THAT SHOULD NEVER BE SHOWNED: {type(item)}")


def inspect_manifest(manifest, section):
    log(f"for manifest '{manifest.name()}, section '{section}':")
    manifest_name = manifest.name()
    if section == "onInstall":
        if len(manifest.on_install()) < 1:
            log('no onInstall section')
            return
        for item in manifest.on_install():
            crawl(item, section=section, manifest_name=manifest_name)
    elif section == "actions":
        if manifest.embeded_actions():
            crawl(manifest.embeded_actions(), section=section, manifest_name=manifest_name)
        else:
            log("no actions section")
    elif section == "events":
        if len(manifest.events()) == 0:
            log('no events detected')
        else:
            crawl(manifest.events(), section=section, manifest_name=manifest_name)
    elif section == "mixins":
        for mixin in manifest.mixins():
            crawl_by_manifest(mixin)
    else:
        log("bad section name")


def crawl_by_manifest(name):
    manifest_id = get_manifest_id_by_name(name)
    if not manifest_id and manifest_id != 0:
        return

    for section in ["actions", "events", "onInstall"]:
        inspect_manifest(manifest_list[manifest_id], section)


def graph_by_manifest(name):
    def create_subgraph(in_graph, subgraph, label):
        if not in_graph.get_subgraph(subgraph):
            child_section_subgraph[subgraph] = manifest_subgraph.add_subgraph(
                    name=subgraph,
                    label=label,
                    **graph_attributes[f"section_{section}"]
                    )
        return in_graph.get_subgraph(subgraph)

    try:
        manifest_id = get_manifest_id_by_name(name)
        manifest = manifest_list[manifest_id]
        manifest_node_id = search_node(get="id", name=name, kind="manifest")[0]
    except:
        return False

    manifest_subgraph = graph.add_subgraph(name=f"cluster_manifest_{manifest.name()}", label=f"{manifest.name()}", **graph_attributes["manifest"])

    for mixin in manifest.mixins():
        graph_by_manifest(mixin)

    child_section_subgraph = {}

    for section in ["actions", "events", "onInstall"]:
        subgraph = create_subgraph(manifest_subgraph, f"cluster_{name}_{section}", section)
        childs_from_section = search_node(parent=manifest_node_id, section=section)
        for child in childs_from_section:
            if re.search(regex_dict["is_mixins"], name) and section != "actions":
                continue

            node_name = f"{manifest.name()}_{section}_{child.name()}"
            if isinstance(child.legit(), bool):
                attributes = "action_legit" if child.legit() else "action_not_legit"
            else:
                attributes = "action_legit"

            subgraph.add_node(node_name, label=child.name(), **graph_attributes[attributes])

            if section == "onInstall" and search_node(name=child.name(), parent=child.parent(), section="actions"):
                target_node = f"{manifest.name()}_actions_{child.name()}"
                subgraph.add_edge(node_name, target_node)
            else:
                for target_node_id in child.call():
                    target_node_id_name = nodes_list[target_node_id].name()
                    target_parent_manifest_id = nodes_list[target_node_id].parent()
                    target_parent_manifest_name = nodes_list[target_parent_manifest_id].name()
                    target_node_name = f"{target_parent_manifest_name}_actions_{target_node_id_name}"
                    graph.add_edge(node_name, target_node_name)


def graph_manifest(name: str, output=None, to_terminal=False):
    if re.search(regex_dict["is_mixins"], name):
        other_mixins = [x.name() for x in manifest_list if re.search(regex_dict["is_mixins"], x.name()) and x.name() != name]
        for mixin in other_mixins:
            crawl_by_manifest(mixin)
            graph_by_manifest(mixin)

    crawl_by_manifest(name)
    graph_by_manifest(name)

    mixins_list = [node for node in graph.nodes() if re.search(regex_dict["is_mixins"], node.name) and not re.search(rf"{name}", node.name)]
    for node in mixins_list:
        node_edges_list = [edge for edge in graph.edges() if node.name in edge]

        if not node_edges_list:
            graph.delete_node(node.get_name())

    if output:
        graph.write(output)
        log("")
        log(f"Output for file {name} is done to {output}")
    elif to_terminal:
        print("ICI")
        log("")
        graph.write()


def display_not_legit(items_list):
    log("")
    for item_id in items_list:
        item = nodes_list[item_id]
        parent_id = item.parent()
        parent = nodes_list[parent_id]
        log(f"'{item.name()}' from {parent.name()} isn't defined", quiet=False, not_legit=True)


def check_for_duplicate_action_in_mixins():
    mixins_list = [x.name() for x in manifest_list if "mixins" in x.kind()]
    actions = {}
    for mixin in mixins_list:
        actions[mixin] = {x.name() for x in actions_list if x.from_file() == mixin}

    all_actions = [action for mixin in actions.keys() for action in actions[mixin]]

    duplicated = {action for action in all_actions if all_actions.count(action) > 1}

    for action in duplicated:
        from_file = [file for file in actions.keys() if action in actions[file]]
        log(f"'{action}' is duplicated: {from_file}", not_legit=True)

    return duplicated


class InternalShell(cmd2.Cmd):
    def __init__(self):
        super().__init__(allow_cli_args=False, include_py=True)
        self.prompt = "deps> "
        self.self_in_py = True

        self.file = "./packages/jahia/augmented-search-install.yml"
        self.add_settable(cmd2.Settable('file', str, 'file to check', self))

        self.output = "output.dot"
        self.add_settable(cmd2.Settable('output', str, 'where to output dot', self))

        self.quiet = False
        self.add_settable(cmd2.Settable('quiet', bool, 'be quiet', self))

        self.console = False
        self.add_settable(cmd2.Settable('console', bool, 'output generated dot to console', self))

    @cmd2.with_argparser(graph_manifest_parser)
    def do_graph(self, opts):
        """Generate dot format of actions dependencies tree for a given manifest"""
        graph_manifest(opts.file, opts.output, to_terminal=opts.console)

    @cmd2.with_argparser(graph_manifest_parser)
    def do_check(self, opts):
        """check actions dependencies or a given manifest"""
        crawl_by_manifest(opts.file)
        not_legit = search_node(get="id", legit=False)
        if not_legit:
            display_not_legit(not_legit)

    def do_check_mixins_duplicates(self, opts):
        """check for duplicated actions in mixins files"""
        check_for_duplicate_action_in_mixins()

    complete_graph = cmd2.Cmd.path_complete
    complete_check = cmd2.Cmd.path_complete


def pretty_search_result(result: list, title=""):
    columns = [
            "id",
            "name",
            "kind",
            "section",
            "call",
            "called_by",
            "parent",
            "childs",
            "legit",
            ]
    table = Table(title=title, box=None)

    for column in columns:
        table.add_column(column)

    rows = []
    for item in result:
        if "id" not in item.keys():
            item["id"] = search_node(get="id", name=item["name"], parent=item["parent"], kind=item["kind"])[0]
        str_item = []
        for column in columns:
            value = item[column]
            if isinstance(value, list):
                if not value:
                    value = None
                else:
                    value = ",".join([str(x) for x in value])
            elif isinstance(value, bool):
                if value:
                    value = "true"
                else:
                    value = "false"
            elif isinstance(value, int):
                value = str(value)
            str_item.append(value)
        rows.append(str_item)

    for row in rows:
        table.add_row(*row)

    console.print(table)


def check_if_not_legit():
    not_legit = search_node(get="id", legit=False)
    if not_legit:
        display_not_legit(not_legit)
        sys.exit(1)


if __name__ == "__main__":
    SILENT_MODE = False

    with console.status("reading files...", spinner="line"):
        generate_lists()

    if args.command in ["check", "graph"]:
        files = []
        for file in args.file:
            if file.name.startswith("./"):
                files.append(file.name)
                continue
            for manifest in manifest_list:
                if re.search(rf"{file.name}", manifest.name()):
                    files.append(f"./{file.name}")
                    break

    if not args.command:
        pass
    elif args.command == "shell":
        InternalShell = InternalShell()
        sys.exit(InternalShell.cmdloop())
    elif args.command == "graph":
        SILENT_MODE = args.quiet
        with console.status("graphing files...", spinner="line"):
            for file in files:
                graph_manifest(file, None)
        if args.output:
            graph.write(args.output)
        if args.console:
            graph.write()
        check_if_not_legit()
    elif args.command == "check":
        SILENT_MODE = args.quiet
        with console.status("checking files...", spinner="line"):
            for file in files:
                crawl_by_manifest(file)
        check_if_not_legit()
    elif args.command == "mixins_duplicates":
        if check_for_duplicate_action_in_mixins():
            sys.exit(1)
    elif args.command == "search":
        criteria_dict = vars(args)
        for criteria in ["childs", "call", "called_by"]:
            if criteria and criteria_dict[criteria] is not None:
                criteria_dict[criteria] = [int(x) for x in criteria_dict[criteria].split(",")]
        if args.not_legit:
            criteria_dict["legit"] = False
        else:
            criteria_dict["legit"] = True

        SILENT_MODE = True

        for i in track(range(len(manifest_list)), description="Building data..."):
            crawl_by_manifest(manifest_list[i].name())

        result = search_node(**criteria_dict)
        result_with_id = []
        for item in result:
            attributes = item.get_all_attributes()
            attributes["id"] = nodes_list.index(item)
            if args.id and int(args.id) != attributes["id"]:
                continue
            result_with_id.append(attributes)

        log("")
        if result_with_id:
            pretty_search_result(result_with_id)
        else:
            log("No match")
