from .exceptions import DIDLMetadataError
from .data_structures import from_didl_string
from .utils import camel_to_underscore
from .xml import XML


def parse_event_xml(xml_event):
    """ Parse the body of a UPnP event

    Arg:
        xml_event (str): a byte string containing the body of the event

    Returns:
        A dict with keys representing the evented variables. The relevant value
        will usually be a string representation of the variable's value, but
        may on occasion be:
        *  a dict (eg when the volume changes, the value will
            itself be a dict containing the volume for each channel:
            `{'Volume': {'LF': '100', 'RF': '100', 'Master': '36'}}` )
        * an instance of a MusicInfoItem subclass (eg if it represents track
            metadata)

    """

    result = {}
    tree = XML.fromstring(xml_event)
    # property values are just under the propertyset, which
    # uses this namespace
    properties = tree.findall(
        '{urn:schemas-upnp-org:event-1-0}property')
    for prop in properties:
        for variable in prop:
            # Special handling for a LastChange event specially. For details on
            # LastChange events, see
            # http://upnp.org/specs/av/UPnP-av-RenderingControl-v1-Service.pdf
            # and http://upnp.org/specs/av/UPnP-av-AVTransport-v1-Service.pdf
            if variable.tag == "LastChange":
                last_change_tree = XML.fromstring(
                    variable.text.encode('utf-8'))
                # We assume there is only one InstanceID tag. This is true for
                # Sonos, as far as we know.
                # InstanceID can be in one of two namespaces, depending on
                # whether we are looking at an avTransport event or a
                # renderingControl event, so we need to look for both
                instance = last_change_tree.find(
                    "{urn:schemas-upnp-org:metadata-1-0/AVT/}InstanceID")
                if instance is None:
                    instance = last_change_tree.find(
                        "{urn:schemas-upnp-org:metadata-1-0/RCS/}InstanceID")
                if instance is None:
                    instance = last_change_tree.find("{urn:schemas-sonos-com:metadata-1-0/Queue/}QueueID")
                # Look at each variable within the LastChange event
                for last_change_var in instance:
                    tag = last_change_var.tag
                    # Remove any namespaces from the tags
                    if tag.startswith('{'):
                        tag = tag.split('}', 1)[1]
                    # Un-camel case it
                    tag = camel_to_underscore(tag)
                    # Now extract the relevant value for the variable.
                    # The UPnP specs suggest that the value of any variable
                    # evented via a LastChange Event will be in the 'val'
                    # attribute, but audio related variables may also have a
                    # 'channel' attribute. In addition, it seems that Sonos
                    # sometimes uses a text value instead: see
                    # http://forums.sonos.com/showthread.php?t=34663
                    value = last_change_var.get('val')
                    if value is None:
                        value = last_change_var.text
                    # If DIDL metadata is returned, convert it to a music
                    # library data structure
                    if value.startswith('<DIDL-Lite'):
                        # If sonos adds a field that we haven't registered don't hose us
                        try:
                            value = from_didl_string(value)[0]
                        except DIDLMetadataError:
                            pass
                    channel = last_change_var.get('channel')
                    if channel is not None:
                        if result.get(tag) is None:
                            result[tag] = {}
                        result[tag][channel] = value
                    else:
                        result[tag] = value
            else:
                result[camel_to_underscore(variable.tag)] = variable.text
    return result
