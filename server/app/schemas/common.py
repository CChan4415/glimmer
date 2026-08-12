import uuid
from datetime import datetime

from pydantic import BaseModel


# ── Contacts ──

class ContactImportItem(BaseModel):
    name: str
    phone: str | None = None
    group: str = "ungrouped"


class ContactBatchImport(BaseModel):
    contacts: list[ContactImportItem]


class ContactCreate(BaseModel):
    name: str
    phone: str | None = None
    group: str = "ungrouped"
    tags: list[str] = []


class ContactUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    group: str | None = None
    tags: list[str] | None = None
    last_contacted_at: datetime | None = None


class MatchedUserOut(BaseModel):
    id: str
    nickname: str | None


class ContactOut(BaseModel):
    id: str
    name: str
    phone_hash: str | None = None
    group: str
    is_manual: bool
    tags: list[str] = []
    last_contacted_at: datetime | None = None
    matched_user: MatchedUserOut | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ContactListOut(BaseModel):
    data: list[ContactOut]
    pagination: dict


# ── Network (2nd degree) ──

class SecondDegreeNode(BaseModel):
    id: str
    display_name: str
    group: str | None = None
    mutual_count: int = 0
    is_registered: bool = False


class SecondDegreeOut(BaseModel):
    data: list[SecondDegreeNode]
    meta: dict
    pagination: dict


# ── Graph ──

class GraphNode(BaseModel):
    id: str
    name: str | None = None
    group: str
    is_registered: bool = False
    is_matched: bool = False
    display_name: str
    tags: list[str] | None = None
    degree: int = 1


class GraphEdge(BaseModel):
    source: str
    target: str


class GraphStats(BaseModel):
    total_contacts: int
    family: int = 0
    colleague: int = 0
    friend: int = 0
    ungrouped: int = 0
    by_tag: dict = {}


class GraphOut(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    stats: GraphStats


# ── Privacy ──

class PrivacySettingsOut(BaseModel):
    allow_contacts_visible: bool
    allow_appear_in_network: bool
    display_level: str
    nickname: str | None


class PrivacySettingsUpdate(BaseModel):
    allow_contacts_visible: bool | None = None
    allow_appear_in_network: bool | None = None
    display_level: str | None = None


class NicknameUpdate(BaseModel):
    nickname: str


# ── Account ──

class AccountOut(BaseModel):
    id: str
    phone: str
    auth_methods: list[str]
    created_at: datetime


class DeleteAccountRequest(BaseModel):
    confirmation: str


# ── Tags ──

class TagPresetOut(BaseModel):
    tag: str
    category: str | None = None
