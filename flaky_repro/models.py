class Run:
    def __init__(
        self, 
        run_index:int | None, 
        status:str | None,
        duration:float | None,
        timestamp:float | None,
        conditions:str | None,
        stdout:str | None,
        stderr:str | None,
        exception_info:str | None,
        evidence:str | None
    ):
        self.run_index = run_index
        self.status = status
        self.duration = duration
        self.timestamp = timestamp
        self.conditions = conditions
        self.stdout = stdout
        self.stderr = stderr
        self.exception_info = exception_info
        self.evidence = evidence