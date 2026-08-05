import asyncio, json, sys
sys.path.insert(0, "/home/annh45/Desktop/datahub_ai_chatbot/datahub-ai-chatbot")
from ingestion.graphql.client import DataHubGraphQLClient
from ingestion.graphql.queries import GET_DATASET_LINEAGE_QUERY

async def main():
    client = DataHubGraphQLClient(
        gms_url="http://datahub-datahub-gms-quickstart-1:8080",
    )
    urn = "urn:li:dataset:(urn:li:dataPlatform:redshift,dim_warehouse,PROD)"
    for direction in ["UPSTREAM", "DOWNSTREAM"]:
        data = await client.execute(GET_DATASET_LINEAGE_QUERY, {
            "urn": urn, "direction": direction, "start": 0, "count": 100,
        })
        lg = (data.get("dataset") or {}).get("lineage") or {}
        rels = lg.get("relationships") or []
        print(f"== {direction} total={lg.get('total')} ==")
        for r in rels:
            e = r.get("entity") or {}
            print("  ", r.get("type"), e.get("type"), e.get("urn"))
    await client.close()

asyncio.run(main())
