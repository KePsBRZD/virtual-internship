class PerevalExistsException(Exception):
    def __init__(self, id: int):
        self.id = id


class EmailNotExistsException(Exception):
    def __init__(self, email: str):
        self.email = email