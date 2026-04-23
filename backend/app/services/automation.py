from __future__ import annotations

import asyncio
from datetime import UTC, datetime, time
from typing import Any

from googleapiclient.discovery import build

from app.core.config import get_settings
from app.models import AutomationJobStatus, AutomationStatusResponse, LocalAiAnalysisResponse, SettingsResponse
from app.services.daily_report import sync_daily_report
from app.services.google_website import ensure_sheet_exists, get_sheet_values, load_service_account_credentials
from app.services.google_website import sync_google_website_data
from app.services.local_ai_analysis import get_local_ai_analysis
from app.services.social_platforms import sync_social_platforms
from app.services.system_settings import apply_runtime_settings, build_settings_response

POLL_SECONDS = 30


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


class AutomationManager:
    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._stop_event: asyncio.Event | None = None
        self._running = False
        self._state: dict[str, Any] = {
            "lastConfigReloadAt": None,
            "effectiveSettings": None,
            "jobs": {
                "sync": self._new_job_state("Đồng bộ dữ liệu"),
                "recommend": self._new_job_state("Phân tích AI"),
                "schedule": self._new_job_state("Báo cáo tự động"),
            },
        }

    @staticmethod
    def _new_job_state(name: str) -> dict[str, Any]:
        return {
            "name": name,
            "enabled": False,
            "lastRunAt": None,
            "lastSuccessAt": None,
            "lastStatus": "idle",
            "lastMessage": "Chưa chạy.",
        }

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop_event = asyncio.Event()
        self._running = True
        self._task = asyncio.create_task(self._run_loop(), name="marketing-ai-automation")

    async def stop(self) -> None:
        self._running = False
        if self._stop_event:
            self._stop_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        self._stop_event = None

    async def _run_loop(self) -> None:
        while self._stop_event and not self._stop_event.is_set():
            try:
                await self.run_cycle()
            except Exception:
                pass

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=POLL_SECONDS)
            except asyncio.TimeoutError:
                continue

    def _is_due(self, last_run_at: str | None, interval_minutes: int) -> bool:
        if not last_run_at:
            return True
        try:
            last_run = datetime.fromisoformat(last_run_at)
        except ValueError:
            return True
        return (datetime.now(UTC) - last_run).total_seconds() >= max(interval_minutes, 1) * 60

    def _parse_last_run_local(self, last_run_at: str | None) -> datetime | None:
        if not last_run_at:
            return None
        try:
            parsed = datetime.fromisoformat(last_run_at)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed
        return parsed.astimezone().replace(tzinfo=None)

    def _is_sync_due(
        self,
        last_run_at: str | None,
        sync_mode: str,
        sync_start_time: str,
        sync_interval_minutes: int,
        sync_days_of_week: list[int],
        sync_loop_enabled: bool,
    ) -> bool:
        if sync_mode != "scheduled":
            return self._is_due(last_run_at, sync_interval_minutes)

        now_local = datetime.now()
        allowed_days = sorted({day for day in sync_days_of_week if 0 <= day <= 6}) or [0, 1, 2, 3, 4, 5, 6]
        if now_local.weekday() not in allowed_days:
            return False

        try:
            start_hour, start_minute = [int(part) for part in sync_start_time.split(":", maxsplit=1)]
            target_time = time(hour=start_hour, minute=start_minute)
        except (TypeError, ValueError):
            return self._is_due(last_run_at, sync_interval_minutes)

        target_datetime = datetime.combine(now_local.date(), target_time)
        if now_local < target_datetime:
            return False

        last_run_local = self._parse_last_run_local(last_run_at)
        if last_run_local is None:
            return True

        if last_run_local.date() < now_local.date():
            return True

        if not sync_loop_enabled:
            return False

        return (now_local - last_run_local).total_seconds() >= max(sync_interval_minutes, 1) * 60

    def _mark_disabled(self, job_key: str, message: str) -> None:
        job = self._state["jobs"][job_key]
        job["enabled"] = False
        job["lastStatus"] = "disabled"
        job["lastMessage"] = message

    def _mark_started(self, job_key: str, enabled: bool) -> None:
        job = self._state["jobs"][job_key]
        job["enabled"] = enabled
        if not enabled:
            return
        job["lastRunAt"] = now_iso()
        job["lastStatus"] = "running"
        job["lastMessage"] = "Đang chạy."

    def _mark_result(self, job_key: str, status: str, message: str, success: bool = False) -> None:
        job = self._state["jobs"][job_key]
        job["lastStatus"] = status
        job["lastMessage"] = message
        if success:
            job["lastSuccessAt"] = now_iso()

    async def run_cycle(self) -> None:
        base_settings = get_settings()
        settings = apply_runtime_settings(base_settings)
        self._state["effectiveSettings"] = build_settings_response(base_settings).model_dump()
        self._state["lastConfigReloadAt"] = now_iso()

        interval_minutes = settings.sync_interval_minutes
        auto_sync = settings.auto_sync
        auto_recommend = settings.auto_recommend
        auto_schedule = settings.auto_schedule

        if auto_sync:
            sync_job = self._state["jobs"]["sync"]
            sync_job["enabled"] = True
            if settings.sync_website_enabled or settings.sync_social_enabled:
                if self._is_sync_due(
                    sync_job["lastRunAt"],
                    settings.sync_mode,
                    settings.sync_start_time,
                    interval_minutes,
                    settings.get_sync_days_of_week(),
                    settings.sync_loop_enabled,
                ):
                    await self._run_sync_job(settings)
            else:
                self._mark_disabled("sync", "Đã bật tự động đồng bộ nhưng chưa chọn website hoặc social.")
        else:
            self._mark_disabled("sync", "Đã tắt tự động đồng bộ trong cài đặt.")

        if auto_recommend:
            recommend_job = self._state["jobs"]["recommend"]
            recommend_job["enabled"] = True
            if self._is_due(recommend_job["lastRunAt"], interval_minutes):
                await self._run_recommend_job(settings)
        else:
            self._mark_disabled("recommend", "Đã tắt gợi ý AI tự động trong cài đặt.")

        if auto_schedule:
            schedule_job = self._state["jobs"]["schedule"]
            schedule_job["enabled"] = True
            if self._is_due(schedule_job["lastRunAt"], interval_minutes):
                await self._run_schedule_job(settings)
        else:
            self._mark_disabled("schedule", "Đã tắt tự động tạo báo cáo trong cài đặt.")

    async def _run_sync_job(self, settings) -> None:  # type: ignore[no-untyped-def]
        self._mark_started("sync", True)
        messages: list[str] = []
        success = False

        if settings.sync_website_enabled:
            try:
                website_response = await sync_google_website_data(settings)
                messages.append(website_response.message)
                success = True
            except Exception as exc:
                messages.append(f"Website: {exc}")
        else:
            messages.append("Website: đã tắt trong cài đặt.")

        if settings.sync_social_enabled:
            try:
                social_response = await sync_social_platforms(settings)
                messages.append(social_response.message)
                success = True
            except Exception as exc:
                messages.append(f"Social: {exc}")
        else:
            messages.append("Social: đã tắt trong cài đặt.")

        self._mark_result(
            "sync",
            "success" if success else "error",
            " | ".join(messages) if messages else "Không có tác vụ nào được chạy.",
            success=success,
        )

    async def _run_recommend_job(self, settings) -> None:  # type: ignore[no-untyped-def]
        self._mark_started("recommend", True)
        try:
            analysis = await get_local_ai_analysis(settings)
            updated_range = self._write_analysis_snapshot(settings, analysis)
            self._mark_result(
                "recommend",
                "success",
                f"Đã tạo phân tích AI và ghi vào {settings.analysis_report_worksheet} ({updated_range}).",
                success=True,
            )
        except Exception as exc:
            self._mark_result("recommend", "error", f"Phân tích AI thất bại: {exc}")

    async def _run_schedule_job(self, settings) -> None:  # type: ignore[no-untyped-def]
        self._mark_started("schedule", True)
        try:
            response = await sync_daily_report(settings)
            self._mark_result("schedule", "success", response.message, success=True)
        except Exception as exc:
            self._mark_result("schedule", "error", f"Tạo báo cáo tự động thất bại: {exc}")

    def _write_analysis_snapshot(self, settings, analysis: LocalAiAnalysisResponse) -> str:  # type: ignore[no-untyped-def]
        credentials = load_service_account_credentials(settings)
        worksheet = settings.analysis_report_worksheet
        ensure_sheet_exists(settings, credentials, worksheet)

        header = ["generated_at", "summary", "analysis", "model_ai", "nguon_ai"]
        row = [analysis.generatedAt, analysis.summary, analysis.analysis, analysis.model, analysis.source]
        service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
        existing_rows = get_sheet_values(settings, credentials, worksheet)

        if not existing_rows:
            service.spreadsheets().values().update(
                spreadsheetId=settings.google_sheet_id,
                range=f"{worksheet}!A1",
                valueInputOption="RAW",
                body={"values": [header, row]},
            ).execute()
            return f"{worksheet}!A1:E2"

        if existing_rows[0] != header:
            service.spreadsheets().values().update(
                spreadsheetId=settings.google_sheet_id,
                range=f"{worksheet}!A1",
                valueInputOption="RAW",
                body={"values": [header]},
            ).execute()

        response = (
            service.spreadsheets()
            .values()
            .append(
                spreadsheetId=settings.google_sheet_id,
                range=f"{worksheet}!A2",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": [row]},
            )
            .execute()
        )
        updates = response.get("updates", {})
        return str(updates.get("updatedRange", "")) or f"{worksheet}!A:E"

    def get_status(self) -> AutomationStatusResponse:
        effective_settings = self._state.get("effectiveSettings") or build_settings_response(get_settings()).model_dump()
        jobs = [
            AutomationJobStatus(**job_state)
            for job_state in self._state["jobs"].values()
        ]
        return AutomationStatusResponse(
            running=self._running,
            pollSeconds=POLL_SECONDS,
            effectiveSettings=SettingsResponse.model_validate(effective_settings),
            lastConfigReloadAt=self._state.get("lastConfigReloadAt"),
            jobs=jobs,
        )


automation_manager = AutomationManager()
