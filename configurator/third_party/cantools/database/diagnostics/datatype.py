class DataType(object):

    def __init__(self, name, id_, bit_length, encoding, minimum, maximum, choices, byte_order, unit, factor, offset,
                 category, tag=None):
        self.name = name
        self.id_ = id_
        self.bit_length = bit_length
        self.encoding = encoding
        self.minimum = minimum
        self.maximum = maximum
        self.choices = choices
        self.byte_order = byte_order
        self.unit = unit
        self.factor = factor
        self.offset = offset
        self.category = category
        self.tag = tag
        self.data_type_str = None

    def set_data_type_str(self, value):
        self.data_type_str = value


class MuxDataType(DataType):

    def __init__(self, name, id_, bit_length, encoding, minimum, maximum, choices, byte_order, unit, factor, offset,
                 category):
        super().__init__(name, id_, bit_length, encoding, minimum, maximum, choices, byte_order, unit, factor, offset,
                         category)

