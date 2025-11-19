from __future__ import annotations

from typing import List

from neo4j import GraphDatabase

from .config import settings

_driver = None


def driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )
    return _driver


def close_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


CYPHER_UPSERT = """
// Upsert Document node
MERGE (d:Document {id: $doc_id})
  ON CREATE SET d.source_url = $source_url, d.created_at = timestamp()
  ON MATCH SET  d.source_url = coalesce($source_url, d.source_url)
WITH d

// Merge jurisdictions
UNWIND $jurisdictions AS jname
  MERGE (j:Jurisdiction {name: jname})
  MERGE (d)-[:MENTIONS]->(j)
WITH d, collect(j) AS jurisdiction_nodes

// Process obligations with bitemporal versioning
UNWIND $obligations AS ob
  MERGE (c:Concept {name: coalesce(ob.concept, 'unspecified')})

  // Check if provision exists with same PID but different hash (content changed)
  OPTIONAL MATCH (old_p:Provision {pid: ob.pid})
    WHERE old_p.hash <> ob.hash AND old_p.tx_to IS NULL

  // Close old version if content changed
  FOREACH (_ IN CASE WHEN old_p IS NOT NULL THEN [1] ELSE [] END |
    SET old_p.tx_to = timestamp(),
        old_p.valid_to = timestamp(),
        old_p.superseded = true
  )

  // Create or match provision (use version_id to distinguish versions)
  WITH d, c, ob, jurisdiction_nodes, old_p,
       ob.pid + ':' + toString(timestamp()) AS version_id
  MERGE (p:Provision {pid: ob.pid, version_id: CASE WHEN old_p IS NOT NULL THEN version_id ELSE ob.pid END})
    ON CREATE SET
      p.text = ob.text,
      p.hash = ob.hash,
      p.tx_from = timestamp(),
      p.valid_from = timestamp(),
      p.tx_to = NULL,
      p.valid_to = NULL,
      p.superseded = false,
      p.version = CASE WHEN old_p IS NOT NULL THEN coalesce(old_p.version, 0) + 1 ELSE 1 END
    ON MATCH SET
      p.text = ob.text,
      p.hash = ob.hash

  MERGE (p)-[:IN_DOCUMENT]->(d)
  MERGE (p)-[:ABOUT]->(c)

  // Link to jurisdictions
  FOREACH (jn IN jurisdiction_nodes |
    MERGE (p)-[:APPLIES_TO]->(jn)
  )

  // Handle thresholds
  FOREACH (_ IN CASE WHEN ob.threshold_is_set THEN [1] ELSE [] END |
    MERGE (t:Threshold {pid: ob.pid, version_id: p.version_id})
      ON CREATE SET
        t.value = ob.threshold_value,
        t.unit = ob.threshold_unit,
        t.unit_normalized = ob.threshold_unit_normalized
      ON MATCH SET
        t.value = ob.threshold_value,
        t.unit = ob.threshold_unit,
        t.unit_normalized = ob.threshold_unit_normalized
    MERGE (p)-[:HAS_THRESHOLD]->(t)
  )

  // Create provenance tracking
  WITH p, ob, d
  MERGE (prov:Provenance {doc_id: $doc_id, start: ob.start, end: ob.end})
    ON CREATE SET prov.page = ob.page
    ON MATCH SET prov.page = coalesce(ob.page, prov.page)
  MERGE (p)-[:PROVENANCE]->(prov)

  // Link superseded provisions
  WITH p, old_p
  FOREACH (_ IN CASE WHEN old_p IS NOT NULL THEN [1] ELSE [] END |
    MERGE (p)-[:SUPERSEDES]->(old_p)
  )
"""


CYPHER_PROVISION_HISTORY = """
// Query provision history (all versions)
MATCH (p:Provision {pid: $pid})
OPTIONAL MATCH (p)-[:SUPERSEDES*]->(older:Provision)
RETURN p, older
ORDER BY p.version DESC
"""

CYPHER_ACTIVE_PROVISIONS_AT_TIME = """
// Query provisions that were active at a specific time
MATCH (p:Provision)-[:IN_DOCUMENT]->(d:Document {id: $doc_id})
WHERE p.tx_from <= $timestamp
  AND (p.tx_to IS NULL OR p.tx_to > $timestamp)
  AND p.valid_from <= $timestamp
  AND (p.valid_to IS NULL OR p.valid_to > $timestamp)
RETURN p, d
"""

CYPHER_PROVISION_CHANGES = """
// Query provision changes between two time periods
MATCH (p:Provision)-[:IN_DOCUMENT]->(d:Document)
WHERE (p.tx_from >= $start_time AND p.tx_from <= $end_time)
   OR (p.tx_to >= $start_time AND p.tx_to <= $end_time)
OPTIONAL MATCH (p)-[:SUPERSEDES]->(old_p:Provision)
RETURN p, old_p, d
ORDER BY p.tx_from DESC
"""


def upsert_from_entities(
    session, doc_id: str, source_url: str | None, entities: List[dict]
):
    jurisdictions = sorted(
        {
            e.get("attrs", {}).get("name")
            for e in entities
            if e.get("type") == "JURISDICTION"
            and e.get("attrs")
            and e["attrs"].get("name")
        }
    ) or ["Unknown"]

    obligations = []
    obligation_entities = [e for e in entities if e.get("type") == "OBLIGATION"]
    thresholds = [e for e in entities if e.get("type") == "THRESHOLD"]

    for entity in obligation_entities:
        pid = f"{doc_id}:{entity['start']}:{entity['end']}"
        contained_thresholds = [
            t
            for t in thresholds
            if entity["start"] <= t.get("start", 0) <= entity["end"]
            and t.get("end", 0) <= entity["end"]
        ]
        threshold = contained_thresholds[0] if contained_thresholds else None
        threshold_attrs = threshold.get("attrs", {}) if threshold else {}
        obligations.append(
            {
                "pid": pid,
                "text": entity.get("text", ""),
                "hash": str(abs(hash(entity.get("text", "")))),
                "start": entity.get("start"),
                "end": entity.get("end"),
                "concept": entity.get("attrs", {}).get("concept"),
                "page": entity.get("attrs", {}).get("page"),
                "threshold_is_set": bool(threshold),
                "threshold_value": threshold_attrs.get("value"),
                "threshold_unit": threshold_attrs.get("unit"),
                "threshold_unit_normalized": threshold_attrs.get("unit_normalized"),
            }
        )

    session.run(
        CYPHER_UPSERT,
        doc_id=doc_id,
        source_url=source_url,
        jurisdictions=jurisdictions,
        obligations=obligations,
    )
