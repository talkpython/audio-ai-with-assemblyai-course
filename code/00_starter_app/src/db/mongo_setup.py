import socket
from typing import Optional

import beanie
import motor.motor_asyncio

from db import models

development_mode: bool = True


async def init_connection(
    database: str,
    server: Optional[str] = 'localhost',
    port: int = 27017,
    username: Optional[str] = None,
    password: Optional[str] = None,
    use_ssl: bool = False,
):
    server = server or 'localhost'
    port = port or 27017

    await _motor_init(
        database=database,
        password=password,
        port=port,
        server=server,
        use_ssl=use_ssl,
        username=username,
        models_classes=models.all_models,
    )


async def _motor_init(
    database: str,
    password: Optional[str],
    port: int,
    server: str,
    use_ssl: bool,
    username: Optional[str],
    models_classes,
):
    ensure_server_is_accessible(server, port)
    conn_string = create_connection_string(password, port, server, use_ssl, username)

    print(f'Initializing motor connection for db {database} on {server}:{port}')
    print(f'Connection string: {conn_string.replace(password or "NO_PASSWORD", "***********")}')

    # Crete Motor client
    client = motor.motor_asyncio.AsyncIOMotorClient(conn_string)

    # Init beanie with the Product document class
    await beanie.init_beanie(database=client[database], document_models=models_classes)
    print(f'Init done for db {database}')


def create_connection_string(password, port, server, use_ssl, username):
    if username or password:
        use_ssl = str(use_ssl).lower()
        return f'mongodb://{username}:{password}@{server}:{port}/?authSource=admin&tls={use_ssl}&tlsInsecure=true'
    else:
        return f'mongodb://{server}:{port}'


def ensure_server_is_accessible(server: str, port: int):
    try:
        # Create a TCP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        print(f'Checking for database server {server} at port {port}.')

        # Connect to a server
        server_address = (server, port)
        sock.connect(server_address)

        print(f'Connected to server {server} successfully.')

        # Close the socket
        sock.close()
    except Exception as x:
        print(f'WARNING: Cannot connected to database server {server}:{port}.')
        print(f'ERROR reason: {x}')
        msg = "You must have MongoDB running at the destination for this app to work."
        print(msg)

        raise Exception(msg) from x
