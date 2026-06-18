from core.action_base.base_action import BaseAction

from shared.tools.flow_loader import FlowLoader
from config.images import ImagePaths
from core.action_executor.desktop_executor import DesktopExecutor


class ActionBase(BaseAction):

    def __init__(
        self,
        variables_base,
        contexto,
        flow_name,
    ):

        super().__init__(
            variables_base,
            contexto,
        )

        self.flow_data = FlowLoader.load(
            flow_name
        )

        image_map = ImagePaths.get_all()

        self.executor = DesktopExecutor(
            flow=self.flow_data,
            image_map=image_map,
            variables_base=self.variables_base,
            contexto=self.contexto,
        )
        self.basic_tools = self.executor.basic_tools
        self.clicker = self.executor.clicker
        self.app_tools = self.executor.app_tools
        self.extractor = self.executor.extractor