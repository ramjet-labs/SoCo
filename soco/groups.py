# -*- coding: utf-8 -*-
# pylint: disable=too-few-public-methods
"""
Classes and functionality relating to Sonos Groups

"""

from __future__ import unicode_literals


class ZoneGroup(object):

    """
    A class representing a Sonos Group. It looks like this::

        ZoneGroup(
            uid='RINCON_000E5879136C01400:58',
            coordinator=SoCo("192.168.1.101"),
            members=set([SoCo("192.168.1.101"), SoCo("192.168.1.102")])
            )
    """

    def __init__(self, uid, coordinator, members=None):
        #: The unique Sonos ID for this group
        self.uid = uid
        #: The :class:`Soco` instance which coordiantes this group
        self.coordinator = coordinator
        self.members = set(members) if members else set()

        group_names = sorted([m.player_name() for m in self.members])
        self._label = ", ".join(group_names)
        self._short_label = group_names[0]
        if len(group_names) > 1:
          self._short_label += " + {0}".format(len(group_names) - 1)

    def __iter__(self):
        return self.members.__iter__()

    def __contains__(self, member):
        return member in self.members

    def __repr__(self):
        return "{0}(uid='{1}', coordinator={2!r}, members={3!r})".format(
            self.__class__.__name__, self.uid, self.coordinator, self.members)

    @property
    def label(self):
        return self._label

    @property
    def short_label(self):
        return self._short_label
