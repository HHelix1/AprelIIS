from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
import uvicorn
import sys
import os
import logging

from database import get_db, init_db, SessionLocal
from models import Employee, EducationProgram, Training, Recommendation, User
from schemas import (
    UserCreate, UserUpdate, UserResponse,
    EmployeeCreate, EmployeeUpdate, EmployeeResponse,
    EducationCreate, EducationUpdate, EducationResponse,
    TrainingCreate, TrainingUpdate, TrainingResponse,
    RecommendationCreate, RecommendationUpdate, RecommendationResponse
)
from crud import (
    create_user, get_users, get_user, update_user, delete_user,
    create_employee, get_employees, get_employee, update_employee, delete_employee,
    create_education, get_educations, get_education, update_education, delete_education,
    create_training, get_trainings, get_training, get_employee_trainings, update_training, delete_training,
    create_recommendation, get_recommendations, get_recommendation, get_employee_recommendations,
    get_user_recommendations, update_recommendation, delete_recommendation
)
from services import (
    generate_employee_recommendations, search_employee, get_employee_stats,
    perform_clustering, get_cluster_recommendations, get_employee_cluster_info
)
from data_generator import (
    DataGenerator, load_users_to_db, load_employees_to_db, load_programs_to_db,
    load_trainings_to_db, load_recommendations_to_db
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="templates")
os.makedirs("templates", exist_ok=True)

app = FastAPI(
    title="Employee Training System",
    version="1.0.0",
    description="Система учета обучения сотрудников"
)


# ==================== UI ROUTES ====================

@app.get("/", response_class=HTMLResponse, tags=["UI"])
async def home(request: Request, db: Session = Depends(get_db)):
    stats = {
        "employees": db.query(Employee).count(),
        "education_programs": db.query(EducationProgram).count(),
        "recommendations": db.query(Recommendation).count()
    }
    return templates.TemplateResponse("index.html", {"request": request, "stats": stats})


@app.get("/employees", response_class=HTMLResponse, tags=["UI"])
async def employees_page(request: Request, db: Session = Depends(get_db)):
    employees = db.query(Employee).all()
    return templates.TemplateResponse("employees.html", {"request": request, "employees": employees})


@app.get("/employee/{worker_id}/recommendations", response_class=HTMLResponse, tags=["UI"])
async def employee_recommendations_page(request: Request, worker_id: int, db: Session = Depends(get_db)):
    employee = get_employee(db, worker_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")

    recommendations = get_employee_recommendations(db, worker_id)
    trainings = get_employee_trainings(db, worker_id)
    stats = get_employee_stats(db, worker_id)
    all_programs = db.query(EducationProgram).all()

    for rec in recommendations:
        rec.program = db.query(EducationProgram).filter(
            EducationProgram.Education_Id == rec.education_id).first()
        if rec.user_id:
            rec.user = db.query(User).filter(User.id_user == rec.user_id).first()

    for training in trainings:
        training.program = db.query(EducationProgram).filter(
            EducationProgram.Education_Id == training.Education_Id).first()

    return templates.TemplateResponse(
        "employee_recommendations.html",
        {
            "request": request,
            "employee": employee,
            "recommendations": recommendations,
            "trainings": trainings,
            "stats": stats,
            "all_programs": all_programs
        }
    )


@app.get("/programs", response_class=HTMLResponse, tags=["UI"])
async def programs_page(request: Request, db: Session = Depends(get_db)):
    programs = db.query(EducationProgram).all()
    return templates.TemplateResponse("programs.html", {"request": request, "programs": programs})


@app.get("/recommendations", response_class=HTMLResponse, tags=["UI"])
async def recommendations_page(request: Request, db: Session = Depends(get_db)):
    recommendations = db.query(Recommendation).order_by(Recommendation.score.desc()).limit(50).all()

    for rec in recommendations:
        rec.employee = db.query(Employee).filter(Employee.Worker_id == rec.worker_id).first()
        rec.program = db.query(EducationProgram).filter(EducationProgram.Education_Id == rec.education_id).first()

    return templates.TemplateResponse(
        "recommendations.html",
        {"request": request, "recommendations": recommendations}
    )


@app.get("/clustering", response_class=HTMLResponse, tags=["UI"])
async def clustering_page(request: Request):
    return templates.TemplateResponse("clustering.html", {"request": request})


# ==================== HEALTH ====================

@app.get("/health", tags=["System"])
def health_check():
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": f"error: {str(e)}"}


# ==================== USERS ====================

@app.post("/api/users/", response_model=UserResponse, status_code=201, tags=["Users"])
def create_user_endpoint(user: UserCreate, db: Session = Depends(get_db)):
    return create_user(db, user)


@app.get("/api/users/", response_model=List[UserResponse], tags=["Users"])
def get_users_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_users(db, skip=skip, limit=limit)


@app.get("/api/users/{user_id}", response_model=UserResponse, tags=["Users"])
def get_user_endpoint(user_id: int, db: Session = Depends(get_db)):
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user


@app.put("/api/users/{user_id}", response_model=UserResponse, tags=["Users"])
def update_user_endpoint(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
    return update_user(db, user_id, user_update)


@app.delete("/api/users/{user_id}", tags=["Users"])
def delete_user_endpoint(user_id: int, db: Session = Depends(get_db)):
    return delete_user(db, user_id)


# ==================== EMPLOYEES ====================

@app.post("/api/employees/", response_model=EmployeeResponse, status_code=201, tags=["Employees"])
def create_employee_endpoint(employee: EmployeeCreate, db: Session = Depends(get_db)):
    return create_employee(db, employee)


@app.get("/api/employees/", response_model=List[EmployeeResponse], tags=["Employees"])
def get_employees_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_employees(db, skip=skip, limit=limit)


@app.get("/api/employees/{worker_id}", response_model=EmployeeResponse, tags=["Employees"])
def get_employee_endpoint(worker_id: int, db: Session = Depends(get_db)):
    employee = get_employee(db, worker_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    return employee


@app.put("/api/employees/{worker_id}", response_model=EmployeeResponse, tags=["Employees"])
def update_employee_endpoint(worker_id: int, employee_update: EmployeeUpdate, db: Session = Depends(get_db)):
    return update_employee(db, worker_id, employee_update)


@app.delete("/api/employees/{worker_id}", tags=["Employees"])
def delete_employee_endpoint(worker_id: int, db: Session = Depends(get_db)):
    return delete_employee(db, worker_id)


# ==================== EDUCATION PROGRAMS ====================

@app.post("/api/education/", response_model=EducationResponse, status_code=201, tags=["Education"])
def create_education_endpoint(education: EducationCreate, db: Session = Depends(get_db)):
    return create_education(db, education)


@app.get("/api/education/", response_model=List[EducationResponse], tags=["Education"])
def get_education_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_educations(db, skip=skip, limit=limit)


@app.get("/api/education/{education_id}", response_model=EducationResponse, tags=["Education"])
def get_education_by_id_endpoint(education_id: int, db: Session = Depends(get_db)):
    education = get_education(db, education_id)
    if not education:
        raise HTTPException(status_code=404, detail="Программа не найдена")
    return education


@app.put("/api/education/{education_id}", response_model=EducationResponse, tags=["Education"])
def update_education_endpoint(education_id: int, education_update: EducationUpdate, db: Session = Depends(get_db)):
    return update_education(db, education_id, education_update)


@app.delete("/api/education/{education_id}", tags=["Education"])
def delete_education_endpoint(education_id: int, db: Session = Depends(get_db)):
    return delete_education(db, education_id)


# ==================== TRAININGS ====================

@app.post("/api/trainings/", response_model=TrainingResponse, status_code=201, tags=["Trainings"])
def create_training_endpoint(training: TrainingCreate, db: Session = Depends(get_db)):
    return create_training(db, training)


@app.get("/api/trainings/", response_model=List[TrainingResponse], tags=["Trainings"])
def get_trainings_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_trainings(db, skip=skip, limit=limit)


@app.get("/api/trainings/{training_id}", response_model=TrainingResponse, tags=["Trainings"])
def get_training_endpoint(training_id: int, db: Session = Depends(get_db)):
    training = get_training(db, training_id)
    if not training:
        raise HTTPException(status_code=404, detail="Обучение не найдено")
    return training


@app.get("/api/employees/{worker_id}/trainings", response_model=List[TrainingResponse], tags=["Trainings"])
def get_employee_trainings_endpoint(worker_id: int, db: Session = Depends(get_db)):
    return get_employee_trainings(db, worker_id)


@app.put("/api/trainings/{training_id}", response_model=TrainingResponse, tags=["Trainings"])
def update_training_endpoint(training_id: int, training_update: TrainingUpdate, db: Session = Depends(get_db)):
    return update_training(db, training_id, training_update)


@app.delete("/api/trainings/{training_id}", tags=["Trainings"])
def delete_training_endpoint(training_id: int, db: Session = Depends(get_db)):
    return delete_training(db, training_id)


# ==================== RECOMMENDATIONS ====================

@app.post("/api/recommendations/", response_model=RecommendationResponse, status_code=201, tags=["Recommendations"])
def create_recommendation_endpoint(recommendation: RecommendationCreate, db: Session = Depends(get_db)):
    return create_recommendation(db, recommendation)


@app.get("/api/recommendations/", response_model=List[RecommendationResponse], tags=["Recommendations"])
def get_recommendations_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_recommendations(db, skip=skip, limit=limit)


@app.get("/api/recommendations/{recommendation_id}", response_model=RecommendationResponse, tags=["Recommendations"])
def get_recommendation_endpoint(recommendation_id: int, db: Session = Depends(get_db)):
    recommendation = get_recommendation(db, recommendation_id)
    if not recommendation:
        raise HTTPException(status_code=404, detail="Рекомендация не найдена")
    return recommendation


@app.get("/api/employees/{worker_id}/recommendations", response_model=List[RecommendationResponse], tags=["Recommendations"])
def get_employee_recommendations_endpoint(worker_id: int, db: Session = Depends(get_db)):
    return get_employee_recommendations(db, worker_id)


@app.get("/api/users/{user_id}/recommendations", response_model=List[RecommendationResponse], tags=["Recommendations"])
def get_user_recommendations_endpoint(user_id: int, db: Session = Depends(get_db)):
    return get_user_recommendations(db, user_id)


@app.put("/api/recommendations/{recommendation_id}", response_model=RecommendationResponse, tags=["Recommendations"])
def update_recommendation_endpoint(recommendation_id: int, recommendation_update: RecommendationUpdate,
                                   db: Session = Depends(get_db)):
    return update_recommendation(db, recommendation_id, recommendation_update)


@app.delete("/api/recommendations/{recommendation_id}", tags=["Recommendations"])
def delete_recommendation_endpoint(recommendation_id: int, db: Session = Depends(get_db)):
    return delete_recommendation(db, recommendation_id)


# ==================== CLUSTERING ====================

@app.post("/api/clustering/perform", tags=["Clustering"])
def api_perform_clustering(n_clusters: int = 4, db: Session = Depends(get_db)):
    return perform_clustering(db, n_clusters)


@app.get("/api/clustering/clusters", tags=["Clustering"])
def api_get_clusters(db: Session = Depends(get_db)):
    result = perform_clustering(db)
    if result['success']:
        return {
            'success': True,
            'clusters': result['cluster_profiles'],
            'total_employees': len(result['employee_ids']),
            'n_clusters': result['n_clusters']
        }
    return result


@app.get("/api/clustering/employee/{employee_id}", tags=["Clustering"])
def api_get_employee_cluster(employee_id: int, db: Session = Depends(get_db)):
    return get_employee_cluster_info(db, employee_id)


@app.get("/api/clustering/cluster/{cluster_id}/recommendations", tags=["Clustering"])
def api_get_cluster_recommendations(cluster_id: int, db: Session = Depends(get_db)):
    recommendations = get_cluster_recommendations(db, cluster_id)
    return {
        'cluster_id': cluster_id,
        'recommendations': recommendations,
        'count': len(recommendations)
    }


@app.get("/api/clustering/visualization-data", tags=["Clustering"])
def api_get_visualization_data(db: Session = Depends(get_db)):
    result = perform_clustering(db)
    if result['success']:
        return {
            'success': True,
            'points': [
                {
                    'employee_id': result['employee_ids'][i],
                    'full_name': result['employee_data'][i]['full_name'],
                    'position': result['employee_data'][i]['position'],
                    'cluster': result['clusters'][i],
                    'x': result['pca_coordinates'][i][0],
                    'y': result['pca_coordinates'][i][1],
                    'success_rate': result['employee_data'][i]['success_rate'],
                    'work_experience': result['employee_data'][i]['work_experience']
                }
                for i in range(len(result['employee_ids']))
            ],
            'cluster_profiles': result['cluster_profiles']
        }
    return result


# ==================== SEARCH & STATS ====================

@app.get("/api/search-employee", tags=["Search"])
def search_employee_endpoint(q: str, db: Session = Depends(get_db)):
    return search_employee(db, q)


@app.post("/api/generate-employee-recommendations/{worker_id}", tags=["Recommendations"])
def generate_employee_recommendations_endpoint(worker_id: int, count: int = 5, db: Session = Depends(get_db)):
    recommendations = generate_employee_recommendations(db, worker_id, count)
    return {"message": f"Сгенерировано {len(recommendations)} рекомендаций", "count": len(recommendations)}


@app.get("/api/employee/{worker_id}/stats", tags=["Search"])
def get_employee_stats_endpoint(worker_id: int, db: Session = Depends(get_db)):
    return get_employee_stats(db, worker_id)


# ==================== DATA GENERATION ====================

@app.post("/api/generate-data", tags=["Data"])
def generate_test_data(
        users: int = 10,
        employees: int = 20,
        programs: int = 5,
        trainings: int = 50,
        recommendations: int = 30
):
    try:
        db = SessionLocal()
        generator = DataGenerator()
        counts = {
            'users': users, 'employees': employees, 'programs': programs,
            'trainings': trainings, 'recommendations': recommendations
        }
        generator.generate_all(counts, db_session=db)
        db.close()
        generator.export_to_csv('generated_data')
        db = SessionLocal()
        total_records = 0
        total_records += load_users_to_db(db, generator.data['users'])
        total_records += load_employees_to_db(db, generator.data['employees'])
        total_records += load_programs_to_db(db, generator.data['programs'])
        total_records += load_trainings_to_db(db, generator.data['trainings'])
        total_records += load_recommendations_to_db(db, generator.data['recommendations'])
        stats = {
            "users": db.query(User).count(),
            "employees": db.query(Employee).count(),
            "education_programs": db.query(EducationProgram).count(),
            "trainings": db.query(Training).count(),
            "recommendations": db.query(Recommendation).count()
        }
        db.close()
        return {
            "message": "Новые тестовые данные успешно добавлены!",
            "generated": counts,
            "new_records_added": total_records,
            "total_records_in_db": stats,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Ошибка при генерации данных: {str(e)}")
        return {"message": f"Ошибка: {str(e)}", "status": "error"}


@app.get("/api/db-stats", tags=["Data"])
def get_db_stats(db: Session = Depends(get_db)):
    stats = {
        "users": db.query(User).count(),
        "employees": db.query(Employee).count(),
        "education_programs": db.query(EducationProgram).count(),
        "trainings": db.query(Training).count(),
        "recommendations": db.query(Recommendation).count(),
        "status": "success"
    }
    return stats


# ==================== MAIN ====================

if __name__ == "__main__":
    init_db()

    if len(sys.argv) > 1 and sys.argv[1] == "--generate":
        print("=" * 60)
        print("ГЕНЕРАЦИЯ ТЕСТОВЫХ ДАННЫХ")
        print("=" * 60)
        db = SessionLocal()
        generator = DataGenerator()
        generator.generate_all({
            'users': 50, 'employees': 200, 'programs': 30,
            'trainings': 500, 'recommendations': 300
        }, db_session=db)
        db.close()
        generator.export_to_csv('generated_data')
        db = SessionLocal()
        load_users_to_db(db, generator.data['users'])
        load_employees_to_db(db, generator.data['employees'])
        load_programs_to_db(db, generator.data['programs'])
        load_trainings_to_db(db, generator.data['trainings'])
        load_recommendations_to_db(db, generator.data['recommendations'])
        db.close()
        print("=" * 60)
        print("ГЕНЕРАЦИЯ ЗАВЕРШЕНА!")
        print("=" * 60)
    else:
        print("=" * 60)
        print("ЗАПУСК EMPLOYEE TRAINING SYSTEM")
        print("=" * 60)
        print("Веб-интерфейс: http://localhost:8000")
        print("Документация API: http://localhost:8000/docs")
        print("Кластеризация: http://localhost:8000/clustering")
        print("=" * 60)
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)