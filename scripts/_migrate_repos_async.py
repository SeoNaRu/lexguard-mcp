"""일회성: repositories 의 sync_get -> await aget 및 해당 메서드 async def 부여."""
import re
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPOS = ROOT / "src" / "repositories"


def process(text: str) -> str:
    if "sync_get(" not in text:
        return text
    text = text.replace(
        "from ..utils.http_client import sync_get",
        "from ..utils.http_client import aget",
    )
    text = text.replace("sync_get(", "await aget(")
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if re.match(r"^    def [a-zA-Z0-9_]+\(", line):
            start_i = i
            i += 1
            while i < n:
                nxt = lines[i]
                if nxt.startswith("    def ") and not nxt.startswith("        "):
                    break
                i += 1
            block = lines[start_i:i]
            if any("await aget(" in L for L in block) and "async def" not in block[0]:
                block[0] = block[0].replace("    def ", "    async def ", 1)
            out.extend(block)
            continue
        out.append(line)
        i += 1
    return "\n".join(out)


def main() -> None:
    for path in sorted(REPOS.glob("*.py")):
        raw = path.read_text(encoding="utf-8")
        if "sync_get(" not in raw:
            continue
        new = process(raw)
        path.write_text(new, encoding="utf-8")
        print("updated", path.relative_to(ROOT))


if __name__ == "__main__":
    main()
