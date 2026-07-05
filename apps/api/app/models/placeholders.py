from pydantic import BaseModel


PLACEHOLDER_NOTE = "No real AI logic or external integrations implemented yet."


class PlaceholderResponse(BaseModel):
    endpoint: str
    status: str = "placeholder"
    note: str = PLACEHOLDER_NOTE

