"""Dev utility: dump PDF text, link annotations and block layout for fixture analysis."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages"))
import fitz


def main(path: str, mode: str = "text") -> None:
    d = fitz.open(path)
    print(f"=== {Path(path).name} pages={d.page_count} ===")
    if mode in ("text", "all"):
        for i, page in enumerate(d, 1):
            print(f"\n----- PAGE {i} -----")
            print(page.get_text("text"))
    if mode in ("links", "all"):
        print("\n----- LINKS -----")
        seen = set()
        for i, page in enumerate(d, 1):
            for l in page.get_links():
                uri = l.get("uri")
                if uri and uri not in seen:
                    seen.add(uri)
                    print(f"p{i}: {uri}")
    if mode in ("blocks", "all"):
        print("\n----- BLOCKS (page, y, x, size, text) -----")
        for i, page in enumerate(d, 1):
            for b in page.get_text("dict").get("blocks", []):
                if b.get("type") != 0:
                    continue
                txt = " ".join(s["text"] for l in b.get("lines", []) for s in l.get("spans", []))
                sizes = {round(s["size"], 1) for l in b.get("lines", []) for s in l.get("spans", [])}
                if txt.strip():
                    print(f"p{i} y={round(b['bbox'][1])} x={round(b['bbox'][0])} sz={sorted(sizes)} | {txt[:160]}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "text")
