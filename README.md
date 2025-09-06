# LeetCode Profile Scraper API

A FastAPI application that scrapes LeetCode profile data using BeautifulSoup4.

## Features

- Scrape LeetCode user profiles
- Extract user information including:
  - Name and username
  - Profile rank
  - Avatar image URL
  - Location and university
  - GitHub and LinkedIn profiles
  - Skills/tags
- RESTful API endpoints
- Error handling and validation

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Running the Server

```bash
python main.py
```

The server will start on `http://localhost:8000`

### API Endpoints

#### 1. Health Check
```
GET /health
```

#### 2. Scrape Profile (POST)
```
POST /scrape-profile
Content-Type: application/json

{
    "username": "Raushan2288"
}
```

#### 3. Scrape Profile (GET)
```
GET /scrape-profile/{username}
```

### Example Usage

#### Using curl:
```bash
# POST request
curl -X POST "http://localhost:8000/scrape-profile" \
     -H "Content-Type: application/json" \
     -d '{"username": "Raushan2288"}'

# GET request
curl "http://localhost:8000/scrape-profile/Raushan2288"
```

#### Using Python requests:
```python
import requests

# POST request
response = requests.post(
    "http://localhost:8000/scrape-profile",
    json={"username": "Raushan2288"}
)
profile_data = response.json()

# GET request
response = requests.get("http://localhost:8000/scrape-profile/Raushan2288")
profile_data = response.json()
```

### Response Format

```json
{
    "name": "Raushan Kumar",
    "username": "Raushan2288",
    "rank": "8,06,824",
    "avatar_url": "https://assets.leetcode.com/users/Raushan2288/avatar_1716696348.png",
    "location": "India",
    "university": "shri ramswaroop memorial university",
    "github": "raushan22882917",
    "linkedin": "RaushanKumar",
    "skills": ["python", "java-10", "dsa", "dbms", "aida"]
}
```

## API Documentation

Once the server is running, you can access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Error Handling

The API includes comprehensive error handling:
- 400: Bad Request (invalid username or network issues)
- 404: Profile not found
- 500: Internal server error

## Dependencies

- FastAPI: Web framework
- BeautifulSoup4: HTML parsing
- Requests: HTTP client
- Pydantic: Data validation
- Uvicorn: ASGI server

## Notes

- The scraper uses appropriate headers to mimic a real browser
- Rate limiting is recommended for production use
- LeetCode may block requests if too many are made in a short time
- Some profile data may not be available for private profiles