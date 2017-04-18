from .exceptions import DIDLMetadataError
from .data_structures import from_didl_string
from .utils import camel_to_underscore
from .xml import XML
from .groups import ZoneGroup
from soco import config


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
  properties = tree.findall('{urn:schemas-upnp-org:event-1-0}property')
  for prop in properties:
    for variable in prop:
      # Special handling for a LastChange event specially. For details on
      # LastChange events, see
      # http://upnp.org/specs/av/UPnP-av-RenderingControl-v1-Service.pdf
      # and http://upnp.org/specs/av/UPnP-av-AVTransport-v1-Service.pdf
      if variable.tag == "LastChange":
        last_change_tree = XML.fromstring(variable.text.encode('utf-8'))
        # We assume there is only one InstanceID tag. This is true for
        # Sonos, as far as we know.
        # InstanceID can be in one of two namespaces, depending on
        # whether we are looking at an avTransport event or a
        # renderingControl event, so we need to look for both
        instance = last_change_tree.find("{urn:schemas-upnp-org:metadata-1-0/AVT/}InstanceID")
        if instance is None:
          instance = last_change_tree.find("{urn:schemas-upnp-org:metadata-1-0/RCS/}InstanceID")
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

def parse_zone_group_state(xml_group_state):
  """ The Zone Group State contains a lot of useful information. Retrieve
  and parse it, and populate the relevant properties. """
  groups = set()
  # Loop over each ZoneGroup Element
  for group_element in xml_group_state.findall('ZoneGroup'):
    groups.add(parse_zone_group(group_element))
  return groups

def parse_zone_group(group_element):
  coordinator_uid = group_element.attrib['Coordinator']
  group_coordinator = None
  members = set()
  for member_element in group_element.findall('ZoneGroupMember'):
    zone = parse_zone_group_member(member_element)
    # Perform extra processing relevant to direct zone group
    # members
    #
    # If this element has the same UUID as the coordinator, it is
    # the coordinator
    if zone._uid == coordinator_uid:
      group_coordinator = zone
      zone._is_coordinator = True
    else:
      zone._is_coordinator = False
    # is_bridge doesn't change, but it does no real harm to
    # set/reset it here, just in case the zone has not been seen
    # before
    zone._is_bridge = True if member_element.attrib.get('IsZoneBridge') == '1' else False
    # add the zone to the members for this group
    members.add(zone)
    # Loop over Satellite elements if present, and process as for
    # ZoneGroup elements
    for satellite_element in member_element.findall('Satellite'):
      zone = parse_zone_group_member(satellite_element)
      # Assume a satellite can't be a bridge or coordinator, so
      # no need to check.
      #
      # Add the zone to the members for this group.
      members.add(zone)
  return ZoneGroup(
      uid=group_element.attrib['ID'],
      coordinator=group_coordinator,
      members=members,
  )

def parse_zone_group_member(member_element):
  """ Parse a ZoneGroupMember or Satellite element from Zone Group
  State, create a SoCo instance for the member, set basic attributes
  and return it. """
  # Create a SoCo instance for each member. Because SoCo
  # instances are singletons, this is cheap if they have already
  # been created, and useful if they haven't. We can then
  # update various properties for that instance.
  member_attribs = member_element.attrib
  ip_addr = member_attribs['Location'].split('//')[1].split(':')[0]
  zone = config.SOCO_CLASS(ip_addr)
  # uid doesn't change, but it's not harmful to (re)set it, in case
  # the zone is as yet unseen.
  zone._uid = member_attribs['UUID']
  zone._player_name = member_attribs['ZoneName']
  # add the zone to the set of all members, and to the set
  # of visible members if appropriate
  is_visible = False if member_attribs.get('Invisible') == '1' else True
  return zone

