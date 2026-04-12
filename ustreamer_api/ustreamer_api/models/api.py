import uuid
import pydantic


class StartTimelapseRequest(pydantic.BaseModel):
    event_duration: float = pydantic.Field(gt=0)
    target_duration: float = pydantic.Field(gt=0)
    target_fps: float = pydantic.Field(gt=0)

    @pydantic.model_validator(mode="after")
    def validate_target_duration(self) -> "StartTimelapseRequest":
        """Ensure the target duration does not exceed the event duration."""
        if self.target_duration > self.event_duration:
            raise ValueError("target_duration must be less than or equal to event_duration")
        return self
