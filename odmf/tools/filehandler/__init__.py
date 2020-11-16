from typing import Callable

class FileHandler:

    def __init__(
            self,
            content: str,
            render: Callable=None,
            edit: Callable=None,
            import_: Callable=None
    ):
        self.content = content
        self.render = render
        self.edit = edit
        self.import_ = import_

    def render(self):
        """
        Creates html literals from the content
        """
        pass

    def edit(self):
        """
        Returns a html form to edit the content
        """
        pass

    def import_(self):
        """
        Performs an import action
        """
        pass
