from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from models import User, Employee, EducationProgram, Training, Recommendation
from schemas import (
    UserCreate, UserUpdate, EmployeeCreate, EmployeeUpdate,
    EducationCreate, EducationUpdate, TrainingCreate, TrainingUpdate,
    RecommendationCreate, RecommendationUpdate
)
from datetime import date
import logging

logger = logging.getLogger(__name__)


def create_user(db: Session, user: UserCreate):
    try:
        existing_user = db.query(User).filter(User.email == user.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail=f"Email {user.email} уже используется")

        db_user = User(**user.model_dump())
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        logger.info(f"Создан пользователь с id: {db_user.id_user}")
        return db_user
    except Exception as e:
        logger.error(f"Ошибка при создании пользователя: {str(e)}")
        db.rollback()
        raise


def get_users(db: Session, skip: int = 0, limit: int = 100):
    try:
        return db.query(User).offset(skip).limit(limit).all()
    except Exception as e:
        logger.error(f"Ошибка при получении пользователей: {str(e)}")
        raise


def get_user(db: Session, user_id: int):
    try:
        return db.query(User).filter(User.id_user == user_id).first()
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя: {str(e)}")
        raise


def update_user(db: Session, user_id: int, user_update: UserUpdate):
    try:
        db_user = db.query(User).filter(User.id_user == user_id).first()
        if not db_user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        if user_update.email and user_update.email != db_user.email:
            existing_user = db.query(User).filter(User.email == user_update.email).first()
            if existing_user:
                raise HTTPException(status_code=400, detail=f"Email {user_update.email} уже используется")

        update_data = user_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_user, field, value)

        db.commit()
        db.refresh(db_user)
        logger.info(f"Обновлен пользователь с id: {user_id}")
        return db_user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении пользователя: {str(e)}")
        db.rollback()
        raise


def delete_user(db: Session, user_id: int):
    try:
        db_user = db.query(User).filter(User.id_user == user_id).first()
        if not db_user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        db.delete(db_user)
        db.commit()
        logger.info(f"Удален пользователь с id: {user_id}")
        return {"message": "Пользователь успешно удален"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при удалении пользователя: {str(e)}")
        db.rollback()
        raise


def create_employee(db: Session, employee: EmployeeCreate):
    try:
        existing_employee = db.query(Employee).filter(Employee.email == employee.email).first()
        if existing_employee:
            raise HTTPException(status_code=400, detail=f"Email {employee.email} уже используется")

        db_employee = Employee(**employee.model_dump())
        db.add(db_employee)
        db.commit()
        db.refresh(db_employee)
        logger.info(f"Создан сотрудник с id: {db_employee.Worker_id}")
        return db_employee
    except Exception as e:
        logger.error(f"Ошибка при создании сотрудника: {str(e)}")
        db.rollback()
        raise


def get_employees(db: Session, skip: int = 0, limit: int = 100):
    try:
        return db.query(Employee).offset(skip).limit(limit).all()
    except Exception as e:
        logger.error(f"Ошибка при получении сотрудников: {str(e)}")
        raise


def get_employee(db: Session, worker_id: int):
    try:
        return db.query(Employee).filter(Employee.Worker_id == worker_id).first()
    except Exception as e:
        logger.error(f"Ошибка при получении сотрудника: {str(e)}")
        raise


def update_employee(db: Session, worker_id: int, employee_update: EmployeeUpdate):
    try:
        db_employee = db.query(Employee).filter(Employee.Worker_id == worker_id).first()
        if not db_employee:
            raise HTTPException(status_code=404, detail="Сотрудник не найден")

        if employee_update.email and employee_update.email != db_employee.email:
            existing_employee = db.query(Employee).filter(Employee.email == employee_update.email).first()
            if existing_employee:
                raise HTTPException(status_code=400, detail=f"Email {employee_update.email} уже используется")

        update_data = employee_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_employee, field, value)

        db.commit()
        db.refresh(db_employee)
        logger.info(f"Обновлен сотрудник с id: {worker_id}")
        return db_employee
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении сотрудника: {str(e)}")
        db.rollback()
        raise


def delete_employee(db: Session, worker_id: int):
    try:
        db_employee = db.query(Employee).filter(Employee.Worker_id == worker_id).first()
        if not db_employee:
            raise HTTPException(status_code=404, detail="Сотрудник не найден")

        db.delete(db_employee)
        db.commit()
        logger.info(f"Удален сотрудник с id: {worker_id}")
        return {"message": "Сотрудник успешно удален"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при удалении сотрудника: {str(e)}")
        db.rollback()
        raise


def create_education(db: Session, education: EducationCreate):
    try:
        existing_program = db.query(EducationProgram).filter(
            EducationProgram.Protocol_number == education.Protocol_number
        ).first()
        if existing_program:
            raise HTTPException(
                status_code=400,
                detail=f"Программа с номером протокола {education.Protocol_number} уже существует"
            )

        db_education = EducationProgram(**education.model_dump())
        db.add(db_education)
        db.commit()
        db.refresh(db_education)
        logger.info(f"Создана программа с id: {db_education.Education_Id}")
        return db_education
    except Exception as e:
        logger.error(f"Ошибка при создании программы: {str(e)}")
        db.rollback()
        raise


def get_educations(db: Session, skip: int = 0, limit: int = 100):
    try:
        return db.query(EducationProgram).offset(skip).limit(limit).all()
    except Exception as e:
        logger.error(f"Ошибка при получении программ: {str(e)}")
        raise


def get_education(db: Session, education_id: int):
    try:
        return db.query(EducationProgram).filter(EducationProgram.Education_Id == education_id).first()
    except Exception as e:
        logger.error(f"Ошибка при получении программы: {str(e)}")
        raise


def update_education(db: Session, education_id: int, education_update: EducationUpdate):
    try:
        db_education = db.query(EducationProgram).filter(EducationProgram.Education_Id == education_id).first()
        if not db_education:
            raise HTTPException(status_code=404, detail="Программа не найдена")

        if education_update.Protocol_number and education_update.Protocol_number != db_education.Protocol_number:
            existing_program = db.query(EducationProgram).filter(
                EducationProgram.Protocol_number == education_update.Protocol_number
            ).first()
            if existing_program:
                raise HTTPException(
                    status_code=400,
                    detail=f"Программа с номером протокола {education_update.Protocol_number} уже существует"
                )

        update_data = education_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_education, field, value)

        db.commit()
        db.refresh(db_education)
        logger.info(f"Обновлена программа с id: {education_id}")
        return db_education
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении программы: {str(e)}")
        db.rollback()
        raise


def delete_education(db: Session, education_id: int):
    try:
        db_education = db.query(EducationProgram).filter(EducationProgram.Education_Id == education_id).first()
        if not db_education:
            raise HTTPException(status_code=404, detail="Программа не найдена")

        db.delete(db_education)
        db.commit()
        logger.info(f"Удалена программа с id: {education_id}")
        return {"message": "Программа успешно удалена"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при удалении программы: {str(e)}")
        db.rollback()
        raise


def create_training(db: Session, training: TrainingCreate):
    try:
        employee = db.query(Employee).filter(Employee.Worker_id == training.Worker_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail=f"Сотрудник с id {training.Worker_id} не найден")

        program = db.query(EducationProgram).filter(EducationProgram.Education_Id == training.Education_Id).first()
        if not program:
            raise HTTPException(status_code=404, detail=f"Программа с id {training.Education_Id} не найдена")

        db_training = Training(**training.model_dump())
        db.add(db_training)
        db.commit()
        db.refresh(db_training)
        logger.info(f"Создано обучение с id: {db_training.id}")
        return db_training
    except Exception as e:
        logger.error(f"Ошибка при создании обучения: {str(e)}")
        db.rollback()
        raise


def get_trainings(db: Session, skip: int = 0, limit: int = 100):
    try:
        return db.query(Training).offset(skip).limit(limit).all()
    except Exception as e:
        logger.error(f"Ошибка при получении обучений: {str(e)}")
        raise


def get_training(db: Session, training_id: int):
    try:
        return db.query(Training).filter(Training.id == training_id).first()
    except Exception as e:
        logger.error(f"Ошибка при получении обучения: {str(e)}")
        raise


def get_employee_trainings(db: Session, worker_id: int):
    try:
        return db.query(Training).filter(Training.Worker_id == worker_id).all()
    except Exception as e:
        logger.error(f"Ошибка при получении обучений сотрудника: {str(e)}")
        raise


def update_training(db: Session, training_id: int, training_update: TrainingUpdate):
    try:
        db_training = db.query(Training).filter(Training.id == training_id).first()
        if not db_training:
            raise HTTPException(status_code=404, detail="Обучение не найдено")

        if training_update.Worker_id:
            employee = db.query(Employee).filter(Employee.Worker_id == training_update.Worker_id).first()
            if not employee:
                raise HTTPException(status_code=404, detail=f"Сотрудник с id {training_update.Worker_id} не найден")

        if training_update.Education_Id:
            program = db.query(EducationProgram).filter(
                EducationProgram.Education_Id == training_update.Education_Id).first()
            if not program:
                raise HTTPException(status_code=404, detail=f"Программа с id {training_update.Education_Id} не найдена")

        update_data = training_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_training, field, value)

        db.commit()
        db.refresh(db_training)
        logger.info(f"Обновлено обучение с id: {training_id}")
        return db_training
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении обучения: {str(e)}")
        db.rollback()
        raise


def delete_training(db: Session, training_id: int):
    try:
        db_training = db.query(Training).filter(Training.id == training_id).first()
        if not db_training:
            raise HTTPException(status_code=404, detail="Обучение не найдено")

        db.delete(db_training)
        db.commit()
        logger.info(f"Удалено обучение с id: {training_id}")
        return {"message": "Обучение успешно удалено"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при удалении обучения: {str(e)}")
        db.rollback()
        raise


def delete_biometric(db: Session, biometric_id: int):
    try:
        db_biometric = db.query(Biometric).filter(Biometric.biometric_id == biometric_id).first()
        if not db_biometric:
            raise HTTPException(status_code=404, detail="Биометрия не найдена")

        db.delete(db_biometric)
        db.commit()
        logger.info(f"Удалена биометрия с id: {biometric_id}")
        return {"message": "Биометрия успешно удалена"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при удалении биометрии: {str(e)}")
        db.rollback()
        raise


def create_recommendation(db: Session, recommendation: RecommendationCreate):
    try:
        employee = db.query(Employee).filter(Employee.Worker_id == recommendation.worker_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail=f"Сотрудник с id {recommendation.worker_id} не найден")

        program = db.query(EducationProgram).filter(
            EducationProgram.Education_Id == recommendation.education_id).first()
        if not program:
            raise HTTPException(status_code=404, detail=f"Программа с id {recommendation.education_id} не найдена")

        if recommendation.user_id:
            user = db.query(User).filter(User.id_user == recommendation.user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail=f"Пользователь с id {recommendation.user_id} не найден")

        max_id = db.query(func.max(Recommendation.recommendation_id)).scalar() or 0
        new_id = max_id + 1

        db_recommendation = Recommendation(
            recommendation_id=new_id,
            worker_id=recommendation.worker_id,
            education_id=recommendation.education_id,
            user_id=recommendation.user_id,
            score=recommendation.score,
            creation_date=date.today()
        )
        db.add(db_recommendation)
        db.commit()
        db.refresh(db_recommendation)
        logger.info(f"Создана рекомендация с id: {db_recommendation.recommendation_id}")
        return db_recommendation
    except Exception as e:
        logger.error(f"Ошибка при создании рекомендации: {str(e)}")
        db.rollback()
        raise


def get_recommendations(db: Session, skip: int = 0, limit: int = 100):
    try:
        return db.query(Recommendation).offset(skip).limit(limit).all()
    except Exception as e:
        logger.error(f"Ошибка при получении рекомендаций: {str(e)}")
        raise


def get_recommendation(db: Session, recommendation_id: int):
    try:
        return db.query(Recommendation).filter(Recommendation.recommendation_id == recommendation_id).first()
    except Exception as e:
        logger.error(f"Ошибка при получении рекомендации: {str(e)}")
        raise


def get_employee_recommendations(db: Session, worker_id: int):
    try:
        return db.query(Recommendation) \
            .filter(Recommendation.worker_id == worker_id) \
            .order_by(Recommendation.score.desc()) \
            .all()
    except Exception as e:
        logger.error(f"Ошибка при получении рекомендаций сотрудника: {str(e)}")
        raise


def get_user_recommendations(db: Session, user_id: int):
    try:
        return db.query(Recommendation).filter(Recommendation.user_id == user_id).all()
    except Exception as e:
        logger.error(f"Ошибка при получении рекомендаций пользователя: {str(e)}")
        raise


def update_recommendation(db: Session, recommendation_id: int, recommendation_update: RecommendationUpdate):
    try:
        db_recommendation = db.query(Recommendation).filter(
            Recommendation.recommendation_id == recommendation_id).first()
        if not db_recommendation:
            raise HTTPException(status_code=404, detail="Рекомендация не найдена")

        if recommendation_update.worker_id:
            employee = db.query(Employee).filter(Employee.Worker_id == recommendation_update.worker_id).first()
            if not employee:
                raise HTTPException(status_code=404,
                                    detail=f"Сотрудник с id {recommendation_update.worker_id} не найден")

        if recommendation_update.education_id:
            program = db.query(EducationProgram).filter(
                EducationProgram.Education_Id == recommendation_update.education_id).first()
            if not program:
                raise HTTPException(status_code=404,
                                    detail=f"Программа с id {recommendation_update.education_id} не найдена")

        if recommendation_update.user_id:
            user = db.query(User).filter(User.id_user == recommendation_update.user_id).first()
            if not user:
                raise HTTPException(status_code=404,
                                    detail=f"Пользователь с id {recommendation_update.user_id} не найден")

        update_data = recommendation_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_recommendation, field, value)

        db.commit()
        db.refresh(db_recommendation)
        logger.info(f"Обновлена рекомендация с id: {recommendation_id}")
        return db_recommendation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении рекомендации: {str(e)}")
        db.rollback()
        raise


def delete_recommendation(db: Session, recommendation_id: int):
    try:
        db_recommendation = db.query(Recommendation).filter(
            Recommendation.recommendation_id == recommendation_id).first()
        if not db_recommendation:
            raise HTTPException(status_code=404, detail="Рекомендация не найдена")

        db.delete(db_recommendation)
        db.commit()
        logger.info(f"Удалена рекомендация с id: {recommendation_id}")
        return {"message": "Рекомендация успешно удалена"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при удалении рекомендации: {str(e)}")
        db.rollback()
        raise