SoCo
====

This is a fork of the [SoCo (Sonos Controller)] (https://github.com/SoCo/SoCo). It attempts to fix certain soco bugs and act as a slow migration to an async framework.

Bugs Fixed:

* DidlMetadata Errors when ingesting certain events [Issue](https://github.com/SoCo/SoCo/issues/276)
* Errors after subscribing to soco.services.Queue [Issue](https://github.com/SoCo/SoCo/issues/378)


### Subscribing to events

```python
event_server = soco.events.SonosEventServer(
	loop=loop,
  listen_host="192.168.1.48",
  listen_port=9000,
)
subscription = soco.events.SonosSubscription(
  loop=loop,
  event_server=event_server,
  subscribe_uri="http://192.168.1.11:1400/MediaRenderer/RenderingControl/Event",
  callback_func=notification_callback,
)
await event_server.start()
await subscription.subscribe(auto_renew=True)
await subscription.unsubscribe()
await event_server.shutdown()

async def notification_callback(event):
  print("Received Event:", event)

```