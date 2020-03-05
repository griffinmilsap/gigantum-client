import pytest
import json
from gtmcore.activity.records import ActivityDetailRecord, ActivityDetailType, ActivityAction


class TestActivityDetailRecord(object):

    def test_constructor(self):
        """Test the constructor"""
        adr = ActivityDetailRecord(ActivityDetailType.CODE)

        assert type(adr) == ActivityDetailRecord
        assert adr.type == ActivityDetailType.CODE
        assert adr.key is None
        assert adr.show is True
        assert adr.importance == 0
        assert adr.tags == []
        assert adr.data == {}

        adr = ActivityDetailRecord(ActivityDetailType.CODE, key="my_key", show=False, importance=23)

        assert type(adr) == ActivityDetailRecord
        assert adr.type == ActivityDetailType.CODE
        assert adr.key == "my_key"
        assert adr.show is False
        assert adr.importance == 23
        assert adr.tags == []
        assert adr.data == {}

    def test_log_str_prop(self):
        """Test the log string property"""
        adr = ActivityDetailRecord(ActivityDetailType.CODE_EXECUTED, key="my_key", show=False, importance=233)

        assert adr.log_str == "3,0,233,my_key,0"

        adr = ActivityDetailRecord(ActivityDetailType.OUTPUT_DATA, key="my_key", show=True, importance=25)

        assert adr.log_str == "1,1,25,my_key,0"

        adr = ActivityDetailRecord(ActivityDetailType.OUTPUT_DATA, key="my_key", show=True, importance=25,
                                   action=ActivityAction.EDIT)

        assert adr.log_str == "1,1,25,my_key,2"

    def test_from_log_str_legacy(self):
        """Test the creating from a log string"""
        adr = ActivityDetailRecord.from_log_str("2,1,25,my_key")

        assert type(adr) == ActivityDetailRecord
        assert adr.type == ActivityDetailType.RESULT
        assert adr.key == "my_key"
        assert adr.show is True
        assert adr.importance == 25
        assert adr.tags == []
        assert adr.data == {}
        assert adr.action == ActivityAction.NOACTION

    def test_from_log_str(self):
        """Test the creating from a log string"""
        adr = ActivityDetailRecord.from_log_str("2,1,25,my_key,3")

        assert type(adr) == ActivityDetailRecord
        assert adr.type == ActivityDetailType.RESULT
        assert adr.key == "my_key"
        assert adr.show is True
        assert adr.importance == 25
        assert adr.tags == []
        assert adr.data == {}
        assert adr.action == ActivityAction.DELETE

    def test_add_value(self):
        """Test adding values to the detail object"""
        adr = ActivityDetailRecord(ActivityDetailType.CODE_EXECUTED, key="my_key2")

        adr = adr.add_value("text/plain", "this is some data")
        adr = adr.add_value("text/html", "<p>this is some data</p>")

        assert len(adr.data.keys()) == 2
        assert adr.data["text/plain"] == "this is some data"
        assert adr.data["text/html"] == "<p>this is some data</p>"

        with pytest.raises(ValueError):
            adr.add_value("text/html", "<p>this is some data</p>")

    def test_data_size(self):
        """Test getting the size of details stored"""
        adr = ActivityDetailRecord(ActivityDetailType.CODE_EXECUTED, key="my_key2")

        assert adr.data_size == 0

        adr = adr.add_value("text/plain", "0000000000")
        assert adr.data_size == 10

        adr = adr.add_value("text/html", "0000000000")
        assert adr.data_size == 20

    def test_to_dict(self):
        """Test converting to a dictionary"""
        adr = ActivityDetailRecord(ActivityDetailType.CODE_EXECUTED, key="my_key2", show=True, importance=25)
        adr = adr.add_value("text/plain", "this is some data")
        adr = adr.add_value("text/html", "<p>this is some data</p>")

        dict_obj = adr.to_dict()
        assert type(dict_obj) == dict
        assert dict_obj['type'] == 3
        assert dict_obj['action'] == 0
        assert dict_obj['importance'] == 25
        assert dict_obj['show'] == 1
        assert dict_obj['data'] == {"text/plain": "this is some data",
                                    "text/html": "<p>this is some data</p>"}

    def test_to_bytes_from_bytes(self):
        """Test converting to a byte array"""
        adr = ActivityDetailRecord(ActivityDetailType.CODE_EXECUTED,
                                   key="my_key3",
                                   show=True,
                                   importance=225,
                                   action=ActivityAction.CREATE,
                                   data={"text/plain": "this is some data"})

        byte_array_no_compression = adr.to_bytes(compress=False)
        assert type(byte_array_no_compression) == bytes

        adr2 = ActivityDetailRecord.from_bytes(byte_array_no_compression, decompress=False)

        assert type(adr2) == ActivityDetailRecord
        assert adr2.type == ActivityDetailType.CODE_EXECUTED
        assert adr2.action == ActivityAction.CREATE
        assert adr2.key is None
        assert adr2.show is True
        assert adr2.importance == 225
        assert adr2.tags == []
        assert adr2.data == {"text/plain": "this is some data"}

    def test_compression(self):
        """Test compression on large objects"""
        adr = ActivityDetailRecord(ActivityDetailType.INPUT_DATA, key="my_ke3", show=True, importance=125)
        adr = adr.add_value("text/plain", "this is some data00000000000000000000000000000000000" * 1000)

        byte_array_no_compression = adr.to_bytes(compress=False)
        assert type(byte_array_no_compression) == bytes

        adr2 = ActivityDetailRecord(ActivityDetailType.INPUT_DATA, key="my_ke3", show=True, importance=125)
        adr2 = adr2.add_value("text/plain", "this is some data00000000000000000000000000000000000" * 1000)
        byte_array_compression = adr2.to_bytes(compress=True)
        assert type(byte_array_compression) == bytes

        assert len(byte_array_compression) < len(byte_array_no_compression)

        adr3 = ActivityDetailRecord.from_bytes(byte_array_compression, decompress=True)

        assert type(adr3) == ActivityDetailRecord
        assert adr3.type == ActivityDetailType.INPUT_DATA
        assert adr3.action == ActivityAction.NOACTION
        assert adr3.key is None
        assert adr3.show is True
        assert adr3.importance == 125
        assert adr3.tags == []
        assert adr3.data == adr.data

    def test_to_json(self):
        """Test converting to json"""
        adr = ActivityDetailRecord(ActivityDetailType.ENVIRONMENT,
                                   key="my_key3",
                                   show=True,
                                   importance=225,
                                   data={"text/plain": "this is some data"})

        adr_in_json = adr.to_json()
        assert type(adr_in_json) == str

        json_dict = json.loads(adr_in_json)

        assert json_dict['type'] == 0
        assert json_dict['importance'] == 225
        assert json_dict['show'] is True
        assert json_dict['data'] == {'text/plain': "this is some data"}

    def test_jsonify_data(self):
        """Test converting to json"""
        adr = ActivityDetailRecord(ActivityDetailType.ENVIRONMENT,
                                   key="my_key3fgjg",
                                   show=True,
                                   importance=45,
                                   data={"text/plain": "this is some data to jsonify",
                                         "text/markdown": "this is some data to `jsonify`"})

        data = adr.jsonify_data()
        assert type(data) == dict

        assert len(data.keys()) == 2
        assert data['text/plain'] == "this is some data to jsonify"
        assert data['text/markdown'] == "this is some data to `jsonify`"
