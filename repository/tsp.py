from loguru import logger
from pydantic import BaseModel, Field
from session_manager import SparkseeSessionManager
from base import BaseRepository, query_executor, parse_sparksee_value


class TSPDB(BaseModel):
    node_id: int = Field(title="TSP Node ID")
    id: str = Field(title="TSP ID")  # noqa
    name: str = Field(title="TSP Name")


class TSPUpdate(BaseModel):
    name: str | None = Field(title="TSP Name", default=None)


class TSPRepository(BaseRepository[TSPDB]):
    model = TSPDB
    entity = "TSP"

    @query_executor(query_type="algebra")
    async def create_tsp(
        self,
        *,
        session_manager: SparkseeSessionManager,  # noqa
        _id: str,
        name: str,
        tsp_type_name: str,
    ) -> tuple[SparkseeSessionManager, str]:
        stmt = f"""
            LET
                @new_tsp = GRAPH::INSERT_NODES('{self.entity}',VALUES([STRING,STRING], [['{_id}','{name}']])),
                @v = GRAPH::SET(@new_tsp, 2, ['{self.entity}'.'id', '{self.entity}'.'name'], FALSE),
                @tsp_type = GRAPH::SELECT('TSP_TYPE'.'name' = '{tsp_type_name}'),
                @tsp_data = PRODUCT( @new_tsp, @tsp_type),
                @link_tsp_and_tsp_type = GRAPH::INSERT_EDGES('BELONGS_TO', 2, 3, @tsp_data),
                @fetched_tsp = {self.algebra_match_conditions(id=_id)},
                @result = GRAPH::GET(@fetched_tsp, 0, [
                                    '{self.entity}'.'id',
                                    '{self.entity}'.'name'
                                ])
            IN
                @result
            """
        return session_manager, stmt

    @query_executor(query_type="algebra")
    async def add_country_to_tsp(
        self,
        session_manager: SparkseeSessionManager,
        tsp_node_id: int,
        country_node_id: int,
    ) -> tuple[SparkseeSessionManager, str]:
        stmt = f"""
            LET
               @oids = VALUES([LONG, LONG], [[{tsp_node_id}L, {country_node_id}L]]),
               @link_tsp_and_country = GRAPH::INSERT_EDGES('OPERATES_IN', 0, 1, @oids),
               @result = GRAPH::GET(VALUES([LONG], [[{tsp_node_id}L]]), 0, [
                                        '{self.entity}'.'id',
                                        '{self.entity}'.'name'
                                    ])
            IN
               @result
            """
        return session_manager, stmt

    @query_executor(query_type="algebra")
    async def add_time_slot_to_tsp(
        self,
        session_manager: SparkseeSessionManager,
        tsp_node_id: int,
        time_slot_node_id: int,
    ) -> tuple[SparkseeSessionManager, str]:
        stmt = f"""
                LET
                   @oids = VALUES([LONG, LONG], [[{tsp_node_id}L, {time_slot_node_id}L]]),
                   @link_tsp_and_country = GRAPH::INSERT_EDGES('HAS_AVAILABILITY', 0, 1, @oids),
                   @result = GRAPH::GET(VALUES([LONG], [[{tsp_node_id}L]]), 0, [
                                            '{self.entity}'.'id',
                                            '{self.entity}'.'name'
                                        ])
                IN
                   @result
                """
        return session_manager, stmt

    @query_executor(query_type="algebra")
    async def get_tsp(
        self,
        session_manager: SparkseeSessionManager,
        size: int = 1,  # noqa
        **kwargs,
    ) -> tuple[SparkseeSessionManager, str]:
        stmt = f"""
        LET
            @tsp = {self.algebra_match_conditions(**kwargs)},
            @result = GRAPH::GET(@tsp, 0, [
                '{self.entity}'.'id',
                '{self.entity}'.'name'
            ])
        IN
            @result
        """

        return session_manager, stmt

    @query_executor(query_type="cypher")
    async def get_list_of_tsp_by_type(
        self,
        *,
        tsp_type_name: str,
        session_manager: SparkseeSessionManager,
        size: int = 10,
    ) -> tuple[SparkseeSessionManager, str]:
        stmt = f"""
                MATCH (tsp_type: TSP_TYPE {{ name : '{tsp_type_name}'}} )<-[:BELONGS_TO]-(tsp:TSP)
                RETURN tsp as node_id, 
                       tsp.id as id, 
                       tsp.name as name
                """  # noqa
        return session_manager, stmt

    @query_executor(query_type="algebra")
    async def update_tsp_by_id(
        self,
        session_manager: SparkseeSessionManager,
        tsp_node_id: int,
        tsp_update: TSPUpdate,
    ) -> tuple[SparkseeSessionManager, str]:
        stmt = f"""
        LET
            @new_values = VALUES([LONG, STRING], [[{tsp_node_id}L, '{tsp_update.name}']]),
            @v = GRAPH::SET(@new_values, 0, [NULL, 'TSP'.'name'], TRUE),
            @result = GRAPH::GET(VALUES([LONG], [[{tsp_node_id}L]]), 0, [
                                '{self.entity}'.'id',
                                '{self.entity}'.'name'
                            ])

        IN
            @result
        """
        return session_manager, stmt

    @query_executor(query_type="algebra")
    async def delete_tsp_by_id(
        self, session_manager: SparkseeSessionManager, tsp_node_id: int
    ) -> tuple[SparkseeSessionManager, str]:
        stmt = f"""
        GRAPH::REMOVE(VALUES([LONG], [[{tsp_node_id}L]]), NULL)
        """
        return session_manager, stmt

    @query_executor(query_type="algebra")
    async def add_data_requirement_to_tsp(
        self,
        session_manager: SparkseeSessionManager,
        tsp_node_id: int,
        data_req_node_id: int,
    ) -> tuple[SparkseeSessionManager, str]:
        stmt = f"""
        LET
           @oids = VALUES([LONG, LONG], [[{tsp_node_id}L, {data_req_node_id}L]]),
           @link_tsp_and_data_req = GRAPH::INSERT_EDGES('CAN_PROVIDE', 0, 1, @oids),
           @result = GRAPH::GET(VALUES([LONG], [[{tsp_node_id}L]]), 0, [
                                    '{self.entity}'.'id',
                                    '{self.entity}'.'name'
                                ])
        IN
           @result
        """
        return session_manager, stmt

    async def remove_data_requirement_from_tsp(
        self,
        session_manager: SparkseeSessionManager,
        tsp_node_id: int,
        data_req_node_id: int,
    ) -> None:
        fetch_stmt = f"""
            PROJECT(GRAPH::CONNECT( VALUES([LONG, LONG], [[{tsp_node_id}L, {data_req_node_id}L]]), ['CAN_PROVIDE']),[2])
            """
        response = await session_manager.execute_query(stmt=fetch_stmt, query_type='algebra', max_rows=1)
        response = response.rows
        if not response:
            logger.error(f"Cannot remove data requirement from TSP {tsp_node_id}")
            return
        fetched_edge_oid = parse_sparksee_value(response[0].columnValues[0])

        remove_stmt = f"GRAPH::REMOVE(VALUES([LONG], [[{fetched_edge_oid}L]]), NULL)"
        await session_manager.execute_query(stmt=remove_stmt, query_type='algebra', max_rows=1)

    @query_executor(query_type="cypher")
    async def get_recommendations(
        self,
        session_manager: SparkseeSessionManager,
        countries: list[str] | None,
        tsp_types: list[str] | None,
        time_slots: list[str] | None,
        size: int = 100,
    ) -> tuple[SparkseeSessionManager, str]:
        tsp_types_condition = self.create_conditions_from_list(
            condition="tsp_type.name", provided_condition=tsp_types
        )

        countries_condition = self.create_conditions_from_list(
            condition="country.name", provided_condition=countries
        )

        time_slots_condition = self.create_conditions_from_list(
            condition="time_slot.name", provided_condition=time_slots
        )

        if tsp_types and countries and time_slots_condition:
            where_clause = f"WHERE {tsp_types_condition} AND {countries_condition} AND {time_slots_condition}"  # noqa
        elif tsp_types is None and countries is None and time_slots_condition is None:
            where_clause = ""
        else:
            conditions = [condition for condition in [tsp_types_condition, countries_condition, time_slots_condition] if
                          condition]
            where_clause = f"WHERE {' AND '.join(conditions)}"  # noqa

        stmt = f"""
                MATCH (tsp_type:TSP_TYPE)<-[:BELONGS_TO]-(tsp:TSP)-[:OPERATES_IN]->(country: COUNTRY),
                       (tsp:TSP)-[:HAS_AVAILABILITY]->(time_slot: TIME_SLOT)
                {where_clause}
                RETURN DISTINCT tsp as node_id,
                       tsp.id as id,
                       tsp.name as name,
                       tsp_type.name as type;
                """
        return session_manager, stmt

    @staticmethod
    async def check_tsp_data_req_connection(
        session_manager: SparkseeSessionManager,
        tsp_node_id: int,
        data_req_node_id: int
    ) -> bool:
        fetch_stmt = f"""
                    PROJECT(GRAPH::CONNECT( VALUES([LONG, LONG], [[{tsp_node_id}L, {data_req_node_id}L]]), ['CAN_PROVIDE']),[2])
                    """
        response = await session_manager.execute_query(
            stmt=fetch_stmt,
            query_type='algebra',
            max_rows=1
        )

        if response.rows:
            return True
        return False
