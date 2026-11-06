class State:
    _count = 0
    def __init__(self,
                name,
                number):
        self.name = name
        # Number of the state according to the order in cdd text file
        self.number = number
        self.used = None

    @property
    def count(self):
        return State._count

    @count.setter
    def count(self, num):
        State._count = num

    def set_used(self, state):
        self.used = state


class StateGroup:
    def __init__(self,
                name,
                state_list,
                spec):
        self.name = name
        self.state_list = state_list
        self.spec = spec
