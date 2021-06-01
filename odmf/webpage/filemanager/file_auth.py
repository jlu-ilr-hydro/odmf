from .. import auth
from pathlib import Path




class AccessRule:
    def __init__(self, group='', project='', user=''):
        self.group = group.strip()
        self.user = user.strip()
        self.project = project.strip()

    def __call__(self, user: auth.User):
        return all([
            not self.group or user.is_member(self.group),
            not self.user or user.name == self.user,
            not self.project or int(self.project) in user.projects
        ])

    def __repr__(self):
        return f'AccessRule(group={self.group}, project={self.project}, user={self.user})'


class AccessFile:

    def __init__(self, dir: Path):
        self.path = dir / '.odmf.access'
        self.rules = []
        if self.path.exists():
            with self.path.open() as f:
                for line in f:
                    if not line.strip().startswith('#'):
                        self.rules.append(AccessRule(*line.split(',')))

    def check(self, user: auth.User):
        if not self.rules:
            return True
        else:
            return any(r(user) for r in self.rules)

    def __repr__(self):
        return f'AccessFile(dir={self.path.parent})'


