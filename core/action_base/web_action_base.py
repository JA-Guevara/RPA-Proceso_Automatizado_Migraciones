from core.action_base.base_action import BaseAction


class WebActionBase(BaseAction):

    def __init__(
        self,
        variables_base,
        contexto=None,
    ):

        super().__init__(
            variables_base,
            contexto,
        )