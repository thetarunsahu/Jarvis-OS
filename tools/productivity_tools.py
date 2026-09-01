from productivity.accountability_engine import AccountabilityEngine
from productivity.productivity_store import ProductivityStore


class ProductivityTools:
    def __init__(self, store=None, accountability_engine=None):
        self.store = store or ProductivityStore()
        self.accountability = accountability_engine or AccountabilityEngine(
            productivity_store=self.store
        )

    def create_goal(self, title, target_date=None):
        goal = self.store.create_goal(title=title, target_date=target_date)
        return {
            "goal_id": goal["goal_id"],
            "title": goal["title"],
            "status": goal["status"],
            "progress": goal["progress"],
            "target_date": goal["target_date"],
        }

    def list_goals(self):
        return self.store.list_goals(status="active", limit=20)

    def update_goal(self, goal_id, progress=None, status=None):
        goal = self.store.update_goal(
            goal_id=goal_id,
            progress=progress,
            status=status,
        )
        if goal is None:
            return f"Goal not found: {goal_id}"
        return goal

    def create_reminder(self, text, due_at):
        reminder = self.store.create_reminder(text=text, due_at=due_at)
        return {
            "reminder_id": reminder["reminder_id"],
            "text": reminder["text"],
            "due_at": reminder["due_at"],
            "status": reminder["status"],
        }

    def list_reminders(self):
        return self.store.list_reminders(status="pending", limit=20)

    def complete_reminder(self, reminder_id):
        reminder = self.store.complete_reminder(reminder_id)
        if reminder is None:
            return f"Reminder not found: {reminder_id}"
        return reminder

    def daily_brief(self):
        return self.accountability.render_brief()
