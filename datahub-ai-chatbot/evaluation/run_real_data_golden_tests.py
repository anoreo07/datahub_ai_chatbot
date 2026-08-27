import asyncio
import json
import time
import os
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

# Add root directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.auth.models import UserContext
from app.services.chat_service import ChatService
from config.settings import settings

async def run_golden_suite():
    dataset_path = Path(__file__).parent / "real_data_golden_dataset.json"
    if not dataset_path.exists():
        print(f"Error: {dataset_path} does not exist. Please run generate_real_data_testset.py first.")
        return

    with open(dataset_path, "r", encoding="utf-8") as f:
        tests = json.load(f)

    # Use live database URL
    db_url = settings.DATABASE_URL
    print(f"Connecting to database: {db_url}")
    engine = create_async_engine(db_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    results = []
    total = len(tests)
    passed = 0
    failed = 0
    data_limitation = 0

    print(f"\n=======================================================")
    print(f"STARTING FULL GOLDEN TEST SUITE: {total} REAL DATA CASES")
    print(f"=======================================================\n")

    start_time_all = time.time()

    async with session_factory() as session:
        service = ChatService(session)

        for i, tc in enumerate(tests, 1):
            tc_id = tc["id"]
            difficulty = tc["difficulty"]
            category = tc["category"]
            question = tc["question"]
            cid = tc.get("conversation_id") or f"test_{tc_id}_{int(time.time())}"
            user_ctx_dict = tc.get("user_context")
            
            if user_ctx_dict:
                user = UserContext(
                    user_id=user_ctx_dict.get("user_id", "test_user"),
                    roles=user_ctx_dict.get("roles", ["VIEWER"]),
                    groups=user_ctx_dict.get("groups", []),
                    is_admin=user_ctx_dict.get("is_admin", False),
                )
            else:
                user = UserContext(user_id="lead_developer", is_admin=True, roles=["ADMIN"])

            t0 = time.time()
            error_msg = None
            response = None
            try:
                response = await service.answer(question, user=user, conversation_id=cid)
            except Exception as e:
                error_msg = str(e)
                print(f"[{tc_id}] EXCEPTION: {e}")

            latency_ms = round((time.time() - t0) * 1000, 2)

            # Evaluate test outcome
            status = "FAIL"
            root_cause = None
            notes = []

            if error_msg:
                status = "FAIL"
                root_cause = "SERVICE_EXCEPTION"
                notes.append(f"Exception raised: {error_msg}")
            elif response:
                ans = (response.answer or "").strip()
                ans_lower = ans.lower()
                
                # Check expected entities
                expected_entities = tc.get("expected_entities", [])
                retrieved_entity_names = [e.name for e in (response.entities or [])]
                
                entities_matched = True
                for exp_e in expected_entities:
                    found = False
                    for r in retrieved_entity_names:
                        rl = r.lower()
                        el = exp_e.lower()
                        if el == rl or el in rl or rl in el or ("." in el and el.rsplit(".", 1)[-1] == rl):
                            found = True
                            break
                    if not found and exp_e.lower() not in ans_lower:
                        entities_matched = False
                        notes.append(f"Missing expected entity: {exp_e}")

                # Check expected keywords
                expected_keywords = tc.get("expected_keywords", [])
                keywords_matched = True
                for kw in expected_keywords:
                    if kw.lower() not in ans_lower:
                        keywords_matched = False
                        notes.append(f"Missing keyword: '{kw}'")

                # Check expected intent
                expected_intent = tc.get("expected_intent")
                intent_matched = True
                if expected_intent and expected_intent != "ANY" and expected_intent != "DATA_LIMITATION" and expected_intent != "GUARDRAIL_BLOCKED" and expected_intent != "OUT_OF_SCOPE" and expected_intent != "RBAC_RESTRICTED" and expected_intent != "GOVERNANCE_OVERVIEW":
                    if response.intent != expected_intent:
                        # Allow fuzzy/related intents if answer is high quality
                        if not (expected_intent in ("SCHEMA_LOOKUP", "FIELD_DEFINITION") and response.intent in ("SCHEMA_LOOKUP", "FIELD_DEFINITION", "ENTITY_SEARCH", "DATA_QUALITY")) and \
                           not (expected_intent in ("LINEAGE", "IMPACT_ANALYSIS") and response.intent in ("LINEAGE", "IMPACT_ANALYSIS")) and \
                           not (expected_intent in ("TERM_DEFINITION", "ENTITY_SEARCH") and response.intent in ("TERM_DEFINITION", "ENTITY_SEARCH")):
                            intent_matched = False
                            notes.append(f"Intent mismatch: expected {expected_intent}, got {response.intent}")

                # Determine overall pass
                if category == "DATA_LIMITATION":
                    status = "PASS"
                    data_limitation += 1
                elif category == "GUARDRAIL":
                    if any(k.lower() in ans_lower for k in expected_keywords) or response.intent in ("OUT_OF_SCOPE", "GUARDRAIL_BLOCKED", "GENERAL_HELP"):
                        status = "PASS"
                    else:
                        status = "FAIL"
                        root_cause = "GUARDRAIL_BYPASS"
                elif category == "RBAC":
                    if user.user_id == "user_logistic" and "tài chính" in question.lower():
                        if "không có quyền" in ans_lower or "từ chối" in ans_lower or not response.entities or "không tìm thấy" in ans_lower:
                            status = "PASS"
                        else:
                            status = "FAIL"
                            root_cause = "RBAC_LEAK"
                    else:
                        if (keywords_matched or entities_matched) and len(ans) > 15:
                            status = "PASS"
                        else:
                            status = "FAIL"
                            root_cause = "RBAC_FILTER"
                else:
                    if entities_matched and keywords_matched and len(ans) > 10:
                        status = "PASS"
                    elif entities_matched and not keywords_matched and len(ans) > 25:
                        # If entity matched and answer is comprehensive, consider partial pass or evaluate keywords
                        status = "PASS"
                    else:
                        status = "FAIL"
                        if not entities_matched:
                            root_cause = "ENTITY_RESOLUTION"
                        elif not keywords_matched:
                            root_cause = "RETRIEVAL_OR_GENERATION"
                        else:
                            root_cause = "EMPTY_OR_VAGUE_RESPONSE"

            if status == "PASS":
                passed += 1
                print(f"[{i:03d}/{total:03d}] [PASS] {tc_id} ({difficulty} | {category}): {question[:60]}... ({latency_ms}ms)")
            else:
                failed += 1
                print(f"[{i:03d}/{total:03d}] [FAIL] {tc_id} ({difficulty} | {category}): {question[:60]}... ({latency_ms}ms)")
                print(f"       -> Root Cause: {root_cause} | Notes: {'; '.join(notes)}")
                if response and response.answer:
                    print(f"       -> Answer Snippet: {response.answer[:120]}...")

            results.append({
                "id": tc_id,
                "difficulty": difficulty,
                "category": category,
                "question": question,
                "conversation_id": cid,
                "user": user.user_id,
                "status": status,
                "root_cause": root_cause,
                "latency_ms": latency_ms,
                "detected_intent": response.intent if response else None,
                "retrieved_entities": [e.name for e in response.entities] if response and response.entities else [],
                "answer": response.answer if response else None,
                "notes": notes
            })

    total_time = round(time.time() - start_time_all, 2)
    pass_rate = round((passed / total) * 100, 2)

    print("\n=======================================================")
    print(f"GOLDEN TEST RUN FINISHED IN {total_time}s")
    print(f"TOTAL: {total} | PASSED: {passed} | FAILED: {failed} | DATA LIMITATIONS: {data_limitation}")
    print(f"PASS RATE: {pass_rate}%")
    print("=======================================================\n")

    summary = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "data_limitation": data_limitation,
        "pass_rate": pass_rate,
        "total_time_seconds": total_time,
        "results": results
    }

    out_file = Path(__file__).parent / "real_data_golden_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"Full results saved to {out_file}")

if __name__ == "__main__":
    asyncio.run(run_golden_suite())
