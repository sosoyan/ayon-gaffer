import re

import ayon_api
from ayon_core.pipeline.context_tools import get_current_task_entity
from ayon_core.pipeline import (
    AutoCreator,
    CreatedInstance)

from ayon_gaffer.api.plugin import CreatorImprintReadMixin

from ayon_gaffer.api.lib import GafferScript


class GafferWorkfileCreator(AutoCreator, CreatorImprintReadMixin):
    identifier = "io.ayon.creators.gaffer.workfile"
    product_type = "workfile"
    label = "Workfile"
    icon = "fa5.file"

    default_variant = ""

    create_allow_context_change = False

    attr_prefix = "ayon_workfile_"

    def collect_instances(self):

        if not GafferScript.node:
            return

        data = self._read(GafferScript.node)
        if not data or data.get("creator_identifier") != self.identifier:
            return

        instance = CreatedInstance(
            product_type=self.product_type,
            product_name=data["productName"],
            data=data,
            creator=self
        )
        instance.transient_data["node"] = GafferScript.node
        self._add_instance_to_context(instance)

    def update_instances(self, update_list):
        for created_inst, _changes in update_list:
            node = created_inst.transient_data["node"]

            # Imprint data into the script root
            data = created_inst.data_to_store()
            self._imprint(node, data)

    def create(self, options=None):

        if not GafferScript.node:
            self.log.error("Unable to find current script")
            return

        existing_instance = None
        for instance in self.create_context.instances:
            if instance.product_type == self.product_type:
                existing_instance = instance
                break

        self.log.info(f"Existing {existing_instance}")

        project_name = self.create_context.get_current_project_name()
        folder_path = self.create_context.get_current_folder_path()
        if hasattr(self.create_context, 'get_current_workfile_comment'):
            wf_comment = self.create_context.get_current_workfile_comment()
            wf_comment = re.sub(
                '([a-zA-Z])', lambda x: x.groups()[0].upper(), wf_comment, 1)
        else:
            wf_comment = "Main"
        task_name = self.create_context.get_current_task_name()
        host_name = self.create_context.host_name

        if existing_instance is None:
            existing_instance_folder = None
        else:
            existing_instance_folder = existing_instance.get("folderPath")

        if existing_instance is None:
            folder_doc = ayon_api.get_folder_by_path(project_name, folder_path)
            task_entity = get_current_task_entity()
            product_name = self.get_product_name(
                project_name, folder_doc, task_entity,
                wf_comment, host_name
            )
            data = {
                "task": task_name,
                "variant": wf_comment
            }
            data["folderPath"] = folder_path
            data["workfile_comment"] = wf_comment

            data.update(self.get_dynamic_data(
                self.default_variant, task_name, folder_doc,
                project_name, host_name, None
            ))

            new_instance = CreatedInstance(
                self.product_type, product_name, data, self
            )
            new_instance.transient_data["node"] = GafferScript.node
            self._add_instance_to_context(new_instance)

        elif (
            existing_instance_folder != folder_path
            or existing_instance["task"] != task_name
            or existing_instance.get("workfile_comment", "") != wf_comment
        ):
            folder_doc = ayon_api.get_folder_by_path(project_name, folder_path)
            task_entity = get_current_task_entity()
            product_name = self.get_product_name(
                project_name, folder_doc, task_entity,
                wf_comment, host_name
            )
            self.log.info(f"GOT NEW PRONAME {product_name}")
            existing_instance["folderPath"] = folder_path
            existing_instance["task"] = task_name
            existing_instance["productName"] = product_name
            existing_instance["workfile_comment"] = wf_comment
