from fastapi import FastAPI, Query
import csv
import os


app = FastAPI(
    title="HCP Engagement Mock APIs",
    description="Mock APIs representing enterprise HCP engagement data sources"
)


# ============================================================
# DATA DIRECTORY
# ============================================================

DATA_DIR = "/home/ec2-user/mock-api/data"


# ============================================================
# LOAD CSV
# ============================================================

def load_csv(filename):

    filepath = os.path.join(DATA_DIR, filename)

    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"Dataset not found: {filepath}"
        )

    with open(
        filepath,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        return list(reader)


# ============================================================
# LOAD ALL DATASETS WHEN API STARTS
# ============================================================

EMAIL_DATA = load_csv("email_activity.csv")
WEB_DATA = load_csv("web_activity.csv")
VEEVA_DATA = load_csv("veeva_activity.csv")
EVENT_DATA = load_csv("event_activity.csv")


# ============================================================
# PAGINATION
# ============================================================

def paginate_data(data, page, limit):

    total_records = len(data)

    total_pages = (
        total_records + limit - 1
    ) // limit

    start = (page - 1) * limit
    end = start + limit

    page_data = data[start:end]

    return {
        "data": page_data,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_records": total_records,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1
        }
    }


# ============================================================
# EMAIL API
# ============================================================

@app.get("/email/activity")
def get_email_activity(
    page: int = Query(1, ge=1),
    limit: int = Query(1000, ge=1, le=10000)
):

    return paginate_data(
        EMAIL_DATA,
        page,
        limit
    )


# ============================================================
# WEB API
# ============================================================

@app.get("/web/activity")
def get_web_activity(
    page: int = Query(1, ge=1),
    limit: int = Query(1000, ge=1, le=10000)
):

    return paginate_data(
        WEB_DATA,
        page,
        limit
    )


# ============================================================
# VEEVA API
# ============================================================

@app.get("/veeva/activity")
def get_veeva_activity(
    page: int = Query(1, ge=1),
    limit: int = Query(1000, ge=1, le=10000)
):

    return paginate_data(
        VEEVA_DATA,
        page,
        limit
    )


# ============================================================
# EVENT API
# ============================================================

@app.get("/event/activity")
def get_event_activity(
    page: int = Query(1, ge=1),
    limit: int = Query(1000, ge=1, le=10000)
):

    return paginate_data(
        EVENT_DATA,
        page,
        limit
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
def root():

    return {
        "status": "running",
        "service": "HCP Engagement Mock APIs",
        "pagination": "Supported",
        "datasets": {
            "email_records": len(EMAIL_DATA),
            "web_records": len(WEB_DATA),
            "veeva_records": len(VEEVA_DATA),
            "event_records": len(EVENT_DATA)
        },
        "endpoints": [
            "/email/activity",
            "/event/activity",
            "/veeva/activity",
            "/web/activity"
        ]
    }
