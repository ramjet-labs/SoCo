import aiohttp.web
import asyncio
import enum
import functools
import logging

from soco import config
from . import parser

from . import exceptions

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class SonosEvent:

  def __init__(self, **entries):
    self.__dict__.update(entries)

class SonosEventServer:

  def __init__(self, loop, listen_host, listen_port):
    self.loop = loop
    self._app = aiohttp.web.Application(loop=loop)
    self._app.router.add_route(
        name="notify_event",
        method="*",
        path="/",
        handler=self.handle_incoming_event,
    )
    self._socket_server_protocol = self._app.make_handler()
    self.listen_host = listen_host
    self.listen_port = listen_port
    self._socket_server = None
    self.sid_to_callback_mapping = {}

  def register_callback_for_service_id(self, sid, callback):
    self.sid_to_callback_mapping.setdefault(sid, set()).add(callback)

  def unregister_callback_for_service_id(self, sid, callback):
    self.sid_to_callback_mapping.setdefault(sid, set()).remove(callback)

  async def start(self):
    log.info("Starting event listening server at %s:%s", self.listen_host, self.listen_port)
    self._socket_server = await self.loop.create_server(
        protocol_factory=self._socket_server_protocol,
        host=self.listen_host,
        port=self.listen_port,
    )

  async def shutdown(self):
    # Stop accepting any new connections
    if self._socket_server:
      self._socket_server.close()
      await self._socket_server.wait_closed()
      self._socket_server = None

    # Fire a shutdown signal to any registered on_shutdown handlers
    await self._app.shutdown()

    # Close any outstanding connections (with a 5 second timeout)
    await self._socket_server_protocol.finish_connections(timeout=5)

  async def handle_incoming_event(self, request):
    if request.method.lower() != "notify":
      return aiohttp.web.Response(status=204)

    content = await request.text()
    variables = parser.parse_event_xml(content)
    variables["sid"] = request.headers["sid"] # Event Subscription Identifier
    variables["seq"] = request.headers["seq"] # Event Sequence Number
    event = SonosEvent(**variables)

    for callback in self.sid_to_callback_mapping.get(request.headers["sid"], []):
      callback_future = asyncio.ensure_future(callback(event), loop=self.loop)
      callback_future.add_done_callback(self.check_for_callback_error)

    return aiohttp.web.Response(status=200)

  def check_for_callback_error(self, callback_future):
    if callback_future.exception():
      log.exception("Exception occured handling event callback: %s", callback_future.exception())


class SonosSubscription:

  def __init__(self, loop, event_server, subscribe_uri, callback_func, requested_timeout=None):
      self.loop = loop
      self.event_server = event_server
      self.subscribe_uri = subscribe_uri
      self.sid = None # A unique ID for this subscription, provided by sonos
      self.callback_func = callback_func # Callback to send events to
      self.requested_timeout = requested_timeout # The period for which the subscription is requested
      self._renewal_handle = None
      self._session = aiohttp.ClientSession(loop=loop)

  async def subscribe(self, auto_renew=False):
      response = await self._make_subscription_request(
          method="SUBSCRIBE",
          headers={
              'Callback': '<http://{0}:{1}>'.format(
                  self.event_server.listen_host, self.event_server.listen_port
              ),
              'NT': 'upnp:event',
          }
      )
      self.sid = response.headers['sid']
      self.event_server.register_callback_for_service_id(self.sid, self.callback_func)
      if auto_renew:
        self._set_up_renewal(response.headers.get('timeout'), auto_renew)

  async def renew(self, auto_renew=False):
      if not self.sid:
          raise exceptions.SoCoException(
              'Cannot renew subscription before subscribing')

      try:
        response = await self._make_subscription_request(
            method="SUBSCRIBE",
            headers={'SID': self.sid}
        )
        if auto_renew:
          self._set_up_renewal(response.headers.get('timeout'), auto_renew)
      except exceptions.SoCoPreconditionException:
        await self.subscribe(auto_renew=auto_renew)

      log.info("Successfully renewed subscription with id: %s", self.sid)

  async def unsubscribe(self):

      if not self.sid:
        return

      if self._renewal_handle:
        self._renewal_handle.cancel()

      await self._make_subscription_request(
          method="UNSUBSCRIBE",
          headers={"SID": self.sid},
      )
      self._session.close()
      self.event_server.unregister_callback_for_service_id(self.sid, self.callback_func)

  async def _make_subscription_request(self, method, headers):
    if self.requested_timeout:
      headers["TIMEOUT"] = "Second-{0}".format(self.requested_timeout)

    async with self._session.request(
        method=method,
        url=self.subscribe_uri,
        headers=headers,
    ) as response:
      if response.status == 412:
        raise exceptions.SoCoPreconditionException("Not subscribed to sonos with sid: %s" %
                                                   self.sid)
      if response.status != 200:
        error_response = await response.text()
        raise exceptions.SoCoException("Request to: %s with headers: %s failed with status: %s %s" %
                           (self.subscribe_uri, response.status, headers, error_response))
      return response

  def _set_up_renewal(self, timeout, auto_renew):
    if not timeout or timeout == 'infinite':
      return
    converted_timeout = int(timeout.lower().lstrip('second-'))
    self._renewal_handle = self.loop.call_later(
        converted_timeout*.75, # We must renew a subscription before it expires
        functools.partial(self._call_renew, auto_renew=auto_renew)
    )

  def _call_renew(self, auto_renew):
    self.loop.create_task(self.renew(auto_renew=auto_renew))


