from api.errors.base import ErrorDefinition


class AuthErrors:
    EMAIL_TAKEN = ErrorDefinition(409, "EMAIL_TAKEN", "An account with this email already exists")
    INVALID_CREDENTIALS = ErrorDefinition(401, "INVALID_CREDENTIALS", "Email or password is incorrect")
    ACCOUNT_INACTIVE = ErrorDefinition(403, "ACCOUNT_INACTIVE", "This account is deactivated")
    MISSING_TOKEN = ErrorDefinition(401, "MISSING_TOKEN", "Authentication required")
    INVALID_TOKEN = ErrorDefinition(401, "INVALID_TOKEN", "Session is invalid or expired")
    INVALID_ROLE = ErrorDefinition(403, "INVALID_ROLE", "Your role cannot perform this action")


class RoomErrors:
    ROOM_NOT_FOUND = ErrorDefinition(404, "ROOM_NOT_FOUND", "Room not found")
    NOT_ROOM_OWNER = ErrorDefinition(403, "NOT_ROOM_OWNER", "You do not own this room")
    NOT_ROOM_MEMBER = ErrorDefinition(403, "NOT_ROOM_MEMBER", "Join this room first")


class PollErrors:
    POLL_NOT_FOUND = ErrorDefinition(404, "POLL_NOT_FOUND", "Poll not found")
    QUESTION_NOT_FOUND = ErrorDefinition(404, "QUESTION_NOT_FOUND", "Question not found")
    POLL_NOT_DRAFT = ErrorDefinition(409, "POLL_NOT_DRAFT", "Only draft polls can be edited")
    POLL_NOT_ACTIVE = ErrorDefinition(409, "POLL_NOT_ACTIVE", "This poll is not active")
    POLL_ALREADY_ACTIVE = ErrorDefinition(
        409, "POLL_ALREADY_ACTIVE", "Another poll is already active in this room"
    )
    POLL_INVALID_FOR_START = ErrorDefinition(
        422, "POLL_INVALID_FOR_START", "Poll is not ready to start"
    )
    INVALID_QUESTION_ORDER = ErrorDefinition(
        422, "INVALID_QUESTION_ORDER", "Order must list every question of the poll exactly once"
    )
    NO_MORE_QUESTIONS = ErrorDefinition(409, "NO_MORE_QUESTIONS", "This is the last question")
    RESULTS_NOT_AVAILABLE = ErrorDefinition(
        409, "RESULTS_NOT_AVAILABLE", "Results are available once the poll has ended"
    )
    NOT_A_PARTICIPANT = ErrorDefinition(403, "NOT_A_PARTICIPANT", "You did not take part in this poll")


class AnswerErrors:
    ANSWER_POLL_CLOSED = ErrorDefinition(409, "ANSWER_POLL_CLOSED", "This poll is no longer accepting answers")
    ANSWER_NOT_CURRENT = ErrorDefinition(
        409, "ANSWER_NOT_CURRENT", "This question is not the one currently open"
    )
    ANSWER_EXPIRED = ErrorDefinition(409, "ANSWER_EXPIRED", "Time is up for this poll")
    ANSWER_INVALID_OPTION = ErrorDefinition(422, "ANSWER_INVALID_OPTION", "That option does not belong to this question")
