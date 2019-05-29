import os
import json
import logging
import distutils.spawn
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.item.SmallResultItem import SmallResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.RunScriptAction import RunScriptAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction

logging.basicConfig()
logger = logging.getLogger(__name__)

global usage_cache
usage_cache = {}

# Usage tracking
script_directory = os.path.dirname(os.path.realpath(__file__))
usage_db = os.path.join(script_directory, "usage.json")
if os.path.exists(usage_db):
    with open(usage_db, 'r') as db:
        # Read JSON string
        raw = db.read()
        # JSON to dict
        usage_cache = json.loads(raw)

# Initialize items cache and x2goclient sessions file path
x2goclient_bin = ""
# Locate x2goclient profiles and binary
x2go_sessions_path = ["{}/.x2goclient/sessions".format(os.environ.get('HOME'))]
x2goclient_bin = distutils.spawn.find_executable('x2goclient')
# This extension is useless without x2goclient
if x2goclient_bin is None or x2goclient_bin == "":
    logger.error("x2goclient executable path could not be determined")
    exit()
# Check if x2goclient sessions file exists
x2go_sessions_path_exists = None
# Check default paths first
if os.path.isfile(x2go_sessions_path):
    x2go_sessions_path_exists = True


class x2goclientExtension(Extension):
    def __init__(self):

        super(x2goclientExtension, self).__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())

    def list_sessions(self, query):
        items = []
        with open('/home/bryan/.x2goclient/sessions') as lines:
            for line in lines:
                if line.startswith('host=') or line.startswith('name='):
                    line = line.rstrip()
                    line = line.split('=',1)
                    item = line[1]
                    items.append(item)
        it_items = iter(items)
        sessions = list(zip(it_items, it_items))
        for session in sessions:
            host = session[0]
            name = session[1]
            # Search for query inside filename and profile description
            # Multiple strings can be used to search in description
            # all() is used to achieve a AND search (include all keywords)
            keywords = query.split(" ")
            # if (query in base.lower()) or (query in desc.lower()):
            if (query.lower() in host.lower()) or (query.lower() in name.lower()):
                items_cache.append(create_item(host, name))

        items_cache = sorted(items_cache, key=sort_by_usage, reverse=True)
        return items_cache



class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        global x2go_sessions_path
        if extension.preferences["sessions"] is not "" or not x2go_sessions_path:
            # Tilde (~) won't work alone, need expanduser()
            x2go_sessions_path = os.path.expanduser(extension.preferences["sessions"])
        # pref_sessions_path = extension.preferences['sessions']
        logger.debug("x2goclient sessions path: {}".format(x2go_sessions_path))
        # Get query
        term = (event.get_argument() or "").lower()
        # Display all items when query empty
        sessions_list = extension.list_sessions(term)
        return RenderResultListAction(sessions_list[:8])


class ItemEnterEventListener(EventListener):
    def on_event(self, event, extension):
        global usage_cache
        # Get query
        data = event.get_data()
        on_enter = data["id"]
        # The profilefile name is the ID
        base = os.path.basename(on_enter)
        b = os.path.splitext(base)[0]
        # Check usage and increment
        if b in usage_cache:
            usage_cache[b] = usage_cache[b]+1
        else:
            usage_cache[b] = 1
        # Update usage JSON
        with open(usage_db, 'w') as db:
            db.write(json.dumps(usage_cache, indent=2))
        return RunScriptAction('#!/usr/bin/env bash\n{} --session {}\n'.format(x2goclient_bin, on_enter), None).run()


def create_item(host, name):
    return ExtensionResultItem(
            name=name,
            description=host,
            icon="images/x2goclient.svg",
            on_enter=ExtensionCustomAction(
                 {"id": name})
            )


def sort_by_usage(i):
    global usage_cache
    # Convert item name to ID format
    j = i._name.lower()
    # Return score according to usage
    if j in usage_cache:
        return usage_cache[j]
    # Default is 0 (no usage rank / unused)
    return 0



if __name__ == "__main__":
    x2goclientExtension().run()
