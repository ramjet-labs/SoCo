from soco import config
from soco import core
from soco import parser
from soco import groups
import unittest
from unittest import mock
from soco.xml import XML

class ParserTestCase(unittest.TestCase):

  def test_zone_group_parser(self):
    tree = XML.fromstring(zone_group_xml().encode('utf-8'))
    zone_groups = parser.parse_zone_group_state(tree)
    self.assertEqual(len(zone_groups), 2)
    ids = [z.uid for z in zone_groups]
    self.assertCountEqual(["RINCON_000XXXX1400:0", "RINCON_000XXX1400:46"], ids)

def zone_group_xml():
  return """
    <ZoneGroups>
      <ZoneGroup Coordinator="RINCON_000XXX1400" ID="RINCON_000XXXX1400:0">
        <ZoneGroupMember
            BootSeq="33"
            Configuration="1"
            Icon="x-rincon-roomicon:zoneextender"
            Invisible="1"
            IsZoneBridge="1"
            Location="http://192.168.1.100:1400/xml/device_description.xml"
            MinCompatibleVersion="22.0-00000"
            SoftwareVersion="24.1-74200"
            UUID="RINCON_000ZZZ1400"
            ZoneName="BRIDGE"/>
      </ZoneGroup>
      <ZoneGroup Coordinator="RINCON_000XXX1400" ID="RINCON_000XXX1400:46">
        <ZoneGroupMember
            BootSeq="44"
            Configuration="1"
            Icon="x-rincon-roomicon:living"
            Location="http://192.168.1.101:1400/xml/device_description.xml"
            MinCompatibleVersion="22.0-00000"
            SoftwareVersion="24.1-74200"
            UUID="RINCON_000XXX1400"
            ZoneName="Living Room"/>
        <ZoneGroupMember
            BootSeq="52"
            Configuration="1"
            Icon="x-rincon-roomicon:kitchen"
            Location="http://192.168.1.102:1400/xml/device_description.xml"
            MinCompatibleVersion="22.0-00000"
            SoftwareVersion="24.1-74200"
            UUID="RINCON_000YYY1400"
            ZoneName="Kitchen"/>
      </ZoneGroup>
     </ZoneGroups>
  """


if __name__ == '__main__':
  unittest.main(verbosity=2)

