from typing import Literal, Optional

from pydantic import BaseModel


# Action Input Models
class SearchGoogleAction(BaseModel):
	query: str


class GoToUrlAction(BaseModel):
	url: str


class ClickElementAction(BaseModel):
	index: int
	num_clicks: int = 1
	xpath: Optional[str] = None


class InputTextAction(BaseModel):
	index: int
	text: str
	xpath: Optional[str] = None


class DoneAction(BaseModel):
	text: str


class SwitchTabAction(BaseModel):
	page_id: int


class OpenTabAction(BaseModel):
	url: str


class ExtractPageContentAction(BaseModel):
	value: Literal['text', 'markdown', 'html'] = 'text'


class ScrollAction(BaseModel):
	amount: Optional[int] = None  # The number of pixels to scroll. If None, scroll down/up one page
