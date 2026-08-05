SEARCH_ENTITIES_QUERY = """
query searchEntities($query: String!, $type: EntityType, $start: Int, $count: Int) {
  search(input: { type: $type, query: $query, start: $start, count: $count }) {
    total
    searchResults {
      entity {
        urn
        type
        ... on Dataset {
          name
          description
        }
        ... on GlossaryTerm {
          name
          description
        }
        ... on Dashboard {
          name
          description
        }
        ... on Document {
          name
          description
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
        ... on Document {
          info { title contents { text } }
          ownership {
            owners {
              owner {
                ... on CorpUser { urn username properties { displayName email } }
                ... on CorpGroup { urn name properties { displayName email } }
              }
            }
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
