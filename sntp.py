from socket import *
from datetime import datetime
from enum import IntEnum


class Server:
    def __init__(self, offset, port: int = 123):
        self.offset = offset
        self.sock = socket(AF_INET, SOCK_DGRAM)
        try:
            self.sock.bind(('localhost', port))
        except Exception:
            print('Something went wrong! Check socket!')
            self.sock.close()
            exit(0)

    def start_server(self):
        print('Server has been started!\nHe is lying for ' + show_inp + ' sec')
        while True:
            print('\nWaiting...')
            request, address = self.sock.recvfrom(1024)
            if request:
                self.handle_request(request, address)

    def handle_request(self, message: bytes, address):
        receive_timestamp = datetime.utcnow()
        print('Request' + str(address))
        response = self.get_answer(message, receive_timestamp)
        self.sock.sendto(response, address)

    def get_answer(self, data: bytes, rec_ts: datetime) -> bytes:
        request = Message.parse(data)
        response = Message(li=LeapIndicator.no_warning,
                           vn=request.vn,
                           mode=Mode.server,
                           stratum=1,
                           originate_timestamp=request.transmit_timestamp,
                           receive_timestamp=self._time_shift(Message.to_seconds(rec_ts)),
                           transmit_timestamp=self._time_shift(Message.to_seconds(datetime.utcnow()))
                           ).to_bytes()
        response[24:32] = data[40:48]
        return bytes(response)

    def _time_shift(self, time: float) -> float:
        return time + self.offset


class LeapIndicator(IntEnum):
    no_warning = 0


class Mode(IntEnum):
    reserved = 0
    symmetric_active = 1
    symmetric_passive = 2
    client = 3
    server = 4
    broadcast = 5
    reserved_for_NTP_control_message = 6
    reserved_for_private_use = 7


class Message:
    epoch_time = datetime(1900, 1, 1)

    def __init__(self,
                 li=LeapIndicator.no_warning,
                 vn: int = 4,
                 mode: Mode = Mode.reserved,
                 stratum: int = 1,
                 poll: int = 0,
                 precision: int = 0,
                 root_delay: float = 0,
                 root_dispersion: float = 0,
                 reference_identifier: int = 'GOES',
                 reference_timestamp: float = 0,
                 originate_timestamp: float = 0,
                 receive_timestamp: float = 0,
                 transmit_timestamp: float = 0):
        self.li = li
        self.vn = vn
        self.mode = mode
        self.stratum = stratum
        self.poll = poll
        self.precision = precision
        self.root_delay = root_delay
        self.root_dispersion = root_dispersion
        self.reference_identifier = reference_identifier
        self.reference_timestamp = reference_timestamp
        self.originate_timestamp = originate_timestamp
        self.receive_timestamp = receive_timestamp
        self.transmit_timestamp = transmit_timestamp

    @staticmethod
    def parse(data: bytes):
        first_byte = (bin(data[0])[2:]).zfill(8)

        LI = LeapIndicator(int(first_byte[0:2], 2))
        VN = int(first_byte[2:5], 2)
        mode = Mode(int(first_byte[5:8], 2))

        stratum = data[1]
        poll = data[2]
        precision = data[3]

        root_delay = Message._from_bytes(data[4:6]) + Message._from_bytes(data[6:8]) / (2 ** 16)
        root_dispersion = Message._from_bytes(data[8:10]) + Message._from_bytes(data[10:12]) / (2 ** 16)
        reference_identifier = data[12:16].decode('utf-8')

        reference_timestamp = Message._from_bytes(data[16:20]) + Message._from_bytes(data[20:24]) / 2 ** 32
        originate_timestamp = Message._from_bytes(data[24:28]) + Message._from_bytes(data[28:32]) / 2 ** 32
        receive_timestamp = Message._from_bytes(data[32:36]) + Message._from_bytes(data[36:40]) / 2 ** 32
        transmit_timestamp = Message._from_bytes(data[40:44]) + Message._from_bytes(data[44:48]) / 2 ** 32

        return Message(LI, VN, mode, stratum, poll, precision, root_delay, root_dispersion, reference_identifier,
                       reference_timestamp, originate_timestamp, receive_timestamp, transmit_timestamp)

    @staticmethod
    def _from_bytes(raw: bytes) -> int:
        return int.from_bytes(raw, byteorder='big')

    def to_bytes(self) -> bytearray:
        res = bytearray()
        first_byte = (bin(self.li)[2:]).zfill(2) + \
                     (bin(self.vn)[2:]).zfill(3) + \
                     (bin(self.mode)[2:]).zfill(3)
        res += int(first_byte, 2).to_bytes(1, 'big')
        res += self.stratum.to_bytes(1, 'big')
        res += self.poll.to_bytes(1, 'big')
        res += self.precision.to_bytes(1, 'big')
        res += Message.encode_timestamp_format(self.root_delay, 4)
        a = Message.encode_timestamp_format(self.root_dispersion, 4)
        res += a
        res += self.reference_identifier.encode('utf-8')
        res += Message.encode_timestamp_format(self.reference_timestamp, 8)
        res += Message.encode_timestamp_format(self.originate_timestamp, 8)
        res += Message.encode_timestamp_format(self.receive_timestamp, 8)
        res += Message.encode_timestamp_format(self.transmit_timestamp, 8)

        return res

    @staticmethod
    def encode_timestamp_format(timestamp: float, length: int) -> bytes:
        half = length // 2
        parts = str(timestamp).split('.')
        seconds = int(parts[0])
        sec_frac = float('0.' + parts[1]) if len(parts) > 1 else 0
        sec_frac *= 2 ** (half * 8)
        return seconds.to_bytes(half, 'big') + int(sec_frac).to_bytes(half, 'big')

    @staticmethod
    def to_seconds(stamp: datetime) -> float:
        return (stamp - Message.epoch_time).total_seconds()


def main():
    input_offset = input('Please, input offset of time in sec: ')
    global show_inp
    show_inp = input_offset
    try: offset = float(input_offset)
    except ValueError:
        print("Offset is a number!\nTry again.")
        exit()
    Server(offset).start_server()


if __name__ == "__main__":
    main()