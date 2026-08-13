class DomainError(Exception):
    pass


class TicketNotFoundError(DomainError):
    pass


class InvalidResponseTimeError(DomainError):
    pass
