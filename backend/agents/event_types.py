from enum import Enum

class EventType(str, Enum):
    EXCAVATION = "excavation"
    WORK_AT_HEIGHT = "work_at_height"
    TOXIC_GAS = "toxic_gas"
    EXTREME_WEATHER = "extreme_weather"
    MATERIAL_SHORTAGE = "material_shortage"

