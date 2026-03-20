"""blueprints/tools.py — JSON / YAML / Excel converter"""
from flask import (
    Blueprint, render_template, request, send_file, current_app
)
from flask_login import login_required
from modules.converter import json_to_yaml, yaml_to_json, excel_to_json, json_to_excel, excel_to_yaml, yaml_to_excel

tools_bp = Blueprint("tools", __name__)

ALLOWED_EXCEL_EXTENSIONS = {".xlsx", ".xls"}
ALLOWED_TEXT_EXTENSIONS  = {".json", ".yaml", ".yml"}


def _ext(filename: str) -> str:
    import os
    return os.path.splitext(filename)[1].lower()


@tools_bp.route("/json", methods=["GET", "POST"])
#@login_required
def json_converter():
    output            = None
    input_text        = ""
    input_format      = None
    output_format     = None
    input_mode        = "paste"
    uploaded_filename = None

    if request.method == "POST":
        input_format  = request.form.get("input_format")
        output_format = request.form.get("output_format")
        input_text    = request.form.get("input_text", "")
        input_mode    = request.form.get("input_mode", "paste")
        file          = request.files.get("file")

        # ── Determine actual source ──────────────────────────────────
        using_file = (
            input_mode == "upload"
            and file
            and file.filename
        )

        if using_file:
            uploaded_filename = file.filename
            ext = _ext(file.filename)

            # Auto-detect format from extension
            if ext in ALLOWED_EXCEL_EXTENSIONS:
                input_format = "excel"
            elif ext in ALLOWED_TEXT_EXTENSIONS:
                # Read text content so it also populates input_text
                file_content = file.read().decode("utf-8", errors="replace")
                input_text   = file_content
                if ext == ".json":
                    input_format = "json"
                else:
                    input_format = "yaml"
                file = None   # already read into input_text
            else:
                output = f"❌ Unsupported file type: {ext}"
                using_file = False

        # ── Validate formats ─────────────────────────────────────────
        if not output:
            if not input_format or not output_format:
                output = "⚠️ Please select both input and output formats."
            elif input_format == output_format:
                output = "⚠️ Input and output formats are the same."
            else:
                try:
                    if input_format == "json" and output_format == "yaml":
                        output = json_to_yaml(input_text)

                    elif input_format == "yaml" and output_format == "json":
                        output = yaml_to_json(input_text)

                    elif input_format == "yaml" and output_format == "excel":
                        file_data = yaml_to_excel(input_text)
                        return send_file(
                            file_data,
                            as_attachment=True,
                            download_name="output.xlsx",
                            mimetype=(
                                "application/vnd.openxmlformats-"
                                "officedocument.spreadsheetml.sheet"
                            ),
                        )

                    elif input_format == "excel" and output_format == "json":
                        src = file if using_file and file else None
                        if not src:
                            output = "⚠️ Please upload an Excel file."
                        else:
                            output = excel_to_json(src)

                    elif input_format == "excel" and output_format == "yaml":
                        src = file if using_file and file else None
                        if not src:
                            output = "⚠️ Please upload an Excel file."
                        else:
                            output = excel_to_yaml(src)

                    elif input_format == "json" and output_format == "excel":
                        file_data = json_to_excel(input_text)
                        return send_file(
                            file_data,
                            as_attachment=True,
                            download_name="output.xlsx",
                            mimetype=(
                                "application/vnd.openxmlformats-"
                                "officedocument.spreadsheetml.sheet"
                            ),
                        )

                    else:
                        output = "❌ Unsupported conversion combination."

                except Exception as exc:
                    current_app.logger.warning("converter error: %s", exc)
                    output = f"Error: {exc}"

    return render_template(
        "json_converter.html",
        input_format=input_format,
        output_format=output_format,
        input_text=input_text,
        output=output,
        input_mode=input_mode,
        uploaded_filename=uploaded_filename,
        current_path=request.path,
        page_title="JSON Converter",
    )