import requests
import random
import time


def buildNextPageQuery(cursor: str):
    if cursor is None:
        return ""
    return ', after:"{0}"'.format(cursor)


def runGraphqlRequest(pat: str, query: str, max_retries: int = 5):
    headers = {"Authorization": "Bearer {0}".format(pat)}

    for attempt in range(max_retries):
        sleepTime = random.randint(1, 4)
        time.sleep(sleepTime)

        try:
            request = requests.post(
                "https://api.github.com/graphql", json={"query": query}, headers=headers,
                timeout=30
            )
        except requests.exceptions.RequestException as e:
            print(f"  [Retry {attempt+1}/{max_retries}] Network error: {e}")
            time.sleep(2 ** attempt)
            continue

        if request.status_code == 200:
            json_data = request.json()
            if "data" in json_data:
                return json_data["data"]
            # GraphQL can return 200 with errors
            if "errors" in json_data:
                print(f"  [Retry {attempt+1}/{max_retries}] GraphQL error: {json_data['errors'][0].get('message', 'unknown')}")
                time.sleep(2 ** attempt)
                continue

        # Rate limit (403) or server error (502/503) — wait and retry
        if request.status_code in (403, 429, 502, 503):
            wait_time = 2 ** (attempt + 2)  # 4, 8, 16, 32, 64 seconds
            if request.status_code in (403, 429):
                # Check for rate limit reset header
                reset_time = request.headers.get("X-RateLimit-Reset")
                if reset_time:
                    wait_time = max(int(reset_time) - int(time.time()), 10)
                    wait_time = min(wait_time, 300)  # cap at 5 min
            print(f"  [Retry {attempt+1}/{max_retries}] HTTP {request.status_code}, waiting {wait_time}s...")
            time.sleep(wait_time)
            continue

        raise Exception(
            "Query execution failed with code {0}: {1}".format(
                request.status_code, request.text
            )
        )

    raise Exception(f"Query failed after {max_retries} retries")


def addLogin(node, authors: list):
    login = extractAuthorLogin(node)

    if not login is None:
        authors.append(login)


def extractAuthorLogin(node):
    if node is None or not "login" in node or node["login"] is None:
        return None

    return node["login"]
