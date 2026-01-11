from dataclasses import dataclass

@dataclass
class UnifiedEvent:
    tracking_number: str
    carrier: str
    status: str
    description: str
    timestamp: str
    location: str
    raw_status_code: str

    def to_dict(self):
        return self.__dict__