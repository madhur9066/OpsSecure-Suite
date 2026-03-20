"""modules/converter.py — JSON ↔ YAML ↔ Excel conversions."""
import json
from io import BytesIO

import yaml
import pandas as pd

MAX_INPUT_CHARS = 500_000   # 500 KB text guard


def _check_size(text: str):
    if len(text) > MAX_INPUT_CHARS:
        raise ValueError(f"Input too large ({len(text):,} chars). Max is {MAX_INPUT_CHARS:,}.")


def _yaml_dump(data) -> str:
    """Dump data as clean 2-space indented YAML (standard format)."""
    class _Dumper(yaml.Dumper):
        def increase_indent(self, flow=False, indentless=False):
            return super().increase_indent(flow=flow, indentless=False)

    return yaml.dump(
        data,
        Dumper=_Dumper,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        indent=2,
    )


# ── Text conversions ──────────────────────────────────────────────────

def json_to_yaml(json_text: str) -> str:
    _check_size(json_text)
    return _yaml_dump(json.loads(json_text))


def yaml_to_json(yaml_text: str) -> str:
    _check_size(yaml_text)
    return json.dumps(yaml.safe_load(yaml_text), indent=4, ensure_ascii=False)


# ── Excel conversions ─────────────────────────────────────────────────

def excel_to_json(file) -> str:
    xls      = pd.ExcelFile(file)
    all_data = {}
    for sheet in xls.sheet_names:
        df = xls.parse(sheet)
        all_data[sheet] = json.loads(df.to_json(orient="records"))
    return json.dumps(all_data, indent=4, ensure_ascii=False)


def excel_to_yaml(file) -> str:
    """Excel → JSON (intermediate) → YAML."""
    return _yaml_dump(json.loads(excel_to_json(file)))


def json_to_excel(json_text: str) -> BytesIO:
    _check_size(json_text)
    data   = json.loads(json_text)
    output = BytesIO()

    if isinstance(data, list):
        data = {"Sheet1": data}

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, records in data.items():
            df = pd.DataFrame(records)
            df.to_excel(writer, sheet_name=str(sheet_name)[:31], index=False)

    output.seek(0)
    return output


def yaml_to_excel(yaml_text: str) -> BytesIO:
    """YAML → JSON (intermediate) → Excel."""
    _check_size(yaml_text)
    return json_to_excel(json.dumps(yaml.safe_load(yaml_text), ensure_ascii=False))