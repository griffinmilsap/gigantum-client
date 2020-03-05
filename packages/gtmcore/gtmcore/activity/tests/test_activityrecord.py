# Copyright (c) 2017 FlashX, LLC
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import pytest
import json
import datetime
from gtmcore.activity.records import ActivityDetailRecord, ActivityDetailType, ActivityRecord, ActivityType, \
    ActivityAction
from gtmcore.activity.utils import DetailRecordList, ImmutableList


class TestActivityRecord(object):

    def test_constructor(self):
        """Test the constructor"""
        ar = ActivityRecord(ActivityType.MILESTONE)

        assert type(ar) == ActivityRecord
        assert ar.type == ActivityType.MILESTONE
        assert ar.commit is None
        assert ar.linked_commit is None
        assert ar.message is None
        assert ar.show is True
        assert ar.importance is None
        assert not ar.tags
        assert len(ar.detail_objects) == 0

        ar = ActivityRecord(ActivityType.CODE,
                            show=False,
                            message="message 1",
                            importance=23,
                            tags=['a', 'b'],
                            linked_commit='aadfadff',
                            username="user1",
                            email="user1@test.com")

        assert type(ar) == ActivityRecord
        assert ar.type == ActivityType.CODE
        assert ar.commit is None
        assert ar.linked_commit == 'aadfadff'
        assert ar.message == "message 1"
        assert ar.show is False
        assert ar.importance == 23
        assert ar.tags == ImmutableList(['a', 'b'])
        assert len(ar.detail_objects) == 0
        assert ar.username == 'user1'
        assert ar.email == 'user1@test.com'

    def test_add_detail_objects_sort(self):
        """Test adding values to the detail object"""
        adrs = []
        adr = ActivityDetailRecord(ActivityDetailType.CODE,
                                   show = True,
                                   importance = 100,
                                   data={"text/plain": "second"})
        adrs.append(adr)

        adr = ActivityDetailRecord(ActivityDetailType.CODE,
                                   show = True,
                                   importance = 200,
                                   data={"text/plain": "first"})
        adrs.append(adr)

        adr = ActivityDetailRecord(ActivityDetailType.CODE,
                                   show = False,
                                   importance = 0,
                                   data={"text/plain": "sixth"})
        adrs.append(adr)

        adr = ActivityDetailRecord(ActivityDetailType.OUTPUT_DATA,
                                   show = True,
                                   importance = 201,
                                   data={"text/plain": "forth"})
        adrs.append(adr)

        adr = ActivityDetailRecord(ActivityDetailType.RESULT,
                                   show = True,
                                   importance = 201,
                                   data={"text/plain": "third"})
        adrs.append(adr)

        adr = ActivityDetailRecord(ActivityDetailType.INPUT_DATA,
                                   show = False,
                                   importance = 201,
                                   data={"text/plain": "fifth"})
        adrs.append(adr)

        ar = ActivityRecord(ActivityType.CODE,
                            show=True,
                            message="added some code",
                            importance=50,
                            linked_commit='aaaaaaaa',
                            detail_objects=DetailRecordList(adrs))

        assert len(ar.detail_objects) == 6

        assert ar.detail_objects[0].data['text/plain'] == 'first'
        assert ar.detail_objects[1].data['text/plain'] == 'second'
        assert ar.detail_objects[2].data['text/plain'] == 'third'
        assert ar.detail_objects[3].data['text/plain'] == 'forth'
        assert ar.detail_objects[4].data['text/plain'] == 'fifth'
        assert ar.detail_objects[5].data['text/plain'] == 'sixth'

    def test_log_str_prop_errors(self):
        """Test the log string property"""
        ar = ActivityRecord(ActivityType.CODE,
                            show=True,
                            importance=50,
                            linked_commit='aaaaaaaa')

        with pytest.raises(ValueError):
            # Missing message
            _ = ar.log_str

        adr = ActivityDetailRecord(ActivityDetailType.CODE,
                                   data={"text/plain": "this is some data"})

        ar = ActivityRecord(ActivityType.CODE,
                            show=True,
                            message="added some code",
                            importance=50,
                            linked_commit='aaaaaaaa',
                            detail_objects=DetailRecordList([adr]))

        with pytest.raises(ValueError):
            # Missing detail key for detail record
            ar.log_str

    def test_log_str_prop(self):
        """Test the log string property"""
        adr = ActivityDetailRecord(ActivityDetailType.CODE,
                                   key='my_fake_detail_key',
                                   data={'text/plain': 'this is some data'})

        ar = ActivityRecord(ActivityType.CODE,
                            show=True,
                            message="added some code",
                            importance=50,
                            linked_commit='aaaaaaaa',
                            detail_objects=DetailRecordList([adr]))

        assert ar.log_str == """_GTM_ACTIVITY_START_**
msg:added some code**
metadata:{"show":true,"importance":50,"type":2,"linked_commit":"aaaaaaaa","tags":[]}**
details:**
4,1,0,my_fake_detail_key,0**
_GTM_ACTIVITY_END_"""

    def test_from_log_str(self):
        """Test the creating from a log string"""

        test_str = """_GTM_ACTIVITY_START_**
msg:added some code**
metadata:{"show":true,"importance":50,"type":2,"linked_commit":"aaaaaaaa","tags":["test"]}**
details:**
4,1,255,my_fake_detail_key,0**
2,0,0,my_fake_detail_key2,3**
_GTM_ACTIVITY_END_"""

        ar = ActivityRecord.from_log_str(test_str, "bbbbbb", datetime.datetime.utcnow())

        assert type(ar) == ActivityRecord
        assert ar.type == ActivityType.CODE
        assert ar.show is True
        assert ar.importance == 50
        assert ar.linked_commit == "aaaaaaaa"
        assert ar.commit == "bbbbbb"
        assert ar.tags == ImmutableList(['test'])
        
        assert len(ar.detail_objects) == 2
        assert type(ar.detail_objects[0]) == ActivityDetailRecord
        assert ar.detail_objects[0].type == ActivityDetailType.CODE
        assert ar.detail_objects[0].action == ActivityAction.NOACTION
        assert ar.detail_objects[0].key == "my_fake_detail_key"
        assert ar.detail_objects[0].show is True
        assert ar.detail_objects[0].importance == 255
        assert len(ar.detail_objects[0].tags) == 0
        assert ar.detail_objects[0].is_loaded is False

        assert type(ar.detail_objects[1]) == ActivityDetailRecord
        assert ar.detail_objects[1].type == ActivityDetailType.RESULT
        assert ar.detail_objects[1].action == ActivityAction.DELETE
        assert ar.detail_objects[1].key == "my_fake_detail_key2"
        assert ar.detail_objects[1].show is False
        assert ar.detail_objects[1].importance == 0
        assert len(ar.detail_objects[1].tags) == 0
        assert ar.detail_objects[1].is_loaded is False

    def test_update_detail_object(self):
        """Test converting to a dictionary"""
        adr1 = ActivityDetailRecord(ActivityDetailType.CODE,
                                    show=True,
                                    importance=100,
                                    data={"text/plain": "first"})

        adr2 = ActivityDetailRecord(ActivityDetailType.CODE,
                                    show=True,
                                    importance=0,
                                    data={"text/plain": "second"})

        ar = ActivityRecord(ActivityType.CODE,
                            show=True,
                            message="added some code",
                            importance=50,
                            linked_commit='aaaaaaaa',
                            detail_objects=DetailRecordList([adr1, adr2]))

        assert len(ar.detail_objects) == 2
        assert ar.detail_objects[0].data['text/plain'] == 'first'
        assert ar.detail_objects[1].data['text/plain'] == 'second'

        adr2 = adr2.update(importance = 200)

        detail_objects = list(ar.detail_objects)
        detail_objects[1] = adr2
        ar = ar.update(detail_objects = DetailRecordList(detail_objects))

        assert len(ar.detail_objects) == 2
        assert ar.detail_objects[0].data['text/plain'] == 'second'
        assert ar.detail_objects[1].data['text/plain'] == 'first'

    def test_trim_detail_objects(self):
        """"""
        adr1 = ActivityDetailRecord(ActivityDetailType.CODE,
                                    show=True,
                                    importance=100,
                                    data={"text/plain": "first"})

        adr2 = ActivityDetailRecord(ActivityDetailType.CODE,
                                    show=True,
                                    importance=0,
                                    data={"text/plain": "second"})

        adr3 = ActivityDetailRecord(ActivityDetailType.CODE,
                                    show=True,
                                    importance=0,
                                    data={"text/plain": "third"})

        ar = ActivityRecord(ActivityType.CODE,
                            show=True,
                            message="added some code",
                            importance=50,
                            linked_commit='aaaaaaaa',
                            detail_objects=DetailRecordList([adr1, adr2, adr3]))

        assert len(ar.detail_objects) == 3
        assert ar.detail_objects[0].data['text/plain'] == 'first'
        assert ar.detail_objects[1].data['text/plain'] == 'second'
        assert ar.detail_objects[2].data['text/plain'] == 'third'

        ar = ar.trim_detail_objects(2)

        assert len(ar.detail_objects) == 2
        assert ar.detail_objects[0].data['text/plain'] == 'first'
        assert ar.detail_objects[1].data['text/plain'] == 'second'

        with pytest.raises(ValueError):
            ar.trim_detail_objects(0)
