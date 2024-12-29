from session_manager import session_context
from repository.tsp import TSPRepository
import asyncio

tsp_repo = TSPRepository()


async def retrieve_tsps_by_types():
    async with session_context() as session_manager:
        for tsp in await tsp_repo.get_list_of_tsp_by_type(
            session_manager=session_manager,
            tsp_type_name="Airline",
            size=100
        ):
            print(tsp)


if __name__ == "__main__":
    print("Retreive tsps by types")
    asyncio.run(retrieve_tsps_by_types())
    print("TSP's were retrieved successfully")
