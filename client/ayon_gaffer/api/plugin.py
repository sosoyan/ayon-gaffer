import sys
import json

from ayon_core.lib import Logger
from ayon_core.pipeline import (AYON_CONTAINER_ID, load)

import Gaffer


log = Logger.get_logger(__name__)

JSON_PREFIX = "JSON:::"

def read(node):
    """Read all 'user' custom data on the node"""
    if "user" not in node:
        # No user attributes
        return {}
    return {
        plug.getName(): plug.getValue() for plug in node["user"]
    }

def imprint_container(node: Gaffer.Node,
                      name: str,
                      namespace: str,
                      context: dict,
                      loader: str = None):
    """Imprint a Loader with metadata

    Containerisation enables a tracking of version, author and origin
    for loaded assets.

    Arguments:
        node (Gaffer.Node): The node in Gaffer to imprint as container,
            usually a node loaded by a Loader.
        name (str): Name of resulting assembly
        namespace (str): Namespace under which to host container
        context (dict): Asset information
        loader (str, optional): Name of loader used to produce this container.

    Returns:
        None

    """
    data = {
        "schema": "openpype:container-2.0",
        "id": AYON_CONTAINER_ID,
        "name": str(name),
        "namespace": str(namespace),
        "loader": str(loader),
        "representation": str(context["representation"]["id"]),
    }
    imprint(node, data)

def imprint(node: Gaffer.Node,
            data: dict,
            section: str = "Ayon"):
    """Store and persist data on a node as `user` data.

    Args:
        node (Gaffer.Node): The node to store the data on.
            This can also be the workfile's root script node.
        data (dict): The key, values to store.
            Any `dict` values will be treated as JSON data and stored as
            string with `JSON:::` as a prefix to the value.
        section (str): Used to register the plug into a subsection in
            the user data allowing them to group data together.

    Returns:

    """

    FLAGS = Gaffer.Plug.Flags.Default | Gaffer.Plug.Flags.Dynamic

    for key, value in data.items():
        # Dict to JSON
        if isinstance(value, dict):
            value = json.dumps(value)
            value = f"{JSON_PREFIX}{value}"

        if key in node["user"]:
            # Set existing attribute
            try:
                if value is None:
                    value = ""
                print(value)
                node["user"][key].setValue(value)
                continue
            except Exception:
                # If an exception occurs then we'll just replace the key
                # with a new plug (likely types have changed)
                log.warning("Unable to set %s attribute %s to value %s (%s). "
                            "Likely there is a value type mismatch. "
                            "Plug will be replaced.",
                            node.getName(), key, value, type(value),
                            exc_info=sys.exc_info())
                pass

        if value is None:
            value = "<None>"

        # Generate new plug with value as default value
        if isinstance(value, str):
            plug = Gaffer.StringPlug(key, defaultValue=value, flags=FLAGS)
        elif isinstance(value, bool):
            plug = Gaffer.BoolPlug(key, defaultValue=value, flags=FLAGS)
        elif isinstance(value, float):
            plug = Gaffer.FloatPlug(key, defaultValue=value, flags=FLAGS)
        elif isinstance(value, int):
            plug = Gaffer.IntPlug(key, defaultValue=value, flags=FLAGS)
        else:
            raise TypeError(
                f"Unsupported value type: {type(value)} -> {value}"
            )

        if section:
            Gaffer.Metadata.registerValue(plug, "layout:section", section)

        node["user"][key] = plug

class CreatorImprintReadMixin:
    """Mixin providing _read and _imprint methods to be used by Creators."""

    attr_prefix = "ayon_"
    op_attr_prefix = "openpype_"

    def _read(self, node: Gaffer.Node) -> dict:
        all_user_data = read(node)

        # Consider only data with the special attribute prefix
        # and strip off the prefix as for the resulting data

        ayon_data = {}
        for key, value in all_user_data.items():

            if key.startswith(self.attr_prefix):
                prefix_len = len(self.attr_prefix)
            elif key.startswith(self.op_attr_prefix):
                prefix_len = len(self.op_attr_prefix)
            else:
                continue

            if isinstance(value, str) and value.startswith(JSON_PREFIX):
                value = value[len(JSON_PREFIX):]  # strip off JSON prefix
                value = json.loads(value)
            elif isinstance(value, str) and value == "<None>":
                value = None

            key = key[prefix_len:]      # strip off prefix
            ayon_data[key] = value

        ayon_data["instance_id"] = node.fullName()

        if "creator_identifier" in ayon_data.keys():
            # if we have an openpye creator identifier, let's temporarily
            # make it an ayon one.
            creator_id = ayon_data["creator_identifier"]
            if ".openpype." in creator_id:
                ayon_data["creator_identifier"] = creator_id.replace(
                    ".openpype.", ".ayon.")

        return ayon_data

    def _imprint(self, node: Gaffer.Node, data: dict):
        # Instance id is the node's unique full name so we don't need to
        # imprint as data. This makes it so that duplicating a node will
        # correctly detect it as a new unique instance.
        data.pop("instance_id", None)

        # Prefix all keys
        ayon_data = {}
        for key, value in data.items():
            key = f"{self.attr_prefix}{key}"
            ayon_data[key] = value

        imprint(node, ayon_data)

class GafferLoaderBase(load.LoaderPlugin):
    pass

