import re
from typing import Optional

import ayon_api
from ayon_core.lib import (Logger, StringTemplate)
from ayon_core.pipeline import context_tools
from ayon_core.pipeline import (get_current_project_name,
                                get_current_folder_path,
                                get_current_task_name)

import Gaffer
import GafferUI
import GafferScene


log = Logger.get_logger(__name__)

def make_box(name: str,
             inputs: list = ["in"],
             outputs: list = ["out"],
             description: Optional[str] = None,
             hide_add_buttons: bool = True,
             connect_passthrough: bool = False) -> Gaffer.Box:
    """Create a Box node with BoxIn and BoxOut nodes

    Note:
        The box is not added as child anywhere - to have it visually
        appear make sure to call e.g. `parent.addChild(box)`

    Arguments:
        name (str): The name to give the box.
        inputs (list): List of input child plugs to add, an empty list creates
            no inputs
        outputs (list): List of child output plugs to add, empty list
            creates no output.
        description (Optional[str]): A description to register for the box.
        hide_add_buttons (bool): Whether the add buttons on the box
            node should be hidden or not. By default, this will hide them.
        connect_passthrough (bool): Should the first input be connected to the
            first outputs passthrough plug?

    Returns:
        Gaffer.Box: The created box

    """

    box = Gaffer.Box(name)

    if description:
        Gaffer.Metadata.registerValue(box, 'description', description)

    for inp in inputs:
        box_in = Gaffer.BoxIn(f"BoxIn_{inp}")
        box.addChild(box_in)
        box_in.setup(GafferScene.ScenePlug('out'))
        # set the newest plug name to the input name
        box.children()[-1].setName(inp)

    for outp in outputs:
        box_out = Gaffer.BoxOut(f"BoxOut_{outp}")

        box.addChild(box_out)
        box_out.setup(GafferScene.ScenePlug("in",))
        box.children()[-1].setName(outp)

    if hide_add_buttons:
        for key in [
            'noduleLayout:customGadget:addButtonTop:visible',
            'noduleLayout:customGadget:addButtonBottom:visible',
            'noduleLayout:customGadget:addButtonLeft:visible',
            'noduleLayout:customGadget:addButtonRight:visible',
        ]:
            Gaffer.Metadata.registerValue(box, key, False)

    if connect_passthrough and len(inputs) > 0 and len(outputs) > 0:
        first_input = box.children(Gaffer.BoxIn)[0]
        first_output = box.children(Gaffer.BoxOut)[0]
        first_output["passThrough"].setInput(first_input["out"])

    return box

def get_next_valid_name(template, script_node):
    """
    Find the next number to replace a _##_ part of templates with.
    Given a template containing a single block of ## this function
    will traverse the nodegraph to find nodes with the same name (but a
    diferent number) and construct a unique name with the next highest number.

    Example:
        given the template 'node_###' and we already have 'node_001' and
            'node_002' in the scene, this function will return 'node_003'

    If no node is found with the name pattern 1 will be used.

    Arguments:
        template (str): The template string to format.
        script_node (Gaffer.ScriptNode): The script scriptNode
    """
    res = re.search(r'([a-zA-Z0-9_]*)(#+)([a-zA-Z0-9_]*)', template)
    if res is not None:
        print(res.group(1), res.group(2), res.group(3))
        head = res.group(1)
        padding = res.group(2)
        tail = res.group(3)
    else:
        head = template
        padding = ""
        tail = ""
        new_number = ""

    if padding:
        pad_len = len(padding)
        ex_names = []
        for child in script_node.children():
            if re.match(f"{head}.*{tail}", child.getName()):
                ex_names.append(child.getName())
        ex_names.sort(reverse=True)
        if len(ex_names) == 0:
            next_number = 1
        else:
            last_name = ex_names[0]

            res = re.search(r'(.*)_*(\d+)(.*)', last_name)
            if res is not None:
                next_number = int(res.group(2)) + 1
        new_number = str(next_number).zfill(pad_len)

    return f"{head}{new_number}{tail}"

def create_sub_groups(parent, sub_groups):
    '''
    Given a parent box node and a list of group names this function adds
    GafferScene.Group nodes to the box, and returns them in the same order
    the sub_groups were in.

    This also adds bool plugs to the box where you can disable each group node
    The labels are concatenated with their preceding groups. Example:
        Given the sub_groups ['a','b','c']:
        'Enable /a' would disable or enable the ['a'] group node
        'Enable /a/b' would disable or enable the ['b'] group node
        'Enable /a/b/c' would disable or enable the ['c'] group node
    This function is mainly here to help make_scene_box function. But who knows
    maybe one day we'll get some use out of it.

    Arguments:
        parent (Gaffer.Box): The parent box, currently there is nothing that
            checks if this is actually a box node.
        sub_groups: list[str]: a list of groups to create, typically the result
            of "/a/b/c".split("/")

    Returns:
        list[GafferScene.Group]: The list of newly created gaffer group nodes.
    '''
    group_nodes = []
    for idx, grp in enumerate(sub_groups):
        print(f"** {grp} **")
        subs = "/".join(sub_groups[0:idx])
        if subs != "":
            subs = f"/{subs}"
        plug_label = f"Enable {subs}/{grp}"
        plug_name = plug_label.replace(" ", "_").replace("/", "_")
        plug = Gaffer.BoolPlug(
                plug_name,
                defaultValue=True,
                flags=Gaffer.Plug.Flags.Default | Gaffer.Plug.Flags.Dynamic,
            )
        parent.addChild(plug)
        Gaffer.Metadata.registerValue(plug, "nodule:type", "")
        Gaffer.Metadata.registerValue(plug, "label", plug_label)

        group_node = GafferScene.Group(f"Group_{grp}")
        group_node["name"].setValue(grp)
        group_node["enabled"].setInput(plug)
        group_nodes.append(group_node)
        parent.addChild(group_node)
    return group_nodes

def make_scene_load_box(
    scene_root,
    name,
    scenegraph_template,
    auxiliary_scengraph_transforms=[]
):
    '''
    Create a Box node to load a scene through. This facilitates placing the
    loaded geometry (or whatever) under certain groups in the scenegraph
    (the `scenegraph_template` parameter). This also supports creating plugs
    for other groups you want underneath the root scenegraph template
    group.

    Arguments:
        scene_root (Gaffer.ScriptNode): The current scriptnode.
        name (str): The name of the box node to be created.
        scengraph_template (str): Where the imported geo will be placed in the
            scenegraph, one template key is expanded, `{node}` which will be
            replaced with the value from the `name` parameter.
            Example: given the scenegraph_template value of '{node}/geo' and
            a name of 'IMPORT_NODE', that will result in the imported geo being
            placed at /IMPORT_NODE/geo/<imported geometry> in the scenegraph.
        auxiliary_scenegraph_transforms (list[str]): a list of other groups
            created under the top created transform, using the example above
            and a parameter value of ['mat', 'fur'] this would result in this
            scenegraph:
                /IMPORT_NODE/geo
                     |------/mat
                     `------/fur

    Returns:
        Gaffer.Box: the created box.

    '''
    box = make_box('scene_load_box', inputs=auxiliary_scengraph_transforms)
    box_name = get_next_valid_name(name, scene_root)
    box.setName(box_name)

    filename_plug = Gaffer.StringPlug(
                "fileName",
                defaultValue="",
                flags=Gaffer.Plug.Flags.Default | Gaffer.Plug.Flags.Dynamic,
            )
    Gaffer.Metadata.registerValue(filename_plug, "nodule:type", "")
    box.addChild(filename_plug)

    # if the scenegraph template has subtransforms main/sub1/sub2 we want to
    # add plugs to disable those groupins, since we _might_ get stuff in that
    # already has thos groups.
    if "/" in scenegraph_template:
        scenegraph_template_parts = scenegraph_template.split("/")
        sc_root_name = scenegraph_template_parts[0]
        sub_groups = scenegraph_template_parts[1:]
    else:
        sc_root_name = scenegraph_template
        sub_groups = []
    print(f"scenegraph template root {sc_root_name}, sub groups: {sub_groups}")

    group_nodes = create_sub_groups(box, sub_groups)
    group_nodes.reverse()
    scene_reader = GafferScene.SceneReader()

    scene_reader["fileName"].setInput(filename_plug)
    scene_reader.setName("Read")
    box.addChild(scene_reader)

    if len(group_nodes) > 0:
        group_nodes[0]["in"][0].setInput(scene_reader["out"])
        current_group = group_nodes[0]
        for group in group_nodes[1:]:
            group["in"][0].setInput(current_group["out"])
            current_group = group
    else:
        print("*****")
        current_group = scene_reader

    merge_scenes = GafferScene.MergeScenes()
    box.addChild(merge_scenes)
    merge_scenes["in"][0].setInput(current_group["out"])

    main_group_name = sc_root_name.format(node=box_name)

    main_group = GafferScene.Group(main_group_name)
    main_group["name"].setValue(main_group_name)
    box.addChild(main_group)
    main_group["in"][0].setInput(merge_scenes["out"])
    box_outs = box.children(Gaffer.BoxOut)
    if len(box_outs) > 0:
        # connect the merge to the output
        box_outs[0]["in"].setInput(main_group["out"])

    # now handle aux transforms
    aux_groups = create_sub_groups(box, auxiliary_scengraph_transforms)
    idx = 1
    for grp, aux in zip(aux_groups, auxiliary_scengraph_transforms):
        grp["in"][0].setInput(box[f"BoxIn_{aux}"]["out"])
        merge_scenes["in"][idx].setInput(grp["out"])
        idx += 1

    return box

def node_name_from_template(template_string, context):
    try:
        from ayon_core.pipeline.template_data import (
            construct_folder_full_name
        )
        use_full_name = True
    except ModuleNotFoundError:
        # couldn't load the rvx custom core function
        use_full_name = False
    folder_entity = context["folder"]
    product_name = context["product"]["name"]
    folder_entity = context["folder"]
    hierarchy_parts = folder_entity["path"].split("/")
    hierarchy_parts.pop(0)
    hierarchy_parts.pop(-1)
    if use_full_name:
        full_name = construct_folder_full_name(
            context["project"]["name"], folder_entity, hierarchy_parts)
    else:
        full_name = folder_entity["name"]
    product_entity = context["product"]
    product_name = product_entity["name"]
    product_type = product_entity["productType"]
    repre_entity = context["representation"]
    repre_cont = repre_entity["context"]
    formatting_data = {
        "asset_name": folder_entity["name"],
        "asset_type": "asset",
        "folder": {
            "name": folder_entity["name"],
            "fullname": full_name,
        },
        "subset": product_name,
        "product": {
            "name": product_name,
            "type": product_type,
        },
        "family": product_type,
        "ext": repre_cont["representation"],
    }
    template = StringTemplate(template_string)
    return template.format(formatting_data)

def retrieve_context():
    """
    Tries to retrieve the saved script context by setting project, folder,
    and task from the Gaffer script variables and updating the context.
    """
    context = GafferScript.node.context()
    attrs = ["ayon:projectName", "ayon:folderPath", "ayon:taskName"]

    project_name, folder_path, task_name = (context.get(i) for i in attrs)

    if all((project_name, folder_path, task_name)):

        folder = ayon_api.get_folder_by_path(project_name, folder_path)
        task = ayon_api.get_task_by_folder_path(project_name,
                                                folder_path,
                                                task_name)

        if all((folder, task)):
            return update_context(folder, task)
        else:
            log.warning(f"Could not retrive saved script context! "
                        f"{project_name}/{folder_path} | {task_name}")

def set_script_settings(script_node, attr):
    """
    Set various settings on a Gaffer script node based on provided attributes.
    """
    frame_start = attr["frameStart"] - attr["handleStart"]
    frame_end = attr["frameEnd"] + attr["handleEnd"]
    fps = attr["fps"]
    res_width = attr["resolutionWidth"]
    res_height = attr["resolutionHeight"]
    pix_aspect = attr["pixelAspect"]

    script_node["frameRange"]["start"].setValue(frame_start)
    script_node["frameRange"]["end"].setValue(frame_end)
    script_node["framesPerSecond"].setValue(fps)

    playback = GafferUI.Playback.acquire(script_node.context())
    playback.setFrameRange(frame_start, frame_end)

    log.info(f"Setting frame range {frame_start}-{frame_end}, {fps}fps")

    display_window = script_node['defaultFormat']["displayWindow"]
    display_window["min"]["x"].setValue(0)
    display_window["min"]["y"].setValue(0)
    display_window["max"]["x"].setValue(res_width)
    display_window["max"]["y"].setValue(res_height)

    default_format = script_node['defaultFormat']
    default_format["pixelAspect"].setValue(pix_aspect)

    log.info(f"Setting default format {res_width}x{res_height}, {pix_aspect}")

def set_script_variables(script_node, attr):
    """
    Sets script variables on the given script
    node based on the provided attributes.
    """
    script_vars = script_node["variables"]
    exists_vars = [i["name"].getValue() for i in script_vars.children()]

    for attrib_name, attrib_value in sorted(attr.items(), reverse=True):

        if attrib_value is not None:

            if isinstance(attrib_value, int):
                plug_type = Gaffer.IntPlug
                default_value = attrib_value

            elif isinstance(attrib_value, float):
                plug_type = Gaffer.FloatPlug
                default_value = attrib_value

            elif isinstance(attrib_value, str):
                plug_type = Gaffer.StringPlug
                default_value = attrib_value
            else:
                log.error(f"Unknown type of {type({attrib_value})} \
                          for {attrib_name} - {attrib_value} skipping!")
                continue

            if not attrib_name.startswith("ayon:"):
                attrib_name = f"ayon:{attrib_name}"

            if attrib_name not in exists_vars:
                script_vars.addChild(
                    Gaffer.NameValuePlug(
                        attrib_name,
                        plug_type(
                            attrib_name,
                            defaultValue=default_value,
                            flags=Gaffer.Plug.Flags.Default | \
                                  Gaffer.Plug.Flags.Dynamic),
                        attrib_name))

            script_vars[attrib_name]["value"].setValue(attrib_value)

def setup_project(script_container=None, script_node=None):
    """
    Sets up global veraiables and projects settings
    for the current Ayon context - project/folder/task
    """
    if all((script_container, script_node)):
        GafferScript.node = script_node
        GafferScript.container = script_container

        if retrieve_context():
            return

    project_name = get_current_project_name()
    folder_path = get_current_folder_path()
    task_name = get_current_task_name()

    GafferSignal.pre_context_changed()(GafferScript.node)

    GafferScript.node["variables"]["projectRootDirectory"]["value"].setValue(
        "${AYON_WORKDIR}")

    task = ayon_api.get_task_by_folder_path(project_name,
                                            folder_path,
                                            task_name)

    tags = task.get("tags")
    task_attrib = task.get("attrib")

    if task_attrib:
        task_attrib.update({"projectName": project_name,
                            "folderPath": folder_path,
                            "taskName": task_name,
                            "tags": " ".join(tags)})

        set_script_settings(GafferScript.node, task_attrib)
        set_script_variables(GafferScript.node, task_attrib)

    GafferSignal.post_context_changed()(GafferScript.node)

def update_context(folder, task=None):
    """
    Update the current context based on the provided folder and task.

    If no task is provided, it attempts to find a task within the folder
    that matches the types "Lookdev" or "Lighting", otherwise picks the first
    task. If no such task is found, it logs a warning and returns False.
    """
    project_name = get_current_project_name()

    if task is None:
        tasks = ayon_api.get_tasks_by_folder_path(project_name, folder["path"])

        if not tasks:
            log.warning(f"No tasks found for folder \
                '{folder['name']}', abort context change!")
            return False

        task = next((t for t in tasks if t["taskType"]
                     in {"Lookdev", "Lighting"}), tasks[0])

    context_tools.change_current_context(folder, task)

    folder_path = get_current_folder_path()
    task_name = get_current_task_name()

    log.info(f"Ayon context has been set to "
             f"{project_name}{folder_path} | {task_name}")

    setup_project()

    return True

class GafferSignal(object):
    """
    A class to handle Gaffer signals for context changes.
    """
    __pre_context_changed = Gaffer.Signal1()
    __post_context_changed = Gaffer.Signal1()

    @classmethod
    def pre_context_changed(cls):
        """
        Method to access the pre-context changed signal.
        """
        return cls.__pre_context_changed

    @classmethod
    def post_context_changed(cls):
        """
        Method to access the post-context changed signal.
        """
        return cls.__post_context_changed

class GafferScript(object):
    """
    GafferScript is a singleton class that manages a node and a container.
    """
    __node = None
    __container = None
    __instance = None

    @property
    def node(self):
        return self.__node

    @node.setter
    def node(self, value):
        self.__node = value

    @property
    def container(self):
        return self.__container

    @container.setter
    def container(self, value):
        self.__container = value

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance
