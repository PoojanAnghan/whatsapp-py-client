"""Location and Poll value objects."""
from __future__ import annotations
from typing import Optional


class Location:
    def __init__(
        self,
        latitude: float,
        longitude: float,
        name: Optional[str] = None,
        address: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        self.latitude = latitude
        self.longitude = longitude
        self.name = name
        self.address = address
        self.url = url
        if name and address:
            self.description = f"{name}\n{address}"
        else:
            self.description = name or address or ""

    def to_dict(self) -> dict:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "name": self.name,
            "address": self.address,
            "url": self.url,
            "description": self.description,
        }


class Poll:
    def __init__(
        self,
        poll_name: str,
        poll_options: list[str],
        allow_multiple_answers: bool = False,
        message_secret: Optional[list[int]] = None,
    ) -> None:
        self.poll_name = poll_name.strip()
        self.poll_options = [
            {"name": opt.strip(), "localId": i} for i, opt in enumerate(poll_options)
        ]
        self.options = {
            "allowMultipleAnswers": allow_multiple_answers,
            "messageSecret": message_secret,
        }
