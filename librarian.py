import os
import json
import shutil
import argparse

class Librarian:
    def __init__(self, discoveries_dir, press_dir, dry_run=True):
        self.discoveries_dir = os.path.abspath(discoveries_dir)
        self.press_dir = os.path.abspath(press_dir)
        self.dry_run = dry_run
        
        # Tiers
        self.tiers = {
            "01_breakthroughs": (80, 101),
            "02_confirmed_theory": (50, 80),
            "03_technical_notes": (20, 50),
            "04_failed_or_trivial": (0, 20)
        }
        
        # Stats
        self.stats = {
            "moved": 0,
            "deleted_press": 0,
            "errors": 0
        }

    def _get_tier(self, score):
        for tier, (low, high) in self.tiers.items():
            if low <= score < high:
                return tier
        return "04_failed_or_trivial"

    def run(self):
        print(f"--- Scientific Librarian {'(DRY RUN)' if self.dry_run else '(EXECUTE)'} ---")
        
        # 1. Create Tier Directories
        for tier in self.tiers.keys():
            tier_path = os.path.join(self.discoveries_dir, tier)
            if not self.dry_run and not os.path.exists(tier_path):
                os.makedirs(tier_path)

        # 2. Iterate Discoveries
        for root, dirs, files in os.walk(self.discoveries_dir):
            # Skip tier directories to avoid infinite loops if script is re-run
            if any(tier in root for tier in self.tiers.keys()):
                continue
                
            for file in files:
                if not file.endswith('.json'):
                    continue
                
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Extract Score
                    score = data.get('evaluation', {}).get('significance_score', 0)
                    if isinstance(score, str):
                        import re
                        match = re.search(r'\d+', score)
                        score = int(match.group()) if match else 0
                    
                    target_tier = self._get_tier(score)
                    target_dir = os.path.join(self.discoveries_dir, target_tier)
                    target_path = os.path.join(target_dir, file)
                    
                    print(f"[DISCOVERY] {file} (Score: {score}) -> {target_tier}")
                    
                    if not self.dry_run:
                        shutil.move(file_path, target_path)
                    
                    self.stats["moved"] += 1
                    
                    # 3. Check for Press Release Pruning
                    if target_tier in ["03_technical_notes", "04_failed_or_trivial"]:
                        topic = data.get('hypothesis', {}).get('topic', '')
                        
                        # Match BaseModule._sanitize_slug logic
                        import re
                        sanitized = re.sub(r'[\\/:*?"<>|]', '', topic)
                        sanitized = re.sub(r'[^a-zA-Z0-9\.\-_]', '_', sanitized)
                        sanitized = re.sub(r'_{2,}', '_', sanitized)
                        clean_name = sanitized[:50].rstrip('_').strip('_').upper()
                        
                        press_filename = f"BREAKTHROUGH_{clean_name}.md"
                        press_path = os.path.join(self.press_dir, press_filename)
                        
                        if os.path.exists(press_path):
                            print(f"  [PRUNE] Found press release: {press_filename} (Reason: Low Tier)")
                            if not self.dry_run:
                                os.remove(press_path)
                            self.stats["deleted_press"] += 1
                        else:
                            # Try a broader check if direct match fails
                            # Sometimes the slug is slightly different
                            topic_slug = clean_name[:20] # Check first 20 chars
                            for pr_file in os.listdir(self.press_dir):
                                if topic_slug in pr_file.upper() and pr_file.startswith("BREAKTHROUGH_"):
                                    print(f"  [PRUNE] Found fuzzy-match press release: {pr_file} (Reason: Low Tier)")
                                    if not self.dry_run:
                                        os.remove(os.path.join(self.press_dir, pr_file))
                                    self.stats["deleted_press"] += 1

                except Exception as e:
                    print(f"  [ERROR] Failed to process {file}: {e}")
                    self.stats["errors"] += 1

        print("\n--- Final Stats ---")
        print(f"Files Moved: {self.stats['moved']}")
        print(f"Press Releases Pruned: {self.stats['deleted_press']}")
        print(f"Errors: {self.stats['errors']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scientific Librarian Cleanup")
    parser.add_argument("--execute", action="store_true", help="Execute the changes")
    parser.add_argument("--discoveries", default="c:/continuous/discoveries", help="Path to discoveries dir")
    parser.add_argument("--press", default="c:/continuous/memory/press_releases", help="Path to press releases dir")
    
    args = parser.parse_args()
    
    lib = Librarian(args.discoveries, args.press, dry_run=not args.execute)
    lib.run()
