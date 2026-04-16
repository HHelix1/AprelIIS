from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from typing import Optional
from datetime import date, datetime


class UserCreate(BaseModel):
    Full_name: str
    Position: Optional[str] = None
    email: str
    Phone_number: Optional[str] = None
    Birth_date: Optional[date] = None
    Work_duration: Optional[date] = None

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if '@' not in v:
            raise ValueError('Некорректный email')
        return v


class UserUpdate(BaseModel):
    Full_name: Optional[str] = None
    Position: Optional[str] = None
    email: Optional[str] = None
    Phone_number: Optional[str] = None
    Birth_date: Optional[date] = None
    Work_duration: Optional[date] = None

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if v and '@' not in v:
            raise ValueError('Некорректный email')
        return v


class UserResponse(BaseModel):
    id_user: int
    Full_name: str
    Position: Optional[str] = None
    email: str
    Phone_number: Optional[str] = None
    Birth_date: Optional[date] = None
    Work_duration: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)


class EmployeeCreate(BaseModel):
    Full_name: str
    Position: str
    email: str
    Phone_number: str
    Birth_date: Optional[date] = None
    Work_duration: Optional[date] = None

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if '@' not in v:
            raise ValueError('Некорректный email')
        return v


class EmployeeUpdate(BaseModel):
    Full_name: Optional[str] = None
    Position: Optional[str] = None
    email: Optional[str] = None
    Phone_number: Optional[str] = None
    Birth_date: Optional[date] = None
    Work_duration: Optional[date] = None

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if v and '@' not in v:
            raise ValueError('Некорректный email')
        return v


class EmployeeResponse(BaseModel):
    Worker_id: int
    Full_name: str
    Position: str
    email: str
    Phone_number: str
    Birth_date: Optional[date] = None
    Work_duration: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)


class EducationCreate(BaseModel):
    Protocol_number: int
    Name: str

    @field_validator('Protocol_number')
    @classmethod
    def validate_protocol(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Номер протокола должен быть положительным числом")
        return v


class EducationUpdate(BaseModel):
    Protocol_number: Optional[int] = None
    Name: Optional[str] = None

    @field_validator('Protocol_number')
    @classmethod
    def validate_protocol(cls, v: int) -> int:
        if v and v <= 0:
            raise ValueError("Номер протокола должен быть положительным числом")
        return v


class EducationResponse(BaseModel):
    Education_Id: int
    Protocol_number: int
    Name: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TrainingCreate(BaseModel):
    Worker_id: int
    Education_Id: int
    Begin_date: date
    End_date: date
    status: str = "planned"

    @model_validator(mode='after')
    def validate_dates(self):
        if self.End_date < self.Begin_date:
            raise ValueError("Дата окончания не может быть раньше даты начала")
        return self


class TrainingUpdate(BaseModel):
    Worker_id: Optional[int] = None
    Education_Id: Optional[int] = None
    Begin_date: Optional[date] = None
    End_date: Optional[date] = None
    status: Optional[str] = None

    @model_validator(mode='after')
    def validate_dates(self):
        if self.Begin_date and self.End_date and self.End_date < self.Begin_date:
            raise ValueError("Дата окончания не может быть раньше даты начала")
        return self


class TrainingResponse(BaseModel):
    id: int
    Worker_id: int
    Education_Id: int
    Begin_date: date
    End_date: date
    status: str

    model_config = ConfigDict(from_attributes=True)


class RecommendationCreate(BaseModel):
    worker_id: int
    education_id: int
    user_id: Optional[int] = None
    score: int

    @field_validator('score')
    @classmethod
    def validate_score(cls, v: int) -> int:
        if v < 0 or v > 100:
            raise ValueError("Оценка должна быть от 0 до 100")
        return v


class RecommendationUpdate(BaseModel):
    worker_id: Optional[int] = None
    education_id: Optional[int] = None
    user_id: Optional[int] = None
    score: Optional[int] = None

    @field_validator('score')
    @classmethod
    def validate_score(cls, v: int) -> int:
        if v and (v < 0 or v > 100):
            raise ValueError("Оценка должна быть от 0 до 100")
        return v


class RecommendationResponse(BaseModel):
    recommendation_id: int
    worker_id: int
    education_id: int
    user_id: Optional[int] = None
    score: int
    creation_date: date

    model_config = ConfigDict(from_attributes=True)