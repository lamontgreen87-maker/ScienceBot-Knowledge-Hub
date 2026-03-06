import os
import json
import time

class KnowledgeBuffer:
    def __init__(self, buffer_path="memory/swarm_buffer.md", max_entries=20):
        self.buffer_path = buffer_path
        self.max_entries = max_entries
        self._ensure_path()

    def _ensure_path(self):
        os.makedirs(os.path.dirname(self.buffer_path), exist_ok=True)
        if not os.path.exists(self.buffer_path):
            with open(self.buffer_path, "w", encoding="utf-8") as f:
                f.write("# Eternal Swarm Knowledge Buffer\n\n")

    def append_finding(self, topic, findings, status="Success"):
        """Atomic append to the live buffer."""
        timestamp = time.strftime("%H:%M:%S")
        entry = f"### [{timestamp}] {topic} | STATUS: {status} | AUDIT: PENDING | SYNTH: PENDING | RIGOR: 0\n{findings}\n\n---\n"
        
        # Read current content
        try:
            with open(self.buffer_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except:
            lines = []

        # Keep only last N entries (simplistic rotation)
        # We look for the "---" separators
        entries = []
        current_entry = []
        for line in lines:
            if line.strip() == "---":
                entries.append("".join(current_entry) + "---\n")
                current_entry = []
            else:
                current_entry.append(line)
        
        entries.append(entry)
        if len(entries) > self.max_entries:
            entries = entries[-self.max_entries:]

        # Rewriting header + entries
        with open(self.buffer_path, "w", encoding="utf-8") as f:
            f.write("# Eternal Swarm Knowledge Buffer (Live Update)\n\n")
            f.writelines(entries)

    def get_latest_context(self):
        """Returns the entire buffer as a string for LLM ingestion."""
        try:
            with open(self.buffer_path, "r", encoding="utf-8") as f:
                return f.read()
        except:
            return "No live context available."

    def update_audit(self, topic, new_status, reason="", rigor_score=None):
        """Updates the audit flag for a specific finding using regex for robustness."""
        try:
            with open(self.buffer_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            import re
            lines = content.split('\n')
            new_lines = []
            updated = False
            for line in lines:
                if f"### [" in line and topic in line and "STATUS: Success" in line:
                    # Extract timestamp
                    ts_match = re.search(r"### \[(\d{2}:\d{2}:\d{2})\]", line)
                    ts = ts_match.group(1) if ts_match else "00:00:00"
                    
                    # Preserve SYNTH status if present
                    synth_match = re.search(r"SYNTH: (\w+)", line)
                    synth_status = synth_match.group(1) if synth_match else "PENDING"
                    
                    new_line = f"### [{ts}] {topic} | STATUS: Success | AUDIT: {new_status} | SYNTH: {synth_status}"
                    if rigor_score is not None:
                        new_line += f" | RIGOR: {rigor_score}"
                    else:
                        new_line += " | RIGOR: 0"
                    if reason:
                        new_line += f" | REASON: {reason}"
                    
                    new_lines.append(new_line)
                    updated = True
                else:
                    new_lines.append(line)

            if updated:
                with open(self.buffer_path, "w", encoding="utf-8") as f:
                    f.write('\n'.join(new_lines))
        except Exception as e:
            pass

    def update_synth_status(self, topic, new_status):
        """Updates the SYNTH status for a specific finding."""
        try:
            with open(self.buffer_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            import re
            lines = content.split('\n')
            new_lines = []
            updated = False
            for line in lines:
                if f"### [" in line and topic in line:
                    # Capture the whole line and replace SYNTH part
                    if "SYNTH:" in line:
                        new_line = re.sub(r"SYNTH: \w+", f"SYNTH: {new_status}", line)
                    else:
                        # Append it if missing (legacy support)
                        new_line = line.replace(" | RIGOR:", f" | SYNTH: {new_status} | RIGOR:")
                    
                    new_lines.append(new_line)
                    updated = True
                else:
                    new_lines.append(line)

            if updated:
                with open(self.buffer_path, "w", encoding="utf-8") as f:
                    f.write('\n'.join(new_lines))
        except:
            pass

    def get_pending_findings(self):
        """Returns a list of findings that haven't been audited yet."""
        try:
            with open(self.buffer_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            entries = content.split("---")
            pending = []
            for entry in entries:
                if "AUDIT: PENDING" in entry:
                    pending.append(entry.strip())
            return pending
        except:
            return []

    def get_promotable_findings(self):
        """Returns verified findings that haven't been synthesized yet."""
        try:
            with open(self.buffer_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            entries = content.split("---")
            promotable = []
            for entry in entries:
                if "AUDIT: VERIFIED" in entry and "SYNTH: PENDING" in entry:
                    promotable.append(entry.strip())
            return promotable
        except:
            return []

    def clear(self):
        """Clears the buffer after a 70B digestion to refresh focus."""
        with open(self.buffer_path, "w", encoding="utf-8") as f:
            f.write("# Eternal Swarm Knowledge Buffer (Refreshed)\n\n")

if __name__ == "__main__":
    # Unit test
    kb = KnowledgeBuffer("/tmp/test_buffer.md", max_entries=3)
    kb.append_finding("Gravity", "Found 8B proof of curvature.")
    kb.append_finding("Singularity", "8B failed to resolve math.")
    kb.append_finding("Event Horizon", "8B simulated photon spheres.")
    kb.append_finding("Hawking", "8B added radiation data.") # Should bump "Gravity"
    print(kb.get_latest_context())
