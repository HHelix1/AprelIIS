import pandas as pd
import numpy as np
import random
from faker import Faker
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import User, Employee, EducationProgram, Training, Recommendation
import os
import logging

logger = logging.getLogger(__name__)
fake = Faker('ru_RU')
Faker.seed(42)
random.seed(42)
np.random.seed(42)


class DataGenerator:
    """Генератор тестовых данных"""

    def __init__(self):
        self.data = {}
        logger.info("Инициализация генератора данных")

    def get_next_ids(self, db: Session):
        next_ids = {}

        next_ids['users'] = db.query(func.max(User.id_user)).scalar() or 0
        next_ids['employees'] = db.query(func.max(Employee.Worker_id)).scalar() or 0
        next_ids['programs'] = db.query(func.max(EducationProgram.Education_Id)).scalar() or 0
        next_ids['trainings'] = db.query(func.max(Training.id)).scalar() or 0
        next_ids['recommendations'] = db.query(func.max(Recommendation.recommendation_id)).scalar() or 0

        logger.info(f"Текущие максимальные ID в БД: {next_ids}")
        return next_ids

    def generate_all(self, counts=None, db_session=None):
        if counts is None:
            counts = {
                'users': 10,
                'employees': 20,
                'programs': 5,
                'trainings': 50,
                'recommendations': 30
            }

        next_ids = {'users': 0, 'employees': 0, 'programs': 0, 'trainings': 0, 'recommendations': 0}
        if db_session:
            db_next_ids = self.get_next_ids(db_session)
            next_ids = db_next_ids

        logger.info("=" * 60)
        logger.info("НАЧАЛО ГЕНЕРАЦИИ НОВЫХ ТЕСТОВЫХ ДАННЫХ")
        logger.info("=" * 60)

        # Пользователи
        users = []
        start_id = next_ids['users'] + 1
        for i in range(start_id, start_id + counts['users']):
            users.append({
                'id_user': i,
                'Full_name': fake.name(),
                'Position': fake.job(),
                'email': f"user{i}@example.com",
                'Phone_number': fake.phone_number(),
                'Birth_date': fake.date_of_birth(minimum_age=18, maximum_age=65),
                'Work_duration': fake.date_between(start_date='-10y', end_date='-1y')
            })
        self.data['users'] = pd.DataFrame(users)
        logger.info(f"Сгенерировано {len(users)} новых пользователей")

        # Сотрудники
        employees = []
        start_id = next_ids['employees'] + 1
        for i in range(start_id, start_id + counts['employees']):
            employees.append({
                'Worker_id': i,
                'Full_name': fake.name(),
                'Position': fake.job(),
                'email': f"employee{i}@company.ru",
                'Phone_number': fake.phone_number(),
                'Birth_date': fake.date_of_birth(minimum_age=18, maximum_age=65),
                'Work_duration': fake.date_between(start_date='-15y', end_date='-1y')
            })
        self.data['employees'] = pd.DataFrame(employees)
        logger.info(f"Сгенерировано {len(employees)} новых сотрудников")

        # Программы
        programs = []
        start_id = next_ids['programs'] + 1
        used_protocols = set()

        if db_session:
            existing_protocols = db_session.query(EducationProgram.Protocol_number).all()
            used_protocols = {p[0] for p in existing_protocols}

        for i in range(start_id, start_id + counts['programs']):
            while True:
                protocol = random.randint(1000, 9999)
                if protocol not in used_protocols:
                    used_protocols.add(protocol)
                    break

            programs.append({
                'Education_Id': i,
                'Protocol_number': protocol,
                'Name': fake.catch_phrase(),
                'created_at': fake.date_time_between(start_date='-2y', end_date='now')
            })
        self.data['programs'] = pd.DataFrame(programs)
        logger.info(f"Сгенерировано {len(programs)} новых программ")

        # Обучение
        trainings = []
        start_id = next_ids['trainings'] + 1
        max_employee = next_ids['employees'] + counts['employees']
        max_program = next_ids['programs'] + counts['programs']

        for i in range(start_id, start_id + counts['trainings']):
            begin = fake.date_between(start_date='-1y', end_date='+3m')
            end = begin + timedelta(days=random.randint(7, 90))
            trainings.append({
                'id': i,
                'Worker_id': random.randint(1, max_employee),
                'Education_Id': random.randint(1, max_program),
                'Begin_date': begin,
                'End_date': end,
                'status': random.choice(['planned', 'in_progress', 'completed', 'cancelled'])
            })
        self.data['trainings'] = pd.DataFrame(trainings)
        logger.info(f"Сгенерировано {len(trainings)} новых записей об обучении")

        # Рекомендации
        recommendations = []
        start_id = next_ids['recommendations'] + 1

        for i in range(start_id, start_id + counts['recommendations']):
            user_id = random.randint(1, max_employee) if random.random() > 0.3 else None
            recommendations.append({
                'recommendation_id': i,
                'worker_id': random.randint(1, max_employee),
                'education_id': random.randint(1, max_program),
                'user_id': user_id,
                'score': random.randint(60, 100),
                'creation_date': fake.date_between(start_date='-3m', end_date='now')
            })
        self.data['recommendations'] = pd.DataFrame(recommendations)
        logger.info(f"Сгенерировано {len(recommendations)} новых рекомендаций")

        logger.info("=" * 60)
        logger.info(f"ГЕНЕРАЦИЯ ЗАВЕРШЕНА. ВСЕГО НОВЫХ ЗАПИСЕЙ: {sum(len(df) for df in self.data.values())}")
        logger.info("=" * 60)

        return self.data

    def export_to_csv(self, output_dir='generated_data'):
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        for table_name, df in self.data.items():
            output_file = os.path.join(output_dir, f"{table_name}_{timestamp}.csv")
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            logger.info(f"Сохранено: {output_file}")


def load_users_to_db(db: Session, users_df: pd.DataFrame):
    count = 0
    for _, row in users_df.iterrows():
        try:
            user = User(**row.to_dict())
            db.add(user)
            count += 1
        except Exception as e:
            logger.error(f"Ошибка при загрузке пользователя: {str(e)}")
            db.rollback()
            raise
    db.commit()
    logger.info(f"Загружено {count} новых пользователей")
    return count


def load_employees_to_db(db: Session, employees_df: pd.DataFrame):
    count = 0
    for _, row in employees_df.iterrows():
        try:
            employee = Employee(**row.to_dict())
            db.add(employee)
            count += 1
        except Exception as e:
            logger.error(f"Ошибка при загрузке сотрудника: {str(e)}")
            db.rollback()
            raise
    db.commit()
    logger.info(f"Загружено {count} новых сотрудников")
    return count


def load_programs_to_db(db: Session, programs_df: pd.DataFrame):
    count = 0
    for _, row in programs_df.iterrows():
        try:
            program = EducationProgram(**row.to_dict())
            db.add(program)
            count += 1
        except Exception as e:
            logger.error(f"Ошибка при загрузке программы: {str(e)}")
            db.rollback()
            raise
    db.commit()
    logger.info(f"Загружено {count} новых программ")
    return count


def load_trainings_to_db(db: Session, trainings_df: pd.DataFrame):
    count = 0
    for _, row in trainings_df.iterrows():
        try:
            training = Training(**row.to_dict())
            db.add(training)
            count += 1
        except Exception as e:
            logger.error(f"Ошибка при загрузке обучения: {str(e)}")
            db.rollback()
            raise
    db.commit()
    logger.info(f"Загружено {count} новых обучений")
    return count


def load_recommendations_to_db(db: Session, recommendations_df: pd.DataFrame):
    count = 0
    for _, row in recommendations_df.iterrows():
        try:
            user_id = row['user_id']
            if pd.isna(user_id):
                user_id = None
            else:
                user_id = int(user_id)

            recommendation = Recommendation(
                recommendation_id=row['recommendation_id'],
                worker_id=row['worker_id'],
                education_id=row['education_id'],
                user_id=user_id,
                score=row['score'],
                creation_date=row['creation_date']
            )
            db.add(recommendation)
            count += 1
        except Exception as e:
            logger.error(f"Ошибка при загрузке рекомендации: {str(e)}")
            db.rollback()
            raise
    db.commit()
    logger.info(f"Загружено {count} новых рекомендаций")
    return count