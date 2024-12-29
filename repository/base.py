from functools import wraps
from typing import Any, Awaitable, Callable, Generic, Type, TypeVar

from pydantic import BaseModel


def parse_sparksee_value(value):
    if value.HasField("nullValue"):
        return None
    elif value.HasField("intValue"):
        return value.intValue
    elif value.HasField("longValue"):
        return value.longValue
    elif value.HasField("stringValue"):
        return value.stringValue
    elif value.HasField("timestampValue"):
        return (
            value.timestampValue.ToDatetime()
        )  # assuming you want to convert to datetime
    elif value.HasField("doubleValue"):
        return value.doubleValue
    elif value.HasField("boolValue"):
        return value.boolValue
    elif value.HasField("oidValue"):
        return value.oidValue
    else:
        return None


ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    model: Type[ModelType] | None
    entity: str

    def process_query_response(
        self,
        *,
        response,
    ) -> list[ModelType]:
        list_of_models = []
        for row in response.rows:
            column_values = [parse_sparksee_value(cv) for cv in row.columnValues]
            new_model = self.model(
                **dict(zip(self.model.model_fields.keys(), column_values, strict=False))
            )
            list_of_models.append(new_model)
        return list_of_models

    @staticmethod
    def _change_query_string(str_object: str) -> str:
        return f"'{str_object}'"

    @staticmethod
    def create_conditions_from_list(
        condition: str, provided_condition: list[str] | None
    ):
        if not provided_condition:
            return None

        conditions = [f"{condition}='{element}'" for element in provided_condition]
        return f"({' OR '.join(conditions)})"

    def algebra_match_conditions(self, **kwargs) -> str:
        list_of_filters = []
        for key, value in kwargs.items():
            updated_string = ""
            if value is None:
                continue
            elif isinstance(value, str):
                updated_string = (
                    f"'{self.entity}'.'{key}' = {self._change_query_string(value)}"
                )
            elif isinstance(value, int):
                updated_string = f"'{self.entity}'.'{key}' = {value}"
            list_of_filters.append(updated_string)

        match_conditions = " AND ".join(list_of_filters)
        if not match_conditions:
            return f"GRAPH::SCAN('{self.entity}')"
        return f"GRAPH::SELECT({match_conditions})"

    def cypher_match_conditions(self, **kwargs) -> str:
        list_of_filters = []
        for key, value in kwargs.items():
            updated_string = ""
            if value is None:
                continue
            elif isinstance(value, str):
                updated_string = f"{key}: {f'{self._change_query_string(value)}'}"  # noqa
            elif isinstance(value, int):
                updated_string = f"{key}: {value}"
            list_of_filters.append(updated_string)

        return ", ".join(list_of_filters)


def query_executor(query_type: str) -> Callable:
    def decorator(func: Callable[..., Awaitable[tuple[Any, str]]]) -> Callable:
        @wraps(func)
        async def wrapper(self, size: int = 1, **kwargs) -> list[Any] | Any | None:
            session_manager, stmt = await func(self, **kwargs)
            response = await session_manager.execute_query(
                stmt=stmt, query_type=query_type, max_rows=size
            )
            parsed_model = self.process_query_response(response=response)
            if not parsed_model:
                return None

            if size == 1:
                return parsed_model[0]
            return parsed_model

        return wrapper

    return decorator
