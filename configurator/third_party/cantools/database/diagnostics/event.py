class Event():

    def __init__(self,
                 name,
                 algorithm=None,
                 clear_allowed=None,
                 clear_behavior=None,
                 rec_same_op_cycle=None,
                 condition=None,
                 storage_condition=None,
                 failure_cycle=None,
                 ff_prestorage=None,
                 ff_prestorage_in_memory=None,
                 kind=None,
                 operation_cycle=None,
                 dtc=None,
                 indicator_connector=None) -> None:
        self.name = name
        self.algorithm = algorithm
        self.clear_allowed = clear_allowed
        self.clear_behavior = clear_behavior
        self.rec_same_op_cycle = rec_same_op_cycle
        self.condition = condition
        self.storage_condition = storage_condition
        self.failure_cycle = failure_cycle
        self.ff_prestorage = ff_prestorage
        self.ff_prestorage_in_memory = ff_prestorage_in_memory
        self.kind = kind
        self.operation_cycle = operation_cycle
        self.dtc = dtc
        self.indicator_connector = indicator_connector
