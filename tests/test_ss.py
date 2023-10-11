from citemap import ss


def test_get_paper_data(s2client, default_fields):
    fields = default_fields
    s2 = ss.S2(s2client, fields)
    ID = "5d9e7dbf28382eb3d8e1bbd2cae6a1c8d223ce4a"
    data = s2.get_paper_data(ID)


def test_get_paper_data_with_other_fields(s2client, default_fields):
    fields = default_fields
    fields.abstract = True
    fields.citationCount = True
    s2 = ss.S2(s2client, fields)
    ID = "5d9e7dbf28382eb3d8e1bbd2cae6a1c8d223ce4a"
    data = s2.get_paper_data(ID)
