from fastapi import APIRouter, Request, UploadFile, File, HTTPException, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import date
import shutil
import yaml

from .services import (
    load_settings, save_settings,
    load_ng_dates, save_ng_dates,
    get_history_summary,
    run_schedule_generation,
    save_generated_schedule,
    add_global_ng_date, remove_global_ng_date,
    add_member_ng_date, remove_member_ng_date,
    add_period_ng, remove_period_ng,
    get_all_members,
    get_resource_path,
    CSV_PATH
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
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "settings": settings,
        "ng_dates": ng_dates,
        "ng_dates_yaml": ng_dates_yaml,
        "history": history_data["data"],
        "pagination": history_data,
        "current_year": current_year,
        "today": date.today().isoformat(),
        "all_members": all_members
    })

@router.get("/history", response_class=HTMLResponse)
async def get_history_table(request: Request, page: int = 1):
    history_data = get_history_summary(page=page, page_size=50)
    return templates.TemplateResponse("components/history_table.html", {
        "request": request,
        "history": history_data["data"],
        "pagination": history_data
    })

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
            if not group_list: return
            for member in group_list:
                existing_member_configs[member['name']] = member
        
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
    new_settings["members"]["day_shift"]["index_1_2_group"] = process_group("day_index_1_2[]", "day")
    new_settings["members"]["day_shift"]["index_3_group"] = process_group("day_index_3[]", "day")

    # Night Shift
    new_settings["members"]["night_shift"]["index_1_group"] = process_group("night_index_1[]", "night")
    new_settings["members"]["night_shift"]["index_2_group"] = process_group("night_index_2[]", "night")
    
    # Load current settings to preserve other values
    current_settings = load_settings()
    
    # Update Members
    current_settings["members"] = new_settings["members"]
    
    # Update Basic Settings
    # Constraints - Rotation Period (REMOVED from UI, keeping defaults or existing)
    # We no longer update start_day/duration from form_data as they are removed from UI.

    # Constraints - Intervals (New)
    if "constraints" not in current_settings: current_settings["constraints"] = {}
    if "interval" not in current_settings["constraints"]: current_settings["constraints"]["interval"] = {}
    if "night_to_day_gap" not in current_settings["constraints"]: current_settings["constraints"]["night_to_day_gap"] = {}

    try:
        # Day Interval
        min_days_day = form_data.get("min_days_day")
        if min_days_day is not None:
             current_settings["constraints"]["interval"]["min_days_between_same_person_day"] = int(min_days_day)
        
        # Night Interval
        min_days_night = form_data.get("min_days_night")
        if min_days_night is not None:
             current_settings["constraints"]["interval"]["min_days_between_same_person_night"] = int(min_days_night)

        # Day Index 3 Interval (with compensatory leave)
        min_days_day_index3 = form_data.get("min_days_day_index3")
        if min_days_day_index3 is not None:
             current_settings["constraints"]["interval"]["min_days_between_same_person_day_index3"] = int(min_days_day_index3)

        # Night to Day Gap
        min_gap = form_data.get("min_gap_night_day")
        if min_gap is not None:
            current_settings["constraints"]["night_to_day_gap"]["min_days"] = int(min_gap)
            
    except ValueError:
        pass # Ignore invalid ints
        
    # Matsuda Schedule
    if "matsuda_schedule" not in current_settings: current_settings["matsuda_schedule"] = {}
    
    current_settings["matsuda_schedule"]["enabled"] = form_data.get("matsuda_enabled") == "on"
    
    ref_date = form_data.get("matsuda_reference_date")
    if ref_date:
        current_settings["matsuda_schedule"]["reference_date"] = ref_date
    
    try:
        save_settings(current_settings)
        return templates.TemplateResponse("components/settings_form.html", {
            "request": request,
            "settings": current_settings,
            "success_message": "設定を保存しました"
        })
    except Exception as e:
        return HTMLResponse(f"<div class='error'>Error: {e}</div>", status_code=500)

# --- NG Dates Operations ---

async def render_ng_dates_form(request, message=None, error=None):
    ng_dates = load_ng_dates()
    ng_dates_yaml = yaml.dump(ng_dates, allow_unicode=True, default_flow_style=False)
    all_members = get_all_members()
    
    context = {
        "request": request,
        "ng_dates": ng_dates,
        "ng_dates_yaml": ng_dates_yaml,
        "all_members": all_members
    }
    if message: context["success_message"] = message
    if error: context["error_message"] = error
    
    return templates.TemplateResponse("components/ng_dates_form.html", context)

@router.post("/ng_dates/update", response_class=HTMLResponse)
async def update_ng_dates_yaml(request: Request):
    """Fallback: Update via YAML textarea"""
    form_data = await request.form()
    yaml_content = form_data.get('ng_dates_yaml')
    
    try:
        data = yaml.safe_load(yaml_content)
        save_ng_dates(data)
        return await render_ng_dates_form(request, message="NG日程(YAML)を保存しました")
    except Exception as e:
        return await render_ng_dates_form(request, error=f"YAML Error: {e}")

@router.post("/ng_dates/global/add", response_class=HTMLResponse)
async def add_global_ng(request: Request):
    form = await request.form()
    date_str = form.get('date')
    if date_str:
        add_global_ng_date(date_str)
    return await render_ng_dates_form(request)

@router.post("/ng_dates/global/remove", response_class=HTMLResponse)
async def remove_global_ng(request: Request):
    form = await request.form()
    date_str = form.get('date')
    if date_str:
        remove_global_ng_date(date_str)
    return await render_ng_dates_form(request)

@router.post("/ng_dates/member/add", response_class=HTMLResponse)
async def add_member_ng(request: Request):
    form = await request.form()
    member = form.get('member')
    date_str = form.get('date')
    if member and date_str:
        add_member_ng_date(member, date_str)
    return await render_ng_dates_form(request)

@router.post("/ng_dates/member/remove", response_class=HTMLResponse)
async def remove_member_ng(request: Request):
    form = await request.form()
    member = form.get('member')
    date_str = form.get('date')
    if member and date_str:
        remove_member_ng_date(member, date_str)
    return await render_ng_dates_form(request)

@router.post("/ng_dates/period/add", response_class=HTMLResponse)
async def add_period_ng_route(request: Request):
    form = await request.form()
    member = form.get('member')
    start = form.get('start')
    end = form.get('end')
    reason = form.get('reason')
    if member and start and end:
        add_period_ng(member, start, end, reason)
    return await render_ng_dates_form(request)

@router.post("/ng_dates/period/remove", response_class=HTMLResponse)
async def remove_period_ng_route(request: Request):
    form = await request.form()
    member = form.get('member')
    start = form.get('start')
    if member and start:
        remove_period_ng(member, start)
    return await render_ng_dates_form(request)

# --- End NG Operations ---

@router.post("/generate", response_class=HTMLResponse)
async def generate_schedule(request: Request):
    form_data = await request.form()
    start_date_str = form_data.get('start_date')
    
    if not start_date_str:
        return HTMLResponse("<div class='error'>開始日を指定してください</div>")
        
    try:
        start_date = date.fromisoformat(start_date_str)
        if start_date.day != 21:
             return HTMLResponse("<div class='error'>開始日は21日を指定してください</div>")
    except ValueError:
        return HTMLResponse("<div class='error'>無効な日付形式です</div>")

    success, result, message = run_schedule_generation(start_date_str)
    
    if not success:
        return HTMLResponse(f"<div class='error'>{message}</div>")
    
    return templates.TemplateResponse("components/schedule_result.html", {
        "request": request,
        "schedule": result['schedule'],
        "statistics": result['statistics'],
        "analysis": result['analysis'],
        "start_date": result['start_date'],
        "end_date": result['end_date']
    })

@router.post("/upload_csv", response_class=HTMLResponse)
async def upload_csv(request: Request, file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        return HTMLResponse("<div class='error'>CSVファイルのみアップロード可能です</div>", status_code=400)
    
    try:
        # Verify content
        content = await file.read()
        # Backup existing
        if CSV_PATH.exists():
            shutil.copy(CSV_PATH, CSV_PATH.with_suffix('.bak'))
            
        with open(CSV_PATH, 'wb') as f:
            f.write(content)
            
        history_data = get_history_summary(page=1, page_size=50)
        return templates.TemplateResponse("components/history_table.html", {
            "request": request,
            "history": history_data["data"],
            "pagination": history_data,
            "success_message": "データを更新しました"
        })
    except Exception as e:
        return HTMLResponse(f"<div class='error'>Upload Error: {e}</div>", status_code=500)

@router.post("/save_result", response_class=HTMLResponse)
async def save_result(request: Request):
    form_data = await request.form()
    start_date = form_data.get('start_date')
    
    if not start_date:
        return HTMLResponse("Error: Missing start date")
        
    success, result, message = run_schedule_generation(start_date)
    
    if success:
        path = save_generated_schedule(result['schedule'])
        return HTMLResponse(f"<div class='success'>CSVを保存しました: {path}</div>")
    else:
        return HTMLResponse(f"<div class='error'>保存失敗: {message}</div>")

# Member Attribute Operations
@router.post("/settings/member/update", response_class=JSONResponse)
async def update_member_attributes(request: Request):
    """Update specific attributes for a member without rebuilding lists"""
    try:
        data = await request.json()
        member_name = data.get('name')
        if not member_name:
            return JSONResponse({"success": False, "error": "Member name required"}, status_code=400)
            
        settings = load_settings()
        
        # Helper to find and update member in all lists
        def update_in_group(group_list):
            if not group_list: return False
            updated = False
            for m in group_list:
                if m['name'] == member_name:
                    # Update fields
                    if 'min_days_day' in data:
                        val = data['min_days_day']
                        if val == "": 
                            m.pop('min_days_day', None)
                        else:
                            m['min_days_day'] = int(val)
                            
                    if 'min_days_night' in data:
                        val = data['min_days_night']
                        if val == "":
                            m.pop('min_days_night', None)
                        else:
                            m['min_days_night'] = int(val)
                    updated = True
            return updated

        found = False
        if "members" in settings:
            m = settings["members"]
            if "day_shift" in m:
                if update_in_group(m["day_shift"].get("index_1_2_group", [])): found = True
                if update_in_group(m["day_shift"].get("index_3_group", [])): found = True
            if "night_shift" in m:
                if update_in_group(m["night_shift"].get("index_1_group", [])): found = True
                if update_in_group(m["night_shift"].get("index_2_group", [])): found = True
        
        if found:
            save_settings(settings)
            return JSONResponse({"success": True})
        else:
            return JSONResponse({"success": False, "error": "Member not found"}, status_code=404)
            
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
