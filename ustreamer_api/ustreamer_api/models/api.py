import uuid
import pydantic

class StartTimelapseRequest(pydantic.BaseModel):
    event_duration: float = pydantic.Field(gt=0)
    timelapse_duration: float = pydantic.Field(gt=0)
    target_fps: float = pydantic.Field(gt=0)


class TimelapseResponse(pydantic.BaseModel):
    id: uuid.UUID
    event_duration: float
    timelapse_duration: float
    target_fps: float
