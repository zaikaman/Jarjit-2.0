import hashlib
from dataclasses import dataclass
from typing import Optional

from browser_use.dom.views import DOMElementNode


@dataclass
class HashedDomElement:
	"""
	Hash of the dom element to be used as a unique identifier
	"""

	branch_path_hash: str
	attributes_hash: str
	# text_hash: str


@dataclass
class DOMHistoryElement:
	tag_name: str
	xpath: str
	highlight_index: Optional[int]
	entire_parent_branch_path: list[str]
	attributes: dict[str, str]
	shadow_root: bool = False

	def to_dict(self) -> dict:
		return {
			'tag_name': self.tag_name,
			'xpath': self.xpath,
			'highlight_index': self.highlight_index,
			'entire_parent_branch_path': self.entire_parent_branch_path,
			'attributes': self.attributes,
			'shadow_root': self.shadow_root,
		}


class HistoryTreeProcessor:
	""" "
	Operations on the DOM elements

	@dev be careful - text nodes can change even if elements stay the same
	"""

	@staticmethod
	def convert_dom_element_to_history_element(dom_element: DOMElementNode) -> DOMHistoryElement:
		parent_branch_path = HistoryTreeProcessor._get_parent_branch_path(dom_element)
		return DOMHistoryElement(
			dom_element.tag_name,
			dom_element.xpath,
			dom_element.highlight_index,
			parent_branch_path,
			dom_element.attributes,
			dom_element.shadow_root,
		)

	@staticmethod
	def find_history_element_in_tree(
		dom_history_element: DOMHistoryElement, tree: DOMElementNode
	) -> Optional[DOMElementNode]:
		hashed_dom_history_element = HistoryTreeProcessor._hash_dom_history_element(
			dom_history_element
		)

		def process_node(node: DOMElementNode):
			if node.highlight_index is not None:
				hashed_node = HistoryTreeProcessor._hash_dom_element(node)
				if hashed_node == hashed_dom_history_element:
					return node
			for child in node.children:
				if isinstance(child, DOMElementNode):
					result = process_node(child)
					if result is not None:
						return result
			return None

		return process_node(tree)

	@staticmethod
	def compare_history_element_and_dom_element(
		dom_history_element: DOMHistoryElement, dom_element: DOMElementNode
	) -> bool:
		hashed_dom_history_element = HistoryTreeProcessor._hash_dom_history_element(
			dom_history_element
		)
		hashed_dom_element = HistoryTreeProcessor._hash_dom_element(dom_element)

		return hashed_dom_history_element == hashed_dom_element

	@staticmethod
	def _hash_dom_history_element(dom_history_element: DOMHistoryElement) -> HashedDomElement:
		branch_path_hash = HistoryTreeProcessor._parent_branch_path_hash(
			dom_history_element.entire_parent_branch_path
		)
		attributes_hash = HistoryTreeProcessor._attributes_hash(dom_history_element.attributes)

		return HashedDomElement(branch_path_hash, attributes_hash)

	@staticmethod
	def _hash_dom_element(dom_element: DOMElementNode) -> HashedDomElement:
		parent_branch_path = HistoryTreeProcessor._get_parent_branch_path(dom_element)
		branch_path_hash = HistoryTreeProcessor._parent_branch_path_hash(parent_branch_path)
		attributes_hash = HistoryTreeProcessor._attributes_hash(dom_element.attributes)
		# text_hash = DomTreeProcessor._text_hash(dom_element)

		return HashedDomElement(branch_path_hash, attributes_hash)

	@staticmethod
	def _get_parent_branch_path(dom_element: DOMElementNode) -> list[str]:
		parents: list[DOMElementNode] = []
		current_element: DOMElementNode = dom_element
		while current_element.parent is not None:
			parents.append(current_element)
			current_element = current_element.parent

		parents.reverse()

		return [parent.tag_name for parent in parents]

	@staticmethod
	def _parent_branch_path_hash(parent_branch_path: list[str]) -> str:
		parent_branch_path_string = '/'.join(parent_branch_path)
		return hashlib.sha256(parent_branch_path_string.encode()).hexdigest()

	@staticmethod
	def _attributes_hash(attributes: dict[str, str]) -> str:
		attributes_string = ''.join(f'{key}={value}' for key, value in attributes.items())
		return hashlib.sha256(attributes_string.encode()).hexdigest()

	@staticmethod
	def _text_hash(dom_element: DOMElementNode) -> str:
		""" """
		text_string = dom_element.get_all_text_till_next_clickable_element()
		return hashlib.sha256(text_string.encode()).hexdigest()
