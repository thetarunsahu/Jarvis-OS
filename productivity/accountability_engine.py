from datetime import datetime, timedelta, timezone

from productivity.productivity_store import ProductivityStore
from tasks.task_store import TaskStore


def parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


class AccountabilityEngine:
    """Builds a compact, evidence-based snapshot of the user's commitments."""

    def __init__(self, productivity_store=None, task_store=None):
        self.productivity = productivity_store or ProductivityStore()
        self.tasks = task_store or TaskStore()

    def snapshot(self, now=None):
        local_now = now or datetime.now().astimezone()
        if local_now.tzinfo is None:
            local_now = local_now.replace(tzinfo=timezone.utc)

        active_goals = self.productivity.list_goals(status="active", limit=50)
        reminders = self.productivity.list_reminders(status=None, limit=100)
        recent_tasks = self.tasks.list(limit=50, status=None)

        overdue = []
        due_today = []
        upcoming = []
        tomorrow_cutoff = local_now + timedelta(hours=48)

        for reminder in reminders:
            if reminder.get("status") not in {"pending", "notified"}:
                continue

            due = parse_iso(reminder.get("due_at"))
            if due is None:
                continue
            due_local = due.astimezone(local_now.tzinfo)

            item = dict(reminder)
            item["due_local"] = due_local.isoformat()

            if due_local < local_now:
                overdue.append(item)
            elif due_local.date() == local_now.date():
                due_today.append(item)
            elif due_local <= tomorrow_cutoff:
                upcoming.append(item)

        task_counts = {
            "active": 0,
            "completed": 0,
            "failed": 0,
        }
        for task in recent_tasks:
            status = task.status.value
            if status == "completed":
                task_counts["completed"] += 1
            elif status == "failed":
                task_counts["failed"] += 1
            elif status not in {"cancelled"}:
                task_counts["active"] += 1

        goals_at_risk = []
        for goal in active_goals:
            target = parse_iso(goal.get("target_date"))
            if target is None:
                continue
            if target.tzinfo is None:
                target = target.replace(tzinfo=local_now.tzinfo)
            target_local = target.astimezone(local_now.tzinfo)
            if target_local <= local_now + timedelta(days=7) and int(goal.get("progress", 0)) < 80:
                goals_at_risk.append(goal)

        return {
            "generated_at": local_now.isoformat(),
            "active_goals": active_goals,
            "goals_at_risk": goals_at_risk,
            "overdue_reminders": overdue,
            "due_today": due_today,
            "upcoming_48h": upcoming,
            "recent_task_counts": task_counts,
        }

    def render_brief(self, now=None):
        data = self.snapshot(now=now)
        lines = ["JARVIS DAILY BRIEF"]

        lines.append(
            f"Goals: {len(data['active_goals'])} active"
            + (
                f" | {len(data['goals_at_risk'])} near target and below 80%"
                if data["goals_at_risk"]
                else ""
            )
        )
        lines.append(
            f"Reminders: {len(data['overdue_reminders'])} overdue | "
            f"{len(data['due_today'])} due today | "
            f"{len(data['upcoming_48h'])} upcoming"
        )
        counts = data["recent_task_counts"]
        lines.append(
            f"Recent JARVIS tasks: {counts['active']} active | "
            f"{counts['completed']} completed | {counts['failed']} failed"
        )

        if data["overdue_reminders"]:
            lines.append("Overdue:")
            for reminder in data["overdue_reminders"][:5]:
                lines.append(
                    f"- {reminder['text']} (due {reminder['due_local']})"
                )

        if data["due_today"]:
            lines.append("Due today:")
            for reminder in data["due_today"][:5]:
                lines.append(
                    f"- {reminder['text']} (due {reminder['due_local']})"
                )

        if data["goals_at_risk"]:
            lines.append("Goals needing attention:")
            for goal in data["goals_at_risk"][:5]:
                lines.append(
                    f"- {goal['title']} ({goal['progress']}%, target {goal['target_date']})"
                )

        if (
            not data["active_goals"]
            and not data["overdue_reminders"]
            and not data["due_today"]
        ):
            lines.append("No active commitments are recorded yet.")

        return "\n".join(lines)
