from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from models import Employee, EducationProgram, Training, User, Recommendation
from datetime import date
import logging
import random
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

logger = logging.getLogger(__name__)


# ==================== ФУНКЦИИ ДЛЯ РАСЧЁТА РЕКОМЕНДАЦИЙ ====================

def get_employee_skill_level(db: Session, worker_id: int) -> int:
    """Определение уровня навыков сотрудника на основе его обучений"""
    trainings = db.query(Training).filter(Training.Worker_id == worker_id).all()

    if not trainings:
        return 40  # Базовый уровень для новых сотрудников

    completed = [t for t in trainings if t.status == 'completed']
    if not completed:
        return 45

    # Количество завершенных обучений
    completed_count = len(completed)

    # Средняя оценка рекомендаций
    recommendations = db.query(Recommendation).filter(Recommendation.worker_id == worker_id).all()
    avg_score = sum(r.score for r in recommendations) / len(recommendations) if recommendations else 70

    # Уровень навыков: базовый + бонус за обучения + бонус за оценки
    skill_level = min(100, 40 + completed_count * 3 + (avg_score - 50) * 0.3)
    return int(skill_level)


def get_program_difficulty(db: Session, program_id: int) -> int:
    """Определение сложности программы"""
    program = db.query(EducationProgram).filter(EducationProgram.Education_Id == program_id).first()
    if not program:
        return 50

    # Количество сотрудников, успешно прошедших программу
    completions = db.query(Training).filter(
        Training.Education_Id == program_id,
        Training.status == 'completed'
    ).count()

    # Базовая сложность от номера протокола
    base_difficulty = 30 + (program.Protocol_number % 60)

    # Чем больше людей прошло, тем программа считается проще
    difficulty = max(20, min(100, base_difficulty - completions // 2))
    return int(difficulty)


def get_required_skill_for_program(program_difficulty: int) -> int:
    """Требуемый уровень навыков для программы (на 20% ниже сложности)"""
    return max(20, min(100, program_difficulty - 20))


def get_performance_rating(db: Session, worker_id: int) -> int:
    """Оценка производительности сотрудника (0-100)"""
    trainings = db.query(Training).filter(Training.Worker_id == worker_id).all()
    recommendations = db.query(Recommendation).filter(Recommendation.worker_id == worker_id).all()

    if not trainings and not recommendations:
        return 50  # Средняя производительность по умолчанию

    # Успешность обучений (60% веса)
    if trainings:
        completed = len([t for t in trainings if t.status == 'completed'])
        success_rate = (completed / len(trainings)) * 100
    else:
        success_rate = 50

    # Средняя оценка рекомендаций (40% веса)
    if recommendations:
        avg_rec_score = sum(r.score for r in recommendations) / len(recommendations)
    else:
        avg_rec_score = 50

    performance = int(success_rate * 0.6 + avg_rec_score * 0.4)
    return max(0, min(100, performance))


def get_time_since_last_training(db: Session, worker_id: int) -> int:
    """Время (в днях) с последнего обучения"""
    last_training = db.query(Training).filter(
        Training.Worker_id == worker_id
    ).order_by(Training.End_date.desc()).first()

    if not last_training:
        return 365  # Давно не обучался (макс)

    days_since = (date.today() - last_training.End_date).days
    return max(0, min(365, days_since))


def calculate_skill_gap_score(employee_skill: int, required_skill: int) -> int:

    skill_gap = max(0, min(100, required_skill - employee_skill + 50))
    return int(skill_gap)


def calculate_urgency_score(performance_rating: int, days_since_training: int) -> int:

    # Фактор времени: чем дольше не обучался, тем выше (макс 100)
    time_factor = min(100, days_since_training / 3.65)  # 365 дней = 100

    urgency = (100 - performance_rating) * 0.6 + time_factor * 0.4
    return int(max(0, min(100, urgency)))


def calculate_relevance_score(employee_skill: int, program_difficulty: int) -> int:

    relevance = max(0, 100 - abs(employee_skill - program_difficulty))
    return int(relevance)


def calculate_final_recommendation_score(db: Session, worker_id: int, program_id: int) -> dict:

    employee_skill = get_employee_skill_level(db, worker_id)
    program_difficulty = get_program_difficulty(db, program_id)
    required_skill = get_required_skill_for_program(program_difficulty)
    performance = get_performance_rating(db, worker_id)
    days_since = get_time_since_last_training(db, worker_id)

    # Рассчитываем компоненты
    skill_gap = calculate_skill_gap_score(employee_skill, required_skill)
    urgency = calculate_urgency_score(performance, days_since)
    relevance = calculate_relevance_score(employee_skill, program_difficulty)

    # Итоговый score (взвешенная сумма)
    final_score = int(skill_gap * 0.3 + urgency * 0.3 + relevance * 0.4)

    return {
        'final_score': final_score,
        'components': {
            'skill_gap': skill_gap,
            'urgency': urgency,
            'relevance': relevance,
            'employee_skill': employee_skill,
            'program_difficulty': program_difficulty,
            'required_skill': required_skill,
            'performance': performance,
            'days_since_training': days_since
        }
    }


# ==================== ОСНОВНАЯ ФУНКЦИЯ ГЕНЕРАЦИИ РЕКОМЕНДАЦИЙ ====================

def generate_employee_recommendations(db: Session, worker_id: int, count: int = 5):
    """
    Интеллектуальная генерация рекомендаций на основе формул:
    - Skill Gap Score
    - Urgency Score
    - Relevance Score
    """
    try:
        employee = db.query(Employee).filter(Employee.Worker_id == worker_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Сотрудник не найден")

        # Получаем программы, которые сотрудник уже прошел
        completed_programs = db.query(Training.Education_Id) \
            .filter(Training.Worker_id == worker_id) \
            .filter(Training.status == 'completed') \
            .all()
        completed_ids = [p[0] for p in completed_programs]

        # Получаем программы, которые уже назначены (в процессе)
        in_progress_programs = db.query(Training.Education_Id) \
            .filter(Training.Worker_id == worker_id) \
            .filter(Training.status == 'in_progress') \
            .all()
        in_progress_ids = [p[0] for p in in_progress_programs]

        # Исключаем пройденные и текущие программы
        excluded_ids = set(completed_ids + in_progress_ids)

        # Получаем все программы
        all_programs = db.query(EducationProgram).all()
        available_programs = [p for p in all_programs if p.Education_Id not in excluded_ids]

        if not available_programs:
            logger.info(f"Нет доступных программ для сотрудника {worker_id}")
            return []

        users = db.query(User).all()
        recommendations = []
        max_id = db.query(func.max(Recommendation.recommendation_id)).scalar() or 0

        # Для каждой доступной программы рассчитываем score по формулам
        program_scores = []
        for program in available_programs:
            score_data = calculate_final_recommendation_score(db, worker_id, program.Education_Id)
            program_scores.append({
                'program': program,
                'score': score_data['final_score'],
                'components': score_data['components']
            })

        # Сортируем по убыванию score (от лучших к худшим)
        program_scores.sort(key=lambda x: x['score'], reverse=True)

        # Берём топ-count программ
        for ps in program_scores[:count]:
            max_id += 1
            user = random.choice(users) if users and len(users) > 0 else None

            recommendation = Recommendation(
                recommendation_id=max_id,
                worker_id=worker_id,
                education_id=ps['program'].Education_Id,
                user_id=user.id_user if user else None,
                score=ps['score'],
                creation_date=date.today()
            )
            db.add(recommendation)
            recommendations.append(recommendation)

            # Логируем детали расчёта
            comp = ps['components']
            logger.info(f"Рекомендация для {employee.Full_name}: {ps['program'].Name}")
            logger.info(f"  → Итоговый Score: {ps['score']}%")
            logger.info(
                f"  → Skill Gap: {comp['skill_gap']}% | Urgency: {comp['urgency']}% | Relevance: {comp['relevance']}%")
            logger.info(
                f"  → Навыки: {comp['employee_skill']} | Сложность: {comp['program_difficulty']} | Производительность: {comp['performance']}%")

        db.commit()
        for rec in recommendations:
            db.refresh(rec)

        logger.info(f"Сгенерировано {len(recommendations)} интеллектуальных рекомендаций для сотрудника {worker_id}")
        return recommendations

    except Exception as e:
        logger.error(f"Ошибка при генерации рекомендаций: {str(e)}")
        db.rollback()
        raise


# ==================== ОСТАЛЬНЫЕ ФУНКЦИИ (БЕЗ ИЗМЕНЕНИЙ) ====================

def search_employee(db: Session, query: str):
    """Поиск сотрудника по имени или email"""
    try:
        employee = db.query(Employee) \
            .filter(
            (Employee.Full_name.ilike(f"%{query}%")) |
            (Employee.email.ilike(f"%{query}%"))
        ) \
            .first()

        if employee:
            return {"found": True, "worker_id": employee.Worker_id}

        similar = db.query(Employee) \
            .filter(
            (Employee.Full_name.ilike(f"%{query}%")) |
            (Employee.email.ilike(f"%{query}%"))
        ) \
            .limit(5) \
            .all()

        return {
            "found": False,
            "similar": [
                {
                    "Worker_id": e.Worker_id,
                    "Full_name": e.Full_name,
                    "Position": e.Position,
                    "email": e.email
                }
                for e in similar
            ]
        }
    except Exception as e:
        logger.error(f"Ошибка при поиске сотрудника: {str(e)}")
        raise


def get_employee_stats(db: Session, worker_id: int):
    """Получение статистики по сотруднику"""
    try:
        trainings = db.query(Training).filter(Training.Worker_id == worker_id).all()
        recommendations = db.query(Recommendation).filter(Recommendation.worker_id == worker_id).all()

        total_trainings = len(trainings)
        completed_trainings = len([t for t in trainings if t.status == 'completed'])

        if recommendations:
            avg_score = sum(r.score for r in recommendations) / len(recommendations)
        else:
            avg_score = 0

        return {
            "total_trainings": total_trainings,
            "completed_trainings": completed_trainings,
            "avg_score": round(avg_score, 1)
        }
    except Exception as e:
        logger.error(f"Ошибка при получении статистики сотрудника: {str(e)}")
        raise


# ==================== ФУНКЦИИ ДЛЯ КЛАСТЕРИЗАЦИИ ====================

def get_employee_features(db: Session):
    """Сбор признаков сотрудников для кластеризации"""
    employees = db.query(Employee).all()

    features = []
    employee_ids = []

    for emp in employees:
        trainings = db.query(Training).filter(Training.Worker_id == emp.Worker_id).all()
        recommendations = db.query(Recommendation).filter(Recommendation.worker_id == emp.Worker_id).all()

        total_trainings = len(trainings)
        completed_trainings = len([t for t in trainings if t.status == 'completed'])
        cancelled_trainings = len([t for t in trainings if t.status == 'cancelled'])

        if trainings:
            avg_duration = sum((t.End_date - t.Begin_date).days for t in trainings) / len(trainings)
        else:
            avg_duration = 0

        success_rate = completed_trainings / total_trainings if total_trainings > 0 else 0

        if recommendations:
            avg_recommendation_score = sum(r.score for r in recommendations) / len(recommendations)
        else:
            avg_recommendation_score = 0

        if emp.Work_duration:
            work_experience = (date.today() - emp.Work_duration).days / 365.25
        else:
            work_experience = 0

        if emp.Birth_date:
            age = (date.today() - emp.Birth_date).days / 365.25
        else:
            age = 0

        position_score = encode_position(emp.Position)

        features.append({
            'employee_id': emp.Worker_id,
            'full_name': emp.Full_name,
            'position': emp.Position,
            'total_trainings': total_trainings,
            'completed_trainings': completed_trainings,
            'cancelled_trainings': cancelled_trainings,
            'success_rate': success_rate,
            'avg_duration': avg_duration,
            'avg_recommendation_score': avg_recommendation_score,
            'work_experience': work_experience,
            'age': age,
            'position_score': position_score
        })
        employee_ids.append(emp.Worker_id)

    return pd.DataFrame(features), employee_ids


def encode_position(position: str) -> int:
    """Кодирование должности в числовое значение"""
    position_levels = {
        'стажер': 1, 'младший': 2, 'специалист': 3, 'ведущий': 4,
        'главный': 5, 'руководитель': 6, 'директор': 7, 'исполнительный': 8,
        'начальник': 6, 'менеджер': 4, 'аналитик': 3, 'разработчик': 3,
        'инженер': 3, 'admin': 5, 'manager': 4
    }

    position_lower = position.lower()
    for key, value in position_levels.items():
        if key in position_lower:
            return value
    return 3


def perform_clustering(db: Session, n_clusters: int = 4):
    """Выполнение кластеризации сотрудников"""
    try:
        df, employee_ids = get_employee_features(db)

        if len(df) < n_clusters:
            n_clusters = max(2, len(df) // 2)

        features_for_clustering = [
            'total_trainings', 'success_rate', 'avg_duration',
            'avg_recommendation_score', 'work_experience', 'age', 'position_score'
        ]

        X = df[features_for_clustering].copy()
        X = X.fillna(0)

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(X_scaled)

        df['cluster'] = clusters

        cluster_profiles = []
        for i in range(n_clusters):
            cluster_data = df[df['cluster'] == i]
            profile = {
                'cluster_id': i,
                'size': int(len(cluster_data)),
                'avg_success_rate': float(cluster_data['success_rate'].mean()) if len(cluster_data) > 0 else 0,
                'avg_work_experience': float(cluster_data['work_experience'].mean()) if len(cluster_data) > 0 else 0,
                'avg_age': float(cluster_data['age'].mean()) if len(cluster_data) > 0 else 0,
                'avg_trainings': float(cluster_data['total_trainings'].mean()) if len(cluster_data) > 0 else 0,
                'avg_recommendation_score': float(cluster_data['avg_recommendation_score'].mean()) if len(
                    cluster_data) > 0 else 0,
                'top_positions': cluster_data['position'].value_counts().head(3).to_dict() if len(
                    cluster_data) > 0 else {}
            }
            cluster_profiles.append(profile)

        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(X_scaled)
        df['pca_x'] = X_pca[:, 0]
        df['pca_y'] = X_pca[:, 1]

        points = []
        for i in range(len(employee_ids)):
            points.append({
                'employee_id': employee_ids[i],
                'full_name': df.iloc[i]['full_name'],
                'position': df.iloc[i]['position'],
                'cluster': int(clusters[i]),
                'x': float(df.iloc[i]['pca_x']),
                'y': float(df.iloc[i]['pca_y']),
                'success_rate': float(df.iloc[i]['success_rate']),
                'work_experience': float(df.iloc[i]['work_experience'])
            })

        return {
            'success': True,
            'clusters': clusters.tolist(),
            'employee_ids': employee_ids,
            'cluster_profiles': cluster_profiles,
            'pca_coordinates': df[['pca_x', 'pca_y']].values.tolist(),
            'employee_data': df.to_dict('records'),
            'n_clusters': n_clusters,
            'explained_variance': pca.explained_variance_ratio_.tolist(),
            'points': points
        }

    except Exception as e:
        logger.error(f"Ошибка при кластеризации: {str(e)}")
        return {'success': False, 'error': str(e)}


def get_cluster_recommendations(db: Session, cluster_id: int):
    """Получение рекомендаций для кластера"""
    try:
        clustering_result = perform_clustering(db)
        if not clustering_result['success']:
            return []

        employee_ids_in_cluster = [
            clustering_result['employee_ids'][i]
            for i, c in enumerate(clustering_result['clusters'])
            if c == cluster_id
        ]

        all_recommendations = db.query(Recommendation).filter(
            Recommendation.worker_id.in_(employee_ids_in_cluster)
        ).all()

        program_counts = {}
        program_scores = {}

        for rec in all_recommendations:
            program_counts[rec.education_id] = program_counts.get(rec.education_id, 0) + 1
            if rec.education_id not in program_scores:
                program_scores[rec.education_id] = []
            program_scores[rec.education_id].append(rec.score)

        cluster_recommendations = []
        for edu_id, count in program_counts.items():
            program = db.query(EducationProgram).filter(
                EducationProgram.Education_Id == edu_id
            ).first()

            if program:
                avg_score = sum(program_scores[edu_id]) / len(program_scores[edu_id])
                popularity = count / len(employee_ids_in_cluster)

                cluster_recommendations.append({
                    'education_id': edu_id,
                    'program_name': program.Name,
                    'protocol_number': program.Protocol_number,
                    'frequency': count,
                    'popularity': popularity,
                    'avg_score': avg_score,
                    'recommendation_score': avg_score * popularity
                })

        cluster_recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)
        return cluster_recommendations[:10]

    except Exception as e:
        logger.error(f"Ошибка при получении рекомендаций кластера: {str(e)}")
        return []


def get_employee_cluster_info(db: Session, employee_id: int):
    """Получение информации о кластере сотрудника"""
    try:
        clustering_result = perform_clustering(db)

        if not clustering_result['success']:
            return {'success': False, 'error': clustering_result.get('error', 'Unknown error')}

        employee_index = None
        for i, emp_id in enumerate(clustering_result['employee_ids']):
            if emp_id == employee_id:
                employee_index = i
                break

        if employee_index is None:
            return {'success': False, 'error': 'Сотрудник не найден'}

        cluster_id = clustering_result['clusters'][employee_index]
        cluster_profile = clustering_result['cluster_profiles'][cluster_id]

        similar_employees = []
        for i, emp_id in enumerate(clustering_result['employee_ids']):
            if i != employee_index and clustering_result['clusters'][i] == cluster_id:
                similar_employees.append({
                    'employee_id': emp_id,
                    'full_name': clustering_result['employee_data'][i]['full_name'],
                    'position': clustering_result['employee_data'][i]['position']
                })

        return {
            'success': True,
            'employee_id': employee_id,
            'cluster_id': cluster_id,
            'cluster_profile': cluster_profile,
            'similar_employees': similar_employees[:10],
            'pca_coordinates': {
                'x': clustering_result['pca_coordinates'][employee_index][0],
                'y': clustering_result['pca_coordinates'][employee_index][1]
            }
        }

    except Exception as e:
        logger.error(f"Ошибка при получении информации о кластере: {str(e)}")
        return {'success': False, 'error': str(e)}