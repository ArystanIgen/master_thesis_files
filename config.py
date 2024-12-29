import json

import environ


@environ.config(prefix="")
class AppConfig:
    @environ.config(prefix="API")
    class API:
        title = environ.var()
        host = environ.var()
        prefix = environ.var()
        version = environ.var()
        debug = environ.var()
        allowed_hosts = environ.var()

    @environ.config(prefix="DB")
    class DB:
        username = environ.var()
        password = environ.var()
        host = environ.var()
        port = environ.var()
        name = environ.var(default="Sign-Air-Discovery")
        certificate_path = environ.var(default="")

        @property
        def url(self):
            return f"{self.host}:{self.port}"

        @property
        def grpc_config(self):
            return [
                ("grpc.enable_retries", 1),
                (
                    "grpc.service_config",
                    json.dumps(
                        {
                            "methodConfig": [
                                {
                                    "name": [{}],
                                    "retryPolicy": {
                                        "maxAttempts": 5,
                                        "initialBackoff": "0.1s",
                                        "maxBackoff": "1s",
                                        "backoffMultiplier": 2,
                                        "retryableStatusCodes": ["UNAVAILABLE"],
                                    },
                                }
                            ]
                        }
                    ),
                ),
            ]

    env = environ.var()

    api: API = environ.group(API)
    db: DB = environ.group(DB)
    use_monitoring = environ.bool_var()
    otel_collector_url = environ.var()


CONFIG: AppConfig = AppConfig.from_environ()  # type: ignore
