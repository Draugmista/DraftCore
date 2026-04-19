from __future__ import annotations


class MarkdownExporter:
    def render(self, content_model: dict[str, object], *, title_override: str | None = None) -> str:
        title = self._resolve_title(content_model, title_override=title_override)
        sections = content_model.get("sections", []) if isinstance(content_model, dict) else []

        lines: list[str] = [f"# {title}"]
        for section in sections if isinstance(sections, list) else []:
            if not isinstance(section, dict):
                continue
            heading = str(section.get("heading", "")).strip()
            if heading:
                lines.extend(["", f"## {heading}"])

            blocks = section.get("blocks", [])
            for block in blocks if isinstance(blocks, list) else []:
                if not isinstance(block, dict):
                    continue
                text = str(block.get("text", "")).strip()
                if text:
                    lines.extend(["", text])

        return "\n".join(lines).strip() + "\n"

    def _resolve_title(self, content_model: dict[str, object], *, title_override: str | None) -> str:
        if title_override and title_override.strip():
            return title_override.strip()
        if isinstance(content_model, dict):
            title = content_model.get("title")
            if isinstance(title, str) and title.strip():
                return title.strip()
        return "Untitled Draft"
