"""Generate data landscape audit artifacts directly from PG + OpenSearch (ground truth from real metadata only)."""
import asyncio
import json
import collections
import os

import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, text
from database.session import async_session_factory
from database.models import Entity, EntityChunk

OUT = os.path.dirname(os.path.abspath(__file__))


def entity_id(urn: str) -> str:
    return urn.split(":")[-1]


async def main() -> None:
    async with async_session_factory() as s:
        r = await s.execute(select(Entity))
        ents = list(r.scalars())
        ds = [e for e in ents if e.entity_type == "dataset"]
        dash = [e for e in ents if e.entity_type == "dashboard"]
        gt = [e for e in ents if e.entity_type == "glossary_term"]
        gn = [e for e in ents if e.entity_type == "glossary_node"]

        # ---------- dataset landscape ----------
        platform_counts = collections.Counter(e.platform for e in ds)
        domain_counts = collections.Counter(e.domain for e in ds)
        env_counts = collections.Counter(e.environment for e in ds)

        def has(payload, key):
            v = (payload or {}).get(key) or []
            return bool(v) if isinstance(v, list) else bool(v)

        dataset_list = []
        for e in ds:
            p = e.payload or {}
            sf = p.get("schema_fields") or []
            dataset_list.append({
                "urn": e.urn,
                "name": e.name,
                "display_name": e.display_name,
                "description": e.description or None,
                "platform": e.platform,
                "environment": e.environment,
                "domain": e.domain,
                "datahub_url": e.datahub_url,
                "schema_field_count": len(sf),
                "owners": [o.get("name") for o in (p.get("owners") or []) if o.get("name")],
                "glossary_term_urns": p.get("glossary_terms") or [],
                "tags": p.get("tags") or [],
                "upstream_urns": p.get("upstreams") or [],
                "downstream_urns": p.get("downstreams") or [],
                "custom_properties": p.get("raw_properties") or {},
                "certified": p.get("certified") or False,
            })

        # ---------- glossary ----------
        glossary_list = []
        for e in gt:
            p = e.payload or {}
            glossary_list.append({
                "urn": e.urn,
                "name": e.name,
                "description": e.description or None,
                "upstream_urns": p.get("upstreams") or [],
                "downstream_urns": p.get("downstreams") or [],
            })
        node_list = []
        for e in gn:
            p = e.payload or {}
            node_list.append({
                "urn": e.urn,
                "name": e.name,
                "description": e.description or None,
            })

        # ---------- dashboard ----------
        dashboard_list = []
        for e in dash:
            p = e.payload or {}
            dashboard_list.append({
                "urn": e.urn,
                "name": e.name,
                "description": e.description or None,
                "platform": e.platform,
                "domain": e.domain,
                "datahub_url": e.datahub_url,
                "owners": [o.get("name") for o in (p.get("owners") or []) if o.get("name")],
                "upstream_urns": p.get("upstreams") or [],
            })

        # ---------- field name inventory (for ambiguity) ----------
        field_counter = collections.Counter()
        field_domains = collections.defaultdict(set)
        for e in ds:
            dom = e.domain or "UNDEFINED"
            for f in (e.payload or {}).get("schema_fields") or []:
                n = (f.get("name") or "").strip()
                if not n or any(x in n for x in ("[version", "DAX", "[table]")):
                    continue
                field_counter[n.lower()] += 1
                field_domains[n.lower()].add(dom)
        top_fields = [{"field": n, "dataset_count": c, "domains": sorted(field_domains[n])}
                      for n, c in field_counter.most_common(200)]

        # ---------- same-name entities ----------
        by_name = collections.defaultdict(list)
        for e in ds:
            by_name[e.name.strip().lower()].append(e.urn)
        same_name_datasets = [{ "name": n, "count": len(u), "urns": u[:20] }
                              for n, u in by_name.items() if len(u) > 1]

        # ---------- name prefix ----------
        import re
        prefix_counter = collections.Counter()
        for e in ds:
            m = re.match(r"^([a-zA-Z]{1,8}_|\[[^\]]+\]_)", e.name)
            if m:
                prefix_counter[m.group(1).lower()] += 1

        # ---------- chunks ----------
        chunk_rows = [(row[0], row[1]) for row in (await s.execute(
            text("SELECT chunk_type, count(*) FROM entity_chunks GROUP BY chunk_type"))).all()]

        # ---------- data completeness ----------
        completeness = {
            "dataset": {
                "total": len(ds),
                "with_description": sum(1 for e in ds if e.description),
                "with_domain": sum(1 for e in ds if e.domain),
                "with_platform": sum(1 for e in ds if e.platform),
                "with_owners": sum(1 for e in ds if has(e.payload, "owners")),
                "with_glossary_terms": sum(1 for e in ds if has(e.payload, "glossary_terms")),
                "with_tags": sum(1 for e in ds if has(e.payload, "tags")),
                "with_upstreams": sum(1 for e in ds if has(e.payload, "upstreams")),
                "with_downstreams": sum(1 for e in ds if has(e.payload, "downstreams")),
                "with_custom_properties": sum(1 for e in ds if has(e.payload, "raw_properties")),
                "schema_fields_zero": sum(1 for e in ds if not (e.payload or {}).get("schema_fields")),
                "schema_fields_total_entries": sum(len((e.payload or {}).get("schema_fields") or []) for e in ds),
            },
            "dashboard": {
                "total": len(dash),
                "with_description": sum(1 for e in dash if e.description),
                "with_domain": sum(1 for e in dash if e.domain),
                "with_owners": sum(1 for e in dash if has(e.payload, "owners")),
                "with_upstreams": sum(1 for e in dash if has(e.payload, "upstreams")),
            },
            "glossary_term": {
                "total": len(gt),
                "with_description": sum(1 for e in gt if e.description),
                "with_domain": sum(1 for e in gt if e.domain),
                "with_parent": sum(1 for e in gt if has(e.payload, "upstreams")),
            },
        }

        # ---------- ground truth snapshot ----------
        gt_snapshot = {
            "schema_version": "1.0",
            "generated_from": ["postgres:chatbot", "opensearch:datahub-rag-chunks-v1"],
            "provenance_note": "All facts derived from pulled DataHub metadata (datahub_pull/*.txt) loaded into PG entities table + OpenSearch chunk index. No LLM-generated metadata. UNKNOWN = no evidence in source data.",
            "entity_counts": {
                "dataset": len(ds),
                "dashboard": len(dash),
                "glossary_term": len(gt),
                "glossary_node": len(gn),
                "total": len(ents),
            },
            "datasets": dataset_list,
            "dashboards": dashboard_list,
            "glossary_terms": glossary_list,
            "glossary_nodes": node_list,
            "completeness": completeness,
            "platform_counts": dict(platform_counts),
            "domain_counts": dict(domain_counts),
            "environment_counts": dict(env_counts),
            "chunk_counts_by_type": dict(chunk_rows),
        }
        with open(os.path.join(OUT, "data_ground_truth.json"), "w", encoding="utf-8") as f:
            json.dump(gt_snapshot, f, ensure_ascii=False, indent=1)

        # ---------- domain semantic map ----------
        dom_map = {}
        # vocabulary per domain derived from real dataset names (heuristic only)
        dom_vocab = collections.defaultdict(collections.Counter)
        for e in ds:
            dom = e.domain
            if not dom:
                continue
            name_low = e.name.lower()
            toks = re.split(r"[\s_\-\.\[\]\(\)/]+", name_low)
            for t in toks:
                if 3 <= len(t) <= 24 and t.isalpha():
                    dom_vocab[dom][t] += 1
        for dom in sorted((d for d in domain_counts if d is not None)):
            dom_upper = dom.upper()
            dom_map[dom] = {
                "dataset_count": domain_counts[dom],
                "dataset_urns": [e.urn for e in ds if e.domain == dom],
                "dataset_names": sorted(e.name for e in ds if e.domain == dom),
                "top_vocabulary": [w for w, _ in dom_vocab[dom].most_common(25)],
                "glossary_terms": [g["name"] for g in glossary_list if (g.get("domain_assignment") == dom)],
                "glossary_nodes": [g["name"] for g in node_list if (g["name"] or "").strip().upper() and
                                   (dom_upper in (g["name"] or "").upper() or (g["name"] or "").upper() in dom_upper or
                                    dom_upper.replace(" ", "") in (g["name"] or "").upper().replace(" ", ""))],
                "dashboards": [{"name": d["name"], "urn": d["urn"]} for d in dashboard_list if d["domain"] == dom],
            }
        # domain-scoped glossary (heuristic assignment: term text -> domain via keyword evidence in description)
        domain_keywords = {
            "SẢN XUẤT": ["kpi logic production", "bom", "ebom", "mbom", "jph", "wip", "production", "sản xuất", "nhà máy", "oee", "ga ", "backflush", "mfg"],
            "TÀI CHÍNH": ["ebitda", "cogs", "capex", "opex", "sg&a", "pbt", "giá vốn", "tài chính", "lợi nhuận", "doanh thu", "cost ", "chi phí tài chính"],
            "KINH DOANH": ["sell in", "sell out", "dealer", "lead", "reservation", "order", "đơn hàng", "bán hàng", "khuyến mãi", "kinh doanh", "sales", "target", "kpi"],
            "HẬU MÃI": ["hậu mãi", "phụ tùng", "spare part", "iptv", "cpv", "warranty", "bảo hành", "repair", "cskh", "sửa chữa", "xdv"],
            "LOGISTIC": ["shipment", "vận chuyển", "inbound", "outbound", "logistic", "coverage", "import", "export", "kho vận", "xuất nhập khẩu"],
            "CUNG ỨNG": ["mrp", "mrd", "mrq", "supplier", "purchase", "pfep", "schedule agreement", "vendor", "mua hàng", "cung ứng", "po ", "pr "],
            "PHÁT TRIỂN XE": ["ecr", "sunk cost", "tooling", "gate", "phát triển xe", "prototype", "development", "bco"],
        }
        domain_scoped_glossary = {}
        for g in glossary_list:
            desc_low = (g["description"] or "").lower()
            name_low = (g["name"] or "").lower()
            matched = []
            for dom, kws in domain_keywords.items():
                if any(k in desc_low or k in name_low for k in kws):
                    matched.append(dom)
            domain_scoped_glossary[g["name"]] = {
                "urn": g["urn"],
                "matched_domains": matched,
                "assignment": matched[0] if len(matched) == 1 else "UNKNOWN" if not matched else "MULTI:" + ",".join(matched),
                "note": "heuristic keyword match on term name/description - NOT metadata ground truth" if matched else "no domain evidence",
            }
        dom_map["_domain_scoped_glossary_heuristic"] = domain_scoped_glossary
        with open(os.path.join(OUT, "domain_semantic_map.json"), "w", encoding="utf-8") as f:
            json.dump(dom_map, f, ensure_ascii=False, indent=1)

        # ---------- asset relationship map ----------
        rel_map = {
            "dataset_to_dataset_upstream": [],
            "dataset_to_dataset_downstream": [],
            "dashboard_to_dataset_input": [],
            "dataset_to_glossary_term": [],
            "glossary_term_to_parent": [],
            "glossary_node_to_term": [],
        }
        for e in ds:
            p = e.payload or {}
            for u in (p.get("upstreams") or []):
                rel_map["dataset_to_dataset_upstream"].append({"dataset_urn": e.urn, "upstream_urn": u})
            for d in (p.get("downstreams") or []):
                rel_map["dataset_to_dataset_downstream"].append({"dataset_urn": e.urn, "downstream_urn": d})
            for t in (p.get("glossary_terms") or []):
                rel_map["dataset_to_glossary_term"].append({"dataset_urn": e.urn, "glossary_term_urn": t})
        for e in dash:
            p = e.payload or {}
            for u in (p.get("upstreams") or []):
                rel_map["dashboard_to_dataset_input"].append({"dashboard_urn": e.urn, "input_urn": u})
        for e in gt:
            p = e.payload or {}
            for u in (p.get("upstreams") or []):
                rel_map["glossary_term_to_parent"].append({"term_urn": e.urn, "parent_urn": u})
        with open(os.path.join(OUT, "asset_relationship_map.json"), "w", encoding="utf-8") as f:
            json.dump(rel_map, f, ensure_ascii=False, indent=1)

        # ---------- retrieval risk map ----------
        risk = {
            "same_name_datasets": same_name_datasets,
            "top_shared_fields": top_fields,
            "duplicate_term_names": [],
            "near_duplicate_term_names": [],
            "same_dataset_prefix": dict(prefix_counter.most_common(40)),
            "glossary_nodes_not_indexed": [g["name"] for g in node_list],
        }
        term_by_name = collections.defaultdict(list)
        for g in glossary_list:
            term_by_name[g["name"].strip().lower()].append(g)
        for n, lst in term_by_name.items():
            if len(lst) > 1:
                risk["duplicate_term_names"].append({"name": lst[0]["name"], "count": len(lst), "urns": [g["urn"] for g in lst]})
        with open(os.path.join(OUT, "retrieval_risk_map.json"), "w", encoding="utf-8") as f:
            json.dump(risk, f, ensure_ascii=False, indent=1)

        # ---------- benchmark source inventory ----------
        bench = {
            "inventory": [],
        }
        # curated: per-domain representative datasets
        seen = set()
        for dom in sorted((d for d in domain_counts if d is not None)):
            names = sorted(e.name for e in ds if e.domain == dom)
            for n in names[:20]:
                e = next(x for x in ds if x.name == n and x.domain == dom)
                if e.urn in seen:
                    continue
                seen.add(e.urn)
                bench["inventory"].append({
                    "domain": dom,
                    "name": e.name,
                    "urn": e.urn,
                    "platform": e.platform,
                    "has_description": bool(e.description),
                    "schema_field_count": len((e.payload or {}).get("schema_fields") or []),
                    "datahub_url": e.datahub_url,
                })
        # glossary terms
        for g in glossary_list:
            bench["inventory"].append({
                "type": "glossary_term",
                "name": g["name"],
                "urn": g["urn"],
                "has_description": bool(g["description"]),
            })
        # dashboards with description or domain
        for d in dashboard_list:
            if d["description"] or d["domain"]:
                bench["inventory"].append({
                    "type": "dashboard",
                    "name": d["name"],
                    "urn": d["urn"],
                    "platform": d["platform"],
                    "domain": d["domain"],
                    "has_description": bool(d["description"]),
                })
        with open(os.path.join(OUT, "benchmark_source_inventory.json"), "w", encoding="utf-8") as f:
            json.dump(bench, f, ensure_ascii=False, indent=1)

        print("OK entities=%d datasets=%d dashboards=%d terms=%d nodes=%d" % (len(ents), len(ds), len(dash), len(gt), len(gn)))
        print("same-name dataset groups:", len(same_name_datasets))
        print("shared fields listed:", len(top_fields))


asyncio.run(main())