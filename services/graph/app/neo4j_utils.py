from __future__ import annotations

import hashlib
import threading
from typing import List

from neo4j import GraphDatabase

from .config import settings

_driver = None
_driver_lock = threading.Lock()


def driver():
    global _driver
    if _driver is None:
        with _driver_lock:
            if _driver is None:
                _driver = GraphDatabase.driver(
                    settings.neo4j_uri,
                    auth=(settings.neo4j_user, settings.neo4j_password),
                )
    return _driver


def close_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


CYPHER_UPSERT = """
MERGE (d:Document {id: $doc_id})
  ON CREATE SET d.source_url = $source_url, d.created_at = timestamp()
  ON MATCH SET  d.source_url = coalesce($source_url, d.source_url)
WITH d
UNWIND $jurisdictions AS jname
  MERGE (j:Jurisdiction {name: jname})
  MERGE (d)-[:MENTIONS]->(j)
WITH d, collect(j) AS jurisdiction_nodes
UNWIND $obligations AS ob
  MERGE (c:Concept {name: coalesce(ob.concept, 'unspecified')})
  MERGE (p:Provision {pid: ob.pid})
    ON CREATE SET p.text = ob.text, p.tx_from = timestamp(), p.valid_from = timestamp(), p.hash = ob.hash
    ON MATCH  SET p.text = ob.text, p.hash = ob.hash
  MERGE (p)-[:IN_DOCUMENT]->(d)
  MERGE (p)-[:ABOUT]->(c)
  FOREACH (jn IN jurisdiction_nodes |
    MERGE (p)-[:APPLIES_TO]->(jn)
  )
  FOREACH (_ IN CASE WHEN ob.threshold_is_set THEN [1] ELSE [] END |
    MERGE (t:Threshold {pid: ob.pid})
      ON CREATE SET t.value = ob.threshold_value, t.unit = ob.threshold_unit, t.unit_normalized = ob.threshold_unit_normalized
      ON MATCH  SET t.value = ob.threshold_value, t.unit = ob.threshold_unit, t.unit_normalized = ob.threshold_unit_normalized
    MERGE (p)-[:HAS_THRESHOLD]->(t)
  )
  WITH p, ob
  MERGE (prov:Provenance {doc_id: $doc_id, start: ob.start, end: ob.end})
    ON CREATE SET prov.page = ob.page
    ON MATCH SET prov.page = coalesce(ob.page, prov.page)
  MERGE (p)-[:PROVENANCE]->(prov)
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
                "hash": hashlib.sha256(entity.get("text", "").encode()).hexdigest()[:16],
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
