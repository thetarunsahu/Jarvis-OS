from productivity.productivity_store import ProductivityStore


class ProductivityTools:
    def __init__(self, store=None):
        self.store = store or ProductivityStore()

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
