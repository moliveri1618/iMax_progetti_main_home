from sqlmodel import SQLModel, Field

class Item(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    type: str = Field(..., nullable=False)
    owner: str = Field(..., nullable=False)
