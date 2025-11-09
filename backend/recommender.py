import json
import os
from dataclasses import dataclass
from typing import List, Optional
import re
import os

import numpy as np
from sentence_transformers import SentenceTransformer

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover
    faiss = None  # lazy fallback; will use numpy search if faiss not present

try:
    import google.generativeai as genai  # type: ignore
except Exception:
    genai = None

CATALOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'catalog.jsonl')


@dataclass
class Recommendation:
    assessment_url: str
    description: Optional[str]
    test_type: List[str]
    adaptive_support: str  # "Yes" or "No"
    remote_support: str    # "Yes" or "No"
    duration: Optional[int]
    relevance_score: Optional[float]


class Recommender:
    def __init__(self):
        self.model_name = "sentence-transformers/all-MiniLM-L6-v2"
        self.model = SentenceTransformer(self.model_name)
        self.items = []  # list of dicts
        self.texts = []  # for encoding
        self.types = []  # test types
        self.urls = []
        self.names = []
        self.descs = []
        self.emb = None
        self.index = None
        self._load_catalog()
        self._build_index()

    def _load_catalog(self):
        self.items = []
        if os.path.exists(CATALOG_PATH):
            with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        obj = json.loads(line)
                        if obj.get('category') == 'Pre-packaged Job Solutions':
                            continue
                        self.items.append(obj)
                    except Exception:
                        continue
        self.texts = [
            (it.get('name', '') or '') + " \n" + (it.get('description', '') or '')
            for it in self.items
        ]
        self.types = [it.get('test_type') for it in self.items]
        self.urls = [it.get('url') for it in self.items]
        self.names = [it.get('name') for it in self.items]
        self.descs = [it.get('description') for it in self.items]

    def _build_index(self):
        if not self.texts:
            self.emb = np.zeros((0, 384), dtype=np.float32)
            self.index = None
            return
        emb = self.model.encode(self.texts, normalize_embeddings=True, convert_to_numpy=True)
        emb = emb.astype('float32')
        self.emb = emb
        if faiss is not None and emb.shape[0] > 0:
            index = faiss.IndexFlatIP(emb.shape[1])
            index.add(emb)
            self.index = index
        else:
            self.index = None

    def _knn(self, qvec: np.ndarray, topk: int = 20):
        if self.index is not None:
            D, I = self.index.search(qvec.reshape(1, -1).astype('float32'), topk)
            return D[0], I[0]
        # numpy fallback
        sims = (self.emb @ qvec)
        I = np.argsort(-sims)[:topk]
        D = sims[I]
        return D, I

    def recommend(self, query: str, k: int = 10) -> List[Recommendation]:
        if not self.items:
            # cold start: no catalog yet
            return []
        q = self.model.encode([query], normalize_embeddings=True, convert_to_numpy=True)[0].astype('float32')
        D, I = self._knn(q, topk=max(30, k*3))
        # Collect candidates
        cands = []
        for score, idx in zip(D, I):
            if idx < 0 or idx >= len(self.items):
                continue
            cands.append({
                'name': self.names[idx],
                'url': self.urls[idx],
                'type': self.types[idx] or None,
                'desc': self.descs[idx],
                'score': float(score),
            })
        # Optional: rerank with Gemini if available
        api_key = os.environ.get('GEMINI_API_KEY')
        if api_key and genai is not None:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                # Build a compact prompt with numbered candidates; ask for JSON scores
                lines = []
                for i, c in enumerate(cands[:30]):
                    lines.append(f"{i+1}. name={c['name']}; url={c['url']}; type={c['type']}; desc={c['desc']}")
                prompt = (
                    "You are a ranking model. Given a hiring query, score each candidate assessment for relevance on a 0..1 scale. "
                    "Return strictly JSON with an array of objects {index, score}. No extra text.\n\n"
                    f"Query: {query}\nCandidates:\n" + "\n".join(lines) +
                    "\n\nJSON only: {\"scores\":[{\"index\":1,\"score\":0.9}] }"
                )
                resp = model.generate_content(prompt)
                text = resp.text or "{}"
                import json as _json
                data = _json.loads(text) if text.strip().startswith('{') else {}
                idx_to_score = {}
                for obj in data.get('scores', []):
                    try:
                        idx_to_score[int(obj['index'])-1] = float(obj['score'])
                    except Exception:
                        continue
                if idx_to_score:
                    for i, c in enumerate(cands[:30]):
                        if i in idx_to_score:
                            c['score'] = 0.5 * c['score'] + 0.5 * idx_to_score[i]
                    cands.sort(key=lambda x: x['score'], reverse=True)
            except Exception:
                pass
        # Balance across types if query suggests multiple domains
        types_present = set([c['type'] for c in cands if c['type']])
        balanced = []
        if len(types_present) >= 2:
            # simple round-robin by type among top candidates
            buckets = {}
            for c in cands:
                t = c['type'] or 'Unknown'
                buckets.setdefault(t, []).append(c)
            # interleave
            while len(balanced) < k and any(buckets.values()):
                for t in list(buckets.keys()):
                    if buckets[t]:
                        balanced.append(buckets[t].pop(0))
                        if len(balanced) >= k:
                            break
        else:
            balanced = cands[:k]
        # Deduplicate by URL
        seen = set()
        uniq = []
        for c in balanced:
            if c['url'] and c['url'] not in seen:
                seen.add(c['url'])
                uniq.append(c)
        # Ensure 5-10
        uniq = uniq[:max(5, min(k, 10))]
        results: List[Recommendation] = []
        for c in uniq:
            page_text = (c.get('desc') or '') + ' ' + (c.get('name') or '')
            # Infer adaptive and remote support heuristically
            adaptive = 'Yes' if re.search(r"adaptive|adaptive test|CAT|computer.?adaptive", page_text, re.I) else 'No'
            remote = 'Yes' if re.search(r"remote|proctor|online|unproctored|at home", page_text, re.I) else 'No'
            # Duration in minutes if mentioned like '60 minutes', '45 min'
            dur = None
            m = re.search(r"(\d{1,3})\s*(minutes|min)\b", page_text, re.I)
            if m:
                try:
                    dur = int(m.group(1))
                except Exception:
                    dur = None
            t = c.get('type')
            tlist = [t] if t else []
            results.append(Recommendation(
                assessment_url=c.get('url') or '',
                description=c.get('desc') or '',
                test_type=tlist,
                adaptive_support=adaptive,
                remote_support=remote,
                duration=dur,
                relevance_score=c.get('score')
            ))
        return results
