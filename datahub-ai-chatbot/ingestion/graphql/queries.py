SEARCH_ENTITIES_QUERY = """
query searchEntities($query: String!, $type: EntityType!, $start: Int, $count: Int) {
  search(input: { type: $type, query: $query, start: $start, count: $count }) {
    total
    searchResults {
      entity {
        urn
        type
        ... on Dataset {
          name
          properties { description customProperties { key value } }
          platform { name urn }
          ownership {
            owners {
              owner {
                ... on CorpUser { urn username properties { displayName email } }
                ... on CorpGroup { urn name properties { displayName email } }
              }
            }
          }
          schemaMetadata {
            fields {
              fieldPath
              description
              nativeDataType
              type
              nullable
              isPartOfKey
            }
          }
          domain {
            domain { urn properties { name description } }
          }
          glossaryTerms {
            terms { term { urn name } }
          }
          tags {
            tags { tag { name urn } }
          }
        }
        ... on Dashboard {
          properties { name description }
          platform { name urn }
          ownership {
            owners {
              owner {
                ... on CorpUser { urn username properties { displayName email } }
                ... on CorpGroup { urn name properties { displayName email } }
              }
            }
          }
          domain {
            domain { urn properties { name description } }
          }
        }
        ... on GlossaryTerm {
          properties { name description }
          ownership {
            owners {
              owner {
                ... on CorpUser { urn username properties { displayName email } }
                ... on CorpGroup { urn name properties { displayName email } }
              }
            }
          }
          domain {
            domain { urn properties { name description } }
          }
        }
        ... on Chart {
          properties { name description }
        }
        ... on DataFlow {
          properties { name description }
        }
        ... on DataJob {
          properties { name description }
        }
        ... on Container {
          properties { name description }
        }
        ... on MLModel {
          name
          description
        }
        ... on Tag {
          properties { name description }
        }
      }
    }
  }
}
"""

SCROLL_ACROSS_ENTITIES_QUERY = """
query scrollAcrossEntities($input: ScrollAcrossEntitiesInput!) {
  scrollAcrossEntities(input: $input) {
    nextScrollId
    count
    total
    searchResults {
      entity {
        urn
        type
        ... on Dataset {
          name
          properties { description customProperties { key value } }
          platform { name urn }
          ownership {
            owners {
              owner {
                ... on CorpUser { urn username properties { displayName email } }
                ... on CorpGroup { urn name properties { displayName email } }
              }
            }
          }
          schemaMetadata {
            fields {
              fieldPath
              description
              nativeDataType
              type
              nullable
              isPartOfKey
            }
          }
          domain {
            domain { urn properties { name description } }
          }
          glossaryTerms {
            terms { term { urn name } }
          }
          tags {
            tags { tag { name urn } }
          }
          upstreamLineage: lineage(input: { direction: UPSTREAM, count: 100 }) {
            total
            relationships {
              entity { urn type }
            }
          }
          downstreamLineage: lineage(input: { direction: DOWNSTREAM, count: 100 }) {
            total
            relationships {
              entity { urn type }
            }
          }
        }
        ... on Dashboard {
          properties { name description }
          platform { name urn }
          ownership {
            owners {
              owner {
                ... on CorpUser { urn username properties { displayName email } }
                ... on CorpGroup { urn name properties { displayName email } }
              }
            }
          }
          domain {
            domain { urn properties { name description } }
          }
          upstreamLineage: lineage(input: { direction: UPSTREAM, count: 100 }) {
            total
            relationships {
              entity { urn type }
            }
          }
          downstreamLineage: lineage(input: { direction: DOWNSTREAM, count: 100 }) {
            total
            relationships {
              entity { urn type }
            }
          }
        }
        ... on GlossaryTerm {
          properties { name description }
          ownership {
            owners {
              owner {
                ... on CorpUser { urn username properties { displayName email } }
                ... on CorpGroup { urn name properties { displayName email } }
              }
            }
          }
          domain {
            domain { urn properties { name description } }
          }
        }
        ... on Chart {
          properties { name description }
        }
        ... on DataFlow {
          properties { name description }
        }
        ... on DataJob {
          properties { name description }
        }
        ... on Container {
          properties { name description }
        }
        ... on MLModel {
          name
          description
        }
        ... on Tag {
          properties { name description }
        }
      }
    }
  }
}
"""

GET_DATASET_QUERY = """
query getDataset($urn: String!) {
  dataset(urn: $urn) {
    urn
    name
    editableProperties {
      description
    }
    properties {
      description
      customProperties { key value }
    }
    platform {
      name
      urn
    }
    schemaMetadata {
      fields {
        fieldPath
        description
        nativeDataType
        type
        nullable
        isPartOfKey
      }
    }
    ownership {
      owners {
        owner {
          ... on CorpUser {
            urn
            username
            properties { displayName email }
          }
          ... on CorpGroup {
            urn
            name
            properties { displayName email }
          }
        }
      }
    }
    upstreamLineage: lineage(input: { direction: UPSTREAM, count: 100 }) {
      total
      relationships {
        entity { urn type }
      }
    }
    downstreamLineage: lineage(input: { direction: DOWNSTREAM, count: 100 }) {
      total
      relationships {
        entity { urn type }
      }
    }
    domain {
      domain {
        urn
        properties { name description }
      }
    }
    glossaryTerms {
      terms {
        term { urn name }
      }
    }
    tags {
      tags {
        tag { name urn }
      }
    }
  }
}
"""

GET_DATASET_LINEAGE_QUERY = """
query getDatasetLineage($urn: String!, $direction: LineageDirection!, $start: Int, $count: Int) {
  dataset(urn: $urn) {
    urn
    lineage(input: { direction: $direction, start: $start, count: $count }) {
      total
      relationships {
        type
        entity { urn type }
      }
    }
  }
}
"""

GET_DASHBOARD_QUERY = """
query getDashboard($urn: String!) {
  dashboard(urn: $urn) {
    urn
    properties {
      name
      description
      customProperties { key value }
    }
    platform { name urn }
    ownership {
      owners {
        owner {
          ... on CorpUser { urn username properties { displayName email } }
          ... on CorpGroup { urn name properties { displayName email } }
        }
      }
    }
    upstreamLineage: lineage(input: { direction: UPSTREAM, count: 100 }) {
      total
      relationships { entity { urn type } }
    }
    downstreamLineage: lineage(input: { direction: DOWNSTREAM, count: 100 }) {
      total
      relationships { entity { urn type } }
    }
    domain {
      domain {
        urn
        properties { name description }
      }
    }
  }
}
"""

GET_GLOSSARY_TERM_QUERY = """
query getGlossaryTerm($urn: String!) {
  glossaryTerm(urn: $urn) {
    urn
    properties {
      name
      description
    }
    ownership {
      owners {
        owner {
          ... on CorpUser { urn username properties { displayName email } }
          ... on CorpGroup { urn name properties { displayName email } }
        }
      }
    }
    relatedEntities {
      total
      relationships {
        entity { urn type name }
      }
    }
    domain {
      domain {
        urn
        properties { name description }
      }
    }
    lastModified { time }
  }
}
"""

LIST_GLOSSARY_TERMS_QUERY = """
query scrollGlossaryTerms($input: ScrollAcrossEntitiesInput!) {
  scrollAcrossEntities(input: $input) {
    nextScrollId
    count
    total
    searchResults {
      entity {
        urn
        type
        ... on GlossaryTerm {
          properties {
            name
            description
          }
          ownership {
            owners {
              owner {
                ... on CorpUser { urn username properties { displayName email } }
                ... on CorpGroup { urn name properties { displayName email } }
              }
            }
          }
          domain {
            domain { urn properties { name description } }
          }
        }
      }
    }
  }
}
"""

GET_DOCUMENT_QUERY = """
query getDocument($urn: String!) {
  document(urn: $urn) {
    urn
    info { title contents { text } }
    ownership {
      owners {
        owner {
          ... on CorpUser { urn username properties { displayName email } }
          ... on CorpGroup { urn name properties { displayName email } }
        }
      }
    }
    lastModified { time }
  }
}
"""

def build_search_query(entity_type: str) -> str:
    """Search query cho một entity type duy nhất (1 fragment), type hardcode inline.

    Mirror scripts/pull_datahub_data.py:build_search_query — đã chạy OK với
    DataHub corporate. Fragment khớp chính xác pull script (không ownership,
    không customProperties, không name top-level). Dùng 1 fragment mỗi query
    để tránh merge-fragment 500.
    """
    frag = {
        "DATASET": """... on Dataset {
        properties { name qualifiedName origin description }
        editableProperties { description }
        platform { name urn }
        domain { domain { urn properties { name description } } }
        glossaryTerms { terms { term { urn name properties { name description } } } }
        tags { tags { tag { urn name } } }
        schemaMetadata { fields { fieldPath description nativeDataType type nullable isPartOfKey } }
        upstreamLineage: lineage(input: { direction: UPSTREAM, count: 100 }) { total relationships { entity { urn type } } }
        downstreamLineage: lineage(input: { direction: DOWNSTREAM, count: 100 }) { total relationships { entity { urn type } } }
      }""",
        "DASHBOARD": """... on Dashboard {
        tool dashboardId properties { name description } platform { name urn }
        domain { domain { urn properties { name description } } }
        upstreamLineage: lineage(input: { direction: UPSTREAM, count: 100 }) { total relationships { entity { urn type } } }
        downstreamLineage: lineage(input: { direction: DOWNSTREAM, count: 100 }) { total relationships { entity { urn type } } }
      }""",
        "CHART": """... on Chart {
        tool chartId properties { name description } platform { name urn }
      }""",
        "CONTAINER": """... on Container {
        properties { name description } platform { name urn }
        domain { domain { urn properties { name description } } }
      }""",
        "DATA_FLOW": """... on DataFlow {
        orchestrator flowId cluster properties { name description externalUrl } platform { name urn }
        domain { domain { urn properties { name description } } }
      }""",
        "DATA_JOB": """... on DataJob {
        jobId dataFlow { flowId } properties { name description externalUrl }
        domain { domain { urn properties { name description } } }
      }""",
        "GLOSSARY_TERM": """... on GlossaryTerm {
        properties { name description }
      }""",
        "MLMODEL": "... on MLModel { name description }",
        "TAG": "... on Tag { name properties { name description } }",
    }.get(entity_type, "... on Dataset { name }")

    return f"""query search($query: String!, $count: Int, $start: Int) {{
  search(input: {{ type: {entity_type}, query: $query, count: $count, start: $start }}) {{
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


MINIMAL_SEARCH_QUERY = """
query search($query: String!, $type: EntityType!, $count: Int, $start: Int) {
  search(input: { type: $type, query: $query, count: $count, start: $start }) {
    total
    searchResults {
      entity {
        urn
        type
        ... on Dataset { name }
        ... on Dashboard { properties { name } }
        ... on GlossaryTerm { properties { name } }
        ... on Chart { properties { name } }
        ... on DataFlow { properties { name } }
        ... on DataJob { properties { name } }
        ... on Container { properties { name } }
        ... on MLModel { name }
        ... on Tag { name }
      }
    }
  }
}
"""
