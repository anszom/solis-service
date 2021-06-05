from datetime import datetime
from io import BytesIO
from functools import reduce
from struct import unpack_from, pack

import pint


ureg = pint.UnitRegistry()

def parse_header(msghdr):
    [ payload_length, type, resp_idx, req_idx, serialno ] = unpack_from("<xHxBBBI", msghdr, 0)
    return {
        "payload_length": payload_length,
        "type": type,
        "resp_idx": resp_idx,
        "req_idx": req_idx,
        "serialno": serialno
    }

def parse_inverter_message(message):
    [   flags, timestamp,
        serialno, temp, pv1_v, pv2_v, pv1_i, pv2_i,
        ac1_i, ac2_i, ac3_i, ac1_v, ac2_v, ac3_v, ac_hz,
        ac_pwr, daily_wh, total_wh, runtime, status,
        swver, hwver, modtemp, bus_v, cpu_v, countdown,
        inputmode, pv1_r, pv2_r, imp, ctry, ind1_i, ct_w,
        leakage_i, a_dist, b_dist, c_dist, vdspver, dspver,
        yy, mm, dd, h, m, s ] = unpack_from(
                "<BxxIxxxxxxxxxxxxxx16shHHHHHHHHHHHIIIIH4s4sHHHxxHHHHHHHHHHHH4s4sBBBBBBxxxx",
                message, 11);
    return {
        "is_current":                       (flags & 0x80) == 0,
        "timestamp":                        timestamp,
        "inverter_serial_number":           serialno.rstrip(),
        "inverter_temperature":             0.1 * temp * ureg.centigrade,
        "dc_voltage_pv1":                   0.1 * pv1_v * ureg.volt,
        "dc_voltage_pv2":                   0.1 * pv2_v * ureg.volt,
        "dc_current_pv1":                   0.1 * pv1_i * ureg.amperes,
        "dc_current_pv2":                   0.1 * pv2_i * ureg.amperes,
        "ac_current_1":                     0.1 * ac1_i * ureg.amperes,
        "ac_current_2":                     0.1 * ac2_i * ureg.amperes,
        "ac_current_3":                     0.1 * ac3_i * ureg.amperes,
        "ac_voltage_1":                     0.1 * ac1_v * ureg.volt,
        "ac_voltage_2":                     0.1 * ac2_v * ureg.volt,
        "ac_voltage_3":                     0.1 * ac3_v * ureg.volt,
        "ac_output_frequency":              0.01 * ac_hz * ureg.hertz,
        "daily_active_generation":          0.01 * daily_wh * ureg.kilowatt_hour,
        "total_active_generation":          0.1 * total_wh * ureg.kilowatt_hour,
    }


def checksum_byte(buffer):
    return reduce(lambda lrc, x: (lrc + x) & 255, buffer) & 255


def mock_server_response(header, request_payload, timestamp=None):
    unix_time = int(datetime.utcnow().timestamp() if timestamp is None else timestamp)
    
    # don't know what's the meaning of these magic values
    # the first byte seems to usually echo the first byte of the request payload
    payload = pack("<BBIBBBB", request_payload[0], 0x01, unix_time, 0xaa, 0xaa, 0x00, 0x00)

    resp_type = header['type'] - 0x30
    header = pack("<BHBBBBI", 0xa5, len(payload), 0x00, resp_type, header['req_idx'], header['req_idx'], header['serialno'])
    message = header + payload
    message += pack("BB", checksum_byte(message[1:]), 0x15)
    return message
