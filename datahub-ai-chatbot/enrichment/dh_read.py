"""DataHub GraphQL reader — dumps full current state to JSON.

READ phase: canonical source of truth from DataHub.
Usage: python enrichment/dh_read.py [output.json]
"""
from __future__ import annotations

import asyncio
import json
import sys

import httpx

GMS = "http://localhost:8080/api/graphql"

SCROLL = """
query scrollAcrossEntities($input: ScrollAcrossEntitiesInput!) {
  scrollAcrossEntities(input: $input) {
    nextScrollId
    total
    searchResults {
      entity {
        urn
        type
        ... on Dataset {
          name
          properties { description customProperties { key value } }
          editableProperties { description }
          platform { name urn }
          ownership {
            owners {
              type
              owner {
                ... on CorpUser { urn username properties { displayName email } }
                ... on CorpGroup { urn name properties { displayName email } }
              }
            }
          }
          schemaMetadata {
            name
            platformUrn
            version
            fields {
              fieldPath
              description
              nativeDataType
              type
              nullable
              isPartOfKey
              isPartitioningKey
              glossaryTerms { terms { term { urn name } } }
              tags { tags { tag { name urn } } }
            }
            primaryKeys
            foreignKeys {
              name
              sourceFields { fieldPath }
              foreignFields { fieldPath }
              foreignDataset { urn }
            }
          }
          domain { domain { urn properties { name description } } }
          glossaryTerms { terms { term { urn name } } }
          tags { tags { tag { name urn } } }
        }
        ... on GlossaryTerm {
          properties { name description }
          ownership {
            owners {
              type
              owner {
                ... on CorpUser { urn username properties { displayName email } }
                ... on CorpGroup { urn name properties { displayName email } }
              }
            }
          }
          domain { domain { urn properties { name description } } }
          parentNodes { nodes { urn properties { name } } }
        }
        ... on GlossaryNode {
          properties { name description }
          parentNodes { nodes { urn properties { name } } }
        }
      }
    }
  }
}
"""

GET_DATASET_LINEAGE = """
query getDatasetLineage($urn: String!, $direction: LineageDirection!, $count: Int) {
  dataset(urn: $urn) {
    urn
    lineage(input: { direction: $direction, count: $count }) {
      total
      relationships {
        type
        entity { urn type }
      }
    }
  }
}
"""

GET_GLOSSARY_TERM = """
query getGlossaryTerm($urn: String!) {
  glossaryTerm(urn: $urn) {
    urn
    properties { name description }
    ownership { owners { type owner { urn ... on CorpUser { username } ... on CorpGroup { name } } } }
    domain { domain { urn properties { name description } } }
    parentNodes { nodes { urn properties { name } } }
    relatedEntities {
      total
      relationships { entity { urn type name } }
    }
  }
}
"""


async def _post(client: httpx.AsyncClient, q: str, v: dict | None = None) -> dict:
    r = await client.post(GMS, json={"query": q, "variables": v or {}})
    r.raise_for_status()
    data = r.json()
    if data.get("errors"):
        raise RuntimeError(f"GraphQL errors: {data['errors']}")
    return data.get("data") or {}


async def scroll_all(client: httpx.AsyncClient, etype: str) -> list[dict]:
    out: list[dict] = []
    cursor: str | None = None
    while True:
        data = await _post(
            client,
            SCROLL,
            {"input": {"types": [etype], "query": "*", "count": 200, "scrollId": cursor, "orFilters": []}},
        )
        scroll = data["scrollAcrossEntities"]
        for hit in scroll.get("searchResults", []):
            out.append(hit.get("entity", {}))
        cursor = scroll.get("nextScrollId")
        if not cursor:
            break
    return out


async def main() -> None:
    out_path = sys.argv[1] if len(sys.argv) > 1 else "datahub_snapshot_current.json"
    async with httpx.AsyncClient(timeout=60) as client:
        datasets = await scroll_all(client, "DATASET")
        print(f"datasets: {len(datasets)}")
        glossary = await scroll_all(client, "GLOSSARY_TERM")
        print(f"glossary terms: {len(glossary)}")

        # lineage per dataset
        lineage = {}
        for i, ds in enumerate(datasets):
            urn = ds["urn"]
            up = await _post(client, GET_DATASET_LINEAGE, {"urn": urn, "direction": "UPSTREAM", "count": 500})
            dn = await _post(client, GET_DATASET_LINEAGE, {"urn": urn, "direction": "DOWNSTREAM", "count": 500})
            lineage[urn] = {
                "upstream": up.get("dataset", {}).get("lineage", {}),
                "downstream": dn.get("dataset", {}).get("lineage", {}),
            }
            if (i + 1) % 25 == 0:
                print(f"lineage {i + 1}/{len(datasets)}")

    payload = {
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "gms": GMS,
        "datasets": datasets,
        "lineage": lineage,
        "glossary_terms": glossary,
    }
    with open(out_path, "w") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
    print(f"wrote {out_path} ({len(datasets)} datasets, {len(glossary)} terms)")


if __name__ == "__main__":
    asyncio.run(main())
