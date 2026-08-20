import json
import sys
import time
import urllib.request

BASE = "http://localhost:8000"
CASES = "audit/test_cases_26.jsonl"
RAW_OUT = "audit/test_harness/raw_26.jsonl"
VERDICT_OUT = "audit/test_harness/verdicts_26.jsonl"

import uuid


def http_json(method, path, payload=None, token=None, timeout=150):
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    return data, time.time() - t0


def abstention_marker(answer):
    low = answer.lower()
    markers = [
        "không tìm thấy", "không có thông tin", "chưa có", "không xác định",
        "không có dữ liệu", "không tồn tại", "no lineage", "no owner",
        "không có upstream", "không có downstream", "không có mô tả",
        "i couldn't find", "không thể", "xin lỗi", "no description",
        "không có owner", "không lưu", "unknown", "unavailable",
    ]
    return any(m in low for m in markers)


def present(sub, hay):
    return sub.lower() in hay.lower()


def evaluate(case, last):
    reasons = []
    exp = case.get("expect", {})
    ans = last.get("answer", "")
    ent_names = " | ".join(e.get("name", "") for e in last.get("entities", []) or [])
    ents = " | ".join(e.get("entity_name", "") for e in last.get("citations", []) or [])
    hay = f"{ans} | {ent_names} | {ents}"

    if abstention_marker(ans):
        if exp.get("abstain_ok", False):
            pass
        else:
            if not exp.get("must_not"):
                reasons.append("abstained_but_not_allowed")
            else:
                for m in exp.get("must_not", []):
                    if present(m, ans):
                        pass
                if exp.get("entities") or exp.get("fields") or exp.get("terms") or exp.get("type_markers"):
                    missing = []
                    if exp.get("entities") and not any(present(e, hay) for e in exp["entities"]):
                        missing.append("entities")
                    if exp.get("fields") and not any(present(f, ans) for f in exp["fields"]):
                        missing.append("fields")
                    if exp.get("terms") and not any(present(t, ans) for t in exp["terms"]):
                        missing.append("terms")
                    if exp.get("type_markers") and not any(present(t, ans) for t in exp["type_markers"]):
                        missing.append("type_markers")
                    if missing:
                        reasons.append("abstained_and_missing_" + "_".join(missing))
    else:
        for m in exp.get("must_not", []):
            if present(m, ans):
                reasons.append(f"forbidden_marker:{m}")
        if exp.get("entities") and not any(present(e, hay) for e in exp["entities"]):
            reasons.append("missing_entities")
        if exp.get("fields") and not any(present(f, ans) for f in exp["fields"]):
            reasons.append("missing_fields")
        if exp.get("terms") and not any(present(t, ans) for t in exp["terms"]):
            reasons.append("missing_terms")
        if exp.get("type_markers") and not any(present(t, ans) for t in exp["type_markers"]):
            reasons.append("missing_type_marker")
        if exp.get("domain_marker") and not present(exp["domain_marker"], ans):
            reasons.append("missing_domain_marker")

    if exp.get("intent_in"):
        if last.get("intent") not in exp["intent_in"]:
            reasons.append(f"intent_mismatch:{last.get('intent')}")

    if exp.get("lineage_honest") or exp.get("owner_honest") or exp.get("honest_no_desc"):
        if not reasons and len(ans) > 260:
            reasons.append("possible_fabrication_long_answer")

    pass_ = len(reasons) == 0
    return pass_, "; ".join(reasons)


def main():
    with open(CASES) as f:
        cases = [json.loads(l) for l in f if l.strip()]
    token_data, _ = http_json("POST", "/api/v1/auth/login",
                              {"username": "admin", "password": "admin123"})
    token = token_data["token"]

    raw_rows = []
    verdicts = []
    for case in cases:
        cid = str(uuid.uuid4())
        turns = []
        for i, q in enumerate(case["turn_questions"]):
            body = {"question": q, "conversation_id": cid}
            try:
                resp, dt = http_json("POST", "/api/v1/chat", body, token)
                turns.append({"index": i, "question": q, "response": resp, "elapsed": round(dt, 2)})
            except Exception as exc:
                turns.append({"index": i, "question": q, "error": str(exc)})
        last = turns[-1].get("response", {}) if turns else {}
        last_ans = last.get("answer", "")
        if not last_ans and turns and "error" in turns[-1]:
            last_ans = turns[-1].get("error", "")
        pass_, reason = evaluate(case, last)
        verdict = {
            "id": case["id"], "category": case["category"],
            "intent": last.get("intent"), "answer_path": last.get("answer_path"),
            "pass": pass_, "reason": reason,
            "confidence": last.get("confidence"), "ambiguous": last.get("ambiguous"),
            "insufficient_context": last.get("insufficient_context"),
            "answer_chars": len(last_ans), "turns": len(case["turn_questions"]),
        }
        verdicts.append(verdict)
        raw_rows.append({"case": case, "conversation_id": cid, "turns": turns, "verdict": verdict})
        status = "PASS" if pass_ else "FAIL"
        intt = last.get("intent") or "-"
        path = last.get("answer_path") or "-"
        print(f"[{status}] {case['id']:<4} intent={intt:<20} path={path:<20} "
              f"chars={len(last_ans):<5} {reason}")

    import os
    os.makedirs("audit/test_harness", exist_ok=True)
    with open(RAW_OUT, "w") as f:
        for r in raw_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(VERDICT_OUT, "w") as f:
        for v in verdicts:
            f.write(json.dumps(v, ensure_ascii=False) + "\n")

    npass = sum(1 for v in verdicts if v["pass"])
    print(f"\n=== {npass}/{len(verdicts)} PASS ===")
    fails = [v["id"] for v in verdicts if not v["pass"]]
    print("FAILS:", fails)


if __name__ == "__main__":
    main()
