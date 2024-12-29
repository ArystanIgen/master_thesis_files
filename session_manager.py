from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Generator, TypeVar

import grpc
from grpc import aio
from loguru import logger
from pydantic import BaseModel

from core.config import CONFIG
from exceptions import GraphDBException, SparkseeConnectionError
from pb.sparksee_server_pb2 import (
    Query,
    ResultRowsArguments,
    ResultSetID,
    Session,
    SessionArguments,
)
from pb.sparksee_server_pb2_grpc import SparkseeGRPCServerStub

ModelType = TypeVar("ModelType", bound=BaseModel)


@dataclass
class SparkseeSessionManager:
    channel: aio.Channel = field(init=False)
    stub: SparkseeGRPCServerStub = field(init=False)
    session: Session = field(init=False)

    async def init(self):
        """Initialize the gRPC channel, stub, and start a new Sparksee session."""
        self.channel = self.create_aio_channel()
        self.stub = self.get_grpc_stub(self.channel)
        await self.create_session()

    def _create_query(self, *, stmt: str, query_type: str) -> Query:
        if query_type not in ["algebra", "cypher"]:
            query_type = "algebra"
        query_params = {"session": self.session, f"{query_type}Query": stmt}
        return Query(**query_params)

    @staticmethod
    def create_aio_channel() -> aio.Channel:
        try:
            return aio.insecure_channel(
                target=CONFIG.db.url,
                options=CONFIG.db.grpc_config,
            )
        except grpc.RpcError as rpc_error:
            logger.error("Failed to create gRPC channel: %s", rpc_error)
            raise SparkseeConnectionError from rpc_error

    @staticmethod
    def get_grpc_stub(channel: grpc.Channel) -> SparkseeGRPCServerStub:
        return SparkseeGRPCServerStub(channel)

    async def create_session(self):
        try:
            self.session = await self.stub.NewSession(SessionArguments())
        except Exception as exc:
            logger.error("Failed to create sparksee session: %s", exc)
            raise GraphDBException(code="Session") from exc

    async def begin_transaction(self):
        try:
            await self.stub.BeginTx(self.session)
        except grpc.RpcError as rpc_error:
            logger.error("Transaction error: %s", rpc_error)
            await self.rollback_transaction()
            raise SparkseeConnectionError from rpc_error
        except Exception as error:
            logger.error("Unexpected error during transaction: %s", error)
            await self.rollback_transaction()
            raise SparkseeConnectionError from error

    async def commit_transaction(self):
        try:
            await self.stub.CommitTx(self.session)
        except grpc.RpcError as rpc_error:
            logger.error("Commit transaction error: %s", rpc_error)
            raise SparkseeConnectionError from rpc_error
        except Exception as error:
            logger.error("Unexpected error during commit transaction: %s", error)
            raise SparkseeConnectionError from error
        finally:
            await self.stub.EndSession(self.session)
            # self.channel.close()

    async def rollback_transaction(self):
        logger.error("Performing Rollback")
        await self.stub.RollbackTx(self.session)

    async def execute_query(
        self,
        *,
        stmt: str,
        query_type: str = "algebra",
        max_rows: int = 10,
    ):
        query = self._create_query(stmt=stmt, query_type=query_type)
        try:
            fetched_query = await self.stub.RunQuery(query)
            response = await self.stub.GetResultRows(
                ResultRowsArguments(
                    id=ResultSetID(session=self.session, queryId=fetched_query.queryId),
                    maxRows=max_rows,
                )
            )
            await self.stub.CloseQuery(
                ResultSetID(session=self.session, queryId=fetched_query.queryId)
            )
            return response
        except grpc.RpcError as rpc_error:
            logger.error("Query run  error: %s", rpc_error)
            raise GraphDBException(code="Query") from rpc_error


@asynccontextmanager
async def session_context() -> Generator[SparkseeSessionManager, None, None]:
    manager = SparkseeSessionManager()
    await manager.init()
    await manager.begin_transaction()
    try:
        yield manager
    finally:
        await manager.commit_transaction()
