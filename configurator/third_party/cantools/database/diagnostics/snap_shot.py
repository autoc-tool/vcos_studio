class SnapShot:
    def __init__(self,
                 name: str,
                 dids,
                 did_refs = None,
                 ) -> None:
        # The snapshot name as a string.
        self.name: str = name
        # Dids that make up the snapshot
        self.dids = dids
        # The dids referenced by this snapshot
        self.did_refs = did_refs
