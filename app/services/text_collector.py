import json
from pathlib import Path

def collect_texts(json_path: Path) -> str:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    texts = []
    for item in data:
        for post in item.get("latestPosts", []):
            if cap := post.get("caption"):
                texts.append(cap)
            for cm in post.get("latestComments", []):
                if txt := cm.get("text"):
                    texts.append(txt)
    return "\n\n".join(texts)
