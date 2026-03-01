import os
import json
import chromadb
from sentence_transformers import SentenceTransformer

class VectorMemory:
    """
    Feature 4: ChromaDB Vector Memory
    Embeds validated scientific discoveries into a local vector database.
    Allows the Explorer agent to search for "mathematically similar" prior discoveries
    to cross-pollinate constants and physics patterns.
    """
    def __init__(self, memory_dir):
        self.db_dir = os.path.join(memory_dir, 'chroma_db')
        os.makedirs(self.db_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.db_dir)
        
        # We use a lightweight local sentence transformer for embeddings
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self.collection = self.client.get_or_create_collection(name="discoveries")

    def embed_discovery(self, filepath):
        """Indexes a breakthrough JSON file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            hyp = data.get('hypothesis', {})
            topic = hyp.get('topic', '')
            blueprint = hyp.get('mathematical_blueprint', '')
            text = hyp.get('hypothesis', '')
            
            # Use the core physics as the embedding text
            embed_text = f"Topic: {topic}\nMath: {blueprint}\nTheory: {text}"
            
            doc_id = os.path.basename(filepath)
            
            # Skip if already embedded
            existing = self.collection.get(ids=[doc_id])
            if existing and existing['ids']:
                return False
                
            embedding = self.encoder.encode(embed_text).tolist()
            
            self.collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[embed_text],
                metadatas=[{
                    "topic": topic, 
                    "blueprint": blueprint,
                    "filepath": filepath
                }]
            )
            return True
        except Exception as e:
            print(f"[VECTOR-MEM] Failed to embed {filepath}: {e}")
            return False

    def query_similar_physics(self, query_topic, n_results=3):
        """Returns the raw mathematically-matched context for LLM injection."""
        try:
            if self.collection.count() == 0:
                return []
                
            query_embedding = self.encoder.encode(query_topic).tolist()
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results, self.collection.count())
            )
            
            context_blocks = []
            if results and results['documents'] and results['documents'][0]:
                for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
                    block = f"- **Prior Physics ({meta['topic']})**: `{meta['blueprint']}` -> {doc.split('Theory: ')[-1]}"
                    context_blocks.append(block)
            return context_blocks
        except Exception as e:
            print(f"[VECTOR-MEM] Query failed: {e}")
            return []
