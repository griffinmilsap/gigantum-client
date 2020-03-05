# Copyright (c) 2020 FlashX, LLC
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

from gtmcore.activity.records import ActivityDetailRecord, ActivityDetailType, ActivityRecord, ActivityType, \
    ActivityAction
from gtmcore.activity.utils import TextData, DetailRecordList
from gtmcore.activity.processors.core import ActivityDetailProgressProcessor

class TestActivityDetailProgressProcessor(object):
    def test_processor(self):
        def create_detail(text):
            adr = ActivityDetailRecord(ActivityDetailType.RESULT,
                                       data=TextData('plain', text))
            return adr

        adrs = [
            create_detail('regular line'),
            create_detail('      '),
            create_detail('\n'),
            create_detail('\n       \n\n'),
            create_detail('\x1b[A\x1b[Amove up two lines'),
            create_detail('\rrewrite the line'),
            create_detail('\n\rstart a new status line'),
        ]

        ar = ActivityRecord(ActivityType.CODE,
                            detail_objects=DetailRecordList(adrs))

        assert ar.num_detail_objects == len(adrs)

        ar = ActivityDetailProgressProcessor().process(ar, [], {}, {})

        # One regular line of text
        # The first line of text that starts with \r or \n\r is kept as it is the final
        #    output from a status line
        assert ar.num_detail_objects == 2
        assert ar.detail_objects[0].data['text/plain'] == 'regular line'
        assert ar.detail_objects[1].data['text/plain'] == '\rrewrite the line'
