def dbc_checker(dbc_info: dict):
    for file_info in dbc_info.values():
        dbc = file_info["parse_result"]
        for msg_value in dbc["details"].values():
            if (msg_value.message_attributes["DiagRequest"].value == 1 or
                    msg_value.message_attributes["DiagResponse"].value == 1 or
                    msg_value.message_attributes["DiagState"].value == 1):
                return True
    return False
