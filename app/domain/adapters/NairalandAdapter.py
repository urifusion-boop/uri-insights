from app.domain.adapters.BaseAdapter import BaseAdapter


class NairalandAdapter(BaseAdapter):
    def __init__(self, data: dict):
        self.data = data

    def to_lead(self) -> dict:
        return self.data

    def to_post(self) -> dict:
        return self.data

    def to_mention(self) -> dict:
        return self.data
