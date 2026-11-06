from .state_group import State


class UdsService:
    def __init__(self, name, service_id, execute_permission, sub_func_avail) -> None:
        self.name = name
        self.service_id = service_id
        self.execute_permission = execute_permission
        self.sub_func_avail = sub_func_avail
        self.subservices = {}

    def add_sub_service(self, name, subservice_id, execute_permission):
        self.subservices.update({
            subservice_id: UdsSubService(name, subservice_id, execute_permission, self)
        })
        # Update execute permission due to the change of subservice
        self.calculate_execute_permission()

    def calculate_execute_permission(self):
        """
        Calculate execute permission of the uds service according to all its subservice
        """
        new_execute_permission = 0
        for subservice in self.subservices.values():
            new_execute_permission |= int(subservice.execute_permission, 2)

        self.execute_permission = bin(new_execute_permission)[2:].zfill(State.count)

    def update_execute_permission(self, execute_permission):
        """
        Update execute permission with new execute permission
        """
        digit_current_permission = int(self.execute_permission, 2)
        digit_current_permission |= int(execute_permission, 2)
        self.execute_permission = bin(digit_current_permission)[2:].zfill(State.count)


class UdsSubService:
    """
    Subservice of uds service
    """
    def __init__(self, name, subservice_id, execute_permission, parent_service) -> None:
        self.name = name
        self.subservice_id = subservice_id
        self.execute_permission = execute_permission
        self.parent_service: UdsService = parent_service

    def update_execute_permission(self, execute_permission):
        digit_current_permission = int(self.execute_permission, 2)
        digit_current_permission |= int(execute_permission, 2)
        self.execute_permission = bin(digit_current_permission)[2:].zfill(State.count)
        # Due to the change of subservice execute permission, the parent service also need update
        self.parent_service.calculate_execute_permission()
