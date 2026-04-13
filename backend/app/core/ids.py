import uuid


def ensure_uuid(value):
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, str):
        return uuid.UUID(value)
    raise ValueError('invalid uuid value')


def ensure_uuid_list(values):
    return [ensure_uuid(v) for v in values]
