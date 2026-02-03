"""Data models for the procurement bot."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass
class UserProfile:
    company_name: str
    inn: str
    kpp: str
    ogrn: str
    bank_name: str
    bank_account: str
    correspondent_account: str
    bik: str
    address: str
    contact_person: str
    email: str
    phone: str
    keywords: List[str] = field(default_factory=list)


@dataclass
class LotRecord:
    lot_id: str
    title: str
    platform: str
    url: str
    published_at: str
    found_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "новый"
