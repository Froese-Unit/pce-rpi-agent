import base64
import logging
import os
import re
from functools import wraps
from typing import Awaitable, Callable, Dict, Union
from uuid import UUID, uuid4

import aiohttp
from aiohttp import web
from aiohttp_session import cookie_storage, get_session, setup  # type: ignore
from cryptography import fernet

from pce import settings as st
from pce.game import Game
from pce.player import Player
from pce.types import Event, OutEvents
from pce.utils import create_task

logger = logging.getLogger(__name__)
routes = web.RouteTableDef()


Client = aiohttp.ClientWebSocketResponse
Handler = Callable[..., Awaitable[web.Response]]


def error_event(message: str) -> Event:
    return {"tipe": OutEvents.error, "data": message}


def error_response(contents: Union[str, Dict[str, str]], status: int) -> web.Response:
    return web.json_response({"error": contents}, status=status)


def with_uuid(handler: Handler) -> Handler:
    @wraps(handler)
    async def wrapper(request: web.Request) -> web.Response:
        session = await get_session(request)
        if "uuid" not in session:
            return error_response(
                {"uuid": "session cookie containing a uuid is needed"}, status=401
            )

        return await handler(request, session["uuid"])

    return wrapper


def as_player(handler: Handler) -> Handler:
    @with_uuid
    @wraps(handler)
    async def wrapper(request: web.Request, uuid: UUID) -> web.Response:
        game = request.app["game"]
        try:
            player = game.players[[p.uuid for p in game.players].index(uuid)]
        except ValueError:
            return error_response(
                {"uuid": "Your uuid must be one of the players"}, status=401
            )

        return await handler(request, uuid, player)

    return wrapper


def as_experimenter(handler: Handler) -> Handler:
    @with_uuid
    @wraps(handler)
    async def wrapper(request: web.Request, uuid: UUID) -> web.Response:
        game = request.app["game"]
        if game.experimenter_uuid != uuid:
            return error_response(
                {"uuid": "Your uuid must be the experimenter's"}, status=401
            )

        return await handler(request, uuid)

    return wrapper


@routes.get("/")
async def get_index(request: web.Request) -> web.FileResponse:
    return web.FileResponse(os.path.join(st.WEBVIZ_PATH, "index.html"))


@routes.get("/api/meta")
async def get_meta(request: web.Request) -> web.Response:
    game = request.app["game"]

    # Get or set the client's uuid
    session = await get_session(request)
    if "uuid" not in session:
        uuid = str(uuid4())
        logger.info("get_meta: create client uuid: %s", uuid)
        session["uuid"] = uuid
    else:
        logger.info("get_meta: client has uuid %s", session["uuid"])

    return web.json_response(game.meta_data(session["uuid"]))


@routes.post("/api/meta/slot")
@with_uuid
async def post_meta_slot(request: web.Request, uuid: UUID) -> web.Response:
    game = request.app["game"]

    post = await request.json()
    slot = post["slot"]

    if slot == "experimenter":
        if game.experimenter_uuid is None:
            logger.info("post_meta_slot: set experimenter slot to uuid %s", uuid)
            game.experimenter_uuid = uuid
        else:
            logger.info(
                "post_meta_slot: experimenter slot is already in use by uuid %s",
                game.experimenter_uuid,
            )
            return error_response(
                {
                    "slot": f"experimenter slot is already in use by uuid {game.experimenter_uuid}"
                },
                status=409,
            )
    else:
        assert slot in ["p0", "p1"]
        player = game.players[int(slot[1:])]
        # AGENT 20260813: the agent's slot is driven by agent_step(), not by a
        # person, so it must stay unclaimed. Claiming it silently breaks the
        # next request: as_player() maps a uuid to the FIRST player matching it,
        # so a browser holding both slots has all its player requests routed to
        # p0 (e.g. "pid of player 0 is already set" when setting p1's pid).
        if player.is_agent:
            logger.info(
                "post_meta_slot: refused -- player %s is the agent slot", player.index
            )
            return error_response(
                {
                    "slot": f"slot {player.index} is the agent and cannot be joined; "
                    "the agent plays it automatically"
                },
                status=409,
            )
        if player.uuid is None:
            logger.info(
                "post_meta_slot: set player %s slot to uuid %s", player.index, uuid
            )
            player.uuid = uuid
        else:
            logger.info(
                "post_meta_slot: player %s slot already in use by uuid %s",
                player.index,
                player.uuid,
            )
            return error_response(
                {
                    "slot": f"slot {player.index} is already in use by uuid {player.uuid}"
                },
                status=409,
            )

    ws_broadcast(request.app["ws_clients"], game.meta_event)
    return web.json_response({"slots": game.slots_data()})


@routes.post("/api/meta/pid")
@as_player
async def post_meta_pid(
    request: web.Request,
    uuid: UUID,
    player: Player,
) -> web.Response:
    game = request.app["game"]

    post = await request.json()
    pid = post["pid"]
    other_player = game.players[1 - player.index]

    if player.pid is None:
        if other_player.pid == pid:
            logger.info(
                "post_meta_pid: posted pid for player %s (uuid %s) is already "
                "in use by player %s (uuid %s)",
                player.index,
                uuid,
                other_player.index,
                other_player.uuid,
            )
            return error_response(
                {
                    "pid": (
                        f"This pid is already used by player "
                        f"{other_player.index} (uuid {other_player.uuid})"
                    )
                },
                status=409,
            )
        elif not re.match(r"^[0-9A-Za-z]{4,}$", pid):
            logger.info(
                "post_meta_pid: received pid (%s) is too short or has bad characters",
                pid,
            )
            return error_response(
                {
                    # TODO: set up translation, or symbol decoded in Elm
                    "pid": (
                        "Please enter a Participant ID with at least 4 characters. "
                        "There should be only numbers, lowercase "
                        "or uppercase letters. In particular, no spaces, "
                        "special characters or accents are allowed."
                    )
                },
                status=400,
            )
        else:
            logger.info(
                "post_meta_pid: set player %s (uuid %s) to pid %s",
                player.index,
                uuid,
                pid,
            )
            player.pid = pid
    else:
        logger.info(
            "post_meta_pid: pid of player %s (uuid %s) is already set (to %s)",
            player.index,
            uuid,
            pid,
        )
        return error_response(
            {"pid": f"pid of player {player.index} (uuid {uuid}) is already set"},
            status=403,
        )

    ws_broadcast(request.app["ws_clients"], game.meta_event)
    return web.json_response({"pids": game.pids_data()})


@routes.post("/api/players/ready")
@as_player
async def post_players_ready(
    request: web.Request,
    uuid: UUID,
    player: Player,
) -> web.Response:
    game = request.app["game"]
    # longpress_callback takes care of broadcasting to ws_clients
    player.longpress_callback()
    return web.json_response({"players": game.players_data()})


@routes.post("/api/phase/start")
@as_experimenter
async def post_phase_start(request: web.Request, uuid: UUID) -> web.Response:
    phase = request.app["game"].phase
    # move_next_phase will broadcast the new phase to ws
    new_phase = phase.move_next_phase()
    return web.json_response({"phase": new_phase.event_data()})


@routes.post("/api/phase/questionnaire")
@as_player
async def post_phase_questionnaire(
    request: web.Request,
    uuid: UUID,
    player: Player,
) -> web.Response:
    phase = request.app["game"].phase
    post = await request.json()

    # Fail early if the questionnaire type is not supported
    for qtype in post.keys():
        if not qtype in (phase.player_qtypes + phase.trial_qtypes):
            return error_response(
                f"Unsupported questionnaire type: {qtype}", status=400
            )

    for qtype, answers in post.items():
        phase.handle_questionnaire(player, qtype, answers)

    ws_broadcast(request.app["ws_clients"], phase.event())
    return web.json_response({"questionnaires": phase.questionnaires_data()})


def ws_broadcast(
    clients: Dict[UUID, Client], event: Union[Callable[[UUID], Event], Event], loop=None
) -> None:
    make_event: Callable[[UUID], Event]
    if callable(event):
        make_event = event
    else:
        # Couldn't find a way to show typing that `event` is an `Event` here, so
        # just ignore type checking
        make_event = lambda _: event  # type: ignore

    for uuid, ws in clients.items():
        create_task(ws.send_json(make_event(uuid)), loop=loop)


@routes.get("/ws")
async def get_ws(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    logger.info("get_ws: new connection")
    clients = request.app["ws_clients"]
    game = request.app["game"]
    uuid = None

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            data = msg.json()
            logger.debug("get_ws: message: %s", data)
            assert data["tipe"] == "uuid"
            assert isinstance(data["data"], str)

            if uuid is None:
                uuid = data["data"]
                clients[uuid] = ws
                logger.info("get_ws: register client as %s", uuid)
                await ws.send_json(game.phase.event())
                await ws.send_json(game.players_event())
            else:
                await ws.send_json(
                    error_event(f"a uuid was already registered ({uuid})")
                )

        elif msg.type == aiohttp.WSMsgType.ERROR:
            logger.info("ws connection closed with exception %s", ws.exception())

    logger.info("websocket_handler: connection closed")
    if uuid is not None:
        del clients[uuid]

    return ws


def make_app(game: Game) -> web.Application:
    app = web.Application()

    # Set up background game and tui tasks
    app["game"] = game
    app.on_startup.append(game.create_tasks)
    app.on_cleanup.append(game.cancel_tasks)

    # Set up cookie storage
    fernet_key = fernet.Fernet.generate_key()
    secret_key = base64.urlsafe_b64decode(fernet_key)
    setup(app, cookie_storage.EncryptedCookieStorage(secret_key))
    # setup(app, SimpleCookieStorage())

    # Store websocket client connections
    app["ws_clients"] = {}

    # Set up routes
    app.add_routes(routes)
    app.add_routes([web.static("/assets", os.path.join(st.WEBVIZ_PATH, "assets"))])

    return app
