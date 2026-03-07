import os
import json
import chromadb
import requests
import time
from sentence_transformers import SentenceTransformer

class VectorMemory:
    """
    ChromaDB Vector Memory
    Embeds validated scientific discoveries and failures into a local vector database.
    Allows for semantic search to avoid duplication and cross-pollinate findings.
    """
    def __init__(self, config):
        self.config = config
        memory_dir = self.config['paths']['memory']
        self.db_dir = os.path.join(memory_dir, 'chroma_db')
        os.makedirs(self.db_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.db_dir)
        
        # Use nomic-embed-text via Ollama if requested, otherwise fallback to local ST
        self.use_ollama = self.config.get('research', {}).get('use_ollama_embeddings', False)
        self.embedding_model = self.config.get('hardware', {}).get('embedding_model', 'nomic-embed-text')
        self.ollama_url = self.config.get('hardware', {}).get('local_url', 'http://localhost:11434/api/embeddings')
        
        if not self.use_ollama:
            self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
            
        self.collection = self.client.get_or_create_collection(name="science_memory")
        self.tensor_cache = self.client.get_or_create_collection(name="tensor_cache")

    def _get_embedding(self, text):
        if self.use_ollama:
            try:
                # Clean URL for API call
                base_url = self.ollama_url.split('/api/')[0]
                resp = requests.post(
                    f"{base_url}/api/embeddings",
                    json={"model": self.embedding_model, "prompt": text},
                    timeout=5
                )
                if resp.status_code == 200:
                    return resp.json()['embedding']
            except Exception as e:
                print(f"[VECTOR-MEM] Ollama embedding failed, falling back: {e}")
        
        # Fallback to SentenceTransformer
        if not hasattr(self, 'encoder'):
            self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        return self.encoder.encode(text).tolist()

    def embed_research(self, topic, text, metadata=None, is_failure=False):
        """Indexes a research finding or failure."""
        try:
            timestamp = metadata.pop('timestamp', 0) if metadata else 0
            doc_id = f"{'FAIL' if is_failure else 'SUCCESS'}_{topic[:50]}_{timestamp}"
            
            # Clean text for embedding
            embed_text = f"Status: {'Failure' if is_failure else 'Success'}\nTopic: {topic}\nContent: {text}"
            
            # Check if exists
            existing = self.collection.get(ids=[doc_id])
            if existing and existing['ids']:
                return False
                
            embedding = self._get_embedding(embed_text)
            
            meta_payload = {
                "topic": topic,
                "type": "failure" if is_failure else "success"
            }
            if metadata:
                meta_payload.update(metadata)
                
            self.collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[embed_text],
                metadatas=[meta_payload]
            )
            return True
        except Exception as e:
            print(f"[VECTOR-MEM] Failed to embed {topic}: {e}")
            return False

    def query_past_research(self, query_topic, n_results=5, filter_type=None):
        """Returns semantically similar past research. filter_type can be 'success' or 'failure'."""
        try:
            if self.collection.count() == 0:
                return []
                
            query_embedding = self._get_embedding(query_topic)
            
            query_args = {
                "query_embeddings": [query_embedding],
                "n_results": min(n_results, self.collection.count())
            }
            
            if filter_type:
                query_args["where"] = {"type": filter_type}
                
            results = self.collection.query(**query_args)
            
            matches = []
            if results and results['documents'] and results['documents'][0]:
                for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
                    matches.append({
                        "topic": meta.get('topic'),
                        "type": meta.get('type'),
                        "content": doc,
                        "metadata": meta
                    })
            return matches
        except Exception as e:
            print(f"[VECTOR-MEM] Query failed: {e}")
            return []

    def store_tensor_component(self, metric_key, component_name, symbolic_expr):
        """Stores a cached symbolic tensor component."""
        try:
            doc_id = f"{metric_key}_{component_name}"
            metadata = {
                "metric_key": metric_key,
                "component": component_name,
                "timestamp": time.time()
            }
            # Remove existing if any to update
            self.tensor_cache.delete(ids=[doc_id])
            
            self.tensor_cache.add(
                ids=[doc_id],
                documents=[str(symbolic_expr)],
                metadatas=[meta_payload] if False else [metadata] # Just being safe with metadata
            )
            return True
        except Exception as e:
            print(f"[VECTOR-MEM] Cache store failed for {component_name}: {e}")
            return False

    def get_tensor_component(self, metric_key, component_name):
        """Retrieves a cached symbolic tensor component."""
        try:
            doc_id = f"{metric_key}_{component_name}"
            results = self.tensor_cache.get(ids=[doc_id])
            if results and results['documents']:
                return results['documents'][0]
            return None
        except Exception as e:
            print(f"[VECTOR-MEM] Cache retrieval failed: {e}")
            return None
