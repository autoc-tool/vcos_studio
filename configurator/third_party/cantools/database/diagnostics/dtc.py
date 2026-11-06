class Dtc:

    def __init__(self, name: str, value, record_info_dict, attr_info_dict=None):
        # The dtc name as a string.
        self.name: str = name
        self.value = value
        self.hex_format = hex(value)
        self.sae_format = self._int_to_sae_dtc(value)
        self.record_info_dict = record_info_dict
        self.attr_info_dict = attr_info_dict
        self.enable_condition_group_index = None

    # Conver integer value to sae format string
    def _int_to_sae_dtc(self, value):
        second_two_bits_mask = 3145728
        fault_system_table = ["P", "C", "B", "U"]
        first_two_bits = value >> 22
        fault_system = fault_system_table[first_two_bits]
        second_two_bits = (value & second_two_bits_mask) >> 20
        sae_dtc_str = fault_system + str(second_two_bits) + hex(value)[3:].upper()

        return sae_dtc_str

    # Set enable condition group index
    def set_enable_condition_group(self, index):
        self.enable_condition_group_index = index


class ObdDtc:

    def __init__(self, name: str, value, record_info_dict, attr_info_dict=None):
        # The dtc name as a string.
        self.name: str = name
        self.value = value
        self.hex_format = hex(value)
        self.record_info_dict = record_info_dict
        self.attr_info_dict = attr_info_dict
