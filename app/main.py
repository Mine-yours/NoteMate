from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List

from app import app
from app.db import (
    delete_pdf_record,
    get_all_pdfs,
    get_glossary_cache,
    get_note_for_lecture,
    get_pdf_by_id,
    insert_pdf,
    upsert_glossary_cache,
    upsert_note_for_lecture,
    update_pdf_filename,
)
from flask import (
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover - ランタイム環境によっては未導入
    genai = None

try:
    from PyPDF2 import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None

ALLOWED_EXTENSIONS = {".pdf"}
UPLOAD_DIR = os.path.join(app.root_path, "static", "uploads", "pdfs")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "models/gemini-2.0-flash")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

if genai and GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)


def _allowed_file(filename: str) -> bool:
    _, ext = os.path.splitext(filename)
    return ext.lower() in ALLOWED_EXTENSIONS


def _extract_pdf_text(file_path: str, page: int | None = None) -> str:
    if not PdfReader:
        raise RuntimeError("PyPDF2 がインストールされていません。")

    reader = PdfReader(file_path)
    if page is not None:
        if page < 0 or page >= len(reader.pages):
            raise ValueError("ページ番号が不正です。")
        return reader.pages[page].extract_text() or ""

    texts: List[str] = []
    for pdf_page in reader.pages:
        texts.append(pdf_page.extract_text() or "")
    return "\n".join(texts)


def _get_pdf_page_count(file_path: str) -> int:
    if not PdfReader:
        raise RuntimeError("PyPDF2 がインストールされていません。")

    reader = PdfReader(file_path)
    return len(reader.pages)


def _generate_glossary(content: str) -> List[Dict[str, Any]]:
    if not genai or not GOOGLE_API_KEY:
        raise RuntimeError("Gemini API が利用できません。GOOGLE_API_KEY を設定してください。")

    # Gemini のトークン制限に配慮してテキスト長をサンプリング
    truncated = content[:12000]
    prompt = (
        "あなたは大学講義のチューターです。以下の資料本文を読み、重要な専門用語を抽出し、"
        "それぞれについて学生にも分かりやすい解説を作成してください。"
        "応答は必ず JSON 配列のみとし、各要素は {\"term\": \"用語\", \"definition\": \"説明\", \"context\": \"資料での文脈\"} の形式で出力してください。"
        "資料本文:\n"
        "```\n"
        f"{truncated}\n"
        "```"
    )

    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content(prompt)
    text = response.text or ""
    candidate = text.strip()

    fence_match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fence_match:
        candidate = fence_match.group(1).strip()

    if not candidate:
        candidate = text.strip()

    try:
        data = json.loads(candidate)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        # 先頭/末尾の余計な文字を取り除いて再試行
        bracket_match = re.search(r"\[[\s\S]*\]", candidate)
        if bracket_match:
            try:
                data = json.loads(bracket_match.group(0))
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                pass

    # Markdown から抽出できなかった場合は生テキストを返す


    # JSON に変換できなかった場合でもテキストを返す
    return [
        {
            "term": "解析失敗",
            "definition": "Gemini API の応答をJSONとして解釈できませんでした。",
            "context": text.strip()[:500],
        }
    ]


@app.route("/")
def index():
    pdfs = get_all_pdfs()
    return render_template("index.html", pdfs=pdfs)


@app.route("/upload", methods=["POST"])
def upload():
    file_storage = request.files.get("pdf")

    if not file_storage or file_storage.filename == "":
        flash("PDFファイルを選択してください。", "error")
        return redirect(url_for("index"))

    original_filename = secure_filename(file_storage.filename)

    if not _allowed_file(original_filename):
        flash("アップロードできるのはPDFファイルのみです。", "error")
        return redirect(url_for("index"))

    lecture_id = uuid.uuid4().hex
    stored_filename = f"{lecture_id}.pdf"

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    save_path = os.path.join(UPLOAD_DIR, stored_filename)
    file_storage.save(save_path)

    insert_pdf(
        lecture_id=lecture_id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        uploaded_at=datetime.now(),
    )

    flash("講義資料をアップロードしました。", "success")
    return redirect(url_for("view_pdf", lecture_id=lecture_id))


@app.route("/lectures/<lecture_id>")
def view_pdf(lecture_id: str):
    pdf = get_pdf_by_id(lecture_id)
    if not pdf:
        flash("指定された資料が見つかりませんでした。", "error")
        return redirect(url_for("index"))

    pdf_url = url_for("static", filename=f"uploads/pdfs/{pdf['stored_filename']}")
    file_path = os.path.join(UPLOAD_DIR, pdf["stored_filename"])
    page_count = 0
    try:
        if os.path.exists(file_path):
            page_count = _get_pdf_page_count(file_path)
    except RuntimeError:
        page_count = 0

    return render_template("view_pdf.html", pdf=pdf, pdf_url=pdf_url, page_count=page_count)


@app.route("/lectures/<lecture_id>/download")
def download_pdf(lecture_id: str):
    pdf = get_pdf_by_id(lecture_id)
    if not pdf:
        flash("指定された資料が見つかりませんでした。", "error")
        return redirect(url_for("index"))
    return send_from_directory(
        UPLOAD_DIR,
        pdf["stored_filename"],
        as_attachment=True,
        download_name=pdf["original_filename"],
    )


@app.route("/lectures/<lecture_id>/delete", methods=["POST"])
def delete_pdf(lecture_id: str):
    pdf = get_pdf_by_id(lecture_id)
    if not pdf:
        flash("指定された資料が見つかりませんでした。", "error")
        return redirect(url_for("index"))

    file_path = os.path.join(UPLOAD_DIR, pdf["stored_filename"])
    file_error: str | None = None

    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except OSError as err:
        file_error = str(err)

    delete_pdf_record(lecture_id)

    if file_error:
        flash(f"資料を削除しましたが、ファイルの削除でエラーが発生しました: {file_error}", "error")
    else:
        flash("講義資料を削除しました。", "success")

    return redirect(url_for("index"))


@app.route("/lectures/<lecture_id>/rename", methods=["POST"])
def rename_pdf(lecture_id: str):
    pdf = get_pdf_by_id(lecture_id)
    if not pdf:
        return jsonify({"error": "資料が見つかりませんでした。"}), 404

    payload = request.get_json(silent=True) or {}
    new_name = (payload.get("original_filename") or "").strip()

    if not new_name:
        return jsonify({"error": "新しいファイル名を入力してください。"}), 400

    if len(new_name) > 255:
        return jsonify({"error": "ファイル名は255文字以内で入力してください。"}), 400

    _, ext = os.path.splitext(new_name)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        return jsonify({"error": f"ファイル名は次の拡張子で終わる必要があります: {allowed}"}), 400

    update_pdf_filename(lecture_id, new_name)
    return jsonify({"lecture_id": lecture_id, "original_filename": new_name})


@app.route("/lectures/<lecture_id>/glossary")
def glossary(lecture_id: str):
    pdf = get_pdf_by_id(lecture_id)
    if not pdf:
        return jsonify({"error": "資料が見つかりませんでした。"}), 404

    file_path = os.path.join(UPLOAD_DIR, pdf["stored_filename"])
    if not os.path.exists(file_path):
        return jsonify({"error": "PDFファイルが見つかりませんでした。"}), 404

    page_param = request.args.get("page")
    page_index: int | None = None
    page_key = "all"
    if page_param and page_param.lower() != "all":
        try:
            page_index = int(page_param) - 1
            page_key = str(page_index + 1)
        except ValueError:
            return jsonify({"error": "ページ指定が不正です。"}), 400

    refresh = request.args.get("refresh")
    if not refresh:
        cached = get_glossary_cache(lecture_id, page_key)
        if cached:
            return jsonify({"items": cached["items"], "cached": True, "updated_at": cached["updated_at"]})

    try:
        content = _extract_pdf_text(file_path, page=page_index)
        if not content.strip():
            return jsonify({"error": "PDFからテキストを抽出できませんでした。"}), 500
        glossary_items = _generate_glossary(content)
        upsert_glossary_cache(lecture_id, page_key, glossary_items, datetime.now())
        return jsonify({"items": glossary_items, "cached": False})
    except RuntimeError as err:
        return jsonify({"error": str(err)}), 500
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
    except Exception as err:  # pragma: no cover - 想定外エラー
        return jsonify({"error": f"AI解析中にエラーが発生しました: {err}"}), 500


@app.route("/lectures/<lecture_id>/note", methods=["GET", "POST"])
def note_api(lecture_id: str):
    pdf = get_pdf_by_id(lecture_id)
    if not pdf:
        return jsonify({"error": "資料が見つかりませんでした。"}), 404

    if request.method == "GET":
        stored = get_note_for_lecture(lecture_id)
        if not stored:
            return jsonify({"content": "", "updated_at": None})
        return jsonify(stored)

    payload = request.get_json(silent=True) or {}
    content = payload.get("content")
    if content is None:
        return jsonify({"error": "content が指定されていません。"}), 400

    upsert_note_for_lecture(lecture_id, str(content), datetime.now())
    return jsonify({"status": "ok"})
