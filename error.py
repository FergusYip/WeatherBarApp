
class LocationNotFoundError(Exception):
    """
    Exception raised when the location is not found

    Attributes:
        message -- explanation of the error
    """
    def __init__(self, message="Location was not found"):
        self.message = message
        super().__init__(self.message)
