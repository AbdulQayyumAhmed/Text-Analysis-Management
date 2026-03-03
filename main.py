from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
import string
import json
import os

app = FastAPI()

DATA_FILE = "users.json"
ANALYSIS_FILE = "analysis.json"

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as file:
        users = json.load(file)
        users = {int(k): v for k, v in users.items()}  
else:
    users = {}

if users:
    next_user_id = max(users.keys()) + 1
else:
    next_user_id = 1

def save_users_to_file():
    with open(DATA_FILE, "w") as file:
        json.dump(users, file, indent=4)

def save_analysis_to_file(analysis_data):
    if os.path.exists(ANALYSIS_FILE):
        with open(ANALYSIS_FILE, "r") as f:
            all_analysis = json.load(f)
    else:
        all_analysis = []
    all_analysis.append(analysis_data)
    with open(ANALYSIS_FILE, "w") as f:
        json.dump(all_analysis, f, indent=4)

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    text: str

class TextInput(BaseModel):
    text: str

@app.post("/users", status_code=201)
def create_user(user: UserCreate):
    global next_user_id

    for existing_user in users.values():
        if existing_user["email"] == user.email:
            raise HTTPException(status_code=400, detail="Email already exists")

    text = user.text.strip()

    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    if len(text) > 200:
        raise HTTPException(status_code=400, detail="Text cannot exceed 200 characters")

    analysis = []

    user_data = {
        "name": user.name,
        "email": user.email,
        "text": text,
        "analyses": analysis
    }

    users[next_user_id] = user_data
    save_users_to_file()

    created_user = {"user_id": next_user_id, **user_data}

    next_user_id += 1

    return created_user

@app.post("/users/{userid}/analyses", status_code=201)
def add_new_analysis(userid: int, text_data: TextInput):

    if userid not in users:
        raise HTTPException(status_code=404, detail="User not found")

    text = text_data.text.strip()

    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    if len(text) > 200:
        raise HTTPException(status_code=400, detail="Text cannot exceed 200 characters")

    word_count = len(text.split())
    uppercase_count = sum(1 for char in text if char.isupper())
    special_char_count = sum(1 for char in text if char in string.punctuation)

    analysis_id = len(users[userid]["analyses"]) + 1

    analysis = {
        "analysis_id": analysis_id,
        "text": text,
        "word_count": word_count,
        "uppercase_count": uppercase_count,
        "special_char_count": special_char_count
    }

    users[userid]["analyses"].append(analysis)

    save_users_to_file()
    save_analysis_to_file({"user_id": userid, **analysis})

    return analysis

@app.get("/users")
def get_all_users(limit: int = 10, offset: int = 0, sort: str = "asc"):
    if limit <= 0:
        raise HTTPException(status_code=400, detail="Limit must be positive")

    if offset < 0:
        raise HTTPException(status_code=400, detail="Offset must be zero or positive")
    
    if sort not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="Sort must be 'asc' or 'desc'")
    

    users_list = [
    {"user_id": user_id, **user_data}
    for user_id, user_data in users.items()
]
    
    reverse_order = True if sort == "desc" else False

    users_list = sorted(users_list, key=lambda x: x["user_id"], reverse=reverse_order)
    
    paginated_users = users_list[offset: offset + limit]
    return paginated_users

@app.get("/users/{userid}")
def get_single_user(userid: int):
    if userid not in users:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": userid, **users[userid]}

@app.delete("/users/{userid}")
def delete_user(userid: int):
    if userid not in users:
        raise HTTPException(status_code=404, detail="User not found")
    del users[userid]
    save_users_to_file()
    return {"message": f"User {userid} deleted successfully"}

@app.get("/analyze/{userid}")
def analyze_user_text(userid: int):
    if userid not in users:
        raise HTTPException(status_code=404, detail="User not found")

    text = users[userid]["text"].strip()
    if not text:
        raise HTTPException(status_code=400, detail="User text is empty")
    if len(text) > 200:
        raise HTTPException(status_code=400, detail="Text cannot exceed 200 characters")

    word_count = len(text.split())
    uppercase_count = sum(1 for char in text if char.isupper())
    special_char_count = sum(1 for char in text if char in string.punctuation)

    analysis_id = len(users[userid]["analyses"]) + 1
    analysis = {
        "analysis_id": analysis_id,
        "text": text,
        "word_count": word_count,
        "uppercase_count": uppercase_count,
        "special_char_count": special_char_count
    }

    users[userid]["analyses"].append(analysis)
    save_users_to_file()
    save_analysis_to_file({"user_id": userid, **analysis})

    return analysis


@app.get("/users/{userid}/analyses")
def get_user_analyses(
    userid: int,
    limit: int = 10,
    offset: int = 0,
    sort: str = "asc",
    min_words: int = 0
):

    if userid not in users:
        raise HTTPException(status_code=404, detail="User not found")

    if limit <= 0:
        raise HTTPException(status_code=400, detail="Limit must be positive")

    if offset < 0:
        raise HTTPException(status_code=400, detail="Offset must be zero or positive")

    if sort not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="Sort must be 'asc' or 'desc'")

    if min_words < 0:
        raise HTTPException(status_code=400, detail="min_words must be zero or positive")

    analyses = users[userid]["analyses"]

    filtered_analyses = [
        analysis for analysis in analyses
        if analysis["word_count"] >= min_words
    ]

    if not filtered_analyses:
        raise HTTPException(status_code=404, detail="No analyses found for this user")

    reverse_order = True if sort == "desc" else False
    sorted_analyses = sorted(
        filtered_analyses,
        key=lambda x: x["analysis_id"],
        reverse=reverse_order
    )

    paginated_analyses = sorted_analyses[offset: offset + limit]

    return paginated_analyses