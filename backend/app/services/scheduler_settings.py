from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.core.config import Settings
from app.models import ScheduleItem, ScheduleRule, SchedulerResponse, SchedulerSaveResponse, SchedulerUpdateRequest
from app.services.oauth_connections import read_store, write_store

DEFAULT_CHANNEL_WINDOWS: dict[str, str] = {
    "Facebook": "18:30-20:30",
    "LinkedIn": "07:30-09:00",
    "TikTok": "19:00-21:00",
    "YouTube": "19:30-21:30",
    "WordPress": "09:00-11:00",
}

DEFAULT_CHANNEL_AUDIENCE: dict[str, str] = {
    "Facebook": "Lead ấm",
    "LinkedIn": "Người ra quyết định",
    "TikTok": "Nhóm tiếp cận mới",
    "YouTube": "Người xem quay lại",
    "WordPress": "Tìm kiếm tự nhiên",
}


def _normalize_schedule_rule_payload(item: object) -> ScheduleRule | None:
    if not isinstance(item, dict):
        return None

    rule_id = str(item.get("id") or uuid4().hex).strip()
    title = str(item.get("title") or "").strip()
    channel = str(item.get("channel") or "").strip()
    publish_mode = str(item.get("publishMode") or "manual").strip().lower()
    start_at = str(item.get("startAt") or "").strip()
    repeat_type = str(item.get("repeatType") or "none").strip().lower()
    note = str(item.get("note") or "").strip() or None

    if not title or not channel or not start_at:
        return None
    if publish_mode not in {"manual", "auto"}:
        publish_mode = "manual"
    if repeat_type not in {"none", "daily", "weekly", "monthly"}:
        repeat_type = "none"

    try:
        repeat_interval = max(1, int(item.get("repeatInterval") or 1))
    except (TypeError, ValueError):
        repeat_interval = 1

    raw_days = item.get("daysOfWeek") or []
    days_of_week: list[int] = []
    if isinstance(raw_days, list):
        for value in raw_days:
            try:
                day = int(value)
            except (TypeError, ValueError):
                continue
            if 0 <= day <= 6 and day not in days_of_week:
                days_of_week.append(day)
    days_of_week.sort()

    active = bool(item.get("active", True))

    return ScheduleRule(
        id=rule_id,
        title=title,
        channel=channel,
        publishMode=publish_mode,  # type: ignore[arg-type]
        startAt=start_at,
        repeatType=repeat_type,  # type: ignore[arg-type]
        repeatInterval=repeat_interval,
        daysOfWeek=days_of_week,
        active=active,
        note=note,
    )


def _format_rule_slot(rule: ScheduleRule) -> str:
    try:
        parsed = datetime.fromisoformat(rule.startAt)
        base_slot = parsed.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        base_slot = rule.startAt

    if rule.repeatType == "daily":
        return f"{base_slot} • Lặp mỗi {rule.repeatInterval} ngày"
    if rule.repeatType == "weekly":
        if rule.daysOfWeek:
            weekday_map = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"]
            labels = ", ".join(weekday_map[day] for day in rule.daysOfWeek)
            return f"{base_slot} • Lặp tuần ({labels})"
        return f"{base_slot} • Lặp mỗi {rule.repeatInterval} tuần"
    if rule.repeatType == "monthly":
        return f"{base_slot} • Lặp mỗi {rule.repeatInterval} tháng"
    return base_slot


def _build_schedule_queue(rules: list[ScheduleRule]) -> list[ScheduleItem]:
    queue: list[ScheduleItem] = []
    for rule in sorted(rules, key=lambda item: item.startAt):
        if not rule.active:
            continue
        queue.append(
            ScheduleItem(
                asset=rule.title,
                channel=rule.channel,
                slot=_format_rule_slot(rule),
                bestWindow=DEFAULT_CHANNEL_WINDOWS.get(rule.channel, "09:00-11:00"),
                audience=DEFAULT_CHANNEL_AUDIENCE.get(rule.channel, "Tệp mục tiêu mặc định"),
            )
        )
    return queue


def _default_scheduler_response() -> SchedulerResponse:
    default_rules = [
        ScheduleRule(
            id=uuid4().hex,
            title="Đẩy bài viết website mới",
            channel="WordPress",
            publishMode="auto",
            startAt=datetime.now(UTC).astimezone().replace(second=0, microsecond=0).isoformat(timespec="minutes"),
            repeatType="weekly",
            repeatInterval=1,
            daysOfWeek=[1, 3, 5],
            active=True,
            note="Xuất bản nội dung website định kỳ.",
        )
    ]
    return SchedulerResponse(
        mode="manual",
        timezone="Asia/Saigon",
        schedules=default_rules,
        queue=_build_schedule_queue(default_rules),
    )


def get_scheduler_settings(base_settings: Settings) -> SchedulerResponse:
    store = read_store(base_settings)
    raw_payload = store.get("schedulerSettings")
    if not isinstance(raw_payload, dict):
        return _default_scheduler_response()

    mode = str(raw_payload.get("mode") or "manual").strip().lower()
    if mode not in {"manual", "auto"}:
        mode = "manual"
    timezone = str(raw_payload.get("timezone") or "Asia/Saigon").strip() or "Asia/Saigon"
    raw_schedules = raw_payload.get("schedules") or []
    schedules: list[ScheduleRule] = []
    if isinstance(raw_schedules, list):
        for item in raw_schedules:
            normalized = _normalize_schedule_rule_payload(item)
            if normalized:
                schedules.append(normalized)
    if not schedules:
        defaults = _default_scheduler_response()
        schedules = defaults.schedules

    return SchedulerResponse(
        mode=mode,  # type: ignore[arg-type]
        timezone=timezone,
        schedules=schedules,
        queue=_build_schedule_queue(schedules),
    )


def save_scheduler_settings(base_settings: Settings, payload: SchedulerUpdateRequest) -> SchedulerSaveResponse:
    normalized_rules: list[ScheduleRule] = []
    for rule in payload.schedules:
        normalized_rules.append(
            ScheduleRule(
                id=rule.id or uuid4().hex,
                title=rule.title.strip(),
                channel=rule.channel.strip(),
                publishMode=rule.publishMode,
                startAt=rule.startAt.strip(),
                repeatType=rule.repeatType,
                repeatInterval=max(1, rule.repeatInterval),
                daysOfWeek=sorted({day for day in rule.daysOfWeek if 0 <= day <= 6}),
                active=rule.active,
                note=(rule.note or "").strip() or None,
            )
        )

    store = read_store(base_settings)
    store["schedulerSettings"] = {
        "mode": payload.mode,
        "timezone": payload.timezone.strip(),
        "schedules": [rule.model_dump() for rule in normalized_rules],
    }
    write_store(base_settings, store)

    scheduler = SchedulerResponse(
        mode=payload.mode,
        timezone=payload.timezone.strip(),
        schedules=normalized_rules,
        queue=_build_schedule_queue(normalized_rules),
    )
    return SchedulerSaveResponse(
        status="success",
        message="Đã lưu cấu hình lên lịch đăng bài.",
        scheduler=scheduler,
    )
