"""
Action models and Locator representations for computer-use operations.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ActionType(str, Enum):
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    EXTRACT = "extract"
    WAIT = "wait"
    FINISH = "finish"
    ESCALATE = "escalate"


class LocatorStrategyType(str, Enum):
    ROLE_NAME = "role_name"
    LABEL = "label"
    TEXT = "text"
    CSS = "css"
    XPATH = "xpath"


class Locator(BaseModel):
    """
    Multi-strategy locator supporting robust fallbacks across layout shifts.
    Priority order: role_name -> label -> text -> css -> xpath
    """
    role_name: Optional[Dict[str, str]] = Field(
        default=None, 
        description="Dictionary with 'role' and 'name' keys, e.g. {'role': 'button', 'name': 'EXECUTE SEARCH PROTOCOL'}"
    )
    label: Optional[str] = Field(default=None, description="Form control label text")
    text: Optional[str] = Field(default=None, description="Exact or partial text content of element")
    css: Optional[str] = Field(default=None, description="CSS selector string")
    xpath: Optional[str] = Field(default=None, description="XPath query string")


class Action(BaseModel):
    """
    Structured action emitted by Discovery Agent or stored in Capability Artifact.
    """
    action_type: ActionType
    locator: Optional[Locator] = None
    value: Optional[str] = Field(default=None, description="Value to type, URL to navigate, or key to extract")
    description: str = Field(..., description="Human-readable description of what this action does")


class ElementInfo(BaseModel):
    """
    Serializable summary of an interactive DOM element observed on the page.
    """
    tag: str
    role: Optional[str] = None
    name: Optional[str] = None
    label: Optional[str] = None
    text: Optional[str] = None
    css_selector: str
    is_interactive: bool = True


class Observation(BaseModel):
    """
    Observed state of a computer surface at a single moment in time.
    """
    url: str
    title: str
    interactive_elements: List[ElementInfo] = Field(default_factory=list)
    accessibility_tree_text: str = ""
    visible_text_summary: str = ""
    screenshot_base64: Optional[str] = None
