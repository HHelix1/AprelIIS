from sqlalchemy import Column, Integer, String, Date, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from datetime import date


class User(Base):
    """Пользователь"""
    __tablename__ = "users"

    id_user = Column(Integer, primary_key=True, index=True)
    Full_name = Column(String(255), nullable=False)
    Position = Column(String(100), nullable=True)
    email = Column(String(100), nullable=False, unique=True)
    Phone_number = Column(String(20), nullable=True)
    Birth_date = Column(Date, nullable=True)
    Work_duration = Column(Date, nullable=True)

    recommendations = relationship("Recommendation", back_populates="user")


class Employee(Base):
    """Сотрудники"""
    __tablename__ = "employees"

    Worker_id = Column(Integer, primary_key=True, index=True)
    Full_name = Column(String(255), nullable=False)
    Position = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False, unique=True)
    Phone_number = Column(String(20), nullable=False)
    Birth_date = Column(Date, nullable=True)
    Work_duration = Column(Date, nullable=True)

    trainings = relationship("Training", back_populates="employee", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="employee")


class EducationProgram(Base):
    """Образовательная программа"""
    __tablename__ = "education_programs"

    Education_Id = Column(Integer, primary_key=True, index=True)
    Protocol_number = Column(Integer, nullable=False, unique=True)
    Name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    trainings = relationship("Training", back_populates="program", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="program")


class Training(Base):
    """Сотрудник и обучение"""
    __tablename__ = "trainings"

    id = Column(Integer, primary_key=True, index=True)
    Worker_id = Column(Integer, ForeignKey("employees.Worker_id", ondelete="CASCADE"))
    Education_Id = Column(Integer, ForeignKey("education_programs.Education_Id", ondelete="CASCADE"))
    Begin_date = Column(Date, nullable=False)
    End_date = Column(Date, nullable=False)
    status = Column(String(50), default="planned")

    employee = relationship("Employee", back_populates="trainings")
    program = relationship("EducationProgram", back_populates="trainings")


class Recommendation(Base):
    """Рекомендация по обучению"""
    __tablename__ = "recommendations"

    recommendation_id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("employees.Worker_id", ondelete="CASCADE"))
    education_id = Column(Integer, ForeignKey("education_programs.Education_Id", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("users.id_user", ondelete="SET NULL"), nullable=True)
    score = Column(Integer, nullable=False)
    creation_date = Column(Date, nullable=False, default=date.today)

    employee = relationship("Employee", back_populates="recommendations")
    program = relationship("EducationProgram", back_populates="recommendations")
    user = relationship("User", back_populates="recommendations")