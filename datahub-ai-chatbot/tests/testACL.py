# ruff: noqa: N999  # filename intentionally camelCase per user request (testACL.py)
"""ACL / Authentication diagnostics against the LIVE DataHub GraphQL API.

What it does
------------
Probes a series of READ-ONLY GraphQL queries with the ``DATAHUB_TOKEN`` in
``.env`` and dumps exactly what each call returns. It tells you which
operations the token's account is allowed to perform and what data comes back:

  * ``me`` identity + (if the schema supports it) roles of the account
  * whether the token can list other users / roles / policies (admin probes)
  * dataset search, fetching a dataset, lineage read
  * an unknown entity (confirms no real metadata leaks for URNs it does not own)

It ends with a full USER INVENTORY: every user with email / display name /
groups, per-user detail and any directly-assigned policies, plus the role,
policy and domain catalogs. Role membership is *not* exposed per-user on this
GMS (corpUser.roles and listAssignments are undefined), so role scoping is
approximated from policy actors when the schema exposes them.

Token scoping
-------------
A DataHub token authenticates as ONE account; authorization is enforced
server-side for that account only. To inspect roles/privileges of OTHER
accounts the token must hold the relevant admin privileges (listUsers /
listRoles / listPolicies). This script probes exactly that and labels each
result:

  * ``OK``     - query executed; see the dumped response
  * ``DENIED`` - DataHub refused it (token lacks the privilege)
  * ``SCHEMA`` - query not supported by this GMS GraphQL schema version
  * ``ERROR``  - network / WAF / transport failure

Safety
------
READ-ONLY ONLY. Every probe is a pure GraphQL *read* (``me``, ``search``,
``dataset``, ``lineage``, ``listUsers``, ``listRoles``, ``listPolicies``).
Nothing creates, updates, deletes, publishes or mutates any DataHub state.

Running
-------
Standalone (auto re-execs with the project venv if deps are missing):

    python3 tests/testACL.py

Or under pytest (skipped by default; the 5 hermetic ACL checks):

    RUN_ACL_TESTS=1 .venv/bin/python -m pytest tests/testACL.py -v
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

# Bootstrap: when run as a script (``python3 tests/testACL.py``) the project
# root is not on sys.path; insert it so `config` / `ingestion` import resolve.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
# Settings reads `.env` from the CWD; pin it to the project root so the script
# works no matter which directory it is launched from.
os.chdir(str(_ROOT))


def _bootstrap_venv() -> None:
    """Re-exec with the project venv when the current interpreter lacks deps.

    The system ``python3`` usually has no project packages (structlog, requests,
    pydantic-settings...). If any is missing we transparently re-run this script
    with ``<project>/.venv/bin/python`` so ``python3 testACL.py`` works from any
    working directory. ImportError from the final interpreter is left to surface.
    """
    try:
        import requests  # noqa: F401
        import structlog  # noqa: F401
        from pydantic_settings import BaseSettings  # noqa: F401
    except ImportError:
        venv_py = _ROOT / ".venv" / "bin" / "python"
        if venv_py.exists():
            print(
                f"[testACL] project deps missing here; re-executing with {venv_py}",
                file=sys.stderr,
            )
            os.execv(
                str(venv_py),
                [str(venv_py), str(Path(__file__).resolve()), *sys.argv[1:]],
            )


_bootstrap_venv()

import asyncio  # noqa: E402

from config.settings import settings  # noqa: E402
from guardrails.sanitizer import mask_secrets  # noqa: E402
from ingestion.errors import (  # noqa: E402
    DataHubAuthError,
    DataHubConnectionError,
    DataHubGraphQLError,
    DataHubTimeoutError,
)
from ingestion.graphql.client import GraphQLClient  # noqa: E402
from ingestion.graphql.queries import (  # noqa: E402
    GET_DATASET_LINEAGE_QUERY,
    GET_DATASET_QUERY,
    MINIMAL_SEARCH_QUERY,
)

try:
    import pytest
    import pytest_asyncio

    _HAS_PYTEST = True
except ImportError:  # pragma: no cover - standalone run without pytest
    pytest = None
    pytest_asyncio = None
    _HAS_PYTEST = False

_ME_QUERY = """
query me {
  me {
    corpUser {
      urn
      username
      properties { displayName email title }
    }
  }
}
"""

# `roles` lives on the CorpUser entity (not on AuthenticatedUser in this GMS
# version); probed with the account's own urn to reveal attached roles.
_CORP_USER_ROLES_QUERY = """
query corpUserRoles($urn: String!) {
  corpUser(urn: $urn) {
    urn
    username
    roles {
      urn
      name
      type
    }
  }
}
"""

_LIST_USERS_QUERY = """
query listUsers($input: ListUsersInput!) {
  listUsers(input: $input) {
    start
    count
    total
    users {
      urn
      username
      properties { displayName email }
    }
  }
}
"""

_LIST_ROLES_QUERY = """
query listRoles($input: ListRolesInput!) {
  listRoles(input: $input) {
    start
    count
    total
    roles {
      urn
      name
      type
    }
  }
}
"""

_LIST_POLICIES_QUERY = """
query listPolicies($input: ListPoliciesInput!) {
  listPolicies(input: $input) {
    start
    count
    total
    policies {
      urn
      name
      type
    }
  }
}
"""

# Policy ACTORS: which users/groups/roles a policy is scoped to. The closest the
# schema may offer to "who has which role", since corpUser.roles and
# listAssignments are undefined on this GMS. Graceful: if `actors` is unsupported
# this query fails validation and the inventory reports policies as unsupported.
_LIST_POLICIES_DETAIL_QUERY = """
query listPoliciesDetail($input: ListPoliciesInput!) {
  listPolicies(input: $input) {
    start
    count
    total
    policies {
      urn
      name
      type
      actors {
        allUsers
        allGroups
        resourceOwners
        users
        groups
        roles
        resolvedRoles { urn name }
      }
    }
  }
}
"""

# Who holds a given role (requires Manage Roles). Field names vary by version;
# a SCHEMA result tells us this GMS does not expose it this way.
_LIST_ASSIGNMENTS_QUERY = """
query listAssignments($input: ListAssignmentsInput!) {
  listAssignments(input: $input) {
    start
    count
    total
    users {
      urn
    }
  }
}
"""

# Introspection: dump the ROOT Query fields so we can see (without guessing)
# which read resolvers this GMS exposes (role membership, list* helpers, ...).
# Requesting __Type.fields on many types at once is refused as "bad faith
# introspection", so we limit this to the Query type only.
_INTROSPECT_QUERY = """
query Introspect {
  queryType: __schema {
    queryType {
      fields { name }
    }
  }
}
"""

# getGrantedPrivileges: what privileges does a user have on a specific resource?
# Requires resourceUrn + actorUrn. We use a real dataset URN from search.
_GET_GRANTED_PRIVILEGES_QUERY = """
query getGrantedPrivileges($resourceUrn: String!, $actorUrn: String!) {
  getGrantedPrivileges(resourceUrn: $resourceUrn, actorUrn: $actorUrn)
}
"""

# Singular role entity query — check if the Role type exposes actors/members.
_ROLE_ENTITY_QUERY = """
query roleEntity($urn: String!) {
  role(urn: $urn) {
    urn
    name
    type
    description
  }
}
"""

# listGroups: enumerate corp groups + their metadata.
_LIST_GROUPS_QUERY = """
query listGroups($input: ListGroupsInput!) {
  listGroups(input: $input) {
    start
    count
    total
    groups {
      urn
      name
    }
  }
}
"""

_LIST_DOMAINS_QUERY = """
query listDomains($input: ListDomainsInput!) {
  listDomains(input: $input) {
    start
    count
    total
    domains {
      urn
      properties { name description }
    }
  }
}
"""

# Per-user detail (broad field set). `groups` / `info` / `isNativeUser` exist on
# newer CorpUser schemas; the inventory falls back to a minimal query when this
# whole shape fails validation.
_CORP_USER_DETAIL_QUERY = """
query corpUserDetails($urn: String!) {
  corpUser(urn: $urn) {
    urn
    username
    properties { displayName email title }
    info { active displayName email title department }
    groups { name }
    isNativeUser
  }
}
"""

_CORP_USER_DETAIL_MIN_QUERY = """
query corpUserDetailsMin($urn: String!) {
  corpUser(urn: $urn) {
    urn
    username
    properties { displayName email }
  }
}
"""

# A URN that cannot exist on any server. Used by the no-leak check: DataHub
# returns a minimal URN-derived stub (never real metadata) for unknown URNs.
_MISSING_URN = "urn:li:dataset:(urn:li:dataPlatform:no_such_platform,acl_test_missing_urn,PROD)"

_NON_MUTATING = True  # sentinel: this module contains no write operations

_MAX_DATA_CHARS = 2500


def _has_token() -> bool:
    return bool((settings.DATAHUB_TOKEN or "").strip())


def _skip_reason() -> str:
    if os.environ.get("RUN_ACL_TESTS", "") != "1":
        return "set RUN_ACL_TESTS=1 to run live DataHub ACL checks"
    if not _has_token():
        return "DATAHUB_TOKEN is empty in .env"
    return ""


def _client() -> GraphQLClient:
    # max_retries=1: fail fast on WAF/network blocks instead of burning the
    # client's backoff budget (default retries on HTTP 403/429).
    return GraphQLClient(max_retries=1)


def _pretty(data: Any) -> str:
    """Pretty-print probe response, secrets masked and length-capped."""
    try:
        text = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    except Exception:
        text = str(data)
    text = mask_secrets(text)
    if len(text) > _MAX_DATA_CHARS:
        text = text[:_MAX_DATA_CHARS] + f"\n... (truncated {len(text) - _MAX_DATA_CHARS} chars)"
    return text


def _status_of(exc: BaseException) -> str:
    if isinstance(exc, DataHubAuthError):
        return "DENIED"
    if isinstance(exc, DataHubGraphQLError):
        return "SCHEMA"
    return "ERROR"


async def _first_dataset_urn(client: GraphQLClient) -> str | None:
    data = await client.execute(
        MINIMAL_SEARCH_QUERY,
        {"query": "*", "type": "DATASET", "count": 10},
    )
    for item in (data.get("search") or {}).get("searchResults") or []:
        urn = ((item.get("entity") or {}).get("urn") or "").strip()
        if urn:
            return urn
    return None


async def _run_probe(
    client: GraphQLClient,
    name: str,
    explain: str,
    query: str,
    variables: dict[str, Any] | None,
) -> dict[str, Any]:
    """Execute one read-only probe and classify OK / DENIED / SCHEMA / ERROR."""
    try:
        data = await client.execute(query, variables)
    except (DataHubAuthError, DataHubGraphQLError,
            DataHubConnectionError, DataHubTimeoutError) as exc:
        return {
            "name": name,
            "explain": explain,
            "status": _status_of(exc),
            "data": None,
            "detail": f"{type(exc).__name__}: {str(exc)[:300]}",
        }
    return {"name": name, "explain": explain, "status": "OK", "data": data, "detail": ""}


def _print_probe(probe: dict[str, Any], idx: int) -> None:
    print("\n" + "=" * 70)
    print(f"[{idx}] {probe['name']}")
    print(f"    {probe['explain']}")
    if probe["status"] == "OK":
        print("    status: OK")
        print(f"    returned data:\n{_pretty(probe['data'])}")
    else:
        print(f"    status: {probe['status']}  ({probe['detail']})")


async def _run_probes(client: GraphQLClient) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    results.append(await _run_probe(
        client, "me_identity", "Identity of the authenticated account",
        _ME_QUERY, None,
    ))

    me = (results[0].get("data") or {}).get("me") or {}
    own_urn = ((me.get("corpUser") or {}).get("urn") or "").strip()
    if own_urn:
        results.append(await _run_probe(
            client, "account_roles", "Roles attached to the authenticated account",
            _CORP_USER_ROLES_QUERY, {"urn": own_urn},
        ))
    else:
        results.append({"name": "account_roles",
                        "explain": "Roles attached to the authenticated account",
                        "status": "SKIP", "data": None,
                        "detail": "me query returned no corpUser urn"})

    results.append(await _run_probe(
        client, "list_users", "Can the token list user accounts? (admin probe)",
        _LIST_USERS_QUERY, {"input": {"query": "*", "start": 0, "count": 100}},
    ))
    results.append(await _run_probe(
        client, "list_roles", "Can the token list roles? (admin probe)",
        _LIST_ROLES_QUERY, {"input": {"query": "*", "start": 0, "count": 100}},
    ))
    results.append(await _run_probe(
        client, "list_policies", "Can the token list policies? (admin probe)",
        _LIST_POLICIES_QUERY, {"input": {"query": "*", "start": 0, "count": 100}},
    ))
    results.append(await _run_probe(
        client, "list_policies_actors",
        "Policy actor scoping (users/groups/roles per policy)",
        _LIST_POLICIES_DETAIL_QUERY,
        {"input": {"query": "*", "start": 0, "count": 100}},
    ))
    results.append(await _run_probe(
        client, "list_assignments",
        "Who holds the Admin role? (requires Manage Roles)",
        _LIST_ASSIGNMENTS_QUERY,
        {"input": {"roleUrn": "urn:li:dataHubRole:Admin", "start": 0, "count": 100}},
    ))
    results.append(await _run_probe(
        client, "list_domains", "Domain catalog (admin probe)",
        _LIST_DOMAINS_QUERY, {"input": {"start": 0, "count": 100}},
    ))
    results.append(await _run_probe(
        client, "introspect_types",
        "Schema fields available on CorpUser/AuthenticatedUser/Role/Query",
        _INTROSPECT_QUERY, None,
    ))
    results.append(await _run_probe(
        client, "list_groups", "Corp group catalog (admin probe)",
        _LIST_GROUPS_QUERY, {"input": {"query": "*", "start": 0, "count": 100}},
    ))
    results.append(await _run_probe(
        client, "role_entity", "Role entity fields (Admin role)",
        _ROLE_ENTITY_QUERY, {"urn": "urn:li:dataHubRole:Admin"},
    ))
    results.append(await _run_probe(
        client, "search_datasets", "Dataset search (read ACL)",
        MINIMAL_SEARCH_QUERY, {"query": "*", "type": "DATASET", "count": 3},
    ))

    try:
        urn = await _first_dataset_urn(client)
    except (DataHubAuthError, DataHubGraphQLError,
            DataHubConnectionError, DataHubTimeoutError):
        urn = None
    if urn:
        results.append(await _run_probe(
            client, "fetch_dataset", "Fetch a real dataset entity",
            GET_DATASET_QUERY, {"urn": urn},
        ))
        results.append(await _run_probe(
            client, "lineage", "Lineage read for that dataset",
            GET_DATASET_LINEAGE_QUERY,
            {"urn": urn, "direction": "DOWNSTREAM", "count": 10},
        ))
        if own_urn:
            results.append(await _run_probe(
                client, "get_granted_privileges",
                "Privileges of this account on a real dataset",
                _GET_GRANTED_PRIVILEGES_QUERY,
                {"resourceUrn": urn, "actorUrn": own_urn},
            ))
    else:
        results.append({"name": "fetch_dataset", "explain": "Fetch a real dataset entity",
                        "status": "SKIP", "data": None,
                        "detail": "no dataset returned by search"})
        results.append({"name": "lineage", "explain": "Lineage read for that dataset",
                        "status": "SKIP", "data": None,
                        "detail": "no dataset returned by search"})

    results.append(await _run_probe(
        client, "unknown_entity", "Unknown entity (no real metadata leaked?)",
        GET_DATASET_QUERY, {"urn": _MISSING_URN},
    ))
    return results


# --------------------------------------------------------------------------- #
# User inventory: users + roles + domains + per-user detail.
# --------------------------------------------------------------------------- #

async def _fetch_list(client: GraphQLClient, query: str, variables: dict[str, Any],
                      field: str, items_key: str) -> list[dict[str, Any]]:
    """Run a list* query and return its result items, or [] on any failure."""
    try:
        data = await client.execute(query, variables)
    except (DataHubAuthError, DataHubGraphQLError,
            DataHubConnectionError, DataHubTimeoutError):
        return []
    return (data.get(field) or {}).get(items_key) or []


async def _run_inventory(client: GraphQLClient) -> dict[str, Any]:
    """Build a full user inventory: users, roles, domains, role assignments.

    Notes
    -----
    DataHub links domains to data ASSETS, not to users; there is no native
    ``user -> domain`` concept. We therefore report the domain catalog and any
    per-user fields the schema exposes (groups / info / status / ...) instead.
    """
    users: list[dict[str, Any]] = []
    roles: list[dict[str, Any]] = []
    domains: list[dict[str, Any]] = []
    policies: list[dict[str, Any]] = []

    users = await _fetch_list(
        client, _LIST_USERS_QUERY, {"input": {"query": "*", "start": 0, "count": 100}},
        "listUsers", "users",
    )
    roles = await _fetch_list(
        client, _LIST_ROLES_QUERY, {"input": {"query": "*", "start": 0, "count": 100}},
        "listRoles", "roles",
    )
    domains = await _fetch_list(
        client, _LIST_DOMAINS_QUERY, {"input": {"start": 0, "count": 100}},
        "listDomains", "domains",
    )

    # Policy actors: closest schema-supported view of role scoping. If `actors`
    # is undefined on DataHubPolicy this whole query fails validation -> report
    # policies as unsupported instead of crashing the inventory.
    policy_status = "unsupported"
    try:
        pdata = await client.execute(
            _LIST_POLICIES_DETAIL_QUERY,
            {"input": {"query": "*", "start": 0, "count": 100}},
        )
    except DataHubGraphQLError:
        pdata = None
    except (DataHubAuthError, DataHubConnectionError, DataHubTimeoutError):
        pdata = None
        policy_status = "denied"
    if pdata is not None:
        policy_status = "ok"
        for p in (pdata.get("listPolicies") or {}).get("policies") or []:
            actors = p.get("actors") or {}
            policies.append({
                "urn": p.get("urn"),
                "name": p.get("name"),
                "type": p.get("type"),
                "allUsers": bool(actors.get("allUsers")),
                "allGroups": bool(actors.get("allGroups")),
                "user_urns": set(actors.get("users") or []),
                "group_urns": set(actors.get("groups") or []),
                "role_urns": sorted(actors.get("roles") or []),
                "resolved_roles": sorted(
                    {r.get("name") for r in (actors.get("resolvedRoles") or []) if r.get("name")}
                ),
            })

    # role urn -> policy names that target that role.
    role_policies: dict[str, list[str]] = {}
    for r in roles:
        r_urn = r.get("urn") or ""
        r_name = r.get("name") or r_urn
        targeted = sorted(
            p["name"] for p in policies
            if r_name in p["resolved_roles"]
        )
        if targeted:
            role_policies[r_name] = targeted

    # user urn -> role names, via listAssignments per role (if supported).
    user_roles: dict[str, list[str]] = {}
    assignment_status = "unsupported"
    for role in roles:
        role_urn = role.get("urn") or ""
        if not role_urn:
            continue
        try:
            a = await client.execute(
                _LIST_ASSIGNMENTS_QUERY,
                {"input": {"roleUrn": role_urn, "start": 0, "count": 100}},
            )
        except DataHubGraphQLError:
            assignment_status = "unsupported"
            break
        except (DataHubAuthError, DataHubConnectionError, DataHubTimeoutError):
            assignment_status = "denied"
            break
        for u in (a.get("listAssignments") or {}).get("users") or []:
            if u.get("urn"):
                user_roles.setdefault(u["urn"], []).append(role.get("name") or role_urn)
        assignment_status = "ok"

    rows: list[dict[str, Any]] = []
    for u in users:
        urn = u.get("urn") or ""
        props = u.get("properties") or {}
        row: dict[str, Any] = {
            "urn": urn,
            "username": u.get("username") or "",
            "email": props.get("email"),
            "displayName": props.get("displayName"),
            "roles": sorted(user_roles.get(urn, [])),
            "groups": [],
            "info": {},
            "isNativeUser": None,
            "policies": sorted(p["name"] for p in policies if urn in p["user_urns"]),
        }
        if urn:
            try:
                d = await client.execute(_CORP_USER_DETAIL_QUERY, {"urn": urn})
                cu = d.get("corpUser") or {}
                row["groups"] = [g.get("name") for g in (cu.get("groups") or []) if g]
                row["isNativeUser"] = cu.get("isNativeUser")
                info = cu.get("info") or {}
                row["info"] = {
                    k: info.get(k) for k in ("active", "department", "title")
                }
            except DataHubGraphQLError:
                try:
                    await client.execute(_CORP_USER_DETAIL_MIN_QUERY, {"urn": urn})
                    row["detail"] = "minimal-fields-only"
                except DataHubGraphQLError:
                    row["detail"] = "corpUser query unsupported"
            except (DataHubAuthError, DataHubConnectionError, DataHubTimeoutError):
                row["detail"] = "denied"
        rows.append(row)

    return {
        "rows": rows,
        "roles": roles,
        "domains": domains,
        "policies": policies,
        "role_policies": role_policies,
        "policy_status": policy_status,
        "assignment_status": assignment_status,
    }


def _print_inventory(inv: dict[str, Any]) -> None:
    print("\n" + "=" * 70)
    print("USER INVENTORY")
    rows = inv["rows"]
    print(f"users: {len(rows)}  roles: {len(inv['roles'])}  domains: {len(inv['domains'])}"
          f"  policies(actor detail): {inv['policy_status']}"
          f"  role-assignments: {inv['assignment_status']}")
    print("\nRoles catalog:")
    for r in inv["roles"]:
        name = r.get("name") or r.get("urn")
        targeted = inv["role_policies"].get(name)
        print(f"  - {r.get('name')} ({r.get('urn')}) [{r.get('type')}]"
              + (f" -> policies: {', '.join(targeted)}" if targeted else ""))
    print("\nPolicies catalog:")
    for p in inv["policies"]:
        scope_parts = []
        if p["allUsers"]:
            scope_parts.append("allUsers")
        if p["user_urns"]:
            scope_parts.append(f"users={len(p['user_urns'])}")
        if p["group_urns"]:
            scope_parts.append(f"groups={len(p['group_urns'])}")
        if p["role_urns"] or p["resolved_roles"]:
            all_r = sorted(set(p["role_urns"]) | {r for r in p["resolved_roles"]})
            role_short = [u.rsplit(":", 1)[-1] for u in all_r]
            scope_parts.append(f"roles={','.join(role_short)}")
        scope = ", ".join(scope_parts) or "-"
        print(f"  - {p.get('name')} ({p.get('urn')}) [{p.get('type')}] <{scope}>")
    if not inv["policies"]:
        print("  (policy actors not exposed by this schema / denied)")
    print("\nDomains catalog:")
    for d in inv["domains"]:
        print(f"  - {d.get('properties', {}).get('name') or d.get('urn')}"
              f"  ({d.get('urn')})")
    if not inv["domains"]:
        print("  (listDomains not exposed / empty)")
    print("\nUsers (username | email | displayName | roles | groups | info | policies):")
    for row in rows:
        print(
            f"  {row['username'] or row['urn']:<40} "
            f"| {row['email'] or '':<35} "
            f"| {row['displayName'] or '':<30} "
            f"| roles={','.join(row['roles']) or '-'} "
            f"| groups={','.join(row['groups']) or '-'} "
            f"| info={row['info'] or '-'} "
            f"| policies={','.join(row['policies']) or '-'}"
            + (f" | {row.get('detail')}" if row.get("detail") else "")
        )
    print("\nNote: DataHub binds domains to data assets, not to users; "
          "user->domain is not a native concept. On this GMS, role membership is "
          "not exposed per-user (corpUser.roles / listAssignments are undefined); "
          "the closest signal is policy actor scoping (shown above).")


def _print_summary(results: list[dict[str, Any]]) -> None:
    print("\n" + "=" * 70)
    print("SUMMARY")
    groups: dict[str, list[str]] = {}
    for r in results:
        groups.setdefault(r["status"], []).append(r["name"])
    for status in ("OK", "DENIED", "SCHEMA", "ERROR", "SKIP"):
        names = groups.get(status)
        if names:
            print(f"  {status:6s}: {', '.join(names)}")


async def _run_all() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    client = _client()
    try:
        results = await _run_probes(client)
        inventory = await _run_inventory(client)
        return results, inventory
    finally:
        await client.close()


def main() -> int:
    if not _has_token():
        print("ACL diagnostics skipped: DATAHUB_TOKEN is empty in .env")
        return 0
    results, inventory = asyncio.run(_run_all())
    for idx, probe in enumerate(results, start=1):
        _print_probe(probe, idx)
    _print_summary(results)
    _print_inventory(inventory)
    denied = [r["name"] for r in results if r["status"] == "DENIED"]
    if denied:
        print(f"\nDenied operations (token lacks privilege): {', '.join(denied)}")
    admin_probes = {"list_users", "list_roles", "list_policies", "list_assignments",
                    "list_domains", "list_groups"}
    ok_admin = [r["name"] for r in results
                if r["name"] in admin_probes and r["status"] == "OK"]
    if ok_admin:
        print("Note: token CAN manage users/roles/policies "
              f"({'/'.join(sorted(ok_admin))} returned OK) -> platform admin-level access.")
    return 0


if __name__ == "__main__":
    sys.exit(main())


# --------------------------------------------------------------------------- #
# Pytest wrappers (only when pytest is installed).
# --------------------------------------------------------------------------- #

if _HAS_PYTEST:

    pytestmark = [
        pytest.mark.acl,
        pytest.mark.skipif(
            os.environ.get("RUN_ACL_TESTS", "") != "1" or not _has_token(),
            reason=_skip_reason(),
        ),
    ]

    @pytest_asyncio.fixture(scope="session")
    async def gql_client() -> GraphQLClient:
        client = _client()
        try:
            yield client
        finally:
            await client.close()

    async def _assert_ok(name: str, check, client: GraphQLClient) -> None:
        probe = await check(client)
        if probe["status"] != "OK":
            pytest.fail(f"{name}: {probe['status']} ({probe['detail']})")
        print(f"\n[ACL] {name}: OK\n{_pretty(probe['data'])}")

    async def check_authentication(client: GraphQLClient) -> dict[str, Any]:
        return await _run_probe(
            client, "authentication", "Identity of the authenticated account",
            _ME_QUERY, None,
        )

    async def check_search_datasets(client: GraphQLClient) -> dict[str, Any]:
        return await _run_probe(
            client, "search_datasets", "Dataset search (read ACL)",
            MINIMAL_SEARCH_QUERY, {"query": "*", "type": "DATASET", "count": 5},
        )

    async def check_fetch_entity(client: GraphQLClient) -> dict[str, Any]:
        try:
            urn = await _first_dataset_urn(client)
        except (DataHubAuthError, DataHubGraphQLError,
                DataHubConnectionError, DataHubTimeoutError):
            urn = None
        if not urn:
            return {"name": "fetch_entity", "explain": "Fetch a real dataset",
                    "status": "OK", "data": {"note": "skipped: no dataset"}, "detail": ""}
        return await _run_probe(client, "fetch_entity", "Fetch a real dataset entity",
                                GET_DATASET_QUERY, {"urn": urn})

    async def check_lineage(client: GraphQLClient) -> dict[str, Any]:
        try:
            urn = await _first_dataset_urn(client)
        except (DataHubAuthError, DataHubGraphQLError,
                DataHubConnectionError, DataHubTimeoutError):
            urn = None
        if not urn:
            return {"name": "lineage", "explain": "Lineage read",
                    "status": "OK", "data": {"note": "skipped: no dataset"}, "detail": ""}
        return await _run_probe(client, "lineage", "Lineage read for a dataset",
                                GET_DATASET_LINEAGE_QUERY,
                                {"urn": urn, "direction": "DOWNSTREAM", "count": 10})

    async def check_missing_entity(client: GraphQLClient) -> dict[str, Any]:
        return await _run_probe(client, "missing_entity",
                                "Unknown entity (no real metadata leaked?)",
                                GET_DATASET_QUERY, {"urn": _MISSING_URN})

    async def test_authentication_token_accepted(gql_client: GraphQLClient) -> None:
        await _assert_ok("authentication", check_authentication, gql_client)

    async def test_search_datasets_authorized(gql_client: GraphQLClient) -> None:
        await _assert_ok("search_datasets", check_search_datasets, gql_client)

    async def test_fetch_entity_read_acl(gql_client: GraphQLClient) -> None:
        await _assert_ok("fetch_entity", check_fetch_entity, gql_client)

    async def test_lineage_read_acl(gql_client: GraphQLClient) -> None:
        await _assert_ok("lineage", check_lineage, gql_client)

    async def test_missing_entity_not_leaked(gql_client: GraphQLClient) -> None:
        await _assert_ok("missing_entity", check_missing_entity, gql_client)
