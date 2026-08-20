"""Diagnose which search query/fragment triggers corporate 500.

Run: .venv/bin/python scripts/diag_search.py
Uses token from .env. Makes several GraphQL calls to corporate DataHub.
"""
import json
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

URL = (os.environ.get("DATAHUB_GMS_URL") or "").rstrip("/").removesuffix("/api/graphql")
TOKEN = os.environ.get("DATAHUB_TOKEN") or ""

USER_AGENT = "DataAtlas-MetadataSync/2.0 (internal metadata mirror; contact: dataatlas team)"

DATASET_VARIANTS = {
    "name-only (baseline, known OK)": """... on Dataset { name }""",
    "+properties": """... on Dataset { name properties { name qualifiedName origin description } }""",
    "+editableProperties": """... on Dataset { name editableProperties { description } }""",
    "+platform": """... on Dataset { name platform { name urn } }""",
    "+domain": """... on Dataset { name domain { domain { urn properties { name description } } } }""",
    "+glossaryTerms": """... on Dataset { name glossaryTerms { terms { term { urn name properties { name description } } } } }""",
    "+tags": """... on Dataset { name tags { tags { tag { urn name } } } }""",
    "+schemaMetadata": """... on Dataset { name schemaMetadata { fields { fieldPath description nativeDataType type nullable isPartOfKey } } }""",
    "full (build_search_query)": """... on Dataset {
        properties { name qualifiedName origin description }
        editableProperties { description }
        platform { name urn }
        domain { domain { urn properties { name description } } }
        glossaryTerms { terms { term { urn name properties { name description } } } }
        tags { tags { tag { urn name } } }
        schemaMetadata { fields { fieldPath description nativeDataType type nullable isPartOfKey } }
      }""",
}

MULTI_FRAGMENT = """... on Dataset { name }
        ... on Dashboard { properties { name } }
        ... on GlossaryTerm { properties { name } }
        ... on Chart { properties { name } }
        ... on DataFlow { properties { name } }
        ... on DataJob { properties { name } }
        ... on Container { properties { name } }
        ... on MLModel { name }
        ... on Tag { name }"""


def make_query(frag: str) -> str:
    return f"""query search($query: String!, $count: Int, $start: Int) {{
  search(input: {{ type: DATASET, query: $query, count: $count, start: $start }}) {{
    total
    searchResults {{
      entity {{
        urn
        type
        {frag}
      }}
    }}
  }}
}}"""


def call(q: str, count: int = 5) -> str:
    r = requests.post(
        f"{URL}/api/graphql",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TOKEN}",
        },
        json={"query": q, "variables": {"query": "*", "count": count, "start": 0}},
        timeout=90,
    )
    if r.status_code != 200:
        return f"HTTP {r.status_code}: {r.text[:120]}"
    data = r.json()
    if "errors" in data and data["errors"]:
        err = data["errors"][0]
        ext = (err.get("extensions") or {}).get("classification") or ""
        return f"500 {ext}: {err.get('message','')[:100]}"
    total = (data.get("data") or {}).get("search", {}).get("total")
    return f"OK total={total}"


def call_session(q: str, count: int = 5) -> str:
    """Y hệt client.py: requests.Session + UA + Accept + Content-Type + timeout=30."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
        "Authorization": f"Bearer {TOKEN}",
    })
    r = session.post(
        f"{URL}/api/graphql",
        json={"query": q, "variables": {"query": "*", "count": count, "start": 0}},
        timeout=30,
    )
    if r.status_code != 200:
        return f"HTTP {r.status_code}: {r.text[:120]}"
    data = r.json()
    if "errors" in data and data["errors"]:
        err = data["errors"][0]
        ext = (err.get("extensions") or {}).get("classification") or ""
        return f"500 {ext}: {err.get('message','')[:100]}"
    total = (data.get("data") or {}).get("search", {}).get("total")
    return f"OK total={total}"


async def call_graphqlclient(q: str, count: int = 5) -> str:
    """Dùng đúng GraphQLClient class (code path full_sync)."""
    from ingestion.graphql.client import GraphQLClient

    async with GraphQLClient() as client:
        data = await client.execute(q, {"query": "*", "count": count, "start": 0})
    total = (data.get("search") or {}).get("total")
    return f"OK total={total}"


FULL_DATASET = DATASET_VARIANTS["full (build_search_query)"]


def main() -> None:
    print(f"URL: {URL}")
    print(f"Token: {'present' if TOKEN else 'MISSING'}")
    print()
    for name, frag in DATASET_VARIANTS.items():
        res = call(make_query(frag))
        print(f"[{name:<30}] {res}")
        time.sleep(0.5)
    print()
    print("[count sweep on FULL fragment]:")
    for count in (100, 50, 20, 10, 5, 1):
        res = call(make_query(FULL_DATASET), count=count)
        print(f"[count={count:<4}] {res}")
        time.sleep(0.5)
    print()
    print(f"[{'multi-fragment (MINIMAL fallback)':<30}] {call(make_query(MULTI_FRAGMENT))}")
    print()
    print("[client.py comparison on FULL fragment, count=100]:")
    print(f"[{'plain requests.post':<30}] {call(make_query(FULL_DATASET), count=100)}")
    time.sleep(0.5)
    print(f"[{'requests.Session + UA hdrs':<30}] {call_session(make_query(FULL_DATASET), count=100)}")
    time.sleep(0.5)
    import asyncio

    try:
        res = asyncio.run(call_graphqlclient(make_query(FULL_DATASET), count=100))
        print(f"[{'GraphQLClient.execute':<30}] {res}")
    except Exception as exc:
        print(f"[{'GraphQLClient.execute':<30}] EXC {type(exc).__name__}: {str(exc)[:200]}")


if __name__ == "__main__":
    main()
