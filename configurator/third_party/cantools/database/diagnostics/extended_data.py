class ExtendedData:
    def __init__(self,
                 name: str,
                 datas,
                 length,
                 update,
                 trigger,
                 record_num
                 ) -> None:
        #: The snapshot name as a string.
        self.name: str = name
        #: The dids referenced by this snapshot
        self.datas = datas
        self.length = length
        self.update = update
        self.trigger = trigger
        self.record_num = record_num
