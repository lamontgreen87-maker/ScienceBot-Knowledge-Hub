import subprocess
import os
import json
import time
from base_module import BaseModule

class GitHubSync(BaseModule):
    COMPONENT_NAME = "sync"
    def __init__(self, config, ui=None):
        super().__init__(config, ui)
        self.repo_url = self.config.get('github', {}).get('repository_url')
        self.token = self.config.get('github', {}).get('token')
        self.branch = self.config.get('github', {}).get('branch', 'main')
        self.enabled = self.config.get('github', {}).get('enabled', False)
        self.root_dir = os.path.dirname(os.path.abspath(__file__))
        self.queue_path = os.path.join(self.config['paths']['memory'], "review_queue.json")

    def initialize_repo(self):
        """Sets up the local git repository if not already present."""
        if not self.enabled or not self.repo_url:
            return False
            
        git_dir = os.path.join(self.root_dir, ".git")
        if not os.path.exists(git_dir):
            if self.ui:
                self.ui.print_log("[SYNC] Initializing local Git repository...")
            
            subprocess.run(["git", "init"], cwd=self.root_dir)
            
            # Use token for authentication if available
            remote_url = self.repo_url
            if self.token and "ghp_" in self.token:
                remote_url = self.repo_url.replace("https://", f"https://{self.token}@")
            
            subprocess.run(["git", "remote", "add", "origin", remote_url], cwd=self.root_dir)
            return True
        return True

    def check_consistency(self):
        """
        Runs on startup. Lists local knowledge, discoveries and press releases,
        checks if they match the remote repo, and adds missing/changed ones to the review queue.
        """
        if not self.enabled:
            return

        if self.ui:
            self.ui.print_log("[SYNC] Performing Startup Consistency Audit...")

        self.initialize_repo()
        
        # Fresh fetch to see what the remote has
        subprocess.run(["git", "fetch", "origin"], cwd=self.root_dir, capture_output=True)

        # 1. Get list of files tracked in remote
        res = subprocess.run(["git", "ls-files"], cwd=self.root_dir, capture_output=True, text=True)
        tracked_files = set(res.stdout.splitlines())

        # 2. Get local status (to find modified tracked files)
        status_res = subprocess.run(["git", "status", "--porcelain"], cwd=self.root_dir, capture_output=True, text=True)
        status_lines = status_res.stdout.splitlines()
        modified_files = {line[3:].strip() for line in status_lines if line.startswith(" M") or line.startswith("M ")}

        # 3. Scan directories
        queue = self._safe_load_json(self.queue_path, default=[])
        queued_paths = {q['file_path'] for q in queue}
        
        folders_to_scan = [
            self.config['paths']['discoveries'],
            os.path.join(self.config['paths']['memory'], "knowledge"),
            os.path.join(self.config['paths']['memory'], "press_releases")
        ]
        
        new_items = 0
        for folder in folders_to_scan:
            if not os.path.exists(folder): continue
            for root, _, files in os.walk(folder):
                for f in files:
                    full_path = os.path.join(root, f)
                    rel_path = os.path.relpath(full_path, self.root_dir).replace("\\", "/")
                    
                    # If not tracked, OR if tracked but modified locally, OR if not in queue
                    needs_review = False
                    if rel_path not in tracked_files:
                        needs_review = True
                    elif rel_path in modified_files:
                        needs_review = True
                    
                    if needs_review and rel_path not in queued_paths:
                        queue.append({
                            "file_path": rel_path,
                            "review_count": 0,
                            "cumulative_score": 0,
                            "status": "pending_review",
                            "submission_ready": False,
                            "added_timestamp": time.time()
                        })
                        queued_paths.add(rel_path)
                        new_items += 1
        
        if new_items > 0:
            self._safe_save_json(self.queue_path, queue)
            if self.ui:
                self.ui.print_log(f"[SYNC] Consistency Audit complete. Added {new_items} new items to Peer-Review Queue.")
        else:
            if self.ui:
                self.ui.print_log("[SYNC] Consistency Audit complete. Local knowledge matches GitHub.")

    def sync_knowledge(self, message="Update Knowledge Base"):
        """
        Modified to ONLY push files that are marked as 'submission_ready' in the review queue.
        Also pushes the journal by default.
        """
        if not self.enabled:
            return False

        if self.ui:
            self.ui.print_log(f"[SYNC] Preparing Peer-Reviewed Push: {message}...")

        try:
            queue = self._safe_load_json(self.queue_path, default=[])
            ready_files = [q for q in queue if q.get('submission_ready')]
            
            if not ready_files:
                # Always sync the journal if enabled, even if no discoveries are ready
                journal_path = os.path.join(self.config['paths']['memory'], "scientific_journal.json")
                if os.path.exists(journal_path):
                    subprocess.run(["git", "add", journal_path], cwd=self.root_dir)
            else:
                for q in ready_files:
                    path = os.path.join(self.root_dir, q['file_path'])
                    if os.path.exists(path):
                        subprocess.run(["git", "add", q['file_path']], cwd=self.root_dir)
                
                # Also add journal
                journal_path = os.path.join(self.config['paths']['memory'], "scientific_journal.json")
                if os.path.exists(journal_path):
                    subprocess.run(["git", "add", journal_path], cwd=self.root_dir)

            # Commit
            result = subprocess.run(["git", "commit", "-m", message], cwd=self.root_dir, capture_output=True, text=True)
            if "nothing to commit" in result.stdout:
                return True

            # Push
            push_res = subprocess.run(["git", "push", "origin", self.branch], cwd=self.root_dir, capture_output=True, text=True)
            
            if push_res.returncode == 0:
                # Remove ready files from queue after successful push
                new_queue = [q for q in queue if not q.get('submission_ready')]
                self._safe_save_json(self.queue_path, new_queue)
                if self.ui:
                    self.ui.print_log(f"[SYNC] ✅ Successfully pushed vetted knowledge to {self.branch}.")
                return True
            else:
                if self.ui:
                    self.ui.print_log(f"[SYNC] ❌ Push failed: {push_res.stderr}")
                return False
                
        except Exception as e:
            if self.ui:
                self.ui.print_log(f"[SYNC] Error during synchronization: {e}")
            return False

if __name__ == "__main__":
    # Test stub
    pass
