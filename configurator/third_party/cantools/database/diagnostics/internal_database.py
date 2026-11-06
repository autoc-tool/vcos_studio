# Internal diagnostics database.


class InternalDatabase(object):
    """Internal diagnostics database.

    """

    def __init__(self, pids, vehi_ids, dids, dtcs, obd_dtcs, enable_conditions, enable_condition_groups, events,
                 snapshots, extended_datas, uds_services, state_groups, routines, interface_param):
        self.dids = dids
        self.pids = pids
        self.vehi_ids = vehi_ids
        self.dtcs = dtcs
        self.obd_dtcs = obd_dtcs
        self.enable_conditions = enable_conditions
        self.enable_condition_groups = enable_condition_groups
        self.events = events
        self.snapshots = snapshots
        self.extended_datas = extended_datas
        self.uds_services = uds_services
        self.state_groups = state_groups
        self.routines = routines
        self.interface_param = interface_param
