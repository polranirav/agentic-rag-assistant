"""
Neo4j Graph Store for GraphRAG.
Provides entity extraction and graph-based retrieval capabilities.
"""

import logging
import os
from typing import List, Dict, Any, Optional, Tuple

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

logger = logging.getLogger(__name__)

# Neo4j connection settings (from environment or defaults)
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")


class GraphStore:
    """
    Neo4j-based graph store for entity extraction and graph retrieval.
    
    Implements GraphRAG pattern:
    1. Extract entities and relationships from documents
    2. Store in Neo4j knowledge graph
    3. Query graph for context enrichment during retrieval
    """
    
    def __init__(self, uri: str = None, user: str = None, password: str = None):
        self.uri = uri or NEO4J_URI
        self.user = user or NEO4J_USER
        self.password = password or NEO4J_PASSWORD
        self.driver = None
        self._connected = False
    
    def connect(self) -> bool:
        """Connect to Neo4j database."""
        try:
            from neo4j import GraphDatabase
            
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            # Verify connection
            self.driver.verify_connectivity()
            self._connected = True
            logger.info(f"✅ Connected to Neo4j at {self.uri}")
            return True
        except ImportError:
            logger.warning("Neo4j driver not installed. Install with: pip install neo4j")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            return False
    
    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()
            self._connected = False
            logger.info("Neo4j connection closed")
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    def create_indexes(self):
        """Create indexes for efficient graph queries."""
        if not self._connected:
            return
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.name)",
            "CREATE INDEX IF NOT EXISTS FOR (d:Document) ON (d.id)",
            "CREATE INDEX IF NOT EXISTS FOR (c:Concept) ON (c.name)",
        ]
        
        with self.driver.session() as session:
            for idx in indexes:
                try:
                    session.run(idx)
                except Exception as e:
                    logger.warning(f"Index creation warning: {e}")
        
        logger.info("✅ Neo4j indexes created")
    
    def extract_entities(self, text: str, openai_api_key: str) -> List[Dict[str, Any]]:
        """
        Extract entities and relationships from text using LLM.
        
        Returns list of: {name, type, relationships: [{target, relation}]}
        """
        try:
            llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0,
                api_key=openai_api_key
            )
            
            extraction_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert at extracting entities and relationships from text.

Extract entities (people, organizations, concepts, technologies, skills, etc.) and their relationships.

Output format (JSON array):
[
  {"name": "Entity Name", "type": "PERSON|ORG|CONCEPT|SKILL|TECH", "relationships": [{"target": "Other Entity", "relation": "WORKS_AT|KNOWS|USES|REQUIRES|etc"}]}
]

Rules:
- Extract 3-10 most important entities
- Focus on meaningful relationships
- Use UPPERCASE for relation types
- Return valid JSON only, no markdown"""),
                ("human", "{text}")
            ])
            
            chain = extraction_prompt | llm | StrOutputParser()
            result = chain.invoke({"text": text[:3000]})  # Limit text length
            
            # Parse JSON response
            import json
            entities = json.loads(result.strip())
            
            logger.info(f"Extracted {len(entities)} entities from text")
            return entities
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return []
    
    def store_entities(self, entities: List[Dict], doc_id: str, doc_source: str):
        """Store extracted entities and relationships in Neo4j."""
        if not self._connected or not entities:
            return
        
        with self.driver.session() as session:
            # Create document node
            session.run(
                "MERGE (d:Document {id: $id}) SET d.source = $source",
                id=doc_id, source=doc_source
            )
            
            # Create entity nodes and relationships
            for entity in entities:
                # Create entity node
                session.run(
                    """
                    MERGE (e:Entity {name: $name})
                    SET e.type = $type
                    WITH e
                    MATCH (d:Document {id: $doc_id})
                    MERGE (e)-[:MENTIONED_IN]->(d)
                    """,
                    name=entity.get("name", ""),
                    type=entity.get("type", "CONCEPT"),
                    doc_id=doc_id
                )
                
                # Create relationships to other entities
                for rel in entity.get("relationships", []):
                    session.run(
                        """
                        MERGE (e1:Entity {name: $source_name})
                        MERGE (e2:Entity {name: $target_name})
                        MERGE (e1)-[r:RELATES_TO {type: $rel_type}]->(e2)
                        """,
                        source_name=entity.get("name", ""),
                        target_name=rel.get("target", ""),
                        rel_type=rel.get("relation", "RELATES_TO")
                    )
        
        logger.info(f"Stored {len(entities)} entities for document {doc_id}")
    
    def query_related_entities(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find entities related to the query using graph traversal.
        
        Returns entities within 2 hops of query-matched entities.
        """
        if not self._connected:
            return []
        
        # Extract keywords from query for matching
        keywords = [w.lower() for w in query.split() if len(w) > 3]
        
        with self.driver.session() as session:
            # Find entities matching keywords and their neighbors
            result = session.run(
                """
                MATCH (e:Entity)
                WHERE any(kw IN $keywords WHERE toLower(e.name) CONTAINS kw)
                OPTIONAL MATCH (e)-[r]-(related:Entity)
                RETURN e.name as name, e.type as type,
                       collect(DISTINCT {name: related.name, relation: type(r)}) as relationships
                LIMIT $limit
                """,
                keywords=keywords,
                limit=limit
            )
            
            entities = []
            for record in result:
                entities.append({
                    "name": record["name"],
                    "type": record["type"],
                    "relationships": record["relationships"]
                })
            
            logger.info(f"Found {len(entities)} related entities for query")
            return entities
    
    def get_entity_context(self, entity_names: List[str]) -> str:
        """
        Get rich context about entities by traversing the graph.
        
        Returns formatted string describing entities and their relationships.
        """
        if not self._connected or not entity_names:
            return ""
        
        context_parts = []
        
        with self.driver.session() as session:
            for name in entity_names[:5]:  # Limit to 5 entities
                result = session.run(
                    """
                    MATCH (e:Entity {name: $name})
                    OPTIONAL MATCH (e)-[r]->(related:Entity)
                    OPTIONAL MATCH (e)-[:MENTIONED_IN]->(d:Document)
                    RETURN e.name as name, e.type as type,
                           collect(DISTINCT {target: related.name, relation: type(r)}) as relationships,
                           collect(DISTINCT d.source) as sources
                    """,
                    name=name
                )
                
                for record in result:
                    if record["name"]:
                        context = f"Entity: {record['name']} ({record['type']})"
                        
                        # Add relationships
                        rels = [r for r in record["relationships"] if r["target"]]
                        if rels:
                            rel_str = ", ".join([f"{r['relation']} -> {r['target']}" for r in rels[:5]])
                            context += f"\n  Relationships: {rel_str}"
                        
                        # Add sources
                        sources = record["sources"]
                        if sources:
                            context += f"\n  Found in: {', '.join(sources[:3])}"
                        
                        context_parts.append(context)
        
        return "\n\n".join(context_parts)


# Singleton instance for easy access
_graph_store: Optional[GraphStore] = None


def get_graph_store() -> GraphStore:
    """Get or create the global GraphStore instance."""
    global _graph_store
    if _graph_store is None:
        _graph_store = GraphStore()
        _graph_store.connect()
        if _graph_store.is_connected:
            _graph_store.create_indexes()
    return _graph_store
