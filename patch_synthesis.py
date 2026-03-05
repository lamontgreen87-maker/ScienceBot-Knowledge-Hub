with open("c:\\continuous\\agent.py", "r", encoding="utf-8") as f:
    text = f.read()

import re

# Insert _run_with_url definition
match1 = re.search(r'(prelim_results = self.pop_from_research_queue\(pull_size\)\n.*?if not prelim_results:\n.*?time\.sleep\(2\).*?\n.*?continue\n\n.*?Popped \{len\(prelim_results\)\} items.*?\n)', text, re.DOTALL)
if match1:
    insertion = """
                def _run_with_url(url, func, *args, **kwargs):
                    from base_module import _THREAD_LOCAL_CONTEXT
                    _THREAD_LOCAL_CONTEXT.api_url = url
                    return func(*args, **kwargs)
"""
    new_text = match1.group(1) + insertion
    text = text.replace(match1.group(1), new_text)

# Fix A.0
old_a0 = r"""                        with concurrent.futures.ThreadPoolExecutor(max_workers=num_shards) as shard_executor:
                            shard_futures = [shard_executor.submit(self.explorer.generate_batch_hypotheses, s, topic) for s in shards]
                            for f in shard_futures:"""
new_a0 = r"""                        with concurrent.futures.ThreadPoolExecutor(max_workers=num_shards) as shard_executor:
                            shard_futures = []
                            for i, s in enumerate(shards):
                                t_url = api_pool[i % len(api_pool)] if api_pool else None
                                shard_futures.append(shard_executor.submit(_run_with_url, t_url, self.explorer.generate_batch_hypotheses, s, topic))
                            for f in shard_futures:"""
text = text.replace(old_a0, new_a0)

# Fix A.1
old_a1 = r"""                    with concurrent.futures.ThreadPoolExecutor(max_workers=num_shards) as shard_executor:
                        shard_futures = [shard_executor.submit(self.explorer.refine_batch, s, topic) for s in shards]
                        for f in shard_futures:"""
new_a1 = r"""                    with concurrent.futures.ThreadPoolExecutor(max_workers=num_shards) as shard_executor:
                        shard_futures = []
                        for i, s in enumerate(shards):
                            t_url = api_pool[i % len(api_pool)] if api_pool else None
                            shard_futures.append(shard_executor.submit(_run_with_url, t_url, self.explorer.refine_batch, s, topic))
                        for f in shard_futures:"""
text = text.replace(old_a1, new_a1)

# Fix B
old_b = r"""                with concurrent.futures.ThreadPoolExecutor(max_workers=num_shards) as shard_executor:
                    shard_futures = [(shard_executor.submit(self.auditor.verify_batch, s), offset)
                                     for s, offset in zip(shards, shard_offsets)]
                    for future, offset in shard_futures:"""
new_b = r"""                with concurrent.futures.ThreadPoolExecutor(max_workers=num_shards) as shard_executor:
                    shard_futures = []
                    for i, (s, offset) in enumerate(zip(shards, shard_offsets)):
                        t_url = api_pool[i % len(api_pool)] if api_pool else None
                        shard_futures.append((shard_executor.submit(_run_with_url, t_url, self.auditor.verify_batch, s), offset))
                    for future, offset in shard_futures:"""
text = text.replace(old_b, new_b)

# Fix Wave 2
old_w2 = r"""                with concurrent.futures.ThreadPoolExecutor(max_workers=max_construction_workers) as executor:
                    construction_futures = {executor.submit(self.worker_stage_construction, r, None): r['topic'] for r in prelim_results}
                    for f in concurrent.futures.as_completed(construction_futures):"""
new_w2 = r"""                with concurrent.futures.ThreadPoolExecutor(max_workers=max_construction_workers) as executor:
                    construction_futures = {}
                    for i, r in enumerate(prelim_results):
                        t_url = api_pool[i % len(api_pool)] if api_pool else None
                        future = executor.submit(self.worker_stage_construction, r, t_url)
                        construction_futures[future] = r['topic']
                    for f in concurrent.futures.as_completed(construction_futures):"""
text = text.replace(old_w2, new_w2)

# Fix Wave 2.5
old_w25 = r"""                    with concurrent.futures.ThreadPoolExecutor(max_workers=max_construction_workers) as executor:
                        fix_futures = {executor.submit(self.worker_stage_self_fix, test_results[i], audit_map[i], None): i for i in fix_candidates}
                        fixed_count = 0
                        for f in concurrent.futures.as_completed(fix_futures):"""
new_w25 = r"""                    with concurrent.futures.ThreadPoolExecutor(max_workers=max_construction_workers) as executor:
                        fix_futures = {}
                        for i, idx in enumerate(fix_candidates):
                            t_url = api_pool[i % len(api_pool)] if api_pool else None
                            future = executor.submit(self.worker_stage_self_fix, test_results[idx], audit_map[idx], t_url)
                            fix_futures[future] = idx
                        fixed_count = 0
                        for f in concurrent.futures.as_completed(fix_futures):"""
text = text.replace(old_w25, new_w25)

# Fix Wave 3
old_w3 = r"""                with concurrent.futures.ThreadPoolExecutor(max_workers=max_construction_workers) as executor:
                    finalize_futures = []
                    for i, res in enumerate(test_results):
                        report = audit_map.get(i, {"audit_passed": False, "rejection_type": "FATAL", "reasoning": "Batch audit index mismatch."})
                        finalize_futures.append(executor.submit(self.worker_stage_finalize, res, report, None))
                    
                    for f in concurrent.futures.as_completed(finalize_futures):"""
new_w3 = r"""                with concurrent.futures.ThreadPoolExecutor(max_workers=max_construction_workers) as executor:
                    finalize_futures = []
                    for i, res in enumerate(test_results):
                        t_url = api_pool[i % len(api_pool)] if api_pool else None
                        report = audit_map.get(i, {"audit_passed": False, "rejection_type": "FATAL", "reasoning": "Batch audit index mismatch."})
                        finalize_futures.append(executor.submit(self.worker_stage_finalize, res, report, t_url))
                    
                    for f in concurrent.futures.as_completed(finalize_futures):"""
text = text.replace(old_w3, new_w3)

with open("c:\\continuous\\agent.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Patch applied.")
