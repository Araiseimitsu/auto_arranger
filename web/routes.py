from fastapi import APIRouter, Request, UploadFile, File, HTTPException, Form, Query
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import date
import json
import shutil
import yaml

from src.calendar_view import build_calendar_print_data
from .services import (
    load_settings,
    save_settings,
    load_ng_dates,
    save_ng_dates,
    get_history_summary,
    run_schedule_generation,
    get_selected_variant_result,
    append_generated_schedule_to_history,
    add_global_ng_date,
    remove_global_ng_date,
    add_member_ng_date,
    remove_member_ng_date,
    add_period_ng,
    remove_period_ng,
    get_all_members,
    normalize_schedule_from_client_json,
    bulk_preview_ng_dates,
    bulk_apply_ng_dates,
    get_resource_path,
    CSV_PATH,
    save_history_csv_page,
)

router = APIRouter()
templates = Jinja2Templates(directory=str(get_resource_path("web/templates")))


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    settings = load_settings()
    ng_dates = load_ng_dates()
    history_data = get_history_summary(page=1, page_size=50)
    current_year = date.today().year
    all_members = get_all_members()

    # Convert ng_dates dict to yaml string for editor (fallback)
    ng_dates_yaml = yaml.dump(ng_dates, allow_unicode=True, default_flow_style=False)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "settings": settings,
            "ng_dates": ng_dates,
            "ng_dates_yaml": ng_dates_yaml,
            "history": history_data["data"],
            "pagination": history_data,
            "current_year": current_year,
            "today": date.today().isoformat(),
            "all_members": all_members,
            "active_tab": "ng-global",
        },
    )


@router.get("/history", response_class=HTMLResponse)
async def get_history_table(request: Request, page: int = 1):
    history_data = get_history_summary(page=page, page_size=50)
    return templates.TemplateResponse(
        "components/history_table.html",
        {
            "request": request,
            "history": history_data["data"],
            "pagination": history_data,
        },
    )


@router.post("/history/save", response_class=JSONResponse)
async def save_history_page(request: Request):
    """履歴CSVの現在ページ分を上書き保存する。"""
    try:
        data = await request.json()
    except Exception:
        return JSONResponse(
            {"success": False, "message": "JSON の形式が不正です"},
            status_code=400,
        )

    try:
        page = int(data.get("page", 1))
        page_size = int(data.get("page_size", 50))
    except (TypeError, ValueError):
        return JSONResponse(
            {"success": False, "message": "ページ指定が不正です"},
            status_code=400,
        )

    rows = data.get("rows")
    if not isinstance(rows, list):
        return JSONResponse(
            {"success": False, "message": "rows が配列ではありません"},
            status_code=400,
        )

    ok, msg = save_history_csv_page(page, page_size, rows)
    if ok:
        return JSONResponse({"success": True, "message": msg})
    return JSONResponse({"success": False, "message": msg}, status_code=400)


@router.post("/settings/update", response_class=HTMLResponse)
async def update_settings(request: Request):
    form_data = await request.form()

    # Reconstruct settings object from flat lists
    # First, build a map of existing member configs to preserve attributes (e.g., fixed_pattern)
    current_settings_loaded = load_settings()
    existing_member_configs = {}

    if "members" in current_settings_loaded:
        m = current_settings_loaded["members"]

        # Helper to extract configs
        def extract_configs(group_list):
            if not group_list:
                return
            for member in group_list:
                existing_member_configs[member["name"]] = member

        if "day_shift" in m:
            extract_configs(m["day_shift"].get("index_1_2_group", []))
            extract_configs(m["day_shift"].get("index_3_group", []))
        if "night_shift" in m:
            extract_configs(m["night_shift"].get("index_1_group", []))
            extract_configs(m["night_shift"].get("index_2_group", []))

    new_settings = {"members": {"day_shift": {}, "night_shift": {}}}

    def process_group(form_list_key, active_suffix):
        members = form_data.getlist(form_list_key)
        group_list = []
        for name in members:
            # Check active status
            # key format: active_{name}_{suffix}
            active_key = f"active_{name}_{active_suffix}"
            is_active = form_data.get(active_key) == "on"

            # Start with existing config or new dict
            member_conf = existing_member_configs.get(name, {}).copy()

            # Update core fields
            member_conf["name"] = name
            member_conf["active"] = is_active

            group_list.append(member_conf)
        return group_list

    # Day Shift
    new_settings["members"]["day_shift"]["index_1_2_group"] = process_group(
        "day_index_1_2[]", "day"
    )
    new_settings["members"]["day_shift"]["index_3_group"] = process_group(
        "day_index_3[]", "day"
    )

    # Night Shift
    new_settings["members"]["night_shift"]["index_1_group"] = process_group(
        "night_index_1[]", "night"
    )
    new_settings["members"]["night_shift"]["index_2_group"] = process_group(
        "night_index_2[]", "night"
    )

    # Load current settings to preserve other values
    current_settings = load_settings()

    # Update Members
    current_settings["members"] = new_settings["members"]

    # Update Basic Settings
    # Constraints - Rotation Period (REMOVED from UI, keeping defaults or existing)
    # We no longer update start_day/duration from form_data as they are removed from UI.

    # Constraints - Intervals (New)
    if "constraints" not in current_settings:
        current_settings["constraints"] = {}
    if "interval" not in current_settings["constraints"]:
        current_settings["constraints"]["interval"] = {}
    if "night_to_day_gap" not in current_settings["constraints"]:
        current_settings["constraints"]["night_to_day_gap"] = {}

    try:
        # Day Interval
        min_days_day = form_data.get("min_days_day")
        if min_days_day is not None:
            current_settings["constraints"]["interval"][
                "min_days_between_same_person_day"
            ] = int(min_days_day)

        # Night Interval
        min_days_night = form_data.get("min_days_night")
        if min_days_night is not None:
            current_settings["constraints"]["interval"][
                "min_days_between_same_person_night"
            ] = int(min_days_night)

        # Day Index 3 Interval (with compensatory leave)
        min_days_day_index3 = form_data.get("min_days_day_index3")
        if min_days_day_index3 is not None:
            current_settings["constraints"]["interval"][
                "min_days_between_same_person_day_index3"
            ] = int(min_days_day_index3)

        # Night to Day Gap
        min_gap = form_data.get("min_gap_night_day")
        if min_gap is not None:
            current_settings["constraints"]["night_to_day_gap"]["min_days"] = int(
                min_gap
            )

    except ValueError:
        pass  # Ignore invalid ints

    # Matsuda Schedule
    if "matsuda_schedule" not in current_settings:
        current_settings["matsuda_schedule"] = {}

    current_settings["matsuda_schedule"]["enabled"] = (
        form_data.get("matsuda_enabled") == "on"
    )

    ref_date = form_data.get("matsuda_reference_date")
    if ref_date:
        current_settings["matsuda_schedule"]["reference_date"] = ref_date

    try:
        save_settings(current_settings)
        return templates.TemplateResponse(
            "components/settings_form.html",
            {
                "request": request,
                "settings": current_settings,
                "success_message": "設定を保存しました",
            },
        )
    except Exception as e:
        return HTMLResponse(f"<div class='error'>Error: {e}</div>", status_code=500)


# --- NG Dates Operations ---


async def render_ng_dates_form(
    request, message=None, error=None, active_tab="ng-global"
):
    ng_dates = load_ng_dates()
    ng_dates_yaml = yaml.dump(ng_dates, allow_unicode=True, default_flow_style=False)
    all_members = get_all_members()

    context = {
        "request": request,
        "ng_dates": ng_dates,
        "ng_dates_yaml": ng_dates_yaml,
        "all_members": all_members,
        "current_year": date.today().year,
        "active_tab": active_tab,
    }
    if message:
        context["success_message"] = message
    if error:
        context["error_message"] = error

    return templates.TemplateResponse("components/ng_dates_form.html", context)


@router.post("/ng_dates/update", response_class=HTMLResponse)
async def update_ng_dates_yaml(request: Request):
    """Fallback: Update via YAML textarea"""
    form_data = await request.form()
    yaml_content = form_data.get("ng_dates_yaml")
    active_tab = form_data.get("active_tab") or "ng-advanced"

    try:
        data = yaml.safe_load(yaml_content)
        save_ng_dates(data)
        return await render_ng_dates_form(
            request, message="NG日程(YAML)を保存しました", active_tab=active_tab
        )
    except Exception as e:
        return await render_ng_dates_form(
            request, error=f"YAML Error: {e}", active_tab=active_tab
        )


@router.post("/ng_dates/global/add", response_class=HTMLResponse)
async def add_global_ng(request: Request):
    form = await request.form()
    date_str = form.get("date")
    active_tab = form.get("active_tab") or "ng-global"
    if date_str:
        add_global_ng_date(date_str)
    return await render_ng_dates_form(request, active_tab=active_tab)


@router.post("/ng_dates/global/remove", response_class=HTMLResponse)
async def remove_global_ng(request: Request):
    form = await request.form()
    date_str = form.get("date")
    active_tab = form.get("active_tab") or "ng-global"
    if date_str:
        remove_global_ng_date(date_str)
    return await render_ng_dates_form(request, active_tab=active_tab)


@router.post("/ng_dates/member/add", response_class=HTMLResponse)
async def add_member_ng(request: Request):
    form = await request.form()
    member = form.get("member")
    date_str = form.get("date")
    active_tab = form.get("active_tab") or "ng-member"
    if member and date_str:
        add_member_ng_date(member, date_str)
    return await render_ng_dates_form(request, active_tab=active_tab)


@router.post("/ng_dates/member/remove", response_class=HTMLResponse)
async def remove_member_ng(request: Request):
    form = await request.form()
    member = form.get("member")
    date_str = form.get("date")
    active_tab = form.get("active_tab") or "ng-member"
    if member and date_str:
        remove_member_ng_date(member, date_str)
    return await render_ng_dates_form(request, active_tab=active_tab)


@router.post("/ng_dates/period/add", response_class=HTMLResponse)
async def add_period_ng_route(request: Request):
    form = await request.form()
    member = form.get("member")
    start = form.get("start")
    end = form.get("end")
    reason = form.get("reason")
    active_tab = form.get("active_tab") or "ng-period"
    if member and start and end:
        add_period_ng(member, start, end, reason)
    return await render_ng_dates_form(request, active_tab=active_tab)


@router.post("/ng_dates/period/remove", response_class=HTMLResponse)
async def remove_period_ng_route(request: Request):
    form = await request.form()
    member = form.get("member")
    start = form.get("start")
    active_tab = form.get("active_tab") or "ng-period"
    if member and start:
        remove_period_ng(member, start)
    return await render_ng_dates_form(request, active_tab=active_tab)


# --- Bulk NG Import ---


@router.post("/ng_dates/bulk/preview", response_class=HTMLResponse)
async def bulk_preview_ng(request: Request):
    """フリーテキストをパースしてプレビューHTMLを返す"""
    form = await request.form()
    text = form.get("text", "")
    mode = form.get("mode", "daily")
    fiscal_year = form.get("fiscal_year")

    if not text.strip():
        return HTMLResponse(
            '<div class="result-alert alert-error">テキストを入力してください</div>'
        )

    try:
        fy = int(fiscal_year) if fiscal_year else None
    except ValueError:
        fy = None

    entries = bulk_preview_ng_dates(text, mode, fy)

    if not entries:
        return HTMLResponse(
            '<div class="result-alert alert-error">解析可能なデータが見つかりませんでした</div>'
        )

    return templates.TemplateResponse(
        "components/ng_bulk_preview.html",
        {
            "request": request,
            "entries": entries,
        },
    )


@router.post("/ng_dates/bulk/apply", response_class=HTMLResponse)
async def bulk_apply_ng(request: Request):
    """選択されたエントリを一括登録"""
    form = await request.form()
    entries_json = form.get("entries", "[]")
    active_tab = form.get("active_tab") or "ng-bulk"

    try:
        entries = json.loads(entries_json)
    except json.JSONDecodeError:
        return await render_ng_dates_form(
            request, error="データの解析に失敗しました", active_tab=active_tab
        )

    if not entries:
        return await render_ng_dates_form(
            request, error="登録対象が選択されていません", active_tab=active_tab
        )

    count = bulk_apply_ng_dates(entries)
    return await render_ng_dates_form(
        request, message=f"{count}件のNG日を登録しました", active_tab=active_tab
    )


# --- End NG Operations ---


@router.post("/generate", response_class=HTMLResponse)
async def generate_schedule(request: Request):
    form_data = await request.form()
    start_date_str = form_data.get("start_date")
    variants = form_data.get("variants")
    variant_top_k = form_data.get("variant_top_k")

    if not start_date_str:
        return HTMLResponse("<div class='error'>開始日を指定してください</div>")

    try:
        start_date = date.fromisoformat(start_date_str)
        if start_date.day != 21:
            return HTMLResponse(
                "<div class='error'>開始日は21日を指定してください</div>"
            )
    except ValueError:
        return HTMLResponse("<div class='error'>無効な日付形式です</div>")

    try:
        variants_int = int(variants) if variants is not None else 1
        variant_top_k_int = int(variant_top_k) if variant_top_k is not None else 3
    except ValueError:
        return HTMLResponse("<div class='error'>バリアント設定が無効です</div>")

    success, result, message = run_schedule_generation(
        start_date_str, variants=variants_int, variant_top_k=variant_top_k_int
    )

    if not success:
        return HTMLResponse(f"<div class='error'>{message}</div>")

    return templates.TemplateResponse(
        "components/schedule_result.html",
        {
            "request": request,
            "variants": result["variants"],
            "failures": result["failures"],
            "start_date": result["start_date"],
            "end_date": result["end_date"],
            "variant_count": result["variant_count"],
            "variant_top_k": result["variant_top_k"],
            "all_members": get_all_members(),
        },
    )


@router.post("/upload_csv", response_class=HTMLResponse)
async def upload_csv(request: Request, file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        return HTMLResponse(
            "<div class='error'>CSVファイルのみアップロード可能です</div>",
            status_code=400,
        )

    try:
        # Verify content
        content = await file.read()
        # Backup existing
        if CSV_PATH.exists():
            shutil.copy(CSV_PATH, CSV_PATH.with_suffix(".bak"))

        with open(CSV_PATH, "wb") as f:
            f.write(content)

        history_data = get_history_summary(page=1, page_size=50)
        return templates.TemplateResponse(
            "components/history_table.html",
            {
                "request": request,
                "history": history_data["data"],
                "pagination": history_data,
                "success_message": "データを更新しました",
            },
        )
    except Exception as e:
        return HTMLResponse(
            f"<div class='error'>Upload Error: {e}</div>", status_code=500
        )


def _render_print_calendar(
    request: Request,
    schedule: dict,
    start_date: date,
    end_date: date,
    variant_number: int,
):
    ng_dates = load_ng_dates()
    calendar_data = build_calendar_print_data(
        schedule,
        ng_dates,
        start_date,
        end_date,
    )
    return templates.TemplateResponse(
        "print_calendar.html",
        {
            "request": request,
            "calendar_data": calendar_data,
            "start_date": start_date,
            "end_date": end_date,
            "variant_number": variant_number,
            "print_created_at": date.today(),
        },
    )


@router.get("/print/calendar", response_class=HTMLResponse)
async def print_calendar(
    request: Request,
    start_date: str | None = Query(default=None),
    variant_index: int = 0,
    variants: int = 1,
    variant_top_k: int = 3,
):
    """クエリで開始日・バリアントを渡し、サーバー側で再生成して印刷ビューを返す。"""
    if not start_date or not str(start_date).strip():
        return HTMLResponse(
            "<div class='error' style='padding:24px;max-width:520px;margin:2rem auto'>"
            "<p><strong>開始日（start_date）が指定されていません。</strong></p>"
            "<p>作成タブでスケジュールを生成したあと、表示される"
            "<strong>「カレンダー表示」</strong>リンクから開いてください。"
            "（URL を直接開くとこのエラーになります。）</p>"
            "</div>",
            status_code=400,
        )

    try:
        start_date = date.fromisoformat(str(start_date).strip())
    except ValueError:
        return HTMLResponse(
            "<div class='error'>無効な開始日です</div>", status_code=400
        )

    success, payload, message = get_selected_variant_result(
        start_date.isoformat(),
        variant_index=variant_index,
        variants=variants,
        variant_top_k=variant_top_k,
    )
    if not success:
        return HTMLResponse(f"<div class='error'>{message}</div>", status_code=400)

    selected = payload["selected"]
    result = payload["result"]
    return _render_print_calendar(
        request,
        selected["schedule"],
        result["start_date"],
        result["end_date"],
        selected["variant_index"] + 1,
    )


@router.post("/print/calendar", response_class=HTMLResponse)
async def print_calendar_post(request: Request):
    """ブラウザで編集したスケジュールをそのまま印刷ビューに渡す。"""
    form = await request.form()
    start_date_str = form.get("start_date")
    end_date_str = form.get("end_date")
    schedule_json = form.get("schedule_json")
    variant_index_str = form.get("variant_index")

    if not start_date_str or not end_date_str:
        return HTMLResponse(
            "<div class='error'>開始日・終了日が必要です</div>", status_code=400
        )

    try:
        start_date = date.fromisoformat(str(start_date_str))
        end_date = date.fromisoformat(str(end_date_str))
    except ValueError:
        return HTMLResponse("<div class='error'>日付が無効です</div>", status_code=400)

    if not schedule_json or not str(schedule_json).strip():
        return HTMLResponse(
            "<div class='error'>スケジュールデータがありません</div>", status_code=400
        )

    try:
        schedule = normalize_schedule_from_client_json(str(schedule_json))
    except (ValueError, json.JSONDecodeError) as e:
        return HTMLResponse(
            f"<div class='error'>スケジュールの解析に失敗しました: {e}</div>",
            status_code=400,
        )

    try:
        variant_num = int(variant_index_str) + 1 if variant_index_str is not None else 1
    except (TypeError, ValueError):
        variant_num = 1

    return _render_print_calendar(request, schedule, start_date, end_date, variant_num)


@router.post("/save_result", response_class=HTMLResponse)
async def save_result(request: Request):
    form_data = await request.form()
    start_date = form_data.get("start_date")
    variant_index = form_data.get("variant_index")
    variants = form_data.get("variants")
    variant_top_k = form_data.get("variant_top_k")
    schedule_json_str = form_data.get("schedule_json")

    if not start_date:
        return HTMLResponse("Error: Missing start date")

    if schedule_json_str and str(schedule_json_str).strip():
        try:
            schedule = normalize_schedule_from_client_json(str(schedule_json_str))
            result = append_generated_schedule_to_history(schedule, CSV_PATH)
            return HTMLResponse(
                f"<div class='success'>履歴CSVに追加しました（編集反映）: {result['path']} "
                f"(追加 {result['added_count']}件 / 重複スキップ {result['skipped_count']}件)</div>"
            )
        except (ValueError, json.JSONDecodeError) as e:
            return HTMLResponse(f"<div class='error'>保存失敗: {e}</div>")

    try:
        variants_int = int(variants) if variants is not None else 1
        variant_top_k_int = int(variant_top_k) if variant_top_k is not None else 3
        variant_index_int = int(variant_index) if variant_index is not None else 0
    except ValueError:
        return HTMLResponse("<div class='error'>バリアント設定が無効です</div>")

    success, payload, message = get_selected_variant_result(
        start_date,
        variant_index=variant_index_int,
        variants=variants_int,
        variant_top_k=variant_top_k_int,
    )

    if success:
        result = append_generated_schedule_to_history(
            payload["selected"]["schedule"], CSV_PATH
        )
        return HTMLResponse(
            f"<div class='success'>履歴CSVに追加しました: {result['path']} "
            f"(追加 {result['added_count']}件 / 重複スキップ {result['skipped_count']}件)</div>"
        )
    else:
        return HTMLResponse(f"<div class='error'>保存失敗: {message}</div>")


# Member Attribute Operations
@router.post("/settings/member/update", response_class=JSONResponse)
async def update_member_attributes(request: Request):
    """Update specific attributes for a member without rebuilding lists"""
    try:
        data = await request.json()
        member_name = data.get("name")
        if not member_name:
            return JSONResponse(
                {"success": False, "error": "Member name required"}, status_code=400
            )

        settings = load_settings()

        # Helper to find and update member in all lists
        def update_in_group(group_list):
            if not group_list:
                return False
            updated = False
            for m in group_list:
                if m["name"] == member_name:
                    # Update fields
                    if "min_days_day" in data:
                        val = data["min_days_day"]
                        if val == "":
                            m.pop("min_days_day", None)
                        else:
                            m["min_days_day"] = int(val)

                    if "min_days_night" in data:
                        val = data["min_days_night"]
                        if val == "":
                            m.pop("min_days_night", None)
                        else:
                            m["min_days_night"] = int(val)
                    updated = True
            return updated

        found = False
        if "members" in settings:
            m = settings["members"]
            if "day_shift" in m:
                if update_in_group(m["day_shift"].get("index_1_2_group", [])):
                    found = True
                if update_in_group(m["day_shift"].get("index_3_group", [])):
                    found = True
            if "night_shift" in m:
                if update_in_group(m["night_shift"].get("index_1_group", [])):
                    found = True
                if update_in_group(m["night_shift"].get("index_2_group", [])):
                    found = True

        if found:
            save_settings(settings)
            return JSONResponse({"success": True})
        else:
            return JSONResponse(
                {"success": False, "error": "Member not found"}, status_code=404
            )

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
