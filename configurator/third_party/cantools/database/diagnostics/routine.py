class Routine:
    def __init__(self,
                name,
                identifier,
                service_list
                ):
        self.name = name
        self.identifier = identifier
        self.service_list = service_list
        self.used = None

    def set_used(self, state: bool):
        self.used = state

class RoutineService:
    def __init__(self,
                name,
                sid,
                ssid,
                parameter_dict,
                execute_permission):
        self.sid = sid
        self.ssid = ssid
        self.name =name
        self.parameter_dict = parameter_dict
        self.execute_permission = execute_permission
